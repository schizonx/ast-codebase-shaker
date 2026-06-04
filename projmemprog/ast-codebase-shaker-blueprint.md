# AST Codebase Shaker — v1.0 Blueprint
> **Optimized & Production-Ready Edition**
> Solo developer | Target: 30–45 days | Python CLI tool

---

## 1. The Real Problem (Sharpened)

Gemini's framing is accurate but undersells the depth. The actual pain has three layers:

**Layer 1 — Token waste is money.** Feeding a 50-file Django backend to Claude or GPT-4o when you're only fixing one controller means you're paying for ~18,000 tokens of irrelevant context on every prompt. At scale, that's $20–100/day in API bills.

**Layer 2 — Attention dilution kills quality.** Even when tokens are cheap, LLMs lose precision when context is noisy. A model asked to refactor `user_auth.py` surrounded by 49 unrelated files produces worse output than one given only the three files that actually matter, with signatures from the rest. This is the "needle in a haystack" failure mode, now well-documented in research.

**Layer 3 — Manual selection doesn't scale.** Developers today copy-paste files manually, use `cat` with grep pipelines, or rely on tools like `repomix` that do naive full-text concatenation with no structural awareness. None of these can answer: *"Give me just the execution path touched by this function call."*

**The gap being filled:** A tool that understands code *structure* (not just text), traces *only the live call graph* from a focal point, and compresses everything else to the minimum needed for the LLM to understand the broader system — without hallucinating the omitted parts.

---

## 2. Target Users (Refined)

| Segment | Core Pain | How Shaker Solves It |
|---|---|---|
| **AI-first engineers** (Claude Code, Cursor, Copilot users) | Burning tokens on giant context pastes before every prompt | One command trims context to the relevant call graph |
| **Solo founders / indie hackers** | API bill anxiety; GPT-4o is expensive at volume | 70–85% token reduction per prompt on targeted tasks |
| **Technical PMs / code reviewers** | Need to understand a change without reading 3,000 lines | Shaker exports a structural skeleton: classes, signatures, no bodies |
| **New team members** | Onboarding to an unfamiliar codebase | Pass any module; get a compressed map of what connects to what |

---

## 3. User Stories (Expanded & Concrete)

### Primary

- **The Debugging Sprint** — *As a backend engineer, I'm debugging a failing `process_payment()` call. I want to run `shaker ./src --focus process_payment --mode signatures` and get a single Markdown file containing the full call graph of that function — its callers, its callees, the models it touches — so the LLM can reason about the bug without seeing the entire repo.*

- **The Safe Refactor** — *As a maintainer, I want to refactor `UserSessionManager` but I'm scared the LLM will also rewrite things I didn't ask about. I run `shaker ./src --focus UserSessionManager --mode strip` and give Claude a context that includes the class body but reduces everything outside it to one-line stubs, making the LLM's blast radius predictable.*

- **The Architecture Snapshot** — *As a developer onboarding to a new repo, I want `shaker ./src --mode signatures --no-focus` to give me a compressed structural map of the entire codebase — all classes, all method signatures, no implementations — so I can understand the shape of the system in a single LLM prompt.*

### Secondary

- **The PR Review** — *As a reviewer, I want `shaker ./src --focus changed_module --mode strip` to produce just the context needed to review a PR intelligently without reading every transitive dependency.*

- **The CI Failure** — *When my pipeline fails, I want Shaker to automatically package the failing function's call graph so the LLM debugging assistant gets exactly the right context with zero manual work.*

---

## 4. MVP Features (v1.0 Scope — No Bloat)

### Core Engine (Must-have)
| Feature | Description | Why It's in v1 |
|---|---|---|
| **AST-based call graph tracing** | Given `--focus func_or_class`, walks the Python AST to build an explicit dependency tree across files | This is the whole product |
| **Three compression tiers** | `full` (keep as-is), `signatures` (class/def headers only, no bodies), `strip` (docstrings/comments removed, bodies kept) | Covers the three real LLM use cases |
| **gitignore-aware file discovery** | Scans directory, skips `.git`, `__pycache__`, `node_modules`, paths in `.gitignore` | Required for any real-world repo |
| **Token count display** | Shows before/after token count (via `tiktoken`) in the terminal before outputting | Core value prop — must be visible |
| **Markdown output** | Emits a structured ```` ```python ```` block per file, with a folder tree header, ready to paste into any LLM chat | The actual deliverable |
| **Clipboard copy** | Copies output automatically (`pyperclip`) | UX must-have — saves the one extra step |
| **`.shakerrc.json` config** | Per-project config for default mode, excludes, max tokens | Lets teams standardize usage |

### What Is Explicitly Out of v1
- No web UI, no Streamlit (stretch goal only)
- No multi-language support (JavaScript/TypeScript via tree-sitter is v2)
- No VS Code extension (v2)
- No cloud/SaaS features
- No database (stateless always)
- No interactive graph visualization

---

## 5. System Architecture

### Philosophy: Stateless Pipe

```
Input (path + args)
    → File Discovery
    → AST Parse (per file)
    → Call Graph Build
    → Focus Resolution (if --focus given)
    → Prune/Compress
    → Serialize to Markdown
    → Token Count
    → Clipboard + stdout
```

Every stage is a pure function. No shared mutable state. Files are never modified. The tool is safe to run on production codebases.

### Data Flow Detail

**Stage 1 — File Discovery**
Walks the target directory using `pathlib`. Respects `.gitignore` rules (via `pathspec`). Collects all `.py` files. Filters by `--exclude` patterns. Returns `List[Path]`.

**Stage 2 — AST Parsing (per file)**
Runs Python's built-in `ast.parse()` on each file. Extracts:
- All `Import` and `ImportFrom` nodes (for cross-file resolution)
- All `ClassDef` nodes with their method `FunctionDef` children
- All module-level `FunctionDef` nodes
- All `Call` nodes within each function body (for call graph edges)

Stores as `ParsedFile` dataclass. Files that fail to parse (syntax errors, encoding issues) are flagged but don't crash the run.

**Stage 3 — Call Graph Construction**
Builds an internal symbol table: `{qualified_name → ParsedFile + AST node}`. Then for each function body, resolves `Call` nodes against the symbol table to produce directed edges: `caller → [callee, ...]`. Uses `networkx.DiGraph` for traversal.

**Stage 4 — Focus Resolution**
If `--focus` is provided, performs a BFS/DFS from the focal node, collecting all reachable nodes in both directions (callers and callees). The "focus set" = this subgraph. Everything outside the focus set gets the compression tier applied.

If no `--focus`, all files are treated as equal and the global `--mode` applies uniformly.

**Stage 5 — Pruning**
Applies the active `--mode` to each file:
- `full`: node unchanged
- `signatures`: `ast.NodeTransformer` that replaces every `FunctionDef` body with a single `...` ellipsis, preserving decorators and type annotations
- `strip`: `ast.NodeTransformer` that removes docstrings (first-child `Expr` with `Constant` value) and comments (strip `#` lines from source)

Files with zero relevant symbols after pruning are fully omitted. Their names appear in a `# [omitted]` section of the output.

**Stage 6 — Serialization**
Emits a single Markdown document:

```
# Codebase Context — [project_name]
> Generated by Codebase Shaker v1.0 | Focus: login_user | Mode: signatures
> Files: 6 retained / 14 total | Lines: 412 / 2,450 | Est. tokens: ~2,940

## File Tree
...

## src/auth/login.py
```python
[pruned source]
```

## src/models/user.py [signatures only]
...
```

**Stage 7 — Token Count & Output**
Runs `tiktoken` on the final string. Prints the summary table (rich). Copies to clipboard. Optionally writes to `--output` file.

---

## 6. Technical Stack

### Required Dependencies
| Library | Purpose | Notes |
|---|---|---|
| `ast` | AST parsing and transformation | Standard library — zero install |
| `pathlib` | Path handling | Standard library |
| `dataclasses` | Internal data models | Standard library |
| `tiktoken` | Token estimation | OpenAI's tokenizer; works offline |
| `networkx` | Call graph (DiGraph, BFS/DFS) | Lightweight, well-maintained |
| `rich` | Terminal UI (progress, tables, colors) | Best-in-class TUI library |
| `pyperclip` | Clipboard copy | Cross-platform (macOS/Windows/Linux) |
| `pathspec` | `.gitignore` rule parsing | Better than manual glob matching |
| `click` | CLI argument parsing | More ergonomic than argparse for this use case |

### Why `click` over `argparse`
`click` gives us cleaner command signatures, automatic `--help` generation, and easier testing of CLI entry points. The extra dependency is worth the DX.

### Why `pathspec` over manual gitignore
`.gitignore` syntax has edge cases (negation patterns, nested `.gitignore` files) that manual glob matching gets wrong. `pathspec` handles the full spec correctly.

### No Database. Ever.
This is a stateless filter. Adding SQLite would require synchronization logic, versioning, and migration handling for zero benefit. Config lives in `.shakerrc.json`.

---

## 7. Folder Structure

```
codebase-shaker/
├── README.md
├── pyproject.toml              # Build config, entry points, metadata
├── requirements.txt            # Pinned deps for reproducibility
├── .shakerrc.json.example      # Template config for users
│
├── src/
│   └── shaker/
│       ├── __init__.py
│       ├── cli.py              # Click entry point, argument definitions
│       │
│       ├── engine/
│       │   ├── __init__.py
│       │   ├── discovery.py    # File walker, gitignore filter
│       │   ├── parser.py       # ast.parse → ParsedFile dataclass
│       │   ├── graph.py        # Symbol table, call graph (networkx)
│       │   ├── resolver.py     # Focus resolution, subgraph extraction
│       │   └── pruner.py       # NodeTransformer per compression mode
│       │
│       ├── output/
│       │   ├── __init__.py
│       │   ├── serializer.py   # Markdown document builder
│       │   └── clipboard.py    # pyperclip wrapper + file output
│       │
│       └── utils/
│           ├── __init__.py
│           ├── config.py       # .shakerrc.json loader/validator
│           └── tokens.py       # tiktoken wrapper, count + estimate
│
└── tests/
    ├── __init__.py
    ├── fixtures/               # Small test codebases (synthetic .py files)
    │   ├── simple_app/
    │   └── circular_imports/
    ├── test_parser.py
    ├── test_graph.py
    ├── test_pruner.py
    └── test_serializer.py
```

**Key decisions:**
- `engine/` is fully unit-testable with no CLI dependency
- `output/` is separated from `engine/` so serialization can be swapped (future: JSON output for IDE plugins)
- `fixtures/` contains real synthetic Python projects, not mocked AST objects, so tests catch regressions on real syntax

---

## 8. CLI Design

### Command Signature

```bash
shaker <path> [--focus <symbol>] [--mode <full|signatures|strip>] [--exclude <pattern>] [--output <file>] [--no-clipboard] [--max-tokens <n>] [--config <path>]
```

### Arguments

| Argument | Type | Default | Description |
|---|---|---|---|
| `path` | positional | required | Directory or single file to process |
| `--focus` / `-f` | string | None | Function or class name to trace the call graph from |
| `--mode` / `-m` | enum | `signatures` | Compression mode for non-focused files: `full`, `signatures`, `strip` |
| `--exclude` / `-e` | string (glob) | None | Filename pattern to exclude (can repeat: `-e "*_test.py" -e "migrations/"`) |
| `--output` / `-o` | path | None | Write output to file instead of (or in addition to) clipboard |
| `--no-clipboard` | flag | False | Skip clipboard copy |
| `--max-tokens` | int | None | Warn (don't fail) if output exceeds this token count |
| `--config` | path | `.shakerrc.json` | Path to config file |

### Example Invocations

```bash
# Focus mode: trace login_user call graph, signatures for everything else
shaker ./src --focus login_user --mode signatures

# Full structural map of an entire codebase (no focus)
shaker ./src --mode signatures --no-clipboard --output context.md

# Debug mode: keep full bodies for focused path, strip docs elsewhere
shaker ./src/auth --focus process_payment --mode strip

# Exclude test files and migrations
shaker . --focus UserModel --exclude "*_test.py" --exclude "migrations/"
```

### `.shakerrc.json` Schema

```json
{
  "default_mode": "signatures",
  "exclude_patterns": ["*_test.py", "migrations/", "fixtures/"],
  "max_tokens": 8000,
  "always_include": ["src/models/"],
  "always_exclude": ["src/legacy/"]
}
```

---

## 9. Terminal UI (TUI) Design

Built with `rich`. No frameworks, no web servers.

```
╔══════════════════════════════════════════════════════╗
║  Codebase Shaker v1.0                                ║
╚══════════════════════════════════════════════════════╝

  Target    ./src/auth
  Focus     login_user
  Mode      signatures

  ████████████████████████████████ 100%  Parsing 14 files...

  ✓ Call graph built — 6 files in focus path

  ┌─────────────────┬────────────────┬──────────────────┐
  │ Metric          │ Raw Input      │ Optimized Output │
  ├─────────────────┼────────────────┼──────────────────┤
  │ Files           │ 14             │ 6 (retained)     │
  │ Lines of code   │ 2,450          │ 412              │
  │ Estimated tokens│ ~18,200        │ ~2,940           │
  │ Reduction       │ —              │ 83.8%            │
  └─────────────────┴────────────────┴──────────────────┘

  ✓ Copied to clipboard. Paste directly into your LLM prompt.
```

No color gimmicks. Information density is the aesthetic.

---

## 10. Output Format (Markdown)

The clipboard payload is a self-contained Markdown document structured for LLM consumption:

```markdown
# Codebase Context
> Tool: Codebase Shaker v1.0 | Focus: `login_user` | Mode: signatures
> Retained: 6/14 files | ~2,940 tokens

## Project Structure
```
src/
├── auth/
│   ├── login.py          ← FOCUS PATH
│   └── validators.py     ← FOCUS PATH
├── models/
│   ├── user.py           ← signatures only
│   └── session.py        ← signatures only
└── utils/
    └── crypto.py         ← signatures only
[8 files omitted — not in call graph]
```

## `src/auth/login.py` — FULL (focus)
```python
def login_user(username: str, password: str) -> Optional[Session]:
    user = User.get_by_username(username)
    if not user or not crypto.verify(password, user.password_hash):
        return None
    return Session.create(user)
```

## `src/models/user.py` — signatures only
```python
class User:
    def get_by_username(cls, username: str) -> Optional["User"]: ...
    def check_password(self, raw: str) -> bool: ...
```
```

The `[N files omitted]` section is critical — it tells the LLM that a complete project exists, preventing hallucination about missing modules.

---

## 11. Edge Cases & Robustness

These are the failure modes Gemini's blueprint didn't address. They need to be handled in v1.

| Edge Case | Behavior |
|---|---|
| **Syntax error in a file** | Log warning, skip file, include in `[N files could not be parsed]` section of output |
| **Circular imports** | `networkx` cycle detection before traversal; break cycles, log warning, continue |
| **Dynamic attribute access** (`getattr`, `__getattr__`) | Cannot be traced statically; preserve the calling function in full (`--mode full` override for that function) |
| **`__all__` exports** | Treat as additional public symbols during resolution |
| **Relative imports** (`from . import ...`) | Resolve relative to current package; fall back to file-path heuristics |
| **Non-UTF-8 files** | Attempt `latin-1` fallback; if still unreadable, skip with warning |
| **Single-file input** | Skip graph-building, apply `--mode` directly to the one file |
| **Zero files found** | Exit with a helpful error: *"No Python files found in ./path. Did you mean a parent directory?"* |
| **`--focus` not found** | Exit with error listing the top 10 most common function/class names in the codebase |
| **Output exceeds `--max-tokens`** | Print a warning with suggestions: increase `--mode` compression, add `--exclude` patterns |

---

## 12. Development Roadmap

**Total target: 35 days** (tightened from Gemini's 30, with buffer)

### Phase 1 — Foundation (Days 1–7)
- Repo setup: `pyproject.toml`, `click` entry point, `pytest` config, GitHub Actions CI (lint + test)
- `discovery.py`: directory walker + `pathspec` gitignore filtering
- `parser.py`: `ast.parse()` → `ParsedFile` dataclass (imports, classes, functions, calls)
- `test_parser.py`: 10+ fixture files covering edge cases (empty file, syntax error, relative imports)

**Exit criteria:** `shaker ./tests/fixtures/simple_app` runs without error and prints a list of parsed files.

### Phase 2 — Call Graph (Days 8–16)
- `graph.py`: symbol table builder + `networkx.DiGraph` population
- `resolver.py`: BFS focus resolution (callers + callees), subgraph extraction
- Handle circular imports, unresolvable symbols
- `test_graph.py`: verify focus correctly identifies 3-hop dependency chains

**Exit criteria:** `shaker ./tests/fixtures/simple_app --focus process_order` correctly identifies all transitive dependencies.

### Phase 3 — Pruning Engine (Days 17–23)
- `pruner.py`: `ast.NodeTransformer` subclasses for each mode
  - `SignatureTransformer`: replaces function bodies with `...`, preserves decorators + type hints
  - `StripTransformer`: removes docstrings and `#` comments
- Roundtrip test: pruned AST → `ast.unparse()` → valid Python (assert `ast.parse()` succeeds)
- `test_pruner.py`: verify each mode produces expected output on fixture files

**Exit criteria:** `--mode signatures` reduces the 2,450-line fixture codebase to under 500 lines, all signatures present, all bodies gone.

### Phase 4 — Output & Polish (Days 24–31)
- `serializer.py`: Markdown document builder with file tree, per-file blocks, omission notices
- `tokens.py`: `tiktoken` integration, before/after counts
- `clipboard.py`: `pyperclip` wrapper with OS-appropriate error messages
- `config.py`: `.shakerrc.json` loader with `pydantic` validation (or `dataclasses` + manual validation to avoid the dep)
- `rich` TUI: progress bar, summary table
- `cli.py`: wire all phases together, `--max-tokens` warning, proper `--help` text

**Exit criteria:** Full run from `shaker ./src --focus login_user --mode signatures` produces correct Markdown output, copies to clipboard, displays accurate token counts.

### Phase 5 — Hardening (Days 32–35)
- End-to-end tests on 3 real open-source Python projects (e.g., Flask, FastAPI's auth module, Celery)
- README with GIF demo, installation instructions, 5 common usage examples
- `pip install codebase-shaker` works clean on macOS + Ubuntu

**Exit criteria:** README is the only documentation needed for a new user to get value in under 5 minutes.

---

## 13. Milestones

| # | Day | What You Can Demonstrate |
|---|---|---|
| M1 | 7 | Parser correctly extracts all symbols from a 10-file Python project |
| M2 | 16 | Focus tracing correctly walks a 3-level call graph across files |
| M3 | 23 | Signature pruning achieves ≥70% line reduction on a real codebase |
| M4 | 31 | Full CLI: one command → clipboard-ready Markdown with token stats |
| M5 | 35 | Installable via pip, README-documented, tested on 3 real projects |

---

## 14. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| **Dynamic Python patterns break static analysis** | High | Medium | Fail safe: preserve unresolvable functions in full; document limitation clearly |
| **`ast.unparse()` produces ugly output** (Python 3.9+) | Medium | Low | Post-process output through `black --check` formatting where available; acceptable without it |
| **`tiktoken` model version mismatch** | Low | Low | Default to `cl100k_base` (GPT-4/Claude compatible); make model configurable |
| **LLM context windows keep growing** | Medium | Low | Reframe: Shaker's value shifts from "fits in context" to "improves output quality by reducing noise" — always true |
| **Competing tools (repomix, aider)** | High | Medium | Differentiation is structural awareness + call graph focus. Repomix is text concatenation. Aider is interactive. Neither traces call graphs. |
| **`pyperclip` fails on headless Linux** | Medium | Low | Graceful fallback: print output to stdout, tell user to pipe to `xclip` or `pbcopy` |

---

## 15. Stretch Goals (v2 — Do Not Touch Until v1 Ships)

These are genuinely good ideas that would bloat v1 and delay shipping:

**High Value / Do Next:**
- **JavaScript/TypeScript support** via `tree-sitter-python` pattern (add `tree-sitter` + language grammars)
- **VS Code extension** with right-click → "Copy as Shaker context"
- **JSON output mode** for IDE integrations

**Medium Value:**
- **Interactive Streamlit UI** — dependency graph you can toggle nodes on/off
- **CI hook** — auto-packages context when a pipeline test fails
- **Watch mode** — re-runs on file save, updates clipboard automatically

**Low Priority:**
- **LLM model-specific token counting** (currently defaults to GPT-4 tokenizer)
- **Diff mode** — only include files changed since a given git commit

---

## 16. What Makes This v1 The Best v1

Gemini's blueprint was solid but had two structural gaps this version fixes:

**Gap 1 — Robustness wasn't specified.** The original blueprint didn't enumerate edge cases: syntax errors, circular imports, dynamic attribute access, non-UTF-8 files. These will all be hit in the first week of real-world use. They're handled here with explicit behaviors — not "figure it out later."

**Gap 2 — The output format wasn't precise enough.** The original said "structured Markdown." This blueprint specifies the exact schema: what the header contains, how the file tree is labeled, what the `[N files omitted]` notice says and why. The LLM's behavior depends on these details — an omission notice prevents hallucination; a missing one causes it.

**What Gemini got right (keep it):** Stateless architecture, no database, three compression tiers, `tiktoken` for local counting, `rich` for TUI, `networkx` for the graph. All correct calls. This blueprint keeps them and adds the missing specificity.

---

*This document is the single source of truth for the Codebase Shaker v1.0 build.*
*Next step: create the repo, set up `pyproject.toml`, write the first fixture file, and implement `discovery.py`.*
