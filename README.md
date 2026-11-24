# accounting

Functions for accounting from the book College Accounting by Jeffery Slater

## Local testing

See [Testing and Quality](docs/contributing/testing.md) for automated tests and
step-by-step browser testing of transaction deletion using a disposable database
on **http://127.0.0.1:8004/transactions**.

## Release process

Replace `vX.Y.Z` with the release version throughout these commands.

### Update main and generate the changelog

```shell
git checkout main
git fetch
git pull
python changelog.py
```

Update `docs/change-log.md` and the release version in `pyproject.toml`.
The project version uses `X.Y.Z`; the changelog heading uses `vX.Y.Z`.
Keep two newline characters between the heading and the first entry:

### Create and push the release branch

```shell
git checkout -b release/vX.Y.Z
git tag vX.Y.Z
git add .
git commit -m "Release vX.Y.Z"
git push origin release/vX.Y.Z
```

### Merge the release branch

Merge the release branch into main, then run:

```shell
git checkout main
git fetch
git pull
```

### Deploy

Run the deployment from this project directory on your development machine.
Use your ignored `deploy/home.local.toml` for the server address, paths, ports,
and MCP settings. Keep MCP enabled there if you want both services running.

Stop any independent scripts writing to the server database. The deployment
script stops the managed website and MCP services itself.

For an **already-deployed server**, run:

```shell
python deploy/deploy_archive.py --config deploy/home.local.toml --tag vX.Y.Z --mode update --writers-stopped --apply
```

This copies the tagged code, backs up the server's existing data, installs the
release, and restarts the website and enabled MCP service. **Update mode preserves
the server's ledger; it does not overwrite it with your local database.** SSH and
sudo may prompt for your server credentials. Firewall rules are not changed.

**Tag behavior in the sequence above:** the tag points to the commit before the
release commit, so the subsequent changelog/version edits are not included in the
deployed archive. The deployment script uses that local tag, not the latest main.
Also, pushing the release branch does not publish the tag to the remote repository.

On Ubuntu, verify the default services:

```shell
sudo systemctl status accounting accounting-mcp --no-pager
```

If MCP is disabled, check only `accounting`. If the service name was customized
in your private config, use that name instead.

Open the website using the address and port in your private config. Verify your
records, attachments, and the released changes. Reconnect Pi after the MCP service
restarts if necessary.

If deployment fails, keep the first error and the printed backup/staging paths.
Do not rerun in first-deployment mode or delete the server data.

See [Deployment guide](deploy/README.md) for first-time setup and rollback, and
[MCP setup](deploy/MCP.md) for Pi connections and SSH tunnels.

## License and attribution

This project's original code is available under the [MIT License](LICENSE).
You may use, modify, and redistribute it, including commercially. Keep the
copyright and license notice in copies or substantial portions of the software.
Credit to **Andy Tunison**, ideally with a link to this repository, is also
appreciated (but not required beyond the MIT notice requirement).
Third-party materials remain subject to their own licenses; this license does
not grant rights to the referenced textbook.

## Accounting and tax disclaimer

This software is provided **as is**, without warranties, as described in the
license. It is not professional accounting, tax, legal, or financial advice.
Calculations, reports, currency conversions, and tax-related information may be
incomplete, inaccurate, or outdated, and compliance with any jurisdiction's
requirements is not guaranteed.

You are responsible for independently verifying inputs, calculations, reports,
and filings before relying on them, maintaining backups, and consulting a
qualified accountant or tax adviser as appropriate. Do not rely on this
software alone to prepare or submit tax returns.

To the extent permitted by applicable law, the authors and copyright holders
disclaim liability for losses arising from use of the software, including
incorrect accounting records, tax underpayments, penalties, interest, missed
deadlines, and lost data. Nothing in this notice excludes liability that cannot
legally be excluded. This notice explains intended use and does not add
restrictions to the MIT License.
