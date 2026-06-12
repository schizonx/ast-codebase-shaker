"""Pipeline engine modules for Codebase Shaker.

Discovery, parsing, graph building, resolution, pruning, scoring,
security scanning, and remote repo support.
"""

from shaker.engine.discovery import discover_files
from shaker.engine.graph import build_graph, get_callees, get_callers
from shaker.engine.parser import parse_files
from shaker.engine.pruner import prune_files
from shaker.engine.remote import clone_remote
from shaker.engine.resolver import (
    FocusDirection,
    resolve_focus,
    resolve_focus_files,
    suggest_symbols,
)
from shaker.engine.scoring import score_files
from shaker.engine.security import (
    redact_report,
    scan_file,
    scan_files,
)

__all__ = [
    "FocusDirection",
    "build_graph",
    "clone_remote",
    "discover_files",
    "get_callers",
    "get_callees",
    "parse_files",
    "prune_files",
    "redact_report",
    "resolve_focus",
    "resolve_focus_files",
    "scan_file",
    "scan_files",
    "score_files",
    "suggest_symbols",
]
