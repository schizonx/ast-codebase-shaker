"""Unit tests for shaker.output.plain_serializer.

Covers plain text structure, metadata, file sections, absence of
Markdown syntax, and omission notices.
"""

from __future__ import annotations

from pathlib import Path

from shaker.models import BuildStats, CompressionMode, OutputMetadata
from shaker.output.plain_serializer import serialize


def _make_metadata(**kwargs: object) -> OutputMetadata:
    """Helper: create OutputMetadata with sensible defaults."""
    defaults: dict[str, object] = {
        "project_name": "test_project",
        "focus": None,
        "mode": CompressionMode.SIGNATURES,
        "config_path": None,
        "timestamp": "2026-06-03T12:00:00",
        "version": "1.0.0",
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


class TestPlainSerializer:
    """Tests for the plain text serializer entry point."""

    def test_contains_project_name(self):
        meta = _make_metadata(project_name="my_project")
        pruned = {Path("a.py"): "x = 1\n"}
        result = serialize(pruned, meta, set(), [])
        assert "Project: my_project" in result

    def test_contains_focus(self):
        meta = _make_metadata(focus="auth.login")
        pruned = {Path("a.py"): "x = 1\n"}
        result = serialize(pruned, meta, set(), [])
        assert "Focus: auth.login" in result

    def test_no_focus_line_when_none(self):
        meta = _make_metadata(focus=None)
        pruned = {Path("a.py"): "x = 1\n"}
        result = serialize(pruned, meta, set(), [])
        assert "Focus:" not in result

    def test_contains_mode(self):
        meta = _make_metadata(mode=CompressionMode.STRIP)
        pruned = {Path("a.py"): "x = 1\n"}
        result = serialize(pruned, meta, set(), [])
        assert "Mode: strip" in result

    def test_contains_timestamp(self):
        meta = _make_metadata(timestamp="2026-01-15T10:30:00")
        pruned = {Path("a.py"): "x = 1\n"}
        result = serialize(pruned, meta, set(), [])
        assert "Timestamp: 2026-01-15T10:30:00" in result

    def test_contains_version(self):
        meta = _make_metadata(version="1.2.3")
        pruned = {Path("a.py"): "x = 1\n"}
        result = serialize(pruned, meta, set(), [])
        assert "Version: 1.2.3" in result

    def test_contains_stats(self):
        meta = _make_metadata()
        pruned = {Path("a.py"): "x = 1\n"}
        result = serialize(pruned, meta, set(), [])
        assert "Files retained: 7 / 10" in result
        assert "Input tokens:   1,000" in result
        assert "Reduction:      60.0%" in result

    def test_no_markdown_headers(self):
        meta = _make_metadata()
        pruned = {Path("a.py"): "x = 1\n"}
        result = serialize(pruned, meta, set(), [])
        # Should not contain Markdown-style # headers
        for line in result.splitlines():
            stripped = line.lstrip()
            assert not stripped.startswith("#"), f"Markdown header found: {stripped}"

    def test_no_markdown_code_blocks(self):
        meta = _make_metadata()
        pruned = {Path("a.py"): "x = 1\n"}
        result = serialize(pruned, meta, set(), [])
        assert "```" not in result

    def test_no_backtick_wrapping(self):
        meta = _make_metadata()
        pruned = {Path("src/main.py"): "x = 1\n"}
        result = serialize(pruned, meta, set(), [])
        # Paths should appear without backtick wrapping
        assert "main.py" in result
        assert "`src/main.py`" not in result

    def test_contains_file_content(self):
        meta = _make_metadata()
        pruned = {Path("a.py"): "def hello():\n    pass\n"}
        result = serialize(pruned, meta, set(), [])
        assert "def hello():" in result
        assert "pass" in result

    def test_focus_badge(self):
        meta = _make_metadata()
        pruned = {Path("focus.py"): "x = 1\n"}
        result = serialize(pruned, meta, {Path("focus.py")}, [])
        assert "[FOCUS]" in result

    def test_compression_badge(self):
        meta = _make_metadata(mode=CompressionMode.STRIP)
        pruned = {Path("other.py"): "x = 1\n"}
        result = serialize(pruned, meta, set(), [])
        assert "(strip)" in result

    def test_full_mode_no_badge(self):
        meta = _make_metadata(mode=CompressionMode.FULL)
        pruned = {Path("other.py"): "x = 1\n"}
        result = serialize(pruned, meta, set(), [])
        assert "(full)" not in result

    def test_omitted_notice(self):
        meta = _make_metadata()
        pruned = {Path("a.py"): "x = 1\n"}
        omitted = [Path("b.py"), Path("c.py")]
        result = serialize(pruned, meta, set(), omitted)
        assert "Omitted Files" in result
        assert "2 file(s) excluded" in result
        assert "b.py" in result
        assert "c.py" in result

    def test_no_markdown_in_omitted(self):
        meta = _make_metadata()
        pruned = {Path("a.py"): "x = 1\n"}
        omitted = [Path("b.py")]
        result = serialize(pruned, meta, set(), omitted)
        lines = result.splitlines()
        for line in lines:
            stripped = line.lstrip()
            assert not stripped.startswith("- `"), f"Markdown list found: {line}"

    def test_file_tree_included(self):
        meta = _make_metadata()
        pruned = {Path("a.py"): "x = 1\n"}
        result = serialize(pruned, meta, set(), [])
        assert "File Tree" in result

    def test_file_tree_excluded(self):
        meta = _make_metadata()
        pruned = {Path("a.py"): "x = 1\n"}
        result = serialize(pruned, meta, set(), [], include_tree=False)
        assert "File Tree" not in result

    def test_empty_pruned(self):
        meta = _make_metadata()
        result = serialize({}, meta, set(), [])
        assert "Codebase Shaker Output" in result

    def test_unicode_in_paths(self):
        meta = _make_metadata()
        pruned = {Path("src/tëst.py"): "x = 1\n"}
        result = serialize(pruned, meta, set(), [])
        assert "tëst.py" in result
