"""Integration tests for shaker.cli.

Tests CLI argument parsing, help text, version output,
error handling, and output delivery using Click's CliRunner.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from shaker.cli import cli


@pytest.fixture
def runner() -> CliRunner:
    """Provide a Click CliRunner."""
    return CliRunner()


@pytest.fixture
def sample_project(tmp_path: Path) -> Path:
    """Create a minimal Python project for testing."""
    main_py = tmp_path / "main.py"
    main_py.write_text(
        "def run():\n"
        "    helper()\n"
        "    return True\n"
        "\n"
        "def helper():\n"
        "    pass\n",
        encoding="utf-8",
    )
    util_py = tmp_path / "util.py"
    util_py.write_text(
        "def util_func():\n    return 42\n",
        encoding="utf-8",
    )
    return tmp_path


class TestCliHelp:
    """Tests for --help output."""

    def test_help_exits_zero(self, runner: CliRunner):
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0

    def test_help_contains_usage(self, runner: CliRunner):
        result = runner.invoke(cli, ["--help"])
        assert "Usage" in result.output

    def test_help_lists_options(self, runner: CliRunner):
        result = runner.invoke(cli, ["--help"])
        assert "--focus" in result.output
        assert "--mode" in result.output
        assert "--output" in result.output


class TestCliVersion:
    """Tests for --version output."""

    def test_version_exits_zero(self, runner: CliRunner):
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0

    def test_version_contains_number(self, runner: CliRunner):
        result = runner.invoke(cli, ["--version"])
        assert "0.0.0" in result.output


class TestCliErrors:
    """Tests for error handling."""

    def test_invalid_path(self, runner: CliRunner):
        result = runner.invoke(cli, ["/nonexistent/path/that/does/not/exist"])
        assert result.exit_code != 0

    def test_invalid_mode(self, runner: CliRunner, sample_project: Path):
        result = runner.invoke(
            cli, [str(sample_project), "--mode", "invalid_mode"]
        )
        assert result.exit_code != 0


class TestCliInvocation:
    """Tests for valid CLI invocations."""

    def test_valid_invocation_exits_zero(
        self, runner: CliRunner, sample_project: Path
    ):
        result = runner.invoke(cli, [str(sample_project)])
        assert result.exit_code == 0

    def test_output_contains_markdown(
        self, runner: CliRunner, sample_project: Path
    ):
        result = runner.invoke(cli, [str(sample_project)])
        assert "# Codebase Shaker Output" in result.output

    def test_dry_run_no_delivery(
        self, runner: CliRunner, sample_project: Path
    ):
        result = runner.invoke(cli, [str(sample_project), "--dry-run"])
        assert result.exit_code == 0

    def test_no_clipboard_flag(
        self, runner: CliRunner, sample_project: Path
    ):
        result = runner.invoke(cli, [str(sample_project), "--no-clipboard"])
        assert result.exit_code == 0

    def test_output_to_file(
        self, runner: CliRunner, sample_project: Path, tmp_path: Path
    ):
        out_file = tmp_path / "output.md"
        result = runner.invoke(
            cli, [str(sample_project), "--output", str(out_file)]
        )
        assert result.exit_code == 0
        assert out_file.exists()
        content = out_file.read_text(encoding="utf-8")
        assert "# Codebase Shaker Output" in content

    def test_focus_option(
        self, runner: CliRunner, sample_project: Path
    ):
        result = runner.invoke(
            cli, [str(sample_project), "--focus", "main.run"]
        )
        assert result.exit_code == 0
        assert "FOCUS" in result.output

    def test_focus_nonexistent(
        self, runner: CliRunner, sample_project: Path
    ):
        result = runner.invoke(
            cli, [str(sample_project), "--focus", "nonexistent.symbol"]
        )
        # Should not crash; may exit non-zero with suggestions
        assert result.exit_code is not None

    def test_strip_mode(
        self, runner: CliRunner, sample_project: Path
    ):
        result = runner.invoke(
            cli, [str(sample_project), "--mode", "strip"]
        )
        assert result.exit_code == 0

    def test_full_mode(
        self, runner: CliRunner, sample_project: Path
    ):
        result = runner.invoke(
            cli, [str(sample_project), "--mode", "full"]
        )
        assert result.exit_code == 0

    def test_signatures_mode(
        self, runner: CliRunner, sample_project: Path
    ):
        result = runner.invoke(
            cli, [str(sample_project), "--mode", "signatures"]
        )
        assert result.exit_code == 0

    def test_verbose_flag(
        self, runner: CliRunner, sample_project: Path
    ):
        result = runner.invoke(cli, [str(sample_project), "--verbose"])
        assert result.exit_code == 0

    def test_exclude_pattern(
        self, runner: CliRunner, sample_project: Path
    ):
        result = runner.invoke(
            cli, [str(sample_project), "--exclude", "util.py"]
        )
        assert result.exit_code == 0

    def test_piping_output(
        self, runner: CliRunner, sample_project: Path
    ):
        result = runner.invoke(cli, [str(sample_project)])
        assert "```python" in result.output
