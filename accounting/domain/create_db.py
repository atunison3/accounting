import sqlite3
from pathlib import Path

sqls = [
    """
    CREATE TABLE IF NOT EXISTS Accounts (
        Id INTEGER PRIMARY KEY,
        AccountNumber TEXT NOT NULL UNIQUE,
        AccountName TEXT NOT NULL UNIQUE,
        AccountType TEXT NOT NULL
            CHECK (
                AccountType IN (
                    'Asset',
                    'Liability',
                    'Equity',
                    'Revenue',
                    'Expense'
                )
            ),
        Description TEXT,
        IsAccountActive INTEGER NOT NULL DEFAULT 1
            CHECK (IsAccountActive in (0, 1)),
        CreatedAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );""",
    """CREATE TABLE IF NOT EXISTS Transactions (
        Id INTEGER PRIMARY KEY,
        TransactionDate TEXT NOT NULL,
        Description TEXT NOT NULL,
        PostingReference TEXT,
        CreatedAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        IsDeleted INTEGER NOT NULL DEFAULT 0
            CHECK (IsDeleted IN (0, 1))
    );""",
    """CREATE TABLE IF NOT EXISTS JournalEntries (
        Id INTEGER PRIMARY KEY,
        TransactionId INTEGER NOT NULL,
        AccountId INTEGER NOT NULL,
        AmountCents INTEGER NOT NULL
            CHECK (AmountCents >= 0),
        IsDebit INTEGER NOT NULL
            CHECK (IsDebit in (0, 1)),
        FOREIGN KEY (TransactionId) REFERENCES Transactions(Id),
        FOREIGN KEY (AccountId) REFERENCES Accounts(Id)
    )
    """,
]

db_folder = Path().home() / "app_data/accounting"
db_folder.mkdir(parents=True, exist_ok=True)


db_path = db_folder / "database.db"

for sql in sqls:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute(sql)
        conn.commit()
        print("Successfully created database!")
    except Exception as e:
        print(f"Failed to create database: {e}")
    conn.close()
