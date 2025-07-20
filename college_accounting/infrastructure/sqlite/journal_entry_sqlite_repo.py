from domain.journal_entry import JournalEntry
from repositories.journal_entry_repository import JournalEntryRepository
from infrastructure.sqlite._core import BaseSQLiteRepository


class SQLiteJournalEntryRepository(JournalEntryRepository, BaseSQLiteRepository):

    def __init__(self, db_path: str) -> JournalEntry:
        self.db_path = db_path

    def add(self, journal_entry: JournalEntry):
        with self._connect() as conn:
            cursor = conn.cursor()
            sql = 'INSERT INTO Journal (Date, Description) VALUES (?, ?);'
            cursor.execute(sql, (journal_entry.date, journal_entry.description))
            journal_entry.id_ = cursor.lastrowid
            conn.commit()
        return journal_entry

    def get_by_id(self, id_: int) -> JournalEntry:
        '''Gets an entry by id'''

        with self._connect() as conn:
            cursor = conn.cursor()
            sql = 'SELECT * FROM Journal WHERE ID = ?;'
            cursor.execute(sql, (id_,))
            row = cursor.fetchone()
            if row:
                return JournalEntry(id_=row[0], date=row[1], description=row[2])
            return None

    def list_all(self) -> list[JournalEntry]:
        journal_entries = []
        with self._connect() as conn:
            cursor = conn.cursor()
            sql = 'SELECT * FROM Journal;'
            cursor.execute(sql)
            for row in cursor.fetchall():
                journal_entries.append(JournalEntry(id_=row[0], date=row[1], description=row[2]))
        return journal_entries

    def delete(self, id_: int):

        with self._connect() as conn:
            cursor = conn.cursor()
            sql = 'DELETE FROM Journal WHERE ID = ?;'
            cursor.execute(sql, (id_,))
            conn.commit()
