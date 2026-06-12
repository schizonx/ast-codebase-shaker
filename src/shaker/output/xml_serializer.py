"""XML output serializer.

Builds XML output from pruned files, metadata, and file list.
Uses xml.etree.ElementTree for safe XML generation with CDATA sections.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from shaker.models import CompressionMode, OutputMetadata


def serialize(
    pruned: dict[Path, str],
    metadata: OutputMetadata,
    focus_files: set[Path],
    omitted_files: list[Path],
    include_tree: bool = True,
) -> str:
    """Build XML output document.

    Args:
        pruned: Mapping of file paths to their pruned source strings.
        metadata: Build metadata for the header.
        focus_files: Set of file paths marked as focus.
        omitted_files: List of file paths excluded from output.
        include_tree: Whether to include the file tree section.

    Returns:
        Complete XML document as a string.
    """
    root = ET.Element("codebase-shaker")

    _append_metadata(root, metadata)
    if include_tree:
        _append_tree(root, list(pruned.keys()), focus_files, omitted_files)
    _append_files(root, pruned, focus_files, metadata.mode)
    _append_omitted(root, omitted_files)

    ET.indent(root, space="  ")
    return "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n" + ET.tostring(
        root, encoding="unicode"
    )


def _append_metadata(parent: ET.Element, metadata: OutputMetadata) -> None:
    """Append the metadata element with all build information."""
    meta = ET.SubElement(parent, "metadata")

    ET.SubElement(meta, "project").text = metadata.project_name
    if metadata.focus:
        ET.SubElement(meta, "focus").text = metadata.focus
    ET.SubElement(meta, "mode").text = metadata.mode.value
    ET.SubElement(meta, "timestamp").text = metadata.timestamp
    ET.SubElement(meta, "version").text = metadata.version
    if metadata.config_path:
        ET.SubElement(meta, "config").text = str(metadata.config_path)

    stats = ET.SubElement(meta, "stats")
    s = metadata.stats
    ET.SubElement(stats, "files-retained").text = str(s.retained_files)
    ET.SubElement(stats, "files-total").text = str(s.total_files)
    ET.SubElement(stats, "files-omitted").text = str(s.omitted_files)
    ET.SubElement(stats, "parse-errors").text = str(s.parse_errors)
    ET.SubElement(stats, "input-tokens").text = str(s.input_tokens)
    ET.SubElement(stats, "output-tokens").text = str(s.output_tokens)
    if s.reduction_pct is not None:
        ET.SubElement(stats, "reduction-pct").text = f"{s.reduction_pct:.1f}"


def _append_tree(
    parent: ET.Element,
    files: list[Path],
    focus_files: set[Path],
    omitted: list[Path],
) -> None:
    """Append the file tree element."""
    tree = ET.SubElement(parent, "file-tree")
    for fpath in sorted(files):
        f = ET.SubElement(tree, "file")
        f.set("path", str(fpath))
        if fpath in focus_files:
            f.set("focus", "true")
    if omitted:
        omitted_el = ET.SubElement(tree, "omitted-files")
        for fpath in sorted(omitted):
            f = ET.SubElement(omitted_el, "file")
            f.set("path", str(fpath))


def _append_files(
    parent: ET.Element,
    pruned: dict[Path, str],
    focus_files: set[Path],
    mode: CompressionMode,
) -> None:
    """Append the files element with code content in CDATA sections."""
    container = ET.SubElement(parent, "files")
    for fpath in sorted(pruned.keys()):
        f = ET.SubElement(container, "file")
        f.set("path", str(fpath))
        is_focus = fpath in focus_files
        if is_focus:
            f.set("focus", "true")
        elif mode != CompressionMode.FULL:
            f.set("compression", mode.value)
        f.text = pruned[fpath]


def _append_omitted(parent: ET.Element, omitted: list[Path]) -> None:
    """Append omitted files notice."""
    if not omitted:
        return
    container = ET.SubElement(parent, "omitted")
    container.set("count", str(len(omitted)))
    for fpath in sorted(omitted):
        f = ET.SubElement(container, "file")
        f.set("path", str(fpath))
