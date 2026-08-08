# # tests/test_sqlite_repositories.py
# from __future__ import annotations

# import sqlite3
# import unittest
# from datetime import date

# from accounting.domain.models import (
#     Account,
#     AccountType,
#     AccountingTransaction,
#     Business,
#     TransactionLine,
#     User,
# )
# from accounting.infrastructure.sqlite.connection import create_connection, get_connection
# from accounting.infrastructure.sqlite.repositories import (
#     SqliteAccountRepository,
#     SqliteBusinessRepository,
#     SqliteTransactionRepository,
#     SqliteUserRepository,
# )


# class TestConnection(unittest.TestCase):
#     def test_create_connection_returns_connection(self) -> None:
#         conn = create_connection(":memory:")
#         try:
#             self.assertIsInstance(conn, sqlite3.Connection)
#             # foreign keys should be enabled
#             cur = conn.execute("PRAGMA foreign_keys")
#             self.assertEqual(cur.fetchone()[0], 1)
#         finally:
#             conn.close()

#     def test_schema_is_created(self) -> None:
#         conn = create_connection(":memory:")
#         try:
#             cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
#             tables = {row[0] for row in cur.fetchall()}
#             expected = {
#                 "users",
#                 "businesses",
#                 "accounts",
#                 "accounting_transactions",
#                 "transaction_lines",
#             }
#             self.assertTrue(expected.issubset(tables), f"Missing tables: {expected - tables}")
#         finally:
#             conn.close()

#     def test_get_connection_context_manager_commits(self) -> None:
#         with get_connection(":memory:") as conn:
#             conn.execute(
#                 "INSERT INTO users (username, first_name, last_name, email) VALUES (?, ?, ?, ?)",
#                 ("alice", "Alice", "Smith", "[email protected]"),
#             )
#             # still inside the context – row should be visible
#             cur = conn.execute("SELECT COUNT(*) FROM users")
#             self.assertEqual(cur.fetchone()[0], 1)

#     def test_row_factory_is_set(self) -> None:
#         conn = create_connection(":memory:")
#         try:
#             self.assertEqual(conn.row_factory, sqlite3.Row)
#         finally:
#             conn.close()


# class TestSqliteRepositories(unittest.TestCase):
#     def setUp(self) -> None:
#         self.conn = create_connection(":memory:")
#         self.user_repo = SqliteUserRepository(self.conn)
#         self.business_repo = SqliteBusinessRepository(self.conn)
#         self.account_repo = SqliteAccountRepository(self.conn)
#         self.tx_repo = SqliteTransactionRepository(self.conn)

#     def tearDown(self) -> None:
#         self.conn.close()

#     # ------------------------------------------------------------------
#     # UserRepository
#     # ------------------------------------------------------------------

#     def test_user_add_and_get_by_id(self) -> None:
#         user = User(username="alice", first_name="Alice", last_name="Smith", email="asmith@website.org")
#         user_id = self.user_repo.add(user)
#         self.assertIsInstance(user_id, int)
#         self.assertGreater(user_id, 0)

#         loaded = self.user_repo.get_by_id(user_id)
#         self.assertIsNotNone(loaded)
#         if loaded is None:
#             raise RuntimeError
#         self.assertEqual(loaded.username, "alice")
#         self.assertEqual(loaded.first_name, "Alice")
#         self.assertEqual(loaded.email, "asmith@website.org")
#         self.assertTrue(loaded.is_active)
#         self.assertIsNone(loaded.deleted_at)

#     def test_user_get_by_username(self) -> None:
#         user = User(
#             username="bob",
#             first_name="Bob",
#             last_name="Jones",
#             email="bjones@enterprise.com",
#         )
#         self.user_repo.add(user)

#         loaded = self.user_repo.get_by_username("bob")
#         self.assertIsNotNone(loaded)
#         if loaded is None:
#             raise RuntimeError
#         self.assertEqual(loaded.username, "bob")

#         missing = self.user_repo.get_by_username("does-not-exist")
#         self.assertIsNone(missing)

#     def test_user_get_by_id_returns_none_for_missing(self) -> None:
#         self.assertIsNone(self.user_repo.get_by_id(99999))

#     # ------------------------------------------------------------------
#     # BusinessRepository
#     # ------------------------------------------------------------------

#     def test_business_add_and_get(self) -> None:
#         user = User(username="alice", first_name="Alice", last_name="Smith", email="asmith@website.org")
#         _ = self.user_repo.add(user)
#         business = Business(
#             title="Acme Corp",
#             tax_id="12-3456789",
#             established=2010,
#             created_by=1,
#         )
#         business_id = self.business_repo.add(business)
#         self.assertGreater(business_id, 0)

#         loaded = self.business_repo.get_by_id(business_id)
#         self.assertIsNotNone(loaded)
#         if loaded is None:
#             raise RuntimeError
#         self.assertEqual(loaded.title, "Acme Corp")
#         self.assertEqual(loaded.tax_id, "12-3456789")
#         self.assertEqual(loaded.established, 2010)
#         self.assertTrue(loaded.is_business_active)

#     def test_business_get_all(self) -> None:
#         user = User(username="alice", first_name="Alice", last_name="Smith", email="asmith@website.org")
#         _ = self.user_repo.add(user)
#         business = Business(
#             title="Acme Corp",
#             tax_id="12-3456789",
#             established=2010,
#             created_by=1,
#         )
#         _ = self.business_repo.add(business)
#         business = Business(
#             title="J. T. Smith Accounting",
#             tax_id="13-3456789",
#             established=2011,
#             created_by=1,
#         )
#         _ = self.business_repo.add(business)

#         all_businesses = self.business_repo.get_all()
#         titles = [b.title for b in all_businesses]
#         self.assertEqual(titles, ["Acme Corp", "J. T. Smith Accounting"])  # ordered by title

#     # ------------------------------------------------------------------
#     # AccountRepository
#     # ------------------------------------------------------------------

#     def test_account_add_and_get(self) -> None:
#         user = User(username="alice", first_name="Alice", last_name="Smith", email="asmith@website.org")
#         _ = self.user_repo.add(user)
#         business = Business(
#             title="Acme Corp",
#             tax_id="12-3456789",
#             established=2010,
#             created_by=1,
#         )
#         business_id = self.business_repo.add(business)
#         account = Account(
#             business_id=business_id,
#             account_number=1000,
#             account_name="Cash",
#             account_type=AccountType.ASSET,
#             description="Main cash account",
#             created_by=1,
#         )
#         account_id = self.account_repo.add(account)
#         self.assertGreater(account_id, 0)

#         loaded = self.account_repo.get_by_id(account_id)
#         self.assertIsNotNone(loaded)
#         if loaded is None:
#             raise RuntimeError
#         self.assertEqual(loaded.account_number, 1000)
#         self.assertEqual(loaded.account_name, "Cash")
#         self.assertEqual(loaded.account_type, AccountType.ASSET)
#         self.assertEqual(loaded.business_id, business_id)

#     def test_account_get_by_number(self) -> None:
#         business_id = self.business_repo.add(Business(title="Test Co"))
#         self.account_repo.add(
#             Account(
#                 business_id=business_id,
#                 account_number=4000,
#                 account_name="Sales",
#                 account_type=AccountType.REVENUE,
#             )
#         )

#         found = self.account_repo.get_by_number(business_id, 4000)
#         self.assertIsNotNone(found)
#         if found is None:
#             raise RuntimeError
#         self.assertEqual(found.account_name, "Sales")

#         missing = self.account_repo.get_by_number(business_id, 9999)
#         self.assertIsNone(missing)

#     def test_account_get_for_business(self) -> None:
#         business_id = self.business_repo.add(Business(title="Test Co"))
#         self.account_repo.add(
#             Account(
#                 business_id=business_id,
#                 account_number=1000,
#                 account_name="Cash",
#                 account_type=AccountType.ASSET,
#             )
#         )
#         self.account_repo.add(
#             Account(
#                 business_id=business_id,
#                 account_number=4000,
#                 account_name="Sales",
#                 account_type=AccountType.REVENUE,
#             )
#         )

#         accounts = self.account_repo.get_for_business(business_id)
#         self.assertEqual(len(accounts), 2)
#         self.assertEqual(accounts[0].account_number, 1000)
#         self.assertEqual(accounts[1].account_number, 4000)

#     # ------------------------------------------------------------------
#     # TransactionRepository
#     # ------------------------------------------------------------------

#     def _seed_accounts(self) -> tuple[int, int]:
#         """Create a business + two accounts and return (cash_id, sales_id)."""
#         business_id = self.business_repo.add(Business(title="Test Co"))
#         cash_id = self.account_repo.add(
#             Account(
#                 business_id=business_id,
#                 account_number=1000,
#                 account_name="Cash",
#                 account_type=AccountType.ASSET,
#             )
#         )
#         sales_id = self.account_repo.add(
#             Account(
#                 business_id=business_id,
#                 account_number=4000,
#                 account_name="Sales",
#                 account_type=AccountType.REVENUE,
#             )
#         )
#         return cash_id, sales_id

#     def test_transaction_add_and_get(self) -> None:
#         cash_id, sales_id = self._seed_accounts()
#         user_id = self.user_repo.add(
#             User(
#                 username="bookkeeper",
#                 first_name="Book",
#                 last_name="Keeper",
#                 email="bkeeper@savethebees.org",
#             )
#         )

#         tx = AccountingTransaction(
#             transaction_date=date(2026, 8, 7),
#             description="Cash sale",
#             posting_reference="INV-001",
#         )
#         lines = [
#             TransactionLine(
#                 transaction_id=1,
#                 account_id=cash_id,
#                 amount_cents=15000,
#                 is_debit=True,
#             ),
#             TransactionLine(
#                 transaction_id=1,
#                 account_id=sales_id,
#                 amount_cents=15000,
#                 is_debit=False,
#             ),
#         ]

#         tx_id = self.tx_repo.add(tx, lines, user_id=user_id) - 1
#         self.assertEqual(tx_id, 1)

#         loaded = self.tx_repo.get_by_id(tx_id)
#         self.assertIsNotNone(loaded)
#         if loaded is None:
#             raise RuntimeError
#         self.assertEqual(loaded.description, "Cash sale")
#         self.assertEqual(loaded.posting_reference, "INV-001")
#         self.assertEqual(loaded.transaction_date, date(2026, 8, 7))
#         self.assertEqual(loaded.created_by, user_id)

#         loaded_lines = self.tx_repo.get_lines(tx_id)
#         self.assertEqual(len(loaded_lines), 2)
#         self.assertEqual(loaded_lines[0].amount_cents, 15000)
#         self.assertTrue(loaded_lines[0].is_debit)
#         self.assertFalse(loaded_lines[1].is_debit)

#     def test_transaction_soft_delete(self) -> None:
#         cash_id, sales_id = self._seed_accounts()
#         user_id = self.user_repo.add(
#             User(
#                 username="bookkeeper",
#                 first_name="Book",
#                 last_name="Keeper",
#                 email="bkeeper@savethebees.com",
#             )
#         )

#         tx = AccountingTransaction(
#             transaction_date=date(2026, 8, 7),
#             description="To be deleted",
#         )
#         lines = [
#             TransactionLine(transaction_id=0, account_id=cash_id, amount_cents=5000, is_debit=True),
#             TransactionLine(transaction_id=0, account_id=sales_id, amount_cents=5000, is_debit=False),
#         ]
#         tx_id = self.tx_repo.add(tx, lines, user_id=user_id)

#         # Soft delete
#         self.tx_repo.delete(tx_id, user_id=user_id)

#         # Should no longer be returned
#         self.assertIsNone(self.tx_repo.get_by_id(tx_id))
#         self.assertEqual(self.tx_repo.get_lines(tx_id), [])

#     def test_transaction_get_missing_returns_none(self) -> None:
#         self.assertIsNone(self.tx_repo.get_by_id(99999))
#         self.assertEqual(self.tx_repo.get_lines(99999), [])


# if __name__ == "__main__":
#     unittest.main()
