"""Security scanning — secret detection and redaction.

Scans source code for patterns that look like secrets (API keys,
tokens, private keys) and either redacts them or warns about them.

The scanner is regex-based with zero additional dependencies.
All patterns are defined in constants.py so they are configurable.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from shaker.constants import SECRET_PATTERNS
from shaker.models import SecurityFinding, SecurityReport

logger = logging.getLogger(__name__)

_SEVERITY_MAP: dict[str, str] = {
    "aws_access_key": "critical",
    "aws_secret_key": "critical",
    "github_token": "critical",
    "private_key": "critical",
    "generic_api_key": "warning",
    "env_secret": "warning",
}

_REDACKET_TARGETS = frozenset({"aws_secret_key", "generic_api_key", "env_secret"})
"""Finding types where the specific value (after = or :) is redacted."""


def scan_file(path: Path, source: str) -> list[SecurityFinding]:
    """Scan a single file's source for secret patterns.

    Args:
        path: File path (for finding metadata).
        source: The full source text to scan.

    Returns:
        List of SecurityFinding objects for detected secrets.
        Empty list if no secrets found or scanning is disabled.
    """
    findings: list[SecurityFinding] = []
    for pattern_name, pattern in SECRET_PATTERNS.items():
        try:
            compiled = re.compile(pattern)
        except re.error:
            logger.warning(
                "Invalid regex pattern '%s': %s", pattern_name, pattern
            )
            continue

        for line_num, line in enumerate(source.splitlines(), start=1):
            if compiled.search(line):
                severity = _SEVERITY_MAP.get(pattern_name, "warning")
                findings.append(
                    SecurityFinding(
                        file=path,
                        line_number=line_num,
                        finding_type=pattern_name,
                        severity=severity,
                    )
                )
    return findings


def scan_files(
    sources: dict[Path, str],
) -> SecurityReport:
    """Scan multiple files for secret patterns.

    Args:
        sources: Mapping of file paths to source text.

    Returns:
        SecurityReport with all findings aggregated.
    """
    all_findings: list[SecurityFinding] = []
    for fpath, source in sources.items():
        findings = scan_file(fpath, source)
        all_findings.extend(findings)

    critical = sum(1 for f in all_findings if f.severity == "critical")
    return SecurityReport(
        findings=all_findings,
        total_scanned=len(sources),
        total_findings=len(all_findings),
        critical_count=critical,
    )


def redact_findings(source: str, findings: list[SecurityFinding]) -> str:
    """Redact secrets found in source text.

    For line-level patterns (aws_access_key, private_key),
    the entire matching section is replaced with [REDACTED].
    For value-patterns (aws_secret_key, generic_api_key, env_secret),
    only the value portion after the delimiter is replaced.

    Args:
        source: Original source text.
        findings: Findings for this file (all must have the same file).

    Returns:
        Source text with secrets replaced by [REDACTED].
    """
    if not findings:
        return source

    trailing_newline = source.endswith("\n")
    lines = source.splitlines()
    redacted_indices: set[int] = set()

    for finding in findings:
        idx = finding.line_number - 1
        if idx < 0 or idx >= len(lines):
            continue

        finding_type = finding.finding_type

        if finding_type == "private_key":
            lines[idx] = "-----BEGIN [REDACTED] PRIVATE KEY-----"
            redacted_indices.add(idx)
            continue

        if finding_type == "aws_access_key":
            lines[idx] = re.sub(
                SECRET_PATTERNS["aws_access_key"],
                "[REDACTED]",
                lines[idx],
            )
            redacted_indices.add(idx)
            continue

        if finding_type in _REDACKET_TARGETS:
            pattern = SECRET_PATTERNS.get(finding_type)
            if pattern and finding_type not in (
                "aws_access_key", "private_key"
            ):
                try:
                    lines[idx] = re.sub(
                        pattern,
                        _replacement_for(finding_type),
                        lines[idx],
                    )
                    redacted_indices.add(idx)
                except re.error:
                    logger.warning(
                        "Failed to redact pattern '%s'", finding_type
                    )

    result = "\n".join(lines)
    if trailing_newline:
        result += "\n"
    return result


def redact_report(
    sources: dict[Path, str],
    report: SecurityReport,
) -> dict[Path, str]:
    """Redact all findings from source texts.

    Group findings by file, then apply redaction to each file.

    Args:
        sources: Mapping of file paths to source text.
        report: SecurityReport with findings.

    Returns:
        New mapping of file paths to redacted source text.
        Files with no findings are included unchanged.
    """
    from collections import defaultdict

    by_file: dict[Path, list[SecurityFinding]] = defaultdict(list)
    for finding in report.findings:
        by_file[finding.file].append(finding)

    result: dict[Path, str] = {}
    redacted_count = 0
    for fpath, source in sources.items():
        if fpath in by_file:
            file_findings = by_file[fpath]
            redacted_source = redact_findings(source, file_findings)
            result[fpath] = redacted_source
            redacted_count += len(file_findings)
        else:
            result[fpath] = source

    report.redacted_count = redacted_count
    return result


def _replacement_for(finding_type: str) -> str:
    """Return the regex replacement string for a finding type.

    Replaces the value portion (after = or :) with [REDACTED].

    Args:
        finding_type: The type of secret finding.

    Returns:
        Replacement string.
    """
    if finding_type == "aws_secret_key":
        return r"aws_secret_access_key=[REDACTED]"
    if finding_type == "generic_api_key":
        return r"\1=[REDACTED]"
    if finding_type == "env_secret":
        return r"\1=[REDACTED]"
    return "[REDACTED]"
