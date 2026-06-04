# Testing

This directory contains all testing materials for the Codebase Shaker project.

## Structure

```
testing/
+-- README.md              # This file
+-- conftest.py            # Shared pytest fixtures
+-- fixtures/              # Synthetic test codebases
|   +-- simple_app/        # 4-module fixture project
|   +-- circular_imports/  # Circular import edge case (2 modules)
+-- unit/                  # Unit tests (one per source module)
+-- integration/           # Integration and end-to-end tests
+-- outputs/               # Generated test output dumps (gitignored)
+-- reports/               # Test reports and benchmarks
+-- logs/                  # Test logs
```

## Running Tests

```bash
# All tests
pytest

# Unit tests only
pytest testing/unit/

# Integration tests only
pytest testing/integration/

# With coverage
pytest --cov=shaker --cov-report=term-missing
```

## Real-Project Tests

`test_real_projects.py` tests against installed pip packages (Flask, FastAPI,
werkzeug) resolved via `__import__`. They run only when those packages are installed
and are skipped gracefully when they are not. No manual cloning needed.
