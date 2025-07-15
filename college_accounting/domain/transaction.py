from datetime import datetime 

__all__ = [
    'Transaction'
]

class Transaction:
    def __init__(self, transaction_id: int, date: datetime, account: Account, amount: int, is_debit: bool):

        self.transaction_id = transaction_id
        self.date = date 
        self.account = account
        self.amount = amount 
        self.is_debit = is_debit