"""Unit tests for shaker.output.serializer.

Covers header construction, file tree, per-file sections,
omission notice, edge cases, and formatting requirements.
"""

from __future__ import annotations

from pathlib import Path

from shaker.models import BuildStats, CompressionMode, OutputMetadata
from shaker.output.serializer import (
    _build_file_section,
    _build_header,
    _build_omitted_notice,
    _build_tree,
    serialize,
)


def _make_metadata(**kwargs: object) -> OutputMetadata:
    """Helper: create OutputMetadata with sensible defaults."""
    defaults: dict[str, object] = {
        "project_name": "test_project",
        "focus": None,
        "mode": CompressionMode.SIGNATURES,
        "config_path": None,
        "timestamp": "2026-06-03T12:00:00",
        "version": "0.1.0",
        "stats": BuildStats(
            total_files=10,
            retained_files=7,
            omitted_files=3,
            parse_errors=0,
            total_lines=500,
            output_lines=200,
            input_tokens=1000,
            output_tokens=400,
            reduction_pct=60.0,
        ),
    }
    defaults.update(kwargs)
    return OutputMetadata(**defaults)


class TestBuildHeader:
    """Tests for _build_header."""

    def test_contains_project_name(self):
        meta = _make_metadata(project_name="my_project")
        result = _build_header(meta)
        assert "my_project" in result

    def test_contains_focus(self):
        meta = _make_metadata(focus="auth.login")
        result = _build_header(meta)
        assert "auth.login" in result

    def test_contains_mode(self):
        meta = _make_metadata(mode=CompressionMode.STRIP)
        result = _build_header(meta)
        assert "strip" in result

    def test_contains_timestamp(self):
        meta = _make_metadata(timestamp="2026-01-15T10:30:00")
        result = _build_header(meta)
        assert "2026-01-15T10:30:00" in result

    def test_contains_version(self):
        meta = _make_metadata(version="1.2.3")
        result = _build_header(meta)
        assert "1.2.3" in result

    def test_contains_stats(self):
        meta = _make_metadata()
        result = _build_header(meta)
        assert "7 / 10" in result
        assert "60.0%" in result

    def test_config_path_shown(self):
        meta = _make_metadata(config_path=Path(".shakerrc.json"))
        result = _build_header(meta)
        assert ".shakerrc.json" in result

    def test_no_focus_omitted(self):
        meta = _make_metadata(focus=None)
        result = _build_header(meta)
        assert "**Focus:**" not in result


class TestBuildTree:
    """Tests for _build_tree."""

    def test_empty_files(self):
        result = _build_tree([], set(), [])
        assert "(no files)" in result

    def test_single_file(self):
        result = _build_tree([Path("a.py")], set(), [])
        assert "`a.py`" in result

    def test_multiple_files_sorted(self):
        result = _build_tree(
            [Path("c.py"), Path("a.py"), Path("b.py")], set(), []
        )
        lines = [ln for ln in result.splitlines() if ln.startswith("-")]
        paths = [ln.split("`")[1] for ln in lines]
        assert paths == ["a.py", "b.py", "c.py"]

    def test_focus_file_marked(self):
        result = _build_tree(
            [Path("a.py"), Path("focus.py")],
            {Path("focus.py")},
            [],
        )
        assert "FOCUS PATH" in result
        lines = result.splitlines()
        focus_line = [ln for ln in lines if "focus.py" in ln][0]
        assert "← FOCUS PATH" in focus_line

    def test_non_focus_not_marked(self):
        result = _build_tree([Path("a.py")], set(), [])
        assert "FOCUS PATH" not in result


class TestBuildFileSection:
    """Tests for _build_file_section."""

    def test_path_in_heading(self):
        p = Path("src") / "main.py"
        result = _build_file_section(
            p, "x = 1\n", False, CompressionMode.FULL
        )
        assert "main.py" in result
        assert "src" in result

    def test_focus_badge(self):
        result = _build_file_section(
            Path("f.py"), "x = 1\n", True, CompressionMode.FULL
        )
        assert "[FOCUS]" in result

    def test_compression_badge(self):
        result = _build_file_section(
            Path("f.py"), "x = 1\n", False, CompressionMode.SIGNATURES
        )
        assert "signatures" in result

    def test_code_block_present(self):
        result = _build_file_section(
            Path("f.py"), "x = 1\n", False, CompressionMode.FULL
        )
        assert "```python" in result
        assert "```" in result
        assert "x = 1" in result

    def test_full_mode_no_badge(self):
        result = _build_file_section(
            Path("f.py"), "x = 1\n", False, CompressionMode.FULL
        )
        assert "[" not in result.split("###")[1].split("```")[0]


class TestBuildOmittedNotice:
    """Tests for _build_omitted_notice."""

    def test_empty_omitted(self):
        result = _build_omitted_notice([])
        assert "0 file(s) excluded" in result

    def test_single_file(self):
        result = _build_omitted_notice([Path("a.py")])
        assert "`a.py`" in result
        assert "1 file(s)" in result

    def test_multiple_files(self):
        result = _build_omitted_notice(
            [Path("a.py"), Path("b.py"), Path("c.py")]
        )
        assert "3 file(s)" in result
        assert "`a.py`" in result
        assert "`b.py`" in result
        assert "`c.py`" in result


class TestSerialize:
    """Integration tests for the serialize() entry point."""

    def test_contains_all_sections(self):
        meta = _make_metadata(focus="main.run")
        pruned = {Path("main.py"): "def run():\n    pass\n"}
        result = serialize(pruned, meta, {Path("main.py")}, [])
        assert "# Codebase Shaker Output" in result
        assert "## File Tree" in result
        assert "### `main.py`" in result
        assert "```python" in result

    def test_empty_pruned(self):
        meta = _make_metadata()
        result = serialize({}, meta, set(), [])
        assert "# Codebase Shaker Output" in result

    def test_omitted_notice_included(self):
        meta = _make_metadata()
        pruned = {Path("a.py"): "x = 1\n"}
        omitted = [Path("b.py"), Path("c.py")]
        result = serialize(pruned, meta, set(), omitted)
        assert "## Omitted Files" in result
        assert "2 file(s) excluded" in result

    def test_omitted_notice_absent_when_none(self):
        meta = _make_metadata()
        pruned = {Path("a.py"): "x = 1\n"}
        result = serialize(pruned, meta, set(), [])
        assert "## Omitted Files" not in result

    def test_unicode_in_paths(self):
        meta = _make_metadata()
        pruned = {Path("src/tëst/文件.py"): "x = 1\n"}
        result = serialize(pruned, meta, set(), [])
        assert "文件.py" in result

    def test_long_path(self):
        meta = _make_metadata()
        long_path = Path("a" * 100) / Path("b" * 50) / "file.py"
        pruned = {long_path: "x = 1\n"}
        result = serialize(pruned, meta, set(), [])
        assert "file.py" in result
