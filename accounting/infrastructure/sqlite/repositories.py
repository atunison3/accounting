# accounting/infrastructure/sqlite/repositories.py
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from accounting.domain.models import (
    Account,
    AccountType,
    AccountingTransaction,
    Business,
    TransactionLine,
    User,
)
from accounting.application.repositories import (
    AccountRepository,
    BusinessRepository,
    TransactionRepository,
    UserRepository,
)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _bool_to_int(value: bool) -> int:
    return 1 if value else 0


def _int_to_bool(value: int | None) -> bool:
    return bool(value)


# ---------------------------------------------------------------------------
# Row → Model helpers
# ---------------------------------------------------------------------------


def _row_to_user(row: sqlite3.Row) -> User:
    return User(
        id=row["id"],
        username=row["username"],
        first_name=row["first_name"],
        last_name=row["last_name"],
        email=row["email"],
        is_active=_int_to_bool(row["is_active"]),
        created_at=row["created_at"],
        created_by=None,
        updated_at=row["updated_at"],
        updated_by=None,
        deleted_at=row["deleted_at"],
        deleted_by=None,
    )


def _row_to_business(row: sqlite3.Row) -> Business:
    return Business(
        id=row["id"],
        title=row["title"],
        tax_id=row["tax_id"],
        is_business_active=_int_to_bool(row["is_business_active"]),
        established=row["established"],
        tax_year_end_month=row["tax_year_end_month"],
        created_at=row["created_at"],
        created_by=row["created_by"],
        updated_at=row["updated_at"],
        updated_by=row["updated_by"],
        deleted_at=row["deleted_at"],
        deleted_by=row["deleted_by"],
    )


def _row_to_account(row: sqlite3.Row) -> Account:
    return Account(
        id=row["id"],
        business_id=row["business_id"],
        account_number=row["account_number"],
        account_name=row["account_name"],
        account_type=AccountType(row["account_type"]),
        description=row["description"],
        is_account_active=_int_to_bool(row["is_account_active"]),
        is_debit=_int_to_bool(row["is_debit"]),
        created_at=row["created_at"],
        created_by=row["created_by"],
        updated_at=row["updated_at"],
        updated_by=row["updated_by"],
        deleted_at=row["deleted_at"],
        deleted_by=row["deleted_by"],
    )


def _row_to_transaction(row: sqlite3.Row) -> AccountingTransaction:
    return AccountingTransaction(
        id=row["id"],
        transaction_date=row["transaction_date"],
        description=row["description"],
        posting_reference=row["posting_reference"],
        created_at=row["created_at"],
        created_by=row["created_by"],
        updated_at=row["updated_at"],
        updated_by=row["updated_by"],
        deleted_at=row["deleted_at"],
        deleted_by=row["deleted_by"],
    )


def _row_to_line(row: sqlite3.Row) -> TransactionLine:
    return TransactionLine(
        id=row["id"],
        transaction_id=row["transaction_id"],
        account_id=row["account_id"],
        amount_cents=row["amount_cents"],
        is_debit=_int_to_bool(row["is_debit"]),
        created_at=row["created_at"],
        created_by=row["created_by"],
        updated_at=row["updated_at"],
        updated_by=row["updated_by"],
        deleted_at=row["deleted_at"],
        deleted_by=row["deleted_by"],
    )


# ---------------------------------------------------------------------------
# Repositories
# ---------------------------------------------------------------------------


class SqliteUserRepository(UserRepository):
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def add(self, user: User) -> int:
        now = _utcnow()
        cur = self._conn.cursor()
        cur.execute(
            """
            INSERT INTO users (
                username, first_name, last_name, email, is_active,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user.username,
                user.first_name,
                user.last_name,
                user.email,
                _bool_to_int(user.is_active),
                now,
                now,
            ),
        )
        last_row_id = cur.lastrowid
        if not isinstance(last_row_id, int):
            raise RuntimeError
        return last_row_id

    def get_by_id(self, user_id: int) -> User | None:
        cur = self._conn.cursor()
        cur.execute(
            "SELECT * FROM users WHERE id = ? AND deleted_at IS NULL",
            (user_id,),
        )
        row = cur.fetchone()
        return _row_to_user(row) if row else None

    def get_by_username(self, username: str) -> User | None:
        cur = self._conn.cursor()
        cur.execute(
            "SELECT * FROM users WHERE username = ? AND deleted_at IS NULL",
            (username,),
        )
        row = cur.fetchone()
        return _row_to_user(row) if row else None


class SqliteBusinessRepository(BusinessRepository):
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def add(self, business: Business) -> int:
        now = _utcnow()
        cur = self._conn.cursor()
        cur.execute(
            """
            INSERT INTO businesses (
                title, tax_id, is_business_active, established,
                created_at, created_by, updated_at, updated_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                business.title,
                business.tax_id,
                _bool_to_int(business.is_business_active),
                business.established,
                now,
                business.created_by,
                now,
                business.updated_by or business.created_by,
            ),
        )
        last_row_id = cur.lastrowid
        if not isinstance(last_row_id, int):
            raise RuntimeError
        return last_row_id

    def get_by_id(self, business_id: int) -> Business | None:
        cur = self._conn.cursor()
        cur.execute(
            "SELECT * FROM businesses WHERE id = ? AND deleted_at IS NULL",
            (business_id,),
        )
        row = cur.fetchone()
        return _row_to_business(row) if row else None

    def get_all(self) -> list[Business]:
        cur = self._conn.cursor()
        cur.execute("SELECT * FROM businesses WHERE deleted_at IS NULL ORDER BY title")
        return [_row_to_business(row) for row in cur.fetchall()]


class SqliteAccountRepository(AccountRepository):
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def add(self, account: Account) -> int:
        now = _utcnow()
        cur = self._conn.cursor()
        cur.execute(
            """
            INSERT INTO accounts (
                business_id, account_number, account_name, account_type,
                description, is_account_active, is_debit,
                created_at, created_by, updated_at, updated_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                account.business_id,
                account.account_number,
                account.account_name,
                account.account_type.value,
                account.description,
                _bool_to_int(account.is_account_active),
                _bool_to_int(account.is_debit),
                now,
                account.created_by,
                now,
                account.updated_by or account.created_by,
            ),
        )
        last_row_id = cur.lastrowid
        if not isinstance(last_row_id, int):
            raise RuntimeError
        return last_row_id

    def get_by_id(self, account_id: int) -> Account | None:
        cur = self._conn.cursor()
        cur.execute(
            "SELECT * FROM accounts WHERE id = ? AND deleted_at IS NULL",
            (account_id,),
        )
        row = cur.fetchone()
        return _row_to_account(row) if row else None

    def get_by_number(self, business_id: int, account_number: int) -> Account | None:
        cur = self._conn.cursor()
        cur.execute(
            """
            SELECT * FROM accounts
            WHERE business_id = ? AND account_number = ? AND deleted_at IS NULL
            """,
            (business_id, account_number),
        )
        row = cur.fetchone()
        return _row_to_account(row) if row else None

    def get_for_business(self, business_id: int) -> list[Account]:
        cur = self._conn.cursor()
        cur.execute(
            """
            SELECT * FROM accounts
            WHERE business_id = ? AND deleted_at IS NULL
            ORDER BY account_number
            """,
            (business_id,),
        )
        return [_row_to_account(row) for row in cur.fetchall()]


class SqliteTransactionRepository(TransactionRepository):
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def add(
        self,
        transaction: AccountingTransaction,
        lines: list[TransactionLine],
        user_id: int,
    ) -> int:
        now = _utcnow()
        cur = self._conn.cursor()

        # Insert header
        cur.execute(
            """
            INSERT INTO accounting_transactions (
                transaction_date, description, posting_reference,
                created_at, created_by, updated_at, updated_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                transaction.transaction_date.isoformat(),
                transaction.description,
                transaction.posting_reference,
                now,
                user_id,
                now,
                user_id,
            ),
        )
        transaction_id = cur.lastrowid
        if transaction_id is None:
            raise RuntimeError("Failed to insert transaction: no lastrowid returned")

        # Insert lines
        for line in lines:
            cur.execute(
                """
                INSERT INTO transaction_lines (
                    transaction_id, account_id, amount_cents, is_debit,
                    created_at, created_by, updated_at, updated_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    transaction_id,
                    line.account_id,
                    line.amount_cents,
                    _bool_to_int(line.is_debit),
                    now,
                    user_id,
                    now,
                    user_id,
                ),
            )

        if not isinstance(transaction_id, int):
            raise RuntimeError("Failed to insert transaction: no lastrowid returned")
        return transaction_id

    def get_by_id(self, transaction_id: int) -> AccountingTransaction | None:
        cur = self._conn.cursor()
        cur.execute(
            "SELECT * FROM accounting_transactions WHERE id = ? AND deleted_at IS NULL",
            (transaction_id,),
        )
        row = cur.fetchone()
        return _row_to_transaction(row) if row else None

    def get_lines(self, transaction_id: int) -> list[TransactionLine]:
        cur = self._conn.cursor()
        cur.execute(
            """
            SELECT * FROM transaction_lines
            WHERE transaction_id = ? AND deleted_at IS NULL
            ORDER BY id
            """,
            (transaction_id,),
        )
        return [_row_to_line(row) for row in cur.fetchall()]

    def delete(self, transaction_id: int, user_id: int) -> None:
        """Soft-delete the transaction and all its lines."""
        now = _utcnow()
        cur = self._conn.cursor()

        cur.execute(
            """
            UPDATE accounting_transactions
            SET deleted_at = ?, deleted_by = ?, updated_at = ?, updated_by = ?
            WHERE id = ? AND deleted_at IS NULL
            """,
            (now, user_id, now, user_id, transaction_id),
        )

        cur.execute(
            """
            UPDATE transaction_lines
            SET deleted_at = ?, deleted_by = ?, updated_at = ?, updated_by = ?
            WHERE transaction_id = ? AND deleted_at IS NULL
            """,
            (now, user_id, now, user_id, transaction_id),
        )
