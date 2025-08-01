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
    IsActive BOOL NOT NULL DEFAULT 1, 
    IsDebitNorm BOOL NOT NULL DEFAULT 0
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

CREATE VIEW IF NOT EXISTS GeneralLedger AS 
WITH Running AS (
    SELECT
        l.ID,
        a.Title,
        l.AccountNumber,
        j.Date,
        j.Description,
        l.TransactionAmount,
        a.IsDebitNorm,

        -- Calculate adjusted running balance (positive means "normal")
        SUM(
            CASE 
                WHEN a.IsDebitNorm = 1 THEN l.TransactionAmount
                ELSE -1 * l.TransactionAmount
            END
        ) OVER (
            PARTITION BY l.AccountNumber
            ORDER BY j.Date, l.ID
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS AdjustedRunningBalance

    FROM Ledger l
    JOIN Journal j ON j.ID = l.EntryID
    JOIN Account a ON a.Number = l.AccountNumber
)

SELECT
    r.ID,
    r.Title,
    r.AccountNumber,
    r.Date,
    r.Description,
    
    -- Debit column for current transaction
    CASE 
        WHEN r.IsDebitNorm = 1 AND r.TransactionAmount > 0 THEN r.TransactionAmount
        WHEN r.IsDebitNorm = 0 AND r.TransactionAmount < 0 THEN ABS(r.TransactionAmount)
        ELSE 0
    END AS Debit,

    -- Credit column for current transaction
    CASE 
        WHEN r.IsDebitNorm = 0 AND r.TransactionAmount > 0 THEN r.TransactionAmount
        WHEN r.IsDebitNorm = 1 AND r.TransactionAmount < 0 THEN ABS(r.TransactionAmount)
        ELSE 0
    END AS Credit,

    -- Running balance split into debit/credit columns
    CASE 
        WHEN r.IsDebitNorm = 1 AND r.AdjustedRunningBalance >= 0 THEN r.AdjustedRunningBalance
        WHEN r.IsDebitNorm = 0 AND r.AdjustedRunningBalance < 0 THEN ABS(r.AdjustedRunningBalance)
        ELSE 0
    END AS BalanceDebit,

    CASE 
        WHEN r.IsDebitNorm = 0 AND r.AdjustedRunningBalance >= 0 THEN r.AdjustedRunningBalance
        WHEN r.IsDebitNorm = 1 AND r.AdjustedRunningBalance < 0 THEN ABS(r.AdjustedRunningBalance)
        ELSE 0
    END AS BalanceCredit

FROM Running r;
'''
