import logging
import os
import sys

from datetime import datetime
from domain.account import Account
from domain.entry import Entry
from domain.transaction import Transaction
from infrastructure.sqlite.sqlite_repository import SQLiteRepository
from sqlite3 import IntegrityError


def get_logger(name: str = 'app') -> logging.Logger:
    '''Set up and return a logger that prints to the terminal.'''
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)  # Change to INFO or WARNING in production

    # Avoid duplicate handlers if called multiple times
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)

        formatter = logging.Formatter(
            fmt='%(asctime)s - %(levelname)s - %(name)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)

        logger.addHandler(handler)

    return logger


def delete_database(db_path: str) -> None:
    '''Deletes a SQLite database file if it exists.'''
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
            print(f'🗑️ Database deleted: {db_path}')
        except PermissionError:
            print(f'❌ Permission denied. Could not delete {db_path}')
        except Exception as e:
            print(f'❌ Failed to delete {db_path}: {e}')
    else:
        print(f'ℹ️ Database does not exist: {db_path}')


logger = get_logger('accounting')

if __name__ == '__main__':

    db_path = '/Users/andrewtunison/accounting.db'
    sqlite_repo = SQLiteRepository(db_path)

    # Configure accounts to make
    # Example from pg 98 of College Accounting
    accounts_to_make = [
        (111, 'Cash', 1),
        (112, 'Accounts Receiveable', 1),
        (131, 'Supplies', 1),
        (141, 'Equipment', 1),
        (211, 'Accounts Payable', 2),
        (311, 'A. Todd Capital', 3),
        (321, 'A. Todd Withdrawls', 3),
        (411, 'Employment Fees Earned', 4),
        (511, 'Wage Expense', 5),
        (521, 'Telephone Expense', 5),
        (531, 'Advertising Expense', 5),
    ]

    for number, name, type_ in accounts_to_make:
        try:
            account = Account(account_id=0, number=number, name=name, type_=type_)
            sqlite_repo.accounts.add(account)
        except IntegrityError:
            print(f'''Account {number} {name} already added''')

    for i in range(1, len(accounts_to_make) + 1):
        account = sqlite_repo.accounts.get_by_id(i)
        print(f'''{account.number} {account.name}''')

    # March 2010

    # 1st: Abby Todd invested $5,000 cash in the new employment agency
    entry = Entry(
        entry_id=0,
        date=datetime(2010, 3, 1),
        description='Abby Todd invested $5,000 cash in the new employment agency.',
    )
    entry = sqlite_repo.entries.add(entry)
    transaction1 = Transaction(
        transaction_id=0, entry_id=entry.entry_id, account_number=111, debit=5000, credit=0
    )
    transaction2 = Transaction(
        transaction_id=0, entry_id=entry.entry_id, account_number=311, debit=0, credit=5000
    )
    transaction1 = sqlite_repo.transactions.add(transaction1)
    transaction2 = sqlite_repo.transactions.add(transaction2)

    # 4th: Bought equipment for cash, $200
    entry = Entry(
        entry_id=0, date=datetime(2010, 3, 4), description='Bought equipment for cash, $200'
    )
    entry = sqlite_repo.entries.add(entry)
    transaction1 = Transaction(
        transaction_id=0, entry_id=entry.entry_id, account_number=141, debit=200, credit=0
    )
    transaction2 = Transaction(
        transaction_id=0, entry_id=entry.entry_id, account_number=111, debit=0, credit=200
    )
    transaction1 = sqlite_repo.transactions.add(transaction1)
    transaction2 = sqlite_repo.transactions.add(transaction2)

    # 5th: Earned employment fee commission, $200, but payment from Blue Co. will not be
    # received unil June
    entry = Entry(
        entry_id=0,
        date=datetime(2010, 3, 5),
        description='Earned employment fee commission, $200, but payment from Blue Co. will not be received until June',
    )
    entry = sqlite_repo.entries.add(entry)
    transaction1 = Transaction(
        transaction_id=0, entry_id=entry.entry_id, account_number=112, debit=200, credit=0
    )
    transaction2 = Transaction(
        transaction_id=0, entry_id=entry.entry_id, account_number=411, debit=0, credit=200
    )
    transaction1 = sqlite_repo.transactions.add(transaction1)
    transaction2 = sqlite_repo.transactions.add(transaction2)

    # 6th
    entry = Entry(entry_id=0, date=datetime(2010, 3, 6), description='Paid wages expense, $300')
    entry = sqlite_repo.entries.add(entry)
    t1 = Transaction(
        transaction_id=0, entry_id=entry.entry_id, account_number=511, debit=300, credit=0
    )
    t2 = Transaction(
        transaction_id=0, entry_id=entry.entry_id, account_number=111, debit=0, credit=300
    )
    t1 = sqlite_repo.transactions.add(t1)
    t2 = sqlite_repo.transactions.add(t2)

    # New entry
    entry = Entry(entry_id=0, date=datetime(2010, 3, 7), description='Personal Withdrawals')
    entry = sqlite_repo.entries.add(entry)
    t1 = Transaction(
        transaction_id=0, entry_id=entry.entry_id, account_number=321, debit=75, credit=0
    )
    t2 = Transaction(
        transaction_id=0, entry_id=entry.entry_id, account_number=111, debit=0, credit=75
    )
    t1 = sqlite_repo.transactions.add(t1)
    t2 = sqlite_repo.transactions.add(t2)

    # New entry
    entry = Entry(entry_id=0, date=datetime(2010, 3, 9), description='Cash fees')
    entry = sqlite_repo.entries.add(entry)
    t1 = Transaction(
        transaction_id=0, entry_id=entry.entry_id, account_number=111, debit=1200, credit=0
    )
    t2 = Transaction(
        transaction_id=0, entry_id=entry.entry_id, account_number=411, debit=0, credit=1200
    )
    t1 = sqlite_repo.transactions.add(t1)
    t2 = sqlite_repo.transactions.add(t2)

    # New entry
    entry = Entry(
        entry_id=0, date=datetime(2010, 3, 15), description='Paid cash for supplies, $200'
    )
    entry = sqlite_repo.entries.add(entry)
    t1 = Transaction(
        transaction_id=0, entry_id=entry.entry_id, account_number=131, debit=200, credit=0
    )
    t2 = Transaction(
        transaction_id=0, entry_id=entry.entry_id, account_number=111, debit=0, credit=200
    )
    t1 = sqlite_repo.transactions.add(t1)
    t2 = sqlite_repo.transactions.add(t2)

    # New entry
    entry = Entry(
        entry_id=0,
        date=datetime(2010, 3, 28),
        description='Telephone bill received but not paid, $180',
    )
    entry = sqlite_repo.entries.add(entry)
    t1 = Transaction(
        transaction_id=0, entry_id=entry.entry_id, account_number=521, debit=180, credit=0
    )
    t2 = Transaction(
        transaction_id=0, entry_id=entry.entry_id, account_number=211, debit=0, credit=180
    )
    t1 = sqlite_repo.transactions.add(t1)
    t2 = sqlite_repo.transactions.add(t2)

    # Entry
    entry = Entry(
        entry_id=0,
        date=datetime(2010, 3, 29),
        description='Advertising bill received but not paid, $400',
    )
    entry = sqlite_repo.entries.add(entry)
    t1 = Transaction(
        transaction_id=0, entry_id=entry.entry_id, account_number=531, debit=400, credit=0
    )
    t2 = Transaction(
        transaction_id=0, entry_id=entry.entry_id, account_number=211, debit=0, credit=400
    )
    t1 = sqlite_repo.transactions.add(t1)
    t2 = sqlite_repo.transactions.add(t2)

    # Journal
    journal = sqlite_repo.get_journal(datetime(2010, 3, 1), datetime(2010, 3, 31))
    i = None
    print_length = 120
    print()
    print(
        '    Date   |  Account Titles and Description'
        + ' ' * (print_length - 77)
        + '| PR  |     Dr     |     Cr     |'
    )
    print('-' * print_length)
    print(
        f'''{journal[0][2][:4]}  |    |{' ' * (print_length - 45)}|     |            |            |'''
    )
    print(
        f'''  {journal[0][2][5:7]}  |    |{' ' * (print_length - 45)}|     |            |            |'''
    )
    for line in journal:

        if not i:
            i = line[0]

            day = line[2][8:10]
            title = line[4]

        elif line[2] != i:
            day = '  '
            title = '  ' + line[4]
            i = None

        n_title = print_length - 47 - len(title)
        if line[6] == 0:
            dr = ''
            cr = f'{line[7]:.2f}'
            n_dr = 10
            n_cr = 10 - len(cr)
        else:
            cr = ''
            dr = f'{line[6]:.2f}'
            n_dr = 10 - len(dr)
            n_cr = 10
        print(
            f'''      | {day} | {title + ' ' * n_title} | {line[5]} | {' ' * n_dr + dr} | {' ' * n_cr + cr} |'''
        )

        if not i:
            n_title = print_length - 50 - len(line[3][: print_length - 50])
            print(
                f'''      |    |    {line[3][:print_length-50] + ' ' * n_title} |     |            |            |'''
            )
            print(f'''      |    |{' ' * (print_length - 45)}|     |            |            |''')

    delete_database(db_path)
