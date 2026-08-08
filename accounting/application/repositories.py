# accounting/application/repositories.py

from accounting.domain.models import AccountingTransaction, TransactionLine, Account, User, Business


class TransactionRepository:
    def add(self, transaction: AccountingTransaction, lines: list[TransactionLine], user_id: int) -> int:
        raise NotImplementedError

    def get_by_id(self, transaction_id: int) -> AccountingTransaction | None:
        raise NotImplementedError

    def get_lines(self, transaction_id: int) -> list[TransactionLine]:
        raise NotImplementedError

    def delete(self, transaction_id: int, user_id: int) -> None:
        raise NotImplementedError


class AccountRepository:
    def add(self, account: Account) -> int:
        raise NotImplementedError

    def get_by_id(self, account_id: int) -> Account | None:
        raise NotImplementedError

    def get_by_number(self, business_id: int, account_number: int) -> Account | None:
        raise NotImplementedError

    def get_for_business(self, business_id: int) -> list[Account]:
        raise NotImplementedError


class UserRepository:
    def add(self, user: User) -> int:
        raise NotImplementedError

    def get_by_id(self, user_id: int) -> User | None:
        raise NotImplementedError

    def get_by_username(self, username: str) -> User | None:
        raise NotImplementedError


class BusinessRepository:
    def add(self, business: Business) -> int:
        raise NotImplementedError

    def get_by_id(self, business_id: int) -> Business | None:
        raise NotImplementedError

    def get_all(self) -> list[Business]:
        raise NotImplementedError
