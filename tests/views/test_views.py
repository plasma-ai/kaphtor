"""The record wiki's builder (`tools/views/`): slugs, the translation normalizer, the counts, the census, sign status,
Markdown escaping and frontmatter, the block splice, and the build's check and write modes.

Most tests run on a fixture written to a temporary folder: three lexicon entries, documents in every census class,
both translation schemas, syllabic and fraction E, and the speculative sign *21F. The live tests read
`data/linear-a/` (or `$KAPHTOR_DATA/linear-a/`) and are skipped when the Linear A data is not in the checkout.
Each module is imported inside its tests, so a missing module fails those tests alone. Nothing here writes outside
the temporary folder.
"""
from __future__ import annotations

import collections
import importlib
import json
import re
import shutil
import subprocess
import sys
import tarfile
import unicodedata
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.paths import LINEAR_A_DATA

# Every file `model.load` reads: the data ships in waves, and the live tests run once the whole set is here.
LIVE_FILES = ("corpus.json", "lexicon.json", "translations.json", "onomasticon.json", "unread_words.json",
              "sign_values.json", "census_classes.json")
ABSENT = pytest.mark.skipif(not all((LINEAR_A_DATA / name).exists() for name in LIVE_FILES),
                            reason="the Linear A data is not all in this checkout")


def LIVE(test):
    """Skipped without the whole set, and a `maintainer` test while part of it is unshipped (`data` once all ships)."""
    return pytest.mark.maintainer(ABSENT(test))


def views(name: str):
    return importlib.import_module(f"tools.views.{name}")


# ---------------------------------------------------------------- the fixture

def record(site: str, provenance: str | None = "GORILA", words: list[str] | None = None) -> dict:
    return {"site": site, "source_provenance": provenance, "support": "Tablet", "context": "LMIB", "findspot": "",
            "scribe": "", "imageRights": "", "names": [], "parsedInscription": "𐘀𐘁",
            "transliteratedWords": words or ["KU-PA₃-NU", "\n", "OLE+KI", "1"], "translatedWords": []}


CORPUS = {
    "HT9a": record("Haghia Triada"),                     # HT9a and HT9b: one document, GORILA labelled
    "HT9b": record("Haghia Triada", words=["A-DU", "KU-RO"]),
    "ZA1": record("Zakros"),                             # labelled since its identification: the label wins
    "GO2r": record("Gournia", "SigLA"),                  # RILA-S1 accepted, two sides
    "GO2v": record("Gournia", "SigLA"),
    "MARG1": record("Margiana", None),                   # outside the Linear A area
    "KNWc23": record("Knossos", None),                   # RILA-S1 doubtful
    "HTWc3023": record("Haghia Triada", None),           # RILA-S1 listed, not counted
    "KNZg57": record("Knossos", None),                   # published after 2023
    "THEZb5": record("Thera"),                           # labelled GORILA by its source, outside both editions
    "HTWa1146": record("Haghia Triada", None),           # GORILA, unlabelled
    "PEZb": record("Petras", None),                      # unresolved
    "HT154ja": record("Haghia Triada"),                  # the two sides of HT 154 fragment J
    "HT154jb": record("Haghia Triada"),
    "HT154a": record("Haghia Triada"),                   # HT 154 A, a fragment of its own
    "APZa<3>": record("Apodoulou"),
}
CENSUS = collections.Counter({
    "GORILA, labelled": 5, "RILA-S1 accepted": 1, "outside the Linear A area": 1, "RILA-S1 doubtful": 1,
    "RILA-S1 listed, not counted": 1, "published after 2023": 1, "outside both editions": 1,
    "GORILA, unlabelled": 1, "unresolved": 1,
})
CLASSES = {
    "description": "fixture",
    "outside_area_sites": ["Margiana", "Troy"],
    "rila_s1_accepted": {"GO 2": {"keys": ["GO2r", "GO2v"], "note": ""}},
    "rila_s1_doubtful": {"D 1 KN Wc 23": ["KNWc23"], "D 6 VRY Za 4": []},
    "rila_s1_listed_not_counted": {"{HT Wc 3023} uninscribed": ["HTWc3023"]},
    "published_after_2023": ["KNZg57"],
    "outside_editions": ["THEZb5"],
    "gorila_unlabelled": ["HTWa1146", "ZA1"],
    "unresolved": ["PEZb"],
    "merged": {"HT9c": "HT9a"},
    "gorila_v": {"documents": 6, "rila_s1_accepted": [], "rila_s1_doubtful": [], "records_holding_two_sigla": []},
}
LEXICON = {"entries": [
    {"word": "KU-PA₃-NU", "reading": "Kubānu", "meaning": "personal name", "confidence": "PROBABLE", "tier": 3,
     "confidence_score": 0.7, "attestations": ["HT9a"], "root": None, "note": "", "source": "", "category": "name",
     "language_layer": "", "semantic_field": "", "is_anchor": False},
    {"word": "A-DU", "reading": "Addu", "meaning": "the storm god", "confidence": "CANDIDATE", "tier": 2,
     "confidence_score": 0.5, "attestations": ["HT9b", "HT27a(*307)"], "root": "ʾ-d-d", "note": "Cf. *301 | APZa<3>.",
     "source": "", "category": "theonym", "language_layer": "", "semantic_field": "", "is_anchor": False},
    {"word": "OLE+KI", "reading": "kīnu?", "meaning": "oil of a kind", "confidence": "CANDIDATE", "tier": 2,
     "confidence_score": 0.4, "attestations": ["HT9a"], "root": None, "note": "", "source": "", "category": "logogram",
     "language_layer": "", "semantic_field": "", "is_anchor": False},
]}
ONOMASTICON = {"entries": [
    {"token": "KU-PA₃-NU", "type": "personal_name", "reading": "Kupanu", "meaning": "", "attestations": ["HT9a"],
     "frequency": 1, "sites": ["Haghia Triada"], "genre_supports": {"Tablet": 1}, "affiliation": "Semitic",
     "affiliation_confidence": "medium", "affiliation_evidence": "", "provenance": "lexicon", "type_confidence": "high",
     "co_occurring_known": [{"word": "OLE+KI"}], "contact_ref": None, "note": ""},
]}
UNREAD = {"statuses": {"intact_unread": "legible, no reading"}, "entries": [
    {"word": "KU-ME-TA", "status": "intact_unread", "role": None, "frequency": 1, "attestations": ["HT9b"],
     "note": "", "sites": ["Haghia Triada"]},
    {"word": "]KU-ME-TA", "status": "intact_unread", "role": None, "frequency": 1, "attestations": ["HT9b"],
     "note": "", "sites": ["Haghia Triada"]},
]}
TRANSLATIONS = {"translations": {
    "HT9a": {"translation": "Kubānu: oil 1.", "site": "Haghia Triada", "notes": "", "confidence": "PROBABLE",
             "source": "di Mino", "words": [
                 {"linear_a": "KU-PA₃-NU", "reading": "Kubānu", "meaning": "a name", "confidence": "PROBABLE"},
                 {"linear_a": "OLE+KI", "reading": "kīnu", "gloss": "oil", "note": "commodity"}]},
    "HT9b": {"composite_translation": "Addu; total.", "site": "Haghia Triada", "notes": "", "status": "fragmentary",
             "source": {"readings": ["di Mino"]}, "words": {"A-DU": {"reading": "Addu", "meaning": "the storm god"}}},
    "GO2r": {"translation": "…", "site": "Gournia", "notes": "", "status": "incomplete", "words": []},
    "ZA1": {"translation": "", "site": "Zakros", "notes": "", "words": []},
}}
SIGN_VALUES = {
    "signs": {
        "E": {"primary": {"consonant": None, "vowel": "e"}, "linear_b": {"sign_number": "B 38", "value": "e"}},
        "AU": {"primary": {"consonant": None, "vowel": "au"}, "linear_b": {"sign_number": "B 85", "value": "au"}},
        "TI": {"primary": {"consonant": "t", "vowel": "i"}, "linear_b": {"sign_number": "B 37", "value": "ti"}},
        "*21F": {"primary": {"consonant": "h", "vowel": "a"}, "linear_b": None, "confirmed_by": ["*21F-TU-NE"]},
        "*306": {"primary": {"consonant": "ʿ", "vowel": "a"}, "linear_b": None},
        "*118": {"primary": {"consonant": "ṭ", "vowel": "a"},
                 "linear_b": {"sign_number": "B 118", "value": "talent (L)"}},
        "*47": {"primary": {"consonant": "s", "vowel": "o"}, "linear_b": {"sign_number": "B 47", "value": None}},
    },
    "logograms": {"_note": "not a record", "TI": {"gloss": "a commodity"}, "*308": {"gloss": "pressed oil"},
                  "*317": {"gloss": "receipt(s)", "status": "CANDIDATE", "tier": 2}},
    "fractions": {"description": "", "signs": {"E": {"value": "1/4"}, "D": {"value": "1/6"}}},
    "resolution_summary": {
        "phonemic": ["AU=au (Linear B *85)"], "logograms": ["*308=pressed oil derivative"], "fractions": ["E=1/4"],
        "total": 2, "phonemic_count": 1, "logogram_count": 1, "fraction_count": 1,
        "proposed": {
            "phonemic": [{"entry": "*306=ʿA", "evidence": "ʿ leads by one word"}],
            "logograms": [{"entry": "*317=LIQḤU"}],
            "fractions": [{"entry": "D=1/6", "evidence": "no balancing total tests it"}],
            "phonemic_count": 1, "logogram_count": 1, "fraction_count": 1,
        },
    },
}
FILES = {"corpus.json": CORPUS, "census_classes.json": CLASSES, "lexicon.json": LEXICON,
         "onomasticon.json": ONOMASTICON, "unread_words.json": UNREAD, "translations.json": TRANSLATIONS,
         "sign_values.json": SIGN_VALUES}


@pytest.fixture(autouse=True)
def backups(tmp_path: Path, monkeypatch) -> Path:
    """Every backup goes to the test's folder, never the user's state folder."""
    folder = tmp_path / "backups"
    monkeypatch.setattr(views("build"), "BACKUPS", folder)
    return folder


@pytest.fixture
def data(tmp_path: Path) -> Path:
    folder = tmp_path / "data"
    folder.mkdir()
    for name, content in FILES.items():
        (folder / name).write_text(json.dumps(content, ensure_ascii=False, indent=1), encoding="utf-8")
    return folder


def snapshot(folder: Path) -> dict:
    return {str(p.relative_to(folder)): (p.stat().st_size, p.stat().st_mtime_ns)
            for p in sorted(folder.rglob("*")) if p.is_file()}


def tree(folder: Path) -> dict:
    return {str(p.relative_to(folder)): p.read_bytes() for p in sorted(folder.rglob("*")) if p.is_file()}


def load_live(name: str):
    return json.loads((LINEAR_A_DATA / name).read_text(encoding="utf-8"))


# ---------------------------------------------------------------- documents and the census

@pytest.mark.parametrize("key, document", [
    ("HT9a", "HT9"), ("HT9b", "HT9"), ("GO2r", "GO2"), ("GO2v", "GO2"), ("KNWc<24a>", "KNWc<24>"),
    ("HT123+124a", "HT123+124"), ("HT154a", "HT154a"), ("HT154n", "HT154n"), ("HT154ja", "HT154j"),
    ("HT154jb", "HT154j"), ("HT154.", "HT154."), ("HT113ter", "HT113ter"), ("HTZb162bis", "HTZb162bis"),
    ("APZa<3>", "APZa<3>"), ("ZA1", "ZA1"),
])
def test_doc_id_folds_sides_and_keeps_fragments(key, document):
    assert views("counts").doc_id(key) == document


def test_census_classes_every_document_once(data):
    counts = views("counts")
    corpus = json.loads((data / "corpus.json").read_text(encoding="utf-8"))
    assert len(counts.documents(corpus)) == 13
    assert counts.census(corpus, CLASSES) == CENSUS


@pytest.mark.parametrize("change", ["unclassified", "overlap", "merged_still_held", "missing_key"])
def test_census_refuses_a_broken_class_file(change):
    counts = views("counts")
    corpus, classes = dict(CORPUS), json.loads(json.dumps(CLASSES))
    if change == "unclassified":
        corpus["XX1"] = record("Nowhere", None)
    elif change == "overlap":
        classes["unresolved"].append("THEZb5")
    elif change == "merged_still_held":
        corpus["HT9c"] = record("Haghia Triada")
    else:
        classes["rila_s1_doubtful"]["D 1 KN Wc 23"] = ["KNWc999"]
    with pytest.raises(ValueError):
        counts.census(corpus, classes)


@LIVE
def test_live_census_is_1603_documents():
    counts = views("counts")
    corpus = load_live("corpus.json")
    assert (len(corpus), len(counts.documents(corpus))) == (1719, 1603)
    assert counts.census(corpus, load_live("census_classes.json")) == collections.Counter({
        "GORILA, labelled": 1370, "RILA-S1 accepted": 110, "GORILA, unlabelled": 50, "outside both editions": 37,
        "RILA-S1 doubtful": 24, "RILA-S1 listed, not counted": 4, "outside the Linear A area": 3, "unresolved": 3,
        "published after 2023": 2,
    })


# ---------------------------------------------------------------- translations

def test_normalizer_reads_both_schemas():
    model = views("model")
    old = model.normalize_translation("HT9a", TRANSLATIONS["translations"]["HT9a"])
    assert old["text"] == "Kubānu: oil 1." and old["complete"] is True and old["status"] is None
    assert [(w["form"], w["reading"], w["gloss"]) for w in old["words"]] == [
        ("KU-PA₃-NU", "Kubānu", "a name"), ("OLE+KI", "kīnu", "oil")]
    new = model.normalize_translation("HT9b", TRANSLATIONS["translations"]["HT9b"])
    assert new["text"] == "Addu; total." and new["complete"] is True and new["status"] == "fragmentary"
    assert [(w["form"], w["reading"], w["gloss"]) for w in new["words"]] == [("A-DU", "Addu", "the storm god")]


def test_normalizer_fails_on_an_unknown_item_key():
    entry = {"translation": "x", "words": [{"linear_a": "A-DU", "reading": "Addu", "glosss": "typo"}]}
    with pytest.raises(ValueError, match="glosss"):
        views("model").normalize_translation("HT1", entry)


def test_normalizer_fails_on_gloss_and_meaning_together():
    entry = {"translation": "x", "words": [{"linear_a": "A-DU", "reading": "Addu", "gloss": "a", "meaning": "b"}]}
    with pytest.raises(ValueError):
        views("model").normalize_translation("HT1", entry)


def test_count_rule_needs_text_and_no_incomplete_status():
    assert views("counts").translation_counts(TRANSLATIONS["translations"]) == (2, 2)


@LIVE
def test_live_translations_normalize_and_match_the_doc_count_rule():
    model, counts = views("model"), views("counts")
    translations = load_live("translations.json")["translations"]
    for doc, entry in translations.items():
        model.normalize_translation(doc, entry)
    complete, incomplete = counts.translation_counts(translations)
    assert complete == sum(1 for t in translations.values() if t.get("status") != "incomplete")
    assert complete + incomplete == len(translations)


# ---------------------------------------------------------------- slugs and paths

@pytest.mark.parametrize("form, name", [
    ("KU-PA₃-NU", "KU_PA3_NU"), ("]KU-ME-TA", "KU_ME_TA_broken_start"), ("KU-ME-TA[", "KU_ME_TA_broken_end"),
    ("*301", "star301"), ("OLE+KI", "OLE_plus_KI"), ("APZa<3>", "APZa_3"),
])
def test_slug(form, name):
    assert views("model").slug(form) == name


def test_paths_are_distinct_and_ascii_identifiers():
    model = views("model")
    forms = ["KU-ME-TA", "]KU-ME-TA", "OLE+KI", "OLE-KI", "*301", "KU-PA₃-NU"]
    paths = [model.word_path(f) for f in forms]
    assert len(set(paths)) == len(forms)
    assert model.sign_path("syllabic", "E") != model.sign_path("fractions", "E")
    assert model.doc_path("HT9a").startswith("wiki/linear-a/inscriptions/HT/HT/")
    assert model.doc_path("HTWa1146").startswith("wiki/linear-a/inscriptions/HT/HTWa/")
    for path in paths + [model.doc_path(k) for k in CORPUS]:
        name = path.rsplit("/", 1)[1]
        assert name.isascii() and name.isidentifier(), path


def test_overrides_place_the_keys_the_series_pattern_misses():
    model = views("model")
    assert model.series("PKZbX") == ("PK", "PKZb")
    assert model.doc_path("KNsceau") == "wiki/linear-a/inscriptions/KN/misc/KNsceau"
    assert model.series("PKZb19") == ("PK", "PKZb")


@LIVE
def test_live_paths_never_collide():
    model = views("model")
    forms = ({e["word"] for e in load_live("lexicon.json")["entries"]}
             | {o["token"] for o in load_live("onomasticon.json")["entries"]}
             | {u["word"] for u in load_live("unread_words.json")["entries"]})
    signs = load_live("sign_values.json")
    pages = collections.defaultdict(set)
    for form in forms:
        pages[model.word_path(form)].add(("word", form))
    for key in load_live("corpus.json"):
        pages[model.doc_path(key)].add(("inscription", key))
    for kind, records in (("syllabic", signs["signs"]), ("logograms", signs["logograms"]),
                          ("fractions", signs["fractions"]["signs"])):
        for key in records:
            if not key.startswith("_"):
                pages[model.sign_path(kind, key)].add((kind, key))
    assert {p: ids for p, ids in pages.items() if len(ids) > 1} == {}
    for path in pages:
        name = path.rsplit("/", 1)[1]
        assert name.isascii() and name.isidentifier(), path


# ---------------------------------------------------------------- signs

def test_sign_status_is_per_kind_and_conventional_only_for_a_linear_b_syllable():
    status = views("model").sign_status(SIGN_VALUES)
    assert status[("fractions", "E")] == ("resolved", "")
    assert status[("syllabic", "E")] == ("conventional", "")
    assert status[("syllabic", "AU")] == ("resolved", "")
    assert status[("logograms", "*308")] == ("resolved", "")
    assert status[("syllabic", "*306")] == ("proposed", "ʿ leads by one word")
    assert status[("fractions", "D")] == ("proposed", "no balancing total tests it")
    assert status[("logograms", "*317")] == ("proposed", "")
    assert status[("syllabic", "*21F")] == ("speculative", "")
    assert status[("logograms", "TI")] == ("speculative", "")
    assert status[("syllabic", "TI")] == ("conventional", "")
    assert status[("syllabic", "*118")] == ("speculative", "")  # Linear B *118 is the talent, not a syllable
    assert status[("syllabic", "*47")] == ("speculative", "")  # Linear B *47 has no value
    assert ("logograms", "_note") not in status


@pytest.mark.parametrize("evidence", ["STRONG: h 4/10 word types", "VERDICT_X: h 4/10 word types"])
def test_sign_status_refuses_evidence_that_opens_with_a_verdict_label(evidence):
    signs = json.loads(json.dumps(SIGN_VALUES))
    signs["resolution_summary"]["proposed"]["phonemic"][0]["evidence"] = evidence
    with pytest.raises(ValueError, match=evidence.split(":")[0]):
        views("model").sign_status(signs)


def test_a_proposed_sign_page_gives_its_evidence_and_no_verdict(data):
    model, render = views("model"), views("render")
    m = model.load(data)
    _, with_evidence = render.sign_page(m, "syllabic", "*306")
    _, without = render.sign_page(m, "logograms", "*317")
    assert "**Status: proposed.**" in with_evidence and "Evidence: ʿ leads by one word" in with_evidence
    assert "**Status: proposed.**" in without and "Evidence:" not in without
    for text in (with_evidence, without):
        assert "Corpus test" not in text and "corpus test" not in text


def test_sign_keys_read_subscripts_as_digits_and_refuse_a_clash():
    model = views("model")
    assert model.sign_keys({"PA₃": {}, "TA2": {}}) == {"PA3": "PA₃", "TA2": "TA2"}
    with pytest.raises(ValueError):
        model.sign_keys({"PA₃": {}, "PA3": {}})


def test_a_sign_key_meets_its_forms_whichever_way_the_subscript_is_written(data):
    model, render = views("model"), views("render")
    m = model.load(data)
    m.sign_values["signs"]["PA3"] = {"primary": {"consonant": "p", "vowel": "a"}, "linear_b": None}
    m.sign_status = model.sign_status(m.sign_values)
    _, sign = render.sign_page(m, "syllabic", "PA3")
    assert f"[[{model.word_path('KU-PA₃-NU')}\\|KU-PA₃-NU]]" in sign
    _, word = render.word_page(m, "KU-PA₃-NU")
    assert f"[[{model.sign_path('syllabic', 'PA3')}|PA₃]]" in word


def test_a_sign_page_writes_alternates_and_linear_b_as_text(data):
    model, render, markdown = views("model"), views("render"), views("markdown")
    m = model.load(data)
    m.sign_values["signs"]["*21F"]["alternates"] = [
        {"consonant": "ḫ", "vowel": "a", "confidence": 0.5, "evidence": ["RA-ḤA-RA | Rꜥ-Ḥr"]}]
    m.sign_values["signs"]["E"]["linear_b"] |= {"unicode": "U+10001", "unicode_name": "LINEAR B SYLLABLE B038 E",
                                                "unicode_source_refs": [{"source": "Unicode names list"}]}
    _, star = render.sign_page(m, "syllabic", "*21F")
    _, e = render.sign_page(m, "syllabic", "E")
    assert "| Alternates | /ḫa/ |" in star and "| /ḫa/ | 0.50 | RA-ḤA-RA \\| Rꜥ-Ḥr |" in star
    assert "| Linear B | B 38, value e |" in e and "| Linear B Unicode | U+10001 LINEAR B SYLLABLE B038 E |" in e
    for text in (star, e):
        body = text.split(markdown.BEGIN, 1)[1]
        assert not re.search(r"[{\[]['\"]", body), body
        assert "Unicode names list" not in body


# ---------------------------------------------------------------- Markdown

@pytest.mark.parametrize("text, escaped", [
    ("*301", r"\*301"), ("]KU-ME-TA", r"\]KU-ME-TA"), ("APZa<3>", "APZa&lt;3&gt;"), ("a | b", r"a \| b"),
    ("KU-PA₃-NU", "KU-PA₃-NU"),
])
def test_escape(text, escaped):
    assert views("markdown").escape(text) == escaped


@pytest.mark.parametrize("text", ["KI-RO 30 [[7]]", "\\]PA-RI-DE [[•]]", "[[[x]]]", "a [ [b", "*301-KI-TA-A [[?]]"])
def test_escaped_double_brackets_never_look_like_a_damaged_wikilink(text):
    escaped = views("markdown").escape(text)
    assert not re.search(r"(?<!\[)\\\[\\?\[", escaped), escaped  # plasma-wiki lint's formatter-damage signature
    assert "[[" not in escaped and "]]" not in escaped


def test_table_escapes_the_bar_of_a_wikilink():
    markdown = views("markdown")
    rows = markdown.table(["Word", "Reading"], [[markdown.link("wiki/linear-a/words/A/A_DU", "A-DU"), "a \\| b"],
                                                [markdown.link("wiki/w/K", markdown.escape("]-KU-NA-[")), ""]])
    assert rows[2] == r"| [[wiki/linear-a/words/A/A_DU\|A-DU]] | a \| b |"
    assert rows[3] == r"| [[wiki/w/K\|&#93;-KU-NA-&#91;]] |  |"


def test_a_link_label_holds_no_bracket():
    markdown = views("markdown")
    assert markdown.link("wiki/w/E", markdown.escape("[…]PI-MI-NA-TE")) == "[[wiki/w/E|&#91;…&#93;PI-MI-NA-TE]]"


def test_frontmatter_round_trips():
    markdown = views("markdown")
    fields = {"title": "]KU-ME-TA", "form": "𐘀𐘁", "nfd": unicodedata.normalize("NFD", "ḫaṭṭu"), "tier": 3,
              "confidence_score": 0.7, "reading": None, "attestations": ["HT9a", "HT27a(*307)"], "quote": 'a "b": c'}
    text = markdown.frontmatter(fields)
    assert text.startswith("---\n") and text.endswith("\n---")
    for line in text.splitlines()[1:-1]:
        key, value = line.split(": ", 1)
        assert json.loads(value) == fields[key]
    assert markdown.parse_frontmatter(text + "\n\n# x\n") == fields


def test_splice_keeps_text_outside_the_block():
    markdown = views("markdown")
    existing = "\n".join([
        markdown.frontmatter({"title": "A-DU", "desc": "old", "updated": "kept by wiki update"}),
        "", "# A-DU", "", "[[wiki/linear-a/words/A/_index|..]]", "", "***", "", "A line someone wrote.", "",
        "<!-- BEGIN kaphtor:record -->", "old body", "<!-- END kaphtor:record -->", "", "Another line.", ""])
    fresh = "\n".join([
        markdown.frontmatter({"title": "A-DU", "desc": "new"}),
        "", "# A-DU", "", "[[wiki/linear-a/words/A/_index|..]]", "", "***", "",
        "<!-- BEGIN kaphtor:record -->", "new body", "<!-- END kaphtor:record -->", ""])
    page = markdown.splice(existing, fresh)
    assert markdown.parse_frontmatter(page) == {"title": "A-DU", "desc": "new", "updated": "kept by wiki update"}
    assert "new body" in page and "old body" not in page
    assert "A line someone wrote." in page and "Another line." in page
    assert markdown.outside_text(page) == ["A line someone wrote.", "Another line."]
    assert markdown.outside_text(fresh) == []


def test_splice_edits_its_own_keys_in_place_and_keeps_every_other_line_verbatim():
    markdown = views("markdown")
    body = ["", "# A-DU", "", "***", "", markdown.BEGIN, "{}", markdown.END, ""]
    existing = "\n".join(["---", "name: wiki/linear-a/words/A/A_DU", 'title: "A-DU"', 'desc: "old"', 'tags: ["x"]',
                          "sources:", "  - Gordon 1966", 'tier: 2', 'reading: |', '  Addu', "  (old)",
                          "created: 2026-10-21T21:01:44Z", "updated: 2026-10-21T21:01:44Z", "---",
                          *body]).format("old")
    fresh = "\n".join([markdown.frontmatter({"title": "A-DU", "desc": "new", "tags": ["x"], "reading": "Addu",
                                             "kind": "word"}), *body]).format("new")
    owned = frozenset({"title", "desc", "tags", "tier", "reading", "kind"})
    page = markdown.splice(existing, fresh, owned)
    assert page.split("---\n")[1].splitlines() == [
        "name: wiki/linear-a/words/A/A_DU", 'title: "A-DU"', 'desc: "new"', 'tags: ["x"]', "sources:",
        "  - Gordon 1966", 'reading: "Addu"', 'kind: "word"', "created: 2026-10-21T21:01:44Z",
        "updated: 2026-10-21T21:01:44Z"]
    assert "new" in page and "old" not in page
    assert markdown.splice(page, fresh, owned) == page


def test_set_frontmatter_writes_its_keys_and_keeps_every_other_line():
    markdown = views("markdown")
    text = "---\nname: wiki/x\ndesc: ...\ntags: []\n---\n\n# x\n"
    assert markdown.set_frontmatter(text, {"desc": "A folder."}) == (
        '---\nname: wiki/x\ndesc: "A folder."\ntags: []\n---\n\n# x\n')
    assert markdown.set_frontmatter("---\nname: wiki/x\n---\n", {"desc": "A."}) == '---\nname: wiki/x\ndesc: "A."\n---\n'


def test_splice_refuses_a_page_without_the_block():
    markdown = views("markdown")
    with pytest.raises(ValueError):
        markdown.splice("---\ntitle: \"x\"\n---\n\n# x\n\nhand-written\n", "---\ntitle: \"x\"\n---\n")


# ---------------------------------------------------------------- pages

def test_a_word_page_lists_the_attestations_of_every_record(data):
    model, render, markdown = views("model"), views("render"), views("markdown")
    m = model.load(data)
    m.lexicon["KU-PA₃-NU"]["attestations"] = None
    m.onomasticon["KU-PA₃-NU"]["attestations"] = ["HT9b", "HT9a"]
    m.unread["KU-PA₃-NU"] = {**UNREAD["entries"][0], "word": "KU-PA₃-NU", "attestations": ["HT9a", "ZA1"]}
    _, text = render.word_page(m, "KU-PA₃-NU")
    assert markdown.parse_frontmatter(text)["attestations"] == ["HT9b", "HT9a", "ZA1"]


def test_an_attestation_links_to_a_page_held_by_its_translation_alone(data):
    model, render = views("model"), views("render")
    m = model.load(data)
    m.translations["LMP-Spell33"] = model.normalize_translation("LMP-Spell33", {"translation": "a spell", "words": []})
    m.lexicon["A-DU"]["attestations"] = ["LMP-Spell33"]
    _, text = render.word_page(m, "A-DU")
    assert f"[[{model.doc_path('LMP-Spell33')}\\|LMP-Spell33]]" in text
    assert "not in corpus" not in text


def test_a_lexicon_entry_without_a_reading_prints_no_none(data):
    model, render, markdown = views("model"), views("render"), views("markdown")
    m = model.load(data)
    m.lexicon["OLE+KI"]["reading"] = None
    _, text = render.word_page(m, "OLE+KI")
    assert markdown.parse_frontmatter(text)["desc"] == "oil of a kind. Lexicon, CANDIDATE (tier 2)."
    assert "None" not in text


def test_a_confirmed_word_page_names_its_reviewer_and_the_outside_scholar(data):
    model, render = views("model"), views("render")
    m = model.load(data)
    m.lexicon["KU-PA₃-NU"] |= {
        "confidence": "CONFIRMED", "tier": 4, "reviewer": "di Mino",
        "outside_scholar": {"scholar": "Cyrus H. Gordon", "work": "Evidence for the Minoan Language", "year": 1966,
                            "sections": ["§119", "§145"], "basis": "published"}}
    m.lexicon["A-DU"] |= {"confidence": "CONFIRMED", "tier": 4, "reviewer": "di Mino"}
    _, text = render.word_page(m, "KU-PA₃-NU")
    review = text.split("### Review\n", 1)[1].split("\n#", 1)[0]
    assert "- **Reviewer:** di Mino" in review
    assert ("- **Published by:** Cyrus H. Gordon, *Evidence for the Minoan Language* (1966), §119, §145"
            in review)
    _, text = render.word_page(m, "A-DU")
    review = text.split("### Review\n", 1)[1].split("\n#", 1)[0]
    assert "- **Reviewer:** di Mino" in review
    assert "Published by" not in review
    _, text = render.word_page(m, "OLE+KI")
    assert "### Review" not in text


def test_every_link_names_a_page_the_build_writes(data):
    model, render = views("model"), views("render")
    m = model.load(data)
    m.translations["HT9a"]["words"].append({**m.translations["HT9a"]["words"][0], "form": "]NA-SI"})
    pages = render.pages(m)
    targets = {t for text in pages.values() for t in re.findall(r"\[\[([^|\\\]]+)", text)}
    assert {t for t in targets if not t.endswith("/_index")} <= set(pages)
    assert "| \\]NA-SI |" in pages[model.doc_path("HT9a")]


def test_the_builder_leaves_name_and_sources_to_wiki_update(data):
    model, render, markdown = views("model"), views("render"), views("markdown")
    for path, text in render.pages(model.load(data)).items():
        assert not {"name", "sources"} & set(markdown.parse_frontmatter(text)), path
    assert not {"name", "sources"} & render.OWNED_KEYS


def test_two_pages_on_one_path_are_refused_even_by_case(data):
    model, render = views("model"), views("render")
    with pytest.raises(ValueError, match="KU_ME_TA"):
        render.collect([("wiki/linear-a/words/K/KU_ME_TA", "a"), ("wiki/linear-a/words/K/ku_me_ta", "b")])
    m = model.load(data)
    m.unread["ku-me-ta"] = {**UNREAD["entries"][0], "word": "ku-me-ta"}
    with pytest.raises(ValueError):
        render.pages(m)


@LIVE
def test_live_signs_meet_their_forms_and_no_word_desc_prints_none():
    model, render, markdown = views("model"), views("render"), views("markdown")
    m = model.load(LINEAR_A_DATA)
    for key in ("TA2", "RA2", "PA₃"):
        _, text = render.sign_page(m, "syllabic", key)
        assert "## Lexicon words written with this sign" in text, key
    for form in m.forms():
        desc = markdown.parse_frontmatter(render.word_page(m, form)[1])["desc"]
        assert "None" not in desc, form


# ---------------------------------------------------------------- folder descs

def test_folder_descs_name_the_site_the_series_and_the_first_sign(data):
    model, indexes = views("model"), views("indexes")
    m = model.load(data)
    for word in ("*301-KI", "[?]-KI"):
        m.unread[word] = {**UNREAD["entries"][0], "word": word}
    descs = indexes.descs(m)
    assert descs["wiki/linear-a/inscriptions/HT"] == "Inscriptions from Haghia Triada."
    assert descs["wiki/linear-a/inscriptions/HT/HTWa"] == "Inscriptions from Haghia Triada, series HTWa."
    assert descs["wiki/linear-a/inscriptions/MARG/MARG"] == "Inscriptions from Margiana, series MARG."
    assert descs["wiki/linear-a/words/K"] == "Words whose first sign begins with K."
    assert descs["wiki/linear-a/words/Q"] == ("Words whose first sign begins with Q, and words that open with an "
                                              "illegible sign.")
    assert descs["wiki/linear-a/words/star"] == "Words that open with a sign known by its number, such as *301."
    folders = set()  # every folder above a word or inscription page, and no other
    for path in views("render").pages(m):
        for root in ("wiki/linear-a/inscriptions/", "wiki/linear-a/words/"):
            if path.startswith(root):
                parts = path[len(root):].split("/")[:-1]
                folders |= {root + "/".join(parts[:i]) for i in range(1, len(parts) + 1)}
    assert set(descs) == folders


def test_a_doubtful_site_reads_as_doubtfully_attributed(data):
    model, indexes = views("model"), views("indexes")
    m = model.load(data)
    m.corpus["KO(?)Zf2"] = record("Kophinas(?)")
    descs = indexes.descs(m)
    assert descs["wiki/linear-a/inscriptions/KO"] == "Inscriptions doubtfully attributed to Kophinas."
    assert descs["wiki/linear-a/inscriptions/KO/KOZf"] == "Inscriptions doubtfully attributed to Kophinas, series KOZf."


def test_an_override_desc_replaces_the_generated_one_where_its_folder_exists(data, monkeypatch):
    model, indexes = views("model"), views("indexes")
    monkeypatch.setitem(model.OVERRIDES, "descs", {"wiki/linear-a/inscriptions/HT": "Written by hand.",
                                                   "wiki/linear-a/inscriptions/NOWHERE": "No folder."})
    descs = indexes.descs(model.load(data))
    assert descs["wiki/linear-a/inscriptions/HT"] == "Written by hand."
    assert "wiki/linear-a/inscriptions/NOWHERE" not in descs


def test_the_keftiu_spell_sits_under_its_own_folder_with_a_desc_by_hand(data):
    model, indexes = views("model"), views("indexes")
    assert model.series("LMP-Spell33") == ("LMP", "")
    assert model.doc_path("LMP-Spell33") == "wiki/linear-a/inscriptions/LMP/LMP_Spell33"
    m = model.load(data)
    m.translations["LMP-Spell33"] = model.normalize_translation(
        "LMP-Spell33", {"translation": "a spell", "site": "Thebes (Egypt)", "words": []})
    descs = indexes.descs(m)
    assert descs["wiki/linear-a/inscriptions/LMP"].startswith("The Keftiu incantation of the London Medical Papyrus")
    assert not any(folder.startswith("wiki/linear-a/inscriptions/LMP/") for folder in descs)


@LIVE
def test_live_every_override_desc_names_a_folder_the_build_fills():
    model, indexes = views("model"), views("indexes")
    descs = indexes.descs(model.load(LINEAR_A_DATA))
    for folder, desc in model.OVERRIDES["descs"].items():
        assert descs.get(folder) == desc, folder


def test_the_build_fills_a_folder_desc_only_where_none_is_written(data, tmp_path, backups):
    build, markdown = views("build"), views("markdown")
    out = tmp_path / "out"
    args = ["--data", str(data), "--out", str(out)]
    desc = lambda path: markdown.parse_frontmatter(path.read_text(encoding="utf-8")).get("desc")
    assert build.main([*args, "--write"]) == 0
    k, a = out / "linear-a" / "words" / "K" / "_index.md", out / "linear-a" / "words" / "A" / "_index.md"
    assert desc(k) == "Words whose first sign begins with K."
    assert build.main(args) == 0
    k.write_text("---\nname: wiki/linear-a/words/K\ndesc: ...\ntags: []\n---\n\n# K\n", encoding="utf-8")
    a.write_text('---\ndesc: "My own words."\n---\n', encoding="utf-8")
    assert build.main(args) == 1  # the placeholder is pending
    assert build.main([*args, "--write"]) == 0
    assert desc(k) == "Words whose first sign begins with K." and "tags: []" in k.read_text(encoding="utf-8")
    assert desc(a) == "My own words."
    assert build.main(args) == 0
    [saved] = backups.glob("*.tar")
    with tarfile.open(saved) as tar:
        assert tar.getnames() == ["linear-a/words/K/_index.md"]


# ---------------------------------------------------------------- ledgers

LEDGERS = ("counts", "standing", "by_site", "by_root", "by_sign")


def test_counts_come_from_the_data_and_not_stored_stats(data):
    model, ledgers = views("model"), views("ledgers")
    unread = json.loads((data / "unread_words.json").read_text(encoding="utf-8"))
    unread["stats"] = {"unread_listed": 987654}
    (data / "unread_words.json").write_text(json.dumps(unread, ensure_ascii=False), encoding="utf-8")
    pages = dict(ledgers.pages(model.load(data)))
    assert sorted(pages) == sorted(f"wiki/linear-a/{name}" for name in LEDGERS)
    counts = pages["wiki/linear-a/counts"]
    for row in ("| Translated inscriptions (complete) | 2 |", "| Translations incomplete | 2 |",
                "| Corpus records | 16 |", "| Documents | 13 |", "| Lexicon entries | 3 |", "| Unread words listed | 2 |",
                "| GORILA, labelled | 5 |", "| RILA-S1 accepted | 1 |", "| unresolved | 1 |",
                "| syllabic | 1 | 1 | 3 | 2 |", "| logograms | 1 | 1 | 1 | 0 |", "| fractions | 1 | 1 | 0 | 0 |"):
        assert row in counts, row
    assert not any("987654" in text for text in pages.values())


def test_the_standing_table_lists_every_entry_once_by_tier(data):
    model, ledgers = views("model"), views("ledgers")
    text = dict(ledgers.pages(model.load(data)))["wiki/linear-a/standing"]
    assert "| Word | Reading | Meaning | Score |" in text
    for form in ("KU-PA₃-NU", "A-DU", "OLE+KI"):
        assert text.count(f"[[{model.word_path(form)}\\|") == 1, form
    assert text.index("## PROBABLE") < text.index("## CANDIDATE")


def test_by_root_groups_by_the_browse_key_and_keeps_roots_unlinked(data):
    model, ledgers = views("model"), views("ledgers")
    text = dict(ledgers.pages(model.load(data)))["wiki/linear-a/by_root"]
    assert "| ʔdd | ʾ-d-d |" in text
    assert "(no root)" in text
    assert "semitic-roots" not in text


def test_by_sign_counts_the_forms_written_with_a_subscript(data):
    model, ledgers = views("model"), views("ledgers")
    m = model.load(data)
    m.sign_values["signs"]["PA3"] = {"primary": {"consonant": "p", "vowel": "a"}, "linear_b": None}
    m.sign_status = model.sign_status(m.sign_values)
    text = dict(ledgers.pages(m))["wiki/linear-a/by_sign"]
    assert (f"| [[{model.sign_path('syllabic', 'PA3')}\\|PA3]] | syllabic | speculative | 1 | "
            f"[[{model.word_path('KU-PA₃-NU')}\\|KU-PA₃-NU]] |") in text


def test_the_build_writes_the_ledgers(data, tmp_path):
    out = tmp_path / "out"
    assert views("build").main(["--data", str(data), "--out", str(out), "--write"]) == 0
    assert all((out / "linear-a" / f"{name}.md").exists() for name in LEDGERS)


# ---------------------------------------------------------------- Aegean

AEGEAN = {
    "eteocretan_inscriptions.json": {"inscriptions": [{
        "id": "ETEOCRETAN_DREROS_1", "common_name": "First Dreros bilingual", "site": "Dreros",
        "object_type": "grey schist block", "date": "late 7th century BCE", "script": "archaic Cretan alphabet",
        "direction": "sinistrorse", "current_transliteration": ["--.ρμαϜ|ετ|ισαλαβρε|̣κομν"],
        "greek_parallel_text": "TON TYRON", "gordon_transliteration": ["]RMAW . ET"],
        "gordon_word_readings": [{"form": "AMO", "meaning": "for his mother", "basis": "Greek MATRI parallel",
                                  "constraint": "bilingual"}],
        "campaign_reconciliation": {"INAI": "CAMPAIGN-TEXT"}, "source_refs": ["Gordon 1966 §§19-50"],
        "relationship_to_linear_a": "comparandum_only", "status": "SOURCE_BACKED"}]},
    "eteocretan_word_analysis.json": {"words": [{
        "inscription_id": "ETEOCRETAN_DREROS_1", "site": "Dreros", "form": "AMO", "gordon_meaning": "for his mother",
        "root": "*ʾumm-ō", "basis": "Greek MATRI parallel", "constraint_type": "bilingual",
        "campaign_note": "CAMPAIGN-NOTE", "status": "SOURCE_BACKED"}]},
    "phaistos_disc.json": {
        "metadata": {"title": "Phaistos Disc Corpus", "authors": "Fixture Author", "version": "1.4",
                     "updated": "2026-10-19", "site": "Phaistos palace, room 8", "material": "fired clay, stamped"},
        "signs": {"01": {"number": 1, "unicode": "U+101D0", "name": "PEDESTRIAN", "description": "Walking figure"},
                  "12": {"number": 12, "unicode": "U+101DB", "name": "SHIELD", "description": "Round shield",
                         "la_correspondence": {"la_sign": "AB78", "la_value": "qe",
                                               "bridge_confidence": "EXPLORATORY-ADOPTED",
                                               "bridge_basis": "PD 12 / AB78 qe (Duhoux 1983, 34 n. 2)",
                                               "alternative_readings": []}},
                  "combining_oblique_stroke": {"unicode": "U+101FD", "name": "COMBINING OBLIQUE STROKE",
                                               "description": "Diacritical slash mark"}},
        "transcription": {
            "side_A": [{"group": "A1", "signs": [12, 1], "has_oblique_stroke": True,
                        "proposed_readings": {"partial_transliteration": "qe-?", "coverage_pct": 50,
                                              "confidence": "EXPLORATORY"}}],
            "side_B": [{"group": "B1", "signs": [1], "has_oblique_stroke": False,
                        "proposed_readings": {"partial_transliteration": "?", "coverage_pct": 0,
                                              "confidence": "EXPLORATORY"}}]}},
    "phaistos_disc_sign_map.json": {"metadata": {"authors": "Fixture Author"}, "sign_bridge": [
        {"pd_sign": 12, "pd_name": "SHIELD", "ch_correspondent": "CH_047", "la_correspondent": "AB78",
         "la_phonetic_value": "qe", "bridge_confidence": "EXPLORATORY-ADOPTED", "bridge_basis": "PD 12 / AB78 qe"}]},
}


def aegean_data(data: Path) -> Path:
    for name, content in AEGEAN.items():
        (data / name).write_text(json.dumps(content, ensure_ascii=False), encoding="utf-8")
    return data


def test_aegean_pages_leave_name_and_sources_to_wiki_update(data):
    markdown = views("markdown")
    for path, text in views("aegean").pages(aegean_data(data)).items():
        assert not {"name", "sources"} & set(markdown.parse_frontmatter(text)), path


def test_no_aegean_pages_without_their_files(data):
    assert views("aegean").pages(data) == {}


def test_eteocretan_page_keeps_the_text_in_a_code_block_and_leaves_campaign_fields_out(data):
    pages = views("aegean").pages(aegean_data(data))
    text = pages["wiki/aegean/eteocretan/ETEOCRETAN_DREROS_1"]
    assert "```text\n--.ρμαϜ|ετ|ισαλαβρε|̣κομν\n```" in text
    assert "| AMO | for his mother |" in text
    assert "CAMPAIGN" not in text


def test_phaistos_pages_merge_the_bridge_and_leave_the_file_metadata_out(data):
    pages = views("aegean").pages(aegean_data(data))
    assert {"wiki/aegean/phaistos_disc/disc", "wiki/aegean/phaistos_disc/signs/PD01",
            "wiki/aegean/phaistos_disc/signs/PD12",
            "wiki/aegean/phaistos_disc/signs/combining_oblique_stroke"} <= set(pages)
    disc = pages["wiki/aegean/phaistos_disc/disc"]
    assert "EXPLORATORY" in disc and "qe-?" in disc and "fired clay" in disc
    assert "held scholarship" not in disc
    assert "[[wiki/aegean/phaistos_disc/signs/PD12\\|12]]" in disc
    shield = pages["wiki/aegean/phaistos_disc/signs/PD12"]
    assert "CH\\_047" in shield or "CH_047" in shield
    assert "A1" in shield  # the groups it occurs in
    assert not any("Fixture Author" in text or "2026-10-19" in text for text in pages.values())


def test_aegean_page_paths_are_ascii_identifiers(data):
    aegean_data(data)
    inscriptions = json.loads((data / "eteocretan_inscriptions.json").read_text(encoding="utf-8"))
    inscriptions["inscriptions"][0]["id"] = "../Dreros 1"
    (data / "eteocretan_inscriptions.json").write_text(json.dumps(inscriptions, ensure_ascii=False), encoding="utf-8")
    disc = json.loads((data / "phaistos_disc.json").read_text(encoding="utf-8"))
    disc["signs"]["combining oblique/stroke"] = disc["signs"].pop("combining_oblique_stroke")
    (data / "phaistos_disc.json").write_text(json.dumps(disc, ensure_ascii=False), encoding="utf-8")
    pages = views("aegean").pages(data)
    assert "wiki/aegean/eteocretan/Dreros_1" in pages
    for path in pages:
        name = path.rsplit("/", 1)[1]
        assert name.isascii() and name.isidentifier(), path


def test_two_aegean_ids_on_one_path_are_refused(data):
    aegean_data(data)
    inscriptions = json.loads((data / "eteocretan_inscriptions.json").read_text(encoding="utf-8"))
    inscriptions["inscriptions"].append({**inscriptions["inscriptions"][0], "id": "ETEOCRETAN-DREROS-1"})
    (data / "eteocretan_inscriptions.json").write_text(json.dumps(inscriptions, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError, match="DREROS"):
        views("aegean").pages(data)


def test_the_amathus_control_is_not_called_eteocretan(data):
    aegean_data(data)
    inscriptions = json.loads((data / "eteocretan_inscriptions.json").read_text(encoding="utf-8"))
    inscriptions["inscriptions"].append({
        "id": "ETEOCYPRIOTE_AMATHUS_CONTROL", "common_name": "Amathus bilingual control", "site": "Amathus, Cyprus",
        "date": "Hellenistic", "relationship_to_linear_a": "eteocypriote_control_only", "status": "PARTIAL",
        "current_transliteration": []})
    (data / "eteocretan_inscriptions.json").write_text(json.dumps(inscriptions, ensure_ascii=False), encoding="utf-8")
    pages = views("aegean").pages(data)
    fields = views("markdown").parse_frontmatter(pages["wiki/aegean/eteocretan/ETEOCYPRIOTE_AMATHUS_CONTROL"])
    assert fields["desc"] == "Eteocypriot control inscription, Amathus, Cyprus, Hellenistic; partial."
    assert "eteocypriot" in fields["tags"] and "eteocretan" not in fields["tags"]
    dreros = views("markdown").parse_frontmatter(pages["wiki/aegean/eteocretan/ETEOCRETAN_DREROS_1"])
    assert dreros["desc"].startswith("Eteocretan inscription, Dreros") and "eteocretan" in dreros["tags"]


def test_the_build_writes_the_aegean_pages(data, tmp_path):
    out = tmp_path / "out"
    assert views("build").main(["--data", str(aegean_data(data)), "--out", str(out), "--write"]) == 0
    assert (out / "aegean" / "eteocretan" / "ETEOCRETAN_DREROS_1.md").exists()
    assert (out / "aegean" / "phaistos_disc" / "signs" / "PD12.md").exists()
    assert views("build").main(["--data", str(data), "--out", str(out)]) == 0


def test_the_build_writes_the_root_pages_from_the_sibling_folder(data, tmp_path):
    roots = tmp_path / "semitic-roots"
    roots.mkdir()
    (roots / "semitic_roots.json").write_text(json.dumps({"schema_version": 2, "description": "x", "roots": [
        {"id": "1", "ps": "*bayt-", "meaning": "house", "basis": {"ps": "sed", "meaning": "sed"},
         "reflexes": []}]}), encoding="utf-8")
    out = tmp_path / "out"
    assert views("build").main(["--data", str(data), "--out", str(out), "--write"]) == 0
    assert (out / "semitic-roots" / "b" / "1_house.md").exists()
    index = views("markdown").parse_frontmatter((out / "semitic-roots" / "b" / "_index.md").read_text(encoding="utf-8"))
    assert index["desc"] == "Semitic roots whose first radical is b."
    assert views("build").main(["--data", str(data), "--out", str(out)]) == 0


# ---------------------------------------------------------------- the build

def test_check_is_the_default_and_writes_nothing(data, tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    (out / "keep.md").write_text("untouched\n", encoding="utf-8")
    before, data_before = snapshot(out), snapshot(data)
    code = views("build").main(["--data", str(data), "--out", str(out)])
    assert code == 1  # every page is missing
    assert snapshot(out) == before and snapshot(data) == data_before


@pytest.mark.parametrize("mode", [[], ["--write"]])
def test_a_missing_data_file_stops_the_build_with_its_name(data, tmp_path, capsys, mode):
    (data / "unread_words.json").unlink()
    out = tmp_path / "out"
    out.mkdir()
    assert views("build").main(["--data", str(data), "--out", str(out), *mode]) == 2
    assert "unread_words.json is not in this checkout" in capsys.readouterr().err
    assert not any(out.iterdir())


def test_write_is_deterministic_and_then_current(data, tmp_path):
    build = views("build")
    first, second = tmp_path / "first", tmp_path / "second"
    assert build.main(["--data", str(data), "--out", str(first), "--write"]) == 0
    assert build.main(["--data", str(data), "--out", str(second), "--write"]) == 0
    pages = tree(first)
    assert pages == tree(second)
    assert any(name.endswith("KU_PA3_NU.md") for name in pages)
    assert not any(re.search(rb"20\d\d-\d\d-\d\d", body) for body in pages.values())
    assert build.main(["--data", str(data), "--out", str(first)]) == 0


def test_check_fails_on_stale_and_orphaned_pages(data, tmp_path):
    build = views("build")
    out = tmp_path / "out"
    assert build.main(["--data", str(data), "--out", str(out), "--write"]) == 0
    lexicon = json.loads((data / "lexicon.json").read_text(encoding="utf-8"))
    lexicon["entries"][0]["meaning"] = "a changed meaning"
    (data / "lexicon.json").write_text(json.dumps(lexicon, ensure_ascii=False), encoding="utf-8")
    assert build.main(["--data", str(data), "--out", str(out)]) == 1
    assert build.main(["--data", str(data), "--out", str(out), "--write"]) == 0
    [backup] = (tmp_path / "backups").glob("*.tar")
    with tarfile.open(backup) as tar:
        # only the pages that changed: the word's own, and the standing table, which shows its meaning
        assert sorted(Path(n).name for n in tar.getnames()) == ["KU_PA3_NU.md", "standing.md"]
    orphan = next(out.rglob("KU_PA3_NU.md")).with_name("NO_SUCH_FORM.md")
    orphan.write_text("orphan\n", encoding="utf-8")
    assert build.main(["--data", str(data), "--out", str(out)]) == 1
    assert build.main(["--data", str(data), "--out", str(out), "--write"]) == 1  # no --prune: refused, kept
    assert orphan.exists()


def test_backups_go_outside_the_repository_and_the_wiki(data, tmp_path, backups):
    paths, build = importlib.import_module("tools.paths"), views("build")
    assert not paths.BACKUPS.resolve().is_relative_to(paths.REPO)
    out = tmp_path / "repo" / "wiki"
    assert build.main(["--data", str(data), "--out", str(out), "--write"]) == 0
    lexicon = json.loads((data / "lexicon.json").read_text(encoding="utf-8"))
    lexicon["entries"][0]["meaning"] = "a changed meaning"
    (data / "lexicon.json").write_text(json.dumps(lexicon, ensure_ascii=False), encoding="utf-8")
    assert build.main(["--data", str(data), "--out", str(out), "--write"]) == 0
    assert len(list(backups.glob("*.tar"))) == 1
    assert not (out.parent / "backups").exists()


def test_prune_backs_up_and_deletes_an_orphan(data, tmp_path):
    build = views("build")
    out = tmp_path / "out"
    assert build.main(["--data", str(data), "--out", str(out), "--write"]) == 0
    orphan = next(out.rglob("KU_PA3_NU.md")).with_name("GONE.md")
    orphan.write_text(next(out.rglob("KU_PA3_NU.md")).read_text(encoding="utf-8"), encoding="utf-8")
    assert build.main(["--data", str(data), "--out", str(out), "--write", "--prune"]) == 0
    assert not orphan.exists()
    [backup] = (tmp_path / "backups").glob("*.tar")
    with tarfile.open(backup) as tar:
        assert [Path(n).name for n in tar.getnames()] == ["GONE.md"]
    assert build.main(["--data", str(data), "--out", str(out)]) == 0


def test_the_build_sees_its_pages_inside_a_dot_folder(data, tmp_path):
    build = views("build")
    out = tmp_path / ".config" / "wiki"
    assert build.main(["--data", str(data), "--out", str(out), "--write"]) == 0
    (out / ".obsidian").mkdir()
    (out / ".obsidian" / "settings.md").write_text("an editor's file\n", encoding="utf-8")
    assert build.main(["--data", str(data), "--out", str(out)]) == 0  # a dot folder inside the wiki is skipped
    page = next(out.rglob("KU_PA3_NU.md"))
    page.with_name("NO_SUCH_FORM.md").write_text(page.read_text(encoding="utf-8"), encoding="utf-8")
    assert build.main(["--data", str(data), "--out", str(out)]) == 1


def test_no_page_path_leaves_the_wiki_folder(tmp_path):
    build = views("build")
    out = tmp_path / "out"
    assert build.file_for(out, "wiki/linear-a/x") == out / "linear-a" / "x.md"
    for path in ("wiki/../../escape", "wiki/linear-a/../../../escape", "/etc/escape"):
        with pytest.raises(ValueError):
            build.file_for(out, path)


def test_the_build_refuses_two_sources_writing_one_page(data, tmp_path, monkeypatch):
    build = views("build")
    monkeypatch.setattr(views("aegean"), "pages", lambda folder: {"wiki/linear-a/standing": "a second page\n"})
    with pytest.raises(ValueError, match="standing"):
        build.main(["--data", str(data), "--out", str(tmp_path / "out")])


WIKI = shutil.which("wiki")


@pytest.mark.skipif(WIKI is None, reason="the plasma-wiki `wiki` command is not installed")
def test_the_builder_and_wiki_update_settle_on_one_tree(data, tmp_path):
    """One wiki at the repository root, as in kaphtor: after a build and a `wiki update`, neither tool would change
    a file, and `wiki lint` passes; the same after the data changes."""
    build = views("build")
    root = tmp_path / "repo"
    (root / ".wiki").mkdir(parents=True)
    (root / ".wiki" / "settings.json").write_text("{}\n", encoding="utf-8")
    args = ["--data", str(aegean_data(data)), "--out", str(root / "wiki"), "--backups", str(tmp_path / "backups")]

    def wiki(*command: str) -> int:
        return subprocess.run([WIKI, *command, "--path", str(root)], capture_output=True, text=True).returncode

    for change in (None, "a changed meaning"):
        if change:
            lexicon = json.loads((data / "lexicon.json").read_text(encoding="utf-8"))
            lexicon["entries"][0]["meaning"] = change
            (data / "lexicon.json").write_text(json.dumps(lexicon, ensure_ascii=False), encoding="utf-8")
        assert build.main([*args, "--write"]) == 0
        assert wiki("update") == 0
        assert build.main(args) == 0, change
        assert wiki("update", "--check") == 0, change
        assert wiki("lint") == 0, change
    page = next((root / "wiki").rglob("KU_PA3_NU.md")).read_text(encoding="utf-8")
    assert "name: wiki/linear-a/words/K/KU_PA3_NU" in page and "a changed meaning" in page


def test_write_refuses_uncommitted_changes_inside_git(data, tmp_path):
    import subprocess
    build = views("build")
    git = ["git", "-C", str(tmp_path), "-c", "user.name=t", "-c", "user.email=t@example.invalid"]
    subprocess.run(git + ["init", "-q"], check=True)
    out = tmp_path / "wiki"
    assert build.main(["--data", str(data), "--out", str(out), "--write"]) == 0  # a new folder: nothing to lose
    lexicon = json.loads((data / "lexicon.json").read_text(encoding="utf-8"))
    lexicon["entries"][0]["meaning"] = "a changed meaning"
    (data / "lexicon.json").write_text(json.dumps(lexicon, ensure_ascii=False), encoding="utf-8")
    before = snapshot(out)
    assert build.main(["--data", str(data), "--out", str(out), "--write"]) == 1  # the pages are not committed
    assert snapshot(out) == before
    subprocess.run(git + ["add", "-A", "wiki"], check=True)
    subprocess.run(git + ["commit", "-qm", "pages"], check=True)
    assert build.main(["--data", str(data), "--out", str(out), "--write"]) == 0


def test_write_refuses_a_folder_holding_pages_it_did_not_write(data, tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    (out / "page.md").write_text("someone's page\n", encoding="utf-8")
    before = snapshot(out)
    assert views("build").main(["--data", str(data), "--out", str(out), "--write"]) != 0
    assert snapshot(out) == before
