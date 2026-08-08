import sqlite3
import tempfile
import unittest
from pathlib import Path

from accounting.database.create_db import create_db

USERS = [
    ("jsmith", "Justin", "Smith", "jsmith@example.com"),
]
BUSINESSES = [
    ("J. T. Smith CPA Services", 1978, 1, 1),
]
ACCOUNTS = [
    (1, 110, "Cash", "Asset", "Cash available to the business", 1, 1),
    (1, 210, "Accounts Payable", "Liability", "Amounts owed to vendors and suppliers", 1, 1),
    (1, 310, "J. T. Smith Capital", "Equity", "Owner capital invested in the business", 1, 1),
    (1, 410, "Fees Earned", "Revenue", "Revenue earned from CPA services", 1, 1),
    (1, 510, "Expenses", "Expense", "General business expenses", 1, 1),
]
ACCOUNTING_TRANSACTIONS = [
    ("1978-03-01", "Paid the rent for March", None, 1, 1),
    ("1978-03-01", "Paid February's telephone bill", None, 1, 1),
    ("1978-03-02", "Received cash for services from A. B. Smith", None, 1, 1),
    ("1978-03-02", "Paid February's electric bill", None, 1, 1),
    ("1978-03-03", "Received cash for services from Bill Tooley", None, 1, 1),
    ("1978-03-03", "Paid the secretary's weekly salary", None, 1, 1),
    ("1978-03-04", "Paid dues to the AICPA", None, 1, 1),
    ("1978-03-04", "Paid business license fee", None, 1, 1),
]
TRANSACTION_LINES = [
    # TransactionId, AccountId, AmountCents, IsDebit, CreatedBy, UpdatedBy
    (1, 5, 17_500, 1, 1, 1),  # Paid rent - debiting expense
    (1, 1, 17_500, 0, 1, 1),  # Paid rent - crediting cash
    (2, 5, 3_700, 1, 1, 1),
    (2, 1, 3_700, 0, 1, 1),
    (3, 1, 2_500, 1, 1, 1),
    (3, 4, 2_500, 0, 1, 1),
    (4, 5, 1_700, 1, 1, 1),
    (4, 1, 1_700, 0, 1, 1),
    (5, 1, 4_000, 1, 1, 1),
    (5, 4, 4_000, 0, 1, 1),
    (6, 5, 7_500, 1, 1, 1),
    (6, 1, 7_500, 0, 1, 1),
    (7, 5, 2_500, 1, 1, 1),
    (7, 1, 2_500, 0, 1, 1),
    (8, 5, 10_000, 1, 1, 1),
    (8, 1, 10_000, 0, 1, 1),
]


class TestCreateDatabase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_directory = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_directory.name) / "accounting" / "database-test.db"

        # Remove an existing test database, if present.
        self.db_path.unlink(missing_ok=True)

        create_db(self.db_path)

        # Add the user
        with sqlite3.connect(self.db_path) as conn:
            # Users
            conn.executemany(
                """
                INSERT INTO User (
                    Username,
                    FirstName,
                    LastName,
                    Email
                )
                VALUES (?, ?, ?, ?)
                """,
                USERS,
            )

            # Add the business
            conn.executemany(
                """
                INSERT INTO Business (
                    Title,
                    Established,
                    CreatedBy,
                    UpdatedBy
                )
                VALUES (?, ?, ?, ?)
                """,
                BUSINESSES,
            )

            # Add the accounts
            conn.executemany(
                """
                INSERT INTO Account (
                    BusinessId,
                    AccountNumber,
                    AccountName,
                    AccountType,
                    Description,
                    CreatedBy,
                    UpdatedBy
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                ACCOUNTS,
            )

            # Add the accounting transactions
            conn.executemany(
                """
                INSERT INTO AccountingTransaction (
                    TransactionDate,
                    Description,
                    PostingReference,
                    CreatedBy,
                    UpdatedBy
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                ACCOUNTING_TRANSACTIONS,
            )

            # Add the transaction lines
            conn.executemany(
                """
                INSERT INTO TransactionLine (
                    TransactionId,
                    AccountId,
                    AmountCents,
                    IsDebit,
                    CreatedBy,
                    UpdatedBy
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                TRANSACTION_LINES,
            )

            conn.commit()

    def tearDown(self) -> None:
        self.temp_directory.cleanup()

    def test_create_db_creates_database_file(self) -> None:
        self.assertTrue(self.db_path.exists())
        self.assertTrue(self.db_path.is_file())

    def test_create_db_creates_expected_table(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                  AND name = ?
                """,
                ("Business",),
            ).fetchone()

        self.assertIsNotNone(row)

    def test_create_db_can_be_called_again(self) -> None:
        create_db(self.db_path)

        self.assertTrue(self.db_path.exists())

    def test_user_exists(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            user = conn.execute(
                """
                SELECT
                    Id,
                    Username,
                    FirstName,
                    LastName,
                    Email,
                    IsActive,
                    CreatedAt,
                    UpdatedAt,
                    DeletedAt
                FROM User
                WHERE Username = ?
                """,
                ("jsmith",),
            ).fetchone()

        self.assertIsNotNone(user)

        assert user is not None  # nosec: B101

        self.assertEqual(user["Username"], "jsmith")
        self.assertEqual(user["FirstName"], "Justin")
        self.assertEqual(user["LastName"], "Smith")
        self.assertEqual(user["Email"], "jsmith@example.com")
        self.assertEqual(user["IsActive"], 1)
        self.assertIsNotNone(user["CreatedAt"])
        self.assertIsNotNone(user["UpdatedAt"])
        self.assertIsNone(user["DeletedAt"])

    def test_business_exists(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            business = conn.execute(
                """
                SELECT
                    Business.Id,
                    Business.Title,
                    Business.TaxId,
                    Business.IsBusinessActive,
                    Business.Established,
                    Business.CreatedBy,
                    Business.UpdatedBy,
                    User.FirstName,
                    User.LastName
                FROM Business
                JOIN User
                    ON Business.CreatedBy = User.Id
                WHERE Business.Title = ?
                """,
                ("J. T. Smith CPA Services",),
            ).fetchone()

        self.assertIsNotNone(business)
        assert business is not None  # nosec: B101

        self.assertEqual(business["Title"], "J. T. Smith CPA Services")
        self.assertIsNone(business["TaxId"])
        self.assertEqual(business["IsBusinessActive"], 1)
        self.assertEqual(business["Established"], 1978)
        self.assertEqual(business["FirstName"], "Justin")
        self.assertEqual(business["LastName"], "Smith")
        self.assertEqual(business["CreatedBy"], 1)
        self.assertEqual(business["UpdatedBy"], 1)

    def test_accounts_exist(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            accounts = conn.execute(
                """
                SELECT
                    BusinessId,
                    AccountNumber,
                    AccountName,
                    AccountType,
                    Description,
                    IsAccountActive,
                    CreatedAt,
                    CreatedBy,
                    UpdatedAt,
                    UpdatedBy,
                    DeletedAt,
                    DeletedBy
                FROM Account
                WHERE BusinessId = ?
                ORDER BY AccountNumber
                """,
                (1,),
            ).fetchall()

        self.assertEqual(len(accounts), 5)

        expected_accounts = [
            (110, "Cash", "Asset"),
            (210, "Accounts Payable", "Liability"),
            (310, "J. T. Smith Capital", "Equity"),
            (410, "Fees Earned", "Revenue"),
            (510, "Expenses", "Expense"),
        ]

        actual_accounts = [
            (
                account["AccountNumber"],
                account["AccountName"],
                account["AccountType"],
            )
            for account in accounts
        ]

        self.assertEqual(actual_accounts, expected_accounts)

        for account in accounts:
            self.assertEqual(account["BusinessId"], 1)
            self.assertEqual(account["IsAccountActive"], 1)
            self.assertEqual(account["CreatedBy"], 1)
            self.assertEqual(account["UpdatedBy"], 1)

            self.assertIsNotNone(account["CreatedAt"])
            self.assertIsNotNone(account["UpdatedAt"])
            self.assertIsNone(account["DeletedAt"])
            self.assertIsNone(account["DeletedBy"])

    def test_accounting_transactions_exist(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            transactions = conn.execute("""
                SELECT
                    TransactionDate,
                    Description,
                    PostingReference,
                    CreatedAt,
                    CreatedBy,
                    UpdatedAt,
                    UpdatedBy,
                    DeletedAt,
                    DeletedBy
                FROM AccountingTransaction
                ORDER BY TransactionDate, Id
                """).fetchall()

        self.assertEqual(len(transactions), len(ACCOUNTING_TRANSACTIONS))

        actual_transactions = [
            (
                transaction["TransactionDate"],
                transaction["Description"],
                transaction["PostingReference"],
                transaction["CreatedBy"],
                transaction["UpdatedBy"],
            )
            for transaction in transactions
        ]

        self.assertEqual(actual_transactions, ACCOUNTING_TRANSACTIONS)

        for transaction in transactions:
            self.assertIsNotNone(transaction["CreatedAt"])
            self.assertIsNotNone(transaction["UpdatedAt"])
            self.assertIsNone(transaction["DeletedAt"])
            self.assertIsNone(transaction["DeletedBy"])

    def test_transaction_lines_exist(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            transaction_lines = conn.execute("""
                SELECT
                    TransactionId,
                    AccountId,
                    AmountCents,
                    IsDebit,
                    CreatedAt,
                    CreatedBy,
                    UpdatedAt,
                    UpdatedBy,
                    DeletedAt,
                    DeletedBy
                FROM TransactionLine
                ORDER BY TransactionId, Id
                """).fetchall()

        self.assertEqual(
            len(transaction_lines),
            len(TRANSACTION_LINES),
        )

        actual_transaction_lines = [
            (
                line["TransactionId"],
                line["AccountId"],
                line["AmountCents"],
                line["IsDebit"],
                line["CreatedBy"],
                line["UpdatedBy"],
            )
            for line in transaction_lines
        ]

        self.assertEqual(
            actual_transaction_lines,
            TRANSACTION_LINES,
        )

        for line in transaction_lines:
            self.assertIsNotNone(line["CreatedAt"])
            self.assertIsNotNone(line["UpdatedAt"])
            self.assertEqual(line["CreatedBy"], 1)
            self.assertEqual(line["UpdatedBy"], 1)
            self.assertIsNone(line["DeletedAt"])
            self.assertIsNone(line["DeletedBy"])


if __name__ == "__main__":
    unittest.main()
