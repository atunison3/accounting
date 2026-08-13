# test_database_operation.py
import unittest
from sqlite3 import IntegrityError, Connection

from accounting.infrastructure.sqlite.connection import create_connection


class TestDatabaseAuditTableTriggers(unittest.TestCase):
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

        document = ("receipt", "2026-08-08", "receipt", "receipt.pdf", 1)
        sql = """
            INSERT INTO documents
                (document_type, document_date, filename, file_path, created_by)
            VALUES
                (?, ?, ?, ?, ?);
        """
        cls.conn.execute(sql, document)
        cls.conn.commit()

        # Force history rows to exist by performing updates that fire the audit triggers
        cls.conn.execute(
            """
            UPDATE accounts
            SET account_name = ?, updated_by = ?
            WHERE id = ?
            """,
            ("Cash Account", 1, 1),
        )
        cls.conn.execute(
            """
            UPDATE accounting_transactions
            SET description = ?, updated_by = ?
            WHERE id = ?
            """,
            ("Owner contributed cash", 1, 1),
        )
        cls.conn.execute(
            """
            UPDATE transaction_lines
            SET amount_cents = ?, updated_by = ?
            WHERE id = ?
            """,
            (150000, 1, 1),
        )
        cls.conn.commit()

    def test_accounts_history_prevent_update(self) -> None:
        sql = "SELECT id FROM accounts_history LIMIT 1"
        history_id = self.conn.execute(sql).fetchone()[0]

        with self.assertRaises(IntegrityError):
            self.conn.execute(
                """
                UPDATE accounts_history
                SET account_name = ?
                WHERE id = ?
                """,
                ("Hacked Name", history_id),
            )

    def test_accounts_history_prevent_delete(self) -> None:
        sql = "SELECT id FROM accounts_history LIMIT 1"
        history_id = self.conn.execute(sql).fetchone()[0]

        with self.assertRaises(IntegrityError):
            self.conn.execute(
                "DELETE FROM accounts_history WHERE id = ?",
                (history_id,),
            )

    def test_transaction_lines_history_prevent_update(self) -> None:
        sql = "SELECT id FROM transaction_lines_history LIMIT 1"
        history_id = self.conn.execute(sql).fetchone()[0]

        with self.assertRaises(IntegrityError):
            self.conn.execute(
                """
                UPDATE transaction_lines_history
                SET amount_cents = ?
                WHERE id = ?
                """,
                (999999, history_id),
            )

    def test_transaction_lines_history_prevent_delete(self) -> None:
        sql = "SELECT id FROM transaction_lines_history LIMIT 1"
        history_id = self.conn.execute(sql).fetchone()[0]

        with self.assertRaises(IntegrityError):
            self.conn.execute(
                "DELETE FROM transaction_lines_history WHERE id = ?",
                (history_id,),
            )

    def test_accounting_transactions_history_prevent_update(self) -> None:
        sql = "SELECT id FROM accounting_transactions_history LIMIT 1"
        history_id = self.conn.execute(sql).fetchone()[0]

        with self.assertRaises(IntegrityError):
            self.conn.execute(
                """
                UPDATE accounting_transactions_history
                SET description = ?
                WHERE id = ?
                """,
                ("Hacked description", history_id),
            )

    def test_accounting_transactions_history_prevent_delete(self) -> None:
        sql = "SELECT id FROM accounting_transactions_history LIMIT 1"
        history_id = self.conn.execute(sql).fetchone()[0]

        with self.assertRaises(IntegrityError):
            self.conn.execute(
                "DELETE FROM accounting_transactions_history WHERE id = ?",
                (history_id,),
            )

    def test_documents_history_prevent_update(self) -> None:
        # documents_history may be empty; insert a row directly so the
        # prevent-update / prevent-delete triggers can be exercised.
        self.conn.execute(
            """
            INSERT INTO documents_history (
                document_id,
                document_type,
                filename,
                file_path,
                updated_by
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (1, "receipt", "test.pdf", "test.pdf", 1),
        )
        self.conn.commit()

        sql = "SELECT id FROM documents_history LIMIT 1"
        history_id = self.conn.execute(sql).fetchone()[0]

        with self.assertRaises(IntegrityError):
            self.conn.execute(
                """
                UPDATE documents_history
                SET filename = ?
                WHERE id = ?
                """,
                ("hacked.pdf", history_id),
            )

    def test_documents_history_prevent_delete(self) -> None:
        sql = "SELECT id FROM documents_history LIMIT 1"
        row = self.conn.execute(sql).fetchone()
        if row is None:
            self.conn.execute(
                """
                INSERT INTO documents_history (
                    document_id,
                    document_type,
                    filename,
                    file_path,
                    updated_by
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (1, "receipt", "test.pdf", "test.pdf", 1),
            )
            self.conn.commit()
            history_id = self.conn.execute(sql).fetchone()[0]
        else:
            history_id = row[0]

        with self.assertRaises(IntegrityError):
            self.conn.execute(
                "DELETE FROM documents_history WHERE id = ?",
                (history_id,),
            )


if __name__ == "__main__":
    unittest.main()
