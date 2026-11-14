"""The Palmyra and Hatra sets under data/ane/ (Public Inscriptions from Palmyra with its sigla concordance, Marcato's
Hatra names, the Palmyrene divine-name table): each matches its manifest, carries no private id or path, is listed
by its index, and the clients read it. The clients offer no Palmyra source the repository does not ship.

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

from tools.paths import ANE_DATA

SETS = {"palmyra-public-inscriptions": {"records.jsonl": 1135, "names.jsonl": 5443, "buildings.jsonl": 90,
                                        "concordance.jsonl": 355},
        "hatra-marcato": {"names.jsonl": 407}}
ELEMENTS = ANE_DATA / "palmyrene-theonym-elements"
PRIVATE = re.compile(r"src_\d+|sources_database|[a-z]+_(?:repo|root):|/Users/|\.claude|\"source_id\"")
# Held under terms that do not allow redistribution: indexed privately, cited here by work and page only.
WITHHELD = ("palmyra-igls", "palmyra-gawlikowski", "palmyra-dumesnil", "palmyra-piersimoni")


def run(script: str, *args: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    env.pop("KAPHTOR_DATA", None)
    cmd = ([sys.executable, "-m", "tools.ane.aneq", *args] if script == "aneq"
           else [sys.executable, str(ROOT / "tools/ane" / script), *args])
    return subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True, timeout=300)


def rows(script: str, *args: str) -> list[dict]:
    done = run(script, *args)
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


@pytest.mark.data
@pytest.mark.parametrize("name", sorted(SETS))
def test_every_output_matches_its_manifest_and_carries_no_private_id(name):
    folder = ANE_DATA / name
    outputs = json.loads((folder / "MANIFEST.json").read_text(encoding="utf-8"))["outputs"]
    assert sorted(p.name for p in folder.glob("*.jsonl")) == sorted(outputs) == sorted(SETS[name])
    for file, info in outputs.items():
        data = (folder / file).read_bytes()
        assert (data.count(b"\n"), hashlib.sha256(data).hexdigest()) == (SETS[name][file], info["sha256"]), file
        assert info["rows"] == SETS[name][file]
    for path in [*folder.glob("*.jsonl"), folder / "MANIFEST.json"]:
        text = path.read_text(encoding="utf-8")
        assert not PRIVATE.search(text), (path.name, PRIVATE.search(text).group())


@pytest.mark.data
@pytest.mark.parametrize("folder", [ANE_DATA / name for name in sorted(SETS)] + [ELEMENTS], ids=lambda p: p.name)
def test_the_index_lists_every_file_and_names_a_licence(folder):
    index = (folder / "_index.md").read_text(encoding="utf-8")
    listed = set(re.findall(r"\[\[[^|\]]+/([^/|\]]+)\|", index))
    here = {p.name for p in folder.iterdir() if p.name != "_index.md" and not p.name.startswith(".")}
    assert here <= listed, here - listed
    assert re.search(r"^license: CC BY 4\.0$", index, re.MULTILINE)


@pytest.mark.data
def test_the_element_table_cites_a_page_for_every_form_and_no_private_id():
    text = (ELEMENTS / "elements.json").read_text(encoding="utf-8")
    assert not PRIVATE.search(text)
    table = json.loads(text)
    assert table["license"] == "CC BY 4.0" and len(table["elements"]) == 13
    ids = {e["id"] for e in table["elements"]}
    for e in table["elements"]:
        assert e.get("built_on") in ids | {None}
        forms = [f for script in ("aramaic", "greek", "vocalised") for f in e[script]]
        assert forms and all("p." in f["source"] or f["source"].startswith("dataset") for f in forms), e["id"]
    assert "project's rule" in table["notes"]["bl_rule"]


@pytest.mark.data
def test_aneq_and_the_name_query_read_the_sets():
    pat8 = rows("aneq", "--json", "palmyra", "PAT 8")
    assert [r["id"] for r in pat8] == ["palmyra-pi:pat:0008"]                       # PAT 8, not PAT 80 or 1008
    assert pat8[0]["building_name"] == "Temple of Nabu"
    names = rows("query_proper_names.py", "Bôlḥazaî", "--source", "palmyra-public", "--json")
    assert any(r["id"] == "palmyra-pi:pat:0008#founder:1" and r["entity_scope"] == "catalogue_name" for r in names)
    # the dataset holds vocalised forms only: consonants find nothing
    assert rows("query_proper_names.py", "bwlḥzy", "--source", "palmyra-public", "--exact", "--json") == []
    hatra = rows("query_proper_names.py", "ʿqb", "--source", "hatra-marcato", "--exact", "--json")
    assert [r["id"] for r in hatra] == ["marcato2018:ʿqb"] and hatra[0]["printed_page"] == 109
    ada = rows("query_proper_names.py", "ʾdʾ", "--source", "hatra-marcato", "--exact", "--json")[0]
    assert ada["palmyrene_refs"] == ["Stark 1971, 65", "PAT no. 2761:4"]
    assert ada["other_readings"].startswith("bbrʾ") and ada["analysis"].startswith("Aram. theophoric male name.")
    text = run("query_proper_names.py", "ʾdʾ", "--source", "hatra-marcato", "--exact").stdout
    assert "Marcato 2018 p. 23" in text and "Palm.: Stark 1971, 65; PAT no. 2761:4" in text


@pytest.mark.data
def test_sigla_and_elements():
    found = rows("query_palmyra.py", "sigla", "PAT 0291", "--json")
    assert [r["sigla"] for r in found] == [["PAT 291", "IGLS 56", "CIS 3945"]]
    assert rows("query_palmyra.py", "sigla", "igls 56", "--json") == found            # the same row from either side
    assert run("query_palmyra.py", "sigla", "PAT 29", "--json").stdout.strip() == "[]"  # a number matches whole
    assert run("query_palmyra.py", "sigla", "Inv III, 17").returncode == 2             # the Inventaire is not here
    bol = {r["name"]: r for r in rows("query_palmyra.py", "element", "bol", "--json")}
    assert {"Zabdibôl", "Bôlḥazaî", "Zabdibol"} <= set(bol) and bol["Yarḥibôlâ"]["also"] == ["yarhibol"]
    assert all(r["match_basis"] == "substring" for r in bol.values())
    assert not any("bel" in r["matched"] for r in bol.values())


def test_no_withheld_palmyra_source_is_offered():
    for source in WITHHELD:
        done = run("query_proper_names.py", "zbdbwl", "--source", source)
        assert done.returncode == 2 and "invalid choice" in done.stderr, source
    clients = "".join(p.read_text(encoding="utf-8") for p in (ROOT / "tools/ane").glob("*.py"))
    assert not any(source in clients for source in WITHHELD)
