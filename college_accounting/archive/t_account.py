import pandas as pd


def leading_digit(n: int) -> int:
    """Returns the leading digit of an integer"""

    return int(str(abs(n))[0])


class Account(pd.DataFrame):
    def __init__(self, name: str, number: int):
        super().__init__(columns=["Transaction", "Amount", "Debit"])
        self.name = name
        self.number = number
        self.type_ = leading_digit(number)

    def add_transaction(self, transaction: str, amount: int, debit: bool):
        """Adds a line to the dataframe"""

        # Create the new row
        new_row = pd.DataFrame([{"Transaction": transaction, "Amount": amount, "Debit": debit}])

        # "Append" the dict and reassign
        updated = pd.concat([self, new_row], ignore_index=True)
        self.__dict__.update(updated.__dict__)

    def print_account(self):
        """Prints the account in a t chart"""

        # Print the header information
        n = (27 - len(self.name + " " + str(self.number))) // 2
        print(" " * n + self.name + " " + str(self.number))
        print("---------------------------")

        # Get lists for debits and credits
        debits = [(r["Transaction"], f"{r['Amount']:,}") for _, r in self.iterrows() if r["Debit"]]
        credits = [
            (r["Transaction"], f"{r['Amount']:,}")
            for r in self.values()
            if r["Debit"] == False  # noqa: E712
        ]

        # Calculate the totals
        left_total = sum(d.Amount for _, d in self.iterrows() if d.Debit)
        right_total = sum(c.Amount for _, c in self.iterrows() if c.Debit == False)  # noqa: E712
        left_sum = f"{left_total:,}"
        right_sum = f"{right_total:,}"

        # Iterate through and print lines
        while debits or credits:
            debits, credits = self.print_line(debits, credits)

        print("             |             ")
        print(
            f"""     {' ' * (7 - len(left_sum))}{left_sum} | {' ' * (7 - len(right_sum))}{right_sum}"""
        )

        total = f"""{left_total - right_total:,}"""
        print(f"""     {' ' * (7 - len(total))}{total}""")

    def print_line(self, debits: list, credits: list):
        """Prints one line in the print_account function"""

        # Automatically assign values in case of nulls
        d, c = (" ", "       "), (" ", "       ")

        # If there are remaining items get the first
        if debits:
            d = debits.pop(0)
        if credits:
            c = credits.pop(0)

        # Build the left/right side of the print line
        if d[0] != " ":
            left = f""" ({d[0]}) {' ' * (7 - len(d[1]))}{d[1]} """
        else:
            left = f"""     {' ' * (7 - len(d[1]))}{d[1]} """
        if c[0] != " ":
            right = f""" {' ' * (7 - len(c[1]))}{c[1]} ({c[0]})"""
        else:
            right = f""" {' ' * (7 - len(c[1]))}{c[1]}    """

        # Join left/right and print
        print("|".join([left, right]))

        return debits, credits


class BusinessAccounts:
    def __init__(self):
        self.accounts = {}

    def add_account(self, name: str, number: int):
        self.accounts[number] = Account(name, number)

    def print_section_title(self, title: str):
        """Prints a section title"""

        n = int((80 - len(title)) // 2)
        print("\n")
        print("-" * 80)
        line = " " * n + title + " " * (n)
        while len(line) < 80:
            line += " "
        print(" " * n + title + " " * (n))
        print("-" * 80)
        print("\n")

    def print_line(self, left: list, right: list) -> tuple[list]:
        """Prints one line"""

        left_str, right_str = "", ""
        if left:
            left_str = left.pop(0)
        if right:
            right_str = right.pop(0)

        m = 44 - len(left_str)
        line = f"""  {left_str}{' ' * m}{right_str}"""
        line += " " * (80 - len(line))
        print(line)

        return left, right

    def chart_of_accounts(self):
        """Print a Chart of Accounts"""

        # Separate the different types of accounts
        assets = [v for k, v in self.accounts.items() if v.type_ == 1]
        liabilities = [v for k, v in self.accounts.items() if v.type_ == 2]
        equities = [v for k, v in self.accounts.items() if v.type_ == 3]
        revenues = [v for k, v in self.accounts.items() if v.type_ == 4]
        expenses = [v for k, v in self.accounts.items() if v.type_ == 5]

        # Print the Balance Sheet Accounts
        self.print_section_title("Balance Sheet Accounts")

        left = ["Assets"] + [f"{x.number} {x.name}" for x in assets]
        right = ["Liabilities"] + [f"{x.number} {x.name}" for x in liabilities]
        right += ["""Owner's Equity"""] + [f"{x.number} {x.name}" for x in equities]

        while left or right:
            left, right = self.print_line(left, right)

        # Print the Income Statement Accounts
        self.print_section_title("Income Statement Accounts")

        left = ["Revenue"] + [f"{x.number} {x.name}" for x in revenues]
        right = ["Expenses"] + [f"{x.number} {x.name}" for x in expenses]
        while left or right:
            left, right = self.print_line(left, right)
