# Architecture

Accounting is a Python application with a **FastAPI website and JSON API**, a
**SQLite ledger**, and an optional **MCP server for AI clients such as Pi**.
It uses an onion-style separation of domain, application, and infrastructure
code, with presentation adapters responsible for wiring them together.

## System overview

```text
Browser
  | HTML forms, page requests, and JavaScript fetch calls
  v
Uvicorn: accounting.main:app
  +-- Website routers -> Jinja2 templates + static CSS + browser JavaScript
  +-- JSON API routes -> validated request/response models
  |                                   |
  +---------- application services ---+
  |                                   |
  +---------- SQLite repositories ----+
                                      |
Pi / another MCP client               v
  | HTTP over SSH tunnel/HTTPS     accounting.db
  v                                   ^
accounting_server.server               |
  +-- bearer authentication           |
  +-- MCP transaction/lookup tools ----+
      via application services and SQLite repositories

Receipt files -> documents/ on disk; metadata and links -> accounting.db
```

The website/API and MCP are separate processes using the **same server-side data**.
The MCP server does not proxy requests through the website. Neither requires a
copy of the ledger on the client's computer.

## Source layout and responsibilities

| Location | Responsibility |
| --- | --- |
| `accounting/domain/models.py` | Pydantic entities, account types, transaction lines, audit metadata, and reporting models |
| `accounting/domain/currency.py` | Currency conversion helpers |
| `accounting/application/repositories.py` | Repository interfaces |
| `accounting/application/services.py` | Transaction creation/update/deletion, balancing rules, analytics, and other application services |
| `accounting/application/income_statement.py` | Income-statement calculations |
| `accounting/infrastructure/sqlite/` | Concrete repositories, connection handling, schema, triggers, and migrations |
| `accounting/main.py` | Combined website/API application factory, API endpoints, health check, and request logging |
| `accounting/website/` | Browser-facing routers, standalone website factory, Jinja2 templates, CSS, and PDF rendering |
| `accounting_server/server.py` | Authenticated MCP transport and accounting tools |
| `deploy/` | Tagged archive deployment, systemd configuration, and initial data relocation |
| `run_local.py` | Disposable local website test environment |

Domain and application modules do not depend on FastAPI or SQLite. Application
services accept supplied repository objects. The outer adapters select concrete
SQLite repositories. In practice, website/API handlers use services for accounting
use cases and also call repositories directly for lookups and some CRUD operations;
this is not a framework-enforced separation where every request passes through a service.

## Website and API entry points

### Combined application: `accounting.main:app`

This is the deployed website service's entry point. Its `create_app(db_path=...)`:

- Stores the database path in `app.state.db_path`.
- Mounts `/static` from `accounting/website/static`.
- Includes the website and income-statement routers.
- Registers JSON endpoints for users, businesses, accounts, and transactions.
- Provides `/health` and FastAPI's generated `/docs` API documentation.
- Adds request logging with rotating log files.

The HTML website and JSON API coexist in this application. For example,
`GET /transactions` renders the browser dashboard, while `POST /transactions`
creates a transaction through the JSON API. The dashboard obtains its table data
from `GET /api/transactions`.

### Standalone website: `accounting.website.app:app`

This factory mounts the same templates/static assets and website routers without
the extra API endpoints, `/health`, or logging middleware registered by
`accounting.main`. The website routers still include their own `/api/...` endpoints
for browser tables and charts. Both factories support an application-specific
database path through `app.state.db_path`.

`run_local.py` uses the standalone factory with a temporary database backup and
an isolated document directory. It binds to localhost on port **8004** by default.
See [local browser testing](../contributing/testing.md).

## Browser presentation

`accounting/website/routes.py` handles most pages and form submissions.
`accounting/website/income_statement.py` supplies the income-statement routes.
Jinja2 templates extend `templates/base.html`, which provides shared navigation,
layout, and CSS. Paths to templates and static assets are derived from the package,
not the process's working directory.

| Page/route | Purpose |
| --- | --- |
| `/`, `/about` | Home and application information |
| `/signup` | Create an accounting user; this is **not** a login/authentication flow |
| `/dashboard` | Workspace for entering businesses, accounts, transactions, and mileage |
| `/transactions` | Filterable transaction-line history, including an optional deleted view |
| `/transactions/{id}/edit` | Edit a journal entry, attach documents, or confirm deletion |
| `/chart-of-accounts` | Business account list with normal balances, status, and edit links |
| `/accounts/{id}/edit` | Edit account details, normal balance, and active status |
| `/documents/upload` | Upload receipt/document files and link them to transactions or mileage |
| `/transactions/{id}/documents` | List documents attached to an active transaction |
| `/mileage` | Mileage records, filters, summaries, and travel documents |
| `/analytics`, `/balance-sheet`, `/income-statement` | Financial dashboards and reports |

The transaction table uses **Tabulator**, loaded from a public CDN, and JavaScript
`fetch` calls to `/api/accounts` and `/api/transactions`. Filters are preserved in
the page's query string. The site is server-rendered with browser enhancements,
not a React application or a Node-based frontend build.

PDF exports use **ReportLab**. Chart of accounts, balance sheet, income statement,
and mileage reports have PDF routes. Some presentation/PDF construction remains
in the website layer; application services supply the underlying calculations.

## Transaction flows

### Create and update

1. A form, JSON API request, or MCP tool call supplies a header and debit/credit lines.
2. The presentation adapter parses dates, account identifiers, currency, amounts,
   and audit-user information. Browser forms convert decimal amounts to integer cents.
3. `AccountingService` checks that there are at least two lines and total debits
   equal total credits.
4. `SqliteTransactionRepository` writes the header and lines within a database transaction.
5. Successful calls commit; failed calls roll back. SQL constraints enforce referential
   integrity, and triggers retain audit history for supported changes.

Updating a transaction replaces its active lines: old lines are soft-deleted and
new lines inserted. Adapters have additional, differing validation. For example,
MCP requires active accounts from the selected business, positive integer-cent
amounts, and a revision match before updating. Do not assume those MCP-specific
protections are implemented identically in every browser/API endpoint.

### Delete and view history

The browser's edit page includes a separate deletion form, an explicit confirmation
checkbox, and a **Please confirm** browser prompt. `POST /transactions/{id}/delete`
requires confirmation and an active audit user before invoking the deletion service.

Deletion is **soft deletion**, not removal from SQLite. The repository stamps the
header and its current lines with `deleted_at` and `deleted_by`. Document files,
links, and audit history remain intact. Default transaction queries exclude deleted
headers; normal reports continue to use active transactions.

Selecting **History → Include deleted transactions** sends `include_deleted=true`
to the history endpoint. Results include deletion timestamps and user IDs; the UI
marks deleted entries read-only and removes Edit/Attach actions. Historical results
show the lines deleted with the header, not every obsolete line from previous edits.
This is deleted-transaction visibility, **not a full audit-log browser or restore UI**.

## Persistence and files

Default data layout, relative to the account running the server:

```text
~/.app_data/accounting/
  accounting.db
  accounting.db-wal / accounting.db-shm  (when SQLite WAL is active)
  documents/                           (uploaded files, grouped by business)
  logs/accounting.log                  (combined application's rotating log)
```

`connection.py` creates directories as needed, enables SQLite foreign keys and WAL,
applies the packaged `schema.sql` and compatibility migrations, and supplies a
context manager that commits or rolls back and closes each connection.
Repositories use parameterized SQL. SQLite provides concurrent readers but still
serializes writers; this deployment is a single-host application, not a distributed
database cluster.

Receipt contents are files, not database blobs. SQLite stores document metadata,
absolute file paths, and links to transactions/mileage. Downloads check that a
resolved path is within the configured documents directory. Initial migration to
a different machine must relocate stored document paths. Copying only the database
is not a complete backup: preserve the document directory too.

The database path can be overridden for tests, but that does **not** automatically
relocate document storage or logs. `run_local.py` explicitly isolates document
storage as well; existing receipts are not copied into that sandbox and cannot be
downloaded there. This application's current upload workflow does not automatically
OCR receipts, call Ollama/OpenAI, or post AI-generated entries.

## MCP adapter

`accounting_server/server.py` provides a separate **Streamable HTTP** endpoint at
`/mcp`, defaulting to loopback port **8003**. It exposes business/account lookups,
transaction reads/date-range searches, and transaction create/update/soft-delete tools.
It currently has no account-creation tool or receipt-upload tool.

A private bearer token is required. Requests are protected by an allowed-Host
check, and browser-origin requests are rejected. A token grants ledger-wide access;
it is not per-business authorization. Writes use a configured existing active user
for audit attribution rather than an agent-supplied user ID.

The MCP `Ledger` opens the **existing** SQLite database in read/write mode without
creating or migrating it. Each call has its own connection/transaction; writes
acquire `BEGIN IMMEDIATE`. Deploy/migrate the website first. Updates and deletes
require a revision derived from the header and active lines to detect stale writes.
Creation is not idempotent: after a timeout, inspect the ledger before retrying.

Pi connects over an SSH tunnel or a properly secured HTTPS endpoint. Tool
annotations and instructions request approval for mutations, but are not an
enforced human-approval system. See the repository's `deploy/MCP.md` for setup.

## Deployment and security boundaries

The recommended archive workflow exports an exact local Git tag and copies it to
Ubuntu; the server needs no Git checkout. Each release gets its own directory and
Python virtual environment. systemd runs the website/API and, optionally, the MCP
service as the configured non-root user. Data stays outside release directories.
Real hostnames, addresses, ports, and audit-user settings belong in ignored
`deploy/*.local.toml` files. Tokens are generated/stored privately on the server.

Update deployments stop the managed writers, back up existing server data, install
the selected release, and restart/health-check the services. Independent writers
must also be stopped by the operator. There is no automatic rollback; schema changes
may require restoring matching code and data together. See `deploy/README.md` and
`deploy/MCP.md` in the repository for operational commands.

**The website and JSON API do not currently provide an authentication boundary.**
User IDs identify audit attribution, not proof of identity. Keep them on a trusted
network or behind appropriate access controls. MCP authentication does not protect
the website. Plain HTTP does not encrypt receipts, ledger data, or bearer tokens;
use SSH/VPN/TLS where required. Do not expose these services directly to the internet.

## Tests and related documentation

Tests use Python `unittest`, temporary SQLite databases, and FastAPI/Starlette
`TestClient`. They cover application/domain behavior, repositories, website routes,
account editing, transaction deletion/history, and MCP validation/authentication.
The shared pre-commit configuration also runs formatting, lint, type, and security checks.

- [Testing and local browser workflow](../contributing/testing.md)
- [Package reference](package.md)
- [Onion architecture concepts](../onion_architecture.md) — conceptual examples,
  not the authoritative current source layout
