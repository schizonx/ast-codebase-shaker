# Codebase Shaker — Testing Progress

> **Living document.** Updated every testing session. Source of truth for test results, validation history, bug tracking, and testing continuity.

---

## Project Information

| Field | Value |
|---|---|
| **Project Name** | Codebase Shaker |
| **Version** | 0.0.0 |
| **Status** | v0.0.0 — Released |
| **Start Date** | June 2026 |
| **Target Language** | Python 3.10+ |
| **License** | MIT |
| **Author** | Solo Developer |

---

## Testing Overview

**Test directory:** `testing/`
**Configuration:** `pyproject.toml` → `testpaths = ["testing"]`
**Framework:** pytest 9.0.3 + pytest-mock + Click CliRunner
**Execution:** `python -m pytest testing/` or `pytest` from project root

### Current Test Counts

| Category | Count | File Count |
|---|---|---|
| Unit Tests | 431 | 12 files |
| Integration Tests | 70 | 3 files |
| Real-Project E2E | 29 | 1 file |
| **Total Collected** | **530** | **16 files** |

### Test Files

**Unit (`testing/unit/`):**
| File | Tests | Coverage Target |
|---|---|---|
| `test_models.py` | 66 | 100% |
| `test_constants.py` | 34 | 100% |
| `test_config.py` | 43 | 90% |
| `test_tokens.py` | 12 | 80% |
| `test_discovery.py` | 37 | 90% |
| `test_parser.py` | 58 | 95% |
| `test_graph.py` | 44 | 90% |
| `test_resolver.py` | 52 | 90% |
| `test_pruner.py` | 48 | 95% |
| `test_serializer.py` | 27 | 90% |
| `test_clipboard.py` | 12 | 85% |
| `test_performance.py` | 4 | Benchmark |

**Integration (`testing/integration/`):**
| File | Tests | Purpose |
|---|---|---|
| `test_cli.py` | 20 | CLI invocation, argument parsing, error handling, version |
| `test_pipeline.py` | 13 | End-to-end pipeline (discovery → serialize → deliver) |
| `test_regression.py` | 26 | Regression tests (15 bug classes + 7 v1.1 feature tests + 4 more) |
| `test_real_projects.py` | 29 | Real-project e2e (Flask, FastAPI, werkzeug) |

---

## Current Testing Status

| Phase | Status | Tests | Notes |
|---|---|---|---|
| Unit — models & constants | ✅ Complete | 100 | All passing |
| Unit — config & tokens | ✅ Complete | 55 | All passing |
| Unit — discovery | ✅ Complete | 37 | All passing |
| Unit — parser | ✅ Complete | 58 | All passing |
| Unit — graph | ✅ Complete | 44 | All passing |
| Unit — resolver | ✅ Complete | 52 | All passing (incl. bounded traversal + direction) |
| Unit — pruner | ✅ Complete | 48 | All passing |
| Unit — serializer | ✅ Complete | 27 | All passing |
| Unit — clipboard | ✅ Complete | 12 | All passing |
| Unit — performance | ✅ Complete | 4 | All passing |
| Integration — CLI | ✅ Complete | 20 | All passing |
| Integration — pipeline | ✅ Complete | 13 | All passing |
| Integration — regression | ✅ Complete | 26 | All passing |
| Integration — real projects | ✅ Complete | 29 | All passing (Flask/FastAPI/werkzeug) |

**Overall: 530/530 passing, 0 failures**

---

## Testing Environment

| Component | Version | Notes |
|---|---|---|
| Python | 3.14.5 | Development platform |
| pytest | 9.0.3 | Test runner |
| OS | Windows 11 | Primary dev platform |
| Platform Matrix (CI) | ubuntu/windows/macos x 3.10–3.13 | Defined in `.github/workflows/ci.yml` |

---

## Test Assets

### Test Repositories

Real-project e2e tests use pip-installed packages resolved via `__import__`:

| Package | Used In | Notes |
|---|---|---|
| Flask | `TestFlaskFullPipeline`, `TestRealWorldFeatures` | 24+ .py files |
| FastAPI | `TestFastAPIFullPipeline` | 48+ .py files |
| werkzeug | `TestWerkzeugFullPipeline` | 52+ .py files |

### Fixtures

**`testing/fixtures/simple_app/`** (4 modules):
- `__init__.py` — package marker
- `main.py` — entry point with `process_order()`
- `auth.py` — login and authentication
- `db.py` — database models
- `utils.py` — utility functions

**`testing/fixtures/circular_imports/`** (2 modules):
- `a.py` — imports from `b.py`
- `b.py` — imports from `a.py`

---

## Test Results

### Unit Testing

| Module | Tests | Status | Notes |
|---|---|---|---|
| `models.py` | 66 | ✅ Pass | All data models validated |
| `constants.py` | 34 | ✅ Pass | BUILTIN_NAMES, STDLIB_MODULES, defaults |
| `config.py` | 43 | ✅ Pass | Load, validate, merge, error paths |
| `tokens.py` | 12 | ✅ Pass | tiktoken + fallback counting |
| `discovery.py` | 37 | ✅ Pass | Gitignore, exclude patterns, recursion |
| `parser.py` | 58 | ✅ Pass | All AST node types, error handling |
| `graph.py` | 44 | ✅ Pass | Symbol table, edges, cycles, builtins |
| `resolver.py` | 52 | ✅ Pass | BFS focus, suggestions, bounded traversal, direction |
| `pruner.py` | 48 | ✅ Pass | All 3 modes, roundtrip validity |
| `serializer.py` | 27 | ✅ Pass | Markdown structure, header, tree, sections |
| `clipboard.py` | 12 | ✅ Pass | Copy, file write, graceful degradation |
| `performance.py` | 4 | ✅ Pass | 100 files < 2s, 500 files < 5s, focus < 5s, signatures ≤ full |

**Unit total: 431 tests, all passing**

### Integration Testing

| Test Class | Tests | Status | Notes |
|---|---|---|---|
| `TestCliHelp` | 3 | ✅ Pass | --help, usage text, options listed |
| `TestCliVersion` | 2 | ✅ Pass | --version exits, contains "0.0.0" |
| `TestCliErrors` | 2 | ✅ Pass | Invalid path, invalid mode |
| `TestCliInvocation` | 13 | ✅ Pass | All modes, focus, output file, dry-run, pipe |
| `TestFullPipeline` | 13 | ✅ Pass | no-focus, with-focus, all modes, errors, stats |
| `TestRegression` | 26 | ✅ Pass | REG-001 through REG-015 + v1.1 features |
| `TestFlaskFullPipeline` | 9 | ✅ Pass | All passing (fixed focus names) |
| `TestFastAPIFullPipeline` | 9 | ✅ Pass | All passing (fixed focus names) |
| `TestWerkzeugFullPipeline` | 9 | ✅ Pass | All passing (fixed focus names) |
| `TestRealWorldFeatures` | 2 | ✅ Pass | list-symbols, no-tree |

**Integration total: 99 tests, all passing**

### Performance Results

| Metric | Before | After |
|---|---|---|
| FastAPI pipeline | HANGS (exponential cycle detection) | 1.99s |
| werkzeug pipeline | HANGS (exponential cycle detection) | 2.25s |
| Flask pipeline | 0.11s | 0.32s |

### Validation Testing

| Validation | Status | Method |
|---|---|---|
| Roundtrip validity (pruner) | ✅ Pass | Every pruned output verified with `ast.parse()` |
| Token counting accuracy | ✅ Pass | Verified against tiktoken when available |
| Focus resolution correctness | ✅ Pass | Multi-hop call graph traversal validated |
| Circular import handling | ✅ Pass | `testing/fixtures/circular_imports/` — no infinite loops |
| Syntax error recovery | ✅ Pass | Parse errors logged, processing continues |
| Cycle detection (large graphs) | ✅ Pass | SCC-based approach handles 1000+ node graphs |

---

## Bugs Found and Fixed

### Bug-001 — Flask Focus Qualified Name Mismatch ✅ Fixed

| Field | Value |
|---|---|
| **Severity** | Medium |
| **Status** | Fixed |
| **File** | `testing/integration/test_real_projects.py` |
| **Description** | Test used `--focus flask.app.Flask` but symbol resolves as `app.Flask`. |
| **Resolution** | Updated test to use correct qualified name. Tool behavior was correct. |

### Bug-002 — Cycle Detection Hang ✅ Fixed

| Field | Value |
|---|---|
| **Severity** | Critical |
| **Status** | Fixed |
| **File** | `src/shaker/engine/graph.py` |
| **Description** | `nx.simple_cycles()` enumerates ALL elementary cycles — exponential time. Hung on FastAPI (380 nodes) and werkzeug (1171 nodes). |
| **Resolution** | Replaced with bounded SCC-based approach: Tarjan's algorithm + cycle enumeration only within SCCs ≤10 nodes. |

### Bug-003 — Duplicate Symbol Warnings ✅ Fixed

| Field | Value |
|---|---|
| **Severity** | Low |
| **Status** | Fixed |
| **File** | `src/shaker/engine/graph.py` |
| **Description** | Real packages with `@property`/`@overload`/`@setter` decorators produce multiple AST nodes with the same qualified name, triggering spurious warnings. |
| **Resolution** | Changed from `warnings.warn()` to silent skip in `_build_symbol_table()`. |

---

## Outstanding Issues

| # | Issue | Severity | Status |
|---|---|---|---|
| — | None | — | All resolved |

---

## Lessons Learned

1. **Exponential algorithms kill on real data.** `nx.simple_cycles()` looks harmless but never completes on graphs with 300+ nodes. Always check algorithmic complexity before using graph library functions.

2. **Real-project tests catch what synthetic fixtures can't.** The cycle detection hang, Flask qualified name mismatch, and duplicate symbol warnings all only appeared with real packages.

3. **Python package re-exports confuse symbol paths.** `flask.Flask` in user's head ≠ `app.Flask` in the AST. The tool resolves correctly; test expectations must match reality.

4. **Decorators create duplicate AST nodes.** `@property`, `@overload`, `@setter` on the same function produce multiple `FunctionDef` nodes with the same qualified name. The symbol table must handle this.

---

## Next Session Instructions

When resuming work:

1. **Read this file first** — it is the testing memory.
2. **Build memory next** — `cbs-build-progress.md` for implementation state.
3. **Run tests with:** `python -m pytest testing/ -q` (full) or `python -m pytest testing/unit/ -q` (fast).

---

*This document is updated every testing session. It is the first file to read when resuming testing work.*
