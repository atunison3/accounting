# Installation

## Requirements

Python 3.11 or newer is required by the code. `pyproject.toml` declares runtime
dependencies, including FastAPI, Jinja2, Uvicorn, Pydantic/email validation,
ReportLab, and the MCP SDK. Installing the checkout installs those dependencies.
The metadata does not currently enforce a `requires-python` value.

For development tools and quality checks, see the
[contributor setup](../contributing/development-setup.md).

### macOS / Linux

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install .
```

### Windows

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install .
```

## Verify the Installation

Verify the package by importing a model:

```bash
python -c "from accounting.domain.models import AccountType; print(AccountType.ASSET)"
```

The website/API entry point is `accounting.main:app`; the standalone website is
`accounting.website.app:app`. The package also installs `accounting-mcp`, which
requires an existing server ledger and private authentication configuration.
See [Architecture](../documentation/architecture.md) for how they fit together.

To test the website from a checkout without modifying your normal ledger, follow
[local browser testing](../contributing/testing.md) using `python run_local.py`.
The test launcher requires an existing local database to copy.
