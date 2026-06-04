"""Pipeline engine modules for Codebase Shaker.

Discovery, parsing, graph building, resolution, and pruning.
"""

from shaker.engine.discovery import discover_files
from shaker.engine.graph import build_graph, get_callees, get_callers
from shaker.engine.parser import parse_files
from shaker.engine.pruner import prune_files
from shaker.engine.resolver import (
    FocusDirection,
    resolve_focus,
    resolve_focus_files,
    suggest_symbols,
)

__all__ = [
    "FocusDirection",
    "build_graph",
    "discover_files",
    "get_callers",
    "get_callees",
    "parse_files",
    "prune_files",
    "resolve_focus",
    "resolve_focus_files",
    "suggest_symbols",
]
