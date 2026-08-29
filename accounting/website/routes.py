from datetime import date
import logging
import re
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from accounting.application.services import AccountService, AccountingService
from accounting.domain.models import Account, AccountType, Business, TransactionLine, User
from accounting.infrastructure.sqlite.connection import DEFAULT_DATABASE_PATH, get_connection
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Spacer, Table, TableStyle, Paragraph

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
LOGGER = logging.getLogger("accounting.api.website.routes")


def _database_path(request: Request) -> str | Path:
    return getattr(request.app.state, "db_path", DEFAULT_DATABASE_PATH)


def _dashboard(request: Request, error: str | None = None) -> HTMLResponse:
    LOGGER.debug("Rendering dashboard error=%s", bool(error))
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
    LOGGER.debug("Rendering home page")
    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={"page_title": "Home"},
    )


@router.get("/signup", response_class=HTMLResponse, name="signup")
def signup(request: Request) -> HTMLResponse:
    LOGGER.debug("Rendering user signup page")
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
    LOGGER.debug("Creating user from signup form email=%s", email)
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
        LOGGER.exception("User signup failed")
        return templates.TemplateResponse(
            request=request,
            name="signup.html",
            context={"page_title": "Create user", "error": f"Could not create user: {exc}"},
            status_code=400,
        )
    LOGGER.debug("User created username=%s", username)
    return RedirectResponse(url="/dashboard?message=User%20created", status_code=303)


@router.get("/about", response_class=HTMLResponse, name="about")
def about(request: Request) -> HTMLResponse:
    LOGGER.debug("Rendering about page")
    return templates.TemplateResponse(
        request=request,
        name="about.html",
        context={"page_title": "About"},
    )


@router.get("/dashboard", response_class=HTMLResponse, name="dashboard")
def dashboard(request: Request) -> HTMLResponse:
    LOGGER.debug("Rendering dashboard page")
    return _dashboard(request)


@router.get("/chart-of-accounts", response_class=HTMLResponse, name="chart_of_accounts")
def chart_of_accounts(request: Request, business_id: int | None = None) -> HTMLResponse:
    LOGGER.debug("Rendering chart of accounts business_id=%s", business_id)
    with get_connection(_database_path(request)) as connection:
        businesses = SqliteBusinessRepository(connection).get_all()
        business = SqliteBusinessRepository(connection).get_by_id(business_id) if business_id is not None else None
        accounts = SqliteAccountRepository(connection).get_for_business(business_id) if business_id is not None else []
    if business_id is not None and business is None:
        raise HTTPException(status_code=404, detail="Business not found")
    account_groups = [
        (account_type.value, [account for account in accounts if account.account_type == account_type])
        for account_type in AccountType
    ]
    return templates.TemplateResponse(
        request=request,
        name="chart_of_accounts.html",
        context={
            "page_title": "Chart of Accounts",
            "businesses": businesses,
            "selected_business": business,
            "accounts": accounts,
            "account_groups": account_groups,
            "selected_business_id": business_id,
        },
    )


@router.get("/chart-of-accounts/pdf", name="chart_of_accounts_pdf")
def chart_of_accounts_pdf(request: Request, business_id: int) -> StreamingResponse:
    LOGGER.debug("Generating chart of accounts PDF business_id=%s", business_id)
    with get_connection(_database_path(request)) as connection:
        business = SqliteBusinessRepository(connection).get_by_id(business_id)
        accounts = SqliteAccountRepository(connection).get_for_business(business_id)
    if business is None:
        raise HTTPException(status_code=404, detail="Business not found")

    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.55 * inch,
        leftMargin=0.55 * inch,
        topMargin=0.55 * inch,
        bottomMargin=0.55 * inch,
    )
    styles = getSampleStyleSheet()
    centered = styles["Title"].clone("centered_title")
    centered.alignment = 1
    subtitle = styles["Heading2"].clone("centered_subtitle")
    subtitle.alignment = 1
    story = [
        Paragraph(business.title, centered),
        Paragraph("Chart of Accounts", subtitle),
        Spacer(1, 0.2 * inch),
    ]
    rows = [["Account No.", "Name of Account"]]
    category_rows: list[int] = []
    for account_type in AccountType:
        grouped_accounts = [account for account in accounts if account.account_type == account_type]
        if grouped_accounts:
            category_rows.append(len(rows))
            rows.append([account_type.value, ""])
            rows.extend([[str(account.account_number), account.account_name] for account in grouped_accounts])
    table = Table(rows, colWidths=[1.25 * inch, 6.3 * inch], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#087f70")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#dce4e8")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f6f5")]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("PADDING", (0, 0), (-1, -1), 7),
                *[("SPAN", (0, row), (-1, row)) for row in category_rows],
                *[("BACKGROUND", (0, row), (-1, row), colors.HexColor("#e6f3f0")) for row in category_rows],
                *[("FONTNAME", (0, row), (-1, row), "Helvetica-Bold") for row in category_rows],
            ]
        )
    )
    story.append(table)
    document.build(story)
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="chart-of-accounts-{business_id}.pdf"'},
    )


@router.post("/businesses/create", response_class=HTMLResponse, response_model=None, name="create_business_form")
def create_business_form(
    request: Request,
    title: str = Form(...),
    created_by: int = Form(...),
    tax_id: str | None = Form(None),
) -> HTMLResponse | RedirectResponse:
    LOGGER.debug("Creating business from dashboard form")
    try:
        business = Business(title=title, tax_id=tax_id or None, created_by=created_by)
        with get_connection(_database_path(request)) as connection:
            SqliteBusinessRepository(connection).add(business)
    except Exception as exc:  # database constraints are rendered as form errors
        LOGGER.exception("Business creation failed")
        return _dashboard(request, f"Could not add business: {exc}")
    LOGGER.debug("Business created successfully")
    return RedirectResponse(url="/dashboard?message=Business%20added", status_code=303)


@router.get("/accounts/{account_id}/edit", response_class=HTMLResponse, name="edit_account")
def edit_account(request: Request, account_id: int) -> HTMLResponse:
    LOGGER.debug("Rendering account edit form account_id=%s", account_id)
    with get_connection(_database_path(request)) as connection:
        account = SqliteAccountRepository(connection).get_by_id(account_id)
    if account is None:
        return _dashboard(request, f"Account {account_id} was not found.")
    return templates.TemplateResponse(
        request=request,
        name="edit_account.html",
        context={"page_title": "Edit account", "account": account, "error": None},
    )


@router.post(
    "/accounts/{account_id}/edit", response_class=HTMLResponse, response_model=None, name="update_account_form"
)
def update_account_form(  # noqa: PLR0913, PLR0917
    request: Request,
    account_id: int,
    account_number: int = Form(...),
    account_name: str = Form(...),
    account_type: AccountType = Form(...),  # noqa: B008
    updated_by: int = Form(...),
    is_debit: bool = Form(False),
    is_account_active: bool = Form(False),
    description: str | None = Form(None),
) -> HTMLResponse | RedirectResponse:
    try:
        with get_connection(_database_path(request)) as connection:
            repository = SqliteAccountRepository(connection)
            account = repository.get_by_id(account_id)
            if account is None:
                return _dashboard(request, f"Account {account_id} was not found.")
            updated = account.model_copy(
                update={
                    "account_number": account_number,
                    "account_name": account_name,
                    "account_type": account_type,
                    "description": description or None,
                    "is_debit": is_debit,
                    "is_account_active": is_account_active,
                }
            )
            AccountService(repository).update(account_id, updated, updated_by)
    except Exception as exc:
        LOGGER.exception("Account update failed account_id=%s", account_id)
        return templates.TemplateResponse(
            request=request,
            name="edit_account.html",
            context={
                "page_title": "Edit account",
                "account": updated if "updated" in locals() else None,
                "error": str(exc),
            },
            status_code=400,
        )
    return RedirectResponse(url=f"/chart-of-accounts?business_id={account.business_id}", status_code=303)


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
    LOGGER.debug("Creating account business_id=%s account_number=%s", business_id, account_number)
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
        LOGGER.exception("Account creation failed")
        return _dashboard(request, f"Could not add account: {exc}")
    LOGGER.debug("Account created successfully")
    return RedirectResponse(url="/dashboard?message=Account%20added", status_code=303)


@router.get("/accounts/lookup", name="lookup_account")
def lookup_account(request: Request, business_id: int, account_number: int) -> JSONResponse:
    LOGGER.debug("Looking up account business_id=%s account_number=%s", business_id, account_number)
    with get_connection(_database_path(request)) as connection:
        account = SqliteAccountRepository(connection).get_by_number(business_id, account_number)
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found for this business")
    return JSONResponse({"id": account.id, "account_number": account.account_number, "name": account.account_name})


@router.post("/transactions/create", response_class=HTMLResponse, response_model=None, name="create_transaction_form")
def create_transaction_form(  # noqa: PLR0913, PLR0917
    request: Request,
    business_id: int = Form(...),
    transaction_date: str = Form(...),
    description: str = Form(...),
    account_numbers: list[int] = Form(...),  # noqa: B008
    amounts_cents: list[int] = Form(...),  # noqa: B008
    line_types: list[str] = Form(...),  # noqa: B008
    user_id: int = Form(...),
    posting_reference: str | None = Form(None),
) -> HTMLResponse | RedirectResponse:
    LOGGER.debug("Creating transaction line_count=%s", len(account_numbers))
    try:
        if not (len(account_numbers) == len(amounts_cents) == len(line_types)):
            raise ValueError("Each transaction line needs an account, amount, and type.")
        with get_connection(_database_path(request)) as connection:
            repository = SqliteAccountRepository(connection)
            account_ids = []
            for account_number in account_numbers:
                account = repository.get_by_number(business_id, account_number)
                if account is None or account.id is None:
                    raise ValueError(f"Account number {account_number} was not found for this business.")
                account_ids.append(account.id)
        lines = [
            TransactionLine(
                transaction_id=0,
                account_id=account_id,
                amount_cents=amount,
                is_debit=line_type == "debit",
            )
            for account_id, amount, line_type in zip(account_ids, amounts_cents, line_types, strict=True)
            if line_type in {"debit", "credit"}
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
        LOGGER.exception("Transaction creation failed")
        return _dashboard(request, f"Could not add transaction: {exc}")
    LOGGER.debug("Transaction posted successfully")
    return RedirectResponse(url="/dashboard?message=Transaction%20posted", status_code=303)
