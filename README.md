# Codebase Shaker

**Compress Python codebases for LLM context windows.**

Codebase Shaker understands code structure (not just text), traces the live call graph from a focal point, and compresses everything else to minimize token usage. The result is a Markdown document that fits more relevant code into a single LLM prompt.

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

## Usage

```
shaker [OPTIONS] [PATH]

Arguments:
  PATH                  Root path to analyze (default: current directory)

Options:
  --focus, -f           Focal symbol name (e.g., 'auth.login')
  --mode, -m            Compression mode: full, signatures (default), strip
  --output, -o          Output file path (default: stdout only)
  --no-clipboard        Skip clipboard copy
  --max-tokens INT      Token limit warning threshold
  --exclude PATTERN     Filename pattern to exclude (repeatable)
  --config PATH         Path to .shakerrc.json config file
  --verbose, -v         Verbose output
  --dry-run             Parse and analyze only, no output delivery
  --list-symbols        List all discovered symbols and exit
  --no-tree             Skip the file tree in Markdown output
  --depth N             Limit focus resolution to N hops (default: unlimited)
  --direction {both,callers,callees}
                        Focus traversal direction (default: both)
  --version             Show version
  --help                Show help
```

## How It Works

```
Input (path + args)
    → File Discovery     Walk directory, respect .gitignore
    → AST Parse          Extract symbols, imports, call sites
    → Call Graph Build   Directed graph of symbol dependencies
    → Focus Resolution   Bidirectional BFS from focal symbol
    → Prune/Compress     AST-based compression of non-focus files
    → Serialize          Markdown with file tree + code blocks
    → Deliver            Clipboard + stdout + optional file
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

Compress a project around a specific symbol:

```bash
shaker ~/projects/myapp --focus "auth.login" -o context.md
```

List all symbols in a project:

```bash
shaker /path/to/project --list-symbols
```

Limit how far the tool traces from the focal point:

```bash
shaker /path/to/project --focus "main.run" --depth 2
```

Trace only what calls a symbol, or only what it calls:

```bash
shaker /path/to/project --focus "auth.login" --direction callers
shaker /path/to/project --focus "auth.login" --direction callees
```

Exclude test files:

```bash
shaker . --exclude "*_test.py" --exclude "conftest.py" --focus "api.create_user"
```

Save to file instead of stdout:

```bash
shaker /path/to/project -o output.md
```

## Configuration

Create a `.shakerrc.json` in your project root:

```json
{
  "default_mode": "signatures",
  "exclude_patterns": ["*_test.py", "conftest.py"],
  "max_tokens": 8000,
  "always_include": ["src/models/", "src/core/"],
  "always_exclude": ["migrations/"]
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
│   └── pruner.py        # AST-based code compression (3 modes)
├── infra/               # Infrastructure
│   ├── config.py        # Config loading (.shakerrc.json) + validation
│   └── tokens.py        # Token counting (tiktoken + chars//4 fallback)
└── output/              # Serialization + delivery
    ├── serializer.py    # Markdown document construction
    └── clipboard.py     # Clipboard + file delivery
```

`models.py` is the foundation — it imports nothing from the project. `cli.py` is the only module that imports from everything.

## Dependencies

Required: `networkx`, `pathspec`, `click`, `rich`

Optional: `pyperclip` (clipboard support), `tiktoken` (accurate token counting)

## License

MIT
