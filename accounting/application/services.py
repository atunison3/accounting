from itertools import zip_longest

from accounting.domain.domain import TAccountDisplay


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


if __name__ == "__main__":

    t_account = TAccountDisplay(
        account_title="Cash", debits=[500000, 100000], credits=[50000, 40000, 30000]
    )

    print_t_account(t_account)
