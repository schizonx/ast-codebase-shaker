"""Token counting for Codebase Shaker.

Uses tiktoken if available, otherwise falls back to chars // 4 estimation.
The encoder is lazily loaded on first use and cached for subsequent calls.
"""

from __future__ import annotations

from typing import Any

from shaker.constants import CHARS_PER_TOKEN_FALLBACK, TIKTOKEN_DEFAULT_ENCODING

_encoder: Any | None = None
_encoder_error: str | None = None


def count_tokens(text: str) -> int:
    """Count tokens in *text* using the best available method.

    Uses tiktoken if installed, otherwise falls back to
    :func:`estimate_tokens`.

    Args:
        text: The text to count tokens for.

    Returns:
        The number of tokens in *text*.
    """
    encoder = _get_encoder()
    if encoder is not None:
        return len(encoder.encode(text))
    return estimate_tokens(text)


def estimate_tokens(text: str) -> int:
    """Estimate token count using character-based heuristic.

    Uses the constant CHARS_PER_TOKEN_FALLBACK (default 4) as the
    divisor. This is a rough approximation that works reasonably
    well for English code and prose.

    Args:
        text: The text to estimate tokens for.

    Returns:
        Estimated token count (always >= 0).
    """
    if not text:
        return 0
    return max(1, len(text) // CHARS_PER_TOKEN_FALLBACK)


def _get_encoder() -> Any | None:
    """Lazily load and cache the tiktoken encoder.

    Returns the cached encoder on subsequent calls. If tiktoken is
    not available or fails to load, returns None and caches the
    error message for diagnostics.

    Returns:
        A tiktoken Encoding instance, or None if unavailable.
    """
    global _encoder, _encoder_error

    if _encoder is not None:
        return _encoder
    if _encoder_error is not None:
        return None

    try:
        import tiktoken  # type: ignore[import-not-found]
        _encoder = tiktoken.get_encoding(TIKTOKEN_DEFAULT_ENCODING)
        return _encoder
    except ImportError:
        _encoder_error = "tiktoken is not installed"
        return None
    except Exception as exc:
        _encoder_error = f"Failed to load tiktoken encoder: {exc}"
        return None


def get_encoder_error() -> str | None:
    """Return the error message from the last failed encoder load.

    Returns None if the encoder loaded successfully or has not
    been attempted yet.

    Returns:
        Error message string, or None.
    """
    return _encoder_error
