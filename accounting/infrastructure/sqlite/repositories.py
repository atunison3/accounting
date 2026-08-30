# accounting/infrastructure/sqlite/repositories.py
from __future__ import annotations

import logging
import sqlite3
from datetime import date, datetime, timezone

from accounting.domain.models import (
    Account,
    AccountType,
    AccountingTransaction,
    Business,
    Mileage,
    TransactionLine,
    TransactionEntry,
    User,
)
from accounting.application.repositories import (
    AccountRepository,
    BusinessRepository,
    MileageRepository,
    TransactionRepository,
    UserRepository,
)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _bool_to_int(value: bool) -> int:
    return 1 if value else 0


def _int_to_bool(value: int | None) -> bool:
    return bool(value)


LOGGER = logging.getLogger("accounting.api.sqlite")


def _execute(cursor: sqlite3.Cursor, sql: str, parameters: tuple = ()) -> sqlite3.Cursor:
    """Execute SQL and log the statement and parameters when it fails."""
    try:
        return cursor.execute(sql, parameters)
    except Exception:
        LOGGER.exception("SQLite execute failed sql=%s parameters=%r", sql.strip(), parameters)
        raise


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


def _row_to_mileage(row: sqlite3.Row) -> Mileage:
    return Mileage(
        id=row["id"],
        business_id=row["business_id"],
        mileage_date=row["miles_date"],
        tenth_miles=row["tenth_miles"],
        start_tenth_miles=row["tenth_miles_begin"],
        end_tenth_miles=row["tenth_miles_end"],
        explanation=row["explanation"],
        vehicle=row["vehicle"],
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
        business_id=row["business_id"],
        transaction_date=row["transaction_date"],
        description=row["description"],
        currency_code=row["currency_code"],
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
        _execute(
            cur,
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
        _execute(
            cur,
            "SELECT * FROM users WHERE id = ? AND deleted_at IS NULL",
            (user_id,),
        )
        row = cur.fetchone()
        return _row_to_user(row) if row else None

    def get_by_username(self, username: str) -> User | None:
        cur = self._conn.cursor()
        _execute(
            cur,
            "SELECT * FROM users WHERE username = ? AND deleted_at IS NULL",
            (username,),
        )
        row = cur.fetchone()
        return _row_to_user(row) if row else None


class SqliteBusinessRepository(BusinessRepository):
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def add(self, business: Business) -> int:
        cur = self._conn.cursor()
        _execute(
            cur,
            """
            INSERT INTO businesses (
                title, tax_id, is_business_active, established, created_by
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                business.title,
                business.tax_id,
                _bool_to_int(business.is_business_active),
                business.established,
                business.created_by,
            ),
        )
        last_row_id = cur.lastrowid
        if not isinstance(last_row_id, int):
            raise RuntimeError
        return last_row_id

    def get_by_id(self, business_id: int) -> Business | None:
        cur = self._conn.cursor()
        _execute(
            cur,
            "SELECT * FROM businesses WHERE id = ? AND deleted_at IS NULL",
            (business_id,),
        )
        row = cur.fetchone()
        return _row_to_business(row) if row else None

    def get_all(self) -> list[Business]:
        cur = self._conn.cursor()
        _execute(cur, "SELECT * FROM businesses WHERE deleted_at IS NULL ORDER BY title")
        return [_row_to_business(row) for row in cur.fetchall()]


class SqliteMileageRepository(MileageRepository):
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def add(self, mileage: Mileage) -> int:
        now = _utcnow()
        cur = self._conn.cursor()
        _execute(
            cur,
            """
            INSERT INTO miles (
                business_id, miles_date, tenth_miles, tenth_miles_begin,
                tenth_miles_end, explanation, vehicle, created_at, created_by,
                updated_at, updated_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                mileage.business_id,
                mileage.mileage_date.isoformat(),
                mileage.tenth_miles,
                mileage.start_tenth_miles,
                mileage.end_tenth_miles,
                mileage.explanation,
                mileage.vehicle,
                now,
                mileage.created_by,
                now,
                mileage.updated_by or mileage.created_by,
            ),
        )
        if not isinstance(cur.lastrowid, int):
            raise RuntimeError("Failed to insert mileage")
        return cur.lastrowid

    def get_by_id(self, mileage_id: int) -> Mileage | None:
        cur = self._conn.cursor()
        _execute(cur, "SELECT * FROM miles WHERE id = ? AND deleted_at IS NULL", (mileage_id,))
        row = cur.fetchone()
        return _row_to_mileage(row) if row else None


class SqliteAccountRepository(AccountRepository):
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def add(self, account: Account) -> int:
        now = _utcnow()
        cur = self._conn.cursor()
        _execute(
            cur,
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
        _execute(
            cur,
            "SELECT * FROM accounts WHERE id = ? AND deleted_at IS NULL",
            (account_id,),
        )
        row = cur.fetchone()
        return _row_to_account(row) if row else None

    def get_by_number(self, business_id: int, account_number: int) -> Account | None:
        cur = self._conn.cursor()
        _execute(
            cur,
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
        _execute(
            cur,
            """
            SELECT * FROM accounts
            WHERE business_id = ? AND deleted_at IS NULL
            ORDER BY account_number
            """,
            (business_id,),
        )
        return [_row_to_account(row) for row in cur.fetchall()]

    def update(self, account_id: int, account: Account, user_id: int) -> None:
        now = _utcnow()
        cur = self._conn.cursor()
        _execute(
            cur,
            """
            UPDATE accounts
            SET account_number = ?, account_name = ?, account_type = ?,
                description = ?, is_account_active = ?, is_debit = ?,
                updated_at = ?, updated_by = ?
            WHERE id = ? AND deleted_at IS NULL
            """,
            (
                account.account_number,
                account.account_name,
                account.account_type.value,
                account.description,
                _bool_to_int(account.is_account_active),
                _bool_to_int(account.is_debit),
                now,
                user_id,
                account_id,
            ),
        )


class SqliteTransactionRepository(TransactionRepository):
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def add(
        self,
        transaction: AccountingTransaction,
        lines: list[TransactionLine],
        user_id: int,
    ) -> int:
        cur = self._conn.cursor()

        # Insert header
        _execute(
            cur,
            """
            INSERT INTO accounting_transactions (
                business_id, transaction_date, description, currency_code,
                posting_reference, created_by
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                transaction.business_id,
                transaction.transaction_date.isoformat(),
                transaction.description,
                transaction.currency_code,
                transaction.posting_reference,
                user_id,
            ),
        )
        transaction_id = cur.lastrowid
        if transaction_id is None:
            raise RuntimeError("Failed to insert transaction: no lastrowid returned")

        # Insert lines
        for line in lines:
            _execute(
                cur,
                """
                INSERT INTO transaction_lines (
                    transaction_id, account_id, amount_cents, is_debit,
                    created_by
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    transaction_id,
                    line.account_id,
                    line.amount_cents,
                    _bool_to_int(line.is_debit),
                    user_id,
                ),
            )

        if not isinstance(transaction_id, int):
            raise RuntimeError("Failed to insert transaction: no lastrowid returned")
        return transaction_id

    def get_by_id(self, transaction_id: int) -> AccountingTransaction | None:
        cur = self._conn.cursor()
        _execute(
            cur,
            "SELECT * FROM accounting_transactions WHERE id = ? AND deleted_at IS NULL",
            (transaction_id,),
        )
        row = cur.fetchone()
        return _row_to_transaction(row) if row else None

    def update(
        self,
        transaction_id: int,
        transaction: AccountingTransaction,
        lines: list[TransactionLine],
        user_id: int,
    ) -> None:
        now = _utcnow()
        cur = self._conn.cursor()
        _execute(
            cur,
            """
            UPDATE accounting_transactions
            SET business_id = ?, transaction_date = ?, description = ?,
                currency_code = ?, posting_reference = ?, updated_at = ?, updated_by = ?
            WHERE id = ? AND deleted_at IS NULL
            """,
            (
                transaction.business_id,
                transaction.transaction_date.isoformat(),
                transaction.description,
                transaction.currency_code,
                transaction.posting_reference,
                now,
                user_id,
                transaction_id,
            ),
        )
        _execute(
            cur,
            """
            UPDATE transaction_lines
            SET deleted_at = ?, deleted_by = ?, updated_at = ?, updated_by = ?
            WHERE transaction_id = ? AND deleted_at IS NULL
            """,
            (now, user_id, now, user_id, transaction_id),
        )
        for line in lines:
            _execute(
                cur,
                """
                INSERT INTO transaction_lines (
                    transaction_id, account_id, amount_cents, is_debit,
                    created_by
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (transaction_id, line.account_id, line.amount_cents, _bool_to_int(line.is_debit), user_id),
            )

    def get_lines(self, transaction_id: int) -> list[TransactionLine]:
        cur = self._conn.cursor()
        _execute(
            cur,
            """
            SELECT * FROM transaction_lines
            WHERE transaction_id = ? AND deleted_at IS NULL
            ORDER BY id
            """,
            (transaction_id,),
        )
        return [_row_to_line(row) for row in cur.fetchall()]

    def search(  # noqa: PLR0913, PLR0917
        self,
        business_id: int,
        account_number: int | None = None,
        is_debit: bool | None = None,
        min_amount_cents: int | None = None,
        max_amount_cents: int | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[TransactionEntry]:
        debit_filter = _bool_to_int(is_debit) if is_debit is not None else None
        parameters = (
            business_id,
            account_number,
            account_number,
            debit_filter,
            debit_filter,
            min_amount_cents,
            min_amount_cents,
            max_amount_cents,
            max_amount_cents,
            date_from.isoformat() if date_from is not None else None,
            date_from.isoformat() if date_from is not None else None,
            date_to.isoformat() if date_to is not None else None,
            date_to.isoformat() if date_to is not None else None,
        )
        cur = self._conn.cursor()
        _execute(
            cur,
            """
            SELECT t.id AS transaction_id, t.transaction_date, t.description,
                   t.currency_code, t.posting_reference, a.account_number, a.account_name,
                   l.amount_cents, l.is_debit
            FROM accounting_transactions AS t
            JOIN transaction_lines AS l ON l.transaction_id = t.id
            JOIN accounts AS a ON a.id = l.account_id
            WHERE t.business_id = ?
              AND t.deleted_at IS NULL
              AND l.deleted_at IS NULL
              AND (? IS NULL OR a.account_number = ?)
              AND (? IS NULL OR l.is_debit = ?)
              AND (? IS NULL OR l.amount_cents >= ?)
              AND (? IS NULL OR l.amount_cents <= ?)
              AND (? IS NULL OR t.transaction_date >= ?)
              AND (? IS NULL OR t.transaction_date <= ?)
            ORDER BY t.transaction_date DESC, t.id DESC, l.id
            """,
            parameters,
        )
        return [
            TransactionEntry(
                transaction_id=row["transaction_id"],
                transaction_date=row["transaction_date"],
                description=row["description"],
                currency_code=row["currency_code"],
                posting_reference=row["posting_reference"],
                account_number=row["account_number"],
                account_name=row["account_name"],
                amount_cents=row["amount_cents"],
                is_debit=_int_to_bool(row["is_debit"]),
            )
            for row in cur.fetchall()
        ]

    def document_coverage(self, business_id: int) -> tuple[int, int]:
        """Return (total active transactions, transactions without documents)."""
        cur = self._conn.cursor()
        _execute(
            cur,
            """
            SELECT COUNT(*) AS total,
                   SUM(CASE WHEN NOT EXISTS (
                       SELECT 1 FROM accounting_transaction_documents AS atd
                       -- The schema's legacy column is misspelled as transction_id.
                       WHERE atd.transction_id = t.id AND atd.deleted_at IS NULL
                   ) THEN 1 ELSE 0 END) AS without_documents
            FROM accounting_transactions AS t
            WHERE t.business_id = ? AND t.deleted_at IS NULL
            """,
            (business_id,),
        )
        row = cur.fetchone()
        return (int(row["total"] or 0), int(row["without_documents"] or 0))

    def delete(self, transaction_id: int, user_id: int) -> None:
        """Soft-delete the transaction and all its lines."""
        now = _utcnow()
        cur = self._conn.cursor()

        _execute(
            cur,
            """
            UPDATE accounting_transactions
            SET deleted_at = ?, deleted_by = ?, updated_at = ?, updated_by = ?
            WHERE id = ? AND deleted_at IS NULL
            """,
            (now, user_id, now, user_id, transaction_id),
        )

        _execute(
            cur,
            """
            UPDATE transaction_lines
            SET deleted_at = ?, deleted_by = ?, updated_at = ?, updated_by = ?
            WHERE transaction_id = ? AND deleted_at IS NULL
            """,
            (now, user_id, now, user_id, transaction_id),
        )
