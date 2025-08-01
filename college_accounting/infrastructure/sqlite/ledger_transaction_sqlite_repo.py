from domain.ledger_transaction import LedgerTransaction
from repositories.ledger_transaction_repository import LedgerTransactionRepository
from infrastructure.sqlite._core import BaseSQLiteRepository


class SQLiteLedgerTransactionRepository(LedgerTransactionRepository, BaseSQLiteRepository):

    def __init__(self, db_path: str):
        self.db_path = db_path

    def add(self, ledger_transaction: LedgerTransaction) -> LedgerTransaction:
        with self._connect() as conn:
            cursor = conn.cursor()
            sql = '''
                INSERT INTO Ledger (AccountNumber, EntryID, TransactionAmount)
                VALUES (?, ?, ?);
            '''
            cursor.execute(
                sql,
                (
                    ledger_transaction.account_number,
                    ledger_transaction.entry_id,
                    ledger_transaction.transaction_amount,
                ),
            )
            ledger_transaction.id_ = cursor.lastrowid
            conn.commit()
        return ledger_transaction

    def get_by_id(self, id_: int) -> LedgerTransaction:
        '''Gets an transaction by id'''

        with self._connect() as conn:
            cursor = conn.cursor()
            sql = '''
            CREATE VIEW LedgerWithBalance AS
            SELECT
                ID,
                EntryID,
                AccountNumber,
                TransactionAmount,
                SUM(TransactionAmount) OVER (
                    PARTITION BY AccountNumber
                    ORDER BY Date, ID
                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                ) AS RunningBalance
            FROM Ledger
            WHERE ID = ?;
            '''
            cursor.execute(sql, (id_,))
            row = cursor.fetchone()
            if row:
                return LedgerTransaction(
                    id_=row[0],
                    entry_id=row[1],
                    account_number=row[2],
                    transaction_amount=row[3],
                    running_balance=row[4],
                )
            return None

    def list_all(self) -> list[LedgerTransaction]:

        transactions = []
        with self._connect() as conn:
            cursor = conn.cursor()
            sql = '''
                CREATE VIEW LedgerWithBalance AS 
                SELECT
                    l.ID,
                    l.EntryID,
                    j.Date,
                    j.Description,
                    l.AccountNumber,
                    l.TransactionAmount,
                    SUM(l.TransactionAmount) OVER (
                        PARTITION BY l.AccountNumber
                        ORDER BY j.Date, l.ID
                        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                    ) AS RunningBalance
                FROM Ledger l
                JOIN Journal j ON j.ID = l.EntryID;
            '''
            sql = '''
                SELECT l.EntryID FROM Ledger l
                LEFT JOIN Journal j ON j.ID = l.EntryID
                WHERE j.ID IS NULL;
            '''
            cursor.execute(sql)
            for row in cursor.fetchall():
                transactions.append(
                    LedgerTransaction(
                        id_=row[0],
                        entry_id=row[1],
                        account_number=row[2],
                        transaction_amount=row[3],
                        # running_balance=0
                        running_balance=row[4],
                    )
                )
        return transactions

    def delete(self, id_: int):

        with self._connect() as conn:
            cursor = conn.cursor()
            sql = 'DELETE FROM Ledger WHERE ID = ?;'
            cursor.execute(sql, (id_,))
            conn.commit()
