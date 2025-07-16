from domain.entry import Entry
from repositories.entry_repository import EntryRepository
from infrastructure.sqlite._core import BaseSQLiteRepository


class SQLiteEntryRepository(EntryRepository, BaseSQLiteRepository):

    def __init__(self, db_path: str) -> Entry:
        self.db_path = db_path

    def add(self, entry: Entry):

        cursor = self._connect()

        sql = 'INSERT INTO entries (date, description) VALUES (?, ?);'
        cursor.execute(sql, (entry.date, entry.description))

        # Update the entry's id
        entry.entry_id = cursor.lastrowid

        self._disconnect()

        return entry

    def get_by_id(self, entry_id: int) -> Entry:
        '''Gets an entry by id'''

        cursor = self._connect()

        sql = 'SELECT * FROM entries WHERE entry_id = ?;'
        cursor.execute(sql, (entry_id,))

        entry = None

        if result := cursor.fetchone():
            entry = Entry(entry_id=result[0], date=result[1], description=result[2])

        self._disconnect()

        return entry

    def list_all(self) -> list[Entry]:

        cursor = self._connect()

        sql = 'SELECT * FROM entries;'
        cursor.execute(sql)

        entrys = []
        if results := cursor.fetchall():
            for result in results:
                entry = Entry(entry_id=result[0], date=result[1], description=result[2])
                entrys.append(entry)

        self._disconnect()

        return entrys

    def delete(self, entry_id: int):

        cursor = self._connect()
        sql = 'DELETE FROM entries WHERE entry_id = ?;'
        cursor.execute(sql, (entry_id,))
        self._disconnect()
