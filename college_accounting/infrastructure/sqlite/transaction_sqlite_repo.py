from domain.transaction import Transaction
from repositories.transaction_repository import TransactionRepository
from infrastructure.sqlite._core import BaseSQLiteRepository


class SQLiteTransactionRepository(TransactionRepository, BaseSQLiteRepository):

    def __init__(self, db_path: str):
        self.db_path = db_path

    def add(self, transaction: Transaction) -> Transaction:
        with self._connect() as conn:
            cursor = conn.cursor()
            sql = '''
                INSERT INTO transactions (account_number, entry_id, debit, credit)
                VALUES (?, ?, ?, ?);
            '''
            cursor.execute(
                sql,
                (
                    transaction.account_number,
                    transaction.entry_id,
                    transaction.debit,
                    transaction.credit,
                ),
            )
            transaction.transaction_id = cursor.lastrowid
            conn.commit()
        return transaction

    def get_by_id(self, transaction_id: int) -> Transaction:
        '''Gets an transaction by id'''

        with self._connect() as conn:
            cursor = conn.cursor()
            sql = 'SELECT * FROM transactions WHERE transaction_id = ?;'
            cursor.execute(sql, (transaction_id,))
            row = cursor.fetchone()
            if row:
                return Transaction(
                    transaction_id=row[0],
                    entry_id=row[1],
                    account_number=row[2],
                    debit=row[3],
                    credit=row[4],
                )
            return None

    def list_all(self) -> list[Transaction]:

        transactions = []
        with self._connect() as conn:
            cursor = conn.cursor()
            sql = 'SELECT * FROM transactions;'
            cursor.execute(sql)
            for row in cursor.fetchall():
                transactions.append(
                    Transaction(
                        transaction_id=row[0],
                        entry_id=row[1],
                        account_number=row[2],
                        debit=row[3],
                        credit=row[4],
                    )
                )
        return transactions

    def delete(self, transaction_id: int):

        with self._connect() as conn:
            cursor = conn.cursor()
            sql = 'DELETE FROM transactions WHERE transaction_id = ?;'
            cursor.execute(sql, (transaction_id,))
            conn.commit()
