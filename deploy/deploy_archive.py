"""One-command archive deployment from a Mac to Ubuntu, with no remote Git.

Default is preview. First deployment snapshots and imports local data; update
mode NEVER copies the local database over server data. Stop all other writers.
"""

import argparse
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import sqlite3
import subprocess
import tarfile
import tempfile

from manage import load_config, unit


def run(*args, **kwargs):
    return subprocess.run(args, check=True, text=True, **kwargs)


def snapshot(source, destination):
    if not (source / "accounting.db").is_file():
        raise ValueError(f"Database not found: {source / 'accounting.db'}")
    # Reject links instead of silently copying files outside the data directory.
    if source.is_symlink() or any(path.is_symlink() for path in source.rglob("*")):
        raise ValueError("Data directory contains symlinks; review them before transfer")
    shutil.copytree(source, destination, ignore=shutil.ignore_patterns(
        "accounting.db", "accounting.db-wal", "accounting.db-shm"))
    with closing(sqlite3.connect((source / "accounting.db").as_uri() + "?mode=ro", uri=True)) as src:
        with closing(sqlite3.connect(destination / "accounting.db")) as dst:
            src.backup(dst)
            if dst.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
                raise RuntimeError("Source database integrity check failed")
    for path in [destination, *destination.rglob("*")]:
        path.chmod(0o700 if path.is_dir() else 0o600)


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--mode", choices=("first", "update"), default="first")
    parser.add_argument("--data-dir", type=Path, default=Path.home() / ".app_data/accounting")
    parser.add_argument("--writers-stopped", action="store_true", help="Confirm local writers (first) and other server writers are stopped")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    config = load_config(args.config)
    target = config["target"]
    host = target["ssh"]
    if not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.@-]*", host):
        parser.error("Use an SSH alias or user@hostname; configure ports in ~/.ssh/config")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", args.tag):
        parser.error("Tag may contain letters, digits, dots, underscores, and hyphens only")
    tools = Path(__file__).resolve().parent
    repo = tools.parent
    commit = run("git", "-C", str(repo), "rev-parse", "--verify", f"refs/tags/{args.tag}^{{commit}}",
                 stdout=subprocess.PIPE).stdout.strip()
    target["checkout"] = f"{target['home']}/apps/accounting-{args.tag}"
    print(f"Mode: {args.mode}; release: {args.tag} ({commit})", flush=True)
    print(f"Target: {host}:{target['checkout']}", flush=True)
    print("Will back up data, install Python dependencies, configure systemd, and check HTTP.", flush=True)
    print("Firewall rules are NOT changed. LAN mode requires a trusted network; internet mode requires an authenticated HTTPS proxy.", flush=True)
    if not args.apply:
        print("Preview only. Stop writers, then add --writers-stopped --apply.")
        return
    if not args.writers_stopped:
        parser.error("Stop local writers for first import and all non-systemd server writers; confirm with --writers-stopped")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    retained = Path.home() / "accounting-deployment-backups" / stamp
    retained.mkdir(parents=True, mode=0o700)
    print(f"Private local deployment backup: {retained}", flush=True)
    run("git", "-C", str(repo), "archive", "--format=tar.gz",
        f"--output={retained / 'release.tar.gz'}", commit)
    old_documents = config.get("migration", {}).get("old_documents", str(args.data_dir.resolve() / "documents"))
    if args.mode == "first":
        snapshot(args.data_dir.resolve(), retained / "data")
        with tarfile.open(retained / "data.tar.gz", "w:gz") as tar:
            tar.add(retained / "data", arcname=".")
    for name in ("install_archive.py", "relocate_documents.py"):
        shutil.copyfile(tools / name, retained / name)
    (retained / "accounting.service").write_text(unit(config))
    filenames = ["release.tar.gz", "install_archive.py", "relocate_documents.py", "accounting.service"]
    if args.mode == "first":
        filenames.append("data.tar.gz")
    hashes = {}
    for name in filenames:
        with (retained / name).open("rb") as stream:
            hashes[name] = hashlib.file_digest(stream, "sha256").hexdigest()
    settings = {"config": config, "commit": commit, "mode": args.mode,
                "old_documents": old_documents, "hashes": hashes}
    (retained / "settings.json").write_text(json.dumps(settings, indent=2))
    # One authenticated SSH connection reused by scp and the interactive sudo session.
    with tempfile.TemporaryDirectory(prefix="acct-ssh-", dir="/tmp") as temporary:
        socket = str(Path(temporary) / "control")
        options = ["-o", f"ControlPath={socket}", "-o", "ControlMaster=auto", "-o", "ControlPersist=60"]
        try:
            run("ssh", *options, "-MNf", host)
            remote = run("ssh", *options, host, "umask 077; mktemp -d /tmp/accounting-deploy.XXXXXXXX",
                         stdout=subprocess.PIPE).stdout.strip()
            if not re.fullmatch(r"/tmp/accounting-deploy\.[A-Za-z0-9]+", remote):
                raise RuntimeError("Unexpected remote staging path")
            print(f"Private remote staging directory: {remote}", flush=True)
            run("scp", *options, *[str(retained / name) for name in filenames + ["settings.json"]], f"{host}:{remote}/")
            command = f"python3 {shlex.quote(remote + '/install_archive.py')} {shlex.quote(remote)}"
            # A TTY lets sudo prompt normally, without putting passwords into scripts.
            run("ssh", *options, "-t", host, command)
            cleanup = "rm -rf -- " + shlex.quote(remote)
            # Only this invocation's validated temporary directory, after success.
            run("ssh", *options, host, cleanup)
        finally:
            subprocess.run(["ssh", "-o", f"ControlPath={socket}", "-O", "exit", host],
                           check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("Deployment complete. Keep the old local app stopped and verify the server's records and attachments.")


if __name__ == "__main__":
    main()
