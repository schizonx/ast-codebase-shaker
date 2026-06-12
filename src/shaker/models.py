"""Shared data models for Codebase Shaker.

All dataclasses and enums used across the codebase are defined here.
This module imports nothing from the project to prevent circular imports.

Every other module in the codebase depends on this module.
It must remain a pure data module with zero business logic.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import networkx as nx  # type: ignore[import-untyped]


class CompressionMode(Enum):
    """Compression mode for non-focus files in the output.

    Determines how aggressively code is compressed when serialized
    to the Markdown output. Focus files are always kept at full detail.
    """

    FULL = "full"
    SIGNATURES = "signatures"
    STRIP = "strip"


class OutputFormat(Enum):
    """Output serialization format."""

    MARKDOWN = "markdown"
    XML = "xml"
    JSON = "json"
    PLAIN = "plain"


class SymbolType(Enum):
    """Classification of extracted symbols for the call graph.

    Used to distinguish between different kinds of named entities
    found in Python source files.
    """

    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"


@dataclass(frozen=True)
class ImportInfo:
    """A single import statement extracted from a Python source file.

    Records enough detail to resolve imported names back to their
    source modules during call graph construction.

    Frozen: import statements are immutable value objects.

    Validation:
        - If is_wildcard is True, names should be empty.
        - If is_relative is True, level must be > 0.
    """

    module: str
    names: tuple[str, ...]
    alias: str | None = None
    is_wildcard: bool = False
    is_relative: bool = False
    level: int = 0
    line_number: int = 0


@dataclass(frozen=True)
class CallSite:
    """A function or method call site found within a function body.

    Represents a single call expression. The qualified_name field
    is populated during graph construction once the call is resolved
    against the symbol table.

    Frozen: call sites are immutable value objects.
    """

    name: str
    qualified_name: str | None = None
    line_number: int = 0
    is_method: bool = False
    receiver: str | None = None


@dataclass(frozen=True)
class Symbol:
    """A named entity found in a Python source file.

    Represents a class, function, or method definition. The qualified_name
    is built from the module path and symbol hierarchy (e.g.,
    ``src.models.user.User.check_password``).

    Frozen: symbols are immutable value objects.

    Validation:
        - qualified_name must be unique within a codebase.
        - For methods, parent must be set to the class qualified name.
    """

    name: str
    qualified_name: str
    symbol_type: SymbolType
    file: Path
    line_number: int = 0
    decorators: tuple[str, ...] = ()
    parent: str | None = None
    is_async: bool = False
    docstring: str | None = None


@dataclass
class ParsedFile:
    """The result of parsing a single Python source file.

    Contains all extracted symbols, imports, and call sites, along
    with the original source and the raw AST for downstream use.

    Mutable: the parser populates fields incrementally during AST walking.

    Validation:
        - If parse_error is set, symbols/imports/call_sites may be empty.
    """

    path: Path
    module_name: str
    symbols: list[Symbol] = field(default_factory=list)
    imports: list[ImportInfo] = field(default_factory=list)
    call_sites: list[CallSite] = field(default_factory=list)
    source: str = ""
    ast_tree: ast.Module | None = None
    parse_error: str | None = None
    encoding: str = "utf-8"


@dataclass
class CallGraph:
    """The call graph built from all parsed files.

    Contains a directed graph of symbol dependencies, a symbol table
    mapping qualified names to Symbol objects, and metadata about
    unresolved calls and detected cycles.

    Mutable: the graph builder populates fields incrementally.

    Validation:
        - All symbols in symbol_table should have corresponding graph nodes.
    """

    graph: nx.DiGraph
    symbol_table: dict[str, Symbol]
    unresolved_calls: list[CallSite] = field(default_factory=list)
    cycles: list[list[str]] = field(default_factory=list)


@dataclass
class BuildStats:
    """Statistics about a single build run.

    Accumulated as the pipeline progresses through all seven stages.
    Displayed in the terminal UI as the before/after summary table.
    """

    total_files: int = 0
    retained_files: int = 0
    omitted_files: int = 0
    parse_errors: int = 0
    total_lines: int = 0
    output_lines: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    reduction_pct: float = 0.0

    @property
    def files_reduction_pct(self) -> float:
        """Percentage of files excluded from the output."""
        if self.total_files == 0:
            return 0.0
        return (1 - self.retained_files / self.total_files) * 100


@dataclass
class OutputMetadata:
    """Metadata about the build, included in the Markdown output header.

    Produced by the CLI and consumed by the serializer to construct
    the header section of the output document.
    """

    project_name: str
    focus: str | None
    mode: CompressionMode
    config_path: Path | None
    timestamp: str
    version: str
    stats: BuildStats


@dataclass
class Config:
    """Application configuration from .shakerrc.json and CLI arguments.

    CLI arguments take precedence over config file values.
    Created by the config loader, used by all pipeline stages.

    Default mode is SIGNATURES since this is the most useful mode
    for LLM context reduction.
    """

    default_mode: CompressionMode = CompressionMode.SIGNATURES
    exclude_patterns: tuple[str, ...] = ()
    max_tokens: int | None = None
    always_include: tuple[str, ...] = ()
    always_exclude: tuple[str, ...] = ()
    config_path: Path | None = None
    output_format: OutputFormat = OutputFormat.MARKDOWN
    security_scan: bool = True
    security_redact: bool = True
    show_progress: bool = True
    quiet: bool = False
    enforce_max_tokens: bool = False
    use_git_scoring: bool = True


@dataclass
class DeliveryResult:
    """Result of the delivery phase (clipboard + file output).

    Produced by clipboard.py, consumed by cli.py for status display.
    """

    clipboard_success: bool = False
    file_path: Path | None = None
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SecurityFinding:
    """A potential secret or sensitive data found in source code."""

    file: Path
    line_number: int
    finding_type: str
    severity: str
    redacted: bool = False


@dataclass
class FileScore:
    """Importance score for a single file."""

    file: Path
    score: float
    importer_count: int
    centrality: float
    git_changes_30d: int = 0
    is_focus: bool = False


@dataclass
class SecurityReport:
    """Results of security scanning."""

    findings: list[SecurityFinding] = field(default_factory=list)
    total_scanned: int = 0
    total_findings: int = 0
    critical_count: int = 0
    redacted_count: int = 0


@dataclass
class PipelineState:
    """Mutable state container that flows through the all seven pipeline stages.

    Created by the CLI with the initial configuration, then mutated
    by each stage in sequence. After all stages complete, the CLI reads
    the final state for display and output.

    Each field corresponds to the output of one or more pipeline stages:
        - discovered_files: Stage 1 (discovery)
        - parsed_files: Stage 2 (parser)
        - call_graph: Stage 3 (graph builder)
        - focus_symbols/focus_files: Stage 4 (resolver)
        - pruned_files/omitted_files: Stage 5 (pruner)
        - output: Stage 6 (serializer)
        - delivery: Stage 7 (clipboard)

    All mutable defaults use field(default_factory=...) to ensure
    each PipelineState instance gets its own independent collections.
    """

    config: Config
    root_path: Path = field(default_factory=Path.cwd)
    focus: str | None = None
    discovered_files: list[Path] = field(default_factory=list)
    parsed_files: dict[Path, ParsedFile] = field(default_factory=dict)
    call_graph: CallGraph | None = None
    focus_symbols: set[str] = field(default_factory=set)
    focus_files: set[Path] = field(default_factory=set)
    pruned_files: dict[Path, str] = field(default_factory=dict)
    omitted_files: list[Path] = field(default_factory=list)
    output: str = ""
    delivery: DeliveryResult | None = None
    stats: BuildStats = field(default_factory=BuildStats)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    security_report: SecurityReport | None = None
    file_scores: dict[Path, FileScore] = field(default_factory=dict)


__all__ = [
    "BuildStats",
    "CallGraph",
    "CallSite",
    "CompressionMode",
    "Config",
    "DeliveryResult",
    "FileScore",
    "ImportInfo",
    "OutputFormat",
    "OutputMetadata",
    "ParsedFile",
    "PipelineState",
    "SecurityFinding",
    "SecurityReport",
    "Symbol",
    "SymbolType",
]
