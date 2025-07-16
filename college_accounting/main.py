import logging
import os
import sys

from domain.account import Account
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
        sqlite_repo.accounts.delete(i)

    # Add the account to the database

    delete_database(db_path)
