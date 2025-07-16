from domain.transaction import Transaction
from repositories.transaction_repository import TransactionRepository
from infrastructure.sqlite._core import BaseSqliteRepository


class SQLiteTransactionRepository(TransactionRepository, BaseSqliteRepository):

    def __init__(self, db_file: str):
        self.db_file = db_file

    def add(self, transaction: Transaction):

        cursor = self._connect()

        sql = 'INSERT INTO transctions (entry_id, account_id, debit, credit) VALUES (?, ?, ?, ?);'
        cursor.execute(sql, (transaction.entry_id, transaction.account_id, transaction.debit, transaction.credit))

        self._disconnect()

    def get_by_id(self, transaction_id: int) -> Transaction:
        '''Gets an transaction by id'''

        cursor = self._connect()

        sql = 'SELECT * FROM transctions WHERE transaction_id = ?;'
        cursor.execute(sql, (transaction_id,))

        transaction = None

        if result := cursor.fetchone():
            transaction = Transaction(transaction_id=result[0], entry_id=result[1], account_id=result[2], debit=result[3], credit=result[4])

        self._disconnect()

        return transaction

    def list_all(self) -> list[Transaction]:

        cursor = self._connect()

        sql = 'SELECT * FROM transctions;'
        cursor.execute(sql)

        transactions = []
        if results := cursor.fetchall():
            for result in results:
                transaction = Transaction(transaction_id=result[0], entry_id=result[1], account_id=result[2], debit=result[3], credit=result[4])
                transactions.append(transaction)

        self._disconnect()

        return transactions

    def delete(self, transaction_id: int):

        cursor = self._connect()
        sql = 'DELETE FROM transctions WHERE transaction_id = ?;'
        cursor.execute(sql, (transaction_id,))
        self._disconnect()
