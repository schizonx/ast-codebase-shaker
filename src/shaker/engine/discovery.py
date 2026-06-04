"""Stage 1: File discovery with gitignore support.

Walks a directory tree to find .py files, filters by .gitignore rules
using pathspec, and applies config exclude patterns.
"""

from __future__ import annotations

import fnmatch
import os
import warnings
from pathlib import Path

import pathspec

from shaker.models import Config


def discover_files(path: Path, config: Config) -> list[Path]:
    """Discover .py files under *path*, respecting gitignore and config.

    Walks the directory tree, applies .gitignore rules via pathspec,
    then applies config exclude_patterns. Files matching
    config.always_include are kept regardless of other rules. Files
    matching config.always_exclude are always removed.

    Args:
        path: Root directory to search (or a single .py file).
        config: Application configuration with exclude/include rules.

    Returns:
        Sorted list of discovered .py file paths.

    Raises:
        FileNotFoundError: If *path* does not exist.
    """
    if not path.exists():
        raise FileNotFoundError(f"Path not found: {path}")

    if path.is_file():
        if path.suffix == ".py":
            return [path]
        return []

    gitignore_spec = _load_gitignore(path)
    always_include = list(config.always_include)
    always_exclude = list(config.always_exclude)
    exclude_patterns = list(config.exclude_patterns)

    results: list[Path] = []

    for file_path in _walk_directory(path):
        if file_path.suffix != ".py":
            continue

        rel = file_path.relative_to(path)

        # always_exclude wins over everything
        if _matches_any(rel, always_exclude):
            continue

        # always_include wins over gitignore and exclude_patterns
        if _matches_any(rel, always_include):
            results.append(file_path)
            continue

        # Apply gitignore rules
        if gitignore_spec and gitignore_spec.match_file(str(rel)):
            continue

        # Apply config exclude patterns
        if _matches_exclude(rel, exclude_patterns):
            continue

        results.append(file_path)

    results.sort()
    return results


def _walk_directory(path: Path) -> list[Path]:
    """Recursively walk *path* and yield all files.

    Skips directories that cannot be read (permission denied),
    emitting a warning. Does not follow symlinks.

    Args:
        path: Root directory to walk.

    Returns:
        List of file paths found under *path*.
    """
    results: list[Path] = []
    _walk_recursive(path, results, depth=0)
    return results


def _walk_recursive(current: Path, results: list[Path], depth: int) -> None:
    """Inner recursive walker with depth guard.

    Args:
        current: Current directory being walked.
        results: Accumulator for found files.
        depth: Current recursion depth (safety guard).
    """
    if depth > 100:
        warnings.warn(
            f"Directory nesting exceeds 100 levels at {current}, stopping.",
            stacklevel=2,
        )
        return

    try:
        entries = list(os.scandir(current))
    except PermissionError:
        warnings.warn(
            f"Permission denied: {current}, skipping.",
            stacklevel=2,
        )
        return
    except OSError as exc:
        warnings.warn(
            f"Error reading directory {current}: {exc}, skipping.",
            stacklevel=2,
        )
        return

    for entry in sorted(entries, key=lambda e: e.name):
        try:
            if entry.is_symlink():
                continue
            if entry.is_dir(follow_symlinks=False):
                _walk_recursive(Path(entry.path), results, depth + 1)
            elif entry.is_file(follow_symlinks=False):
                results.append(Path(entry.path))
        except OSError as exc:
            warnings.warn(
                f"Error accessing {entry.path}: {exc}, skipping.",
                stacklevel=2,
            )


def _matches_exclude(file: Path, patterns: list[str]) -> bool:
    """Check if *file* matches any of the exclude glob patterns.

    Patterns are matched against the file path as a string using
    Unix shell-style wildcards via fnmatch.

    Args:
        file: Relative file path to check.
        patterns: List of glob patterns (e.g., ``*_test.py``).

    Returns:
        True if *file* matches any pattern.
    """
    return _matches_any(file, patterns)


def _matches_any(file: Path, patterns: list[str]) -> bool:
    """Check if *file* matches any glob pattern in *patterns*.

    Uses forward-slash normalized paths for matching so patterns
    work consistently across platforms. Also checks each path component
    so directory-prefix patterns like ``migrations/`` match nested files.

    Args:
        file: Relative file path to check.
        patterns: List of glob patterns.

    Returns:
        True if *file* matches any pattern.
    """
    file_str = file.as_posix()
    parts = file_str.split("/")
    for pattern in patterns:
        # Match against full relative path
        if fnmatch.fnmatch(file_str, pattern):
            return True
        # Match against filename alone
        if fnmatch.fnmatch(parts[-1], pattern):
            return True
        # Match directory-prefix patterns: "migrations/" matches
        # "migrations/001_init.py" by checking if any parent dir matches
        if pattern.endswith("/"):
            dir_pattern = pattern.rstrip("/")
            for part in parts[:-1]:
                if fnmatch.fnmatch(part, dir_pattern):
                    return True
        # Match against any individual path component (handles
        # patterns like "tests/" matching "src/tests/foo.py")
        for i in range(len(parts)):
            subpath = "/".join(parts[i:])
            if fnmatch.fnmatch(subpath, pattern):
                return True
    return False


def _load_gitignore(path: Path) -> pathspec.PathSpec | None:  # type: ignore[type-arg]
    """Load .gitignore from *path* using pathspec.

    Reads the .gitignore file at the root of the search path and
    returns a compiled PathSpec for matching. Returns None if no
    .gitignore exists.

    Args:
        path: Root directory that may contain .gitignore.

    Returns:
        Compiled PathSpec, or None if no .gitignore found.
    """
    gitignore_path = path / ".gitignore"
    if not gitignore_path.is_file():
        return None

    try:
        lines = gitignore_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None

    return pathspec.PathSpec.from_lines("gitignore", lines)
