# accounting/application/services.py

from datetime import date

from accounting.domain.models import AccountingTransaction, TransactionLine


class AccountingService:
    def __init__(self, repository) -> None:
        self.repository = repository

    def create_transaction(
        self,
        transaction_date: date,
        description: str,
        lines: list[TransactionLine],
        user_id: int,
        posting_reference: str | None = None,
    ) -> int:
        if len(lines) < 2:
            raise ValueError("A transaction must contain at least two transaction lines.")

        total_debits = sum(line.amount_cents for line in lines if line.is_debit)
        total_credits = sum(line.amount_cents for line in lines if not line.is_debit)

        if total_debits != total_credits:
            raise ValueError(f"Debits and credits must be equal. Debits: {total_debits}, Credits: {total_credits}.")

        transaction = AccountingTransaction(
            transaction_date=transaction_date,
            description=description,
            posting_reference=posting_reference,
            created_by=user_id,
            updated_by=user_id,
        )

        return self.repository.create_transaction(
            transaction=transaction,
            lines=lines,
            user_id=user_id,
        )

    def get_transaction(self, transaction_id: int) -> AccountingTransaction | None:
        return self.repository.get_transaction(transaction_id)

    def get_transaction_lines(self, transaction_id: int) -> list[TransactionLine]:
        return self.repository.get_transaction_lines(transaction_id)

    def delete_transaction(self, transaction_id: int, user_id: int) -> None:
        transaction = self.repository.get_transaction(transaction_id)

        if transaction is None:
            raise ValueError(f"Transaction {transaction_id} does not exist.")

        self.repository.delete_transaction(transaction_id, user_id)
