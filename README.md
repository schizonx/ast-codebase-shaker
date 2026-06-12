# Codebase Shaker

**Compress Python codebases for LLM context windows.**

Codebase Shaker understands code structure (not just text), traces the live call graph from a focal point, and compresses everything else to minimize token usage. The result is a structured document that fits more relevant code into a single LLM prompt.

## Quick Start

```bash
# 1. Install
pip install codebase-shaker

# 2. Point it at your project
shaker /path/to/project --focus "auth.login"

# 3. Output goes to clipboard and stdout. Paste into your LLM prompt.
```

That's it. The tool discovers all Python files, builds a call graph, identifies the code relevant to `auth.login`, keeps that code at full detail, and compresses everything else to function signatures.

## Installation

```bash
pip install codebase-shaker
```

Or from source:

```bash
git clone https://github.com/schizonx/codebase-shaker.git
cd codebase-shaker
pip install -e .
```

Requires Python 3.10+.

Optional extras:

```bash
pip install codebase-shaker[mcp]   # MCP server mode
```

## Usage

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
  --verbose, -v           Verbose output
  --version               Show version
  --help                  Show help
```

## How It Works

```
Input (path + args)
    → File Discovery      Walk directory, respect .gitignore
    → AST Parse           Extract symbols, imports, call sites
    → Call Graph Build    Directed graph of symbol dependencies
    → Focus Resolution    Bidirectional BFS from focal symbol(s)
    → Security Scan       Detect and redact secrets (optional)
    → File Scoring        Rank files by importance (optional)
    → Prune/Compress      AST-based compression of non-focus files
    → Serialize           Markdown / XML / JSON / Plain text
    → Deliver             Clipboard + stdout + optional file
```

When you provide `--focus "auth.login"`, the tool:

1. Finds the symbol in the call graph
2. Traces all callees (everything it calls)
3. Traces all callers (everything that calls it)
4. Keeps those files at full detail
5. Compresses everything else to function signatures

If the focus symbol isn't found, the tool suggests similar names.

## Compression Modes

| Mode | What it does | When to use |
|---|---|---|
| `signatures` (default) | Replaces function bodies with `...`; keeps signatures, decorators, type hints | Understanding API surface and call patterns |
| `strip` | Removes docstrings and comments; keeps all code | When you need full logic but not docs |
| `full` | Preserves everything unchanged | Debugging, or when you need the full source |

## Examples

### Focus on multiple symbols

```bash
shaker ~/projects/myapp --focus "auth.login" --focus "api.create_user"
```

### Use a framework preset

```bash
shaker ~/projects/myapp --preset django --focus "views.dashboard"
shaker ~/projects/api --preset fastapi --focus "routes.users"
shaker ~/projects/app --preset flask --focus "app.create_app"
```

### Auto-fit to a token budget

```bash
# Automatically increases compression if output exceeds 4000 tokens
shaker ~/projects/myapp --focus "auth.login" --max-tokens 4000 --enforce-max-tokens
```

### Clone and analyze a remote repo

```bash
shaker --remote https://github.com/user/repo --focus "main.run"
```

### Security scanning

```bash
# Default: secrets are redacted in output
shaker ~/projects/myapp --focus "config.load"

# Warn mode: secrets are flagged but not modified
shaker ~/projects/myapp --focus "config.load" --security-warn

# Disable scanning entirely
shaker ~/projects/myapp --focus "config.load" --no-security-scan
```

### Output formats

```bash
# Markdown (default)
shaker ~/projects/myapp --focus "auth.login" -o context.md

# JSON (machine-readable)
shaker ~/projects/myapp --focus "auth.login" --format json -o context.json

# XML
shaker ~/projects/myapp --focus "auth.login" --format xml -o context.xml

# Plain text (minimal, for LLM context)
shaker ~/projects/myapp --focus "auth.login" --format plain -o context.txt
```

### File importance scoring

```bash
shaker ~/projects/myapp --focus "auth.login" --score-files
```

### Generate a config template

```bash
shaker --init
# Creates .shakerrc.json in the current directory
```

### Write build stats

```bash
shaker ~/projects/myapp --focus "auth.login" --stats build-stats.json
```

## Security Scanning

Codebase Shaker scans for common secret patterns before including code in output:

| Pattern | Example |
|---|---|
| AWS Access Key | `AKIAIOSFODNN7EXAMPLE` |
| GitHub Token | `ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` |
| RSA Private Key | `-----BEGIN RSA PRIVATE KEY-----` |
| Generic API Key | `api_key = "..."` |
| .env-style values | `SECRET = "..."` |

By default, detected secrets are replaced with `[REDACTED]` in the output. Use `--security-warn` to log warnings without modifying output, or `--no-security-scan` to skip scanning entirely.

## File Importance Scoring

When `--score-files` is enabled, each file is scored by importance:

- **Static scoring** (always available): Based on how many other files import the file and its centrality in the call graph
- **Git scoring** (when git is available): Adds git change frequency from the last 30 days

Files are sorted by score in the output, helping you understand which files matter most.

## Context Budget Management

When `--enforce-max-tokens` is enabled with `--max-tokens`, the tool automatically adjusts compression depth for non-focus files:

| Budget ratio | Effective mode |
|---|---|
| > 2.0x | Strip (remove docstrings and comments) |
| > 1.5x | Signatures (keep only signatures) |
| ≤ 1.5x | User's chosen mode |

Files are never silently excluded — the budget is met by increasing compression, not by dropping files.

## MCP Server Mode

Launch Codebase Shaker as an MCP server for integration with AI coding assistants:

```bash
shaker --mcp
```

Requires: `pip install codebase-shaker[mcp]`

Two tools are available:

- **`shake`** — Compress a Python codebase for LLM context
  - Parameters: `path`, `focus` (optional), `mode` (optional), `max_tokens` (optional)
- **`list_symbols`** — List all discovered symbols in a codebase
  - Parameters: `path`

## Configuration

Create a `.shakerrc.json` in your project root (or `~/.shakerrc.json` for global defaults):

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

CLI arguments override config file values.

## Environment Variables

| Variable | Description | Example |
|---|---|---|
| `SHAKER_MODE` | Default compression mode | `SHAKER_MODE=strip` |
| `SHAKER_MAX_TOKENS` | Token limit warning threshold | `SHAKER_MAX_TOKENS=8000` |
| `SHAKER_EXCLUDE` | Comma-separated exclude patterns | `SHAKER_EXCLUDE="*_test.py,conftest.py"` |

Precedence (lowest to highest): environment variables < config file < CLI flags.

## Architecture

```
src/shaker/
├── __init__.py          # Package version
├── __main__.py          # python -m shaker entry point
├── models.py            # Pure data models (foundation — imports nothing)
├── constants.py         # Shared constants, stdlib module list
├── cli.py               # Click entry point (composition root)
├── engine/              # Pipeline stages
│   ├── discovery.py     # File discovery + gitignore filtering
│   ├── parser.py        # AST parsing → symbols, imports, calls
│   ├── graph.py         # Symbol table + call graph construction
│   ├── resolver.py      # Focus resolution (BFS), fuzzy suggestions
│   ├── pruner.py        # AST-based code compression (3 modes)
│   ├── security.py      # Secret detection and redaction
│   ├── scoring.py       # File importance scoring (static + git)
│   └── remote.py        # Remote repository cloning + cleanup
├── infra/               # Infrastructure
│   ├── config.py        # Config loading (.shakerrc.json) + validation
│   └── tokens.py        # Token counting (tiktoken + chars//4 fallback)
├── output/              # Serialization + delivery
│   ├── serializer.py    # Markdown document construction
│   ├── xml_serializer.py    # XML output
│   ├── json_serializer.py   # JSON output
│   ├── plain_serializer.py  # Plain text output
│   └── clipboard.py     # Clipboard + file delivery
└── mcp/                 # MCP server mode
    └── server.py        # stdio transport with shake + list_symbols tools
```

`models.py` is the foundation — it imports nothing from the project. `cli.py` is the only module that imports from everything.

## Dependencies

Required: `networkx`, `pathspec`, `click`, `rich`

Optional: `pyperclip` (clipboard support), `tiktoken` (accurate token counting), `mcp` (MCP server mode)

## Testing

```bash
python -m pytest testing/ -v        # All tests
python -m pytest testing/ -q        # Quiet mode
python -m pytest testing/unit/      # Unit tests only
python -m pytest testing/integration/ -k "not real_projects"  # Skip network tests
```

697 tests across unit, integration, and regression suites. mypy strict mode, ruff linting.

## License

MIT
