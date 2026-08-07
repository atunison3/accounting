from accounting.domain.domain import BalanceColumnDisplay, BalanceColumnItem


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

        # Print a separate year row before the first item of each year.
        if current_year != previous_year:
            print(
                "│ "
                + str(current_year).ljust(5)
                + "│"
                + " " * 4
                + "│"
                + " " * 50
                + "│"
                + " " * 10
                + "│"
                + " " * 14
                + "│"
                + " " * 14
                + "│"
                + " " * 14
                + "│"
            )

            previous_month = None

        month = item.date.strftime("%b") if current_month != previous_month else ""

        day = str(item.date.day)
        posting_reference = item.posting_reference or ""

        debit = format_money(item.debit)
        credit = format_money(item.credit)
        balance = format_money(item.balance)

        print(
            "│ "
            + month.ljust(5)
            + "│"
            + day.rjust(3)
            + " │  "
            + item.explanation[:48].ljust(48)
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
        "╰"
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
        + "╯"
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
    print("╭" + "─" * 11 + "┬" + "─" * 50 + "┬" + "─" * 10 + "┬" + "─" * 14 + "┬" + "─" * 14 + "┬" + "─" * 14 + "╮")

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

    items = [
        BalanceColumnItem(
            date=datetime(2026, 8, 5),
            explanation="Owner investment",
            posting_reference=None,
            debit=5_000_00,
            credit=None,
            balance=5_000_00,
        ),
        BalanceColumnItem(
            date=datetime(2026, 8, 10),
            explanation="Purchased parts",
            posting_reference=None,
            debit=None,
            credit=500_00,
            balance=4500_00,
        ),
        BalanceColumnItem(
            date=datetime(2026, 9, 2),
            explanation="Revenue from services",
            posting_reference=None,
            debit=1_000_00,
            credit=None,
            balance=5_500_00,
        ),
        BalanceColumnItem(
            date=datetime(2027, 1, 3),
            explanation="Paid rent",
            posting_reference=None,
            debit=None,
            credit=400_00,
            balance=5_100_00,
        ),
        BalanceColumnItem(
            date=datetime(2027, 1, 4),
            explanation="Paid for advertising",
            posting_reference=None,
            debit=None,
            credit=300_00,
            balance=4_800_00,
        ),
    ]

    balance_column = BalanceColumnDisplay(account_title="Cash", account_number=100, transactions=items)

    print_balance_column(balance_column)
