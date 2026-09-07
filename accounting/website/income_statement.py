"""HTML and PDF presentation of the same income statement."""

from calendar import month_name
from datetime import date
from decimal import Decimal
from io import BytesIO
from html import escape

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from accounting.application.income_statement import income_statement, statement_period
from accounting.infrastructure.sqlite.connection import get_connection
from accounting.infrastructure.sqlite.repositories import (
    SqliteAccountRepository,
    SqliteBusinessRepository,
    SqliteTransactionRepository,
)
from accounting.website.routes import _database_path, templates

router = APIRouter()


def accounting_money(cents: int) -> str:
    amount = f"${Decimal(abs(cents)) / 100:,.2f}"
    return f"({amount})" if cents < 0 else amount


templates.env.filters["accounting_money"] = accounting_money


@router.get("/income-statement", response_class=HTMLResponse, name="income_statement_page")
def income_statement_page(  # noqa: PLR0913, PLR0917
    request: Request,
    business_id: int | None = None,
    period: str = "last-quarter",
    year: int | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> HTMLResponse:
    error = None
    business = None
    statement = None
    start, end = statement_period()
    try:
        start, end = statement_period(period, year, start_date, end_date)
    except ValueError as exc:
        error = str(exc)
    with get_connection(_database_path(request)) as connection:
        businesses = SqliteBusinessRepository(connection).get_all()
        if business_id is not None:
            business = SqliteBusinessRepository(connection).get_by_id(business_id)
            if business is None:
                raise HTTPException(404, "Business not found")
            if error is None:
                try:
                    statement = income_statement(
                        SqliteTransactionRepository(connection),
                        SqliteAccountRepository(connection),
                        business_id,
                        start,
                        end,
                    )
                except ValueError as exc:
                    error = str(exc)
    return templates.TemplateResponse(
        request=request,
        name="income_statement.html",
        context={
            "page_title": "Income Statement",
            "businesses": businesses,
            "business": business,
            "statement": statement,
            "period": period,
            "year": year or end.year,
            "start_date": start,
            "end_date": end,
            "months": list(enumerate(month_name))[1:],
            "error": error,
        },
        status_code=400 if error else 200,
    )


@router.get("/income-statement/pdf", name="income_statement_pdf")
def income_statement_pdf(
    request: Request,
    business_id: int,
    start_date: date,
    end_date: date,
) -> StreamingResponse:
    with get_connection(_database_path(request)) as connection:
        business = SqliteBusinessRepository(connection).get_by_id(business_id)
        if business is None:
            raise HTTPException(404, "Business not found")
        try:
            statement = income_statement(
                SqliteTransactionRepository(connection),
                SqliteAccountRepository(connection),
                business_id,
                start_date,
                end_date,
            )
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
    buffer = BytesIO()
    pdf = SimpleDocTemplate(buffer, rightMargin=42, leftMargin=42)
    styles = getSampleStyleSheet()
    story = [
        Paragraph(escape(business.title), styles["Title"]),
        Paragraph("Income Statement", styles["Title"]),
        Paragraph(f"{start_date:%B %d, %Y} through {end_date:%B %d, %Y} · Amounts in USD", styles["Normal"]),
        Spacer(1, 18),
    ]
    rows: list[list[object]] = [["Account", "Amount (USD)"]]
    for key, title in (("revenue", "Revenue"), ("expenses", "Expenses")):
        rows.append([Paragraph(title, styles["Heading3"]), ""])
        for row in statement[key]:
            rows.append(
                [
                    Paragraph(escape(f"{row['number']} · {row['name']}"), styles["Normal"]),
                    accounting_money(row["cents"]),
                ]
            )
        rows.append([f"Total {title.lower()}", accounting_money(statement[f"{key}_total"])])
    rows.append(["Net Income (Loss)", accounting_money(statement["net_income"])])
    table = Table(rows, colWidths=[pdf.width - 115, 115], repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e6f3f0")),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 9),
                ("LINEABOVE", (0, -1), (-1, -1), 1, colors.black),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ]
        )
    )
    story.append(table)
    pdf.build(story)
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="income-statement-{business_id}-{start_date}-{end_date}.pdf"',
        },
    )
