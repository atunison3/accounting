from abc import ABC, abstractmethod

from domain.ledger_transaction import LedgerTransaction


class LedgerTransactionRepository(ABC):
    '''Abstract base class for ledger transaction repositories.'''

    @abstractmethod
    def add(self, ledger_transaction: LedgerTransaction) -> None:
        '''Add a ledger transaction to the repository.'''
        pass

    @abstractmethod
    def get_by_id(self, id_: int) -> LedgerTransaction:
        '''Retrieve a ledger transaction by its ID.'''
        pass

    @abstractmethod
    def list_all(self) -> list[LedgerTransaction]:
        '''Return all ledger transactions.'''
        pass

    @abstractmethod
    def delete(self, id_: int) -> None:
        '''Delete a ledger transaction by its ID.'''
        pass
