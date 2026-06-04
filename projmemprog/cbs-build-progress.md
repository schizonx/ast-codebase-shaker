# Codebase Shaker Development Tracker

> **Living document.** Updated every development session. Source of truth for project progress, architecture decisions, and session continuity.

---

## Project Information

| Field | Value |
|---|---|
| **Project Name** | Codebase Shaker |
| **Version** | 0.0.0 |
| **Status** | **v0.0.0 — Released** |
| **Start Date** | June 2026 |
| **Architecture Version** | IMPLEMENTATION_FRAMEWORK.md v0.0.0 |
| **Target Language** | Python 3.10+ |
| **License** | MIT |
| **Author** | Solo Developer |
| **GitHub** | https://github.com/schizonx/codebase-shaker.git |

---

## Project Goal

Codebase Shaker is a Python CLI tool that understands code **structure** (not just text), traces **only the live call graph** from a focal point, and compresses everything else to the minimum needed for an LLM to understand the broader system — without hallucinating the omitted parts.

**Core workflow:**
```
Input (path + args)
    → File Discovery
    → AST Parse (per file)
    → Call Graph Build
    → Focus Resolution
    → Prune/Compress
    → Serialize to Markdown
    → Token Count + Deliver (clipboard + stdout)
```

**Value proposition:** 70–85% token reduction per LLM prompt on targeted tasks, with higher output quality due to reduced attention dilution.

---

## Architecture Summary

### Pipeline Stages

| Stage | Module | Responsibility |
|---|---|---|
| 1 | `discovery.py` | Walk directory, filter by .gitignore |
| 2 | `parser.py` | AST parse → symbols, imports, calls |
| 3 | `graph.py` | Symbol table → networkx DiGraph |
| 4 | `resolver.py` | BFS from focal node → subgraph |
| 5 | `pruner.py` | AST transform per compression mode |
| 6 | `serializer.py` | Markdown document construction |
| 7 | `clipboard.py` | Delivery (clipboard + file) |

### Package Dependency Flow
```
constants.py ← models.py
     ↑              ↑
infra/           engine/         output/
     ↑              ↑              ↑
     └──────────────┴──────────────┘
                    ↑
                 cli.py
```

### Key Architectural Decisions

| Decision | Rationale |
|---|---|
| `PipelineState` dataclass | Carries mutable state through all pipeline stages. |
| `models.py` as foundation | All data structures in one place. Imports nothing from project. |
| `engine/` never imports `output/` or `infra/` | Clean data flow: engine → output. |
| `cli.py` as sole composition root | Only module that imports from everything. |
| `networkx` for graph ops | DiGraph, BFS/DFS, cycle detection out of box. |
| `tiktoken` optional | Large download. `chars // 4` fallback acceptable. |
| `pyperclip` optional | Fails on headless Linux. Never crash. |
| `ruff` as sole liner | Replaces flake8 + black + isort + pyupgrade. |
| Python 3.10+ minimum | 3.9 EOL October 2025. ast.unparse() stability. |

---

## Development Phases

### Phase 0 — Scaffolding ✅

- [x] `src/shaker/models.py`, `constants.py`, `__init__.py`, `__main__.py`
- [x] `pyproject.toml`, `conftest.py`, fixture projects
- [x] `.github/workflows/ci.yml`, `LICENSE`, `CONTRIBUTING.md`, `CHANGELOG.md`

### Phase 1 — Discovery + Config ✅

- [x] `discovery.py` (37 tests), `config.py` (43 tests)

### Phase 2 — Parser ✅

- [x] `parser.py` (58 tests)

### Phase 3 — Call Graph ✅

- [x] `graph.py` (44 tests), `resolver.py` (52 tests incl. bounded traversal + direction)

### Phase 4 — Pruner ✅

- [x] `pruner.py` (48 tests)

### Phase 5 — Output + Tokens ✅

- [x] `serializer.py` (27 tests), `clipboard.py` (12 tests), `tokens.py` (12 tests)

### Phase 6 — CLI + TUI ✅

- [x] `cli.py`, integration tests (20 CLI + 13 pipeline)

### Phase 7 — Hardening ✅

- [x] Real-project e2e tests (29 tests: Flask/FastAPI/werkzeug)
- [x] Performance benchmarks (4 tests)
- [x] Regression test suite (26 tests)
- [x] README, CHANGELOG, CONTRIBUTING complete
- [x] CI config, linting, type checking all green
- [x] Version 0.0.0 released and tagged

---

## Build Order

| Step | File | Purpose | Status |
|---|---|---|---|
| 1 | `src/shaker/models.py` | All shared data models (foundation) | ✅ Complete |
| 2 | `src/shaker/constants.py` | Shared constants | ✅ Complete |
| 3 | `src/shaker/infra/config.py` | Config loading (.shakerrc.json) | ✅ Complete |
| 4 | `src/shaker/infra/tokens.py` | Token counting | ✅ Complete |
| 5 | `src/shaker/engine/discovery.py` | File discovery + gitignore | ✅ Complete |
| 6 | `src/shaker/engine/parser.py` | AST parsing (most complex) | ✅ Complete |
| 7 | `src/shaker/engine/graph.py` | Call graph construction | ✅ Complete |
| 8 | `src/shaker/engine/resolver.py` | Focus resolution | ✅ Complete |
| 9 | `src/shaker/engine/pruner.py` | Code compression | ✅ Complete |
| 10 | `src/shaker/output/serializer.py` | Markdown serialization | ✅ Complete |
| 11 | `src/shaker/output/clipboard.py` | Clipboard + file output | ✅ Complete |
| 12 | `src/shaker/cli.py` | CLI entry point (composition root) | ✅ Complete |

---

## Session Log

### Session 2026-06-04 — Cycle Detection Fix + Real-Project Tests

**Critical Fix:** Replaced `nx.simple_cycles()` (exponential-time) with bounded SCC-based cycle detection in `graph.py`. Uses Tarjan's algorithm to find SCCs, only enumerates cycles within SCCs of ≤10 nodes, summarizes large SCCs instead. Fixed hang on FastAPI (380 nodes, 1900 edges) and werkzeug (1171 nodes, 3605 edges).

**Secondary Fix:** Duplicate symbol warnings (from `@property`, `@overload`, `@setter` decorators producing multiple AST nodes with the same qualified name) changed from `warnings.warn()` to silent skip.

**Test Fixes:** Fixed FastAPI/werkzeug focus names in `test_real_projects.py`. Updated `test_graph.py` duplicate name test.

**Result:** 530 tests passing (431 unit + 99 integration/regression/real-project). Real-project times: Flask 0.32s, FastAPI 1.99s, werkzeug 2.25s.

---

### Session 2026-06-04 — Regression Test Suite

**Files Created:** `testing/integration/test_regression.py` — 26 tests (REG-001 through REG-015 + 7 v1.1 feature tests + 4 more).

**Fixed:** Clipboard mock test to patch `_pyperclip` instead of `_HAS_CLIPBOARD`.

---

### Session 2026-06-04 — v1.1 Features

**New CLI Flags:** `--list-symbols`, `--no-tree`, `--depth N`, `--direction {both,callers,callees}`.

**New Env Vars:** `SHAKER_MODE`, `SHAKER_MAX_TOKENS`, `SHAKER_EXCLUDE`.

**Engine Changes:** `resolver.py` — `FocusDirection` class, `_bounded_traversal()`, direction-aware `resolve_focus()`. `serializer.py` — `include_tree` param.

**Version bumped to 1.1.0.**

---

### Session 2026-06-05 — v0.0.0 Release Polish

**Version Reconciliation:** Bumped version from `1.1.0`/`0.1.0` to `0.0.0` across `__init__.py`, `pyproject.toml`, `CHANGELOG.md`, and CLI test.

**File Cleanup:**
- Removed: `.coverage`, `codebase_shaker.egg-info/`, `thoughts/`, all `__pycache__/`, test artifacts, empty `docs/`, `testing/logs/`, `testing/reports/`
- Updated `.gitignore`: added `.coverage`, `htmlcov/`, `*.egg-info/`, `__pycache__/`, IDE files, OS files, proper `testing/outputs/*` pattern

**Documentation:**
- `README.md` — full rewrite: direct language, Quick Start section, all flags/env vars documented, corrected GitHub URLs
- `CONTRIBUTING.md` — corrected URLs and test commands, removed AI-sounding language
- `CHANGELOG.md` — restructured as 0.0.0 first public release

**CI Fix:** `.github/workflows/ci.yml` — `pytest tests/` → `pytest testing/`

**Verification:**
- 530/530 tests pass
- mypy --strict: 0 errors (17 source files)
- ruff: 0 issues
- `pip install -e .` works, installs as `codebase-shaker==0.0.0`
- `shaker --version` → `0.0.0`

**Git:** Committed, tagged `v0.0.0`, pushed to `https://github.com/schizonx/codebase-shaker.git`.

---

## Architecture Decisions Log

### ADR-001: models.py as Foundation
**Date:** Session 001
**Decision:** Implement `models.py` first. It imports NOTHING from the project.
**Consequences:** No circular imports possible through `models.py`.

### ADR-002: PipelineState Dataclass
**Date:** Session 001
**Decision:** Mutable dataclass flows through the pipeline. Each stage mutates it.
**Consequences:** Dramatically reduces boilerplate vs threading tuples through every function.

### ADR-003: Frozen Dataclasses for Value Objects
**Date:** Session 001
**Decision:** `@dataclass(frozen=True)` for `ImportInfo`, `CallSite`, `Symbol`. Mutable for accumulators.
**Consequences:** Immutable value objects are hashable and safe as dict keys.

### ADR-004: TYPE_CHECKING for networkx
**Date:** Session 001
**Decision:** `from __future__ import annotations` + `TYPE_CHECKING` guard for networkx import in `models.py`.
**Consequences:** `models.py` remains lightweight.

### ADR-005: No Database
**Date:** Blueprint
**Decision:** No SQLite, no database. Config lives in `.shakerrc.json`.

### ADR-006: Conservative Analysis
**Date:** Blueprint
**Decision:** When unsure, include more context rather than less.

### ADR-007: BUILTIN_NAMES via Runtime Introspection
**Date:** Session 002
**Decision:** `frozenset(dir(builtins))` at module load time. Zero maintenance.

### ADR-008: STDLIB_MODULES Hybrid Generation
**Date:** Session 002
**Decision:** Union curated hardcoded tuple with `sys.stdlib_module_names`.

### ADR-009: Bool Rejection for max_tokens
**Date:** Session 003
**Decision:** Explicit `isinstance(value, bool)` check before `isinstance(value, int)`.

### ADR-010: Unknown Config Fields → Warning Not Error
**Date:** Session 003
**Decision:** Unknown fields trigger `warnings.warn()`, not exception.

### ADR-011: Closest Ancestor Wins for Config Discovery
**Date:** Session 003
**Decision:** Walk from CWD upward, first `.shakerrc.json` wins.

### ADR-012: Bounded SCC-Based Cycle Detection
**Date:** Session 2026-06-04
**Decision:** Replace `nx.simple_cycles()` (exponential) with Tarjan's SCC + bounded enumeration (≤10 nodes per SCC).
**Consequences:** Fixes hang on large real-world packages. Large SCCs produce summary instead of enumerating all cycles.

### ADR-013: Silent Duplicate Symbol Skip
**Date:** Session 2026-06-04
**Decision:** `_build_symbol_table()` silently skips duplicate qualified names instead of warning.
**Consequences:** Real packages with `@property`/`@overload`/`@setter` decorators no longer produce noise.

---

## Current Status (2026-06-05)

| Metric | Value |
|---|---|
| Version | 0.0.0 |
| Tests | 530 passing (431 unit + 99 integration/regression/real-project) |
| mypy --strict | 0 errors, 17 source files |
| ruff | 0 issues |
| Git commits | 10 on master |
| Git tag | v0.0.0 |
| Remote | https://github.com/schizonx/codebase-shaker.git |
| Working tree | Clean |
| pip install | Verified working |

---

## Completion Status Dashboard

### Files Completed

| Category | Completed | Total | Percentage |
|---|---|---|---|
| Source Files | 17 | 17 | 100% |
| Test Files | 13 | 13 | 100% |
| Config Files | 1 | 1 | 100% |
| Fixture Projects | 2 | 2 | 100% |
| **Overall** | **33** | **33** | **100%** |

### Tests Completed

| Category | Completed | Target | Percentage |
|---|---|---|---|
| Unit Tests | 431 | 110+ | 392% |
| Integration Tests | 99 | 20+ | 495% |
| **Overall** | **530** | **130+** | **408%** |

### Phase Completion

| Phase | Description | Completion |
|---|---|---|
| Phase 0 | Scaffolding | 100% |
| Phase 1 | Discovery + Config | 100% |
| Phase 2 | Parser | 100% |
| Phase 3 | Call Graph | 100% |
| Phase 4 | Pruner | 100% |
| Phase 5 | Output + Tokens | 100% |
| Phase 6 | CLI + TUI | 100% |
| Phase 7 | Hardening | 100% |
| **Overall** | **Phases 0–7** | **100%** |

---

*This document is updated every development session. It is the first file to read when resuming work.*
