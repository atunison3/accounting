from domain.account import Account
from repositories.account_repository import AccountRepository
from infrastructure.sqlite._core import BaseSQLiteRepository


class SQLiteAccountRepository(AccountRepository, BaseSQLiteRepository):

    def __init__(self, db_path: str):
        self.db_path = db_path

    def add(self, account: Account) -> Account:
        with self._connect() as conn:
            cursor = conn.cursor()
            sql = 'INSERT INTO accounts (number, name, type_) VALUES (?, ?, ?);'
            cursor.execute(sql, (account.number, account.name, account.type_))
            account.account_id = cursor.lastrowid
            conn.commit()
        return account

    def get_by_id(self, account_id: int) -> Account:
        '''Gets an account by id'''

        with self._connect() as conn:
            cursor = conn.cursor()
            sql = 'SELECT * FROM accounts WHERE account_id = ?;'
            cursor.execute(sql, (account_id,))
            row = cursor.fetchone()
            if row:
                return Account(account_id=row[0], number=row[1], name=row[2], type_=row[3])
            return None

    def list_all(self) -> list[Account]:

        accounts = []
        with self._connect() as conn:
            cursor = conn.cursor()
            sql = 'SELECT * FROM accounts;'
            cursor.execute(sql)
            for row in cursor.fetchall():
                accounts.append(
                    Account(account_id=row[0], number=row[1], name=row[2], type_=row[3])
                )
        return accounts

    def delete(self, account_id: int):

        with self._connect() as conn:
            cursor = conn.cursor()
            sql = 'DELETE FROM accounts WHERE account_id = ?;'
            cursor.execute(sql, (account_id,))
            conn.commit()
