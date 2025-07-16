from domain.account import Account
from repositories.account_repository import AccountRepository
from infrastructure.sqlite._core import BaseSQLiteRepository


class SQLiteAccountRepository(AccountRepository, BaseSQLiteRepository):

    def __init__(self, db_path: str):
        self.db_path = db_path

    def add(self, account: Account) -> Account:

        cursor = self._connect()

        sql = 'INSERT INTO accounts (number, name, type_) VALUES (?, ?, ?);'
        cursor.execute(sql, (account.number, account.name, account.type_))

        # Update the account_id
        account.account_id = cursor.lastrowid

        self._disconnect()

        return account

    def get_by_id(self, account_id: int) -> Account:
        '''Gets an account by id'''

        cursor = self._connect()

        sql = 'SELECT * FROM accounts WHERE account_id = ?;'
        cursor.execute(sql, (account_id,))

        account = None

        if result := cursor.fetchone():
            account = Account(
                account_id=result[0], number=result[1], name=result[2], type_=result[3]
            )

        self._disconnect()

        return account

    def list_all(self) -> list[Account]:

        cursor = self._connect()

        sql = 'SELECT * FROM accounts;'
        cursor.execute(sql)

        accounts = []
        if results := cursor.fetchall():
            for result in results:
                account = Account(
                    account_id=result[0], number=result[1], name=result[2], type_=result[3]
                )
                accounts.append(account)

        self._disconnect()

        return accounts

    def delete(self, account_id: int):

        cursor = self._connect()
        sql = 'DELETE FROM accounts WHERE account_id = ?;'
        cursor.execute(sql, (account_id,))
        self._disconnect()
