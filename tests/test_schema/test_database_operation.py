# test_database_operation.py
import time
import unittest
from sqlite3 import IntegrityError, Connection

from accounting.infrastructure.sqlite.connection import create_connection


class TestDatabaseUserOperation(unittest.TestCase):
    conn: Connection

    @classmethod
    def setUpClass(cls):
        cls.conn = create_connection(":memory:")

    def test_create_user(self) -> None:
        #       Username, First,   Last,    Email
        user = ("alice", "Alice", "Smith", "asmith@example.com")

        # Add user
        sql = """
        INSERT INTO users
            (username, first_name, last_name, email)
        VALUES
            (?, ?, ?, ?)
        """
        self.conn.execute(sql, user)
        self.conn.commit()

        sql = "SELECT * FROM users;"
        results = self.conn.execute(sql).fetchall()

        self.assertEqual(len(results), 1)

        user = results[0]
        self.assertEqual(user[0], 1)
        self.assertEqual(user[1], "alice")
        self.assertEqual(user[2], "Alice")
        self.assertEqual(user[3], "Smith")
        self.assertEqual(user[4], "asmith@example.com")
        self.assertEqual(user[5], 1)
        self.assertIsNotNone(user[6])
        self.assertIsNotNone(user[7])
        self.assertIsNone(user[8])

    def test_create_user_invalid_email(self) -> None:
        sql = """
        INSERT INTO users
            (username, first_name, last_name, email)
        VALUES
            (?, ?, ?, ?)
        """

        with self.assertRaises(IntegrityError):
            user = ("alice", "Alice", "Smith", "fake_email")
            self.conn.execute(sql, user)

        with self.assertRaises(IntegrityError):
            user = ("alice", "Alice", "Smith", "fake_emailexample.com")
            self.conn.execute(sql, user)

        with self.assertRaises(IntegrityError):
            user = ("alice", "Alice", "Smith", "fake_email@example")
            self.conn.execute(sql, user)

    def test_update_user_updated_at(self) -> None:
        sql = """
        UPDATE users
        SET last_name = ?
        WHERE id = ?;"""
        user = ("Doe", 1)

        # Sleep delay to account for speed of code execute in updated timestamp
        time.sleep(1)
        self.conn.execute(sql, user)

        sql = "SELECT * FROM users;"
        user = self.conn.execute(sql).fetchone()

        self.assertEqual(user[3], "Doe")
        self.assertNotEqual(user[6], user[7])


class TestDatabaseBusinessOperation(unittest.TestCase):
    conn: Connection

    @classmethod
    def setUpClass(cls):
        cls.conn = create_connection(":memory:")

        # Enter a couple of users
        users = [
            ("asmith", "Alice", "Smith", "asmith@example.com"),
            ("bbarker", "Bob", "Barker", "bbarker@website.com"),
        ]
        sql = """
            INSERT INTO users
                (username, first_name, last_name, email)
            VALUES
                (?, ?, ?, ?)"""

        cls.conn.executemany(sql, users)
        cls.conn.commit()

    def test_create_business(self) -> None:
        business = ("Alice INC.", "12-3456789", "2026-08-08", 7, 1)

        sql = """
            INSERT INTO businesses
                (title, tax_id, established, tax_year_end_month, created_by)
            VALUES
                (?, ?, ?, ?, ?);"""

        self.conn.execute(sql, business)

        sql = "SELECT * FROM businesses"
        results = self.conn.execute(sql).fetchall()

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][0], 1)
        self.assertEqual(results[0][1], "Alice INC.")
        self.assertEqual(results[0][2], "12-3456789")
        self.assertEqual(results[0][3], 1)
        self.assertEqual(results[0][4], "2026-08-08")
        self.assertEqual(results[0][5], 7)
        self.assertIsNotNone(results[0][6])
        self.assertEqual(results[0][7], 1)
        self.assertIsNotNone(results[0][8])
        self.assertIsNone(results[0][9], 1)
        self.assertIsNone(results[0][10])
        self.assertIsNone(results[0][11])

    def test_deleted(self) -> None:
        business = ("Alice INC.", "12-3456789", "2026-08-08", 7, 1)

        sql = """
            INSERT INTO businesses
                (title, tax_id, established, tax_year_end_month, created_by)
            VALUES
                (?, ?, ?, ?, ?);"""

        self.conn.execute(sql, business)

        sql = """
            UPDATE businesses
            SET
                deleted_by = ?,
                deleted_at = CURRENT_TIMESTAMP
            WHERE id = ?"""
        self.conn.execute(sql, (1, 1))

        sql = """SELECT * FROM businesses"""
        business = self.conn.execute(sql).fetchone()

        self.assertEqual(business[-1], 1)
        self.assertIsNotNone(business[-2])

    def test_valid_tax_id(self) -> None:
        sql = """
            INSERT INTO businesses
                (title, tax_id, established, tax_year_end_month, created_by)
            VALUES
                (?, ?, ?, ?, ?);"""

        with self.assertRaises(IntegrityError):
            # Missing a digit
            business = ("Alice INC.", "12-345678", "2026-08-08", 7, 1)
            self.conn.execute(sql, business)

        with self.assertRaises(IntegrityError):
            business = ("Alice INC.", "123456789", "2026-08-08", 7, 1)
            self.conn.execute(sql, business)

    def test_valid_tax_year(self) -> None:
        sql = """
            INSERT INTO businesses
                (title, tax_id, established, tax_year_end_month, created_by)
            VALUES
                (?, ?, ?, ?, ?);"""

        with self.assertRaises(IntegrityError):
            business = ("Alice INC.", "12-3456789", "2026-08-08", 0, 1)
            self.conn.execute(sql, business)
        with self.assertRaises(IntegrityError):
            business = ("Alice INC.", "12-3456789", "2026-08-08", -1, 1)
            self.conn.execute(sql, business)
        with self.assertRaises(IntegrityError):
            business = ("Alice INC.", "12-3456789", "2026-08-08", 13, 1)
            self.conn.execute(sql, business)
        with self.assertRaises(IntegrityError):
            business = ("Alice INC.", "12-3456789", "2026-08-08", 999999, 1)
            self.conn.execute(sql, business)

    def test_valid_established_date(self) -> None:
        sql = """
            INSERT INTO businesses
                (title, tax_id, established, tax_year_end_month, created_by)
            VALUES
                (?, ?, ?, ?, ?);"""

        with self.assertRaises(IntegrityError):
            business = ("Alice INC.", "12-3456789", "May, 2026", 12, 1)
            self.conn.execute(sql, business)
        with self.assertRaises(IntegrityError):
            business = ("Alice INC.", "12-3456789", "20260808", -1, 1)
            self.conn.execute(sql, business)


class TestDatabaseAccountOperation(unittest.TestCase):
    conn: Connection

    @classmethod
    def setUpClass(cls):
        cls.conn = create_connection(":memory:")

        # Enter a couple of users
        users = [
            ("asmith", "Alice", "Smith", "asmith@example.com"),
            ("bbarker", "Bob", "Barker", "bbarker@website.com"),
        ]
        sql = """
            INSERT INTO users
                (username, first_name, last_name, email)
            VALUES
                (?, ?, ?, ?)"""

        cls.conn.executemany(sql, users)

        business = ("Alice INC.", "12-3456789", "2026-08-08", 7, 1)

        sql = """
            INSERT INTO businesses
                (title, tax_id, established, tax_year_end_month, created_by)
            VALUES
                (?, ?, ?, ?, ?);"""

        cls.conn.execute(sql, business)
        cls.conn.commit()

    def test_account_creation(self) -> None:
        account = (1, 110, "Cash", "Asset", "Cash", 1, 1)
        sql = """
            INSERT INTO accounts
                (business_id, account_number, account_name, account_type, description, is_debit, created_by)
            VALUES
                (?, ?, ?, ?, ?, ?, ?)"""
        self.conn.execute(sql, account)

        sql = "SELECT * FROM accounts"
        account = self.conn.execute(sql).fetchone()

        self.assertEqual(account[0], 1)
        self.assertEqual(account[1], 1)
        self.assertEqual(account[2], 110)
        self.assertEqual(account[3], "Cash")
        self.assertEqual(account[4], "Asset")
        self.assertEqual(account[5], "Cash")
        self.assertEqual(account[6], 1)


class TestDatabaseAccountingTransaction(unittest.TestCase):
    conn: Connection

    @classmethod
    def setUpClass(cls) -> None:
        cls.conn = create_connection(":memory:")

        users = [
            ("asmith", "Alice", "Smith", "asmith@example.com"),
            ("bbarker", "Bob", "Barker", "bbarker@website.com"),
        ]

        sql = """
            INSERT INTO users
                (username, first_name, last_name, email)
            VALUES
                (?, ?, ?, ?)
        """
        cls.conn.executemany(sql, users)

        business = ("Alice INC.", "12-3456789", "2026-08-08", 7, 1)

        sql = """
            INSERT INTO businesses
                (title, tax_id, established, tax_year_end_month, created_by)
            VALUES
                (?, ?, ?, ?, ?)
        """
        cls.conn.execute(sql, business)
        cls.conn.commit()

    def test_transaction_creation(self) -> None:
        transaction = ("2026-08-08", "Owner contributed cash to business", "GJ1", 1)

        sql = """
            INSERT INTO accounting_transactions
                (transaction_date, description, posting_reference, created_by)
            VALUES
                (?, ?, ?, ?)
        """
        self.conn.execute(sql, transaction)

        sql = "SELECT * FROM accounting_transactions;"
        transaction = self.conn.execute(sql).fetchone()

        self.assertIsNotNone(transaction)
        self.assertEqual(transaction[0], 1)
        self.assertEqual(transaction[1], "2026-08-08")
        self.assertEqual(transaction[2], "Owner contributed cash to business")
        self.assertEqual(transaction[3], "GJ1")
        self.assertIsNotNone(transaction[4])
        self.assertEqual(transaction[5], 1)
        self.assertIsNotNone(transaction[6])
        self.assertIsNone(transaction[7])
        self.assertIsNone(transaction[8])
        self.assertIsNone(transaction[9])

    def test_transaction_without_posting_reference(self) -> None:
        transaction = ("2026-08-09", "Purchased office supplies", None, 1)

        sql = """
            INSERT INTO accounting_transactions
                (transaction_date, description, posting_reference, created_by)
            VALUES
                (?, ?, ?, ?)
        """
        self.conn.execute(sql, transaction)

        sql = """
            SELECT *
            FROM accounting_transactions
            WHERE transaction_date = ?;
        """
        transaction = self.conn.execute(sql, ("2026-08-09",)).fetchone()

        self.assertIsNotNone(transaction)
        self.assertEqual(transaction[1], "2026-08-09")
        self.assertEqual(transaction[2], "Purchased office supplies")
        self.assertIsNone(transaction[3])

    def test_transaction_updated_at(self) -> None:
        transaction = ("2026-08-10", "Purchased equipment", None, 1)

        sql = """
            INSERT INTO accounting_transactions
                (transaction_date, description, posting_reference, created_by)
            VALUES
                (?, ?, ?, ?)
        """
        cursor = self.conn.execute(sql, transaction)
        transaction_id = cursor.lastrowid

        time.sleep(1)

        sql = """
            UPDATE accounting_transactions
            SET
                description = ?,
                updated_by = ?
            WHERE id = ?;
        """
        self.conn.execute(sql, ("Purchased shop equipment", 2, transaction_id))

        sql = """
            SELECT *
            FROM accounting_transactions
            WHERE id = ?;
        """
        transaction = self.conn.execute(sql, (transaction_id,)).fetchone()

        self.assertIsNotNone(transaction)
        self.assertEqual(transaction[2], "Purchased shop equipment")
        self.assertEqual(transaction[7], 2)
        self.assertNotEqual(transaction[4], transaction[6])

    def test_transaction_deleted(self) -> None:
        transaction = ("2026-08-11", "Transaction to delete", None, 1)

        sql = """
            INSERT INTO accounting_transactions
                (transaction_date, description, posting_reference, created_by)
            VALUES
                (?, ?, ?, ?)
        """
        cursor = self.conn.execute(sql, transaction)
        transaction_id = cursor.lastrowid

        sql = """
            UPDATE accounting_transactions
            SET
                deleted_at = CURRENT_TIMESTAMP,
                deleted_by = ?
            WHERE id = ?;
        """
        self.conn.execute(sql, (1, transaction_id))

        sql = """
            SELECT *
            FROM accounting_transactions
            WHERE id = ?;
        """
        transaction = self.conn.execute(sql, (transaction_id,)).fetchone()

        self.assertIsNotNone(transaction)
        self.assertIsNotNone(transaction[-2])
        self.assertEqual(transaction[-1], 1)


class TestDatabaseTransactionLine(unittest.TestCase):
    conn: Connection

    @classmethod
    def setUpClass(cls) -> None:
        cls.conn = create_connection(":memory:")

        users = [
            ("asmith", "Alice", "Smith", "asmith@example.com"),
            ("bbarker", "Bob", "Barker", "bbarker@website.com"),
        ]

        sql = """
            INSERT INTO users
                (username, first_name, last_name, email)
            VALUES
                (?, ?, ?, ?)
        """
        cls.conn.executemany(sql, users)

        business = ("Alice INC.", "12-3456789", "2026-08-08", 7, 1)

        sql = """
            INSERT INTO businesses
                (title, tax_id, established, tax_year_end_month, created_by)
            VALUES
                (?, ?, ?, ?, ?)
        """
        cls.conn.execute(sql, business)

        accounts = [
            (1, 110, "Cash", "Asset", "Cash", 1, 1),
            (1, 310, "Owner Capital", "Equity", "Owner contributions", 0, 1),
        ]

        sql = """
            INSERT INTO accounts
                (business_id, account_number, account_name, account_type, description, is_debit, created_by)
            VALUES
                (?, ?, ?, ?, ?, ?, ?)
        """
        cls.conn.executemany(sql, accounts)

        transaction = ("2026-08-08", "Owner contributed $1,000 cash", "GJ1", 1)

        sql = """
            INSERT INTO accounting_transactions
                (transaction_date, description, posting_reference, created_by)
            VALUES
                (?, ?, ?, ?)
        """
        cls.conn.execute(sql, transaction)
        cls.conn.commit()

    def test_transaction_line_creation(self) -> None:
        line = (1, 1, 100000, 1, 1)

        sql = """
            INSERT INTO transaction_lines
                (transaction_id, account_id, amount_cents, is_debit, created_by)
            VALUES
                (?, ?, ?, ?, ?)
        """
        self.conn.execute(sql, line)

        sql = "SELECT * FROM transaction_lines;"
        transaction_line = self.conn.execute(sql).fetchone()

        self.assertIsNotNone(transaction_line)
        self.assertEqual(transaction_line[0], 1)
        self.assertEqual(transaction_line[1], 1)
        self.assertEqual(transaction_line[2], 1)
        self.assertEqual(transaction_line[3], 100000)
        self.assertEqual(transaction_line[4], 1)
        self.assertIsNotNone(transaction_line[5])
        self.assertEqual(transaction_line[6], 1)
        self.assertIsNotNone(transaction_line[7])
        self.assertIsNone(transaction_line[8])
        self.assertIsNone(transaction_line[9])
        self.assertIsNone(transaction_line[10])

    def test_transaction_debit_and_credit_lines(self) -> None:
        lines = [
            (1, 1, 100000, 1, 1),
            (1, 2, 100000, 0, 1),
        ]

        sql = """
            INSERT INTO transaction_lines
                (transaction_id, account_id, amount_cents, is_debit, created_by)
            VALUES
                (?, ?, ?, ?, ?)
        """
        self.conn.executemany(sql, lines)

        sql = """
            SELECT *
            FROM transaction_lines
            WHERE transaction_id = ?;
        """
        lines = self.conn.execute(sql, (1,)).fetchall()

        self.assertEqual(len(lines), 2)

        debit = lines[0]
        credit = lines[1]

        self.assertEqual(debit[2], 1)
        self.assertEqual(debit[3], 100000)
        self.assertEqual(debit[4], 1)

        self.assertEqual(credit[2], 2)
        self.assertEqual(credit[3], 100000)
        self.assertEqual(credit[4], 0)

    def test_transaction_line_negative_amount(self) -> None:
        line = (1, 1, -100000, 1, 1)

        sql = """
            INSERT INTO transaction_lines
                (transaction_id, account_id, amount_cents, is_debit, created_by)
            VALUES
                (?, ?, ?, ?, ?)
        """

        with self.assertRaises(IntegrityError):
            self.conn.execute(sql, line)

    def test_transaction_line_invalid_transaction(self) -> None:
        line = (999, 1, 100000, 1, 1)

        sql = """
            INSERT INTO transaction_lines
                (transaction_id, account_id, amount_cents, is_debit, created_by)
            VALUES
                (?, ?, ?, ?, ?)
        """

        with self.assertRaises(IntegrityError):
            self.conn.execute(sql, line)

    def test_transaction_line_invalid_account(self) -> None:
        line = (1, 999, 100000, 1, 1)

        sql = """
            INSERT INTO transaction_lines
                (transaction_id, account_id, amount_cents, is_debit, created_by)
            VALUES
                (?, ?, ?, ?, ?)
        """

        with self.assertRaises(IntegrityError):
            self.conn.execute(sql, line)

    def test_transaction_line_updated_at(self) -> None:
        line = (1, 1, 50000, 1, 1)

        sql = """
            INSERT INTO transaction_lines
                (transaction_id, account_id, amount_cents, is_debit, created_by)
            VALUES
                (?, ?, ?, ?, ?)
        """
        cursor = self.conn.execute(sql, line)
        line_id = cursor.lastrowid

        time.sleep(1)

        sql = """
            UPDATE transaction_lines
            SET
                amount_cents = ?,
                updated_by = ?
            WHERE id = ?;
        """
        self.conn.execute(sql, (75000, 2, line_id))

        sql = """
            SELECT *
            FROM transaction_lines
            WHERE id = ?;
        """
        line = self.conn.execute(sql, (line_id,)).fetchone()

        self.assertIsNotNone(line)
        self.assertEqual(line[3], 75000)
        self.assertEqual(line[8], 2)
        self.assertNotEqual(line[5], line[7])

    def test_transaction_line_deleted(self) -> None:
        line = (1, 1, 25000, 1, 1)

        sql = """
            INSERT INTO transaction_lines
                (transaction_id, account_id, amount_cents, is_debit, created_by)
            VALUES
                (?, ?, ?, ?, ?)
        """
        cursor = self.conn.execute(sql, line)
        line_id = cursor.lastrowid

        sql = """
            UPDATE transaction_lines
            SET
                deleted_at = CURRENT_TIMESTAMP,
                deleted_by = ?
            WHERE id = ?;
        """
        self.conn.execute(sql, (1, line_id))

        sql = """
            SELECT *
            FROM transaction_lines
            WHERE id = ?;
        """
        line = self.conn.execute(sql, (line_id,)).fetchone()

        self.assertIsNotNone(line)
        self.assertIsNotNone(line[-2])
        self.assertEqual(line[-1], 1)


class TestDatabaseDocumentsOperation(unittest.TestCase):
    conn: Connection

    @classmethod
    def setUpClass(cls) -> None:
        cls.conn = create_connection(":memory:")

        users = [
            ("asmith", "Alice", "Smith", "asmith@example.com"),
            ("bbarker", "Bob", "Barker", "bbarker@website.com"),
        ]

        sql = """
            INSERT INTO users
                (username, first_name, last_name, email)
            VALUES
                (?, ?, ?, ?)
        """
        cls.conn.executemany(sql, users)

        business = ("Alice INC.", "12-3456789", "2026-08-08", 7, 1)

        sql = """
            INSERT INTO businesses
                (title, tax_id, established, tax_year_end_month, created_by)
            VALUES
                (?, ?, ?, ?, ?)
        """
        cls.conn.execute(sql, business)

        accounts = [
            (1, 110, "Cash", "Asset", "Cash", 1),
            (1, 310, "Owner Capital", "Equity", "Owner contributions", 1),
        ]

        sql = """
            INSERT INTO accounts
                (business_id, account_number, account_name, account_type, description, created_by)
            VALUES
                (?, ?, ?, ?, ?, ?)
        """
        cls.conn.executemany(sql, accounts)

        transaction = ("2026-08-08", "Owner contributed $1,000 cash", "GJ1", 1)

        sql = """
            INSERT INTO accounting_transactions
                (transaction_date, description, posting_reference, created_by)
            VALUES
                (?, ?, ?, ?)
        """
        cls.conn.execute(sql, transaction)

        lines = [
            (1, 1, 100000, 1, 1),
            (1, 2, 100000, 0, 1),
        ]

        sql = """
            INSERT INTO transaction_lines
                (transaction_id, account_id, amount_cents, is_debit, created_by)
            VALUES
                (?, ?, ?, ?, ?)
        """
        cls.conn.executemany(sql, lines)
        cls.conn.commit()


class TestDatabaseAccountsHistory(unittest.TestCase):
    conn: Connection

    @classmethod
    def setUpClass(cls) -> None:
        cls.conn = create_connection(":memory:")

        users = [
            ("asmith", "Alice", "Smith", "asmith@example.com"),
            ("bbarker", "Bob", "Barker", "bbarker@website.com"),
        ]

        sql = """
            INSERT INTO users
                (username, first_name, last_name, email)
            VALUES
                (?, ?, ?, ?)
        """
        cls.conn.executemany(sql, users)

        business = ("Alice INC.", "12-3456789", "2026-08-08", 7, 1)

        sql = """
            INSERT INTO businesses
                (title, tax_id, established, tax_year_end_month, created_by)
            VALUES
                (?, ?, ?, ?, ?)
        """
        cls.conn.execute(sql, business)

        accounts = [
            (1, 110, "Cash", "Asset", "Cash", 1, 1),
            (1, 310, "Owner Capital", "Equity", "Owner contributions", 0, 1),
        ]

        sql = """
            INSERT INTO accounts
                (business_id, account_number, account_name, account_type, description, is_debit, created_by)
            VALUES
                (?, ?, ?, ?, ?, ?, ?)
        """
        cls.conn.executemany(sql, accounts)

        transaction = ("2026-08-08", "Owner contributed $1,000 cash", "GJ1", 1)

        sql = """
            INSERT INTO accounting_transactions
                (transaction_date, description, posting_reference, created_by)
            VALUES
                (?, ?, ?, ?)
        """
        cls.conn.execute(sql, transaction)

        transaction_lines = [(1, 1, 1_000_00, 1, 1), (1, 2, 1_000_00, 0, 1)]
        sql = """
            INSERT INTO transaction_lines
                (transaction_id, account_id, amount_cents, is_debit, created_by)
            VALUES
                (?, ?, ?, ?, ?);
        """
        cls.conn.executemany(sql, transaction_lines)
        cls.conn.commit()

    def test_accounts_history(self):
        update_lines = [(100_00, 1, 1), (100_00, 1, 2)]
        sql = """
            UPDATE transaction_lines
            SET amount_cents = ?, updated_by = ?
            WHERE id = ?;
        """
        self.conn.executemany(sql, update_lines)

        sql = """
            SELECT
                tlh.id,
                tl.id,
                at.description,
                a.account_name,
                tlh.amount_cents,
                u.username
            FROM transaction_lines_history tlh
            JOIN transaction_lines tl
                ON tl.id = tlh.transaction_line_id
            JOIN accounting_transactions at
                ON at.id = tlh.transaction_id
            JOIN accounts a
                ON a.id = tlh.account_id
            JOIN users u
                ON u.id = tlh.updated_by"""
        _ = self.conn.execute(sql).fetchall()


if __name__ == "__main__":
    unittest.main()
