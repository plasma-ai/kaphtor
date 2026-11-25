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


DATING = ("period_code", "period_label", "date_range_bce", "date_midpoint_bce", "date_certainty", "dating_basis")
DERIVED = (*DATING, "dating_status", "conflicts", "script", "subcorpus")
UNDATED = {**{f: None for f in DATING}, "dating_status": "UNDATED", "conflicts": [], "script": "Cypro-Minoan",
           "subcorpus": None, "null_reasons": {**{f: "no held source dates it" for f in DATING},
                                               "subcorpus": "no held source assigns it"}}
NO_YEARS = "Tables I.1 and I.2 (Valério 2016, 39) give no years for LC IIIC"


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
        **{f: [] for f in FIELDS}, **UNDATED,
    }
    return {**base, **fields}


CATALOGUE = {
    "KITI Avas 001": record(
        "KITI Avas 001", "##130", "KITI", "Avas", site="Kition", hochymin_no=130,
        site_authorities={"match": "city", "pleiades": "707617", "tm": "1095", "note": None},
        hochymin_type={"gloss": "Pottery (complete or fragmentary)", "key_code": "Avas", "material": "clay",
                       "object": "pottery (complete or fragmentary)", "note": None},
        field_sources={"site": [cite("Valério 2016", 36)], "hochymin_type": [cite("Valério 2016", 37)],
                       "script": [cite("Valério 2016", 481)],
                       "subcorpus": [cite("Valério 2016", 452), cite("Valério 2016", 451)]},
        museum_no=[{"text": "Larnaca District Museum, inv. 1885", "cites": [cite("É. Masson 1978", 49)]}],
        findspot=[{"text": None, "pointer": True, "cites": [cite("Valério 2016", 419)]},
                  {"text": "Site: Kition; Context type: Tomb", "cites": [cite("Donnelly 2021", 294)]}],
        date=[{"text": "1300-1100", "relayed_from": "HoChyMin (Vandenabeele)", "cites": [cite("Valério 2016", 645)]}],
        period_code="LC IIC–IIIA", period_label="Late Cypriot IIC–IIIA", date_range_bce=[1320, 1100],
        date_midpoint_bce=1210, date_certainty="LOW", dating_status="CONFLICT",
        dating_basis={"source": "HoChyMin (Vandenabeele)", "text": "1300-1100", "cites": [cite("Valério 2016", 645)]},
        conflicts=[{"source": "Donnelly 2021", "text": None, "pointer": True, "cites": [cite("Donnelly 2021", 294)],
                    "note": "Said of the tomb as a whole.", "period_code": "LC IIIB", "date_range_bce": [1100, 1050],
                    "relation": "disjoint"}],
        subcorpus="CM 1", null_reasons={}),
    "KITI Avas 002": record("KITI Avas 002", "##131", "KITI", "Avas", site="Kition",
                            identity=[{"text": "RS 20.25", "basis": "stated", "cites": [cite("Valério 2016", 353)]}],
                            field_sources={"script": [cite("Valério 2016", 500,
                                                           note="allows that the script may be Cypro-Greek")]}),
    "KITI Abou 001": record(
        "KITI Abou 001", "##003", "KITI", "Abou", site="Kition", period_code="LC IIIC",
        period_label="Late Cypriot IIIC", date_certainty="MEDIUM", dating_status="AGREE",
        dating_basis={"source": "CMI II (Ferrara)", "text": "LC IIIC", "cites": [cite("Valério 2016", 641)],
                      "note": "Appendix C's row for the ball."},
        null_reasons={"date_range_bce": NO_YEARS, "date_midpoint_bce": NO_YEARS,
                      "subcorpus": "no held source assigns it"}),
    "DHEN Mvas 001": record("DHEN Mvas 001", "ADD##221", "DHEN", "Mvas"),
    "ENKO Abou 016bis": record("ENKO Abou 016bis", "##019", "ENKO", "Abou", inclusion_status="unepigraphic",
                               script=None, null_reasons={**UNDATED["null_reasons"],
                                                          "script": "unepigraphic (Valério 2016, 455)"}),
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
    assert (stats["records"], stats["witnesses_outside_appendix_a"]) == (7, 1)
    assert stats["statements"]["findspot"] == 2 and stats["pointers"] == {"findspot": 1}


def test_doc_prints_the_date_its_basis_and_each_conflict_a_pointer_as_a_pointer(data):
    out = run("--doc", "KITI Avas 001", data=data).stdout
    assert ("  Date: LC IIC–IIIA (Late Cypriot IIC–IIIA), 1320–1100 BCE (Valério 2016, 39); CONFLICT, certainty LOW\n"
            "    basis: HoChyMin (Vandenabeele), \"1300-1100\" (Valério 2016, 645)\n"
            "    conflict (disjoint): Donnelly 2021, [the source's own words, not reproduced], LC IIIB, 1100–1050 BCE\n"
            "      Donnelly 2021, 294\n      Said of the tomb as a whole.\n") in out
    assert "  Script: Cypro-Minoan (Valério 2016, 481)\n  Subcorpus: CM 1 (Valério 2016, 452; Valério 2016, 451)\n" in out
    assert out.index("Type:") < out.index("Date:") < out.index("Script:") < out.index("Subcorpus:") < out.index("Edition:")


def test_doc_prints_a_null_field_with_its_reason_and_a_cites_note(data):
    out = run("--doc", "KITI Avas 002", data=data).stdout
    assert "  Date: none: no held source dates it\n" in out
    assert "  Script: Cypro-Minoan (Valério 2016, 500)\n      Valério 2016, 500: allows that the script may be " \
           "Cypro-Greek\n" in out
    assert "  Subcorpus: none: no held source assigns it\n" in out
    assert "  Script: none: unepigraphic (Valério 2016, 455)\n" in run("--doc", "ENKO Abou 016bis", data=data).stdout
    out = run("--doc", "##003", data=data).stdout
    assert f"  Date: LC IIIC (Late Cypriot IIIC), no years: {NO_YEARS}; AGREE, certainty MEDIUM\n" \
           "    basis: CMI II (Ferrara), \"LC IIIC\" (Valério 2016, 641)\n      Appendix C's row for the ball.\n" in out
    assert "  Script: Cypro-Minoan\n" in out                              # no cites, no empty parentheses


def test_the_list_shows_each_texts_period_and_its_json_the_date_and_script(data):
    out = run("--site", "KITI", data=data).stdout
    assert re.search(r"KITI Avas 001 +##130 +\S.* +LC IIC–IIIA +inscription", out)
    assert re.search(r"KITI Avas 002 +##131 +undated +inscription", out)
    texts = json.loads(run("--site", "KITI", "--format", "json", data=data).stdout)["texts"]
    row = next(t for t in texts if t["siglum"] == "KITI Avas 001")
    assert {f: row[f] for f in ("period_code", "date_range_bce", "dating_status", "script", "subcorpus")} == \
        {"period_code": "LC IIC–IIIA", "date_range_bce": [1320, 1100], "dating_status": "CONFLICT",
         "script": "Cypro-Minoan", "subcorpus": "CM 1"}


def test_stats_count_the_date_and_script_fields(data):
    counts = json.loads(run("--stats", "--format", "json", data=data).stdout)["dating_and_script"]
    assert counts["dating_status"] == {"AGREE": 1, "CONFLICT": 1, "UNDATED": 5}
    assert counts["script"] == {"Cypro-Minoan": 6, "null": 1}
    assert counts["subcorpus"] == {"CM 1": 1, "null": 6}


def test_a_missing_catalogue_is_named(tmp_path):
    done = run("--stats", data=tmp_path)
    assert done.returncode == 2, (done.stdout, done.stderr)
    assert "cypro-minoan/catalogue.json is not in this checkout" in done.stderr


# ---------------------------------------------------------------- the translations

def word(line, page, group, reading, values, gloss=None, confidence="CANDIDATE", text="corpus", **more):
    return {"line": line, "page": page, "text": text, "cypro_minoan": group, "reading": reading,
            "reading_type": None, "gloss": gloss, "values": values, "confidence": confidence, "rivals": [],
            "note": None, **more}


TRANSLATIONS = {
    "translations": {"KITI Avas 002": {
        "record_id": "cm:##131", "source": "di Mino", "confidence": "CANDIDATE", "status": "incomplete",
        "translation": "Kôṯar-ʾabī, son.", "notes": "A list of names.\n\nOne group stays unread.",
        "words": [
            word("A.01", 547, "021-082-075-051", "Kôṯar-ʾabī", ["ko", "sa", "ra", "pi"],
                 gloss="personal name 'Kothar is my father'", confidence="PROBABLE", note="Saporetti's reading.",
                 rivals=[{"proposer": "É. Masson", "reading": "?-ḫi-ra-bi", "work": "É. Masson 1974", "page": 43,
                          "gloss": "a name ending in rb 'great'"}]),
            word("A.02", 551, "051-028", "binu", ["pi", None], gloss="son", text="emended"),
            word("A.06", 548, None, None, [], confidence=None, reading_type="UNRESOLVED", note="No reading.",
                 rivals=[{"proposer": "Valério", "work": "Valério 2016", "page": 548, "gloss": "a name"}]),
        ]}},
    "sign_values": {"021": {"value": "ko", "tier": "PROBABLE", "evidence": "ko with most proposers."}},
}


@pytest.fixture
def translated(data):
    (data / "ane" / "cypro-minoan" / "translations.json").write_text(json.dumps(TRANSLATIONS, ensure_ascii=False),
                                                                    encoding="utf-8")
    return data


def test_doc_prints_the_translation_word_by_word_with_its_line_and_page(translated):
    done = run("--doc", "KITI Avas 002", data=translated)
    assert done.returncode == 0, done.stderr
    lines = done.stdout.splitlines()
    head = lines.index("  Translation: di Mino, CANDIDATE, incomplete; 3 words")
    assert lines[head + 1] == "    Kôṯar-ʾabī, son."
    assert lines[head + 3:head + 10] == [
        "    A.01  p. 547  021-082-075-051  ko-sa-ra-pi  Kôṯar-ʾabī  personal name 'Kothar is my father'  PROBABLE",
        "      rival: É. Masson, ?-ḫi-ra-bi, a name ending in rb 'great' (É. Masson 1974, 43)",
        "      Saporetti's reading.",
        "    A.02  p. 551  051-028  pi-?  binu  'son'  CANDIDATE, emended text",
        "    A.06  p. 548  [group not reproduced]  unresolved",
        "      rival: Valério, a name (Valério 2016, 548)",
        "      No reading.",
    ]
    assert lines[head + 10:head + 14] == ["", "    Notes:", "    A list of names.", "    One group stays unread."]
    assert head < lines.index("  Metadata, each statement with its source")
    assert "No transcription ships in this repository beyond the sign groups of the words read" in done.stdout


def test_doc_json_carries_the_translation_or_null(translated):
    read = json.loads(run("--doc", "KITI Avas 002", "--format", "json", data=translated).stdout)
    assert [w["reading"] for w in read["translation"]["words"]] == ["Kôṯar-ʾabī", "binu", None]
    assert json.loads(run("--doc", "KITI Avas 001", "--format", "json", data=translated).stdout)["translation"] is None


def test_a_text_without_a_translation_keeps_the_plain_closing_line(translated):
    out = run("--doc", "KITI Avas 001", data=translated).stdout
    assert "Translation:" not in out
    assert "No transcription ships in this repository; the edition line names" in out


def test_stats_count_the_translations(translated):
    stats = json.loads(run("--stats", "--format", "json", data=translated).stdout)
    assert stats["translations"] == {"texts": 1, "complete": 0, "incomplete": 1, "words": 3}


def test_stats_count_an_incomplete_text_by_its_status(data):
    """A text with no translation and no status is neither complete nor incomplete, as the skill counts."""
    blank = {**TRANSLATIONS["translations"]["KITI Avas 002"], "record_id": "cm:##130", "status": None,
             "translation": ""}
    both = {**TRANSLATIONS, "translations": {**TRANSLATIONS["translations"], "KITI Avas 001": blank}}
    (data / "ane" / "cypro-minoan" / "translations.json").write_text(json.dumps(both, ensure_ascii=False),
                                                                    encoding="utf-8")
    stats = json.loads(run("--stats", "--format", "json", data=data).stdout)
    assert stats["translations"] == {"texts": 2, "complete": 0, "incomplete": 1, "words": 6}


def test_the_lookup_works_without_the_translations_file(data):
    done = run("--doc", "KITI Avas 002", data=data)
    assert done.returncode == 0, done.stderr
    assert "Translation:" not in done.stdout
    stats = json.loads(run("--stats", "--format", "json", data=data).stdout)
    assert stats["translations"] == {"texts": 0, "complete": 0, "incomplete": 0, "words": 0}


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


PROSE = {"translation", "notes", "note", "gloss", "evidence"}
# a work named with its year in the translations' prose ("Valério 2016", "Steele (ed.) 2013"), or DULAT
CITED = re.compile(r"(?:[A-ZÉ]\. )?[A-ZÉ][\w'-]+(?: \(ed\.\))?(?: et al\.)?(?: and [A-ZÉ][\w'-]+)? \d{4}[a-z]?\b"
                   r"|\bDULAT\b")


@pytest.mark.data
def test_every_cite_anywhere_names_a_manifest_work_and_every_work_is_cited():
    catalogue = json.loads((SHIPPED / "catalogue.json").read_text(encoding="utf-8"))
    translations = json.loads((SHIPPED / "translations.json").read_text(encoding="utf-8"))
    extra = [json.loads((SHIPPED / name).read_text(encoding="utf-8"))
             for name in ("grammar_hypotheses.json", "lexicon.json", "onomasticon.json", "grid.json")
             if (SHIPPED / name).is_file()]
    works = json.loads((SHIPPED / "MANIFEST.json").read_text(encoding="utf-8"))["works"]

    def cited(value):
        if isinstance(value, dict):
            return ([value["work"]] if isinstance(value.get("work"), str) else []) + [
                w for v in value.values() for w in cited(v)]
        return [w for v in value for w in cited(v)] if isinstance(value, list) else []
    named = cited(catalogue) + cited(translations) + [w for obj in extra for w in cited(obj)]
    named += [w for k, v in walk(translations) if k in PROSE and isinstance(v, str) for w in CITED.findall(v)]
    for obj in extra:
        for _, v in walk(obj):
            if isinstance(v, str):
                for w in CITED.findall(v):
                    if w not in works and " and " in w and w.split(" and ", 1)[1] in works:
                        w = w.split(" and ", 1)[1]
                    named.append(w)
    assert set(named) <= set(works), sorted(set(named) - set(works))
    assert set(works) <= set(named), sorted(set(works) - set(named))


@pytest.mark.data
def test_shipped_grammar_lexicon_onomasticon_and_grid_honor_t5_and_manifest_pins():
    manifest = json.loads((SHIPPED / "MANIFEST.json").read_text(encoding="utf-8"))
    assert not (SHIPPED / "unread_words.json").exists()
    bracket_unv = re.compile(r"\[\d{3}b?\]")
    for name in ("grammar_hypotheses.json", "lexicon.json", "onomasticon.json", "grid.json"):
        p = SHIPPED / name
        assert p.is_file(), f"missing shipped {name}"
        raw = p.read_bytes()
        assert manifest["files"][name] == {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
        obj = json.loads(raw)
        keys = {k for k, _ in walk(obj)}
        assert not keys & {"unvalued_index", "quote", "sign2vec", "lines", "sequences"}
        strings = [v for _, v in walk(obj) if isinstance(v, str)]
        assert not [s for s in strings if "src_" in s or bracket_unv.search(s) or "| 112" in s], name
    grammar = json.loads((SHIPPED / "grammar_hypotheses.json").read_text(encoding="utf-8"))
    lexicon = json.loads((SHIPPED / "lexicon.json").read_text(encoding="utf-8"))
    onomasticon = json.loads((SHIPPED / "onomasticon.json").read_text(encoding="utf-8"))
    assert len(grammar["hypotheses"]) == manifest["grammar"]["hypotheses"] >= 20
    assert all(h["kaphtor_exportable"] is True for h in grammar["hypotheses"])
    lex_by_id = {e["entry_id"]: e for e in lexicon["entries"]}
    onom_by_id = {o["onom_id"]: o for o in onomasticon["entries"]}
    assert len(onom_by_id) == manifest["lexicon"]["onomasticon_entries"]
    for o in onom_by_id.values():
        le = lex_by_id[o["lexicon_ref"]]
        assert le["entry_kind"] == "name_ref" and le["onomasticon_ref"] == o["onom_id"]
    for le in lex_by_id.values():
        if le["entry_kind"] == "name_ref":
            assert le["onomasticon_ref"] in onom_by_id


@pytest.mark.data
def test_the_translations_ship_only_the_groups_of_the_words_read():
    shipped = json.loads((SHIPPED / "translations.json").read_text(encoding="utf-8"))
    keys = {k for k, _ in walk(shipped)}
    assert not keys & {"lines", "sequences", "transcription", "reported_reading", "sign2vec", "quote",
                       "lines_sha256", "agrees_with", "against"}
    strings = [v for _, v in walk(shipped) if isinstance(v, str)]
    assert not [v for v in strings if "src_" in v or re.search("[\U00012F90-\U00012FFF]", v)]
    assert not [v for v in strings if re.search(r"\[\d{3}b?\]", v)]
    assert not [v for v in strings if "044-002-098-023" in v or "*98" in v or "*26" in v
                or "še-[x]-98-ti" in v or "e-no-62" in v or "| 112" in v]
    words = [w for r in shipped["translations"].values() for w in r["words"]]
    assert words and all(set(r) >= {"record_id", "source", "translation", "status", "words"}
                         for r in shipped["translations"].values())
    for w in words:
        if w["reading"]:
            assert w["cypro_minoan"] and len(w["values"]) == len(w["cypro_minoan"].split("-")), w
        else:                    # nor do its rivals' readings, which spell the group in other notations
            assert w["cypro_minoan"] is None and w["values"] == [], w
            assert all("reading" not in v for v in w["rivals"]), w
        assert isinstance(w["page"], int) and (w["line"] is None or (isinstance(w["line"], str) and w["line"])) \
            and w["text"] in ("corpus", "emended"), w
        assert all(v["work"] and v["page"] for v in w["rivals"]), w
    assert set(shipped["translations"]) <= set(json.loads((SHIPPED / "catalogue.json").read_text(encoding="utf-8")))


@pytest.mark.data
def test_the_manifest_counts_and_checksum_match_the_translations():
    body = (SHIPPED / "translations.json").read_bytes()
    manifest = json.loads((SHIPPED / "MANIFEST.json").read_text(encoding="utf-8"))
    shipped = json.loads(body)
    texts = shipped["translations"]
    complete = sum(1 for r in texts.values() if r["translation"] and r["status"] != "incomplete")
    incomplete = sum(1 for r in texts.values() if r["status"] == "incomplete")
    assert manifest["files"]["translations.json"] == {"sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body)}
    assert manifest["translations"] == {"texts": len(texts), "complete": complete, "incomplete": incomplete,
                                        "words": sum(len(r["words"]) for r in texts.values()),
                                        "sign_values": len(shipped["sign_values"])}
    assert manifest["policy"]["merge_into_linear_a"] is False


@pytest.mark.data
def test_the_lookup_reads_the_shipped_translation():
    done = run("--doc", "RASH Atab 004")
    assert done.returncode == 0, done.stderr
    assert "  Translation: di Mino, " in done.stdout and "Kôṯar-ʾabī" in done.stdout


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
def test_every_text_carries_the_date_and_script_fields_each_null_with_its_reason():
    catalogue = json.loads((SHIPPED / "catalogue.json").read_text(encoding="utf-8"))
    manifest = json.loads((SHIPPED / "MANIFEST.json").read_text(encoding="utf-8"))
    bad, counts = [], {f: {} for f in ("dating_status", "date_certainty", "script", "subcorpus")}
    for key, r in catalogue.items():
        bad += [(key, f) for f in DERIVED if f not in r]
        bad += [(key, f, "no reason") for f in DERIVED if r.get(f) is None and not r["null_reasons"].get(f)]
        cites = [c for f in ("script", "subcorpus") for c in r["field_sources"].get(f, [])]
        cites += (r["dating_basis"] or {}).get("cites", []) + [c for x in r["conflicts"] for c in x["cites"]]
        bad += [(key, c.get("work")) for c in cites if c["work"] not in manifest["works"] or not c.get("page")]
        # the lead and each conflict ship as their date statement does, a pointer where it is one
        for st in ([r["dating_basis"]] if r["dating_basis"] else []) + r["conflicts"]:
            if not any(d["text"] == st["text"] and d["cites"] == st["cites"] and d.get("note") == st.get("note")
                       and bool(d.get("pointer")) == bool(st.get("pointer")) for d in r["date"]):
                bad.append((key, "statement", st["text"]))
            if bool(st.get("pointer")) != (st["text"] is None):
                bad.append((key, "pointer", st["text"]))
        for f, counter in counts.items():
            value = "null" if r[f] is None else r[f]
            counter[value] = counter.get(value, 0) + 1
    assert not bad, bad[:10]
    assert manifest["dating_and_script"] == {f: dict(sorted(c.items())) for f, c in counts.items()}
    assert manifest["dating_and_script"]["dating_status"] == {"AGREE": 171, "CONFLICT": 18, "OVERLAP": 67,
                                                              "UNDATED": 7}
    doubts = {r["record_id"]: [(c["page"], c.get("note")) for c in r["field_sources"]["script"]]
              for r in catalogue.values() if any(c.get("note") for c in r["field_sources"].get("script", []))}
    single = (60, "discounts it as an inscription, with three other texts of one sign")
    assert doubts == {
        "cm:##172": [(496, "doubts that the signs are Cypro-Minoan writing, or writing at all")],
        "cm:##190": [(500, "allows that the script may be Cypro-Greek")],
        "cm:ADD##219": [(553, "takes the sign for a mark rather than an inscription"), single],
        "cm:ADD##221": [(554, "allows that the signs may be marks, not writing")],
        "cm:ADD##222": [(554, "sees one sign only, not an inscription"), single],
        "cm:ADD##223": [(554, "says of it what it says of ENKO Apes 002"), single],
        "cm:ADD##227": [(556, None), (60, "doubts that the seal's signs make an inscription")],
        "cm:ADD##228": [(556, "sees no formal writing in it"), single],
        "cm:ADD##236": [(558, "allows that it may not be writing in the strict sense")],
        "cm:kalo-chorafi-loom-weight-6": [
            (126, None), (66, None),
            (71, "finds no literate setting for it and so does not count it as writing in the strict sense")]}
    assert catalogue["ENKO Atab 002"]["dating_basis"]["note"] == "Appendix C's row for ENKO Atab 002a."
    dikaios = catalogue["ENKO Atab 003"]["conflicts"]
    assert [(c["source"], c["relation"], c["text"], c.get("pointer")) for c in dikaios] == \
        [("P. Dikaios", "chronology", None, True)]


@pytest.mark.data
def test_the_lookup_prints_the_shipped_date_and_script():
    out = run("--doc", "RS 20.25").stdout
    assert "  Date: LC IIC–IIIA (Late Cypriot IIC–IIIA), 1320–1100 BCE (Valério 2016, 39); OVERLAP, certainty MEDIUM" \
           in out
    assert "  Script: Cypro-Minoan (Valério 2016, 547)\n  Subcorpus: CM 3 (Valério 2016, 539; Valério 2016, 451)\n" in out


@pytest.mark.data
def test_the_lookup_reads_the_shipped_catalogue():
    done = run("--site", "KITI", "--type", "Avas", "--format", "json")
    assert done.returncode == 0, done.stderr
    assert len(json.loads(done.stdout)["texts"]) == 21
    done = run("--doc", "DO 5288")
    assert done.returncode == 0, done.stderr
    assert done.stdout.splitlines()[1].strip().startswith("RASH Atab 004")
