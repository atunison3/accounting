import re

from datetime import datetime

from domain.account import Account
from domain.entry import Entry
from domain.transaction import Transaction
from infrastructure.sqlite.sqlite_repository import SQLiteRepository


def is_valid_date(date: str):

    if len(date) != 10:
        return False
    if not re.findall(r'\d{4}-\d{2}-\d{2}'):
        return False

    return True


class Application:
    def __init__(self, db_path: str):
        self.repo = SQLiteRepository(db_path)

    def add_account(self, number: int, name: str):
        '''Creates an account'''

        # Data integrity
        if not isinstance(number, int):
            raise TypeError('invalid number type')
        if not isinstance(name, str):
            raise TypeError('invalid name type')

        if number < 100:
            raise ValueError('invalid number (number > 99)')

        # Leading digit should inform of account type
        type_ = int(str(number)[0])

        # Initialize the account
        account = Account(account_id=0, number=number, name=name, type_=type_)

        account = self.repo.accounts.add(account)

        return account

    def add_transaction(self, entry_id: int, account_number: int, debit: float, credit: float):

        if not isinstance(account_number, int):
            raise TypeError('invalid account_number type')
        if not isinstance(debit, float | int):
            raise TypeError('invalid debit type')
        if not isinstance(credit, float | int):
            raise TypeError('invalid credit type')
        if not isinstance(entry_id, int):
            raise TypeError('invalid entry id')

        if account_number < 100:
            raise ValueError('invalid account number (account_number > 99)')
        if debit < 0 or credit < 0:
            raise ValueError('invalid debit or credit values')
        if (debit != 0) and (credit != 0):
            raise ValueError('invalid debit and credit values (one value needs to be zero)')
        if entry_id < 1:
            raise ValueError('invalid entry id (entry_id > 0)')

        transaction = Transaction(
            transaction_id=0,
            entry_id=entry_id,
            account_number=account_number,
            debit=debit,
            credit=credit,
        )

        transaction = self.repo.transactions.add(transaction)

        return transaction

    def add_entry(self, date: str, description: str):

        if not isinstance(date, str):
            raise TypeError('invalid date type')
        if not isinstance(description, str):
            raise TypeError('invalid description type')

        if not is_valid_date(date):
            raise ValueError('invalid date format')
        if len(description) < 10:
            raise ValueError('description is too short')

        # Data corrections
        date = datetime.strptime(date, '%Y-%m-%d')

        # Create entry entity
        entry = Entry(entry_id=0, date=date, description=description)

        entry = self.repo.entries.add(entry)

        return entry

    def chart_of_accounts(self):
        '''Print a chart of accounts'''

        accounts = self.repo.accounts.list_all()
        accounts.sort(key=lambda x: x.number)

        def print_types(section_title: str, type_: int):
            print(section_title)
            for account in [a for a in accounts if a.type_ == type_]:
                print(f'    {account.number} {account.name}')
            print()

        print('\nChart of Accounts')
        print_types('  Asset Accounts', 1)
        print_types('  Liability Accounts', 2)
        print_types('  Capital Accounts', 3)
        print_types('  Revenue Accounts', 4)
        print_types('  Expense Accounts', 5)
