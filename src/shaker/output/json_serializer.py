"""JSON output serializer.

Builds JSON output from pruned files, metadata, and file list.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from shaker.models import CompressionMode, OutputMetadata


def serialize(
    pruned: dict[Path, str],
    metadata: OutputMetadata,
    focus_files: set[Path],
    omitted_files: list[Path],
    include_tree: bool = True,
) -> str:
    """Build JSON output document.

    Args:
        pruned: Mapping of file paths to their pruned source strings.
        metadata: Build metadata for the header.
        focus_files: Set of file paths marked as focus.
        omitted_files: List of file paths excluded from output.
        include_tree: Whether to include the file tree section.

    Returns:
        Complete JSON document as a string.
    """
    doc: dict[str, Any] = {
        "metadata": _build_metadata(metadata, include_tree, pruned, focus_files, omitted_files),
        "files": _build_files(pruned, focus_files, metadata.mode),
        "omitted": [str(p) for p in sorted(omitted_files)],
    }
    return json.dumps(doc, indent=2) + "\n"


def _build_metadata(
    metadata: OutputMetadata,
    include_tree: bool,
    pruned: dict[Path, str],
    focus_files: set[Path],
    omitted_files: list[Path],
) -> dict[str, Any]:
    """Build the metadata section."""
    s = metadata.stats
    result: dict[str, Any] = {
        "project": metadata.project_name,
        "version": metadata.version,
        "timestamp": metadata.timestamp,
        "mode": metadata.mode.value,
        "stats": {
            "files_retained": s.retained_files,
            "files_total": s.total_files,
            "files_omitted": s.omitted_files,
            "parse_errors": s.parse_errors,
            "input_tokens": s.input_tokens,
            "output_tokens": s.output_tokens,
        },
    }
    if metadata.focus:
        result["focus"] = metadata.focus
    if metadata.config_path:
        result["config"] = str(metadata.config_path)
    if s.reduction_pct is not None:
        result["stats"]["reduction_pct"] = round(s.reduction_pct, 1)
    if include_tree:
        result["file_tree"] = [
            {
                "path": str(p),
                "focus": p in focus_files,
            }
            for p in sorted(pruned.keys())
        ]
    return result


def _build_files(
    pruned: dict[Path, str],
    focus_files: set[Path],
    mode: CompressionMode,
) -> list[dict[str, Any]]:
    """Build the files array."""
    files: list[dict[str, Any]] = []
    for fpath in sorted(pruned.keys()):
        is_focus = fpath in focus_files
        entry: dict[str, Any] = {
            "path": str(fpath),
            "focus": is_focus,
        }
        if not is_focus and mode != CompressionMode.FULL:
            entry["compression"] = mode.value
        entry["code"] = pruned[fpath]
        files.append(entry)
    return files
