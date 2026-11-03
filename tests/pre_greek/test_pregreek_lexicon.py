"""The Pre-Greek lexicon (data/pre-greek/): its ids are unique, every feature id and every `proto_semitic` id it cites
resolves, every work is in docs/bibliography.md or carries its full reference, the index rebuilds from the lexicon,
and no key falls outside the datasheet's fields. Nothing of a source's text ships: no quoted gloss in an entry, no
private path, email or source id, and no engine key or verdict.

Each check is a function that returns what it finds wrong. The `data` tests run it on the shipped files; the `unit`
tests hand it one planted defect and show it reports that defect, so each check can fail. Nothing here writes.
"""
import copy
import json
import re
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.ane.ane_keys import greek_fold, greek_skeleton, pregreek_index
from tools.paths import PRE_GREEK_DATA, SEMITIC_ROOTS_DATA

LEXICON = PRE_GREEK_DATA / "pregreek_lexicon.json"
FEATURES = PRE_GREEK_DATA / "pregreek_features.json"
GLOSSES = PRE_GREEK_DATA / "pregreek_wiktionary_glosses.json"
INDEX = PRE_GREEK_DATA / "pregreek_lexicon.index.json"
ROOTS = SEMITIC_ROOTS_DATA / "semitic_roots.json"
BIBLIOGRAPHY = ROOT / "docs" / "bibliography.md"
MISSING = [p.name for p in (LEXICON, FEATURES, GLOSSES, INDEX, ROOTS) if not p.exists()]
shipped = pytest.mark.skipif(bool(MISSING), reason=f"{', '.join(MISSING)} not in this checkout")

# The fields the datasheet names, at each depth.
SCHEMA = {
    "lexicon": {"schema_version", "description", "works", "entries"},
    "work": {"source_class", "verdicts", "reference"},
    "entry": {"id", "lemma", "key", "translit_key", "lemma_basis", "variants", "variant_of", "sources",
              "semitic_comparisons", "proto_semitic", "review_status"},
    "source": {"work", "loc", "section", "verdict", "features", "example_of", "toponym", "url", "source_class"},
    "comparison": {"lang", "variety", "form", "variants", "cite", "by", "work", "loc", "verdict", "cf",
                   "gloss_withheld"},
    "cite": {"siglum", "loc"},
    "proto_semitic": {"id", "form"},
    "features": {"schema_version", "description", "features"},
    "feature": {"id", "kind", "chapter", "printed_page", "notation"},
    "glosses": {"schema_version", "description", "license", "work", "glosses"},
    "gloss": {"gloss", "url"},
}
# The varieties the datasheet names; a comparison's `variety` is one of them.
VARIETIES = {"Neo-Assyrian", "Neo-Babylonian", "Neo-Assyrian and Neo-Babylonian", "Neo-Babylonian and Neo-Assyrian",
             "Late Babylonian", "syllabic Ugaritic", "Old Canaanite", "epigraphic Hebrew", "Mishnaic Hebrew",
             "Modern Hebrew", "Old Aramaic", "Early Aramaic", "Imperial Aramaic", "Hatra", "Deir Alla", "Palmyrene",
             "Christian Palestinian", "Samaritan", "epigraphic Judaic Aramaic", "colloquial Arabic", "Tunisian Arabic"}
# A source's gloss in quotation marks: 'axe', "Axt", “Axt”, ‘Axt’.
GLOSS = re.compile(r"(?<!\w)'(?:[^']|(?<=[\w.])'(?=\w))*?'(?!\w)")
DQ_GLOSS = re.compile(r'"[^"]*"|“[^”]*”|‘[^’]*’')
PRIVATE = re.compile(r"src_\d+|sources_database|/Users/|~/|\$HOME|expanduser|\.claude/")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
ENGINE_KEYS = {"d", "p", "score", "distance"}
ENGINE_VALUE = re.compile(r"\bPG_[A-Z]")
REFERENCE_DATE = re.compile(r"\b(?:1[5-9]|20)\d\d\b|\bn\.d\.|https?://")
GLOSS_WORDS = 12


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def strings(obj, path=""):
    """(path, string) for every string value inside obj."""
    if isinstance(obj, str):
        yield path, obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from strings(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from strings(v, f"{path}[{i}]")


def all_keys(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from all_keys(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from all_keys(v)


# --- the checks ------------------------------------------------------------------------------------------------------
def duplicate_ids(lexicon: dict) -> list[str]:
    seen, dup = set(), []
    for e in lexicon["entries"]:
        if e["id"] in seen:
            dup.append(e["id"])
        seen.add(e["id"])
    return dup


def unresolved_features(lexicon: dict, features: dict) -> list[str]:
    ids = {f["id"] for f in features["features"]}
    return [f"{e['id']}: {fid}" for e in lexicon["entries"] for s in e["sources"]
            for fid in s.get("features", []) + ([s["example_of"]] if "example_of" in s else []) if fid not in ids]


def unresolved_proto_semitic(lexicon: dict, root_ids: set[str]) -> list[str]:
    return [f"{e['id']}: {e['proto_semitic'].get('id')}" for e in lexicon["entries"]
            if "proto_semitic" in e and str(e["proto_semitic"].get("id")) not in root_ids]


def unreferenced_works(lexicon: dict, bibliography: str) -> list[str]:
    """Works neither listed in the bibliography (`**key**`) nor given a reference that opens with the key's first
    word (author or site) and gives a year, n.d. or URL."""
    listed = set(re.findall(r"^\*\*(.+?)\*\*", bibliography, re.MULTILINE))
    bad = []
    for key, work in lexicon["works"].items():
        reference = work.get("reference") or ""
        if key in listed:
            continue
        if not (reference.startswith(key.split()[0]) and REFERENCE_DATE.search(reference)):
            bad.append(key)
    return bad


def proposer_keys(by: str) -> list[str]:
    """The keys in a comparison's `by`: "Lewy 1895: 104; GEW: I, 814" gives Lewy 1895 and GEW. A piece that only
    continues the one before it ("II, 356") names no key."""
    keys = []
    for piece in by.split(";"):
        key = piece.split(":")[0].strip()
        if re.fullmatch(r"[A-ZÉ][^,]*", key) and (re.search(r"\d{4}", key) or key.isupper()):
            keys.append(key)
    return keys


def unlisted_citations(lexicon: dict, bibliography: str) -> list[str]:
    """Proposer keys (`by`) and sigla (`cite`) the bibliography lists nowhere: not as a work (`**key**`), not at
    second hand (`- **key**`), not as a siglum (`| siglum |`)."""
    listed = set(re.findall(r"^(?:- )?\*\*(.+?)\*\*", bibliography, re.MULTILINE))
    listed |= set(re.findall(r"^\| ([^|]+?) \|", bibliography, re.MULTILINE))
    cited = set()
    for e in lexicon["entries"]:
        for c in e.get("semitic_comparisons", []):
            cited.update(proposer_keys(c.get("by") or ""))
            cited.update(x["siglum"] for x in c.get("cite", []))
    return sorted(cited - listed)


def unknown_works(lexicon: dict) -> list[str]:
    return sorted({x["work"] for e in lexicon["entries"]
                   for x in e["sources"] + e.get("semitic_comparisons", []) if x["work"] not in lexicon["works"]})


def outside_schema(lexicon: dict, features: dict, glosses: dict) -> list[str]:
    bad = []

    def check(obj: dict, kind: str, where: str):
        extra = set(obj) - SCHEMA[kind]
        if extra:
            bad.append(f"{where}: {sorted(extra)}")

    check(lexicon, "lexicon", "lexicon")
    for key, work in lexicon["works"].items():
        check(work, "work", key)
    for e in lexicon["entries"]:
        check(e, "entry", e["id"])
        for s in e["sources"]:
            check(s, "source", e["id"])
        for c in e.get("semitic_comparisons", []):
            check(c, "comparison", e["id"])
            for x in c.get("cite", []):
                check(x, "cite", e["id"])
            if "variety" in c and c["variety"] not in VARIETIES:
                bad.append(f"{e['id']}: variety {c['variety']!r}")
        if "proto_semitic" in e:
            check(e["proto_semitic"], "proto_semitic", e["id"])
    check(features, "features", "features")
    for f in features["features"]:
        check(f, "feature", f["id"])
    check(glosses, "glosses", "glosses")
    for pid, g in glosses["glosses"].items():
        check(g, "gloss", pid)
    return bad


def misplaced_glosses(lexicon: dict, glosses: dict) -> list[str]:
    """Sidecar glosses on a word with no Wiktionary source, or longer than GLOSS_WORDS words."""
    wiktionary = {e["id"] for e in lexicon["entries"] for s in e["sources"] if s["work"] == "Wiktionary"}
    return [pid for pid, g in glosses["glosses"].items()
            if pid not in wiktionary or len(g["gloss"].split()) > GLOSS_WORDS]


def source_text(lexicon: dict) -> list[str]:
    """A quoted gloss anywhere in the entries; the `works` definitions and references are the project's own."""
    return [f"{path}: {s[:80]!r}" for path, s in strings(lexicon["entries"], "entries")
            if GLOSS.search(s) or DQ_GLOSS.search(s)]


def leaks(*docs: dict) -> list[str]:
    """A private path, source id or email in any value or key of any file."""
    out = []
    for i, doc in enumerate(docs):
        for path, s in list(strings(doc, f"file{i}")) + [(f"file{i} key", k) for k in all_keys(doc)]:
            if PRIVATE.search(s) or EMAIL.search(s):
                out.append(f"{path}: {s[:80]!r}")
    return out


def engine_output(*docs: dict) -> list[str]:
    """An engine key (d, p, score, distance) or a PG_ verdict. The index is not passed: its keys are skeletons
    (a one-consonant word's is `d` or `p`)."""
    out = []
    for i, doc in enumerate(docs):
        out += [f"file{i}: key {k!r}" for k in set(all_keys(doc)) & ENGINE_KEYS]
        out += [f"{path}: {s!r}" for path, s in strings(doc, f"file{i}") if ENGINE_VALUE.search(s)]
    return out


# --- the shipped files -----------------------------------------------------------------------------------------------
@pytest.fixture(scope="module")
def docs():
    return load(LEXICON), load(FEATURES), load(GLOSSES)


@pytest.mark.data
@shipped
def test_ids_are_unique(docs):
    assert not duplicate_ids(docs[0])


@pytest.mark.data
@shipped
def test_every_feature_id_resolves(docs):
    assert not unresolved_features(docs[0], docs[1])


@pytest.mark.data
@shipped
def test_every_proto_semitic_id_resolves_in_the_semitic_roots(docs):
    roots = {str(r["id"]) for r in load(ROOTS)["roots"]}
    assert not unresolved_proto_semitic(docs[0], roots)


@pytest.mark.data
@shipped
def test_a_planted_proto_semitic_id_fails_on_a_copy_of_the_shipped_lexicon(tmp_path):
    shutil.copy(LEXICON, tmp_path / LEXICON.name)
    lexicon = load(tmp_path / LEXICON.name)
    lexicon["entries"][0]["proto_semitic"] = {"id": "no-such-root", "form": "*x"}
    roots = {str(r["id"]) for r in load(ROOTS)["roots"]}
    assert unresolved_proto_semitic(lexicon, roots) == [f"{lexicon['entries'][0]['id']}: no-such-root"]


@pytest.mark.data
@shipped
def test_every_work_is_in_the_bibliography_or_carries_its_reference(docs):
    assert not unknown_works(docs[0])
    assert not unreferenced_works(docs[0], BIBLIOGRAPHY.read_text(encoding="utf-8"))


@pytest.mark.data
@shipped
def test_every_proposer_and_siglum_is_in_the_bibliography(docs):
    assert not unlisted_citations(docs[0], BIBLIOGRAPHY.read_text(encoding="utf-8"))


@pytest.mark.data
@shipped
def test_the_index_rebuilds_from_the_lexicon(docs):
    assert pregreek_index(docs[0]["entries"]) == load(INDEX)


@pytest.mark.data
@shipped
def test_no_key_outside_the_datasheet_fields(docs):
    assert not outside_schema(*docs)


@pytest.mark.data
@shipped
def test_wiktionary_glosses_sit_on_wiktionary_words(docs):
    assert docs[2]["license"] == "CC BY-SA 4.0"
    assert not misplaced_glosses(docs[0], docs[2])


@pytest.mark.data
@shipped
def test_no_source_text_leak_or_engine_output(docs):
    assert not source_text(docs[0])
    assert not leaks(*docs, load(INDEX))
    assert not engine_output(*docs)


# --- each check reports a planted defect ----------------------------------------------------------------------------
def toy():
    """A lexicon, features and glosses that pass every check: one word, two works."""
    entry = {"id": "pg:αξινη", "lemma": "ἀξίνη", "key": "αξινη", "translit_key": "axine", "lemma_basis": "lsj",
             "variants": ["ἀξίνα"], "variant_of": None,
             "sources": [{"work": "Rosół 2013", "loc": "21", "verdict": "probable_loan", "source_class": "closed"},
                         {"work": "Beekes 2014", "loc": "10", "verdict": "example", "example_of": "2.2a.3",
                          "source_class": "closed"},
                         {"work": "Wiktionary", "url": "https://en.wiktionary.org/wiki/x", "source_class": "web"}],
             "semitic_comparisons": [{"lang": "Akkadian", "variety": "Neo-Babylonian", "form": "ḫaṣṣīnnu",
                                      "cite": [{"siglum": "AHw", "loc": "332"}], "by": "Rosół 2013",
                                      "work": "Rosół 2013", "loc": "21", "verdict": "probable_loan", "cf": False,
                                      "gloss_withheld": True}],
             "review_status": "machine_compiled"}
    lexicon = {"schema_version": 1, "description": "d", "entries": [entry],
               "works": {"Rosół 2013": {"source_class": "closed", "verdicts": {"probable_loan": "probably a loan"},
                                        "reference": "Rosół, Rafał. 2013. *Frühe semitische Lehnwörter*."},
                         "Beekes 2014": {"source_class": "closed", "verdicts": {"example": "an example"}},
                         "Wiktionary": {"source_class": "web",
                                        "reference": "Wiktionary contributors. https://en.wiktionary.org/"}}}
    features = {"schema_version": 1, "description": "d",
                "features": [{"id": "2.2a.3", "kind": "phonology", "chapter": 2, "printed_page": 10, "notation": "βδ"}]}
    glosses = {"schema_version": 1, "description": "d", "license": "CC BY-SA 4.0", "work": "Wiktionary",
               "glosses": {"pg:αξινη": {"gloss": "axe", "url": "https://en.wiktionary.org/wiki/x"}}}
    return copy.deepcopy((lexicon, features, glosses))


BIB = "**Beekes 2014**\nBeekes, Robert S. P. 2014. *Pre-Greek*.\n"


def test_the_toy_passes_every_check():
    lexicon, features, glosses = toy()
    assert not duplicate_ids(lexicon) and not unresolved_features(lexicon, features)
    assert not unresolved_proto_semitic(lexicon, {"1570"}) and not unreferenced_works(lexicon, BIB)
    assert not unknown_works(lexicon) and not outside_schema(lexicon, features, glosses)
    assert not misplaced_glosses(lexicon, glosses) and not source_text(lexicon)
    assert not leaks(lexicon, features, glosses) and not engine_output(lexicon, features, glosses)


def test_a_duplicate_id_is_reported():
    lexicon, _, _ = toy()
    lexicon["entries"].append(copy.deepcopy(lexicon["entries"][0]))
    assert duplicate_ids(lexicon) == ["pg:αξινη"]


def test_an_unknown_feature_id_is_reported():
    lexicon, features, _ = toy()
    lexicon["entries"][0]["sources"][1]["example_of"] = "9.9"
    assert unresolved_features(lexicon, features) == ["pg:αξινη: 9.9"]


def test_an_unknown_proto_semitic_id_is_reported():
    lexicon, _, _ = toy()
    lexicon["entries"][0]["proto_semitic"] = {"id": "2339", "form": "*gaṣṣ-"}
    assert unresolved_proto_semitic(lexicon, {"1570"}) == ["pg:αξινη: 2339"]
    lexicon["entries"][0]["proto_semitic"]["id"] = "1570"
    assert not unresolved_proto_semitic(lexicon, {"1570"})


def test_a_work_without_bibliography_key_or_reference_is_reported():
    lexicon, _, _ = toy()
    del lexicon["works"]["Rosół 2013"]["reference"]
    lexicon["works"]["Wiktionary"]["reference"] = "Wiktionary contributors."
    assert unreferenced_works(lexicon, BIB) == ["Rosół 2013", "Wiktionary"]
    assert not unreferenced_works(lexicon, BIB + "**Rosół 2013**\n**Wiktionary**\n")


def test_an_unlisted_proposer_or_siglum_is_reported():
    lexicon, _, _ = toy()
    comparison = lexicon["entries"][0]["semitic_comparisons"][0]
    comparison["by"] = "Lewy 1895: 104; GEW: I, 814; Lagarde 1884-91: I, 384; II, 356"
    bib = "**Rosół 2013**\n- **Lewy 1895**: Lewy, H. (1895).\n"
    assert proposer_keys(comparison["by"]) == ["Lewy 1895", "GEW", "Lagarde 1884-91"]
    assert unlisted_citations(lexicon, bib) == ["AHw", "GEW", "Lagarde 1884-91"]
    bib += "- **Lagarde 1884-91**: Lagarde (1884-91).\n| GEW | Frisk |\n| AHw | von Soden |\n"
    assert not unlisted_citations(lexicon, bib)


def test_a_work_missing_from_works_is_reported():
    lexicon, _, _ = toy()
    lexicon["entries"][0]["sources"][0]["work"] = "Rosol 2013"
    assert unknown_works(lexicon) == ["Rosol 2013"]


def test_a_stale_index_fails_to_match_its_rebuild():
    lexicon, _, _ = toy()
    index = pregreek_index(lexicon["entries"])
    assert index == {"axine": ["pg:αξινη"], "αξινα": ["pg:αξινη"], "αξινη": ["pg:αξινη"], "k-s-n": ["pg:αξινη"]}
    lexicon["entries"][0]["variants"] = []
    assert pregreek_index(lexicon["entries"]) != index


def test_greek_keys_fold_and_skeletonise():
    assert greek_fold("Ἀξίνη") == "αξινη" and greek_fold("-ινθ-(ο-)") == "ινθο"
    assert greek_skeleton("κνέφας") == "k-n-p" and greek_skeleton("ἄγκυρα") == "n-k-r"
    assert greek_skeleton("ᾱ") is None


@pytest.mark.parametrize("plant", ["entry", "comparison", "source", "variety"])
def test_a_key_outside_the_fields_is_reported(plant):
    lexicon, features, glosses = toy()
    entry = lexicon["entries"][0]
    if plant == "entry":
        entry["gloss"] = "axe"
    elif plant == "comparison":
        entry["semitic_comparisons"][0]["gloss"] = "Axt"
    elif plant == "source":
        entry["sources"][0]["entry_id"] = "rosol-2013-p021-e01"
    else:
        entry["semitic_comparisons"][0]["variety"] = "neuassyrisch"
    assert len(outside_schema(lexicon, features, glosses)) == 1


def test_a_misplaced_or_long_gloss_is_reported():
    lexicon, _, glosses = toy()
    glosses["glosses"]["pg:αξινη"]["gloss"] = " ".join(["word"] * 13)
    assert misplaced_glosses(lexicon, glosses) == ["pg:αξινη"]
    _, _, glosses = toy()
    lexicon["entries"][0]["sources"].pop()  # the Wiktionary source
    assert misplaced_glosses(lexicon, glosses) == ["pg:αξινη"]


@pytest.mark.parametrize("form", ["ḫaṣṣīnnu 'axe'", "ḫaṣṣīnnu “Axt”", "ḫaṣṣīnnu ‘Axt’", 'ḫaṣṣīnnu "Axt"'])
def test_a_quoted_gloss_is_reported(form):
    lexicon, _, _ = toy()
    lexicon["entries"][0]["semitic_comparisons"][0]["form"] = form
    assert len(source_text(lexicon)) == 1


@pytest.mark.parametrize("value", ["21 src_1024", "/Users/someone/x.pdf", "~/notes", "mailto:a@example.org"])
def test_a_private_trace_is_reported(value):
    lexicon, features, glosses = toy()
    lexicon["entries"][0]["sources"][0]["loc"] = value
    assert len(leaks(lexicon, features, glosses)) == 1


def test_engine_output_is_reported():
    lexicon, features, glosses = toy()
    lexicon["entries"][0]["score"] = 0.93
    features["features"][0]["notation"] = "PG_STRONG"
    assert len(engine_output(lexicon, features, glosses)) == 2
