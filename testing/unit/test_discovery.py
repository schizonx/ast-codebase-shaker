"""Unit tests for shaker.engine.discovery.

Covers file discovery, gitignore handling, exclude patterns, and edge cases.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from shaker.engine.discovery import (
    _load_gitignore,
    _matches_exclude,
    _walk_directory,
    discover_files,
)
from shaker.models import Config


@pytest.fixture
def default_config():
    """A default Config with no custom patterns."""
    return Config()


@pytest.fixture
def make_project(tmp_path):
    """Helper to create a project directory structure.

    Usage:
        root = make_project({
            "src/main.py": "",
            "src/utils.py": "",
            "tests/test_main.py": "",
        })
    """
    def _create(files: dict[str, str]) -> Path:
        for rel, content in files.items():
            fpath = tmp_path / rel
            fpath.parent.mkdir(parents=True, exist_ok=True)
            fpath.write_text(content, encoding="utf-8")
        return tmp_path
    return _create


class TestDiscoverFilesBasic:
    """Tests for basic file discovery."""

    def test_no_py_files_returns_empty(self, make_project, default_config):
        root = make_project({"readme.md": "", "data.json": ""})
        result = discover_files(root, default_config)
        assert result == []

    def test_finds_all_py_files(self, make_project, default_config):
        root = make_project({
            "a.py": "",
            "b.py": "",
            "c.py": "",
        })
        result = discover_files(root, default_config)
        names = [p.name for p in result]
        assert sorted(names) == ["a.py", "b.py", "c.py"]

    def test_finds_py_files_in_subdirs(self, make_project, default_config):
        root = make_project({
            "src/main.py": "",
            "src/utils.py": "",
            "tests/test_main.py": "",
        })
        result = discover_files(root, default_config)
        names = [p.relative_to(root).as_posix() for p in result]
        assert "src/main.py" in names
        assert "src/utils.py" in names
        assert "tests/test_main.py" in names

    def test_result_is_sorted(self, make_project, default_config):
        root = make_project({
            "z.py": "",
            "a.py": "",
            "m.py": "",
        })
        result = discover_files(root, default_config)
        names = [p.name for p in result]
        assert names == ["a.py", "m.py", "z.py"]

    def test_ignores_non_py_files(self, make_project, default_config):
        root = make_project({
            "main.py": "",
            "readme.md": "",
            "data.json": "",
            "config.yaml": "",
        })
        result = discover_files(root, default_config)
        assert len(result) == 1
        assert result[0].name == "main.py"

    def test_nonexistent_path_raises(self, tmp_path, default_config):
        with pytest.raises(FileNotFoundError, match="Path not found"):
            discover_files(tmp_path / "nonexistent", default_config)

    def test_single_py_file_input(self, make_project, default_config):
        root = make_project({"main.py": "x = 1"})
        result = discover_files(root / "main.py", default_config)
        assert len(result) == 1
        assert result[0].name == "main.py"

    def test_single_non_py_file_returns_empty(self, make_project, default_config):
        root = make_project({"readme.md": "hello"})
        result = discover_files(root / "readme.md", default_config)
        assert result == []


class TestDiscoverFilesGitignore:
    """Tests for .gitignore handling."""

    def test_gitignore_excludes_pyc(self, make_project, default_config):
        root = make_project({
            ".gitignore": "*.pyc\n",
            "main.py": "",
            "main.pyc": "",
        })
        result = discover_files(root, default_config)
        names = [p.name for p in result]
        assert "main.py" in names
        assert "main.pyc" not in names

    def test_gitignore_excludes_directory(self, make_project, default_config):
        root = make_project({
            ".gitignore": "tests/\n",
            "src/main.py": "",
            "tests/test_main.py": "",
        })
        result = discover_files(root, default_config)
        names = [p.relative_to(root).as_posix() for p in result]
        assert "src/main.py" in names
        assert not any("tests" in n for n in names)

    def test_gitignore_negation(self, make_project, default_config):
        root = make_project({
            ".gitignore": "*.py\n!important.py\n",
            "main.py": "",
            "important.py": "",
        })
        result = discover_files(root, default_config)
        names = [p.name for p in result]
        assert "important.py" in names
        assert "main.py" not in names

    def test_no_gitignore_loads_all(self, make_project, default_config):
        root = make_project({
            "main.py": "",
            "util.py": "",
        })
        result = discover_files(root, default_config)
        assert len(result) == 2

    def test_gitignore_excludes_pycache(self, make_project, default_config):
        root = make_project({
            ".gitignore": "__pycache__/\n*.pyc\n",
            "main.py": "",
            "__pycache__/main.cpython-314.pyc": "",
        })
        result = discover_files(root, default_config)
        names = [p.name for p in result]
        assert "main.py" in names
        assert not any("__pycache__" in str(p) for p in result)

    def test_gitignore_excludes_dot_git(self, make_project, default_config):
        root = make_project({
            ".gitignore": ".git/\n",
            "main.py": "",
            ".git/config": "",
        })
        result = discover_files(root, default_config)
        assert len(result) == 1
        assert result[0].name == "main.py"

    def test_gitignore_excludes_hidden_dir(self, make_project, default_config):
        root = make_project({
            ".gitignore": ".venv/\n",
            "main.py": "",
            ".venv/lib/python3.14/site-packages/foo.py": "",
        })
        result = discover_files(root, default_config)
        assert len(result) == 1
        assert result[0].name == "main.py"


class TestDiscoverFilesExcludePatterns:
    """Tests for config exclude_patterns."""

    def test_exclude_test_files(self, make_project):
        root = make_project({
            "src/main.py": "",
            "src/auth_test.py": "",
            "src/util_test.py": "",
        })
        config = Config(exclude_patterns=("*_test.py",))
        result = discover_files(root, config)
        names = [p.relative_to(root).as_posix() for p in result]
        assert "src/main.py" in names
        assert len(result) == 1

    def test_exclude_multiple_patterns(self, make_project):
        root = make_project({
            "src/main.py": "",
            "src/migrations/001_init.py": "",
            "src/auth_test.py": "",
        })
        config = Config(exclude_patterns=("*_test.py", "migrations/"))
        result = discover_files(root, config)
        names = [p.relative_to(root).as_posix() for p in result]
        assert "src/main.py" in names
        assert len(result) == 1

    def test_exclude_by_filename_only(self, make_project):
        root = make_project({
            "conftest.py": "",
            "main.py": "",
        })
        config = Config(exclude_patterns=("conftest.py",))
        result = discover_files(root, config)
        names = [p.name for p in result]
        assert "main.py" in names
        assert "conftest.py" not in names

    def test_empty_exclude_patterns(self, make_project, default_config):
        root = make_project({
            "a.py": "",
            "b.py": "",
        })
        result = discover_files(root, default_config)
        assert len(result) == 2


class TestDiscoverFilesAlwaysInclude:
    """Tests for config always_include override."""

    def test_always_include_overrides_gitignore(self, make_project):
        root = make_project({
            ".gitignore": "tests/\n",
            "tests/test_main.py": "",
            "tests/test_utils.py": "",
        })
        config = Config(always_include=("tests/test_main.py",))
        result = discover_files(root, config)
        names = [p.relative_to(root).as_posix() for p in result]
        assert "tests/test_main.py" in names
        assert "tests/test_utils.py" not in names

    def test_always_include_overrides_exclude(self, make_project):
        root = make_project({
            "tests/test_main.py": "",
            "tests/test_utils.py": "",
        })
        config = Config(
            exclude_patterns=("tests/",),
            always_include=("tests/test_main.py",),
        )
        result = discover_files(root, config)
        names = [p.relative_to(root).as_posix() for p in result]
        assert "tests/test_main.py" in names
        assert "tests/test_utils.py" not in names


class TestDiscoverFilesAlwaysExclude:
    """Tests for config always_exclude."""

    def test_always_exclude_removes_file(self, make_project):
        root = make_project({
            "main.py": "",
            "debug.py": "",
        })
        config = Config(always_exclude=("debug.py",))
        result = discover_files(root, config)
        names = [p.name for p in result]
        assert "main.py" in names
        assert "debug.py" not in names

    def test_always_exclude_wins_over_always_include(self, make_project):
        """always_exclude takes precedence over always_include."""
        root = make_project({
            "main.py": "",
        })
        config = Config(
            always_include=("main.py",),
            always_exclude=("main.py",),
        )
        result = discover_files(root, config)
        assert result == []


class TestDiscoverFilesEdgeCases:
    """Tests for edge cases."""

    def test_deep_nesting(self, make_project, default_config):
        """Very deep directory nesting should work."""
        deep = "/".join(f"level{i}" for i in range(15))
        root = make_project({f"{deep}/deep.py": ""})
        result = discover_files(root, default_config)
        assert len(result) == 1
        assert result[0].name == "deep.py"

    def test_mixed_valid_and_invalid(self, make_project, default_config):
        root = make_project({
            "good.py": "",
            "readme.md": "",
            "good2.py": "",
            "data.json": "",
        })
        result = discover_files(root, default_config)
        names = [p.name for p in result]
        assert sorted(names) == ["good.py", "good2.py"]

    def test_empty_directory(self, tmp_path, default_config):
        result = discover_files(tmp_path, default_config)
        assert result == []

    def test_gitignore_with_comments_and_blanks(self, make_project, default_config):
        root = make_project({
            ".gitignore": "# This is a comment\n\n*.pyc\n\n# Another comment\n",
            "main.py": "",
            "main.pyc": "",
        })
        result = discover_files(root, default_config)
        names = [p.name for p in result]
        assert "main.py" in names
        assert "main.pyc" not in names


class TestWalkDirectory:
    """Tests for the internal _walk_directory function."""

    def test_walks_nested_dirs(self, make_project):
        root = make_project({
            "a.py": "",
            "sub/b.py": "",
            "sub/deep/c.py": "",
        })
        result = _walk_directory(root)
        names = {p.name for p in result}
        assert names == {"a.py", "b.py", "c.py"}

    def test_does_not_follow_symlinks(self, tmp_path):
        """Symlinks should not be followed."""
        real_dir = tmp_path / "real"
        real_dir.mkdir()
        (real_dir / "file.py").write_text("")

        link_dir = tmp_path / "link"
        try:
            link_dir.symlink_to(real_dir)
        except OSError:
            pytest.skip("Symlinks not supported on this platform")

        result = _walk_directory(tmp_path)
        names = [p.name for p in result]
        # Should find file.py in real/ but not follow the symlink
        assert "file.py" in names
        # Should not duplicate via symlink
        assert names.count("file.py") == 1


class TestMatchesExclude:
    """Tests for _matches_exclude."""

    def test_matches_wildcard(self):
        assert _matches_exclude(Path("test_main.py"), ["*_test.py"]) is False
        assert _matches_exclude(Path("main_test.py"), ["*_test.py"]) is True

    def test_matches_exact_filename(self):
        assert _matches_exclude(Path("conftest.py"), ["conftest.py"]) is True

    def test_no_match(self):
        assert _matches_exclude(Path("main.py"), ["*_test.py"]) is False

    def test_empty_patterns(self):
        assert _matches_exclude(Path("main.py"), []) is False

    def test_matches_dir_prefix_pattern(self):
        assert _matches_exclude(Path("migrations/001_init.py"), ["migrations/"]) is True


class TestLoadGitignore:
    """Tests for _load_gitignore."""

    def test_loads_valid_gitignore(self, make_project):
        root = make_project({
            ".gitignore": "*.pyc\n__pycache__/\n",
        })
        spec = _load_gitignore(root)
        assert spec is not None
        assert spec.match_file("main.pyc")
        assert spec.match_file("__pycache__/foo.py")
        assert not spec.match_file("main.py")

    def test_returns_none_when_no_gitignore(self, tmp_path):
        spec = _load_gitignore(tmp_path)
        assert spec is None

    def test_handles_empty_gitignore(self, make_project):
        root = make_project({".gitignore": ""})
        spec = _load_gitignore(root)
        assert spec is not None
        assert not spec.match_file("anything.py")
