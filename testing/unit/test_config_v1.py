"""Unit tests for new v1 config fields.

Tests loading, validation, and CLI merging of new configuration
options: format, security_scan, security_redact, show_progress,
quiet, enforce_max_tokens, use_git_scoring.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from shaker.infra.config import (
    _validate_bool,
    _validate_format,
    load_config,
    merge_config_with_cli,
)
from shaker.models import Config, OutputFormat


class TestValidateFormat:
    """Tests for _validate_format."""

    def test_markdown(self):
        assert _validate_format("markdown") == OutputFormat.MARKDOWN

    def test_xml(self):
        assert _validate_format("xml") == OutputFormat.XML

    def test_json(self):
        assert _validate_format("json") == OutputFormat.JSON

    def test_plain(self):
        assert _validate_format("plain") == OutputFormat.PLAIN

    def test_case_insensitive(self):
        assert _validate_format("XML") == OutputFormat.XML
        assert _validate_format("Markdown") == OutputFormat.MARKDOWN

    def test_invalid_format(self):
        with pytest.raises(ValueError, match="Invalid format 'yaml'"):
            _validate_format("yaml")

    def test_non_string(self):
        with pytest.raises(ValueError, match="Format must be a string"):
            _validate_format(123)


class TestValidateBool:
    """Tests for _validate_bool."""

    def test_true(self):
        assert _validate_bool(True, "field") is True

    def test_false(self):
        assert _validate_bool(False, "field") is False

    def test_int_fails(self):
        with pytest.raises(ValueError, match="'field' must be a boolean"):
            _validate_bool(1, "field")

    def test_string_fails(self):
        with pytest.raises(ValueError, match="'field' must be a boolean"):
            _validate_bool("true", "field")


class TestLoadConfigNewFields:
    """Tests for loading new config fields from .shakerrc.json."""

    def _write_config(self, tmp_dir: Path, data: dict) -> Path:
        config_path = tmp_dir / ".shakerrc.json"
        config_path.write_text(json.dumps(data), encoding="utf-8")
        return config_path

    def test_defaults_when_not_present(self, tmp_path: Path):
        config_path = self._write_config(tmp_path, {})
        config = load_config(config_path)
        assert config.output_format == OutputFormat.MARKDOWN
        assert config.security_scan is True
        assert config.security_redact is True
        assert config.show_progress is True
        assert config.quiet is False
        assert config.enforce_max_tokens is False
        assert config.use_git_scoring is True

    def test_format_xml(self, tmp_path: Path):
        config_path = self._write_config(tmp_path, {"format": "xml"})
        config = load_config(config_path)
        assert config.output_format == OutputFormat.XML

    def test_format_json(self, tmp_path: Path):
        config_path = self._write_config(tmp_path, {"format": "json"})
        config = load_config(config_path)
        assert config.output_format == OutputFormat.JSON

    def test_format_plain(self, tmp_path: Path):
        config_path = self._write_config(tmp_path, {"format": "plain"})
        config = load_config(config_path)
        assert config.output_format == OutputFormat.PLAIN

    def test_security_scan_disabled(self, tmp_path: Path):
        config_path = self._write_config(
            tmp_path, {"security_scan": False}
        )
        config = load_config(config_path)
        assert config.security_scan is False

    def test_security_redact_disabled(self, tmp_path: Path):
        config_path = self._write_config(
            tmp_path, {"security_redact": False}
        )
        config = load_config(config_path)
        assert config.security_redact is False

    def test_quiet_enabled(self, tmp_path: Path):
        config_path = self._write_config(tmp_path, {"quiet": True})
        config = load_config(config_path)
        assert config.quiet is True

    def test_enforce_max_tokens(self, tmp_path: Path):
        config_path = self._write_config(
            tmp_path, {"enforce_max_tokens": True}
        )
        config = load_config(config_path)
        assert config.enforce_max_tokens is True

    def test_use_git_scoring_disabled(self, tmp_path: Path):
        config_path = self._write_config(
            tmp_path, {"use_git_scoring": False}
        )
        config = load_config(config_path)
        assert config.use_git_scoring is False

    def test_invalid_format_value(self, tmp_path: Path):
        config_path = self._write_config(tmp_path, {"format": "yaml"})
        with pytest.raises(ValueError, match="Invalid format"):
            load_config(config_path)

    def test_invalid_bool_value(self, tmp_path: Path):
        config_path = self._write_config(
            tmp_path, {"quiet": "yes"}
        )
        with pytest.raises(ValueError, match="must be a boolean"):
            load_config(config_path)

    def test_all_new_fields(self, tmp_path: Path):
        config_path = self._write_config(tmp_path, {
            "format": "xml",
            "security_scan": False,
            "security_redact": False,
            "show_progress": False,
            "quiet": True,
            "enforce_max_tokens": True,
            "use_git_scoring": False,
        })
        config = load_config(config_path)
        assert config.output_format == OutputFormat.XML
        assert config.security_scan is False
        assert config.security_redact is False
        assert config.show_progress is False
        assert config.quiet is True
        assert config.enforce_max_tokens is True
        assert config.use_git_scoring is False


class TestMergeConfigWithCli:
    """Tests for merging new CLI arguments with config."""

    def _base_config(self) -> Config:
        return Config()

    def test_format_override(self):
        config = self._base_config()
        result = merge_config_with_cli(config, {"format": "xml"})
        assert result.output_format == OutputFormat.XML

    def test_quiet_override(self):
        config = self._base_config()
        result = merge_config_with_cli(config, {"quiet": True})
        assert result.quiet is True

    def test_no_progress_override(self):
        config = self._base_config()
        result = merge_config_with_cli(config, {"no_progress": True})
        assert result.show_progress is False

    def test_no_security_scan(self):
        config = self._base_config()
        result = merge_config_with_cli(config, {"no_security_scan": True})
        assert result.security_scan is False

    def test_security_warn(self):
        config = self._base_config()
        result = merge_config_with_cli(config, {"security_warn": False})
        assert result.security_redact is True
        result = merge_config_with_cli(config, {"security_warn": True})
        assert result.security_redact is False

    def test_enforce_max_tokens(self):
        config = self._base_config()
        result = merge_config_with_cli(config, {"enforce_max_tokens": True})
        assert result.enforce_max_tokens is True

    def test_no_override_preserves_default(self):
        config = self._base_config()
        result = merge_config_with_cli(config, {})
        assert result.output_format == OutputFormat.MARKDOWN
        assert result.security_scan is True
        assert result.quiet is False
        assert result.show_progress is True
