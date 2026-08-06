from datetime import datetime
from pydantic import BaseModel


class DatabaseModel(BaseModel):
    id: int | None = None
    created_at: datetime | None = None
    is_deleted: bool = False


class Account(DatabaseModel):
    number: int
    title: str
    type: str
    description: str
    is_active: bool = True
    account_description: str | None = None


class JournalEntry(DatabaseModel):
    transaction_id: int | None = None
    account_id: int
    amount_cents: int
    is_debit: bool


class Transactions(DatabaseModel):
    date: datetime
    explanation: str


class Mileage(DatabaseModel):
    date: datetime
    tenth_miles: int
    start_tength_miles: int | None = None
    end_tength_miles: int | None = None
    explanation: str


####################
# Display Items
####################


class TAccountDisplay(BaseModel):
    account_title: str
    debits: list[int]
    credits: list[int]
