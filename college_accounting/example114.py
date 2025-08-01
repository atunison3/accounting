from sqlite3 import IntegrityError

from application.cli_app import CLIApp
from utility_functions import delete_database

if __name__ == '__main__':

    db_path = '/Users/andrewtunison/accounting.db'
    delete_database(db_path)
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
    journal_entry = app.add_journal_entry(date, description)
    ledger_transaction = app.add_ledger_transaction(journal_entry.id_, 111, 8000)
    ledger_transaction = app.add_ledger_transaction(journal_entry.id_, 311, -8000)

    date, description = '2010-11-01', 'Paid ten months\' rent in advance, $2,800'
    journal_entry = app.add_journal_entry(date, description)
    ledger_transaction = app.add_ledger_transaction(journal_entry.id_, 114, 2800)
    ledger_transaction = app.add_ledger_transaction(journal_entry.id_, 111, -2800)

    date, description = '2010-11-03', 'Purchased $1,200 of equipment from Omni Co. on account.'
    journal_entry = app.add_journal_entry(date, description)
    ledger_transaction = app.add_ledger_transaction(journal_entry.id_, 131, 1200)
    ledger_transaction = app.add_ledger_transaction(journal_entry.id_, 211, -1200)

    date, description = '2010-11-05', 'Purchased $900 cash for art-training workshop for teachers.'
    journal_entry = app.add_journal_entry(date, description)
    ledger_transaction = app.add_ledger_transaction(journal_entry.id_, 521, 900)
    ledger_transaction = app.add_ledger_transaction(journal_entry.id_, 111, -900)

    date, description = '2010-11-08', 'Purchased $450 of art supplies for cash.'
    journal_entry = app.add_journal_entry(date, description)
    ledger_transaction = app.add_ledger_transaction(journal_entry.id_, 121, 450)
    ledger_transaction = app.add_ledger_transaction(journal_entry.id_, 111, -450)

    date, description = (
        '2010-11-09',
        'Billed Howie Co. $2,500 for group art lessons for its employees.',
    )
    journal_entry = app.add_journal_entry(date, description)
    ledger_transaction = app.add_ledger_transaction(journal_entry.id_, 112, 2500)
    ledger_transaction = app.add_ledger_transaction(journal_entry.id_, 411, -2500)

    date, description = '2010-11-10', 'Paid salaries of assistants, $1,300'
    journal_entry = app.add_journal_entry(date, description)
    ledger_transaction = app.add_ledger_transaction(journal_entry.id_, 521, 1300)
    ledger_transaction = app.add_ledger_transaction(journal_entry.id_, 111, -1300)

    date, description = '2010-11-15', 'Barbie withdrew $100 from the business for personal use'
    journal_entry = app.add_journal_entry(date, description)
    ledger_transaction = app.add_ledger_transaction(journal_entry.id_, 312, 100)
    ledger_transaction = app.add_ledger_transaction(journal_entry.id_, 111, -100)

    date, description = '2010-11-28', 'Paid electrical bill, $110'
    journal_entry = app.add_journal_entry(date, description)
    ledger_transaction = app.add_ledger_transaction(journal_entry.id_, 511, 110)
    ledger_transaction = app.add_ledger_transaction(journal_entry.id_, 111, -110)

    date, description = '2010-11-29', 'Paid telephone bill for November, $140'
    journal_entry = app.add_journal_entry(date, description)
    ledger_transaction = app.add_ledger_transaction(journal_entry.id_, 531, 140)
    ledger_transaction = app.add_ledger_transaction(journal_entry.id_, 111, -140)

    app.print_general_journal('2010-11-01', '2010-11-30')

    app.print_trial_balance()

    delete_database(db_path)
