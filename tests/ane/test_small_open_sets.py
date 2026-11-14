"""Four small CC BY 4.0 sets under data/ane/ (Ugarit Texts Database metadata, ELiSiR Eblaite lexicon, IG XV 1
Cypriot syllabic, I.Sicily Semitic): each matches its manifest, carries no private id or path, and aneq reads it.

Runs aneq as a user would (a subprocess from the repo root) on the shipped files. No network.
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

from tools.paths import ANE_DATA

SETS = {"ugarit-texts-database": 4582, "elisir-eblaite": 37, "ig-xv-1-cypriot": 311, "isicily-semitic": 73}
PRIVATE = re.compile(r"src_\d+|sources_database|[a-z]+_(?:repo|root):|/Users/|\.claude")


def aneq(*args: str) -> list[dict]:
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    env.pop("KAPHTOR_DATA", None)
    done = subprocess.run([sys.executable, "-m", "tools.ane.aneq", "--json", *args], cwd=ROOT, env=env,
                          capture_output=True, text=True, timeout=300)
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


@pytest.mark.data
@pytest.mark.parametrize("name", sorted(SETS))
def test_records_match_the_manifest_and_carry_no_private_path(name):
    folder = ANE_DATA / name
    data = (folder / "records.jsonl").read_bytes()
    info = json.loads((folder / "MANIFEST.json").read_text(encoding="utf-8"))["outputs"]["records.jsonl"]
    assert (data.count(b"\n"), hashlib.sha256(data).hexdigest()) == (SETS[name], info["sha256"])
    assert info["rows"] == SETS[name]
    for path in (folder / "records.jsonl", folder / "MANIFEST.json"):
        assert not PRIVATE.search(path.read_text(encoding="utf-8")), path.name


@pytest.mark.data
def test_aneq_reads_each_set():
    assert any("16.156" in json.dumps(r, ensure_ascii=False) for r in aneq("ugaritdb", "16.156"))
    assert any(r.get("canonical_label") == "A.MU" for r in aneq("elisir", "father"))
    assert any(r.get("designation") == "IG XV 1, 1" for r in aneq("cypriot", "Amathus"))
    assert aneq("isicily", "Erice")
