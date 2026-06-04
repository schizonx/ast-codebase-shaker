# Contributing to Codebase Shaker

## Development Setup

```bash
git clone https://github.com/schizonx/codebase-shaker.git
cd codebase-shaker
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -e ".[dev]"
```

## Running Tests

```bash
# All tests
python -m pytest testing/ -q

# Unit tests only
python -m pytest testing/unit/ -q

# Integration tests (local — skips slow real-project tests)
python -m pytest testing/integration/test_cli.py testing/integration/test_pipeline.py -q

# All tests including real-project e2e
python -m pytest testing/ -q

# With coverage
python -m pytest testing/ --cov=shaker --cov-report=term-missing
```

## Linting and Type Checking

```bash
ruff check src/ testing/
python -m mypy src/ --strict
```

## Project Structure

```
src/shaker/
├── __init__.py          # Package version
├── __main__.py          # python -m shaker entry point
├── models.py            # Pure data models (foundation)
├── constants.py         # Shared constants
├── cli.py               # Click entry point (composition root)
├── engine/              # Pipeline stages
│   ├── discovery.py     # File discovery + gitignore
│   ├── parser.py        # AST parsing + symbol extraction
│   ├── graph.py         # Call graph construction
│   ├── resolver.py      # Focus resolution
│   └── pruner.py        # AST-based compression
├── infra/               # Infrastructure
│   ├── config.py        # Config loading
│   └── tokens.py        # Token counting
└── output/              # Serialization + delivery
    ├── serializer.py    # Markdown builder
    └── clipboard.py     # Clipboard + file output
```

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Run tests and linting (`python -m pytest testing/ -q && ruff check src/ testing/ && mypy src/`)
4. Commit your changes
5. Push to the branch
6. Open a Pull Request

## Code Style

- Python 3.10+ type hints everywhere
- `ruff` for linting (configured in `pyproject.toml`)
- `mypy --strict` for type checking
- Docstrings for public functions
- No circular imports (enforced by architecture)
- `models.py` must not import from any other project module
