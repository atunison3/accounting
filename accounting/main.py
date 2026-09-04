"""FastAPI entry point for the accounting application.

The API is a thin presentation layer: request validation is handled by
Pydantic/domain models, use cases live in application services, and SQLite is
selected only when wiring the application at the edge.
"""

from __future__ import annotations

import logging
import sqlite3
import time
from datetime import date
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from accounting.application.services import AccountingService
from accounting.domain.models import (
    Account,
    AccountingTransaction,
    Business,
    TransactionLine,
    User,
)
from accounting.infrastructure.sqlite.connection import DEFAULT_DATABASE_PATH, get_connection
from accounting.website.routes import router as website_router
from accounting.website.income_statement import router as income_statement_router
from accounting.infrastructure.sqlite.repositories import (
    SqliteAccountRepository,
    SqliteBusinessRepository,
    SqliteTransactionRepository,
    SqliteUserRepository,
)


class TransactionLineInput(BaseModel):
    account_id: int
    amount_cents: int = Field(ge=0)
    is_debit: bool


class TransactionInput(BaseModel):
    business_id: int = Field(gt=0)
    transaction_date: date
    currency_code: str = Field(default="USD", min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")
    description: str = Field(min_length=1)
    user_id: int = Field(gt=0)
    posting_reference: str | None = None
    lines: list[TransactionLineInput] = Field(min_length=2)


DATA_DIRECTORY = Path.home() / ".app_data" / "accounting"
LOG_DIRECTORY = DATA_DIRECTORY / "logs"
LOG_FILE = LOG_DIRECTORY / "accounting.log"
LOGGER = logging.getLogger("accounting.api")
WEBSITE_STATIC_DIR = Path(__file__).with_name("website") / "static"


def get_database_path(request: Request) -> str | Path:
    """Resolve the database configured on the current application instance."""
    return request.app.state.db_path


DatabasePath = Annotated[str | Path, Depends(get_database_path)]


def configure_logging() -> logging.Logger:
    """Configure rotating file logging without duplicating handlers."""
    LOG_DIRECTORY.mkdir(parents=True, exist_ok=True)
    LOGGER.setLevel(logging.INFO)
    LOGGER.propagate = False

    if not LOGGER.handlers:
        handler = RotatingFileHandler(LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
        LOGGER.addHandler(handler)

    return LOGGER


def create_app(db_path: str | Path = DEFAULT_DATABASE_PATH) -> FastAPI:  # noqa: C901, PLR0915
    """Build the API and wire its application services to SQLite adapters."""
    logger = configure_logging()
    app = FastAPI(title="Accounting API", version="0.1.0")
    app.state.db_path = db_path
    app.mount("/static", StaticFiles(directory=WEBSITE_STATIC_DIR), name="static")
    app.include_router(website_router)
    app.include_router(income_statement_router)

    @app.middleware("http")
    async def log_requests(request: Request, call_next: Any) -> Any:
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("Unhandled request error method=%s path=%s", request.method, request.url.path)
            raise
        duration_ms = (time.perf_counter() - started) * 1000
        logger.info(
            "Request completed method=%s path=%s status=%s duration_ms=%.2f",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response

    logger.info("Accounting API initialized database=%s log_file=%s", db_path, LOG_FILE)

    @app.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/users", response_model=User, status_code=status.HTTP_201_CREATED, tags=["users"])
    def create_user(user: User, path: DatabasePath) -> User:
        try:
            with get_connection(path) as connection:
                user_id = SqliteUserRepository(connection).add(user)
                created = SqliteUserRepository(connection).get_by_id(user_id)
        except sqlite3.IntegrityError as exc:
            raise HTTPException(
                status_code=409, detail="User already exists or violates a database constraint"
            ) from exc
        if created is None:
            raise HTTPException(status_code=500, detail="User was not created")
        return created

    @app.get("/users/{user_id}", response_model=User, tags=["users"])
    def get_user(user_id: int, path: DatabasePath) -> User:
        with get_connection(path) as connection:
            user = SqliteUserRepository(connection).get_by_id(user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        return user

    @app.post("/businesses", response_model=Business, status_code=status.HTTP_201_CREATED, tags=["businesses"])
    def create_business(business: Business, path: DatabasePath) -> Business:
        try:
            with get_connection(path) as connection:
                business_id = SqliteBusinessRepository(connection).add(business)
                created = SqliteBusinessRepository(connection).get_by_id(business_id)
        except sqlite3.IntegrityError as exc:
            raise HTTPException(status_code=400, detail="Business violates a database constraint") from exc
        if created is None:
            raise HTTPException(status_code=500, detail="Business was not created")
        return created

    @app.get("/businesses", response_model=list[Business], tags=["businesses"])
    def list_businesses(path: DatabasePath) -> list[Business]:
        with get_connection(path) as connection:
            return SqliteBusinessRepository(connection).get_all()

    @app.post("/accounts", response_model=Account, status_code=status.HTTP_201_CREATED, tags=["accounts"])
    def create_account(account: Account, path: DatabasePath) -> Account:
        try:
            with get_connection(path) as connection:
                account_id = SqliteAccountRepository(connection).add(account)
                created = SqliteAccountRepository(connection).get_by_id(account_id)
        except sqlite3.IntegrityError as exc:
            raise HTTPException(status_code=400, detail="Account violates a database constraint") from exc
        if created is None:
            raise HTTPException(status_code=500, detail="Account was not created")
        return created

    @app.get("/businesses/{business_id}/accounts", response_model=list[Account], tags=["accounts"])
    def list_accounts(business_id: int, path: DatabasePath) -> list[Account]:
        with get_connection(path) as connection:
            return SqliteAccountRepository(connection).get_for_business(business_id)

    @app.post(
        "/transactions",
        response_model=AccountingTransaction,
        status_code=status.HTTP_201_CREATED,
        tags=["transactions"],
    )
    def create_transaction(payload: TransactionInput, path: DatabasePath) -> AccountingTransaction:
        lines = [TransactionLine(transaction_id=0, **line.model_dump()) for line in payload.lines]
        try:
            with get_connection(path) as connection:
                repository = SqliteTransactionRepository(connection)
                transaction_id = AccountingService(repository).create_transaction(
                    business_id=payload.business_id,
                    transaction_date=payload.transaction_date,
                    currency_code=payload.currency_code,
                    description=payload.description,
                    posting_reference=payload.posting_reference,
                    lines=lines,
                    user_id=payload.user_id,
                )
                created = repository.get_by_id(transaction_id)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except sqlite3.IntegrityError as exc:
            raise HTTPException(status_code=400, detail="Transaction violates a database constraint") from exc
        if created is None:
            raise HTTPException(status_code=500, detail="Transaction was not created")
        return created

    @app.get("/transactions/{transaction_id}", response_model=AccountingTransaction, tags=["transactions"])
    def get_transaction(transaction_id: int, path: DatabasePath) -> AccountingTransaction:
        with get_connection(path) as connection:
            transaction = SqliteTransactionRepository(connection).get_by_id(transaction_id)
        if transaction is None:
            raise HTTPException(status_code=404, detail="Transaction not found")
        return transaction

    @app.get("/transactions/{transaction_id}/lines", response_model=list[TransactionLine], tags=["transactions"])
    def get_transaction_lines(transaction_id: int, path: DatabasePath) -> list[TransactionLine]:
        with get_connection(path) as connection:
            if SqliteTransactionRepository(connection).get_by_id(transaction_id) is None:
                raise HTTPException(status_code=404, detail="Transaction not found")
            return SqliteTransactionRepository(connection).get_lines(transaction_id)

    @app.delete(
        "/transactions/{transaction_id}",
        response_model=None,
        status_code=status.HTTP_204_NO_CONTENT,
        tags=["transactions"],
    )
    def delete_transaction(transaction_id: int, path: DatabasePath, user_id: int = Query(gt=0)) -> None:
        with get_connection(path) as connection:
            service = AccountingService(SqliteTransactionRepository(connection))
            try:
                service.delete_transaction(transaction_id, user_id=user_id)
            except ValueError as exc:
                raise HTTPException(status_code=404, detail=str(exc)) from exc

    return app


app = create_app()
