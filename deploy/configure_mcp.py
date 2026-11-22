"""Ubuntu-side MCP service configuration, invoked by the archive installer.

Real host/audit-user settings come from the ignored deployment TOML's [mcp]
section. The token is generated only on Ubuntu and never put in Git or logs.
"""

import ipaddress
import os
from pathlib import Path
import secrets
import subprocess
import tempfile


def configure_mcp(config):
    settings = config.get("mcp", {})
    if not settings.get("enabled", False):
        return
    target = config["target"]
    host = settings.get("bind", "127.0.0.1")
    address = ipaddress.ip_address(host)
    allowed = any(
        address in ipaddress.ip_network(network)
        for network in ("127.0.0.0/8", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")
    )
    if not allowed:
        raise ValueError("MCP must bind to loopback or an RFC1918 LAN IPv4 address")
    if config["web"]["mode"] == "internet" and not address.is_loopback:
        raise ValueError("Internet mode requires loopback MCP with an SSH tunnel or HTTPS proxy")
    port = settings.get("port", 8003)
    user_id = settings.get("user_id")
    if type(port) is not int or not 1024 <= port <= 65535 or port == config["web"]["port"]:
        raise ValueError("MCP needs a separate unprivileged port from the website")
    if type(user_id) is not int or user_id <= 0:
        raise ValueError("Set mcp.user_id to an existing active accounting user ID")
    home = Path(target["home"])
    database = home / ".app_data/accounting/accounting.db"
    python = Path(target["checkout"]) / ".venv/bin/python"
    # Validate the installed package and user before installing/starting the service.
    subprocess.run(
        [
            str(python),
            "-c",
            "import sys; from pathlib import Path; from accounting_server.server import Ledger; "
            "Ledger(Path(sys.argv[1]), int(sys.argv[2]))",
            str(database),
            str(user_id),
        ],
        check=True,
    )
    private = home / ".config/accounting"
    private.mkdir(parents=True, exist_ok=True, mode=0o700)
    token_file = private / "mcp.token"
    if not token_file.exists():
        descriptor = os.open(token_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w") as stream:
            stream.write(secrets.token_urlsafe(48) + "\n")
    if token_file.is_symlink() or token_file.stat().st_mode & 0o077:
        raise ValueError("MCP token must be a regular owner-only file (chmod 600)")
    service = target["service"] + "-mcp.service"
    unit = f"""[Unit]
Description=Authenticated accounting MCP server
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User={target['user']}
WorkingDirectory={target['checkout']}
Environment=HOME={home}
Environment=ACCOUNTING_DATABASE_PATH={database}
Environment=ACCOUNTING_MCP_HOST={host}
Environment=ACCOUNTING_MCP_PORT={port}
Environment=ACCOUNTING_MCP_USER_ID={user_id}
Environment=ACCOUNTING_MCP_TOKEN_FILE={token_file}
ExecStart={python} -m accounting_server.server
Restart=on-failure
RestartSec=5
UMask=0077
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full

[Install]
WantedBy=multi-user.target
"""
    with tempfile.TemporaryDirectory() as temporary:
        path = Path(temporary) / service
        path.write_text(unit)
        subprocess.run(
            ["sudo", "install", "-o", "root", "-g", "root", "-m", "600", str(path), f"/etc/systemd/system/{service}"],
            check=True,
        )
    subprocess.run(["sudo", "systemctl", "daemon-reload"], check=True)
    subprocess.run(["sudo", "systemctl", "enable", service], check=True)
    subprocess.run(["sudo", "systemctl", "restart", service], check=True)
    # Probe without printing/sending a token through command-line arguments.
    probe = """
import json, sys, time, urllib.request, urllib.error
from pathlib import Path
url, token_file = sys.argv[1:]
headers = {'Authorization': 'Bearer ' + Path(token_file).read_text().strip(),
           'Accept': 'application/json, text/event-stream', 'Content-Type': 'application/json'}
body = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {
    'protocolVersion': '2025-03-26', 'capabilities': {},
    'clientInfo': {'name': 'deployment-check', 'version': '1'}}}).encode()
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
for attempt in range(20):
    try:
        with opener.open(urllib.request.Request(url, data=body, headers=headers), timeout=3) as response:
            result = json.load(response)
            if result.get('result', {}).get('serverInfo', {}).get('name') == 'accounting':
                break
    except (OSError, urllib.error.URLError):
        pass
    time.sleep(1)
else:
    raise RuntimeError('MCP initialization failed; inspect the service journal')
"""
    subprocess.run([str(python), "-c", probe, f"http://{host}:{port}/mcp", str(token_file)], check=True)
    print(f"MCP healthy: http://{host}:{port}/mcp; private token file: {token_file}", flush=True)
