from itertools import zip_longest

from accounting.domain.domain import TAccountDisplay
from accounting.domain.domain import BalanceColumnDisplay, BalanceColumnItem


def print_t_account(
    t_account: TAccountDisplay,
    terminal_length: int = 40,
) -> None:
    """Print a formatted T-account.

    Debit and credit values are provided as integer cents.
    """
    if terminal_length < 20:
        raise ValueError("terminal_length must be at least 20")

    left_width = terminal_length // 2
    right_width = terminal_length - left_width - 1
    margin = 2

    print()
    print(t_account.account_title.center(terminal_length))
    print("─" * left_width + "┬" + "─" * right_width)
    print("Dr.".center(left_width) + "│" + "Cr.".center(right_width))

    for debit, credit in zip_longest(
        t_account.debits,
        t_account.credits,
        fillvalue=None,
    ):
        debit_text = f"{debit / 100:,.2f}" if debit is not None else ""
        credit_text = f"{credit / 100:,.2f}" if credit is not None else ""

        debit_column = debit_text.rjust(left_width - margin)
        credit_column = credit_text.rjust(right_width - margin)

        print(debit_column + " " * margin + "│" + credit_column + " " * margin)

    # Print final space
    print("│".center(terminal_length + 1))
    print()


def format_money(amount_cents: int | None, width: int = 14) -> str:
    """Format cents as a right-aligned monetary value."""
    if amount_cents is None:
        return " " * width

    amount = amount_cents / 100
    return f"{amount:,.2f}".rjust(width - 2) + "  "


def print_balance_rows(
    items: list[BalanceColumnItem],
) -> None:
    """Print transaction rows for a balance-column account form."""

    previous_year: int | None = None
    previous_month: int | None = None

    for item in items:
        current_year = item.date.year
        current_month = item.date.month

        if current_year != previous_year:
            # Example: "26 Aug"
            year_month = item.date.strftime("%y %b")
        elif current_month != previous_month:
            # Same year, new month: "   Sep"
            year_month = item.date.strftime("   %b")
        else:
            year_month = ""

        day = str(item.date.day)

        explanation = item.explanation[:50]
        posting_reference = item.posting_reference or ""

        debit = format_money(item.debit)
        credit = format_money(item.credit)
        balance = format_money(item.balance)

        print(
            "│ "
            + year_month.ljust(5)
            + "│"
            + day.rjust(3)
            + " │"
            + explanation.ljust(50)
            + "│"
            + posting_reference.center(10)
            + "│"
            + debit
            + "│"
            + credit
            + "│"
            + balance
            + "│"
        )

        previous_year = current_year
        previous_month = current_month

    print(
        "└"
        + "─" * 6
        + "┴"
        + "─" * 4
        + "┴"
        + "─" * 50
        + "┴"
        + "─" * 10
        + "┴"
        + "─" * 14
        + "┴"
        + "─" * 14
        + "┴"
        + "─" * 14
        + "┘"
    )


def print_balance_column(
    balance_column: BalanceColumnDisplay, terminal_length: int = 120, number_field_width: int = 12
):
    """Prints a balance column"""

    account_number = str(balance_column.account_number)
    account_title = balance_column.account_title

    label = "Account No."
    right_section_width = len(label) + number_field_width

    # Center the title across the full terminal width
    title_start = max(0, (terminal_length - len(account_title)) // 2)

    # Right align the account-number section
    right_start = terminal_length - right_section_width

    spacing_before_title = " " * title_start
    spacing_between = " " * (right_start - title_start - len(account_title))

    underlined_number = "\033[4m" + account_number.center(number_field_width) + "\033[0m"

    # Print the header
    print()
    print(spacing_before_title + account_title + spacing_between + label + underlined_number)
    print("┌" + "─" * 11 + "┬" + "─" * 50 + "┬" + "─" * 10 + "┬" + "─" * 14 + "┬" + "─" * 14 + "┬" + "─" * 14 + "┐")

    # Print the column headers
    print(
        "│ "
        + "Date".ljust(10)
        + "│"
        + "Explanation".center(50)
        + "│   P.R.   │"
        + "Debit".center(14)
        + "│"
        + "Credit".center(14)
        + "│"
        + "Balance".center(14)
        + "│"
    )
    print(
        "├"
        + "─" * 6
        + "┬"
        + "─" * 4
        + "┼"
        + "─" * 50
        + "┼"
        + "─" * 10
        + "┼"
        + "─" * 14
        + "┼"
        + "─" * 14
        + "┼"
        + "─" * 14
        + "┤"
    )

    print_balance_rows(balance_column.transactions)
    print()


if __name__ == "__main__":
    from datetime import datetime

    t_account = TAccountDisplay(account_title="Cash", debits=[500000, 100000], credits=[50000, 40000, 30000])
    print_t_account(t_account)

    items = [
        BalanceColumnItem(
            date=datetime(1978, 10, 31),
            explanation="Owner's investment",
            posting_reference=None,
            debit=500000,
            credit=None,
            balance=50000,
        )
    ]
    balance_column = BalanceColumnDisplay(account_title="Cash", account_number=100, transactions=items)

    print_balance_column(balance_column)
