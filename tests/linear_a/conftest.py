"""Every Shoresh engine a test builds without contexts gets an empty one, and the command's corpus
(tools/linear_a/root_match.py CORPUS) is an empty corpus file, so no unit test reads data/linear-a/corpus.json and no
verdict in one depends on it. A test of the default itself is marked `live_contexts` and keeps it; a test that gives
the command its own corpus patches CORPUS itself.
"""
from __future__ import annotations

import sys

import pytest


@pytest.fixture(scope="session")
def _empty_corpus(tmp_path_factory):
    path = tmp_path_factory.mktemp("corpus") / "corpus.json"
    path.write_text("{}", encoding="utf-8")
    return path


@pytest.fixture(autouse=True)
def _no_live_contexts(request, monkeypatch, _empty_corpus):
    if request.node.get_closest_marker("live_contexts"):
        return
    rm = sys.modules.get("tools.core.root_match")
    if rm is not None:
        from tools.core.semantic_gate import Contexts
        monkeypatch.setattr(rm.Shoresh, "_live_contexts", staticmethod(lambda: Contexts({})))
    cli = sys.modules.get("tools.linear_a.root_match")
    if cli is not None and hasattr(cli, "CORPUS"):
        monkeypatch.setattr(cli, "CORPUS", _empty_corpus)
