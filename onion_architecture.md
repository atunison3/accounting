# Onion Architecture

Onion architecture organizes an application into layers arranged from the center outward. The central idea is that dependencies point inward: outer layers may depend on inner layers, but inner layers should not depend on outer layers.

## 1. Domain Layer

The domain layer is the center of the application. It contains the core business concepts and business rules.

For an accounting application, this layer could contain models such as:

```python
class User:
    ...

class Business:
    ...

class Account:
    ...

class AccountingTransaction:
    ...

class TransactionLine:
    ...

class Mileage:
    ...
```

It may also contain domain rules such as:

- Debits must equal credits.
- Account types must be valid.
- A transaction must contain at least two transaction lines.
- Deleted records should not appear in normal business operations.
- An account must belong to a business.
- A transaction line must reference an account and a transaction.

The domain layer should not depend on SQLite, FastAPI, a command-line interface, or other external technologies.

## 2. Application Layer

The application layer contains the application's use cases. It coordinates domain objects and defines the steps required to perform business operations.

Examples include:

```python
class AccountingService:
    def create_transaction(self, transaction):
        ...

    def get_general_ledger(self, account_id):
        ...

    def delete_transaction(self, transaction_id, user_id):
        ...
```

The application layer may also define repository interfaces:

```python
from typing import Protocol


class TransactionRepository(Protocol):
    def add(
        self,
        transaction: AccountingTransaction,
    ) -> int:
        ...

    def get_by_id(
        self,
        transaction_id: int,
    ) -> AccountingTransaction | None:
        ...
```

The application layer decides what must happen, but it should not contain SQLite queries or other infrastructure-specific details.

## 3. Infrastructure Layer

The infrastructure layer contains technical implementations for interfaces defined by the inner layers.

Examples include:

- SQLite repositories
- Database connection management
- Schema creation
- File storage
- Email services
- Logging
- External API clients

For example:

```python
class SQLiteTransactionRepository:
    def __init__(
        self,
        connection: sqlite3.Connection,
    ) -> None:
        self.connection = connection

    def add(
        self,
        transaction: AccountingTransaction,
    ) -> int:
        ...
```

The infrastructure layer may depend on the application and domain layers. The domain and application layers should not depend on infrastructure.

## 4. Presentation Layer

The presentation layer is how users or external systems interact with the application.

Examples include:

- Command-line interfaces
- FastAPI routes
- Desktop applications
- Web interfaces
- REST APIs

For example:

```python
def create_transaction_command(args) -> None:
    service.create_transaction(
        transaction_date=args.date,
        description=args.description,
        lines=args.lines,
    )
```

The presentation layer should call application services rather than execute SQL directly.

## Onion Architecture Diagram

```text
                                            ╔══════════════════════════════════════════════════════════════╗
                                            ║                    PRESENTATION LAYER                        ║
                                            ║                                                              ║
                                            ║        CLI · Web UI · REST API · Desktop Interface           ║
                                            ║                                                              ║
                                            ║   ╔══════════════════════════════════════════════════════╗   ║
                                            ║   ║                 INFRASTRUCTURE LAYER                 ║   ║
                                            ║   ║                                                      ║   ║
                                            ║   ║   SQLite · Repositories · Files · Email · Logging    ║   ║
                                            ║   ║                                                      ║   ║
                                            ║   ║   ╔══════════════════════════════════════════════╗   ║   ║
                                            ║   ║   ║              APPLICATION LAYER               ║   ║   ║
                                            ║   ║   ║                                              ║   ║   ║
                                            ║   ║   ║  Use Cases · Services · Repository Protocols ║   ║   ║
                                            ║   ║   ║                                              ║   ║   ║
                                            ║   ║   ║   ╔══════════════════════════════════════╗   ║   ║   ║
                                            ║   ║   ║   ║            DOMAIN LAYER              ║   ║   ║   ║
                                            ║   ║   ║   ║                                      ║   ║   ║   ║
                                            ║   ║   ║   ║  Entities · Value Objects · Rules    ║   ║   ║   ║
                                            ║   ║   ║   ║                                      ║   ║   ║   ║
                                            ║   ║   ║   ║ Account · Transaction · Business     ║   ║   ║   ║
                                            ║   ║   ║   ╚══════════════════════════════════════╝   ║   ║   ║
                                            ║   ║   ╚══════════════════════════════════════════════╝   ║   ║
                                            ║   ╚══════════════════════════════════════════════════════╝   ║
                                            ╚══════════════════════════════════════════════════════════════╝

                                                                Dependencies point inward
                                                                        ↓
                                                        Presentation / Infrastructure
                                                                        ↓
                                                                    Application
                                                                        ↓
                                                                        Domain
```

The nested boxes represent the onion. The domain is at the center, while presentation and infrastructure are on the outside. Source-code dependencies should always point toward the center.

## Dependency Direction

Dependencies point inward:

```text
Presentation
     |
     v
Application
     |
     v
Domain

Infrastructure
     |
     +----> Application
     |
     +----> Domain
```

A more compact representation is:

```text
Presentation ------+
                   +----> Application ----> Domain
Infrastructure ----+
```

The most important rule is:

> Inner layers must not import from outer layers.

For example:

- Domain models should not import `sqlite3`.
- Application services should not execute SQL.
- Infrastructure may import domain models and application interfaces.
- Presentation may import application services.

## Project Structure

```text
accounting/
├── domain/
│   ├── models.py
│   ├── enums.py
│   ├── exceptions.py
│   └── services.py
│
├── application/
│   ├── services.py
│   ├── repositories.py
│   └── unit_of_work.py
│
├── infrastructure/
│   ├── database.py
│   ├── sqlite_repositories.py
│   ├── schema.sql
│   └── sqlite_unit_of_work.py
│
├── presentation/
│   ├── cli.py
│   └── formatters.py
│
└── tests/
    ├── unit/
    └── integration/
```

## Suggested Placement for the Accounting Application

### `domain/models.py`

```text
User
Business
Account
AccountingTransaction
TransactionLine
Mileage
```

### `domain/enums.py`

```text
AccountType
```

### `application/repositories.py`

```text
UserRepository
BusinessRepository
AccountRepository
TransactionRepository
MileageRepository
```

### `application/services.py`

```text
AccountingService
MileageService
```

### `infrastructure/database.py`

```text
create_db
get_connection
```

### `infrastructure/sqlite_repositories.py`

```text
SQLiteUserRepository
SQLiteBusinessRepository
SQLiteAccountRepository
SQLiteTransactionRepository
SQLiteMileageRepository
```

### `presentation/cli.py`

```text
Command-line argument handling
Input parsing
Application-service calls
```

### `presentation/formatters.py`

```text
Journal output
Ledger output
Account listings
Error messages
```

## Unit of Work

A unit-of-work abstraction can manage transactions across multiple repositories.

```python
from typing import Protocol


class UnitOfWork(Protocol):
    users: UserRepository
    businesses: BusinessRepository
    accounts: AccountRepository
    transactions: TransactionRepository

    def commit(self) -> None:
        ...

    def rollback(self) -> None:
        ...
```

The SQLite implementation belongs in infrastructure:

```python
class SQLiteUnitOfWork:
    def __enter__(self):
        self.connection = sqlite3.connect(self.db_path)
        self.users = SQLiteUserRepository(self.connection)
        self.businesses = SQLiteBusinessRepository(self.connection)
        self.accounts = SQLiteAccountRepository(self.connection)
        self.transactions = SQLiteTransactionRepository(
            self.connection
        )
        return self

    def commit(self) -> None:
        self.connection.commit()

    def rollback(self) -> None:
        self.connection.rollback()

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        if exc_type is not None:
            self.rollback()

        self.connection.close()
```

An application service can then use it without depending directly on SQLite:

```python
class AccountingService:
    def __init__(self, unit_of_work_factory) -> None:
        self.unit_of_work_factory = unit_of_work_factory

    def create_transaction(
        self,
        transaction: AccountingTransaction,
    ) -> int:
        with self.unit_of_work_factory() as unit_of_work:
            transaction_id = unit_of_work.transactions.add(
                transaction
            )
            unit_of_work.commit()
            return transaction_id
```

## Testing Strategy

Unit tests should focus on domain and application behavior without requiring a real database.

Examples:

- A transaction is balanced.
- Invalid account types are rejected.
- A transaction with unequal debits and credits is rejected.
- Deleted transaction lines are excluded from totals.
- Application services call the expected repositories.

Integration tests should exercise the infrastructure layer with a temporary SQLite database.

Examples:

- `create_db()` creates the expected tables.
- Repository methods insert and retrieve records.
- Foreign-key constraints are enforced.
- Audit fields are populated.
- Soft-deleted rows are excluded from normal queries.

## Summary

The onion architecture layers are:

1. **Domain** — business concepts and rules
2. **Application** — use cases and coordination
3. **Infrastructure** — databases and external technologies
4. **Presentation** — user and system interfaces

The dependency rule is what defines the architecture: dependencies must point inward toward the domain.
