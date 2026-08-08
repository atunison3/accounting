# tests/test_repositories.py
from __future__ import annotations

import unittest
from datetime import date

from accounting.application.repositories import (
    AccountRepository,
    BusinessRepository,
    TransactionRepository,
    UserRepository,
)
from accounting.domain.models import (
    Account,
    AccountingTransaction,
    TransactionLine,
)


class TestRepositoryInterfaces(unittest.TestCase):
    """Tests for the repository interface classes."""

    def test_transaction_repository_has_expected_methods(self) -> None:
        expected = {"add", "get_by_id", "get_lines", "delete"}
        actual = {
            name
            for name in dir(TransactionRepository)
            if not name.startswith("_") and callable(getattr(TransactionRepository, name))
        }
        self.assertTrue(
            expected.issubset(actual),
            f"Missing methods on TransactionRepository: {expected - actual}",
        )

    def test_account_repository_has_expected_methods(self) -> None:
        expected = {"add", "get_by_id", "get_by_number", "get_for_business"}
        actual = {
            name
            for name in dir(AccountRepository)
            if not name.startswith("_") and callable(getattr(AccountRepository, name))
        }
        self.assertTrue(
            expected.issubset(actual),
            f"Missing methods on AccountRepository: {expected - actual}",
        )

    def test_user_repository_has_expected_methods(self) -> None:
        expected = {"add", "get_by_id", "get_by_username"}
        actual = {
            name for name in dir(UserRepository) if not name.startswith("_") and callable(getattr(UserRepository, name))
        }
        self.assertTrue(
            expected.issubset(actual),
            f"Missing methods on UserRepository: {expected - actual}",
        )

    def test_business_repository_has_expected_methods(self) -> None:
        expected = {"add", "get_by_id", "get_all"}
        actual = {
            name
            for name in dir(BusinessRepository)
            if not name.startswith("_") and callable(getattr(BusinessRepository, name))
        }
        self.assertTrue(
            expected.issubset(actual),
            f"Missing methods on BusinessRepository: {expected - actual}",
        )

    def test_can_instantiate_interfaces(self) -> None:
        """Plain classes can be instantiated (even if methods are not implemented)."""
        TransactionRepository()
        AccountRepository()
        UserRepository()
        BusinessRepository()

    def test_interface_methods_exist_and_are_callable(self) -> None:
        repo = TransactionRepository()
        self.assertTrue(callable(repo.add))
        self.assertTrue(callable(repo.get_by_id))
        self.assertTrue(callable(repo.get_lines))
        self.assertTrue(callable(repo.delete))


class TestRepositoryMethodSignatures(unittest.TestCase):
    """Light checks that the methods accept the expected arguments."""

    def test_transaction_repository_add_signature(self) -> None:
        repo = TransactionRepository()
        tx = AccountingTransaction(
            transaction_date=date(2026, 8, 7),
            description="Test",
        )
        lines = [
            TransactionLine(
                transaction_id=0,
                account_id=1,
                amount_cents=1000,
                is_debit=True,
            )
        ]
        # Should not raise TypeError about unexpected arguments
        # (it may raise NotImplementedError or just return None/Ellipsis)
        try:
            repo.add(tx, lines, user_id=1)
        except TypeError as e:
            self.fail(f"add() has unexpected signature: {e}")
        except NotImplementedError:
            pass

    def test_account_repository_methods_signatures(self) -> None:
        repo = AccountRepository()
        account = Account(
            business_id=1,
            account_number=1000,
            account_name="Cash",
            account_type="Asset",  # type: ignore[arg-type]
        )
        try:
            repo.add(account)
            repo.get_by_id(1)
            repo.get_by_number(1, 1000)
            repo.get_for_business(1)
        except TypeError as e:
            self.fail(f"AccountRepository method has unexpected signature: {e}")
        except NotImplementedError:
            pass


if __name__ == "__main__":
    unittest.main()
