import unittest

from college_accounting import Account 

class TestAccount(unittest.TestCase):

    def test_add_existing_accounts(self):
        a = Account()
        t1 = {'cash': 500, 'equipment': 200}
        result = a + t1

        self.assertEqual(result.book['cash'], 500)
        self.assertEqual(result.book['equipment'], 200)
        self.assertEqual(result.book['accounts_payable'], 0)
        self.assertEqual(result.book['owner_capital'], 0)

    def test_add_new_account_key(self):
        a = Account()
        t1 = {'new_asset': 1000}
        result = a + t1

        self.assertEqual(result.book['new_asset'], 1000)
        self.assertIn('new_asset', result.book)

    def test_original_account_immutable(self):
        a = Account()
        t1 = {'cash': 100}
        result = a + t1

        # Original account unchanged
        self.assertEqual(a.book['cash'], 0)
        self.assertEqual(result.book['cash'], 100)

    def test_chained_additions(self):
        a = Account()
        t1 = {'cash': 300}
        t2 = {'equipment': 700}
        t3 = {'cash': -50, 'owner_capital': 150}

        result = a + t1 + t2 + t3

        self.assertEqual(result.book['cash'], 250)  # 300 - 50
        self.assertEqual(result.book['equipment'], 700)
        self.assertEqual(result.book['owner_capital'], 150)

    def test_reverse_addition(self):
        a = Account()
        t1 = {'cash': 400, 'accounts_payable': -100}
        result = t1 + a  # __radd__

        self.assertEqual(result.book['cash'], 400)
        self.assertEqual(result.book['accounts_payable'], -100)
        self.assertEqual(result.book['equipment'], 0)

if __name__ == '__main__':
    unittest.main()
