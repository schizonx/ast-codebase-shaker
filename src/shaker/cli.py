"""CLI entry point. The composition root.

Defines Click commands and options, orchestrates the full pipeline,
and displays results via Rich. This is the only module that imports
from all other packages. No business logic lives here.
"""

from __future__ import annotations

import datetime
import json
import logging
import os
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table

from shaker import __version__
from shaker.engine import (
    FocusDirection,
    build_graph,
    clone_remote,
    discover_files,
    parse_files,
    prune_files,
    redact_report,
    resolve_focus,
    resolve_focus_files,
    scan_files,
    suggest_symbols,
)
from shaker.engine import (
    score_files as _score_files,
)
from shaker.infra import count_tokens, load_config
from shaker.models import (
    CompressionMode,
    Config,
    OutputFormat,
    OutputMetadata,
    PipelineState,
)
from shaker.output import (
    deliver,
    serialize_json,
    serialize_markdown,
    serialize_plain,
    serialize_xml,
)

logger = logging.getLogger(__name__)
console = Console()

_FORMAT_SERIALIZERS = {
    OutputFormat.MARKDOWN: serialize_markdown,
    OutputFormat.XML: serialize_xml,
    OutputFormat.JSON: serialize_json,
    OutputFormat.PLAIN: serialize_plain,
}

_PRESETS: dict[str, dict[str, list[str]]] = {
    "django": {
        "exclude": [
            "__pycache__/", "*.pyc", ".git/", "venv/", ".venv/",
            "migrations/", "*.mo", ".static/", "staticfiles/",
            "*.sqlite3", ".coverage", "htmlcov/",
        ],
    },
    "fastapi": {
        "exclude": [
            "__pycache__/", "*.pyc", ".git/", "venv/", ".venv/",
            ".mypy_cache/", ".pytest_cache/", "*.egg-info/",
        ],
    },
    "flask": {
        "exclude": [
            "__pycache__/", "*.pyc", ".git/", "venv/", ".venv/",
            "instance/", ".mypy_cache/", "*.egg-info/",
        ],
    },
}


@click.command()
@click.argument("path", type=click.Path(exists=False), default=".")
@click.option(
    "--focus",
    "-f",
    multiple=True,
    default=(),
    help="Focal symbol name (e.g., 'auth.login'). Can repeat.",
)
@click.option(
    "--mode",
    "-m",
    type=click.Choice(["full", "signatures", "strip"]),
    default=None,
    help="Compression mode (default: signatures)",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["markdown", "xml", "json", "plain"]),
    default=None,
    help="Output format (default: markdown)",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default=None,
    help="Output file path (default: stdout only)",
)
@click.option(
    "--no-clipboard",
    is_flag=True,
    default=False,
    help="Skip clipboard copy",
)
@click.option(
    "--max-tokens",
    type=int,
    default=None,
    help="Token limit warning threshold",
)
@click.option(
    "--exclude",
    multiple=True,
    help="Filename patterns to exclude (can repeat)",
)
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=True),
    default=None,
    help="Path to .shakerrc.json config file",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    default=False,
    help="Verbose output",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Parse and analyze only, no output delivery",
)
@click.option(
    "--list-symbols",
    is_flag=True,
    default=False,
    help="List all discovered symbols and exit",
)
@click.option(
    "--no-tree",
    is_flag=True,
    default=False,
    help="Skip the file tree in Markdown output",
)
@click.option(
    "--depth",
    type=int,
    default=None,
    help="Limit focus resolution to N hops (default: unlimited)",
)
@click.option(
    "--direction",
    type=click.Choice(["both", "callers", "callees"]),
    default=None,
    help="Focus traversal direction (default: both)",
)
@click.option(
    "--quiet",
    "-q",
    is_flag=True,
    default=False,
    help="Suppress non-essential output (stats, warnings)",
)
@click.option(
    "--no-progress",
    is_flag=True,
    default=False,
    help="Disable progress bar",
)
@click.option(
    "--no-security-scan",
    is_flag=True,
    default=False,
    help="Disable security scanning",
)
@click.option(
    "--security-warn",
    is_flag=True,
    default=False,
    help="Warn on secrets instead of redacting",
)
@click.option(
    "--stats",
    "stats_path",
    type=click.Path(),
    default=None,
    help="Write build statistics to a JSON file",
)
@click.option(
    "--init",
    is_flag=True,
    default=False,
    help="Generate a .shakerrc.json template and exit",
)
@click.option(
    "--remote",
    default=None,
    help="Remote repository URL to clone and analyze",
)
@click.option(
    "--mcp",
    is_flag=True,
    default=False,
    help="Run as MCP server (stdio transport)",
)
@click.option(
    "--score-files",
    is_flag=True,
    default=False,
    help="Display file importance scores in output",
)
@click.option(
    "--preset",
    type=click.Choice(["django", "fastapi", "flask"]),
    default=None,
    help="Use a framework-specific config preset",
)
@click.option(
    "--enforce-max-tokens",
    is_flag=True,
    default=False,
    help="Auto-adjust compression to fit within --max-tokens budget",
)
@click.version_option(version=__version__)
def cli(
    path: str,
    focus: tuple[str, ...],
    mode: str | None,
    output_format: str | None,
    output: str | None,
    no_clipboard: bool,
    max_tokens: int | None,
    exclude: tuple[str, ...],
    config_path: str | None,
    verbose: bool,
    dry_run: bool,
    list_symbols: bool,
    no_tree: bool,
    depth: int | None,
    direction: str | None,
    quiet: bool,
    no_progress: bool,
    no_security_scan: bool,
    security_warn: bool,
    stats_path: str | None,
    init: bool,
    remote: str | None,
    mcp: bool,
    score_files: bool,
    preset: str | None,
    enforce_max_tokens: bool,
) -> None:
    """Codebase Shaker — Compress Python codebases for LLM context.

    Analyzes the call graph from a focal point and compresses
    everything else to minimize token usage while preserving
    structural understanding.
    """
    if init:
        _generate_config_template()
        return

    if mcp:
        _run_mcp_server()
        return

    if verbose:
        logging.basicConfig(level=logging.DEBUG)

    try:
        state = run_pipeline(
            path=Path(path),
            focus=list(focus) if focus else [],
            mode=mode,
            output_format=output_format,
            output=Path(output) if output else None,
            no_clipboard=no_clipboard,
            max_tokens=max_tokens,
            exclude=exclude,
            config_path=Path(config_path) if config_path else None,
            verbose=verbose,
            dry_run=dry_run,
            list_symbols=list_symbols,
            no_tree=no_tree,
            depth=depth,
            direction=direction,
            quiet=quiet,
            show_progress=not no_progress and console.is_terminal,
            no_security_scan=no_security_scan,
            security_warn=security_warn,
            stats_path=Path(stats_path) if stats_path else None,
            remote=remote,
            score_files=score_files,
            preset=preset,
            enforce_max_tokens=enforce_max_tokens,
        )
        display_results(
            state,
            list_symbols=list_symbols,
            quiet=quiet,
            score_files=score_files,
        )
    except FileNotFoundError as e:
        handle_error(e)
        sys.exit(1)
    except Exception as e:
        handle_error(e)
        sys.exit(2)


def run_pipeline(
    path: Path,
    focus: list[str],
    mode: str | None,
    output_format: str | None,
    output: Path | None,
    no_clipboard: bool,
    max_tokens: int | None,
    exclude: tuple[str, ...],
    config_path: Path | None,
    verbose: bool,
    dry_run: bool,
    list_symbols: bool = False,
    no_tree: bool = False,
    depth: int | None = None,
    direction: str | None = None,
    quiet: bool = False,
    show_progress: bool = True,
    no_security_scan: bool = False,
    security_warn: bool = False,
    stats_path: Path | None = None,
    remote: str | None = None,
    score_files: bool = False,
    preset: str | None = None,
    enforce_max_tokens: bool = False,
) -> PipelineState:
    """Orchestrate the full pipeline.

    Executes all stages in sequence:
    -1. Remote cloning (if --remote)
     0. Config loading
     1. File discovery
     2. AST parsing
     3. Call graph building
     4. Focus resolution
     5. Pruning/compression (with optional budget enforcement)
     5.5. Security scanning (if enabled)
     6. File importance scoring (if requested)
     7. Serialization + delivery
     8. Cleanup (remote temp dir)

    Args:
        path: Root path to analyze.
        focus: List of focal symbol names.
        mode: Compression mode string.
        output_format: Output format string.
        output: Output file path.
        no_clipboard: Skip clipboard.
        max_tokens: Token limit.
        exclude: Exclude patterns.
        config_path: Config file path.
        verbose: Verbose output.
        dry_run: Analyze only, no delivery.
        list_symbols: List symbols and exit.
        no_tree: Skip file tree in output.
        depth: Max hop count for focus resolution.
        direction: Focus traversal direction.
        quiet: Suppress non-essential output.
        show_progress: Show progress bar.
        no_security_scan: Disable security scanning.
        security_warn: Warn instead of redact on secrets.
        stats_path: Path to write stats JSON.
        remote: Remote repository URL.
        score_files: Whether to compute and display file scores.
        preset: Framework preset name.
        enforce_max_tokens: Auto-adjust compression to fit budget.

    Returns:
        Final PipelineState with all fields populated.
    """
    # Stage -1: Remote cloning
    remote_path: Path | None = None
    if remote is not None:
        if not quiet:
            console.print(f"[dim]Cloning {remote}...[/dim]")
        remote_path = clone_remote(remote)
        path = remote_path

    # Stage 0: Config (with environment variable fallback and preset)
    config = load_config(config_path)

    if preset is not None:
        _apply_preset(config, preset)

    mode = mode or os.environ.get("SHAKER_MODE")
    max_tokens = max_tokens or _env_int("SHAKER_MAX_TOKENS")
    if not exclude:
        env_exclude = os.environ.get("SHAKER_EXCLUDE", "")
        if env_exclude:
            exclude = tuple(p.strip() for p in env_exclude.split(",") if p.strip())
    if mode is not None:
        config.default_mode = CompressionMode(mode)
    if max_tokens is not None:
        config.max_tokens = max_tokens
    if exclude:
        config.exclude_patterns = tuple(exclude)
    if output_format is not None:
        config.output_format = OutputFormat(output_format)
    if quiet:
        config.quiet = True
    if no_security_scan:
        config.security_scan = False
    if security_warn:
        config.security_redact = False
    if enforce_max_tokens:
        config.enforce_max_tokens = True

    focus_str = ", ".join(focus) if focus else None
    state = PipelineState(config=config, root_path=path, focus=focus_str)

    progress_ctx = (
        Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            console=console,
            disable=not show_progress,
        )
        if show_progress
        else None
    )

    if progress_ctx is not None:
        progress_ctx.__enter__()

    try:
        # Stage 1: Discovery
        if progress_ctx is not None:
            t = progress_ctx.add_task("Discovering files...", total=None)
        state.discovered_files = discover_files(path, config)
        state.stats.total_files = len(state.discovered_files)
        if progress_ctx is not None:
            progress_ctx.update(
                t, completed=True,
                description=f"Discovered {state.stats.total_files} files",
            )

        # Stage 2: Parsing
        if progress_ctx is not None:
            t = progress_ctx.add_task("Parsing files...", total=None)
        state.parsed_files = parse_files(
            state.discovered_files, config, root=path,
        )
        state.stats.parse_errors = sum(
            1 for pf in state.parsed_files.values() if pf.parse_error
        )
        if progress_ctx is not None:
            progress_ctx.update(
                t, completed=True,
                description=f"Parsed {len(state.parsed_files)} files",
            )

        # Stage 3: Graph building
        if progress_ctx is not None:
            t = progress_ctx.add_task("Building call graph...", total=None)
        state.call_graph = build_graph(state.parsed_files)
        if progress_ctx is not None:
            progress_ctx.update(t, completed=True, description="Call graph built")

        # Stage 4: Focus resolution (supports multiple focus symbols)
        focus_direction = FocusDirection.BOTH
        if direction == "callers":
            focus_direction = FocusDirection.CALLERS
        elif direction == "callees":
            focus_direction = FocusDirection.CALLEES

        if focus:
            all_focus_symbols: set[str] = set()
            for f in focus:
                resolved = resolve_focus(
                    state.call_graph, f,
                    direction=focus_direction,
                    max_depth=depth,
                )
                if not resolved:
                    suggestions = suggest_symbols(state.call_graph, f)
                    if suggestions and not quiet:
                        console.print(
                            f"[yellow]Focus '{f}' not found. "
                            f"Did you mean:[/yellow]"
                        )
                        for s in suggestions:
                            console.print(f"  - {s}")
                    raise FileNotFoundError(
                        f"Focus '{f}' not found in call graph"
                    )
                all_focus_symbols |= resolved
            state.focus_symbols = all_focus_symbols

        state.focus_files = resolve_focus_files(
            state.focus_symbols, state.parsed_files
        )

        # Stage 5: Pruning (with budget awareness)
        if progress_ctx is not None:
            t = progress_ctx.add_task("Pruning files...", total=None)
        state.pruned_files = prune_files(
            state.parsed_files,
            state.focus_files,
            config.default_mode,
            max_tokens=config.max_tokens,
            enforce_max_tokens=config.enforce_max_tokens,
        )
        if progress_ctx is not None:
            progress_ctx.update(t, completed=True, description="Pruning complete")

        # Determine omitted files (discovered but not in pruned)
        all_discovered = set(state.parsed_files.keys())
        retained = set(state.pruned_files.keys())
        state.omitted_files = sorted(all_discovered - retained)

        # Stats
        state.stats.retained_files = len(state.pruned_files)
        state.stats.omitted_files = len(state.omitted_files)
        state.stats.total_lines = sum(
            len(pf.source.splitlines()) for pf in state.parsed_files.values()
        )
        state.stats.output_lines = sum(
            len(src.splitlines()) for src in state.pruned_files.values()
        )

        if dry_run:
            return state

        # Token counting
        state.stats.input_tokens = count_tokens(
            "\n".join(pf.source for pf in state.parsed_files.values())
        )
        state.stats.output_tokens = count_tokens(
            "\n".join(state.pruned_files.values())
        )
        if state.stats.input_tokens > 0:
            state.stats.reduction_pct = round(
                (1 - state.stats.output_tokens / state.stats.input_tokens) * 100,
                1,
            )

        # Stage 5.5: Security scanning
        if config.security_scan:
            if progress_ctx is not None:
                t = progress_ctx.add_task("Scanning for secrets...", total=None)
            sources_for_scan = {
                fpath: pf.source
                for fpath, pf in state.parsed_files.items()
            }
            state.security_report = scan_files(sources_for_scan)
            if progress_ctx is not None:
                progress_ctx.update(
                    t, completed=True,
                    description=(
                        f"Scanned {state.security_report.total_scanned} files, "
                        f"found {state.security_report.total_findings} secrets"
                    ),
                )

            if state.security_report.total_findings > 0 and config.security_redact:
                redacted = redact_report(
                    state.pruned_files, state.security_report
                )
                state.pruned_files = redacted

        # Stage 5.6: File importance scoring
        if score_files and state.call_graph is not None:
            if progress_ctx is not None:
                t = progress_ctx.add_task("Scoring files...", total=None)
            state.file_scores = _score_files(
                state.parsed_files,
                state.call_graph,
                state.focus_files,
                use_git=config.use_git_scoring,
            )
            if progress_ctx is not None:
                progress_ctx.update(
                    t, completed=True,
                    description=f"Scored {len(state.file_scores)} files",
                )

        # Stage 6: Serialization
        project_name = path.resolve().name or "project"
        metadata = OutputMetadata(
            project_name=project_name,
            focus=focus_str,
            mode=config.default_mode,
            config_path=config_path,
            timestamp=datetime.datetime.now().isoformat(),
            version=__version__,
            stats=state.stats,
        )
        serializer = _FORMAT_SERIALIZERS.get(
            config.output_format, serialize_markdown
        )
        state.output = serializer(
            state.pruned_files,
            metadata,
            state.focus_files,
            state.omitted_files,
            include_tree=not no_tree,
        )

        # Recount output tokens against the actual serialized output
        state.stats.output_tokens = count_tokens(state.output)
        if state.stats.input_tokens > 0:
            state.stats.reduction_pct = round(
                (1 - state.stats.output_tokens / state.stats.input_tokens) * 100,
                1,
            )

        # Write stats file if requested
        if stats_path is not None:
            _write_stats_file(state, stats_path)

        # Stage 7: Delivery
        state.delivery = deliver(
            state.output,
            output,
            copy_to_clipboard=not no_clipboard,
        )

        return state

    finally:
        if progress_ctx is not None:
            progress_ctx.__exit__(None, None, None)
        # Stage 8: Cleanup remote temp dir
        if remote_path is not None:
            from shaker.engine.remote import cleanup_remote
            cleanup_remote(remote_path)


def _apply_preset(config: Config, preset: str) -> None:
    """Apply a framework preset to the config.

    Args:
        config: The config to modify.
        preset: Preset name (django, fastapi, flask).
    """
    preset_data = _PRESETS.get(preset, {})
    if "exclude" in preset_data:
        config.exclude_patterns = tuple(preset_data["exclude"])


def _write_stats_file(state: PipelineState, stats_path: Path) -> None:
    """Write build statistics to a JSON file.

    Args:
        state: Final pipeline state.
        stats_path: Path to write the stats JSON file.
    """
    s = state.stats
    stats_data = {
        "project": state.root_path.resolve().name,
        "version": __version__,
        "timestamp": datetime.datetime.now().isoformat(),
        "focus": state.focus,
        "format": state.config.output_format.value,
        "stats": {
            "total_files": s.total_files,
            "retained_files": s.retained_files,
            "omitted_files": s.omitted_files,
            "parse_errors": s.parse_errors,
            "total_lines": s.total_lines,
            "output_lines": s.output_lines,
            "input_tokens": s.input_tokens,
            "output_tokens": s.output_tokens,
            "reduction_pct": s.reduction_pct,
        },
    }
    if state.security_report is not None:
        stats_data["security"] = {
            "total_scanned": state.security_report.total_scanned,
            "total_findings": state.security_report.total_findings,
            "critical_count": state.security_report.critical_count,
            "redacted_count": state.security_report.redacted_count,
        }
    stats_path.parent.mkdir(parents=True, exist_ok=True)
    stats_path.write_text(
        json.dumps(stats_data, indent=2) + "\n", encoding="utf-8"
    )


def display_results(
    state: PipelineState,
    list_symbols: bool = False,
    quiet: bool = False,
    score_files: bool = False,
) -> None:
    """Display build results via Rich.

    Shows a summary table with before/after stats,
    warnings, and delivery status. If *list_symbols* is True,
    displays all discovered symbols instead of pipeline results.

    Args:
        state: Final pipeline state.
        list_symbols: Whether to list symbols.
        quiet: Whether to suppress non-essential output.
        score_files: Whether to display file importance scores.
    """
    if list_symbols:
        _display_symbols(state)
        return

    if not quiet:
        stats = state.stats
        table = Table(title="Codebase Shaker Results", show_header=True)
        table.add_column("Metric", style="bold")
        table.add_column("Value", justify="right")

        table.add_row("Files retained", f"{stats.retained_files} / {stats.total_files}")
        table.add_row("Files omitted", str(stats.omitted_files))
        table.add_row("Parse errors", str(stats.parse_errors))
        table.add_row("Input tokens", f"{stats.input_tokens:,}")
        table.add_row("Output tokens", f"{stats.output_tokens:,}")
        if stats.reduction_pct:
            table.add_row("Reduction", f"{stats.reduction_pct:.1f}%")

        console.print(table)

        # Security report summary
        if state.security_report and state.security_report.total_findings > 0:
            sr = state.security_report
            console.print(
                f"[yellow]Security:[/yellow] {sr.total_findings} finding(s) "
                f"({sr.critical_count} critical, "
                f"{sr.redacted_count} redacted)"
            )

        if state.delivery and state.delivery.warnings:
            console.print("[yellow]Warnings:[/yellow]")
            for w in state.delivery.warnings:
                console.print(f"  - {w}")

    if score_files and state.file_scores:
        _display_file_scores(state)

    if state.output:
        console.print(state.output)


def _display_symbols(state: PipelineState) -> None:
    """Display all discovered symbols in a Rich table.

    Args:
        state: Pipeline state with a populated call_graph.
    """
    if state.call_graph is None:
        console.print("[red]No call graph built.[/red]")
        return

    table = Table(title="Discovered Symbols", show_header=True)
    table.add_column("Qualified Name", style="bold")
    table.add_column("Type")
    table.add_column("File")
    table.add_column("Line", justify="right")

    for qname in sorted(state.call_graph.symbol_table.keys()):
        sym = state.call_graph.symbol_table[qname]
        table.add_row(
            sym.qualified_name,
            sym.symbol_type.value,
            str(sym.file),
            str(sym.line_number),
        )

    console.print(table)
    console.print(f"\n[dim]Total: {len(state.call_graph.symbol_table)} symbols[/dim]")


def _display_file_scores(state: PipelineState) -> None:
    """Display file importance scores in a Rich table.

    Args:
        state: Pipeline state with populated file_scores.
    """
    if not state.file_scores:
        return

    table = Table(title="File Importance Scores", show_header=True)
    table.add_column("File", style="bold")
    table.add_column("Score", justify="right")
    table.add_column("Importers", justify="right")
    table.add_column("Centrality", justify="right")
    table.add_column("Git Changes (30d)", justify="right")
    table.add_column("Focus", justify="center")

    sorted_scores = sorted(
        state.file_scores.values(),
        key=lambda s: s.score,
        reverse=True,
    )
    for fs in sorted_scores:
        table.add_row(
            str(fs.file),
            f"{fs.score:.4f}",
            str(fs.importer_count),
            f"{fs.centrality:.4f}",
            str(fs.git_changes_30d),
            "★" if fs.is_focus else "",
        )

    console.print(table)


def handle_error(error: Exception) -> str:
    """Format an error for user-friendly display.

    Args:
        error: The exception to format.

    Returns:
        Formatted error message string.
    """
    msg = f"[red]Error:[/red] {error}"
    console.print(msg)
    return str(error)


def _env_int(name: str) -> int | None:
    """Read an integer from an environment variable.

    Returns None if the variable is unset or not a valid integer.

    Args:
        name: Environment variable name.

    Returns:
        Parsed integer value, or None.
    """
    raw = os.environ.get(name)
    if raw is None:
        return None
    try:
        return int(raw)
    except ValueError:
        logger.warning("Invalid integer for env var %s: %r", name, raw)
        return None


def _generate_config_template() -> None:
    """Generate a .shakerrc.json template file.

    Writes a commented JSON template to the current directory.
    If the file already exists, warns and does not overwrite.
    """
    target = Path(".shakerrc.json")
    if target.exists():
        console.print(
            "[yellow]Warning:[/yellow] .shakerrc.json already exists. "
            "Not overwriting."
        )
        return

    template = {
        "mode": "signatures",
        "format": "markdown",
        "exclude": ["__pycache__/", "*.pyc", ".git/", "venv/", ".venv/"],
        "max_tokens": None,
        "always_include": [],
        "always_exclude": [],
        "security_scan": True,
        "security_redact": True,
        "show_progress": True,
        "quiet": False,
        "enforce_max_tokens": False,
        "use_git_scoring": True,
    }
    target.write_text(
        json.dumps(template, indent=2) + "\n", encoding="utf-8"
    )
    console.print(f"[green]Created {target}[/green]")


def _run_mcp_server() -> None:
    """Start the MCP server.

    Imports the MCP server module and runs it.
    Handles the case where the mcp package is not installed.
    """
    try:
        from shaker.mcp.server import main as mcp_main
        mcp_main()
    except ImportError:
        console.print(
            "[red]Error:[/red] MCP server requires the 'mcp' package. "
            "Install it with: pip install codebase-shaker[mcp]"
        )
        sys.exit(1)


def main() -> None:
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
