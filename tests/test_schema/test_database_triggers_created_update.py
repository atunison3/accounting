# test_database_triggers_created_update.py
import unittest
from sqlite3 import IntegrityError, Connection

from accounting.infrastructure.sqlite.connection import create_connection

IMMUTABLE_CREATED_FIELD_TABLES = {
    "businesses",
    "accounts",
    "accounting_transactions",
    "documents",
    "accounting_transaction_documents",
    "transaction_lines",
}


class TestDatabaseTriggersCreatedUpdate(unittest.TestCase):
    """
    Tests that the BEFORE UPDATE triggers correctly prevent any modification
    of created_at and created_by columns on the relevant tables.
    """

    conn: Connection
    user_id: int
    business_id: int

    @classmethod
    def setUpClass(cls) -> None:
        cls.conn = create_connection(":memory:")

        # Seed a single user that can be referenced by foreign keys
        cls.conn.execute("""
            INSERT INTO users (username, first_name, last_name, email)
            VALUES ('creator', 'C', 'User', 'creator@example.com');
            """)
        cls.user_id = cls.conn.execute("SELECT id FROM users WHERE username = 'creator';").fetchone()[0]

        # Seed a business required by accounts and miles
        cls.conn.execute(
            """
            INSERT INTO businesses
                (title, tax_id, established, tax_year_end_month, created_by)
            VALUES ('Trigger Test Biz', '11-1111111', '2020-01-01', 12, ?);
            """,
            (cls.user_id,),
        )
        cls.business_id = cls.conn.execute("SELECT id FROM businesses WHERE title = 'Trigger Test Biz';").fetchone()[0]

        cls.conn.commit()

    def _assert_created_fields_immutable(self, table: str, row_id: int) -> None:
        """
        Helper: attempt to modify created_at and created_by on the given row
        and assert that both attempts raise IntegrityError.
        """
        if table not in IMMUTABLE_CREATED_FIELD_TABLES:
            raise ValueError(f"Invalid table: {table}")

        created_at = "2000-01-01 00:00:00"
        created_by = self.user_id

        with self.assertRaises(IntegrityError):
            self.conn.execute(
                f"UPDATE {table} SET created_at = ? WHERE id = ?;",  # nosec: B608
                (created_at, row_id),
            )

        with self.assertRaises(IntegrityError):
            self.conn.execute(
                f"UPDATE {table} SET created_by = ? WHERE id = ?;",  # nosec: B608
                (created_by, row_id),
            )

        with self.assertRaises(IntegrityError):
            self.conn.execute(
                f"UPDATE {table} SET created_at = ?, created_by = ? WHERE id = ?;",  # nosec: B608
                (created_at, created_by, row_id),
            )

    # ------------------------------------------------------------------
    # businesses
    # ------------------------------------------------------------------
    def test_businesses_prevent_created_update(self) -> None:
        self.conn.execute(
            """
            INSERT INTO businesses
                (title, tax_id, established, tax_year_end_month, created_by)
            VALUES ('Biz Prevent Created', '22-2222222', '2021-05-15', 6, ?);
            """,
            (self.user_id,),
        )
        row_id = self.conn.execute("SELECT id FROM businesses WHERE title = 'Biz Prevent Created';").fetchone()[0]

        self._assert_created_fields_immutable("businesses", row_id)

        # Legitimate update that does not touch created_* must succeed
        self.conn.execute(
            "UPDATE businesses SET title = 'Biz Prevent Created Updated' WHERE id = ?;",
            (row_id,),
        )
        title = self.conn.execute("SELECT title FROM businesses WHERE id = ?;", (row_id,)).fetchone()[0]
        self.assertEqual(title, "Biz Prevent Created Updated")

    # ------------------------------------------------------------------
    # accounts
    # ------------------------------------------------------------------
    def test_accounts_prevent_created_update(self) -> None:
        self.conn.execute(
            """
            INSERT INTO accounts
                (business_id, account_number, account_name, account_type,
                 description, created_by)
            VALUES (?, 210, 'Accounts Payable', 'Liability', 'AP', ?);
            """,
            (self.business_id, self.user_id),
        )
        row_id = self.conn.execute(
            "SELECT id FROM accounts WHERE account_number = 210 AND business_id = ?;",
            (self.business_id,),
        ).fetchone()[0]

        self._assert_created_fields_immutable("accounts", row_id)

        # Legitimate update
        self.conn.execute(
            "UPDATE accounts SET description = 'Updated AP' WHERE id = ?;",
            (row_id,),
        )
        desc = self.conn.execute("SELECT description FROM accounts WHERE id = ?;", (row_id,)).fetchone()[0]
        self.assertEqual(desc, "Updated AP")

    # ------------------------------------------------------------------
    # accounting_transactions
    # ------------------------------------------------------------------
    def test_accounting_transactions_prevent_created_update(self) -> None:
        self.conn.execute(
            """
            INSERT INTO accounting_transactions
                (transaction_date, description, posting_reference, created_by)
            VALUES ('2026-03-15', 'Prevent created test', 'GJ-PREVENT', ?);
            """,
            (self.user_id,),
        )
        row_id = self.conn.execute(
            "SELECT id FROM accounting_transactions WHERE posting_reference = 'GJ-PREVENT';"
        ).fetchone()[0]

        self._assert_created_fields_immutable("accounting_transactions", row_id)

        # Legitimate update
        self.conn.execute(
            """
            UPDATE accounting_transactions
            SET description = 'Prevent created test - updated'
            WHERE id = ?;
            """,
            (row_id,),
        )
        desc = self.conn.execute(
            "SELECT description FROM accounting_transactions WHERE id = ?;",
            (row_id,),
        ).fetchone()[0]
        self.assertEqual(desc, "Prevent created test - updated")

    # ------------------------------------------------------------------
    # documents
    # ------------------------------------------------------------------
    def test_documents_prevent_created_update(self) -> None:
        self.conn.execute(
            """
            INSERT INTO documents
                (document_type, document_date, title, filename, file_path, created_by)
            VALUES ('invoice', '2026-04-01', 'Prevent Created Doc',
                    'prevent.pdf', '/docs/prevent.pdf', ?);
            """,
            (self.user_id,),
        )
        row_id = self.conn.execute("SELECT id FROM documents WHERE filename = 'prevent.pdf';").fetchone()[0]

        self._assert_created_fields_immutable("documents", row_id)

        # Legitimate update
        self.conn.execute(
            "UPDATE documents SET title = 'Prevent Created Doc Updated' WHERE id = ?;",
            (row_id,),
        )
        title = self.conn.execute("SELECT title FROM documents WHERE id = ?;", (row_id,)).fetchone()[0]
        self.assertEqual(title, "Prevent Created Doc Updated")

    # ------------------------------------------------------------------
    # accounting_transaction_documents
    # ------------------------------------------------------------------
    def test_accounting_transaction_documents_prevent_created_update(self) -> None:
        # Need a transaction and a document first
        self.conn.execute(
            """
            INSERT INTO accounting_transactions
                (transaction_date, description, posting_reference, created_by)
            VALUES ('2026-05-01', 'Junction test tx', 'GJ-JUNC', ?);
            """,
            (self.user_id,),
        )
        tx_id = self.conn.execute(
            "SELECT id FROM accounting_transactions WHERE posting_reference = 'GJ-JUNC';"
        ).fetchone()[0]

        self.conn.execute(
            """
            INSERT INTO documents
                (document_type, document_date, title, filename, file_path, created_by)
            VALUES ('receipt', '2026-05-01', 'Junction Doc',
                    'junc.pdf', '/docs/junc.pdf', ?);
            """,
            (self.user_id,),
        )
        doc_id = self.conn.execute("SELECT id FROM documents WHERE filename = 'junc.pdf';").fetchone()[0]

        # The table uses a plain INTEGER PRIMARY KEY (no AUTOINCREMENT)
        self.conn.execute(
            """
            INSERT INTO accounting_transaction_documents
                (id, transction_id, document_id, created_by)
            VALUES (1, ?, ?, ?);
            """,
            (tx_id, doc_id, self.user_id),
        )
        row_id = 1

        self._assert_created_fields_immutable("accounting_transaction_documents", row_id)

        # Legitimate update (note the typo in the column name in the schema)
        self.conn.execute(
            """
            UPDATE accounting_transaction_documents
            SET updated_by = ?
            WHERE id = ?;
            """,
            (self.user_id, row_id),
        )
        updated_by = self.conn.execute(
            "SELECT updated_by FROM accounting_transaction_documents WHERE id = ?;",
            (row_id,),
        ).fetchone()[0]
        self.assertEqual(updated_by, self.user_id)

    # ------------------------------------------------------------------
    # transaction_lines
    # ------------------------------------------------------------------
    def test_transaction_lines_prevent_created_update(self) -> None:
        # Prerequisites: account + transaction
        self.conn.execute(
            """
            INSERT OR IGNORE INTO accounts
                (business_id, account_number, account_name, account_type,
                 description, created_by)
            VALUES (?, 110, 'Cash', 'Asset', 'Cash', ?);
            """,
            (self.business_id, self.user_id),
        )
        account_id = self.conn.execute(
            "SELECT id FROM accounts WHERE account_number = 110 AND business_id = ?;",
            (self.business_id,),
        ).fetchone()[0]

        self.conn.execute(
            """
            INSERT INTO accounting_transactions
                (transaction_date, description, posting_reference, created_by)
            VALUES ('2026-06-01', 'Line prevent test', 'GJ-LINE', ?);
            """,
            (self.user_id,),
        )
        tx_id = self.conn.execute(
            "SELECT id FROM accounting_transactions WHERE posting_reference = 'GJ-LINE';"
        ).fetchone()[0]

        self.conn.execute(
            """
            INSERT INTO transaction_lines
                (transaction_id, account_id, amount_cents, is_debit, created_by)
            VALUES (?, ?, 50000, 1, ?);
            """,
            (tx_id, account_id, self.user_id),
        )
        row_id = self.conn.execute(
            "SELECT id FROM transaction_lines WHERE transaction_id = ? AND account_id = ?;",
            (tx_id, account_id),
        ).fetchone()[0]

        self._assert_created_fields_immutable("transaction_lines", row_id)

        # Legitimate update
        self.conn.execute(
            "UPDATE transaction_lines SET amount_cents = 75000 WHERE id = ?;",
            (row_id,),
        )
        amount = self.conn.execute("SELECT amount_cents FROM transaction_lines WHERE id = ?;", (row_id,)).fetchone()[0]
        self.assertEqual(amount, 75000)

    # ------------------------------------------------------------------
    # miles
    # ------------------------------------------------------------------
    def test_miles_prevent_created_update(self) -> None:
        self.conn.execute(
            """
            INSERT INTO miles
                (business_id, miles_date, tenth_miles, tenth_miles_begin,
                 tenth_miles_end, explanation, vehicle, created_by)
            VALUES (?, '2026-07-01', 85, 20000, 20085, 'Prevent created miles', 'Honda', ?);
            """,
            (self.business_id, self.user_id),
        )
        row_id = self.conn.execute("SELECT id FROM miles WHERE explanation = 'Prevent created miles';").fetchone()[0]

        self._assert_created_fields_immutable("miles", row_id)

        # Legitimate update
        self.conn.execute(
            "UPDATE miles SET explanation = 'Prevent created miles - updated' WHERE id = ?;",
            (row_id,),
        )
        explanation = self.conn.execute("SELECT explanation FROM miles WHERE id = ?;", (row_id,)).fetchone()[0]
        self.assertEqual(explanation, "Prevent created miles - updated")


if __name__ == "__main__":
    unittest.main()
