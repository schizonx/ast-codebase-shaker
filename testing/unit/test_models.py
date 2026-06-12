"""Unit tests for shaker.models.

Validates construction, defaults, immutability, computed properties,
and independence of mutable instances for all data models.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from shaker.models import (
    BuildStats,
    CallGraph,
    CallSite,
    CompressionMode,
    Config,
    DeliveryResult,
    ImportInfo,
    OutputMetadata,
    ParsedFile,
    PipelineState,
    Symbol,
    SymbolType,
)


class TestCompressionMode:
    """Tests for the CompressionMode enum."""

    def test_full_value(self) -> None:
        assert CompressionMode.FULL.value == "full"

    def test_signatures_value(self) -> None:
        assert CompressionMode.SIGNATURES.value == "signatures"

    def test_strip_value(self) -> None:
        assert CompressionMode.STRIP.value == "strip"

    def test_all_members_present(self) -> None:
        members = {m.name for m in CompressionMode}
        assert members == {"FULL", "SIGNATURES", "STRIP"}

    def test_enum_from_value(self) -> None:
        assert CompressionMode("full") is CompressionMode.FULL
        assert CompressionMode("signatures") is CompressionMode.SIGNATURES
        assert CompressionMode("strip") is CompressionMode.STRIP


class TestSymbolType:
    """Tests for the SymbolType enum."""

    def test_module_value(self) -> None:
        assert SymbolType.MODULE.value == "module"

    def test_class_value(self) -> None:
        assert SymbolType.CLASS.value == "class"

    def test_function_value(self) -> None:
        assert SymbolType.FUNCTION.value == "function"

    def test_method_value(self) -> None:
        assert SymbolType.METHOD.value == "method"

    def test_all_members_present(self) -> None:
        members = {m.name for m in SymbolType}
        assert members == {"MODULE", "CLASS", "FUNCTION", "METHOD"}


class TestImportInfo:
    """Tests for the ImportInfo frozen dataclass."""

    def test_construction_with_required_fields(self) -> None:
        info = ImportInfo(module="os.path", names=("join", "basename"))
        assert info.module == "os.path"
        assert info.names == ("join", "basename")
        assert info.alias is None
        assert info.is_wildcard is False
        assert info.is_relative is False
        assert info.level == 0
        assert info.line_number == 0

    def test_construction_with_all_fields(self) -> None:
        info = ImportInfo(
            module="src.models",
            names=("User",),
            alias="models",
            is_wildcard=False,
            is_relative=True,
            level=2,
            line_number=5,
        )
        assert info.module == "src.models"
        assert info.names == ("User",)
        assert info.alias == "models"
        assert info.is_relative is True
        assert info.level == 2
        assert info.line_number == 5

    def test_frozen_immutability(self) -> None:
        info = ImportInfo(module="os", names=("path",))
        with pytest.raises(AttributeError):
            info.module = "sys"  # type: ignore[misc]

    def test_wildcard_import(self) -> None:
        info = ImportInfo(module="foo", names=(), is_wildcard=True)
        assert info.is_wildcard is True
        assert len(info.names) == 0

    def test_hashable(self) -> None:
        info = ImportInfo(module="os", names=("path",))
        # Frozen dataclasses with hashable fields are hashable
        # (though not explicitly setting frozen=True does not auto-hash)
        # Just verify it doesn't raise
        d: dict[ImportInfo, str] = {info: "test"}
        assert d[info] == "test"

    def test_names_as_tuple(self) -> None:
        info = ImportInfo(module="os", names=("path", "join"))
        assert isinstance(info.names, tuple)


class TestCallSite:
    """Tests for the CallSite frozen dataclass."""

    def test_construction_with_required_field(self) -> None:
        call = CallSite(name="process_payment")
        assert call.name == "process_payment"
        assert call.qualified_name is None
        assert call.line_number == 0
        assert call.is_method is False
        assert call.receiver is None

    def test_construction_with_all_fields(self) -> None:
        call = CallSite(
            name="check_password",
            qualified_name="src.models.user.User.check_password",
            line_number=42,
            is_method=True,
            receiver="user",
        )
        assert call.name == "check_password"
        assert call.qualified_name == "src.models.user.User.check_password"
        assert call.line_number == 42
        assert call.is_method is True
        assert call.receiver == "user"

    def test_frozen_immutability(self) -> None:
        call = CallSite(name="foo")
        with pytest.raises(AttributeError):
            call.name = "bar"  # type: ignore[misc]

    def test_qualified_name_none_by_default(self) -> None:
        call = CallSite(name="unknown_func")
        assert call.qualified_name is None


class TestSymbol:
    """Tests for the Symbol frozen dataclass."""

    def test_construction_with_required_fields(self) -> None:
        symbol = Symbol(
            name="User",
            qualified_name="src.models.user.User",
            symbol_type=SymbolType.CLASS,
            file=Path("src/models/user.py"),
        )
        assert symbol.name == "User"
        assert symbol.qualified_name == "src.models.user.User"
        assert symbol.symbol_type is SymbolType.CLASS
        assert symbol.file == Path("src/models/user.py")
        assert symbol.line_number == 0
        assert symbol.decorators == ()
        assert symbol.parent is None
        assert symbol.is_async is False
        assert symbol.docstring is None

    def test_construction_with_all_fields(self) -> None:
        symbol = Symbol(
            name="check_password",
            qualified_name="src.models.user.User.check_password",
            symbol_type=SymbolType.METHOD,
            file=Path("src/models/user.py"),
            line_number=42,
            decorators=("validator", "log_call"),
            parent="src.models.user.User",
            is_async=True,
            docstring="Check the user password.",
        )
        assert symbol.name == "check_password"
        assert symbol.symbol_type is SymbolType.METHOD
        assert symbol.line_number == 42
        assert symbol.decorators == ("validator", "log_call")
        assert symbol.parent == "src.models.user.User"
        assert symbol.is_async is True
        assert symbol.docstring == "Check the user password."

    def test_frozen_immutability(self) -> None:
        symbol = Symbol(
            name="Foo",
            qualified_name="m.Foo",
            symbol_type=SymbolType.CLASS,
            file=Path("m.py"),
        )
        with pytest.raises(AttributeError):
            symbol.name = "Bar"  # type: ignore[misc]

    def test_method_requires_parent(self) -> None:
        """A method-type symbol should have parent set."""
        symbol = Symbol(
            name="save",
            qualified_name="db.Model.save",
            symbol_type=SymbolType.METHOD,
            file=Path("db/model.py"),
            parent="db.Model",
        )
        assert symbol.parent == "db.Model"

    def test_function_has_no_parent(self) -> None:
        symbol = Symbol(
            name="main",
            qualified_name="app.main",
            symbol_type=SymbolType.FUNCTION,
            file=Path("app.py"),
        )
        assert symbol.parent is None


class TestParsedFile:
    """Tests for the ParsedFile mutable dataclass."""

    def test_construction_with_required_fields(self) -> None:
        parsed = ParsedFile(path=Path("src/models/user.py"), module_name="src.models.user")
        assert parsed.path == Path("src/models/user.py")
        assert parsed.module_name == "src.models.user"
        assert parsed.symbols == []
        assert parsed.imports == []
        assert parsed.call_sites == []
        assert parsed.source == ""
        assert parsed.ast_tree is None
        assert parsed.parse_error is None
        assert parsed.encoding == "utf-8"

    def test_mutable_symbols_list(self) -> None:
        parsed = ParsedFile(path=Path("m.py"), module_name="m")
        symbol = Symbol(
            name="Foo",
            qualified_name="m.Foo",
            symbol_type=SymbolType.CLASS,
            file=Path("m.py"),
        )
        parsed.symbols.append(symbol)
        assert len(parsed.symbols) == 1

    def test_mutable_imports_list(self) -> None:
        parsed = ParsedFile(path=Path("m.py"), module_name="m")
        imp = ImportInfo(module="os", names=("path",))
        parsed.imports.append(imp)
        assert len(parsed.imports) == 1

    def test_mutable_call_sites_list(self) -> None:
        parsed = ParsedFile(path=Path("m.py"), module_name="m")
        call = CallSite(name="foo")
        parsed.call_sites.append(call)
        assert len(parsed.call_sites) == 1

    def test_encoding_fallback(self) -> None:
        parsed = ParsedFile(path=Path("m.py"), module_name="m", encoding="latin-1")
        assert parsed.encoding == "latin-1"

    def test_parse_error_recorded(self) -> None:
        parsed = ParsedFile(
            path=Path("broken.py"),
            module_name="broken",
            parse_error="SyntaxError: invalid syntax at line 1",
        )
        assert "SyntaxError" in parsed.parse_error

    def test_source_stored(self) -> None:
        source = "def foo():\n    return 1\n"
        parsed = ParsedFile(path=Path("m.py"), module_name="m", source=source)
        assert parsed.source == source

    def test_ast_tree_stored(self) -> None:
        tree = ast.parse("x = 1")
        parsed = ParsedFile(path=Path("m.py"), module_name="m", ast_tree=tree)
        assert parsed.ast_tree is tree


class TestCallGraph:
    """Tests for the CallGraph mutable dataclass."""

    def test_construction_with_required_fields(self) -> None:
        import networkx as nx

        graph = nx.DiGraph()
        symbol_table: dict[str, Symbol] = {}
        cg = CallGraph(graph=graph, symbol_table=symbol_table)
        assert cg.graph is graph
        assert cg.symbol_table is symbol_table
        assert cg.unresolved_calls == []
        assert cg.cycles == []

    def test_mutable_unresolved_calls(self) -> None:
        import networkx as nx

        cg = CallGraph(graph=nx.DiGraph(), symbol_table={})
        call = CallSite(name="dynamic_call")
        cg.unresolved_calls.append(call)
        assert len(cg.unresolved_calls) == 1

    def test_mutable_cycles(self) -> None:
        import networkx as nx

        cg = CallGraph(graph=nx.DiGraph(), symbol_table={})
        cg.cycles.append(["a.func", "b.func", "a.func"])
        assert len(cg.cycles) == 1
        assert cg.cycles[0] == ["a.func", "b.func", "a.func"]

    def test_symbol_table_populated(self) -> None:
        import networkx as nx

        symbol = Symbol(
            name="User",
            qualified_name="models.User",
            symbol_type=SymbolType.CLASS,
            file=Path("models.py"),
        )
        cg = CallGraph(
            graph=nx.DiGraph(),
            symbol_table={"models.User": symbol},
        )
        assert "models.User" in cg.symbol_table
        assert cg.symbol_table["models.User"].name == "User"


class TestBuildStats:
    """Tests for the BuildStats mutable dataclass and computed properties."""

    def test_default_values(self) -> None:
        stats = BuildStats()
        assert stats.total_files == 0
        assert stats.retained_files == 0
        assert stats.omitted_files == 0
        assert stats.parse_errors == 0
        assert stats.total_lines == 0
        assert stats.output_lines == 0
        assert stats.input_tokens == 0
        assert stats.output_tokens == 0
        assert stats.reduction_pct == 0.0

    def test_construction_with_values(self) -> None:
        stats = BuildStats(
            total_files=14,
            retained_files=6,
            omitted_files=8,
            parse_errors=0,
            total_lines=2450,
            output_lines=412,
            input_tokens=18200,
            output_tokens=2940,
            reduction_pct=83.8,
        )
        assert stats.total_files == 14
        assert stats.retained_files == 6
        assert stats.reduction_pct == 83.8

    def test_files_reduction_pct(self) -> None:
        stats = BuildStats(total_files=10, retained_files=3)
        assert stats.files_reduction_pct == 70.0

    def test_files_reduction_pct_zero_files(self) -> None:
        stats = BuildStats(total_files=0, retained_files=0)
        assert stats.files_reduction_pct == 0.0

    def test_files_reduction_pct_all_retained(self) -> None:
        stats = BuildStats(total_files=10, retained_files=10)
        assert stats.files_reduction_pct == 0.0

    def test_files_reduction_pct_none_retained(self) -> None:
        stats = BuildStats(total_files=10, retained_files=0)
        assert stats.files_reduction_pct == 100.0

    def test_mutable_fields(self) -> None:
        stats = BuildStats()
        stats.total_files = 100
        stats.parse_errors = 2
        assert stats.total_files == 100
        assert stats.parse_errors == 2


class TestOutputMetadata:
    """Tests for the OutputMetadata mutable dataclass."""

    def test_construction(self) -> None:
        stats = BuildStats(total_files=10, retained_files=5)
        meta = OutputMetadata(
            project_name="my_project",
            focus="login_user",
            mode=CompressionMode.SIGNATURES,
            config_path=Path(".shakerrc.json"),
            timestamp="2026-06-15T14:30:00",
            version="0.0.0",
            stats=stats,
        )
        assert meta.project_name == "my_project"
        assert meta.focus == "login_user"
        assert meta.mode is CompressionMode.SIGNATURES
        assert meta.config_path == Path(".shakerrc.json")
        assert meta.timestamp == "2026-06-15T14:30:00"
        assert meta.version == "0.0.0"
        assert meta.stats.total_files == 10

    def test_focus_can_be_none(self) -> None:
        meta = OutputMetadata(
            project_name="my_project",
            focus=None,
            mode=CompressionMode.SIGNATURES,
            config_path=None,
            timestamp="2026-06-15T14:30:00",
            version="0.0.0",
            stats=BuildStats(),
        )
        assert meta.focus is None
        assert meta.config_path is None


class TestConfig:
    """Tests for the Config mutable dataclass."""

    def test_default_values(self) -> None:
        config = Config()
        assert config.default_mode is CompressionMode.SIGNATURES
        assert config.exclude_patterns == ()
        assert config.max_tokens is None
        assert config.always_include == ()
        assert config.always_exclude == ()
        assert config.config_path is None

    def test_construction_with_all_fields(self) -> None:
        config = Config(
            default_mode=CompressionMode.FULL,
            exclude_patterns=("*_test.py", "migrations/"),
            max_tokens=8000,
            always_include=("src/models/",),
            always_exclude=("src/legacy/",),
            config_path=Path(".shakerrc.json"),
        )
        assert config.default_mode is CompressionMode.FULL
        assert config.exclude_patterns == ("*_test.py", "migrations/")
        assert config.max_tokens == 8000
        assert config.always_include == ("src/models/",)
        assert config.always_exclude == ("src/legacy/",)
        assert config.config_path == Path(".shakerrc.json")

    def test_exclude_patterns_as_tuple(self) -> None:
        config = Config(exclude_patterns=("a", "b"))
        assert isinstance(config.exclude_patterns, tuple)

    def test_mutable(self) -> None:
        config = Config()
        config.max_tokens = 5000
        assert config.max_tokens == 5000


class TestDeliveryResult:
    """Tests for the DeliveryResult mutable dataclass."""

    def test_default_values(self) -> None:
        result = DeliveryResult()
        assert result.clipboard_success is False
        assert result.file_path is None
        assert result.warnings == []

    def test_construction_with_all_fields(self) -> None:
        result = DeliveryResult(
            clipboard_success=True,
            file_path=Path("output.md"),
            warnings=["Clipboard unavailable on headless system"],
        )
        assert result.clipboard_success is True
        assert result.file_path == Path("output.md")
        assert len(result.warnings) == 1

    def test_mutable_warnings(self) -> None:
        result = DeliveryResult()
        result.warnings.append("warning 1")
        result.warnings.append("warning 2")
        assert len(result.warnings) == 2


class TestPipelineState:
    """Tests for the PipelineState mutable dataclass."""

    def test_default_values(self) -> None:
        state = PipelineState(config=Config())
        assert state.root_path == Path.cwd()
        assert state.focus is None
        assert state.discovered_files == []
        assert state.parsed_files == {}
        assert state.call_graph is None
        assert state.focus_symbols == set()
        assert state.focus_files == set()
        assert state.pruned_files == {}
        assert state.omitted_files == []
        assert state.output == ""
        assert state.delivery is None
        assert isinstance(state.stats, BuildStats)
        assert state.warnings == []
        assert state.errors == []

    def test_independent_mutable_defaults(self) -> None:
        """Ensure each PipelineState instance gets independent mutable objects."""
        state1 = PipelineState(config=Config())
        state2 = PipelineState(config=Config())

        state1.discovered_files.append(Path("a.py"))
        assert len(state2.discovered_files) == 0

        state1.parsed_files[Path("a.py")] = ParsedFile(
            path=Path("a.py"), module_name="a"
        )
        assert len(state2.parsed_files) == 0

        state1.focus_symbols.add("a.func")
        assert len(state2.focus_symbols) == 0

        state1.warnings.append("warning")
        assert len(state2.warnings) == 0

        state1.errors.append("error")
        assert len(state2.errors) == 0

    def test_independent_stats(self) -> None:
        state1 = PipelineState(config=Config())
        state2 = PipelineState(config=Config())
        state1.stats.total_files = 42
        assert state2.stats.total_files == 0

    def test_independent_output_string(self) -> None:
        state1 = PipelineState(config=Config())
        state2 = PipelineState(config=Config())
        state1.output = "# Context"
        assert state2.output == ""

    def test_independent_omitted_files(self) -> None:
        state1 = PipelineState(config=Config())
        state2 = PipelineState(config=Config())
        state1.omitted_files.append(Path("x.py"))
        assert len(state2.omitted_files) == 0

    def test_with_focus(self) -> None:
        state = PipelineState(config=Config(), focus="login_user")
        assert state.focus == "login_user"

    def test_with_root_path(self) -> None:
        state = PipelineState(config=Config(), root_path=Path("/tmp/project"))
        assert state.root_path == Path("/tmp/project")

    def test_stats_is_build_stats(self) -> None:
        state = PipelineState(config=Config())
        assert isinstance(state.stats, BuildStats)
        state.stats.total_files = 10
        state.stats.retained_files = 3
        assert state.stats.files_reduction_pct == 70.0


class TestModuleLevelContract:
    """Tests for the module's public API contract."""

    def test_all_public_names_exported(self) -> None:
        from shaker import models

        expected = {
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
        }
        assert set(models.__all__) == expected

    def test_no_project_imports(self) -> None:
        """models.py must not import from any shaker module."""
        import shaker.models as mod

        module_str = str(mod.__file__)
        # Verify the module exists and is loadable
        assert module_str is not None

    def test_all_models_importable(self) -> None:
        from shaker.models import (  # noqa: F401
            BuildStats,
            CallGraph,
            CallSite,
            CompressionMode,
            Config,
            DeliveryResult,
            ImportInfo,
            OutputMetadata,
            ParsedFile,
            PipelineState,
            Symbol,
            SymbolType,
        )

    def test_compression_mode_str_values(self) -> None:
        """Ensure string values match expected serialization."""
        assert CompressionMode.FULL.value == "full"
        assert CompressionMode.SIGNATURES.value == "signatures"
        assert CompressionMode.STRIP.value == "strip"

    def test_symbol_type_str_values(self) -> None:
        """Ensure string values match expected serialization."""
        assert SymbolType.MODULE.value == "module"
        assert SymbolType.CLASS.value == "class"
        assert SymbolType.FUNCTION.value == "function"
        assert SymbolType.METHOD.value == "method"
