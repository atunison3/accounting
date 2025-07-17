from sqlite3 import IntegrityError

from application.cli_app import CLIApp
from utility_functions import delete_database

if __name__ == '__main__':
    db_path = '/Users/andrewtunison/accounting.db'
    app = CLIApp(db_path)

    # Configure accounts to make
    # Example from pg 98 of College Accounting
    accounts_to_make = [
        ('Cash', 111),
        ('Accounts Receiveable', 112),
        ('Prepaid Rent', 114),
        ('Art Supplies', 121),
        ('Equipment', 131),
        ('Accounts Payable', 211),
        ('Barbie Riley, Capital', 311),
        ('Barbie Riley, Withdrawals', 312),
        ('Arts Fees Earned', 411),
        ('Electrical Expense', 511),
        ('Salaries Expense', 521),
        ('Telephone Expense', 531),
    ]
    for name, number in accounts_to_make:
        try:
            app.add_account(number, name)
        except IntegrityError:
            print(f'{number} {name} already in database')

    app.chart_of_accounts()

    # Add journal entry (pg 114)
    date, description = '2010-11-01', 'A. Glover invested $5,000 cash in the placement agency'
    transactions = [(111, 8000, 0), (311, 0, 8000)]
    app.add_journal(date, description, transactions)

    date, description = '2010-11-01', 'Paid ten months\' rent in advance, $2,800'
    transactions = [(114, 2800, 0), (111, 0, 2800)]
    app.add_journal(date, description, transactions)

    date, description = '2010-11-03', 'Purchased $1,200 of equipment from Omni Co. on account.'
    transactions = [(131, 1200, 0), (211, 0, 1200)]
    app.add_journal(date, description, transactions)

    app.print_journal('2010-11-01', '2010-11-30')

    delete_database(db_path)
