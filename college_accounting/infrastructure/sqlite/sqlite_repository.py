import os
import sqlite3

from datetime import datetime
from infrastructure.sqlite._core import BaseSQLiteRepository
from infrastructure.sqlite.account_sqlite_repo import SQLiteAccountRepository
from infrastructure.sqlite.entry_sqlite_repo import SQLiteEntryRepository
from infrastructure.sqlite.transaction_sqlite_repo import SQLiteTransactionRepository
from infrastructure.sqlite._core import schema_sql


class SQLiteRepository(BaseSQLiteRepository):
    def __init__(self, db_path: str, schema_sql: str = schema_sql):

        super().__init__(db_path)

        self._schema_sql = schema_sql
        self.accounts = SQLiteAccountRepository(db_path)
        self.entries = SQLiteEntryRepository(db_path)
        self.transactions = SQLiteTransactionRepository(db_path)

        self.ensure_db_exists()

    def ensure_db_exists(self) -> None:
        '''Check if a SQLite database exists. If not, create it.'''
        db_exists = os.path.exists(self.db_path)

        if db_exists:
            print(f'✅ Database already exists at {self.db_path}')
        else:
            print(f'⚡ Creating new database at {self.db_path}')
            # Create the SQLite DB file (connect creates it automatically)
            with sqlite3.connect(self.db_path) as conn:
                if self._schema_sql:
                    conn.executescript(self._schema_sql)
                    print('📦 Database schema initialized.')
                else:
                    print('📦 Empty database created (no schema).')

    def get_journal(self, from_: datetime, to_: datetime = None) -> list:
        '''Gets information for a journal'''

        if not to_:
            to_ = datetime.today()

        cursor = self._connect()

        sql = '''
            SELECT
                e.entry_id,
                t.transaction_id,
                e.date,
                e.description,
                a.name,
                a.number,
                t.debit,
                t.credit
            FROM transactions t
            JOIN entries e ON t.entry_id = e.entry_id
            JOIN accounts a ON t.account_number = a.number
            WHERE
                e.date >= ? AND
                e.date <= ?
            '''
        cursor.execute(sql, (from_, to_))

        results = cursor.fetchall()

        self._disconnect()

        return results
