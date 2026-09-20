"""Migration and HTTP regression tests using isolated databases and uploads."""

import sqlite3
import unittest
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from fastapi.testclient import TestClient

from accounting.infrastructure.sqlite.connection import create_connection, get_connection
from accounting.infrastructure.sqlite.repositories import SqliteMileageRepository
from accounting.website.app import create_app
from accounting.website.mileage_pdf import mileage_pdf, miles

ROOT = Path(__file__).resolve().parents[1]


class TestMileageChanges(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.database = Path(self.temp.name) / "accounting.db"
        self.files = Path(self.temp.name) / "documents"
        with closing(sqlite3.connect(self.database)) as connection:
            connection.executescript((ROOT / "tests/fixtures/pre_mileage_locations.sql").read_text())
            connection.executescript("""
                INSERT INTO users (id, username, first_name, last_name, email)
                    VALUES (1, 'test', 'Test', 'User', 'test@example.com');
                INSERT INTO businesses (id, title, created_by) VALUES (1, 'Test business', 1);
                INSERT INTO businesses (id, title, created_by) VALUES (2, 'Other business', 1);
                INSERT INTO miles (id, business_id, miles_date, tenth_miles, explanation, created_by)
                    VALUES (1, 1, '2026-08-18', 125, 'Client visit', 1);
                UPDATE miles SET explanation = 'Client visits', updated_by = 1 WHERE id = 1;
                INSERT INTO documents (id, document_type, document_date, filename, file_path, created_by)
                    VALUES (1, 'Map', '2026-08-18', 'map.png', 'map.png', 1);
                INSERT INTO mileage_documents (mileage_id, document_id, created_by) VALUES (1, 1, 1);
            """)

    def assert_migrated(self) -> None:
        with get_connection(self.database) as connection:
            repo = SqliteMileageRepository(connection)
            trip = repo.get_by_id(1)
            if trip is None:
                self.fail("Migrated mileage record was not found")
            self.assertEqual(trip.business_purpose, "Client visits")
            self.assertIsNone(trip.starting_location)
            self.assertEqual(repo.summary(1, 2026), (125, 1, 0))
            self.assertEqual(repo.documents(1)[0].filename, "map.png")
            history = connection.execute("SELECT business_purpose FROM miles_history ORDER BY id").fetchall()
            self.assertEqual(history[0][0], "Client visit")
            connection.execute("""
                UPDATE miles SET starting_location = 'Home', destination_location = 'Clinic\nBank',
                    business_purpose = 'Visits and banking', updated_by = 1 WHERE id = 1
            """)
            connection.execute("UPDATE miles SET destination_location = 'Clinic\nBank\nHome' WHERE id = 1")
            old = connection.execute("SELECT * FROM miles_history ORDER BY id DESC LIMIT 1").fetchone()
            self.assertEqual(old["starting_location"], "Home")
            self.assertEqual(old["destination_location"], "Clinic\nBank")
            self.assertEqual(old["business_purpose"], "Visits and banking")
            self.assertEqual(connection.execute("PRAGMA foreign_key_check").fetchall(), [])
        # Opening again must not fail or destroy document links.
        with get_connection(self.database) as connection:
            self.assertEqual(SqliteMileageRepository(connection).summary(1, 2026), (125, 1, 0))

    def test_automatic_migration_preserves_data_history_and_links(self) -> None:
        self.assert_migrated()

    def test_standalone_script_then_application_start(self) -> None:
        with closing(sqlite3.connect(self.database)) as connection:
            connection.executescript((ROOT / "migrations/001_mileage_locations.sql").read_text())
        self.assert_migrated()

    def test_fresh_schema_and_repeated_initialization(self) -> None:
        path = Path(self.temp.name) / "fresh.db"
        for _ in range(2):
            connection = create_connection(path)
            try:
                columns = {row[1] for row in connection.execute("PRAGMA table_info(miles)")}
                self.assertTrue({"business_purpose", "starting_location", "destination_location"} <= columns)
                self.assertNotIn("explanation", columns)
                self.assertIsNotNone(
                    connection.execute("SELECT name FROM sqlite_master WHERE name='travel_docs'").fetchone()
                )
            finally:
                connection.close()

    def test_mileage_pdf_export_and_filters(self) -> None:
        app = create_app()
        app.state.db_path = self.database
        with TestClient(app) as client:
            response = client.get("/mileage/pdf?business_id=1&date_from=2026-08-01&date_to=2026-08-31")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers["content-type"], "application/pdf")
            self.assertTrue(response.content.startswith(b"%PDF-"))
            self.assertIn("mileage-log-1.pdf", response.headers["content-disposition"])
            # Empty queries also produce printable reports.
            self.assertEqual(client.get("/mileage/pdf?business_id=1&vehicle=Unknown").status_code, 200)
            self.assertEqual(client.get("/mileage/pdf?business_id=999").status_code, 404)
            self.assertEqual(
                client.get("/mileage/pdf?business_id=1&date_from=2026-09-01&date_to=2026-08-01").status_code, 422
            )

    def test_printable_mileage_wraps_and_paginates(self) -> None:
        self.assertEqual(miles(125), "12.5")
        self.assertEqual(miles(0), "0.0")
        self.assertEqual(miles(None), "—")
        row = {
            "miles_date": "2026-08-18",
            "tenth_miles": 125,
            "vehicle": "Car",
            "starting_location": "Home & office",
            "destination_location": "Clinic\nBank\nHome",
            "tenth_miles_begin": None,
            "tenth_miles_end": None,
            "business_purpose": "Client visits <appointments> " * 15,
        }
        report = mileage_pdf("Business & Co", [row] * 60, None, None, None)
        self.assertTrue(report.startswith(b"%PDF-"))

    def test_create_multistop_trip_attach_and_download(self) -> None:
        app = create_app()
        app.state.db_path = self.database
        with patch("accounting.website.routes.DOCUMENTS_DIRECTORY", self.files), TestClient(app) as client:
            response = client.post(
                "/mileage/create",
                data={
                    "business_id": "1",
                    "mileage_date": "2026-08-19",
                    "miles": "12.5",
                    "start_miles": "100",
                    "end_miles": "112.5",
                    "created_by": "1",
                    "business_purpose": "Client visit and banking",
                    "starting_location": "Home",
                    "destination_location": " Clinic \n Bank \n Home ",
                },
                follow_redirects=False,
            )
            self.assertEqual(response.status_code, 303)
            rows = client.get("/api/mileage?business_id=1").json()
            trip = rows[0]
            self.assertEqual(trip["business_purpose"], "Client visit and banking")
            self.assertEqual(trip["destination_location"], "Clinic\nBank\nHome")
            self.assertEqual(trip["miles"], 12.5)
            self.assertFalse(trip["has_document"])
            form = {
                "business_id": "1",
                "mileage_id": str(trip["id"]),
                "created_by": "1",
                "document_type": "Map",
                "document_date": "2026-08-19",
                "return_to": "/mileage?business_id=1",
            }
            for _ in range(2):
                response = client.post(
                    "/documents/upload",
                    data=form,
                    files={"document_file": ("map.png", b"map bytes", "image/png")},
                    follow_redirects=False,
                )
                self.assertEqual(response.status_code, 303)
                self.assertEqual(response.headers["location"], "/mileage?business_id=1")
            self.assertEqual(len(list((self.files / "1").iterdir())), 2)
            with get_connection(self.database) as connection:
                docs = SqliteMileageRepository(connection).documents(trip["id"])
                self.assertEqual(len(docs), 2)
            self.assertEqual(client.get(f"/documents/{docs[0].id}/download").content, b"map bytes")
            self.assertIn("map.png", client.get(f"/mileage/{trip['id']}/documents").text)
            self.assertTrue(client.get("/api/mileage?business_id=1").json()[0]["has_document"])
            self.assertEqual(
                client.get("/api/mileage/summary?business_id=1&year=2026").json()["without_document_percentage"], 0
            )
            form["business_id"] = "2"
            response = client.post(
                "/documents/upload", data=form, files={"document_file": ("map.png", b"map", "image/png")}
            )
            self.assertEqual(response.status_code, 400)
            self.assertFalse((self.files / "2").exists())
