PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;


------ CREATE TABLES ------
CREATE TABLE IF NOT EXISTS users (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    username    TEXT    NOT NULL UNIQUE,
    first_name  TEXT    NOT NULL,
    last_name   TEXT    NOT NULL,
    email       TEXT    NOT NULL UNIQUE,
    is_active   INTEGER NOT NULL DEFAULT 1,

    created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at  TEXT,

    CHECK (
        email LIKE '%_@_%._%' AND
        LENGTH(email) - LENGTH(REPLACE(email, '@', '')) = 1
    )
);

CREATE TABLE IF NOT EXISTS businesses (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    title               TEXT    NOT NULL,
    tax_id              TEXT,
    is_business_active  INTEGER NOT NULL DEFAULT 1,
    established         TEXT,
    tax_year_end_month  INTEGER NOT NULL DEFAULT 12,

    created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by  INTEGER NOT NULL,
    updated_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by  INTEGER REFERENCES users(id),
    deleted_at  TEXT,
    deleted_by  INTEGER REFERENCES users(id),

    CHECK (
        (deleted_at IS NULL AND deleted_by IS NULL) OR
        (deleted_at IS NOT NULL AND deleted_by IS NOT NULL)
    ),
    CHECK (
        tax_id IS NULL OR (
            length(tax_id) = 10
            AND substr(tax_id, 3, 1) = '-'
            AND substr(tax_id, 1, 2) GLOB '[0-9][0-9]'
            AND substr(tax_id, 4, 7) GLOB '[0-9][0-9][0-9][0-9][0-9][0-9][0-9]'
        )
    ),
    CHECK (
        tax_year_end_month BETWEEN 1 and 12
    ),
    CHECK (
        established IS NULL
        OR (
            established GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
            AND date(established) IS NOT NULL
            AND date(established) = established
        )
    ),

    FOREIGN KEY (created_by) REFERENCES users(id),
    FOREIGN KEY (updated_by) REFERENCES users(id),
    FOREIGN KEY (deleted_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS miles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    business_id       INTEGER REFERENCES businesses(id),
    miles_date        TEXT NOT NULL,
    tenth_miles       INTEGER NOT NULL,
    tenth_miles_begin INTEGER,
    tenth_miles_end   INTEGER,
    explanation       TEXT NOT NULL,
    vehicle           TEXT,

    created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by  INTEGER NOT NULL,
    updated_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by  INTEGER REFERENCES users(id),
    deleted_at  TEXT,
    deleted_by  INTEGER REFERENCES users(id),

    CHECK (
        tenth_miles_begin IS NULL
        OR tenth_miles_begin >= 0
    ),

    CHECK (
        tenth_miles_end IS NULL
        OR tenth_miles_end >= 0
    ),

    CHECK (
        tenth_miles_begin IS NULL
        OR tenth_miles_end IS NULL
        OR tenth_miles_end > tenth_miles_begin
    ),

    CHECK (
        (deleted_at IS NULL AND deleted_by IS NULL) OR
        (deleted_at IS NOT NULL AND deleted_by IS NOT NULL)
    ),

    FOREIGN KEY (created_by) REFERENCES users(id),
    FOREIGN KEY (updated_by) REFERENCES users(id),
    FOREIGN KEY (deleted_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS accounts (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    business_id       INTEGER NOT NULL REFERENCES businesses(id),
    account_number    INTEGER NOT NULL,
    account_name      TEXT    NOT NULL,
    account_type      TEXT    NOT NULL,
    description       TEXT,
    is_account_active INTEGER NOT NULL DEFAULT 1,
    is_debit          INTEGER NOT NULL,  -- Normal balance is debit yes/no

    created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by  INTEGER,
    updated_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by  INTEGER REFERENCES users(id),
    deleted_at  TEXT,
    deleted_by  INTEGER REFERENCES users(id),

    CHECK (
        account_type in ('Asset', 'Contra-asset', 'Liability', 'Equity', 'Revenue', 'Expense')
    ),
    CHECK (
        is_debit in (0, 1)
    ),

    CHECK (
        (deleted_at IS NULL AND deleted_by IS NULL) OR
        (deleted_at IS NOT NULL AND deleted_by IS NOT NULL)
    ),

    FOREIGN KEY (created_by) REFERENCES users(id),
    FOREIGN KEY (updated_by) REFERENCES users(id),
    FOREIGN KEY (deleted_by) REFERENCES users(id),

    UNIQUE (business_id, account_number)
);

CREATE TABLE IF NOT EXISTS accounting_transactions (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_date   TEXT    NOT NULL,
    description        TEXT    NOT NULL,
    posting_reference  TEXT,

    created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by  INTEGER,
    updated_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by  REFERENCES users(id),
    deleted_at  TEXT,
    deleted_by  REFERENCES users(id),

    CHECK (
        (deleted_at IS NULL AND deleted_by IS NULL) OR
        (deleted_at IS NOT NULL AND deleted_by IS NOT NULL)
    ),

    FOREIGN KEY (created_by) REFERENCES users(id),
    FOREIGN KEY (updated_by) REFERENCES users(id),
    FOREIGN KEY (deleted_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS documents (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,

    document_type       TEXT NOT NULL,
    document_date       TEXT NOT NULL,
    title               TEXT,
    description         TEXT,

    filename            TEXT NOT NULL,
    file_path           TEXT NOT NULL,
    mime_type           TEXT,
    file_size_bytes     INTEGER,

    sha256_hash         TEXT,

    source              TEXT,
    received_from       TEXT,
    notes               TEXT,

    created_at          TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by          INTEGER NOT NULL,
    updated_at          TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by          REFERENCES users(id),
    deleted_at          TEXT,
    deleted_by          REFERENCES users(id),

    CHECK (
        document_date IS NULL
        OR (
            document_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
            AND date(document_date) IS NOT NULL
            AND date(document_date) = document_date
        )
    )
);

CREATE TABLE IF NOT EXISTS accounting_transaction_documents (
    id            INTEGER PRIMARY KEY,

    transction_id INTEGER REFERENCES accounting_transactions(id),
    document_id   INTEGER REFERENCES documents(id),

    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER NOT NULL REFERENCES users(id),
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by INTEGER REFERENCES users(id),
    deleted_at TEXT,
    deleted_by INTEGER REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS transaction_lines (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id  INTEGER NOT NULL,
    account_id      INTEGER NOT NULL,
    amount_cents    INTEGER NOT NULL CHECK (amount_cents >= 0),
    is_debit        INTEGER NOT NULL,

    created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by  INTEGER,
    updated_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by  REFERENCES users(id),
    deleted_at  TEXT,
    deleted_by  REFERENCES users(id),

    CHECK (
        (deleted_at IS NULL AND deleted_by IS NULL) OR
        (deleted_at IS NOT NULL AND deleted_by IS NOT NULL)
    ),

    FOREIGN KEY (created_by) REFERENCES users(id),
    FOREIGN KEY (updated_by) REFERENCES users(id),
    FOREIGN KEY (deleted_by) REFERENCES users(id),
    FOREIGN KEY (transaction_id) REFERENCES accounting_transactions(id),
    FOREIGN KEY (account_id) REFERENCES accounts(id)
);

CREATE TABLE IF NOT EXISTS accounts_history (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,

    account_id        INTEGER NOT NULL REFERENCES accounts(id),

    account_number    INTEGER NOT NULL,
    account_name      TEXT    NOT NULL,
    account_type      TEXT    NOT NULL,
    description       TEXT,
    is_account_active INTEGER NOT NULL DEFAULT 1,

    updated_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by  INTEGER REFERENCES users(id),

    CHECK (
        account_type in ('Asset', 'Liability', 'Equity', 'Revenue', 'Expense')
    )
);

CREATE TABLE IF NOT EXISTS transaction_lines_history (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,

    transaction_line_id INTEGER REFERENCES transaction_lines(id),

    transaction_id      INTEGER NOT NULL,
    account_id          INTEGER NOT NULL,
    amount_cents        INTEGER NOT NULL CHECK (amount_cents >= 0),
    is_debit            INTEGER NOT NULL,

    updated_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by  INTEGER REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS accounting_transactions_history (
    id                         INTEGER PRIMARY KEY AUTOINCREMENT,

    transaction_id  INTEGER REFERENCES accounting_transactions(id),

    transaction_date           TEXT    NOT NULL,
    description                TEXT    NOT NULL,
    posting_reference          TEXT,

    updated_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by  INTEGER REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS documents_history (
    id                  INTEGER PRIMARY KEY,

    document_id         INTEGER REFERENCES documents(id),

    transaction_id      INTEGER,

    document_type       TEXT,
    document_date       TEXT,
    title               TEXT,
    description         TEXT,

    filename            TEXT,
    file_path           TEXT,
    mime_type           TEXT,
    file_size_bytes     INTEGER,

    sha256_hash         TEXT,

    source              TEXT,
    received_from       TEXT,
    notes               TEXT,

    updated_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by  INTEGER REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS miles_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    miles_id          INTEGER REFERENCES miles(id),
    business_id       INTEGER,
    miles_date        TEXT,
    tenth_miles       INTEGER,
    tenth_miles_begin INTEGER,
    tenth_miles_end   INTEGER,
    explanation       TEXT,
    vehicle           TEXT,

    created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by  INTEGER NOT NULL,
    updated_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by  INTEGER REFERENCES users(id),
    deleted_at  TEXT,
    deleted_by  INTEGER REFERENCES users(id),

    CHECK (
        tenth_miles_begin IS NULL
        OR tenth_miles_begin >= 0
    ),

    CHECK (
        tenth_miles_end IS NULL
        OR tenth_miles_end >= 0
    ),

    CHECK (
        tenth_miles_begin IS NULL
        OR tenth_miles_end IS NULL
        OR tenth_miles_end > tenth_miles_begin
    ),

    CHECK (
        (deleted_at IS NULL AND deleted_by IS NULL) OR
        (deleted_at IS NOT NULL AND deleted_by IS NOT NULL)
    ),

    FOREIGN KEY (created_by) REFERENCES users(id),
    FOREIGN KEY (updated_by) REFERENCES users(id),
    FOREIGN KEY (deleted_by) REFERENCES users(id)

);






------ Triggers for preventing created by/at
CREATE TRIGGER IF NOT EXISTS trg_businesses_prevent_created_update
BEFORE UPDATE OF created_at, created_by ON businesses
FOR EACH ROW
WHEN
    NEW.created_at IS NOT OLD.created_at
    OR NEW.created_by IS NOT OLD.created_by
BEGIN
    SELECT RAISE(ABORT, 'created_at and created_by cannot be updated');
END;

CREATE TRIGGER IF NOT EXISTS trg_accounts_prevent_created_update
BEFORE UPDATE OF created_at, created_by ON accounts
FOR EACH ROW
WHEN
    NEW.created_at IS NOT OLD.created_at
    OR NEW.created_by IS NOT OLD.created_by
BEGIN
    SELECT RAISE(ABORT, 'created_at and created_by cannot be updated');
END;

CREATE TRIGGER IF NOT EXISTS trg_accounting_transactions_prevent_created_update
BEFORE UPDATE OF created_at, created_by ON accounting_transactions
FOR EACH ROW
WHEN
    NEW.created_at IS NOT OLD.created_at
    OR NEW.created_by IS NOT OLD.created_by
BEGIN
    SELECT RAISE(ABORT, 'created_at and created_by cannot be updated');
END;

CREATE TRIGGER IF NOT EXISTS trg_documents_prevent_created_update
BEFORE UPDATE OF created_at, created_by ON documents
FOR EACH ROW
WHEN
    NEW.created_at IS NOT OLD.created_at
    OR NEW.created_by IS NOT OLD.created_by
BEGIN
    SELECT RAISE(ABORT, 'created_at and created_by cannot be updated');
END;

CREATE TRIGGER IF NOT EXISTS trg_accounting_transaction_documents_prevent_created_update
BEFORE UPDATE OF created_at, created_by ON accounting_transaction_documents
FOR EACH ROW
WHEN
    NEW.created_at IS NOT OLD.created_at
    OR NEW.created_by IS NOT OLD.created_by
BEGIN
    SELECT RAISE(ABORT, 'created_at and created_by cannot be updated');
END;

CREATE TRIGGER IF NOT EXISTS trg_transaction_lines_prevent_created_update
BEFORE UPDATE OF created_at, created_by ON transaction_lines
FOR EACH ROW
WHEN
    NEW.created_at IS NOT OLD.created_at
    OR NEW.created_by IS NOT OLD.created_by
BEGIN
    SELECT RAISE(ABORT, 'created_at and created_by cannot be updated');
END;

CREATE TRIGGER IF NOT EXISTS trg_miles_prevent_created_update
BEFORE UPDATE OF created_at, created_by ON miles
FOR EACH ROW
WHEN
    NEW.created_at IS NOT OLD.created_at
    OR NEW.created_by IS NOT OLD.created_by
BEGIN
    SELECT RAISE(ABORT, 'created_at and created_by cannot be updated');
END;





------ Trigger for copying history ------
CREATE TRIGGER IF NOT EXISTS trg_account_audit_update
BEFORE UPDATE OF
    business_id,
    account_number,
    account_name,
    account_type,
    description,
    is_account_active,
    updated_by,
    deleted_at,
    deleted_by
ON accounts
FOR EACH ROW
BEGIN
    INSERT INTO accounts_history (
        account_id,
        account_number,
        account_name,
        account_type,
        description,
        is_account_active,
        updated_at,
        updated_by
    )
    VALUES (
        OLD.id,
        OLD.account_number,
        OLD.account_name,
        OLD.account_type,
        OLD.description,
        OLD.is_account_active,
        CURRENT_TIMESTAMP,
        NEW.updated_by
    );
END;

CREATE TRIGGER IF NOT EXISTS trg_accounting_transactions_audit_update
BEFORE UPDATE OF
    transaction_date,
    description,
    posting_reference,
    updated_by,
    deleted_at,
    deleted_by
ON accounting_transactions
FOR EACH ROW
BEGIN
    INSERT INTO accounting_transactions_history (
        transaction_id,
        transaction_date,
        description,
        posting_reference,
        updated_at,
        updated_by
    )
    VALUES (
        OLD.id,
        OLD.transaction_date,
        OLD.description,
        OLD.posting_reference,
        CURRENT_TIMESTAMP,
        NEW.updated_by
    );
END;

CREATE TRIGGER IF NOT EXISTS trg_transaction_lines_audit_update
BEFORE UPDATE OF
    transaction_id,
    account_id,
    amount_cents,
    is_debit,
    updated_by,
    deleted_at,
    deleted_by
ON transaction_lines
FOR EACH ROW
BEGIN
    INSERT INTO transaction_lines_history (
        transaction_line_id,
        transaction_id,
        account_id,
        amount_cents,
        is_debit,
        updated_at,
        updated_by
    )
    VALUES (
        OLD.id,
        OLD.transaction_id,
        OLD.account_id,
        OLD.amount_cents,
        OLD.is_debit,
        CURRENT_TIMESTAMP,
        NEW.updated_by
    );
END;

CREATE TRIGGER IF NOT EXISTS trg_documents_audit_update
BEFORE UPDATE OF document_type, document_date, title, description, filename,
    file_path, mime_type, file_size_bytes, sha256_hash, source, received_from,
    notes, updated_by, deleted_at, deleted_by
ON documents
FOR EACH ROW
BEGIN
    INSERT INTO documents_history (
        document_id, document_type, document_date, title, description, filename,
        file_path, mime_type, file_size_bytes, sha256_hash, source, received_from,
        notes, updated_at, updated_by
    )
    VALUES (
        OLD.id, OLD.document_type, OLD.document_date, OLD.title, OLD.description,
        OLD.filename, OLD.file_path, OLD.mime_type, OLD.file_size_bytes,
        OLD.sha256_hash, OLD.source, OLD.received_from, OLD.notes,
        CURRENT_TIMESTAMP, NEW.updated_by
    );
END;

CREATE TRIGGER IF NOT EXISTS trg_miles_audit_update
BEFORE UPDATE OF business_id, miles_date, tenth_miles, tenth_miles_begin,
    tenth_miles_end, explanation, vehicle, updated_by, deleted_at, deleted_by
ON miles
FOR EACH ROW
BEGIN
    INSERT INTO miles_history (
        miles_id, business_id, miles_date, tenth_miles, tenth_miles_begin,
        tenth_miles_end, explanation, vehicle, created_at, created_by,
        updated_at, updated_by, deleted_at, deleted_by
    )
    VALUES (
        OLD.id, OLD.business_id, OLD.miles_date, OLD.tenth_miles,
        OLD.tenth_miles_begin, OLD.tenth_miles_end, OLD.explanation, OLD.vehicle,
        OLD.created_at, OLD.created_by, CURRENT_TIMESTAMP, NEW.updated_by,
        OLD.deleted_at, OLD.deleted_by
    );
END;






------ Triggers to update updated_at ------
CREATE TRIGGER IF NOT EXISTS trg_users_updated
AFTER UPDATE ON users
FOR EACH ROW
BEGIN
    UPDATE users
    SET updated_at = CURRENT_TIMESTAMP
    WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS trg_businesses_updated
AFTER UPDATE OF updated_by ON businesses
FOR EACH ROW
BEGIN
    UPDATE businesses
    SET updated_at = CURRENT_TIMESTAMP
    WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS trg_accounts_updated
AFTER UPDATE OF updated_by ON accounts
FOR EACH ROW
BEGIN
    UPDATE accounts
    SET updated_at = CURRENT_TIMESTAMP
    WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS trg_accounting_transactions_updated
AFTER UPDATE OF updated_by ON accounting_transactions
FOR EACH ROW
BEGIN
    UPDATE accounting_transactions
    SET updated_at = CURRENT_TIMESTAMP
    WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS trg_transaction_lines_updated
AFTER UPDATE OF updated_by ON transaction_lines
FOR EACH ROW
BEGIN
    UPDATE transaction_lines
    SET updated_at = CURRENT_TIMESTAMP
    WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS trg_documents_updated
AFTER UPDATE OF updated_by ON documents
FOR EACH ROW
BEGIN
    UPDATE documents
    SET updated_at = CURRENT_TIMESTAMP
    WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS trg_miles_updated
AFTER UPDATE OF updated_by ON miles
FOR EACH ROW
BEGIN
    UPDATE miles
    SET updated_at = CURRENT_TIMESTAMP
    WHERE id = NEW.id;
END;





------ Triggers preventing updates on audit tables
CREATE TRIGGER IF NOT EXISTS trg_accounts_history_prevent_update
BEFORE UPDATE ON accounts_history
FOR EACH ROW
BEGIN
    SELECT RAISE(ABORT, 'Audit records cannot be updated');
END;

CREATE TRIGGER IF NOT EXISTS trg_accounts_history_prevent_delete
BEFORE DELETE ON accounts_history
FOR EACH ROW
BEGIN
    SELECT RAISE(ABORT, 'Audit records cannot be deleted');
END;


CREATE TRIGGER IF NOT EXISTS trg_transaction_lines_history_prevent_update
BEFORE UPDATE ON transaction_lines_history
FOR EACH ROW
BEGIN
    SELECT RAISE(ABORT, 'Audit records cannot be updated');
END;

CREATE TRIGGER IF NOT EXISTS trg_transaction_lines_history_prevent_delete
BEFORE DELETE ON transaction_lines_history
FOR EACH ROW
BEGIN
    SELECT RAISE(ABORT, 'Audit records cannot be deleted');
END;


CREATE TRIGGER IF NOT EXISTS trg_accounting_transactions_history_prevent_update
BEFORE UPDATE ON accounting_transactions_history
FOR EACH ROW
BEGIN
    SELECT RAISE(ABORT, 'Audit records cannot be updated');
END;

CREATE TRIGGER IF NOT EXISTS trg_accounting_transactions_history_prevent_delete
BEFORE DELETE ON accounting_transactions_history
FOR EACH ROW
BEGIN
    SELECT RAISE(ABORT, 'Audit records cannot be deleted');
END;


CREATE TRIGGER IF NOT EXISTS trg_documents_history_prevent_update
BEFORE UPDATE ON documents_history
FOR EACH ROW
BEGIN
    SELECT RAISE(ABORT, 'Audit records cannot be updated');
END;

CREATE TRIGGER IF NOT EXISTS trg_documents_history_prevent_delete
BEFORE DELETE ON documents_history
FOR EACH ROW
BEGIN
    SELECT RAISE(ABORT, 'Audit records cannot be deleted');
END;

CREATE TRIGGER IF NOT EXISTS trg_miles_history_prevent_delete
BEFORE DELETE ON miles_history
FOR EACH ROW
BEGIN
    SELECT RAISE(ABORT, 'Audit records cannot be deleted');
END;





------ Indexing ------
CREATE INDEX IF NOT EXISTS idx_accounts_business
    ON accounts(business_id) WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_transactions_date
    ON accounting_transactions(transaction_date) WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_lines_transaction
    ON transaction_lines(transaction_id) WHERE deleted_at IS NULL;
