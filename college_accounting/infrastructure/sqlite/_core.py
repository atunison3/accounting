import sqlite3


class BaseSQLiteRepository:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def _connect(self):
        self.conn = sqlite3.connect(self.db_path)
        cursor = self.conn.cursor()

        return cursor

    def _disconnect(self):
        self.conn.commit()
        self.conn.close()


schema_sql = '''
CREATE TABLE IF NOT EXISTS accounts (
    account_id INTEGER PRIMARY KEY AUTOINCREMENT,
    number INTEGER NOT NULL UNIQUE,
    name TEXT NOT NULL,
    type_ INT NOT NULL
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
