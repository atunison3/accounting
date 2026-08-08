# tests/test_services.py
from __future__ import annotations

import unittest
from datetime import date
from unittest.mock import MagicMock

from accounting.application.services import AccountingService
from accounting.domain.models import AccountingTransaction, TransactionLine


class TestAccountingService(unittest.TestCase):
    def setUp(self) -> None:
        self.mock_repo = MagicMock()
        self.service = AccountingService(repository=self.mock_repo)
        self.user_id = 1
        self.today = date(2026, 8, 7)

    def _make_balanced_lines(self) -> list[TransactionLine]:
        """Two-line balanced transaction (debit + credit)."""
        return [
            TransactionLine(
                transaction_id=0,
                account_id=100,
                amount_cents=15000,
                is_debit=True,
            ),
            TransactionLine(
                transaction_id=0,
                account_id=400,
                amount_cents=15000,
                is_debit=False,
            ),
        ]

    # -------------------------------------------------------------------------
    # create_transaction
    # -------------------------------------------------------------------------

    def test_create_transaction_success(self) -> None:
        lines = self._make_balanced_lines()
        self.mock_repo.create_transaction.return_value = 42

        result = self.service.create_transaction(
            transaction_date=self.today,
            description="Cash sale",
            lines=lines,
            user_id=self.user_id,
            posting_reference="INV-1001",
        )

        self.assertEqual(result, 42)
        self.mock_repo.create_transaction.assert_called_once()
        args, kwargs = self.mock_repo.create_transaction.call_args

        # Check the transaction object that was passed
        tx = kwargs["transaction"]
        self.assertIsInstance(tx, AccountingTransaction)
        self.assertEqual(tx.transaction_date, self.today)
        self.assertEqual(tx.description, "Cash sale")
        self.assertEqual(tx.posting_reference, "INV-1001")
        self.assertEqual(tx.created_by, self.user_id)
        self.assertEqual(tx.updated_by, self.user_id)

        self.assertEqual(kwargs["lines"], lines)
        self.assertEqual(kwargs["user_id"], self.user_id)

    def test_create_transaction_raises_when_fewer_than_two_lines(self) -> None:
        lines = [
            TransactionLine(
                transaction_id=0,
                account_id=100,
                amount_cents=1000,
                is_debit=True,
            )
        ]

        with self.assertRaises(ValueError) as ctx:
            self.service.create_transaction(
                transaction_date=self.today,
                description="Invalid",
                lines=lines,
                user_id=self.user_id,
            )

        self.assertIn("at least two transaction lines", str(ctx.exception))
        self.mock_repo.create_transaction.assert_not_called()

    def test_create_transaction_raises_when_unbalanced(self) -> None:
        lines = [
            TransactionLine(
                transaction_id=0,
                account_id=100,
                amount_cents=15000,
                is_debit=True,
            ),
            TransactionLine(
                transaction_id=0,
                account_id=400,
                amount_cents=14000,  # not equal
                is_debit=False,
            ),
        ]

        with self.assertRaises(ValueError) as ctx:
            self.service.create_transaction(
                transaction_date=self.today,
                description="Unbalanced",
                lines=lines,
                user_id=self.user_id,
            )

        self.assertIn("Debits and credits must be equal", str(ctx.exception))
        self.mock_repo.create_transaction.assert_not_called()

    def test_create_transaction_with_no_posting_reference(self) -> None:
        lines = self._make_balanced_lines()
        self.mock_repo.create_transaction.return_value = 7

        result = self.service.create_transaction(
            transaction_date=self.today,
            description="Simple entry",
            lines=lines,
            user_id=self.user_id,
        )

        self.assertEqual(result, 7)
        tx = self.mock_repo.create_transaction.call_args.kwargs["transaction"]
        self.assertIsNone(tx.posting_reference)

    # -------------------------------------------------------------------------
    # get_transaction
    # -------------------------------------------------------------------------

    def test_get_transaction_returns_transaction(self) -> None:
        expected = AccountingTransaction(
            id=10,
            transaction_date=self.today,
            description="Test",
        )
        self.mock_repo.get_transaction.return_value = expected

        result = self.service.get_transaction(10)

        self.assertEqual(result, expected)
        self.mock_repo.get_transaction.assert_called_once_with(10)

    def test_get_transaction_returns_none_when_not_found(self) -> None:
        self.mock_repo.get_transaction.return_value = None

        result = self.service.get_transaction(999)

        self.assertIsNone(result)
        self.mock_repo.get_transaction.assert_called_once_with(999)

    # -------------------------------------------------------------------------
    # get_transaction_lines
    # -------------------------------------------------------------------------

    def test_get_transaction_lines(self) -> None:
        lines = self._make_balanced_lines()
        self.mock_repo.get_transaction_lines.return_value = lines

        result = self.service.get_transaction_lines(5)

        self.assertEqual(result, lines)
        self.mock_repo.get_transaction_lines.assert_called_once_with(5)

    # -------------------------------------------------------------------------
    # delete_transaction
    # -------------------------------------------------------------------------

    def test_delete_transaction_success(self) -> None:
        existing = AccountingTransaction(
            id=20,
            transaction_date=self.today,
            description="To be deleted",
        )
        self.mock_repo.get_transaction.return_value = existing

        self.service.delete_transaction(20, user_id=self.user_id)

        self.mock_repo.get_transaction.assert_called_once_with(20)
        self.mock_repo.delete_transaction.assert_called_once_with(20, self.user_id)

    def test_delete_transaction_raises_when_not_found(self) -> None:
        self.mock_repo.get_transaction.return_value = None

        with self.assertRaises(ValueError) as ctx:
            self.service.delete_transaction(999, user_id=self.user_id)

        self.assertIn("does not exist", str(ctx.exception))
        self.mock_repo.delete_transaction.assert_not_called()


if __name__ == "__main__":
    unittest.main()
