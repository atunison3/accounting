from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class AccountType(StrEnum):
    ASSET = "Asset"
    CONTRA_ASSET = "Contra-asset"
    LIABILITY = "Liability"
    EQUITY = "Equity"
    REVENUE = "Revenue"
    EXPENSE = "Expense"


class DatabaseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, validate_assignment=True)

    id: int | None = None
    created_at: datetime | None = None
    created_by: int | None = None
    updated_at: datetime | None = None
    updated_by: int | None = None
    deleted_at: datetime | None = None
    deleted_by: int | None = None

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None


class User(DatabaseModel):
    username: str = Field(min_length=1)
    first_name: str = Field(min_length=1)
    last_name: str = Field(min_length=1)
    email: EmailStr
    is_active: bool = True

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


class Business(DatabaseModel):
    title: str = Field(min_length=1)
    tax_id: str | None = None
    is_business_active: bool = True
    # The schema stores ISO dates; int is retained for compatibility with legacy callers.
    established: date | int | None = None
    tax_year_end_month: int = Field(default=12, ge=1, le=12)


class Account(DatabaseModel):
    business_id: int
    account_number: int = Field(gt=0)
    account_name: str = Field(min_length=1)
    account_type: AccountType
    description: str | None = None
    is_account_active: bool = True
    is_debit: bool = True


class AccountingTransaction(DatabaseModel):
    business_id: int | None = None
    transaction_date: date
    description: str = Field(min_length=1)
    currency_code: str = Field(default="USD", min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")
    posting_reference: str | None = None


class TransactionLine(DatabaseModel):
    transaction_id: int
    account_id: int
    amount_cents: int = Field(ge=0)
    is_debit: bool


class TransactionWithLines(AccountingTransaction):
    lines: list[TransactionLine] = Field(default_factory=list)

    @property
    def total_debits_cents(self) -> int:
        return sum(line.amount_cents for line in self.lines if line.is_debit and not line.is_deleted)

    @property
    def total_credits_cents(self) -> int:
        return sum(line.amount_cents for line in self.lines if not line.is_debit and not line.is_deleted)

    @property
    def is_balanced(self) -> bool:
        return self.total_debits_cents == self.total_credits_cents

    @model_validator(mode="after")
    def validate_balanced_transaction(self) -> "TransactionWithLines":
        if self.lines and not self.is_balanced:
            raise ValueError("Transaction debits and credits must be equal.")
        return self


class Mileage(DatabaseModel):
    business_id: int | None = None
    mileage_date: date
    tenth_miles: int = Field(ge=0)
    start_tenth_miles: int | None = Field(default=None, ge=0)
    end_tenth_miles: int | None = Field(default=None, ge=0)
    explanation: str = Field(min_length=1)
    vehicle: str | None = None

    @model_validator(mode="after")
    def validate_mileage(self) -> "Mileage":
        if self.start_tenth_miles is not None and self.end_tenth_miles is not None:
            if self.end_tenth_miles <= self.start_tenth_miles:
                raise ValueError("End mileage must be greater than start mileage.")
            if self.tenth_miles != self.end_tenth_miles - self.start_tenth_miles:
                raise ValueError("Tenth miles must equal end mileage minus start mileage.")
        return self


class Document(DatabaseModel):
    document_type: str = Field(min_length=1)
    document_date: date
    filename: str = Field(min_length=1)
    file_path: str = Field(min_length=1)
    title: str | None = None
    description: str | None = None
    mime_type: str | None = None
    file_size_bytes: int | None = Field(default=None, ge=0)
    sha256_hash: str | None = None
    source: str | None = None
    received_from: str | None = None
    notes: str | None = None


class AccountingTransactionDocument(DatabaseModel):
    transaction_id: int
    document_id: int


class TransactionEntry(BaseModel):
    transaction_id: int
    transaction_date: date
    description: str
    currency_code: str
    posting_reference: str | None = None
    account_number: int
    account_name: str
    amount_cents: int
    is_debit: bool


class TAccountDisplay(BaseModel):
    account_title: str
    debits: list[int]
    credits: list[int]


class BalanceColumnItem(BaseModel):
    date: datetime
    explanation: str
    posting_reference: str | None = None
    debit: int | None = None
    credit: int | None = None
    balance: int


class BalanceColumnDisplay(BaseModel):
    account_title: str
    account_number: int
    transactions: list[BalanceColumnItem]
