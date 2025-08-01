import os
import sqlite3

from datetime import datetime
from infrastructure.sqlite._core import BaseSQLiteRepository
from infrastructure.sqlite.account_sqlite_repo import SQLiteAccountRepository
from infrastructure.sqlite.journal_entry_sqlite_repo import SQLiteJournalEntryRepository
from infrastructure.sqlite.ledger_transaction_sqlite_repo import SQLiteLedgerTransactionRepository
from infrastructure.sqlite._core import schema_sql


class SQLiteRepository(BaseSQLiteRepository):
    def __init__(self, db_path: str, schema_sql: str = schema_sql):

        super().__init__(db_path)

        self._schema_sql = schema_sql
        self.accounts = SQLiteAccountRepository(db_path)
        self.journal_entries = SQLiteJournalEntryRepository(db_path)
        self.ledger_transactions = SQLiteLedgerTransactionRepository(db_path)

        self.ensure_db_exists()

    def ensure_db_exists(self) -> None:
        '''Check if a SQLite database exists. If not, create it.'''
        db_exists = os.path.exists(self.db_path)

        if not db_exists:
            # Create the SQLite DB file (connect creates it automatically)
            with sqlite3.connect(self.db_path) as conn:
                conn.executescript(self._schema_sql)

    def get_journal_entries(self, from_: datetime, to_: datetime = None) -> list:
        '''Gets information for a journal'''

        if not to_:
            to_ = datetime.today()

        with self._connect() as conn:
            cursor = conn.cursor()
            sql = '''
                SELECT
                    j.ID,
                    l.ID,
                    j.Date,
                    j.Description,
                    a.Title,
                    a.Number,
                    l.TransactionAmount, 
                    a.IsDebitNorm
                FROM Ledger l
                JOIN Journal j ON l.EntryID = j.ID
                JOIN Account a ON l.AccountNumber = a.Number
                WHERE
                    DATE(j.Date) >= DATE(?) AND
                    DATE(j.Date) <= DATE(?)
                '''
            cursor.execute(sql, (from_, to_))
            results = cursor.fetchall()

        return results

    def get_general_ledger(self, account_number: int, from_: datetime, to_: datetime = None) -> list:
        '''Gets a general ledger'''

        if not to_:
            to_ = datetime.today()
        
        with self._connect() as conn:
            cursor = conn.cursor()
            sql = '''
                SELECT * 
                FROM GeneralLedger
                WHERE 
                    AccountNumber = ? AND 
                    DATE >= ? AND 
                    DATE <= ?;
            '''
            cursor.execute(sql, (account_number, from_, to_))
            results = cursor.fetchall()

        return results

