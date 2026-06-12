# Codebase Shaker — Version 1.0 Implementation Framework

> **Coding Standards, Patterns, Conventions, and Architecture Rules**
> Created: 2026-06-12
> Source: Repository audit of v0.0.0 + v1.0 implementation
> Status: Active — Governs all v1.0 code

---

## 1. Purpose

This document defines the **implementation framework** for Codebase Shaker v1.0 — the coding standards, architectural patterns, and conventions that all code must follow. It ensures consistency across the codebase and provides a reference for current and future contributors.

Cross-reference with:
- `cbs-blueprint-1.0.md` — what to build
- `v1.0-build-progress.md` — what's been built
- `v1.0-testing-progress.md` — how it's tested

---

## 2. Project Layout

```
codebase-shaker/
├── src/shaker/                  # Main package (src layout)
│   ├── __init__.py              # Package version only
│   ├── __main__.py              # python -m shaker entry
│   ├── models.py                # Pure data models (foundation)
│   ├── constants.py             # Shared constants
│   ├── cli.py                   # Click entry point (composition root)
│   ├── engine/                  # Pipeline stages
│   │   ├── __init__.py
│   │   ├── discovery.py
│   │   ├── parser.py
│   │   ├── graph.py
│   │   ├── resolver.py
│   │   ├── pruner.py
│   │   ├── scoring.py           # v1.0
│   │   ├── security.py          # v1.0
│   │   └── remote.py            # v1.0
│   ├── infra/                   # Infrastructure
│   │   ├── __init__.py
│   │   ├── config.py
│   │   └── tokens.py
│   ├── output/                  # Serialization + delivery
│   │   ├── __init__.py
│   │   ├── serializer.py
│   │   ├── xml_serializer.py    # v1.0
│   │   ├── json_serializer.py   # v1.0
│   │   ├── plain_serializer.py  # v1.0
│   │   └── clipboard.py
│   └── mcp/                     # v1.0
│       └── server.py
├── testing/
│   ├── unit/                    # Per-module unit tests
│   ├── integration/             # End-to-end CLI tests
│   │   ├── test_cli.py
│   │   ├── test_pipeline.py
│   │   ├── test_regression.py
│   │   └── test_real_projects.py
│   └── fixtures/                # Test fixture projects
│       ├── simple_app/
│       └── circular_imports/
├── projmemprog/                 # Project memory
│   └── v1.0/
│       ├── V1_ROADMAP.md
│       ├── cbs-blueprint-1.0.md
│       ├── implementation-framework-1.0.md
│       ├── v1.0-build-progress.md
│       └── v1.0-testing-progress.md
├── pyproject.toml               # Build config, dependencies, tool config
├── README.md
├── CHANGELOG.md
├── CONTRIBUTING.md
└── LICENSE
```

---

## 3. Architecture Rules

### 3.1 Layered Dependency Rule

```
models.py  ←  (foundation — imports NOTHING from project)
constants.py  ←  (shared constants — imports nothing)
engine/*.py  ←  (pipeline stages — import from models, constants, infra)
infra/*.py  ←  (infrastructure — import from models, constants)
output/*.py  ←  (serializers — import from models, engine)
mcp/*.py  ←  (MCP server — import from models, engine, infra)
cli.py  ←  (composition root — imports from EVERYTHING)
```

**Rule:** `models.py` must never import from any other `shaker` module. `cli.py` is the only module that imports from all layers.

### 3.2 Stateless Pipeline Rule

Each pipeline stage is a **pure function** that takes inputs and returns outputs. No global state. No singletons. No mutable class state.

```python
# GOOD: stateless function
def build_graph(parsed: dict[Path, ParsedFile]) -> CallGraph:
    ...

# BAD: mutable class with state
class GraphBuilder:
    def __init__(self):
        self.graph = None  # mutable state
```

**Exception:** `cli.py::run_pipeline()` is the composition root and may hold local state for orchestration.

### 3.3 Error Handling Rule

- **Parse errors:** Catch, set `parse_error` field, continue pipeline
- **Focus not found:** Suggest similar symbols, exit gracefully
- **Security findings:** Redact or warn based on config, continue
- **Remote clone failures:** Clean up temp dir, raise with helpful message
- **Invalid config:** Show which field is invalid, suggest fix
- **AST unparse failures:** Fall back to original source with warning

### 3.4 Module Size Rule

- Single file: ≤ 400 lines preferred, ≤ 600 lines max
- If a module exceeds 600 lines, consider splitting by responsibility

Current sizes (post-v1.0):
- `cli.py`: ~900 lines (composition root — acceptable)
- `pruner.py`: ~340 lines
- `resolver.py`: ~200 lines
- Other modules: all under 200 lines

---

## 4. Coding Standards

### 4.1 Python Version

- **Target:** Python 3.10+
- **Syntax:** Use 3.10+ features (match/case, union types `X | Y`, `list[X]` instead of `List[X]`)
- **Avoid:** `from __future__ import annotations` (not needed in 3.10+)

### 4.2 Type Annotations

- **All functions** must have full type annotations (parameters + return type)
- **mypy `--strict`** must pass with zero errors
- Use `X | Y` syntax (not `Union[X, Y]`)
- Use `list[X]`, `dict[K, V]` (not `List[X]`, `Dict[K, V]`)
- Use `TYPE_CHECKING` guard for imports only needed for type hints

```python
from __future__ import annotations  # NOT needed in 3.10+

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from types import FrameType
```

### 4.3 Linting

- **ruff** with configuration in `pyproject.toml`
- Line length: 99 characters
- Rules: pycodestyle (E, W), pyflakes (F), isort (I)
- Run: `python -m ruff check src/ testing/`
- Fix: `python -m ruff check src/ testing/ --fix`

### 4.4 Docstrings

- **Public functions:** One-line docstring (Google style)
- **WHY, not WHAT:** Explain the reason, not the mechanism
- **No multi-line docstrings** unless the behavior is genuinely complex
- **No obvious docstrings:** `"""Parse file."""` is noise

```python
def parse_file(path: Path, name: str) -> ParsedFile:
    """Parse a Python file into symbols, imports, and call sites.

    Catches SyntaxError and sets parse_error field instead of raising,
    allowing the pipeline to continue past unparseable files.
    """
```

### 4.5 Comments

- **Default:** No comments. Code should be self-documenting.
- **Allowed:** Comments that explain non-obvious WHY (workarounds, edge cases, bug fixes)
- **Not allowed:** Comments that explain WHAT the code does
- **TODO/FIXME/HACK:** Not allowed in production code

### 4.6 Naming Conventions

- **Modules:** `snake_case.py`
- **Classes:** `PascalCase` (dataclasses, enums, exceptions)
- **Functions:** `snake_case`
- **Constants:** `UPPER_SNAKE_CASE`
- **Private:** `_leading_underscore`
- **CLI flags:** `--kebab-case` / `-single-letter`

### 4.7 Imports

- **Order:** stdlib → third-party → project (enforced by ruff isort)
- **Style:** `from X import Y` for project imports; `import X` for third-party
- **No wildcard imports:** `from X import *` is forbidden
- **No unused imports:** ruff F401 catches these

```python
# Good
import ast
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from shaker.models import CompressionMode, Config, ParsedFile

if TYPE_CHECKING:
    from types import FrameType
```

### 4.8 Data Models

- **All data classes:** Use `@dataclass`
- **Immutable data:** Use `@dataclass(frozen=True)`
- **No methods on data classes:** Data classes hold data only; behavior goes in engine modules
- **No inheritance between data classes:** Use composition instead
- **Enums:** Use `Enum` class, UPPER_SNAKE_CASE values

```python
@dataclass(frozen=True)
class SecurityFinding:
    """A potential secret or sensitive data found in source code."""
    file: Path
    line_number: int
    finding_type: str
    severity: str
    redacted: bool = False
```

### 4.9 Logging

- Use `logging.getLogger(__name__)` at module level
- Use appropriate levels: `debug`, `info`, `warning`, `error`
- Log important state transitions and errors
- Don't log sensitive data (secrets, tokens)

```python
logger = logging.getLogger(__name__)

def clone_remote(url: str) -> Path:
    logger.info("Cloning %s to %s", url, tmp_path)
    ...
    logger.info("Cleaned up remote clone at %s", tmp_path)
```

---

## 5. Testing Standards

### 5.1 Test Organization

```
testing/
├── unit/
│   ├── test_discovery.py
│   ├── test_parser.py
│   ├── test_graph.py
│   ├── test_resolver.py
│   ├── test_pruner.py
│   ├── test_pruner_budget.py     # v1.0
│   ├── test_security.py          # v1.0
│   ├── test_scoring.py           # v1.0
│   ├── test_remote.py            # v1.0
│   ├── test_serializer.py
│   ├── test_xml_serializer.py    # v1.0
│   ├── test_json_serializer.py   # v1.0
│   ├── test_plain_serializer.py  # v1.0
│   ├── test_config.py
│   ├── test_tokens.py
│   └── ...
├── integration/
│   ├── test_cli.py
│   ├── test_pipeline.py
│   ├── test_regression.py
│   └── test_real_projects.py
└── fixtures/
    ├── simple_app/
    └── circular_imports/
```

### 5.2 Test Naming

- Test files: `test_<module>.py`
- Test classes: `Test<ClassName>` (for grouping related tests)
- Test functions: `test_<behavior_under_test>`
- Descriptive names: `test_regression_circular_imports` not `test_circ`

### 5.3 Test Structure

```python
def test_<behavior>(<fixture>):
    """One-line docstring explaining what this tests."""
    # Arrange
    ...
    # Act
    ...
    # Assert
    ...
```

### 5.4 Test Fixtures

- Use pytest fixtures for common setup
- Use `tmp_path` for temporary files
- Use `monkeypatch` for env vars and CWD changes
- Use `CliRunner` from Click for CLI tests
- Use `unittest.mock.patch` for mocking

### 5.5 Test Coverage Goals

- **Unit tests:** All public functions, happy path + edge cases + error conditions
- **Integration tests:** End-to-end CLI behavior with real fixtures
- **Regression tests:** One test per known bug fix
- **Target:** 700+ tests total

### 5.6 Running Tests

```bash
python -m pytest testing/ -v              # All tests verbose
python -m pytest testing/ -q              # All tests quiet
python -m pytest testing/unit/            # Unit only
python -m pytest testing/integration/     # Integration only
python -m pytest testing/ -x              # Stop on first failure
python -m pytest testing/ -k "security"   # Filter by keyword
python -m pytest testing/ --no-cov        # Without coverage
```

---

## 6. Git Conventions

### 6.1 Commit Messages

```
<type>: <imperative summary>

<optional body explaining WHY>
```

**Types:**
- `feat:` — new feature
- `fix:` — bug fix
- `test:` — test addition or fix
- `docs:` — documentation
- `refactor:` — code restructuring
- `chore:` — maintenance

**Examples:**
```
feat: add security scanner for secret detection

Scans for AWS keys, GitHub tokens, private keys, API keys,
and .env-style values. Defaults to redaction with [REDACTED].
```

```
fix: handle trailing newline loss in redact_findings

str.splitlines() + join() was dropping trailing newlines.
Detect and preserve them.
```

### 6.2 Branching

- `main` — stable, release-ready
- Feature branches: `feat/<feature-name>` (optional, can commit to main for small project)

### 6.3 Authorship

- **Author:** Schizooo (schizonx)
- **No AI co-authors** in commits
- **No AI attribution** files
- **No Claude references** in git history

---

## 7. Release Process

### 7.1 Pre-Release Checklist

1. All tests pass: `python -m pytest testing/ -q`
2. mypy strict clean: `python -m mypy src/ --strict`
3. ruff clean: `python -m ruff check src/ testing/`
4. Package builds: `python -m build --wheel`
5. README updated
6. CHANGELOG updated
7. Version bumped in `pyproject.toml` and `src/shaker/__init__.py`
8. No TODO/FIXME/HACK in source
9. Git status clean

### 7.2 Versioning

- **Semantic Versioning:** MAJOR.MINOR.PATCH
- **Current:** 1.0.0
- **Version locations:**
  - `pyproject.toml` → `version = "1.0.0"`
  - `src/shaker/__init__.py` → `__version__ = "1.0.0"`

### 7.3 Changelog

- File: `CHANGELOG.md`
- Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
- Each release: `## [X.Y.Z] — YYYY-MM-DD`
- Sections: `Added`, `Changed`, `Fixed`, `Removed`

---

## 8. Performance Guidelines

- **Regex compilation:** Compile once at module level, not per-call
- **File I/O:** Use `Path.read_text()` / `Path.write_text()` for simple reads/writes
- **AST parsing:** One parse per file; reuse `ast_tree` from `ParsedFile`
- **Graph building:** Use `networkx` built-in algorithms (linear-time where possible)
- **Target:** 500 files < 3s on modern hardware

---

## 9. Security Guidelines

- **No secrets in code:** Use test fixtures with fake keys (e.g., `AKIAIOSFODNN7EXAMPLE`)
- **No secrets in git history:** Scan before committing
- **Subprocess:** Use `subprocess.run()` with `check=True` and `capture_output=True`
- **Temp directories:** Always clean up, even on error or interrupt
- **Signal handlers:** Restore default handlers after use

---

*End of Version 1.0 Implementation Framework*
*This document governs all v1.0 code. Update it when patterns change.*
