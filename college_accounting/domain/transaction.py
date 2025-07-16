from pydantic import BaseModel


class Transaction(BaseModel):
    entry_id: int
    account_id: int
    debit: float = None
    credit: float = None
