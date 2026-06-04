"""Shared test fixtures for Codebase Shaker."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure src/ is on the path for all test runs
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
