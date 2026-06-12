"""Unit tests for the security scanner.

Tests secret detection, redaction, and SecurityReport generation.
"""

from __future__ import annotations

from pathlib import Path

from shaker.engine.security import (
    redact_findings,
    redact_report,
    scan_file,
    scan_files,
)
from shaker.models import SecurityFinding, SecurityReport


class TestScanFile:
    """Tests for scan_file."""

    def test_no_secrets(self):
        source = "x = 1\ny = 2\n"
        findings = scan_file(Path("test.py"), source)
        assert findings == []

    def test_aws_access_key(self):
        source = "access_key_id = 'AKIAIOSFODNN7EXAMPLE'\n"
        findings = scan_file(Path("config.py"), source)
        types = [f.finding_type for f in findings]
        assert "aws_access_key" in types
        aws_findings = [f for f in findings if f.finding_type == "aws_access_key"]
        assert len(aws_findings) == 1
        assert aws_findings[0].severity == "critical"
        assert aws_findings[0].line_number == 1

    def test_aws_secret_key(self):
        source = "aws_secret_access_key = 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'\n"
        findings = scan_file(Path("config.py"), source)
        types = {f.finding_type for f in findings}
        assert "aws_secret_key" in types
        assert "generic_api_key" not in types  # should not double-match

    def test_github_token_ghp(self):
        source = "token = 'ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijkl'\n"
        findings = scan_file(Path("deploy.py"), source)
        assert any(f.finding_type == "github_token" for f in findings)

    def test_github_token_pat(self):
        source = "token = 'github_pat_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijkl'\n"
        findings = scan_file(Path("deploy.py"), source)
        assert any(f.finding_type == "github_token" for f in findings)

    def test_private_key(self):
        source = "key = '''-----BEGIN RSA PRIVATE KEY-----\nMIIE...'''\n"
        findings = scan_file(Path("key.pem"), source)
        assert any(f.finding_type == "private_key" for f in findings)

    def test_private_key_ec(self):
        source = "-----BEGIN EC PRIVATE KEY-----\nMHQ...\n"
        findings = scan_file(Path("key.pem"), source)
        assert any(f.finding_type == "private_key" for f in findings)

    def test_private_key_openssh(self):
        source = "-----BEGIN OPENSSH PRIVATE KEY-----\nb3Bl...\n"
        findings = scan_file(Path("key"), source)
        assert any(f.finding_type == "private_key" for f in findings)

    def test_generic_api_key(self):
        source = "api_key = 'abcdefghijklmnopqrstuvwxyz123456'\n"
        findings = scan_file(Path("config.py"), source)
        assert any(f.finding_type == "generic_api_key" for f in findings)

    def test_env_secret(self):
        source = "SECRET_KEY = 'abcdefghijklmnopqrstuvwxyz123456'\n"
        findings = scan_file(Path(".env"), source)
        assert any(f.finding_type == "env_secret" for f in findings)

    def test_multiple_secrets_same_file(self):
        source = (
            "key = 'AKIAIOSFODNN7EXAMPLE'\n"
            "token = 'ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijkl'\n"
        )
        findings = scan_file(Path("config.py"), source)
        assert len(findings) >= 2

    def test_secrets_on_different_lines(self):
        source = (
            "x = 1\n"
            "key = 'AKIAIOSFODNN7EXAMPLE'\n"
            "y = 2\n"
            "SECRET = 'abcdefghijklmnopqrstuvwxyz123456'\n"
        )
        findings = scan_file(Path("config.py"), source)
        lines = {f.line_number for f in findings}
        assert 2 in lines
        assert 4 in lines

    def test_empty_source(self):
        findings = scan_file(Path("empty.py"), "")
        assert findings == []

    def test_finding_metadata(self):
        source = "access_key_id = 'AKIAIOSFODNN7EXAMPLE'\n"
        findings = scan_file(Path("src/config.py"), source)
        aws_findings = [f for f in findings if f.finding_type == "aws_access_key"]
        assert len(aws_findings) == 1
        f = aws_findings[0]
        assert f.file == Path("src/config.py")
        assert f.redacted is False


class TestScanFiles:
    """Tests for scan_files."""

    def test_no_files(self):
        report = scan_files({})
        assert report.total_scanned == 0
        assert report.total_findings == 0
        assert report.critical_count == 0

    def test_clean_files(self):
        sources = {
            Path("a.py"): "x = 1\n",
            Path("b.py"): "y = 2\n",
        }
        report = scan_files(sources)
        assert report.total_scanned == 2
        assert report.total_findings == 0

    def test_mixed_files(self):
        sources = {
            Path("clean.py"): "x = 1\n",
            Path("leaky.py"): "AKIAIOSFODNN7EXAMPLE\n",
        }
        report = scan_files(sources)
        assert report.total_scanned == 2
        assert report.total_findings == 1
        assert report.critical_count == 1

    def test_multiple_critical(self):
        sources = {
            Path("a.py"): "AKIAIOSFODNN7EXAMPLE\n",
            Path("b.py"): "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijkl\n",
        }
        report = scan_files(sources)
        assert report.critical_count == 2


class TestRedactFindings:
    """Tests for redact_findings."""

    def test_no_findings(self):
        source = "x = 1\ny = 2\n"
        result = redact_findings(source, [])
        assert result == source

    def test_redact_aws_access_key(self):
        source = "key = 'AKIAIOSFODNN7EXAMPLE'\n"
        findings = [
            SecurityFinding(
                file=Path("config.py"),
                line_number=1,
                finding_type="aws_access_key",
                severity="critical",
            )
        ]
        result = redact_findings(source, findings)
        assert "[REDACTED]" in result
        assert "AKIA" not in result

    def test_redact_private_key(self):
        source = "key = '''-----BEGIN RSA PRIVATE KEY-----\nMIIE...'''\n"
        findings = [
            SecurityFinding(
                file=Path("key.pem"),
                line_number=1,
                finding_type="private_key",
                severity="critical",
            )
        ]
        result = redact_findings(source, findings)
        assert "[REDACTED]" in result
        assert "RSA PRIVATE KEY" not in result

    def test_redact_preserves_other_lines(self):
        source = (
            "x = 1\n"
            "key = 'AKIAIOSFODNN7EXAMPLE'\n"
            "y = 2\n"
        )
        findings = [
            SecurityFinding(
                file=Path("config.py"),
                line_number=2,
                finding_type="aws_access_key",
                severity="critical",
            )
        ]
        result = redact_findings(source, findings)
        lines = result.splitlines()
        assert lines[0] == "x = 1"
        assert "[REDACTED]" in lines[1]
        assert lines[2] == "y = 2"

    def test_redact_out_of_range_line(self):
        source = "x = 1\n"
        findings = [
            SecurityFinding(
                file=Path("config.py"),
                line_number=99,
                finding_type="aws_access_key",
                severity="critical",
            )
        ]
        result = redact_findings(source, findings)
        assert result == source


class TestRedactReport:
    """Tests for redact_report."""

    def test_no_findings(self):
        sources = {Path("a.py"): "x = 1\n"}
        report = SecurityReport(total_scanned=1)
        result = redact_report(sources, report)
        assert result == sources
        assert report.redacted_count == 0

    def test_redacts_matching_files(self):
        sources = {
            Path("clean.py"): "x = 1\n",
            Path("leaky.py"): "key = 'AKIAIOSFODNN7EXAMPLE'\n",
        }
        findings = [
            SecurityFinding(
                file=Path("leaky.py"),
                line_number=1,
                finding_type="aws_access_key",
                severity="critical",
            )
        ]
        report = SecurityReport(
            findings=findings,
            total_scanned=2,
            total_findings=1,
            critical_count=1,
        )
        result = redact_report(sources, report)
        assert "AKIA" not in result[Path("leaky.py")]
        assert "[REDACTED]" in result[Path("leaky.py")]
        assert result[Path("clean.py")] == "x = 1\n"
        assert report.redacted_count == 1

    def test_counts_redacted(self):
        sources = {
            Path("leaky.py"): "AKIAIOSFODNN7EXAMPLE\n",
        }
        findings = [
            SecurityFinding(
                file=Path("leaky.py"),
                line_number=1,
                finding_type="aws_access_key",
                severity="critical",
            )
        ]
        report = SecurityReport(
            findings=findings,
            total_scanned=1,
            total_findings=1,
            critical_count=1,
        )
        redact_report(sources, report)
        assert report.redacted_count == 1
