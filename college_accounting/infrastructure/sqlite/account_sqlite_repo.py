from domain.account import Account
from repositories.account_repository import AccountRepository
from infrastructure.sqlite._core import BaseSqliteRepository


class SQLiteAccountRepository(AccountRepository, BaseSqliteRepository):

    def __init__(self, db_file: str):
        self.db_file = db_file

    def add(self, account: Account):

        cursor = self._connect()

        sql = 'INSERT INTO accounts (number, name, type_) VALUES (?, ?, ?);'
        cursor.execute(sql, (account.number, account.name, account.type_))

        self._disconnect()

    def get_by_id(self, account_id: int) -> Account:
        '''Gets an account by id'''

        cursor = self._connect()

        sql = 'SELECT * FROM accounts WHERE account_id = ?;'
        cursor.execute(sql, (account_id,))

        account = None

        if result := cursor.fetchone():
            account = Account(account_id=result[0], number=result[1], name=result[2], type_=result[3])

        self._disconnect()

        return account

    def list_all(self) -> list[Account]:

        cursor = self._connect()

        sql = 'SELECT * FROM accounts;'
        cursor.execute(sql)

        accounts = []
        if results := cursor.fetchall():
            for result in results:
                account = Account(account_id=result[0], number=result[1], name=result[2], type_=result[3])
                accounts.append(account)

        self._disconnect()

        return accounts

    def delete(self, account_id: int):

        cursor = self._connect()
        sql = 'DELETE FROM accounts WHERE account_id = ?;'
        cursor.execute(sql, (account_id,))
        self._disconnect()
