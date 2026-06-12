"""Remote repository support — clone from URL and cleanup.

Clones a remote Git repository (GitHub/GitLab/etc.) to a temporary
directory, runs the pipeline against it, and securely cleans up the
temporary directory even on errors or interrupts.
"""

from __future__ import annotations

import logging
import shutil
import signal
import subprocess
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import FrameType

logger = logging.getLogger(__name__)


def clone_remote(url: str) -> Path:
    """Clone a remote repository to a temporary directory.

    Creates a temporary directory, clones the repository into it,
    and registers signal handlers for cleanup on SIGINT/SIGTERM.
    The caller is responsible for calling cleanup_remote() when done.

    Args:
        url: The remote repository URL (HTTPS or SSH).
            Supports GitHub, GitLab, Bitbucket, and any git-hosted repo.

    Returns:
        Path to the cloned repository root (the temp directory).

    Raises:
        subprocess.CalledProcessError: If git clone fails.
        FileNotFoundError: If git is not installed.
    """
    tmp_dir = tempfile.mkdtemp(prefix="shaker-remote-")
    tmp_path = Path(tmp_dir)

    logger.info("Cloning %s to %s", url, tmp_path)

    try:
        subprocess.run(
            ["git", "clone", "--depth=1", url, tmp_dir],
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise FileNotFoundError(
            "git is not installed or not on PATH. "
            "Install git to use --remote."
        ) from exc
    except subprocess.CalledProcessError as exc:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise subprocess.CalledProcessError(
            exc.returncode, exc.cmd,
            output=exc.output, stderr=exc.stderr,
        ) from exc

    _register_cleanup(tmp_path)
    return tmp_path


def cleanup_remote(tmp_path: Path) -> None:
    """Remove a cloned remote repository.

    Removes the temporary directory and unregisters signal handlers.
    Safe to call multiple times.

    Args:
        tmp_path: Path to the temporary directory to remove.
    """
    _unregister_cleanup()
    if tmp_path.exists():
        shutil.rmtree(tmp_path, ignore_errors=True)
        logger.info("Cleaned up remote clone at %s", tmp_path)


def _register_cleanup(tmp_path: Path) -> None:
    """Register SIGINT/SIGTERM handlers for cleanup.

    Args:
        tmp_path: Path to clean up on signal.
    """
    signal.signal(signal.SIGINT, _make_cleanup_handler(tmp_path))
    signal.signal(signal.SIGTERM, _make_cleanup_handler(tmp_path))


def _unregister_cleanup() -> None:
    """Unregister signal handlers, restoring defaults."""
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    signal.signal(signal.SIGTERM, signal.SIG_DFL)


def _make_cleanup_handler(tmp_path: Path) -> Callable[[int, FrameType | None], None]:
    """Create a signal handler that cleans up the temp directory.

    Args:
        tmp_path: Path to clean up.

    Returns:
        Signal handler function.
    """
    def handler(signum: int, frame: FrameType | None) -> None:
        logger.info("Received signal %d, cleaning up %s", signum, tmp_path)
        cleanup_remote(tmp_path)
        raise KeyboardInterrupt()
    return handler
