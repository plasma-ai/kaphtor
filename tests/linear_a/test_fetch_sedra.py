"""tools/linear_a/fetch_sedra.py on hand-made tables: no network, no Sedra data. A row is a live lexeme with a Semitic
or proper-name root, its root Sedra's letters in sedra.py's Latin; a file that differs from the manifest is deleted
and stops the run; the overlay puts the built file in the Syriac slot and links everything else.
"""
import gzip
import hashlib
import json

import pytest

from tools.linear_a import fetch_sedra as fs

pytestmark = pytest.mark.unit

ROOTS = [
    {"id": 1, "syriac": "ܐܒ", "kind": "semitic"},
    {"id": 2, "syriac": "ܡܪܝ", "kind": "proper_name"},
    {"id": 3, "syriac": "ܐܘܓܣܛ", "kind": "loanword"},
    {"id": 4, "syriac": "ܟܠ ܚܕ", "kind": "phrase"},
]
LEXEMES = [
    {"id": 3, "root_id": 1, "syriac": "ܐܒܗܘܬܐ", "syriac_vocalized": "ܐܰܒ݂ܳܗܽܘܬ݂ܳܐ", "category_type_id": 7},
    {"id": 10, "root_id": 2, "syriac": "ܡܪܝܡ", "syriac_vocalized": None, "category_type_id": None},
    {"id": 11, "root_id": 2, "syriac": "ܡܪܝܢ", "syriac_vocalized": "ܡܰܪܝܰܢ", "category_type_id": 18},
    {"id": 20, "root_id": 3, "syriac": "ܐܘܓܣܛܘܣ", "syriac_vocalized": None, "category_type_id": 12},
    {"id": 21, "root_id": 4, "syriac": "ܟܠܚܕ", "syriac_vocalized": None, "category_type_id": None},
    {"id": 30, "root_id": None, "syriac": "ܒܝܬܐ", "syriac_vocalized": None, "category_type_id": 7},
    {"id": 31, "root_id": 1, "syriac": "ܐܒܐ", "syriac_vocalized": "ܐܰܒ݂ܳܐ", "category_type_id": 7,
     "is_merged": True, "merged_into_id": 3},
    {"id": 32, "root_id": 1, "syriac": "ܐܒܐ", "syriac_vocalized": "ܐܰܒ݂ܳܜ", "category_type_id": 7},
]
GLOSSES = [
    {"id": 1, "lexeme_id": 3, "language_id": 10, "sort_order": 1, "meaning": "parentage", "prefix": None,
     "postfix": None},
    {"id": 2, "lexeme_id": 3, "language_id": 10, "sort_order": 0, "meaning": "fatherhood", "prefix": None,
     "postfix": None},
    {"id": 3, "lexeme_id": 3, "language_id": 10, "sort_order": 2, "meaning": "fatherhood\N{RIGHT-TO-LEFT MARK}.",
     "prefix": None, "postfix": None},
    {"id": 4, "lexeme_id": 3, "language_id": 16, "sort_order": 0, "meaning": "paternité", "prefix": None,
     "postfix": None},
    {"id": 5, "lexeme_id": 11, "language_id": 10, "sort_order": 0, "meaning": "Marin", "prefix": "the town",
     "postfix": None},
    {"id": 6, "lexeme_id": 32, "language_id": 10, "sort_order": 0,
     "meaning": 'IIIa <span class="selectableFont">ܐܰܘܒܶܕ</span> <em>to</em> destroy', "prefix": None, "postfix": None},
    {"id": 7, "lexeme_id": 32, "language_id": 10, "sort_order": 1, "meaning": "bread &amp; salt", "prefix": None,
     "postfix": None},
]
LANGUAGES = [{"id": 3, "name": "Greek", "iso_code": "grc"}, {"id": 4, "name": "Hebrew", "iso_code": "heb"},
             {"id": 10, "name": "English", "iso_code": "eng"}, {"id": 16, "name": "French", "iso_code": "fre"}]
CATEGORIES = [{"id": 7, "name": "noun"}, {"id": 12, "name": "proper noun"},
              {"id": 18, "name": "proper noun (place name)"}]
ETYMOLOGIES = [
    {"id": 1, "lexeme_id": 3, "language_id": 3, "source_word": "πατρότης", "meaning": "", "sort_order": 0},
    {"id": 2, "lexeme_id": 32, "language_id": 3, "source_word": "ἄρτος", "meaning": "bread", "sort_order": 1},
    {"id": 3, "lexeme_id": 32, "language_id": 3, "source_word": "ἅλς", "meaning": "", "sort_order": 0},
    {"id": 4, "lexeme_id": 11, "language_id": 4, "source_word": "מרין", "meaning": "", "sort_order": 0},
    {"id": 5, "lexeme_id": 20, "language_id": 3, "source_word": "Αὔγουστος", "meaning": "", "sort_order": 0},
]
TABLES = {"roots": ROOTS, "lexemes": LEXEMES, "glosses": GLOSSES, "languages": LANGUAGES,
          "category_types": CATEGORIES, "etymologies": ETYMOLOGIES}
RULINGS = {"loans": {"3": "Greek"}, "not_loans": {"32": "Greek equivalents of a native word"}}


def built():
    rows, tally = fs.build_rows(TABLES, "2026-10-25", rulings=RULINGS)
    return {r["id"]: r for r in rows}, tally


def test_rows_are_live_lexemes_with_semitic_or_name_roots():
    rows, tally = built()
    assert sorted(rows) == ["syr:sedra:10", "syr:sedra:11", "syr:sedra:3", "syr:sedra:32"]
    assert tally["loanword root"] == 1 and tally["phrase root"] == 1
    assert tally["no root"] == 1 and tally["merged lexeme"] == 1


def test_root_is_sedra_letters_in_latin():
    rows, _ = built()
    assert rows["syr:sedra:3"]["root"] == "ʔ-b"
    assert rows["syr:sedra:11"]["root"] == "m-r-y"
    assert rows["syr:sedra:3"]["match_keys"][:2] == ["ʔ-b", "ʔb"]


def test_vocalized_form_read_through_sedra_or_left_empty():
    rows, tally = built()
    assert rows["syr:sedra:3"]["normalized"] == "ʔabāhūtā"
    assert rows["syr:sedra:32"]["normalized"] == ""          # U+071C, a Garshuni letter sedra.py does not read
    assert rows["syr:sedra:10"]["normalized"] == ""          # no vocalization
    assert tally["no vocalized form read"] == 2


def test_english_glosses_in_order_once_each():
    rows, _ = built()
    assert rows["syr:sedra:3"]["meaning"] == "fatherhood; parentage"
    assert rows["syr:sedra:11"]["meaning"] == "the town Marin"


def test_glosses_lose_sedras_markup_but_keep_its_words():
    rows, _ = built()
    assert rows["syr:sedra:32"]["meaning"] == "IIIa ܐܰܘܒܶܕ to destroy; bread & salt"


def test_names_are_flagged_for_the_root_index():
    rows, _ = built()
    assert rows["syr:sedra:11"]["pos"] == "toponym"
    assert rows["syr:sedra:10"]["pos"] == "proper_noun"      # no category, proper-name root
    assert rows["syr:sedra:3"]["pos"] == "noun"


def test_etymologies_are_carried_and_only_ruled_loans_are_marked():
    rows, tally = built()
    assert rows["syr:sedra:3"]["semantic_domain"] == ["loan"]
    assert rows["syr:sedra:3"]["etymology"] == [{"language": "Greek", "source_word": "πατρότης"}]
    assert rows["syr:sedra:32"]["semantic_domain"] == ["general"]          # ruled: an equivalent, not the source
    assert rows["syr:sedra:32"]["etymology"] == [{"language": "Greek", "source_word": "ἅλς"},
                                                 {"language": "Greek", "source_word": "ἄρτος", "meaning": "bread"}]
    assert rows["syr:sedra:11"]["semantic_domain"] == ["general"]          # not ruled
    assert "etymology" not in rows["syr:sedra:10"]
    assert (tally["loan (ruled)"], tally["etymology ruled not a loan"], tally["etymology not ruled"]) == (1, 1, 1)


def test_shipped_loan_rulings_are_well_formed():
    rulings = fs.load_rulings()
    loans, not_loans = rulings["loans"], rulings["not_loans"]
    assert loans and not_loans and not set(loans) & set(not_loans)
    assert all(k.isdigit() for k in (*loans, *not_loans))
    assert set(loans.values()) <= {"Greek", "Latin", "Hebrew", "Akkadian", "Persian", "Arabic"}
    assert all(reason.strip() for reason in not_loans.values())


def test_rows_credit_the_release():
    rows, _ = built()
    ref = rows["syr:sedra:3"]["source_refs"][0]
    assert ref["source"] == "Sedra (Beth Mardutho), data release 2026-10-25" and ref["lexeme"] == 3


def manifest(tmp_path, damage=None):
    files, blobs = [], {}
    for table, rows in TABLES.items():
        blob = gzip.compress("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows).encode())
        path = f"/downloads/2026-10-25/{table}.jsonl.gz"
        blobs[fs.BASE + path] = blob
        files.append({"table": table, "path": path, "rows": len(rows), "bytes": len(blob),
                      "sha256": hashlib.sha256(blob).hexdigest()})
    files.append({"table": "roots", "path": "/downloads/2026-10-25/sedra4/roots.jsonl.gz", "rows": 1, "bytes": 1,
                  "sha256": "0"})
    if damage:
        blobs[fs.BASE + f"/downloads/2026-10-25/{damage}.jsonl.gz"] += b"x"
    return {"files": files}, blobs


def test_manifest_gives_release_and_skips_sedra4(tmp_path):
    m, _ = manifest(tmp_path)
    release, files = fs.manifest_files(m)
    assert release == "2026-10-25" and "/sedra4/" not in files["roots"]["path"]
    with pytest.raises(fs.ReleaseError):
        fs.manifest_files({"files": [f for f in m["files"] if f["table"] != "glosses"]})


def test_fetch_waits_between_requests_and_skips_current_files(tmp_path):
    m, blobs = manifest(tmp_path)
    _, files = fs.manifest_files(m)
    asked, slept = [], []
    fetched = fs.fetch(files, tmp_path / "raw", get=lambda u: asked.append(u) or blobs[u], sleep=slept.append)
    assert fetched == list(fs.TABLES) and len(asked) == 6 and slept == [fs.CRAWL_DELAY] * 5
    assert fs.fetch(files, tmp_path / "raw", get=lambda u: pytest.fail(u), sleep=slept.append) == []


def test_a_file_unlike_the_manifest_is_deleted_and_stops_the_run(tmp_path):
    m, blobs = manifest(tmp_path, damage="lexemes")
    _, files = fs.manifest_files(m)
    with pytest.raises(fs.ReleaseError, match="lexemes"):
        fs.fetch(files, tmp_path / "raw", get=blobs.__getitem__, sleep=lambda s: None)
    assert not (tmp_path / "raw" / "lexemes.jsonl.gz").exists()


def test_overlay_puts_the_build_in_the_syriac_slot(tmp_path):
    data = tmp_path / "data"
    (data / "contact").mkdir(parents=True)
    (data / "semitic-roots").mkdir()
    for name in ("syriac_lexicon.jsonl", "hebrew_lexicon.jsonl"):
        (data / "contact" / name).write_text("{}\n")
    built_file = tmp_path / "release" / "syriac_lexicon.jsonl"
    built_file.parent.mkdir()
    built_file.write_text("[sedra]\n")
    overlay = fs.write_overlay(tmp_path / "release", built_file, data=data)
    assert (overlay / "contact" / "syriac_lexicon.jsonl").read_text() == "[sedra]\n"
    assert (overlay / "contact" / "hebrew_lexicon.jsonl").resolve() == (data / "contact" / "hebrew_lexicon.jsonl")
    assert (overlay / "semitic-roots").resolve() == data / "semitic-roots"
    assert fs.write_overlay(tmp_path / "release", built_file, data=data) == overlay      # a rerun rebuilds it
