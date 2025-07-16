from abc import ABC, abstractmethod

from domain.entry import Entry


class EntryRepository(ABC):

    @abstractmethod
    def add(self, entry: Entry) -> None:
        """Add a Entry to the repository."""
        pass

    @abstractmethod
    def get_by_id(self, entry_id: int) -> Entry:
        """Retrieve a Entry by its ID."""
        pass

    @abstractmethod
    def list_all(self) -> list[Entry]:
        """Return all Entry."""
        pass

    @abstractmethod
    def delete(self, entry_id: int) -> None:
        """Delete a Entry by its ID."""
        pass
