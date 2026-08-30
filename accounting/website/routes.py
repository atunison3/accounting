from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
import hashlib
import logging
import re
import uuid
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from accounting.application.services import AccountService, AccountingService, AnalyticsService, MileageService
from accounting.domain.models import (
    Account,
    AccountType,
    AccountingTransactionDocument,
    Business,
    Document,
    Mileage,
    TransactionLine,
    User,
)
from accounting.infrastructure.sqlite.connection import DEFAULT_DATABASE_PATH, get_connection
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Spacer, Table, TableStyle, Paragraph

from accounting.infrastructure.sqlite.repositories import (
    SqliteAccountRepository,
    SqliteBusinessRepository,
    SqliteDocumentRepository,
    SqliteMileageRepository,
    SqliteTransactionDocumentRepository,
    SqliteTransactionRepository,
    SqliteUserRepository,
)

PACKAGE_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = PACKAGE_DIR / "templates"

router = APIRouter()
templates = Jinja2Templates(directory=TEMPLATE_DIR)
LOGGER = logging.getLogger("accounting.api.website.routes")
DOCUMENTS_DIRECTORY = Path.home() / ".app_data" / "accounting" / "documents"


def _database_path(request: Request) -> str | Path:
    return getattr(request.app.state, "db_path", DEFAULT_DATABASE_PATH)


def _optional_int(value: str | None) -> int | None:
    return int(value) if value and value.strip() else None


def _optional_decimal(value: str | None) -> Decimal | None:
    return Decimal(value) if value and value.strip() else None


def _optional_date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value and value.strip() else None


def _optional_bool(value: str | None) -> bool | None:
    if not value or not value.strip():
        return None
    if value.lower() in {"true", "yes", "1"}:
        return True
    if value.lower() in {"false", "no", "0"}:
        return False
    raise ValueError("Document filter must be true or false.")


def _miles_to_tenths(value: Decimal) -> int:
    exponent = value.as_tuple().exponent
    if not value.is_finite() or value < 0 or not isinstance(exponent, int) or exponent < -1:
        raise ValueError("Mileage must be a non-negative value with at most one decimal place.")
    return int(value * 10)


def _dollars_to_cents(value: Decimal) -> int:
    """Convert a dollar amount with at most two decimals to integer cents."""
    exponent = value.as_tuple().exponent
    if not value.is_finite() or value < 0 or not isinstance(exponent, int) or exponent < -2:
        raise ValueError("Amount must be a non-negative dollar value with at most two decimal places.")
    try:
        return int(value * 100)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("Amount must be a valid dollar value.") from exc


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


@router.post("/mileage/create", response_class=HTMLResponse, response_model=None, name="create_mileage_form")
def create_mileage_form(  # noqa: PLR0913, PLR0917
    request: Request,
    business_id: int = Form(...),
    mileage_date: date = Form(...),  # noqa: B008
    miles: Decimal = Form(...),  # noqa: B008
    explanation: str = Form(...),
    created_by: int = Form(...),
    start_miles: Decimal | None = Form(None),  # noqa: B008
    end_miles: Decimal | None = Form(None),  # noqa: B008
    vehicle: str | None = Form(None),
) -> HTMLResponse | RedirectResponse:
    try:
        start_tenths = _miles_to_tenths(start_miles) if start_miles is not None else None
        end_tenths = _miles_to_tenths(end_miles) if end_miles is not None else None
        mileage = Mileage(
            business_id=business_id,
            mileage_date=mileage_date,
            tenth_miles=_miles_to_tenths(miles),
            start_tenth_miles=start_tenths,
            end_tenth_miles=end_tenths,
            explanation=explanation,
            vehicle=vehicle or None,
            created_by=created_by,
        )
        with get_connection(_database_path(request)) as connection:
            MileageService(SqliteMileageRepository(connection)).record(mileage)
    except Exception as exc:
        LOGGER.exception("Mileage creation failed")
        return _dashboard(request, f"Could not log mileage: {exc}")
    return RedirectResponse(url="/dashboard?message=Mileage%20logged", status_code=303)


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


@router.get("/documents/upload", response_class=HTMLResponse, name="upload_document")
def upload_document(
    request: Request,
    business_id: int | None = None,
    transaction_id: int | None = None,
) -> HTMLResponse:
    with get_connection(_database_path(request)) as connection:
        businesses = SqliteBusinessRepository(connection).get_all()
    return templates.TemplateResponse(
        request=request,
        name="upload_document.html",
        context={
            "page_title": "Upload document",
            "businesses": businesses,
            "selected_business_id": business_id,
            "selected_transaction_id": transaction_id,
            "error": None,
        },
    )


@router.post("/documents/upload", response_class=HTMLResponse, response_model=None, name="upload_document_form")
def upload_document_form(  # noqa: PLR0913, PLR0917
    request: Request,
    document_file: UploadFile = File(...),  # noqa: B008
    business_id: int = Form(...),
    transaction_id: int = Form(...),
    document_type: str = Form(...),
    document_date: date = Form(...),  # noqa: B008
    created_by: int = Form(...),
    title: str | None = Form(None),
    description: str | None = Form(None),
) -> HTMLResponse | RedirectResponse:
    stored_path: Path | None = None
    try:
        if not document_file.filename:
            raise ValueError("A document file is required.")
        with get_connection(_database_path(request)) as connection:
            business = SqliteBusinessRepository(connection).get_by_id(business_id)
            transaction = SqliteTransactionRepository(connection).get_by_id(transaction_id)
            if business is None:
                raise ValueError("Business not found.")
            if transaction is None or transaction.business_id != business_id:
                raise ValueError("Transaction not found for this business.")

            content = document_file.file.read()
            extension = Path(document_file.filename).suffix.lower()
            extension = re.sub(r"[^a-z0-9.]", "", extension)
            stored_name = hashlib.sha256(uuid.uuid4().bytes + content).hexdigest() + extension
            directory = DOCUMENTS_DIRECTORY / str(business_id)
            directory.mkdir(parents=True, exist_ok=True)
            stored_path = directory / stored_name
            stored_path.write_bytes(content)
            document = Document(
                document_type=document_type,
                document_date=document_date,
                title=title or None,
                description=description or None,
                filename=document_file.filename,
                file_path=str(stored_path),
                mime_type=document_file.content_type,
                file_size_bytes=len(content),
                sha256_hash=hashlib.sha256(content).hexdigest(),
                created_by=created_by,
            )
            document_id = SqliteDocumentRepository(connection).add(document)
            SqliteTransactionDocumentRepository(connection).add(
                AccountingTransactionDocument(
                    transaction_id=transaction_id,
                    document_id=document_id,
                    created_by=created_by,
                )
            )
    except Exception as exc:
        if stored_path is not None:
            stored_path.unlink(missing_ok=True)
        LOGGER.exception("Document upload failed business_id=%s transaction_id=%s", business_id, transaction_id)
        with get_connection(_database_path(request)) as connection:
            businesses = SqliteBusinessRepository(connection).get_all()
        return templates.TemplateResponse(
            request=request,
            name="upload_document.html",
            context={
                "page_title": "Upload document",
                "businesses": businesses,
                "selected_business_id": business_id,
                "selected_transaction_id": transaction_id,
                "error": str(exc),
            },
            status_code=400,
        )
    return RedirectResponse(url="/dashboard?message=Document%20uploaded%20and%20linked", status_code=303)


@router.get("/analytics", response_class=HTMLResponse, name="analytics_dashboard")
def analytics_dashboard(request: Request, business_id: int | None = None) -> HTMLResponse:
    """Render the business analytics dashboard shell."""
    with get_connection(_database_path(request)) as connection:
        businesses = SqliteBusinessRepository(connection).get_all()
    return templates.TemplateResponse(
        request=request,
        name="analytics.html",
        context={
            "page_title": "Business analytics",
            "businesses": businesses,
            "selected_business_id": business_id,
        },
    )


@router.get("/api/analytics/equity", name="api_equity_analytics")
def api_equity_analytics(request: Request, business_id: int) -> JSONResponse:
    """Return cumulative owner equity in USD cents for one business."""
    with get_connection(_database_path(request)) as connection:
        points = AnalyticsService(
            SqliteTransactionRepository(connection),
            SqliteAccountRepository(connection),
        ).owner_equity_over_time(business_id)
    return JSONResponse(points)


@router.get("/api/analytics/overview", name="api_analytics_overview")
def api_analytics_overview(request: Request, business_id: int) -> JSONResponse:
    """Return the chart series used by the business analytics dashboard."""
    with get_connection(_database_path(request)) as connection:
        analytics = AnalyticsService(
            SqliteTransactionRepository(connection),
            SqliteAccountRepository(connection),
        )
        data = {
            "equity": analytics.owner_equity_over_time(business_id),
            "revenue_expenses": analytics.revenue_and_expenses_over_time(business_id),
            "cash": analytics.cash_balance_over_time(business_id),
            "document_coverage": analytics.documentless_transaction_percentage(business_id),
        }
    return JSONResponse(data)


@router.get("/transactions", response_class=HTMLResponse, name="transactions_dashboard")
def transactions_dashboard(  # noqa: PLR0913, PLR0917
    request: Request,
    business_id: int | None = None,
    account_number: str | None = None,
    entry_type: str | None = None,
    amount_min: str | None = None,
    amount_max: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    currency_code: str | None = None,
    has_document: str | None = None,
    days: int = 30,
) -> HTMLResponse:
    LOGGER.debug("Rendering transactions dashboard business_id=%s", business_id)
    businesses = []
    accounts = []
    transactions = []
    error = None
    try:
        selected_account = _optional_int(account_number)
        selected_amount_min = _optional_decimal(amount_min)
        selected_amount_max = _optional_decimal(amount_max)
        selected_currency = currency_code.strip().upper() if currency_code and currency_code.strip() else None
        selected_has_document = _optional_bool(has_document)
        selected_date_from = _optional_date(date_from)
        selected_date_to = _optional_date(date_to)
        if days < 1:
            raise ValueError("Days must be at least 1.")
        if selected_date_from is None:
            selected_date_from = date.today() - timedelta(days=days - 1)
        if selected_date_to is None:
            selected_date_to = date.today()
        is_debit = None if not entry_type else entry_type == "debit"
        if entry_type not in {None, "", "debit", "credit"}:
            raise ValueError("Entry type must be debit or credit.")
        with get_connection(_database_path(request)) as connection:
            businesses = SqliteBusinessRepository(connection).get_all()
            if business_id is not None:
                accounts = SqliteAccountRepository(connection).get_for_business(business_id)
                transactions = AccountingService(SqliteTransactionRepository(connection)).list_transactions(
                    business_id=business_id,
                    account_number=selected_account,
                    is_debit=is_debit,
                    min_amount_cents=(
                        _dollars_to_cents(selected_amount_min) if selected_amount_min is not None else None
                    ),
                    max_amount_cents=(
                        _dollars_to_cents(selected_amount_max) if selected_amount_max is not None else None
                    ),
                    date_from=selected_date_from,
                    date_to=selected_date_to,
                    currency_code=selected_currency,
                    has_document=selected_has_document,
                )
    except Exception as exc:
        LOGGER.exception("Transaction dashboard query failed")
        error = str(exc)
    return templates.TemplateResponse(
        request=request,
        name="transactions.html",
        context={
            "page_title": "Transactions",
            "businesses": businesses,
            "accounts": accounts,
            "transactions": transactions,
            "filters": request.query_params,
            "days": days,
            "error": error,
        },
    )


@router.get("/api/accounts", name="api_accounts")
def api_accounts(request: Request, business_id: int) -> JSONResponse:
    LOGGER.debug("Querying account options business_id=%s", business_id)
    with get_connection(_database_path(request)) as connection:
        accounts = SqliteAccountRepository(connection).get_for_business(business_id)
    return JSONResponse(
        [
            {"id": account.id, "account_number": account.account_number, "name": account.account_name}
            for account in accounts
        ]
    )


@router.get("/api/transactions", name="api_transactions")
def api_transactions(  # noqa: PLR0913, PLR0917
    request: Request,
    business_id: int,
    account_number: str | None = None,
    entry_type: str | None = None,
    amount_min: str | None = None,
    amount_max: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    currency_code: str | None = None,
    has_document: bool | None = None,
    days: int = 30,
) -> JSONResponse:
    """Return filtered transaction lines for Tabulator's remote data source."""
    selected_date_from = _optional_date(date_from) or date.today() - timedelta(days=days - 1)
    selected_date_to = _optional_date(date_to) or date.today()
    is_debit = None if not entry_type else entry_type == "debit"
    if entry_type not in {None, "", "debit", "credit"} or days < 1:
        raise HTTPException(status_code=422, detail="Invalid transaction filters")
    min_amount = _optional_decimal(amount_min)
    max_amount = _optional_decimal(amount_max)
    with get_connection(_database_path(request)) as connection:
        results = AccountingService(SqliteTransactionRepository(connection)).list_transactions(
            business_id=business_id,
            account_number=_optional_int(account_number),
            is_debit=is_debit,
            min_amount_cents=_dollars_to_cents(min_amount) if min_amount is not None else None,
            max_amount_cents=_dollars_to_cents(max_amount) if max_amount is not None else None,
            date_from=selected_date_from,
            date_to=selected_date_to,
            currency_code=currency_code.upper() if currency_code else None,
            has_document=has_document,
        )
    return JSONResponse([result.model_dump(mode="json") for result in results])


@router.get("/transactions/{transaction_id}/edit", response_class=HTMLResponse, name="edit_transaction")
def edit_transaction(request: Request, transaction_id: int, return_to: str | None = None) -> HTMLResponse:
    with get_connection(_database_path(request)) as connection:
        repository = SqliteTransactionRepository(connection)
        transaction = repository.get_by_id(transaction_id)
        lines = repository.get_lines(transaction_id)
        accounts = SqliteAccountRepository(connection)
        line_data = [(line, accounts.get_by_id(line.account_id)) for line in lines]
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return templates.TemplateResponse(
        request=request,
        name="edit_transaction.html",
        context={
            "page_title": "Edit transaction",
            "transaction": transaction,
            "line_data": line_data,
            "return_to": return_to or "/transactions",
            "error": None,
        },
    )


@router.post(
    "/transactions/{transaction_id}/edit",
    response_class=HTMLResponse,
    response_model=None,
    name="update_transaction_form",
)
def update_transaction_form(  # noqa: PLR0913, PLR0917
    request: Request,
    transaction_id: int,
    business_id: int = Form(...),
    transaction_date: date = Form(...),  # noqa: B008
    currency_code: str = Form("USD"),  # noqa: B008
    description: str = Form(...),
    account_numbers: list[int] = Form(...),  # noqa: B008
    amounts: list[Decimal] = Form(...),  # noqa: B008
    line_types: list[str] = Form(...),  # noqa: B008
    user_id: int = Form(...),
    posting_reference: str | None = Form(None),
    return_to: str | None = Form(None),
) -> HTMLResponse | RedirectResponse:
    try:
        if not (len(account_numbers) == len(amounts) == len(line_types)):
            raise ValueError("Each transaction line needs an account, amount, and type.")
        with get_connection(_database_path(request)) as connection:
            account_repository = SqliteAccountRepository(connection)
            account_ids = []
            for account_number in account_numbers:
                account = account_repository.get_by_number(business_id, account_number)
                if account is None or account.id is None:
                    raise ValueError(f"Account number {account_number} was not found for this business.")
                account_ids.append(account.id)
        lines = [
            TransactionLine(
                transaction_id=transaction_id,
                account_id=account_id,
                amount_cents=_dollars_to_cents(amount),
                is_debit=line_type == "debit",
            )
            for account_id, amount, line_type in zip(account_ids, amounts, line_types, strict=True)
        ]
        with get_connection(_database_path(request)) as connection:
            AccountingService(SqliteTransactionRepository(connection)).update_transaction(
                transaction_id,
                transaction_date,
                description,
                lines,
                user_id,
                posting_reference,
                business_id,
                currency_code,
            )
    except Exception as exc:
        LOGGER.exception("Transaction update failed transaction_id=%s", transaction_id)
        return _dashboard(request, f"Could not update transaction: {exc}")
    destination = (
        return_to
        if return_to and return_to.startswith("/") and not return_to.startswith("//")
        else f"/transactions?business_id={business_id}"
    )
    return RedirectResponse(url=destination, status_code=303)


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
    currency_code: str = Form("USD"),  # noqa: B008
    description: str = Form(...),
    account_numbers: list[int] = Form(...),  # noqa: B008
    amounts: list[Decimal] = Form(...),  # noqa: B008
    line_types: list[str] = Form(...),  # noqa: B008
    user_id: int = Form(...),
    posting_reference: str | None = Form(None),
) -> HTMLResponse | RedirectResponse:
    LOGGER.debug("Creating transaction line_count=%s", len(account_numbers))
    try:
        if not (len(account_numbers) == len(amounts) == len(line_types)):
            raise ValueError("Each transaction line needs an account, amount, and type.")
        amounts_cents = [_dollars_to_cents(amount) for amount in amounts]
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
                business_id=business_id,
                transaction_date=date.fromisoformat(transaction_date),
                currency_code=currency_code,
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
