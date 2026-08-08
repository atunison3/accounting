# accounting/infrastructure/sqlite/connection.py
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterator
from contextlib import contextmanager

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

    created_at  TEXT,
    created_by  INTEGER,
    updated_at  TEXT,
    updated_by  INTEGER,
    deleted_at  TEXT,
    deleted_by  INTEGER
);

CREATE TABLE IF NOT EXISTS businesses (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    title               TEXT    NOT NULL,
    tax_id              TEXT,
    is_business_active  INTEGER NOT NULL DEFAULT 1,
    established         INTEGER,

    created_at  TEXT,
    created_by  INTEGER,
    updated_at  TEXT,
    updated_by  INTEGER,
    deleted_at  TEXT,
    deleted_by  INTEGER
);

CREATE TABLE IF NOT EXISTS accounts (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    business_id      INTEGER NOT NULL REFERENCES businesses(id),
    account_number   INTEGER NOT NULL,
    account_name     TEXT    NOT NULL,
    account_type     TEXT    NOT NULL,
    description      TEXT,
    is_account_active INTEGER NOT NULL DEFAULT 1,

    created_at  TEXT,
    created_by  INTEGER,
    updated_at  TEXT,
    updated_by  INTEGER,
    deleted_at  TEXT,
    deleted_by  INTEGER,

    UNIQUE (business_id, account_number)
);

CREATE TABLE IF NOT EXISTS transactions (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_date   TEXT    NOT NULL,
    description        TEXT    NOT NULL,
    posting_reference  TEXT,

    created_at  TEXT,
    created_by  INTEGER,
    updated_at  TEXT,
    updated_by  INTEGER,
    deleted_at  TEXT,
    deleted_by  INTEGER
);

CREATE TABLE IF NOT EXISTS transaction_lines (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id  INTEGER NOT NULL REFERENCES transactions(id),
    account_id      INTEGER NOT NULL REFERENCES accounts(id),
    amount_cents    INTEGER NOT NULL CHECK (amount_cents >= 0),
    is_debit        INTEGER NOT NULL,

    created_at  TEXT,
    created_by  INTEGER,
    updated_at  TEXT,
    updated_by  INTEGER,
    deleted_at  TEXT,
    deleted_by  INTEGER
);

CREATE INDEX IF NOT EXISTS idx_accounts_business
    ON accounts(business_id) WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_transactions_date
    ON transactions(transaction_date) WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_lines_transaction
    ON transaction_lines(transaction_id) WHERE deleted_at IS NULL;
"""


def create_connection(db_path: str | Path = "accounting.db") -> sqlite3.Connection:
    """Create a configured SQLite connection and ensure schema exists."""
    conn = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
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
