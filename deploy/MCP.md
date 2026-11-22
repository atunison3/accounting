# Accounting MCP for Pi (Ubuntu home server)

This is a separate authenticated **Streamable HTTP** service at `/mcp`. It runs
on Ubuntu, beside the website, and reads/writes the same server-side SQLite ledger.
No local Mac database copy is used by the MCP client. Default MCP port: **8003**.
The website keeps its separately configured port.

## Tools

| Tool | Purpose |
| --- | --- |
| `list_businesses` | Discover business IDs |
| `list_accounts` | Discover account IDs for a business |
| `get_transaction` | Header, active lines, and current revision |
| `get_transactions_by_business_and_date_range` | Inclusive ISO dates, 1–100 transactions per page, `next_offset` |
| `create_transaction` | Post a balanced debit/credit transaction |
| `update_transaction` | Replace header and ALL lines using a current revision |
| `delete_transaction` | Soft-delete using a current revision and `confirm=true` |

Writes use the configured existing accounting user's ID for audit attribution.
Amounts are positive **integer cents**, not floating-point currency. Accounts must
be active and belong to the transaction's business. Balanced entries are required.
Updates cannot move a transaction to another business. Stale revisions fail rather
than overwriting a concurrent change from the website or another agent.

The bearer token grants **ledger-wide read/write access**, not per-business or
per-client authorization. Use only with trusted agents. Tool annotations and
instructions ask agents to obtain approval, but they are NOT a human-approval
security boundary. Configure your Pi permission gate if you require approval for
every write. A token holder can delete records (soft-delete); treat it like a password.

Creation is not idempotent. If a create call times out, inspect the ledger before
retrying to avoid duplicate transactions. All normal validation/write failures
roll back the database transaction; history and soft-deleted lines are retained.

The old date-range tool name remains but now returns a paginated object with
`transactions` and `next_offset`, rather than an unbounded list. Refresh client
schemas. The old unauthenticated stdio entry point is replaced with authenticated
HTTP startup; update old local client configurations accordingly.

## 1. Configure your private deployment file (Mac)

Add this section to `deploy/home.local.toml`, which is ignored by Git:

```toml
[mcp]
enabled = true
bind = "127.0.0.1"
port = 8003
user_id = 1
```

**Replace `user_id` with an actual active accounting user ID.** To discover IDs,
run this read-only query on Ubuntu (it does not create users or change data):

```bash
python3 -c 'import sqlite3,pathlib; p=pathlib.Path.home()/".app_data/accounting/accounting.db"; c=sqlite3.connect(p.as_uri()+"?mode=ro",uri=True); print(c.execute("SELECT id, username FROM users WHERE is_active=1 AND deleted_at IS NULL").fetchall()); c.close()'
```

Using a dedicated existing user makes MCP activity easier to identify. A token is
a shared identity; it cannot distinguish multiple agents using the same token.

Loopback is recommended: traffic from Pi travels over an encrypted SSH tunnel,
while the MCP process and database stay entirely on the home server. You do NOT
need a new inbound firewall rule with this setup.

For direct LAN access, set `bind` to the server's private IPv4 address instead.
Allow port 8003 only from trusted client IPs in the firewall. **Plain LAN HTTP
exposes bearer tokens and accounting data to network interception.** Prefer the
SSH tunnel, VPN, or an HTTPS proxy; never forward this port on your router.
Internet deployment mode requires loopback, with SSH or an authenticated HTTPS
proxy configured separately. No browser-origin requests are accepted.

## 2. Release and deploy (Mac)

Commit these implementation changes through your release workflow and create a
**new** tag containing them (for example `v0.2.0`, if unused). Existing `v0.1.0`
does not contain this implementation; do not overwrite it. Verify the tag includes
`accounting_server/server.py` and the packaging changes. Run tests before tagging.

The server already has your data, so use **update mode**, not first import:

```bash
python deploy/deploy_archive.py --config deploy/home.local.toml --tag v0.2.0 --mode update --writers-stopped --apply
```

Replace the tag with the release you actually created. Stop any independent
scripts/MCP writers first. The installer automatically stops the managed website
and existing MCP service before backing up server data, installs the new tagged
release, and configures/restarts both services. It never replaces server data with
your Mac database in update mode.

The optional MCP setup generates a random secret only on Ubuntu:

```text
~/.config/accounting/mcp.token
```

The file is owner-only, never committed, and reused on later updates. The service
unit contains its path, not the token. An authenticated MCP `initialize` request
checks startup. Failure leaves staging/backups for inspection; check the journal
rather than repeating imports. Keep the `[mcp]` section for later upgrades. Setting
`enabled=false` stops/disables the existing managed MCP service. Once MCP is
installed, an absent `[mcp]` section makes upgrades fail early rather than leave
an old database writer running during backup/migration.

The default service name is `accounting-mcp`. On Ubuntu:

```bash
sudo systemctl status accounting-mcp --no-pager
```

```bash
sudo journalctl -u accounting-mcp -n 50 --no-pager
```

The installer uses the new release's Python environment; no Git installation is
needed on Ubuntu. The package includes `accounting_server` and pins the compatible
MCP SDK major version (`mcp>=1.26,<2`); SDK 2 renamed FastMCP and is not compatible
with the previous adapter implementation.

## 3. Connect Pi securely (Mac)

Substitute your private `user@server` SSH target in the commands below. Do not
commit real addresses/tokens to the shared instructions.

Start a tunnel in a separate terminal and leave it open:

```bash
ssh -N -o ExitOnForwardFailure=yes -L 8003:127.0.0.1:8003 user@server
```

The remote service is loopback-only. Pi connects to `http://127.0.0.1:8003/mcp`,
but execution/data storage happen on Ubuntu. Reserve local port 8003 for the
tunnel; if you choose another local port, the server's allowed Host list must be
adjusted too (currently restricted to its configured port).

Copy the private token via SSH into a private directory on the Mac:

```bash
mkdir -p "$HOME/.config/accounting"
```

```bash
chmod 700 "$HOME/.config/accounting"
```

```bash
scp user@server:.config/accounting/mcp.token "$HOME/.config/accounting/mcp.token"
```

```bash
chmod 600 "$HOME/.config/accounting/mcp.token"
```

Set the environment variable **in the terminal that launches Pi**:

```bash
export ACCOUNTING_MCP_TOKEN="$(< "$HOME/.config/accounting/mcp.token")"
```

Merge this entry into the existing `mcpServers` object in
`~/.pi/agent/mcp.json` (do not replace unrelated servers):

```json
{
  "mcpServers": {
    "accounting-home": {
      "url": "http://127.0.0.1:8003/mcp",
      "headers": {
        "Authorization": "Bearer ${ACCOUNTING_MCP_TOKEN}"
      }
    }
  }
}
```

This URL/header format works with Pi's built-in MCP support and the installed
`pi-mcp-adapter`. Keep it in the user-global configuration, not a public project
file. The adapter can also use `~/.config/mcp/mcp.json`; don't create duplicate
entries in multiple locations.

For built-in Pi MCP, the equivalent CLI command is:

```bash
pi mcp add accounting-home --url http://127.0.0.1:8003/mcp --bearer-token-env-var ACCOUNTING_MCP_TOKEN
```

Launch Pi from the shell with the token exported. In Pi, use `/mcp` to inspect
or reconnect the server and `/reload` after file changes. A running Pi process
cannot inherit a newly exported variable from another shell; restart it when needed.
If `pi-mcp-adapter` replaces built-in MCP, its `/mcp` UI manages connections; the
shell `pi mcp` commands still operate on the built-in configuration.

Ask Pi to list businesses/accounts first, then read a transaction. Only test a
write after reviewing the exact accounts, amounts, currency, and date. Verify the
result in the website. The server declares mutation tools as destructive so Pi
permission extensions can gate them.

Example `create_transaction` tool arguments (replace IDs with discovered IDs):

```json
{
  "payload": {
    "business_id": 1,
    "transaction_date": "2026-11-22",
    "description": "Cash sale",
    "currency_code": "USD",
    "lines": [
      {"account_id": 1, "amount_cents": 1250, "is_debit": true},
      {"account_id": 2, "amount_cents": 1250, "is_debit": false}
    ]
  }
}
```

For update, supply `transaction_id`, the complete replacement `payload`, and
`expected_revision` from a fresh read. A stale revision must be resolved by reading
and reviewing the changes, not by forcing an overwrite.

## Operations and troubleshooting

- **401**: wrong/missing bearer token; export it before starting Pi.
- **421**: wrong Host header/port; use the configured IP or loopback and MCP port.
- **403**: browser-origin request rejected; use a native MCP client.
- **Missing/inactive audit user**: select an active existing user, then redeploy.
- **Connection refused**: check the SSH tunnel, service status, and journal.
- **Service starts but tool errors**: verify the app has migrated the existing
  database; MCP deliberately does not initialize/migrate an empty database.
- **Rotate token**: stop MCP, securely replace the owner-only token file with a new
  random secret, restart MCP, and replace the client copy. Never print tokens in
  chat/logs. All clients sharing the previous token lose access.
- **Rollback/backups**: stop BOTH services and all other writers first. Preserve
  both service units and the full data directory. Restore matching code/dependencies
  and data together; don't revert data after new writes without reconciliation.
- Protect the original website too: MCP authentication does not add authentication
  to the website's existing endpoints.
