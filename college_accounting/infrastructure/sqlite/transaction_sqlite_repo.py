from domain.transaction import Transaction
from repositories.transaction_repository import TransactionRepository
from infrastructure.sqlite._core import BaseSQLiteRepository


class SQLiteTransactionRepository(TransactionRepository, BaseSQLiteRepository):

    def __init__(self, db_path: str):
        self.db_path = db_path

    def add(self, transaction: Transaction) -> Transaction:

        cursor = self._connect()

        sql = 'INSERT INTO transactions (account_number, entry_id, debit, credit) VALUES (?, ?, ?, ?);'
        cursor.execute(
            sql,
            (
                transaction.account_number,
                transaction.entry_id,
                transaction.debit,
                transaction.credit,
            ),
        )

        # Update the transaction id
        transaction.transaction_id = cursor.lastrowid

        self._disconnect()

        return transaction

    def get_by_id(self, transaction_id: int) -> Transaction:
        '''Gets an transaction by id'''

        cursor = self._connect()

        sql = 'SELECT * FROM transactions WHERE transaction_id = ?;'
        cursor.execute(sql, (transaction_id,))

        transaction = None

        if result := cursor.fetchone():
            transaction = Transaction(
                transaction_id=result[0],
                entry_id=result[1],
                account_number=result[2],
                debit=result[3],
                credit=result[4],
            )

        self._disconnect()

        return transaction

    def list_all(self) -> list[Transaction]:

        cursor = self._connect()

        sql = 'SELECT * FROM transactions;'
        cursor.execute(sql)

        transactions = []
        if results := cursor.fetchall():
            for result in results:
                transaction = Transaction(
                    transaction_id=result[0],
                    entry_id=result[1],
                    account_number=result[2],
                    debit=result[3],
                    credit=result[4],
                )
                transactions.append(transaction)

        self._disconnect()

        return transactions

    def delete(self, transaction_id: int):

        cursor = self._connect()
        sql = 'DELETE FROM transactions WHERE transaction_id = ?;'
        cursor.execute(sql, (transaction_id,))
        self._disconnect()
