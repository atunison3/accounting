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
CREATE TABLE IF NOT EXISTS Account (
    ID INTEGER PRIMARY KEY AUTOINCREMENT,
    Number INTEGER NOT NULL UNIQUE,
    Title TEXT NOT NULL,
    Type_ INT NOT NULL, 
    IsActive BOOL NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS Journal (
    ID INTEGER PRIMARY KEY AUTOINCREMENT,
    Date TEXT NOT NULL,
    Description TEXT
);

CREATE TABLE IF NOT EXISTS Ledger (
    ID INTEGER PRIMARY KEY AUTOINCREMENT,
    EntryID INTEGER NOT NULL REFERENCES Journal(ID),
    AccountNumber INTEGER NOT NULL REFERENCES Account(Number), -- FK to Accounts table
    TransactionAmount REAL NOT NULL
) STRICT;
'''
