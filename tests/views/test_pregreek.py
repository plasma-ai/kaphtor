"""The Pre-Greek pages: one per word of pregreek_lexicon.json, filed by initial, with the feature and comparison
ledgers."""
import json
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.paths import PRE_GREEK_DATA, SEMITIC_ROOTS_DATA
from tools.views import pregreek, roots

WORKS = {
    "Beekes 2014": {"source_class": "closed", "verdicts": {"PG": "in the lexicon of Pre-Greek words",
                                                           "example": "cited as an example of the feature"}},
    "Rosół 2013": {"source_class": "closed", "verdicts": {"loan": "a Semitic loanword",
                                                          "rejected": "a Semitic etymology proposed and rejected"}},
    "Wiktionary": {"source_class": "web", "reference": "Wiktionary contributors."},
}
ENTRIES = [
    {"id": "pg:γυψοσ", "lemma": "γύψος", "key": "γυψοσ", "translit_key": "gupsos", "lemma_basis": "lsj",
     "variants": [], "variant_of": None,
     "sources": [{"work": "Rosół 2013", "loc": "34", "verdict": "loan", "source_class": "closed"},
                 {"work": "Wiktionary", "url": "https://en.wiktionary.org/wiki/x", "source_class": "web"}],
     "semitic_comparisons": [
         {"lang": "Akkadian", "form": "gaṣṣu", "cite": [{"siglum": "AHw", "loc": "282f"}], "by": "Rosół 2013",
          "work": "Rosół 2013", "loc": "34", "verdict": "loan", "cf": False, "gloss_withheld": True},
         {"lang": "Aramaic", "variety": "Hatra", "form": "gṣ", "variants": ["gṣṣ"], "by": "Rosół 2013",
          "work": "Rosół 2013", "loc": "34", "verdict": "loan", "cf": True}],
     "proto_semitic": {"id": "1", "form": "*gaṣṣ-"},
     "review_status": "machine_compiled"},
    {"id": "pg:αβδησ", "lemma": "ἄβδης", "key": "αβδησ", "translit_key": "abdes", "lemma_basis": "first_lane",
     "variants": ["ἄβδη"], "variant_of": None,
     "sources": [{"work": "Beekes 2014", "loc": "114", "section": "9.4", "verdict": "PG",
                  "features": ["2.2a.3", "3.2"], "source_class": "closed"},
                 {"work": "Rosół 2013", "loc": "155", "verdict": "rejected", "source_class": "closed"}],
     "semitic_comparisons": [
         {"lang": "Hebrew", "form": "ḥbṭ", "by": "Lewy 1895: 111", "work": "Rosół 2013", "loc": "155",
          "verdict": "rejected", "cf": False, "gloss_withheld": True}],
     "review_status": "machine_compiled"},
    {"id": "pg:αβδαλα", "lemma": "ἀβδάλα", "key": "αβδαλα", "translit_key": "abdala", "lemma_basis": "lsj",
     "variants": [], "variant_of": "pg:αβδησ",
     "sources": [{"work": "Beekes 2014", "loc": "10", "verdict": "example", "example_of": "2.2a.3", "toponym": True,
                  "source_class": "closed"}],
     "review_status": "machine_compiled"},
    {"id": "pg:κιλλιξ#2", "lemma": "κίλλιξ", "key": "κιλλιξ#2", "translit_key": "killix", "lemma_basis": "lsj",
     "variants": [], "variant_of": None,
     "sources": [{"work": "Wiktionary", "url": "https://en.wiktionary.org/wiki/x", "source_class": "web"}],
     "review_status": "machine_compiled"},
    {"id": "pg:ϝανακ σ", "lemma": "ϝάνακ ς", "key": "ϝανακ σ", "translit_key": "wanak s", "lemma_basis": "lsj",
     "variants": [], "variant_of": None,
     "sources": [{"work": "Wiktionary", "url": "https://en.wiktionary.org/wiki/x", "source_class": "web"}],
     "review_status": "machine_compiled"},
]
FEATURES = [{"id": "2.2a.3", "kind": "phonology", "chapter": 2, "printed_page": 10, "notation": "βδ"},
            {"id": "3.2", "kind": "suffix", "chapter": 3, "printed_page": 30},
            {"id": "2.10", "kind": "phonology", "chapter": 2, "printed_page": 40}]
GLOSSES = {"pg:γυψοσ": {"gloss": "chalk", "url": "https://en.wiktionary.org/wiki/x"}}
ROOTS = {"schema_version": 2, "description": "x", "roots": [
    {"id": "1", "ps": "*gaṣṣ-", "meaning": "gypsum", "basis": {"ps": "project", "meaning": "project"},
     "reflexes": []},
    {"id": "2", "ps": "*ḥbṭ", "meaning": "to beat", "basis": {"ps": "project", "meaning": "project"}, "reflexes": []}]}


def write(folder: Path, name: str, doc: dict) -> None:
    (folder / name).write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")


@pytest.fixture
def folders(tmp_path):
    pg, sr = tmp_path / "pre-greek", tmp_path / "semitic-roots"
    pg.mkdir()
    sr.mkdir()
    write(pg, pregreek.FILE, {"schema_version": 1, "description": "x", "works": WORKS, "entries": ENTRIES})
    write(pg, pregreek.FEATURES, {"schema_version": 1, "description": "x", "features": FEATURES})
    write(pg, pregreek.GLOSSES, {"schema_version": 1, "description": "x", "license": "CC BY-SA 4.0",
                                 "work": "Wiktionary", "glosses": GLOSSES})
    write(sr, roots.FILE, ROOTS)
    return pg, sr


def built(folders) -> dict[str, str]:
    return pregreek.pages(*folders)


def test_one_page_per_word_filed_by_initial_and_the_two_ledgers(folders):
    assert list(built(folders)) == [
        "wiki/pre-greek/by_feature", "wiki/pre-greek/semitic", "wiki/pre-greek/α/αβδαλα", "wiki/pre-greek/α/αβδησ",
        "wiki/pre-greek/γ/γυψοσ", "wiki/pre-greek/κ/κιλλιξ_2", "wiki/pre-greek/ϝ/ϝανακ_σ"]


def test_no_lexicon_no_pages(tmp_path):
    assert pregreek.pages(tmp_path, tmp_path) == {}
    assert pregreek.descs(tmp_path) == {}
    assert pregreek.by_root(tmp_path) == {}


def test_a_homograph_keeps_its_number_in_the_title_and_out_of_the_link(folders):
    text = built(folders)["wiki/pre-greek/κ/κιλλιξ_2"]
    assert '\ntitle: "κίλλιξ (2)"\n' in text and "# κίλλιξ (2)" in text
    assert "#2]]" not in text and "#2|" not in text


def test_the_word_page_shows_its_sources_features_and_comparisons(folders):
    text = built(folders)["wiki/pre-greek/α/αβδησ"]
    assert '\ndesc: "Greek ἄβδης (abdes), in the Pre-Greek lexicon: treated by 2 works, with 1 Semitic comparison."\n' \
        in text
    assert "| Headword from | the first work's spelling |" in text
    assert "| Variants | ἄβδη |" in text
    assert "| Beekes 2014 | 114 | 9.4 | PG | 2.2a.3 βδ, 3.2 |" in text
    assert "| Rosół 2013 | 155 |  | rejected |  |" in text
    assert "| Hebrew | ḥbṭ |  | Lewy 1895: 111 | Rosół 2013, 155 | rejected | gloss withheld |" in text
    assert "| Review | compiled from the works' indexes, not reviewed by hand |" in text
    gypsum = built(folders)["wiki/pre-greek/γ/γυψοσ"]
    assert "| Akkadian | gaṣṣu | AHw 282f | Rosół 2013 | Rosół 2013, 34 | loan | gloss withheld |" in gypsum
    assert "| Aramaic (Hatra) | gṣ, gṣṣ |  | Rosół 2013 | Rosół 2013, 34 | loan | for comparison |" in gypsum


def test_a_word_without_comparisons_says_nothing_of_them(folders):
    text = built(folders)["wiki/pre-greek/α/αβδαλα"]
    assert "Semitic comparison" not in text
    assert "| Beekes 2014 | 10 |  | example | example of 2.2a.3 βδ; a toponym |" in text


def test_variants_link_both_ways(folders):
    pages = built(folders)
    assert "| Variant of | [[wiki/pre-greek/α/αβδησ\\|ἄβδης]] |" in pages["wiki/pre-greek/α/αβδαλα"]
    assert "| Variants with a record | [[wiki/pre-greek/α/αβδαλα\\|ἀβδάλα]] |" in pages["wiki/pre-greek/α/αβδησ"]


def test_no_field_the_page_does_not_name_reaches_it(folders, tmp_path):
    """A gloss, note or text of a closed work, were one to slip into the lexicon, is never printed."""
    pg, sr = folders
    planted = json.loads(json.dumps(ENTRIES))
    planted[1]["gloss"] = "PLANTED-GLOSS"
    planted[1]["note"] = "PLANTED-NOTE"
    planted[1]["sources"][0]["gloss"] = "PLANTED-SOURCE"
    planted[1]["semitic_comparisons"][0]["gloss"] = "PLANTED-COMPARISON"
    write(pg, pregreek.FILE, {"schema_version": 1, "description": "x", "works": WORKS, "entries": planted})
    text = "".join(pregreek.pages(pg, sr).values())
    assert "PLANTED" not in text


def test_only_a_word_page_shows_a_wiktionary_gloss_and_always_with_its_licence(folders):
    pages = built(folders)
    gypsum = pages["wiki/pre-greek/γ/γυψοσ"]
    assert "| Gloss | chalk |" in gypsum and "| Licence | CC BY-SA 4.0 |" in gypsum
    assert pregreek.ATTRIBUTION in gypsum and "https://creativecommons.org/licenses/by-sa/4.0/" in gypsum
    for path, text in pages.items():
        if path != "wiki/pre-greek/γ/γυψοσ":
            assert "chalk" not in text and "Wiktionary gloss" not in text and pregreek.ATTRIBUTION not in text


def test_proto_semitic_links_the_root_page_and_nothing_else_does(folders):
    pages = built(folders)
    assert "| Proto-Semitic root | [[wiki/semitic-roots/g/1_gypsum\\|\\*gaṣṣ-]] |" in pages["wiki/pre-greek/γ/γυψοσ"]
    # ἄβδης compares ḥbṭ, the form of root 2, but no hand review ties it there
    assert "semitic-roots" not in pages["wiki/pre-greek/α/αβδησ"]
    assert pregreek.by_root(folders[0]) == {"1": [("wiki/pre-greek/γ/γυψοσ", "γύψος")]}


def test_a_proto_semitic_id_the_root_file_lacks_is_refused(folders):
    pg, sr = folders
    planted = json.loads(json.dumps(ENTRIES))
    planted[0]["proto_semitic"] = {"id": "999", "form": "*x"}
    write(pg, pregreek.FILE, {"schema_version": 1, "description": "x", "works": WORKS, "entries": planted})
    with pytest.raises(ValueError, match="999"):
        pregreek.pages(pg, sr)


def test_by_feature_lists_the_words_naming_each_feature_and_its_examples(folders):
    text = built(folders)["wiki/pre-greek/by_feature"]
    assert ("| 2.2a.3 | βδ | phonology | 10 | [[wiki/pre-greek/α/αβδησ\\|ἄβδης]] "
            "| [[wiki/pre-greek/α/αβδαλα\\|ἀβδάλα]] |") in text
    assert "| 3.2 |  | suffix | 30 | [[wiki/pre-greek/α/αβδησ\\|ἄβδης]] |  |" in text
    rows = [line.split(" | ")[0] for line in text.splitlines() if line.startswith(("| 2", "| 3"))]
    assert rows == ["| 2.2a.3", "| 2.10", "| 3.2"]


def test_the_semitic_ledger_groups_by_language_and_verdict(folders):
    text = built(folders)["wiki/pre-greek/semitic"]
    headings = [line for line in text.splitlines() if line.startswith("#")]
    assert headings == ["# Pre-Greek words with a Semitic comparison", "## Akkadian", "### loan", "## Aramaic",
                        "### loan", "## Hebrew", "### rejected"]
    assert "Rosół 2013: a Semitic etymology proposed and rejected." in text
    assert "| [[wiki/pre-greek/α/αβδησ\\|ἄβδης]] | ḥbṭ |  | Lewy 1895: 111 | Rosół 2013, 155 |" in text
    assert "| [[wiki/pre-greek/γ/γυψοσ\\|γύψος]] | gṣ, gṣṣ (Hatra) |  | Rosół 2013 | Rosół 2013, 34 |" in text


def test_each_folder_has_a_desc(folders):
    descs = pregreek.descs(folders[0])
    assert list(descs) == ["wiki/pre-greek", "wiki/pre-greek/α", "wiki/pre-greek/γ", "wiki/pre-greek/κ",
                           "wiki/pre-greek/ϝ"]
    assert descs["wiki/pre-greek/κ"] == "Pre-Greek words whose key begins with κ."


def test_every_link_names_a_page_the_build_writes(folders):
    pages = built(folders)
    targets = set(pages) | {p.rsplit("/", 1)[0] + "/_index" for p in pages} | set(roots.pages(folders[1]))
    links = {m for text in pages.values() for m in re.findall(r"\[\[([^\]|\\]+)", text)}
    assert links and links <= targets


ABSENT = pytest.mark.skipif(not (PRE_GREEK_DATA / pregreek.FILE).exists()
                            or not (SEMITIC_ROOTS_DATA / roots.FILE).exists(),
                            reason="the Pre-Greek lexicon or the root database is not in this checkout")


@pytest.mark.data
@ABSENT
def test_live_one_page_per_word_and_every_gloss_attributed():
    lexicon = json.loads((PRE_GREEK_DATA / pregreek.FILE).read_text(encoding="utf-8"))
    glosses = json.loads((PRE_GREEK_DATA / pregreek.GLOSSES).read_text(encoding="utf-8"))["glosses"]
    pages = pregreek.pages(PRE_GREEK_DATA, SEMITIC_ROOTS_DATA)
    assert len(pages) == len(lexicon["entries"]) + 2
    attributed = [p for p, text in pages.items() if pregreek.ATTRIBUTION in text]
    assert len(attributed) == len(glosses)
    assert all("## Wiktionary gloss" in pages[p] for p in attributed)
    assert sum("## Wiktionary gloss" in text for text in pages.values()) == len(glosses)
