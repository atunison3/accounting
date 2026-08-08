import unittest
from datetime import date, datetime

from pydantic import ValidationError

from accounting.domain.models import (
    Account,
    AccountingTransaction,
    AccountType,
    Business,
    Mileage,
    TransactionLine,
    User,
)


class TestUser(unittest.TestCase):
    def test_user(self) -> None:
        user = User(
            id=1,
            username="jsmith",
            first_name="Justin",
            last_name="Smith",
            email="jsmith@example.com",
        )

        self.assertEqual(user.id, 1)
        self.assertEqual(user.username, "jsmith")
        self.assertEqual(user.first_name, "Justin")
        self.assertEqual(user.last_name, "Smith")
        self.assertEqual(user.email, "jsmith@example.com")
        self.assertTrue(user.is_active)

        self.assertIsNone(user.created_at)
        self.assertIsNone(user.created_by)
        self.assertIsNone(user.updated_at)
        self.assertIsNone(user.updated_by)
        self.assertIsNone(user.deleted_at)
        self.assertIsNone(user.deleted_by)

    def test_user_full_name(self) -> None:
        user = User(
            username="jsmith",
            first_name="Justin",
            last_name="Smith",
            email="jsmith@example.com",
        )

        self.assertEqual(user.full_name, "Justin Smith")

    def test_user_is_not_deleted_by_default(self) -> None:
        user = User(
            username="jsmith",
            first_name="Justin",
            last_name="Smith",
            email="jsmith@example.com",
        )

        self.assertFalse(user.is_deleted)

    def test_user_is_deleted_when_deleted_at_exists(self) -> None:
        user = User(
            username="jsmith",
            first_name="Justin",
            last_name="Smith",
            email="jsmith@example.com",
            deleted_at=datetime(2026, 8, 7, 12, 0),
            deleted_by=1,
        )

        self.assertTrue(user.is_deleted)
        self.assertEqual(user.deleted_by, 1)

    def test_user_rejects_invalid_email(self) -> None:
        with self.assertRaises(ValidationError):
            User(
                username="jsmith",
                first_name="Justin",
                last_name="Smith",
                email="not-an-email",
            )


class TestBusiness(unittest.TestCase):
    def test_business(self) -> None:
        business = Business(
            id=1,
            title="J. T. Smith CPA Services",
            tax_id=None,
            is_business_active=True,
            established=1978,
            created_by=1,
            updated_by=1,
        )

        self.assertEqual(business.id, 1)
        self.assertEqual(business.title, "J. T. Smith CPA Services")
        self.assertIsNone(business.tax_id)
        self.assertTrue(business.is_business_active)
        self.assertEqual(business.established, 1978)
        self.assertEqual(business.created_by, 1)
        self.assertEqual(business.updated_by, 1)
        self.assertFalse(business.is_deleted)

    def test_business_is_active_by_default(self) -> None:
        business = Business(title="J. T. Smith CPA Services")

        self.assertTrue(business.is_business_active)


class TestAccount(unittest.TestCase):
    def test_account(self) -> None:
        account = Account(
            id=1,
            business_id=1,
            account_number=110,
            account_name="Cash",
            account_type=AccountType.ASSET,
            description="Cash available to the business",
            created_by=1,
            updated_by=1,
        )

        self.assertEqual(account.id, 1)
        self.assertEqual(account.business_id, 1)
        self.assertEqual(account.account_number, 110)
        self.assertEqual(account.account_name, "Cash")
        self.assertEqual(account.account_type, AccountType.ASSET)
        self.assertEqual(account.description, "Cash available to the business")
        self.assertTrue(account.is_account_active)

    def test_account_is_active_by_default(self) -> None:
        account = Account(
            business_id=1,
            account_number=110,
            account_name="Cash",
            account_type=AccountType.ASSET,
        )

        self.assertTrue(account.is_account_active)

    def test_account_rejects_invalid_account_type(self) -> None:
        with self.assertRaises(ValidationError):
            Account(
                business_id=1,
                account_number=110,
                account_name="Cash",
                account_type="Something Else",  # type: ignore
            )

    def test_account_rejects_non_positive_account_number(self) -> None:
        with self.assertRaises(ValidationError):
            Account(
                business_id=1,
                account_number=0,
                account_name="Cash",
                account_type=AccountType.ASSET,
            )


class TestAccountingTransaction(unittest.TestCase):
    def test_accounting_transaction(self) -> None:
        transaction = AccountingTransaction(
            id=1,
            transaction_date=date(1978, 3, 1),
            description="Paid the rent for March",
            posting_reference=None,
            created_by=1,
            updated_by=1,
        )

        self.assertEqual(transaction.id, 1)
        self.assertEqual(transaction.transaction_date, date(1978, 3, 1))
        self.assertEqual(transaction.description, "Paid the rent for March")
        self.assertIsNone(transaction.posting_reference)
        self.assertEqual(transaction.created_by, 1)
        self.assertEqual(transaction.updated_by, 1)
        self.assertFalse(transaction.is_deleted)


class TestTransactionLine(unittest.TestCase):
    def test_debit_transaction_line(self) -> None:
        line = TransactionLine(
            id=1,
            transaction_id=1,
            account_id=5,
            amount_cents=17_500,
            is_debit=True,
            created_by=1,
            updated_by=1,
        )

        self.assertEqual(line.id, 1)
        self.assertEqual(line.transaction_id, 1)
        self.assertEqual(line.account_id, 5)
        self.assertEqual(line.amount_cents, 17_500)
        self.assertTrue(line.is_debit)

    def test_credit_transaction_line(self) -> None:
        line = TransactionLine(
            transaction_id=1,
            account_id=1,
            amount_cents=17_500,
            is_debit=False,
        )

        self.assertFalse(line.is_debit)

    def test_transaction_line_rejects_negative_amount(self) -> None:
        with self.assertRaises(ValidationError):
            TransactionLine(
                transaction_id=1,
                account_id=1,
                amount_cents=-100,
                is_debit=True,
            )

    def test_transaction_line_allows_zero_amount(self) -> None:
        line = TransactionLine(
            transaction_id=1,
            account_id=1,
            amount_cents=0,
            is_debit=True,
        )

        self.assertEqual(line.amount_cents, 0)


class TestMileage(unittest.TestCase):
    def test_mileage(self) -> None:
        mileage = Mileage(
            business_id=1,
            mileage_date=date(2026, 8, 7),
            tenth_miles=125,
            start_tenth_miles=10_000,
            end_tenth_miles=10_125,
            explanation="Drove to client",
        )

        self.assertEqual(mileage.business_id, 1)
        self.assertEqual(mileage.mileage_date, date(2026, 8, 7))
        self.assertEqual(mileage.tenth_miles, 125)
        self.assertEqual(mileage.start_tenth_miles, 10_000)
        self.assertEqual(mileage.end_tenth_miles, 10_125)
        self.assertEqual(mileage.explanation, "Drove to client")

    def test_mileage_rejects_negative_miles(self) -> None:
        with self.assertRaises(ValidationError):
            Mileage(
                business_id=1,
                mileage_date=date(2026, 8, 7),
                tenth_miles=-10,
                explanation="Invalid mileage",
            )

    def test_mileage_rejects_end_mileage_less_than_start(self) -> None:
        with self.assertRaises(ValidationError):
            Mileage(
                business_id=1,
                mileage_date=date(2026, 8, 7),
                tenth_miles=100,
                start_tenth_miles=10_100,
                end_tenth_miles=10_000,
                explanation="Invalid mileage",
            )

    def test_mileage_rejects_incorrect_calculated_mileage(self) -> None:
        with self.assertRaises(ValidationError):
            Mileage(
                business_id=1,
                mileage_date=date(2026, 8, 7),
                tenth_miles=200,
                start_tenth_miles=10_000,
                end_tenth_miles=10_100,
                explanation="Mileage does not match odometer values",
            )


if __name__ == "__main__":
    unittest.main()
