"""Stage 3: Call graph construction.

Builds a symbol table from parsed files, constructs a networkx DiGraph of
symbol dependencies, resolves call sites against the symbol table, and
detectes cycles. Handles unresolvable symbols (builtins, stdlib, dynamic)
gracefully by recording them in CallGraph.unresolved_calls.
"""

from __future__ import annotations

from pathlib import Path

import networkx as nx  # type: ignore[import-untyped]

from shaker.constants import BUILTIN_NAMES, STDLIB_MODULES
from shaker.models import (
    CallGraph,
    CallSite,
    ImportInfo,
    ParsedFile,
    Symbol,
    SymbolType,
)


def build_graph(parsed: dict[Path, ParsedFile]) -> CallGraph:
    """Build a call graph from parsed files.

    Constructs a symbol table mapping qualified names to Symbol objects,
    then resolves all call sites against the symbol table to produce
    directed edges. Detects cycles and records unresolvable calls.

    Args:
        parsed: Dict mapping file paths to ParsedFile objects (from parser.py).

    Returns:
        A CallGraph with the constructed DiGraph, symbol table, and metadata.
    """
    symbol_table = _build_symbol_table(parsed)
    graph = nx.DiGraph()
    unresolved: list[CallSite] = []

    for qualified_name, symbol in symbol_table.items():
        graph.add_node(qualified_name, symbol=symbol)

    for _fpath, parsed_file in parsed.items():
        import_map = _build_import_map(parsed_file.imports)
        caller_symbols = [
            s for s in parsed_file.symbols if _is_callable(s)
        ]
        module_prefix = f"{parsed_file.module_name}."

        for call_site in parsed_file.call_sites:
            resolved = _resolve_call(
                call_site, import_map, symbol_table, module_prefix,
            )
            if resolved is None:
                if _is_builtin(call_site.name):
                    continue
                unresolved.append(call_site)
                continue

            if resolved not in symbol_table:
                unresolved.append(call_site)
                continue

            for caller in caller_symbols:
                if caller.qualified_name == resolved:
                    continue
                graph.add_edge(caller.qualified_name, resolved)

    cycles = _detect_cycles(graph)

    return CallGraph(
        graph=graph,
        symbol_table=symbol_table,
        unresolved_calls=unresolved,
        cycles=cycles,
    )


def get_callers(graph: CallGraph, symbol: str) -> set[str]:
    """Get all callers of a symbol.

    Returns the set of qualified names that have an edge pointing
    to the given symbol.

    Args:
        graph: The CallGraph to query.
        symbol: Qualified name of the symbol.

    Returns:
        Set of qualified names of all callers. Empty set if the symbol
        is not in the graph or has no callers.
    """
    if symbol not in graph.graph:
        return set()
    return set(graph.graph.predecessors(symbol))


def get_callees(graph: CallGraph, symbol: str) -> set[str]:
    """Get all callees of a symbol.

    Returns the set of qualified names that the given symbol has an
    edge pointing to.

    Args:
        graph: The CallGraph to query.
        symbol: Qualified name of the symbol.

    Returns:
        Set of qualified names of all callees. Empty set if the symbol
        is not in the graph or has no callees.
    """
    if symbol not in graph.graph:
        return set()
    return set(graph.graph.successors(symbol))


def _build_symbol_table(parsed: dict[Path, ParsedFile]) -> dict[str, Symbol]:
    """Build a symbol table from parsed files.

    Creates a mapping from qualified names to Symbol objects.
    Duplicate qualified names (from @property, @overload, etc.) are
    silently skipped — the first definition wins.

    Args:
        parsed: Dict mapping file paths to ParsedFile objects.

    Returns:
        Dict mapping qualified names to Symbol objects.
    """
    table: dict[str, Symbol] = {}

    for _fpath, parsed_file in parsed.items():
        for symbol in parsed_file.symbols:
            qname = symbol.qualified_name
            if qname in table:
                continue
            table[qname] = symbol

    return table


def _build_import_map(imports: list[ImportInfo]) -> dict[str, str]:
    """Build a local-name → qualified-module-name mapping from imports.

    Handles:
    - ``import os`` → ``{"os": "os"}``
    - ``import os.path`` → ``{"os": "os"}``
    - ``import numpy as np`` → ``{"np": "numpy"}``
    - ``from os.path import join`` → ``{"join": "os.path"}``
    - ``from .utils import helper`` → ``{"helper": ""}`` (relative, unresolved)
    - ``from foo import *`` → empty dict (wildcard, conservative)

    The returned values are the *module* names, not the final symbol names.
    The resolver combines these with the call site name to look up symbols.

    Args:
        imports: List of ImportInfo objects from a single file.

    Returns:
        Dict mapping local names to module-level qualified names.
    """
    mapping: dict[str, str] = {}

    for imp in imports:
        if imp.is_wildcard:
            continue

        if imp.alias is not None:
            mapping[imp.alias] = imp.module
        elif not imp.is_relative:
            for name in imp.names:
                mapping[name] = imp.module
            if not imp.names:
                top_level = imp.module.split(".")[0]
                mapping[top_level] = imp.module

    return mapping


def _resolve_call(
    call: CallSite,
    import_map: dict[str, str],
    symbol_table: dict[str, Symbol],
    module_prefix: str = "",
) -> str | None:
    """Resolve a call site against the symbol table using the import map.

    Resolution strategy:
    1. Simple name (e.g., ``join()``):
       - Look up bare name in symbol_table (already qualified)
       - Look up via import_map: ``{module}.{name}`` in symbol_table
       - If intra-file, try ``{module_prefix}{name}`` in symbol_table
    2. Method call (e.g., ``obj.method()``):
       - Look up bare method name in symbol_table
       - Resolve receiver via import_map

    Conservative: when ambiguous, returns None rather than guessing wrong.

    Args:
        call: The CallSite to resolve.
        import_map: Local-name → module mapping from _build_import_map().
        symbol_table: Qualified-name → Symbol mapping.
        module_prefix: Module prefix for intra-file resolution (e.g. "test.").

    Returns:
        Qualified name of the resolved symbol, or None if unresolvable.
    """
    if call.is_method and call.receiver is not None:
        name = call.name

        if name in symbol_table:
            return name

        receiver = call.receiver
        if "." in receiver:
            last_part = receiver.rsplit(".", 1)[-1]
            if last_part in import_map:
                module = import_map[last_part]
                candidate = f"{module}.{name}"
                if candidate in symbol_table:
                    return candidate
            receiver_base = receiver.split(".")[0]
            if receiver_base in import_map:
                module = import_map[receiver_base]
                candidate = f"{module}.{name}"
                if candidate in symbol_table:
                    return candidate
        else:
            if receiver in import_map:
                module = import_map[receiver]
                candidate = f"{module}.{name}"
                if candidate in symbol_table:
                    return candidate

        if name in symbol_table:
            return name

        return None

    name = call.name

    if name in symbol_table:
        return name

    if name in import_map:
        module = import_map[name]
        candidate = f"{module}.{name}"
        if candidate in symbol_table:
            return candidate

    if module_prefix:
        intra_candidate = f"{module_prefix}{name}"
        if intra_candidate in symbol_table:
            return intra_candidate

    return None


def _is_callable(symbol: Symbol) -> bool:
    """Check if a symbol represents a callable (function or method).

    Classes are not directly callable in the call graph sense — method
    calls on instances are handled through the method symbols themselves.

    Args:
        symbol: The Symbol to check.

    Returns:
        True if the symbol is a function or method.
    """
    return symbol.symbol_type in (SymbolType.FUNCTION, SymbolType.METHOD)


def _detect_cycles(graph: nx.DiGraph, max_scc_size: int = 10) -> list[list[str]]:
    """Detect cycles in the call graph using bounded SCC enumeration.

    Finds strongly connected components (SCCs) and enumerates elementary
    cycles only within small SCCs (≤ max_scc_size nodes). Larger SCCs
    produce a single summary entry instead, preventing exponential
    blowup on real-world codebases.

    Args:
        graph: The DiGraph to analyze.
        max_scc_size: Maximum SCC size for full cycle enumeration.
            SCCs larger than this produce a single summary entry.

    Returns:
        List of cycles, where each cycle is a list of qualified names.
        Large SCCs produce a single entry like ["scc:N:node1", "scc:N:node2", ...].
        Empty list if no cycles exist.
    """
    cycles: list[list[str]] = []
    for scc in nx.strongly_connected_components(graph):
        if len(scc) <= 1:
            # Check for self-loop
            node = next(iter(scc))
            if graph.has_edge(node, node):
                cycles.append([node])
            continue
        if len(scc) <= max_scc_size:
            subgraph = graph.subgraph(scc)
            cycles.extend(list(cycle) for cycle in nx.simple_cycles(subgraph))
        else:
            # Large SCC: record summary instead of enumerating exponentially
            nodes = sorted(scc)
            cycles.append([f"scc:{len(scc)}:{n}" for n in nodes])
    return cycles


def _is_builtin(name: str) -> bool:
    """Check if *name* is a Python builtin.

    Args:
        name: The name to check.

    Returns:
        True if the name is in Python's builtins.
    """
    return name in BUILTIN_NAMES


def _is_stdlib_module(module: str) -> bool:
    """Check if *module* is part of the Python standard library.

    Args:
        module: The module name (e.g., ``os.path``).

    Returns:
        True if the top-level package is in the stdlib set.
    """
    if not module:
        return False
    top_level = module.split(".")[0]
    return top_level in STDLIB_MODULES
