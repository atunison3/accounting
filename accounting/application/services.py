from datetime import date
from typing import Any

from accounting.domain.models import (
    Account,
    AccountingTransaction,
    AccountingTransactionDocument,
    Business,
    Document,
    Mileage,
    TransactionEntry,
    TransactionLine,
)


class AccountingService:
    """Application use cases for balanced accounting transactions.

    The service depends on a repository port only. SQLite, HTTP, or another
    adapter can be supplied without changing these use cases.
    """

    def __init__(self, repository: Any) -> None:
        self.repository = repository

    def create_transaction(
        self,
        transaction_date: date,
        description: str,
        lines: list[TransactionLine],
        user_id: int,
        posting_reference: str | None = None,
    ) -> int:
        if len(lines) < 2:
            raise ValueError("A transaction must contain at least two transaction lines.")

        total_debits = sum(line.amount_cents for line in lines if line.is_debit)
        total_credits = sum(line.amount_cents for line in lines if not line.is_debit)
        if total_debits != total_credits:
            raise ValueError(f"Debits and credits must be equal. Debits: {total_debits}, Credits: {total_credits}.")

        transaction = AccountingTransaction(
            transaction_date=transaction_date,
            description=description,
            posting_reference=posting_reference,
            created_by=user_id,
            updated_by=user_id,
        )
        add = getattr(type(self.repository), "add", None)
        if add is None:
            add = self.repository.create_transaction
        else:
            add = self.repository.add
        return add(transaction=transaction, lines=lines, user_id=user_id)

    def list_transactions(  # noqa: PLR0913, PLR0917
        self,
        business_id: int,
        account_number: int | None = None,
        is_debit: bool | None = None,
        min_amount_cents: int | None = None,
        max_amount_cents: int | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[TransactionEntry]:
        return self.repository.search(
            business_id,
            account_number,
            is_debit,
            min_amount_cents,
            max_amount_cents,
            date_from,
            date_to,
        )

    def get_transaction(self, transaction_id: int) -> AccountingTransaction | None:
        get = getattr(type(self.repository), "get_by_id", None)
        return (self.repository.get_by_id if get else self.repository.get_transaction)(transaction_id)

    def get_transaction_lines(self, transaction_id: int) -> list[TransactionLine]:
        get = getattr(type(self.repository), "get_lines", None)
        return (self.repository.get_lines if get else self.repository.get_transaction_lines)(transaction_id)

    def delete_transaction(self, transaction_id: int, user_id: int) -> None:
        if self.get_transaction(transaction_id) is None:
            raise ValueError(f"Transaction {transaction_id} does not exist.")
        delete = getattr(type(self.repository), "delete", None)
        (self.repository.delete if delete else self.repository.delete_transaction)(transaction_id, user_id)


class BusinessService:
    def __init__(self, repository: Any) -> None:
        self.repository = repository

    def create(self, business: Business) -> int:
        return self.repository.add(business)

    def get(self, business_id: int) -> Business | None:
        return self.repository.get_by_id(business_id)

    def list(self) -> list[Business]:
        return self.repository.get_all()


class AccountService:
    def __init__(self, repository: Any) -> None:
        self.repository = repository

    def create(self, account: Account) -> int:
        return self.repository.add(account)

    def get(self, account_id: int) -> Account | None:
        return self.repository.get_by_id(account_id)

    def for_business(self, business_id: int) -> list[Account]:
        return self.repository.get_for_business(business_id)

    def update(self, account_id: int, account: Account, user_id: int) -> None:
        if self.repository.get_by_id(account_id) is None:
            raise ValueError(f"Account {account_id} does not exist.")
        self.repository.update(account_id, account, user_id)


class MileageService:
    def __init__(self, repository: Any) -> None:
        self.repository = repository

    def record(self, mileage: Mileage) -> int:
        return self.repository.add(mileage)

    def get(self, mileage_id: int) -> Mileage | None:
        return self.repository.get_by_id(mileage_id)


class DocumentService:
    def __init__(self, repository: Any, links: Any | None = None) -> None:
        self.repository = repository
        self.links = links

    def add(self, document: Document) -> int:
        return self.repository.add(document)

    def get(self, document_id: int) -> Document | None:
        return self.repository.get_by_id(document_id)

    def attach_to_transaction(self, transaction_id: int, document_id: int, user_id: int) -> int:
        if self.links is None:
            raise ValueError("A transaction-document repository is required to create links.")
        return self.links.add(
            AccountingTransactionDocument(
                transaction_id=transaction_id,
                document_id=document_id,
                created_by=user_id,
            )
        )
