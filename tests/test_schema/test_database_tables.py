# test_database_schema.py
import unittest
from sqlite3 import IntegrityError, Connection

from accounting.infrastructure.sqlite.connection import create_connection


class TestDatabaseSchema(unittest.TestCase):
    """
    Comprehensive tests verifying that all tables are created correctly,
    accept valid data of the expected types, and enforce their CHECK
    constraints and basic integrity rules.
    """

    conn: Connection

    @classmethod
    def setUpClass(cls) -> None:
        cls.conn = create_connection(":memory:")

    def _table_exists(self, table_name: str) -> bool:
        sql = """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name = ?;
        """
        result = self.conn.execute(sql, (table_name,)).fetchone()
        return result is not None

    def _column_names(self, table_name: str) -> list[str]:
        cursor = self.conn.execute(f"PRAGMA table_info({table_name});")
        return [row[1] for row in cursor.fetchall()]

    # ------------------------------------------------------------------
    # users
    # ------------------------------------------------------------------
    def test_users_table_exists(self) -> None:
        self.assertTrue(self._table_exists("users"))
        columns = self._column_names("users")
        expected = {
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "is_active",
            "created_at",
            "updated_at",
            "deleted_at",
        }
        self.assertTrue(expected.issubset(set(columns)))

    def test_users_insert_valid(self) -> None:
        sql = """
            INSERT INTO users (username, first_name, last_name, email)
            VALUES (?, ?, ?, ?);
        """
        self.conn.execute(sql, ("alice", "Alice", "Smith", "asmith@example.com"))
        self.conn.commit()

        row = self.conn.execute("SELECT * FROM users WHERE username = ?;", ("alice",)).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row[1], "alice")
        self.assertEqual(row[2], "Alice")
        self.assertEqual(row[3], "Smith")
        self.assertEqual(row[4], "asmith@example.com")
        self.assertEqual(row[5], 1)
        self.assertIsNotNone(row[6])  # created_at
        self.assertIsNotNone(row[7])  # updated_at
        self.assertIsNone(row[8])  # deleted_at

    def test_users_email_check_constraint(self) -> None:
        sql = """
            INSERT INTO users (username, first_name, last_name, email)
            VALUES (?, ?, ?, ?);
        """
        invalid_emails = [
            "fake_email",
            "fake_emailexample.com",
            "fake_email@example",
            "noatsign.com",
            "@missinglocal.com",
            "missingdomain@",
        ]
        for email in invalid_emails:
            with self.subTest(email=email):
                with self.assertRaises(IntegrityError):
                    self.conn.execute(sql, ("user_" + email[:5], "F", "L", email))

    def test_users_unique_constraints(self) -> None:
        sql = """
            INSERT INTO users (username, first_name, last_name, email)
            VALUES (?, ?, ?, ?);
        """
        self.conn.execute(sql, ("bob", "Bob", "Barker", "bbarker@website.com"))
        self.conn.commit()

        with self.assertRaises(IntegrityError):
            self.conn.execute(sql, ("bob", "Robert", "Barker", "different@email.com"))

        with self.assertRaises(IntegrityError):
            self.conn.execute(sql, ("different", "Bob", "Barker", "bbarker@website.com"))

    # ------------------------------------------------------------------
    # businesses
    # ------------------------------------------------------------------
    def test_businesses_table_exists(self) -> None:
        self.assertTrue(self._table_exists("businesses"))
        columns = self._column_names("businesses")
        expected = {
            "id",
            "title",
            "tax_id",
            "is_business_active",
            "established",
            "tax_year_end_month",
            "created_at",
            "created_by",
            "updated_at",
            "updated_by",
            "deleted_at",
            "deleted_by",
        }
        self.assertTrue(expected.issubset(set(columns)))

    def test_businesses_insert_valid(self) -> None:
        # Ensure a user exists for the foreign key
        self.conn.execute(
            "INSERT OR IGNORE INTO users (username, first_name, last_name, email) "
            "VALUES ('creator', 'C', 'User', 'creator@example.com');"
        )
        user_id = self.conn.execute("SELECT id FROM users WHERE username = 'creator';").fetchone()[0]

        sql = """
            INSERT INTO businesses
                (title, tax_id, established, tax_year_end_month, created_by)
            VALUES (?, ?, ?, ?, ?);
        """
        self.conn.execute(sql, ("Alice INC.", "12-3456789", "2026-08-08", 7, user_id))
        self.conn.commit()

        row = self.conn.execute("SELECT * FROM businesses WHERE title = ?;", ("Alice INC.",)).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row[1], "Alice INC.")
        self.assertEqual(row[2], "12-3456789")
        self.assertEqual(row[3], 1)  # is_business_active default
        self.assertEqual(row[4], "2026-08-08")
        self.assertEqual(row[5], 7)
        self.assertIsNotNone(row[6])  # created_at
        self.assertEqual(row[7], user_id)

    def test_businesses_tax_id_check(self) -> None:
        self.conn.execute(
            "INSERT OR IGNORE INTO users (username, first_name, last_name, email) "
            "VALUES ('creator', 'C', 'User', 'creator@example.com');"
        )
        user_id = self.conn.execute("SELECT id FROM users WHERE username = 'creator';").fetchone()[0]

        sql = """
            INSERT INTO businesses
                (title, tax_id, established, tax_year_end_month, created_by)
            VALUES (?, ?, ?, ?, ?);
        """
        invalid_tax_ids = [
            "12-345678",  # too short
            "123456789",  # missing hyphen
            "12-34567890",  # too long
            "ab-3456789",  # non-digit prefix
            "12-abcdefg",  # non-digit suffix
        ]
        for tax_id in invalid_tax_ids:
            with self.subTest(tax_id=tax_id):
                with self.assertRaises(IntegrityError):
                    self.conn.execute(sql, ("Bad Tax", tax_id, "2026-01-01", 12, user_id))

    def test_businesses_tax_year_end_month_check(self) -> None:
        self.conn.execute(
            "INSERT OR IGNORE INTO users (username, first_name, last_name, email) "
            "VALUES ('creator', 'C', 'User', 'creator@example.com');"
        )
        user_id = self.conn.execute("SELECT id FROM users WHERE username = 'creator';").fetchone()[0]

        sql = """
            INSERT INTO businesses
                (title, tax_id, established, tax_year_end_month, created_by)
            VALUES (?, ?, ?, ?, ?);
        """
        for month in (0, -1, 13, 999):
            with self.subTest(month=month):
                with self.assertRaises(IntegrityError):
                    self.conn.execute(sql, ("Bad Month", "12-3456789", "2026-01-01", month, user_id))

    def test_businesses_established_date_check(self) -> None:
        self.conn.execute(
            "INSERT OR IGNORE INTO users (username, first_name, last_name, email) "
            "VALUES ('creator', 'C', 'User', 'creator@example.com');"
        )
        user_id = self.conn.execute("SELECT id FROM users WHERE username = 'creator';").fetchone()[0]

        sql = """
            INSERT INTO businesses
                (title, tax_id, established, tax_year_end_month, created_by)
            VALUES (?, ?, ?, ?, ?);
        """
        invalid_dates = [
            "May, 2026",
            "20260808",
            "2026/08/08",
            "08-08-2026",
            "2026-13-01",
            "2026-02-30",
        ]
        for established in invalid_dates:
            with self.subTest(established=established):
                with self.assertRaises(IntegrityError):
                    self.conn.execute(sql, ("Bad Date", "12-3456789", established, 12, user_id))

    def test_businesses_deleted_consistency_check(self) -> None:
        self.conn.execute(
            "INSERT OR IGNORE INTO users (username, first_name, last_name, email) "
            "VALUES ('creator', 'C', 'User', 'creator@example.com');"
        )
        user_id = self.conn.execute("SELECT id FROM users WHERE username = 'creator';").fetchone()[0]

        # First create a valid business
        self.conn.execute(
            """
            INSERT INTO businesses (title, tax_id, established, tax_year_end_month, created_by)
            VALUES ('To Delete', '98-7654321', '2025-01-01', 12, ?);
            """,
            (user_id,),
        )
        biz_id = self.conn.execute("SELECT id FROM businesses WHERE title = 'To Delete';").fetchone()[0]

        # Attempt to set only deleted_at (should fail the CHECK)
        with self.assertRaises(IntegrityError):
            self.conn.execute(
                "UPDATE businesses SET deleted_at = CURRENT_TIMESTAMP WHERE id = ?;",
                (biz_id,),
            )

        # Attempt to set only deleted_by (should fail the CHECK)
        with self.assertRaises(IntegrityError):
            self.conn.execute(
                "UPDATE businesses SET deleted_by = ? WHERE id = ?;",
                (user_id, biz_id),
            )

    # ------------------------------------------------------------------
    # accounts
    # ------------------------------------------------------------------
    def test_accounts_table_exists(self) -> None:
        self.assertTrue(self._table_exists("accounts"))
        columns = self._column_names("accounts")
        expected = {
            "id",
            "business_id",
            "account_number",
            "account_name",
            "account_type",
            "description",
            "is_account_active",
            "created_at",
            "created_by",
            "updated_at",
            "updated_by",
            "deleted_at",
            "deleted_by",
        }
        self.assertTrue(expected.issubset(set(columns)))

    def test_accounts_insert_valid(self) -> None:
        self.conn.execute(
            "INSERT OR IGNORE INTO users (username, first_name, last_name, email) "
            "VALUES ('creator', 'C', 'User', 'creator@example.com');"
        )
        user_id = self.conn.execute("SELECT id FROM users WHERE username = 'creator';").fetchone()[0]

        # Ensure a business exists
        self.conn.execute(
            """
            INSERT OR IGNORE INTO businesses
                (title, tax_id, established, tax_year_end_month, created_by)
            VALUES ('Test Biz', '11-1111111', '2020-01-01', 12, ?);
            """,
            (user_id,),
        )
        biz_id = self.conn.execute("SELECT id FROM businesses WHERE title = 'Test Biz';").fetchone()[0]

        sql = """
            INSERT INTO accounts
                (business_id, account_number, account_name, account_type, description, created_by)
            VALUES (?, ?, ?, ?, ?, ?);
        """
        self.conn.execute(sql, (biz_id, 110, "Cash", "Asset", "Cash account", user_id))
        self.conn.commit()

        row = self.conn.execute(
            "SELECT * FROM accounts WHERE account_number = 110 AND business_id = ?;",
            (biz_id,),
        ).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row[2], 110)
        self.assertEqual(row[3], "Cash")
        self.assertEqual(row[4], "Asset")
        self.assertEqual(row[5], "Cash account")
        self.assertEqual(row[6], 1)

    def test_accounts_account_type_check(self) -> None:
        self.conn.execute(
            "INSERT OR IGNORE INTO users (username, first_name, last_name, email) "
            "VALUES ('creator', 'C', 'User', 'creator@example.com');"
        )
        user_id = self.conn.execute("SELECT id FROM users WHERE username = 'creator';").fetchone()[0]
        self.conn.execute(
            """
            INSERT OR IGNORE INTO businesses
                (title, tax_id, established, tax_year_end_month, created_by)
            VALUES ('Test Biz', '11-1111111', '2020-01-01', 12, ?);
            """,
            (user_id,),
        )
        biz_id = self.conn.execute("SELECT id FROM businesses WHERE title = 'Test Biz';").fetchone()[0]

        sql = """
            INSERT INTO accounts
                (business_id, account_number, account_name, account_type, description, created_by)
            VALUES (?, ?, ?, ?, ?, ?);
        """
        invalid_types = ["asset", "ASSETS", "Income", "Cost", "Other"]
        for atype in invalid_types:
            with self.subTest(account_type=atype):
                with self.assertRaises(IntegrityError):
                    self.conn.execute(sql, (biz_id, 999, "Bad", atype, "desc", user_id))

    def test_accounts_unique_business_account_number(self) -> None:
        self.conn.execute(
            "INSERT OR IGNORE INTO users (username, first_name, last_name, email) "
            "VALUES ('creator', 'C', 'User', 'creator@example.com');"
        )
        user_id = self.conn.execute("SELECT id FROM users WHERE username = 'creator';").fetchone()[0]
        self.conn.execute(
            """
            INSERT OR IGNORE INTO businesses
                (title, tax_id, established, tax_year_end_month, created_by)
            VALUES ('Test Biz', '11-1111111', '2020-01-01', 12, ?);
            """,
            (user_id,),
        )
        biz_id = self.conn.execute("SELECT id FROM businesses WHERE title = 'Test Biz';").fetchone()[0]

        sql = """
            INSERT INTO accounts
                (business_id, account_number, account_name, account_type, description, created_by)
            VALUES (?, ?, ?, ?, ?, ?);
        """
        self.conn.execute(sql, (biz_id, 120, "AR", "Asset", "Receivables", user_id))
        self.conn.commit()

        with self.assertRaises(IntegrityError):
            self.conn.execute(sql, (biz_id, 120, "Duplicate", "Asset", "dup", user_id))

    # ------------------------------------------------------------------
    # accounting_transactions
    # ------------------------------------------------------------------
    def test_accounting_transactions_table_exists(self) -> None:
        self.assertTrue(self._table_exists("accounting_transactions"))
        columns = self._column_names("accounting_transactions")
        expected = {
            "id",
            "transaction_date",
            "description",
            "posting_reference",
            "created_at",
            "created_by",
            "updated_at",
            "updated_by",
            "deleted_at",
            "deleted_by",
        }
        self.assertTrue(expected.issubset(set(columns)))

    def test_accounting_transactions_insert_valid(self) -> None:
        self.conn.execute(
            "INSERT OR IGNORE INTO users (username, first_name, last_name, email) "
            "VALUES ('creator', 'C', 'User', 'creator@example.com');"
        )
        user_id = self.conn.execute("SELECT id FROM users WHERE username = 'creator';").fetchone()[0]

        sql = """
            INSERT INTO accounting_transactions
                (transaction_date, description, posting_reference, created_by)
            VALUES (?, ?, ?, ?);
        """
        self.conn.execute(sql, ("2026-08-08", "Owner contribution", "GJ1", user_id))
        self.conn.commit()

        row = self.conn.execute("SELECT * FROM accounting_transactions WHERE posting_reference = 'GJ1';").fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row[1], "2026-08-08")
        self.assertEqual(row[2], "Owner contribution")
        self.assertEqual(row[3], "GJ1")
        self.assertIsNotNone(row[4])
        self.assertEqual(row[5], user_id)

    def test_accounting_transactions_null_posting_reference(self) -> None:
        self.conn.execute(
            "INSERT OR IGNORE INTO users (username, first_name, last_name, email) "
            "VALUES ('creator', 'C', 'User', 'creator@example.com');"
        )
        user_id = self.conn.execute("SELECT id FROM users WHERE username = 'creator';").fetchone()[0]

        sql = """
            INSERT INTO accounting_transactions
                (transaction_date, description, posting_reference, created_by)
            VALUES (?, ?, ?, ?);
        """
        self.conn.execute(sql, ("2026-08-09", "No reference entry", None, user_id))
        self.conn.commit()

        row = self.conn.execute(
            "SELECT posting_reference FROM accounting_transactions WHERE description = ?;",
            ("No reference entry",),
        ).fetchone()
        self.assertIsNone(row[0])

    def test_accounting_transactions_deleted_consistency(self) -> None:
        self.conn.execute(
            "INSERT OR IGNORE INTO users (username, first_name, last_name, email) "
            "VALUES ('creator', 'C', 'User', 'creator@example.com');"
        )
        user_id = self.conn.execute("SELECT id FROM users WHERE username = 'creator';").fetchone()[0]

        self.conn.execute(
            """
            INSERT INTO accounting_transactions
                (transaction_date, description, posting_reference, created_by)
            VALUES ('2026-08-10', 'To be soft-deleted', NULL, ?);
            """,
            (user_id,),
        )
        tx_id = self.conn.execute(
            "SELECT id FROM accounting_transactions WHERE description = 'To be soft-deleted';"
        ).fetchone()[0]

        with self.assertRaises(IntegrityError):
            self.conn.execute(
                "UPDATE accounting_transactions SET deleted_at = CURRENT_TIMESTAMP WHERE id = ?;",
                (tx_id,),
            )

        with self.assertRaises(IntegrityError):
            self.conn.execute(
                "UPDATE accounting_transactions SET deleted_by = ? WHERE id = ?;",
                (user_id, tx_id),
            )

    # ------------------------------------------------------------------
    # transaction_lines
    # ------------------------------------------------------------------
    def test_transaction_lines_table_exists(self) -> None:
        self.assertTrue(self._table_exists("transaction_lines"))
        columns = self._column_names("transaction_lines")
        expected = {
            "id",
            "transaction_id",
            "account_id",
            "amount_cents",
            "is_debit",
            "created_at",
            "created_by",
            "updated_at",
            "updated_by",
            "deleted_at",
            "deleted_by",
        }
        self.assertTrue(expected.issubset(set(columns)))

    def test_transaction_lines_insert_valid(self) -> None:
        self.conn.execute(
            "INSERT OR IGNORE INTO users (username, first_name, last_name, email) "
            "VALUES ('creator', 'C', 'User', 'creator@example.com');"
        )
        user_id = self.conn.execute("SELECT id FROM users WHERE username = 'creator';").fetchone()[0]

        self.conn.execute(
            """
            INSERT OR IGNORE INTO businesses
                (title, tax_id, established, tax_year_end_month, created_by)
            VALUES ('Test Biz', '11-1111111', '2020-01-01', 12, ?);
            """,
            (user_id,),
        )
        biz_id = self.conn.execute("SELECT id FROM businesses WHERE title = 'Test Biz';").fetchone()[0]

        self.conn.execute(
            """
            INSERT OR IGNORE INTO accounts
                (business_id, account_number, account_name, account_type, description, created_by)
            VALUES (?, 110, 'Cash', 'Asset', 'Cash', ?);
            """,
            (biz_id, user_id),
        )
        account_id = self.conn.execute(
            "SELECT id FROM accounts WHERE account_number = 110 AND business_id = ?;",
            (biz_id,),
        ).fetchone()[0]

        self.conn.execute(
            """
            INSERT INTO accounting_transactions
                (transaction_date, description, posting_reference, created_by)
            VALUES ('2026-08-08', 'Contribution', 'GJ1', ?);
            """,
            (user_id,),
        )
        tx_id = self.conn.execute("SELECT id FROM accounting_transactions WHERE posting_reference = 'GJ1';").fetchone()[
            0
        ]

        sql = """
            INSERT INTO transaction_lines
                (transaction_id, account_id, amount_cents, is_debit, created_by)
            VALUES (?, ?, ?, ?, ?);
        """
        self.conn.execute(sql, (tx_id, account_id, 100000, 1, user_id))
        self.conn.commit()

        row = self.conn.execute(
            "SELECT * FROM transaction_lines WHERE transaction_id = ? AND account_id = ?;",
            (tx_id, account_id),
        ).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row[3], 100000)
        self.assertEqual(row[4], 1)

    def test_transaction_lines_amount_cents_non_negative(self) -> None:
        self.conn.execute(
            "INSERT OR IGNORE INTO users (username, first_name, last_name, email) "
            "VALUES ('creator', 'C', 'User', 'creator@example.com');"
        )
        user_id = self.conn.execute("SELECT id FROM users WHERE username = 'creator';").fetchone()[0]

        self.conn.execute(
            """
            INSERT OR IGNORE INTO businesses
                (title, tax_id, established, tax_year_end_month, created_by)
            VALUES ('Test Biz', '11-1111111', '2020-01-01', 12, ?);
            """,
            (user_id,),
        )
        biz_id = self.conn.execute("SELECT id FROM businesses WHERE title = 'Test Biz';").fetchone()[0]

        self.conn.execute(
            """
            INSERT OR IGNORE INTO accounts
                (business_id, account_number, account_name, account_type, description, created_by)
            VALUES (?, 110, 'Cash', 'Asset', 'Cash', ?);
            """,
            (biz_id, user_id),
        )
        account_id = self.conn.execute(
            "SELECT id FROM accounts WHERE account_number = 110 AND business_id = ?;",
            (biz_id,),
        ).fetchone()[0]

        self.conn.execute(
            """
            INSERT INTO accounting_transactions
                (transaction_date, description, posting_reference, created_by)
            VALUES ('2026-08-11', 'Negative test', NULL, ?);
            """,
            (user_id,),
        )
        tx_id = self.conn.execute(
            "SELECT id FROM accounting_transactions WHERE description = 'Negative test';"
        ).fetchone()[0]

        sql = """
            INSERT INTO transaction_lines
                (transaction_id, account_id, amount_cents, is_debit, created_by)
            VALUES (?, ?, ?, ?, ?);
        """
        with self.assertRaises(IntegrityError):
            self.conn.execute(sql, (tx_id, account_id, -1, 1, user_id))

    def test_transaction_lines_foreign_keys(self) -> None:
        self.conn.execute(
            "INSERT OR IGNORE INTO users (username, first_name, last_name, email) "
            "VALUES ('creator', 'C', 'User', 'creator@example.com');"
        )
        user_id = self.conn.execute("SELECT id FROM users WHERE username = 'creator';").fetchone()[0]

        sql = """
            INSERT INTO transaction_lines
                (transaction_id, account_id, amount_cents, is_debit, created_by)
            VALUES (?, ?, ?, ?, ?);
        """
        # Non-existent transaction_id
        with self.assertRaises(IntegrityError):
            self.conn.execute(sql, (99999, 1, 100, 1, user_id))

        # Non-existent account_id
        with self.assertRaises(IntegrityError):
            self.conn.execute(sql, (1, 99999, 100, 1, user_id))

    # ------------------------------------------------------------------
    # documents
    # ------------------------------------------------------------------
    def test_documents_table_exists(self) -> None:
        self.assertTrue(self._table_exists("documents"))
        columns = self._column_names("documents")
        expected = {
            "id",
            "document_type",
            "document_date",
            "title",
            "description",
            "filename",
            "file_path",
            "mime_type",
            "file_size_bytes",
            "sha256_hash",
            "source",
            "received_from",
            "notes",
            "created_at",
            "created_by",
            "updated_at",
            "updated_by",
            "deleted_at",
            "deleted_by",
        }
        self.assertTrue(expected.issubset(set(columns)))

    def test_documents_insert_valid(self) -> None:
        self.conn.execute(
            "INSERT OR IGNORE INTO users (username, first_name, last_name, email) "
            "VALUES ('creator', 'C', 'User', 'creator@example.com');"
        )
        user_id = self.conn.execute("SELECT id FROM users WHERE username = 'creator';").fetchone()[0]

        sql = """
            INSERT INTO documents
                (document_type, document_date, title, filename, file_path, created_by)
            VALUES (?, ?, ?, ?, ?, ?);
        """
        self.conn.execute(
            sql,
            ("receipt", "2026-08-08", "Office supplies", "receipt.pdf", "/docs/receipt.pdf", user_id),
        )
        self.conn.commit()

        row = self.conn.execute("SELECT * FROM documents WHERE filename = 'receipt.pdf';").fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row[1], "receipt")
        self.assertEqual(row[2], "2026-08-08")
        self.assertEqual(row[3], "Office supplies")
        self.assertEqual(row[5], "receipt.pdf")
        self.assertEqual(row[6], "/docs/receipt.pdf")

    def test_documents_document_date_check(self) -> None:
        self.conn.execute(
            "INSERT OR IGNORE INTO users (username, first_name, last_name, email) "
            "VALUES ('creator', 'C', 'User', 'creator@example.com');"
        )
        user_id = self.conn.execute("SELECT id FROM users WHERE username = 'creator';").fetchone()[0]

        sql = """
            INSERT INTO documents
                (document_type, document_date, title, filename, file_path, created_by)
            VALUES (?, ?, ?, ?, ?, ?);
        """
        invalid_dates = ["2026/08/08", "08-08-2026", "20260808", "August 8, 2026"]
        for d in invalid_dates:
            with self.subTest(document_date=d):
                with self.assertRaises(IntegrityError):
                    self.conn.execute(
                        sql,
                        ("invoice", d, "Bad date", "bad.pdf", "bad.pdf", user_id),
                    )

    # ------------------------------------------------------------------
    # miles
    # ------------------------------------------------------------------
    def test_miles_table_exists(self) -> None:
        self.assertTrue(self._table_exists("miles"))
        columns = self._column_names("miles")
        expected = {
            "id",
            "business_id",
            "miles_date",
            "tenth_miles",
            "tenth_miles_begin",
            "tenth_miles_end",
            "explanation",
            "vehicle",
            "created_at",
            "created_by",
            "updated_at",
            "updated_by",
            "deleted_at",
            "deleted_by",
        }
        self.assertTrue(expected.issubset(set(columns)))

    def test_miles_insert_valid(self) -> None:
        self.conn.execute(
            "INSERT OR IGNORE INTO users (username, first_name, last_name, email) "
            "VALUES ('creator', 'C', 'User', 'creator@example.com');"
        )
        user_id = self.conn.execute("SELECT id FROM users WHERE username = 'creator';").fetchone()[0]

        self.conn.execute(
            """
            INSERT OR IGNORE INTO businesses
                (title, tax_id, established, tax_year_end_month, created_by)
            VALUES ('Test Biz', '11-1111111', '2020-01-01', 12, ?);
            """,
            (user_id,),
        )
        biz_id = self.conn.execute("SELECT id FROM businesses WHERE title = 'Test Biz';").fetchone()[0]

        sql = """
            INSERT INTO miles
                (business_id, miles_date, tenth_miles, tenth_miles_begin,
                 tenth_miles_end, explanation, vehicle, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """
        self.conn.execute(
            sql,
            (biz_id, "2026-08-01", 125, 10000, 10125, "Client visit", "Toyota", user_id),
        )
        self.conn.commit()

        row = self.conn.execute("SELECT * FROM miles WHERE explanation = 'Client visit';").fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row[3], 125)
        self.assertEqual(row[4], 10000)
        self.assertEqual(row[5], 10125)

    def test_miles_begin_end_checks(self) -> None:
        self.conn.execute(
            "INSERT OR IGNORE INTO users (username, first_name, last_name, email) "
            "VALUES ('creator', 'C', 'User', 'creator@example.com');"
        )
        user_id = self.conn.execute("SELECT id FROM users WHERE username = 'creator';").fetchone()[0]

        self.conn.execute(
            """
            INSERT OR IGNORE INTO businesses
                (title, tax_id, established, tax_year_end_month, created_by)
            VALUES ('Test Biz', '11-1111111', '2020-01-01', 12, ?);
            """,
            (user_id,),
        )
        biz_id = self.conn.execute("SELECT id FROM businesses WHERE title = 'Test Biz';").fetchone()[0]

        sql = """
            INSERT INTO miles
                (business_id, miles_date, tenth_miles, tenth_miles_begin,
                 tenth_miles_end, explanation, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?);
        """
        # Negative begin
        with self.assertRaises(IntegrityError):
            self.conn.execute(sql, (biz_id, "2026-08-02", 10, -1, 9, "neg begin", user_id))

        # Negative end
        with self.assertRaises(IntegrityError):
            self.conn.execute(sql, (biz_id, "2026-08-02", 10, 0, -5, "neg end", user_id))

        # end <= begin
        with self.assertRaises(IntegrityError):
            self.conn.execute(sql, (biz_id, "2026-08-02", 10, 100, 100, "equal", user_id))
        with self.assertRaises(IntegrityError):
            self.conn.execute(sql, (biz_id, "2026-08-02", 10, 100, 50, "end < begin", user_id))

    # ------------------------------------------------------------------
    # accounting_transaction_documents (junction)
    # ------------------------------------------------------------------
    def test_accounting_transaction_documents_table_exists(self) -> None:
        self.assertTrue(self._table_exists("accounting_transaction_documents"))

    # ------------------------------------------------------------------
    # History / audit tables
    # ------------------------------------------------------------------
    def test_accounts_history_table_exists(self) -> None:
        self.assertTrue(self._table_exists("accounts_history"))
        columns = self._column_names("accounts_history")
        expected = {
            "id",
            "account_id",
            "account_number",
            "account_name",
            "account_type",
            "description",
            "is_account_active",
            "updated_at",
            "updated_by",
        }
        self.assertTrue(expected.issubset(set(columns)))

    def test_transaction_lines_history_table_exists(self) -> None:
        self.assertTrue(self._table_exists("transaction_lines_history"))
        columns = self._column_names("transaction_lines_history")
        expected = {
            "id",
            "transaction_line_id",
            "transaction_id",
            "account_id",
            "amount_cents",
            "is_debit",
            "updated_at",
            "updated_by",
        }
        self.assertTrue(expected.issubset(set(columns)))

    def test_accounting_transactions_history_table_exists(self) -> None:
        self.assertTrue(self._table_exists("accounting_transactions_history"))
        columns = self._column_names("accounting_transactions_history")
        expected = {
            "id",
            "transaction_id",
            "transaction_date",
            "description",
            "posting_reference",
            "updated_at",
            "updated_by",
        }
        self.assertTrue(expected.issubset(set(columns)))

    def test_documents_history_table_exists(self) -> None:
        self.assertTrue(self._table_exists("documents_history"))

    def test_miles_history_table_exists(self) -> None:
        self.assertTrue(self._table_exists("miles_history"))

    # ------------------------------------------------------------------
    # Basic smoke test that all expected tables are present
    # ------------------------------------------------------------------
    def test_all_expected_tables_present(self) -> None:
        expected_tables = {
            "users",
            "businesses",
            "miles",
            "accounts",
            "accounting_transactions",
            "documents",
            "accounting_transaction_documents",
            "transaction_lines",
            "accounts_history",
            "transaction_lines_history",
            "accounting_transactions_history",
            "documents_history",
            "miles_history",
        }
        sql = "SELECT name FROM sqlite_master WHERE type = 'table';"
        existing = {row[0] for row in self.conn.execute(sql).fetchall()}
        missing = expected_tables - existing
        self.assertEqual(missing, set(), f"Missing tables: {missing}")


if __name__ == "__main__":
    unittest.main()
