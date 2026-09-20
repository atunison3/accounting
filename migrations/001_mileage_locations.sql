-- One-time migration from the pre-mileage-location schema. Stop the app and back up first.
-- Run with: sqlite3 -bail ~/.app_data/accounting/accounting.db < migrations/001_mileage_locations.sql
-- Do not run after the application has already auto-migrated the database.
PRAGMA foreign_keys = ON;
BEGIN IMMEDIATE;
DROP TRIGGER IF EXISTS trg_miles_audit_update;
ALTER TABLE miles RENAME COLUMN explanation TO business_purpose;
ALTER TABLE miles ADD COLUMN starting_location TEXT;
ALTER TABLE miles ADD COLUMN destination_location TEXT;
ALTER TABLE miles_history RENAME COLUMN explanation TO business_purpose;
ALTER TABLE miles_history ADD COLUMN starting_location TEXT;
ALTER TABLE miles_history ADD COLUMN destination_location TEXT;
CREATE TABLE IF NOT EXISTS mileage_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mileage_id INTEGER NOT NULL REFERENCES miles(id),
    document_id INTEGER NOT NULL REFERENCES documents(id),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER NOT NULL REFERENCES users(id),
    deleted_at TEXT,
    deleted_by INTEGER REFERENCES users(id)
);
ALTER TABLE mileage_documents RENAME TO travel_docs;
CREATE TRIGGER IF NOT EXISTS trg_miles_audit_update
BEFORE UPDATE OF business_id, miles_date, tenth_miles, tenth_miles_begin,
    tenth_miles_end, business_purpose, starting_location, destination_location,
    vehicle, updated_by, deleted_at, deleted_by
ON miles
FOR EACH ROW
BEGIN
    INSERT INTO miles_history (
        miles_id, business_id, miles_date, tenth_miles, tenth_miles_begin,
        tenth_miles_end, business_purpose, starting_location, destination_location, vehicle, created_at, created_by,
        updated_at, updated_by, deleted_at, deleted_by
    )
    VALUES (
        OLD.id, OLD.business_id, OLD.miles_date, OLD.tenth_miles,
        OLD.tenth_miles_begin, OLD.tenth_miles_end, OLD.business_purpose,
        OLD.starting_location, OLD.destination_location, OLD.vehicle,
        OLD.created_at, OLD.created_by, CURRENT_TIMESTAMP, NEW.updated_by,
        OLD.deleted_at, OLD.deleted_by
    );
END;
COMMIT;
PRAGMA foreign_key_check;
