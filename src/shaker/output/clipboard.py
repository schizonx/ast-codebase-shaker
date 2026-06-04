"""Stage 7: Output delivery (clipboard + file).

Copies output to the system clipboard and/or writes it to a file.
Gracefully degrades when clipboard is unavailable.
"""

from __future__ import annotations

import logging
from pathlib import Path

from shaker.models import DeliveryResult

logger = logging.getLogger(__name__)

try:
    import pyperclip as _pyperclip  # type: ignore[import-untyped]
except ImportError:
    _pyperclip = None

_HAS_CLIPBOARD: bool = _pyperclip is not None


def deliver(
    content: str,
    output_path: Path | None,
    copy_to_clipboard: bool,
) -> DeliveryResult:
    """Deliver output to clipboard and/or file.

    Attempts clipboard copy when requested, falling back gracefully
    when clipboard support is unavailable. Writes to file when a
    path is provided.

    Args:
        content: The output string to deliver.
        output_path: Path to write output file, or ``None``.
        copy_to_clipboard: Whether to copy to clipboard.

    Returns:
        ``DeliveryResult`` with success/failure status.
    """
    result = DeliveryResult()
    if copy_to_clipboard:
        result.clipboard_success = _copy_to_clipboard(content)
        if not result.clipboard_success:
            result.warnings.append("Clipboard unavailable")
            logger.warning("Clipboard copy failed or unavailable")
    if output_path is not None:
        try:
            _write_to_file(content, output_path)
            result.file_path = output_path
        except OSError as e:
            result.warnings.append(f"File write failed: {e}")
            logger.warning("Failed to write output file: %s", e)
    return result


def _copy_to_clipboard(content: str) -> bool:
    """Copy content to the system clipboard.

    Returns False if clipboard support is unavailable or fails.

    Args:
        content: String to copy.

    Returns:
        True if clipboard copy succeeded.
    """
    if _pyperclip is None:
        return False
    try:
        _pyperclip.copy(content)
    except Exception:
        return False
    else:
        return True


def _write_to_file(content: str, path: Path) -> None:
    """Write content to a file, creating parent directories if needed.

    Args:
        content: String to write.
        path: Destination file path.

    Raises:
        OSError: If the file cannot be written.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
