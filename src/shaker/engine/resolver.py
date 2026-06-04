"""Stage 4: Focus resolution and subgraph extraction.

Given a focal symbol name, extracts the relevant subgraph from a CallGraph
by performing bidirectional BFS (callers + callees). Maps the resulting
symbols back to file paths for downstream pruning. Provides fuzzy symbol
suggestions when the focal symbol is not found.
"""

from __future__ import annotations

import difflib
from pathlib import Path

import networkx as nx  # type: ignore[import-untyped]

from shaker.models import CallGraph, ParsedFile


class FocusDirection:
    """Direction for focus resolution traversal."""

    BOTH = "both"
    CALLERS = "callers"
    CALLEES = "callees"


def resolve_focus(
    graph: CallGraph,
    focus: str,
    direction: str = FocusDirection.BOTH,
    max_depth: int | None = None,
) -> set[str]:
    """Resolve the focus set from a call graph.

    Performs a traversal starting from *focus* and collecting symbols
    within the given *direction* and *max_depth*.

    Args:
        graph: The CallGraph to search.
        focus: Qualified name of the focal symbol.
        direction: Traversal direction — ``"both"`` (default),
            ``"callers"``, or ``"callees"``.
        max_depth: Maximum number of hops from *focus*. ``None``
            means unlimited (full traversal).

    Returns:
        Set of qualified names in the focus set. Returns an empty set
        if *focus* is not in the graph.
    """
    if focus not in graph.graph:
        return set()

    if max_depth is not None and max_depth < 0:
        max_depth = None

    descendants: set[str] = _bounded_traversal(
        graph.graph, focus, "out", max_depth
    )
    ancestors: set[str] = _bounded_traversal(
        graph.graph, focus, "in", max_depth
    )

    if direction == FocusDirection.CALLEES:
        return {focus} | descendants
    if direction == FocusDirection.CALLERS:
        return {focus} | ancestors
    return {focus} | descendants | ancestors


def _bounded_traversal(
    graph: nx.DiGraph,
    start: str,
    direction: str,
    max_depth: int | None,
) -> set[str]:
    """Traverse the graph from *start* up to *max_depth* hops.

    Uses BFS layering to respect the depth limit.

    Args:
        graph: The DiGraph to traverse.
        start: Starting node.
        direction: ``"out"`` for callees (successors),
            ``"in"`` for callers (predecessors).
        max_depth: Maximum hops. None means unlimited.

    Returns:
        Set of reachable node names, excluding *start*.
    """
    if start not in graph:
        return set()

    if max_depth is None:
        if direction == "out":
            return set(nx.descendants(graph, start))
        return set(nx.ancestors(graph, start))

    # BFS with depth tracking
    visited: set[str] = set()
    current_layer: set[str] = {start}
    for _ in range(max_depth):
        next_layer: set[str] = set()
        for node in current_layer:
            neighbors = (
                graph.successors(node)
                if direction == "out"
                else graph.predecessors(node)
            )
            for n in neighbors:
                if n not in visited and n != start:
                    visited.add(n)
                    next_layer.add(n)
        current_layer = next_layer
        if not current_layer:
            break
    return visited


def resolve_focus_files(
    focus_symbols: set[str],
    parsed: dict[Path, ParsedFile],
) -> set[Path]:
    """Map focus symbols back to the files that contain them.

    Scans all parsed files and returns the set of file paths where at
    least one focus symbol is defined. This tells the pruner which
    files should be preserved at full detail.

    Args:
        focus_symbols: Set of qualified names from resolve_focus().
        parsed: Dict mapping file paths to ParsedFile objects.

    Returns:
        Set of file paths that contain at least one focus symbol.
        Includes files where focus symbols appear in the symbol_table
        even if they have no direct definition (conservative: if the
        symbol_table maps to a file, include it).
    """
    focus_files: set[Path] = set()

    for fpath, parsed_file in parsed.items():
        for symbol in parsed_file.symbols:
            if symbol.qualified_name in focus_symbols:
                focus_files.add(fpath)
                break

    return focus_files


def suggest_symbols(
    graph: CallGraph,
    query: str,
    limit: int = 10,
) -> list[str]:
    """Suggest symbol names matching *query*.

    Uses difflib's fuzzy matching to find the closest symbol names
    in the graph. Useful when the user provides a --focus that
    doesn't exist.

    Args:
        graph: The CallGraph to search for candidate symbols.
        query: The focal symbol name the user provided.
        limit: Maximum number of suggestions to return.

    Returns:
        List of suggested qualified names, ordered by match quality.
        Returns an empty list if the graph is empty.
    """
    candidates = list(graph.graph.nodes)
    if not candidates:
        return []

    direct_matches = difflib.get_close_matches(query, candidates, n=limit)
    if direct_matches:
        return direct_matches

    bare_query = query.split(".")[-1] if "." in query else query
    bare_to_qname: dict[str, list[str]] = {}
    for qname in candidates:
        bare = qname.rsplit(".", 1)[-1]
        bare_to_qname.setdefault(bare, []).append(qname)

    close_bare = difflib.get_close_matches(
        bare_query, list(bare_to_qname), n=limit
    )
    suggestions: list[str] = []
    seen: set[str] = set()
    for bare in close_bare:
        for qname in bare_to_qname[bare]:
            if qname not in seen:
                seen.add(qname)
                suggestions.append(qname)
                if len(suggestions) >= limit:
                    break
        if len(suggestions) >= limit:
            break
    if suggestions:
        return suggestions

    return candidates[:limit]


def _bfs(
    graph: nx.DiGraph,
    start: str,
    direction: str = "out",
) -> set[str]:
    """Perform BFS from *start* in the given direction.

    Args:
        graph: The DiGraph to traverse.
        start: Starting node.
        direction: ``"out"`` for callees (successors),
            ``"in"`` for callers (predecessors).

    Returns:
        Set of node names reachable from *start* in the
        given direction, excluding *start* itself.
    """
    if start not in graph:
        return set()
    if direction == "out":
        return set(nx.descendants(graph, start))
    return set(nx.ancestors(graph, start))


def _fuzzy_match(
    query: str,
    candidates: list[str],
    limit: int = 10,
) -> list[str]:
    """Return fuzzy matches for *query* from *candidates*.

    Thin wrapper around difflib.get_close_matches for testability.

    Args:
        query: The search string.
        candidates: List of strings to match against.
        limit: Maximum number of matches.

    Returns:
        List of the best matching candidates.
    """
    return difflib.get_close_matches(query, candidates, n=limit)


