from domain.account import Account
from repositories.account_repository import AccountRepository
from infrastructure.sqlite._core import BaseSQLiteRepository


class SQLiteAccountRepository(AccountRepository, BaseSQLiteRepository):

    def __init__(self, db_path: str):
        self.db_path = db_path

    def add(self, account: Account) -> Account:
        with self._connect() as conn:
            cursor = conn.cursor()
            sql = 'INSERT INTO Account (Number, Title, Type_) VALUES (?, ?, ?);'
            cursor.execute(sql, (account.number, account.title, account.type_))
            account.id_ = cursor.lastrowid
            conn.commit()
        return account

    def get_by_id(self, id_: int) -> Account:
        '''Gets an account by id'''

        with self._connect() as conn:
            cursor = conn.cursor()
            sql = '''
            SELECT * 
            FROM Account
            WHERE 
                ID = ?;
            '''
            cursor.execute(sql, (id_,))
            row = cursor.fetchone()
            if row:
                return Account(
                    id_=row[0], number=row[1], title=row[2], type_=row[3], is_active=row[4]
                )
            return None

    def list_all_active(self) -> list[Account]:

        accounts = []
        with self._connect() as conn:
            cursor = conn.cursor()
            sql = '''
            SELECT * 
            FROM Account
            WHERE IsActive = 1;
            '''
            cursor.execute(sql)
            for row in cursor.fetchall():
                accounts.append(
                    Account(
                        id_=row[0],
                        number=row[1],
                        title=row[2],
                        type_=row[3],
                        is_active=row[4],
                    )
                )
        return accounts

    def delete(self, id_: int):

        with self._connect() as conn:
            cursor = conn.cursor()
            sql = 'DELETE FROM Account WHERE ID = ?;'
            cursor.execute(sql, (id_,))
            conn.commit()
