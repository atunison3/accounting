"""Model Context Protocol server for the accounting SQLite database."""

from __future__ import annotations

from datetime import date
from typing import Any

from mcp.server.fastmcp import FastMCP

from accounting.infrastructure.sqlite.connection import DEFAULT_DATABASE_PATH, get_connection
from accounting.infrastructure.sqlite.repositories import SqliteTransactionRepository


mcp = FastMCP("accounting")


@mcp.tool()
def get_transactions_by_business_and_date_range(
    business_id: int,
    start_date: str,
    end_date: str,
) -> list[dict[str, Any]]:
    """Get all transaction lines for a business between two inclusive ISO dates.

    Dates must use YYYY-MM-DD format. Results are grouped by transaction and
    include account numbers, currency, and integer-cent amounts.
    """
    try:
        beginning = date.fromisoformat(start_date)
        ending = date.fromisoformat(end_date)
    except ValueError as exc:
        raise ValueError("Dates must use YYYY-MM-DD format.") from exc
    if beginning > ending:
        raise ValueError("start_date must be on or before end_date.")

    with get_connection(DEFAULT_DATABASE_PATH) as connection:
        entries = SqliteTransactionRepository(connection).search(
            business_id=business_id,
            date_from=beginning,
            date_to=ending,
        )

    grouped: dict[int, dict[str, Any]] = {}
    for entry in entries:
        transaction = grouped.setdefault(
            entry.transaction_id,
            {
                "transaction_id": entry.transaction_id,
                "transaction_date": entry.transaction_date.isoformat(),
                "description": entry.description,
                "currency_code": entry.currency_code,
                "posting_reference": entry.posting_reference,
                "lines": [],
            },
        )
        transaction["lines"].append(
            {
                "account_number": entry.account_number,
                "account_name": entry.account_name,
                "amount_cents": entry.amount_cents,
                "is_debit": entry.is_debit,
            }
        )
    return list(grouped.values())


if __name__ == "__main__":
    mcp.run()
