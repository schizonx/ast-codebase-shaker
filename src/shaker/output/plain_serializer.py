"""Plain text output serializer.

Builds plain text output from pruned files, metadata, and file list.
No Markdown formatting — just readable text with clear section separators.
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
    """Build plain text output document.

    Args:
        pruned: Mapping of file paths to their pruned source strings.
        metadata: Build metadata for the header.
        focus_files: Set of file paths marked as focus.
        omitted_files: List of file paths excluded from output.
        include_tree: Whether to include the file tree section.

    Returns:
        Complete plain text document as a string.
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
    """Build the plain text header section."""
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append("Codebase Shaker Output")
    lines.append("=" * 60)
    lines.append(f"Project: {metadata.project_name}")
    if metadata.focus:
        lines.append(f"Focus: {metadata.focus}")
    lines.append(f"Mode: {metadata.mode.value}")
    lines.append(f"Timestamp: {metadata.timestamp}")
    lines.append(f"Version: {metadata.version}")
    if metadata.config_path:
        lines.append(f"Config: {metadata.config_path}")
    lines.append("")
    lines.append("Stats")
    lines.append("-" * 40)
    s = metadata.stats
    lines.append(f"  Files retained: {s.retained_files} / {s.total_files}")
    lines.append(f"  Files omitted:  {s.omitted_files}")
    lines.append(f"  Parse errors:   {s.parse_errors}")
    lines.append(f"  Input tokens:   {s.input_tokens:,}")
    lines.append(f"  Output tokens:  {s.output_tokens:,}")
    if s.reduction_pct is not None:
        lines.append(f"  Reduction:      {s.reduction_pct:.1f}%")
    return "\n".join(lines)


def _build_tree(
    files: list[Path],
    focus_files: set[Path],
    omitted: list[Path],
) -> str:
    """Build a plain text file listing."""
    lines: list[str] = ["File Tree", "-" * 40]
    if not files:
        lines.append("(no files)")
        return "\n".join(lines)
    for fpath in sorted(files):
        marker = "  [FOCUS]" if fpath in focus_files else ""
        lines.append(f"  {fpath}{marker}")
    return "\n".join(lines)


def _build_file_section(
    path: Path,
    source: str,
    is_focus: bool,
    mode: CompressionMode,
) -> str:
    """Build a single file's plain text section."""
    lines: list[str] = []
    badge = ""
    if is_focus:
        badge = " [FOCUS]"
    elif mode != CompressionMode.FULL:
        badge = f" ({mode.value})"
    lines.append(f"{path}{badge}")
    lines.append("-" * 40)
    lines.append(source.rstrip())
    return "\n".join(lines)


def _build_omitted_notice(omitted: list[Path]) -> str:
    """Build the omission notice."""
    lines: list[str] = [
        "Omitted Files",
        "-" * 40,
        f"{len(omitted)} file(s) excluded from output:",
    ]
    for fpath in sorted(omitted):
        lines.append(f"  {fpath}")
    return "\n".join(lines)
