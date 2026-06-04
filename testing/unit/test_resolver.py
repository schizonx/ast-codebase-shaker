"""Unit tests for shaker.engine.resolver.

Covers focus resolution (bidirectional BFS), symbol-to-file mapping,
fuzzy suggestions, and edge cases.
"""

from __future__ import annotations

from pathlib import Path

import networkx as nx

from shaker.engine.resolver import (
    FocusDirection,
    _bfs,
    _bounded_traversal,
    _fuzzy_match,
    resolve_focus,
    resolve_focus_files,
    suggest_symbols,
)
from shaker.models import CallGraph, ParsedFile, Symbol, SymbolType


def _make_graph(edges: list[tuple[str, str]] | None = None) -> CallGraph:
    """Helper: build a CallGraph from edge list."""
    graph = nx.DiGraph()
    if edges:
        graph.add_edges_from(edges)
    return CallGraph(
        graph=graph,
        symbol_table={},
        unresolved_calls=[],
        cycles=[],
    )


def _make_graph_with_nodes(
    nodes: list[str],
    edges: list[tuple[str, str]],
) -> CallGraph:
    """Helper: build a CallGraph with explicit nodes and edges."""
    graph = nx.DiGraph()
    graph.add_nodes_from(nodes)
    graph.add_edges_from(edges)
    return CallGraph(
        graph=graph,
        symbol_table={n: _stub_symbol(n) for n in nodes},
        unresolved_calls=[],
        cycles=[],
    )


def _stub_symbol(qualified_name: str) -> Symbol:
    """Helper: create a minimal Symbol for testing."""
    return Symbol(
        name=qualified_name.rsplit(".", 1)[-1],
        qualified_name=qualified_name,
        symbol_type=SymbolType.FUNCTION,
        file=Path("test.py"),
    )


class TestResolveFocus:
    """Tests for resolve_focus."""

    def test_empty_graph(self):
        graph = _make_graph()
        assert resolve_focus(graph, "anything") == set()

    def test_focus_not_in_graph(self):
        graph = _make_graph_with_nodes(["a", "b"], [("a", "b")])
        assert resolve_focus(graph, "nonexistent") == set()

    def test_focus_includes_self(self):
        graph = _make_graph_with_nodes(["a", "b"], [("a", "b")])
        result = resolve_focus(graph, "a")
        assert "a" in result

    def test_leaf_node_only_self_and_callers(self):
        graph = _make_graph_with_nodes(
            ["a", "b", "c"],
            [("a", "c"), ("b", "c")],
        )
        result = resolve_focus(graph, "c")
        assert result == {"a", "b", "c"}

    def test_root_node_self_and_all_callees(self):
        graph = _make_graph_with_nodes(
            ["root", "mid", "leaf"],
            [("root", "mid"), ("mid", "leaf")],
        )
        result = resolve_focus(graph, "root")
        assert result == {"root", "mid", "leaf"}

    def test_middle_node_both_directions(self):
        graph = _make_graph_with_nodes(
            ["a", "b", "c"],
            [("a", "b"), ("b", "c")],
        )
        result = resolve_focus(graph, "b")
        assert result == {"a", "b", "c"}

    def test_focus_in_cycle_terminates(self):
        graph = _make_graph_with_nodes(
            ["a", "b", "c"],
            [("a", "b"), ("b", "c"), ("c", "a")],
        )
        result = resolve_focus(graph, "a")
        assert result == {"a", "b", "c"}

    def test_isolated_node(self):
        graph = _make_graph_with_nodes(["a", "b"], [("a", "b")])
        result = resolve_focus(graph, "a")
        assert "b" in result

    def test_focus_independent_of_direction(self):
        graph = _make_graph_with_nodes(
            ["caller", "target", "callee"],
            [("caller", "target"), ("target", "callee")],
        )
        result = resolve_focus(graph, "target")
        assert "caller" in result
        assert "callee" in result
        assert "target" in result


class TestResolveFocusFiles:
    """Tests for resolve_focus_files."""

    def test_empty_symbols(self):
        parsed = {Path("a.py"): ParsedFile(path=Path("a.py"), module_name="a")}
        assert resolve_focus_files(set(), parsed) == set()

    def test_single_symbol_single_file(self):
        sym = _stub_symbol("mod.func")
        parsed = {
            Path("mod.py"): ParsedFile(
                path=Path("mod.py"), module_name="mod", symbols=[sym]
            )
        }
        result = resolve_focus_files({"mod.func"}, parsed)
        assert result == {Path("mod.py")}

    def test_multiple_symbols_same_file(self):
        s1 = _stub_symbol("mod.func_a")
        s2 = _stub_symbol("mod.func_b")
        parsed = {
            Path("mod.py"): ParsedFile(
                path=Path("mod.py"), module_name="mod", symbols=[s1, s2]
            )
        }
        result = resolve_focus_files({"mod.func_a", "mod.func_b"}, parsed)
        assert result == {Path("mod.py")}

    def test_symbols_across_files(self):
        s1 = _stub_symbol("mod_a.func")
        s2 = _stub_symbol("mod_b.func")
        parsed = {
            Path("mod_a.py"): ParsedFile(
                path=Path("mod_a.py"), module_name="mod_a", symbols=[s1]
            ),
            Path("mod_b.py"): ParsedFile(
                path=Path("mod_b.py"), module_name="mod_b", symbols=[s2]
            ),
        }
        result = resolve_focus_files({"mod_a.func", "mod_b.func"}, parsed)
        assert result == {Path("mod_a.py"), Path("mod_b.py")}

    def test_partial_match(self):
        s1 = _stub_symbol("mod_a.func")
        s2 = _stub_symbol("mod_b.func")
        parsed = {
            Path("mod_a.py"): ParsedFile(
                path=Path("mod_a.py"), module_name="mod_a", symbols=[s1]
            ),
            Path("mod_b.py"): ParsedFile(
                path=Path("mod_b.py"), module_name="mod_b", symbols=[s2]
            ),
        }
        result = resolve_focus_files({"mod_a.func"}, parsed)
        assert result == {Path("mod_a.py")}

    def test_no_matching_symbols(self):
        s1 = _stub_symbol("mod_a.func")
        parsed = {
            Path("mod_a.py"): ParsedFile(
                path=Path("mod_a.py"), module_name="mod_a", symbols=[s1]
            ),
        }
        result = resolve_focus_files({"nonexistent.func"}, parsed)
        assert result == set()


class TestSuggestSymbols:
    """Tests for suggest_symbols."""

    def test_empty_graph(self):
        graph = _make_graph()
        assert suggest_symbols(graph, "anything") == []

    def test_exact_match(self):
        graph = _make_graph_with_nodes(
            ["auth.login", "auth.logout", "db.query"], []
        )
        result = suggest_symbols(graph, "auth.login")
        assert "auth.login" in result

    def test_close_match(self):
        graph = _make_graph_with_nodes(
            ["auth.authenticate", "auth.authorize", "db.query"], []
        )
        result = suggest_symbols(graph, "auth.authentcate")
        assert "auth.authenticate" in result

    def test_bare_name_match(self):
        graph = _make_graph_with_nodes(
            ["auth.authenticate", "db.authenticate", "utils.helper"], []
        )
        result = suggest_symbols(graph, "authenticate")
        assert "auth.authenticate" in result or "db.authenticate" in result

    def test_limit_respected(self):
        nodes = [f"mod.func_{i}" for i in range(20)]
        graph = _make_graph_with_nodes(nodes, [])
        result = suggest_symbols(graph, "func", limit=5)
        assert len(result) <= 5

    def test_no_match_returns_candidates(self):
        graph = _make_graph_with_nodes(["aaa", "bbb", "ccc"], [])
        result = suggest_symbols(graph, "zzz")
        assert len(result) > 0

    def test_limit_default_is_10(self):
        nodes = [f"mod.func_{i}" for i in range(20)]
        graph = _make_graph_with_nodes(nodes, [])
        result = suggest_symbols(graph, "func")
        assert len(result) <= 10


class TestBfs:
    """Tests for _bfs internal function."""

    def test_out_direction(self):
        graph = nx.DiGraph()
        graph.add_edges_from([("a", "b"), ("b", "c")])
        result = _bfs(graph, "a", "out")
        assert result == {"b", "c"}

    def test_in_direction(self):
        graph = nx.DiGraph()
        graph.add_edges_from([("a", "b"), ("b", "c")])
        result = _bfs(graph, "c", "in")
        assert result == {"a", "b"}

    def test_start_not_in_graph(self):
        graph = nx.DiGraph()
        graph.add_node("x")
        result = _bfs(graph, "missing", "out")
        assert result == set()

    def test_cycle_terminates(self):
        graph = nx.DiGraph()
        graph.add_edges_from([("a", "b"), ("b", "a")])
        result = _bfs(graph, "a", "out")
        assert result == {"b"}


class TestFuzzyMatch:
    """Tests for _fuzzy_match internal function."""

    def test_exact_match(self):
        result = _fuzzy_match("hello", ["hello", "world"])
        assert result == ["hello"]

    def test_close_match(self):
        result = _fuzzy_match("helo", ["hello", "help", "world"])
        assert "hello" in result

    def test_empty_candidates(self):
        result = _fuzzy_match("hello", [])
        assert result == []

    def test_limit(self):
        candidates = [f"item_{i}" for i in range(20)]
        result = _fuzzy_match("item", candidates, limit=3)
        assert len(result) <= 3


class TestIntegration:
    """Integration-style tests combining resolve_focus + resolve_focus_files."""

    def test_full_pipeline(self):
        """Build a graph, resolve focus, map to files."""
        graph = _make_graph_with_nodes(
            ["auth.login", "auth.validate", "db.query_user", "utils.hash"],
            [
                ("auth.login", "auth.validate"),
                ("auth.login", "db.query_user"),
                ("auth.validate", "utils.hash"),
            ],
        )

        focus_set = resolve_focus(graph, "auth.login")
        assert focus_set == {
            "auth.login",
            "auth.validate",
            "db.query_user",
            "utils.hash",
        }

        parsed = {
            Path("auth.py"): ParsedFile(
                path=Path("auth.py"),
                module_name="auth",
                symbols=[
                    _stub_symbol("auth.login"),
                    _stub_symbol("auth.validate"),
                ],
            ),
            Path("db.py"): ParsedFile(
                path=Path("db.py"),
                module_name="db",
                symbols=[_stub_symbol("db.query_user")],
            ),
            Path("utils.py"): ParsedFile(
                path=Path("utils.py"),
                module_name="utils",
                symbols=[_stub_symbol("utils.hash")],
            ),
        }

        focus_files = resolve_focus_files(focus_set, parsed)
        assert focus_files == {Path("auth.py"), Path("db.py"), Path("utils.py")}

    def test_focus_on_middle_node(self):
        graph = _make_graph_with_nodes(
            ["a.start", "b.process", "c.end"],
            [("a.start", "b.process"), ("b.process", "c.end")],
        )

        focus_set = resolve_focus(graph, "b.process")
        assert focus_set == {"a.start", "b.process", "c.end"}

    def test_focus_not_found_suggests(self):
        graph = _make_graph_with_nodes(
            ["auth.authenticate", "auth.authorize"], []
        )
        suggestions = suggest_symbols(graph, "auth.authentcate")
        assert "auth.authenticate" in suggestions


class TestBoundedTraversal:
    """Tests for _bounded_traversal (v1.1 depth-limited resolution)."""

    def _make_dag(self) -> nx.DiGraph:
        """Create a linear chain: A -> B -> C -> D -> E."""
        g = nx.DiGraph()
        for node in ["a.A", "b.B", "c.C", "d.D", "e.E"]:
            g.add_node(node)
        for src, dst in [
            ("a.A", "b.B"), ("b.B", "c.C"), ("c.C", "d.D"), ("d.D", "e.E")
        ]:
            g.add_edge(src, dst)
        return g

    def test_depth_0_returns_empty(self):
        """Depth 0 should return only the start (excluded), so empty set."""
        g = self._make_dag()
        result = _bounded_traversal(g, "c.C", "out", 0)
        assert result == set()

    def test_depth_1_returns_immediate_neighbors(self):
        """Depth 1 from c.C outward should return {d.D}."""
        g = self._make_dag()
        result = _bounded_traversal(g, "c.C", "out", 1)
        assert result == {"d.D"}

    def test_depth_2_returns_two_hops(self):
        """Depth 2 from c.C outward should return {d.D, e.E}."""
        g = self._make_dag()
        result = _bounded_traversal(g, "c.C", "out", 2)
        assert result == {"d.D", "e.E"}

    def test_depth_none_is_unlimited(self):
        """None depth should return all descendants."""
        g = self._make_dag()
        result = _bounded_traversal(g, "c.C", "out", None)
        assert result == {"d.D", "e.E"}

    def test_depth_in_direction(self):
        """In-direction from c.C with depth 1 should return {b.B}."""
        g = self._make_dag()
        result = _bounded_traversal(g, "c.C", "in", 1)
        assert result == {"b.B"}

    def test_depth_in_direction_depth_2(self):
        """In-direction from c.C with depth 2 should return {a.A, b.B}."""
        g = self._make_dag()
        result = _bounded_traversal(g, "c.C", "in", 2)
        assert result == {"a.A", "b.B"}

    def test_depth_exceeds_graph(self):
        """Depth larger than graph should return all reachable nodes."""
        g = self._make_dag()
        result = _bounded_traversal(g, "c.C", "out", 100)
        assert result == {"d.D", "e.E"}

    def test_missing_start_returns_empty(self):
        """Missing start node returns empty set."""
        g = self._make_dag()
        result = _bounded_traversal(g, "nonexistent", "out", 5)
        assert result == set()


class TestResolveFocusDirection:
    """Tests for resolve_focus with direction parameter (v1.1)."""

    def _make_graph(self) -> CallGraph:
        """Create a simple graph: caller -> focus -> callee."""
        g = nx.DiGraph()
        g.add_node("mod.caller")
        g.add_node("mod.focus")
        g.add_node("mod.callee")
        g.add_edge("mod.caller", "mod.focus")
        g.add_edge("mod.focus", "mod.callee")
        return CallGraph(
            graph=g,
            symbol_table={
                "mod.caller": _stub_symbol("mod.caller"),
                "mod.focus": _stub_symbol("mod.focus"),
                "mod.callee": _stub_symbol("mod.callee"),
            },
        )

    def test_direction_both(self):
        """Default (both) should include callers and callees."""
        graph = self._make_graph()
        result = resolve_focus(graph, "mod.focus", direction=FocusDirection.BOTH)
        assert result == {"mod.caller", "mod.focus", "mod.callee"}

    def test_direction_callers_only(self):
        """Callers direction should exclude callees."""
        graph = self._make_graph()
        result = resolve_focus(graph, "mod.focus", direction=FocusDirection.CALLERS)
        assert result == {"mod.caller", "mod.focus"}
        assert "mod.callee" not in result

    def test_direction_callees_only(self):
        """Callees direction should exclude callers."""
        graph = self._make_graph()
        result = resolve_focus(graph, "mod.focus", direction=FocusDirection.CALLEES)
        assert result == {"mod.focus", "mod.callee"}
        assert "mod.caller" not in result

    def test_direction_with_depth(self):
        """Direction and depth should compose correctly."""
        g = nx.DiGraph()
        for n in ["a.1", "a.2", "a.3", "a.4"]:
            g.add_node(n)
        for src, dst in [("a.1", "a.2"), ("a.2", "a.3"), ("a.3", "a.4")]:
            g.add_edge(src, dst)
        graph = CallGraph(
            graph=g,
            symbol_table={n: _stub_symbol(n) for n in ["a.1", "a.2", "a.3", "a.4"]},
        )
        result = resolve_focus(
            graph, "a.1",
            direction=FocusDirection.CALLEES,
            max_depth=2,
        )
        assert result == {"a.1", "a.2", "a.3"}
        assert "a.4" not in result
