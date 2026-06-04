"""Configuration loading and validation for Codebase Shaker.

Loads .shakerrc.json, validates all fields, and merges with CLI arguments.
CLI arguments always take precedence over config file values.
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path
from typing import Any

from shaker.constants import DEFAULT_MODE, SUPPORTED_MODES
from shaker.models import CompressionMode, Config


def load_config(path: Path | None = None) -> Config:
    """Load and validate configuration from .shakerrc.json.

    If *path* is provided, load from that exact path.
    Otherwise, search upward from the current working directory
    for the first .shakerrc.json found.

    Args:
        path: Explicit config file path, or None for autodiscovery.

    Returns:
        A validated Config instance. Returns defaults if no config
        file is found. Raises ValueError on invalid config values.
    """
    config_path: Path | None
    raw: dict[str, Any]

    if path is not None:
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        config_path = path
        raw = _read_json_file(path)
    else:
        config_path = _find_config_file(Path.cwd())
        if config_path is None:
            return Config()
        raw = _read_json_file(config_path)

    return _parse_config(raw, config_path)


def merge_config_with_cli(config: Config, cli_args: dict[str, Any]) -> Config:
    """Merge CLI arguments into an existing Config.

    CLI arguments take precedence. Only non-None CLI values override
    config file values.

    Args:
        config: The base config loaded from .shakerrc.json.
        cli_args: Dict of CLI argument names to values.
            Recognized keys: 'mode', 'exclude', 'max_tokens',
            'always_include', 'always_exclude'.

    Returns:
        A new Config with CLI overrides applied.
    """
    mode = config.default_mode
    if cli_args.get("mode") is not None:
        mode = _validate_mode(cli_args["mode"])

    exclude_patterns = config.exclude_patterns
    if cli_args.get("exclude") is not None:
        exclude_patterns = _validate_patterns(cli_args["exclude"])

    max_tokens = config.max_tokens
    if cli_args.get("max_tokens") is not None:
        max_tokens = _validate_max_tokens(cli_args["max_tokens"])

    always_include = config.always_include
    if cli_args.get("always_include") is not None:
        always_include = tuple(cli_args["always_include"])

    always_exclude = config.always_exclude
    if cli_args.get("always_exclude") is not None:
        always_exclude = tuple(cli_args["always_exclude"])

    return Config(
        default_mode=mode,
        exclude_patterns=exclude_patterns,
        max_tokens=max_tokens,
        always_include=always_include,
        always_exclude=always_exclude,
        config_path=config.config_path,
    )


def _find_config_file(start: Path) -> Path | None:
    """Search upward for .shakerrc.json from *start* to filesystem root.

    Args:
        start: Directory to begin searching from.

    Returns:
        Path to the first .shakerrc.json found, or None if not found.
    """
    current = start.resolve()
    for parent in [current, *current.parents]:
        candidate = parent / ".shakerrc.json"
        if candidate.is_file():
            return candidate
    return None


def _read_json_file(path: Path) -> dict[str, Any]:
    """Read and parse a JSON file.

    Args:
        path: Path to the JSON file.

    Returns:
        Parsed JSON as a dict.

    Raises:
        ValueError: If the file contains invalid JSON or is not a dict.
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Invalid JSON in config file {path}: {exc}"
        ) from exc

    if not isinstance(data, dict):
        raise ValueError(
            f"Config file {path} must contain a JSON object, "
            f"got {type(data).__name__}"
        )
    return data


def _parse_config(raw: dict[str, Any], config_path: Path | None) -> Config:
    """Parse a raw dict into a Config, applying defaults and validation.

    Unknown keys are ignored with a warning.

    Args:
        raw: The parsed JSON object.
        config_path: The path the config was loaded from (for error messages).

    Returns:
        A validated Config instance.
    """
    _warn_unknown_fields(raw, config_path)

    mode = DEFAULT_MODE
    if "mode" in raw:
        mode = _validate_mode(raw["mode"])

    exclude_patterns: tuple[str, ...] = ()
    if "exclude" in raw:
        exclude_patterns = _validate_patterns(raw["exclude"])

    max_tokens: int | None = None
    if "max_tokens" in raw:
        max_tokens = _validate_max_tokens(raw["max_tokens"])

    always_include: tuple[str, ...] = ()
    if "always_include" in raw:
        always_include = _validate_string_list(raw["always_include"], "always_include")

    always_exclude: tuple[str, ...] = ()
    if "always_exclude" in raw:
        always_exclude = _validate_string_list(raw["always_exclude"], "always_exclude")

    return Config(
        default_mode=mode,
        exclude_patterns=exclude_patterns,
        max_tokens=max_tokens,
        always_include=always_include,
        always_exclude=always_exclude,
        config_path=config_path,
    )


def _validate_mode(mode: str) -> CompressionMode:
    """Validate and convert a mode string to a CompressionMode.

    Args:
        mode: The mode string (e.g., "full", "signatures", "strip").

    Returns:
        The corresponding CompressionMode.

    Raises:
        ValueError: If the mode string is not a valid CompressionMode value.
    """
    if not isinstance(mode, str):
        raise ValueError(
            f"Mode must be a string, got {type(mode).__name__}: {mode!r}"
        )
    try:
        return CompressionMode(mode.lower())
    except ValueError:
        valid = ", ".join(m.value for m in SUPPORTED_MODES)
        raise ValueError(
            f"Invalid mode '{mode}'. Must be one of: {valid}"
        ) from None


def _validate_patterns(patterns: list[Any]) -> tuple[str, ...]:
    """Validate a list of glob pattern strings.

    Args:
        patterns: List of pattern strings.

    Returns:
        Tuple of validated pattern strings.

    Raises:
        ValueError: If patterns is not a list or contains non-strings.
    """
    return _validate_string_list(patterns, "exclude")


def _validate_string_list(value: list[Any], field_name: str) -> tuple[str, ...]:
    """Validate that value is a list of strings.

    Args:
        value: The value to validate.
        field_name: Name of the config field (for error messages).

    Returns:
        Tuple of strings.

    Raises:
        ValueError: If validation fails.
    """
    if not isinstance(value, list):
        raise ValueError(
            f"'{field_name}' must be a list, got {type(value).__name__}"
        )
    for i, item in enumerate(value):
        if not isinstance(item, str):
            raise ValueError(
                f"'{field_name}[{i}]' must be a string, "
                f"got {type(item).__name__}: {item!r}"
            )
    result: tuple[str, ...] = tuple(value)
    return result


def _validate_max_tokens(value: int) -> int:
    """Validate max_tokens is a positive integer.

    Args:
        value: The max_tokens value.

    Returns:
        The validated integer.

    Raises:
        ValueError: If value is not a positive integer.
    """
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(
            f"'max_tokens' must be an integer, got {type(value).__name__}: {value!r}"
        )
    if value <= 0:
        raise ValueError(
            f"'max_tokens' must be a positive integer, got {value}"
        )
    return value


def _warn_unknown_fields(raw: dict[str, Any], config_path: Path | None) -> None:
    """Warn about unknown fields in the config dict.

    Args:
        raw: The full config dict.
        config_path: The config file path (for warning message).
    """
    known = {"mode", "exclude", "max_tokens", "always_include", "always_exclude"}
    unknown = set(raw.keys()) - known
    if unknown:
        path_str = f" {config_path}" if config_path else ""
        warnings.warn(
            f"Unknown config fields{path_str}: {', '.join(sorted(unknown))}",
            stacklevel=3,
        )
