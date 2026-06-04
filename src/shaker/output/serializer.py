"""Stage 6: Markdown document construction.

Builds the full Markdown output from pruned files, metadata, and file lists.
Uses a list-of-strings pattern for efficient string building.
"""

from __future__ import annotations

from pathlib import Path

from shaker.models import CompressionMode, OutputMetadata


def serialize(
    pruned: dict[Path, str],
    metadata: OutputMetadata,
    focus_files: set[Path],
    omitted_files: list[Path],
    include_tree: bool = True,
) -> str:
    """Build the full Markdown output document.

    Assembles the header, file tree, per-file code sections, and
    omission notice into a single Markdown string.

    Args:
        pruned: Mapping of file paths to their pruned source strings.
        metadata: Build metadata for the header.
        focus_files: Set of file paths marked as focus.
        omitted_files: List of file paths excluded from output.
        include_tree: Whether to include the file tree section.

    Returns:
        Complete Markdown document as a string.
    """
    parts: list[str] = []
    parts.append(_build_header(metadata))
    parts.append("")
    if include_tree:
        parts.append(
            _build_tree(list(pruned.keys()), focus_files, omitted_files)
        )
        parts.append("")
    for fpath in sorted(pruned.keys()):
        is_focus = fpath in focus_files
        section = _build_file_section(
            fpath, pruned[fpath], is_focus, metadata.mode
        )
        parts.append(section)
        parts.append("")
    if omitted_files:
        parts.append(_build_omitted_notice(omitted_files))
        parts.append("")
    return "\n".join(parts)


def _build_header(metadata: OutputMetadata) -> str:
    """Build the Markdown header section.

    Contains project name, focus, mode, timestamp, version,
    and build statistics.

    Args:
        metadata: Build metadata.

    Returns:
        Header string with YAML-style frontmatter.
    """
    lines: list[str] = []
    lines.append("# Codebase Shaker Output")
    lines.append("")
    lines.append(f"**Project:** `{metadata.project_name}`")
    if metadata.focus:
        lines.append(f"**Focus:** `{metadata.focus}`")
    lines.append(f"**Mode:** `{metadata.mode.value}`")
    lines.append(f"**Timestamp:** {metadata.timestamp}")
    lines.append(f"**Version:** {metadata.version}")
    if metadata.config_path:
        lines.append(f"**Config:** `{metadata.config_path}`")
    lines.append("")
    stats = metadata.stats
    lines.append("## Stats")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---|")
    lines.append(f"| Files retained | {stats.retained_files} / {stats.total_files} |")
    lines.append(f"| Files omitted | {stats.omitted_files} |")
    lines.append(f"| Parse errors | {stats.parse_errors} |")
    lines.append(f"| Input tokens | {stats.input_tokens:,} |")
    lines.append(f"| Output tokens | {stats.output_tokens:,} |")
    if stats.reduction_pct:
        lines.append(f"| Reduction | {stats.reduction_pct:.1f}% |")
    return "\n".join(lines)


def _build_tree(
    files: list[Path],
    focus_files: set[Path],
    omitted: list[Path],
) -> str:
    """Build an ASCII file tree.

    Lists all retained files in a tree-like format. Focus files
    are marked with ``← FOCUS PATH``. Omitted files are listed
    separately.

    Args:
        files: Retained file paths.
        focus_files: Paths to mark as focus.
        omitted: Omitted file paths.

    Returns:
        ASCII tree string.
    """
    lines: list[str] = ["## File Tree", ""]
    if not files:
        lines.append("*(no files)*")
        return "\n".join(lines)
    for fpath in sorted(files):
        marker = "  ← FOCUS PATH" if fpath in focus_files else ""
        lines.append(f"- `{fpath}`{marker}")
    return "\n".join(lines)


def _build_file_section(
    path: Path,
    source: str,
    is_focus: bool,
    mode: CompressionMode,
) -> str:
    """Build a single file's Markdown section.

    Includes a heading with the file path, focus/compression badge,
    and the code block with Python syntax highlighting.

    Args:
        path: File path for the heading.
        source: Pruned source code.
        is_focus: Whether this is a focus file.
        mode: Compression mode applied.

    Returns:
        Markdown section string for this file.
    """
    lines: list[str] = []
    badge = ""
    if is_focus:
        badge = " **[FOCUS]**"
    elif mode != CompressionMode.FULL:
        badge = f" *({mode.value})*"
    lines.append(f"### `{path}`{badge}")
    lines.append("")
    lines.append("```python")
    lines.append(source.rstrip())
    lines.append("```")
    return "\n".join(lines)


def _build_omitted_notice(omitted: list[Path]) -> str:
    """Build the omission notice.

    Lists all files that were excluded from the output.

    Args:
        omitted: List of omitted file paths.

    Returns:
        Omission notice string.
    """
    lines: list[str] = ["## Omitted Files", ""]
    lines.append(
        f"{len(omitted)} file(s) excluded from output:"
    )
    lines.append("")
    for fpath in sorted(omitted):
        lines.append(f"- `{fpath}`")
    return "\n".join(lines)
