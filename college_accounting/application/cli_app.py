# import re

from datetime import datetime

from domain.account import Account
from domain.entry import Entry
from domain.journal import JournalEntry
from domain.transaction import Transaction
from infrastructure.sqlite.sqlite_repository import SQLiteRepository


def is_valid_date(date: str):

    if len(date) != 10:
        return False
    # if not re.findall(r'\d{4}-\d{2}-\d{2}'):
    #     return False
    if date[4] != '-' or date[7] != '-':
        return False

    return True


class CLIApp:
    def __init__(self, db_path: str):
        self.repo = SQLiteRepository(db_path)

    def add_account(self, number: str | int, name: str):
        '''Creates an account'''

        # Data integrity
        if not isinstance(number, int | str):
            raise TypeError('invalid number type')
        if not isinstance(name, str):
            raise TypeError('invalid name type')

        number = int(number)
        if number < 100:
            raise ValueError('invalid number (number > 99)')

        # Leading digit should inform of account type
        type_ = int(str(number)[0])

        # Initialize the account
        account = Account(account_id=0, number=number, name=name, type_=type_, is_active=1)

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

    def add_journal(self, date: str, description: str, transactions_list: list):
        '''Makes a journal entry and adds associated transactions'''

        # Add the entry
        try:
            entry = self.add_entry(date, description)
        except Exception as e:
            print(f'Error: {e}')

        # Verify balanced debits and credits
        dr_total = 0
        cr_total = 0
        for transaction in transactions_list:
            dr_total += transaction[1]
            cr_total += transaction[2]
        if dr_total != cr_total:
            raise ValueError("Unbalanced transaction!")

        # Iterate through transactions and add them
        for transaction_row in transactions_list:
            account_number, debit, credit = transaction_row
            try:
                _ = self.add_transaction(entry.entry_id, account_number, debit, credit)
            except Exception as e:
                print(f'Error: {e}')

    # Printing functions
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

    def print_journal(self, from_: str, to_: str):
        '''Prints journal entries'''

        if (not isinstance(from_, str)) or (not isinstance(to_, str | None)):
            raise TypeError('invalid date type(s)')
        if (not is_valid_date(from_)) or (not is_valid_date(to_)):
            raise ValueError('invalid date(s)')

        # Convert to datetime
        from_ = datetime.strptime(from_, '%Y-%m-%d')
        to_ = datetime.strptime(to_, '%Y-%m-%d')
        entries = self.repo.get_journal(from_, to_)

        # Convert entries to journal entries
        journal_entries = []
        last_id = 0
        for entry in entries:
            this_id = entry[0]
            if this_id != last_id:
                # New entry id (need to create a new journal entry)
                last_id = this_id
                journal_entry = JournalEntry(
                    entry_id=this_id,
                    date=entry[2],
                    description=entry[3],
                    debits=[(entry[4], entry[5], entry[6])],
                    credits=[],
                )
                journal_entries.append(journal_entry)
            elif entry[6] != 0:
                # Same entry adding another debit
                journal_entries[-1].debits.append((entry[4], entry[5], entry[6]))
            else:
                # Same entry adding the credits
                journal_entries[-1].credits.append((entry[4], entry[5], entry[7]))

        # Try printing
        print()
        print(
            f'''   Date  |  {'Account Titles and Description' + ' ' * 49}| PR  |    Dr.    |   Cr.    '''
        )
        print('-' * 120)
        print(f'''         |{' ' * 81}|     |           |          ''')
        for journal_entry in journal_entries:
            journal_entry.print_to_terminal()
        print()
