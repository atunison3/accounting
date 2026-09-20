"""Idempotent upgrade of mileage fields before loading the current schema."""

import sqlite3


def migrate_mileage(connection: sqlite3.Connection) -> None:
    miles = {row[1] for row in connection.execute("PRAGMA table_info(miles)")}
    history = {row[1] for row in connection.execute("PRAGMA table_info(miles_history)")}
    if not miles:
        return
    with connection:
        required = {"business_purpose", "starting_location", "destination_location"}
        if not required.issubset(miles) or not required.issubset(history):
            connection.execute("DROP TRIGGER IF EXISTS trg_miles_audit_update")
        if "explanation" in miles:
            connection.execute("ALTER TABLE miles RENAME COLUMN explanation TO business_purpose")
        if "explanation" in history:
            connection.execute("ALTER TABLE miles_history RENAME COLUMN explanation TO business_purpose")
        if "starting_location" not in miles:
            connection.execute("ALTER TABLE miles ADD COLUMN starting_location TEXT")
        if "destination_location" not in miles:
            connection.execute("ALTER TABLE miles ADD COLUMN destination_location TEXT")
        if history and "starting_location" not in history:
            connection.execute("ALTER TABLE miles_history ADD COLUMN starting_location TEXT")
        if history and "destination_location" not in history:
            connection.execute("ALTER TABLE miles_history ADD COLUMN destination_location TEXT")
        old_links = connection.execute("SELECT name FROM sqlite_master WHERE name = 'mileage_documents'").fetchone()
        if old_links:
            connection.execute("ALTER TABLE mileage_documents RENAME TO travel_docs")
