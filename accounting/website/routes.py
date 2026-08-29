from datetime import date
import re
from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from accounting.application.services import AccountingService
from accounting.domain.models import Account, AccountType, Business, TransactionLine, User
from accounting.infrastructure.sqlite.connection import DEFAULT_DATABASE_PATH, get_connection
from accounting.infrastructure.sqlite.repositories import (
    SqliteAccountRepository,
    SqliteBusinessRepository,
    SqliteTransactionRepository,
    SqliteUserRepository,
)

PACKAGE_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = PACKAGE_DIR / "templates"

router = APIRouter()
templates = Jinja2Templates(directory=TEMPLATE_DIR)


def _database_path(request: Request) -> str | Path:
    return getattr(request.app.state, "db_path", DEFAULT_DATABASE_PATH)


def _dashboard(request: Request, error: str | None = None) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "page_title": "Dashboard",
            "message": request.query_params.get("message"),
            "error": error,
        },
    )


@router.get("/", response_class=HTMLResponse, name="home")
def home(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={"page_title": "Home"},
    )


@router.get("/signup", response_class=HTMLResponse, name="signup")
def signup(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="signup.html",
        context={"page_title": "Create user", "error": None},
    )


@router.post("/users/create", response_class=HTMLResponse, response_model=None, name="create_user_form")
def create_user_form(
    request: Request,
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
) -> HTMLResponse | RedirectResponse:
    try:
        base_username = re.sub(r"[^a-z0-9]+", ".", f"{first_name}.{last_name}".lower()).strip(".")
        username = base_username or "user"
        with get_connection(_database_path(request)) as connection:
            repository = SqliteUserRepository(connection)
            suffix = 1
            while repository.get_by_username(username) is not None:
                suffix += 1
                username = f"{base_username or 'user'}.{suffix}"
            repository.add(User(username=username, first_name=first_name, last_name=last_name, email=email))
    except Exception as exc:
        return templates.TemplateResponse(
            request=request,
            name="signup.html",
            context={"page_title": "Create user", "error": f"Could not create user: {exc}"},
            status_code=400,
        )
    return RedirectResponse(url="/dashboard?message=User%20created", status_code=303)


@router.get("/about", response_class=HTMLResponse, name="about")
def about(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="about.html",
        context={"page_title": "About"},
    )


@router.get("/dashboard", response_class=HTMLResponse, name="dashboard")
def dashboard(request: Request) -> HTMLResponse:
    return _dashboard(request)


@router.post("/businesses/create", response_class=HTMLResponse, response_model=None, name="create_business_form")
def create_business_form(
    request: Request,
    title: str = Form(...),
    created_by: int = Form(...),
    tax_id: str | None = Form(None),
) -> HTMLResponse | RedirectResponse:
    try:
        business = Business(title=title, tax_id=tax_id or None, created_by=created_by)
        with get_connection(_database_path(request)) as connection:
            SqliteBusinessRepository(connection).add(business)
    except Exception as exc:  # database constraints are rendered as form errors
        return _dashboard(request, f"Could not add business: {exc}")
    return RedirectResponse(url="/dashboard?message=Business%20added", status_code=303)


@router.post("/accounts/create", response_class=HTMLResponse, response_model=None, name="create_account_form")
def create_account_form(  # noqa: PLR0913, PLR0917
    request: Request,
    business_id: int = Form(...),
    account_number: int = Form(...),
    account_name: str = Form(...),
    account_type: AccountType = Form(...),  # noqa: B008
    created_by: int = Form(...),
    is_debit: bool = Form(False),
) -> HTMLResponse | RedirectResponse:
    try:
        account = Account(
            business_id=business_id,
            account_number=account_number,
            account_name=account_name,
            account_type=account_type,
            created_by=created_by,
            is_debit=is_debit,
        )
        with get_connection(_database_path(request)) as connection:
            SqliteAccountRepository(connection).add(account)
    except Exception as exc:
        return _dashboard(request, f"Could not add account: {exc}")
    return RedirectResponse(url="/dashboard?message=Account%20added", status_code=303)


@router.post("/transactions/create", response_class=HTMLResponse, response_model=None, name="create_transaction_form")
def create_transaction_form(  # noqa: PLR0913, PLR0917
    request: Request,
    transaction_date: str = Form(...),
    description: str = Form(...),
    debit_account_id: int = Form(...),
    credit_account_id: int = Form(...),
    amount_cents: int = Form(...),
    user_id: int = Form(...),
    posting_reference: str | None = Form(None),
) -> HTMLResponse | RedirectResponse:
    try:
        lines = [
            TransactionLine(transaction_id=0, account_id=debit_account_id, amount_cents=amount_cents, is_debit=True),
            TransactionLine(transaction_id=0, account_id=credit_account_id, amount_cents=amount_cents, is_debit=False),
        ]
        with get_connection(_database_path(request)) as connection:
            AccountingService(SqliteTransactionRepository(connection)).create_transaction(
                transaction_date=date.fromisoformat(transaction_date),
                description=description,
                posting_reference=posting_reference or None,
                lines=lines,
                user_id=user_id,
            )
    except Exception as exc:
        return _dashboard(request, f"Could not add transaction: {exc}")
    return RedirectResponse(url="/dashboard?message=Transaction%20posted", status_code=303)
