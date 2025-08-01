import logging

from sqlite3 import IntegrityError

from application.cli_app import CLIApp
from utility_functions import delete_database

if __name__ == '__main__':

    # Set up the logger
    logger = logging.getLogger('general')
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    db_path = '/Users/andrewtunison/accounting.db'
    delete_database(db_path)
    app = CLIApp(db_path)

    # Configure accounts to make
    # Example from pg 98 of College Accounting
    accounts_to_make = [
        ('Cash', 111, True),
        ('Accounts Receiveable', 112, True),
        ('Supplies', 131, True),
        ('Equipment', 141, True),
        ('Accounts Payable', 211, False),
        ('A. Todd, Capital', 311, False),
        ('A. Todd, Withdrawals', 321, True),
        ('Employment Fees Earned', 411, False),
        ('Wage Expense', 511, True),
        ('Telephone Expense', 521, True),
        ('Advertising Expense', 531, True),
    ]
    for name, number, is_debit in accounts_to_make:
        try:
            app.add_account(number, name, is_debit)
        except IntegrityError:
            logging.info(f'{log_emoji.info} {number} {name} already in database')

    app.chart_of_accounts()

    # Add journal entry (pg 98)
    date, description = '2010-03-01', 'Abby Todd invested $5,000 cash in the new employment agency.'
    journal_entry = app.add_journal_entry(date, description)
    ledger_transaction = app.add_ledger_transaction(journal_entry.id_, 111, 5000)
    ledger_transaction = app.add_ledger_transaction(journal_entry.id_, 311, -5000)

    date, description = '2010-03-04', 'Bought equipment for cash, $200.'
    journal_entry = app.add_journal_entry(date, description)
    ledger_transaction = app.add_ledger_transaction(journal_entry.id_, 141, 200)
    ledger_transaction = app.add_ledger_transaction(journal_entry.id_, 111, -200)

    date, description = (
        '2010-03-05',
        'Earned employment fee commision, $200, but payment from Blue Co. will not be received until June.',
    )
    journal_entry = app.add_journal_entry(date, description)
    ledger_transaction = app.add_ledger_transaction(journal_entry.id_, 112, 200)
    ledger_transaction = app.add_ledger_transaction(journal_entry.id_, 411, -200)

    date, description = '2010-03-06', 'Paid wages expense, $300.'
    journal_entry = app.add_journal_entry(date, description)
    ledger_transaction = app.add_ledger_transaction(journal_entry.id_, 511, 300)
    ledger_transaction = app.add_ledger_transaction(journal_entry.id_, 111, -300)

    date, description = (
        '2010-03-07',
        'Abby paid her home utility bill from the company checkbook, $75.',
    )
    journal_entry = app.add_journal_entry(date, description)
    ledger_transaction = app.add_ledger_transaction(journal_entry.id_, 321, 75)
    ledger_transaction = app.add_ledger_transaction(journal_entry.id_, 111, -75)

    date, description = (
        '2010-03-09',
        'Placed Rick Wool at VCR Corporation, receiving $1,200 cash.',
    )
    journal_entry = app.add_journal_entry(date, description)
    ledger_transaction = app.add_ledger_transaction(journal_entry.id_, 111, 1200)
    ledger_transaction = app.add_ledger_transaction(journal_entry.id_, 411, -1200)

    date, description = '2010-03-15', 'Paid cash for supplies, $200'
    journal_entry = app.add_journal_entry(date, description)
    ledger_transaction = app.add_ledger_transaction(journal_entry.id_, 131, 200)
    ledger_transaction = app.add_ledger_transaction(journal_entry.id_, 111, -200)

    date, description = '2010-03-28', 'Telephone bill received but not paid, $180.'
    journal_entry = app.add_journal_entry(date, description)
    ledger_transaction = app.add_ledger_transaction(journal_entry.id_, 521, 180)
    ledger_transaction = app.add_ledger_transaction(journal_entry.id_, 211, -180)

    date, description = '2010-03-29', 'Advertising bill received but not paid, $400'
    journal_entry = app.add_journal_entry(date, description)
    ledger_transaction = app.add_ledger_transaction(journal_entry.id_, 531, 400)
    ledger_transaction = app.add_ledger_transaction(journal_entry.id_, 211, -400)

    app.print_general_journal('2010-03-01', '2010-03-31')

    app.print_trial_balance()

    accounts = app.list_all_active_accounts()
    for account in accounts:
        app.print_account_ledger(account.number, '2010-03-01', '2010-03-31')

    # delete_database(db_path)
