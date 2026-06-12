# Codebase Shaker — Version 1.0 Roadmap

> **Strategic Planning Document | Definitive Development Blueprint**
> Created: 2026-06-06
> Status: Planning Phase — Pre-Implementation
> Target: Version 1.0 Production Release

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Current State Assessment](#2-current-state-assessment)
3. [Research Findings](#3-research-findings)
4. [Competitive Analysis](#4-competitive-analysis)
5. [Differentiation Strategy](#5-differentiation-strategy)
6. [Version 1 Feature Discovery](#6-version-1-feature-discovery)
7. [Architecture Planning](#7-architecture-planning)
8. [User Experience Design](#8-user-experience-design)
9. [Version 1 Roadmap — Phases](#9-version-1-roadmap--phases)
10. [Implementation Priorities](#10-implementation-priorities)
11. [Risk Analysis](#11-risk-analysis)
12. [Recommended Scope & Final Strategy](#12-recommended-scope--final-strategy)

---

## 1. Executive Summary

Codebase Shaker is a Python CLI tool that compresses Python codebases for LLM context windows. The beta (v0.0.0) is complete: a 7-stage pipeline with AST-based compression, call graph analysis, focus resolution, Markdown output, and clipboard delivery. 530 tests. mypy strict clean. It works.

**The question this document answers: What should Version 1.0 be?**

After analyzing the codebase, the competitive landscape (Repomix, Aider, Cursor, Cline, src2md, CntxtPY, Bloop, Sourcegraph Cody), and hundreds of developer complaints across Reddit, Hacker News, Dev.to, GitHub issues, and community forums, the answer is clear:

**Version 1.0 should become the most developer-friendly, context-aware codebase packaging tool for Python projects — with multi-format output, security scanning, remote repo support, MCP server integration, and intelligent context budget management.**

Not a kitchen-sink release. A focused, high-utility release that solves the real problems developers face when feeding code to LLMs.

### Key Strategic Decisions

| Decision | Rationale |
|---|---|
| **Stay Python-only for v1** | Multi-language (Tree-sitter) is a v2 concern. Python has enough depth to differentiate. |
| **Add XML + JSON output formats** | Lowest-effort, highest-impact gap vs Repomix. LLMs parse XML more reliably than Markdown. |
| **Add security scanning** | Only Repomix has this. It's a procurement requirement for enterprises. |
| **Add remote repo support** | Expected by 2026. Users shouldn't have to clone first. |
| **Add MCP server mode** | MCP is becoming the integration standard. Every competitor is adding it. |
| **Add context budget management** | No tool does this well. It's the #1 developer pain point. |
| **Add file importance scoring** | Makes no-focus mode dramatically smarter. |
| **Add `--quiet` and progress bar** | Missing from beta. Expected in any production CLI tool. |
| **Defer LLM-powered compression** | API cost/complexity. Better as v2 opt-in. |
| **Defer watch mode, web UI, VS Code extension** | v2 features. Would overload v1. |


---

## 2. Current State Assessment

### 2.1 What Exists (v0.0.0 Beta)

**Architecture:** 7-stage stateless pipeline
1. **Discovery** — File walking with `.gitignore` support via `pathspec`
2. **Parsing** — AST extraction of symbols, imports, call sites
3. **Graph** — `networkx.DiGraph` of symbol dependencies with cycle detection
4. **Resolution** — Bidirectional BFS focus resolution with fuzzy suggestions
5. **Pruning** — 3 compression modes (full/signatures/strip) via `ast.NodeTransformer`
6. **Serialization** — Markdown output with YAML header, ASCII tree, code blocks
7. **Delivery** — Clipboard copy via `pyperclip` + file write

**CLI:** Click-based with 14 options. Rich terminal output with stats table.

**Config:** `.shakerrc.json` with autodiscovery. Environment variable fallback. CLI override.

**Quality:** 530 tests (431 unit + 99 integration). mypy `--strict` clean across 17 source files.

**Dependencies:** `networkx`, `pathspec`, `click`, `rich` (required). `pyperclip`, `tiktoken` (optional).

### 2.2 What's Missing (Gaps)

| Gap | Severity | User Impact |
|---|---|---|
| Only Markdown output | **High** | LLMs parse XML better; JSON needed for programmatic use |
| No security scanning | **High** | Users leak API keys/tokens to LLMs |
| No remote repo support | **Medium** | Must clone locally first |
| No MCP server mode | **Medium** | Can't integrate with Claude Code, Cursor natively |
| No context budget management | **High** | Users hit context limits unexpectedly |
| No file importance scoring | **Medium** | All non-focus files treated equally |
| No `--quiet` flag | **Low** | Can't suppress output in scripts |
| No progress bar | **Low** | No visual feedback on large repos |
| No `--format` flag | **High** | Stuck with Markdown |
| No diff/incremental mode | **Medium** | Must re-run on every change |
| No token budget enforcement | **High** | No intelligent fitting within context windows |

### 2.3 Codebase Health

- **Strengths:** Clean architecture, pure data models, no circular dependencies, comprehensive test coverage, strict typing
- **Weaknesses:** No `--quiet` mode, no progress indication, serializer only outputs Markdown, no security layer
- **Technical Debt:** Minimal. The codebase is clean. The `OMIT_THRESHOLD` constant is defined but unused. `--verbose` has almost no debug log messages.


---

## 3. Research Findings

### 3.1 Developer Pain Points (from community research)

Research sources: Reddit (r/ChatGPTCoding, r/GithubCopilot), Hacker News, Dev.to, Cursor Community Forum, GitHub issues, Medium technical blogs, arXiv papers.

#### The #1 Problem: Codebase >> Context Window

A medium TypeScript project (50K LOC) contains 2-3 million tokens. Even with 200K context windows, the model sees 7-10% of the code at best. 90%+ is invisible. This is the fundamental physical constraint that makes tools like Codebase Shaker necessary.

#### Top 10 Developer Frustrations

1. **Silent context overflow** — When context fills mid-task, the LLM starts producing garbage. No warning. No graceful degradation. Just broken output.

2. **Between-session amnesia** — Every new session starts from scratch. Architecture decisions, debugging history, three hours of explanation — gone. Developers re-explain the same context 15-30 minutes/day across tools.

3. **No intelligent context management** — No token budgets, no prioritization, no selective forget. Requests are dispatched blindly and rejected with cryptic errors.

4. **Context degradation is invisible** — No signal-to-noise meter. No way to know when your context is polluted beyond recovery.

5. **Cross-tool context fragmentation** — Cursor, Claude Code, Copilot each maintain their own contradictory context. 43% of senior engineers waste 2.5 hours/week re-explaining.

6. **Cross-service/cross-file blindness** — Tools miss architectural dependencies. 78-90% of users get suggestions referencing non-existent or outdated code on 500+ file projects.

7. **No incremental updates** — Small change = re-package entire codebase. No concept of "context diff."

8. **Security leaks** — Users accidentally paste API keys, passwords, and tokens into LLM prompts. Only Repomix scans for this.

9. **Cost unpredictability** — Token consumption silently compounds. "Unlimited" plans have hidden limits. Overage billing surprises.

10. **Recovery requires total restart** — No surgical context editing. No "keep this, drop that." Polluted context = start over.

#### What Developers Want But No Tool Provides

- **Context budget management** — "A profiler for LLM context" showing exactly which files consume the most tokens
- **Persistent cross-session memory** — Accumulated codebase knowledge across sessions
- **Automatic context sharding** — Breaking monorepos into semantically-coherent chunks
- **Real-time incremental updates** — File watcher that updates context on change
- **Security-first pipeline** — Automatic secret/PII redaction before any code reaches an LLM
- **Intelligent file prioritization** — Not all files are equal; score by centrality, importers, git activity

### 3.2 Prompt Engineering & Context Engineering Insights

The research reveals a critical shift in the developer community: **context engineering has replaced prompt engineering as the bottleneck.**

Key findings:
- "Context debt > prompt engineering" is the real bottleneck (Dev.to)
- Beyond 60-70% of a model's stated context capacity, performance degrades measurably
- Models pay more attention to the beginning and end of context; middle information is effectively lost
- Tool definition overhead (50+ tools) wastes thousands of tokens before the user sends anything
- Polite conversation ("thank you", "looks great!") costs ~400 tokens vs ~40 for direct prompts — 10x overhead

**Implication for Codebase Shaker:** The tool should help developers maximize the *signal* in their context budget, not just reduce token count. File importance scoring and context budget management directly address this.


---

## 4. Competitive Analysis

### 4.1 Competitive Landscape Map

| Tool | Category | Output | Languages | Security | MCP | Remote | Pricing |
|---|---|---|---|---|---|---|---|
| **Repomix** | Packaging | XML/JSON/MD/text | 20+ (Tree-sitter) | Yes | Yes | Yes | Free |
| **Aider** | Pair programming | N/A (inline) | Multi | No | No | No | Free + API |
| **Cursor** | AI IDE | N/A (IDE) | Multi | No | No | Yes | $20-200/mo |
| **Claude Code** | Agent | N/A (agent) | Multi | No | Yes | Yes | $20-200/mo |
| **Cline** | Agent (VS Code) | N/A (agent) | Multi | No | No | No | Free + API |
| **src2md** | Compression | MD/JSON/HTML | Multi (AST) | No | No | No | Free |
| **CntxtPY** | Knowledge graph | JSON/text | Python only | No | No | No | Free |
| **Bloop** | Code search | N/A (search) | 10+ | No | No | No | Free/$12/mo |
| **Sourcegraph Cody** | Enterprise | N/A (search+AI) | Multi | Enterprise | Yes | Yes | $16K+ |
| **code2prompt** | Packaging | Template-based | Multi (Rust) | No | No | No | Free |
| **Codebase Shaker** | Packaging | Markdown only | Python only | No | No | No | Free |

### 4.2 Competitor Strengths

**Repomix (market leader):**
- Multi-language via Tree-sitter (20+ languages)
- Multiple output formats (XML optimized for Claude)
- Secretlint security scanning
- MCP server mode
- Remote GitHub repo support
- Web UI for zero-install usage
- 16+ language translations
- Near-weekly release cadence

**Aider:**
- Repo Map — dynamic codebase-wide context map
- Works with any LLM provider
- Git-native workflow (every AI change = tracked commit)
- Automatic linting/testing on changes
- Self-bootstrapping (88% of own code written by Aider)

**Cursor:**
- Full IDE replacement with deep codebase context
- Multi-model support with automatic routing
- `.cursorrules` for project-specific AI behavior
- Cloud Agents for background tasks

**Claude Code:**
- 200K+ token context window
- Highest SWE-bench score (80.9%)
- 30+ hour autonomous execution
- 91% CSAT, NPS 54 (highest loyalty)

### 4.3 Competitor Weaknesses

**Repomix:**
- No auto-sharding for massive repos (50K+ files)
- Node.js dependency feels heavy
- Web UI limited to public repos
- No context budget management
- No incremental/diff mode

**Aider:**
- Terminal-only (steep learning curve)
- One Git repo at a time (no monorepo support)
- No built-in budget caps
- Long sessions get expensive

**Cursor:**
- Code reversion bug (silent, undone edits)
- Heavy memory/CPU usage
- Escalating costs ($40-50/mo vs $20 advertised)
- Privacy concerns (data sent to servers)
- Hallucinates APIs

**Claude Code:**
- Weekly usage limits interrupt deep work
- Pro plan insufficient for serious work
- Terminal-only
- Can generate security nightmares

### 4.4 Market Gaps (Opportunities)

| Gap | Current State | Opportunity |
|---|---|---|
| **Context budget management** | No tool does this | Build a "profiler for LLM context" |
| **Incremental/real-time updates** | All tools require re-run | File watcher with incremental update |
| **Cross-tool context portability** | Each tool has own format | Standardized context interchange |
| **Security-first pipeline** | Only Repomix has it | Automatic secret/PII redaction |
| **Monorepo context scoping** | Fundamentally broken everywhere | Package-level context inheritance |
| **Context diff mode** | Feature requested but unimplemented | Send only changed portions |
| **Python-specific knowledge graphs** | CntxtPY is early-stage, 113 stars | Production-ready Python knowledge graph |


---

## 5. Differentiation Strategy

### 5.1 What Codebase Shaker Can Do Better

**1. Python-First Depth Over Multi-Language Breadth**

Repomix supports 20+ languages but does shallow analysis on each. Codebase Shaker can go deeper on Python:
- Full AST-level understanding (not just text)
- Call graph with cycle detection
- Import resolution (including relative imports)
- Class hierarchy analysis
- Decorator-aware symbol extraction

**This is the "do one thing exceptionally well" strategy.**

**2. Context Budget Management (No Competitor Has This)**

A "profiler for LLM context" that:
- Shows per-file token consumption
- Suggests which files to compress vs exclude
- Automatically fits the most valuable context within a token budget
- Warns before output exceeds model limits

**3. Developer Experience**

- Clean, intuitive CLI with `--quiet` mode for scripting
- Progress bars for large repos
- Clear error messages with actionable suggestions
- Sensible defaults that work out of the box

**4. Security-First Design**

- Built-in secret scanning (regex-based, zero dependencies)
- Configurable redaction vs warning
- Pre-flight check before any output leaves the machine

### 5.2 Why Users Would Choose Codebase Shaker

| User Type | Why They'd Choose Shaker |
|---|---|
| **Python developer** | Deepest Python analysis available; understands call graphs, not just text |
| **Security-conscious team** | Built-in secret scanning; no keys leak to LLMs |
| **Power user** | Context budget management; maximize signal per token |
| **Open source maintainer** | Free, no API keys needed, works offline |
| **Enterprise** | Security scanning + audit-friendly output formats |

### 5.3 What Would Make Shaker Irreplaceable

1. **Accumulated project context** — If Shaker builds knowledge about your codebase over time (not just per-session), switching means losing that understanding
2. **Deepest Python call graph** — No other tool resolves Python imports, class hierarchies, and call sites as accurately
3. **Context budget intelligence** — The "profiler" concept, if executed well, becomes indispensable
4. **Custom rules** — Project-specific configuration that shapes output (like `.cursorrules` but for context packaging)


---

## 6. Version 1 Feature Discovery

### 6.1 Must-Have Features (Non-Negotiable for v1)

These features are required for v1 to be competitive and complete:

#### F1: Multi-Format Output (`--format` flag)
- **What:** Add `--format` flag with choices: `markdown` (default), `xml`, `json`, `plain`
- **Why:** LLMs parse XML more reliably than Markdown. JSON needed for programmatic use. This is the #1 gap vs Repomix.
- **Effort:** Medium — new serializer modules, same pipeline
- **Impact:** High — immediately competitive with Repomix

#### F2: Security Scanning (Secret Detection)
- **What:** Regex-based secret scanner that detects AWS keys, GitHub tokens, private keys, .env values, API keys
- **Why:** Users leak secrets to LLMs. Only Repomix has this. Enterprise procurement requirement.
- **Effort:** Low — regex patterns, configurable redaction
- **Impact:** High — prevents a real and common security incident

#### F3: Remote Repository Support (`--remote` flag)
- **What:** Clone from GitHub/GitLab URL to temp dir, run pipeline, clean up
- **Why:** Expected in 2026. Users shouldn't have to clone first.
- **Effort:** Low-Medium — subprocess + tempdir or gitpython
- **Impact:** Medium — great for quick "analyze this repo" workflows

#### F4: MCP Server Mode (`--mcp` flag)
- **What:** Run Shaker as an MCP server so AI assistants can call it natively
- **Why:** MCP is becoming the integration standard. Repomix, Sourcegraph Cody, Stainless all have MCP servers.
- **Effort:** Medium — MCP server wrapper around existing pipeline
- **Impact:** Medium-High — growing in importance as MCP adoption increases
- **Note:** The `mcp` Python package (v1.27.2) is currently in Beta. To avoid stability risk for non-MCP users, this is an **optional dependency** installed via `pip install codebase-shaker[mcp]`.

#### F5: `--quiet` Flag
- **What:** Suppress all non-essential output (stats table, warnings). Only output the serialized content.
- **Why:** Required for scripting and piping. Missing from beta. Expected in any production CLI.
- **Effort:** Trivial — conditional console output
- **Impact:** Low effort, high polish

#### F6: Progress Bar
- **What:** Rich progress bar showing file discovery, parsing, graph building progress
- **Why:** No visual feedback on large repos. Expected in modern CLI tools.
- **Effort:** Low — Rich `Progress` widget
- **Impact:** Low effort, high polish

### 6.2 High-Impact Features (Significantly Improve Usefulness)

#### F7: File Importance Scoring
- **What:** Score files by: number of importers, centrality in call graph, optionally enhanced by recent git changes
- **Why:** When there's no `--focus`, all non-focus files are treated equally. Some files matter more.
- **Effort:** Medium — graph analysis + optional git log parsing
- **Impact:** Medium — makes no-focus mode much smarter
- **Architecture:** Git is optional. `StaticScorer` (importer count + graph centrality) is the default and works everywhere. `GitScorer` adds git change history when git is available and `config.use_git_scoring` is enabled. This ensures scoring works in CI environments, shallow clones, and non-git directories.

#### F8: Context Budget Management (`--max-tokens` enforcement)
- **What:** Per-file token reporting in stats + automatic compression depth selection based on budget ratio. When `--max-tokens` is set and `enforce_max_tokens` is enabled, the pruner automatically selects compression depth: if `input_tokens / max_tokens > 2` use `strip`; if > 1.5 use `signatures`; otherwise use the user's chosen mode. Files are never silently excluded — the budget is met by increasing compression depth, not by dropping files.
- **Why:** No tool provides per-file token visibility or automatic compression adjustment. Developers hit context limits unexpectedly.
- **Effort:** Medium — token reporting in stats + compression depth heuristic in pruner
- **Impact:** High — directly addresses the #1 developer pain point
- **Backward compatibility:** `enforce_max_tokens` defaults to `False`. Existing `--max-tokens` behavior (warning-only) is preserved unless the user opts in.

#### F9: Output Statistics File (`--stats` flag)
- **What:** Write build statistics to a JSON file alongside the output
- **Why:** Programmatic access to token counts, reduction percentages, file lists
- **Effort:** Low — JSON serialization of `BuildStats`
- **Impact:** Low-Medium — useful for CI/CD integration

### 6.3 Differentiator Features (Competitors Lack)

#### F10: Per-File Compression Control
- **What:** Allow different compression modes for different files via config
- **Why:** Some files need full detail, others can be stripped. One-size-fits-all is wasteful.
- **Effort:** Medium — config schema change + pruner modification
- **Impact:** Medium — more control, better context budget use

#### F11: Git-Aware Output
- **What:** Include git metadata in output: last commit, author, changed files since date
- **Why:** LLMs benefit from knowing what's recently changed. No tool does this well.
- **Effort:** Medium — git log parsing
- **Impact:** Medium — useful context for LLMs

#### F12: Circular Import Visualization
- **What:** In the output, highlight circular dependencies with warnings
- **Why:** Circular imports are a common source of bugs. Shaker already detects them.
- **Effort:** Low — add to serializer
- **Impact:** Low-Medium — useful diagnostic information

### 6.4 Advanced Features (If Justified by Effort)

#### F13: Config Presets
- **What:** Named config presets (e.g., `--preset django`, `--preset fastapi`) with pre-configured excludes and settings
- **Why:** Framework-specific patterns (migrations, __pycache__, .pyc) should be excluded by default
- **Effort:** Low — predefined config templates
- **Impact:** Medium — better out-of-box experience

#### F14: Multiple Focus Symbols
- **What:** Accept multiple `--focus` flags for multi-symbol analysis
- **Why:** Users often want to focus on several related symbols
- **Effort:** Low — extend existing resolver
- **Impact:** Medium — more flexible focus resolution

### 6.5 Future Features (Version 2+)

These are explicitly deferred to avoid overloading v1:

| Feature | Why Deferred |
|---|---|
| Multi-language (Tree-sitter) | Massive scope increase. Python-only is the v1 strategy. |
| LLM-powered semantic compression | API cost/complexity. Opt-in feature for v2. |
| Watch mode / file system watcher | Requires daemon process. v2 feature. |
| Web UI | Requires web framework. v2 feature. |
| VS Code extension | Requires extension development. v2 feature. |
| Diff mode / incremental output | Complex change tracking. v2 feature. |
| Knowledge graph visualization | Requires graphviz/matplotlib. v2 feature. |
| Team/enterprise features (SSO, audit) | Enterprise is v2+. |
| Cloud/SaaS offering | Business model decision. Post-v1. |
| GitHub Gist integration | Nice-to-have. v2. |
| XDG config directory support | Polish feature. v2. |
| Model-specific token counting | tiktoken covers most cases. v2. |


---

## 7. Architecture Planning

### 7.1 New Modules

```
src/shaker/
├── engine/
│   ├── scoring.py          # NEW: File importance scoring (git-optional abstraction)
│   ├── security.py         # NEW: Secret detection and redaction
│   └── remote.py           # NEW: Remote repo cloning and cleanup
├── output/
│   ├── xml_serializer.py   # NEW: XML output format
│   ├── json_serializer.py  # NEW: JSON output format
│   └── plain_serializer.py # NEW: Plain text output format
├── mcp/
│   └── server.py           # NEW: MCP server mode
└── cli.py                  # MODIFIED: New flags, progress bar, quiet mode
```

### 7.2 New Data Models

Additions to `models.py`:

```python
class OutputFormat(Enum):
    """Output serialization format."""
    MARKDOWN = "markdown"
    XML = "xml"
    JSON = "json"
    PLAIN = "plain"

@dataclass(frozen=True)
class SecurityFinding:
    """A potential secret or sensitive data found in source code."""
    file: Path
    line_number: int
    finding_type: str          # "aws_key", "github_token", "private_key", etc.
    severity: str              # "critical", "warning", "info"
    redacted: bool = False

@dataclass
class FileScore:
    """Importance score for a single file."""
    file: Path
    score: float               # 0.0 to 1.0
    importer_count: int        # Number of files that import this
    centrality: float          # Graph centrality score
    git_changes_30d: int       # Git commits in last 30 days
    is_focus: bool = False

@dataclass
class SecurityReport:
    """Results of security scanning."""
    findings: list[SecurityFinding]
    total_scanned: int
    total_findings: int
    critical_count: int
    redacted_count: int
```

### 7.3 Modified Data Models

Additions to `Config`:
```python
output_format: OutputFormat = OutputFormat.MARKDOWN
security_scan: bool = True
security_redact: bool = True
show_progress: bool = True
quiet: bool = False
enforce_max_tokens: bool = False   # When True, auto-adjust compression to fit budget
use_git_scoring: bool = True        # When True, enhance file scoring with git history
```

Additions to `PipelineState`:
```python
security_report: SecurityReport | None = None
file_scores: dict[Path, FileScore] = field(default_factory=dict)
```

### 7.4 New Workflows

#### Security Scanning Workflow (New Stage 5.5)
```
Stage 1: Discovery
Stage 2: Parsing
Stage 3: Graph Building
Stage 4: Focus Resolution
Stage 5: Pruning
Stage 5.5: Security Scanning  ← NEW
  - Scan all pruned source for secret patterns
  - Redact or warn based on config
  - Generate SecurityReport
Stage 6: Serialization
Stage 7: Delivery
```

#### Remote Repo Workflow (Pre-Stage 0)
```
Stage -1: Remote Resolution  ← NEW
  - Clone remote URL to temp directory using tempfile.TemporaryDirectory()
  - Set path to temp directory
  - Register SIGINT/SIGTERM handlers for cleanup on interrupt
Stage 0: Config
Stage 1-7: Normal pipeline (including security scanning of cloned code)
Stage 8: Cleanup  ← NEW
  - TemporaryDirectory context manager ensures cleanup even on crash/interrupt
  - Security note: cloned code may contain secrets — cleanup is critical
```

#### Context Budget Workflow (Enhancement to Stage 5 + Stage 6)
```
Stage 5: Pruning with Budget Awareness
  - If max_tokens is set AND enforce_max_tokens is True:
    1. Calculate budget ratio: input_tokens / max_tokens
    2. Select compression depth:
       - ratio > 2.0  → use strip mode for non-focus files
       - ratio > 1.5  → use signatures mode for non-focus files
       - ratio ≤ 1.5  → use user's chosen mode
    3. Focus files always remain at full detail
  - If enforce_max_tokens is False (default):
    - Current behavior: warn when output exceeds max_tokens

Stage 6: Serialization with Per-File Token Reporting
  - Stats table includes per-file token consumption
  - Users can see exactly where their context budget goes
```

### 7.5 New Outputs

#### XML Output Format
```xml
<?xml version="1.0" encoding="UTF-8"?>
<codebase-shaker>
  <metadata>
    <project>my-project</project>
    <focus>auth.login</focus>
    <mode>signatures</mode>
    <timestamp>2026-06-06T12:00:00</timestamp>
    <version>1.0.0</version>
    <stats>
      <files-retained>15</files-retained>
      <files-total>42</files-total>
      <input-tokens>45000</input-tokens>
      <output-tokens>12000</output-tokens>
      <reduction-pct>73.3</reduction-pct>
    </stats>
  </metadata>
  <files>
    <file path="src/auth.py" focus="true">
      <code><![CDATA[...]]></code>
    </file>
    <file path="src/db.py" compression="signatures">
      <code><![CDATA[...]]></code>
    </file>
  </files>
  <omitted>
    <file path="src/migrations/001_initial.py"/>
  </omitted>
</codebase-shaker>
```

#### JSON Output Format
```json
{
  "metadata": {
    "project": "my-project",
    "focus": "auth.login",
    "mode": "signatures",
    "timestamp": "2026-06-06T12:00:00",
    "version": "1.0.0",
    "stats": {
      "files_retained": 15,
      "files_total": 42,
      "input_tokens": 45000,
      "output_tokens": 12000,
      "reduction_pct": 73.3
    }
  },
  "files": [
    {"path": "src/auth.py", "focus": true, "code": "..."},
    {"path": "src/db.py", "compression": "signatures", "code": "..."}
  ],
  "omitted": ["src/migrations/001_initial.py"]
}
```

### 7.6 CLI Improvements

**New flags:**
```
--format {markdown,xml,json,plain}   Output format
--remote URL                          Remote repository URL
--mcp                                 Run as MCP server
--quiet, -q                           Suppress non-essential output
--no-progress                         Disable progress bar
--security-scan/--no-security-scan    Enable/disable security scanning
--security-redact/--security-warn     Redact or warn on secrets
--stats FILE                          Write stats JSON to file
--preset NAME                         Use a config preset
--score-files                         Show file importance scores
```

**Modified behavior:**
- Progress bar shown by default (disable with `--no-progress`)
- Stats table shown by default (disable with `--quiet`)
- Security scan enabled by default (disable with `--no-security-scan`)

### 7.7 MCP Server Design

The MCP server exposes two tools:

1. **`shake`** — Compress a Python codebase for LLM context
   - Parameters: `path`, `focus`, `mode`, `format`, `max_tokens`
   - Returns: serialized output as text

2. **`list_symbols`** — List all symbols in a Python codebase
   - Parameters: `path`
   - Returns: list of symbols with types and locations

Uses stdio transport. Wraps the existing `run_pipeline()` function.


---

## 8. User Experience Design

### 8.1 User Journey

#### First-Time User
1. `pip install codebase-shaker`
2. `cd my-project`
3. `shaker . --focus "auth.login"`
4. Output appears in terminal + clipboard
5. Paste into Claude Code / ChatGPT
6. Ask questions about the auth system

#### Power User
1. Create `.shakerrc.json` with project-specific settings
2. `shaker . --focus "api.create_user" --format xml --max-tokens 8000`
3. XML output piped to a script or pasted into an LLM
4. Use `--stats stats.json` for CI/CD integration

#### Team Lead
1. Commit `.shakerrc.json` to repo with team conventions
2. Team members use `shaker` with consistent settings
3. Security scanning prevents secrets from reaching LLMs
4. MCP server mode integrates with team's AI coding tools

### 8.2 Typical Workflow

```
Developer wants to understand how auth works:

1. shaker . --focus "auth" --list-symbols
   => See all symbols in the auth module

2. shaker . --focus "auth.login" --format xml --max-tokens 10000
   => Get XML output focused on login, within token budget

3. Paste into Claude Code
   => "How does the login flow work?"
   => "What are the security implications of changing the token expiry?"

4. shaker . --focus "auth.login" --format json --stats auth-stats.json
   => Get JSON for programmatic use + stats for CI tracking
```

### 8.3 Beginner Experience

**Goal:** Zero-config, sensible defaults, clear feedback.

- Run `shaker .` in any Python project => get compressed Markdown
- No config file needed => sensible defaults
- Clear error messages => "Focus 'auth.logn' not found. Did you mean: auth.login?"
- Progress bar => know it's working
- Stats table => understand what happened

### 8.4 Advanced User Experience

**Goal:** Maximum control, scriptability, integration.

- `.shakerrc.json` with per-project settings
- `--quiet` for piping and scripting
- `--format json` for programmatic consumption
- `--stats` for CI/CD metrics
- `--max-tokens` with automatic budget enforcement
- `--mcp` for AI assistant integration
- `--score-files` for understanding file importance
- `--preset django` for framework-specific defaults

### 8.5 Error Handling Philosophy

| Error Type | Behavior |
|---|---|
| Focus not found | Suggest similar symbols, exit with code 1 |
| Parse error | Warn, skip file, continue pipeline |
| Security finding | Redact or warn based on config, continue |
| Token budget exceeded | Warn, show which files were compressed/excluded |
| Remote clone fail | Clear error message, suggest checking URL/access |
| Invalid config | Show which field is invalid, suggest fix |


---

## 9. Version 1 Roadmap — Phases

### Phase 1: Foundation & Output Formats
**Objective:** Add multi-format output and polish CLI basics

**Deliverables:**
- [ ] `--format` flag with `markdown`, `xml`, `json`, `plain` options
- [ ] `xml_serializer.py` — XML output with CDATA sections
- [ ] `json_serializer.py` — JSON output with metadata + files array
- [ ] `plain_serializer.py` — Plain text output (no Markdown formatting)
- [ ] `--quiet` / `-q` flag
- [ ] Progress bar (Rich `Progress` widget)
- [ ] `--no-progress` flag
- [ ] `--init` flag — generates a commented `.shakerrc.json` template for first-time users
- [ ] Pipe-friendly auto-detection: suppress stats table when stdout is not a terminal
- [ ] Call graph summary section in output (focus symbol reachability, circular dep count)
- [ ] Version bump to `1.0.0`
- [ ] Update README with new flags
- [ ] Update CHANGELOG

**Dependencies:** None (self-contained)

**Risks:** Low — serializers are isolated modules, no pipeline changes

**Complexity:** Low-Medium

**Success Criteria:**
- All 4 output formats produce valid output
- XML validates against a simple schema
- JSON is parseable by `json.loads()`
- Plain text has no Markdown syntax
- `--quiet` suppresses all non-output text
- Progress bar shows during discovery, parsing, graph building
- All existing tests pass + 50+ new tests for serializers

---

### Phase 2: Security & Remote Support
**Objective:** Add security scanning and remote repo support

**Deliverables:**
- [ ] `security.py` — Regex-based secret scanner
  - AWS access keys, secret keys
  - GitHub tokens (ghp_, gho_)
  - Private keys (RSA, EC, OpenSSH)
  - Generic API keys (`api_key`, `api_secret`, `password`, `token`)
  - .env-style values (`SECRET=`, `PASSWORD=`)
- [ ] `--security-scan` / `--no-security-scan` flag (default: on)
- [ ] `--security-redact` / `--security-warn` flag (default: redact)
- [ ] `SecurityFinding` and `SecurityReport` models
- [ ] Security findings in output (summary section)
- [ ] `remote.py` — Remote repo cloning via `subprocess` + `tempfile`
- [ ] `--remote URL` flag
- [ ] Temp directory cleanup on completion
- [ ] Security findings in XML/JSON output

**Dependencies:** Phase 1 (output format changes needed for security report sections)

**Risks:** Low-Medium
- Security: False positives on test fixtures with fake keys
- Remote: Network failures, large repos, auth for private repos

**Complexity:** Medium

**Success Criteria:**
- All secret patterns detected in test files
- False positive rate < 5% on real-world codebases
- Redaction replaces secrets with `[REDACTED]`
- Remote cloning works for public GitHub repos
- Temp directory cleaned up even on error
- 30+ new tests for security scanner
- 10+ new tests for remote support

---

### Phase 3: MCP Server & Context Budget
**Objective:** Add MCP server mode and intelligent context budget management

**Deliverables:**
- [ ] `mcp/server.py` — MCP server with `shake` and `list_symbols` tools
- [ ] `--mcp` flag to run in server mode
- [ ] MCP server reads from stdin/stdout (stdio transport)
- [ ] Context budget management in pruner
  - Per-file token consumption tracking in stats
  - Auto compression depth selection when `enforce_max_tokens` is True
  - Backward compatible: `--max-tokens` warning-only by default
- [ ] `--score-files` flag to display file importance scores
- [ ] `scoring.py` — File importance scoring with git-optional abstraction
  - `StaticScorer` (default): importer count + graph centrality
  - `GitScorer` (opt-in): adds git change history when available
  - Graceful fallback when git is not installed or directory is not a git repo
- [ ] `FileScore` model
- [ ] Stats include per-file token consumption and budget utilization
- [ ] `enforce_max_tokens` config option (default: False)

**Dependencies:** Phase 1 (output formats), Phase 2 (security scanning before budget)

**Risks:** Medium
- MCP: `mcp` package is currently in Beta — mitigated by making it an optional dependency
- Budget: Compression depth heuristic may not perfectly fit all cases — acceptable since focus files are always preserved at full detail
- Scoring: Git-optional abstraction eliminates the git dependency risk

**Complexity:** Medium-High

**Success Criteria:**
- MCP server starts and responds to tool calls (requires `pip install codebase-shaker[mcp]`)
- `shake` tool returns valid output for a test repo
- `list_symbols` tool returns symbol list
- Context budget: per-file token consumption visible in stats; auto compression depth reduces output tokens when `enforce_max_tokens` is True
- `--max-tokens` warning-only behavior preserved when `enforce_max_tokens` is False (backward compatible)
- File scores: core modules score higher than one-off scripts; scoring works without git
- 20+ new tests for MCP server
- 15+ new tests for budget management
- 10+ new tests for file scoring (including git-optional fallback)

---

### Phase 4: Polish & Advanced Features
**Objective:** Add remaining high-value features and polish

**Deliverables:**
- [ ] `--stats FILE` flag — Write stats JSON to file
- [ ] `--preset` flag with `django`, `fastapi`, `flask` presets
- [ ] Multiple focus symbols (`--focus a --focus b`)
- [ ] Per-file compression control in config
- [ ] Git-aware output (recent commits, changed files)
- [ ] Circular import visualization in output
- [ ] Output validation (warn if output exceeds model context)
- [ ] Improved `--verbose` with debug logging throughout pipeline
- [ ] Performance: parallel file parsing for large repos

**Dependencies:** Phases 1-3

**Risks:** Low — all are isolated additions

**Complexity:** Medium

**Success Criteria:**
- Stats JSON file is valid and complete
- Presets work for their respective frameworks
- Multiple focus symbols resolve correctly
- Git metadata appears in output
- Circular imports highlighted in output
- Performance: 500 files < 3s
- 40+ new tests

---

### Phase 5: Release & Documentation
**Objective:** Final testing, documentation, and release

**Deliverables:**
- [ ] Full test suite passes (target: 700+ tests)
- [ ] mypy `--strict` clean
- [ ] ruff lint clean
- [ ] README updated with all new features
- [ ] CHANGELOG for v1.0.0
- [ ] Migration guide from v0 to v1
- [ ] PyPI release
- [ ] GitHub release with notes
- [ ] Sample `.shakerrc.json` with all options documented
- [ ] MCP server setup guide for Claude Code, Cursor

**Dependencies:** Phases 1-4 complete

**Risks:** Low

**Complexity:** Low

**Success Criteria:**
- All tests pass
- All linters pass
- README documents all features with examples
- PyPI package installs and runs correctly
- MCP server works with Claude Code


---

## 10. Implementation Priorities

### Critical (Must be in v1)

| Feature | Phase | Effort | Justification |
|---|---|---|---|
| Multi-format output (XML/JSON/plain) | 1 | Medium | #1 gap vs Repomix |
| `--quiet` flag | 1 | Trivial | Required for scripting |
| Progress bar | 1 | Low | Expected in modern CLI |
| Security scanning | 2 | Low-Medium | Prevents secret leaks |
| Remote repo support | 2 | Low-Medium | Expected in 2026 |
| MCP server mode | 3 | Medium | Integration standard |

### Important (Should be in v1)

| Feature | Phase | Effort | Justification |
|---|---|---|---|
| Context budget management | 3 | Medium-High | No competitor has this |
| File importance scoring | 3 | Medium | Makes no-focus mode smarter |
| `--stats` output file | 4 | Low | CI/CD integration |
| Config presets | 4 | Low | Better DX |
| Multiple focus symbols | 4 | Low | More flexible analysis |

### Nice-To-Have (If time permits in v1)

| Feature | Phase | Effort | Justification |
|---|---|---|---|
| Git-aware output | 4 | Medium | Useful LLM context |
| Circular import visualization | 4 | Low | Diagnostic value |
| Per-file compression control | 4 | Medium | Fine-grained control |
| Output validation | 4 | Low | Safety net |
| Parallel file parsing | 4 | Medium | Performance |

### Future (v2+)

| Feature | Version | Why Deferred |
|---|---|---|
| Multi-language (Tree-sitter) | 2.0 | Massive scope |
| LLM-powered compression | 2.0 | API cost/complexity |
| Watch mode | 2.0 | Daemon process |
| Web UI | 2.0 | Web framework needed |
| VS Code extension | 2.0 | Extension development |
| Diff mode | 2.0 | Complex change tracking |
| Knowledge graph visualization | 2.0 | Graphviz dependency |
| Enterprise features | 2.0 | Post-MVP |

---

## 11. Risk Analysis

### 11.1 Technical Risks

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| XML/JSON serializers produce invalid output | Low | High | Schema validation in tests; use `xml.etree.ElementTree` for XML generation |
| Security scanner false positives on test fixtures | Medium | Medium | Use markers in test data; document known patterns |
| MCP `mcp` package API instability | Low | Low | `mcp` is an optional dependency — Beta changes don't affect core tool; isolate MCP code for easy updates |
| Context budget iteration is too slow | Low | Medium | Set max iteration count; fall back to warning if budget can't be met |
| Remote clone fails for large repos | Medium | Low | Timeout with clear error; suggest manual clone |
| Git dependency for file scoring | Low | Low | Make git optional; fall back to static analysis only |

### 11.2 Product Risks

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Feature overload — v1 becomes too large | Medium | High | Strict phase gates; defer to v2 if phase exceeds estimate |
| Repomix adds all these features first | Low | Medium | Shaker's Python depth is the differentiator; focus on quality over breadth |
| MCP standard changes or fragments | Medium | Medium | MCP is backed by Anthropic, Cursor, Sourcegraph — unlikely to disappear |
| Users want multi-language immediately | Medium | Medium | Clear communication: Python-first is the strategy; multi-language is v2 |

### 11.3 Adoption Risks

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Low awareness vs Repomix (22K stars) | High | Medium | Focus on quality, unique features (budget management, security), Python community |
| Users don't see value over Repomix | Medium | High | Emphasize: deeper Python analysis, context budget management, security-first |
| pip install issues on Windows | Low | Medium | Test on Windows (primary dev platform); CI on all platforms |

### 11.4 UX Risks

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Too many flags overwhelm new users | Low | Medium | Sensible defaults; `--help` with examples; presets |
| Security scanning slows pipeline | Low | Low | Regex is fast; benchmark and optimize if needed |
| Progress bar adds complexity | Low | Low | Rich makes this trivial |

### 11.5 Maintenance Risks

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Secret patterns need frequent updates | Medium | Low | Make patterns configurable in `.shakerrc.json` |
| Output format changes break consumers | Low | Medium | Version output format; document schema |
| Test suite becomes too large/slow | Low | Low | Separate unit/integration; CI parallelism |


---

## 12. Recommended Scope & Final Strategy

### 12.1 Recommended Version 1 Scope

**The v1 that should be built includes Phases 1-3 + Phase 5:**

1. **Multi-format output** (XML, JSON, plain + markdown)
2. **Security scanning** (secret detection + redaction, on by default)
3. **Remote repo support** (clone from URL, secure cleanup)
4. **MCP server mode** (stdio transport, optional dependency)
5. **Context budget management** (per-file token reporting + auto compression depth, backward compatible)
6. **File importance scoring** (graph centrality + git-optional enhancement)
7. **CLI polish** (`--quiet`, progress bar, `--score-files`, `--init`, pipe auto-detection)
8. **Call graph summary** in output (reachability stats, zero additional computation)

**Total estimated new code:** ~2,500-3,500 lines across 8 new modules
**Total estimated new tests:** ~150-200 tests
**Estimated effort:** 6-10 weeks of focused development

### 12.2 Recommended Version 1 MVP

**If time is constrained, the absolute minimum v1 is:**

1. Multi-format output (at least XML + Markdown)
2. Security scanning (basic secret detection)
3. `--quiet` flag + progress bar
4. Version bump to 1.0.0

This is the "ship something good" baseline. It closes the biggest gaps vs Repomix while maintaining quality.

### 12.3 Recommended Version 1 Stretch Goals

**If Phase 1-3 complete ahead of schedule:**

1. Remote repo support
2. MCP server mode
3. `--stats` output file
4. Config presets
5. Multiple focus symbols

### 12.4 Recommended Version 2 Ideas

**For planning purposes, v2 should focus on:**

1. **Multi-language support** (Tree-sitter for JS/TS, Rust, Go)
2. **LLM-powered semantic compression** (opt-in, API-based)
3. **Watch mode** (file system watcher for incremental updates)
4. **Knowledge graph visualization** (interactive call graph)
5. **VS Code extension** (GUI for Shaker)
6. **Diff mode** (only output changed files since last run)
7. **Web UI** (browser-based interface)

### 12.5 Final Strategic Recommendation

**If I were the product owner, here is exactly what I would build next and why:**

#### Start with Phase 1: Multi-Format Output

This is the highest-ROI starting point because:
- It's self-contained (new serializer modules, no pipeline changes)
- It immediately closes the #1 gap vs Repomix
- It validates the architecture (if serializers are clean, everything else follows)
- It can be shipped as a mini-release if needed
- It builds confidence in the codebase

#### Then Phase 2: Security + Remote

Security scanning is a differentiator that no Python-focused tool has. It's also low-effort and high-impact. Remote support is expected in 2026 and easy to implement.

#### Then Phase 3: MCP + Budget Management

MCP server mode is the integration play — it makes Shaker a native tool in the AI assistant ecosystem. Context budget management is the innovation play — it's something no competitor does and directly addresses the #1 developer pain point.

#### Why This Order

1. **Technical dependency:** Output formats -> Security (needs format support) -> Budget (needs security to run before budget fitting) -> MCP (wraps the complete pipeline)
2. **User value:** Each phase delivers standalone value
3. **Risk management:** Each phase is independently shippable
4. **Momentum:** Early wins (format output) build confidence for harder problems (budget management)

#### The Core Thesis

**Codebase Shaker v1 should be the tool that Python developers reach for when they need their LLM to actually understand their code's structure — not just read its text.**

The call graph is Shaker's moat. No competitor builds a Python call graph with import resolution, class hierarchy analysis, and cycle detection. Every feature — focus resolution, file importance scoring, context budget management — is built on top of this structural understanding.

Security-first design (on-by-default secret scanning) keeps secrets safe. Context budget intelligence (per-file token visibility + auto compression depth) maximizes every token. Multiple output formats (XML, JSON, plain text, Markdown) fit any workflow. MCP server mode integrates with the AI assistant ecosystem.

Not a Repomix clone. Not a general-purpose packaging tool. The best Python codebase compressor for LLMs, period.

---

## Appendix A: Dependency Changes

### New Required Dependencies
No changes — all existing required dependencies remain:
```toml
[project.dependencies]
networkx>=3.0
pathspec>=0.12.0
click>=8.0
rich>=13.0
```

### New Optional Dependencies
```toml
[project.optional-dependencies]
# Existing
dev = [...]
# New
mcp = ["mcp>=1.0"]            # MCP server mode (Beta — kept optional for stability)
remote = ["gitpython>=3.0"]   # Alternative to subprocess for remote cloning
```
Install MCP support via: `pip install codebase-shaker[mcp]`

### New Dev Dependencies
```toml
[project.optional-dependencies]
dev = [
    # Existing...
    "lxml>=5.0",     # XML validation in tests
]
```

## Appendix B: File Tree (Target v1)

```
src/shaker/
+-- __init__.py              # version = "1.0.0"
+-- __main__.py
+-- models.py                # +OutputFormat, +SecurityFinding, +FileScore, +SecurityReport
+-- constants.py             # +secret patterns, +output format defaults
+-- cli.py                   # +--format, +--remote, +--mcp, +--quiet, +--no-progress,
+--                         #  +--security-scan, +--security-redact, +--stats, +--preset,
+--                         #  +--score-files, progress bar
+-- engine/
|   +-- __init__.py          # +re-exports
|   +-- discovery.py         # unchanged
|   +-- parser.py            # unchanged
|   +-- graph.py             # unchanged
|   +-- resolver.py          # +multiple focus symbols
|   +-- pruner.py            # +budget-aware compression
|   +-- scoring.py           # NEW: File importance scoring
|   +-- security.py          # NEW: Secret detection and redaction
|   +-- remote.py            # NEW: Remote repo cloning
+-- infra/
|   +-- __init__.py
|   +-- config.py            # +new config fields
|   +-- tokens.py            # unchanged
+-- output/
|   +-- __init__.py          # +re-exports
|   +-- serializer.py        # Markdown (existing)
|   +-- xml_serializer.py    # NEW: XML output
|   +-- json_serializer.py   # NEW: JSON output
|   +-- plain_serializer.py  # NEW: Plain text output
+-- mcp/
    +-- server.py            # NEW: MCP server mode
```

## Appendix C: Test Plan (Target v1)

Test quality (behavioral coverage) matters more than test quantity. All new features must have:

- **Unit tests** for all public functions, covering happy path, edge cases, and error conditions
- **Integration tests** for end-to-end behavior (e.g., "run shaker with --format xml on test fixture, validate output")
- **Regression tests** for any bug fixes

| Module | Key Behaviors to Test |
|---|---|
| `xml_serializer.py` | Valid XML output, CDATA handling, all metadata fields present, roundtrip parseable |
| `json_serializer.py` | Valid JSON output, all metadata fields present, parseable by `json.loads()` |
| `plain_serializer.py` | No Markdown syntax, readable output, all files included |
| `security.py` | All 5 secret pattern categories detected, redaction replaces with `[REDACTED]`, configurable warn vs redact, false positive handling |
| `remote.py` | Clone from public URL, cleanup on success, cleanup on error, cleanup on SIGINT, timeout handling |
| `scoring.py` | Scoring works without git, scoring enhanced with git, core modules score higher than utilities, graceful fallback in CI |
| `pruner.py` (budget) | Auto compression depth selection at different ratios, focus files always full detail, backward compatible warning-only mode |
| `mcp/server.py` | Tool listing, shake tool returns valid output, list_symbols returns symbols, graceful error for invalid path |
| `cli.py` (new flags) | All new flags work individually and in combination, `--quiet` suppresses stats, `--init` generates template, pipe auto-detection |
| `config.py` (new fields) | New config fields load correctly, validation rejects invalid values, CLI override works |

**Existing tests:** 530 (431 unit + 99 integration) — all must continue to pass.

---

*End of Version 1.0 Roadmap*
*This document is the source of truth for Version 1 development.*
