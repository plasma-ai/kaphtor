"""The ANE clients find the data this repository ships, and say so when a dataset is not in the checkout.

Runs the clients as a user would (a subprocess from the repo root) on the shipped PNM v6 tables and place
authorities. No network.
"""
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
ANE = ROOT / "tools" / "ane"
sys.path.insert(0, str(ROOT))

from tools.paths import ANE_DATA, CACHE, SHARE_ALIKE

# Each portal client and the module attribute holding its query cache.
PORTAL_CACHES = {
    "query_deaps": "CACHE", "query_elephantine": "CACHE", "query_rsti": "CACHE", "query_diconab": "CACHE",
    "query_idai_gazetteer": "DEFAULT_CACHE",
}


def load(name: str):
    spec = importlib.util.spec_from_file_location(f"paths_test_{name}", ANE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(script: str, *args: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    env.pop("KAPHTOR_DATA", None)
    return subprocess.run([sys.executable, str(ANE / script), *args], cwd=ROOT, env=env,
                          capture_output=True, text=True, timeout=120)


@pytest.mark.data
def test_resolver_names_the_shipped_folders():
    assert (ANE_DATA / "pnm-v6" / "tables" / "persons.jsonl").is_file()
    assert (ANE_DATA / "place-authorities" / "pleiades_places.jsonl").is_file()
    assert (SHARE_ALIKE / "trismegistos" / "trismegistos_places.jsonl").is_file()


@pytest.mark.data
def test_place_authorities_reach_pleiades():
    done = run("query_place_authorities.py", "Tell el Amarna", "--authority", "pleiades", "--json")
    assert done.returncode == 0, done.stderr
    assert "149576487" in [row["authority_id"] for row in json.loads(done.stdout)]


@pytest.mark.data
def test_place_authorities_reach_every_shipped_authority():
    for authority in ("pleiades", "tm"):
        done = run("query_place_authorities.py", "", "--authority", authority, "--limit", "1", "--json")
        assert done.returncode == 0, (authority, done.stderr)
        assert len(json.loads(done.stdout)) == 1, authority


@pytest.mark.data
def test_held_idai_records_are_named_and_skipped():
    # iDAI.gazetteer publishes no licence for its place data, so its records are held.
    assert not (ANE_DATA / "place-authorities" / "idai_places.jsonl").exists()
    done = run("query_place_authorities.py", "Knossos", "--json")
    assert done.returncode == 0, done.stderr
    assert "idai is not in this checkout" in done.stderr
    datasets = {row["dataset"] for row in json.loads(done.stdout)}
    assert "pleiades" in datasets and "idai" not in datasets


@pytest.mark.data
def test_proper_names_reach_pnm():
    done = run("query_proper_names.py", "PD 769", "--source", "pnm", "--layer", "persons", "--json")
    assert done.returncode == 0, done.stderr
    assert "dd-tw" in [row.get("personal_name") for row in json.loads(done.stdout)]


def test_a_source_not_in_the_checkout_is_named():
    done = run("query_proper_names.py", "Idrimi", "--source", "oracc")
    assert done.returncode != 0
    assert "oracc" in done.stderr and "not in this checkout" in done.stderr


@pytest.mark.data
def test_all_sources_go_on_past_a_missing_one():
    # name_forms reads ORACC beside the shipped layers; ORACC alone is not shipped, so it is named and skipped.
    done = run("query_proper_names.py", "dd-tw", "--layer", "name_forms", "--json")
    assert done.returncode == 0, done.stderr
    assert "dd-tw" in [row.get("personal_name") for row in json.loads(done.stdout)]
    assert "oracc is not in this checkout" in done.stderr


def test_portal_caches_sit_under_the_user_cache_not_the_repo():
    for name, attr in PORTAL_CACHES.items():
        cache = Path(getattr(load(name), attr))
        assert cache.is_relative_to(CACHE), (name, cache)
        assert not cache.resolve().is_relative_to(ROOT.resolve()), (name, cache)


def test_idai_refuses_a_delay_under_one_second(tmp_path):
    # A cached answer for the query, so the client never needs the network, before the fix or after it.
    idai = load("query_idai_gazetteer")
    cached = idai.cache_path(tmp_path, "Knossos")
    cached.write_text(json.dumps({"query": "Knossos", "response": {"total": 0, "result": []}}), encoding="utf-8")
    done = run("query_idai_gazetteer.py", "Knossos", "--cache", str(tmp_path), "--delay", "0.5")
    assert done.returncode == 2 and "--delay" in done.stderr
