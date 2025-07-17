from domain.entry import Entry
from repositories.entry_repository import EntryRepository
from infrastructure.sqlite._core import BaseSQLiteRepository


class SQLiteEntryRepository(EntryRepository, BaseSQLiteRepository):

    def __init__(self, db_path: str) -> Entry:
        self.db_path = db_path

    def add(self, entry: Entry):
        with self._connect() as conn:
            cursor = conn.cursor()
            sql = 'INSERT INTO entries (date, description) VALUES (?, ?);'
            cursor.execute(sql, (entry.date, entry.description))
            entry.entry_id = cursor.lastrowid
            conn.commit()
        return entry

    def get_by_id(self, entry_id: int) -> Entry:
        '''Gets an entry by id'''

        with self._connect() as conn:
            cursor = conn.cursor()
            sql = 'SELECT * FROM entries WHERE entry_id = ?;'
            cursor.execute(sql, (entry_id,))
            row = cursor.fetchone()
            if row:
                return Entry(entry_id=row[0], date=row[1], description=row[2])
            return None

    def list_all(self) -> list[Entry]:
        entries = []
        with self._connect() as conn:
            cursor = conn.cursor()
            sql = 'SELECT * FROM entries;'
            cursor.execute(sql)
            for row in cursor.fetchall():
                entries.append(Entry(entry_id=row[0], date=row[1], description=row[2]))
        return entries

    def delete(self, entry_id: int):

        with self._connect() as conn:
            cursor = conn.cursor()
            sql = 'DELETE FROM entries WHERE entry_id = ?;'
            cursor.execute(sql, (entry_id,))
            conn.commit()
