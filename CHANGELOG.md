# Changelog

All notable changes to Codebase Shaker will be documented in this file.

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
