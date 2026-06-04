"""Unit tests for shaker.engine.parser.

Covers symbol extraction, import extraction, call site extraction,
error handling, and edge cases.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from shaker.engine.parser import (
    _is_builtin,
    _is_stdlib,
    _resolve_module_name,
    parse_file,
    parse_files,
)
from shaker.models import (
    SymbolType,
)


@pytest.fixture
def make_py_file(tmp_path):
    """Helper to create a .py file with given source code."""
    def _create(source: str, name: str = "test_module.py") -> Path:
        fpath = tmp_path / name
        fpath.parent.mkdir(parents=True, exist_ok=True)
        fpath.write_text(source, encoding="utf-8")
        return fpath
    return _create


class TestParseFileBasic:
    """Tests for basic parse_file behavior."""

    def test_empty_file(self, make_py_file):
        fpath = make_py_file("")
        result = parse_file(fpath)
        assert result.path == fpath
        assert result.symbols == []
        assert result.imports == []
        assert result.call_sites == []
        assert result.parse_error is None

    def test_file_with_only_comments(self, make_py_file):
        fpath = make_py_file("# just a comment\n# another comment\n")
        result = parse_file(fpath)
        assert result.symbols == []
        assert result.imports == []
        assert result.parse_error is None

    def test_file_with_docstring_only(self, make_py_file):
        fpath = make_py_file('"""Module docstring."""\n')
        result = parse_file(fpath)
        assert result.symbols == []
        assert result.source == '"""Module docstring."""\n'
        assert result.parse_error is None

    def test_source_stored(self, make_py_file):
        source = "x = 1\ny = 2\n"
        fpath = make_py_file(source)
        result = parse_file(fpath)
        assert result.source == source

    def test_ast_tree_stored(self, make_py_file):
        fpath = make_py_file("x = 1\n")
        result = parse_file(fpath)
        assert result.ast_tree is not None
        assert isinstance(result.ast_tree, ast.Module)

    def test_encoding_utf8(self, make_py_file):
        fpath = make_py_file("x = 1\n")
        result = parse_file(fpath)
        assert result.encoding in ("utf-8", "utf-8-sig")


class TestParseFileErrors:
    """Tests for parse error handling."""

    def test_syntax_error(self, make_py_file):
        fpath = make_py_file("def foo(\n")
        result = parse_file(fpath)
        assert result.parse_error is not None
        assert "SyntaxError" in result.parse_error
        assert result.symbols == []

    def test_syntax_error_includes_line_number(self, make_py_file):
        fpath = make_py_file("x = 1\ny = \n")
        result = parse_file(fpath)
        assert result.parse_error is not None
        assert "line" in result.parse_error

    def test_source_preserved_on_error(self, make_py_file):
        source = "def broken(\n"
        fpath = make_py_file(source)
        result = parse_file(fpath)
        assert result.source == source
        assert result.parse_error is not None


class TestParseFileEncoding:
    """Tests for encoding handling."""

    def test_latin1_fallback(self, tmp_path):
        fpath = tmp_path / "latin1_module.py"
        fpath.write_bytes("# -*- coding: latin-1 -*-\n# café\nx = 1\n".encode("latin-1"))
        result = parse_file(fpath)
        assert result.parse_error is None
        assert result.encoding == "latin-1"

    def test_utf8_bom(self, tmp_path):
        fpath = tmp_path / "bom_module.py"
        fpath.write_bytes(b"\xef\xbb\xbfx = 1\n")
        result = parse_file(fpath)
        assert result.parse_error is None


class TestExtractImports:
    """Tests for import extraction."""

    def test_simple_import(self, make_py_file):
        fpath = make_py_file("import os\n")
        result = parse_file(fpath)
        assert len(result.imports) == 1
        assert result.imports[0].module == "os"
        assert result.imports[0].names == ("os",)

    def test_import_as(self, make_py_file):
        fpath = make_py_file("import numpy as np\n")
        result = parse_file(fpath)
        assert len(result.imports) == 1
        assert result.imports[0].module == "numpy"
        assert result.imports[0].alias == "np"

    def test_from_import(self, make_py_file):
        fpath = make_py_file("from os.path import join, basename\n")
        result = parse_file(fpath)
        assert len(result.imports) == 1
        imp = result.imports[0]
        assert imp.module == "os.path"
        assert imp.names == ("join", "basename")

    def test_wildcard_import(self, make_py_file):
        fpath = make_py_file("from foo import *\n")
        result = parse_file(fpath)
        assert len(result.imports) == 1
        imp = result.imports[0]
        assert imp.is_wildcard is True
        assert imp.names == ("*",)

    def test_relative_import(self, make_py_file):
        fpath = make_py_file("from . import utils\n")
        result = parse_file(fpath)
        assert len(result.imports) == 1
        imp = result.imports[0]
        assert imp.is_relative is True
        assert imp.level == 1

    def test_relative_import_parent(self, make_py_file):
        fpath = make_py_file("from ..models import User\n")
        result = parse_file(fpath)
        imp = result.imports[0]
        assert imp.is_relative is True
        assert imp.level == 2
        assert imp.module == "models"

    def test_multiple_imports(self, make_py_file):
        fpath = make_py_file(
            "import os\nfrom sys import path\nimport json\n"
        )
        result = parse_file(fpath)
        assert len(result.imports) == 3

    def test_import_line_numbers(self, make_py_file):
        fpath = make_py_file("\n\nimport os\n")
        result = parse_file(fpath)
        assert result.imports[0].line_number == 3

    def test_future_import(self, make_py_file):
        fpath = make_py_file("from __future__ import annotations\n")
        result = parse_file(fpath)
        imp = result.imports[0]
        assert imp.module == "__future__"
        assert imp.names == ("annotations",)

    def test_import_in_type_checking_block(self, make_py_file):
        source = (
            "from typing import TYPE_CHECKING\n"
            "if TYPE_CHECKING:\n"
            "    from mypy.types import Type\n"
        )
        fpath = make_py_file(source)
        result = parse_file(fpath)
        # The import inside if block is still extracted
        modules = [imp.module for imp in result.imports]
        assert "typing" in modules
        assert "mypy.types" in modules


class TestExtractSymbols:
    """Tests for symbol extraction."""

    def test_single_function(self, make_py_file):
        fpath = make_py_file("def hello():\n    pass\n")
        result = parse_file(fpath)
        assert len(result.symbols) == 1
        sym = result.symbols[0]
        assert sym.name == "hello"
        assert sym.symbol_type is SymbolType.FUNCTION
        assert sym.parent is None

    def test_single_class(self, make_py_file):
        fpath = make_py_file("class User:\n    pass\n")
        result = parse_file(fpath)
        assert len(result.symbols) == 1
        sym = result.symbols[0]
        assert sym.name == "User"
        assert sym.symbol_type is SymbolType.CLASS

    def test_class_with_methods(self, make_py_file):
        source = (
            "class User:\n"
            "    def __init__(self):\n"
            "        pass\n"
            "    def save(self):\n"
            "        pass\n"
        )
        fpath = make_py_file(source)
        result = parse_file(fpath)
        names = [s.name for s in result.symbols]
        assert "User" in names
        assert "__init__" in names
        assert "save" in names

    def test_method_qualified_name(self, make_py_file):
        source = (
            "class User:\n"
            "    def save(self):\n"
            "        pass\n"
        )
        fpath = make_py_file(source)
        result = parse_file(fpath)
        method = [s for s in result.symbols if s.name == "save"][0]
        assert method.symbol_type is SymbolType.METHOD
        assert "User" in method.parent

    def test_nested_classes(self, make_py_file):
        source = (
            "class Outer:\n"
            "    class Inner:\n"
            "        def inner_method(self):\n"
            "            pass\n"
        )
        fpath = make_py_file(source)
        result = parse_file(fpath)
        names = [s.name for s in result.symbols]
        assert "Outer" in names
        assert "Inner" in names
        assert "inner_method" in names

    def test_async_function(self, make_py_file):
        fpath = make_py_file("async def fetch():\n    pass\n")
        result = parse_file(fpath)
        assert len(result.symbols) == 1
        assert result.symbols[0].is_async is True

    def test_decorators_preserved(self, make_py_file):
        source = (
            "@property\n"
            "def name(self):\n"
            "    return self._name\n"
        )
        fpath = make_py_file(source)
        result = parse_file(fpath)
        sym = result.symbols[0]
        assert "property" in sym.decorators

    def test_multiple_decorators(self, make_py_file):
        source = (
            "@decorator1\n"
            "@decorator2\n"
            "def func():\n"
            "    pass\n"
        )
        fpath = make_py_file(source)
        result = parse_file(fpath)
        sym = result.symbols[0]
        assert "decorator1" in sym.decorators
        assert "decorator2" in sym.decorators

    def test_decorator_with_args(self, make_py_file):
        source = (
            "@app.route('/home')\n"
            "def home():\n"
            "    pass\n"
        )
        fpath = make_py_file(source)
        result = parse_file(fpath)
        sym = result.symbols[0]
        assert len(sym.decorators) == 1

    def test_docstring_preserved(self, make_py_file):
        source = (
            "def hello():\n"
            '    """Say hello."""\n'
            "    pass\n"
        )
        fpath = make_py_file(source)
        result = parse_file(fpath)
        sym = result.symbols[0]
        assert sym.docstring == "Say hello."

    def test_line_number(self, make_py_file):
        source = "\n\ndef hello():\n    pass\n"
        fpath = make_py_file(source)
        result = parse_file(fpath)
        assert result.symbols[0].line_number == 3

    def test_nested_function(self, make_py_file):
        source = (
            "def outer():\n"
            "    def inner():\n"
            "        pass\n"
        )
        fpath = make_py_file(source)
        result = parse_file(fpath)
        names = [s.name for s in result.symbols]
        assert "outer" in names
        assert "inner" in names

    def test_class_method_decorators(self, make_py_file):
        source = (
            "class Foo:\n"
            "    @staticmethod\n"
            "    def bar():\n"
            "        pass\n"
            "    @classmethod\n"
            "    def baz(cls):\n"
            "        pass\n"
        )
        fpath = make_py_file(source)
        result = parse_file(fpath)
        bar = [s for s in result.symbols if s.name == "bar"][0]
        baz = [s for s in result.symbols if s.name == "baz"][0]
        assert "staticmethod" in bar.decorators
        assert "classmethod" in baz.decorators


class TestExtractCalls:
    """Tests for call site extraction."""

    def test_simple_call(self, make_py_file):
        fpath = make_py_file("print('hello')\n")
        result = parse_file(fpath)
        assert len(result.call_sites) == 1
        assert result.call_sites[0].name == "print"

    def test_method_call(self, make_py_file):
        fpath = make_py_file("obj.method()\n")
        result = parse_file(fpath)
        call = result.call_sites[0]
        assert call.name == "method"
        assert call.is_method is True
        assert call.receiver == "obj"

    def test_chained_method_call(self, make_py_file):
        fpath = make_py_file("db.session.query(User).filter(active=True).all()\n")
        result = parse_file(fpath)
        names = [c.name for c in result.call_sites]
        assert "query" in names
        assert "filter" in names
        assert "all" in names

    def test_call_in_function(self, make_py_file):
        source = (
            "def process():\n"
            "    result = transform(data)\n"
            "    return result\n"
        )
        fpath = make_py_file(source)
        result = parse_file(fpath)
        names = [c.name for c in result.call_sites]
        assert "transform" in names

    def test_call_line_number(self, make_py_file):
        fpath = make_py_file("\n\nprint('hi')\n")
        result = parse_file(fpath)
        assert result.call_sites[0].line_number == 3

    def test_multiple_calls(self, make_py_file):
        fpath = make_py_file("a()\nb()\nc()\n")
        result = parse_file(fpath)
        assert len(result.call_sites) == 3

    def test_call_with_no_args(self, make_py_file):
        fpath = make_py_file("func()\n")
        result = parse_file(fpath)
        assert result.call_sites[0].name == "func"

    def test_nested_call(self, make_py_file):
        fpath = make_py_file("outer(inner(x))\n")
        result = parse_file(fpath)
        names = [c.name for c in result.call_sites]
        assert "outer" in names
        assert "inner" in names

    def test_fstring_with_call(self, make_py_file):
        source = 'f"Result: {calculate()}"\n'
        fpath = make_py_file(source)
        result = parse_file(fpath)
        names = [c.name for c in result.call_sites]
        assert "calculate" in names


class TestResolveModuleName:
    """Tests for _resolve_module_name."""

    def test_simple_file(self, tmp_path):
        assert _resolve_module_name(tmp_path / "main.py") == "main"

    def test_nested_file_stem(self, tmp_path):
        fpath = tmp_path / "src" / "models" / "user.py"
        fpath.parent.mkdir(parents=True)
        assert _resolve_module_name(fpath) == "user"

    def test_init_file(self, tmp_path):
        fpath = tmp_path / "src" / "__init__.py"
        fpath.parent.mkdir(parents=True)
        assert _resolve_module_name(fpath) == "src"


class TestIsBuiltin:
    """Tests for _is_builtin."""

    def test_common_builtins(self):
        assert _is_builtin("print") is True
        assert _is_builtin("len") is True
        assert _is_builtin("range") is True

    def test_non_builtins(self):
        assert _is_builtin("os") is False
        assert _is_builtin("my_function") is False


class TestIsStdlib:
    """Tests for _is_stdlib."""

    def test_stdlib_modules(self):
        assert _is_stdlib("os") is True
        assert _is_stdlib("os.path") is True
        assert _is_stdlib("collections") is True

    def test_non_stdlib(self):
        assert _is_stdlib("requests") is False
        assert _is_stdlib("django") is False


class TestParseFiles:
    """Tests for the batch parse_files function."""

    def test_parse_multiple_files(self, make_py_file, tmp_path):
        f1 = make_py_file("def a():\n    pass\n", name="a.py")
        f2 = make_py_file("def b():\n    pass\n", name="b.py")
        results = parse_files([f1, f2], config=None)
        assert len(results) == 2
        assert f1 in results
        assert f2 in results

    def test_parse_empty_list(self):
        results = parse_files([], config=None)
        assert results == {}


class TestComplexFiles:
    """Tests for complex real-world-ish files."""

    def test_class_with_inheritance(self, make_py_file):
        source = (
            "class User(BaseModel):\n"
            "    def __init__(self, name: str):\n"
            "        self.name = name\n"
            "    \n"
            "    def greet(self) -> str:\n"
            "        return f'Hello, {self.name}'\n"
        )
        fpath = make_py_file(source)
        result = parse_file(fpath)
        assert result.parse_error is None
        names = [s.name for s in result.symbols]
        assert "User" in names
        assert "__init__" in names
        assert "greet" in names

    def test_walrus_operator(self, make_py_file):
        source = (
            "def process(data):\n"
            "    if (n := len(data)) > 10:\n"
            "        return n\n"
        )
        fpath = make_py_file(source)
        result = parse_file(fpath)
        assert result.parse_error is None
        names = [c.name for c in result.call_sites]
        assert "len" in names

    def test_match_statement(self, make_py_file):
        source = (
            "def check(value):\n"
            "    match value:\n"
            "        case 1:\n"
            "            return one()\n"
            "        case _:\n"
            "            return other()\n"
        )
        fpath = make_py_file(source)
        result = parse_file(fpath)
        assert result.parse_error is None
        names = [c.name for c in result.call_sites]
        assert "one" in names
        assert "other" in names

    def test_type_annotations(self, make_py_file):
        source = (
            "from typing import Optional\n"
            "\n"
            "def greet(name: Optional[str] = None) -> str:\n"
            "    return f'Hello, {name}'\n"
        )
        fpath = make_py_file(source)
        result = parse_file(fpath)
        assert result.parse_error is None
        sym = result.symbols[0]
        assert sym.name == "greet"

    def test_lambda_body(self, make_py_file):
        source = "f = lambda x: x + 1\n"
        fpath = make_py_file(source)
        result = parse_file(fpath)
        assert result.parse_error is None

    def test_large_file(self, make_py_file):
        """A 1000+ line file should parse without issue."""
        lines = []
        for i in range(200):
            lines.append(f"def func_{i}():\n    return {i}\n")
        source = "\n".join(lines)
        fpath = make_py_file(source)
        result = parse_file(fpath)
        assert result.parse_error is None
        assert len(result.symbols) == 200
