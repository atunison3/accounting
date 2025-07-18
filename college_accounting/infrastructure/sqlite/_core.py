import sqlite3


class BaseSQLiteRepository:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = None

    def _connect(self):
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.execute("PRAGMA journal_mode=WAL;")  # Enable Write-Ahead Logging
        return conn


schema_sql = '''
CREATE TABLE IF NOT EXISTS accounts (
    account_id INTEGER PRIMARY KEY AUTOINCREMENT,
    number INTEGER NOT NULL UNIQUE,
    name TEXT NOT NULL,
    type_ INT NOT NULL, 
    is_active BOOL NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS entries (
    entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS transactions (
    transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_id INTEGER NOT NULL,
    account_number INTEGER NOT NULL,
    debit REAL,
    credit REAL,
    FOREIGN KEY (account_number) REFERENCES accounts (number),
    FOREIGN KEY (entry_id) REFERENCES entries (entry_id)
);
'''
