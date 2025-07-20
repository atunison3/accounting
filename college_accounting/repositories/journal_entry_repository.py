from abc import ABC, abstractmethod

from domain.journal_entry import JournalEntry


class JournalEntryRepository(ABC):

    @abstractmethod
    def add(self, journal_entry: JournalEntry) -> None:
        '''Add a JournalEntry to the repository.'''
        pass

    @abstractmethod
    def get_by_id(self, id_: int) -> JournalEntry:
        '''Retrieve a JournalEntry by its ID.'''
        pass

    @abstractmethod
    def list_all(self) -> list[JournalEntry]:
        '''Return all JournalEntry.'''
        pass

    @abstractmethod
    def delete(self, id_: int) -> None:
        '''Delete a JournalEntry by its ID.'''
        pass
