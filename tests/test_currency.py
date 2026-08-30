import unittest
from datetime import date

from accounting.application.services import AccountingService
from accounting.domain.currency import convert_currency
from pydantic import ValidationError

from accounting.domain.models import (
    Account,
    AccountType,
    AccountingTransaction,
    Business,
    TransactionLine,
    User,
)
from accounting.infrastructure.sqlite.connection import create_connection
from accounting.infrastructure.sqlite.repositories import (
    SqliteAccountRepository,
    SqliteBusinessRepository,
    SqliteTransactionRepository,
    SqliteUserRepository,
)


class TestTransactionCurrency(unittest.TestCase):
    def setUp(self) -> None:
        self.connection = create_connection(":memory:")
        users = SqliteUserRepository(self.connection)
        businesses = SqliteBusinessRepository(self.connection)
        accounts = SqliteAccountRepository(self.connection)
        user_id = users.add(
            User(
                username="currency-user",
                first_name="Currency",
                last_name="User",
                email="currency@example.com",
            )
        )
        business_id = businesses.add(Business(title="Currency Business", created_by=user_id))
        self.cash_id = accounts.add(
            Account(
                business_id=business_id,
                account_number=1000,
                account_name="Cash",
                account_type=AccountType.ASSET,
                created_by=user_id,
            )
        )
        self.revenue_id = accounts.add(
            Account(
                business_id=business_id,
                account_number=4000,
                account_name="Revenue",
                account_type=AccountType.REVENUE,
                created_by=user_id,
            )
        )
        self.business_id = business_id
        self.user_id = user_id

    def tearDown(self) -> None:
        self.connection.close()

    def test_currency_defaults_to_usd(self) -> None:
        transaction = AccountingTransaction(transaction_date=date(2026, 8, 29), description="USD entry")
        self.assertEqual(transaction.currency_code, "USD")

    def test_currency_is_persisted_and_returned(self) -> None:
        service = AccountingService(SqliteTransactionRepository(self.connection))
        transaction_id = service.create_transaction(
            business_id=self.business_id,
            currency_code="EUR",
            transaction_date=date(2026, 8, 29),
            description="Euro sale",
            lines=[
                TransactionLine(transaction_id=0, account_id=self.cash_id, amount_cents=1000, is_debit=True),
                TransactionLine(transaction_id=0, account_id=self.revenue_id, amount_cents=1000, is_debit=False),
            ],
            user_id=self.user_id,
        )
        transaction = SqliteTransactionRepository(self.connection).get_by_id(transaction_id)
        if transaction is None:
            self.fail("Transaction was not persisted")
        self.assertEqual(transaction.currency_code, "EUR")

    def test_thai_baht_converts_to_usd_and_legacy_alias_is_supported(self) -> None:
        self.assertEqual(convert_currency(3300, "THB"), 100)
        self.assertEqual(convert_currency(100, "USD", "THB"), 3300)
        self.assertEqual(convert_currency(3300, "TBH"), 100)

    def test_currency_code_must_be_three_uppercase_letters(self) -> None:
        with self.assertRaises(ValidationError):
            AccountingTransaction(transaction_date=date.today(), description="Invalid", currency_code="usd")
