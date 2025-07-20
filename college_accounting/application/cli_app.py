# import re

from datetime import datetime

from domain.account import Account
from domain.journal_entry import JournalEntry
from domain.journal import Journal
from domain.ledger_transaction import LedgerTransaction
from infrastructure.sqlite.sqlite_repository import SQLiteRepository


def is_valid_date(date: str):

    if len(date) != 10:
        return False
    if date[4] != '-' or date[7] != '-':
        return False

    return True


class CLIApp:
    def __init__(self, db_path: str):
        self.repo = SQLiteRepository(db_path)

    def add_account(self, number: str | int, title: str):
        '''Creates an account'''

        # Data integrity
        if not isinstance(number, int | str):
            raise TypeError('invalid number type')
        if not isinstance(title, str):
            raise TypeError('invalid account title type')

        number = int(number)
        if number < 100:
            raise ValueError('invalid number (number > 99)')

        # Leading digit should inform of account type
        type_ = int(str(number)[0])

        # Initialize the account
        account = Account(id_=0, number=number, title=title, type_=type_, is_active=1)

        account = self.repo.accounts.add(account)

        return account

    def add_ledger_transaction(self, entry_id: int, account_number: int, transaction_amount: float):

        if not isinstance(account_number, int):
            raise TypeError('invalid account_number type')
        if not isinstance(transaction_amount, float | int):
            raise TypeError('invalid debit type')
        if not isinstance(entry_id, int):
            raise TypeError('invalid entry id')

        if account_number < 100:
            raise ValueError('invalid account number (account_number > 99)')
        if entry_id < 1:
            raise ValueError('invalid entry_id (entry_id > 0)')

        ledger_transaction = LedgerTransaction(
            id_=0,
            entry_id=entry_id,
            account_number=account_number,
            transaction_amount=transaction_amount,
            account_balance=None,
        )

        ledger_transaction = self.repo.ledger_transactions.add(ledger_transaction)

        return ledger_transaction

    def add_journal_entry(self, date: str, description: str):

        if not isinstance(date, str):
            raise TypeError('invalid date type')
        if not isinstance(description, str):
            raise TypeError('invalid description type')

        if not is_valid_date(date):
            raise ValueError('invalid date format')
        if len(description) < 10:
            raise ValueError('description is too short')

        # Create entry entity
        journal_entry = JournalEntry(id_=0, date=date, description=description)

        journal_entry = self.repo.journal_entries.add(journal_entry)

        return journal_entry

    def add_journal_entry_and_transaction(self, date: str, description: str, transactions_list: list):
        '''Makes a journal entry and adds associated transactions'''

        # Add the entry
        try:
            journal_entry = self.add_journal_entry(date, description)
        except Exception as e:
            print(f'Error: {e}')

        # Verify balanced debits and credits
        total = 0
        for transaction in transactions_list:
            total += transaction[1]
        if total != 0:
            raise ValueError("Unbalanced transaction!")

        # Iterate through transactions and add them
        for transaction_row in transactions_list:
            account_number, transaction_amount = transaction_row
            try:
                _ = self.add_ledger_transaction(journal_entry.id_, account_number, transaction_amount)
            except Exception as e:
                print(f'Error: {e}')

    # Printing functions
    def chart_of_accounts(self):
        '''Print a chart of accounts'''

        accounts = self.repo.accounts.list_all_active()
        accounts.sort(key=lambda x: x.number)

        def print_types(section_title: str, type_: int):
            print(section_title)
            for account in [a for a in accounts if a.type_ == type_]:
                print(f'    {account.number} {account.title}')
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
        journal_entries = self.repo.get_journal_entries(from_, to_)

        # Convert entries to journal entries
        journals  = []
        last_id = 0
        for entry in journal_entries:
            this_id = entry[0]
            if this_id != last_id:
                # New entry id (need to create a new journal entry)
                last_id = this_id
                journal = Journal(
                    id_=this_id,
                    date=datetime.strptime(entry[2], '%Y-%m-%d'),
                    description=entry[3],
                    debits=[(entry[4], entry[5], entry[6])],
                    credits=[],
                )
                journals.append(journal)
            elif entry[6] > 0:
                # Same entry adding another debit
                journals[-1].debits.append((entry[4], entry[5], entry[6]))
            else:
                # Same entry adding the credits
                journals[-1].credits.append((entry[4], entry[5], entry[6]))

        # Try printing
        print()
        print(
            f'''   Date  |  {'Account Titles and Description' + ' ' * 49}| PR  |    Dr.    |   Cr.    '''
        )
        print('-' * 120)
        print(f'''         |{' ' * 81}|     |           |          ''')
        for journal in journals:
            journal.print_to_terminal()
        print()
