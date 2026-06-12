"""MCP server mode for Codebase Shaker.

Exposes Codebase Shaker as an MCP server with two tools:
- shake: Compress a Python codebase for LLM context
- list_symbols: List all symbols in a Python codebase

Uses stdio transport. Requires the optional `mcp` package:
    pip install codebase-shaker[mcp]
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from shaker.engine import (
    build_graph,
    discover_files,
    parse_files,
    prune_files,
    resolve_focus,
    resolve_focus_files,
)
from shaker.infra import load_config

logger = logging.getLogger(__name__)


async def handle_request(request: dict[str, Any]) -> dict[str, Any]:
    """Handle an MCP tool call request.

    Dispatches to the appropriate tool handler based on the
    ``params.name`` field.

    Args:
        request: The JSON-RPC request with ``params.name`` and
            ``params.arguments``.

    Returns:
        JSON-RPC response dict with tool result.
    """
    method = request.get("method", "")

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request.get("id"),
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {
                    "name": "codebase-shaker",
                    "version": "1.0.0",
                },
            },
        }

    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": request.get("id"),
            "result": {
                "tools": [
                    {
                        "name": "shake",
                        "description": (
                            "Compress a Python codebase for LLM context. "
                            "Analyzes the call graph and produces compressed "
                            "output focused on the specified symbol."
                        ),
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "path": {
                                    "type": "string",
                                    "description": "Path to the Python project root",
                                },
                                "focus": {
                                    "type": "string",
                                    "description": "Focal symbol name (e.g., 'auth.login')",
                                },
                                "mode": {
                                    "type": "string",
                                    "enum": ["full", "signatures", "strip"],
                                    "description": "Compression mode (default: signatures)",
                                },
                                "max_tokens": {
                                    "type": "integer",
                                    "description": "Token budget limit",
                                },
                            },
                            "required": ["path"],
                        },
                    },
                    {
                        "name": "list_symbols",
                        "description": (
                            "List all discovered symbols in a Python codebase "
                            "with their types and locations."
                        ),
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "path": {
                                    "type": "string",
                                    "description": "Path to the Python project root",
                                },
                            },
                            "required": ["path"],
                        },
                    },
                ],
            },
        }

    if method == "tools/call":
        name = request.get("params", {}).get("name", "")
        args = request.get("params", {}).get("arguments", {})

        if name == "shake":
            return await _handle_shake(request.get("id"), args)
        if name == "list_symbols":
            return await _handle_list_symbols(request.get("id"), args)

    return {
        "jsonrpc": "2.0",
        "id": request.get("id"),
        "error": {"code": -32601, "message": f"Unknown method: {method}"},
    }


async def _handle_shake(req_id: int | str | None, args: dict[str, Any]) -> dict[str, Any]:
    """Handle the shake tool call.

    Args:
        req_id: Request ID from the JSON-RPC request.
        args: Tool arguments (path, focus, mode, max_tokens).

    Returns:
        JSON-RPC response with compressed output.
    """
    try:
        path = Path(str(args.get("path", ".")))
        focus = args.get("focus")
        mode_str = str(args.get("mode", "signatures"))
        max_tokens_raw = args.get("max_tokens")
        max_tokens: int | None = None
        if max_tokens_raw is not None:
            max_tokens = int(max_tokens_raw)

        from shaker.models import CompressionMode, OutputFormat

        config = load_config()
        if max_tokens:
            config.max_tokens = max_tokens
        config.default_mode = CompressionMode(mode_str)
        config.output_format = OutputFormat.PLAIN
        config.show_progress = False
        config.quiet = True

        path_obj = Path(path)
        discovered = discover_files(path_obj, config)
        parsed = parse_files(discovered, config, root=path_obj)
        call_graph = build_graph(parsed)

        focus = focus or ""
        focus_symbols = set()
        if focus:
            focus_symbols = resolve_focus(call_graph, focus)
        focus_files = resolve_focus_files(focus_symbols, parsed)
        pruned = prune_files(parsed, focus_files, config.default_mode)

        parts: list[str] = []
        for fpath in sorted(pruned.keys()):
            is_focus = fpath in focus_files
            badge = " [FOCUS]" if is_focus else ""
            parts.append(f"## {fpath}{badge}\n")
            parts.append(pruned[fpath])
            parts.append("")

        output = "\n".join(parts)

        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [
                    {"type": "text", "text": output}
                ],
            },
        }
    except Exception as exc:
        logger.exception("shake tool failed")
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [
                    {"type": "text", "text": f"Error: {exc}"}
                ],
                "isError": True,
            },
        }


async def _handle_list_symbols(req_id: int | str | None, args: dict[str, Any]) -> dict[str, Any]:
    """Handle the list_symbols tool call.

    Args:
        req_id: Request ID from the JSON-RPC request.
        args: Tool arguments (path).

    Returns:
        JSON-RPC response with symbol listing.
    """
    try:
        path = Path(str(args.get("path", ".")))

        config = load_config()
        config.show_progress = False

        path_obj = Path(path)
        discovered = discover_files(path_obj, config)
        parsed = parse_files(discovered, config, root=path_obj)
        call_graph = build_graph(parsed)

        symbols = []
        for qname in sorted(call_graph.symbol_table.keys()):
            sym = call_graph.symbol_table[qname]
            symbols.append({
                "name": sym.qualified_name,
                "type": sym.symbol_type.value,
                "file": str(sym.file),
                "line": sym.line_number,
            })

        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(symbols, indent=2),
                    }
                ],
            },
        }
    except Exception as exc:
        logger.exception("list_symbols tool failed")
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [
                    {"type": "text", "text": f"Error: {exc}"}
                ],
                "isError": True,
            },
        }


async def run_server() -> None:
    """Run the MCP server via stdio transport.

    Reads JSON-RPC lines from stdin, dispatches to handle_request,
    and writes responses to stdout.
    """
    loop = asyncio.get_event_loop()
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: protocol, __import__("sys").stdin)

    writer_transport, writer_protocol = await loop.connect_write_pipe(
        asyncio.streams.FlowControlMixin, __import__("sys").stdout
    )
    writer = asyncio.StreamWriter(
        writer_transport, writer_protocol, reader, loop
    )

    while True:
        try:
            line = await reader.readline()
            if not line:
                break
            request = json.loads(line.decode("utf-8").strip())
            response = await handle_request(request)
            response_line = json.dumps(response) + "\n"
            writer.write(response_line.encode("utf-8"))
            await writer.drain()
        except json.JSONDecodeError:
            continue
        except Exception:
            logger.exception("MCP server error")
            break


def main() -> None:
    """Entry point for MCP server mode."""
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
