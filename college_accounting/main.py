from sqlite3 import IntegrityError

# from domain.account import Account
# from domain.entry import Entry
# from domain.transaction import Transaction

from application.application import Application
from utility_functions import delete_database

if __name__ == '__main__':
    db_path = '/Users/andrewtunison/accounting.db'
    app = Application(db_path)

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
    for number, name, _ in accounts_to_make:
        try:
            app.add_account(number, name)
        except IntegrityError:
            print(f'{number} {name} already in database')

    app.chart_of_accounts()

    delete_database(db_path)
