__all__ = ["leading_digit", "Entry", "Account"]


def leading_digit(n: int) -> int:
    return int(str(abs(n))[0])


class Entry:
    def __init__(self, transaction_id: str, amount: float, type_: str):
        assert type_ in ("debit", "credit"), "type_ must be 'debit' or 'credit'"
        self.transaction_id = transaction_id
        self.amount = amount
        self.type_ = type_

    def __repr__(self):
        return f"<Entry {self.type_.capitalize()} {self.amount}>"


class Account:
    def __init__(self, name: str, type_: int):

        if not isinstance(type_, int):
            raise TypeError("Invalid account type_ instance")

        self.name = name
        self.entries = []
        self.type_ = type_

    def add_entry(self, new_entry: Entry):
        self.entries.append(new_entry)

    def print_account(self, width=30):
        """Print the T Account"""

        credits = [entry.value for entry in self.entries if entry.type_ == "credit"]
        debits = [entry.value for entry in self.entries if entry.type_ == "debit"]

        while len(debits) < len(credits):
            debits.append(float("nan"))
        while len(credits) < len(debits):
            credits.append(float("nan"))

        # Find the widest entry for nice formatting
        max_debit_width = max([len(str(d)) for d in debits] + [5])
        max_credit_width = max([len(str(c)) for c in credits] + [5])

        # Determine the number of rows (max of debits and credits)
        rows = max(len(debits), len(credits))

        # Header
        print(f"{self.account_name:^width}")
        print("-" * width)
        print(f"{'Debits':<{max_debit_width}} | {'Credits':>{max_credit_width}}")
        print("-" * width)

        # Rows
        for i in range(rows):
            debit = f"{debits[i]:>{max_debit_width}}" if i < len(debits) else " " * max_debit_width
            credit = f"{credits[i]:>{max_credit_width}}" if i < len(credits) else " " * max_credit_width
            print(f"{debit} | {credit}")

        # Totals
        total_debits = sum(debits)
        total_credits = sum(credits)
        print("-" * width)
        print(f"{total_debits:>{max_debit_width}} | {total_credits:>{max_credit_width}}")
        print("-" * width)


class ChartOfAccounts:
    def __init__(self):
        self.accounts = {}

    def add_account(self, account_number: int, account_name: str):

        if len(account_name) > 32:
            raise ValueError("Invalid account name")
        if account_number in self.accounts.keys():
            raise ValueError("Invalid account number")
        if account_name in self.accounts.keys():
            raise ValueError("Invalid account name")

        self.accounts[account_number] = Account(account_name, leading_digit(account_number))

    def print_chart(self):
        """Prints the charts"""
        pass


# def print_charts(assets, liabilities, equities, revenues, expenses):

#     def print_title(title: str):
#         n = int((80 - len(title)) // 2)
#         print("-" * 80)
#         print(" " * n + title + " " * (n))
#         print("-" * 80)

#     def print_two_columns(t1: list, t2: list):
#         x = t1.pop(0)
#         y = t2.pop(0)

#         m = 40 - len(x[1])
#         print(f"""  {x[0]} {x[1]}{' ' * m}{y[0]} {y[1]}""")

#         return t1, t2

#     def print_right_column(t2: list):
#         y = t2.pop(0)

#         print(f"""{' ' * 46}{y[0]} {y[1]}""")
#         return t2

#     print_title("Balance Sheet Accounts")

#     print("  Assets" + " " * 38 + "Liabilities")
#     while (assets) and (liabilities):
#         assets, liabilities = print_two_columns(assets, liabilities)

#     if assets:
#         assets, _ = print_two_columns(assets, [("""Owner's Equity""", "")])
#         while assets and equities:
#             print_two_columns(assets, equities)
#         if assets:
#             while assets:
#                 a = assets.pop(0)
#                 print(f"  {a[0]} {a[1]}")
#         elif equities:
#             while equities:
#                 equities = print_right_column(equities)
#     elif liabilities:
#         while liabilities:
#             liabilities = print_right_column(liabilities)
#         print(" " * 46 + """Owner's Equity""")
#         while equities:
#             equities = print_right_column(equities)
#     else:
#         while equities:
#             equities = print_right_column(equities)

#     print_title("Income Statement Accounts")
#     print("  Revenue" + " " * 37 + "Expenses")
#     for i in range(max(len(revenues), len(expenses))):
#         if i < len(revenues):
#             r = revenues[i]
#         else:
#             r = ("   ", "")
#         if i < len(expenses):
#             e = expenses[i]
#         else:
#             e = ("   ", "")

#         m = 40 - len(r[1])
#         print(f"""  {r[0]} {r[1]}{' ' * m}{e[0]} {e[1]}""")
