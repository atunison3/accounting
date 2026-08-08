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
        account = (1, 110, "Cash", "Asset", "Cash", 1)
        sql = """
            INSERT INTO accounts
                (business_id, account_number, account_name, account_type, description, created_by)
            VALUES
                (?, ?, ?, ?, ?, ?)"""
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


if __name__ == "__main__":
    unittest.main()
