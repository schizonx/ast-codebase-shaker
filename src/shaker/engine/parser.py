"""Stage 2: AST parsing and symbol extraction.

Parses Python files into AST, extracts symbols (classes, functions,
methods), imports, and call sites. Handles syntax errors and encoding
issues gracefully.
"""

from __future__ import annotations

import ast
from pathlib import Path

from shaker.constants import BUILTIN_NAMES, STDLIB_MODULES
from shaker.models import (
    CallSite,
    ImportInfo,
    ParsedFile,
    Symbol,
    SymbolType,
)

_DefNode = ast.FunctionDef | ast.AsyncFunctionDef
_ClassOrDef = ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef


def parse_files(
    files: list[Path], config: object, root: Path | None = None,
) -> dict[Path, ParsedFile]:
    """Parse all files and return a map of path → ParsedFile.

    Args:
        files: List of .py file paths to parse.
        config: Application configuration (unused currently, reserved
            for future parser options).
        root: Root directory of the project. When provided, module names
            are computed as dotted paths relative to this root (e.g.,
            ``flask.app`` for ``flask/app.py``). When ``None``, falls
            back to the filename stem only.

    Returns:
        Dict mapping each file path to its ParsedFile result.
    """
    results: dict[Path, ParsedFile] = {}
    for fpath in files:
        results[fpath] = parse_file(fpath, root=root)
    return results


def parse_file(path: Path, root: Path | None = None) -> ParsedFile:
    """Parse a single Python file into a ParsedFile.

    Attempts UTF-8 first, then latin-1 fallback. On syntax error,
    returns a ParsedFile with parse_error set.

    Args:
        path: Path to the .py file.
        root: Root directory of the project. When provided, module names
            are computed as dotted paths relative to this root.

    Returns:
        ParsedFile with extracted symbols, imports, and call sites.
    """
    module_name = _resolve_module_name(path, root=root)
    source, encoding, read_error = _read_source(path)

    if read_error is not None:
        return ParsedFile(
            path=path,
            module_name=module_name,
            source="",
            parse_error=read_error,
            encoding=encoding,
        )

    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        return ParsedFile(
            path=path,
            module_name=module_name,
            source=source,
            parse_error=f"SyntaxError: {exc.msg} at line {exc.lineno}",
            encoding=encoding,
        )

    imports = _extract_imports(tree)
    symbols = _extract_symbols(tree, module_name)
    call_sites = _extract_all_calls(tree, module_name)

    return ParsedFile(
        path=path,
        module_name=module_name,
        symbols=symbols,
        imports=imports,
        call_sites=call_sites,
        source=source,
        ast_tree=tree,
        encoding=encoding,
    )


def _read_source(path: Path) -> tuple[str, str, str | None]:
    """Read file source with encoding fallback.

    Tries UTF-8 first, then latin-1.

    Args:
        path: Path to the file.

    Returns:
        Tuple of (source_text, encoding_used, error_message_or_None).
    """
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return path.read_text(encoding=enc), enc, None
        except UnicodeDecodeError:
            continue
        except OSError as exc:
            return "", "utf-8", f"Read error: {exc}"
    return "", "utf-8", "Read error: could not decode file with any encoding"


def _resolve_module_name(path: Path, root: Path | None = None) -> str:
    """Convert a file path to a dotted module name.

    When *root* is provided, computes the dotted module path relative
    to the root directory. When *root* is ``None``, falls back to the
    filename stem only (backward compatible).

    With root::

        root/flask/app.py       → ``flask.app``
        root/flask/__init__.py  → ``flask``
        root/flask/json/__init__.py → ``flask.json``
        root/app.py             → ``app``

    Without root::

        ``user.py`` → ``user``
        ``__init__.py`` → parent directory name.

    Args:
        path: File path.
        root: Optional root directory for relative module resolution.

    Returns:
        Dotted module name string.
    """
    if root is not None:
        try:
            rel = path.relative_to(root)
        except ValueError:
            root = None

    if root is not None:
        parts = list(rel.parts)
        if not parts:
            # Single file: path and root are the same
            return path.stem
        # Remove .py extension from the last component
        if parts[-1] == "__init__.py":
            # __init__.py maps to the package name (drop the filename)
            parts = parts[:-1]
        else:
            # Replace filename stem
            parts[-1] = Path(parts[-1]).stem
        return ".".join(parts) if parts else path.stem

    # Fallback: no root provided
    if path.name == "__init__.py":
        return path.parent.name
    return path.stem


def _extract_imports(tree: ast.Module) -> list[ImportInfo]:
    """Extract all import statements from an AST module.

    Handles ``import X``, ``import X as Y``, ``from X import Y``,
    ``from X import *``, and relative imports.

    Args:
        tree: The parsed AST module.

    Returns:
        List of ImportInfo for each import statement.
    """
    imports: list[ImportInfo] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(ImportInfo(
                    module=alias.name,
                    names=(alias.name.split(".")[0],),
                    alias=alias.asname,
                    line_number=node.lineno,
                ))
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            names = tuple(
                alias.name for alias in node.names
            )
            is_wildcard = any(alias.name == "*" for alias in node.names)
            imports.append(ImportInfo(
                module=module,
                names=names,
                is_wildcard=is_wildcard,
                is_relative=node.level > 0,
                level=node.level,
                line_number=node.lineno,
            ))
    return imports


def _extract_symbols(tree: ast.Module, module_name: str) -> list[Symbol]:
    """Extract all top-level and nested symbols from an AST module.

    Walks the module body to find class and function definitions,
    including nested ones. Builds qualified names from the hierarchy.

    Args:
        tree: The parsed AST module.
        module_name: The dotted module name.

    Returns:
        List of Symbol objects for all definitions found.
    """
    symbols: list[Symbol] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            symbols.append(_make_symbol(node, module_name, None))
            symbols.extend(_extract_nested_from_body(
                node.body, module_name, parent_name=node.name,
            ))
    return symbols


def _extract_nested_from_body(
    body: list[ast.stmt],
    module_name: str,
    parent_name: str,
) -> list[Symbol]:
    """Extract nested symbols from a body of statements.

    Handles nested functions, methods, and classes within any
    enclosing scope (function, method, or class body).

    Args:
        body: List of AST statement nodes.
        module_name: The dotted module name.
        parent_name: Qualified name of the parent scope.

    Returns:
        List of Symbol objects for nested definitions.
    """
    symbols: list[Symbol] = []
    for child in body:
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            symbols.append(_make_symbol(
                child, module_name, parent_name=parent_name,
            ))
            symbols.extend(_extract_nested_from_body(
                child.body, module_name,
                parent_name=f"{parent_name}.{child.name}",
            ))
    return symbols


def _make_symbol(
    node: _ClassOrDef,
    module_name: str,
    parent_name: str | None,
) -> Symbol:
    """Create a Symbol from an AST definition node.

    Args:
        node: The AST node (FunctionDef, AsyncFunctionDef, or ClassDef).
        module_name: The dotted module name.
        parent_name: Qualified name of the parent (for methods), or None.

    Returns:
        A populated Symbol object.
    """
    if parent_name is not None:
        qualified_name = f"{module_name}.{parent_name}.{node.name}"
        symbol_type = SymbolType.METHOD
    else:
        qualified_name = f"{module_name}.{node.name}"
        symbol_type = (
            SymbolType.CLASS
            if isinstance(node, ast.ClassDef)
            else SymbolType.FUNCTION
        )

    decorators = _extract_decorators(node)
    docstring = ast.get_docstring(node)
    is_async = isinstance(node, ast.AsyncFunctionDef)

    return Symbol(
        name=node.name,
        qualified_name=qualified_name,
        symbol_type=symbol_type,
        file=Path(""),  # Filled in by caller if needed
        line_number=node.lineno,
        decorators=decorators,
        parent=f"{module_name}.{parent_name}" if parent_name else None,
        is_async=is_async,
        docstring=docstring,
    )


def _extract_decorators(node: _ClassOrDef) -> tuple[str, ...]:
    """Extract decorator names from a definition node.

    Handles ``@name``, ``@name(args)``, ``@obj.attr``, and
    ``@obj.attr(args)`` forms.

    Args:
        node: The AST definition node.

    Returns:
        Tuple of decorator name strings.
    """
    decorators: list[str] = []
    for dec in node.decorator_list:
        decorators.append(_format_decorator(dec))
    return tuple(decorators)


def _format_decorator(node: ast.expr) -> str:
    """Format a decorator AST node as a readable string.

    Args:
        node: The decorator expression node.

    Returns:
        String representation of the decorator.
    """
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Attribute):
        return f"{_format_decorator(node.value)}.{node.attr}"
    elif isinstance(node, ast.Call):
        return _format_decorator(node.func)
    else:
        return ast.unparse(node)


def _extract_all_calls(tree: ast.Module, module_name: str) -> list[CallSite]:
    """Extract all call sites from an AST module.

    Walks the entire tree to find Call nodes, recording the function
    name and any receiver (for method calls like ``obj.method()``).

    Args:
        tree: The parsed AST module.
        module_name: The dotted module name (for context).

    Returns:
        List of CallSite objects.
    """
    extractor = _CallExtractor()
    extractor.visit(tree)
    return extractor.calls


class _CallExtractor(ast.NodeVisitor):
    """AST visitor that collects all Call nodes.

    Records function name, line number, and receiver for method calls.
    """

    def __init__(self) -> None:
        self.calls: list[CallSite] = []

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        name, receiver, is_method = self._resolve_call_name(node.func)
        self.calls.append(CallSite(
            name=name,
            line_number=node.lineno,
            is_method=is_method,
            receiver=receiver,
        ))
        self.generic_visit(node)

    @staticmethod
    def _resolve_call_name(
        node: ast.expr,
    ) -> tuple[str, str | None, bool]:
        """Resolve a call expression to (name, receiver, is_method).

        Args:
            node: The call's function expression.

        Returns:
            Tuple of (name, receiver_or_None, is_method).
        """
        if isinstance(node, ast.Name):
            return node.id, None, False
        elif isinstance(node, ast.Attribute):
            receiver = _CallExtractor._format_receiver(node.value)
            return node.attr, receiver, True
        else:
            return ast.unparse(node), None, False

    @staticmethod
    def _format_receiver(node: ast.expr) -> str:
        """Format a receiver expression as a string.

        Args:
            node: The receiver expression.

        Returns:
            String representation.
        """
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            inner = _CallExtractor._format_receiver(node.value)
            return f"{inner}.{node.attr}"
        elif isinstance(node, ast.Call):
            return _CallExtractor._format_receiver(node.func)
        elif isinstance(node, ast.Subscript):
            return _CallExtractor._format_receiver(node.value)
        else:
            return ast.unparse(node)


def _is_builtin(name: str) -> bool:
    """Check if *name* is a Python builtin.

    Args:
        name: The name to check.

    Returns:
        True if the name is in Python's builtins.
    """
    return name in BUILTIN_NAMES


def _is_stdlib(module: str) -> bool:
    """Check if *module* is part of the Python standard library.

    Checks the top-level package name against the stdlib set.

    Args:
        module: The module name (e.g., ``os.path``).

    Returns:
        True if the top-level package is in the stdlib set.
    """
    top_level = module.split(".")[0] if module else ""
    return top_level in STDLIB_MODULES
