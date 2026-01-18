# Coding Guidelines

## Style & Conventions
- **Language**: Python 3.12+
- **Type Hints**: Mandatory for all functions and methods.
- **Docstrings**: Required for modules, classes, and public methods.
- **Formatting**: Adhere to `ruff` or `black` (via `make format`).

## Pre-commit Hooks
The project uses pre-commit hooks to enforce quality:
- Linting (`make lint`)
- Formatting (`make format`)

Ensure these pass before pushing changes.
