"""Paradigm B's port (tools/linear_a/validation/paradigm_b.py): the shipped files verify against the freeze, the
ledger ships no replaced string, a changed byte or a credit in the ledger fails verification, and the quick rerun
reproduces the frozen runs from the files as shipped. A maintainer test, given the key (KAPHTOR_PARADIGM_B_KEY),
restores the frozen bytes. The commands run in subprocesses, since the
frozen package imports its modules under top-level names; a test that changes a file does it in a copy under
tmp_path, pointed at by KAPHTOR_DATA, and the rerun builds its package in a temporary folder.
"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tools.linear_a.validation import paradigm_b as pb
from tools.paths import LINEAR_A_DATA

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "tools" / "linear_a" / "validation" / "paradigm_b.py"
HAS_NUMPY = all(importlib.util.find_spec(m) is not None for m in ("numpy", "scipy"))
# the maintainer's key of the strings the port replaced; not shipped
KEY = os.environ.get("KAPHTOR_PARADIGM_B_KEY")
NEEDS_KEY = pytest.mark.skipif(not (KEY and Path(KEY).is_file()),
                               reason="the maintainer's key is not in this checkout (KAPHTOR_PARADIGM_B_KEY)")


def run(*args: str, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, cwd=REPO,
                          env={**os.environ, **(env or {})}, timeout=900)


def test_compare_holds_floats_to_the_tolerance_and_nan_to_nan():
    assert pb.compare({"a": [1.0, float("nan")], "b": "x"}, {"a": [1.0 + 1e-13, float("nan")], "b": "x"})[0] == []
    diffs, gap = pb.compare({"a": 1.0}, {"a": 1.0 + 1e-9})
    assert diffs and gap > pb.TOLERANCE
    assert pb.compare({"a": True}, {"a": 1.0})[0]
    assert pb.compare({"a": [1]}, {"a": [1, 2]})[0]
    assert pb.compare({"a": 1}, {"b": 1})[0]


@pytest.mark.data
def test_verify_passes_on_the_shipped_files():
    result = run("verify")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "verify: PASS" in result.stdout
    assert "data/snapshot/lexicon.json: drifted after the freeze" in result.stdout


@pytest.mark.data
def test_the_ledger_ships_no_replaced_string():
    for row in pb.load_ledger()["files"]:
        for sub in row["substitutions"]:
            assert set(sub) == {"new", "count"}, row["path"]


@pytest.mark.data
def test_verify_names_a_credit_in_the_ledger(tmp_path):
    data = tmp_path / "data"
    shutil.copytree(LINEAR_A_DATA / "paradigm-b", data / "linear-a" / "paradigm-b")
    ledger = data / "linear-a" / "paradigm-b" / "PORT-LEDGER.json"
    raw = json.loads(ledger.read_text(encoding="utf-8"))
    raw["_meta"]["attribution"] = "di Mino & " + "Claude"
    ledger.write_text(json.dumps(raw, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    result = run("verify", env={"KAPHTOR_DATA": str(data)})
    assert result.returncode == 1, result.stdout + result.stderr
    assert "FAIL PORT-LEDGER.json names & Claude" in result.stdout


@pytest.mark.maintainer
@NEEDS_KEY
def test_the_key_restores_every_file_to_the_freeze():
    result = run("verify", "--key", KEY)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "(20 substitutions undone from the key)" in result.stdout


@pytest.mark.data
def test_verify_names_a_changed_byte(tmp_path):
    data = tmp_path / "data"
    shutil.copytree(LINEAR_A_DATA / "paradigm-b", data / "linear-a" / "paradigm-b")
    target = data / "linear-a" / "paradigm-b" / "paradigm" / "luwian.json"
    raw = json.loads(target.read_text(encoding="utf-8"))
    raw["morphemes"][0]["cost"] = 0.5
    target.write_text(json.dumps(raw, ensure_ascii=False, indent=1), encoding="utf-8")
    result = run("verify", env={"KAPHTOR_DATA": str(data)})
    assert result.returncode == 1, result.stdout + result.stderr
    assert "FAIL data/linear-a/paradigm-b/paradigm/luwian.json" in result.stdout


@pytest.mark.data
def test_verify_stops_when_a_shipped_file_is_missing(tmp_path):
    data = tmp_path / "data"
    shutil.copytree(LINEAR_A_DATA / "paradigm-b", data / "linear-a" / "paradigm-b")
    (data / "linear-a" / "paradigm-b" / "formula_family.json").unlink()
    result = run("verify", env={"KAPHTOR_DATA": str(data)})
    assert result.returncode == 2
    assert "formula_family.json is not in this checkout" in result.stderr


@pytest.mark.data
@pytest.mark.skipif(not HAS_NUMPY, reason="needs numpy and scipy (the paradigm extra)")
def test_quick_reproduce_matches_the_frozen_runs():
    result = run("reproduce", "--quick")
    out = result.stdout
    assert result.returncode == 0, out + result.stderr
    assert "rebuilt the frozen package from the files as shipped (14 carry the port's substitutions" in out
    assert "reproduce: PASS" in out
    assert "A_free 0.860  A_cs 0.890  A_nws_floor 0.890  A_luwian 0.110  A_hurrian 0.311  A_egyptian 0.263" in out
    assert "delta 0.579  scorable 57" in out
    assert "G1 pass: D mean 0.292, p95 0.500, r 0/10000" in out
    assert "G2 fail: AUC(delta) 0.904 [0.809, 0.975] 782 pairs; AUC(A_cs) 0.931 [0.844, 0.989]" in out
    assert "['B-NEG-mycenaean_greek-02']" in out
    assert "G3 (descriptive): D2 delta p95 0.187, r 0/10000; D2x2 r 0/10000" in out
    assert out.count("rows 0–199:") == 2 and "DIFFERS" not in out
