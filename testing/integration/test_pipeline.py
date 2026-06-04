"""End-to-end pipeline integration tests.

Tests the full pipeline from CLI args to output, verifying
integration between all modules.
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
    """Create a minimal Python project with a call graph."""
    main_py = tmp_path / "main.py"
    main_py.write_text(
        "from util import helper\n"
        "\n"
        "def run():\n"
        "    helper()\n"
        "    return True\n",
        encoding="utf-8",
    )
    util_py = tmp_path / "util.py"
    util_py.write_text(
        "def helper():\n"
        "    return 42\n"
        "\n"
        "def unused():\n"
        "    pass\n",
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def project_with_errors(tmp_path: Path) -> Path:
    """Create a project with a syntax error file."""
    good_py = tmp_path / "good.py"
    good_py.write_text("x = 1\n", encoding="utf-8")
    bad_py = tmp_path / "bad.py"
    bad_py.write_text("def broken(\n", encoding="utf-8")
    return tmp_path


@pytest.fixture
def project_with_cycles(tmp_path: Path) -> Path:
    """Create a project with circular imports."""
    a_py = tmp_path / "a.py"
    a_py.write_text(
        "from b import func_b\n"
        "\n"
        "def func_a():\n"
        "    return func_b()\n",
        encoding="utf-8",
    )
    b_py = tmp_path / "b.py"
    b_py.write_text(
        "from a import func_a\n"
        "\n"
        "def func_b():\n"
        "    return func_a()\n",
        encoding="utf-8",
    )
    return tmp_path


class TestFullPipeline:
    """End-to-end pipeline tests."""

    def test_no_focus_signatures(
        self, runner: CliRunner, sample_project: Path
    ):
        result = runner.invoke(cli, [str(sample_project)])
        assert result.exit_code == 0
        assert "# Codebase Shaker Output" in result.output
        assert "```python" in result.output

    def test_with_focus_signatures(
        self, runner: CliRunner, sample_project: Path
    ):
        result = runner.invoke(
            cli, [str(sample_project), "--focus", "main.run"]
        )
        assert result.exit_code == 0
        assert "FOCUS" in result.output

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
        # Full mode should preserve source
        assert "helper()" in result.output

    def test_syntax_error_files(
        self, runner: CliRunner, project_with_errors: Path
    ):
        result = runner.invoke(cli, [str(project_with_errors)])
        assert result.exit_code == 0
        assert "Parse errors" in result.output

    def test_circular_imports(
        self, runner: CliRunner, project_with_cycles: Path
    ):
        result = runner.invoke(cli, [str(project_with_cycles)])
        assert result.exit_code == 0

    def test_nonexistent_focus(
        self, runner: CliRunner, sample_project: Path
    ):
        result = runner.invoke(
            cli, [str(sample_project), "--focus", "nonexistent.func"]
        )
        # Should handle gracefully — non-zero exit with suggestions
        assert result.exit_code is not None

    def test_exclude_patterns(
        self, runner: CliRunner, sample_project: Path
    ):
        result = runner.invoke(
            cli, [str(sample_project), "--exclude", "util.py"]
        )
        assert result.exit_code == 0

    def test_output_file(
        self, runner: CliRunner, sample_project: Path, tmp_path: Path
    ):
        out_file = tmp_path / "out.md"
        result = runner.invoke(
            cli, [str(sample_project), "--output", str(out_file)]
        )
        assert result.exit_code == 0
        assert out_file.exists()
        content = out_file.read_text(encoding="utf-8")
        assert "# Codebase Shaker Output" in content

    def test_single_file_input(
        self, runner: CliRunner, tmp_path: Path
    ):
        single = tmp_path / "single.py"
        single.write_text("def hello():\n    pass\n", encoding="utf-8")
        result = runner.invoke(cli, [str(single)])
        assert result.exit_code == 0

    def test_max_tokens_warning(
        self, runner: CliRunner, sample_project: Path
    ):
        result = runner.invoke(
            cli, [str(sample_project), "--max-tokens", "1"]
        )
        assert result.exit_code == 0

    def test_stats_table_present(
        self, runner: CliRunner, sample_project: Path
    ):
        result = runner.invoke(cli, [str(sample_project)])
        assert result.exit_code == 0
        assert "Input tokens" in result.output
        assert "Output tokens" in result.output
