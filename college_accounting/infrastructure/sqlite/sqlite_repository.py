import logging
import os
import sqlite3

from infrastructure.sqlite.account_sqlite_repo import SQLiteAccountRepository
from infrastructure.sqlite._core import schema_sql


class SQLiteRepository:
    def __init__(self, db_path: str, schema_sql: str = schema_sql):

        self.db_path = db_path
        self._schema_sql = schema_sql
        self.accounts = SQLiteAccountRepository(db_path)

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
