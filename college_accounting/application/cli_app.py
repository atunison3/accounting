import logging

from datetime import datetime

from domain.account import Account
from domain.journal_entry import JournalEntry
from domain.journal import Journal
from domain.ledger_transaction import LedgerTransaction
from infrastructure.sqlite.sqlite_repository import SQLiteRepository
from application.log_emoji import LogEmoji


def is_valid_date(date: str):

    if len(date) != 10:
        return False
    if date[4] != '-' or date[7] != '-':
        return False

    return True


class CLIApp:
    def __init__(self, db_path: str):
        self.repo = SQLiteRepository(db_path)

    def add_account(self, number: str | int, title: str, is_debit_norm: bool):
        '''Creates an account'''

        # Data integrity
        if not isinstance(number, int | str):
            raise TypeError('invalid number type')
        if not isinstance(title, str):
            raise TypeError('invalid account title type')
        if not isinstance(is_debit_norm, bool):
            raise TypeError('invalid is_debit_norm type')

        number = int(number)
        if number < 100:
            raise ValueError('invalid number (number > 99)')

        # Leading digit should inform of account type
        type_ = int(str(number)[0])

        # Verify a
        if not self.check_normal_balance(number, title, is_debit_norm):
            logging.warning(
                LogEmoji.WARNING.value + f'Account {number} may have the wrong debited boolean.'
            )

        # Initialize the account
        account = Account(
            id_=0,
            number=number,
            title=title,
            type_=type_,
            is_active=1,
            is_debit_norm=is_debit_norm,
            balance=None,
        )

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
            running_balance=None,
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

    # fmt: off
    def add_journal_entry_and_transaction(
        self, date: str, description: str, transactions_list: list
        ):
        # fmt: on
        '''Makes a journal entry and adds associated transactions'''

        # Add the entry
        try:
            journal_entry = self.add_journal_entry(date, description)
        except Exception as e:
            logging.error(LogEmoji.error + {e})

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
                _ = self.add_ledger_transaction(
                    journal_entry.id_, account_number, transaction_amount
                )
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

    def print_general_journal(self, from_: str, to_: str):
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
        journals = []
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
                journals[-1].credits.append((entry[4], entry[5], -1 * entry[6]))

        # Try printing
        print()
        print(' ' * 52 + 'GENERAL JOURNAL' + ' ' * 53)
        print('=' * 120)
        print(' ' * 9 + '|' + ' ' * 81 + '|     |           |')
        print(
            f'''   Date  |  {'Account Titles and Description' + ' ' * 49}| PR  |    Dr.    |   Cr.    '''
        )
        print('-' * 120)
        print(f'''         |{' ' * 81}|     |           |          ''')
        for journal in journals:
            journal.print_to_terminal()
        print()

    def print_trial_balance(self):
        '''Prints the trial balance sheet'''

        # Get a list of current accounts and balances
        accounts = self.repo.accounts.list_all_active()

        # Print title
        print()
        print(' ' * 54 + 'COMPANY NAME' + ' ' * 54)
        print(' ' * 53 + 'TRIAL BALANCE' + ' ' * 54)
        print(' ' * 58 + 'DATE' + ' ' * 58)
        print('=' * 120)

        # Print rows
        print(' ' * 96 + '|           |          ')
        print(' ' * 96 + '|    Dr.    |   Cr.    ')
        print('-' * 120)

        dr = 0
        cr = 0
        for account in accounts:
            if account.is_debit_norm:
                dr += account.balance
                n_title = 93 - len(account.title)
                print(f'  {account.title + ' ' * n_title} | {account.balance:>9.2f} |           ')
            else:
                cr += account.balance
                n_title = 93 - len(account.title)
                print(
                    f'  {account.title + ' ' * n_title} |           | {abs(account.balance):>9.2f} '
                )
        print()
        print(' ' * 96 + f'| {dr:>9.2f} | {abs(cr):>9.2f} ')
        print()

    def print_accounting_rules(self) -> None:
        '''Prints general debiting and crediting rules (source: ChatGPT)'''

        print("📘 Accounting Debit and Credit Rules\n")

        headers = ["Account Type", "Normal Balance", "Increase With", "Decrease With"]
        rows = [
            ["Assets", "Debit", "Debit", "Credit"],
            ["Liabilities", "Credit", "Credit", "Debit"],
            ["Equity (Capital)", "Credit", "Credit", "Debit"],
            ["Revenue (Income)", "Credit", "Credit", "Debit"],
            ["Expenses", "Debit", "Debit", "Credit"],
            ["Dividends / Drawings", "Debit", "Debit", "Credit"],
        ]

        # Print header
        print(
            f"| {'Account Type':<24} | {'Normal Balance':<15} | {'Increase With':<15} | {'Decrease With':<15} |"
        )
        print("|" + "-" * 26 + "|" + "-" * 17 + "|" + "-" * 17 + "|" + "-" * 17 + "|")

        # Print rows
        for row in rows:
            print(f"| {row[0]:<24} | {row[1]:<15} | {row[2]:<15} | {row[3]:<15} |")

    # Other functions
    def check_normal_balance(self, account_number: int, account_title: str, is_debit: bool) -> bool:
        '''Checks whether the given account's debit/credit direction (is_debit)'''

        title_lower = account_title.lower()

        # Special rule: any title with 'withdrawal' is treated as normally debit
        if 'withdrawal' in title_lower:
            normal_balance = True  # Debit
        elif 100 <= account_number < 200:
            normal_balance = True  # Assets
        elif 200 <= account_number < 300:
            normal_balance = False  # Liabilities
        elif 300 <= account_number < 400:
            normal_balance = False  # Equity (except withdrawals already handled)
        elif 400 <= account_number < 500:
            normal_balance = False  # Revenue
        elif 500 <= account_number < 600:
            normal_balance = True  # Expenses
        else:
            raise ValueError(f"Unknown account number range: {account_number}")

        return normal_balance == is_debit
