import unittest
from datetime import date

from accounting.application.services import AccountingService, AnalyticsService
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

    def test_balance_sheet_shows_current_period_loss_in_equity(self) -> None:
        capital_id = SqliteAccountRepository(self.connection).add(
            Account(
                business_id=self.business_id,
                account_number=3000,
                account_name="Owner's Capital",
                account_type=AccountType.EQUITY,
                is_debit=False,
                created_by=self.user_id,
            )
        )
        expense_id = SqliteAccountRepository(self.connection).add(
            Account(
                business_id=self.business_id,
                account_number=5100,
                account_name="Supplies Expense",
                account_type=AccountType.EXPENSE,
                created_by=self.user_id,
            )
        )
        service = AccountingService(SqliteTransactionRepository(self.connection))
        for description, debit_id, credit_id in [
            ("Owner contribution", self.cash_id, capital_id),
            ("Supplies purchase", expense_id, self.cash_id),
        ]:
            service.create_transaction(
                business_id=self.business_id,
                transaction_date=date(2026, 8, 18),
                description=description,
                lines=[
                    TransactionLine(transaction_id=0, account_id=debit_id, amount_cents=254677, is_debit=True),
                    TransactionLine(transaction_id=0, account_id=credit_id, amount_cents=254677, is_debit=False),
                ],
                user_id=self.user_id,
            )
        statement = AnalyticsService(
            SqliteTransactionRepository(self.connection), SqliteAccountRepository(self.connection)
        ).balance_sheet(self.business_id, date(2026, 8, 30))
        self.assertEqual(statement["current_period_earnings_usd_cents"], -254677)
        self.assertEqual(statement["owner_equity_total_usd_cents"], 0)
        self.assertEqual(statement["assets_total_usd_cents"], statement["liabilities_equity_total_usd_cents"])

    def test_currency_code_must_be_three_uppercase_letters(self) -> None:
        with self.assertRaises(ValidationError):
            AccountingTransaction(transaction_date=date.today(), description="Invalid", currency_code="usd")
