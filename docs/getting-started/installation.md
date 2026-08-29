# Installation

## Requirements

The code uses `enum.StrEnum`, so Python 3.11 or newer is required. The package metadata does not declare a `requires-python` value or install-time dependencies, while the models import Pydantic and `EmailStr`. Install the repository requirements before using the package.

From a checkout, `requirements.txt` installs the pinned project environment, including Pydantic and email validation support.

### macOS / Linux

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install .
```

### Windows

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install .
```

## Verify the Installation

There is no configured console-script entry point. Verify the package by importing a model:

```bash
python -c "from accounting.domain.models import AccountType; print(AccountType.ASSET)"
```
