# Changelog

All notable changes to Codebase Shaker are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] — 2026-06-12

### Added

**Core Engine**
- **AST-based compression** with three modes: `full` (no compression), `signatures` (keep function/method signatures, replace bodies with `...`), `strip` (remove docstrings and comments); all modes guarantee valid Python output via roundtrip validation
- **Call graph analysis** using `networkx.DiGraph` for dependency tracking
- **Bidirectional focus resolution** — BFS from focal symbols to find all transitively related files
- **Security scanning** (`engine/security.py`) — regex-based secret detection for AWS keys, GitHub tokens, RSA private keys, API keys, and `.env` values, with `redact` (default) and `warn` modes
- **File importance scoring** (`engine/scoring.py`) — `StaticScorer` (importer count + graph centrality) and `GitScorer` (adds git change frequency, graceful fallback when git unavailable)
- **Remote repository support** (`engine/remote.py`) — clone any GitHub/GitLab repo via `--remote URL` with SIGINT/SIGTERM cleanup
- **Auto budget enforcement** — `--enforce-max-tokens` auto-selects compression depth based on token budget ratio (>2.0→strip, >1.5→signatures, ≤1.5→user mode); never drops files, only compresses harder

**CLI**
- Multiple `--focus` flags — `--focus auth.login --focus utils.hash`
- `--preset` flag — pre-configured exclude patterns for `django`, `fastapi`, `flask`
- `--score-files` — display file importance scores before output
- `--security-warn` — warn mode instead of redaction
- `--no-security-scan` — disable scanning entirely
- `--enforce-max-tokens` — auto-adjust compression depth
- `--init` — generate `.shakerrc.json` template
- `--stats` — write build stats to a JSON file
- `--verbose` / `-v` — enable debug logging
- All options via a single `click` CLI with env-var overrides (`SHAKER_MODE`, `SHAKER_MAX_TOKENS`)

**Output Formats**
- Markdown (default) — with `[FOCUS]` badges, file tree, and config summary
- XML — structured output with `<codebase-shaker>` root
- JSON — machine-readable with `{metadata, files}` schema
- Plain text — minimal output for LLM context

**Configuration**
- `.shakerrc` / `.shakerrc.json` per-project config files
- `~/.shakerrc.json` global user config
- Config supports: `mode`, `format`, `max_tokens`, `focus`, `direction`, `depth`, `always_include`, `always_exclude`, `exclude`, `show_stats`, `no_tree`, `verbosity`, `preset`, `enforce_max_tokens`

**MCP Server**
- `shaker --mcp` launches an MCP server via stdio transport
- Two tools: `shake` (compress a codebase) and `list_symbols` (list all symbols)
- Requires optional `pip install codebase-shaker[mcp]`

**Testing**
- 106+ total tests across unit, integration, and regression suites
- Regression tests cover 15 known bugs (REG-001 through REG-015)
- New feature tests for all Phase 2-4 additions (security, remote, scoring, presets, budget, multiple focus)
- Real-project e2e tests validate against Flask, FastAPI, and werkzeug codebases

**Linting & Type Safety**
- mypy strict mode with zero errors
- ruff linting (pycodestyle + pyflakes), 99-char line length
- 3.10+ type annotations throughout

## [0.0.0] — 2026-06-05

Initial beta release.

### Features

- **7-stage pipeline** — File discovery, AST parsing, call graph construction, focus resolution, code compression, Markdown serialization, clipboard/file delivery
- **AST-based compression** — Three modes: `full` (preserve everything), `signatures` (bodies replaced with `...`), `strip` (remove docstrings and comments)
- **Focus resolution** — Bidirectional BFS from a focal symbol, with `--depth` for bounded traversal and `--direction` for callers-only or callees-only
- **Fuzzy symbol suggestions** — When the focus symbol isn't found, similar names are suggested
- **`.gitignore` support** — File discovery respects `.gitignore` patterns
- **`.shakerrc.json` config** — Per-project defaults with CLI override
- **Environment variables** — `SHAKER_MODE`, `SHAKER_MAX_TOKENS`, `SHAKER_EXCLUDE`
- **`--list-symbols`** — List all discovered symbols in a Rich table
- **`--no-tree`** — Skip file tree in Markdown output
- **Token counting** — tiktoken integration with `chars // 4` fallback
- **Clipboard delivery** — Auto-copy output to clipboard (with graceful degradation)
- **Rich terminal output** — Stats table with before/after metrics

### Performance

- Cycle detection uses bounded SCC-based approach (linear-time Tarjan's algorithm + bounded enumeration within small components)
- Verified on real-world packages: Flask 0.32s, FastAPI 1.99s, werkzeug 2.25s

### Test Suite

- 530 tests: 431 unit + 99 integration/regression/real-project e2e
- Real-project tests validate against Flask, FastAPI, and werkzeug codebases
- mypy --strict: 0 errors across 17 source files

[1.0.0]: https://github.com/VOID/codebase-shaker/releases/tag/v1.0.0
