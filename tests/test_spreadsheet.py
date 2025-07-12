import unittest
from datetime import datetime

from college_accounting import SpreadSheet, Transaction

class TestSpreadSheet(unittest.TestCase):
    def setUp(self):
        """Set up a new spreadsheet and add transactions"""
        self.sheet = SpreadSheet()

        transactions = [
            Transaction(datetime(2024, 7, 1), cash=4500, freedman_capital=4500,
                        description="Invested $4,500 of his savings into the business."),
            Transaction(datetime(2024, 7, 2), cash=-1200, shop_equipment=1200,
                        description="Paid $1,200 for computer equipment."),
            Transaction(datetime(2024, 7, 3), cash=-600, office_equipment=600,
                        description="Paid $600 for office equipment."),
            Transaction(datetime(2024, 7, 4), accounts_payable=250, supplies=250,
                        description="Purchased $250 in office supplies on credit."),
            Transaction(datetime(2024, 7, 5), cash=-400, expenses=400,
                        description="Paid July rent, $400."),
            Transaction(datetime(2024, 7, 6), cash=250, service_revenue=250,
                        description="Collected $250 for repair services."),
            Transaction(datetime(2024, 7, 7), cash=200, service_revenue=200,
                        description="Collected $200 for system upgrade labor."),
            Transaction(datetime(2024, 7, 8), cash=200, service_revenue=200,
                        description="Collected $200 for system upgrade labor."),
            Transaction(datetime(2024, 7, 8), cash=200, service_revenue=200,
                        description="Collected $200 for system upgrade labor."),
            Transaction(datetime(2024, 7, 9), accounts_payable=85, expenses=85,
                        description="Electric bill due but unpaid, $85."),
            Transaction(datetime(2024, 7, 10), cash=1200, service_revenue=1200,
                        description="Collected $1,200 for services."),
            Transaction(datetime(2024, 7, 11), cash=-100, freedman_withdrawal=100,
                        description="Withdrew $100 for personal use."),
        ]

        for t in transactions:
            self.sheet.add_row(t)

    def test_final_balance(self):
        """Test the final balance after all transactions"""
        last_row = self.sheet.iloc[-1]

        # Expected totals (manually calculated)
        expected_cash = 6450
        expected_shop_equipment = 1200
        expected_office_equipment = 600
        expected_supplies = 250
        expected_accounts_payable = 335  # 250 + 85 unpaid
        expected_freedman_capital = 4500
        expected_freedman_withdrawal = 100
        expected_service_revenue = 2050  # sum of all service revenue
        expected_expenses = 485  # rent + electric

        self.assertEqual(last_row['Cash'], expected_cash)
        self.assertEqual(last_row['Computer Shop Equipment'], expected_shop_equipment)
        self.assertEqual(last_row['Office Equipment'], expected_office_equipment)
        self.assertEqual(last_row['Supplies'], expected_supplies)
        self.assertEqual(last_row['Accounts Payable'], expected_accounts_payable)
        self.assertEqual(last_row['Freedman Capital'], expected_freedman_capital)
        self.assertEqual(last_row['Freedman Withdrawal'], expected_freedman_withdrawal)
        self.assertEqual(last_row['Service Revenue'], expected_service_revenue)
        self.assertEqual(last_row['Expenses'], expected_expenses)

    def test_assets_equals_liabilities_plus_equity(self):
        """Test Assets = Liabilities + Equity in final balance"""
        total_assets = self.sheet.total_assets
        total_liabilities_and_equity = self.sheet.total_liabilities_and_equity

        self.assertAlmostEqual(total_assets, total_liabilities_and_equity, places=2)

    def test_row_count(self):
        """Test total number of rows: each transaction + balance pair"""
        expected_rows = 12 * 2  # 12 transactions + 12 balances
        self.assertEqual(len(self.sheet), expected_rows)

if __name__ == '__main__':
    unittest.main()
