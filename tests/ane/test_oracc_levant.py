"""The ORACC Levantine layer (data/share-alike/oracc-levant/): its files match the manifest and carry no private
id, and aneq and query_proper_names read it: a tablet by its find number, its translation, a name occurrence.

Runs the clients as a user would (a subprocess from the repo root) on the shipped files. No network.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.ane.find_numbers import find_number_pattern
from tools.paths import SHARE_ALIKE

LAYER = SHARE_ALIKE / "oracc-levant"
PRIVATE = re.compile(r"src_\d+|sources_database|[a-z]+_(?:repo|root):|/Users/")


def run(*command: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    env.pop("KAPHTOR_DATA", None)
    return subprocess.run([sys.executable, *command], cwd=ROOT, env=env, capture_output=True, text=True, timeout=300)


def aneq(*args: str) -> list[dict]:
    done = run("-m", "tools.ane.aneq", "--json", "cuneiform", *args)
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


@pytest.mark.data
def test_every_output_matches_the_manifest():
    outputs = json.loads((LAYER / "MANIFEST.json").read_text(encoding="utf-8"))["outputs"]
    assert sorted(p.relative_to(LAYER).as_posix() for p in LAYER.rglob("*.jsonl")) == sorted(outputs)
    for name, info in outputs.items():
        data = (LAYER / name).read_bytes()
        assert hashlib.sha256(data).hexdigest() == info["sha256"], name
        assert data.count(b"\n") == info["rows"], name


@pytest.mark.data
def test_no_private_catalogue_id_or_path_and_every_edition_is_share_alike():
    for path in sorted(LAYER.rglob("*.json*")):
        assert not PRIVATE.search(path.read_text(encoding="utf-8")), path.name
    with (LAYER / "oracc_documents.jsonl").open(encoding="utf-8") as f:
        licences = {(row["license"], row["archive_license"]) for row in map(json.loads, f)}
    assert licences == {("CC BY-SA 3.0", "This data is released under the CC0 license")}


def test_a_find_number_is_read_with_padding_and_spacing_free():
    pattern = find_number_pattern("RS 16.156")
    assert all(re.search(pattern, s) for s in ("RS 16.0156", "RS16.156", "PRU 3, 61 (RS 16.156)"))
    assert not re.search(pattern, "RS 16.1560") and not re.search(find_number_pattern("EA 34"), "EA 340")
    assert find_number_pattern("marziḥu") is None


@pytest.mark.data
def test_a_tablet_is_found_by_its_find_number_however_it_is_typed():
    for typed in ("RS 16.156", "RS 16.0156", "RS16.156"):
        assert "P503399" in {r["canonical_id"] for r in aneq(typed)}, typed
    assert not any("EA 340" in r["designation"] for r in aneq("EA 34"))


@pytest.mark.data
def test_the_translation_of_a_found_tablet_is_shown_unit_by_unit():
    units = aneq("RS 16.156", "--translation")
    assert units[0]["translation"].startswith("As of today, before Niqmaddu")
    assert {u["project"] for u in units} == {"aemw/ugarit"} and units[0]["url"].endswith("/aemw/ugarit/P503399/html")


@pytest.mark.data
def test_a_name_occurrence_of_the_layer_is_found():
    done = run("tools/ane/query_proper_names.py", "Niqmaddu", "--source", "oracc-levant", "--json", "--limit", "5")
    assert done.returncode == 0, done.stderr
    rows = json.loads(done.stdout)
    assert rows and all(r["dataset"] == "oracc-levant" and r["project"].startswith("aemw/") for r in rows)
