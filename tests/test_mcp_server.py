"""Exercise MCP against temporary ledgers, never the user's accounting data."""

import unittest
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

from pydantic import ValidationError
from starlette.testclient import TestClient

from accounting.domain.models import Account, AccountType, Business, User
from accounting.infrastructure.sqlite.connection import get_connection
from accounting.infrastructure.sqlite.repositories import (
    SqliteAccountRepository,
    SqliteBusinessRepository,
    SqliteUserRepository,
)
from accounting_server.server import Ledger, TransactionInput, create_app


class TestMCPServer(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.database = Path(temporary.name) / "test.db"
        with get_connection(self.database) as connection:
            self.user_id = SqliteUserRepository(connection).add(
                User(
                    username="agent",
                    first_name="MCP",
                    last_name="Test",
                    email="agent@example.com",
                )
            )
            businesses = SqliteBusinessRepository(connection)
            self.business_id = businesses.add(Business(title="Test", created_by=self.user_id))
            self.other_business = businesses.add(Business(title="Other", created_by=self.user_id))
            accounts = SqliteAccountRepository(connection)
            self.accounts = [
                accounts.add(
                    Account(
                        business_id=business,
                        account_number=number,
                        account_name=name,
                        account_type=kind,
                        created_by=self.user_id,
                    )
                )
                for business, number, name, kind in [
                    (self.business_id, 1000, "Cash", AccountType.ASSET),
                    (self.business_id, 4000, "Sales", AccountType.REVENUE),
                    (self.other_business, 1000, "Other cash", AccountType.ASSET),
                ]
            ]
        self.ledger = Ledger(self.database, self.user_id)
        self.token = "test-only-token-" + "a" * 32
        self.headers = {"Authorization": f"Bearer {self.token}", "Accept": "application/json, text/event-stream"}

    def payload(self):
        return TransactionInput(
            business_id=self.business_id,
            transaction_date=date(2026, 1, 15),
            description="Sale",
            lines=[
                {"account_id": self.accounts[0], "amount_cents": 1250, "is_debit": True},
                {"account_id": self.accounts[1], "amount_cents": 1250, "is_debit": False},
            ],
        )

    def test_create_update_delete_and_audit(self):
        created = self.ledger.create(self.payload())
        self.assertEqual(created["created_by"], self.user_id)
        self.assertEqual(len(created["lines"]), 2)
        payload = self.payload()
        payload.description = "Corrected sale"
        updated = self.ledger.update(created["id"], payload, created["revision"])
        self.assertEqual(updated["description"], "Corrected sale")
        self.assertNotEqual(updated["revision"], created["revision"])
        with self.ledger.connect() as connection:
            history = connection.execute("SELECT COUNT(*) FROM accounting_transactions_history").fetchone()[0]
            self.assertGreater(history, 0)
        with self.assertRaisesRegex(ValueError, "approval"):
            self.ledger.delete(created["id"], updated["revision"], False)
        result = self.ledger.delete(created["id"], updated["revision"], True)
        self.assertTrue(result["soft_deleted"])
        with self.ledger.connect() as connection:
            with self.assertRaisesRegex(ValueError, "not found"):
                self.ledger.transaction(connection, created["id"])
            row = connection.execute(
                "SELECT deleted_by FROM accounting_transactions WHERE id=?", (created["id"],)
            ).fetchone()
            self.assertEqual(row[0], self.user_id)

    def test_unbalanced_write_and_update_roll_back(self):
        payload = self.payload()
        payload.lines[0].amount_cents += 1
        with self.assertRaisesRegex(ValueError, "equal"):
            self.ledger.create(payload)
        with self.ledger.connect() as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM accounting_transactions").fetchone()[0], 0)
        created = self.ledger.create(self.payload())
        with self.assertRaisesRegex(ValueError, "equal"):
            self.ledger.update(created["id"], payload, created["revision"])
        with self.ledger.connect() as connection:
            self.assertEqual(self.ledger.transaction(connection, created["id"]), created)

    def test_foreign_business_account_and_missing_account_rejected(self):
        for account_id in [self.accounts[2], 99999]:
            with self.subTest(account_id=account_id):
                payload = self.payload()
                payload.lines[0].account_id = account_id
                with self.assertRaisesRegex(ValueError, "belong"):
                    self.ledger.create(payload)

    def test_stale_revision_rejects_update_and_delete(self):
        created = self.ledger.create(self.payload())
        payload = self.payload()
        payload.description = "Concurrent website edit"
        self.ledger.update(created["id"], payload, created["revision"])
        with self.assertRaisesRegex(ValueError, "changed"):
            self.ledger.update(created["id"], self.payload(), created["revision"])
        with self.assertRaisesRegex(ValueError, "changed"):
            self.ledger.delete(created["id"], created["revision"], True)

    def test_pagination_and_date_validation(self):
        first = self.ledger.create(self.payload())
        second = self.ledger.create(self.payload())
        page = self.ledger.list_transactions(self.business_id, date(2026, 1, 15), date(2026, 1, 15), 1)
        self.assertEqual(page["transactions"][0]["id"], first["id"])
        self.assertEqual(page["next_offset"], 1)
        page = self.ledger.list_transactions(self.business_id, date(2026, 1, 15), date(2026, 1, 15), 1, 1)
        self.assertEqual(page["transactions"][0]["id"], second["id"])
        self.assertIsNone(page["next_offset"])
        with self.assertRaises(ValueError):
            self.ledger.list_transactions(self.business_id, date(2026, 2, 1), date(2026, 1, 1))

    def test_strict_amounts_and_unexpected_fields(self):
        for amount in [0, -1, 1.25, True, "100"]:
            with self.subTest(amount=amount):
                data = self.payload().model_dump()
                data["lines"][0]["amount_cents"] = amount
                with self.assertRaises(ValidationError):
                    TransactionInput.model_validate(data)
        data = self.payload().model_dump()
        data["user_id"] = 999
        with self.assertRaises(ValidationError):
            TransactionInput.model_validate(data)

    def test_missing_database_and_audit_user_fail_closed(self):
        missing = self.database.with_name("missing.db")
        with self.assertRaises(ValueError):
            Ledger(missing, self.user_id)
        self.assertFalse(missing.exists())
        with self.assertRaisesRegex(ValueError, "audit user"):
            Ledger(self.database, 999)
        with self.ledger.connect(write=True) as connection:
            connection.execute("UPDATE users SET is_active=0 WHERE id=?", (self.user_id,))
        with self.assertRaisesRegex(ValueError, "audit user"):
            self.ledger.create(self.payload())

    def client(self):
        return TestClient(create_app(self.database, self.user_id, self.token, ["testserver"]))

    def test_http_auth_all_methods_and_browser_origin(self):
        with self.client() as client:
            for method in ["GET", "POST", "DELETE"]:
                self.assertEqual(client.request(method, "/mcp").status_code, 401)
                self.assertEqual(
                    client.request(method, "/mcp", headers={"Authorization": "Bearer wrong"}).status_code, 401
                )
            response = client.post("/mcp", headers={**self.headers, "Origin": "https://evil.example"}, json={})
            self.assertEqual(response.status_code, 403)

    def test_http_initialize_tools_and_transaction_roundtrip(self):
        with self.client() as client:

            def rpc(method, params=None):
                response = client.post(
                    "/mcp",
                    headers=self.headers,
                    json={
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": method,
                        "params": params or {},
                    },
                )
                self.assertEqual(response.status_code, 200, response.text)
                return response.json()["result"]

            initialized = rpc(
                "initialize",
                {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "test", "version": "1"}},
            )
            self.assertEqual(initialized["serverInfo"]["name"], "accounting")
            tools = {tool["name"]: tool for tool in rpc("tools/list")["tools"]}
            self.assertEqual(len(tools), 7)
            self.assertTrue(tools["get_transaction"]["annotations"]["readOnlyHint"])
            self.assertTrue(tools["delete_transaction"]["annotations"]["destructiveHint"])
            created = rpc(
                "tools/call",
                {
                    "name": "create_transaction",
                    "arguments": {
                        "payload": self.payload().model_dump(mode="json"),
                    },
                },
            )
            self.assertFalse(created.get("isError", False), created)
            transaction = created["structuredContent"]
            read = rpc("tools/call", {"name": "get_transaction", "arguments": {"transaction_id": transaction["id"]}})
            self.assertEqual(read["structuredContent"]["revision"], transaction["revision"])
            missing = rpc("tools/call", {"name": "get_transaction", "arguments": {"transaction_id": 9999}})
            self.assertTrue(missing["isError"])
            bad_host = client.post("/mcp", headers={**self.headers, "Host": "evil.example"}, json={})
            self.assertEqual(bad_host.status_code, 421)


if __name__ == "__main__":
    unittest.main()
