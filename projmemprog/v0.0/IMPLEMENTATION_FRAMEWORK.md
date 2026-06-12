# Codebase Shaker — Definitive Implementation Framework

> **Version:** 0.0.0
> **Date:** June 2026
> **Status:** Pre-Implementation — Source of Truth
> **Target:** Python CLI tool for intelligent codebase compression via AST-based call graph analysis

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Executive Summary](#2-executive-summary)
3. [Blueprint Review](#3-blueprint-review)
4. [Architecture Review](#4-architecture-review)
5. [Final Architecture](#5-final-architecture)
6. [Complete Folder Structure](#6-complete-folder-structure)
7. [Module Specifications](#7-module-specifications)
8. [Data Models](#8-data-models)
9. [Development Roadmap](#9-development-roadmap)
10. [File-by-File Implementation Inventory](#10-file-by-file-implementation-inventory)
11. [Dependency Review](#11-dependency-review)
12. [Testing Architecture](#12-testing-architecture)
13. [Risk Analysis](#13-risk-analysis)
14. [MVP Definition](#14-mvp-definition)
15. [Recommended Build Order](#15-recommended-build-order)
16. [Engineering Standards](#16-engineering-standards)
17. [Definition of Done](#17-definition-of-done)
18. [Future Roadmap](#18-future-roadmap)

---

## 1. Project Overview

### Project Mission

Codebase Shaker is a Python CLI tool that understands code **structure** (not just text), traces **only the live call graph** from a focal point, and compresses everything else to the minimum needed for an LLM to understand the broader system — without hallucinating the omitted parts.

### Problem Statement

The problem has three layers:

**Layer 1 — Token waste is money.** Feeding a 50-file Django backend to an LLM when you are only fixing one controller means paying for ~18,000 tokens of irrelevant context on every prompt. At scale, that is $20–100/day in API bills.

**Layer 2 — Attention dilution kills quality.** LLMs lose precision when context is noisy. A model asked to refactor `user_auth.py` surrounded by 49 unrelated files produces worse output than one given only the three files that actually matter. This is the well-documented "needle in a haystack" failure mode.

**Layer 3 — Manual selection does not scale.** Developers today copy-paste files manually, use `cat` with grep pipelines, or rely on tools like `repomix` that do naive full-text concatenation with no structural awareness. None of these can answer: *"Give me just the execution path touched by this function call."*

### Target Users

| Segment | Core Pain | How Shaker Solves It |
|---|---|---|
| **AI-first engineers** (Claude Code, Cursor, Copilot users) | Burning tokens on giant context pastes before every prompt | One command trims context to the relevant call graph |
| **Solo founders / indie hackers** | API bill anxiety; GPT-4o/Claude is expensive at volume | 70–85% token reduction per prompt on targeted tasks |
| **Technical PMs / code reviewers** | Need to understand a change without reading 3,000 lines | Shaker exports a structural skeleton: classes, signatures, no bodies |
| **New team members** | Onboarding to an unfamiliar codebase | Pass any module; get a compressed map of what connects to what |
| **Power Users / Automation** | Want to pipe context into scripts and CI pipelines | stdout-first design, `--output` flag, pipe-friendly |

### Project Goals

1. **Correctness:** The tool must never silently drop code that is relevant to the focus.
2. **Usability:** One command from zero to clipboard-ready Markdown.
3. **Performance:** Process a 500-file project in under 3 seconds on average hardware.
4. **Robustness:** Never crash on real-world codebases (syntax errors, circular imports, dynamic patterns).
5. **Extensibility:** Clean architecture that supports v2 features (multi-language, IDE plugins) without rewrite.

### Design Philosophy

- **Stateless pipe:** Input → Process → Output. No database, no daemon, no persistent state.
- **Conservative analysis:** When unsure, include more context rather than less. False positives are acceptable; false negatives are not.
- **Stdout-first:** The primary output channel is always stdout. Clipboard and file output are secondary.
- **Graceful degradation:** Optional dependencies (`tiktoken`, `pyperclip`) enhance the experience but never block it.
- **Pure functions where possible:** Each pipeline stage is a well-defined transformation with clear inputs and outputs.

### Scope Boundaries

**In scope for v1:**
- Python-only (single language)
- CLI tool (no GUI, no web interface)
- AST-based static analysis
- Three compression modes: `full`, `signatures`, `strip`
- Markdown output format
- Local operation (no cloud/SaaS)
- Single-user, single-machine

**Explicitly out of v1:**
- Web UI / Streamlit interface
- JavaScript/TypeScript support (v2)
- VS Code extension (v2)
- Cloud/SaaS features
- Database (stateless always)
- Interactive graph visualization
- Multi-user collaboration
- Real-time watch mode (v2)
- PR diff integration (v2)

---

## 2. Executive Summary

### Overall Architecture

Codebase Shaker follows a **7-stage stateless pipeline**:

```
Input (path + args)
    → File Discovery          (walk directory, filter by .gitignore)
    → AST Parse (per file)    (extract symbols, imports, calls)
    → Call Graph Build        (symbol table → networkx DiGraph)
    → Focus Resolution        (BFS/DFS from focal node)
    → Prune/Compress          (AST transformation per mode)
    → Serialize to Markdown   (structured document)
    → Token Count + Deliver   (tiktoken, clipboard, stdout)
```

Each stage reads from and writes to a `PipelineState` dataclass that accumulates results, warnings, and metadata. The CLI is a thin composition root that orchestrates the pipeline and displays results.

### Implementation Strategy

- **Language:** Python 3.10+
- **Build system:** `pyproject.toml` only (no `requirements.txt`)
- **CLI framework:** `click`
- **Graph library:** `networkx`
- **TUI library:** `rich`
- **Token counting:** `tiktoken` (optional) with `chars // 4` fallback
- **Clipboard:** `pyperclip` (optional) with graceful degradation
- **Gitignore parsing:** `pathspec`
- **Linting/Formatting:** `ruff`
- **Testing:** `pytest` + `pytest-cov` + `pytest-mock`

### Guiding Engineering Principles

1. **Single Responsibility:** Each module does one thing well.
2. **Separation of Concerns:** Engine (analysis), Output (serialization), Infra (cross-cutting) are independent.
3. **High Coherence:** Related code lives together.
4. **Low Coupling:** Modules communicate through data classes, not shared state (except `PipelineState`).
5. **Testability:** Every module is unit-testable in isolation. Integration tests cover the full pipeline.
6. **Fail-safe:** The tool never crashes on bad input. It warns, degrades, and continues.

### Major Technical Decisions

| Decision | Rationale |
|---|---|
| **`networkx` for call graph** | Provides DiGraph, BFS/DFS, cycle detection out of the box. Heavy (~5MB) but saves ~200 lines of graph code. |
| **`click` over `argparse`** | Cleaner command signatures, automatic `--help`, easier CLI testing. |
| **`pathspec` over manual gitignore** | `.gitignore` syntax has edge cases (negation, nested files) that manual glob matching gets wrong. |
| **`tiktoken` as optional** | Large download. Fallback to `len(text) // 4` is acceptable for estimation. |
| **`pyperclip` as optional** | Fails on headless Linux. Never crash; degrade gracefully. |
| **`rich` for TUI** | Best-in-class TUI library. Tables, progress bars, colors with minimal code. |
| **No database** | Stateless filter. Config lives in `.shakerrc.json`. Adding SQLite would require synchronization for zero benefit. |
| **Python 3.10+ minimum** | 3.9 is EOL October 2025. 3.10 gives us `match` statement support, better error messages, and `ast.unparse()` stability. |
| **`ruff` as sole linter** | Replaces `flake8` + `black` + `isort` + `pyupgrade` in one tool. Fast, modern, zero config. |

---

## 3. Blueprint Review

### Section 1 — The Real Problem

**Strengths:**
- The three-layer framing (token waste, attention dilution, manual selection) is sharp and gives the product a clear value proposition.
- Grounding the attention dilution claim in "needle in a haystack" LLM research adds credibility.

**Weaknesses:**
- Layer 2 (attention dilution) is harder to quantify than Layer 1 (token cost). The tool can demonstrate token reduction empirically; quality improvement is subjective.

**Risks:**
- Overpromising on quality improvement could create unrealistic user expectations.

**Recommended Improvements:**
- Add a performance budget: "v1 must process a 500-file project in under 3 seconds on average hardware."
- Acknowledge the cold start problem — AST parsing + graph construction takes time, and users need to know this is expected.

---

### Section 2 — Target Users

**Strengths:**
- Four distinct segments with clear pain-solution mapping.
- The "AI-first engineers" segment is correctly identified as the beachhead.

**Weaknesses:**
- "Technical PMs / code reviewers" may expect PR diff integration features that are out of v1.

**Risks:**
- The PM/reviewer segment could create scope creep.

**Recommended Improvements:**
- Add a "Power User / Automation" segment for developers who want to pipe output into scripts and CI pipelines.
- Reclassify the PM/reviewer segment as a v2 target.

---

### Section 3 — User Stories

**Strengths:**
- Three primary stories (Debugging Sprint, Safe Refactor, Architecture Snapshot) cover the core use cases well.
- The "blast radius" language in the Safe Refactor story is excellent product thinking.

**Weaknesses:**
- The "CI Failure" story implies automatic packaging with "zero manual work," which requires CI integration — explicitly out of v1.

**Risks:**
- The CI story sets an expectation that v1 cannot meet.

**Recommended Improvements:**
- Reclassify the CI Failure story as v2.
- Add an "Expanding Context" story: the iterative workflow where a user re-runs with a different focus when the LLM says "I need to see X."

---

### Section 4 — MVP Features

**Strengths:**
- The "What Is Explicitly Out of v1" table is excellent discipline.
- Three compression tiers are well-scoped.

**Weaknesses:**
- Clipboard as a "must-have" is debatable — it fails on headless systems.
- Missing standard CLI flags: `--version`, `--verbose`, `--quiet`, `--dry-run`.

**Risks:**
- Making clipboard a must-have implies robust fallback from day one, adding complexity.

**Recommended Improvements:**
- Demote clipboard to "should-have" with graceful degradation.
- Add `--version`, `--verbose`, `--quiet`, `--dry-run` as must-haves.
- Ensure stdout is always the primary output channel.

---

### Section 5 — System Architecture

**Strengths:**
- The stateless pipe philosophy is correct.
- The 7-stage pipeline is clean and sequential.
- `ParsedFile` dataclass approach is sound.

**Weaknesses:**
- Stage 3 (Call Graph Construction) is dramatically underspecified. Resolving `Call` nodes against a symbol table is the hardest part of the entire project.
- Stage 5 (Pruning) says "Files with zero relevant symbols are fully omitted," but files with only needed imports should be preserved as stubs.
- No error aggregation strategy for multiple parse failures.
- No intermediate representation between parsing and serialization.

**Risks:**
- The symbol resolution problem (`foo.bar()` — method? module function? chained attribute?) is fundamentally ambiguous in Python.
- Without a state container, every function signature grows to carry warnings + metadata.

**Recommended Improvements:**
- Introduce a `PipelineState` dataclass that accumulates results, warnings, and metadata.
- Document the symbol resolution heuristic and its limitations explicitly.
- Add an intermediate representation (pruned AST → string) to decouple engine from output.

---

### Section 6 — Technical Stack

**Strengths:**
- The dependency list is lean.
- Justifications for `click` and `pathspec` are sound.

**Weaknesses:**
- `tiktoken` is a large dependency (~2MB for tokenizer data).
- No linting/formatting toolchain specified.
- No `typing-extensions` for backward-compatible type hints.

**Risks:**
- `tiktoken` install issues could block users with limited internet access.

**Recommended Improvements:**
- Make `tiktoken` optional with `chars // 4` fallback.
- Specify `ruff` as the sole linting/formatting tool.
- Add `typing-extensions` for Python < 3.11 backports.

---

### Section 7 — Folder Structure

**Strengths:**
- Clean separation of `engine/`, `output/`, and `utils/`.
- `fixtures/` with real synthetic projects is the right approach.

**Weaknesses:**
- `utils/` is a dumping ground — config and token utilities are infrastructure, not utils.
- Both `requirements.txt` and `pyproject.toml` is redundant.
- No `CHANGELOG.md`, `CONTRIBUTING.md`, `LICENSE` mentioned.
- No `conftest.py`, no `__main__.py`, no centralized `models.py`.

**Risks:**
- Scattered data models will cause circular import issues.

**Recommended Improvements:**
- Rename `utils/` to `infra/` or split into `config/` and `core/`.
- Add `models.py` at the package root for all shared data models.
- Add `__main__.py`, `conftest.py`.
- Remove `requirements.txt` in favor of `pyproject.toml` only.
- Add `LICENSE` (MIT), `CONTRIBUTING.md`, `CHANGELOG.md` from day 1.

---

### Section 8 — CLI Design

**Strengths:**
- The command signature is clean.
- `.shakerrc.json` schema is reasonable.

**Weaknesses:**
- `path` accepts "directory or single file" — these are fundamentally different operations.
- `--exclude` uses glob patterns, but `pathspec` uses gitignore syntax — mismatch.
- No `--format` option for future extensibility.
- No `--version`, `--verbose`, `--quiet`, `--dry-run`, `--list-symbols`.

**Risks:**
- Without `--format` in the CLI signature, adding JSON output later requires a breaking API change.

**Recommended Improvements:**
- Add `--format` with `markdown` as default (only v1 implementation).
- Add `--version`, `--verbose`, `--quiet`, `--dry-run`, `--list-symbols`.
- Clarify that `--exclude` uses gitignore syntax (consistent with `.gitignore`).

---

### Section 9 — Terminal UI

**Strengths:**
- The `rich` output design is clean and informative.
- The before/after table is the right centerpiece.

**Weaknesses:**
- The progress bar assumes we know the total before parsing begins (true), but should account for all 7 stages, not just parsing.
- No error/warning display in the TUI.

**Risks:**
- Progress bar jumping to 100% while still doing graph construction creates a poor UX.

**Recommended Improvements:**
- Add a warnings/errors section to the TUI output.
- Make the progress bar multi-stage.
- Ensure stderr (warnings, progress) does not contaminate stdout (which may be piped).

---

### Section 10 — Output Format

**Strengths:**
- The Markdown schema is well-specified.
- The `[N files omitted]` notice is critical and correctly motivated.

**Weaknesses:**
- The file tree can be very long for large codebases.

**Risks:**
- A 50-file tree adds noise to the LLM prompt.

**Recommended Improvements:**
- Add a `--no-tree` flag for large codebases.
- Consider a compact tree format or depth limit.

---

### Section 11 — Edge Cases & Robustness

**Strengths:**
- This is the strongest section of the blueprint.
- The edge case table is thorough and behaviors are well-specified.

**Weaknesses:**
- "Dynamic attribute access" handling requires detecting `getattr`, `__getattr__`, `eval`, `exec`, `globals()` — significant analysis burden for v1.
- Relative imports resolution requires understanding package structure.

**Risks:**
- Trying to handle all dynamic patterns in v1 could delay shipping indefinitely.

**Recommended Improvements:**
- Document unresolvable patterns as known limitations.
- Degrade gracefully: preserve more context rather than less.
- Add missing edge cases: `*` imports, conditional imports, `__init__.py` re-exports, decorators that modify signatures.

---

### Section 12 — Development Roadmap

**Strengths:**
- 5 phases with clear exit criteria.
- 35-day estimate is realistic for a solo developer.

**Weaknesses:**
- Phase 1 (7 days) is aggressive — parser alone could take 5 days.
- Phase 5 (4 days) includes end-to-end tests on 3 real projects + README with GIF demo + pip install verification.
- No explicit buffer for unexpected complexity.

**Risks:**
- Underestimating parser complexity will cascade through all subsequent phases.

**Recommended Improvements:**
- Add 5 days of buffer (40 days total): +2 for parser, +2 for graph/resolver, +1 for polish.

---

### Section 13 — Milestones

**Strengths:**
- 5 milestones with clear demonstrable outcomes.

**Weaknesses:**
- M3 (≥70% line reduction) is easy to game — just remove more code.

**Recommended Improvements:**
- Add quality criteria: "≥70% line reduction while preserving all public signatures and type annotations."

---

### Section 14 — Risks & Mitigations

**Strengths:**
- The risk table is honest and well-structured.

**Weaknesses:**
- Missing performance risk (large codebases).
- Missing maintenance risk (Python AST changes between versions).
- Missing adoption risk (PyPI publishing, discoverability).

**Recommended Improvements:**
- Add these three risks to the table.
- Set minimum Python version to 3.10.
- Plan for PyPI publishing from day 1.

---

### Section 15 — Stretch Goals

**Strengths:**
- Clear prioritization.
- "Do Not Touch Until v1 Ships" is the right discipline.

**Weaknesses:**
- "Diff mode" is listed as low priority but is arguably the highest-value v2 feature (directly enables PR review).

**Recommended Improvements:**
- Reclassify diff mode as high-value v2.

---

## 4. Architecture Review

### Architecture Evaluation

The blueprint's 7-stage pipeline is architecturally sound. The stateless pipe philosophy is correct for this class of tool. The main gap is the absence of a state container to carry context through the pipeline.

**Key architectural addition: `PipelineState`.**
Without it, every function must return `(result, warnings, metadata)` tuples, and the CLI must manually thread these through. With `PipelineState`, each stage mutates the state, and the CLI reads from it at the end. This is not purely functional, but it is pragmatic and dramatically reduces boilerplate.

**Key architectural addition: Centralized models.**
The blueprint implicitly defines data structures across modules. This will cause circular imports. All shared data models must live in a single `models.py` at the package root, imported by all other modules.

**Key architectural addition: `__package__` re-exports.**
Each subpackage (`engine/`, `output/`, `infra/`) should have an `__init__.py` that re-exports its public API. This gives the CLI (and future consumers) a clean import surface:
```python
from shaker.engine import discover_files, parse_files, build_graph, resolve_focus, prune_files
from shaker.output import serialize, deliver
from shaker.infra import load_config, count_tokens
```

### Dependency Evaluation

| Dependency | Weight | Justification | Verdict |
|---|---|---|---|
| `click` | ~200KB | Best CLI framework for Python | ✅ Keep |
| `networkx` | ~5MB | Graph algorithms (BFS, DFS, cycles) | ✅ Keep for v1 |
| `rich` | ~500KB | Best TUI library for Python | ✅ Keep |
| `tiktoken` | ~2MB | Accurate token counting | ⚠️ Optional |
| `pyperclip` | ~50KB | Clipboard access | ⚠️ Optional |
| `pathspec` | ~100KB | Correct gitignore parsing | ✅ Keep |
| `typing-extensions` | ~200KB | Backported type hints | ✅ Add |

### AST Analysis Approach

**Parsing strategy:** Use Python's built-in `ast.parse()` on each file. Walk the AST with a custom `ast.NodeVisitor` that extracts:
- `Import` and `ImportFrom` nodes → `ImportInfo` objects
- `ClassDef` nodes → `Symbol` objects with `SymbolType.CLASS`
- `FunctionDef` and `AsyncFunctionDef` nodes → `Symbol` objects with `SymbolType.FUNCTION` or `SymbolType.METHOD`
- `Call` nodes within function bodies → `CallSite` objects

**Scope handling:** Use `module_path.symbol_name` as the qualified name (e.g., `auth.login.process`). For class methods, use `module_path.ClassName.method_name`.

**Call filtering:** Skip calls to Python builtins (`print`, `len`, `isinstance`, etc.) and optionally skip stdlib modules. This is configurable via `constants.BUILTIN_NAMES` and `constants.STDLIB_MODULES`.

**Import tracking:** Maintain a per-file mapping of local name → fully qualified module symbol. For `from foo import bar`, map `bar` → `foo.bar`. For `import foo as f`, map `f` → `foo`. For `from foo import *`, mark all of `foo`'s symbols as potentially reachable.

### Graph Strategy

**Data structure:** `networkx.DiGraph` where nodes are qualified symbol names and edges represent "calls" relationships.

**Construction:**
1. Build a symbol table: `{qualified_name: Symbol}` from all parsed files.
2. For each `CallSite`, attempt to resolve it against the symbol table using the file's import mapping.
3. If resolved, add an edge: `caller_qualified_name → callee_qualified_name`.
4. If unresolved, log it in `CallGraph.unresolved_calls`.

**Cycle detection:** Use `networkx.simple_cycles()` after graph construction. Log cycles as warnings. The graph remains valid; cycles are informational.

**Focus resolution:** Given a focal symbol, use `networkx.descendants()` (callees) + `networkx.ancestors()` (callers) to extract the relevant subgraph. Map symbols back to files for the pruner.

**Conservative approach:** When resolution is ambiguous (e.g., `foo.bar()` could resolve to multiple symbols), include all candidates. Better to include too much context than too little.

### Pruning Strategy

**Approach:** Use `ast.NodeTransformer` subclasses for each compression mode. Transform the AST, then use `ast.unparse()` to produce the output source.

**`SignatureTransformer` (for `--mode signatures`):**
- Replace every `FunctionDef`/`AsyncFunctionDef` body with a single `ast.Expr(value=ast.Constant(value=...))` (i.e., `...`).
- Preserve decorators, type annotations, default argument values, `*args`, `**kwargs`, keyword-only markers, positional-only markers.
- Preserve class definitions with their method signatures.
- Preserve module-level code (imports, constants, etc.).

**`StripTransformer` (for `--mode strip`):**
- Remove docstrings (first-child `Expr` with `Constant` value in a function/class/module body).
- Remove `#` comment lines from source (post-processing, not AST-based, since comments are not in the AST).
- Preserve all code bodies.

**Roundtrip guarantee:** Every pruned output must pass `ast.parse()` successfully. This is tested in the pruner's unit tests.

### Output Strategy

**Format:** Markdown document, structured for LLM consumption.

**Schema:**
```
# Codebase Context — [project_name]
> Generated by Codebase Shaker v1.0 | Focus: login_user | Mode: signatures
> Files: 6 retained / 14 total | Lines: 412 / 2,450 | Est. tokens: ~2,940

## File Tree
[ASCII tree with focus markers]

## src/auth/login.py — FULL (focus)
```python
[pruned source]
```

## src/models/user.py — signatures only
```python
[pruned source]
```

[8 files omitted — not in call graph]
```

**Building the output:** Use a list-of-strings pattern (append to list, `"\n".join()` at the end) for efficiency with large outputs.

**File tree:** Recursive function that builds an ASCII tree. Files in the focus path are marked with `← FOCUS PATH`. Omitted files are listed in a separate section.

**Omission notice:** Critical for preventing LLM hallucination. The `[N files omitted]` section tells the LLM that a complete project exists beyond what is shown.

---

## 5. Final Architecture

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                           CLI (cli.py)                              │
│                     Composition Root / Wiring                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │   engine/    │  │   output/    │  │        infra/            │  │
│  │              │  │              │  │                          │  │
│  │ discovery.py │  │ serializer.py│  │    config.py             │  │
│  │ parser.py    │  │ clipboard.py │  │    tokens.py             │  │
│  │ graph.py     │  │              │  │                          │  │
│  │ resolver.py  │  │              │  │                          │  │
│  │ pruner.py    │  │              │  │                          │  │
│  └──────┬───────┘  └──────┬───────┘  └────────────┬─────────────┘  │
│         │                 │                        │                │
│  ┌──────┴─────────────────┴────────────────────────┴─────────────┐  │
│  │                        models.py                               │  │
│  │                   (Shared Data Models)                         │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │                      constants.py                              │  │
│  │                    (Shared Constants)                          │  │
│  └────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### Package Layout

```
shaker/
├── __init__.py              # Version
├── __main__.py              # python -m shaker
├── models.py                # ALL shared dataclasses
├── constants.py             # ALL shared constants
├── cli.py                   # Click entry point (composition root)
│
├── engine/                  # Core analysis pipeline
│   ├── __init__.py          # Public API re-exports
│   ├── discovery.py         # Stage 1: File discovery
│   ├── parser.py            # Stage 2: AST parsing
│   ├── graph.py             # Stage 3: Call graph construction
│   ├── resolver.py          # Stage 4: Focus resolution
│   └── pruner.py            # Stage 5: Code compression
│
├── output/                  # Serialization and delivery
│   ├── __init__.py          # Public API re-exports
│   ├── serializer.py        # Stage 6: Markdown serialization
│   └── clipboard.py         # Stage 7: Delivery (clipboard/file)
│
└── infra/                   # Cross-cutting concerns
    ├── __init__.py          # Public API re-exports
    ├── config.py            # Configuration loading
    └── tokens.py            # Token counting
```

### Module Boundaries

**Rule 1:** `models.py` imports nothing from the project. It is the foundation.

**Rule 2:** `engine/` modules never import from `output/` or `infra/`. Data flows engine → output, never backward.

**Rule 3:** `cli.py` is the only module that imports from all other packages. It is the composition root.

**Rule 4:** No circular imports between any two modules. If two modules need shared code, it goes in `models.py` or `constants.py`.

**Rule 5:** Each subpackage's `__init__.py` re-exports only the public API. Internal functions are not re-exported.

### Dependency Flow

```
constants.py ← models.py
     ↑              ↑
infra/           engine/         output/
     ↑              ↑              ↑
     └──────────────┴──────────────┘
                    ↑
                 cli.py
```

Dependencies flow upward. `cli.py` depends on everything. `models.py` depends on nothing (stdlib only). `constants.py` depends only on `models.py`.

### Data Flow

```
User Input (CLI args)
       │
       ▼
┌──────────────┐
│ PipelineState│ ← Created by CLI with config + args
└──────┬───────┘
       │
       ▼
┌──────────────┐     ┌──────────────┐
│  Discovery   │────►│ PipelineState│ .discovered_files
└──────────────┘     └──────┬───────┘
                            │
                            ▼
┌──────────────┐     ┌──────────────┐
│   Parser     │────►│ PipelineState│ .parsed_files
└──────────────┘     └──────┬───────┘
                            │
                            ▼
┌──────────────┐     ┌──────────────┐
│ Graph Build  │────►│ PipelineState│ .call_graph
└──────────────┘     └──────┬───────┘
                            │
                            ▼
┌──────────────┐     ┌──────────────┐
│  Resolver    │────►│ PipelineState│ .focus_symbols, .focus_files
└──────────────┘     └──────┬───────┘
                            │
                            ▼
┌──────────────┐     ┌──────────────┐
│   Pruner     │────►│ PipelineState│ .pruned_files, .omitted_files
└──────────────┘     └──────┬───────┘
                            │
                            ▼
┌──────────────┐     ┌──────────────┐
│ Serializer   │────►│ PipelineState│ .output
└──────────────┘     └──────┬───────┘
                            │
                            ▼
┌──────────────┐     ┌──────────────┐
│  Delivery    │────►│ PipelineState│ .delivery
└──────────────┘     └──────┬───────┘
                            │
                            ▼
                     ┌──────────────┐
                     │  CLI Display │ ← Rich TUI output
                     └──────────────┘
```

---

## 6. Complete Folder Structure

### Repository Root

```
codebase-shaker/
├── CHANGELOG.md                    # Version history
├── CONTRIBUTING.md                 # How to contribute
├── LICENSE                         # MIT License
├── README.md                       # Installation, usage, examples
├── pyproject.toml                  # Build config, deps, entry points (sole build file)
├── .github/
│   └── workflows/
│       └── ci.yml                  # GitHub Actions: lint + test
├── .gitignore
└── .shakerrc.json.example          # Template config for users
```

**Root file responsibilities:**

| File | Purpose |
|---|---|
| `pyproject.toml` | Sole build configuration. Dependencies, entry points, metadata, tool config (ruff, mypy, pytest). |
| `README.md` | Installation, usage, examples, architecture overview. The only documentation needed for a new user. |
| `CHANGELOG.md` | Version history. Updated with each release. |
| `CONTRIBUTING.md` | How to set up dev environment, run tests, submit PRs. |
| `LICENSE` | MIT License. |
| `.shakerrc.json.example` | Template config file showing all available options. |

### Source Package

```
src/
└── shaker/
    ├── __init__.py
    ├── __main__.py
    ├── models.py
    ├── constants.py
    ├── cli.py
    │
    ├── engine/
    │   ├── __init__.py
    │   ├── discovery.py
    │   ├── parser.py
    │   ├── graph.py
    │   ├── resolver.py
    │   └── pruner.py
    │
    ├── output/
    │   ├── __init__.py
    │   ├── serializer.py
    │   └── clipboard.py
    │
    └── infra/
        ├── __init__.py
        ├── config.py
        └── tokens.py
```

**Package responsibilities:**

| Package | Purpose | Key Constraint |
|---|---|---|
| `shaker` (root) | Version, models, constants, CLI | `models.py` imports nothing from the project |
| `shaker.engine` | Core analysis pipeline (stages 1–5) | Never imports from `output/` or `infra/` |
| `shaker.output` | Serialization and delivery (stages 6–7) | Depends on `models` only, not on `engine` internals |
| `shaker.infra` | Cross-cutting concerns (config, tokens) | Self-contained, no engine/output deps |

### Test Suite

```
tests/
├── __init__.py
├── conftest.py                     # Shared fixtures and helpers
│
├── fixtures/
│   ├── __init__.py
│   ├── simple_app/                 # 5-10 file synthetic project
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── services.py
│   │   └── utils.py
│   ├── circular_imports/           # Circular import edge case
│   │   ├── __init__.py
│   │   ├── a.py
│   │   └── b.py
│   ├── syntax_errors/             # Files with syntax errors
│   │   ├── __init__.py
│   │   ├── valid.py
│   │   └── broken.py
│   ├── dynamic_patterns/          # getattr, eval, etc.
│   │   ├── __init__.py
│   │   └── dynamic.py
│   ├── edge_cases/                # Python feature edge cases
│   │   ├── __init__.py
│   │   ├── async_code.py
│   │   ├── decorators.py
│   │   ├── type_annotations.py
│   │   └── walrus_match.py
│   └── large_app/                 # 50+ files for perf testing
│       └── ...
│
├── unit/
│   ├── __init__.py
│   ├── test_discovery.py
│   ├── test_parser.py
│   ├── test_graph.py
│   ├── test_resolver.py
│   ├── test_pruner.py
│   ├── test_serializer.py
│   ├── test_config.py
│   └── test_tokens.py
│
└── integration/
    ├── __init__.py
    ├── test_pipeline.py            # End-to-end pipeline tests
    └── test_cli.py                # CLI invocation tests
```

**Test directory responsibilities:**

| Directory | Purpose |
|---|---|
| `fixtures/` | Real synthetic Python projects. Not mocked AST objects — actual `.py` files that catch regressions on real syntax. |
| `unit/` | One test file per module. Tests each module in isolation with mocked dependencies. |
| `integration/` | End-to-end tests. Full pipeline from CLI args to output. |

---

## 7. Module Specifications

### `models.py`

**Purpose:** All shared data models. The foundation of the architecture. Zero business logic — pure data containers.

**Responsibilities:**
- Define every dataclass and enum used across the codebase
- Provide type-safe data structures for inter-module communication
- Centralize all model definitions to prevent circular imports

**Public API:**
- `CompressionMode` (enum)
- `SymbolType` (enum)
- `ImportInfo` (dataclass, frozen)
- `CallSite` (dataclass, frozen)
- `Symbol` (dataclass, frozen)
- `ParsedFile` (dataclass)
- `CallGraph` (dataclass)
- `BuildStats` (dataclass)
- `OutputMetadata` (dataclass)
- `Config` (dataclass)
- `DeliveryResult` (dataclass)
- `PipelineState` (dataclass)

**Internal Components:** None. Pure data module.

**Dependencies:** `dataclasses`, `enum`, `pathlib`, `typing`, `typing_extensions`

**Testing Requirements:** Models are tested indirectly through every other module's tests. No dedicated test file needed.

**Future Extension Points:**
- Add `Language` enum for multi-language support (v2)
- Add `OutputFormat` enum for JSON/XML output (v2)
- Add `DiffRange` for diff mode (v2)

---

### `constants.py`

**Purpose:** Shared constants used across the codebase.

**Responsibilities:**
- Define all magic values, defaults, and lookup tables in one place
- Provide builtin/stdlib name sets for call filtering

**Public API:**
- `DEFAULT_MODE: CompressionMode`
- `SUPPORTED_MODES: tuple[CompressionMode, ...]`
- `DEFAULT_ENCODING: str` = `"utf-8"`
- `FALLBACK_ENCODING: str` = `"latin-1"`
- `OMIT_THRESHOLD: int` = 50
- `TIKTOKEN_DEFAULT_ENCODING: str` = `"cl100k_base"`
- `CHARS_PER_TOKEN_FALLBACK: int` = 4
- `BUILTIN_NAMES: frozenset[str]`
- `STDLIB_MODULES: frozenset[str]`

**Internal Components:** None.

**Dependencies:** `shaker.models`

**Testing Requirements:** Trivial module, tested indirectly.

**Future Extension Points:**
- Add `LANGUAGE_PARSERS` dict for multi-language support (v2)
- Add `OUTPUT_FORMATS` for format registry (v2)

---

### `cli.py`

**Purpose:** CLI entry point. The composition root that wires all packages together.

**Responsibilities:**
- Define Click commands and options
- Orchestrate the full pipeline via `PipelineState`
- Display results via Rich (progress bar, summary table, warnings)
- Handle errors gracefully with user-friendly messages

**Public API:**
- `cli()` — Click command group (the entry point)

**Internal Components:**
- `run_pipeline(path, focus, mode, ...)` — orchestrates the full pipeline
- `display_results(state: PipelineState)` — Rich output formatting
- `handle_error(error: Exception)` — user-friendly error messages
- `create_progress_bar()` — Rich progress bar setup

**Dependencies:** All shaker packages, `click`, `rich`

**Testing Requirements:** Tested via `integration/test_cli.py` using Click's `CliRunner`.

**Future Extension Points:**
- Add subcommands: `shaker list-symbols`, `shaker config init`
- Add `--format json` for machine-readable output
- Add `--watch` mode for file-system monitoring (v2)

---

### `engine/discovery.py`

**Purpose:** Stage 1 of the pipeline. File discovery with gitignore support.

**Responsibilities:**
- Walk a directory tree to find `.py` files
- Filter by `.gitignore` rules using `pathspec`
- Apply `--exclude` patterns
- Return a sorted list of `Path` objects

**Public API:**
- `discover_files(path: Path, config: Config) -> list[Path]`

**Internal Components:**
- `_walk_directory(path: Path) -> Iterator[Path]` — recursive walker
- `_matches_exclude(file: Path, patterns: list[str]) -> bool` — glob matching
- `_load_gitignore(path: Path) -> pathspec.PathSpec | None` — gitignore loader

**Dependencies:** `pathlib`, `pathspec`, `shaker.models`, `shaker.constants`

**Testing Requirements:** 15+ unit tests covering gitignore handling, exclude patterns, edge cases.

**Future Extension Points:**
- Add `--include` patterns (whitelist mode)
- Add file size filtering
- Add language detection for multi-language support (v2)

---

### `engine/parser.py`

**Purpose:** Stage 2 of the pipeline. AST parsing and symbol extraction.

**Responsibilities:**
- Parse Python files into AST using `ast.parse()`
- Extract imports, classes, functions, methods, and calls
- Build `ParsedFile` objects
- Handle parse errors gracefully (log warning, don't crash)

**Public API:**
- `parse_files(files: list[Path], config: Config) -> dict[Path, ParsedFile]`
- `parse_file(path: Path) -> ParsedFile`

**Internal Components:**
- `_extract_imports(tree: ast.Module) -> list[ImportInfo]`
- `_extract_classes(tree: ast.Module, module_name: str) -> list[Symbol]`
- `_extract_functions(tree: ast.Module, module_name: str) -> list[Symbol]`
- `_extract_calls(body: list[ast.stmt], scope: str) -> list[CallSite]`
- `_resolve_module_name(path: Path, root: Path) -> str`
- `_is_builtin(name: str) -> bool`
- `_is_stdlib(module: str) -> bool`

**Dependencies:** `ast`, `pathlib`, `shaker.models`, `shaker.constants`

**Testing Requirements:** 25+ unit tests covering all node types, error handling, edge cases. This is the most complex module and needs the most thorough testing.

**Future Extension Points:**
- Add `_extract_type_aliases()` for type alias tracking
- Add `_extract_decorators()` for decorator analysis
- Add tree-sitter backend for multi-language support (v2)

---

### `engine/graph.py`

**Purpose:** Stage 3 of the pipeline. Call graph construction.

**Responsibilities:**
- Build a symbol table from parsed files
- Construct a `networkx.DiGraph` of symbol dependencies
- Handle unresolvable symbols gracefully
- Detect cycles

**Public API:**
- `build_graph(parsed: dict[Path, ParsedFile]) -> CallGraph`
- `get_callers(graph: CallGraph, symbol: str) -> set[str]`
- `get_callees(graph: CallGraph, symbol: str) -> set[str]`

**Internal Components:**
- `_build_symbol_table(parsed: dict[Path, ParsedFile]) -> dict[str, Symbol]`
- `_resolve_call(call: CallSite, imports: list[ImportInfo], symbol_table: dict[str, Symbol]) -> str | None`
- `_detect_cycles(graph: nx.DiGraph) -> list[list[str]]`

**Dependencies:** `networkx`, `shaker.models`

**Testing Requirements:** 15+ unit tests covering graph construction, resolution, cycles, edge cases.

**Future Extension Points:**
- Add weighted edges (call frequency)
- Add community detection for module clustering
- Replace `networkx` with lightweight `dict`-based graph if dependency weight matters (v2)

---

### `engine/resolver.py`

**Purpose:** Stage 4 of the pipeline. Focus resolution and subgraph extraction.

**Responsibilities:**
- Given a focal symbol, extract the relevant subgraph
- Handle missing focus gracefully with suggestions
- Map symbols back to files

**Public API:**
- `resolve_focus(graph: CallGraph, focus: str) -> set[str]`
- `resolve_focus_files(focus_symbols: set[str], parsed: dict[Path, ParsedFile]) -> set[Path]`
- `suggest_symbols(graph: CallGraph, query: str, limit: int = 10) -> list[str]`

**Internal Components:**
- `_bfs(graph: nx.DiGraph, start: str, direction: str) -> set[str]`
- `_fuzzy_match(query: str, candidates: list[str], limit: int) -> list[str]`

**Dependencies:** `networkx`, `shaker.models`

**Testing Requirements:** 10+ unit tests covering focus resolution, suggestions, edge cases.

**Future Extension Points:**
- Add `--focus-depth N` to limit BFS depth
- Add `--focus-callers-only` / `--focus-callees-only` directional flags
- Add regex-based focus matching

---

### `engine/pruner.py`

**Purpose:** Stage 5 of the pipeline. AST-based code compression.

**Responsibilities:**
- Apply compression modes to parsed files
- Preserve focus files at full detail
- Apply the selected mode to non-focus files
- Ensure pruned output is valid Python

**Public API:**
- `prune_files(parsed: dict[Path, ParsedFile], focus_files: set[Path], mode: CompressionMode) -> dict[Path, str]`

**Internal Components:**
- `SignatureTransformer(ast.NodeTransformer)` — replaces function bodies with `...`
- `StripTransformer(ast.NodeTransformer)` — removes docstrings and comments
- `_prune_file(parsed: ParsedFile, mode: CompressionMode) -> str`
- `_remove_comments(source: str) -> str`
- `_is_docstring(node: ast.stmt) -> bool`

**Dependencies:** `ast`, `shaker.models`, `shaker.constants`

**Testing Requirements:** 20+ unit tests covering all modes, roundtrip validity, edge cases.

**Future Extension Points:**
- Add `MinimalTransformer` (v2) — removes all non-essential code
- Add `--preserve-decorators` / `--strip-decorators` flags
- Add `--preserve-type-hints` / `--strip-type-hints` flags

---

### `output/serializer.py`

**Purpose:** Stage 6 of the pipeline. Markdown document construction.

**Responsibilities:**
- Build the Markdown output document from pruned files and metadata
- Generate the ASCII file tree
- Format per-file sections with language tags
- Generate the omission notice

**Public API:**
- `serialize(pruned: dict[Path, str], metadata: OutputMetadata, focus_files: set[Path], omitted_files: list[Path]) -> str`

**Internal Components:**
- `_build_header(metadata: OutputMetadata) -> str`
- `_build_tree(files: list[Path], focus_files: set[Path], omitted: list[Path]) -> str`
- `_build_file_section(path: Path, source: str, is_focus: bool, mode: CompressionMode) -> str`
- `_build_omitted_notice(omitted: list[Path]) -> str`

**Dependencies:** `shaker.models`, `shaker.constants`

**Testing Requirements:** 10+ unit tests covering output format, tree generation, edge cases.

**Future Extension Points:**
- Add `_build_json_output()` for JSON format (v2)
- Add collapsible sections for large outputs
- Add `--no-tree` flag support

---

### `output/clipboard.py`

**Purpose:** Stage 7 of the pipeline. Output delivery (clipboard + file).

**Responsibilities:**
- Copy output to clipboard via `pyperclip`
- Write output to file
- Handle errors gracefully (clipboard unavailable, file write errors)

**Public API:**
- `deliver(content: str, output_path: Path | None, copy_to_clipboard: bool) -> DeliveryResult`

**Internal Components:**
- `_copy_to_clipboard(content: str) -> bool`
- `_write_to_file(content: str, path: Path) -> None`

**Dependencies:** `pyperclip` (optional), `shaker.models`

**Testing Requirements:** 6+ unit tests covering clipboard, file output, error handling.

**Future Extension Points:**
- Add `_pipe_to_stdout()` for explicit stdout delivery
- Add `_upload_to_gist()` for GitHub Gist integration (v2)

---

### `infra/config.py`

**Purpose:** Configuration loading and validation.

**Responsibilities:**
- Load `.shakerrc.json` from the project directory or a specified path
- Validate config values
- Merge config with CLI arguments (CLI wins)
- Provide default values for all config options

**Public API:**
- `load_config(path: Path | None = None) -> Config`
- `merge_config_with_cli(config: Config, cli_args: dict) -> Config`

**Internal Components:**
- `_validate_mode(mode: str) -> CompressionMode`
- `_validate_patterns(patterns: list[str]) -> list[str]`
- `_find_config_file(path: Path) -> Path | None`

**Dependencies:** `json`, `pathlib`, `shaker.models`, `shaker.constants`

**Testing Requirements:** 10+ unit tests covering validation, merging, error messages.

**Future Extension Points:**
- Add environment variable support (`SHAKER_MODE`, `SHAKER_MAX_TOKENS`)
- Add XDG config directory support (`~/.config/shaker/config.json`)
- Add config migration for version upgrades

---

### `infra/tokens.py`

**Purpose:** Token counting.

**Responsibilities:**
- Count tokens in a string using `tiktoken` (if available)
- Provide fallback estimation when `tiktoken` is unavailable
- Lazy-load the tiktoken encoder for performance

**Public API:**
- `count_tokens(text: str) -> int`
- `estimate_tokens(text: str) -> int`

**Internal Components:**
- `_get_encoder() -> tiktoken.Encoding | None`

**Dependencies:** `tiktoken` (optional), `shaker.constants`

**Testing Requirements:** 5+ unit tests covering counting accuracy, fallback behavior.

**Future Extension Points:**
- Add model-specific token counting (GPT-3.5, GPT-4, Claude, etc.)
- Add `--tokenizer-model` flag

---

## 8. Data Models

### `CompressionMode`

**Purpose:** Enum for the three compression modes. Using an enum prevents stringly-typed errors.

**Fields:**

| Field | Type | Description |
|---|---|---|
| `FULL` | `str` = `"full"` | Keep source as-is |
| `SIGNATURES` | `str` = `"signatures"` | Headers only, bodies replaced with `...` |
| `STRIP` | `str` = `"strip"` | Remove docstrings and comments |

**Validation Rules:** Must be one of the three values. Case-insensitive parsing from CLI/config.

**Relationships:** Used by `Config`, `OutputMetadata`, `pruner.py`, `serializer.py`.

**Example Instance:**
```python
mode = CompressionMode.SIGNATURES
assert mode.value == "signatures"
```

---

### `SymbolType`

**Purpose:** Classify extracted symbols for the call graph.

**Fields:**

| Field | Type | Description |
|---|---|---|
| `MODULE` | `str` = `"module"` | A Python module |
| `CLASS` | `str` = `"class"` | A class definition |
| `FUNCTION` | `str` = `"function"` | A module-level function |
| `METHOD` | `str` = `"method"` | A class method |

**Validation Rules:** Must be one of the four values.

**Relationships:** Used by `Symbol`.

**Example Instance:**
```python
symbol_type = SymbolType.METHOD
assert symbol_type.value == "method"
```

---

### `ImportInfo`

**Purpose:** Record an import statement with enough detail to resolve symbols.

**Fields:**

| Field | Type | Default | Description |
|---|---|---|---|
| `module` | `str` | (required) | e.g., `"os.path"`, `"src.models.user"` |
| `names` | `tuple[str, ...]` | (required) | e.g., `("join", "basename")` for `from os.path import join, basename` |
| `alias` | `str \| None` | `None` | e.g., `"np"` for `import numpy as np` |
| `is_wildcard` | `bool` | `False` | True for `from foo import *` |
| `is_relative` | `bool` | `False` | True for `from . import foo` |
| `level` | `int` | `0` | Relative import level (number of dots) |
| `line_number` | `int` | `0` | Source line number |

**Validation Rules:**
- If `is_wildcard` is `True`, `names` should be empty.
- If `is_relative` is `True`, `level` must be > 0.

**Relationships:** Used by `ParsedFile`.

**Example Instance:**
```python
import_info = ImportInfo(
    module="src.models.user",
    names=("User", "UserManager"),
    alias=None,
    is_wildcard=False,
    is_relative=False,
    level=0,
    line_number=3
)
```

---

### `CallSite`

**Purpose:** Record a function/method call site within a function body.

**Fields:**

| Field | Type | Default | Description |
|---|---|---|---|
| `name` | `str` | (required) | The called name, e.g., `"process_payment"` or `"user.check_password"` |
| `qualified_name` | `str \| None` | `None` | Resolved qualified name, e.g., `"src.models.user.User.check_password"` |
| `line_number` | `int` | `0` | Source line number |
| `is_method` | `bool` | `False` | True if call is on an object (`foo.bar()`) |
| `receiver` | `str \| None` | `None` | The object being called on, if known |

**Validation Rules:** If `is_method` is `True`, `receiver` should be set (even if just a variable name).

**Relationships:** Used by `ParsedFile`.

**Example Instance:**
```python
call = CallSite(
    name="check_password",
    qualified_name="src.models.user.User.check_password",
    line_number=42,
    is_method=True,
    receiver="user"
)
```

---

### `Symbol`

**Purpose:** A named entity in the codebase.

**Fields:**

| Field | Type | Default | Description |
|---|---|---|---|
| `name` | `str` | (required) | e.g., `"User"`, `"process_payment"` |
| `qualified_name` | `str` | (required) | e.g., `"src.models.user.User"` |
| `symbol_type` | `SymbolType` | (required) | The type of symbol |
| `file` | `Path` | (required) | File path |
| `line_number` | `int` | (0 | Source line number |
| `decorators` | `tuple[str, ...]` | `()` | Decorator names |
| `parent` | `str \| None` | `None` | For methods: the class qualified name |
| `is_async` | `bool` | `False` | Whether the symbol is async |
| `docstring` | `str \| None` | `None` | The symbol's docstring |

**Validation Rules:**
- `qualified_name` must be unique within a codebase.
- For methods, `parent` must be set.

**Relationships:** Used by `ParsedFile`, `CallGraph.symbol_table`.

**Example Instance:**
```python
symbol = Symbol(
    name="User",
    qualified_name="src.models.user.User",
    symbol_type=SymbolType.CLASS,
    file=Path("src/models/user.py"),
    line_number=10,
    decorators=("dataclass",),
    parent=None,
    is_async=False,
    docstring="Represents a user in the system."
)
```

---

### `ParsedFile`

**Purpose:** The result of parsing a single Python file.

**Fields:**

| Field | Type | Default | Description |
|---|---|---|---|
| `path` | `Path` | (required) | File path |
| `module_name` | `str` | (required) | Dotted module name, e.g., `"src.models.user"` |
| `symbols` | `list[Symbol]` | `[]` | Extracted symbols |
| `imports` | `list[ImportInfo]` | `[]` | Extracted imports |
| `call_sites` | `list[CallSite]` | `[]` | Extracted call sites |
| `source` | `str` | `""` | Original source code |
| `ast_tree` | `ast.Module \| None` | `None` | Parsed AST (not serialized) |
| `parse_error` | `str \| None` | `None` | Error message if parsing failed |
| `encoding` | `str` | `"utf-8"` | File encoding |

**Validation Rules:** If `parse_error` is set, `symbols`, `imports`, and `call_sites` may be empty.

**Relationships:** Produced by `parser.py`, consumed by `graph.py`, `resolver.py`, `pruner.py`.

**Example Instance:**
```python
parsed = ParsedFile(
    path=Path("src/models/user.py"),
    module_name="src.models.user",
    symbols=[...],
    imports=[...],
    call_sites=[...],
    source="import ...",
    ast_tree=<ast.Module>,
    parse_error=None,
    encoding="utf-8"
)
```

---

### `CallGraph`

**Purpose:** The call graph with its symbol table and metadata.

**Fields:**

| Field | Type | Default | Description |
|---|---|---|---|
| `graph` | `nx.DiGraph` | (required) | networkx directed graph |
| `symbol_table` | `dict[str, Symbol]` | (required) | qualified_name → Symbol |
| `unresolved_calls` | `list[CallSite]` | `[]` | Calls that could not be resolved |
| `cycles` | `list[list[str]]` | `[]` | Detected cycles |

**Validation Rules:** All symbols in `symbol_table` should have corresponding nodes in `graph`.

**Relationships:** Produced by `graph.py`, consumed by `resolver.py`.

**Example Instance:**
```python
graph = CallGraph(
    graph=<nx.DiGraph with 42 nodes>,
    symbol_table={"src.models.user.User": <Symbol>, ...},
    unresolved_calls=[<CallSite for getattr(...)>, ...],
    cycles=[["a.process", "b.handle", "a.process"]]
)
```

---

### `BuildStats`

**Purpose:** Statistics about the build, displayed in the TUI.

**Fields:**

| Field | Type | Default | Description |
|---|---|---|---|
| `total_files` | `int` | `0` | Total files discovered |
| `retained_files` | `int` | `0` | Files in the output |
| `omitted_files` | `int` | `0` | Files not in the output |
| `parse_errors` | `int` | `0` | Files that failed to parse |
| `total_lines` | `int` | `0` | Total lines in input |
| `output_lines` | `int` | `0` | Lines in output |
| `input_tokens` | `int` | `0` | Estimated input tokens |
| `output_tokens` | `int` | `0` | Estimated output tokens |
| `reduction_pct` | `float` | `0.0` | Token reduction percentage |

**Computed Properties:**

| Property | Type | Description |
|---|---|---|
| `files_reduction_pct` | `float` | Percentage of files reduced |

**Relationships:** Used by `OutputMetadata`, `cli.py` display.

**Example Instance:**
```python
stats = BuildStats(
    total_files=14,
    retained_files=6,
    omitted_files=8,
    parse_errors=0,
    total_lines=2450,
    output_lines=412,
    input_tokens=18200,
    output_tokens=2940,
    reduction_pct=83.8
)
assert stats.files_reduction_pct == 57.1
```

---

### `OutputMetadata`

**Purpose:** Metadata included in the Markdown output header.

**Fields:**

| Field | Type | Description |
|---|---|---|
| `project_name` | `str` | Name of the project (derived from directory name) |
| `focus` | `str \| None` | The focus symbol, if any |
| `mode` | `CompressionMode` | The compression mode used |
| `config_path` | `Path \| None` | Path to the config file used |
| `timestamp` | `str` | ISO 8601 timestamp of the build |
| `version` | `str` | Codebase Shaker version |
| `stats` | `BuildStats` | Build statistics |

**Relationships:** Produced by `cli.py`, consumed by `serializer.py`.

**Example Instance:**
```python
metadata = OutputMetadata(
    project_name="my_project",
    focus="login_user",
    mode=CompressionMode.SIGNATURES,
    config_path=Path(".shakerrc.json"),
    timestamp="2026-06-15T14:30:00",
    version="0.0.0",
    stats=<BuildStats>
)
```

---

### `Config`

**Purpose:** Application configuration from `.shakerrc.json` and CLI.

**Fields:**

| Field | Type | Default | Description |
|---|---|---|---|
| `default_mode` | `CompressionMode` | `CompressionMode.SIGNATURES` | Default compression mode |
| `exclude_patterns` | `tuple[str, ...]` | `()` | Filename patterns to exclude |
| `max_tokens` | `int \| None` | `None` | Token limit warning threshold |
| `always_include` | `tuple[str, ...]` | `()` | Paths to always include |
| `always_exclude` | `tuple[str, ...]` | `()` | Paths to always exclude |
| `config_path` | `Path \| None` | `None` | Path to the config file |

**Validation Rules:**
- `max_tokens` must be positive if set.
- `default_mode` must be a valid `CompressionMode`.

**Relationships:** Produced by `config.py`, used by all pipeline stages.

**Example Instance:**
```python
config = Config(
    default_mode=CompressionMode.SIGNATURES,
    exclude_patterns=("*_test.py", "migrations/"),
    max_tokens=8000,
    always_include=("src/models/",),
    always_exclude=("src/legacy/",),
    config_path=Path(".shakerrc.json")
)
```

---

### `DeliveryResult`

**Purpose:** Result of the delivery phase (clipboard + file output).

**Fields:**

| Field | Type | Default | Description |
|---|---|---|---|
| `clipboard_success` | `bool` | `False` | Whether clipboard copy succeeded |
| `file_path` | `Path \| None` | `None` | Path to the output file, if written |
| `warnings` | `list[str]` | `[]` | Warnings from delivery |

**Relationships:** Produced by `clipboard.py`, consumed by `cli.py`.

**Example Instance:**
```python
result = DeliveryResult(
    clipboard_success=True,
    file_path=Path("output.md"),
    warnings=[]
)
```

---

### `PipelineState`

**Purpose:** Mutable state container that flows through the pipeline. Each stage reads from and writes to this object.

**Fields:**

| Field | Type | Default | Description |
|---|---|---|---|
| `config` | `Config` | (required) | Application configuration |
| `root_path` | `Path` | `Path.cwd()` | Root path being analyzed |
| `focus` | `str \| None` | `None` | Focus symbol |
| `discovered_files` | `list[Path]` | `[]` | Stage 1 output |
| `parsed_files` | `dict[Path, ParsedFile]` | `{}` | Stage 2 output |
| `call_graph` | `CallGraph \| None` | `None` | Stage 3 output |
| `focus_symbols` | `set[str]` | `set()` | Stage 4 output |
| `focus_files` | `set[Path]` | `set()` | Stage 4 output |
| `pruned_files` | `dict[Path, str]` | `{}` | Stage 5 output |
| `omitted_files` | `list[Path]` | `[]` | Stage 5 output |
| `output` | `str` | `""` | Stage 6 output |
| `delivery` | `DeliveryResult \| None` | `None` | Stage 7 output |
| `stats` | `BuildStats` | `BuildStats()` | Accumulated statistics |
| `warnings` | `list[str]` | `[]` | Accumulated warnings |
| `errors` | `list[str]` | `[]` | Accumulated errors |

**Relationships:** Created by `cli.py`, mutated by every pipeline stage, read by `cli.py` for display.

**Example Instance:**
```python
state = PipelineState(
    config=<Config>,
    root_path=Path("./src"),
    focus="login_user"
)
# After pipeline execution:
# state.discovered_files = [Path("src/auth/login.py"), ...]
# state.parsed_files = {Path("src/auth/login.py"): <ParsedFile>, ...}
# state.call_graph = <CallGraph>
# state.focus_symbols = {"src.auth.login.login_user", ...}
# state.focus_files = {Path("src/auth/login.py"), ...}
# state.pruned_files = {Path("src/auth/login.py"): "def login_user(...): ...", ...}
# state.output = "# Codebase Context\n..."
# state.stats = <BuildStats with reduction_pct=83.8>
```

---

## 9. Development Roadmap

### Phase 0 — Scaffolding (Days 1–2)

**Objective:** Repository setup, build configuration, CI, and test infrastructure.

**Deliverables:**
- `pyproject.toml` with all dependencies, entry points, build config
- `.github/workflows/ci.yml` (ruff + mypy + pytest)
- `src/shaker/__init__.py` — version declaration
- `src/shaker/__main__.py` — `python -m shaker` entry point
- `src/shaker/models.py` — all data models
- `src/shaker/constants.py` — all constants
- `tests/conftest.py` — shared fixtures
- `tests/fixtures/simple_app/` — basic 5-file synthetic project
- `ruff.toml` — linting config
- `mypy.ini` — type checking config
- `LICENSE` (MIT)
- `CONTRIBUTING.md` (template)
- `CHANGELOG.md` (empty, with v1.0 heading)

**Dependencies:** None. This is the foundation.

**Exit Criteria:**
- `pip install -e .` works without errors
- `shaker --help` prints help text (even if it does nothing yet)
- `pytest tests/` runs and passes (0 tests is fine)
- CI passes on GitHub Actions (lint + type check)
- `ruff check .` reports zero issues
- `mypy src/shaker/` reports zero errors

**Risks:** Low. Standard project setup.

**Testing Requirements:** No tests yet. Infrastructure only.

**Estimated Complexity:** Low.

---

### Phase 1 — Discovery + Config (Days 3–5)

**Objective:** File discovery with gitignore support and config loading.

**Deliverables:**
- `engine/discovery.py` — directory walker, gitignore filter
- `infra/config.py` — `.shakerrc.json` loader/validator
- `unit/test_discovery.py` — 15+ tests
- `unit/test_config.py` — 10+ tests
- `tests/fixtures/` — add `.gitignore` files to test fixtures

**Dependencies:** Phase 0 (models, constants).

**Exit Criteria:**
- `shaker ./tests/fixtures/simple_app --dry-run` prints the list of discovered `.py` files
- Gitignore patterns are correctly respected (including negation)
- Config file is loaded and validated with clear error messages
- All unit tests pass
- Coverage: discovery ≥ 90%, config ≥ 90%

**Risks:** Low-Medium. `pathspec` integration is straightforward. Config validation needs careful error messages.

**Testing Requirements:**
- Discovery: 15+ tests covering gitignore, excludes, edge cases
- Config: 10+ tests covering validation, merging, error messages

**Estimated Complexity:** Low-Medium.

---

### Phase 2 — Parser (Days 6–12)

**Objective:** AST parsing that extracts symbols, imports, and calls from Python files.

**Deliverables:**
- `engine/parser.py` — full AST extraction
- `unit/test_parser.py` — 25+ tests
- `tests/fixtures/` — add fixtures for edge cases:
  - Empty files
  - Syntax errors
  - Non-UTF-8 encoding
  - Decorators
  - Async functions
  - Type annotations
  - Relative imports
  - Wildcard imports
  - Walrus operator
  - Match statement
  - F-strings with calls
  - Lambda expressions

**Dependencies:** Phase 0 (models). Phase 1 (discovery provides file list).

**Exit Criteria:**
- Parser correctly extracts all imports, classes, functions, and calls from the simple app fixture
- Parser handles syntax errors gracefully (logs warning, returns partial result)
- Parser handles non-UTF-8 files with `latin-1` fallback
- All unit tests pass
- Coverage: parser ≥ 95%

**Risks:** **High.** This is the most complex single module. Python's AST has many node types. Import tracking (name → module mapping) is fiddly. Call extraction needs to distinguish function calls from method calls from chained attribute access.

**Testing Requirements:** 25+ tests covering all node types, error handling, encoding issues, Python feature coverage.

**Estimated Complexity:** **Very High.**

---

### Phase 3 — Call Graph (Days 13–19)

**Objective:** Build a directed graph of symbol dependencies and resolve focus queries.

**Deliverables:**
- `engine/graph.py` — symbol table + `networkx.DiGraph`
- `engine/resolver.py` — BFS focus resolution, subgraph extraction
- `unit/test_graph.py` — 15+ tests
- `unit/test_resolver.py` — 10+ tests
- `tests/fixtures/circular_imports/` — circular import test fixture

**Dependencies:** Phase 2 (parser provides `ParsedFile` objects).

**Exit Criteria:**
- `shaker ./tests/fixtures/simple_app --focus process_order --dry-run` correctly identifies the 3-hop call graph
- Circular imports do not cause infinite loops
- Unresolvable symbols are handled gracefully (logged, not crashed)
- Focus resolution correctly walks both callers and callees
- All unit tests pass
- Coverage: graph ≥ 90%, resolver ≥ 90%

**Risks:** **High.** Symbol resolution is the hardest problem in the project. `foo.bar()` could be a method call, a module function call, or a chained attribute access. The resolver needs heuristics and must be conservative.

**Testing Requirements:**
- Graph: 15+ tests covering construction, resolution, cycles
- Resolver: 10+ tests covering focus, suggestions, edge cases

**Estimated Complexity:** **High.**

---

### Phase 4 — Pruner (Days 20–25)

**Objective:** AST-based code compression with three modes.

**Deliverables:**
- `engine/pruner.py` — `SignatureTransformer`, `StripTransformer`
- `unit/test_pruner.py` — 20+ tests
- Roundtrip tests: pruned output is valid Python

**Dependencies:** Phase 2 (parser provides AST nodes). Phase 3 (resolver provides focus set).

**Exit Criteria:**
- `--mode signatures` reduces the simple app to signatures-only with all decorators and type annotations preserved
- `--mode strip` removes all docstrings and comments
- `--mode full` preserves source as-is
- Pruned output passes `ast.parse()` (valid Python) — roundtrip guarantee
- All unit tests pass
- Coverage: pruner ≥ 95%

**Risks:** Medium. `ast.NodeTransformer` is well-documented. The main risk is `ast.unparse()` producing unexpected output for edge-case AST nodes.

**Testing Requirements:** 20+ tests covering all modes, roundtrip validity, decorators, async, type annotations, edge cases.

**Estimated Complexity:** Medium.

---

### Phase 5 — Output + Tokens (Days 26–30)

**Objective:** Markdown serialization, token counting, clipboard, and file output.

**Deliverables:**
- `output/serializer.py` — Markdown document builder
- `output/clipboard.py` — clipboard + file output
- `infra/tokens.py` — token counting with `tiktoken` + fallback
- `unit/test_serializer.py` — 10+ tests
- `unit/test_tokens.py` — 5+ tests

**Dependencies:** Phase 4 (pruner provides pruned source). Phase 0 (models for metadata).

**Exit Criteria:**
- Full Markdown output matches the schema from the blueprint
- Token counts are accurate (verified against known values)
- Clipboard works on the dev machine (or degrades gracefully)
- `--output file.md` writes correctly
- All unit tests pass
- Coverage: serializer ≥ 90%, tokens ≥ 85%

**Risks:** Low-Medium. Straightforward string building. Token counting is a thin wrapper.

**Testing Requirements:**
- Serializer: 10+ tests covering output format, tree generation, edge cases
- Tokens: 5+ tests covering counting accuracy, fallback behavior

**Estimated Complexity:** Low-Medium.

---

### Phase 6 — CLI + TUI (Days 31–34)

**Objective:** Wire everything together with Click and Rich.

**Deliverables:**
- `cli.py` — full CLI implementation
- `integration/test_cli.py` — 10+ integration tests
- `integration/test_pipeline.py` — 5+ end-to-end tests

**Dependencies:** All previous phases.

**Exit Criteria:**
- `shaker ./src --focus login_user --mode signatures` produces correct output
- `--help` text is comprehensive and accurate
- Progress bar and summary table display correctly
- All integration tests pass
- Coverage: overall ≥ 85%

**Risks:** Low-Medium. Mostly wiring. The main risk is getting the Click argument definitions right.

**Testing Requirements:**
- CLI: 10+ tests covering argument parsing, error messages, help text
- Pipeline: 5+ tests covering end-to-end workflows

**Estimated Complexity:** Low-Medium.

---

### Phase 7 — Hardening (Days 35–40)

**Objective:** Testing on real projects, documentation, packaging.

**Deliverables:**
- End-to-end tests on 3 real open-source Python projects (Flask, FastAPI auth module, Celery)
- README with installation, usage, examples
- `CHANGELOG.md` with v1.0 entry
- PyPI publishing setup (`twine`, `build`)
- CONTRIBUTING.md with dev environment setup

**Dependencies:** All previous phases.

**Exit Criteria:**
- `pip install codebase-shaker` works from TestPyPI
- README is sufficient for a new user to get value in under 5 minutes
- All tests pass on Python 3.10, 3.11, 3.12, 3.13
- CI passes on Ubuntu, macOS, and Windows
- Overall test coverage ≥ 85%

**Risks:** Low. Mostly documentation and packaging. Real-project testing may reveal edge cases that need fixing.

**Testing Requirements:** Real-project end-to-end tests. Multi-platform CI verification.

**Estimated Complexity:** Low.

---

## 10. File-by-File Implementation Inventory

### `src/shaker/__init__.py`

**Purpose:** Package version declaration.

**Responsibilities:**
- Define the package version as `__version__`

**Classes:** None.

**Functions:** None.

**Dependencies:** None.

**Testing Requirements:** None (trivial).

**Notes:** This is the single source of truth for the package version. All other modules import the version from here.

---

### `src/shaker/__main__.py`

**Purpose:** Enable `python -m shaker` invocation.

**Responsibilities:**
- Import and call the CLI entry point when the package is run as a module

**Classes:** None.

**Functions:**
- `main()` — calls `shaker.cli.cli()`

**Dependencies:** `shaker.cli`

**Testing Requirements:** None (trivial).

**Notes:** Must be a thin wrapper. No logic.

---

### `src/shaker/models.py`

**Purpose:** All shared data models. The foundation of the architecture.

**Responsibilities:**
- Define every dataclass and enum used across the codebase
- Zero business logic — pure data containers

**Classes:**
- `CompressionMode(Enum)` — `FULL`, `SIGNATURES`, `STRIP`
- `SymbolType(Enum)` — `MODULE`, `CLASS`, `FUNCTION`, `METHOD`
- `ImportInfo(frozen dataclass)` — import statement record
- `CallSite(frozen dataclass)` — function/method call site
- `Symbol(frozen dataclass)` — named entity
- `ParsedFile(dataclass)` — parsed file result
- `CallGraph(dataclass)` — dependency graph wrapper
- `BuildStats(dataclass)` — build statistics
- `OutputMetadata(dataclass)` — output metadata
- `Config(dataclass)` — application configuration
- `DeliveryResult(dataclass)` — delivery result
- `PipelineState(dataclass)` — pipeline state container

**Functions:** None (data only).

**Dependencies:** `dataclasses`, `enum`, `pathlib`, `typing`, `typing_extensions`, `networkx` (for `CallGraph.graph` type annotation only — use `TYPE_CHECKING` guard).

**Testing Requirements:** Models are tested indirectly through every other module's tests.

**Notes:** This file must NOT import from any other `shaker` module. It is the foundation.

---

### `src/shaker/constants.py`

**Purpose:** Shared constants.

**Responsibilities:**
- Define all magic values, defaults, and lookup tables

**Classes:** None.

**Functions:** None.

**Dependencies:** `shaker.models` (for `CompressionMode` type annotation).

**Testing Requirements:** Trivial module, tested indirectly.

**Notes:** `BUILTIN_NAMES` and `STDLIB_MODULES` are large frozensets. Consider generating them programmatically at module load time rather than hardcoding.

---

### `src/shaker/cli.py`

**Purpose:** CLI entry point. The composition root.

**Responsibilities:**
- Define Click commands and options
- Orchestrate the full pipeline
- Display results via Rich
- Handle errors gracefully

**Classes:**
- None (uses Click decorators on functions)

**Functions:**
- `cli()` — Click command group (entry point, decorated with `@click.command()`)
- `run_pipeline(path, focus, mode, output, no_clipboard, max_tokens, exclude, config_path, verbose, dry_run)` — orchestrates the full pipeline
- `display_results(state: PipelineState)` — Rich output formatting
- `handle_error(error: Exception)` — user-friendly error messages

**Dependencies:** All shaker packages, `click`, `rich`

**Testing Requirements:** Tested via `integration/test_cli.py` using Click's `CliRunner`.

**Notes:** This is the only module that imports from all other packages. Keep it thin — no business logic.

---

### `src/shaker/engine/__init__.py`

**Purpose:** Re-exports the public engine API.

**Responsibilities:**
- Provide a clean import surface for the engine package

**Classes:** None.

**Functions (re-exported):**
- `discover_files()` from `discovery.py`
- `parse_files()` from `parser.py`
- `build_graph()` from `graph.py`
- `resolve_focus()` from `resolver.py`
- `prune_files()` from `pruner.py`

**Dependencies:** All engine submodules.

**Testing Requirements:** None.

**Notes:** Only re-export public API functions. Internal helpers stay internal.

---

### `src/shaker/engine/discovery.py`

**Purpose:** Stage 1 — File discovery with gitignore support.

**Responsibilities:**
- Walk a directory tree to find `.py` files
- Filter by `.gitignore` rules
- Apply `--exclude` patterns
- Return a sorted list of `Path` objects

**Classes:** None.

**Functions:**
- `discover_files(path: Path, config: Config) -> list[Path]` — main entry point
- `_walk_directory(path: Path) -> Iterator[Path]` — recursive walker (internal)
- `_matches_exclude(file: Path, patterns: list[str]) -> bool` — glob matching (internal)
- `_load_gitignore(path: Path) -> pathspec.PathSpec | None` — gitignore loader (internal)

**Dependencies:** `pathlib`, `pathspec`, `shaker.models`, `shaker.constants`

**Testing Requirements:** 15+ unit tests:
- Directory with no `.py` files → empty list
- Directory with `.py` files → returns all
- `.gitignore` with `*.pyc` → `.pyc` files excluded
- `.gitignore` with `tests/` → test directory excluded
- `.gitignore` with negation (`!important.py`) → negation respected
- Nested `.gitignore` files → both respected
- `--exclude "*_test.py"` → test files excluded
- `--exclude` with multiple patterns → all respected
- Symlinks → not followed
- Single file input → returns `[path]`
- Nonexistent path → raises `FileNotFoundError`
- `__pycache__` → excluded
- `.git` directory → excluded
- Mixed valid/invalid → only valid returned
- Hidden directories (`.venv`) → excluded via gitignore
- Very deep nesting → handled without recursion limit issues
- Permission denied → warning, skip

**Notes:** Always return sorted results for deterministic output.

---

### `src/shaker/engine/parser.py`

**Purpose:** Stage 2 — AST parsing and symbol extraction.

**Responsibilities:**
- Parse Python files into AST
- Extract imports, classes, functions, methods, and calls
- Build `ParsedFile` objects
- Handle parse errors gracefully

**Classes:**
- `SymbolExtractor(ast.NodeVisitor)` — walks the AST and extracts all symbols (internal)

**Functions:**
- `parse_files(files: list[Path], config: Config) -> dict[Path, ParsedFile]` — parse all files
- `parse_file(path: Path) -> ParsedFile` — parse a single file
- `_extract_imports(tree: ast.Module) -> list[ImportInfo]` — extract import nodes (internal)
- `_extract_classes(tree: ast.Module, module_name: str) -> list[Symbol]` — extract class definitions (internal)
- `_extract_functions(tree: ast.Module, module_name: str) -> list[Symbol]` — extract function definitions (internal)
- `_extract_calls(body: list[ast.stmt], scope: str) -> list[CallSite]` — extract call sites (internal)
- `_resolve_module_name(path: Path, root: Path) -> str` — convert file path to dotted module name (internal)
- `_is_builtin(name: str) -> bool` — check if a name is a Python builtin (internal)
- `_is_stdlib(module: str) -> bool` — check if a module is stdlib (internal)

**Dependencies:** `ast`, `pathlib`, `shaker.models`, `shaker.constants`

**Testing Requirements:** 25+ unit tests:
- Empty file → empty `ParsedFile`
- File with only imports → imports extracted, no symbols
- File with one class → class extracted with methods
- File with nested classes → all extracted with correct qualified names
- File with decorators → decorators preserved in symbol metadata
- File with type annotations → annotations preserved
- File with async functions → extracted correctly
- File with syntax error → `ParsedFile` with error flag, no crash
- File with non-UTF-8 encoding → `latin-1` fallback
- File with `*` import → recorded as wildcard import
- File with relative import → recorded with relative module path
- File with `from __future__ import annotations` → handled correctly
- File with `@property`, `@staticmethod`, `@classmethod` → decorators preserved
- File with `if TYPE_CHECKING:` block → imports inside recorded
- File with walrus operator → parsed correctly
- File with match statement → parsed correctly
- Very large file (1000+ lines) → parsed without issue
- File with only comments → empty `ParsedFile`
- File with docstring only → module docstring recorded
- File with f-strings containing calls → calls extracted
- File with lambda → lambda body calls extracted (or documented as limitation)

**Notes:** This is the most complex module. The `SymbolExtractor` visitor needs to handle all Python AST node types. Use a `try/except` around `ast.parse()` to handle syntax errors gracefully.

---

### `src/shaker/engine/graph.py`

**Purpose:** Stage 3 — Call graph construction.

**Responsibilities:**
- Build a symbol table from parsed files
- Construct a `networkx.DiGraph` of symbol dependencies
- Handle unresolvable symbols gracefully
- Detect cycles

**Classes:** None.

**Functions:**
- `build_graph(parsed: dict[Path, ParsedFile]) -> CallGraph` — build the full call graph
- `get_callers(graph: CallGraph, symbol: str) -> set[str]` — get all callers of a symbol
- `get_callees(graph: CallGraph, symbol: str) -> set[str]` — get all callees of a symbol
- `_build_symbol_table(parsed: dict[Path, ParsedFile]) -> dict[str, Symbol]` — build symbol table (internal)
- `_resolve_call(call: CallSite, imports: list[ImportInfo], symbol_table: dict[str, Symbol]) -> str | None` — resolve a call (internal)
- `_detect_cycles(graph: nx.DiGraph) -> list[list[str]]` — detect cycles (internal)

**Dependencies:** `networkx`, `shaker.models`

**Testing Requirements:** 15+ unit tests:
- Empty parsed dict → empty graph
- Single file, no calls → graph with nodes, no edges
- Single file, one call → graph with one edge
- Cross-file call → edge between files
- Unresolvable call → no edge, logged in `unresolved_calls`
- Circular call (A→B→A) → cycle detected, no infinite loop
- Diamond dependency (A→B, A→C, B→D, C→D) → correct graph
- Multiple functions with same name in different modules → disambiguated
- Call to builtin → no edge (filtered)
- Call to stdlib → no edge (filtered)
- Wildcard import → all symbols from module potentially reachable
- Very large graph (1000+ nodes) → builds in < 1 second

**Notes:** The `_resolve_call` function is the core heuristic. It should be conservative: if unsure, return `None` (unresolved) rather than guessing wrong.

---

### `src/shaker/engine/resolver.py`

**Purpose:** Stage 4 — Focus resolution and subgraph extraction.

**Responsibilities:**
- Given a focal symbol, extract the relevant subgraph
- Handle missing focus gracefully with suggestions
- Map symbols back to files

**Classes:** None.

**Functions:**
- `resolve_focus(graph: CallGraph, focus: str) -> set[str]` — get the focus set
- `resolve_focus_files(focus_symbols: set[str], parsed: dict[Path, ParsedFile]) -> set[Path]` — map symbols to files
- `suggest_symbols(graph: CallGraph, query: str, limit: int = 10) -> list[str]` — suggest symbols for `--focus` when not found
- `_bfs(graph: nx.DiGraph, start: str, direction: str) -> set[str]` — BFS traversal (internal)
- `_fuzzy_match(query: str, candidates: list[str], limit: int) -> list[str]` — fuzzy matching (internal)

**Dependencies:** `networkx`, `shaker.models`

**Testing Requirements:** 10+ unit tests:
- Focus on leaf node → only that node + callers
- Focus on root node → full downstream graph
- Focus on middle node → both directions
- Focus not found → suggestions returned
- Focus with multiple matches → all returned with disambiguation
- Empty graph → empty focus set
- Focus on symbol in cycle → terminates correctly

**Notes:** Use `networkx.descendants()` for callees and `networkx.ancestors()` for callers. The fuzzy matching can use `difflib.get_close_matches()` from the standard library.

---

### `src/shaker/engine/pruner.py`

**Purpose:** Stage 5 — AST-based code compression.

**Responsibilities:**
- Apply compression modes to parsed files
- Preserve focus files at full detail
- Ensure pruned output is valid Python

**Classes:**
- `SignatureTransformer(ast.NodeTransformer)` — replaces function bodies with `...` (internal)
- `StripTransformer(ast.NodeTransformer)` — removes docstrings and comments (internal)

**Functions:**
- `prune_files(parsed: dict[Path, ParsedFile], focus_files: set[Path], mode: CompressionMode) -> dict[Path, str]` — prune all files
- `_prune_file(parsed: ParsedFile, mode: CompressionMode) -> str` — prune a single file (internal)
- `_remove_comments(source: str) -> str` — strip `#` comment lines (internal)
- `_is_docstring(node: ast.stmt) -> bool` — check if a node is a docstring (internal)

**Dependencies:** `ast`, `shaker.models`, `shaker.constants`

**Testing Requirements:** 20+ unit tests:
- `full` mode → output identical to input
- `signatures` mode → all function bodies replaced with `...`
- `signatures` mode → decorators preserved
- `signatures` mode → type annotations preserved
- `signatures` mode → default arguments preserved
- `signatures` mode → class definitions preserved with method signatures
- `signatures` mode → module-level code preserved
- `strip` mode → docstrings removed
- `strip` mode → comments removed
- `strip` mode → code bodies preserved
- Roundtrip: pruned output → `ast.parse()` succeeds
- Empty file → empty output
- File with only imports → imports preserved
- File with only a class → class signature preserved
- File with decorators → decorators preserved in signatures mode
- File with async functions → handled correctly
- File with `*args, **kwargs` → preserved
- File with keyword-only args → preserved
- File with positional-only args → preserved

**Notes:** The roundtrip test is critical. Every pruned output must be valid Python. If `ast.unparse()` fails for any reason, fall back to the original source with a warning.

---

### `src/shaker/output/__init__.py`

**Purpose:** Re-exports the public output API.

**Responsibilities:**
- Provide a clean import surface for the output package

**Classes:** None.

**Functions (re-exported):**
- `serialize()` from `serializer.py`
- `deliver()` from `clipboard.py`

**Dependencies:** `shaker.output.serializer`, `shaker.output.clipboard`

**Testing Requirements:** None.

---

### `src/shaker/output/serializer.py`

**Purpose:** Stage 6 — Markdown document construction.

**Responsibilities:**
- Build the Markdown output document from pruned files and metadata
- Generate the ASCII file tree
- Format per-file sections
- Generate the omission notice

**Classes:** None.

**Functions:**
- `serialize(pruned: dict[Path, str], metadata: OutputMetadata, focus_files: set[Path], omitted_files: list[Path]) -> str` — build the full Markdown document
- `_build_header(metadata: OutputMetadata) -> str` — build the header section (internal)
- `_build_tree(files: list[Path], focus_files: set[Path], omitted: list[Path]) -> str` — build the file tree (internal)
- `_build_file_section(path: Path, source: str, is_focus: bool, mode: CompressionMode) -> str` — build a single file's section (internal)
- `_build_omitted_notice(omitted: list[Path]) -> str` — build the omission notice (internal)

**Dependencies:** `shaker.models`, `shaker.constants`

**Testing Requirements:** 10+ unit tests:
- Header contains correct metadata
- File tree is correctly formatted
- Focus files marked with `← FOCUS PATH`
- Omitted files listed in notice
- Per-file sections have correct language tags
- Empty pruned dict → minimal valid Markdown
- Large number of files → tree is compact/readable
- Unicode in file paths → handled correctly
- Very long file paths → tree formatting doesn't break

**Notes:** Use a list-of-strings pattern for building the output (append to list, `"\n".join()` at the end) for efficiency.

---

### `src/shaker/output/clipboard.py`

**Purpose:** Stage 7 — Output delivery (clipboard + file).

**Responsibilities:**
- Copy output to clipboard
- Write output to file
- Handle errors gracefully

**Classes:** None.

**Functions:**
- `deliver(content: str, output_path: Path | None, copy_to_clipboard: bool) -> DeliveryResult` — deliver the output
- `_copy_to_clipboard(content: str) -> bool` — clipboard operation with fallback (internal)
- `_write_to_file(content: str, path: Path) -> None` — file write (internal)

**Dependencies:** `pyperclip` (optional), `shaker.models`

**Testing Requirements:** 6+ unit tests:
- Clipboard copy succeeds → `DeliveryResult(clipboard=True)`
- Clipboard unavailable → `DeliveryResult(clipboard=False)`, no crash
- File write succeeds → file exists with correct content
- File write to nonexistent directory → creates directories
- File write to read-only path → error message
- Both clipboard and file → both succeed

**Notes:** Wrap `pyperclip` import in `try/except`. If unavailable, `_copy_to_clipboard` returns `False` with a warning.

---

### `src/shaker/infra/__init__.py`

**Purpose:** Re-exports the public infra API.

**Responsibilities:**
- Provide a clean import surface for the infra package

**Classes:** None.

**Functions (re-exported):**
- `load_config()` from `config.py`
- `count_tokens()` from `tokens.py`

**Dependencies:** `shaker.infra.config`, `shaker.infra.tokens`

**Testing Requirements:** None.

---

### `src/shaker/infra/config.py`

**Purpose:** Configuration loading and validation.

**Responsibilities:**
- Load `.shakerrc.json`
- Validate config values
- Merge config with CLI arguments (CLI wins)
- Provide default values

**Classes:** None.

**Functions:**
- `load_config(path: Path | None = None) -> Config` — load and validate config
- `merge_config_with_cli(config: Config, cli_args: dict) -> Config` — CLI overrides config
- `_validate_mode(mode: str) -> CompressionMode` — validate mode string (internal)
- `_validate_patterns(patterns: list[str]) -> list[str]` — validate glob patterns (internal)
- `_find_config_file(path: Path) -> Path | None` — search for `.shakerrc.json` (internal)

**Dependencies:** `json`, `pathlib`, `shaker.models`, `shaker.constants`

**Testing Requirements:** 10+ unit tests:
- Valid config file → correct `Config` object
- Missing config file → default `Config`
- Invalid mode → clear error message
- Invalid JSON → clear error message
- Config with all fields → all loaded
- Config with partial fields → defaults filled in
- CLI arg overrides config → CLI wins
- Config file discovery → searches upward from cwd
- Config with unknown fields → warning, not error
- Config with negative max_tokens → validation error

**Notes:** Config file search should walk up from the target directory to the filesystem root, stopping at the first `.shakerrc.json` found.

---

### `src/shaker/infra/tokens.py`

**Purpose:** Token counting.

**Responsibilities:**
- Count tokens using `tiktoken` (if available)
- Provide fallback estimation

**Classes:** None.

**Functions:**
- `count_tokens(text: str) -> int` — count tokens
- `estimate_tokens(text: str) -> int` — estimate without tiktoken
- `_get_encoder() -> tiktoken.Encoding | None` — lazy-load encoder (internal)

**Dependencies:** `tiktoken` (optional), `shaker.constants`

**Testing Requirements:** 5+ unit tests:
- Empty string → 0 tokens
- Known string → correct count
- tiktoken unavailable → fallback estimation
- Very long string → counts without error
- Unicode text → counted correctly

**Notes:** Wrap `tiktoken` import in `try/except`. If unavailable, `_get_encoder` returns `None` and `count_tokens` falls back to `estimate_tokens`.

---

### `tests/conftest.py`

**Purpose:** Shared test fixtures.

**Responsibilities:**
- Provide pytest fixtures used across test modules
- Set up test data (fixture paths, parsed files, graphs)

**Classes:** None.

**Functions (fixtures):**
- `simple_app_path() -> Path` — path to the simple app fixture (session scope)
- `simple_app_files(simple_app_path) -> list[Path]` — discovered files (session scope)
- `simple_app_parsed(simple_app_files) -> dict[Path, ParsedFile]` — parsed simple app (session scope)
- `simple_app_graph(simple_app_parsed) -> CallGraph` — built graph (session scope)
- `default_config() -> Config` — default config (function scope)
- `temp_output_dir() -> Path` — temporary directory (function scope, auto-cleanup)

**Dependencies:** All shaker packages, `pytest`, `tempfile`, `shutil`

**Testing Requirements:** Fixtures are tested indirectly by all test modules.

**Notes:** Use `session` scope for expensive fixtures (parsing, graph building). Use `function` scope for mutable state.

---

### `tests/integration/test_pipeline.py`

**Purpose:** End-to-end pipeline tests.

**Responsibilities:**
- Test the full pipeline from CLI args to output
- Verify integration between all modules

**Test Cases:**
- Full pipeline, no focus, signatures mode
- Full pipeline, with focus, signatures mode
- Full pipeline, strip mode
- Full pipeline, full mode
- Pipeline with syntax error files → warnings in output
- Pipeline with circular imports → no infinite loop
- Pipeline with nonexistent focus → error with suggestions
- Pipeline with exclude patterns → excluded files not in output
- Pipeline with output file → file written correctly
- Pipeline with max-tokens exceeded → warning displayed
- Pipeline with single file input → works without graph
- Pipeline with all files omitted → empty output with notice

**Dependencies:** All shaker packages

**Notes:** These are the most valuable tests. They catch integration issues that unit tests miss. Run them with `pytest tests/integration/ -v`.

---

### `tests/integration/test_cli.py`

**Purpose:** CLI invocation tests.

**Responsibilities:**
- Test CLI argument parsing and error handling
- Verify help text, version output, and error messages

**Test Cases:**
- `--help` → exits 0, prints comprehensive help
- `--version` → prints version string
- No arguments → error with usage hint
- Invalid path → error with "path not found" message
- Invalid mode → error with valid modes listed
- Valid invocation → exits 0
- `--dry-run` → no clipboard, no file output
- `--no-clipboard` → no clipboard attempt
- `--output file.md` → file created with correct content
- `--focus nonexistent` → error with suggestions
- `--verbose` → extra output on stderr
- `--quiet` → minimal output
- Piping output → stdout contains Markdown

**Dependencies:** `click.testing.CliRunner`, `shaker.cli`

**Notes:** Use Click's `CliRunner` for isolated CLI testing. Test both exit codes and output content.

---

## 11. Dependency Review

### `ast` (stdlib)

**Purpose:** Python AST parsing and transformation.

**Why Chosen:** Standard library. No alternative for Python AST parsing.

**Alternatives Considered:** `lib2to3` (deprecated), `parso` (Jedi's parser, third-party), `tree-sitter` (multi-language but heavy).

**Risks:** `ast.unparse()` was added in 3.9 and has had edge-case bugs in early releases. Target Python 3.10+ for stability.

**Final Decision:** ✅ Keep (stdlib). No installation required.

---

### `pathlib` (stdlib)

**Purpose:** Modern path handling.

**Why Chosen:** Standard library. Replaces `os.path`.

**Alternatives Considered:** `os.path` (legacy), `path` (third-party, Matthew Wright).

**Risks:** None.

**Final Decision:** ✅ Keep (stdlib).

---

### `dataclasses` (stdlib)

**Purpose:** Clean data models with minimal boilerplate.

**Why Chosen:** Standard library since Python 3.7. Perfect for pure data containers.

**Alternatives Considered:** `attrs` (third-party, more features), `pydantic` (third-party, validation), `NamedTuple` (stdlib, immutable only).

**Risks:** None.

**Final Decision:** ✅ Keep (stdlib). Use `frozen=True` for immutable models.

---

### `click`

**Purpose:** CLI argument parsing and command definition.

**Why Chosen:** Best-in-class CLI framework for Python. Clean decorator API, automatic help generation, excellent testing support via `CliRunner`.

**Alternatives Considered:**
- `argparse` (stdlib) — More verbose, no automatic help formatting, harder to test.
- `typer` (third-party) — Built on click, more modern with type inference. Slightly heavier dependency chain.
- `fire` (Google) — Too magical, poor control over help text.

**Risks:** None significant. Mature, well-maintained library.

**Final Decision:** ✅ Keep. Best balance of features, ergonomics, and ecosystem support.

---

### `networkx`

**Purpose:** Call graph data structure and algorithms (DiGraph, BFS, DFS, cycle detection).

**Why Chosen:** Provides graph algorithms out of the box. `descendants()`, `ancestors()`, `simple_cycles()` are exactly what we need.

**Alternatives Considered:**
- `dict[str, set[str]]` adjacency list — Lightweight, no dependency. Would need to implement BFS/DFS/cycle detection manually (~200 lines).
- `igraph` — Faster for large graphs, but C dependency complicates installation.
- `graph-tool` — Very fast, but complex installation.

**Risks:** ~5MB dependency. For v1's scope (single-language, single-process), this is acceptable. Could be replaced with a lightweight alternative in v2 if distribution size matters.

**Final Decision:** ✅ Keep for v1. The development time saved outweighs the dependency weight. Re-evaluate for v2.

---

### `rich`

**Purpose:** Terminal UI (progress bars, tables, colors, formatting).

**Why Chosen:** Best TUI library for Python. Tables, progress bars, syntax highlighting, all with minimal code. Beautiful output with zero configuration.

**Alternatives Considered:**
- `curses` (stdlib) — Low-level, complex, Unix-only.
- `blessed` — Lower-level than rich, less featureful.
- `colorama` — Colors only, no tables or progress bars.
- Manual ANSI codes — Fragile, hard to maintain.

**Risks:** None. Pure Python, well-maintained, minimal dependencies.

**Final Decision:** ✅ Keep. No competition for this use case.

---

### `tiktoken`

**Purpose:** Accurate token counting using OpenAI's tokenizer.

**Why Chosen:** Provides accurate token counts compatible with GPT-4/Claude tokenization. Works offline after initial download.

**Alternatives Considered:**
- `chars // 4` fallback — Simple estimation, no dependency. Accuracy: ±20%.
- `transformers` (Hugging Face) — Supports many tokenizers, but ~500MB+ dependency.
- Custom tokenizer — Significant development effort, unlikely to match OpenAI's accuracy.

**Risks:** ~2MB download for tokenizer data. Some users may have limited internet access. Install can fail in restricted environments.

**Final Decision:** ⚠️ Make optional. Use `try: import tiktoken` with graceful fallback to `len(text) // 4`. Document that token counts are estimates without tiktoken.

---

### `pyperclip`

**Purpose:** Cross-platform clipboard access.

**Why Chosen:** Simple API for copying text to clipboard on macOS, Windows, and Linux.

**Alternatives Considered:**
- `pyclip` — Similar functionality, less maintained.
- Platform-specific commands (`pbcopy`, `xclip`, `clip.exe`) — More code, but no dependency.

**Risks:** Fails on headless Linux without `xclip` or `wl-clipboard`. Can crash without a display server.

**Final Decision:** ⚠️ Make optional. Wrap in `try/except`. If unavailable, print a notice and continue. Never crash.

---

### `pathspec`

**Purpose:** `.gitignore` rule parsing and matching.

**Why Chosen:** Correctly implements the full gitignore specification including negation patterns, nested `.gitignore` files, and directory-specific rules.

**Alternatives Considered:**
- Manual glob matching — Gets edge cases wrong (negation, `**`, directory-only patterns).
- `gitignore-parser` (third-party) — Less maintained, fewer features.

**Risks:** None. Small, pure-Python library.

**Final Decision:** ✅ Keep. Correct solution for the problem.

---

### `typing_extensions`

**Purpose:** Backported type hints for Python < 3.11.

**Why Chosen:** Provides `Self`, `TypeAlias`, `Required`, `NotRequired`, `Unpack`, and other modern type hints on older Python versions.

**Alternatives Considered:**
- Only use types available in the minimum Python version — Limits expressiveness.
- `typing_extensions` is already a transitive dependency of many libraries.

**Risks:** None. Minimal, well-maintained library from the Python typing team.

**Final Decision:** ✅ Add. Use `from typing_extensions import Self, TypeAlias` etc.

---

### `pytest` (dev)

**Purpose:** Test runner.

**Why Chosen:** Standard test runner for Python. Fixtures, parametrize, markers, plugins.

**Alternatives Considered:** `unittest` (stdlib) — More verbose, fewer features. `nose2` — Less popular.

**Risks:** None.

**Final Decision:** ✅ Keep (dev dependency).

---

### `pytest-cov` (dev)

**Purpose:** Test coverage reporting.

**Why Chosen:** Standard coverage plugin for pytest. Integrates with CI.

**Alternatives Considered:** `coverage.py` directly — More configuration, less integrated.

**Risks:** None.

**Final Decision:** ✅ Keep (dev dependency).

---

### `pytest-mock` (dev)

**Purpose:** Mocking fixture for pytest.

**Why Chosen:** Provides `mocker` fixture that auto-cleans mocks. Reduces boilerplate vs `unittest.mock`.

**Alternatives Considered:** `unittest.mock` (stdlib) — Works fine, more verbose. `pytest-monkeypatch` — Built into pytest, but different use case.

**Risks:** None.

**Final Decision:** ✅ Add (dev dependency).

---

### `ruff` (dev)

**Purpose:** Linting and formatting.

**Why Chosen:** Replaces `flake8` + `black` + `isort` + `pyupgrade` in one tool. 10-100x faster than the alternatives. Zero config needed for most cases.

**Alternatives Considered:**
- `flake8` + `black` + `isort` — Three tools, slower, more config.
- `pylint` — More thorough but much slower, more false positives.
- `pyright` — Type checking, not linting.

**Risks:** None. Rapidly becoming the Python standard.

**Final Decision:** ✅ Add (dev dependency). Sole linting/formatting tool.

---

### `mypy` (dev)

**Purpose:** Static type checking.

**Why Chosen:** Catches type errors before runtime. Critical for a project with many dataclasses and complex data flow.

**Alternatives Considered:**
- `pyright` / `pylance` — Faster, but VS Code-specific. Good as a secondary check.
- `pytype` (Google) — Different approach, less popular.

**Risks:** Can be strict. May need configuration to avoid false positives.

**Final Decision:** ✅ Add (dev dependency). Run in CI.

---

## 12. Testing Architecture

### Testing Philosophy

**Three layers of testing:**

1. **Unit tests** — Test each module in isolation. Mock dependencies. Fast (< 100ms per test). High coverage.
2. **Integration tests** — Test the full pipeline end-to-end. Use real fixture codebases. Slower (< 5s per test). Catch integration issues.
3. **Fixture-based tests** — Real synthetic Python projects that exercise specific features. Not mocked AST objects — actual `.py` files.

**Testing principles:**
- Every public function has at least one test.
- Every edge case identified in the blueprint has a test.
- Every error path has a test.
- Tests are deterministic — no randomness, no network, no time dependence.
- Tests are isolated — no shared mutable state between tests.

### Unit Testing Strategy

**Scope:** One test file per source module. Tests each module in isolation with mocked dependencies.

**Test file mapping:**

| Source Module | Test File | Min Tests |
|---|---|---|
| `engine/discovery.py` | `unit/test_discovery.py` | 15 |
| `engine/parser.py` | `unit/test_parser.py` | 25 |
| `engine/graph.py` | `unit/test_graph.py` | 15 |
| `engine/resolver.py` | `unit/test_resolver.py` | 10 |
| `engine/pruner.py` | `unit/test_pruner.py` | 20 |
| `output/serializer.py` | `unit/test_serializer.py` | 10 |
| `infra/config.py` | `unit/test_config.py` | 10 |
| `infra/tokens.py` | `unit/test_tokens.py` | 5 |

**Total minimum unit tests: 110**

**Coverage goals:**

| Module | Minimum Coverage | Target Coverage |
|---|---|---|
| `parser.py` | 90% | 95% |
| `pruner.py` | 90% | 95% |
| `graph.py` | 85% | 90% |
| `resolver.py` | 85% | 90% |
| `discovery.py` | 85% | 90% |
| `serializer.py` | 85% | 90% |
| `config.py` | 85% | 90% |
| `tokens.py` | 80% | 85% |
| **Overall** | **85%** | **90%** |

### Integration Testing Strategy

**Scope:** End-to-end tests that run the full pipeline. Use Click's `CliRunner` for CLI tests. Use real fixture codebases for pipeline tests.

**Test files:**

| Test File | Min Tests | Focus |
|---|---|---|
| `integration/test_cli.py` | 10 | CLI invocation, argument parsing, error messages |
| `integration/test_pipeline.py` | 10 | Full pipeline, end-to-end workflows |

**Total minimum integration tests: 20**

### Fixture Design

Each fixture is a real Python project with actual files, committed to the repo. Fixtures are organized by what they test:

| Fixture | Purpose | Files | Key Features |
|---|---|---|---|
| `simple_app/` | Basic parsing, graph, pruning | 5-10 | Clean code, clear call graph |
| `circular_imports/` | Circular dependency handling | 2-3 | Circular imports between modules |
| `syntax_errors/` | Error handling | 2-3 | Mix of valid and broken files |
| `dynamic_patterns/` | Dynamic Python patterns | 3-4 | `getattr`, `eval`, dynamic dispatch |
| `edge_cases/` | Python feature coverage | 5-8 | Async, decorators, walrus, match, type annotations, lambdas |
| `large_app/` | Performance testing | 50+ | Generated files for perf benchmarks |

**Fixture conventions:**
- Each fixture is a valid Python package with `__init__.py`.
- Each fixture has a `README.md` describing its structure and call graph.
- Fixtures are immutable — tests never modify fixture files.
- New fixtures are added when new edge cases are discovered.

### Regression Testing

**Strategy:**
- All fixtures are committed to the repo. Any change that breaks a fixture's expected output is a regression.
- Snapshot tests for the serializer: record expected output, compare in CI.
- Milestone tests: at each milestone, run the full test suite and record results.

**Snapshot approach:**
- For each fixture, store the expected output in `tests/snapshots/`.
- On test run, compare actual output to snapshot.
- If output changes intentionally, update the snapshot with `--update-snapshots` flag.

### CI Testing

**GitHub Actions workflow:**

```yaml
# .github/workflows/ci.yml
strategy:
  matrix:
    os: [ubuntu-latest, macos-latest, windows-latest]
    python-version: ["3.10", "3.11", "3.12", "3.13"]
```

**CI steps:**
1. Lint: `ruff check .`
2. Format check: `ruff format --check .`
3. Type check: `mypy src/shaker/`
4. Unit tests: `pytest tests/unit/ -v --cov=src/shaker --cov-report=xml`
5. Integration tests: `pytest tests/integration/ -v`
6. Coverage check: `pytest --cov-fail-under=85`

### Edge-Case Coverage

The following edge cases must have dedicated tests:

| Edge Case | Test Location | Description |
|---|---|---|
| Empty file | `test_parser.py` | File with zero bytes |
| Syntax error | `test_parser.py` | File with invalid Python |
| Non-UTF-8 encoding | `test_parser.py` | File with `latin-1` encoding |
| Circular imports | `test_graph.py` | A imports B, B imports A |
| Dynamic attribute access | `test_graph.py` | `getattr(obj, name)()` |
| Wildcard imports | `test_parser.py` | `from foo import *` |
| Relative imports | `test_parser.py` | `from . import foo` |
| `*` imports in graph | `test_graph.py` | Wildcard import resolution |
| Very large file | `test_parser.py` | 1000+ line file |
| Very deep directory | `test_discovery.py` | 10+ levels of nesting |
| Permission denied | `test_discovery.py` | Unreadable directory |
| Symlink | `test_discovery.py` | Symlinked directory |
| Focus not found | `test_resolver.py` | Nonexistent focus symbol |
| Focus with multiple matches | `test_resolver.py` | Ambiguous focus |
| Empty graph | `test_resolver.py` | No symbols in graph |
| Pruned output validity | `test_pruner.py` | `ast.parse(pruned_output)` succeeds |
| Config validation | `test_config.py` | Invalid config values |
| Config merging | `test_config.py` | CLI overrides config |
| Clipboard unavailable | `test_cli.py` | No crash when clipboard fails |
| Output to file | `test_cli.py` | File written correctly |
| Max tokens exceeded | `test_cli.py` | Warning displayed |

---

## 13. Risk Analysis

### Technical Risks

| Risk | Description | Impact | Likelihood | Mitigation Strategy | Contingency Plan |
|---|---|---|---|---|---|
| **Dynamic Python patterns break static analysis** | `getattr`, `eval`, `exec`, monkey-patching cannot be resolved statically. The call graph will have false negatives. | High | Certain | Document limitation clearly. Preserve functions containing dynamic patterns in full (mode=full override). Never crash on dynamic patterns. | If false negatives are too aggressive, add a `--safe-mode` flag that preserves all functions with any dynamic pattern. |
| **`ast.unparse()` produces ugly or invalid output** | `ast.unparse()` (Python 3.9+) can produce unexpected formatting or fail on edge-case AST nodes. | Medium | Medium | Roundtrip test: every pruned output must pass `ast.parse()`. If `ast.unparse()` fails, fall back to original source with a warning. | If `ast.unparse()` is unreliable, switch to a source-level approach (regex-based comment removal, line-based signature extraction). |
| **Call graph has too many false positives** | Conservative resolution may include edges that don't exist at runtime, bloating the output. | Medium | High | Accept false positives as a design choice. Document that the graph is an approximation. Focus on reducing false negatives (missing real edges). | Add a `--strict-mode` that only includes edges with high confidence. |
| **Performance on large codebases** | 10,000+ file projects could cause memory issues or slow processing. | Low | Medium | Profile early with `large_app` fixture. Set performance budget: 3s for 500 files. Use efficient data structures. | Add `--max-files` limit. Add progress indication for long-running operations. Consider parallel parsing with `multiprocessing`. |
| **Python version compatibility** | AST node types and `ast.unparse()` behavior change between Python versions. | Medium | Medium | Target Python 3.10+. Test on 3.10, 3.11, 3.12, 3.13 in CI. Use `typing_extensions` for backports. | Pin minimum Python version. Document known issues per version. |
| **Circular imports cause infinite loops** | If the graph traversal doesn't handle cycles, it could loop forever. | High | Low | `networkx` provides cycle detection. Test with `circular_imports` fixture. Use `visited` set in all traversals. | Add a traversal depth limit as a safety net. |

### Architecture Risks

| Risk | Description | Impact | Likelihood | Mitigation Strategy | Contingency Plan |
|---|---|---|---|---|---|
| **Tight coupling between parser and graph** | If the parser's output format changes, the graph builder breaks. | Medium | Medium | The parser outputs `ParsedFile` (pure data). The graph builder consumes `ParsedFile`. No shared state. This boundary is clean and tested. | Add a validation layer between parser and graph that checks `ParsedFile` integrity. |
| **Output format changes break users** | If the Markdown schema changes, users' LLM prompts may break. | Low | Medium | Version the output format. Include `Tool: Codebase Shaker v1.0` in the header. Follow semantic versioning. | Add `--format-version` flag for backward compatibility. |
| **Config format changes** | If `.shakerrc.json` schema changes, existing configs break. | Low | Medium | Validate unknown fields with a warning, not an error. Support old config formats with migration. | Add `shaker config migrate` command. |

### Static Analysis Limitations

These are **known, documented limitations** — not bugs. They should be documented in the README:

1. **`getattr(obj, name)`** — Cannot resolve dynamically. The calling function is preserved in full.
2. **`eval()`, `exec()`** — Cannot resolve. Preserved in full.
3. **`from foo import *`** — Cannot resolve which names are imported. All symbols from `foo` are considered potentially reachable.
4. **Conditional imports** (`if TYPE_CHECKING:`) — Treated as real imports. May include symbols that aren't available at runtime.
5. **Decorators that change signatures** — The original signature is preserved. The decorator's effect is not analyzed.
6. **Metaclasses and dynamic class creation** — Classes created via `type()` calls are not in the symbol table.
7. **Monkey-patching** — If a function is replaced at runtime, the graph shows the original.
8. **String-based dispatch** (e.g., `getattr(registry, name)()`) — Not analyzed.
9. **C extensions** — Calls to C extension functions are not resolved.
10. **Import hooks** — Custom import hooks (`sys.meta_path`) are not executed.

### Python Edge Cases

| Edge Case | Handling | Test |
|---|---|---|
| `__init__.py` re-exports | Parse normally. Re-exports appear as imports. | `test_parser.py` |
| `__all__` exports | Parse `__all__` and treat listed names as public API. | `test_parser.py` |
| `from __future__ import annotations` | Parse normally. The import is recorded. | `test_parser.py` |
| Walrus operator (`:=`) | Parsed by `ast.parse()`. Calls inside are extracted. | `test_parser.py` |
| Match statement (Python 3.10+) | Parsed by `ast.parse()`. Calls inside are extracted. | `test_parser.py` |
| F-strings with expressions | Calls inside f-strings are extracted. | `test_parser.py` |
| Type comments (`# type: ignore`) | Stripped in `strip` mode (they're comments). | `test_pruner.py` |
| Encoding declarations | Handled by Python's encoding detection. | `test_parser.py` |
| Shebang line | Preserved in output. | `test_pruner.py` |
| BOM (Byte Order Mark) | Handled by UTF-8-SIG encoding detection. | `test_parser.py` |

---

## 14. MVP Definition

### True MVP Scope

The MVP is the **smallest version that delivers meaningful value to the "AI-first engineer" segment** — the beachhead user.

**The MVP user story:**
> *As an AI-first engineer, I want to run `shaker ./src --focus my_function` and get a Markdown document containing the call graph of `my_function`, so I can paste it into Claude and get better debugging help.*

### MVP Includes

| Feature | Why |
|---|
| File discovery with gitignore | Required to work on real projects |
| AST parsing (symbols, imports, calls) | The core analysis |
| Call graph construction | The core value |
| Focus resolution | The core value |
| `signatures` compression mode only | The most useful mode — the killer feature |
| Markdown output | The deliverable |
| Basic token counting (`chars // 4`) | Core value prop — must be visible |
| CLI with `--focus`, `--mode`, `--output` | Minimum viable interface |
| Clipboard copy with graceful fallback | UX must-have |
| Unit tests for parser, graph, resolver, pruner | Quality must-have |

### MVP Does NOT Include

| Feature | Why Deferred |
|---|
| `full` and `strip` modes | `signatures` is the killer feature. Others are nice-to-have. |
| `.shakerrc.json` config | CLI args only for MVP. Config adds complexity. |
| Rich TUI (progress bar, tables) | Plain text output is fine for MVP. |
| `--max-tokens` warning | Nice-to-have. Not core value. |
| `--exclude` patterns | Process all `.py` files. Excludes add complexity. |
| `--dry-run`, `--verbose`, `--quiet` | Nice-to-have flags. |
| `--list-symbols` | Nice-to-have discovery feature. |
| `--format json` | Markdown only for MVP. |
| `--version` flag | Trivial to add, but not blocking. |
| PyPI publishing | Local install only for MVP. |
| CI/CD | Manual testing only for MVP. |
| Multi-platform testing | Developer's platform only for MVP. |
| README with GIF | Text README is fine for MVP. |
| CONTRIBUTING.md | No contributors yet. |
| Real-project testing | Fixture testing only for MVP. |

### MVP Exit Criteria

1. `shaker ./my_project --focus my_function` produces a Markdown document with the call graph.
2. The document can be pasted into Claude/Cursor and produces useful output.
3. Token reduction is visible (before/after count).
4. All core unit tests pass (parser, graph, resolver, pruner, serializer).
5. The tool handles syntax errors gracefully (no crash).
6. The tool handles circular imports gracefully (no infinite loop).
7. The tool handles missing focus gracefully (error with suggestions).

### Estimated MVP Time: 15-18 days

### Post-MVP (v0.5 — "Usable")

Add: `full` and `strip` modes, `.shakerrc.json` config, `--exclude`, `--output`, clipboard, Rich TUI, `--verbose`, `--version`.

**Estimated: +7 days. Total: 22-25 days.**

### v1.0 (Production)

Add: `--max-tokens`, `--dry-run`, `--quiet`, `--list-symbols`, PyPI publishing, CI/CD, multi-platform testing, README, CONTRIBUTING.md, real-project testing.

**Estimated: +15 days. Total: 37-40 days.**

---

## 15. Recommended Build Order

This order minimizes rework by building dependencies first and ensuring each module can be tested before its dependents are built.

### Step 1: `models.py`

**Why This Step Exists:** Every other module depends on the data models. Define all data structures first. No logic to get wrong.

**Dependencies:** None (stdlib only).

**Expected Output:** A module with all dataclasses and enums defined. Importable without errors.

**Verification Method:** `python -c "from shaker.models import *; print('OK')"` succeeds.

**Completion Criteria:** All 12 models defined with correct types, defaults, and field documentation. Passes `mypy --strict`.

---

### Step 2: `constants.py`

**Why This Step Exists:** Constants are needed by almost every module. Define them early.

**Dependencies:** `models.py`.

**Expected Output:** A module with all constants defined. `BUILTIN_NAMES`, `STDLIB_MODULES`, `DEFAULT_MODE`, etc.

**Verification Method:** `python -c "from shaker.constants import *; print(BUILTIN_NAMES)"` succeeds.

**Completion Criteria:** All constants defined. `BUILTIN_NAMES` contains at least all Python 3.10 builtins. `STDLIB_MODULES` contains common stdlib modules.

---

### Step 3: `config.py`

**Why This Step Exists:** Configuration is needed by the CLI and pipeline, but the logic is self-contained. Build it early so it's ready when the CLI needs it.

**Dependencies:** `models.py`, `constants.py`.

**Expected Output:** A working config loader that reads `.shakerrc.json` and returns a `Config` object.

**Verification Method:** `unit/test_config.py` passes (10+ tests).

**Completion Criteria:** All config tests pass. Validation error messages are clear. Config merging (CLI overrides config) works correctly.

---

### Step 4: `tokens.py`

**Why This Step Exists:** Token counting is needed for the final output, but the logic is self-contained. Build it early.

**Dependencies:** `constants.py`.

**Expected Output:** A working token counter that uses `tiktoken` if available, falls back to `chars // 4`.

**Verification Method:** `unit/test_tokens.py` passes (5+ tests).

**Completion Criteria:** All token tests pass. Fallback works when `tiktoken` is unavailable.

---

### Step 5: `discovery.py`

**Why This Step Exists:** File discovery is the first stage of the pipeline. Must work before parsing can begin.

**Dependencies:** `models.py`, `constants.py`, `config.py`.

**Expected Output:** A working file discoverer that walks directories, respects `.gitignore`, and applies exclude patterns.

**Verification Method:** `unit/test_discovery.py` passes (15+ tests).

**Completion Criteria:** All discovery tests pass. Gitignore patterns correctly respected. Exclude patterns work. Edge cases handled.

---

### Step 6: `parser.py`

**Why This Step Exists:** The parser is the second stage and the most complex module. It needs thorough testing before graph building can begin.

**Dependencies:** `models.py`, `constants.py`. (Discovery provides file list, but the parser can be tested with individual files.)

**Expected Output:** A working parser that extracts symbols, imports, and calls from Python files.

**Verification Method:** `unit/test_parser.py` passes (25+ tests).

**Completion Criteria:** All parser tests pass. Handles syntax errors gracefully. Handles non-UTF-8 files. Extracts all node types correctly. Coverage ≥ 95%.

---

### Step 7: `graph.py`

**Why This Step Exists:** The graph builder is the third stage. It consumes `ParsedFile` objects from the parser.

**Dependencies:** `models.py`, `parser.py`.

**Expected Output:** A working call graph builder that constructs a `networkx.DiGraph` from parsed files.

**Verification Method:** `unit/test_graph.py` passes (15+ tests).

**Completion Criteria:** All graph tests pass. Circular imports handled. Unresolvable symbols logged. Cycle detection works.

---

### Step 8: `resolver.py`

**Why This Step Exists:** The resolver is the fourth stage. It consumes `CallGraph` from the graph builder.

**Dependencies:** `models.py`, `graph.py`.

**Expected Output:** A working focus resolver that extracts the relevant subgraph and maps symbols to files.

**Verification Method:** `unit/test_resolver.py` passes (10+ tests).

**Completion Criteria:** All resolver tests pass. Focus resolution walks both directions. Suggestions work for missing focus.

---

### Step 9: `pruner.py`

**Why This Step Exists:** The pruner is the fifth stage. It consumes `ParsedFile` objects and the focus set.

**Dependencies:** `models.py`, `constants.py`, `parser.py`.

**Expected Output:** A working pruner that applies compression modes and produces valid Python.

**Verification Method:** `unit/test_pruner.py` passes (20+ tests).

**Completion Criteria:** All pruner tests pass. Roundtrip validity confirmed. All three modes work correctly. Coverage ≥ 95%.

---

### Step 10: `serializer.py`

**Why This Step Exists:** The serializer is the sixth stage. It takes pruned output (plain strings), so it's decoupled from the engine.

**Dependencies:** `models.py`, `constants.py`.

**Expected Output:** A working Markdown serializer that produces the correct output format.

**Verification Method:** `unit/test_serializer.py` passes (10+ tests).

**Completion Criteria:** All serializer tests pass. Output matches the schema. File tree is correctly formatted.

---

### Step 11: `clipboard.py`

**Why This Step Exists:** The clipboard module is the seventh stage. It's self-contained.

**Dependencies:** `models.py`.

**Expected Output:** A working delivery module that copies to clipboard and writes to file.

**Verification Method:** Integration tests pass.

**Completion Criteria:** Clipboard works (or degrades gracefully). File output works. Error handling is correct.

---

### Step 12: `cli.py`

**Why This Step Exists:** The CLI is the composition root. It's built last because it depends on everything.

**Dependencies:** All shaker packages.

**Expected Output:** A working CLI that orchestrates the full pipeline and displays results.

**Verification Method:** `integration/test_cli.py` and `integration/test_pipeline.py` pass (20+ tests).

**Completion Criteria:** All integration tests pass. Full CLI works end-to-end. Help text is comprehensive. Error messages are user-friendly.

---

### Dependency Graph (Build Order)

```
Step 1:  models.py ──────┬──► Step 2: constants.py ───► Step 3: config.py ───┐
                         │                                                   │
                         ├──► Step 4: tokens.py                               │
                         │                                                   │
                         ├──► Step 5: discovery.py ◄──────────────────────────┤
                         │                                                   │
                         ├──► Step 6: parser.py ───► Step 7: graph.py ───► Step 8: resolver.py
                         │       │                             │
                         │       └─────────────────────────────┤
                         │                                     │
                         ├──► Step 9: pruner.py ◄──────────────┤
                         │                                     │
                         ├──► Step 10: serializer.py            │
                         │                                     │
                         ├──► Step 11: clipboard.py             │
                         │                                     │
                         └──► Step 12: cli.py ◄────────────────┘
```

---

## 16. Engineering Standards

### Python Standards

- **Minimum Python version:** 3.10
- **Target Python versions:** 3.10, 3.11, 3.12, 3.13
- **Style guide:** PEP 8 (enforced by `ruff`)
- **Formatter:** `ruff format` (enforced in CI)
- **Linter:** `ruff check` (enforced in CI)
- **Type checker:** `mypy --strict` (enforced in CI)

### Naming Conventions

| Element | Convention | Example |
|---|---|---|
| Module | `snake_case` | `discovery.py` |
| Class | `PascalCase` | `ParsedFile`, `SymbolExtractor` |
| Function | `snake_case` | `discover_files()`, `parse_file()` |
| Constant | `UPPER_SNAKE_CASE` | `DEFAULT_MODE`, `BUILTIN_NAMES` |
| Private function | `_snake_case` | `_walk_directory()` |
| Private class | `_PascalCase` | `_SymbolExtractor()` |
| Enum member | `UPPER_SNAKE_CASE` | `CompressionMode.SIGNATURES` |
| Dataclass field | `snake_case` | `line_number`, `is_async` |
| Test function | `test_<description>` | `test_parser_handles_syntax_error()` |
| Test file | `test_<module>.py` | `test_parser.py` |
| Fixture | `<description>` | `simple_app_path` |

### Typing Requirements

- **All function signatures** must have type annotations for parameters and return types.
- **All class fields** must have type annotations.
- **No `Any`** except where genuinely unavoidable (e.g., `ast.AST` node attributes).
- **Use `typing_extensions`** for `Self`, `TypeAlias`, and other backported types.
- **Use `from __future__ import annotations`** in all modules for forward references.
- **Generic types** must be parameterized: `list[Symbol]`, not `List[Symbol]`.
- **Union types** use `X | Y` syntax (Python 3.10+).

### Documentation Requirements

- **Module docstrings:** Every module has a docstring describing its purpose.
- **Class docstrings:** Every class has a docstring describing its purpose and usage.
- **Function docstrings:** Every public function has a docstring with:
  - Description
  - Args (with types)
  - Returns (with type)
  - Raises (if applicable)
- **Internal functions:** Docstrings recommended but not required. A single-line comment is sufficient.
- **Complex logic:** Inline comments explaining WHY, not WHAT.
- **README:** Comprehensive, with installation, usage, examples, and architecture overview.

### Testing Requirements

- **Every public function** has at least one unit test.
- **Every error path** has a test.
- **Every edge case** identified in this document has a test.
- **Test coverage** ≥ 85% overall, ≥ 90% for critical modules.
- **Tests are deterministic** — no randomness, no network, no time dependence.
- **Tests are isolated** — no shared mutable state between tests.
- **Test names** are descriptive: `test_<module>_<scenario>_<expected_outcome>`.

### Error Handling Standards

- **Never crash on bad input.** Log a warning and continue.
- **User-facing errors** are clear and actionable. Include suggestions when possible.
- **Internal errors** (bugs) raise exceptions with descriptive messages.
- **Parse errors** are collected and reported in the output, not printed to stderr.
- **Missing focus** produces an error with the top 10 most similar symbol names.
- **Missing path** produces an error with a helpful message.
- **Invalid config** produces an error with the specific field and expected format.

### Logging Standards

- **Use `rich.console.Console` for all output.**
- **stdout** is reserved for the Markdown output (for piping).
- **stderr** is used for progress, warnings, and errors.
- **Verbose mode** (`--verbose`) prints additional diagnostic information.
- **Quiet mode** (`--quiet`) suppresses all non-error output.
- **No `print()` statements** in library code. All output goes through the CLI.

### Architecture Rules

1. **`models.py` imports nothing from the project.** It is the foundation.
2. **`engine/` modules never import from `output/` or `infra/`.** Data flows engine → output, never backward.
3. **`cli.py` is the only module that imports from all other packages.** It is the composition root.
4. **No circular imports** between any two modules.
5. **Each subpackage's `__init__.py`** re-exports only the public API.
6. **Internal functions** are prefixed with `_` and not re-exported.
7. **Data flows through `PipelineState`.** No global mutable state.

---

## 17. Definition of Done

### File-Level Definition of Done

A Python source file is considered complete when:

- [ ] All functions have type annotations (parameters and return types).
- [ ] All public functions have docstrings.
- [ ] All classes have docstrings.
- [ ] The module has a docstring.
- [ ] `ruff check` reports zero issues.
- [ ] `ruff format --check` reports zero formatting issues.
- [ ] `mypy --strict` reports zero errors.
- [ ] All unit tests for the module pass.
- [ ] Test coverage for the module meets the minimum threshold.
- [ ] No `print()` statements (library code only).
- [ ] No `Any` types except where unavoidable.
- [ ] All error paths are tested.

### Module-Level Definition of Done

A module (subpackage) is considered complete when:

- [ ] All source files in the module are complete (per file-level criteria).
- [ ] The `__init__.py` re-exports the public API.
- [ ] All unit tests pass.
- [ ] Integration tests involving the module pass.
- [ ] The module's public API is documented in the README.
- [ ] No circular imports with other modules.

### Phase-Level Definition of Done

A development phase is considered complete when:

- [ ] All deliverables for the phase are implemented.
- [ ] All exit criteria are met.
- [ ] All tests pass (unit + integration).
- [ ] Test coverage meets the phase's target.
- [ ] `ruff check`, `ruff format --check`, and `mypy --strict` all pass.
- [ ] CI passes on all platforms.
- [ ] The CHANGELOG is updated with phase accomplishments.
- [ ] Known issues are documented (not hidden).

### MVP Definition of Done

The MVP is considered complete when:

- [ ] `shaker ./my_project --focus my_function` produces correct Markdown output.
- [ ] The output can be pasted into an LLM and produces useful results.
- [ ] Token reduction is visible (before/after count).
- [ ] All core unit tests pass (parser, graph, resolver, pruner, serializer).
- [ ] The tool handles syntax errors gracefully (no crash).
- [ ] The tool handles circular imports gracefully (no infinite loop).
- [ ] The tool handles missing focus gracefully (error with suggestions).
- [ ] Overall test coverage ≥ 85%.
- [ ] `ruff check`, `ruff format --check`, and `mypy --strict` all pass.
- [ ] README is sufficient for a new user to get value.

### v1.0 Definition of Done

v1.0 is considered complete when:

- [ ] All MVP criteria are met.
- [ ] All three compression modes work correctly.
- [ ] `.shakerrc.json` config is supported.
- [ ] Rich TUI displays correctly (progress bar, summary table).
- [ ] Clipboard works on the developer's platform (or degrades gracefully).
- [ ] All CLI flags work as documented.
- [ ] End-to-end tests pass on 3 real open-source Python projects.
- [ ] `pip install codebase-shaker` works from TestPyPI.
- [ ] All tests pass on Python 3.10, 3.11, 3.12, 3.13.
- [ ] CI passes on Ubuntu, macOS, and Windows.
- [ ] Overall test coverage ≥ 85%.
- [ ] README is comprehensive (installation, usage, examples, architecture).
- [ ] CONTRIBUTING.md is complete (dev environment, testing, PRs).
- [ ] CHANGELOG.md has a v1.0 entry.
- [ ] LICENSE (MIT) is present.

---

## 18. Future Roadmap

### v1.1 — Quality of Life

These are high-value, low-effort improvements that should be considered after v1.0 ships:

- **`--list-symbols` flag:** List all available symbols in a codebase to help users discover what to focus on.
- **`--no-tree` flag:** Skip the file tree in output for large codebases.
- **`--depth N` flag:** Limit focus resolution to N hops.
- **`--callers-only` / `--callees-only` flags:** Directional focus resolution.
- **Improved fuzzy matching:** Use `rapidfuzz` for better symbol suggestions.
- **Config autodiscovery:** Search upward from the target directory for `.shakerrc.json`.
- **Environment variable support:** `SHAKER_MODE`, `SHAKER_MAX_TOKENS`, etc.
- **Watch mode (basic):** Re-run on file save, update clipboard automatically.

### v2 — Multi-Language + Ecosystem

These are significant features that require architectural changes:

- **JavaScript/TypeScript support:** Add `tree-sitter` as a parser backend. Abstract the parser interface to support multiple languages.
- **VS Code extension:** Right-click → "Copy as Shaker context." Requires JSON output mode.
- **JSON output mode:** Machine-readable output for IDE integrations and scripts.
- **Diff mode:** Only include files changed since a given git commit. High-value for PR review.
- **CI hook:** Auto-package context when a pipeline test fails. GitHub Actions / GitLab CI integration.
- **Interactive Streamlit UI:** Dependency graph you can toggle nodes on/off. Requires web framework.
- **LLM model-specific token counting:** Support GPT-3.5, GPT-4, Claude, Gemini tokenizers.
- **Caching:** Cache parse results for unchanged files. Requires file hash tracking.
- **Parallel parsing:** Use `multiprocessing` to parse files in parallel for large codebases.

### Architectural Expansion Plans

**Parser abstraction:**
```python
class BaseParser(ABC):
    @abstractmethod
    def parse_file(self, path: Path) -> ParsedFile: ...
    
    @abstractmethod
    def supported_extensions(self) -> set[str]: ...

class PythonParser(BaseParser): ...
class JavaScriptParser(BaseParser): ...
class TypeScriptParser(BaseParser): ...
```

**Output format abstraction:**
```python
class BaseSerializer(ABC):
    @abstractmethod
    def serialize(self, pruned: dict[Path, str], metadata: OutputMetadata) -> str: ...

class MarkdownSerializer(BaseSerializer): ...
class JsonSerializer(BaseSerializer): ...
```

**Plugin system (v2):**
```python
# Allow users to register custom parsers and serializers
@shaker.parser(".rb")
class RubyParser(BaseParser): ...

@shaker.serializer("xml")
class XmlSerializer(BaseSerializer): ...
```

### Technical Debt Considerations

- **`networkx` dependency:** If distribution weight becomes a concern, replace with a lightweight `dict`-based graph implementation. The graph interface is cleanly separated.
- **`ast.unparse()` reliability:** If `ast.unparse()` proves unreliable across Python versions, switch to a source-level approach (line-based signature extraction, regex-based comment removal).
- **Symbol resolution heuristic:** The current heuristic is conservative. If users report too many false positives, add a `--strict-mode` with higher confidence thresholds.
- **Performance:** If large codebases (>5000 files) become a common use case, add parallel parsing and caching.

---

*This document is the single source of truth for the Codebase Shaker implementation. It should be updated as the project evolves. All significant architectural decisions should be documented here.*

*Last updated: June 2026*
*Version: 0.0.0*
