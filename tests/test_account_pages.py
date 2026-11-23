"""Account management routes use an isolated database, never the live ledger."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

from accounting.domain.models import Account, AccountType, Business, User
from accounting.infrastructure.sqlite.connection import get_connection
from accounting.infrastructure.sqlite.repositories import (
    SqliteAccountRepository,
    SqliteBusinessRepository,
    SqliteUserRepository,
)
from accounting.website.app import create_app


class TestAccountPages(unittest.TestCase):
    def setUp(self) -> None:
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.database = Path(temporary.name) / "accounts.db"
        with get_connection(self.database) as connection:
            self.user_id = SqliteUserRepository(connection).add(
                User(username="tester", first_name="Test", last_name="User", email="test@example.com")
            )
            self.business_id = SqliteBusinessRepository(connection).add(
                Business(title="Example business", created_by=self.user_id)
            )
            self.account_id = SqliteAccountRepository(connection).add(
                Account(
                    business_id=self.business_id,
                    account_number=2300,
                    account_name="Reimbursement payable",
                    account_type=AccountType.LIABILITY,
                    is_debit=True,
                    created_by=self.user_id,
                )
            )
        app = create_app()
        app.state.db_path = self.database
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def form(self) -> dict[str, str]:
        return {
            "account_number": "2300",
            "account_name": "Reimbursement payable",
            "account_type": "Liability",
            "updated_by": str(self.user_id),
            "is_account_active": "on",
            "description": "Personally funded business expenses",
        }

    def test_chart_links_to_edit_page_and_shows_normal_balance(self) -> None:
        response = self.client.get(f"/chart-of-accounts?business_id={self.business_id}")
        self.assertEqual(response.status_code, 200)
        self.assertIn(f'/accounts/{self.account_id}/edit', response.text)
        self.assertIn("Normal balance", response.text)
        self.assertIn("Debit", response.text)
        edit = self.client.get(f"/accounts/{self.account_id}/edit")
        self.assertEqual(edit.status_code, 200)
        self.assertIn("Reimbursement payable", edit.text)
        self.assertIn('name="is_debit"', edit.text)

    def test_unchecked_debit_saves_credit_balance_and_audit(self) -> None:
        response = self.client.post(f"/accounts/{self.account_id}/edit", data=self.form(), follow_redirects=False)
        self.assertEqual(response.status_code, 303, response.text)
        self.assertEqual(response.headers["location"], f"/chart-of-accounts?business_id={self.business_id}")
        with get_connection(self.database) as connection:
            account = SqliteAccountRepository(connection).get_by_id(self.account_id)
            self.assertIsNotNone(account)
            assert account is not None
            self.assertFalse(account.is_debit)
            self.assertTrue(account.is_account_active)
            self.assertEqual(account.updated_by, self.user_id)
            self.assertEqual(account.description, "Personally funded business expenses")
            self.assertGreater(connection.execute("SELECT COUNT(*) FROM accounts_history").fetchone()[0], 0)
        page = self.client.get(f"/chart-of-accounts?business_id={self.business_id}")
        self.assertIn("Credit", page.text)

    def test_checked_debit_and_unchecked_active_are_saved(self) -> None:
        form = self.form()
        form["is_debit"] = "on"
        del form["is_account_active"]
        response = self.client.post(f"/accounts/{self.account_id}/edit", data=form, follow_redirects=False)
        self.assertEqual(response.status_code, 303)
        with get_connection(self.database) as connection:
            account = SqliteAccountRepository(connection).get_by_id(self.account_id)
            assert account is not None
            self.assertTrue(account.is_debit)
            self.assertFalse(account.is_account_active)
        page = self.client.get(f"/chart-of-accounts?business_id={self.business_id}")
        self.assertIn(f'/accounts/{self.account_id}/edit', page.text)
        self.assertIn("Inactive", page.text)

    def test_creation_with_unchecked_debit_is_credit(self) -> None:
        response = self.client.post(
            "/accounts/create",
            data={
                "business_id": str(self.business_id),
                "account_number": "2400",
                "account_name": "Another payable",
                "account_type": "Liability",
                "created_by": str(self.user_id),
            },
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 303, response.text)
        with get_connection(self.database) as connection:
            account = SqliteAccountRepository(connection).get_by_number(self.business_id, 2400)
            assert account is not None
            self.assertFalse(account.is_debit)

    def test_missing_account_returns_404(self) -> None:
        self.assertEqual(self.client.get("/accounts/99999/edit").status_code, 404)
        self.assertEqual(self.client.post("/accounts/99999/edit", data=self.form()).status_code, 404)

    def test_invalid_account_number_does_not_change_record(self) -> None:
        form = self.form()
        form["account_number"] = "0"
        response = self.client.post(f"/accounts/{self.account_id}/edit", data=form)
        self.assertEqual(response.status_code, 422)
        with get_connection(self.database) as connection:
            account = SqliteAccountRepository(connection).get_by_id(self.account_id)
            assert account is not None
            self.assertEqual(account.account_number, 2300)

    def test_duplicate_number_shows_error_and_preserves_record(self) -> None:
        with get_connection(self.database) as connection:
            SqliteAccountRepository(connection).add(
                Account(
                    business_id=self.business_id,
                    account_number=2400,
                    account_name="Other account",
                    account_type=AccountType.LIABILITY,
                    is_debit=False,
                    created_by=self.user_id,
                )
            )
        form = self.form()
        form["account_number"] = "2400"
        response = self.client.post(f"/accounts/{self.account_id}/edit", data=form)
        self.assertEqual(response.status_code, 400)
        self.assertIn("role=\"alert\"", response.text)
        self.assertIn(f'/accounts/{self.account_id}/edit', response.text)
        with get_connection(self.database) as connection:
            account = SqliteAccountRepository(connection).get_by_id(self.account_id)
            assert account is not None
            self.assertEqual(account.account_number, 2300)


if __name__ == "__main__":
    unittest.main()
