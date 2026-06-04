"""Unit tests for shaker.output.clipboard.

Covers clipboard delivery, file write, error handling,
and graceful degradation when clipboard is unavailable.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from shaker.output.clipboard import (
    _copy_to_clipboard,
    _write_to_file,
    deliver,
)


class TestCopyToClipboard:
    """Tests for _copy_to_clipboard."""

    def test_returns_false_when_pyperclip_unavailable(self):
        with patch("shaker.output.clipboard._pyperclip", None):
            result = _copy_to_clipboard("hello")
            assert result is False

    def test_returns_true_when_copy_succeeds(self):
        mock_clipboard = MagicMock()
        with (
            patch("shaker.output.clipboard._HAS_CLIPBOARD", True),
            patch("shaker.output.clipboard._pyperclip", mock_clipboard),
        ):
            result = _copy_to_clipboard("hello")
            assert result is True
            mock_clipboard.copy.assert_called_once_with("hello")

    def test_returns_false_on_exception(self):
        mock_clipboard = MagicMock()
        mock_clipboard.copy.side_effect = RuntimeError("no display")
        with (
            patch("shaker.output.clipboard._HAS_CLIPBOARD", True),
            patch("shaker.output.clipboard._pyperclip", mock_clipboard),
        ):
            result = _copy_to_clipboard("hello")
            assert result is False


class TestWriteToFile:
    """Tests for _write_to_file."""

    def test_writes_content(self, tmp_path: Path):
        dest = tmp_path / "output.md"
        _write_to_file("hello world", dest)
        assert dest.read_text(encoding="utf-8") == "hello world"

    def test_creates_parent_directories(self, tmp_path: Path):
        dest = tmp_path / "sub" / "dir" / "output.md"
        _write_to_file("content", dest)
        assert dest.exists()
        assert dest.read_text(encoding="utf-8") == "content"

    def test_overwrites_existing(self, tmp_path: Path):
        dest = tmp_path / "output.md"
        dest.write_text("old", encoding="utf-8")
        _write_to_file("new", dest)
        assert dest.read_text(encoding="utf-8") == "new"

    def test_unicode_content(self, tmp_path: Path):
        dest = tmp_path / "output.md"
        content = "tëst 文件 🎉"
        _write_to_file(content, dest)
        assert dest.read_text(encoding="utf-8") == content


class TestDeliver:
    """Tests for the deliver() entry point."""

    def test_file_write_only(self, tmp_path: Path):
        dest = tmp_path / "out.md"
        result = deliver("content", dest, copy_to_clipboard=False)
        assert result.file_path == dest
        assert dest.read_text(encoding="utf-8") == "content"
        assert result.warnings == []

    def test_no_output_no_clipboard(self):
        result = deliver("content", None, copy_to_clipboard=False)
        assert result.file_path is None
        assert result.clipboard_success is False
        assert result.warnings == []

    def test_clipboard_unavailable_warning(self):
        with patch(
            "shaker.output.clipboard._copy_to_clipboard", return_value=False
        ):
            result = deliver("content", None, copy_to_clipboard=True)
            assert result.clipboard_success is False
            assert "Clipboard unavailable" in result.warnings

    def test_both_clipboard_and_file(self, tmp_path: Path):
        dest = tmp_path / "out.md"
        with patch(
            "shaker.output.clipboard._copy_to_clipboard", return_value=True
        ):
            result = deliver("content", dest, copy_to_clipboard=True)
            assert result.clipboard_success is True
            assert result.file_path == dest

    def test_file_write_error(self, tmp_path: Path):
        with patch(
            "shaker.output.clipboard._write_to_file",
            side_effect=OSError("permission denied"),
        ):
            dest = tmp_path / "out.md"
            result = deliver("content", dest, copy_to_clipboard=False)
            assert "File write failed" in result.warnings[0]
