__all__ = ["BalanceSheet"]


class BalanceSheet:
    def __init__(self):
        self._assets = {}
        self._liabilities = {}

    @property
    def assets(self):
        return sum(self._assets.values())

    @property
    def liabilities(self):
        return sum(self._liabilities.values())

    @property
    def equity(self):
        return self.assets - self.liabilities

    def add_asset(self, new_asset: str, value: float):
        """Add asset to list"""
        self._assets[new_asset[:12]] = value

    def add_liability(self, new_liability: str, value: float):
        """Add new liability"""
        self._liabilities[new_liability[:12]] = value

    def print_balance_sheet(self):
        """Prints the balance sheet in a clean format"""

        width = 36

        print("=" * width)
        n = (width - 14) // 2
        print(" " * n + "BALANCE SHEET" + " " * n)
        print("=" * width)

        print("Assets")
        for i, (k, v) in enumerate(self._assets.items()):
            if i == 0:
                line = f"    {k}"
                n = width - 5 - len(k) - len(str(v))
                line += " " * n
                line += f"${v:d}"
            else:
                line = f"    {k}"
                n = width - 4 - len(k) - len(str(v))
                line += " " * n
                line += f"{v:d}"
            print(line)
        print("Total Assets")
        print("=" * width)

        print("Liabilities")
        # Fill in liabilities
        for i, (k, v) in enumerate(self._liabilities.items()):
            if i == 0:
                line = f"    {k}"
                n = width - 5 - len(k) - len(str(v))
                line += " " * n
                line += f"${v:d}"
            else:
                line = f"    {k}"
                n = width - 4 - len(k) - len(str(v))
                line += " " * n
                line += f"{v:d}"
            print(line)
        liabilities = self.liabilities
        n = width - 18 - len(str(liabilities))
        line = f"Total Liabilities" + " " * n + f"${liabilities}"
        print(line)
        print("=" * width)

        equity = self.equity
        line = "Total Equity" + " " * (width - 13 - len(str(equity))) + f"${equity}"
        print(line)
