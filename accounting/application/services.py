from datetime import date
from typing import Any

from accounting.domain.currency import convert_currency
from accounting.domain.models import (
    Account,
    AccountType,
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

    def create_transaction(  # noqa: PLR0913, PLR0917
        self,
        transaction_date: date,
        description: str,
        lines: list[TransactionLine],
        user_id: int,
        posting_reference: str | None = None,
        business_id: int | None = None,
        currency_code: str = "USD",
    ) -> int:
        if len(lines) < 2:
            raise ValueError("A transaction must contain at least two transaction lines.")

        total_debits = sum(line.amount_cents for line in lines if line.is_debit)
        total_credits = sum(line.amount_cents for line in lines if not line.is_debit)
        if total_debits != total_credits:
            raise ValueError(f"Debits and credits must be equal. Debits: {total_debits}, Credits: {total_credits}.")

        transaction = AccountingTransaction(
            business_id=business_id,
            transaction_date=transaction_date,
            description=description,
            currency_code=currency_code,
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

    def update_transaction(  # noqa: PLR0913, PLR0917
        self,
        transaction_id: int,
        transaction_date: date,
        description: str,
        lines: list[TransactionLine],
        user_id: int,
        posting_reference: str | None = None,
        business_id: int | None = None,
        currency_code: str = "USD",
    ) -> None:
        if len(lines) < 2:
            raise ValueError("A transaction must contain at least two transaction lines.")
        total_debits = sum(line.amount_cents for line in lines if line.is_debit)
        total_credits = sum(line.amount_cents for line in lines if not line.is_debit)
        if total_debits != total_credits:
            raise ValueError("Debits and credits must be equal.")
        if self.get_transaction(transaction_id) is None:
            raise ValueError(f"Transaction {transaction_id} does not exist.")
        transaction = AccountingTransaction(
            id=transaction_id,
            business_id=business_id,
            transaction_date=transaction_date,
            description=description,
            currency_code=currency_code,
            posting_reference=posting_reference,
        )
        self.repository.update(transaction_id, transaction, lines, user_id)

    def list_transactions(  # noqa: PLR0913, PLR0917
        self,
        business_id: int,
        account_number: int | None = None,
        is_debit: bool | None = None,
        min_amount_cents: int | None = None,
        max_amount_cents: int | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        currency_code: str | None = None,
        has_document: bool | None = None,
    ) -> list[TransactionEntry]:
        return self.repository.search(
            business_id,
            account_number,
            is_debit,
            min_amount_cents,
            max_amount_cents,
            date_from,
            date_to,
            currency_code,
            has_document,
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


class AnalyticsService:
    """Build business analytics from repository ports."""

    def __init__(self, transaction_repository: Any, account_repository: Any) -> None:
        self.transaction_repository = transaction_repository
        self.account_repository = account_repository

    def _business_accounts_and_entries(self, business_id: int) -> tuple[dict[int, Account], list[Any]]:
        accounts = {
            account.account_number: account for account in self.account_repository.get_for_business(business_id)
        }
        entries = self.transaction_repository.search(business_id, None, None, None, None, None, None)
        return accounts, entries

    def owner_equity_over_time(self, business_id: int) -> list[dict[str, int | str]]:
        """Return cumulative owner-equity balances converted to USD cents."""
        accounts, entries = self._business_accounts_and_entries(business_id)
        daily_changes: dict[str, int] = {}
        for entry in entries:
            account = accounts.get(entry.account_number)
            if account is None or account.account_type != AccountType.EQUITY:
                continue
            amount = convert_currency(entry.amount_cents, entry.currency_code)
            change = amount if entry.is_debit == account.is_debit else -amount
            day = entry.transaction_date.isoformat()
            daily_changes[day] = daily_changes.get(day, 0) + change
        return self._cumulative_series(daily_changes, "equity_usd_cents")

    def revenue_and_expenses_over_time(self, business_id: int) -> list[dict[str, int | str]]:
        """Return daily revenue and expense activity converted to USD cents."""
        accounts, entries = self._business_accounts_and_entries(business_id)
        daily: dict[str, dict[str, int]] = {}
        for entry in entries:
            account = accounts.get(entry.account_number)
            if account is None or account.account_type not in {AccountType.REVENUE, AccountType.EXPENSE}:
                continue
            day = entry.transaction_date.isoformat()
            values = daily.setdefault(day, {"revenue_usd_cents": 0, "expenses_usd_cents": 0})
            key = "revenue_usd_cents" if account.account_type == AccountType.REVENUE else "expenses_usd_cents"
            amount = convert_currency(entry.amount_cents, entry.currency_code)
            values[key] += amount if entry.is_debit == account.is_debit else -amount
        return [{"date": day, **daily[day]} for day in sorted(daily)]

    def documentless_transaction_percentage(self, business_id: int) -> dict[str, int | float]:
        """Return the percentage of active transactions lacking documents."""
        total, without_documents = self.transaction_repository.document_coverage(business_id)
        percentage = round(without_documents / total * 100, 2) if total else 0.0
        return {
            "transaction_count": total,
            "without_documents": without_documents,
            "percentage": percentage,
        }

    def cash_balance_over_time(self, business_id: int) -> list[dict[str, int | str]]:
        """Return cumulative cash and bank balances converted to USD cents."""
        accounts, entries = self._business_accounts_and_entries(business_id)
        cash_accounts = {
            number
            for number, account in accounts.items()
            if account.account_type == AccountType.ASSET
            and any(word in account.account_name.lower() for word in ("cash", "bank", "checking", "savings"))
        }
        daily_changes: dict[str, int] = {}
        for entry in entries:
            if entry.account_number not in cash_accounts:
                continue
            amount = convert_currency(entry.amount_cents, entry.currency_code)
            day = entry.transaction_date.isoformat()
            daily_changes[day] = daily_changes.get(day, 0) + (amount if entry.is_debit else -amount)
        return self._cumulative_series(daily_changes, "cash_usd_cents")

    @staticmethod
    def _cumulative_series(changes: dict[str, int], value_key: str) -> list[dict[str, int | str]]:
        balance = 0
        points: list[dict[str, int | str]] = []
        for day in sorted(changes):
            balance += changes[day]
            points.append({"date": day, value_key: balance})
        return points


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
