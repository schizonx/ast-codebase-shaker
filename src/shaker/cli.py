"""CLI entry point. The composition root.

Defines Click commands and options, orchestrates the full pipeline,
and displays results via Rich. This is the only module that imports
from all other packages. No business logic lives here.
"""

from __future__ import annotations

import datetime
import logging
import os
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from shaker import __version__
from shaker.engine import (
    FocusDirection,
    build_graph,
    discover_files,
    parse_files,
    prune_files,
    resolve_focus,
    resolve_focus_files,
    suggest_symbols,
)
from shaker.infra import count_tokens, load_config
from shaker.models import (
    CompressionMode,
    OutputMetadata,
    PipelineState,
)
from shaker.output import deliver, serialize

logger = logging.getLogger(__name__)
console = Console()


@click.command()
@click.argument("path", type=click.Path(exists=True), default=".")
@click.option(
    "--focus",
    "-f",
    default=None,
    help="Focal symbol name (e.g., 'auth.login')",
)
@click.option(
    "--mode",
    "-m",
    type=click.Choice(["full", "signatures", "strip"]),
    default=None,
    help="Compression mode (default: signatures)",
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
@click.version_option(version=__version__)
def cli(
    path: str,
    focus: str | None,
    mode: str | None,
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
) -> None:
    """Codebase Shaker — Compress Python codebases for LLM context.

    Analyzes the call graph from a focal point and compresses
    everything else to minimize token usage while preserving
    structural understanding.
    """
    if verbose:
        logging.basicConfig(level=logging.DEBUG)

    try:
        state = run_pipeline(
            path=Path(path),
            focus=focus,
            mode=mode,
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
        )
        display_results(state, list_symbols=list_symbols)
    except FileNotFoundError as e:
        handle_error(e)
        sys.exit(1)
    except Exception as e:
        handle_error(e)
        sys.exit(2)


def run_pipeline(
    path: Path,
    focus: str | None,
    mode: str | None,
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
) -> PipelineState:
    """Orchestrate the full pipeline.

    Executes all seven stages in sequence:
    1. Config loading
    2. File discovery
    3. AST parsing
    4. Call graph building
    5. Focus resolution
    6. Pruning/compression
    7. Serialization + delivery

    Args:
        path: Root path to analyze.
        focus: Focal symbol name.
        mode: Compression mode string.
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

    Returns:
        Final PipelineState with all fields populated.
    """
    # Stage 0: Config (with environment variable fallback)
    config = load_config(config_path)
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

    state = PipelineState(config=config, root_path=path, focus=focus)

    # Stage 1: Discovery
    state.discovered_files = discover_files(path, config)
    state.stats.total_files = len(state.discovered_files)

    # Stage 2: Parsing
    state.parsed_files = parse_files(state.discovered_files, config, root=path)
    state.stats.parse_errors = sum(
        1 for pf in state.parsed_files.values() if pf.parse_error
    )

    # Stage 3: Graph building
    state.call_graph = build_graph(state.parsed_files)

    # Stage 4: Focus resolution
    focus_direction = FocusDirection.BOTH
    if direction == "callers":
        focus_direction = FocusDirection.CALLERS
    elif direction == "callees":
        focus_direction = FocusDirection.CALLEES

    if focus:
        state.focus_symbols = resolve_focus(
            state.call_graph, focus,
            direction=focus_direction,
            max_depth=depth,
        )
        if not state.focus_symbols:
            suggestions = suggest_symbols(state.call_graph, focus)
            if suggestions:
                console.print(
                    f"[yellow]Focus '{focus}' not found. Did you mean:[/yellow]"
                )
                for s in suggestions:
                    console.print(f"  - {s}")
                raise FileNotFoundError(
                    f"Focus '{focus}' not found in call graph"
                )
    state.focus_files = resolve_focus_files(
        state.focus_symbols, state.parsed_files
    )

    # Stage 5: Pruning
    state.pruned_files = prune_files(
        state.parsed_files, state.focus_files, config.default_mode
    )

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

    # Token counting (must happen before serialization so stats are correct
    # in the Markdown header, but after pruning so output is known)
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

    # Stage 6: Serialization
    project_name = path.resolve().name or "project"
    metadata = OutputMetadata(
        project_name=project_name,
        focus=focus,
        mode=config.default_mode,
        config_path=config_path,
        timestamp=datetime.datetime.now().isoformat(),
        version=__version__,
        stats=state.stats,
    )
    state.output = serialize(
        state.pruned_files,
        metadata,
        state.focus_files,
        state.omitted_files,
        include_tree=not no_tree,
    )

    # Recount output tokens against the actual Markdown (not raw pruned source)
    state.stats.output_tokens = count_tokens(state.output)
    if state.stats.input_tokens > 0:
        state.stats.reduction_pct = round(
            (1 - state.stats.output_tokens / state.stats.input_tokens) * 100,
            1,
        )

    # Stage 7: Delivery
    state.delivery = deliver(
        state.output,
        output,
        copy_to_clipboard=not no_clipboard,
    )

    return state


def display_results(state: PipelineState, list_symbols: bool = False) -> None:
    """Display build results via Rich.

    Shows a summary table with before/after stats,
    warnings, and delivery status. If *list_symbols* is True,
    displays all discovered symbols instead of pipeline results.

    Args:
        state: Final pipeline state.
        list_symbols: Whether to list symbols.
    """
    if list_symbols:
        _display_symbols(state)
        return

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

    if state.delivery and state.delivery.warnings:
        console.print("[yellow]Warnings:[/yellow]")
        for w in state.delivery.warnings:
            console.print(f"  - {w}")

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


def main() -> None:
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
