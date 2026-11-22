"""Validate copied attachments and relocate live paths, without importing the app.

Run with the application stopped. Default is a dry run; --apply creates a
SQLite backup before modifying paths. Audit history remains unchanged.
"""

import argparse
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path.home() / ".app_data/accounting")
    parser.add_argument("--old-root", type=Path, required=True, help="Original documents directory")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    database = args.data_dir.resolve() / "accounting.db"
    new_root = args.data_dir.resolve() / "documents"
    old_root = args.old_root
    if not old_root.is_absolute():
        parser.error("--old-root must be absolute")
    if not database.is_file():
        parser.error(f"Database not found: {database}")
    connection = sqlite3.connect(database.as_uri() + "?mode=rw", uri=True)
    try:
        integrity = connection.execute("PRAGMA integrity_check").fetchall()
        if integrity != [("ok",)]:
            raise RuntimeError(f"Integrity check failed: {integrity}")
        changes = []
        for document_id, stored_path in connection.execute("SELECT id, file_path FROM documents"):
            original = Path(stored_path)
            if original.is_relative_to(new_root):
                destination = original.resolve()
            else:
                destination = (new_root / original.relative_to(old_root)).resolve()
            if not destination.is_relative_to(new_root) or not destination.is_file():
                raise RuntimeError(f"Missing or unsafe attachment for document {document_id}: {destination}")
            if str(destination) != stored_path:
                changes.append((str(destination), document_id))
        print(f"Validated attachments; {len(changes)} document paths need relocation.")
        if not args.apply or not changes:
            return
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        backup = database.with_name(f"accounting.before-relocation-{stamp}.db")
        with sqlite3.connect(backup) as target:
            connection.backup(target)
        backup.chmod(0o600)
        print(f"Backup: {backup}")
        with connection:
            connection.executemany("UPDATE documents SET file_path = ? WHERE id = ?", changes)
        print("Relocation complete. Existing audit history was retained.")
    finally:
        connection.close()


if __name__ == "__main__":
    main()
