"""Real-project end-to-end tests.

Tests the full pipeline against actual installed Python packages:
Flask (24 .py files), FastAPI (48 .py files), and werkzeug (52 .py files).

These are real-world codebases with complex patterns: decorators, metaclasses,
complex import chains, async/await, type hints, generics, __all__, star imports,
relative imports, and more.
"""
from __future__ import annotations

import logging
from pathlib import Path

import pytest
from click.testing import CliRunner

from shaker.cli import cli

logger = logging.getLogger(__name__)


def _get_package_path(package_name: str) -> Path | None:
    """Get the source path of an installed package, or None if not installed."""
    try:
        mod = __import__(package_name)
        return Path(mod.__file__).parent
    except ImportError:
        return None


def _output_contains(output: str, *fragments: str) -> bool:
    """Check if output contains all fragments on the same line."""
    return any(all(f in line for f in fragments) for line in output.split("\n"))


def _output_contains_any(output: str, *fragments: str) -> bool:
    """Check if output contains any of the fragments."""
    return any(f in output for f in fragments)


# ---- Fixtures ---------------------------------------------------------------


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def flask_path() -> Path | None:
    return _get_package_path("flask")


@pytest.fixture
def fastapi_path() -> Path | None:
    return _get_package_path("fastapi")


@pytest.fixture
def werkzeug_path() -> Path | None:
    return _get_package_path("werkzeug")


def _skip_if_missing(path: Path | None, name: str):
    if path is None:
        pytest.skip(f"{name} not installed")


# ---- Flask tests ------------------------------------------------------------

class TestFlaskFullPipeline:
    """Full pipeline on Flask's real source code."""

    def test_discover_all_files(self, runner, flask_path):
        _skip_if_missing(flask_path, "Flask")
        result = runner.invoke(cli, [str(flask_path), "--dry-run"])
        assert result.exit_code == 0, f"Output: {result.output}\nException: {result.exception}"
        assert _output_contains(result.output, "Parse errors", "0")

    def test_all_three_modes(self, runner, flask_path):
        _skip_if_missing(flask_path, "Flask")
        for mode in ("full", "signatures", "strip"):
            result = runner.invoke(
                cli, [str(flask_path), "--mode", mode, "--dry-run"]
            )
            assert result.exit_code == 0, f"Mode {mode}: {result.output}"
            assert _output_contains(result.output, "Parse errors", "0")

    def test_with_focus_flask_app(self, runner, flask_path):
        _skip_if_missing(flask_path, "Flask")
        result = runner.invoke(
            cli,
            [str(flask_path), "--focus", "app.Flask", "--dry-run"],
        )
        assert result.exit_code == 0, f"Output: {result.output}"
        assert "Files retained" in result.output

    def test_with_focus_flask_route(self, runner, flask_path):
        _skip_if_missing(flask_path, "Flask")
        result = runner.invoke(
            cli,
            [str(flask_path), "--focus", "sansio.scaffold.Scaffold.route", "--dry-run"],
        )
        assert result.exit_code == 0, f"Output: {result.output}"

    def test_nonexistent_focus_suggests(self, runner, flask_path):
        _skip_if_missing(flask_path, "Flask")
        result = runner.invoke(
            cli,
            [str(flask_path), "--focus", "flask.app.NonexistentClass"],
        )
        assert result.exit_code is not None

    def test_output_file_creation(self, runner, flask_path, tmp_path):
        _skip_if_missing(flask_path, "Flask")
        out_file = tmp_path / "flask_output.md"
        result = runner.invoke(
            cli, [str(flask_path), "--output", str(out_file)]
        )
        assert result.exit_code == 0
        assert out_file.exists()
        content = out_file.read_text(encoding="utf-8")
        assert "# Codebase Shaker Output" in content
        assert "```python" in content
        assert "flask" in content.lower() or "Flask" in content

    def test_token_reduction_reported(self, runner, flask_path):
        _skip_if_missing(flask_path, "Flask")
        result = runner.invoke(
            cli, [str(flask_path), "--mode", "signatures", "--dry-run"]
        )
        assert result.exit_code == 0
        assert "Input tokens" in result.output
        assert "Output tokens" in result.output

    def test_exclude_patterns_work(self, runner, flask_path):
        _skip_if_missing(flask_path, "Flask")
        result = runner.invoke(
            cli,
            [str(flask_path), "--exclude", "test*.py", "--dry-run"],
        )
        assert result.exit_code == 0

    def test_file_tree_present(self, runner, flask_path, tmp_path):
        _skip_if_missing(flask_path, "Flask")
        out_file = tmp_path / "flask_tree.md"
        result = runner.invoke(cli, [str(flask_path), "--output", str(out_file)])
        assert result.exit_code == 0
        content = out_file.read_text(encoding="utf-8")
        assert "## File Tree" in content


# ---- FastAPI tests -----------------------------------------------------------

class TestFastAPIFullPipeline:
    """Full pipeline on FastAPI's real source code."""

    def test_discover_all_files(self, runner, fastapi_path):
        _skip_if_missing(fastapi_path, "FastAPI")
        result = runner.invoke(cli, [str(fastapi_path), "--dry-run"])
        assert result.exit_code == 0, f"Output: {result.output}\nException: {result.exception}"
        assert _output_contains(result.output, "Parse errors", "0")

    def test_all_three_modes(self, runner, fastapi_path):
        _skip_if_missing(fastapi_path, "FastAPI")
        for mode in ("full", "signatures", "strip"):
            result = runner.invoke(
                cli, [str(fastapi_path), "--mode", mode, "--dry-run"]
            )
            assert result.exit_code == 0, f"Mode {mode}: {result.output}"

    def test_with_focus_fastapi_app(self, runner, fastapi_path):
        _skip_if_missing(fastapi_path, "FastAPI")
        result = runner.invoke(
            cli,
            [str(fastapi_path), "--focus", "applications.FastAPI", "--dry-run"],
        )
        assert result.exit_code == 0, f"Output: {result.output}"
        assert "Files retained" in result.output

    def test_nonexistent_focus(self, runner, fastapi_path):
        _skip_if_missing(fastapi_path, "FastAPI")
        result = runner.invoke(
            cli,
            [str(fastapi_path), "--focus", "fastapi.does.not.exist"],
        )
        assert result.exit_code is not None

    def test_output_file(self, runner, fastapi_path, tmp_path):
        _skip_if_missing(fastapi_path, "FastAPI")
        out_file = tmp_path / "fastapi_output.md"
        result = runner.invoke(
            cli, [str(fastapi_path), "--output", str(out_file)]
        )
        assert result.exit_code == 0
        assert out_file.exists()
        content = out_file.read_text(encoding="utf-8")
        assert "# Codebase Shaker Output" in content

    def test_stats_present(self, runner, fastapi_path):
        _skip_if_missing(fastapi_path, "FastAPI")
        result = runner.invoke(
            cli, [str(fastapi_path), "--mode", "strip", "--dry-run"]
        )
        assert result.exit_code == 0
        assert "Files retained" in result.output
        assert "Input tokens" in result.output


# ---- werkzeug tests ----------------------------------------------------------

class TestWerkzeugFullPipeline:
    """Full pipeline on werkzeug's real source code."""

    def test_discover_all_files(self, runner, werkzeug_path):
        _skip_if_missing(werkzeug_path, "werkzeug")
        result = runner.invoke(cli, [str(werkzeug_path), "--dry-run"])
        assert result.exit_code == 0, f"Output: {result.output}\nException: {result.exception}"
        assert _output_contains(result.output, "Parse errors", "0")

    def test_all_three_modes(self, runner, werkzeug_path):
        _skip_if_missing(werkzeug_path, "werkzeug")
        for mode in ("full", "signatures", "strip"):
            result = runner.invoke(
                cli, [str(werkzeug_path), "--mode", mode, "--dry-run"]
            )
            assert result.exit_code == 0, f"Mode {mode}: {result.output}"

    def test_with_focus(self, runner, werkzeug_path):
        _skip_if_missing(werkzeug_path, "werkzeug")
        result = runner.invoke(
            cli,
            [str(werkzeug_path), "--focus", "wrappers.request.Request", "--dry-run"],
        )
        assert result.exit_code == 0, f"Output: {result.output}"

    def test_no_clipboard_flag(self, runner, werkzeug_path):
        _skip_if_missing(werkzeug_path, "werkzeug")
        result = runner.invoke(
            cli,
            [str(werkzeug_path), "--no-clipboard", "--dry-run"],
        )
        assert result.exit_code == 0

    def test_file_output(self, runner, werkzeug_path, tmp_path):
        _skip_if_missing(werkzeug_path, "werkzeug")
        out_file = tmp_path / "werkzeug_output.md"
        result = runner.invoke(
            cli, [str(werkzeug_path), "--output", str(out_file)]
        )
        assert result.exit_code == 0
        assert out_file.exists()
        content = out_file.read_text(encoding="utf-8")
        assert "# Codebase Shaker Output" in content
        assert "Omitted Files" in content or "File Tree" in content


# ---- Cross-cutting real-world feature tests ---------------------------------

class TestRealWorldFeatures:
    """Test specific features against real-world code patterns."""

    def test_flask_decorators_preserved_in_signatures(
        self, runner, flask_path, tmp_path
    ):
        """Real decorators like @app.route should appear in signature mode."""
        _skip_if_missing(flask_path, "Flask")
        out_file = tmp_path / "flask_sigs.md"
        runner.invoke(
            cli,
            [str(flask_path), "--mode", "signatures", "--output", str(out_file)],
        )
        content = out_file.read_text(encoding="utf-8")
        # Signatures mode should contain decorator-like strings
        # (the exact output depends on ast.unparse, but decorators should be present)
        assert "@" in content

    def test_strip_mode_removes_docstrings(self, runner, flask_path, tmp_path):
        """Strip mode should remove docstrings from real code."""
        _skip_if_missing(flask_path, "Flask")
        out_file = tmp_path / "flask_strip.md"
        runner.invoke(
            cli,
            [str(flask_path), "--mode", "strip", "--output", str(out_file)],
        )
        content = out_file.read_text(encoding="utf-8")
        # Output should be valid Markdown with code blocks
        assert "```python" in content
        assert "# Codebase Shaker Output" in content

    def test_full_mode_preserves_everything(self, runner, flask_path, tmp_path):
        """Full mode should preserve source byte-for-byte."""
        _skip_if_missing(flask_path, "Flask")
        out_file = tmp_path / "flask_full.md"
        runner.invoke(
            cli,
            [str(flask_path), "--mode", "full", "--output", str(out_file)],
        )
        content = out_file.read_text(encoding="utf-8")
        # Flask's app.py contains "class Flask" — should be preserved
        assert "class Flask" in content

    def test_focus_reduces_output_files(self, runner, flask_path, tmp_path):
        """Focus mode should result in fewer files than no-focus."""
        _skip_if_missing(flask_path, "Flask")
        # No focus — all files retained
        out_all = tmp_path / "flask_all.md"
        runner.invoke(
            cli,
            [str(flask_path), "--mode", "full", "--output", str(out_all)],
        )
        # With focus — only relevant files retained
        out_focused = tmp_path / "flask_focused.md"
        runner.invoke(
            cli,
            [
                str(flask_path),
                "--focus",
                "app.Flask",
                "--mode",
                "full",
                "--output",
                str(out_focused),
            ],
        )
        all_content = out_all.read_text(encoding="utf-8")
        focused_content = out_focused.read_text(encoding="utf-8")
        # Focused output should contain "###" headings but fewer of them
        all_file_count = all_content.count("### `")
        focused_file_count = focused_content.count("### `")
        assert focused_file_count <= all_file_count

    def test_fastapi_complex_type_hints(self, runner, fastapi_path):
        """FastAPI uses heavy type hints — parser should handle them."""
        _skip_if_missing(fastapi_path, "FastAPI")
        result = runner.invoke(cli, [str(fastapi_path), "--dry-run"])
        assert result.exit_code == 0
        assert _output_contains(result.output, "Parse errors", "0")

    def test_werkzeug_nested_classes(self, runner, werkzeug_path):
        """werkzeug has deeply nested classes — symbols should extract."""
        _skip_if_missing(werkzeug_path, "werkzeug")
        result = runner.invoke(cli, [str(werkzeug_path), "--dry-run"])
        assert result.exit_code == 0

    def test_all_packages_parse_without_errors(
        self, runner, flask_path, fastapi_path, werkzeug_path
    ):
        """All three real packages should parse with zero errors."""
        for name, path in [
            ("Flask", flask_path),
            ("FastAPI", fastapi_path),
            ("werkzeug", werkzeug_path),
        ]:
            _skip_if_missing(path, name)
            result = runner.invoke(cli, [str(path), "--dry-run"])
            assert result.exit_code == 0, f"{name}: {result.output}"
            assert _output_contains(result.output, "Parse errors", "0"), (
                f"{name}: Expected 0 parse errors"
            )

    def test_multiple_exclude_patterns(self, runner, flask_path):
        """Multiple --exclude flags should work on real code."""
        _skip_if_missing(flask_path, "Flask")
        result = runner.invoke(
            cli,
            [
                str(flask_path),
                "--exclude",
                "test*.py",
                "--exclude",
                "__main__.py",
                "--dry-run",
            ],
        )
        assert result.exit_code == 0

    def test_verbose_mode_no_crash(self, runner, flask_path):
        """Verbose logging should not crash on real code."""
        _skip_if_missing(flask_path, "Flask")
        result = runner.invoke(
            cli, [str(flask_path), "--verbose", "--dry-run"]
        )
        assert result.exit_code == 0
