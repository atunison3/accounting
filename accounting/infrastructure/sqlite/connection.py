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
    return conn


def _remove_legacy_user_credential_column(conn: sqlite3.Connection) -> None:
    """Remove the credential column from databases created by older releases."""
    columns = {row[1] for row in conn.execute("PRAGMA table_info(users)")}
    if "password_hash" in columns:
        conn.execute("ALTER TABLE users DROP COLUMN password_hash")


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
