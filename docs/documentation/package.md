# Package Reference

## `accounting.domain.models`

The domain models are Pydantic `BaseModel` classes. `DatabaseModel` enables attribute-based construction, validates assignment, and provides common database/audit fields (`id`, timestamps, user IDs, and soft-delete state).

### `AccountType`

A string enum with the values `Asset`, `Liability`, `Equity`, `Revenue`, and `Expense`.

### `User`

```python
User(username: str, first_name: str, last_name: str, email: EmailStr, is_active: bool = True)
```

Provides `full_name`, and inherits `is_deleted` and audit fields from `DatabaseModel`.

### `Business`

```python
Business(title: str, tax_id: str | None = None, is_business_active: bool = True, established: int | None = None)
```

`established`, when supplied, must be a four-digit year.

### `Account`

```python
Account(business_id: int, account_number: int, account_name: str, account_type: AccountType, description: str | None = None, is_account_active: bool = True)
```

Account numbers must be positive and account names must not be empty.

### `AccountingTransaction`

```python
AccountingTransaction(transaction_date: date, description: str, posting_reference: str | None = None)
```

### `TransactionLine`

```python
TransactionLine(transaction_id: int, account_id: int, amount_cents: int, is_debit: bool)
```

Amounts must be non-negative integer cents.

### `TransactionWithLines`

Extends `AccountingTransaction` with `lines`. It exposes `total_debits_cents`, `total_credits_cents`, and `is_balanced`. A non-empty set of lines must balance.

### `Mileage`

```python
Mileage(business_id: int, mileage_date: date, tenth_miles: int, explanation: str, start_tenth_miles: int | None = None, end_tenth_miles: int | None = None)
```

Mileage values cannot be negative. When both odometer values are present, `tenth_miles` must equal `end_tenth_miles - start_tenth_miles`.

### Display models

`TAccountDisplay`, `BalanceColumnItem`, and `BalanceColumnDisplay` hold data used to render account reports.

## `accounting.application.services`

### `AccountingService`

```python
AccountingService(repository)
```

`create_transaction(transaction_date, description, lines, user_id, posting_reference=None) -> int` requires at least two lines and equal debit and credit totals, then calls the repository's `create_transaction` method.

`get_transaction(transaction_id) -> AccountingTransaction | None` delegates to `repository.get_transaction`.

`get_transaction_lines(transaction_id) -> list[TransactionLine]` delegates to `repository.get_transaction_lines`.

`delete_transaction(transaction_id, user_id) -> None` raises `ValueError` when the transaction does not exist; otherwise it delegates to `repository.delete_transaction`.

## `accounting.application.repositories`

The repository classes are intentionally minimal interfaces whose methods raise `NotImplementedError`:

- `TransactionRepository`: `add`, `get_by_id`, `get_lines`, `delete`
- `AccountRepository`: `add`, `get_by_id`, `get_by_number`, `get_for_business`
- `UserRepository`: `add`, `get_by_id`, `get_by_username`
- `BusinessRepository`: `add`, `get_by_id`, `get_all`
