"""Ubuntu/systemd deployment helper. Python 3.11+, standard library only.

Rendering is safe on any platform. Deploy runs locally ON THE TARGET SERVER;
it stops the service, backs up data, and installs an exact fetched Git tag.
It never pushes Git changes, transfers data, or configures firewall/proxy rules.
"""

import argparse
import ipaddress
import os
from pathlib import Path
import pwd
import re
import shutil
import subprocess
import tempfile
import tomllib
from datetime import datetime, timezone


def run(*args, **kwargs):
    return subprocess.run(args, check=True, text=True, **kwargs)


def load_config(path):
    with open(path, "rb") as stream:
        config = tomllib.load(stream)
    target, web = config["target"], config["web"]
    for key in ("user", "service"):
        if not re.fullmatch(r"[a-z_][a-z0-9_-]*", target[key]):
            raise ValueError(f"Invalid target.{key}")
    for key in ("home", "checkout"):
        value = target[key]
        if not re.fullmatch(r"/[A-Za-z0-9_./-]+", value) or ".." in Path(value).parts:
            raise ValueError(f"target.{key} must be an absolute path without spaces or special characters")
    address = ipaddress.ip_address(web["bind"])
    if address.version != 4:
        raise ValueError("This deployment template currently supports IPv4 only")
    if web["mode"] not in ("lan", "internet"):
        raise ValueError("web.mode must be lan or internet")
    if web["mode"] == "internet" and not address.is_loopback:
        raise ValueError("Internet deployments must bind to loopback behind an authenticated HTTPS proxy")
    private = any(address in ipaddress.ip_network(network) for network in
                  ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "127.0.0.0/8"))
    if web["mode"] == "lan" and not private:
        raise ValueError("LAN deployments must bind to a private or loopback address, never 0.0.0.0")
    if type(web["port"]) is not int or not 1024 <= web["port"] <= 65535:
        raise ValueError("web.port must be an unprivileged port (1024-65535)")
    return config


def unit(config):
    target, web = config["target"], config["web"]
    return f"""[Unit]
Description=Accounting web application
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User={target['user']}
WorkingDirectory={target['checkout']}
Environment=HOME={target['home']}
Environment=PYTHONUNBUFFERED=1
ExecStart={target['checkout']}/.venv/bin/python -m uvicorn accounting.main:app --host {web['bind']} --port {web['port']} --workers 1 --no-proxy-headers
Restart=on-failure
RestartSec=5
UMask=0077
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full

[Install]
WantedBy=multi-user.target
"""


def deploy(config, tag):
    target = config["target"]
    account = pwd.getpwuid(os.getuid())
    if account.pw_name != target["user"] or account.pw_dir != target["home"]:
        raise ValueError("Run as the configured service user ON the destination server, not with sudo")
    checkout = Path(target["checkout"])
    if Path.cwd().resolve() != checkout.resolve():
        raise ValueError(f"Run from the configured checkout: {checkout}")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]*", tag):
        raise ValueError("Invalid release tag")
    if run("git", "status", "--porcelain", stdout=subprocess.PIPE).stdout.strip():
        raise ValueError("Checkout must be clean; ignore private configs before deploying")
    # Fetch and resolve the tag before interrupting the running service.
    run("git", "fetch", "origin", "--tags")
    commit = run("git", "rev-parse", "--verify", f"refs/tags/{tag}^{{commit}}", stdout=subprocess.PIPE).stdout.strip()
    previous = run("git", "rev-parse", "HEAD", stdout=subprocess.PIPE).stdout.strip()
    data = Path(target["home"]) / ".app_data/accounting"
    if not (data / "accounting.db").is_file():
        raise ValueError("Import and validate the existing database before first deployment")
    run("sudo", "-v")
    service = target["service"] + ".service"
    state = subprocess.run(
        ["systemctl", "show", service, "--property=LoadState", "--value"],
        text=True, capture_output=True, check=False,
    )
    loaded = state.stdout.strip()
    if loaded != "not-found" and state.returncode:
        raise RuntimeError(f"Could not inspect service: {state.stderr}")
    if not loaded:
        raise RuntimeError("systemd returned no service load state")
    if loaded != "not-found":
        run("sudo", "systemctl", "stop", service)
    # All other writers (MCP/scripts) must also be stopped by the operator.
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup = Path(target["home"]) / "accounting-backups" / stamp
    backup.mkdir(parents=True, mode=0o700)
    shutil.copytree(data, backup / "data")
    (backup / "revision.txt").write_text(previous + "\n")
    python = checkout / ".venv/bin/python"
    if python.exists():
        freeze = run(str(python), "-m", "pip", "freeze", stdout=subprocess.PIPE).stdout
        (backup / "dependencies.txt").write_text(freeze)
    print(f"Pre-deployment backup: {backup}", flush=True)
    run("git", "switch", "--detach", commit)
    if not python.exists():
        run("python3", "-m", "venv", str(checkout / ".venv"))
    run(str(python), "-m", "pip", "install", ".")
    run(str(python), "-m", "pip", "check")
    with tempfile.TemporaryDirectory() as temporary:
        generated = Path(temporary) / service
        generated.write_text(unit(config))
        run("sudo", "install", "-o", "root", "-g", "root", "-m", "600",
            str(generated), f"/etc/systemd/system/{service}")
    run("sudo", "systemctl", "daemon-reload")
    run("sudo", "systemctl", "enable", "--now", service)
    run("sudo", "systemctl", "status", service, "--no-pager")
    print("Service started. Verify HTTP, records, attachments, and persistence before accepting writes.")


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("render", help="Print systemd unit; does not change the system")
    get = sub.add_parser("get", help="Print a single config value for shell commands")
    get.add_argument("key", help="section.key")
    install = sub.add_parser("deploy", help="Deploy a fetched tag on the destination server")
    install.add_argument("--tag", required=True)
    install.add_argument("--apply", action="store_true", help="Required confirmation of service/data changes")
    args = parser.parse_args()
    config = load_config(args.config)
    if args.action == "render":
        print(unit(config), end="")
    elif args.action == "get":
        section, key = args.key.split(".", 1)
        print(config[section][key])
    elif not args.apply:
        parser.error("Review the runbook, stop other database writers, then pass --apply on the server")
    else:
        deploy(config, args.tag)


if __name__ == "__main__":
    main()
