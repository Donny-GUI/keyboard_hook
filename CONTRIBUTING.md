# Contributing

Thanks for your interest in contributing.

## Development setup

1. Fork and clone the repository.
2. Create and activate a virtual environment.
3. Install the project in editable mode.

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -e . pytest
```

## Running tests

```bash
python -m pytest -q
```

## Coding guidelines

- Keep changes focused and minimal.
- Preserve public API stability unless the change explicitly targets API evolution.
- Add or update tests for behavior changes.
- Keep callback paths non-blocking and avoid heavy work inside hook callbacks.

## Pull requests

1. Create a feature branch from the default branch.
2. Add tests for new behavior and run the test suite locally.
3. Update documentation when behavior, API, or workflow changes.
4. Open a PR with:
   - problem statement
   - implementation summary
   - test evidence

## Issues

When reporting bugs, include:
- Python version
- Windows version
- reproduction steps
- expected behavior and actual behavior
- relevant logs or tracebacks