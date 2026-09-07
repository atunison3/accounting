"""Income statement periods and calculations independent of the website."""

from calendar import monthrange
from datetime import date, timedelta
from typing import Any

from accounting.domain.currency import convert_currency
from accounting.domain.models import AccountType


def statement_period(
    period: str = "last-quarter",
    year: int | None = None,
    start: date | None = None,
    end: date | None = None,
    today: date | None = None,
) -> tuple[date, date]:
    """Resolve inclusive calendar dates; last quarter means last completed quarter."""
    today = today or date.today()
    if period == "last-quarter":
        end = date(today.year, ((today.month - 1) // 3) * 3 + 1, 1) - timedelta(days=1)
        return date(end.year, ((end.month - 1) // 3) * 3 + 1, 1), end
    if period == "custom":
        if start is None or end is None or start > end:
            raise ValueError("Choose a valid start and end date, with start on or before end.")
        return start, end
    year = year or today.year
    if period in {f"q{quarter}" for quarter in range(1, 5)}:
        month = (int(period[1:]) - 1) * 3 + 1
        return date(year, month, 1), date(year, month + 2, monthrange(year, month + 2)[1])
    if period in {f"m{month}" for month in range(1, 13)}:
        month = int(period[1:])
        return date(year, month, 1), date(year, month, monthrange(year, month)[1])
    raise ValueError("Select a supported reporting period.")


def income_statement(transactions: Any, accounts: Any, business_id: int, start: date, end: date) -> dict[str, Any]:
    """Net credit revenue less net debit expenses, including reversals and zero balances."""
    if start > end:
        raise ValueError("Start date must be on or before end date.")
    selected = {
        account.account_number: account
        for account in accounts.get_for_business(business_id)
        if account.account_type in {AccountType.REVENUE, AccountType.EXPENSE}
    }
    balances = dict.fromkeys(selected, 0)
    for entry in transactions.search(business_id, date_from=start, date_to=end):
        account = selected.get(entry.account_number)
        if account is None:
            continue
        amount = convert_currency(entry.amount_cents, entry.currency_code)
        positive = entry.is_debit == (account.account_type == AccountType.EXPENSE)
        balances[entry.account_number] += amount if positive else -amount
    result: dict[str, Any] = {}
    for key, kind in (("revenue", AccountType.REVENUE), ("expenses", AccountType.EXPENSE)):
        result[key] = [
            {"number": number, "name": selected[number].account_name, "cents": balances[number]}
            for number in sorted(selected)
            if selected[number].account_type == kind
        ]
        result[f"{key}_total"] = sum(row["cents"] for row in result[key])
    result["net_income"] = result["revenue_total"] - result["expenses_total"]
    return result
