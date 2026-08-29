from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

SCHEMA_FILE_PATH = Path(__file__).with_name("schema.sql")


def create_connection(db_path: str | Path = "accounting.db") -> sqlite3.Connection:
    """Create a configured SQLite connection and apply the packaged schema."""
    conn = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.executescript(SCHEMA_FILE_PATH.read_text(encoding="utf-8"))
    return conn


@contextmanager
def get_connection(db_path: str | Path = "accounting.db") -> Iterator[sqlite3.Connection]:
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
