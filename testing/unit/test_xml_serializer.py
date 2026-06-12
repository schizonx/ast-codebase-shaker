"""Unit tests for shaker.output.xml_serializer.

Covers XML structure, metadata, file sections, CDATA handling,
omission notices, and output validity.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from shaker.models import BuildStats, CompressionMode, OutputMetadata
from shaker.output.xml_serializer import serialize


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


class TestXmlSerializer:
    """Tests for the XML serializer entry point."""

    def test_valid_xml(self):
        meta = _make_metadata()
        pruned = {Path("main.py"): "def run():\n    pass\n"}
        result = serialize(pruned, meta, set(), [])
        # Parse to verify valid XML
        root = ET.fromstring(result.split("\n", 1)[1])
        assert root.tag == "codebase-shaker"

    def test_contains_metadata(self):
        meta = _make_metadata(project_name="my_project")
        pruned = {Path("a.py"): "x = 1\n"}
        result = serialize(pruned, meta, set(), [])
        root = ET.fromstring(result.split("\n", 1)[1])
        meta_el = root.find("metadata")
        assert meta_el is not None
        assert meta_el.find("project").text == "my_project"

    def test_contains_focus(self):
        meta = _make_metadata(focus="auth.login")
        pruned = {Path("a.py"): "x = 1\n"}
        result = serialize(pruned, meta, set(), [])
        root = ET.fromstring(result.split("\n", 1)[1])
        assert root.find("metadata/focus").text == "auth.login"

    def test_no_focus_omitted(self):
        meta = _make_metadata(focus=None)
        pruned = {Path("a.py"): "x = 1\n"}
        result = serialize(pruned, meta, set(), [])
        root = ET.fromstring(result.split("\n", 1)[1])
        assert root.find("metadata/focus") is None

    def test_contains_mode(self):
        meta = _make_metadata(mode=CompressionMode.STRIP)
        pruned = {Path("a.py"): "x = 1\n"}
        result = serialize(pruned, meta, set(), [])
        root = ET.fromstring(result.split("\n", 1)[1])
        assert root.find("metadata/mode").text == "strip"

    def test_contains_timestamp(self):
        meta = _make_metadata(timestamp="2026-01-15T10:30:00")
        pruned = {Path("a.py"): "x = 1\n"}
        result = serialize(pruned, meta, set(), [])
        root = ET.fromstring(result.split("\n", 1)[1])
        assert root.find("metadata/timestamp").text == "2026-01-15T10:30:00"

    def test_contains_version(self):
        meta = _make_metadata(version="1.2.3")
        pruned = {Path("a.py"): "x = 1\n"}
        result = serialize(pruned, meta, set(), [])
        root = ET.fromstring(result.split("\n", 1)[1])
        assert root.find("metadata/version").text == "1.2.3"

    def test_contains_stats(self):
        meta = _make_metadata()
        pruned = {Path("a.py"): "x = 1\n"}
        result = serialize(pruned, meta, set(), [])
        root = ET.fromstring(result.split("\n", 1)[1])
        stats = root.find("metadata/stats")
        assert stats.find("files-retained").text == "7"
        assert stats.find("files-total").text == "10"
        assert stats.find("files-omitted").text == "3"
        assert stats.find("input-tokens").text == "1000"
        assert stats.find("output-tokens").text == "400"
        assert stats.find("reduction-pct").text == "60.0"

    def test_files_section(self):
        meta = _make_metadata()
        pruned = {Path("main.py"): "def run():\n    pass\n"}
        result = serialize(pruned, meta, set(), [])
        root = ET.fromstring(result.split("\n", 1)[1])
        files_el = root.find("files")
        assert files_el is not None
        file_els = files_el.findall("file")
        assert len(file_els) == 1
        assert file_els[0].get("path") == "main.py"
        assert "def run()" in file_els[0].text

    def test_focus_file_marked(self):
        meta = _make_metadata()
        pruned = {Path("focus.py"): "x = 1\n", Path("other.py"): "y = 2\n"}
        result = serialize(pruned, meta, {Path("focus.py")}, [])
        root = ET.fromstring(result.split("\n", 1)[1])
        files_el = root.find("files")
        focus_files = files_el.findall("file[@focus='true']")
        assert len(focus_files) == 1
        assert focus_files[0].get("path") == "focus.py"

    def test_compression_attribute(self):
        meta = _make_metadata(mode=CompressionMode.SIGNATURES)
        pruned = {Path("other.py"): "x = 1\n"}
        result = serialize(pruned, meta, set(), [])
        root = ET.fromstring(result.split("\n", 1)[1])
        f = root.find("files/file")
        assert f.get("compression") == "signatures"

    def test_full_mode_no_compression_attr(self):
        meta = _make_metadata(mode=CompressionMode.FULL)
        pruned = {Path("other.py"): "x = 1\n"}
        result = serialize(pruned, meta, set(), [])
        root = ET.fromstring(result.split("\n", 1)[1])
        f = root.find("files/file")
        assert f.get("compression") is None

    def test_omitted_files(self):
        meta = _make_metadata()
        pruned = {Path("a.py"): "x = 1\n"}
        omitted = [Path("b.py"), Path("c.py")]
        result = serialize(pruned, meta, set(), omitted)
        root = ET.fromstring(result.split("\n", 1)[1])
        omitted_el = root.find("omitted")
        assert omitted_el is not None
        assert omitted_el.get("count") == "2"
        paths = [f.get("path") for f in omitted_el.findall("file")]
        assert "b.py" in paths
        assert "c.py" in paths

    def test_no_omitted_when_empty(self):
        meta = _make_metadata()
        pruned = {Path("a.py"): "x = 1\n"}
        result = serialize(pruned, meta, set(), [])
        root = ET.fromstring(result.split("\n", 1)[1])
        assert root.find("omitted") is None

    def test_file_tree_included(self):
        meta = _make_metadata()
        pruned = {Path("a.py"): "x = 1\n"}
        result = serialize(pruned, meta, set(), [])
        root = ET.fromstring(result.split("\n", 1)[1])
        tree = root.find("file-tree")
        assert tree is not None

    def test_file_tree_excluded(self):
        meta = _make_metadata()
        pruned = {Path("a.py"): "x = 1\n"}
        result = serialize(pruned, meta, set(), [], include_tree=False)
        root = ET.fromstring(result.split("\n", 1)[1])
        assert root.find("file-tree") is None

    def test_empty_pruned(self):
        meta = _make_metadata()
        result = serialize({}, meta, set(), [])
        root = ET.fromstring(result.split("\n", 1)[1])
        assert root.find("files") is not None

    def test_special_characters_in_code(self):
        meta = _make_metadata()
        pruned = {Path("a.py"): 'x = "<tag>&amp;</tag>"\n'}
        result = serialize(pruned, meta, set(), [])
        # Must still be valid XML
        root = ET.fromstring(result.split("\n", 1)[1])
        f = root.find("files/file")
        assert "<tag>" in f.text

    def test_unicode_in_paths(self):
        meta = _make_metadata()
        pruned = {Path("src/tëst.py"): "x = 1\n"}
        result = serialize(pruned, meta, set(), [])
        root = ET.fromstring(result.split("\n", 1)[1])
        f = root.find("files/file")
        assert "tëst.py" in f.get("path")

    def test_xml_declaration_present(self):
        meta = _make_metadata()
        pruned = {Path("a.py"): "x = 1\n"}
        result = serialize(pruned, meta, set(), [])
        assert result.startswith('<?xml version="1.0" encoding="UTF-8"?>')

    def test_config_path_in_metadata(self):
        meta = _make_metadata(config_path=Path(".shakerrc.json"))
        pruned = {Path("a.py"): "x = 1\n"}
        result = serialize(pruned, meta, set(), [])
        root = ET.fromstring(result.split("\n", 1)[1])
        assert root.find("metadata/config").text == ".shakerrc.json"
