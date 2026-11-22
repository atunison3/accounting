"""Copy a tagged source release to Ubuntu without a server-side Git checkout.

Run on the development machine. No database transfer, package installation, or
service changes occur. Requires local git/scp/ssh and remote tar/mktemp.
"""

import argparse
from pathlib import Path
import re
import shlex
import subprocess
import tempfile

from manage import load_config


def run(*args, **kwargs):
    return subprocess.run(args, check=True, text=True, **kwargs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--apply", action="store_true", help="Actually copy files; otherwise preview only")
    args = parser.parse_args()
    config_path = args.config.resolve()
    config = load_config(config_path)
    target = config["target"]
    host = target["ssh"]
    if not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.@-]*", host):
        parser.error("target.ssh must be an SSH alias or user@hostname; configure custom ports in ~/.ssh/config")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", args.tag):
        parser.error("Tag must contain only letters, digits, dots, underscores, and hyphens")
    repository = Path(__file__).resolve().parent.parent
    ref = f"refs/tags/{args.tag}"
    commit = run("git", "-C", str(repository), "rev-parse", "--verify", f"{ref}^{{commit}}",
                 stdout=subprocess.PIPE).stdout.strip()
    destination = f"{target['home']}/apps/accounting-{args.tag}"
    print(f"Release: {args.tag} ({commit})")
    print(f"Destination: {host}:{destination}")
    print("Private config will be copied as deploy/target.local.toml with owner-only permissions.")
    print("No accounting data, virtual environments, or services will be changed.")
    if not args.apply:
        print("Preview only. Add --apply to transfer.")
        return
    quote = shlex.quote
    # Preflight before uploading. mkdir below also guards against concurrent copies.
    run("ssh", host, f"test ! -e {quote(destination)}")
    with tempfile.TemporaryDirectory(prefix="accounting-release-") as temporary:
        archive = Path(temporary) / "release.tar.gz"
        run("git", "-C", str(repository), "archive", "--format=tar.gz",
            f"--output={archive}", commit)
        remote_temp = run("ssh", host, "umask 077; mktemp -d /tmp/accounting-release.XXXXXXXX",
                          stdout=subprocess.PIPE).stdout.strip()
        if not re.fullmatch(r"/tmp/accounting-release\.[A-Za-z0-9]+", remote_temp):
            raise RuntimeError("Unexpected remote temporary path; refusing to upload")
        try:
            run("scp", str(archive), f"{host}:{remote_temp}/release.tar.gz")
            run("scp", str(config_path), f"{host}:{remote_temp}/target.local.toml")
            # No destructive cleanup of destination on failure: leave it for inspection.
            command = (
                f"set -eu; umask 077; mkdir -p {quote(target['home'] + '/apps')}; "
                f"mkdir {quote(destination)}; "
                f"tar -xzf {quote(remote_temp + '/release.tar.gz')} -C {quote(destination)}; "
                f"mkdir -p {quote(destination + '/deploy')}; "
                f"install -m 600 {quote(remote_temp + '/target.local.toml')} "
                f"{quote(destination + '/deploy/target.local.toml')}; "
                f"printf '%s\\n' {quote(commit)} > {quote(destination + '/RELEASE_COMMIT')}"
            )
            run("ssh", host, command)
        finally:
            # Only delete this invocation's validated temporary upload files.
            cleanup = (
                f"rm -f {quote(remote_temp + '/release.tar.gz')} "
                f"{quote(remote_temp + '/target.local.toml')}; rmdir {quote(remote_temp)}"
            )
            result = subprocess.run(["ssh", host, cleanup], check=False)
            if result.returncode:
                print(f"Warning: remote temporary files need manual cleanup: {remote_temp}")
    print(f"Copied successfully: {destination}")
    print("The app is NOT running yet. The Git-based manage.py deploy command cannot use this archive.")
    print("Before configuring systemd, set target.checkout in the copied config to the release directory.")
    print("Keep the database/documents outside the release directory; transfer them separately.")


if __name__ == "__main__":
    main()
