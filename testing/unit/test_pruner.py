"""Unit tests for shaker.engine.pruner.

Covers all compression modes, roundtrip validity, edge cases,
decorators, async functions, class preservation, and argument styles.
"""

from __future__ import annotations

import ast
from pathlib import Path

from shaker.engine.pruner import (
    _is_docstring,
    _prune_file,
    _remove_comments,
    _SignatureTransformer,
    _StripTransformer,
    prune_files,
)
from shaker.models import CompressionMode, ParsedFile


def _pf(source: str, path: str = "test.py") -> ParsedFile:
    """Helper: build a ParsedFile from source."""
    tree = ast.parse(source)
    return ParsedFile(
        path=Path(path),
        module_name="test",
        source=source,
        ast_tree=tree,
    )


def _roundtrip(source: str) -> None:
    """Assert that source parses and roundtrips through ast.unparse."""
    tree = ast.parse(source)
    ast.unparse(tree)


class TestFullMode:
    """Tests for CompressionMode.FULL."""

    def test_full_mode_identical(self):
        source = "def f():\n    return 1\n"
        pf = _pf(source)
        result = _prune_file(pf, CompressionMode.FULL)
        assert result == source

    def test_full_mode_preserves_comments(self):
        source = "# comment\nx = 1\n"
        pf = _pf(source)
        result = _prune_file(pf, CompressionMode.FULL)
        assert result == source

    def test_full_mode_preserves_docstrings(self):
        source = '"""Module docstring."""\n'
        pf = _pf(source)
        result = _prune_file(pf, CompressionMode.FULL)
        assert result == source


class TestSignaturesMode:
    """Tests for CompressionMode.SIGNATURES."""

    def test_simple_function_body_replaced(self):
        source = "def f():\n    return 1\n"
        pf = _pf(source)
        result = _prune_file(pf, CompressionMode.SIGNATURES)
        assert "..." in result
        assert "return" not in result

    def test_multiple_functions(self):
        source = (
            "def f():\n"
            "    return 1\n"
            "\n"
            "def g():\n"
            "    return 2\n"
        )
        pf = _pf(source)
        result = _prune_file(pf, CompressionMode.SIGNATURES)
        assert "return" not in result
        assert "def f" in result
        assert "def g" in result

    def test_decorators_preserved(self):
        source = "@decorator\ndef f():\n    return 1\n"
        pf = _pf(source)
        result = _prune_file(pf, CompressionMode.SIGNATURES)
        assert "@decorator" in result
        assert "def f" in result

    def test_multiple_decorators(self):
        source = "@decorator1\n@decorator2\ndef f():\n    return 1\n"
        pf = _pf(source)
        result = _prune_file(pf, CompressionMode.SIGNATURES)
        assert "@decorator1" in result
        assert "@decorator2" in result

    def test_type_annotations_preserved(self):
        source = "def f(x: int, y: str = 'hi') -> bool:\n    return True\n"
        pf = _pf(source)
        result = _prune_file(pf, CompressionMode.SIGNATURES)
        assert "int" in result
        assert "str" in result
        assert "bool" in result

    def test_default_arguments_preserved(self):
        source = "def f(x=1, y='hello', z=None):\n    pass\n"
        pf = _pf(source)
        result = _prune_file(pf, CompressionMode.SIGNATURES)
        assert "x=1" in result or "x = 1" in result
        assert "None" in result

    def test_class_with_methods(self):
        source = (
            "class C:\n"
            "    def method(self):\n"
            "        return 1\n"
        )
        pf = _pf(source)
        result = _prune_file(pf, CompressionMode.SIGNATURES)
        assert "class C" in result
        assert "def method" in result
        assert "return" not in result

    def test_module_level_code_preserved(self):
        source = "x = 1\ny = 2\ndef f():\n    pass\n"
        pf = _pf(source)
        result = _prune_file(pf, CompressionMode.SIGNATURES)
        assert "x = 1" in result
        assert "y = 2" in result

    def test_async_function(self):
        source = "async def f():\n    await something()\n"
        pf = _pf(source)
        result = _prune_file(pf, CompressionMode.SIGNATURES)
        assert "async def f" in result
        assert "await" not in result

    def test_args_kwargs(self):
        source = "def f(*args, **kwargs):\n    pass\n"
        pf = _pf(source)
        result = _prune_file(pf, CompressionMode.SIGNATURES)
        assert "args" in result
        assert "kwargs" in result

    def test_keyword_only_args(self):
        source = "def f(*, key, value):\n    pass\n"
        pf = _pf(source)
        result = _prune_file(pf, CompressionMode.SIGNATURES)
        assert "key" in result
        assert "value" in result

    def test_positional_only_args(self):
        source = "def f(x, y, /, z):\n    pass\n"
        pf = _pf(source)
        result = _prune_file(pf, CompressionMode.SIGNATURES)
        assert "x" in result
        assert "y" in result
        assert "z" in result

    def test_decorated_async_function(self):
        source = "@decorator\nasync def f():\n    await x\n"
        pf = _pf(source)
        result = _prune_file(pf, CompressionMode.SIGNATURES)
        assert "@decorator" in result
        assert "async def f" in result


class TestStripMode:
    """Tests for CompressionMode.STRIP."""

    def test_docstring_removed(self):
        source = '"""Module docstring."""\nx = 1\n'
        pf = _pf(source)
        result = _prune_file(pf, CompressionMode.STRIP)
        assert '"""' not in result
        assert "x = 1" in result

    def test_function_docstring_removed(self):
        source = (
            "def f():\n"
            '    """Function docstring."""\n'
            "    return 1\n"
        )
        pf = _pf(source)
        result = _prune_file(pf, CompressionMode.STRIP)
        assert '"""' not in result
        assert "return 1" in result

    def test_class_docstring_removed(self):
        source = (
            "class C:\n"
            '    """Class docstring."""\n'
            "    pass\n"
        )
        pf = _pf(source)
        result = _prune_file(pf, CompressionMode.STRIP)
        assert '"""' not in result
        assert "class C" in result

    def test_comments_removed(self):
        source = "x = 1  # inline comment\n# full line comment\ny = 2\n"
        pf = _pf(source)
        result = _prune_file(pf, CompressionMode.STRIP)
        assert "inline comment" not in result
        assert "full line comment" not in result
        assert "x = 1" in result
        assert "y = 2" in result

    def test_code_bodies_preserved(self):
        source = "def f():\n    x = 1\n    return x\n"
        pf = _pf(source)
        result = _prune_file(pf, CompressionMode.STRIP)
        assert "x = 1" in result
        assert "return x" in result


class TestRoundtrip:
    """Roundtrip tests: pruned output must be valid Python."""

    def _assert_roundtrip(self, source: str, mode: CompressionMode) -> None:
        pf = _pf(source)
        result = _prune_file(pf, mode)
        ast.parse(result)

    def test_roundtrip_simple(self):
        self._assert_roundtrip("x = 1\n", CompressionMode.SIGNATURES)

    def test_roundtrip_function(self):
        self._assert_roundtrip(
            "def f():\n    return 1\n", CompressionMode.SIGNATURES
        )

    def test_roundtrip_class(self):
        self._assert_roundtrip(
            "class C:\n    pass\n", CompressionMode.SIGNATURES
        )

    def test_roundtrip_strip(self):
        self._assert_roundtrip(
            '"""doc"""\nx = 1\n', CompressionMode.STRIP
        )

    def test_roundtrip_full(self):
        self._assert_roundtrip("x = 1\n", CompressionMode.FULL)

    def test_roundtrip_complex(self):
        source = (
            "import os\n"
            "from pathlib import Path\n"
            "\n"
            "CONST = 42\n"
            "\n"
            "class C:\n"
            '    """Class doc."""\n'
            "    def method(self, x: int) -> None:\n"
            "        return x\n"
            "\n"
            "@decorator\n"
            "def func(a, b=1, *args, **kwargs):\n"
            "    pass\n"
            "\n"
            "async def async_func():\n"
            "    await something()\n"
        )
        self._assert_roundtrip(source, CompressionMode.SIGNATURES)
        self._assert_roundtrip(source, CompressionMode.STRIP)
        self._assert_roundtrip(source, CompressionMode.FULL)


class TestEdgeCases:
    """Edge case tests."""

    def test_empty_file(self):
        pf = _pf("")
        result = _prune_file(pf, CompressionMode.SIGNATURES)
        assert result == ""

    def test_empty_file_strip(self):
        pf = _pf("")
        result = _prune_file(pf, CompressionMode.STRIP)
        assert result == ""

    def test_only_imports(self):
        source = "import os\nfrom pathlib import Path\n"
        pf = _pf(source)
        result = _prune_file(pf, CompressionMode.SIGNATURES)
        assert "import os" in result
        assert "from pathlib import Path" in result

    def test_only_class(self):
        source = "class C:\n    pass\n"
        pf = _pf(source)
        result = _prune_file(pf, CompressionMode.SIGNATURES)
        assert "class C" in result

    def test_nested_functions(self):
        source = (
            "def outer():\n"
            "    def inner():\n"
            "        return 1\n"
            "    return inner\n"
        )
        pf = _pf(source)
        result = _prune_file(pf, CompressionMode.SIGNATURES)
        assert "def outer" in result
        assert "return" not in result

    def test_lambda_preserved(self):
        source = "f = lambda x: x + 1\n"
        pf = _pf(source)
        result = _prune_file(pf, CompressionMode.SIGNATURES)
        assert "lambda" in result


class TestPruneFiles:
    """Tests for the prune_files entry point."""

    def test_focus_files_preserved(self):
        source = "def f():\n    return 1\n"
        pf = _pf(source, "focus.py")
        parsed = {Path("focus.py"): pf}
        result = prune_files(parsed, {Path("focus.py")}, CompressionMode.SIGNATURES)
        assert result[Path("focus.py")] == source

    def test_non_focus_files_pruned(self):
        source = "def f():\n    return 1\n"
        pf = _pf(source, "other.py")
        parsed = {Path("other.py"): pf}
        result = prune_files(parsed, set(), CompressionMode.SIGNATURES)
        assert "return" not in result[Path("other.py")]

    def test_mixed_focus_and_non_focus(self):
        focus_source = "def f():\n    return 1\n"
        other_source = "def g():\n    return 2\n"
        parsed = {
            Path("focus.py"): _pf(focus_source, "focus.py"),
            Path("other.py"): _pf(other_source, "other.py"),
        }
        result = prune_files(
            parsed, {Path("focus.py")}, CompressionMode.SIGNATURES
        )
        assert result[Path("focus.py")] == focus_source
        assert "return" not in result[Path("other.py")]

    def test_empty_parsed(self):
        result = prune_files({}, set(), CompressionMode.SIGNATURES)
        assert result == {}


class TestRemoveComments:
    """Tests for _remove_comments."""

    def test_full_line_comment(self):
        assert _remove_comments("# just a comment\n") == ""

    def test_inline_comment(self):
        result = _remove_comments("x = 1  # comment\n")
        assert "x = 1" in result
        assert "comment" not in result

    def test_preserves_strings_with_hash(self):
        result = _remove_comments('x = "# not a comment"\n')
        assert "#" in result

    def test_preserves_code(self):
        result = _remove_comments("x = 1\ny = 2\n")
        assert "x = 1" in result
        assert "y = 2" in result


class TestIsDocstring:
    """Tests for _is_docstring."""

    def test_string_literal_is_docstring(self):
        node = ast.Expr(value=ast.Constant(value="hello"))
        assert _is_docstring(node) is True

    def test_non_string_not_docstring(self):
        node = ast.Expr(value=ast.Constant(value=42))
        assert _is_docstring(node) is False

    def test_non_expr_not_docstring(self):
        node = ast.parse("x = 1").body[0]
        assert _is_docstring(node) is False


class TestSignatureTransformerUnit:
    """Direct tests for _SignatureTransformer."""

    def test_transforms_body(self):
        source = "def f():\n    return 1\n"
        tree = ast.parse(source)
        result = _SignatureTransformer().visit(tree)
        ast.fix_missing_locations(result)
        unparsed = ast.unparse(result)
        assert "..." in unparsed
        assert "return" not in unparsed

    def test_preserves_decorators(self):
        source = "@dec\ndef f():\n    pass\n"
        tree = ast.parse(source)
        result = _SignatureTransformer().visit(tree)
        ast.fix_missing_locations(result)
        unparsed = ast.unparse(result)
        assert "@dec" in unparsed


class TestStripTransformerUnit:
    """Direct tests for _StripTransformer."""

    def test_removes_docstring(self):
        source = '"""doc"""\nx = 1\n'
        tree = ast.parse(source)
        result = _StripTransformer().visit(tree)
        ast.fix_missing_locations(result)
        unparsed = ast.unparse(result)
        assert '"""' not in unparsed
        assert "x = 1" in unparsed

    def test_preserves_body(self):
        source = "def f():\n    x = 1\n    return x\n"
        tree = ast.parse(source)
        result = _StripTransformer().visit(tree)
        ast.fix_missing_locations(result)
        unparsed = ast.unparse(result)
        assert "x = 1" in unparsed
        assert "return x" in unparsed
