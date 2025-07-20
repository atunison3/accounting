from pydantic import BaseModel


class Account(BaseModel):
    id_: int
    number: int
    title: str
    type_: int
    is_active: bool
