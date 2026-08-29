# Testing and Quality

The project uses Python's `unittest` discovery through the repository's pre-commit hook.

Run the test suite with:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

The configured quality tools are:

```bash
black accounting tests
ruff check accounting tests
mypy accounting tests
bandit -r accounting/ tests/
```

GitHub Actions runs Bandit and Ruff. The pre-commit configuration also runs Black, mypy, and the unittest suite.
