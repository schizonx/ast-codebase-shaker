"""File importance scoring.

Scores files by their importance in the call graph using:
- Importer count: how many other files import symbols from this file
- Graph centrality: how central the file's symbols are in the call graph
- Git changes (optional): how many commits touched this file in the last 30 days

Git scoring is optional and gracefully degrades when git is not available
or the directory is not a git repository.
"""

from __future__ import annotations

import logging
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Protocol

from shaker.models import CallGraph, FileScore, ParsedFile

logger = logging.getLogger(__name__)


class Scorer(Protocol):
    """Protocol for file scoring strategies."""

    def score(
        self,
        parsed: dict[Path, ParsedFile],
        call_graph: CallGraph,
        focus_files: set[Path],
    ) -> dict[Path, FileScore]:
        """Score all files.

        Args:
            parsed: Mapping of file paths to parsed files.
            call_graph: The built call graph.
            focus_files: Set of focus file paths.

        Returns:
            Mapping of file paths to their importance scores.
        """
        ...


class StaticScorer:
    """Score files using importer count and graph centrality.

    This is the default scorer. It works without git and provides
    reliable results based purely on the call graph structure.

    The score is a weighted combination:
    - 50% importer count (normalized)
    - 50% graph centrality (normalized)
    """

    def score(
        self,
        parsed: dict[Path, ParsedFile],
        call_graph: CallGraph,
        focus_files: set[Path],
    ) -> dict[Path, FileScore]:
        """Score files using static analysis only."""
        if not parsed:
            return {}

        importer_counts = _count_importers(parsed, call_graph)
        centralities = _compute_centrality(call_graph, parsed)

        max_importers = max(importer_counts.values()) if importer_counts else 1
        max_centrality = max(centralities.values()) if centralities else 1
        if max_importers == 0:
            max_importers = 1
        if max_centrality == 0:
            max_centrality = 1

        scores: dict[Path, FileScore] = {}
        for fpath in parsed:
            imp = importer_counts.get(fpath, 0) / max_importers
            cent = centralities.get(fpath, 0.0) / max_centrality
            combined = 0.5 * imp + 0.5 * cent
            scores[fpath] = FileScore(
                file=fpath,
                score=round(combined, 4),
                importer_count=importer_counts.get(fpath, 0),
                centrality=round(centralities.get(fpath, 0.0), 4),
                is_focus=fpath in focus_files,
            )

        return scores


class GitScorer:
    """Score files with git change history enhancement.

    Extends StaticScorer with git commit frequency data.
    Falls back to StaticScorer when git is unavailable.

    The score is a weighted combination:
    - 40% importer count (normalized)
    - 40% graph centrality (normalized)
    - 20% git changes in last 30 days (normalized)
    """

    def score(
        self,
        parsed: dict[Path, ParsedFile],
        call_graph: CallGraph,
        focus_files: set[Path],
    ) -> dict[Path, FileScore]:
        """Score files with git enhancement."""
        static = StaticScorer()
        base_scores = static.score(parsed, call_graph, focus_files)

        git_changes = _count_git_changes(parsed)

        if not git_changes:
            return base_scores

        max_changes = max(git_changes.values()) if git_changes else 1
        if max_changes == 0:
            max_changes = 1

        scores: dict[Path, FileScore] = {}
        for fpath, base in base_scores.items():
            git_score = git_changes.get(fpath, 0) / max_changes
            combined = 0.4 * (base.importer_count / max(
                s.importer_count for s in base_scores.values()
            ) if base_scores else 0) + \
                0.4 * (base.centrality / max(
                    s.centrality for s in base_scores.values()
                ) if base_scores else 0) + \
                0.2 * git_score
            scores[fpath] = FileScore(
                file=fpath,
                score=round(combined, 4),
                importer_count=base.importer_count,
                centrality=base.centrality,
                git_changes_30d=git_changes.get(fpath, 0),
                is_focus=fpath in focus_files,
            )

        return scores


def score_files(
    parsed: dict[Path, ParsedFile],
    call_graph: CallGraph,
    focus_files: set[Path],
    use_git: bool = True,
) -> dict[Path, FileScore]:
    """Score all files by importance.

    Args:
        parsed: Mapping of file paths to parsed files.
        call_graph: The built call graph.
        focus_files: Set of focus file paths.
        use_git: Whether to enhance scoring with git history.

    Returns:
        Mapping of file paths to their importance scores.
    """
    if use_git:
        scorer: Scorer = GitScorer()
    else:
        scorer = StaticScorer()
    return scorer.score(parsed, call_graph, focus_files)


def _count_importers(
    parsed: dict[Path, ParsedFile],
    call_graph: CallGraph,
) -> dict[Path, int]:
    """Count how many other files import from each file.

    For each file, counts the number of distinct other files that
    import at least one symbol defined in it.

    Args:
        parsed: Mapping of file paths to parsed files.
        call_graph: The built call graph.

    Returns:
        Mapping of file paths to importer counts.
    """
    file_modules: dict[str, Path] = {}
    for fpath, pf in parsed.items():
        file_modules[pf.module_name] = fpath

    importer_counts: dict[Path, int] = defaultdict(int)

    for fpath, pf in parsed.items():
        for imp in pf.imports:
            if imp.module in file_modules:
                target = file_modules[imp.module]
                if target != fpath:
                    importer_counts[target] += 1

    return dict(importer_counts)


def _compute_centrality(
    call_graph: CallGraph,
    parsed: dict[Path, ParsedFile],
) -> dict[Path, float]:
    """Compute per-file centrality from the call graph.

    Uses degree centrality averaged across all symbols in each file.

    Args:
        call_graph: The built call graph.
        parsed: Mapping of file paths to parsed files.

    Returns:
        Mapping of file paths to centrality scores.
    """
    try:
        import networkx as nx  # type: ignore[import-untyped]

        centrality = nx.degree_centrality(call_graph.graph)
    except Exception:
        return {fpath: 0.0 for fpath in parsed}

    file_symbols: dict[Path, list[str]] = defaultdict(list)
    for sym in call_graph.symbol_table.values():
        file_symbols[sym.file].append(sym.qualified_name)

    result: dict[Path, float] = {}
    for fpath in parsed:
        symbols = file_symbols.get(fpath, [])
        if symbols:
            total = sum(centrality.get(s, 0.0) for s in symbols)
            result[fpath] = total / len(symbols)
        else:
            result[fpath] = 0.0

    return result


def _count_git_changes(
    parsed: dict[Path, ParsedFile],
) -> dict[Path, int]:
    """Count git commits per file in the last 30 days.

    Returns an empty dict if git is not available or the directory
    is not a git repository.

    Args:
        parsed: Mapping of file paths to parsed files.

    Returns:
        Mapping of file paths to commit counts (last 30 days).
    """
    if not parsed:
        return {}

    root = _find_git_root(next(iter(parsed)))
    if root is None:
        return {}

    try:
        result = subprocess.run(
            [
                "git", "log", "--since=30 days ago",
                "--pretty=format:", "--name-only",
            ],
            capture_output=True,
            text=True,
            cwd=str(root),
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        logger.debug("Git not available or timed out")
        return {}

    if result.returncode != 0:
        return {}

    changes: dict[Path, int] = defaultdict(int)
    for line in result.stdout.splitlines():
        line = line.strip()
        if line:
            p = Path(line)
            changes[p] += 1

    return dict(changes)


def _find_git_root(start: Path) -> Path | None:
    """Find the git root directory starting from a file path.

    Args:
        start: File or directory path to start searching from.

    Returns:
        Path to the git root, or None if not found.
    """
    current = start if start.is_dir() else start.parent
    for parent in [current, *current.parents]:
        if (parent / ".git").is_dir():
            return parent
    return None
