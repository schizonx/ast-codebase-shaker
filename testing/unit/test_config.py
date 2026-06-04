"""Unit tests for shaker.infra.config.

Covers config loading, validation, merging, autodiscovery, and error handling.
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path

import pytest

from shaker.infra.config import (
    _find_config_file,
    _validate_max_tokens,
    _validate_mode,
    _validate_patterns,
    load_config,
    merge_config_with_cli,
)
from shaker.models import CompressionMode, Config


@pytest.fixture
def tmp_config(tmp_path):
    """Helper to create a .shakerrc.json with given content."""
    def _write(data: dict) -> Path:
        path = tmp_path / ".shakerrc.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        return path
    return _write


class TestLoadConfigNoFile:
    """Tests for load_config when no config file exists."""

    def test_no_config_returns_defaults(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        config = load_config()
        assert config == Config()

    def test_no_config_has_no_config_path(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        config = load_config()
        assert config.config_path is None


class TestLoadConfigExplicitPath:
    """Tests for load_config with an explicit path."""

    def test_loads_valid_config(self, tmp_config):
        path = tmp_config({"mode": "full", "max_tokens": 4000})
        config = load_config(path)
        assert config.default_mode is CompressionMode.FULL
        assert config.max_tokens == 4000

    def test_missing_file_raises_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="Config file not found"):
            load_config(tmp_path / "nonexistent.json")

    def test_invalid_json_raises_value_error(self, tmp_path):
        bad = tmp_path / ".shakerrc.json"
        bad.write_text("{not json}", encoding="utf-8")
        with pytest.raises(ValueError, match="Invalid JSON"):
            load_config(bad)

    def test_non_dict_json_raises_value_error(self, tmp_path):
        bad = tmp_path / ".shakerrc.json"
        bad.write_text("[1, 2, 3]", encoding="utf-8")
        with pytest.raises(ValueError, match="must contain a JSON object"):
            load_config(bad)


class TestLoadConfigFields:
    """Tests for individual config field loading."""

    def test_mode_full(self, tmp_config):
        config = load_config(tmp_config({"mode": "full"}))
        assert config.default_mode is CompressionMode.FULL

    def test_mode_signatures(self, tmp_config):
        config = load_config(tmp_config({"mode": "signatures"}))
        assert config.default_mode is CompressionMode.SIGNATURES

    def test_mode_strip(self, tmp_config):
        config = load_config(tmp_config({"mode": "strip"}))
        assert config.default_mode is CompressionMode.STRIP

    def test_mode_case_insensitive(self, tmp_config):
        config = load_config(tmp_config({"mode": "FULL"}))
        assert config.default_mode is CompressionMode.FULL

    def test_exclude_patterns(self, tmp_config):
        config = load_config(tmp_config({"exclude": ["*_test.py", "migrations/"]}))
        assert config.exclude_patterns == ("*_test.py", "migrations/")

    def test_max_tokens(self, tmp_config):
        config = load_config(tmp_config({"max_tokens": 8000}))
        assert config.max_tokens == 8000

    def test_always_include(self, tmp_config):
        config = load_config(tmp_config({"always_include": ["src/models/"]}))
        assert config.always_include == ("src/models/",)

    def test_always_exclude(self, tmp_config):
        config = load_config(tmp_config({"always_exclude": ["src/legacy/"]}))
        assert config.always_exclude == ("src/legacy/",)

    def test_partial_config_fills_defaults(self, tmp_config):
        config = load_config(tmp_config({"mode": "strip"}))
        assert config.default_mode is CompressionMode.STRIP
        assert config.exclude_patterns == ()
        assert config.max_tokens is None
        assert config.always_include == ()
        assert config.always_exclude == ()

    def test_all_fields_loaded(self, tmp_config):
        data = {
            "mode": "full",
            "exclude": ["*_test.py"],
            "max_tokens": 4000,
            "always_include": ["src/core/"],
            "always_exclude": ["src/legacy/"],
        }
        config = load_config(tmp_config(data))
        assert config.default_mode is CompressionMode.FULL
        assert config.exclude_patterns == ("*_test.py",)
        assert config.max_tokens == 4000
        assert config.always_include == ("src/core/",)
        assert config.always_exclude == ("src/legacy/",)

    def test_config_path_set(self, tmp_config):
        path = tmp_config({"mode": "full"})
        config = load_config(path)
        assert config.config_path == path


class TestLoadConfigValidation:
    """Tests for config validation errors."""

    def test_invalid_mode_raises_value_error(self, tmp_config):
        with pytest.raises(ValueError, match="Invalid mode 'turbo'"):
            load_config(tmp_config({"mode": "turbo"}))

    def test_non_string_mode_raises_value_error(self, tmp_config):
        with pytest.raises(ValueError, match="Mode must be a string"):
            load_config(tmp_config({"mode": 42}))

    def test_negative_max_tokens_raises_value_error(self, tmp_config):
        with pytest.raises(ValueError, match="positive integer"):
            load_config(tmp_config({"max_tokens": -1}))

    def test_zero_max_tokens_raises_value_error(self, tmp_config):
        with pytest.raises(ValueError, match="positive integer"):
            load_config(tmp_config({"max_tokens": 0}))

    def test_non_int_max_tokens_raises_value_error(self, tmp_config):
        with pytest.raises(ValueError, match="must be an integer"):
            load_config(tmp_config({"max_tokens": "lots"}))

    def test_bool_max_tokens_raises_value_error(self, tmp_config):
        with pytest.raises(ValueError, match="must be an integer"):
            load_config(tmp_config({"max_tokens": True}))

    def test_non_list_exclude_raises_value_error(self, tmp_config):
        with pytest.raises(ValueError, match="'exclude' must be a list"):
            load_config(tmp_config({"exclude": "*.py"}))

    def test_non_string_in_exclude_raises_value_error(self, tmp_config):
        with pytest.raises(ValueError, match="'exclude\\[0\\]' must be a string"):
            load_config(tmp_config({"exclude": [42]}))

    def test_non_list_always_include_raises_value_error(self, tmp_config):
        with pytest.raises(ValueError, match="'always_include' must be a list"):
            load_config(tmp_config({"always_include": "src/"}))


class TestLoadConfigUnknownFields:
    """Tests for unknown field warnings."""

    def test_unknown_field_emits_warning(self, tmp_config):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            load_config(tmp_config({"mode": "full", "unknown_key": 1}))
            assert len(w) == 1
            assert "unknown_key" in str(w[0].message)

    def test_multiple_unknown_fields_in_warning(self, tmp_config):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            load_config(tmp_config({"foo": 1, "bar": 2}))
            assert len(w) == 1
            msg = str(w[0].message)
            assert "bar" in msg
            assert "foo" in msg

    def test_known_fields_no_warning(self, tmp_config):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            load_config(tmp_config({"mode": "full", "max_tokens": 1000}))
            assert len(w) == 0


class TestFindConfigFile:
    """Tests for config file autodiscovery."""

    def test_finds_in_current_dir(self, tmp_path, monkeypatch):
        config_file = tmp_path / ".shakerrc.json"
        config_file.write_text("{}", encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        found = _find_config_file(Path.cwd())
        assert found == config_file

    def test_finds_in_parent_dir(self, tmp_path, monkeypatch):
        config_file = tmp_path / ".shakerrc.json"
        config_file.write_text("{}", encoding="utf-8")
        child = tmp_path / "sub" / "deep"
        child.mkdir(parents=True)
        monkeypatch.chdir(child)
        found = _find_config_file(Path.cwd())
        assert found == config_file

    def test_returns_none_when_not_found(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        found = _find_config_file(Path.cwd())
        assert found is None

    def test_closest_ancestor_wins(self, tmp_path, monkeypatch):
        root_config = tmp_path / ".shakerrc.json"
        root_config.write_text(json.dumps({"mode": "full"}), encoding="utf-8")
        child = tmp_path / "sub"
        child.mkdir()
        child_config = child / ".shakerrc.json"
        child_config.write_text(json.dumps({"mode": "strip"}), encoding="utf-8")
        monkeypatch.chdir(child)
        found = _find_config_file(Path.cwd())
        assert found == child_config


class TestMergeConfigWithCli:
    """Tests for CLI argument merging."""

    def test_cli_mode_overrides_config(self, tmp_config):
        config = load_config(tmp_config({"mode": "full"}))
        merged = merge_config_with_cli(config, {"mode": "strip"})
        assert merged.default_mode is CompressionMode.STRIP

    def test_cli_none_does_not_override(self, tmp_config):
        config = load_config(tmp_config({"mode": "full"}))
        merged = merge_config_with_cli(config, {"mode": None})
        assert merged.default_mode is CompressionMode.FULL

    def test_cli_exclude_overrides(self, tmp_config):
        config = load_config(tmp_config({"exclude": ["*_test.py"]}))
        merged = merge_config_with_cli(config, {"exclude": ["migrations/"]})
        assert merged.exclude_patterns == ("migrations/",)

    def test_cli_max_tokens_overrides(self, tmp_config):
        config = load_config(tmp_config({"max_tokens": 4000}))
        merged = merge_config_with_cli(config, {"max_tokens": 8000})
        assert merged.max_tokens == 8000

    def test_cli_always_include_overrides(self, tmp_config):
        config = load_config(tmp_config({"always_include": ["src/core/"]}))
        merged = merge_config_with_cli(config, {"always_include": ["src/models/"]})
        assert merged.always_include == ("src/models/",)

    def test_cli_always_exclude_overrides(self, tmp_config):
        config = load_config(tmp_config({"always_exclude": ["src/legacy/"]}))
        merged = merge_config_with_cli(config, {"always_exclude": ["tests/"]})
        assert merged.always_exclude == ("tests/",)

    def test_empty_cli_args_preserves_config(self, tmp_config):
        config = load_config(tmp_config({
            "mode": "strip",
            "exclude": ["*_test.py"],
            "max_tokens": 4000,
        }))
        merged = merge_config_with_cli(config, {})
        assert merged.default_mode is CompressionMode.STRIP
        assert merged.exclude_patterns == ("*_test.py",)
        assert merged.max_tokens == 4000

    def test_config_path_preserved_after_merge(self, tmp_config):
        path = tmp_config({"mode": "full"})
        config = load_config(path)
        merged = merge_config_with_cli(config, {"mode": "strip"})
        assert merged.config_path == path


class TestValidateMode:
    """Direct tests for _validate_mode."""

    def test_valid_modes(self):
        assert _validate_mode("full") is CompressionMode.FULL
        assert _validate_mode("signatures") is CompressionMode.SIGNATURES
        assert _validate_mode("strip") is CompressionMode.STRIP

    def test_case_insensitive(self):
        assert _validate_mode("FULL") is CompressionMode.FULL
        assert _validate_mode("Signatures") is CompressionMode.SIGNATURES

    def test_invalid_mode(self):
        with pytest.raises(ValueError, match="Invalid mode"):
            _validate_mode("invalid")

    def test_non_string_mode(self):
        with pytest.raises(ValueError, match="Mode must be a string"):
            _validate_mode(123)


class TestValidatePatterns:
    """Direct tests for _validate_patterns."""

    def test_valid_patterns(self):
        result = _validate_patterns(["*_test.py", "migrations/"])
        assert result == ("*_test.py", "migrations/")

    def test_empty_list(self):
        result = _validate_patterns([])
        assert result == ()

    def test_non_list_raises(self):
        with pytest.raises(ValueError, match="must be a list"):
            _validate_patterns("*.py")

    def test_non_string_item_raises(self):
        with pytest.raises(ValueError, match="must be a string"):
            _validate_patterns([123])


class TestValidateMaxTokens:
    """Direct tests for _validate_max_tokens."""

    def test_valid_positive(self):
        assert _validate_max_tokens(1000) == 1000

    def test_zero_raises(self):
        with pytest.raises(ValueError, match="positive integer"):
            _validate_max_tokens(0)

    def test_negative_raises(self):
        with pytest.raises(ValueError, match="positive integer"):
            _validate_max_tokens(-5)

    def test_non_int_raises(self):
        with pytest.raises(ValueError, match="must be an integer"):
            _validate_max_tokens("1000")

    def test_bool_raises(self):
        with pytest.raises(ValueError, match="must be an integer"):
            _validate_max_tokens(True)
