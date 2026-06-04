"""Unit tests for shaker.constants.

Validates all public constants have correct types, values, and meet
the invariants required by downstream modules.
"""

from __future__ import annotations

import builtins
import sys

import pytest

from shaker.constants import (
    BUILTIN_NAMES,
    CHARS_PER_TOKEN_FALLBACK,
    DEFAULT_ENCODING,
    DEFAULT_MODE,
    FALLBACK_ENCODING,
    OMIT_THRESHOLD,
    STDLIB_MODULES,
    SUPPORTED_MODES,
    TIKTOKEN_DEFAULT_ENCODING,
)
from shaker.models import CompressionMode


class TestDefaultMode:
    """Tests for DEFAULT_MODE."""

    def test_default_mode_is_signatures(self) -> None:
        assert DEFAULT_MODE is CompressionMode.SIGNATURES

    def test_default_mode_is_compression_mode(self) -> None:
        assert isinstance(DEFAULT_MODE, CompressionMode)

    def test_default_mode_value(self) -> None:
        assert DEFAULT_MODE.value == "signatures"


class TestSupportedModes:
    """Tests for SUPPORTED_MODES."""

    def test_all_three_modes_present(self) -> None:
        assert set(SUPPORTED_MODES) == {
            CompressionMode.FULL,
            CompressionMode.SIGNATURES,
            CompressionMode.STRIP,
        }

    def test_supported_modes_is_tuple(self) -> None:
        assert isinstance(SUPPORTED_MODES, tuple)

    def test_supported_modes_is_immutable(self) -> None:
        with pytest.raises(AttributeError):
            SUPPORTED_MODES.append(CompressionMode.FULL)  # type: ignore[attr-defined]

    def test_supported_modes_has_three_entries(self) -> None:
        assert len(SUPPORTED_MODES) == 3


class TestEncodingConstants:
    """Tests for encoding-related constants."""

    def test_default_encoding_is_utf8(self) -> None:
        assert DEFAULT_ENCODING == "utf-8"

    def test_fallback_encoding_is_latin1(self) -> None:
        assert FALLBACK_ENCODING == "latin-1"

    def test_default_and_fallback_are_different(self) -> None:
        assert DEFAULT_ENCODING != FALLBACK_ENCODING

    def test_default_encoding_is_lowercase(self) -> None:
        assert DEFAULT_ENCODING.lower() == DEFAULT_ENCODING


class TestOmitThreshold:
    """Tests for OMIT_THRESHOLD."""

    def test_omit_threshold_is_50(self) -> None:
        assert OMIT_THRESHOLD == 50

    def test_omit_threshold_is_positive(self) -> None:
        assert OMIT_THRESHOLD > 0

    def test_omit_threshold_is_int(self) -> None:
        assert isinstance(OMIT_THRESHOLD, int)


class TestTiktokenConstants:
    """Tests for tiktoken-related constants."""

    def test_tiktoken_default_encoding(self) -> None:
        assert TIKTOKEN_DEFAULT_ENCODING == "cl100k_base"

    def test_chars_per_token_fallback_is_4(self) -> None:
        assert CHARS_PER_TOKEN_FALLBACK == 4

    def test_chars_per_token_fallback_is_positive(self) -> None:
        assert CHARS_PER_TOKEN_FALLBACK > 0


class TestBuiltinNames:
    """Tests for BUILTIN_NAMES."""

    def test_is_frozenset(self) -> None:
        assert isinstance(BUILTIN_NAMES, frozenset)

    def test_contains_common_builtins(self) -> None:
        common = {"print", "len", "range", "int", "str", "list", "dict",
                  "set", "tuple", "type", "isinstance", "issubclass",
                  "hasattr", "getattr", "setattr", "open", "input",
                  "enumerate", "zip", "map", "filter", "sorted", "reversed",
                  "any", "all", "sum", "min", "max", "abs", "round",
                  "super", "property", "staticmethod", "classmethod",
                  "ValueError", "TypeError", "KeyError", "IndexError",
                  "AttributeError", "RuntimeError", "StopIteration",
                  "GeneratorExit", "SystemExit", "KeyboardInterrupt",
                  "NotImplemented", "Ellipsis", "None", "True", "False"}
        assert common.issubset(BUILTIN_NAMES)

    def test_contains_exception_types(self) -> None:
        assert "Exception" in BUILTIN_NAMES
        assert "BaseException" in BUILTIN_NAMES

    def test_matches_runtime_builtins(self) -> None:
        runtime_builtins = frozenset(dir(builtins))
        assert runtime_builtins == BUILTIN_NAMES

    def test_not_empty(self) -> None:
        assert len(BUILTIN_NAMES) > 0

    def test_all_entries_are_strings(self) -> None:
        for name in BUILTIN_NAMES:
            assert isinstance(name, str)


class TestStdlibModules:
    """Tests for STDLIB_MODULES."""

    def test_is_frozenset(self) -> None:
        assert isinstance(STDLIB_MODULES, frozenset)

    def test_contains_common_stdlib(self) -> None:
        common = {
            "os", "sys", "pathlib", "collections", "itertools",
            "functools", "json", "re", "math", "datetime", "time",
            "hashlib", "secrets", "random", "string", "textwrap",
            "typing", "dataclasses", "enum", "abc", "io",
            "contextlib", "copy", "pprint", "codecs", "unicodedata",
            "statistics", "decimal", "fractions", "numbers",
            "struct", "csv", "configparser", "argparse", "logging",
            "warnings", "traceback", "dis", "ast", "token", "tokenize",
            "keyword", "linecache", "pickle", "shelve", "sqlite3",
            "zlib", "gzip", "bz2", "lzma", "zipfile", "tarfile",
            "shutil", "tempfile", "glob", "fnmatch", "filecmp",
            "urllib", "http", "ftplib", "smtplib", "email",
            "html", "xml", "webbrowser",
            "subprocess", "signal", "threading", "multiprocessing",
            "concurrent", "asyncio", "socket", "ssl",
            "unittest", "doctest", "test",
            "pdb", "profile", "cProfile", "timeit", "trace",
            "gc", "weakref", "types", "inspect", "importlib",
            "pkgutil", "modulefinder",
            "code", "codeop", "compileall",
            "symtable", "venv", "ensurepip",
        }
        assert common.issubset(STDLIB_MODULES)

    def test_does_not_include_third_party(self) -> None:
        third_party = {"requests", "flask", "django", "numpy", "pandas",
                       "pytest", "click", "rich", "networkx", "tiktoken",
                       "pyperclip", "pathspec"}
        for name in third_party:
            assert name not in STDLIB_MODULES

    def test_includes_os_and_sys(self) -> None:
        assert "os" in STDLIB_MODULES
        assert "sys" in STDLIB_MODULES

    def test_includes_collections_and_itertools(self) -> None:
        assert "collections" in STDLIB_MODULES
        assert "itertools" in STDLIB_MODULES

    def test_not_empty(self) -> None:
        assert len(STDLIB_MODULES) > 0

    def test_all_entries_are_strings(self) -> None:
        for name in STDLIB_MODULES:
            assert isinstance(name, str)

    def test_includes_runtime_stdlib(self) -> None:
        if hasattr(sys, "stdlib_module_names"):
            for name in sys.stdlib_module_names:
                assert name in STDLIB_MODULES


class TestModuleLevelContract:
    """Tests for the module's public API contract."""

    def test_all_constants_exist(self) -> None:
        """All framework-specified constants must be present."""
        import shaker.constants as mod
        expected = {
            "DEFAULT_MODE",
            "SUPPORTED_MODES",
            "DEFAULT_ENCODING",
            "FALLBACK_ENCODING",
            "OMIT_THRESHOLD",
            "TIKTOKEN_DEFAULT_ENCODING",
            "CHARS_PER_TOKEN_FALLBACK",
            "BUILTIN_NAMES",
            "STDLIB_MODULES",
        }
        for name in expected:
            assert hasattr(mod, name), f"Missing constant: {name}"

    def test_only_models_imported(self) -> None:
        """constants.py must only import from models, not other shaker modules."""
        import inspect

        import shaker.constants as mod
        source = inspect.getsource(mod)
        # Verify no shaker imports except from models
        for line in source.split("\n"):
            stripped = line.strip()
            if stripped.startswith("from shaker") or stripped.startswith("import shaker"):
                assert "from shaker.models" in stripped or "import shaker.models" in stripped, \
                    f"constants.py imports from non-models shaker module: {stripped}"

    def test_no_business_logic(self) -> None:
        """constants.py must define no new functions or classes."""
        import inspect

        import shaker.constants as mod

        source = inspect.getsource(mod)
        for line in source.split("\n"):
            stripped = line.strip()
            if stripped.startswith("def ") or stripped.startswith("class "):
                raise AssertionError(
                    f"constants.py defines business logic: {stripped}"
                )
