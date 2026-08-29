# Usage

`accounting` is currently used as an importable Python package; it does not provide a configured command-line command.

## Create and validate models

```python
from datetime import date

from accounting.domain.models import (
    Account,
    AccountType,
    AccountingTransaction,
    TransactionLine,
    TransactionWithLines,
)

account = Account(
    business_id=1,
    account_number=110,
    account_name="Cash",
    account_type=AccountType.ASSET,
)

transaction = TransactionWithLines(
    transaction_date=date(2026, 8, 7),
    description="Cash sale",
    lines=[
        TransactionLine(transaction_id=0, account_id=account.id or 100, amount_cents=15000, is_debit=True),
        TransactionLine(transaction_id=0, account_id=400, amount_cents=15000, is_debit=False),
    ],
)

assert transaction.is_balanced
```

Amounts are integer cents. A `TransactionWithLines` rejects non-balanced non-empty lines, and `AccountingService.create_transaction` also requires at least two lines.

## Use the application service

```python
from accounting.application.services import AccountingService

service = AccountingService(repository=my_repository)
transaction_id = service.create_transaction(
    transaction_date=date(2026, 8, 7),
    description="Cash sale",
    lines=transaction.lines,
    user_id=1,
    posting_reference="INV-1001",
)
```

The service delegates persistence to the supplied repository. See the [package reference](../documentation/package.md) for the required method names and signatures.
