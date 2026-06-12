# Codebase Shaker — Version 1.0 Blueprint

> **Definitive Technical Blueprint | Implementation Reference**
> Created: 2026-06-12
> Source: V1_ROADMAP.md (prompt.md) + previous session.txt + repository audit
> Status: Implementation Complete — Release Candidate

---

## 1. Purpose

This document is the **authoritative technical blueprint** for Codebase Shaker v1.0. It translates the strategic roadmap (V1_ROADMAP.md) into concrete implementation specifications that any developer can follow.

Cross-reference with:
- `V1_ROADMAP.md` — strategic context, market research, phased plan
- `implementation-framework-1.0.md` — coding standards, patterns, conventions
- `v1.0-build-progress.md` — what's built, what's remaining
- `v1.0-testing-progress.md` — test status, coverage, known issues

---

## 2. Scope

### 2.1 In Scope (v1.0)

**Core Features (from V1_ROADMAP.md Phases 1-3 + 4):**

| ID | Feature | Phase | Module(s) | Status |
|---|---|---|---|---|
| F1 | Multi-format output (XML/JSON/plain + markdown) | 1 | `output/xml_serializer.py`, `output/json_serializer.py`, `output/plain_serializer.py` | DONE |
| F2 | Security scanning (secret detection + redaction) | 2 | `engine/security.py` | DONE |
| F3 | Remote repository support | 2 | `engine/remote.py` | DONE |
| F4 | MCP server mode | 3 | `mcp/server.py` | DONE |
| F5 | `--quiet` flag | 1 | `cli.py` | DONE |
| F6 | Progress bar | 1 | `cli.py` | DONE |
| F7 | File importance scoring | 3 | `engine/scoring.py` | DONE |
| F8 | Context budget management | 3 | `engine/pruner.py` | DONE |
| F9 | Output statistics file (`--stats`) | 4 | `cli.py` | DONE |
| F10 | Per-file compression control | 4 | (deferred — config schema supports future extension) | DEFERRED |
| F11 | Git-aware output | 4 | (deferred — git metadata not in output) | DEFERRED |
| F12 | Circular import visualization | 4 | (deferred — not in output) | DEFERRED |
| F13 | Config presets (django/fastapi/flask) | 4 | `cli.py` | DONE |
| F14 | Multiple focus symbols | 4 | `cli.py`, `engine/resolver.py` | DONE |

**Additional Phase 1 deliverables:**
- `--init` flag — generates `.shakerrc.json` template
- Pipe-friendly auto-detection — suppress stats when stdout is not a terminal
- Call graph summary section in output
- Version bump to `1.0.0`
- README + CHANGELOG updates

### 2.2 Out of Scope (v2+)

- Multi-language support (Tree-sitter)
- LLM-powered semantic compression
- Watch mode / file system watcher
- Web UI
- VS Code extension
- Diff mode / incremental output
- Knowledge graph visualization
- Team/enterprise features (SSO, audit)
- Cloud/SaaS offering
- GitHub Gist integration
- XDG config directory support
- Model-specific token counting

---

## 3. Architecture

### 3.1 Pipeline Stages

```
Stage -1: Remote Resolution (optional)
    → Clone remote URL to temp dir via subprocess + tempfile
    → Register SIGINT/SIGTERM handlers for cleanup

Stage 0: Config
    → Load .shakerrc.json (per-project) or ~/.shakerrc.json (global)
    → Apply env-var overrides (SHAKER_MODE, SHAKER_MAX_TOKENS)
    → Apply CLI overrides

Stage 1: Discovery
    → Walk directory, respect .gitignore via pathspec
    → Apply always_exclude (priority) > always_include > exclude patterns

Stage 2: Parsing
    → AST parse each .py file
    → Extract: symbols (functions, classes, methods), imports, call sites
    → Handle syntax errors gracefully (set parse_error, continue)

Stage 3: Graph Building
    → Build networkx.DiGraph of symbol dependencies
    → Construct symbol table (qualified_name → Symbol)
    → Detect cycles

Stage 4: Focus Resolution
    → Bidirectional BFS from focal symbol(s)
    → Respect --depth and --direction flags
    → Multiple --focus flags supported

Stage 5: Pruning
    → AST-based compression of non-focus files
    → Three modes: full, signatures (default), strip
    → Budget-aware: if enforce_max_tokens, auto-select depth by ratio
    → Focus files always at full detail

Stage 5.5: Security Scanning
    → Regex-based secret detection (AWS, GitHub, private keys, API keys, .env)
    → Redact (default) or warn mode
    → Generate SecurityReport

Stage 5.6: File Scoring (optional, --score-files)
    → StaticScorer: importer count + graph centrality
    → GitScorer: adds git change history (graceful fallback)

Stage 6: Serialization
    → Output format: markdown (default), xml, json, plain
    → Include metadata, file tree, code blocks, stats
    → Include security report summary if findings exist

Stage 7: Delivery
    → Clipboard copy (pyperclip, graceful degradation)
    → File write (if -o specified)
    → Stdout (pipe-friendly: suppress stats if not a tty)

Stage 8: Remote Cleanup (if --remote used)
    → Remove temp directory
    → Restore default signal handlers
```

### 3.2 Module Inventory

```
src/shaker/
├── __init__.py              # version = "1.0.0"
├── __main__.py              # python -m shaker entry point
├── models.py                # Pure data models (foundation — imports nothing)
├── constants.py             # Shared constants, stdlib module list, SECRET_PATTERNS
├── cli.py                   # Click entry point (composition root)
├── engine/
│   ├── __init__.py          # Re-exports
│   ├── discovery.py         # File discovery + gitignore filtering
│   ├── parser.py            # AST parsing → symbols, imports, calls
│   ├── graph.py             # Symbol table + call graph construction
│   ├── resolver.py          # Focus resolution (BFS), fuzzy suggestions
│   ├── pruner.py            # AST-based code compression (3 modes) + budget
│   ├── scoring.py           # File importance scoring (StaticScorer, GitScorer)
│   ├── security.py          # Secret detection and redaction
│   └── remote.py            # Remote repo cloning + signal-based cleanup
├── infra/
│   ├── __init__.py
│   ├── config.py            # Config loading (.shakerrc.json) + validation
│   └── tokens.py            # Token counting (tiktoken + chars//4 fallback)
├── output/
│   ├── __init__.py          # Re-exports
│   ├── serializer.py        # Markdown document construction
│   ├── xml_serializer.py    # XML output with ElementTree
│   ├── json_serializer.py   # JSON output with metadata + files array
│   ├── plain_serializer.py  # Plain text output (no Markdown syntax)
│   └── clipboard.py         # Clipboard + file delivery
└── mcp/
    └── server.py            # MCP server mode (stdio transport)
```

### 3.3 Data Models

**Core (models.py):**
- `CompressionMode(Enum)` — FULL, SIGNATURES, STRIP
- `OutputFormat(Enum)` — MARKDOWN, XML, JSON, PLAIN
- `SymbolType(Enum)` — FUNCTION, CLASS, METHOD, MODULE, VARIABLE
- `Symbol(dataclass)` — name, qualified_name, symbol_type, file, line_number
- `Import(dataclass)` — module, names, is_from, alias, line_number
- `CallSite(dataclass)` — caller, callee, line_number
- `ParsedFile(dataclass)` — path, source, ast_tree, symbols, imports, call_sites, parse_error
- `CallGraph(dataclass)` — graph (DiGraph), symbol_table (dict[str, Symbol])
- `Config(dataclass)` — all config fields with defaults
- `BuildStats(dataclass)` — files_retained, files_total, input_tokens, output_tokens, etc.
- `OutputMetadata(dataclass)` — project_name, focus, mode, config_path, timestamp, version, stats
- `PipelineState(dataclass)` — config, discovered, parsed, call_graph, focus_files, pruned_files, security_report, file_scores
- `SecurityFinding(frozen dataclass)` — file, line_number, finding_type, severity, redacted
- `SecurityReport(dataclass)` — findings, total_scanned, total_findings, critical_count, redacted_count
- `FileScore(dataclass)` — file, score, importer_count, centrality, git_changes_30d, is_focus

**Config fields (v1 additions):**
- `output_format: OutputFormat = OutputFormat.MARKDOWN`
- `security_scan: bool = True`
- `security_redact: bool = True`
- `show_progress: bool = True`
- `quiet: bool = False`
- `enforce_max_tokens: bool = False`
- `use_git_scoring: bool = True`

### 3.4 Dependencies

**Required:**
```
networkx>=3.0
pathspec>=0.12.0
click>=8.0
rich>=13.0
```

**Optional:**
```
pyperclip                   # Clipboard support
tiktoken                    # Accurate token counting
mcp>=1.0                    # MCP server mode (pip install codebase-shaker[mcp])
```

---

## 4. Feature Specifications

### 4.1 F1: Multi-Format Output

**Files:** `output/xml_serializer.py`, `output/json_serializer.py`, `output/plain_serializer.py`

**Behavior:**
- `--format markdown` (default): existing Markdown serializer with YAML header, ASCII tree, code blocks
- `--format xml`: `<codebase-shaker>` root with `<metadata>`, `<files>`, `<omitted>` sections; CDATA for code
- `--format json`: `{metadata, files, omitted}` schema; parseable by `json.loads()`
- `--format plain`: no Markdown headers or code fences; minimal output for LLM context

**CLI:** `--format {markdown,xml,json,plain}` / `-F`

### 4.2 F2: Security Scanning

**File:** `engine/security.py`

**Patterns detected (constants.py::SECRET_PATTERNS):**
- `aws_key`: AWS Access Key (AKIA...)
- `github_token`: GitHub token (ghp_, gho_)
- `private_key`: RSA/EC/OpenSSH private keys
- `api_key`: Generic API keys (api_key, api_secret, password, token assignments)
- `env_secret`: .env-style values (SECRET=, PASSWORD=, TOKEN=, KEY=)

**Behavior:**
- Default: redact secrets with `[REDACTED]`
- `--security-warn`: log warning but don't modify output
- `--no-security-scan`: skip scanning entirely
- Security findings included in output summary section
- Security findings included in XML/JSON output

**CLI:** `--security-scan/--no-security-scan`, `--security-redact/--security-warn`

### 4.3 F3: Remote Repository Support

**File:** `engine/remote.py`

**Behavior:**
- `clone_remote(url)`: clone via `subprocess.run(["git", "clone", "--depth=1", url, tmp_dir])`
- Creates temp directory with prefix `shaker-remote-`
- Registers SIGINT/SIGTERM handlers for cleanup on interrupt
- `cleanup_remote(tmp_path)`: removes temp dir, restores default signal handlers
- `FileNotFoundError` caught and re-raised with helpful message
- `CalledProcessError` caught, temp dir cleaned up, re-raised

**CLI:** `--remote URL`

### 4.4 F4: MCP Server Mode

**File:** `mcp/server.py`

**Tools:**
- `shake`: compress a codebase (params: path, focus, mode, max_tokens)
- `list_symbols`: list all symbols (params: path)

**Transport:** stdio (reads JSON-RPC lines from stdin, writes to stdout)

**Dependencies:** optional `mcp` package (installed via `pip install codebase-shaker[mcp]`)

**CLI:** `--mcp`

### 4.5 F5: `--quiet` Flag

**Behavior:** Suppress all non-essential output (stats table, warnings). Only output the serialized content.

**CLI:** `--quiet` / `-q`

### 4.6 F6: Progress Bar

**Behavior:** Rich `Progress` widget showing file discovery, parsing, graph building progress. Shown by default; disabled with `--no-progress`.

### 4.7 F7: File Importance Scoring

**File:** `engine/scoring.py`

**Scorers:**
- `StaticScorer` (default): importer count (50%) + graph centrality (50%)
- `GitScorer` (opt-in): importer count (40%) + graph centrality (40%) + git changes (20%)

**Behavior:**
- `_count_git_changes()`: `subprocess.run(["git", "log", "--since=30 days ago", ...])` with 10s timeout
- Graceful degradation: returns empty dict on any failure
- `GitScorer` falls back to `StaticScorer` behavior when git unavailable

**CLI:** `--score-files`

### 4.8 F8: Context Budget Management

**File:** `engine/pruner.py` (modified `prune_files()`)

**Behavior:**
- `prune_files()` accepts `max_tokens` and `enforce_max_tokens` params
- `_resolve_effective_mode()`: ratio-based heuristic
  - `input_tokens / max_tokens > 2.0` → STRIP
  - `> 1.5` → SIGNATURES
  - `≤ 1.5` → user's chosen mode
- Focus files always at full detail regardless of budget
- Backward compatible: `enforce_max_tokens` defaults to False

**CLI:** `--max-tokens INT`, `--enforce-max-tokens`

### 4.9 F9: Output Statistics File

**Behavior:** Write build statistics to a JSON file alongside the output.

**CLI:** `--stats FILE`

### 4.10 F13: Config Presets

**File:** `cli.py` (`_apply_preset()`)

**Presets:**
- `django`: excludes migrations/, admin/, settings/, tests/, wsgi.py, asgi.py, manage.py
- `fastapi`: excludes tests/, alembic/, .env, .venv/
- `flask`: excludes tests/, migrations/, venv/, .venv/

**CLI:** `--preset FRAMEWORK`

### 4.11 F14: Multiple Focus Symbols

**Behavior:** `--focus` flag is `multiple=True`; all specified symbols resolved via BFS.

---

## 5. CLI Reference

```
shaker [OPTIONS] [PATH]

Arguments:
  PATH                    Root path to analyze (default: current directory)

Options:
  --focus, -f TEXT        Focal symbol name (repeatable)
  --mode, -m              Compression mode: full, signatures (default), strip
  --format, -F            Output format: markdown (default), xml, json, plain
  --output, -o            Output file path (default: stdout only)
  --no-clipboard          Skip clipboard copy
  --max-tokens INT        Token limit for budget enforcement
  --enforce-max-tokens    Auto-adjust compression depth to fit budget
  --exclude PATTERN       Filename pattern to exclude (repeatable)
  --config PATH           Path to .shakerrc.json config file
  --preset FRAMEWORK      Use framework preset: django, fastapi, flask
  --score-files           Display file importance scores
  --security-warn         Warn on secrets instead of redacting
  --no-security-scan      Disable secret scanning
  --remote URL            Clone and analyze a remote Git repository
  --stats FILE            Write build stats to a JSON file
  --init                  Generate a .shakerrc.json template
  --dry-run               Parse and analyze only, no output delivery
  --list-symbols          List all discovered symbols and exit
  --no-tree               Skip the file tree in Markdown output
  --depth N               Limit focus resolution to N hops (default: unlimited)
  --direction {both,callers,callees}
                          Focus traversal direction (default: both)
  --mcp                   Launch MCP server mode (stdio transport)
  --quiet, -q             Suppress non-essential output
  --no-progress           Disable progress bar
  --verbose, -v           Verbose output
  --version               Show version
  --help                  Show help
```

---

## 6. Configuration Reference

**Config file:** `.shakerrc.json` (per-project) or `~/.shakerrc.json` (global)

```json
{
  "mode": "signatures",
  "format": "markdown",
  "max_tokens": 8000,
  "enforce_max_tokens": false,
  "exclude": ["__pycache__/", "*.pyc", ".git/", "venv/", ".venv/"],
  "always_include": [],
  "always_exclude": [],
  "security_scan": true,
  "security_redact": true,
  "show_progress": true,
  "quiet": false,
  "use_git_scoring": true
}
```

**Precedence:** environment variables < config file < CLI flags

---

## 7. Test Plan

**Target:** 700+ tests (unit + integration + regression)

**Structure:**
- `testing/unit/` — per-module unit tests
- `testing/integration/` — end-to-end CLI tests
- `testing/fixtures/` — test fixture projects (simple_app, circular_imports)
- `testing/integration/test_regression.py` — regression tests (REG-001 through REG-015, v1.1, v1.2)

**Key test areas:**
- All 4 output formats produce valid output
- All 5 secret pattern categories detected
- Redaction replaces secrets with `[REDACTED]`
- Remote clone success/failure/cleanup
- MCP server tool listing and tool calls
- Budget auto-compression at different ratios
- File scoring works without git
- All CLI flags work individually and in combination

---

## 8. Release Checklist

- [x] All features implemented per blueprint
- [x] All data models defined in models.py
- [x] All CLI flags working
- [x] All config fields supported
- [x] README updated with all features
- [x] CHANGELOG for v1.0.0
- [x] mypy --strict clean
- [x] ruff lint clean
- [x] 697 tests passing
- [x] Package builds (`python -m build --wheel`)
- [x] Git history clean
- [x] No TODOs or placeholder code in source
- [x] Project memory files created (this set)

---

*End of Version 1.0 Blueprint*
*This document is the source of truth for Version 1 implementation.*
