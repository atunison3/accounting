# Repeatable Ubuntu deployment

Commit this directory's tools, example config, and instructions. Keep each real
server's config private. Python 3.11+ and systemd are required (Ubuntu 24.04 is a
suitable baseline). No Docker is required. Run commands individually; stop on errors.

## Configuration and privacy

```bash
cp deploy/config.example.toml deploy/home.local.toml
chmod 600 deploy/home.local.toml
# Edit home.local.toml for your server, using your editor.
export CONFIG=deploy/home.local.toml
python3 deploy/manage.py --config "$CONFIG" render
git check-ignore "$CONFIG"
```

`deploy/*.local.toml`, `deploy/generated/`, and `.deploy-local/` are ignored.
The example contains placeholders only. Use another file such as
`deploy/cloud.local.toml` for another server. Do not force-add private configs.
Git ignore rules do not hide files from administrators or erase prior commits.
Use SSH keys/agent; do not put passwords or private keys in these files.
Generated units, deployment records, and database backups can contain private
information and should not be committed or attached to public issues.

The existing application stores the database, documents, and logs under the
service user's `<home>/.app_data/accounting`. Arbitrary data paths are not
supported by this workflow. Paths in the systemd template cannot contain spaces.

## 1. Test and release (development machine)

Choose an unused version; the version below is an example. Review changes and
resolve any upstream changes through your normal merge/PR workflow.

```bash
export RELEASE=v0.1.0
git fetch origin --tags
git switch -c release/0.1.0
.venv/bin/python -m unittest discover -s tests
git diff --check
git add .gitignore pyproject.toml deploy
git diff --cached --stat
git diff --cached
# Confirm NO private configs, personal paths, addresses, or datasets are staged.
git commit -m "Add configurable Ubuntu deployment"
git switch main
git merge --ff-only origin/main
git merge --no-ff release/0.1.0
git tag -a "$RELEASE" -m "Release $RELEASE"
git push origin main
git push origin "$RELEASE"
```

Never overwrite a release tag. If branch protection requires a PR, merge that
first and tag the resulting main commit. Release metadata is public to repository
readers; machine-specific deployment details remain outside Git.

## 2. Prepare the server

On the development machine:

```bash
export CONFIG=deploy/home.local.toml
TARGET=$(python3 deploy/manage.py --config "$CONFIG" get target.ssh)
ssh "$TARGET"
```

Verify the SSH fingerprint using a trusted source before accepting it. On Ubuntu:

```bash
sudo apt update
sudo apt install -y python3 python3-venv git rsync curl ufw
python3 --version
```

Create/use the non-root account specified by `target.user`; its actual home must
match `target.home`. The helper intentionally checks both. Clone the repository
as that user into `target.checkout` (substitute your repository URL and path):

```bash
git clone <repository-url> <configured-checkout>
cd <configured-checkout>
git fetch origin --tags
git switch --detach <release-tag>
```

For an existing clone, require a clean checkout before switching tags. Fetching
and selecting an exact tag is safer than pulling an unpinned branch. Do not use
the root `requirements.txt`: it references an old editable app revision. The
helper installs the selected checkout with `pip install .`.

Transfer only the chosen private config from the development machine, for example:

```bash
# This guide uses the same home.local.toml filename on both machines.
# Substitute the configured absolute checkout path below.
scp "$CONFIG" "$TARGET:<configured-checkout>/deploy/home.local.toml"
```

On Ubuntu, restrict it with `chmod 600 deploy/home.local.toml`. Verify
`git check-ignore deploy/home.local.toml` before proceeding. Do not copy a Mac
virtual environment to Linux.

## 3. Snapshot and transfer existing data (development machine)

Stop ALL local writers: web app, API, MCP server, scripts, and background services.
Keep them stopped until cutover. Check `lsof +D "$HOME/.app_data/accounting"`
and inspect your process/service managers. Do not blindly kill all Python processes.
Check available disk space on both machines. The following copies all documents
and logs and uses SQLite backup to include committed WAL contents:

```bash
export STAGE="$(mktemp -d "$HOME/accounting-transfer.XXXXXX")"
chmod 700 "$STAGE"
rsync -a --exclude='accounting.db' --exclude='accounting.db-wal' \
  --exclude='accounting.db-shm' "$HOME/.app_data/accounting/" "$STAGE/"
python3 - <<'PY'
import os
import sqlite3
from pathlib import Path
source = Path.home() / '.app_data/accounting/accounting.db'
with sqlite3.connect(source.as_uri() + '?mode=ro', uri=True) as src:
    with sqlite3.connect(Path(os.environ['STAGE']) / 'accounting.db') as dst:
        src.backup(dst)
        if dst.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
            raise RuntimeError('Database integrity check failed')
print('Retain this private backup:', os.environ['STAGE'])
PY
chmod -R go-rwx "$STAGE"
ssh "$TARGET" 'umask 077; mkdir "$HOME/accounting-import"'
rsync -a --progress "$STAGE/" "$TARGET:accounting-import/"
rsync -rcn --itemize-changes "$STAGE/" "$TARGET:accounting-import/"
```

If remote `mkdir` fails, stop and inspect the previous import; do not mix datasets.
The checksum comparison must succeed with no output. Keep the original Mac data
and snapshot intact. Do not copy a changing raw SQLite main file without its WAL.

## 4. Install data and validate document paths (Ubuntu)

Run as the configured service user. Stop any existing application service first.
Do not overwrite existing data: it might contain newer transactions.

```bash
umask 077
mkdir -p "$HOME/.app_data"
test ! -e "$HOME/.app_data/accounting" && \
  mv "$HOME/accounting-import" "$HOME/.app_data/accounting"
```

Continue only if the move succeeded. From the configured checkout:

```bash
chmod -R go-rwx "$HOME/.app_data/accounting"
export CONFIG=deploy/home.local.toml
OLD_ROOT=$(python3 deploy/manage.py --config "$CONFIG" get migration.old_documents)
python3 deploy/relocate_documents.py --old-root "$OLD_ROOT"
# Only after validation succeeds:
python3 deploy/relocate_documents.py --old-root "$OLD_ROOT" --apply
```

This validates all live attachments and database integrity, creates a backup,
and relocates absolute paths. Historical audit paths remain unchanged. Unexpected
paths and missing attachments abort migration. No application import occurs here;
startup may apply additional database migrations later.

## 5. Network security BEFORE startup

**The app has no authentication boundary.** Anyone who reaches it may read or
modify financial data. The deployment tool does not configure firewall, TLS, or
authentication and must not be mistaken for an internet-security setup.

### LAN profile

Set `web.mode = "lan"` and `web.bind` to the reserved private server IP (or
loopback if using an SSH tunnel). Confirm the actual trusted CIDR with
`ip -4 route`; do not guess the subnet from the address.

Inspect `sudo ufw status verbose`, preserve SSH and other required services,
and ensure console recovery is available. Then, using actual values:

```bash
sudo ufw allow OpenSSH
sudo ufw allow from <trusted-LAN-CIDR> to <bind-IP> port <configured-port> proto tcp
sudo ufw default deny incoming
sudo ufw enable
sudo ufw status verbose
```

If SSH uses a nonstandard port, allow that port instead. Remove any broad existing
allow rule for the application port. Test a second SSH session before closing the
first. Do not enable router port forwarding. LAN HTTP remains unencrypted; only
use it on a trusted network.

### Internet profile

Create a separate private config with `web.mode = "internet"` and
`web.bind = "127.0.0.1"`. The helper rejects non-loopback internet bindings.

Before exposing anything publicly:

- Configure DNS and a maintained reverse proxy (e.g. Caddy/nginx) with HTTPS.
- Put authentication/access control in front of **every** route, including API,
  static assets, downloads, and any documentation endpoints. Prefer a VPN or
  identity-aware access proxy; this application is not yet hardened for public use.
- Keep the backend port blocked in both UFW and the cloud provider firewall.
  Expose only the required HTTPS endpoint and restricted administration access.
- Review CSRF protection, upload limits, dependency/security updates, backups,
  and authorization needs before accepting production financial data.
- The generated unit disables forwarded-header trust. If proxy URL generation
  requires it, explicitly configure trust for only your local proxy, never `*`.
- Verify unauthorized requests cannot reach any application endpoint.

An SSH tunnel is a safer interim option; keep the backend loopback-only:
`ssh -L 8000:127.0.0.1:<configured-port> <SSH-target>`.
Do not change the binding to `0.0.0.0` to solve proxy problems.

## 6. Deploy the tagged release (Ubuntu, from configured checkout)

Stop any other database writers, including MCP processes. Review the generated
unit and deployment settings before applying:

```bash
export CONFIG=deploy/home.local.toml
python3 deploy/manage.py --config "$CONFIG" render
python3 deploy/manage.py --config "$CONFIG" deploy --tag <release-tag> --apply
```

The helper checks the account/home, checkout location, clean Git state, and tag;
fetches tags; stops the existing service; backs up the complete data directory
under `~/accounting-backups/<timestamp>/`; records the previous revision and
available dependency versions; checks out the exact tag; creates a venv if
needed; installs the package; installs the unit; and enables/starts systemd.
Backups are private. Dependencies are version ranges, not a lockfile: test each
release and retain dependency records. The helper does not auto-rollback.
If anything fails after stopping the service, inspect and recover before accepting
writes; don't assume the old app is still running. Initial data import is required
and is never repeated automatically on later deployments.

## 7. Verify and cut over

```bash
SERVICE=$(python3 deploy/manage.py --config "$CONFIG" get target.service)
BIND=$(python3 deploy/manage.py --config "$CONFIG" get web.bind)
PORT=$(python3 deploy/manage.py --config "$CONFIG" get web.port)
curl --fail "http://$BIND:$PORT/" >/dev/null
sudo journalctl -u "$SERVICE" -n 50 --no-pager
```

Check businesses, transaction totals, mileage, and several downloaded attachments.
Test an appropriate upload/record without polluting real accounting reports.
Restart the service and verify persistence; test boot startup in a maintenance
window. For internet mode verify the authenticated HTTPS endpoint separately.
Keep the Mac app/MCP writer stopped; do not maintain two writable ledger copies.

## Later releases, backups, and rollback

Repeat release creation and the server `deploy --tag ... --apply` command.
Do not repeat the initial data import. Copy private config changes separately.
The helper does not remove stale venv dependencies, so periodically test a fresh
venv and establish a pinned dependency policy for production use.

Keep periodic off-server, access-restricted/encrypted backups of the complete data
directory, taken with every writer stopped (or via a coordinated SQLite/files
snapshot). Same-disk pre-deployment backups are not disaster recovery.

If verification fails, stop all writers and preserve the failed data separately.
Restore the previous Git revision and dependencies plus the matching complete data
backup; do not merge directories. Code-only rollback can fail after schema changes.
Restore loses newer writes unless reconciled first. On first deployment, the
untouched development-machine data is a fallback only if the server accepted no
new writes. Test backup restoration before relying on it.
