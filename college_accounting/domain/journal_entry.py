from pydantic import BaseModel


class JournalEntry(BaseModel):
    id_: int
    date: str
    description: str
