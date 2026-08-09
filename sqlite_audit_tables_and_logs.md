# SQLite Audit Tables and Logs

There are several common SQLite audit designs. For Bob’s requirement—recording when a row changed, who changed it, and what the old value was—the most reliable approach is usually an append-only audit/history table populated by triggers.

Suppose Bob has:

```sql
CREATE TABLE Account (
    Id INTEGER PRIMARY KEY,
    AccountName TEXT NOT NULL,
    Description TEXT,
    IsActive INTEGER NOT NULL DEFAULT 1
);
```

## 1. Audit Columns on the Original Table

You can add:

```sql
UpdatedAt TEXT,
UpdatedBy INTEGER
```

This answers:

> Who changed this row most recently, and when?

But it does not answer:

> What was it before?

Every update overwrites the previous audit information. This is useful, but it is not a complete audit history.

## 2. Full-Row History Table

This is probably the design I would use for an accounting application.

Create a table containing previous versions of the record:

```sql
CREATE TABLE AccountHistory (
    HistoryId INTEGER PRIMARY KEY AUTOINCREMENT,

    AccountId INTEGER NOT NULL,

    AccountName TEXT NOT NULL,
    Description TEXT,
    IsActive INTEGER NOT NULL,

    ChangedAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ChangedBy INTEGER NOT NULL,

    FOREIGN KEY (AccountId) REFERENCES Account(Id),
    FOREIGN KEY (ChangedBy) REFERENCES User(Id)
);
```

Then before updating an account, copy the old row into the history table:

```sql
CREATE TRIGGER trg_Account_AuditUpdate
BEFORE UPDATE ON Account
FOR EACH ROW
BEGIN
    INSERT INTO AccountHistory (
        AccountId,
        AccountName,
        Description,
        IsActive,
        ChangedAt,
        ChangedBy
    )
    VALUES (
        OLD.Id,
        OLD.AccountName,
        OLD.Description,
        OLD.IsActive,
        CURRENT_TIMESTAMP,
        NEW.UpdatedBy
    );
END;
```

Now imagine the account originally contains:

```text
Id:          15
AccountName: Office Supplies
Description: General office supplies
IsActive:    1
```

Bob changes it to:

```text
AccountName: Office Supplies and Equipment
```

The `Account` table contains the current state, while `AccountHistory` contains:

```text
HistoryId:   1
AccountId:   15
AccountName: Office Supplies
Description: General office supplies
IsActive:    1
ChangedAt:   2026-08-08 14:30:00
ChangedBy:   4
```

So you can reconstruct exactly what existed before the change.

This design is simple and quite powerful.

## 3. Change/Event Audit Table

Instead of storing an entire old row, you can store individual field changes:

```sql
CREATE TABLE AuditLog (
    Id INTEGER PRIMARY KEY AUTOINCREMENT,
    TableName TEXT NOT NULL,
    RecordId INTEGER NOT NULL,
    ColumnName TEXT NOT NULL,
    OldValue TEXT,
    NewValue TEXT,
    ChangedAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ChangedBy INTEGER NOT NULL
);
```

An update might produce:

```text
TableName   RecordId  ColumnName   OldValue          NewValue
----------  --------  -----------  ----------------  -----------------------------
Account     15        AccountName  Office Supplies   Office Supplies and Equipment
```

This is attractive because a person can immediately see:

> Bob changed `AccountName` from X to Y.

But SQLite triggers become considerably more verbose because you generally need to test each field:

```sql
CREATE TRIGGER trg_Account_AuditUpdate
AFTER UPDATE ON Account
FOR EACH ROW
BEGIN
    INSERT INTO AuditLog (
        TableName,
        RecordId,
        ColumnName,
        OldValue,
        NewValue,
        ChangedAt,
        ChangedBy
    )
    SELECT
        'Account',
        OLD.Id,
        'AccountName',
        OLD.AccountName,
        NEW.AccountName,
        CURRENT_TIMESTAMP,
        NEW.UpdatedBy
    WHERE OLD.AccountName IS NOT NEW.AccountName;

    INSERT INTO AuditLog (
        TableName,
        RecordId,
        ColumnName,
        OldValue,
        NewValue,
        ChangedAt,
        ChangedBy
    )
    SELECT
        'Account',
        OLD.Id,
        'Description',
        OLD.Description,
        NEW.Description,
        CURRENT_TIMESTAMP,
        NEW.UpdatedBy
    WHERE OLD.Description IS NOT NEW.Description;
END;
```

Notice the use of:

```sql
OLD.Description IS NOT NEW.Description
```

rather than:

```sql
OLD.Description != NEW.Description
```

The former handles `NULL` correctly.

## 4. Store Before/After Rows as JSON

SQLite's JSON support gives you another option:

```sql
CREATE TABLE AuditLog (
    Id INTEGER PRIMARY KEY AUTOINCREMENT,
    TableName TEXT NOT NULL,
    RecordId INTEGER NOT NULL,
    Operation TEXT NOT NULL,
    OldData TEXT,
    NewData TEXT,
    ChangedAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ChangedBy INTEGER NOT NULL
);
```

Then:

```sql
INSERT INTO AuditLog (
    TableName,
    RecordId,
    Operation,
    OldData,
    NewData,
    ChangedBy
)
VALUES (
    'Account',
    OLD.Id,
    'UPDATE',
    json_object(
        'AccountName', OLD.AccountName,
        'Description', OLD.Description,
        'IsActive', OLD.IsActive
    ),
    json_object(
        'AccountName', NEW.AccountName,
        'Description', NEW.Description,
        'IsActive', NEW.IsActive
    ),
    NEW.UpdatedBy
);
```

You end up with something conceptually like:

```json
{
    "AccountName": "Office Supplies",
    "Description": "General office supplies",
    "IsActive": 1
}
```

and:

```json
{
    "AccountName": "Office Supplies and Equipment",
    "Description": "General office supplies",
    "IsActive": 1
}
```

This is much easier to implement generically across many tables, but it gives up some relational structure and type enforcement.

## Recommended Design

For an accounting application, I would lean toward a combination of normal audit columns and full-row history tables:

```text
Account
├── Id
├── AccountName
├── ...
├── CreatedAt
├── CreatedBy
├── UpdatedAt
├── UpdatedBy
├── DeletedAt
└── DeletedBy

AccountHistory
├── HistoryId
├── AccountId
├── AccountName
├── ...
├── ChangedAt
├── ChangedBy
└── ChangeType
```

With:

```sql
ChangeType TEXT NOT NULL CHECK (
    ChangeType IN ('UPDATE', 'DELETE')
)
```

The important distinction is that `Account` represents the current truth, while `AccountHistory` represents previous truths.

For example:

```text
Account

Id   AccountName
15   Office Supplies and Equipment
```

and:

```text
AccountHistory

HistoryId   AccountId   AccountName       ChangedAt            ChangedBy
1           15          Office Supplies   2026-08-08 14:30     4
```

This also works particularly well with a soft-delete approach. A deletion does not actually destroy the row; you set `DeletedAt` and `DeletedBy`, and the audit/history table preserves what happened before that transition.
