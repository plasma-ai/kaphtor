"""Ventris Engine run persistence.

Saves every Ventris run (decode or propagation) to a timestamped directory
under the cache (CACHE/linear-a/runs/, outside the repository) with full
provenance: parameters, corpus hash, git state, and the complete JSON output.
Maintains an INDEX.json manifest for querying.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    from ..paths import CACHE, LINEAR_A_DATA, REPO
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from tools.paths import CACHE, LINEAR_A_DATA, REPO

DATA_DIR = LINEAR_A_DATA
RUNS_DIR = CACHE / "linear-a" / "runs"
INDEX_PATH = RUNS_DIR / "INDEX.json"


def _corpus_hash() -> str:
    corpus_path = DATA_DIR / "corpus.json"
    if not corpus_path.exists():
        return "missing"
    h = hashlib.sha256()
    h.update(corpus_path.read_bytes())
    return h.hexdigest()[:12]


def _lexicon_hash() -> str:
    lex_path = DATA_DIR / "lexicon.json"
    if not lex_path.exists():
        return "missing"
    h = hashlib.sha256()
    h.update(lex_path.read_bytes())
    return h.hexdigest()[:12]


def _git_state() -> dict[str, str]:
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(REPO),
            stderr=subprocess.DEVNULL,
        ).decode().strip()
    except (OSError, subprocess.CalledProcessError):
        commit = "unknown"
    try:
        dirty = subprocess.check_output(
            ["git", "status", "--porcelain"],
            cwd=str(REPO),
            stderr=subprocess.DEVNULL,
        ).decode().strip()
    except (OSError, subprocess.CalledProcessError):
        dirty = ""
    return {"commit": commit, "dirty": bool(dirty)}


def _count_results(data: dict, run_type: str) -> dict[str, int]:
    if run_type == "decode":
        prop = data.get("propagation", {})
        return {
            "known": prop.get("known", 0),
            "new_candidates": prop.get("new_candidates", 0),
            "no_match": prop.get("no_match", 0),
            "cross_validated": len(data.get("cross_validated", [])),
        }
    elif run_type == "propagation":
        results = data.get("results", [])
        known = len([r for r in results if r.get("status") == "known"])
        new = len([r for r in results if r.get("status") != "known"])
        return {
            "known": known,
            "new_candidates": new,
            "total_results": len(results),
        }
    elif run_type == "hypothesis_test":
        results = data.get("results", [])
        verdicts = data.get("verdicts", {})
        return {"candidates_tested": len(results), **verdicts}
    return {}


def save_run(
    run_type: str,
    params: dict[str, Any],
    data: dict,
    label: str | None = None,
) -> Path:
    """Save a Ventris run to RUNS_DIR/<timestamp>-<type>/.

    Returns the path to the saved run directory.
    """
    RUNS_DIR.mkdir(parents=True, exist_ok=True)

    now = datetime.now(UTC)
    ts = now.strftime("%Y%m%d-%H%M%S")
    slug = f"{ts}-{run_type}"
    if label:
        slug += f"-{label}"
    run_dir = RUNS_DIR / slug
    run_dir.mkdir(parents=True, exist_ok=True)

    provenance = {
        "run_id": slug,
        "run_type": run_type,
        "timestamp": now.isoformat(),
        "label": label,
        "parameters": params,
        "corpus_hash": _corpus_hash(),
        "lexicon_hash": _lexicon_hash(),
        "git": _git_state(),
        "python_version": sys.version.split()[0],
        "counts": _count_results(data, run_type),
    }

    (run_dir / "provenance.json").write_text(
        json.dumps(provenance, indent=2, ensure_ascii=False) + "\n"
    )
    (run_dir / "output.json").write_text(
        json.dumps(data, indent=2, ensure_ascii=False, default=str) + "\n"
    )

    _update_index(provenance)

    return run_dir


def _update_index(provenance: dict) -> None:
    index = load_index()
    index["runs"].append({
        "run_id": provenance["run_id"],
        "run_type": provenance["run_type"],
        "timestamp": provenance["timestamp"],
        "label": provenance.get("label"),
        "corpus_hash": provenance["corpus_hash"],
        "counts": provenance["counts"],
        "parameters": provenance["parameters"],
    })
    content = json.dumps(index, indent=2, ensure_ascii=False) + "\n"
    fd, tmp_path = tempfile.mkstemp(dir=str(RUNS_DIR), suffix=".tmp")
    closed = False
    try:
        os.write(fd, content.encode("utf-8"))
        os.close(fd)
        closed = True
        os.replace(tmp_path, str(INDEX_PATH))
    except BaseException:
        if not closed:
            os.close(fd)
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def load_index() -> dict:
    if INDEX_PATH.exists():
        return json.loads(INDEX_PATH.read_text())
    return {"schema_version": 1, "runs": []}


def list_runs(run_type: str | None = None, limit: int = 20) -> list[dict]:
    index = load_index()
    runs = index["runs"]
    if run_type:
        runs = [r for r in runs if r["run_type"] == run_type]
    return sorted(runs, key=lambda r: r["timestamp"], reverse=True)[:limit]


def load_run(run_id: str) -> tuple[dict, dict]:
    """Load provenance and output for a given run_id."""
    run_dir = RUNS_DIR / run_id
    provenance = json.loads((run_dir / "provenance.json").read_text())
    output = json.loads((run_dir / "output.json").read_text())
    return provenance, output


def diff_runs(run_id_a: str, run_id_b: str) -> dict:
    """Compare two propagation runs by their candidate word sets."""
    _, out_a = load_run(run_id_a)
    _, out_b = load_run(run_id_b)

    def _words(data: dict) -> set[str]:
        results = data.get("results", [])
        if not results:
            cv = data.get("cross_validated", [])
            return {c.get("word", "") for c in cv}
        return {r.get("word", "") for r in results if r.get("status") != "known"}

    words_a = _words(out_a)
    words_b = _words(out_b)

    return {
        "only_in_a": sorted(words_a - words_b),
        "only_in_b": sorted(words_b - words_a),
        "shared": sorted(words_a & words_b),
        "a_count": len(words_a),
        "b_count": len(words_b),
        "shared_count": len(words_a & words_b),
    }
