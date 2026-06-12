"""Unit tests for shaker.output.json_serializer.

Covers JSON structure, metadata, file sections, omission list,
and output validity.
"""

from __future__ import annotations

import json
from pathlib import Path

from shaker.models import BuildStats, CompressionMode, OutputMetadata
from shaker.output.json_serializer import serialize


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


class TestJsonSerializer:
    """Tests for the JSON serializer entry point."""

    def test_valid_json(self):
        meta = _make_metadata()
        pruned = {Path("main.py"): "def run():\n    pass\n"}
        result = serialize(pruned, meta, set(), [])
        data = json.loads(result)
        assert isinstance(data, dict)

    def test_contains_metadata(self):
        meta = _make_metadata(project_name="my_project")
        pruned = {Path("a.py"): "x = 1\n"}
        result = serialize(pruned, meta, set(), [])
        data = json.loads(result)
        assert "metadata" in data
        assert data["metadata"]["project"] == "my_project"

    def test_contains_focus(self):
        meta = _make_metadata(focus="auth.login")
        pruned = {Path("a.py"): "x = 1\n"}
        result = serialize(pruned, meta, set(), [])
        data = json.loads(result)
        assert data["metadata"]["focus"] == "auth.login"

    def test_no_focus_key_when_none(self):
        meta = _make_metadata(focus=None)
        pruned = {Path("a.py"): "x = 1\n"}
        result = serialize(pruned, meta, set(), [])
        data = json.loads(result)
        assert "focus" not in data["metadata"]

    def test_contains_mode(self):
        meta = _make_metadata(mode=CompressionMode.STRIP)
        pruned = {Path("a.py"): "x = 1\n"}
        result = serialize(pruned, meta, set(), [])
        data = json.loads(result)
        assert data["metadata"]["mode"] == "strip"

    def test_contains_timestamp(self):
        meta = _make_metadata(timestamp="2026-01-15T10:30:00")
        pruned = {Path("a.py"): "x = 1\n"}
        result = serialize(pruned, meta, set(), [])
        data = json.loads(result)
        assert data["metadata"]["timestamp"] == "2026-01-15T10:30:00"

    def test_contains_version(self):
        meta = _make_metadata(version="1.2.3")
        pruned = {Path("a.py"): "x = 1\n"}
        result = serialize(pruned, meta, set(), [])
        data = json.loads(result)
        assert data["metadata"]["version"] == "1.2.3"

    def test_contains_stats(self):
        meta = _make_metadata()
        pruned = {Path("a.py"): "x = 1\n"}
        result = serialize(pruned, meta, set(), [])
        data = json.loads(result)
        stats = data["metadata"]["stats"]
        assert stats["files_retained"] == 7
        assert stats["files_total"] == 10
        assert stats["files_omitted"] == 3
        assert stats["input_tokens"] == 1000
        assert stats["output_tokens"] == 400
        assert stats["reduction_pct"] == 60.0

    def test_files_array(self):
        meta = _make_metadata()
        pruned = {Path("main.py"): "def run():\n    pass\n"}
        result = serialize(pruned, meta, set(), [])
        data = json.loads(result)
        assert "files" in data
        assert len(data["files"]) == 1
        assert data["files"][0]["path"] == "main.py"
        assert "def run()" in data["files"][0]["code"]

    def test_focus_file_marked(self):
        meta = _make_metadata()
        pruned = {Path("focus.py"): "x = 1\n", Path("other.py"): "y = 2\n"}
        result = serialize(pruned, meta, {Path("focus.py")}, [])
        data = json.loads(result)
        focus_files = [f for f in data["files"] if f["focus"]]
        assert len(focus_files) == 1
        assert focus_files[0]["path"] == "focus.py"

    def test_compression_attribute(self):
        meta = _make_metadata(mode=CompressionMode.SIGNATURES)
        pruned = {Path("other.py"): "x = 1\n"}
        result = serialize(pruned, meta, set(), [])
        data = json.loads(result)
        assert data["files"][0]["compression"] == "signatures"

    def test_full_mode_no_compression_attr(self):
        meta = _make_metadata(mode=CompressionMode.FULL)
        pruned = {Path("other.py"): "x = 1\n"}
        result = serialize(pruned, meta, set(), [])
        data = json.loads(result)
        assert "compression" not in data["files"][0]

    def test_omitted_list(self):
        meta = _make_metadata()
        pruned = {Path("a.py"): "x = 1\n"}
        omitted = [Path("b.py"), Path("c.py")]
        result = serialize(pruned, meta, set(), omitted)
        data = json.loads(result)
        assert "omitted" in data
        assert len(data["omitted"]) == 2
        assert "b.py" in data["omitted"]
        assert "c.py" in data["omitted"]

    def test_omitted_empty_when_none(self):
        meta = _make_metadata()
        pruned = {Path("a.py"): "x = 1\n"}
        result = serialize(pruned, meta, set(), [])
        data = json.loads(result)
        assert data["omitted"] == []

    def test_file_tree_included(self):
        meta = _make_metadata()
        pruned = {Path("a.py"): "x = 1\n"}
        result = serialize(pruned, meta, set(), [])
        data = json.loads(result)
        assert "file_tree" in data["metadata"]
        assert len(data["metadata"]["file_tree"]) == 1

    def test_file_tree_excluded(self):
        meta = _make_metadata()
        pruned = {Path("a.py"): "x = 1\n"}
        result = serialize(pruned, meta, set(), [], include_tree=False)
        data = json.loads(result)
        assert "file_tree" not in data["metadata"]

    def test_empty_pruned(self):
        meta = _make_metadata()
        result = serialize({}, meta, set(), [])
        data = json.loads(result)
        assert data["files"] == []

    def test_unicode_in_paths(self):
        meta = _make_metadata()
        pruned = {Path("src/tëst.py"): "x = 1\n"}
        result = serialize(pruned, meta, set(), [])
        data = json.loads(result)
        assert "tëst.py" in data["files"][0]["path"]

    def test_special_characters_in_code(self):
        meta = _make_metadata()
        pruned = {Path("a.py"): 'x = "hello\\nworld"\t\n'}
        result = serialize(pruned, meta, set(), [])
        data = json.loads(result)
        assert 'hello\\nworld' in data["files"][0]["code"]
