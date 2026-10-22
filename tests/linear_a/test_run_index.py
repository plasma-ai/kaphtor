"""Every saved run goes through tools.core.run_saver, so the run index stays one shape.

`ventris_runs.py list` and `hypothesis_test.py --decode-run latest` read the index by `run_type`; a row written in
another shape stops them both. The runs land in a tmp folder here, never in the user cache.
"""
import json

import pytest

from tools.core import run_saver
from tools.linear_a.validation import guttural_audit, null_model_audit


@pytest.fixture
def runs(monkeypatch, tmp_path):
    monkeypatch.setattr(run_saver, "RUNS_DIR", tmp_path)
    monkeypatch.setattr(run_saver, "INDEX_PATH", tmp_path / "INDEX.json")
    for module in (null_model_audit, guttural_audit):
        monkeypatch.setattr(module, "RUNS_DIR", tmp_path, raising=False)
    monkeypatch.setattr(run_saver, "_corpus_hash", lambda: "c")
    monkeypatch.setattr(run_saver, "_lexicon_hash", lambda: "l")
    monkeypatch.setattr(run_saver, "_git_state", lambda: {"commit": "-", "dirty": False})
    return tmp_path


def test_a_saved_null_model_audit_leaves_the_index_listable(runs):
    run_dir = null_model_audit.save_run({"mode": "skeleton-permutation", "language": "nws", "iterations": 5,
                                         "thresholds": {0.3: {"z_score": 1.5}}})
    assert [r["run_type"] for r in run_saver.list_runs()] == ["null-model-audit"]
    assert run_saver.list_runs("decode") == []
    output = json.loads((run_dir / "output.json").read_text(encoding="utf-8"))
    assert output["thresholds"]["0.3"]["z_score"] == 1.5
    assert output["iterations"] == 5


def test_a_saved_guttural_audit_leaves_the_index_listable(runs):
    guttural_audit.save_run({"threshold": 0.5, "summary": {}, "critical_entries": [], "skipped_no_root": 0})
    assert [r["run_type"] for r in run_saver.list_runs()] == ["guttural-audit"]
