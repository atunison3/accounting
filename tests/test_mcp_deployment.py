import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from deploy.configure_mcp import configure_mcp


class TestMCPDeployment(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name)
        self.config = {
            "target": {
                "home": str(self.home),
                "user": "testuser",
                "service": "accounting",
                "checkout": str(self.home / "release"),
            },
            "web": {"mode": "lan", "port": 8002},
            "mcp": {"enabled": True, "user_id": 1, "bind": "127.0.0.1", "port": 8003},
        }

    def test_setup_generates_private_token_and_reuses_it(self):
        installed_units = []

        def record(command, **kwargs):
            if command[:2] == ["sudo", "install"]:
                installed_units.append(Path(command[-2]).read_text())

        with patch("deploy.configure_mcp.subprocess.run", side_effect=record):
            configure_mcp(self.config)
            token_file = self.home / ".config/accounting/mcp.token"
            token = token_file.read_text().strip()
            self.assertGreaterEqual(len(token), 32)
            self.assertEqual(token_file.stat().st_mode & 0o777, 0o600)
            configure_mcp(self.config)
            self.assertEqual(token_file.read_text().strip(), token)
        self.assertEqual(len(installed_units), 2)
        self.assertNotIn(token, installed_units[0])
        self.assertIn("ACCOUNTING_MCP_PORT=8003", installed_units[0])
        self.assertIn("-m accounting_server.server", installed_units[0])

    def test_disabled_is_noop(self):
        self.config["mcp"]["enabled"] = False
        with patch("deploy.configure_mcp.subprocess.run") as process:
            configure_mcp(self.config)
            process.assert_not_called()
        self.assertFalse((self.home / ".config").exists())

    def test_unsafe_bind_conflicting_port_and_missing_identity_rejected(self):
        cases = [{"bind": "0.0.0.0"}, {"bind": "8.8.8.8"}, {"port": 8002}, {"user_id": None}]
        for changes in cases:
            with self.subTest(changes=changes):
                config = {**self.config, "mcp": {**self.config["mcp"], **changes}}
                with patch("deploy.configure_mcp.subprocess.run") as process:
                    with self.assertRaises(ValueError):
                        configure_mcp(config)
                    process.assert_not_called()
        self.config["web"]["mode"] = "internet"
        self.config["mcp"]["bind"] = "192.168.1.10"
        with self.assertRaises(ValueError):
            configure_mcp(self.config)


if __name__ == "__main__":
    unittest.main()
