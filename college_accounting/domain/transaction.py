from pydantic import BaseModel


class Transaction(BaseModel):
    transaction_id: int
    entry_id: int
    account_number: int
    debit: float = None
    credit: float = None
