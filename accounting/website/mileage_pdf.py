"""Print-friendly mileage reports without document metadata."""

from datetime import date
from decimal import Decimal
from html import escape
from io import BytesIO
from typing import cast

from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def miles(value: object) -> str:
    """Format stored tenths, preserving missing odometer readings as a dash."""
    if value is None:
        return "—"
    return f"{Decimal(cast(int, value)) / 10:,.1f}"


def mileage_pdf(
    business_name: str,
    rows: list[dict[str, object]],
    date_from: date | None,
    date_to: date | None,
    vehicle: str | None,
) -> bytes:
    buffer = BytesIO()
    report = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        leftMargin=30,
        rightMargin=30,
        topMargin=30,
        bottomMargin=36,
        title="Mileage Log",
        author=business_name,
    )
    styles = getSampleStyleSheet()
    cell_style = ParagraphStyle("MileageCell", parent=styles["Normal"], fontSize=8, leading=11)
    header_style = ParagraphStyle("MileageHeader", parent=cell_style, fontName="Helvetica-Bold")

    def text(value: object) -> Paragraph:
        return Paragraph(escape(str(value)).replace("\n", "<br/>") if value else "—", cell_style)

    story = [
        Paragraph(escape(business_name), styles["Title"]),
        Paragraph("Mileage Log", styles["Title"]),
        Paragraph(
            f"Date range: {date_from or 'Beginning of records'} through {date_to or 'Latest record'}", styles["Normal"]
        ),
        Paragraph(f"Vehicle: {escape(vehicle) if vehicle else 'All vehicles'} · Distances in miles", styles["Normal"]),
        Spacer(1, 14),
    ]
    headings = [
        "Date",
        "Miles",
        "Vehicle",
        "Starting location",
        "Destination(s), in order",
        "Odometer start",
        "Odometer stop",
        "Business justification",
    ]
    cells: list[list[object]] = [[Paragraph(label, header_style) for label in headings]]
    # Match the mileage dashboard's query order.
    for row in rows:
        cells.append(
            [
                text(row["miles_date"]),
                miles(row["tenth_miles"]),
                text(row["vehicle"]),
                text(row["starting_location"]),
                text(row["destination_location"]),
                miles(row["tenth_miles_begin"]),
                miles(row["tenth_miles_end"]),
                text(row["business_purpose"]),
            ]
        )
    if rows:
        table = Table(cells, colWidths=[60, 44, 64, 100, 120, 62, 62, 120], repeatRows=1, splitInRow=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e6f3f0")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ALIGN", (1, 1), (1, -1), "RIGHT"),
                    ("ALIGN", (5, 1), (6, -1), "RIGHT"),
                    ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#dce4e8")),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ]
            )
        )
        story.append(table)
    else:
        story.append(Paragraph("No mileage logs match the selected filters.", styles["Normal"]))
    total = sum(cast(int, row["tenth_miles"]) for row in rows)
    story.extend([Spacer(1, 12), Paragraph(f"{len(rows)} trips · Total miles: {miles(total)}", styles["Heading3"])])
    report.build(story)
    return buffer.getvalue()
