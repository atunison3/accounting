"""Authenticated, streamable-HTTP MCP adapter for the server's existing ledger."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import sqlite3

import uvicorn
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import Annotated, Any

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations
from pydantic import BaseModel, ConfigDict, Field
from starlette.responses import JSONResponse

from accounting.application.services import AccountingService
from accounting.domain.models import TransactionLine
from accounting.infrastructure.sqlite.connection import DEFAULT_DATABASE_PATH
from accounting.infrastructure.sqlite.repositories import (
    SqliteAccountRepository,
    SqliteBusinessRepository,
    SqliteTransactionRepository,
    SqliteUserRepository,
)

PositiveId = Annotated[int, Field(gt=0)]
READ = ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False)
WRITE = ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=False, openWorldHint=False)


class LineInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    account_id: int = Field(gt=0, strict=True)
    amount_cents: int = Field(gt=0, strict=True)
    is_debit: bool = Field(strict=True)


class TransactionInput(BaseModel):
    """Complete replacement payload, not a partial patch. Amounts are integer cents."""

    model_config = ConfigDict(extra="forbid")
    business_id: int = Field(gt=0, strict=True)
    transaction_date: date
    description: str = Field(min_length=1, max_length=2000)
    currency_code: str = Field(default="USD", pattern=r"^[A-Z]{3}$")
    posting_reference: str | None = Field(default=None, max_length=255)
    lines: list[LineInput] = Field(min_length=2, max_length=200)


class Ledger:
    """One connection/transaction per call, sharing SQLite safely with the website.

    No implicit database creation or schema migration: deploy/migrate the website
    first. A configured audit user is used, never an agent-supplied user ID.
    """

    def __init__(self, database: Path, user_id: int):
        self.database = Path(database).resolve()
        self.user_id = user_id
        if user_id <= 0 or not self.database.is_file():
            raise ValueError("An existing database and a positive audit user ID are required")
        with self.connect() as connection:
            self.check_user(connection)

    @contextmanager
    def connect(self, write: bool = False):
        connection = sqlite3.connect(self.database.as_uri() + "?mode=rw", uri=True, timeout=15)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def check_user(self, connection):
        user = SqliteUserRepository(connection).get_by_id(self.user_id)
        if user is None or not user.is_active:
            raise ValueError("Configured MCP audit user does not exist or is inactive")

    @staticmethod
    def transaction(connection, transaction_id):
        repository = SqliteTransactionRepository(connection)
        header = repository.get_by_id(transaction_id)
        if header is None:
            raise ValueError("Transaction not found (or soft-deleted)")
        result = header.model_dump(mode="json")
        result["lines"] = [line.model_dump(mode="json") for line in repository.get_lines(transaction_id)]
        result["revision"] = hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()
        return result

    @staticmethod
    def validate_payload(connection, payload):
        business = SqliteBusinessRepository(connection).get_by_id(payload.business_id)
        if business is None or not business.is_business_active:
            raise ValueError("Business not found or inactive")
        if not payload.description.strip():
            raise ValueError("Description cannot be blank")
        accounts = SqliteAccountRepository(connection)
        for line in payload.lines:
            account = accounts.get_by_id(line.account_id)
            if account is None or not account.is_account_active or account.business_id != payload.business_id:
                raise ValueError(f"Account {line.account_id} must be active and belong to the transaction business")

    @staticmethod
    def check_revision(current, expected_revision):
        if current["revision"] != expected_revision:
            raise ValueError("Transaction changed. Read it again and review changes before retrying.")

    def create(self, payload: TransactionInput):
        with self.connect(write=True) as connection:
            self.check_user(connection)
            self.validate_payload(connection, payload)
            arguments = payload.model_dump(exclude={"lines"})
            lines = [TransactionLine(transaction_id=0, **line.model_dump()) for line in payload.lines]
            transaction_id = AccountingService(SqliteTransactionRepository(connection)).create_transaction(
                **arguments,
                lines=lines,
                user_id=self.user_id,
            )
            return self.transaction(connection, transaction_id)

    def update(self, transaction_id: int, payload: TransactionInput, expected_revision: str):
        with self.connect(write=True) as connection:
            self.check_user(connection)
            current = self.transaction(connection, transaction_id)
            self.check_revision(current, expected_revision)
            if current["business_id"] != payload.business_id:
                raise ValueError("Moving a transaction to another business is not allowed")
            self.validate_payload(connection, payload)
            arguments = payload.model_dump(exclude={"lines"})
            lines = [TransactionLine(transaction_id=transaction_id, **line.model_dump()) for line in payload.lines]
            AccountingService(SqliteTransactionRepository(connection)).update_transaction(
                transaction_id,
                **arguments,
                lines=lines,
                user_id=self.user_id,
            )
            return self.transaction(connection, transaction_id)

    def delete(self, transaction_id: int, expected_revision: str, confirm: bool):
        if not confirm:
            raise ValueError("Deletion requires explicit user approval and confirm=true")
        with self.connect(write=True) as connection:
            self.check_user(connection)
            self.check_revision(self.transaction(connection, transaction_id), expected_revision)
            AccountingService(SqliteTransactionRepository(connection)).delete_transaction(transaction_id, self.user_id)
        return {"transaction_id": transaction_id, "soft_deleted": True}

    def list_transactions(self, business_id, start_date, end_date, limit=50, offset=0):
        if start_date > end_date:
            raise ValueError("start_date must be on or before end_date")
        if not 1 <= limit <= 100 or offset < 0:
            raise ValueError("limit must be 1-100 and offset nonnegative")
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT id FROM accounting_transactions WHERE business_id = ? AND deleted_at IS NULL "
                "AND transaction_date BETWEEN ? AND ? ORDER BY transaction_date, id LIMIT ? OFFSET ?",
                (business_id, start_date.isoformat(), end_date.isoformat(), limit + 1, offset),
            ).fetchall()
            return {
                "transactions": [self.transaction(connection, row["id"]) for row in rows[:limit]],
                "next_offset": offset + limit if len(rows) > limit else None,
            }


def create_mcp(ledger: Ledger, allowed_hosts: list[str]) -> FastMCP:
    server = FastMCP(
        "accounting",
        instructions=(
            "Accounting ledger tools. Read business/account IDs before writing. Amounts are integer cents. "
            "Ask the user to approve writes/deletions. Updates replace all lines and require a fresh revision. "
            "Never blindly retry create_transaction after a timeout: check the ledger first to avoid duplicates."
        ),
        stateless_http=True,
        json_response=True,
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=allowed_hosts,
            allowed_origins=[],
        ),
    )

    @server.tool(annotations=READ)
    def list_businesses() -> list[dict[str, Any]]:
        """List non-deleted businesses and their IDs. This token has ledger-wide access."""
        with ledger.connect() as connection:
            return [business.model_dump(mode="json") for business in SqliteBusinessRepository(connection).get_all()]

    @server.tool(annotations=READ)
    def list_accounts(business_id: PositiveId) -> list[dict[str, Any]]:
        """List accounts for a business; use account IDs (not account numbers) in transaction lines."""
        with ledger.connect() as connection:
            return [
                account.model_dump(mode="json")
                for account in SqliteAccountRepository(connection).get_for_business(business_id)
            ]

    @server.tool(annotations=READ)
    def get_transaction(transaction_id: PositiveId) -> dict[str, Any]:
        """Read a transaction, its active lines, and its revision for safe updates/deletion."""
        with ledger.connect() as connection:
            return ledger.transaction(connection, transaction_id)

    @server.tool(annotations=READ)
    def get_transactions_by_business_and_date_range(
        business_id: PositiveId,
        start_date: date,
        end_date: date,
        limit: Annotated[int, Field(ge=1, le=100)] = 50,
        offset: Annotated[int, Field(ge=0)] = 0,
    ) -> dict[str, Any]:
        """List transactions in an inclusive ISO date range, paginated by transaction, with lines/revisions."""
        return ledger.list_transactions(business_id, start_date, end_date, limit, offset)

    @server.tool(annotations=WRITE)
    def create_transaction(payload: TransactionInput) -> dict[str, Any]:
        """Post a balanced transaction after user approval. Not idempotent: do not blindly retry after a timeout."""
        return ledger.create(payload)

    @server.tool(annotations=WRITE)
    def update_transaction(
        transaction_id: PositiveId,
        payload: TransactionInput,
        expected_revision: str,
    ) -> dict[str, Any]:
        """Replace header and ALL lines after approval. Get the revision from get_transaction; stale writes fail."""
        return ledger.update(transaction_id, payload, expected_revision)

    @server.tool(annotations=WRITE)
    def delete_transaction(
        transaction_id: PositiveId,
        expected_revision: str,
        confirm: bool = False,
    ) -> dict[str, Any]:
        """Soft-delete with user approval, current revision, and confirm=true. Preserves audit history."""
        return ledger.delete(transaction_id, expected_revision, confirm)

    return server


class BearerAuth:
    """Authenticate every HTTP method before passing requests to MCP (including GET/DELETE)."""

    def __init__(self, app, token: str):
        if len(token) < 32 or not token.isascii() or any(character.isspace() for character in token):
            raise ValueError("MCP token must contain at least 32 ASCII non-whitespace characters")
        self.app = app
        self.expected = ("Bearer " + token).encode()

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            headers = scope.get("headers", [])
            authorization = [value for key, value in headers if key.lower() == b"authorization"]
            if len(authorization) != 1 or not hmac.compare_digest(authorization[0], self.expected):
                response = JSONResponse(
                    {"error": "Unauthorized"}, status_code=401, headers={"WWW-Authenticate": "Bearer"}
                )
                await response(scope, receive, send)
                return
            # Browser-origin calls are not supported. Prevent cross-site invocation even with a token.
            if any(key.lower() == b"origin" for key, _ in headers):
                await JSONResponse({"error": "Browser origins are not allowed"}, status_code=403)(scope, receive, send)
                return
        await self.app(scope, receive, send)


def create_app(database: Path, user_id: int, token: str, allowed_hosts: list[str]):
    server = create_mcp(Ledger(database, user_id), allowed_hosts)
    return BearerAuth(server.streamable_http_app(), token)


def main():
    token_file = Path(os.environ["ACCOUNTING_MCP_TOKEN_FILE"]).expanduser()
    if token_file.stat().st_mode & 0o077:
        raise ValueError("Token file must not be accessible to group/others (chmod 600)")
    host = os.environ.get("ACCOUNTING_MCP_HOST", "127.0.0.1")
    port = int(os.environ.get("ACCOUNTING_MCP_PORT", "8003"))
    allowed_hosts = [f"{host}:{port}", f"127.0.0.1:{port}", f"localhost:{port}"]
    app = create_app(
        Path(os.environ.get("ACCOUNTING_DATABASE_PATH", str(DEFAULT_DATABASE_PATH))).expanduser(),
        int(os.environ["ACCOUNTING_MCP_USER_ID"]),
        token_file.read_text().strip(),
        allowed_hosts,
    )
    uvicorn.run(app, host=host, port=port, proxy_headers=False)


if __name__ == "__main__":
    main()
