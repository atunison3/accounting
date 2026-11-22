"""Internal Ubuntu-side installer, uploaded by deploy_archive.py. No Git needed."""

from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import pwd
import shutil
import sqlite3
import subprocess
import sys
import tarfile
import time
import urllib.request
from datetime import datetime, timezone


def run(*args, **kwargs):
    return subprocess.run(args, check=True, text=True, **kwargs)


def digest(path):
    with open(path, "rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def extract(archive, destination):
    """Only regular files/directories; reject traversal, links, and special files."""
    with tarfile.open(archive) as tar:
        members = tar.getmembers()
        for member in members:
            path = Path(member.name)
            if path.is_absolute() or ".." in path.parts or not (member.isdir() or member.isfile()):
                raise ValueError(f"Unsafe archive member: {member.name}")
        # Destination must be new, so existing symlinks cannot redirect extraction.
        destination.mkdir(parents=True, exist_ok=False, mode=0o700)
        tar.extractall(destination, members=members)


def main():
    os.umask(0o077)
    bundle = Path(sys.argv[1]).resolve()
    settings = json.loads((bundle / "settings.json").read_text())
    target, web = settings["config"]["target"], settings["config"]["web"]
    account = pwd.getpwuid(os.getuid())
    if account.pw_name != target["user"] or account.pw_dir != target["home"]:
        raise RuntimeError("SSH user/home does not match deployment config")
    if sys.version_info < (3, 11):
        raise RuntimeError("Ubuntu needs Python 3.11 or newer")
    for filename, expected in settings["hashes"].items():
        if digest(bundle / filename) != expected:
            raise RuntimeError(f"Transfer checksum failed: {filename}")
    home = Path(target["home"])
    data = home / ".app_data/accounting"
    release = Path(target["checkout"])
    first = settings["mode"] == "first"
    if first and data.exists():
        raise RuntimeError(f"Refusing to overwrite existing data: {data}. Inspect it before choosing update mode.")
    if not first and not (data / "accounting.db").is_file():
        raise RuntimeError("Update requires an existing server database")
    service = target["service"] + ".service"
    if first and subprocess.run(["systemctl", "is-active", "--quiet", service]).returncode == 0:
        raise RuntimeError("First deployment requires the existing service to be stopped")
    if release.exists():
        marker = release / "RELEASE_COMMIT"
        if not marker.is_file() or marker.read_text().strip() != settings["commit"]:
            raise RuntimeError("Existing release has no matching commit marker; refusing to overwrite")
        # Check all tracked files against the transferred archive before reusing it.
        with tarfile.open(bundle / "release.tar.gz") as tar:
            for member in tar.getmembers():
                if member.isfile():
                    path = release / member.name
                    if path.is_symlink() or not path.is_file():
                        raise RuntimeError(f"Existing release differs: {member.name}")
                    with tar.extractfile(member) as expected:
                        if digest(path) != hashlib.file_digest(expected, "sha256").hexdigest():
                            raise RuntimeError(f"Existing release differs: {member.name}")
        print(f"Reusing verified release: {release}", flush=True)
    else:
        extract(bundle / "release.tar.gz", release)
        (release / "RELEASE_COMMIT").write_text(settings["commit"] + "\n")
    # Avoid modifying a live environment when redeploying the same release.
    run("sudo", "-v")
    if not first:
        run("sudo", "systemctl", "stop", service)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup = home / "accounting-backups" / stamp
    backup.mkdir(parents=True, mode=0o700)
    old_unit = Path("/etc/systemd/system") / service
    if old_unit.exists():
        previous = run("sudo", "cat", str(old_unit), stdout=subprocess.PIPE).stdout
        (backup / "previous.service").write_text(previous)
    if not first:
        shutil.copytree(data, backup / "data")
    print(f"Backup directory: {backup}", flush=True)
    run("sudo", "apt-get", "update")
    run("sudo", "apt-get", "install", "-y", "python3-venv")
    python = release / ".venv/bin/python"
    if python.exists():
        frozen = run(str(python), "-m", "pip", "freeze", stdout=subprocess.PIPE).stdout
        (backup / "dependencies.txt").write_text(frozen)
    else:
        run("python3", "-m", "venv", str(release / ".venv"))
    run(str(python), "-m", "pip", "install", str(release))
    run(str(python), "-m", "pip", "check")
    if first:
        staged = bundle / "validated-data"
        extract(bundle / "data.tar.gz", staged)
        with closing(sqlite3.connect((staged / "accounting.db").as_uri() + "?mode=ro", uri=True)) as connection:
            if connection.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
                raise RuntimeError("Imported database failed integrity check")
        shutil.copytree(staged, backup / "data")
        data.parent.mkdir(parents=True, exist_ok=True)
        # No existing data is replaced; failures retain the imported data for recovery.
        shutil.copytree(staged, data)
        run(str(python), str(bundle / "relocate_documents.py"), "--data-dir", str(data),
            "--old-root", settings["old_documents"], "--apply")
    run("sudo", "install", "-o", "root", "-g", "root", "-m", "600",
        str(bundle / "accounting.service"), str(old_unit))
    run("sudo", "systemctl", "daemon-reload")
    run("sudo", "systemctl", "enable", "--now", service)
    url = f"http://{web['bind']}:{web['port']}/"
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    for attempt in range(30):
        try:
            with opener.open(url, timeout=3) as response:
                if response.status == 200:
                    break
        except (OSError, urllib.error.URLError):
            pass
        time.sleep(1)
    else:
        run("sudo", "systemctl", "stop", service)
        raise RuntimeError(f"HTTP health check failed; service stopped. Inspect journalctl -u {service}. Backup: {backup}")
    (backup / "deployed-commit.txt").write_text(settings["commit"] + "\n")
    print(f"Deployment healthy: {url}\nVerify records and attachments before accepting writes.", flush=True)


if __name__ == "__main__":
    main()
