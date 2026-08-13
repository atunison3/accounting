# accounting/infrastructure/sqlite/connection.py
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterator
from contextlib import contextmanager

# Get the directory where connection.py is located
CURRENT_DIR = Path(__file__).resolve().parent
SCHEMA_FILE_PATH = CURRENT_DIR / "schema.sql"
SCHEMA = """
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS users (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    username    TEXT    NOT NULL UNIQUE,
    first_name  TEXT    NOT NULL,
    last_name   TEXT    NOT NULL,
    email       TEXT    NOT NULL UNIQUE,
    is_active   INTEGER NOT NULL DEFAULT 1,

    created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at  TEXT,

    CHECK (
        email LIKE '%_@_%._%' AND
        LENGTH(email) - LENGTH(REPLACE(email, '@', '')) = 1
    )
);

CREATE TABLE IF NOT EXISTS businesses (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    title               TEXT    NOT NULL,
    tax_id              TEXT,
    is_business_active  INTEGER NOT NULL DEFAULT 1,
    established         TEXT,
    tax_year_end_month  INTEGER NOT NULL DEFAULT 12,

    created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by  INTEGER NOT NULL,
    updated_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by  INTEGER,
    deleted_at  TEXT,
    deleted_by  INTEGER,

    CHECK (
        (deleted_at IS NULL AND deleted_by IS NULL) OR
        (deleted_at IS NOT NULL AND deleted_by IS NOT NULL)
    ),
    CHECK (
        tax_id IS NULL OR (
            length(tax_id) = 10
            AND substr(tax_id, 3, 1) = '-'
            AND substr(tax_id, 1, 2) GLOB '[0-9][0-9]'
            AND substr(tax_id, 4, 7) GLOB '[0-9][0-9][0-9][0-9][0-9][0-9][0-9]'
        )
    ),
    CHECK (
        tax_year_end_month BETWEEN 1 and 12
    ),
    CHECK (
        established IS NULL
        OR (
            established GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
            AND date(established) IS NOT NULL
        )
    ),

    FOREIGN KEY (created_by) REFERENCES users(id),
    FOREIGN KEY (updated_by) REFERENCES users(id),
    FOREIGN KEY (deleted_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS accounts (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    business_id       INTEGER NOT NULL REFERENCES businesses(id),
    account_number    INTEGER NOT NULL,
    account_name      TEXT    NOT NULL,
    account_type      TEXT    NOT NULL,
    description       TEXT,
    is_account_active INTEGER NOT NULL DEFAULT 1,

    created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by  INTEGER,
    updated_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by  INTEGER,
    deleted_at  TEXT,
    deleted_by  INTEGER,

    CHECK (
        account_type in ('Asset', 'Liability', 'Equity', 'Revenue', 'Expense')
    ),

    CHECK (
        (deleted_at IS NULL AND deleted_by IS NULL) OR
        (deleted_at IS NOT NULL AND deleted_by IS NOT NULL)
    ),

    FOREIGN KEY (created_by) REFERENCES users(id),
    FOREIGN KEY (updated_by) REFERENCES users(id),
    FOREIGN KEY (deleted_by) REFERENCES users(id)

    UNIQUE (business_id, account_number)
);

CREATE TABLE IF NOT EXISTS accounting_transactions (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_date   TEXT    NOT NULL,
    description        TEXT    NOT NULL,
    posting_reference  TEXT,

    created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by  INTEGER,
    updated_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by  INTEGER,
    deleted_at  TEXT,
    deleted_by  INTEGER

    CHECK (
        (deleted_at IS NULL AND deleted_by IS NULL) OR
        (deleted_at IS NOT NULL AND deleted_by IS NOT NULL)
    ),

    FOREIGN KEY (created_by) REFERENCES users(id),
    FOREIGN KEY (updated_by) REFERENCES users(id),
    FOREIGN KEY (deleted_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS transaction_lines (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id  INTEGER NOT NULL,
    account_id      INTEGER NOT NULL,
    amount_cents    INTEGER NOT NULL CHECK (amount_cents >= 0),
    is_debit        INTEGER NOT NULL,

    created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by  INTEGER,
    updated_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by  INTEGER,
    deleted_at  TEXT,
    deleted_by  INTEGER

    CHECK (
        (deleted_at IS NULL AND deleted_by IS NULL) OR
        (deleted_at IS NOT NULL AND deleted_by IS NOT NULL)
    ),

    FOREIGN KEY (created_by) REFERENCES users(id),
    FOREIGN KEY (updated_by) REFERENCES users(id),
    FOREIGN KEY (deleted_by) REFERENCES users(id),
    FOREIGN KEY (transaction_id) REFERENCES accounting_transactions(id),
    FOREIGN KEY (account_id) REFERENCES accounts(id)
);

CREATE TABLE IF NOT EXISTS accounts_history (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,

    account_id        INTEGER NOT NULL REFERENCES accounts(id),

    account_number    INTEGER NOT NULL,
    account_name      TEXT    NOT NULL,
    account_type      TEXT    NOT NULL,
    description       TEXT,
    is_account_active INTEGER NOT NULL DEFAULT 1,

    updated_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by  INTEGER,
    deleted_at  TEXT,
    deleted_by  INTEGER,

    CHECK (
        account_type in ('Asset', 'Liability', 'Equity', 'Revenue', 'Expense')
    ),

    FOREIGN KEY (account_id) REFERENCES accounts(id),
    FOREIGN KEY (updated_by) REFERENCES users(id),
);

CREATE TABLE IF NOT EXISTS AccountingTransactionHistory (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_date   TEXT    NOT NULL,
    description        TEXT    NOT NULL,
    posting_reference  TEXT,

    updated_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by  INTEGER,
    deleted_at  TEXT,
    deleted_by  INTEGER,

    CHECK (
        (deleted_at IS NULL AND deleted_by IS NULL) OR
        (deleted_at IS NOT NULL AND deleted_by IS NOT NULL)
    ),

    FOREIGN KEY (created_by) REFERENCES users(id),
    FOREIGN KEY (updated_by) REFERENCES users(id),
    FOREIGN KEY (deleted_by) REFERENCES users(id)
);




------ Triggers to update updated_at ------

CREATE TRIGGER trg_users_updated
AFTER UPDATE ON users
FOR EACH ROW
BEGIN
    UPDATE users
    SET updated_at = CURRENT_TIMESTAMP
    WHERE id = NEW.id;
END;

CREATE TRIGGER trg_businesses_updated
AFTER UPDATE OF updated_by ON businesses
FOR EACH ROW
BEGIN
    UPDATE businesses
    SET updated_at = CURRENT_TIMESTAMP
    WHERE id = NEW.id;
END;

CREATE TRIGGER trg_accounts_updated
AFTER UPDATE OF updated_by ON accounts
FOR EACH ROW
BEGIN
    UPDATE accounts
    SET updated_at = CURRENT_TIMESTAMP
    WHERE id = NEW.id;
END;

CREATE TRIGGER trg_accounting_transactions_updated
AFTER UPDATE OF updated_by ON accounting_transactions
FOR EACH ROW
BEGIN
    UPDATE accounting_transactions
    SET updated_at = CURRENT_TIMESTAMP
    WHERE id = NEW.id;
END;

CREATE TRIGGER trg_transaction_lines_updated
AFTER UPDATE OF updated_by ON transaction_lines
FOR EACH ROW
BEGIN
    UPDATE transaction_lines
    SET updated_at = CURRENT_TIMESTAMP
    WHERE id = NEW.id;
END;

------ Tigger for copying history ------

CREATE TRIGGER trg_account_audit_update
BEFORE UPDATE ON accounts
FOR EACH ROW
BEGIN
    INSERT INTO accounts_history (
        account_id,
        account_number,
        account_name,
        account_type,
        description,
        is_account_active,
        updated_at,
        updated_by
    )
    VALUES (
        OLD.id,
        OLD.account_number,
        OLD.account_name,
        OLD.account_type,
        OLD.description,
        OLD.is_account_active,
        CURRENT_TIMESTAMP,
        NEW.updated_by
    );

------ Indexing ------

CREATE INDEX IF NOT EXISTS idx_accounts_business
    ON accounts(business_id) WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_transactions_date
    ON accounting_transactions(transaction_date) WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_lines_transaction
    ON transaction_lines(transaction_id) WHERE deleted_at IS NULL;
"""


def create_connection(db_path: str | Path = "accounting.db") -> sqlite3.Connection:
    """Create a configured SQLite connection and ensure schema exists."""
    conn = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    schema = SCHEMA_FILE_PATH.read_text(encoding="utf-8")
    conn.executescript(schema)
    return conn


@contextmanager
def get_connection(db_path: str | Path = "accounting.db") -> Iterator[sqlite3.Connection]:
    """Context manager that yields a connection and commits/rollbacks automatically."""
    conn = create_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
