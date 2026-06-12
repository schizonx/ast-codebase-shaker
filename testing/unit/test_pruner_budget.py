"""Unit tests for budget-aware pruning (enforce_max_tokens).

Tests the auto compression depth selection based on token budget ratio.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from shaker.engine.pruner import _resolve_effective_mode
from shaker.models import CompressionMode, ParsedFile


def _make_parsed(path: str, source: str) -> ParsedFile:
    return ParsedFile(
        path=Path(path),
        module_name=Path(path).stem,
        source=source,
    )


def _make_files(sources: dict[str, str]) -> dict[Path, ParsedFile]:
    return {Path(p): _make_parsed(p, s) for p, s in sources.items()}


class TestResolveEffectiveMode:
    """Tests for _resolve_effective_mode."""

    def test_no_enforce_preserves_mode(self):
        parsed = _make_files({"a.py": "x = 1\n" * 100})
        result = _resolve_effective_mode(
            parsed, set(), CompressionMode.SIGNATURES,
            max_tokens=10, enforce_max_tokens=False,
        )
        assert result == CompressionMode.SIGNATURES

    def test_no_max_tokens_preserves_mode(self):
        parsed = _make_files({"a.py": "x = 1\n" * 100})
        result = _resolve_effective_mode(
            parsed, set(), CompressionMode.SIGNATURES,
            max_tokens=None, enforce_max_tokens=True,
        )
        assert result == CompressionMode.SIGNATURES

    def test_low_ratio_preserves_user_mode(self):
        parsed = _make_files({"a.py": "x = 1\n" * 100})
        with patch("shaker.engine.pruner.count_tokens", return_value=100):
            result = _resolve_effective_mode(
                parsed, set(), CompressionMode.FULL,
                max_tokens=200, enforce_max_tokens=True,
            )
        # ratio = 100/200 = 0.5 < 1.5, preserves user mode
        assert result == CompressionMode.FULL

    def test_medium_ratio_uses_signatures(self):
        parsed = _make_files({"a.py": "x = 1\n" * 100})
        with patch("shaker.engine.pruner.count_tokens", return_value=100):
            result = _resolve_effective_mode(
                parsed, set(), CompressionMode.FULL,
                max_tokens=60, enforce_max_tokens=True,
            )
        # ratio = 100/60 ≈ 1.67 > 1.5, uses signatures
        assert result == CompressionMode.SIGNATURES

    def test_high_ratio_uses_strip(self):
        parsed = _make_files({"a.py": "x = 1\n" * 100})
        with patch("shaker.engine.pruner.count_tokens", return_value=100):
            result = _resolve_effective_mode(
                parsed, set(), CompressionMode.FULL,
                max_tokens=40, enforce_max_tokens=True,
            )
        # ratio = 100/40 = 2.5 > 2.0, uses strip
        assert result == CompressionMode.STRIP

    def test_zero_tokens_preserves_mode(self):
        parsed = _make_files({"a.py": ""})
        with patch("shaker.engine.pruner.count_tokens", return_value=0):
            result = _resolve_effective_mode(
                parsed, set(), CompressionMode.FULL,
                max_tokens=100, enforce_max_tokens=True,
            )
        assert result == CompressionMode.FULL

    def test_empty_parsed_preserves_mode(self):
        parsed = _make_files({"a.py": ""})
        with patch("shaker.engine.pruner.count_tokens", return_value=0):
            result = _resolve_effective_mode(
                parsed, set(), CompressionMode.SIGNATURES,
                max_tokens=100, enforce_max_tokens=True,
            )
        assert result == CompressionMode.SIGNATURES
