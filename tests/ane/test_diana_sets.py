"""DIANA I and II under data/ane/: Volume I, Safaitic (Al-Jallad 2026, CC BY-NC-ND 4.0, diana-safaitic/) and
Volume II, Taymanitic (Al-Jallad 2026b, CC BY-NC 4.0, diana2-taymanitic/). Each matches its manifest, carries no
private id or path, and is listed by its folder's index; `aneq diana` reads each volume by headword, root, homograph,
typed sibilant and gloss, and `query_proper_names --source taymanitic` reads Volume II's names and places, never its
dictionary's words.

Runs both tools as a user would (a subprocess from the repo root) on the shipped files. No network.
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

# Volume I: the 1,546 entries and the 282 group and 58 divine names of its two lists (pp. 184-187)
SETS = {"diana-safaitic": (1546 + 282 + 58, "CC BY-NC-ND 4.0"), "diana2-taymanitic": (556, "CC BY-NC 4.0")}
PRIVATE = re.compile(r"src_\d+|sources_database|[a-z]+_(?:repo|root):|/Users/|\.claude")


def run(*args: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    env.pop("KAPHTOR_DATA", None)
    done = subprocess.run([sys.executable, *args], cwd=ROOT, env=env, capture_output=True, text=True, timeout=300)
    assert done.returncode == 0, done.stderr
    return done


def aneq(*args: str) -> list[dict]:
    return json.loads(run("-m", "tools.ane.aneq", "--json", *args).stdout)


def names(*args: str) -> list[list[str]]:
    out = run("tools/ane/query_proper_names.py", *args).stdout
    return [line.split("\t") for line in out.splitlines() if line.strip()]


@pytest.mark.data
@pytest.mark.parametrize("name", sorted(SETS))
def test_records_match_the_manifest_carry_no_private_path_and_are_indexed(name):
    rows, licence = SETS[name]
    folder = ANE_DATA / name
    data = (folder / "records.jsonl").read_bytes()
    meta = json.loads((folder / "MANIFEST.json").read_text(encoding="utf-8"))
    info = meta["outputs"]["records.jsonl"]
    assert (data.count(b"\n"), hashlib.sha256(data).hexdigest()) == (rows, info["sha256"])
    assert info["rows"] == rows and meta["license"] == licence
    for path in (folder / "records.jsonl", folder / "MANIFEST.json"):
        assert not PRIVATE.search(path.read_text(encoding="utf-8")), path.name
    index = (folder / "_index.md").read_text(encoding="utf-8")
    assert "records.jsonl" in index and "MANIFEST.json" in index and licence in index
    assert f"{name}/" in (ANE_DATA / "_index.md").read_text(encoding="utf-8")


@pytest.mark.data
def test_aneq_reads_volume_one():
    assert [r["headword"] for r in aneq("diana", "ʿ-g-z")] == ["ʿgzt", "ʿgz"]                # a root
    assert [r["id"] for r in aneq("diana", "ʿhnt²")] == ["diana:p0044#7"]                    # a homograph as printed
    assert all(r["headword"].endswith("sfr") for r in aneq("diana", "s1fr"))                  # s¹ is printed s
    assert "diana:p0044#2" in {r["id"] for r in aneq("diana", "drought")}                     # a gloss word
    hebrew = aneq("diana", "q-b-r", "--cognate", "Hebrew")
    assert hebrew and all("Hebrew" in r["cognates"] for r in hebrew)
    assert aneq("diana", "ʿ-g-z", "--cognate", "Hebrew") == []                                  # the notes cite none


@pytest.mark.data
def test_aneq_reads_volume_one_s_two_lists():
    allat = aneq("diana", "lt", "--section", "divine_names")                                  # a variant spelling
    assert [(r["id"], r["headword"], r["printed_page"]) for r in allat] == [("diana:p0217#9", "ʾlt", 186)]
    assert len(aneq("diana", "--section", "divine_names", "--limit", "100")) == 58
    groups = aneq("diana", "--section", "group_names", "--limit", "400")
    assert len(groups) == 282 and {r["kind"] for r in groups} == {"name"}
    for volume, section in (("1", "onomasticon"), ("2", "divine_names")):                     # a part the book lacks
        done = subprocess.run([sys.executable, "-m", "tools.ane.aneq", "diana", "--volume", volume, "--section", section],
                              cwd=ROOT, capture_output=True, text=True, timeout=300)
        assert done.returncode == 2 and f"volume {volume} has no {section}" in done.stderr


@pytest.mark.data
def test_aneq_reads_volume_two():
    by_headword = aneq("diana", "nṣr", "--volume", "2")
    assert by_headword[0]["id"] == "diana2:p0043#1" and by_headword[0]["gloss"] == "to keep watch; to guard"
    assert {r["headword"] for r in aneq("diana", "ʿ-z-r", "--volume", "2")} >= {"ʿzr", "ʿzrn"}     # a root
    assert [r["headword"] for r in aneq("diana", "s3fr", "--volume", "2")] == ["s³fr"]          # a typed sibilant
    assert any(r["headword"] == "zy" for r in aneq("diana", "radiance", "--volume", "2"))      # a gloss word
    assert len(aneq("diana", "--volume", "2", "--section", "toponyms")) == 7                   # no query, a section


@pytest.mark.data
def test_the_names_source_reads_names_and_places_only():
    rows = names("ṣlm", "--source", "taymanitic", "--limit", "60")
    assert any(r[1] == "lṣlm" and "Al-Jallad 2026b, 76" in r[3] for r in rows)
    assert names("ddn", "--source", "taymanitic", "--kind", "place")[0][1] == "ddn"
    assert names("ʾḫr", "--source", "taymanitic") == []                                       # a word of the dictionary
