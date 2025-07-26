from pydantic import BaseModel


class LedgerTransaction(BaseModel):
    id_: int
    entry_id: int
    account_number: int
    transaction_amount: float
    running_balance: float | None
