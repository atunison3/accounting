import sqlite3
from pathlib import Path

SQL = """
    CREATE TABLE IF NOT EXISTS User (
        Id INTEGER PRIMARY KEY, 
        Username TEXT NOT NULL,
        FirstName TEXT NOT NULL,
        LastName TEXT NOT NULL,
        Email TEXT NOT NULL,
        IsActive INTEGER NOT NULL DEFAULT 1
            CHECK (IsActive in (0, 1)),
        CreatedAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UpdatedAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        DeletedAt TEXT
    );
    CREATE TABLE IF NOT EXISTS Business (
        Id INTEGER PRIMARY KEY,
        Title TEXT NOT NULL,
        TaxId TEXT,
        IsBusinessActive INTEGER NOT NULL DEFAULT 1
            CHECK (IsBusinessActive in (0, 1)),
        Established INTEGER,
        CreatedAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CreatedBy INTEGER NOT NULL,
        UpdatedAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UpdatedBy INTEGER NOT NULL,
        DeletedAy TEXT,
        DeletedBy INTEGER,

        FOREIGN KEY (CreatedBy) REFERENCES User(Id),
        FOREIGN KEY (UpdatedBy) REFERENCES User(Id),
        FOREIGN KEY (DeletedBy) REFERENCES User(Id)

    );
    CREATE TABLE IF NOT EXISTS Account (
        Id INTEGER PRIMARY KEY,
        BusinessId INTEGER NOT NULL,
        AccountNumber INTEGER NOT NULL,
        AccountName TEXT NOT NULL,
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
        CreatedAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CreatedBy INTEGER NOT NULL,
        UpdatedAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UpdatedBy INTEGER NOT NULL,
        DeletedAt TEXT,
        DeletedBy INTEGER,
        FOREIGN KEY (CreatedBy) REFERENCES User(Id),
        FOREIGN KEY (UpdatedBy) REFERENCES User(Id),
        FOREIGN KEY (DeletedBy) REFERENCES User(Id),
        FOREIGN KEY (BusinessId) REFERENCES Business(Id)
    );
    CREATE TABLE IF NOT EXISTS AccountingTransaction (
        Id INTEGER PRIMARY KEY,
        TransactionDate TEXT NOT NULL,
        Description TEXT NOT NULL,
        PostingReference TEXT,
        CreatedAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CreatedBy INTEGER NOT NULL,
        UpdatedAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UpdatedBy INTEGER NOT NULL,
        DeletedAt TEXT,
        DeletedBy INTEGER,

        FOREIGN KEY (CreatedBy) REFERENCES User(Id),
        FOREIGN KEY (UpdatedBy) REFERENCES User(Id),
        FOREIGN KEY (DeletedBy) REFERENCES User(Id)
    );
    CREATE TABLE IF NOT EXISTS TransactionLine (
        Id INTEGER PRIMARY KEY,
        TransactionId INTEGER NOT NULL,
        AccountId INTEGER NOT NULL,
        AmountCents INTEGER NOT NULL
            CHECK (AmountCents >= 0),
        IsDebit INTEGER NOT NULL
            CHECK (IsDebit in (0, 1)),
        CreatedAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CreatedBy INTEGER NOT NULL,
        UpdatedAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UpdatedBy INTEGER NOT NULL,
        DeletedAt TEXT,
        DeletedBy INTEGER,

        FOREIGN KEY (CreatedBy) REFERENCES User(Id),
        FOREIGN KEY (UpdatedBy) REFERENCES User(Id),
        FOREIGN KEY (DeletedBy) REFERENCES User(Id),
        FOREIGN KEY (TransactionId) REFERENCES AccountingTransactions(Id)
    );
    """

USERS = [("rbobby", "Ricky", "Bobby", "rbobby@example.com")]


def create_db(db_path: Path) -> None:
    """Creates the database"""

    # Verify path exists
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_path) as conn:
        conn.executescript(SQL)
        conn.commit()
