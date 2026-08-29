# accounting

`accounting` is a Python package containing domain models and application services for the accounting exercises described in *College Accounting* by Jeffery Slater.

## What is it?

The package models businesses, users, accounts, accounting transactions, transaction lines, and mileage records. It uses Pydantic validation for data integrity and an application service for balanced transaction creation and retrieval.

## Why use it?

The package provides a small, typed foundation for accounting software without coupling the domain models to a database or user interface. Repository interfaces allow storage implementations to be supplied separately.

## Features

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

`my_repository` must provide the methods used by `AccountingService`; the repository implementations are not currently included in the package.

## Documentation

- [Installation](getting-started/installation.md)
- [Usage](getting-started/usage.md)
- [Package reference](documentation/package.md)

## Contributing

See the [contributor guide](contributing/README.md) for development setup, tests, and quality checks.
