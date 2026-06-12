"""Unit tests for new v1 data models.

Tests OutputFormat, SecurityFinding, FileScore, SecurityReport,
and updated Config/PipelineState.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from shaker.models import (
    Config,
    FileScore,
    OutputFormat,
    PipelineState,
    SecurityFinding,
    SecurityReport,
)


class TestOutputFormat:
    """Tests for the OutputFormat enum."""

    def test_values(self):
        assert OutputFormat.MARKDOWN.value == "markdown"
        assert OutputFormat.XML.value == "xml"
        assert OutputFormat.JSON.value == "json"
        assert OutputFormat.PLAIN.value == "plain"

    def test_all_formats_present(self):
        formats = {f.value for f in OutputFormat}
        assert formats == {"markdown", "xml", "json", "plain"}


class TestSecurityFinding:
    """Tests for SecurityFinding model."""

    def test_create(self):
        finding = SecurityFinding(
            file=Path("config.py"),
            line_number=42,
            finding_type="aws_key",
            severity="critical",
        )
        assert finding.file == Path("config.py")
        assert finding.line_number == 42
        assert finding.finding_type == "aws_key"
        assert finding.severity == "critical"
        assert finding.redacted is False

    def test_redacted_default(self):
        finding = SecurityFinding(
            file=Path("config.py"),
            line_number=1,
            finding_type="api_key",
            severity="warning",
            redacted=True,
        )
        assert finding.redacted is True

    def test_frozen(self):
        finding = SecurityFinding(
            file=Path("a.py"), line_number=1,
            finding_type="test", severity="info",
        )
        with pytest.raises(AttributeError):
            finding.severity = "critical"


class TestFileScore:
    """Tests for FileScore model."""

    def test_create(self):
        score = FileScore(
            file=Path("main.py"),
            score=0.95,
            importer_count=10,
            centrality=0.8,
        )
        assert score.file == Path("main.py")
        assert score.score == 0.95
        assert score.importer_count == 10
        assert score.centrality == 0.8
        assert score.git_changes_30d == 0
        assert score.is_focus is False

    def test_with_git_changes(self):
        score = FileScore(
            file=Path("main.py"),
            score=0.9,
            importer_count=5,
            centrality=0.7,
            git_changes_30d=12,
            is_focus=True,
        )
        assert score.git_changes_30d == 12
        assert score.is_focus is True


class TestSecurityReport:
    """Tests for SecurityReport model."""

    def test_defaults(self):
        report = SecurityReport()
        assert report.findings == []
        assert report.total_scanned == 0
        assert report.total_findings == 0
        assert report.critical_count == 0
        assert report.redacted_count == 0

    def test_with_findings(self):
        findings = [
            SecurityFinding(
                Path("a.py"), 1, "aws_key", "critical", redacted=True
            ),
            SecurityFinding(
                Path("b.py"), 5, "api_key", "warning"
            ),
        ]
        report = SecurityReport(
            findings=findings,
            total_scanned=10,
            total_findings=2,
            critical_count=1,
            redacted_count=1,
        )
        assert len(report.findings) == 2
        assert report.total_scanned == 10
        assert report.critical_count == 1


class TestConfigNewFields:
    """Tests for new Config fields."""

    def test_defaults(self):
        config = Config()
        assert config.output_format == OutputFormat.MARKDOWN
        assert config.security_scan is True
        assert config.security_redact is True
        assert config.show_progress is True
        assert config.quiet is False
        assert config.enforce_max_tokens is False
        assert config.use_git_scoring is True

    def test_custom_values(self):
        config = Config(
            output_format=OutputFormat.XML,
            security_scan=False,
            quiet=True,
        )
        assert config.output_format == OutputFormat.XML
        assert config.security_scan is False
        assert config.quiet is True


class TestPipelineStateNewFields:
    """Tests for new PipelineState fields."""

    def test_defaults(self):
        state = PipelineState(config=Config())
        assert state.security_report is None
        assert state.file_scores == {}

    def test_with_security_report(self):
        report = SecurityReport(total_scanned=5, total_findings=1)
        state = PipelineState(config=Config(), security_report=report)
        assert state.security_report.total_scanned == 5

    def test_with_file_scores(self):
        scores = {
            Path("main.py"): FileScore(
                Path("main.py"), 0.9, 10, 0.8
            ),
        }
        state = PipelineState(config=Config(), file_scores=scores)
        assert len(state.file_scores) == 1
        assert state.file_scores[Path("main.py")].score == 0.9
