"""Unit tests for remote repository support.

Tests clone_remote, cleanup_remote, and signal handling.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from shaker.engine.remote import cleanup_remote, clone_remote


class TestCloneRemote:
    """Tests for clone_remote."""

    def test_successful_clone(self, tmp_path):
        with patch("shaker.engine.remote.tempfile.mkdtemp", return_value=str(tmp_path)):
            with patch("shaker.engine.remote.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                result = clone_remote("https://github.com/user/repo.git")
                assert result == tmp_path
                mock_run.assert_called_once_with(
                    ["git", "clone", "--depth=1", "https://github.com/user/repo.git", str(tmp_path)],
                    check=True,
                    capture_output=True,
                    text=True,
                )

    def test_git_not_installed(self, tmp_path):
        with patch("shaker.engine.remote.tempfile.mkdtemp", return_value=str(tmp_path)):
            with patch("shaker.engine.remote.subprocess.run", side_effect=FileNotFoundError):
                with patch("shaker.engine.remote.shutil.rmtree") as mock_rmtree:
                    with pytest.raises(FileNotFoundError, match="git is not installed"):
                        clone_remote("https://github.com/user/repo.git")
                    mock_rmtree.assert_called_once()

    def test_clone_failure(self, tmp_path):
        with patch("shaker.engine.remote.tempfile.mkdtemp", return_value=str(tmp_path)):
            with patch(
                "shaker.engine.remote.subprocess.run",
                side_effect=subprocess.CalledProcessError(1, "git", stderr="fatal: repo not found"),
            ):
                with patch("shaker.engine.remote.shutil.rmtree") as mock_rmtree:
                    with pytest.raises(subprocess.CalledProcessError):
                        clone_remote("https://github.com/user/nonexistent.git")
                    mock_rmtree.assert_called_once()


class TestCleanupRemote:
    """Tests for cleanup_remote."""

    def test_cleanup_existing_dir(self, tmp_path):
        tmp_path.mkdir(exist_ok=True)
        (tmp_path / "test.txt").write_text("test")
        cleanup_remote(tmp_path)
        assert not tmp_path.exists()

    def test_cleanup_nonexistent_dir(self):
        cleanup_remote(Path("/nonexistent/path/shaker-test"))

    def test_cleanup_idempotent(self, tmp_path):
        tmp_path.mkdir(exist_ok=True)
        cleanup_remote(tmp_path)
        cleanup_remote(tmp_path)  # Should not raise
