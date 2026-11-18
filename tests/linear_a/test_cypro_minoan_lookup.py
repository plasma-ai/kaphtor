"""The Cypro-Minoan catalogue (data/ane/cypro-minoan/) and its lookup, tools/linear_a/cypro_minoan_lookup.py.

The unit tests point KAPHTOR_DATA at a catalogue written inline; the data tests read the shipped files: no
transcription and no quotation in them, every statement with its work and page, and the counts and checksum the
MANIFEST gives. Nothing here writes to data/.
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
SCRIPT = ROOT / "tools" / "linear_a" / "cypro_minoan_lookup.py"
SHIPPED = ROOT / "data" / "ane" / "cypro-minoan"
FIELDS = ("identity", "museum_no", "editions", "findspot", "date", "dimensions", "object", "document_form", "hand",
          "visual_evidence")


def cite(work, page, **more):
    return {"work": work, "page": page, **more}


def record(siglum, corpus_no, site_code, type_code, **fields):
    base = {
        "record_id": f"cm:{corpus_no}" if corpus_no else f"cm:{siglum}", "siglum": siglum, "corpus_no": corpus_no,
        "hochymin_no": None, "number": "001", "suffix": None, "site_code": site_code, "type_code": type_code,
        "site": None, "site_queried": False, "site_authorities": None, "hochymin_type": None,
        "traditional_subcorpus": None, "inclusion_status": "inscription", "text_status": "edition",
        "edition": {"of_record": "HoChyMin", "valerio_edition_ref": "HoChyMin: 171", "appendix_a_pages": [481],
                    "verified": False, "verification_note": "Not checked against HoChyMin, which is not held.",
                    "edition_note": None},
        "siglum_note": None, "siglum_exception": None, "witness": None, "field_sources": {},
        **{f: [] for f in FIELDS},
    }
    return {**base, **fields}


CATALOGUE = {
    "KITI Avas 001": record(
        "KITI Avas 001", "##130", "KITI", "Avas", site="Kition", hochymin_no=130,
        site_authorities={"match": "city", "pleiades": "707617", "tm": "1095", "note": None},
        hochymin_type={"gloss": "Pottery (complete or fragmentary)", "key_code": "Avas", "material": "clay",
                       "object": "pottery (complete or fragmentary)", "note": None},
        field_sources={"site": [cite("Valério 2016", 36)], "hochymin_type": [cite("Valério 2016", 37)]},
        museum_no=[{"text": "Larnaca District Museum, inv. 1885", "cites": [cite("É. Masson 1978", 49)]}],
        findspot=[{"text": None, "pointer": True, "cites": [cite("Valério 2016", 419)]},
                  {"text": "Site: Kition; Context type: Tomb", "cites": [cite("Donnelly 2021", 294)]}],
        date=[{"text": "1300-1100", "relayed_from": "HoChyMin (Vandenabeele)", "cites": [cite("Valério 2016", 645)]}]),
    "KITI Avas 002": record("KITI Avas 002", "##131", "KITI", "Avas", site="Kition",
                            identity=[{"text": "RS 20.25", "basis": "stated", "cites": [cite("Valério 2016", 353)]}]),
    "KITI Abou 001": record("KITI Abou 001", "##003", "KITI", "Abou", site="Kition"),
    "DHEN Mvas 001": record("DHEN Mvas 001", "ADD##221", "DHEN", "Mvas"),
    "CYPR? Psce 003": record("CYPR? Psce 003", "##195", "CYPR", "Psce"),
    "MI Zb 3": record(
        "MI Zb 3", None, None, None, inclusion_status=None, text_status="no held transcription",
        edition={"of_record": None, "valerio_edition_ref": None, "appendix_a_pages": [], "verified": False,
                 "verification_note": "No transcription is held.", "edition_note": None},
        witness={"edition_held": False, "kind": "post_appendix_find", "what": "A jug handle from Melos.",
                 "cites": [cite("Donnelly 2026", 71)]}),
}


def run(*args: str, data: Path | None = None) -> subprocess.CompletedProcess:
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    env.pop("KAPHTOR_DATA", None)
    if data is not None:
        env["KAPHTOR_DATA"] = str(data)
    return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=ROOT, env=env, capture_output=True, text=True,
                          timeout=120)


@pytest.fixture
def data(tmp_path):
    folder = tmp_path / "ane" / "cypro-minoan"
    folder.mkdir(parents=True)
    (folder / "catalogue.json").write_text(json.dumps(CATALOGUE, ensure_ascii=False), encoding="utf-8")
    return tmp_path


@pytest.mark.parametrize(("query", "siglum"), [
    ("KITI Avas 001", "KITI Avas 001"), ("kiti avas 1", "KITI Avas 001"), ("##130", "KITI Avas 001"),
    ("cm:##130", "KITI Avas 001"), ("130", "KITI Avas 001"), ("inv. 1885", "KITI Avas 001"),
    ("RS 20.25", "KITI Avas 002"), ("ADD##221", "DHEN Mvas 001"), ("##221", "DHEN Mvas 001"),
    ("MI Zb 3", "MI Zb 3"), ("CYPR Psce 3", "CYPR? Psce 003"),
])
def test_doc_finds_a_text_by_siglum_number_museum_or_object_number(data, query, siglum):
    done = run("--doc", query, "--format", "json", data=data)
    assert done.returncode == 0, done.stderr
    assert json.loads(done.stdout)["record"]["siglum"] == siglum


@pytest.mark.parametrize(("query", "siglum"), [
    ("1885", "KITI Avas 001"), ("1193", "ENKO Atab 002"), ("##207A", "ENKO Atab 002"),
    ("ENKO Atab 002a", "ENKO Atab 002"), ("no. 20.01", "ENKO Atab 002"), ("209", "ENKO Atab 004"),
])
def test_doc_finds_a_text_by_a_bare_inventory_number_or_either_side_of_an_identity(tmp_path, query, siglum):
    tablet = record("ENKO Atab 002", "##207", "ENKO", "Atab",
                    identity=[{"text": "ENKO Atab 002a = ##207A = no. 20.01", "basis": "stated",
                               "cites": [cite("Steele (ed.) 2013", 55)]}],
                    museum_no=[{"text": "Musée de Chypre, inv. 1193", "cites": [cite("É. Masson 1974", 26)]}])
    catalogue = {**CATALOGUE, "ENKO Atab 002": tablet, "ENKO Atab 004": record("ENKO Atab 004", "##209", "ENKO", "Atab")}
    folder = tmp_path / "ane" / "cypro-minoan"
    folder.mkdir(parents=True)
    (folder / "catalogue.json").write_text(json.dumps(catalogue, ensure_ascii=False), encoding="utf-8")
    done = run("--doc", query, "--format", "json", data=tmp_path)
    assert done.returncode == 0, done.stderr
    assert json.loads(done.stdout)["record"]["siglum"] == siglum


def test_stats_takes_no_other_query(data):
    done = run("--stats", "--doc", "KITI Avas 001", data=data)
    assert done.returncode == 1
    assert "--stats takes no --doc, --site or --type" in done.stderr


def test_doc_names_no_text_that_does_not_answer(data):
    done = run("--doc", "ENKO Atab 009", data=data)
    assert done.returncode == 1
    assert "No Cypro-Minoan text 'ENKO Atab 009'" in done.stderr


def test_doc_prints_the_edition_the_statements_and_a_pointer_as_a_pointer(data):
    done = run("--doc", "KITI Avas 001", data=data)
    assert done.returncode == 0, done.stderr
    out = done.stdout
    assert "KITI Avas 001  —  ##130 (cm:##130)" in out
    assert "Site: Kition (KITI; Valério 2016, 36)" in out
    assert "Edition: HoChyMin, transcribed in Valério 2016, Appendix A, 481; unverified" in out
    assert "    1300-1100 (relayed from HoChyMin (Vandenabeele))" in out
    assert "    [the source's own words, not reproduced]\n      Valério 2016, 419" in out
    assert "None" not in out
    assert "No transcription ships in this repository" in out


def test_doc_prints_no_edition_line_for_a_witness(data):
    done = run("--doc", "MI Zb 3", data=data)
    assert done.returncode == 0, done.stderr
    assert "Edition:" not in done.stdout
    assert "Witness outside Appendix A (post_appendix_find): A jug handle from Melos." in done.stdout


def test_site_and_type_list_the_texts(data):
    done = run("--site", "kiti", "--type", "Avas", data=data)
    assert done.returncode == 0, done.stderr
    assert done.stdout.startswith("2 texts, site kiti, type Avas")
    assert "KITI Avas 001" in done.stdout and "KITI Avas 002" in done.stdout and "KITI Abou" not in done.stdout
    listed = json.loads(run("--site", "KITI", "--format", "json", data=data).stdout)
    assert [t["siglum"] for t in listed["texts"]] == ["KITI Abou 001", "KITI Avas 001", "KITI Avas 002"]


def test_a_code_no_text_has_and_a_doc_with_a_filter_are_refused(data):
    done = run("--site", "KITI,XXXX", data=data)
    assert done.returncode == 1
    assert "no text has site XXXX" in done.stderr
    done = run("--doc", "KITI Avas 001", "--site", "KITI", data=data)
    assert done.returncode == 1
    assert "takes a text or a filter" in done.stderr


def test_stats_count_the_texts_statements_and_pointers(data):
    done = run("--stats", "--format", "json", data=data)
    assert done.returncode == 0, done.stderr
    stats = json.loads(done.stdout)
    assert (stats["records"], stats["witnesses_outside_appendix_a"]) == (6, 1)
    assert stats["statements"]["findspot"] == 2 and stats["pointers"] == {"findspot": 1}


def test_a_missing_catalogue_is_named(tmp_path):
    done = run("--stats", data=tmp_path)
    assert done.returncode == 2, (done.stdout, done.stderr)
    assert "cypro-minoan/catalogue.json is not in this checkout" in done.stderr


# ---------------------------------------------------------------- the shipped catalogue

def walk(value):
    if isinstance(value, dict):
        for k, v in value.items():
            yield k, v
            yield from walk(v)
    elif isinstance(value, list):
        for v in value:
            yield from walk(v)


@pytest.mark.data
def test_the_catalogue_ships_no_transcription_no_quote_key_and_no_private_id():
    catalogue = json.loads((SHIPPED / "catalogue.json").read_text(encoding="utf-8"))
    keys = {k for k, _ in walk(catalogue)}
    assert not keys & {"lines", "sequences", "transcription", "reported_reading", "sign2vec", "quote"}
    strings = [v for _, v in walk(catalogue) if isinstance(v, str)]
    assert not [v for v in strings if "src_" in v]
    assert not [v for v in strings if re.search("[\U00012F90-\U00012FFF]", v)]  # the Cypro-Minoan block
    assert not [v for v in strings if re.search(r"\b\d{2,3}(?:-\d{2,3}){2,}\b", v)]  # a run of Olivier numbers


@pytest.mark.data
def test_every_statement_names_a_work_the_manifest_lists_and_a_page():
    catalogue = json.loads((SHIPPED / "catalogue.json").read_text(encoding="utf-8"))
    works = json.loads((SHIPPED / "MANIFEST.json").read_text(encoding="utf-8"))["works"]
    bad = []
    for key, r in catalogue.items():
        for field in FIELDS:
            for st in r[field]:
                if not st["cites"] or any(c["work"] not in works or not c.get("page") for c in st["cites"]):
                    bad.append((key, field))
                if bool(st.get("pointer")) != (st["text"] is None):
                    bad.append((key, field, "pointer"))
    assert not bad, bad[:10]


@pytest.mark.data
def test_every_cite_anywhere_names_a_manifest_work_and_every_work_is_cited():
    catalogue = json.loads((SHIPPED / "catalogue.json").read_text(encoding="utf-8"))
    works = json.loads((SHIPPED / "MANIFEST.json").read_text(encoding="utf-8"))["works"]

    def cited(value):
        if isinstance(value, dict):
            return ([value["work"]] if isinstance(value.get("work"), str) else []) + [
                w for v in value.values() for w in cited(v)]
        return [w for v in value for w in cited(v)] if isinstance(value, list) else []
    named = cited(catalogue)
    assert set(named) <= set(works), sorted(set(named) - set(works))
    assert set(works) <= set(named), sorted(set(works) - set(named))


@pytest.mark.data
def test_the_manifest_counts_and_checksum_match_the_catalogue():
    body = (SHIPPED / "catalogue.json").read_bytes()
    manifest = json.loads((SHIPPED / "MANIFEST.json").read_text(encoding="utf-8"))
    catalogue = json.loads(body)
    assert manifest["files"]["catalogue.json"] == {"sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body)}
    assert manifest["records"] == len(catalogue) == 263
    assert manifest["statements"] == {f: sum(len(r[f]) for r in catalogue.values()) for f in FIELDS}
    assert manifest["pointers"] == {f: n for f in FIELDS
                                    if (n := sum(1 for r in catalogue.values() for st in r[f] if st.get("pointer")))}
    assert manifest["license"] == "CC BY 4.0"


@pytest.mark.data
def test_the_lookup_reads_the_shipped_catalogue():
    done = run("--site", "KITI", "--type", "Avas", "--format", "json")
    assert done.returncode == 0, done.stderr
    assert len(json.loads(done.stdout)["texts"]) == 21
    done = run("--doc", "DO 5288")
    assert done.returncode == 0, done.stderr
    assert done.stdout.splitlines()[1].strip().startswith("RASH Atab 004")
