# accounting

`accounting` is a Python accounting application with a FastAPI website, JSON API,
SQLite ledger, and optional MCP tools for AI clients such as Pi. Its domain models
and services build on the accounting concepts described in *College Accounting*
by Jeffery Slater.

## What is it?

The package models businesses, users, accounts, accounting transactions, transaction lines, and mileage records. It uses Pydantic validation for data integrity and an application service for balanced transaction creation and retrieval.

## Why use it?

The website provides transaction entry/history, account management, receipt
attachments, mileage, and financial reports. Domain models and application services
remain separate from presentation and storage, with SQLite repository implementations
supplied at the application boundary.

## Features

- Server-rendered FastAPI/Jinja2 website and browser-facing JSON endpoints.
- Account editing and confirmed transaction soft deletion with deleted-history visibility.
- Receipt/document attachments, mileage tracking, and PDF financial reports.
- SQLite persistence with audit triggers and transaction rollback.
- Authenticated MCP transaction tools for remote clients.
- Pydantic models for core accounting entities.
- Asset, liability, equity, revenue, and expense account types.
- Debit and credit amounts represented in cents.
- Validation that transaction debits equal credits.
- Soft-delete metadata and display models for account reporting.
- Repository interfaces for businesses, users, accounts, and transactions.

## Quick Example

```python
from datetime import date

from accounting.application.services import AccountingService
from accounting.domain.models import TransactionLine

service = AccountingService(repository=my_repository)
transaction_id = service.create_transaction(
    transaction_date=date(2026, 8, 7),
    description="Cash sale",
    lines=[
        TransactionLine(transaction_id=0, account_id=100, amount_cents=15000, is_debit=True),
        TransactionLine(transaction_id=0, account_id=400, amount_cents=15000, is_debit=False),
    ],
    user_id=1,
)
```

`my_repository` must provide the methods used by `AccountingService`. The package
includes `SqliteTransactionRepository` in `accounting.infrastructure.sqlite.repositories`;
the website/API and MCP adapters wire services to these concrete repositories.

## Documentation

- [Installation](getting-started/installation.md)
- [Usage](getting-started/usage.md)
- [Architecture: website, API, SQLite, and MCP](documentation/architecture.md)
- [Package reference](documentation/package.md)

## Contributing

See the [contributor guide](contributing/README.md) for development setup, tests, and quality checks.

## Support the project

If this project helps you, consider buying Andy a coffee. Support is optional and appreciated!

<a href="https://www.buymeacoffee.com/atunison" target="_blank" rel="noopener noreferrer">
  <img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me a Coffee" width="217" height="60" style="max-width: 100%; height: auto;">
</a>
