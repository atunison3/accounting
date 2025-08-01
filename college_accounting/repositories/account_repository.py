from abc import ABC, abstractmethod

from domain.account import Account


class AccountRepository(ABC):

    @abstractmethod
    def add(self, account: Account) -> None:
        '''Add a account to the repository.'''
        pass

    @abstractmethod
    def get_by_id(self, id_: int) -> Account:
        '''Retrieve a account by its ID.'''
        pass

    @abstractmethod
    def list_all_active(self) -> list[Account]:
        '''Return all accounts.'''
        pass

    @abstractmethod
    def delete(self, id_: int) -> None:
        '''Delete a account by its ID.'''
        pass
