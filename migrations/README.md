# Mileage locations and travel documents

`001_mileage_locations.sql` upgrades the schema that has `miles.explanation` and
`miles_history.explanation`. It preserves mileage records, audit history, and
existing `mileage_documents` links.

## Automatic upgrade

The application checks and upgrades the mileage schema when opening a database.
Repeated opens are supported. Existing location fields remain NULL until supplied;
no locations or routes are invented for historical trips.

## Manual upgrade of an existing installation

1. Stop all accounting app/MCP processes that use this database.
2. Back up the database using SQLite's backup command (including WAL contents):

   ```sh
   sqlite3 ~/.app_data/accounting/accounting.db ".backup '$HOME/.app_data/accounting/accounting-before-mileage.db'"
   ```

3. Before starting the updated app, run from the repository root:

   ```sh
   sqlite3 -bail ~/.app_data/accounting/accounting.db < migrations/001_mileage_locations.sql
   ```

4. Start the updated application. `PRAGMA foreign_key_check` should produce no rows.

The standalone SQL is a **one-time migration**, not an idempotent schema loader.
Do not run it after the application has already upgraded the database. Check with
`PRAGMA table_info(miles);`: if `business_purpose` exists instead of `explanation`,
the rename has already been applied. No database deletion/recreation is required.

## Data representation

- `starting_location`: origin of the trip.
- `destination_location`: ordered stops stored as newline-separated text. The form
  accepts one city, town, area, or address per line, including the return location.
- `business_purpose`: renamed from `explanation` in both live records and history.
- The mileage audit trigger records previous values when purpose or locations change.
- `travel_docs`: mileage-to-document link table, renamed from `mileage_documents`.
  Multiple receipts, maps, or screenshots may be attached to a mileage log. File
  metadata stays in `documents`, with files stored under the existing randomized
  `~/.app_data/accounting/documents/<business_id>/` layout.
- Document coverage counts only non-deleted links to non-deleted documents.

From **Mileage**, use **Attach** to upload travel evidence and **View documents**
to retrieve it. The upload verifies that the mileage log belongs to the selected
business and redirects to the mileage query after success. It does not alter a
journal transaction. Expense categories/amounts remain outside this schema change;
record financial expenses through accounting transactions.
