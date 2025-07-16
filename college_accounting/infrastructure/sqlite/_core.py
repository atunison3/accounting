import sqlite3


class BaseSqliteRepository:
    def __init__(self, db_file: str):
        self.db_file = db_file

    def _connect(self):
        self.conn = sqlite3.connect(self.db_file)
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
    date TEXT NOT NULL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS transactions (
    transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    amount REAL NOT NULL,
    is_debit BOOLEAN NOT NULL,
    account_id INTEGER NOT NULL,
    entry_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    FOREIGN KEY (account_id) REFERENCES accounts (id),
    FOREIGN KEY (entry_id) REFERENCES entries (id)
);
'''
