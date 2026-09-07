import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock

from accounting.application.income_statement import income_statement, statement_period
from accounting.domain.models import Account, AccountType


class TestIncomeStatement(unittest.TestCase):
    def test_last_completed_quarter(self) -> None:
        for today, start, end in [
            (date(2026, 8, 30), date(2026, 4, 1), date(2026, 6, 30)),
            (date(2026, 1, 1), date(2025, 10, 1), date(2025, 12, 31)),
            (date(2026, 3, 31), date(2025, 10, 1), date(2025, 12, 31)),
        ]:
            with self.subTest(today=today):
                self.assertEqual(statement_period(today=today), (start, end))

    def test_presets_and_custom_dates(self) -> None:
        self.assertEqual(statement_period("m2", 2024), (date(2024, 2, 1), date(2024, 2, 29)))
        self.assertEqual(statement_period("q4", 2026), (date(2026, 10, 1), date(2026, 12, 31)))
        start, end = date(2026, 1, 5), date(2026, 2, 8)
        self.assertEqual(statement_period("custom", start=start, end=end), (start, end))
        with self.assertRaises(ValueError):
            statement_period("custom", start=end, end=start)
        with self.assertRaises(ValueError):
            statement_period("q5")

    def test_conversion_reversals_and_loss(self) -> None:
        accounts = Mock()
        accounts.get_for_business.return_value = [
            Account(business_id=1, account_number=4000, account_name="Revenue", account_type=AccountType.REVENUE),
            Account(business_id=1, account_number=5000, account_name="Expense", account_type=AccountType.EXPENSE),
        ]
        transactions = Mock()
        transactions.search.return_value = [
            SimpleNamespace(account_number=4000, amount_cents=33000, currency_code="THB", is_debit=False),
            SimpleNamespace(account_number=4000, amount_cents=100, currency_code="USD", is_debit=True),
            SimpleNamespace(account_number=5000, amount_cents=2000, currency_code="USD", is_debit=True),
        ]
        start, end = date(2026, 4, 1), date(2026, 6, 30)
        result = income_statement(transactions, accounts, 1, start, end)
        self.assertEqual(result["revenue_total"], 900)
        self.assertEqual(result["expenses_total"], 2000)
        self.assertEqual(result["net_income"], -1100)
        transactions.search.assert_called_once_with(1, date_from=start, date_to=end)
