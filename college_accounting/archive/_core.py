import pandas as pd
from datetime import datetime

__all__ = ["SpreadSheet", "Transaction"]


class AccountingRow:
    def __init__(  # noqa: PLR0913
        self,
        date: datetime,
        cash: float = 0,
        supplies: float = 0,
        shop_equipment: float = 0,
        office_equipment: float = 0,
        accounts_payable: float = 0,
        freedman_capital: float = 0,
        freedman_withdrawal: float = 0,
        service_revenue: float = 0,
        expenses: float = 0,
        expense_type: str = "",
        description: str = None,
    ):
        self.A = None
        self.date = date
        self.cash = cash
        self.supplies = supplies
        self.computer_shop_equipment = shop_equipment
        self.office_equipment = office_equipment
        self.accounts_payable = accounts_payable
        self.freedman_capital = freedman_capital
        self.freedman_withdrawal = freedman_withdrawal
        self.service_revenue = service_revenue
        self.expenses = expenses
        self.expense_type = expense_type
        self.description = description

    def to_dict(self):
        return {
            "A": self.A,
            "Date": self.date,
            "Cash": self.cash,
            "Supplies": self.supplies,
            "Computer Shop Equipment": self.computer_shop_equipment,
            "Office Equipment": self.office_equipment,
            "Accounts Payable": self.accounts_payable,
            "Freedman Capital": self.freedman_capital,
            "Freedman Withdrawal": self.freedman_withdrawal,
            "Service Revenue": self.service_revenue,
            "Expenses": self.expenses,
            "Expense Type": self.expense_type,
            "Description": self.description,
        }


class Transaction(AccountingRow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.A = "Transaction"


class Balance(AccountingRow):
    def __init__(self, date: datetime, prev_balance: dict, transaction: dict):
        super().__init__(date)
        self.A = "Balance"

        # Sum previous balance with transaction
        for key in prev_balance:
            if key not in ["A", "Date", "Expense Type", "Description"]:
                prev_value = prev_balance.get(key, 0)
                trans_value = transaction.get(key, 0)
                setattr(self, key.lower().replace(" ", "_"), prev_value + trans_value)


# Setup DataFrame
class SpreadSheet(pd.DataFrame):
    def __init__(self):

        columns = [
            "A",
            "Date",
            "Cash",
            "Supplies",
            "Computer Shop Equipment",
            "Office Equipment",  # Assets
            "Accounts Payable",  # Liabilities
            "Freedman Capital",
            "Freedman Withdrawal",
            "Service Revenue",
            "Expenses",  # Equity
            "Expense Type",
            "Description",
        ]
        super().__init__(columns=columns)

    @property
    def total_assets(self):
        """Calculates the total assets"""

        if len(self) == 0:
            return 0
        n = len(self) - 1  # get the last row (Balance)
        return sum(
            self.loc[n, col]
            for col in ["Cash", "Supplies", "Computer Shop Equipment", "Office Equipment"]
        )

    @property
    def total_liabilities(self):
        """Calculates total liabilities"""

        if len(self) == 0:
            return 0
        n = len(self) - 1

        return sum(self.loc[n, col] for col in ["Accounts Payable"])

    @property
    def total_equity(self):
        """Calculates total equity"""

        if len(self) == 0:
            return 0
        n = len(self) - 1

        total_equity = 0
        for column in ["Freedman Capital", "Service Revenue"]:
            total_equity += self.loc[n, column]
        for column in ["Freedman Withdrawal", "Expenses"]:
            total_equity -= self.loc[n, column]

        return total_equity

    def add_row(self, accounting_row: Transaction):
        """Adds a Transaction row and updates Balance row"""
        if not isinstance(accounting_row, Transaction):
            raise TypeError("Only Transaction rows can be added directly.")

        # Append the transaction
        transaction_df = pd.DataFrame([accounting_row.to_dict()])
        updated_df = pd.concat([self, transaction_df], ignore_index=True)

        # Calculate new balance
        prev_balance = (
            updated_df.iloc[-2].to_dict()
            if (len(updated_df) >= 2) and (updated_df.iloc[-2]["A"] == "Balance")
            else {col: 0 for col in self.columns}
        )

        balance_row = Balance(
            date=accounting_row.date,
            prev_balance=prev_balance,
            transaction=accounting_row.to_dict(),
        )

        # Append the balance row
        balance_df = pd.DataFrame([balance_row.to_dict()])
        updated_df = pd.concat([updated_df, balance_df], ignore_index=True)

        # Update self in place
        self.__init__()
        for col in updated_df.columns:
            self[col] = updated_df[col]

        if self.total_assets != self.total_liabilities + self.total_equity:
            raise ValueError("Spreadsheet is not balanced!")
