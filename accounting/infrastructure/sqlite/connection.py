from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

SCHEMA_FILE_PATH = Path(__file__).with_name("schema.sql")
DATA_DIR = Path.home() / ".app_data" / "accounting"
DEFAULT_DATABASE_PATH = DATA_DIR / "accounting.db"


def create_connection(db_path: str | Path = DEFAULT_DATABASE_PATH) -> sqlite3.Connection:
    """Create a configured SQLite connection and apply the packaged schema."""
    database_path = Path(db_path)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(database_path, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.executescript(SCHEMA_FILE_PATH.read_text(encoding="utf-8"))
    _remove_legacy_user_credential_column(conn)
    _migrate_transaction_business_id(conn)
    _migrate_transaction_currency_code(conn)
    return conn


def _remove_legacy_user_credential_column(conn: sqlite3.Connection) -> None:
    """Remove the credential column from databases created by older releases."""
    columns = {row[1] for row in conn.execute("PRAGMA table_info(users)")}
    if "password_hash" in columns:
        conn.execute("ALTER TABLE users DROP COLUMN password_hash")


def _migrate_transaction_business_id(conn: sqlite3.Connection) -> None:
    """Add and backfill business ownership for older transactions."""
    columns = {row[1] for row in conn.execute("PRAGMA table_info(accounting_transactions)")}
    if "business_id" not in columns:
        conn.execute("ALTER TABLE accounting_transactions ADD COLUMN business_id INTEGER REFERENCES businesses(id)")
    conn.execute("""
        UPDATE accounting_transactions
        SET business_id = (
            SELECT a.business_id
            FROM transaction_lines AS l
            JOIN accounts AS a ON a.id = l.account_id
            WHERE l.transaction_id = accounting_transactions.id
            GROUP BY a.business_id
            HAVING COUNT(DISTINCT a.business_id) = 1
        )
        WHERE business_id IS NULL
        """)


def _migrate_transaction_currency_code(conn: sqlite3.Connection) -> None:
    """Add the default currency to databases created by older releases."""
    columns = {row[1] for row in conn.execute("PRAGMA table_info(accounting_transactions)")}
    if "currency_code" not in columns:
        conn.execute("ALTER TABLE accounting_transactions ADD COLUMN currency_code TEXT NOT NULL DEFAULT 'USD'")


@contextmanager
def get_connection(db_path: str | Path = DEFAULT_DATABASE_PATH) -> Iterator[sqlite3.Connection]:
    """Yield a connection and commit on success or roll back on failure."""
    conn = create_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
