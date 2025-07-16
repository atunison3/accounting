from abc import ABC, abstractmethod

from domain.transaction import Transaction


class TransactionRepository(ABC):
    """Abstract base class for transaction repositories."""

    @abstractmethod
    def add(self, transaction: Transaction) -> None:
        """Add a transaction to the repository."""
        pass

    @abstractmethod
    def get_by_id(self, transaction_id: int) -> Transaction:
        """Retrieve a transaction by its ID."""
        pass

    @abstractmethod
    def list_all(self) -> list[Transaction]:
        """Return all transactions."""
        pass

    @abstractmethod
    def delete(self, transaction_id: int) -> None:
        """Delete a transaction by its ID."""
        pass
