# Development Setup

The repository is packaged with setuptools and uses the `accounting` package directory.

### macOS / Linux

```bash
git clone https://github.com/atunison3/accounting.git
cd accounting
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install -e .
```

### Windows

```powershell
git clone https://github.com/atunison3/accounting.git
cd accounting
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install -e .
```

The repository also contains pre-commit configuration. If pre-commit is available in the environment, install its hooks with:

```bash
pre-commit install
```

To preview this Docsify site, serve the `docs` directory with an HTTP server or a locally installed Docsify server. No Docsify package or project-specific documentation command is configured in this repository.
