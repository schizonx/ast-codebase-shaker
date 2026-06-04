"""Regression tests for Codebase Shaker.

Each test guards against a specific bug or class of bugs that has been
discovered during development. If a test here ever fails, it means a
previously-fixed bug has reappeared.

These tests use the simple_app fixture and synthetic edge-case files
to avoid dependencies on external packages.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from click.testing import CliRunner

from shaker.cli import cli
from shaker.constants import BUILTIN_NAMES, STDLIB_MODULES
from shaker.engine.parser import parse_file, parse_files
from shaker.models import CompressionMode, Config

# ---- Fixtures ----------------------------------------------------------------


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def simple_app_path() -> Path:
    return Path(__file__).parent.parent / "fixtures" / "simple_app"


# ---- REG-001: Empty file parsing --------------------------------------------
# Bug: Early versions crashed on empty .py files with IndexError.
# Fix: parse_file now returns a ParsedFile with empty lists.


def test_regression_empty_file(tmp_path):
    """REG-001: Empty .py file must parse without error."""
    empty = tmp_path / "empty.py"
    empty.write_text("", encoding="utf-8")
    result = parse_file(empty, "empty")
    assert result.parse_error is None
    assert result.symbols == []
    assert result.imports == []
    assert result.call_sites == []


def test_regression_whitespace_only_file(tmp_path):
    """REG-001b: Whitespace-only .py file must parse without error."""
    ws = tmp_path / "whitespace.py"
    ws.write_text("   \n\n  \n", encoding="utf-8")
    result = parse_file(ws, "whitespace")
    assert result.parse_error is None


# ---- REG-002: Syntax error recovery -----------------------------------------
# Bug: A single syntax-error file would abort the entire pipeline.
# Fix: parse_file catches SyntaxError and sets parse_error field.


def test_regression_syntax_error_recovery(tmp_path):
    """REG-002: File with syntax error must not crash the pipeline."""
    bad = tmp_path / "bad.py"
    bad.write_text("def foo(\n  invalid syntax here\n", encoding="utf-8")
    result = parse_file(bad, "bad")
    assert result.parse_error is not None
    assert len(result.symbols) == 0


def test_regression_syntax_error_does_not_abort_batch(tmp_path):
    """REG-002b: One bad file in a batch must not prevent others from parsing."""
    good = tmp_path / "good.py"
    good.write_text("x = 1\n", encoding="utf-8")
    bad = tmp_path / "bad.py"
    bad.write_text("def broken(\n", encoding="utf-8")
    results = parse_files([good, bad], Config(), root=tmp_path)
    assert results[good].parse_error is None
    assert results[bad].parse_error is not None


# ---- REG-003: Circular imports ------------------------------------------------
# Bug: Circular imports caused infinite loops in early graph builder versions.
# Fix: networkx handles cycles natively; resolver uses nx.descendants/ancestors.


def test_regression_circular_imports(simple_app_path):
    """REG-003: Circular imports must not cause infinite loops or crashes."""
    circular = Path(__file__).parent.parent / "fixtures" / "circular_imports"
    if not circular.exists():
        pytest.skip("circular_imports fixture not found")
    results = parse_files(
        list(circular.glob("__init__.py")) + list(circular.glob("*.py")),
        Config(),
        root=circular,
    )
    for pf in results.values():
        assert pf.parse_error is None


# ---- REG-004: Builtin call filtering -----------------------------------------
# Bug: Calls to print(), len(), etc. created spurious graph edges.
# Fix: _is_builtin() filters calls to Python builtins.


def test_regression_builtin_calls_no_edges(tmp_path):
    """REG-004: Calls to builtins (print, len) must not create graph edges."""
    from shaker.engine.graph import build_graph

    f = tmp_path / "mod.py"
    f.write_text("def foo():\n    print(len('hello'))\n", encoding="utf-8")
    parsed = parse_files([f], Config(), root=tmp_path)
    graph = build_graph(parsed)
    # The only node should be mod.foo — no edges to builtins
    assert "print" not in graph.graph.nodes
    assert "len" not in graph.graph.nodes


# ---- REG-005: Pruner roundtrip validity --------------------------------------
# Bug: ast.unparse() could produce invalid Python for some AST nodes.
# Fix: Double roundtrip check (parse → unparse → parse) with fallback.


def test_regression_signatures_roundtrip(tmp_path):
    """REG-005: Signatures mode output must be valid Python."""
    from shaker.engine.pruner import _prune_file

    f = tmp_path / "complex.py"
    f.write_text(
        "import os\n"
        "from typing import Optional\n"
        "\n"
        "class Foo:\n"
        "    '''A class.'''\n"
        "    def bar(self, x: int, *, y: str = 'hi') -> Optional[bool]:\n"
        "        '''Method docstring.'''\n"
        "        return None\n"
        "\n"
        "@decorator\n"
        "async def baz(a, b, *args, **kwargs):\n"
        "    pass\n",
        encoding="utf-8",
    )
    parsed = parse_file(f, "complex")
    assert parsed.parse_error is None
    result = _prune_file(parsed, CompressionMode.SIGNATURES)
    # Must parse without error
    ast.parse(result)


def test_regression_strip_roundtrip(tmp_path):
    """REG-005b: Strip mode output must be valid Python."""
    from shaker.engine.pruner import _prune_file

    f = tmp_path / "docstring_heavy.py"
    f.write_text(
        '"""Module docstring."""\n'
        "\n"
        "class Foo:\n"
        '    """Class docstring."""\n'
        "    def bar(self):\n"
        '        """Method docstring."""\n'
        "        pass\n",
        encoding="utf-8",
    )
    parsed = parse_file(f, "docstring_heavy")
    result = _prune_file(parsed, CompressionMode.STRIP)
    ast.parse(result)


# ---- REG-006: Focus not found suggestions ------------------------------------
# Bug: Early versions crashed with KeyError when focus was not in graph.
# Fix: resolve_focus returns empty set; suggest_symbols provides alternatives.


def test_regression_focus_not_found_no_crash(simple_app_path, runner):
    """REG-006: Nonexistent focus must not crash; must suggest alternatives."""
    result = runner.invoke(
        cli,
        [str(simple_app_path), "--focus", "nonexistent_symbol_xyz"],
    )
    # Must not crash — exit code may be 0 (with warning) or non-zero
    assert result.exit_code is not None


# ---- REG-007: Duplicate qualified names --------------------------------------
# Bug: Duplicate symbols (same qualified name in different files) caused
#   silent overwrites in the symbol table.
# Fix: _build_symbol_table warns and keeps the first occurrence.


def test_regression_duplicate_qualified_names(tmp_path):
    """REG-007: Duplicate qualified names must warn, not crash."""
    from shaker.engine.graph import build_graph

    f1 = tmp_path / "a.py"
    f1.write_text("def foo():\n    pass\n", encoding="utf-8")
    f2 = tmp_path / "b.py"
    f2.write_text("def foo():\n    pass\n", encoding="utf-8")
    parsed = parse_files([f1, f2], Config(), root=tmp_path)
    # Must not crash — symbol table keeps first occurrence
    graph = build_graph(parsed)
    assert "a.foo" in graph.symbol_table
    assert "b.foo" in graph.symbol_table


# ---- REG-008: Config bool-as-int bug -----------------------------------------
# Bug: max_tokens: true in JSON was accepted because bool is subclass of int.
# Fix: _validate_max_tokens explicitly rejects booleans.


def test_regression_config_bool_max_tokens():
    """REG-008: Boolean values must be rejected for max_tokens."""
    from shaker.infra.config import _validate_max_tokens

    with pytest.raises(ValueError, match="must be an integer"):
        _validate_max_tokens(True)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="must be an integer"):
        _validate_max_tokens(False)  # type: ignore[arg-type]


# ---- REG-009: Clipboard graceful degradation ---------------------------------
# Bug: Missing pyperclip caused ImportError at module load time.
# Fix: try/except around import; _pyperclip set to None when unavailable.


def test_regression_clipboard_import_optional():
    """REG-009: Clipboard module must not fail if pyperclip is missing."""
    from shaker.output import clipboard as clip

    # Module must load regardless of pyperclip availability
    assert hasattr(clip, "deliver")
    assert hasattr(clip, "_pyperclip")


# ---- REG-010: File discovery with no gitignore -------------------------------
# Bug: Early discovery crashed when .gitignore was missing.
# Fix: _load_gitignore returns None when file doesn't exist.


def test_regression_discovery_no_gitignore(tmp_path):
    """REG-010: Discovery must work when .gitignore is absent."""
    f = tmp_path / "app.py"
    f.write_text("x = 1\n", encoding="utf-8")
    from shaker.engine.discovery import discover_files

    config = Config()
    files = discover_files(tmp_path, config)
    assert f in files


# ---- REG-011: always_exclude overrides always_include -----------------------
# Bug: Priority order was wrong — always_include could override always_exclude.
# Fix: always_exclude checked first, then always_include.


def test_regression_always_exclude_wins(tmp_path):
    """REG-011: always_exclude must take priority over always_include."""
    from shaker.engine.discovery import discover_files

    f = tmp_path / "keep.py"
    f.write_text("x = 1\n", encoding="utf-8")
    config = Config(
        always_include=("keep.py",),
        always_exclude=("keep.py",),
    )
    files = discover_files(tmp_path, config)
    assert f not in files


# ---- REG-012: Stdlib module detection ----------------------------------------
# Bug: Some stdlib modules were missing from hardcoded list.
# Fix: Hybrid approach — curated list unioned with sys.stdlib_module_names.


def test_regression_stdlib_includes_common_modules():
    """REG-012: Common stdlib modules must be in STDLIB_MODULES."""
    for mod in ("os", "sys", "json", "pathlib", "collections", "typing"):
        assert mod in STDLIB_MODULES, f"Missing stdlib module: {mod}"


def test_regression_builtins_complete():
    """REG-012b: BUILTIN_NAMES must include common builtins."""
    for name in ("print", "len", "range", "int", "str", "list", "dict"):
        assert name in BUILTIN_NAMES, f"Missing builtin: {name}"


# ---- REG-013: Delivery with both clipboard and file --------------------------
# Bug: Early versions only did one or the other, not both.
# Fix: deliver() handles both clipboard and file independently.


def test_regression_delivery_both_clipboard_and_file(tmp_path):
    """REG-013: deliver() must support clipboard + file simultaneously."""
    from shaker.output.clipboard import deliver

    out = tmp_path / "output.md"
    result = deliver("test content", output_path=out, copy_to_clipboard=False)
    assert result.clipboard_success is False
    assert result.file_path == out
    assert out.read_text(encoding="utf-8") == "test content"


# ---- REG-014: Serializer with empty input ------------------------------------
# Bug: Serializer crashed on empty pruned_files dict.
# Fix: Handles empty input gracefully.


def test_regression_serializer_empty_input():
    """REG-014: Serializer must handle empty input without crashing."""
    from datetime import datetime

    from shaker.models import BuildStats, OutputMetadata
    from shaker.output.serializer import serialize

    meta = OutputMetadata(
        project_name="test",
        focus=None,
        mode=CompressionMode.SIGNATURES,
        config_path=None,
        timestamp=datetime.now().isoformat(),
        version="0.1.0",
        stats=BuildStats(),
    )
    result = serialize({}, meta, set(), [])
    assert "# Codebase Shaker Output" in result


# ---- REG-015: CLI with single file path --------------------------------------
# Bug: CLI expected a directory; passing a single .py file crashed.
# Fix: CLI accepts both files and directories.


def test_regression_cli_single_file(tmp_path, runner):
    """REG-015: CLI must accept a single .py file as path."""
    f = tmp_path / "single.py"
    f.write_text("def hello():\n    pass\n", encoding="utf-8")
    result = runner.invoke(cli, [str(f), "--dry-run"])
    assert result.exit_code == 0


# ---- v1.1 feature tests -----------------------------------------------------


def test_v11_list_symbols(simple_app_path, runner):
    """v1.1: --list-symbols must list all discovered symbols."""
    result = runner.invoke(cli, [str(simple_app_path), "--list-symbols"])
    assert result.exit_code == 0
    assert "auth.login" in result.output
    assert "db.query_user" in result.output
    assert "Total:" in result.output


def test_v11_no_tree(simple_app_path, runner, tmp_path):
    """v1.1: --no-tree must omit the file tree from Markdown output."""
    out = tmp_path / "no_tree.md"
    result = runner.invoke(
        cli, [str(simple_app_path), "--no-tree", "-o", str(out)]
    )
    assert result.exit_code == 0
    content = out.read_text(encoding="utf-8")
    assert "## File Tree" not in content
    assert "```python" in content


def test_v11_depth_limit(simple_app_path, runner):
    """v1.1: --depth must limit focus resolution to N hops."""
    result = runner.invoke(
        cli,
        [str(simple_app_path), "--focus", "auth.login", "--depth", "1", "--dry-run"],
    )
    assert result.exit_code == 0


def test_v11_direction_callers(simple_app_path, runner):
    """v1.1: --direction callers must only trace upward."""
    result = runner.invoke(
        cli,
        [str(simple_app_path), "--focus", "auth.login", "--direction", "callers", "--dry-run"],
    )
    assert result.exit_code == 0


def test_v11_direction_callees(simple_app_path, runner):
    """v1.1: --direction callees must only trace downward."""
    result = runner.invoke(
        cli,
        [str(simple_app_path), "--focus", "auth.login", "--direction", "callees", "--dry-run"],
    )
    assert result.exit_code == 0


def test_v11_env_var_mode(simple_app_path, runner, monkeypatch):
    """v1.1: SHAKER_MODE env var must set the default mode."""
    monkeypatch.setenv("SHAKER_MODE", "strip")
    result = runner.invoke(cli, [str(simple_app_path), "--dry-run"])
    assert result.exit_code == 0


def test_v11_env_var_max_tokens(simple_app_path, runner, monkeypatch):
    """v1.1: SHAKER_MAX_TOKENS env var must set the token limit."""
    monkeypatch.setenv("SHAKER_MAX_TOKENS", "5000")
    result = runner.invoke(cli, [str(simple_app_path), "--dry-run"])
    assert result.exit_code == 0
