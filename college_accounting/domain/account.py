from pydantic import BaseModel


class Account(BaseModel):
    account_id: int
    number: int
    name: str
    type_: int
    is_active: bool
