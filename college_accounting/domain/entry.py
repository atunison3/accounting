from datetime import datetime
from pydantic import BaseModel


class Entry(BaseModel):
    entry_id: int
    date: datetime
    description: str
