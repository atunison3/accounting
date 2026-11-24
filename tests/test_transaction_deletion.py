"""Soft-delete UI and history regression tests using temporary SQLite ledgers."""

import unittest
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from fastapi.testclient import TestClient

from accounting.application.services import AccountingService
from accounting.domain.models import (
    Account,
    AccountType,
    AccountingTransactionDocument,
    Business,
    Document,
    TransactionLine,
    User,
)
from accounting.infrastructure.sqlite.connection import get_connection
from accounting.infrastructure.sqlite.repositories import (
    SqliteAccountRepository,
    SqliteBusinessRepository,
    SqliteDocumentRepository,
    SqliteTransactionDocumentRepository,
    SqliteTransactionRepository,
    SqliteUserRepository,
)
from accounting.website.app import create_app


class TestTransactionDeletion(unittest.TestCase):
    def setUp(self) -> None:
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.database = Path(temporary.name) / "ledger.db"
        with get_connection(self.database) as connection:
            self.user_id = SqliteUserRepository(connection).add(
                User(
                    username="test",
                    first_name="Test",
                    last_name="User",
                    email="test@example.com",
                )
            )
            self.business_id = SqliteBusinessRepository(connection).add(
                Business(title="Test business", created_by=self.user_id)
            )
            self.account_ids = [
                SqliteAccountRepository(connection).add(
                    Account(
                        business_id=self.business_id,
                        account_number=number,
                        account_name=name,
                        account_type=kind,
                        created_by=self.user_id,
                    )
                )
                for number, name, kind in [(1000, "Cash", AccountType.ASSET), (4000, "Sales", AccountType.REVENUE)]
            ]
            self.transaction_id = AccountingService(SqliteTransactionRepository(connection)).create_transaction(
                transaction_date=date(2026, 1, 15),
                description="Test sale",
                lines=self.lines(1250),
                user_id=self.user_id,
                business_id=self.business_id,
            )
            self.document_id = SqliteDocumentRepository(connection).add(
                Document(
                    document_type="receipt",
                    document_date=date(2026, 1, 15),
                    filename="receipt.pdf",
                    file_path="/unused/receipt.pdf",
                    created_by=self.user_id,
                )
            )
            SqliteTransactionDocumentRepository(connection).add(
                AccountingTransactionDocument(
                    transaction_id=self.transaction_id,
                    document_id=self.document_id,
                    created_by=self.user_id,
                )
            )
        app = create_app()
        app.state.db_path = self.database
        self.client = TestClient(app)
        self.addCleanup(self.client.close)
        self.delete_url = f"/transactions/{self.transaction_id}/delete"
        self.filters = {"business_id": str(self.business_id), "date_from": "2026-01-01", "date_to": "2026-01-31"}

    def lines(self, amount: int) -> list[TransactionLine]:
        return [
            TransactionLine(transaction_id=0, account_id=account_id, amount_cents=amount, is_debit=index == 0)
            for index, account_id in enumerate(self.account_ids)
        ]

    def delete(self, **overrides):
        data = {"user_id": str(self.user_id), "confirm": "true", **overrides}
        return self.client.post(self.delete_url, data=data, follow_redirects=False)

    def test_edit_page_has_separate_delete_form_and_confirmation(self) -> None:
        response = self.client.get(f"/transactions/{self.transaction_id}/edit")
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.delete_url, response.text)
        self.assertIn("Delete transaction", response.text)
        self.assertIn("window.confirm('Please confirm:", response.text)
        self.assertIn('name="confirm" type="checkbox" value="true" required', response.text)
        self.assertEqual(response.text.count('<form '), 2)
        history = self.client.get("/transactions", params=self.filters)
        self.assertIn("Include deleted transactions", history.text)
        self.assertIn("Deleted (read-only)", history.text)

    def test_missing_or_false_confirmation_never_deletes(self) -> None:
        for data in [{"user_id": str(self.user_id)}, {"user_id": str(self.user_id), "confirm": "false"}]:
            with self.subTest(data=data):
                response = self.client.post(self.delete_url, data=data)
                self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.get(self.delete_url).status_code, 405)
        with get_connection(self.database) as connection:
            self.assertIsNotNone(SqliteTransactionRepository(connection).get_by_id(self.transaction_id))
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM accounting_transactions_history").fetchone()[0], 0
            )

    def test_confirmed_delete_is_audited_and_hidden_by_default(self) -> None:
        response = self.delete()
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["location"], f"/transactions?business_id={self.business_id}")
        with get_connection(self.database) as connection:
            header = connection.execute(
                "SELECT * FROM accounting_transactions WHERE id=?", (self.transaction_id,)
            ).fetchone()
            self.assertIsNotNone(header["deleted_at"])
            self.assertEqual(header["deleted_by"], self.user_id)
            lines = connection.execute(
                "SELECT * FROM transaction_lines WHERE transaction_id=?", (self.transaction_id,)
            ).fetchall()
            self.assertEqual(len(lines), 2)
            self.assertTrue(all(line["deleted_at"] == header["deleted_at"] for line in lines))
            self.assertTrue(all(line["deleted_by"] == self.user_id for line in lines))
            self.assertGreater(
                connection.execute("SELECT COUNT(*) FROM accounting_transactions_history").fetchone()[0], 0
            )
            self.assertEqual(
                len(SqliteTransactionDocumentRepository(connection).get_for_transaction(self.transaction_id)), 1
            )
            self.assertEqual(
                AccountingService(SqliteTransactionRepository(connection)).list_transactions(self.business_id), []
            )
        self.assertEqual(self.client.get("/api/transactions", params=self.filters).json(), [])
        self.assertEqual(self.client.get(f"/transactions/{self.transaction_id}/edit").status_code, 404)
        self.assertEqual(self.delete().status_code, 404)

    def test_include_deleted_shows_final_lines_not_superseded_edits(self) -> None:
        with get_connection(self.database) as connection:
            with patch(
                "accounting.infrastructure.sqlite.repositories._utcnow", return_value="2026-01-16T12:00:00+00:00"
            ):
                AccountingService(SqliteTransactionRepository(connection)).update_transaction(
                    self.transaction_id,
                    date(2026, 1, 15),
                    "Corrected sale",
                    self.lines(1500),
                    self.user_id,
                    business_id=self.business_id,
                )
        with patch("accounting.infrastructure.sqlite.repositories._utcnow", return_value="2026-01-17T12:00:00+00:00"):
            self.assertEqual(self.delete().status_code, 303)
        response = self.client.get("/api/transactions", params={**self.filters, "include_deleted": "true"})
        self.assertEqual(response.status_code, 200)
        rows = response.json()
        self.assertEqual(len(rows), 2)
        self.assertEqual({row["amount_cents"] for row in rows}, {1500})
        self.assertTrue(all(row["deleted_at"] and row["deleted_by"] == self.user_id for row in rows))
        self.assertTrue(all(row["has_document"] for row in rows))
        self.assertTrue(all(row["description"] == "Corrected sale" for row in rows))
        with get_connection(self.database) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM transaction_lines").fetchone()[0], 4)

    def test_history_preserves_business_date_account_and_document_filters(self) -> None:
        self.delete()
        params = {**self.filters, "include_deleted": "true", "account_number": "1000", "has_document": "true"}
        rows = self.client.get("/api/transactions", params=params).json()
        self.assertEqual(len(rows), 1)
        for override in [
            {"business_id": "999"},
            {"date_from": "2026-01-16"},
            {"account_number": "9999"},
            {"has_document": "false"},
            {"amount_min": "20"},
        ]:
            with self.subTest(override=override):
                self.assertEqual(self.client.get("/api/transactions", params={**params, **override}).json(), [])

    def test_invalid_audit_user_rolls_back_and_external_redirect_is_rejected(self) -> None:
        self.assertEqual(self.delete(user_id="99999").status_code, 422)
        self.assertEqual(self.delete(user_id="0").status_code, 422)
        with get_connection(self.database) as connection:
            self.assertIsNotNone(SqliteTransactionRepository(connection).get_by_id(self.transaction_id))
        response = self.delete(return_to="//evil.example")
        self.assertEqual(response.headers["location"], f"/transactions?business_id={self.business_id}")

    def test_delete_retains_safe_history_filters(self) -> None:
        destination = f"/transactions?business_id={self.business_id}&include_deleted=true&days=365"
        response = self.delete(return_to=destination)
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["location"], destination)


if __name__ == "__main__":
    unittest.main()
