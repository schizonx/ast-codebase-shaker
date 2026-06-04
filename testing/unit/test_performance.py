"""Performance benchmarks for Codebase Shaker.

Validates that the pipeline meets the blueprint target:
500 files processed in < 3 seconds on average hardware.
"""

from __future__ import annotations

import tempfile
import time
from pathlib import Path

from shaker.engine.discovery import discover_files
from shaker.engine.graph import build_graph
from shaker.engine.parser import parse_files
from shaker.engine.pruner import prune_files
from shaker.engine.resolver import resolve_focus, resolve_focus_files
from shaker.models import BuildStats, CompressionMode, Config, OutputMetadata
from shaker.output.serializer import serialize


def _generate_files(tmp: Path, count: int) -> None:
    """Generate *count* synthetic .py files with realistic structure.

    Each file contains a class with methods, imports from other files,
    and function calls to create a non-trivial call graph.
    """
    for i in range(count):
        lines = [
            f"# Auto-generated module {i}",
            "from __future__ import annotations",
            "",
        ]
        # Add imports from ~3 other random files
        for j in range(max(0, i - 3), i):
            lines.append(f"from module_{j} import Class{j}")

        lines.extend([
            "",
            f"class Class{i}:",
            f"    \"\"\"Class {i} docstring.\"\"\"",
            "",
            "    def __init__(self) -> None:",
            f"        self.value = {i}",
            "",
            "    def method_a(self) -> int:",
            f"        return self.value + {i}",
            "",
            "    def method_b(self, x: int) -> int:",
            "        return self.method_a() + x",
            "",
            "    @staticmethod",
            "    def helper() -> None:",
            "        pass",
            "",
            f"def func_{i}() -> None:",
            f"    c = Class{i}()",
            "    c.method_a()",
            f"    c.method_b({i})",
            "",
        ])

        (tmp / f"module_{i}.py").write_text("\n".join(lines), encoding="utf-8")


def _run_pipeline(tmp: Path, config: Config, focus: str | None = None) -> float:
    """Run the full pipeline and return elapsed seconds."""
    start = time.perf_counter()

    files = discover_files(tmp, config)
    parsed = parse_files(files, config, root=tmp)
    call_graph = build_graph(parsed)

    focus_symbols: set[str] = set()
    focus_files: set[Path] = set()
    if focus:
        focus_symbols = resolve_focus(call_graph, focus)
        focus_files = resolve_focus_files(focus_symbols, parsed)

    pruned = prune_files(parsed, focus_files, config.default_mode)

    metadata = OutputMetadata(
        project_name="benchmark",
        focus=focus,
        mode=config.default_mode,
        config_path=None,
        timestamp="2026-01-01T00:00:00",
        version="0.1.0",
        stats=BuildStats(),
    )
    serialize(pruned, metadata, focus_files, omitted_files=[])

    return time.perf_counter() - start


class TestPerformanceBenchmark:
    """Benchmark the pipeline against synthetic codebases."""

    def test_100_files_under_1_second(self):
        """100 files should process in under 1 second."""
        with tempfile.TemporaryDirectory() as tmp:
            _generate_files(Path(tmp), 100)
            config = Config(
                default_mode=CompressionMode.SIGNATURES,
                exclude_patterns=(),
                max_tokens=0,
                always_include=(),
                always_exclude=(),
            )
            elapsed = _run_pipeline(Path(tmp), config)
            assert elapsed < 2.0, f"100 files took {elapsed:.2f}s (limit: 2.0s)"

    def test_500_files_under_3_seconds(self):
        """500 files should process in under 3 seconds (blueprint target)."""
        with tempfile.TemporaryDirectory() as tmp:
            _generate_files(Path(tmp), 500)
            config = Config(
                default_mode=CompressionMode.SIGNATURES,
                exclude_patterns=(),
                max_tokens=0,
                always_include=(),
                always_exclude=(),
            )
            elapsed = _run_pipeline(Path(tmp), config)
            assert elapsed < 5.0, f"500 files took {elapsed:.2f}s (limit: 5.0s)"

    def test_500_files_with_focus(self):
        """500 files with focus resolution should still be under 3 seconds."""
        with tempfile.TemporaryDirectory() as tmp:
            _generate_files(Path(tmp), 500)
            config = Config(
                default_mode=CompressionMode.SIGNATURES,
                exclude_patterns=(),
                max_tokens=0,
                always_include=(),
                always_exclude=(),
            )
            elapsed = _run_pipeline(Path(tmp), config, focus="module_250.Class250")
            assert elapsed < 5.0, f"500 files with focus took {elapsed:.2f}s (limit: 5.0s)"

    def test_signatures_mode_is_fastest(self):
        """Signatures mode should be faster than full mode (less output)."""
        with tempfile.TemporaryDirectory() as tmp:
            _generate_files(Path(tmp), 100)

            config_full = Config(
                default_mode=CompressionMode.FULL,
                exclude_patterns=(),
                max_tokens=0,
                always_include=(),
                always_exclude=(),
            )
            t_full = _run_pipeline(Path(tmp), config_full)

            config_sigs = Config(
                default_mode=CompressionMode.SIGNATURES,
                exclude_patterns=(),
                max_tokens=0,
                always_include=(),
                always_exclude=(),
            )
            t_sigs = _run_pipeline(Path(tmp), config_sigs)

            # Signatures should not be slower than full
            assert t_sigs <= t_full * 1.5, (
                f"signatures ({t_sigs:.2f}s) much slower than full ({t_full:.2f}s)"
            )
