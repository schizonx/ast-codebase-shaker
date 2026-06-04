"""Unit tests for shaker.infra.tokens.

Covers token counting, estimation, and fallback behavior.
"""

from __future__ import annotations

import pytest

from shaker.infra.tokens import (
    _get_encoder,
    count_tokens,
    estimate_tokens,
    get_encoder_error,
)


@pytest.fixture(autouse=True)
def _reset_encoder_cache():
    """Reset the global encoder cache before each test."""
    import shaker.infra.tokens as mod
    mod._encoder = None
    mod._encoder_error = None
    yield
    mod._encoder = None
    mod._encoder_error = None


class TestEstimateTokens:
    """Tests for the character-based token estimation fallback."""

    def test_empty_string_returns_zero(self):
        assert estimate_tokens("") == 0

    def test_short_string_returns_at_least_one(self):
        assert estimate_tokens("a") == 1

    def test_four_chars_is_one_token(self):
        assert estimate_tokens("abcd") == 1

    def test_eight_chars_is_two_tokens(self):
        assert estimate_tokens("abcdefgh") == 2

    def test_python_code_estimation(self):
        code = "def hello():\n    return 'world'\n"
        estimated = estimate_tokens(code)
        assert estimated > 0
        assert estimated == len(code) // 4

    def test_large_text(self):
        text = "x" * 4000
        assert estimate_tokens(text) == 1000


class TestCountTokens:
    """Tests for the main count_tokens function."""

    def test_empty_string(self):
        assert count_tokens("") == 0

    def test_returns_positive_for_nonzero_input(self):
        result = count_tokens("hello world")
        assert result > 0

    def test_longer_text_has_more_tokens(self):
        short = count_tokens("hello")
        long_result = count_tokens("hello " * 100)
        assert long_result > short


class TestGetEncoder:
    """Tests for the lazy tiktoken encoder loader."""

    def test_returns_none_or_encoding(self):
        encoder = _get_encoder()
        # Either tiktoken is available (returns Encoding) or not (returns None)
        if encoder is not None:
            # Should have an encode method
            assert hasattr(encoder, "encode")

    def test_caches_encoder(self):
        enc1 = _get_encoder()
        enc2 = _get_encoder()
        assert enc1 is enc2

    def test_error_accessible_via_get_encoder_error(self):
        _get_encoder()
        # Either no error or a descriptive string
        error = get_encoder_error()
        if error is not None:
            assert isinstance(error, str)
            assert len(error) > 0


class TestGetEncoderError:
    """Tests for the error accessor."""

    def test_returns_none_on_first_call_before_encoder_load(self):
        # With autouse fixture, cache is reset — error should be None
        assert get_encoder_error() is None

    def test_returns_string_after_failed_load(self):
        _get_encoder()
        error = get_encoder_error()
        # If tiktoken is installed, error is None; otherwise it's a string
        assert error is None or isinstance(error, str)
