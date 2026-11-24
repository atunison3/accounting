"""Run the website against a disposable local ledger copy, never the original.

Usage: python run_local.py
Existing receipt downloads are unavailable in this isolated test environment.
Test uploads and database changes are removed when the server exits normally.
"""

import argparse
import sqlite3
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory

import uvicorn

from accounting.website import routes
from accounting.website.app import create_app


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path.home() / ".app_data/accounting/accounting.db")
    parser.add_argument("--port", type=int, default=8004)
    args = parser.parse_args()
    source = args.source.expanduser().resolve()
    if not source.is_file():
        parser.error(f"Source database does not exist: {source}")
    if not 1024 <= args.port <= 65535:
        parser.error("Port must be between 1024 and 65535")
    with TemporaryDirectory(prefix="accounting-local-test-") as temporary:
        directory = Path(temporary)
        database = directory / "accounting.db"
        with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as original:
            with closing(sqlite3.connect(database)) as copied:
                original.backup(copied)
        database.chmod(0o600)
        # Prevent test uploads from touching the normal document directory.
        routes.DOCUMENTS_DIRECTORY = directory / "documents"
        app = create_app()
        app.state.db_path = database
        print(f"Local test page: http://127.0.0.1:{args.port}/transactions")
        print(f"Disposable database: {database}")
        print("Original database unchanged. Test data is discarded when you stop with Ctrl+C.")
        print("Existing receipt downloads are unavailable; test uploads use temporary storage.")
        uvicorn.run(app, host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
