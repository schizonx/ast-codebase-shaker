"""Unit tests for shaker.engine.graph.

Covers symbol table construction, call graph building, call resolution,
cycle detection, builtin/stdlib filtering, and edge cases.
"""

from __future__ import annotations

from pathlib import Path

import networkx as nx
import pytest

from shaker.engine.graph import (
    _build_import_map,
    _build_symbol_table,
    _detect_cycles,
    _is_builtin,
    _is_stdlib_module,
    build_graph,
    get_callees,
    get_callers,
)
from shaker.models import (
    CallGraph,
    CallSite,
    ImportInfo,
    ParsedFile,
    Symbol,
    SymbolType,
)


@pytest.fixture
def make_symbol():
    """Factory fixture for creating Symbol objects."""
    def _create(
        name: str = "func",
        qualified_name: str | None = None,
        symbol_type: SymbolType = SymbolType.FUNCTION,
        file: Path | None = None,
        parent: str | None = None,
        line_number: int = 1,
    ) -> Symbol:
        return Symbol(
            name=name,
            qualified_name=qualified_name or f"test.{name}",
            symbol_type=symbol_type,
            file=file or Path("test.py"),
            parent=parent,
            line_number=line_number,
        )
    return _create


@pytest.fixture
def make_parsed_file():
    """Factory fixture for creating ParsedFile objects."""
    def _create(
        path: Path = Path("test.py"),
        module_name: str = "test",
        symbols: list[Symbol] | None = None,
        imports: list[ImportInfo] | None = None,
        call_sites: list[CallSite] | None = None,
    ) -> ParsedFile:
        return ParsedFile(
            path=path,
            module_name=module_name,
            symbols=symbols or [],
            imports=imports or [],
            call_sites=call_sites or [],
            source="",
        )
    return _create


class TestBuildSymbolTable:
    """Tests for _build_symbol_table."""

    def test_empty_parsed(self):
        result = _build_symbol_table({})
        assert result == {}

    def test_single_file_single_symbol(self, make_symbol, make_parsed_file):
        sym = make_symbol("foo")
        parsed = make_parsed_file(symbols=[sym])
        result = _build_symbol_table({Path("test.py"): parsed})
        assert "test.foo" in result
        assert result["test.foo"].name == "foo"

    def test_single_file_multiple_symbols(self, make_symbol, make_parsed_file):
        s1 = make_symbol("foo", "test.foo")
        s2 = make_symbol("bar", "test.bar")
        parsed = make_parsed_file(symbols=[s1, s2])
        result = _build_symbol_table({Path("test.py"): parsed})
        assert len(result) == 2
        assert "test.foo" in result
        assert "test.bar" in result

    def test_multiple_files(self, make_symbol, make_parsed_file):
        s1 = make_symbol("foo", "mod1.foo", file=Path("mod1.py"))
        s2 = make_symbol("bar", "mod2.bar", file=Path("mod2.py"))
        parsed1 = make_parsed_file(path=Path("mod1.py"), module_name="mod1", symbols=[s1])
        parsed2 = make_parsed_file(path=Path("mod2.py"), module_name="mod2", symbols=[s2])
        result = _build_symbol_table({Path("mod1.py"): parsed1, Path("mod2.py"): parsed2})
        assert len(result) == 2
        assert "mod1.foo" in result
        assert "mod2.bar" in result

    def test_duplicate_qualified_name_silent(self, make_symbol, make_parsed_file):
        s1 = make_symbol("foo", "mod.foo", file=Path("mod1.py"))
        s2 = make_symbol("foo", "mod.foo", file=Path("mod2.py"))
        parsed1 = make_parsed_file(path=Path("mod1.py"), symbols=[s1])
        parsed2 = make_parsed_file(path=Path("mod2.py"), symbols=[s2])
        result = _build_symbol_table({Path("mod1.py"): parsed1, Path("mod2.py"): parsed2})
        assert len(result) == 1
        assert "mod.foo" in result


class TestBuildImportMap:
    """Tests for _build_import_map."""

    def test_simple_import(self):
        imports = [ImportInfo(module="os", names=("os",))]
        result = _build_import_map(imports)
        assert result == {"os": "os"}

    def test_import_as(self):
        imports = [ImportInfo(module="numpy", names=("numpy",), alias="np")]
        result = _build_import_map(imports)
        assert result == {"np": "numpy"}

    def test_from_import(self):
        imports = [ImportInfo(module="os.path", names=("join", "basename"))]
        result = _build_import_map(imports)
        assert result["join"] == "os.path"
        assert result["basename"] == "os.path"

    def test_relative_import_ignored(self):
        imports = [
            ImportInfo(module="", names=("utils",), is_relative=True, level=1),
        ]
        result = _build_import_map(imports)
        assert "utils" not in result

    def test_wildcard_import_ignored(self):
        imports = [ImportInfo(module="math", names=("*",), is_wildcard=True)]
        result = _build_import_map(imports)
        assert result == {}

    def test_empty_imports(self):
        result = _build_import_map([])
        assert result == {}

    def test_no_names_import(self):
        imports = [ImportInfo(module="os", names=())]
        result = _build_import_map(imports)
        assert "os" in result


class TestBuildGraphEmpty:
    """Tests for build_graph with empty or minimal input."""

    def test_empty_parsed(self):
        result = build_graph({})
        assert isinstance(result, CallGraph)
        assert isinstance(result.graph, nx.DiGraph)
        assert result.symbol_table == {}
        assert result.graph.number_of_nodes() == 0
        assert result.graph.number_of_edges() == 0
        assert result.unresolved_calls == []
        assert result.cycles == []

    def test_single_function_no_calls(self, make_symbol, make_parsed_file):
        sym = make_symbol("foo", "test.foo")
        parsed = make_parsed_file(module_name="test", symbols=[sym])
        result = build_graph({Path("test.py"): parsed})
        assert result.graph.number_of_nodes() == 1
        assert result.graph.number_of_edges() == 0
        assert "test.foo" in result.graph.nodes


class TestBuildGraphEdges:
    """Tests for call graph edge creation."""

    def test_intra_file_call(self, make_symbol, make_parsed_file):
        caller_sym = make_symbol("caller", "test.caller")
        callee_sym = make_symbol("callee", "test.callee")
        calls = [CallSite(name="callee", line_number=2)]
        parsed = make_parsed_file(
            module_name="test",
            symbols=[caller_sym, callee_sym],
            call_sites=calls,
        )
        result = build_graph({Path("test.py"): parsed})
        assert result.graph.number_of_nodes() == 2
        assert result.graph.number_of_edges() == 1
        assert result.graph.has_edge("test.caller", "test.callee")

    def test_cross_file_call(self, make_symbol, make_parsed_file):
        caller_sym = make_symbol("caller", "mod1.caller", file=Path("mod1.py"))
        callee_sym = make_symbol("do_work", "mod2.do_work", file=Path("mod2.py"))
        imports = [ImportInfo(module="mod2", names=("do_work",))]
        calls = [CallSite(name="do_work", line_number=2)]
        parsed1 = make_parsed_file(
            path=Path("mod1.py"),
            module_name="mod1",
            symbols=[caller_sym],
            imports=imports,
            call_sites=calls,
        )
        parsed2 = make_parsed_file(
            path=Path("mod2.py"),
            module_name="mod2",
            symbols=[callee_sym],
        )
        result = build_graph({Path("mod1.py"): parsed1, Path("mod2.py"): parsed2})
        assert result.graph.has_edge("mod1.caller", "mod2.do_work")

    def test_multiple_calls_same_file(self, make_symbol, make_parsed_file):
        caller_sym = make_symbol("caller", "test.caller")
        callee1 = make_symbol("helper1", "test.helper1")
        callee2 = make_symbol("helper2", "test.helper2")
        calls = [
            CallSite(name="helper1", line_number=2),
            CallSite(name="helper2", line_number=3),
            CallSite(name="helper1", line_number=4),
        ]
        parsed = make_parsed_file(
            module_name="test",
            symbols=[caller_sym, callee1, callee2],
            call_sites=calls,
        )
        result = build_graph({Path("test.py"): parsed})
        assert result.graph.has_edge("test.caller", "test.helper1")
        assert result.graph.has_edge("test.caller", "test.helper2")


class TestBuildGraphBuiltinFiltering:
    """Tests that builtin calls are filtered from the graph."""

    def test_builtin_call_not_added(self, make_symbol, make_parsed_file):
        caller_sym = make_symbol("caller", "test.caller")
        calls = [CallSite(name="print", line_number=2)]
        parsed = make_parsed_file(
            module_name="test",
            symbols=[caller_sym],
            call_sites=calls,
        )
        result = build_graph({Path("test.py"): parsed})
        assert result.graph.number_of_edges() == 0
        assert result.unresolved_calls == []

    def test_len_call_builtin(self, make_symbol, make_parsed_file):
        caller_sym = make_symbol("caller", "test.caller")
        calls = [CallSite(name="len", line_number=2)]
        parsed = make_parsed_file(
            module_name="test",
            symbols=[caller_sym],
            call_sites=calls,
        )
        result = build_graph({Path("test.py"): parsed})
        assert all(call.name != "len" for call in result.unresolved_calls)


class TestBuildGraphUnresolvedCalls:
    """Tests for unresolved call recording."""

    def test_unresolved_dynamic_call(self, make_symbol, make_parsed_file):
        caller_sym = make_symbol("caller", "test.caller")
        calls = [CallSite(name="dynamic_func", line_number=2)]
        parsed = make_parsed_file(
            module_name="test",
            symbols=[caller_sym],
            call_sites=calls,
        )
        result = build_graph({Path("test.py"): parsed})
        assert len(result.unresolved_calls) >= 1

    def test_method_call_unresolved(self, make_symbol, make_parsed_file):
        caller_sym = make_symbol("caller", "test.caller")
        calls = [CallSite(name="method", is_method=True, receiver="obj", line_number=2)]
        parsed = make_parsed_file(
            module_name="test",
            symbols=[caller_sym],
            call_sites=calls,
        )
        result = build_graph({Path("test.py"): parsed})
        unresolved_names = [c.name for c in result.unresolved_calls]
        assert "method" in unresolved_names


class TestBuildGraphCycles:
    """Tests for cycle detection."""

    def test_simple_cycle(self, make_symbol, make_parsed_file):
        sym_a = make_symbol("a", "mod.a")
        sym_b = make_symbol("b", "mod.b")
        calls_a = [CallSite(name="b", line_number=2)]
        calls_b = [CallSite(name="a", line_number=2)]
        parsed = make_parsed_file(
            module_name="mod",
            symbols=[sym_a, sym_b],
            call_sites=calls_a + calls_b,
        )
        result = build_graph({Path("mod.py"): parsed})
        assert result.graph.number_of_edges() == 2
        cycles = result.cycles
        assert len(cycles) >= 1
        cycle_nodes = set()
        for cycle in cycles:
            cycle_nodes.update(cycle)
        assert "mod.a" in cycle_nodes
        assert "mod.b" in cycle_nodes

    def test_diamond_dependency(self, make_symbol, make_parsed_file):
        sym_a = make_symbol("a", "mod.a")
        sym_b = make_symbol("b", "mod.b")
        sym_c = make_symbol("c", "mod.c")
        sym_d = make_symbol("d", "mod.d")
        calls_a = [
            CallSite(name="b", line_number=2),
            CallSite(name="c", line_number=3),
        ]
        calls_b = [CallSite(name="d", line_number=2)]
        calls_c = [CallSite(name="d", line_number=2)]
        parsed = make_parsed_file(
            module_name="mod",
            symbols=[sym_a, sym_b, sym_c, sym_d],
            call_sites=calls_a + calls_b + calls_c,
        )
        result = build_graph({Path("mod.py"): parsed})
        assert result.graph.has_edge("mod.a", "mod.b")
        assert result.graph.has_edge("mod.a", "mod.c")
        assert result.graph.has_edge("mod.b", "mod.d")
        assert result.graph.has_edge("mod.c", "mod.d")

    def test_no_false_cycle(self, make_symbol, make_parsed_file):
        sym_a = make_symbol("a", "mod.a")
        sym_b = make_symbol("b", "mod.b")
        calls_a = [CallSite(name="b", line_number=2)]
        parsed = make_parsed_file(
            module_name="mod",
            symbols=[sym_a, sym_b],
            call_sites=calls_a,
        )
        result = build_graph({Path("mod.py"): parsed})
        assert result.cycles == []


class TestBuildGraphClassHandling:
    """Tests that class symbols are added but no spurious edges from them."""

    def test_class_with_methods(self, make_symbol, make_parsed_file):
        class_sym = make_symbol(
            "Service", "test.Service", SymbolType.CLASS
        )
        method_sym = make_symbol(
            "run", "test.Service.run", SymbolType.METHOD, parent="test.Service"
        )
        parsed = make_parsed_file(
            module_name="test",
            symbols=[class_sym, method_sym],
        )
        result = build_graph({Path("test.py"): parsed})
        assert result.graph.number_of_nodes() == 2
        assert "test.Service" in result.graph.nodes
        assert "test.Service.run" in result.graph.nodes


class TestBuildGraphWildcardImports:
    """Tests handling of wildcard imports."""

    def test_wildcard_no_edges_not_in_table(self, make_parsed_file):
        imports = [ImportInfo(module="helpers", names=("*",), is_wildcard=True)]
        parsed = make_parsed_file(
            module_name="mod",
            imports=imports,
        )
        result = build_graph({Path("mod.py"): parsed})
        assert result.graph.number_of_nodes() == 0
        assert result.graph.number_of_edges() == 0


class TestBuildGraphMultipleCallers:
    """Tests for multiple callers to same callee."""

    def test_multiple_callers(self, make_symbol, make_parsed_file):
        sym_a = make_symbol("a", "mod.a")
        sym_b = make_symbol("b", "mod.b")
        sym_c = make_symbol("c", "mod.c")
        calls_a = [CallSite(name="c", line_number=2)]
        calls_b = [CallSite(name="c", line_number=2)]
        parsed = make_parsed_file(
            module_name="mod",
            symbols=[sym_a, sym_b, sym_c],
            call_sites=calls_a + calls_b,
        )
        result = build_graph({Path("mod.py"): parsed})
        assert result.graph.has_edge("mod.a", "mod.c")
        assert result.graph.has_edge("mod.b", "mod.c")
        assert result.graph.in_degree("mod.c") == 2


class TestGraphMetadata:
    """Tests that symbol metadata is attached to graph nodes."""

    def test_symbol_data_on_node(self, make_symbol, make_parsed_file):
        sym = make_symbol("foo", "test.foo")
        parsed = make_parsed_file(module_name="test", symbols=[sym])
        result = build_graph({Path("test.py"): parsed})
        node_data = result.graph.nodes["test.foo"]
        assert "symbol" in node_data
        assert node_data["symbol"].name == "foo"


class TestGetCallers:
    """Tests for get_callers function."""

    def test_direct_callers(self, make_symbol, make_parsed_file):
        sym_a = make_symbol("a", "mod.a")
        sym_b = make_symbol("target", "mod.target")
        calls_a = [CallSite(name="target", line_number=2)]
        parsed = make_parsed_file(
            module_name="mod",
            symbols=[sym_a, sym_b],
            call_sites=calls_a,
        )
        result = build_graph({Path("mod.py"): parsed})
        callers = get_callers(result, "mod.target")
        assert callers == {"mod.a"}

    def test_no_callers(self, make_symbol, make_parsed_file):
        sym = make_symbol("isolated", "mod.isolated")
        parsed = make_parsed_file(module_name="mod", symbols=[sym])
        result = build_graph({Path("mod.py"): parsed})
        assert get_callers(result, "mod.isolated") == set()

    def test_symbol_not_in_graph(self):
        empty = build_graph({})
        assert get_callers(empty, "nonexistent") == set()


class TestGetCallees:
    """Tests for get_callees function."""

    def test_direct_callees(self, make_symbol, make_parsed_file):
        sym_a = make_symbol("a", "mod.a")
        sym_b = make_symbol("helper", "mod.helper")
        calls_a = [CallSite(name="helper", line_number=2)]
        parsed = make_parsed_file(
            module_name="mod",
            symbols=[sym_a, sym_b],
            call_sites=calls_a,
        )
        result = build_graph({Path("mod.py"): parsed})
        callees = get_callees(result, "mod.a")
        assert callees == {"mod.helper"}

    def test_no_callees(self, make_symbol, make_parsed_file):
        sym = make_symbol("leaf", "mod.leaf")
        parsed = make_parsed_file(module_name="mod", symbols=[sym])
        result = build_graph({Path("mod.py"): parsed})
        assert get_callees(result, "mod.leaf") == set()

    def test_symbol_not_in_graph(self):
        empty = build_graph({})
        assert get_callees(empty, "nonexistent") == set()


class TestDetectCycles:
    """Tests for _detect_cycles internal function."""

    def test_empty_graph(self):
        g = nx.DiGraph()
        assert _detect_cycles(g) == []

    def test_linear_graph(self):
        g = nx.DiGraph()
        g.add_edge("a", "b")
        g.add_edge("b", "c")
        assert _detect_cycles(g) == []

    def test_single_cycle(self):
        g = nx.DiGraph()
        g.add_edge("a", "b")
        g.add_edge("b", "a")
        cycles = _detect_cycles(g)
        assert len(cycles) == 1
        cycle = cycles[0]
        assert set(cycle) == {"a", "b"}


class TestIsBuiltinGraph:
    """Tests for _is_builtin in graph module."""

    def test_known_builtins(self):
        assert _is_builtin("print") is True
        assert _is_builtin("len") is True
        assert _is_builtin("open") is True

    def test_non_builtins(self):
        assert _is_builtin("os") is False
        assert _is_builtin("my_func") is False


class TestIsStdlibModuleGraph:
    """Tests for _is_stdlib_module in graph module."""

    def test_stdlib_modules(self):
        assert _is_stdlib_module("os") is True
        assert _is_stdlib_module("os.path") is True
        assert _is_stdlib_module("sys") is True

    def test_non_stdlib(self):
        assert _is_stdlib_module("myproject") is False
        assert _is_stdlib_module("flask") is False

    def test_empty_module(self):
        assert _is_stdlib_module("") is False


class TestBuildGraphWithImportAlias:
    """Tests that aliased imports resolve correctly."""

    def test_aliased_module_call(self, make_symbol, make_parsed_file):
        caller_sym = make_symbol("caller", "mod1.caller", file=Path("mod1.py"))
        helper_sym = make_symbol("helper", "helpers.helper", file=Path("helpers.py"))
        imports = [ImportInfo(module="helpers", names=("helpers",), alias="h")]
        calls = [CallSite(name="helper", is_method=True, receiver="h", line_number=2)]
        parsed1 = make_parsed_file(
            path=Path("mod1.py"),
            module_name="mod1",
            symbols=[caller_sym],
            imports=imports,
            call_sites=calls,
        )
        parsed2 = make_parsed_file(
            path=Path("helpers.py"),
            module_name="helpers",
            symbols=[helper_sym],
        )
        result = build_graph({Path("mod1.py"): parsed1, Path("helpers.py"): parsed2})
        assert result.graph.has_edge("mod1.caller", "helpers.helper")


class TestBuildGraphComplexScenario:
    """Integration-style test with a realistic multi-file setup."""

    def test_realistic_project(self):
        """Build a graph simulating a 3-file project with cross-file calls."""

        def sym(
            name: str, qname: str, path: Path,
            stype: SymbolType = SymbolType.FUNCTION,
        ) -> Symbol:
            return Symbol(name=name, qualified_name=qname, symbol_type=stype, file=path)

        auth_sym = sym("authenticate", "auth.authenticate", Path("auth.py"))
        db_sym = sym("query_user", "db.query_user", Path("db.py"))
        log_sym = sym("log_event", "logging.log_event", Path("logging.py"))

        parsed_auth = ParsedFile(
            path=Path("auth.py"),
            module_name="auth",
            symbols=[auth_sym],
            imports=[
                ImportInfo(module="db", names=("query_user",)),
                ImportInfo(module="logging", names=("log_event",)),
            ],
            call_sites=[
                CallSite(name="query_user", line_number=10),
                CallSite(name="log_event", line_number=12),
                CallSite(name="print", line_number=14),
            ],
        )

        parsed_db = ParsedFile(
            path=Path("db.py"),
            module_name="db",
            symbols=[db_sym],
            imports=[ImportInfo(module="logging", names=("log_event",))],
            call_sites=[CallSite(name="log_event", line_number=5)],
        )

        parsed_logging = ParsedFile(
            path=Path("logging.py"),
            module_name="logging",
            symbols=[log_sym],
        )

        result = build_graph({
            Path("auth.py"): parsed_auth,
            Path("db.py"): parsed_db,
            Path("logging.py"): parsed_logging,
        })

        assert result.graph.number_of_nodes() == 3
        assert result.graph.number_of_edges() == 3
        assert result.graph.has_edge("auth.authenticate", "db.query_user")
        assert result.graph.has_edge("auth.authenticate", "logging.log_event")
        assert result.graph.has_edge("db.query_user", "logging.log_event")
        assert result.cycles == []
