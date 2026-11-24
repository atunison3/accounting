# Testing and Quality

Run commands from the project root. Use the project's installed development
dependencies and activate its virtual environment first.

macOS / Linux:

```bash
source .venv/bin/activate
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

## Automated tests

Run the full unittest suite:

```shell
python -m unittest discover -s tests -p "test_*.py"
```

Run just the transaction deletion tests:

```shell
python -m unittest discover -s tests -p test_transaction_deletion.py
```

The deletion tests use temporary databases, not your real ledger. They cover
confirmation, soft deletion, audit attribution, deleted-history filtering,
exclusion of superseded transaction lines, retained document links, and redirects.

## Test transaction deletion locally in the browser

### Recommended: one short command

From the project root with the virtual environment activated, run:

```shell
python run_local.py
```

Open **http://127.0.0.1:8004/transactions**. No environment variables or multiline
shell commands are needed. The launcher makes a temporary SQLite backup of your
local ledger and starts the website on localhost. Database changes and test uploads
are isolated and discarded when you stop it with **Ctrl+C**. Existing receipt
downloads are unavailable because their files are not copied into the sandbox.
The original local database and the Ubuntu server remain unchanged.

If needed, select another port with `python run_local.py --port 8005`, or another
existing source database with `python run_local.py --source /path/to/accounting.db`.
Then follow the acceptance checklist in step 4 below.

### Alternative: manual environment-variable setup

This runs the current local code with a **disposable copy of your local database**.
It does not connect to or modify your Ubuntu server. The local database may be
older than the server's data, and must already exist at
`~/.app_data/accounting/accounting.db`.

### 1. Choose a temporary database path

Keep the same terminal open for the remaining commands.

macOS / Linux:

```bash
export ACCOUNTING_TEST_DB="$(mktemp -d)/accounting.db"
```

Windows PowerShell:

```powershell
$testDir = Join-Path ([System.IO.Path]::GetTempPath()) ([guid]::NewGuid().ToString())
New-Item -ItemType Directory -Path $testDir | Out-Null
$env:ACCOUNTING_TEST_DB = Join-Path $testDir 'accounting.db'
```

### 2. Copy the local ledger with SQLite backup

The source is opened read-only, and SQLite backup includes committed WAL data.
This command works in both shells:

```shell
python -c 'import os, sqlite3; from pathlib import Path; src=sqlite3.connect((Path.home()/".app_data/accounting/accounting.db").as_uri()+"?mode=ro", uri=True); dst=sqlite3.connect(os.environ["ACCOUNTING_TEST_DB"]); src.backup(dst); dst.close(); src.close()'
```

Stop if it fails; do not start the website against an unintended database. The
copy contains private financial data—keep it out of Git and shared folders.

### 3. Start the local website on port 8004

```shell
python -c 'import os, uvicorn; from accounting.website.app import create_app; app=create_app(); app.state.db_path=os.environ["ACCOUNTING_TEST_DB"]; uvicorn.run(app, host="127.0.0.1", port=8004)'
```

`ACCOUNTING_TEST_DB` is used by this test command to set `app.state.db_path`; it is
not a general application environment setting. Run the full command above rather
than a plain Uvicorn command, which would use the default local ledger.

Open **http://127.0.0.1:8004/transactions**.

### 4. Verify the acceptance criteria

1. Select a business and a date range containing transactions; click **Apply filters**.
2. Click **Edit** on a transaction and find the **Delete transaction** section.
3. Enter an existing active user ID and check the confirmation checkbox.
4. Click **Delete transaction**. In the **Please confirm** prompt, choose **Cancel**.
   Verify that the transaction remains unchanged.
5. Repeat and approve the prompt. The transaction should disappear from the active list.
6. Set **History → Include deleted transactions** and click **Apply filters**.
7. Verify the entry is marked **Deleted**, has a deletion timestamp/user, and offers
   no Edit action. Its original date, amounts, and account lines remain visible.
8. Switch back to **Active transactions only**. The deleted entry should disappear again.

Keep the transaction's date within the selected range when checking history.
The table loads Tabulator from a public CDN, so browser internet access is required.

**Storage limitation:** this procedure isolates only the database. Uploaded files
still use the normal local document directory. Do not upload or modify receipts
while using this test instance. No Ubuntu data is changed by this local setup.

### 5. Stop the test server

Press **Ctrl+C** in its terminal. Restart the command to pick up Python code changes;
this test command does not enable automatic reload. When finished, remove only the
disposable directory you created, not `~/.app_data/accounting`.

## Shared quality checks

On macOS/Linux, run the same hook configuration used by CI:

```bash
python -m pre_commit run --all-files --show-diff-on-failure
```

The hooks run Black, Ruff, mypy, Bandit, and unittest. Black and whitespace hooks
can change files; review and re-stage those changes, then rerun until all hooks pass.
Tools run through `.venv/bin/python` to avoid stale console-script paths.

CI installs pinned dependencies from `requirements.txt`, creates `.venv`, and runs
this same pre-commit configuration. The hook executable paths are POSIX-specific.
On Windows, use WSL for hook parity; the tests and browser workflow above can also
run directly in PowerShell.
