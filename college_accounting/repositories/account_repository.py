from abc import ABC, abstractmethod

from domain.account import Account


class AccountRepository(ABC):

    @abstractmethod
    def add(self, account: Account) -> None:
        '''Add a account to the repository.'''
        pass

    @abstractmethod
    def get_by_id(self, account_id: int) -> Account:
        '''Retrieve a account by its ID.'''
        pass

    @abstractmethod
    def list_all(self) -> list[Account]:
        '''Return all accounts.'''
        pass

    @abstractmethod
    def delete(self, account_id: int) -> None:
        '''Delete a account by its ID.'''
        pass
