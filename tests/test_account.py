import unittest

from college_accounting import Account


class TestAccount(unittest.TestCase):

    def test_add_existing_accounts(self):
        a = Account()
        t1 = {"cash": 500, "equipment": 200}
        a + t1

        self.assertEqual(a.book["cash"], 500)
        self.assertEqual(a.book["equipment"], 200)
        self.assertEqual(a.book["accounts_payable"], 0)
        self.assertEqual(a.book["owner_capital"], 0)

    def test_add_new_account_key(self):
        a = Account()
        t1 = {"new_asset": 1000}
        a + t1

        self.assertEqual(a.book["new_asset"], 1000)
        self.assertIn("new_asset", a.book)

    def test_original_account_immutable(self):
        a = Account()
        t1 = {"cash": 100}
        a + t1

        # Original account unchanged
        self.assertEqual(a.book["cash"], 100)

    def test_chained_additions(self):
        a = Account()
        t1 = {"cash": 300}
        t2 = {"equipment": 700}
        t3 = {"cash": -50, "owner_capital": 150}

        a + t1
        a + t2
        a + t3

        self.assertEqual(a.book["cash"], 250)  # 300 - 50
        self.assertEqual(a.book["equipment"], 700)
        self.assertEqual(a.book["owner_capital"], 150)


if __name__ == "__main__":
    unittest.main()
