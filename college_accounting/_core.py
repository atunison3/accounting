class Account:
    def __init__(self):
        self.book = {
            'cash': 0, 
            'equipment': 0, 
            'accounts_payable': 0, 
            'owner_capital': 0
        }

    def __add__(self, transaction: dict):
        for k, v in transaction.items():
            if k in self.book.keys():
                self.book[k] += v
            else:
                self.book[k] = v
        

    