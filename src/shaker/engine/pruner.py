"""Stage 5: AST-based code compression.

Parses each non-focus file according to the compression mode and
produces a pruned string. Focus files are always kept at full detail.
All pruned output is guaranteed to be valid Python (roundtrip-tested).
"""

from __future__ import annotations

import ast
import logging
from pathlib import Path

from shaker.models import CompressionMode, ParsedFile

logger = logging.getLogger(__name__)

_SENTINEL = ast.Expr(value=ast.Constant(value=...))


class _SignatureTransformer(ast.NodeTransformer):
    """Replace function/method bodies with ``...`` while preserving signatures.

    Decorators, type annotations, default arguments, keyword-only args,
    positional-only args, ``*args``, and ``*kwargs`` are all preserved.
    """

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        self.generic_visit(node)
        return ast.FunctionDef(
            name=node.name,
            args=node.args,
            body=[_SENTINEL],
            decorator_list=node.decorator_list,
            returns=node.returns,
            type_comment=node.type_comment,
        )

    def visit_AsyncFunctionDef(
        self, node: ast.AsyncFunctionDef
    ) -> ast.AsyncFunctionDef:
        self.generic_visit(node)
        return ast.AsyncFunctionDef(
            name=node.name,
            args=node.args,
            body=[_SENTINEL],
            decorator_list=node.decorator_list,
            returns=node.returns,
            type_comment=node.type_comment,
        )


class _StripTransformer(ast.NodeTransformer):
    """Remove docstrings from function, class, and module bodies.

    Code bodies are preserved. Only the first statement is checked
    for docstring removal.
    """

    @staticmethod
    def _is_docstring(node: ast.stmt) -> bool:
        return (
            isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        )

    @staticmethod
    def _strip_body(body: list[ast.stmt]) -> list[ast.stmt]:
        if body and _StripTransformer._is_docstring(body[0]):
            return body[1:]
        return body

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        self.generic_visit(node)
        return ast.FunctionDef(
            name=node.name,
            args=node.args,
            body=self._strip_body(node.body),
            decorator_list=node.decorator_list,
            returns=node.returns,
            type_comment=node.type_comment,
        )

    def visit_AsyncFunctionDef(
        self, node: ast.AsyncFunctionDef
    ) -> ast.AsyncFunctionDef:
        self.generic_visit(node)
        return ast.AsyncFunctionDef(
            name=node.name,
            args=node.args,
            body=self._strip_body(node.body),
            decorator_list=node.decorator_list,
            returns=node.returns,
            type_comment=node.type_comment,
        )

    def visit_ClassDef(self, node: ast.ClassDef) -> ast.ClassDef:
        self.generic_visit(node)
        return ast.ClassDef(
            name=node.name,
            bases=node.bases,
            keywords=node.keywords,
            body=self._strip_body(node.body),
            decorator_list=node.decorator_list,
        )

    def visit_Module(self, node: ast.Module) -> ast.Module:
        self.generic_visit(node)
        return ast.Module(
            body=self._strip_body(node.body),
            type_ignores=node.type_ignores,
        )


def _remove_comments(source: str) -> str:
    """Strip ``#``-style comments while preserving string literals."""
    result: list[str] = []
    for line in source.splitlines(keepends=True):
        stripped = line.lstrip()
        if stripped.startswith("#"):
            continue
        cleaned = _strip_inline_comment(line)
        if cleaned.strip() or not stripped.startswith("#"):
            result.append(cleaned)
    return "".join(result)


def _strip_inline_comment(line: str) -> str:
    """Remove inline comments from a single line, respecting strings."""
    in_string: str | None = None
    i = 0
    while i < len(line):
        ch = line[i]
        if in_string is not None:
            if ch == "\\":
                i += 2
                continue
            if ch == in_string:
                in_string = None
            i += 1
            continue
        if ch == "\\" and i + 1 < len(line) and line[i + 1] == "\n":
            i += 2
            continue
        if ch == "#":
            return line[:i].rstrip() + "\n" if line.endswith("\n") else line[:i].rstrip()
        if ch == "'" or ch == '"':
            if line[i : i + 3] in ('"""', "'''"):
                in_string = line[i : i + 3]
                i += 3
                continue
            in_string = ch
        i += 1
    return line


def prune_files(
    parsed: dict[Path, ParsedFile],
    focus_files: set[Path],
    mode: CompressionMode,
) -> dict[Path, str]:
    """Prune all files according to the compression mode.

    Focus files are always kept at full detail regardless of mode.

    Args:
        parsed: Mapping of file paths to their parsed representations.
        focus_files: Set of file paths to preserve at full detail.
        mode: Compression mode to apply to non-focus files.

    Returns:
        Mapping of file paths to their pruned source strings.
    """
    result: dict[Path, str] = {}
    for fpath, pf in parsed.items():
        if fpath in focus_files:
            result[fpath] = pf.source
        else:
            result[fpath] = _prune_file(pf, mode)
    return result


def _prune_file(parsed: ParsedFile, mode: CompressionMode) -> str:
    """Prune a single file according to the compression mode.

    If mode is ``FULL``, returns the original source.
    If mode is ``SIGNATURES``, replaces all function/method bodies with ``...``.
    If mode is ``STRIP``, removes docstrings and comments.

    Falls back to the original source with a warning if ``ast.unparse()``
    produces invalid output.

    Args:
        parsed: The parsed file to prune.
        mode: Compression mode.

    Returns:
        Pruned source string guaranteed to be valid Python.
    """
    if mode == CompressionMode.FULL:
        return parsed.source

    if not parsed.source.strip():
        return ""

    tree = parsed.ast_tree
    if tree is None:
        try:
            tree = ast.parse(parsed.source, filename=str(parsed.path))
        except SyntaxError:
            logger.warning(
                "Could not parse %s; returning source as-is", parsed.path
            )
            return parsed.source

    transformer: ast.NodeTransformer
    if mode == CompressionMode.SIGNATURES:
        transformer = _SignatureTransformer()
    else:
        transformer = _StripTransformer()

    transformed = transformer.visit(tree)
    ast.fix_missing_locations(transformed)

    try:
        result = ast.unparse(transformed)
    except Exception:
        logger.warning(
            "ast.unparse() failed for %s; returning source as-is",
            parsed.path,
        )
        return parsed.source

    if mode == CompressionMode.STRIP:
        result = _remove_comments(result)

    try:
        ast.parse(result)
    except SyntaxError:
        logger.warning(
            "Pruned output for %s is not valid Python; returning source as-is",
            parsed.path,
        )
        return parsed.source

    return result


def _is_docstring(node: ast.stmt) -> bool:
    """Check if a statement node is a docstring.

    A docstring is the first expression statement in a module, class,
    or function body that consists of a string constant.

    Args:
        node: An AST statement node.

    Returns:
        True if *node* is a docstring.
    """
    return (
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    )
