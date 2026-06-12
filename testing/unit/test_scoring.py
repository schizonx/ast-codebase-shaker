"""Unit tests for file importance scoring.

Tests StaticScorer, GitScorer, and the score_files interface.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from shaker.engine.scoring import (
    GitScorer,
    StaticScorer,
    score_files,
)
from shaker.models import (
    CallGraph,
    ParsedFile,
    Symbol,
    SymbolType,
)


def _make_symbol(
    name: str, qname: str, file: Path,
    sym_type: SymbolType = SymbolType.FUNCTION,
) -> Symbol:
    return Symbol(
        name=name,
        qualified_name=qname,
        symbol_type=sym_type,
        file=file,
        line_number=1,
    )


def _make_parsed_file(path: str, module: str, symbols: list[Symbol] | None = None) -> ParsedFile:
    return ParsedFile(
        path=Path(path),
        module_name=module,
        symbols=symbols or [],
        source="# source",
    )


def _make_call_graph(symbols: list[str]) -> CallGraph:
    import networkx as nx
    g = nx.DiGraph()
    for s in symbols:
        g.add_node(s)
    sym_table = {}
    for s in symbols:
        parts = s.rsplit(".", 1)
        name = parts[-1] if parts else s
        file = Path("src") / "app.py"
        sym_table[s] = _make_symbol(name, s, file)
    return CallGraph(graph=g, symbol_table=sym_table)


class TestStaticScorer:
    """Tests for the StaticScorer."""

    def test_empty_parsed(self):
        scorer = StaticScorer()
        graph = _make_call_graph([])
        result = scorer.score({}, graph, set())
        assert result == {}

    def test_single_file(self):
        fpath = Path("src/app.py")
        sym = _make_symbol("main", "app.main", fpath)
        parsed = {fpath: _make_parsed_file("src/app.py", "app", [sym])}
        graph = _make_call_graph(["app.main"])
        scorer = StaticScorer()
        result = scorer.score(parsed, graph, set())
        assert fpath in result
        assert result[fpath].score >= 0.0
        assert result[fpath].score <= 1.0

    def test_focus_files_marked(self):
        fpath = Path("src/app.py")
        sym = _make_symbol("main", "app.main", fpath)
        parsed = {fpath: _make_parsed_file("src/app.py", "app", [sym])}
        graph = _make_call_graph(["app.main"])
        scorer = StaticScorer()
        result = scorer.score(parsed, graph, focus_files={fpath})
        assert result[fpath].is_focus is True

    def test_non_focus_files_not_marked(self):
        fpath = Path("src/app.py")
        sym = _make_symbol("main", "app.main", fpath)
        parsed = {fpath: _make_parsed_file("src/app.py", "app", [sym])}
        graph = _make_call_graph(["app.main"])
        scorer = StaticScorer()
        result = scorer.score(parsed, graph, focus_files=set())
        assert result[fpath].is_focus is False

    def test_multiple_files_different_scores(self):
        f1 = Path("src/core.py")
        f2 = Path("src/helper.py")
        s1 = _make_symbol("process", "core.process", f1)
        s2 = _make_symbol("helper_fn", "helper.helper_fn", f2)
        parsed = {
            f1: _make_parsed_file("src/core.py", "core", [s1]),
            f2: _make_parsed_file("src/helper.py", "helper", [s2]),
        }
        graph = _make_call_graph(["core.process", "helper.helper_fn"])
        scorer = StaticScorer()
        result = scorer.score(parsed, graph, set())
        assert len(result) == 2
        assert f1 in result
        assert f2 in result


class TestGitScorer:
    """Tests for the GitScorer."""

    def test_falls_back_without_git(self):
        fpath = Path("src/app.py")
        sym = _make_symbol("main", "app.main", fpath)
        parsed = {fpath: _make_parsed_file("src/app.py", "app", [sym])}
        graph = _make_call_graph(["app.main"])
        scorer = GitScorer()
        with patch("shaker.engine.scoring._count_git_changes", return_value={}):
            result = scorer.score(parsed, graph, set())
        assert fpath in result

    def test_scores_non_negative(self):
        fpath = Path("src/app.py")
        sym = _make_symbol("main", "app.main", fpath)
        parsed = {fpath: _make_parsed_file("src/app.py", "app", [sym])}
        graph = _make_call_graph(["app.main"])
        scorer = GitScorer()
        with patch("shaker.engine.scoring._count_git_changes", return_value={}):
            result = scorer.score(parsed, graph, set())
        assert result[fpath].score >= 0.0


class TestScoreFiles:
    """Tests for the score_files interface function."""

    def test_without_git(self):
        fpath = Path("src/app.py")
        sym = _make_symbol("main", "app.main", fpath)
        parsed = {fpath: _make_parsed_file("src/app.py", "app", [sym])}
        graph = _make_call_graph(["app.main"])
        result = score_files(parsed, graph, set(), use_git=False)
        assert fpath in result

    def test_with_git(self):
        fpath = Path("src/app.py")
        sym = _make_symbol("main", "app.main", fpath)
        parsed = {fpath: _make_parsed_file("src/app.py", "app", [sym])}
        graph = _make_call_graph(["app.main"])
        with patch("shaker.engine.scoring._count_git_changes", return_value={}):
            result = score_files(parsed, graph, set(), use_git=True)
        assert fpath in result

    def test_empty_files(self):
        graph = _make_call_graph([])
        result = score_files({}, graph, set(), use_git=False)
        assert result == {}
