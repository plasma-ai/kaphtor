"""The names section: one page per name of onomasticon.json, filed by language layer, with the roots beneath them."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

from tools.paths import LINEAR_A_DATA
from tools.views import model, names, names_map

WIKILINK = re.compile(r"\[\[([^\]|\\]+)")


def name(token, affiliation="semitic", kind="personal_name", ref=True, **more):
    return {"token": token, "affiliation": affiliation, "type": kind, "lexicon_ref": token if ref else None,
            "reading": "x", "meaning": "y", "attestations": ["HT1"], "sites": ["Haghia Triada"], "frequency": 1,
            "type_confidence": "CANDIDATE", "affiliation_confidence": "CANDIDATE",
            "affiliation_evidence": "lexicon_reading", "note": "", **more}


def entry(word, root, **more):
    return {"word": word, "root": root, "confidence": "CANDIDATE", "tier": 2, **more}


def build(onomasticon, lexicon):
    return model.Model(corpus={}, lexicon={e["word"]: e for e in lexicon},
                       onomasticon={n["token"]: n for n in onomasticon}, unread={}, unread_statuses={},
                       translations={}, sign_values={}, census_classes={})


SMALL = build(
    [name("DA-NA", weak_cognates=[{"root": "d-n-n", "language": "Ugaritic", "distance": 0.2}],
          co_occurring_known=[{"word": "KU-RO", "reading": "kull", "meaning": "total"},
                              {"word": "SA-RA₂", "reading": "šarra", "meaning": "king"}]),
     name("SA-RA₂", kind="title"), name("YA-MU", kind="theonym"), name("PA-DE", affiliation="hurrian"),
     name("*306-TU", affiliation="unknown", ref=False, reading=None, meaning=None,
          weak_cognates=[{"root": "t-w", "language": "Hebrew", "distance": 0.3}])],
    [entry("DA-NA", "d-y-n", proto_semitic={"id": "12", "form": "*dīn-"}, note="One.\n\nTwo."),
     entry("SA-RA₂", "ḏ + š-r-r (king), a title", proto_semitic=[{"id": "1", "form": "*ḏ-"}]),
     entry("YA-MU", "š-r-r + -ān-"), entry("PA-DE", "š-r-r")])


def test_every_name_has_one_page_under_its_layer():
    pages = names.pages(SMALL)
    assert "wiki/names/semitic/names/DA_NA" in pages
    assert "wiki/names/hurrian/names/PA_DE" in pages
    assert "wiki/names/unread/names/star306_TU" in pages
    assert sum("/names/" in p.removeprefix("wiki/names/") for p in pages) == 5


def test_root_parts_drop_remarks_and_affixes():
    assert names.root_parts("ḏ + š-r-r (king), a title") == [("ḏ", ""), ("š-r-r", "king")]
    assert names.root_parts("Kubaba (Sumerian Kug-Baba, Haas 1994, 406) + -ān-") == [
        ("Kubaba", "Sumerian Kug-Baba, Haas 1994, 406")]
    assert names.root_parts(None) == []


def test_a_compound_name_stands_under_each_root_and_roots_stay_inside_their_layer():
    pages = names.pages(SMALL)
    semitic, hurrian = pages["wiki/names/semitic/roots/sh-r-r"], pages["wiki/names/hurrian/roots/sh-r-r"]
    assert "SA-RA₂" in semitic and "YA-MU" in semitic and "PA-DE" not in semitic
    assert "PA-DE" in hurrian and "SA-RA₂" not in hurrian
    assert "SA-RA₂" in pages["wiki/names/semitic/roots/dh"]
    # the Proto-Semitic form comes only from a name built on the root alone
    assert "\\*dīn-" in pages["wiki/names/semitic/roots/d-y-n"]
    assert "Proto-Semitic" not in semitic


def test_root_slugs_are_ascii_and_distinct():
    assert names.root_slug("ʿ-b-r") == "ayin-b-r"
    many = build([name("A"), name("B")], [entry("A", "ṣ-d-q"), entry("B", "ss-d-q")])
    roots = sorted(p for p in names.pages(many) if "/roots/" in p)
    assert roots == ["wiki/names/semitic/roots/ss-d-q", "wiki/names/semitic/roots/ss-d-q-2"]
    assert all(p.isascii() for p in names.pages(SMALL))


def test_an_unread_name_shows_no_comparison():
    page = names.pages(SMALL)["wiki/names/unread/names/star306_TU"]
    assert "No reading." in page
    assert "t-w" not in page and "Hebrew" not in page and "Distance" not in page
    assert "d-n-n" not in names.pages(SMALL)["wiki/names/semitic/names/DA_NA"]


def test_a_name_page_links_its_kind_layer_root_and_company():
    page = names.pages(SMALL)["wiki/names/semitic/names/DA_NA"]
    for target in ("wiki/names/guide/kinds/people", "wiki/names/semitic/_index", "wiki/names/semitic/roots/d-y-n",
                   "wiki/names/semitic/names/SA_RA2"):
        assert f"[[{target}" in page
    assert "| KU-RO | kull | total |" in page          # company that is no name is plain text
    assert "One.\n\nTwo." in page                        # a note keeps its paragraphs
    assert "CANDIDATE" in page and "tier" not in page    # the tier by name, never by number


def test_the_section_links_only_to_itself_and_no_link_is_dead():
    for data in (SMALL, model.load(LINEAR_A_DATA)):
        pages, descs, summaries = names.pages(data), names.descs(data), names.summaries(data)
        known = set(pages) | {f"{folder}/_index" for folder in descs}
        links = {t for text in [*pages.values(), *summaries.values()] for t in WIKILINK.findall(text)}
        assert links and not sorted(links - known)
        assert set(summaries) <= set(descs)


def test_the_shipped_record_has_a_page_for_every_name():
    data = model.load(LINEAR_A_DATA)
    pages = names.pages(data)
    assert sum(1 for text in pages.values() if 'kind: "name"\n' in text) == len(data.onomasticon)
    assert pages == names.pages(data)   # the same bytes on a second run


def test_descs_hold_no_count_and_summaries_count_from_the_data():
    assert not any(re.search(r"\d", d) for d in names.descs(SMALL).values())
    top = names.summaries(SMALL)["wiki/names"]
    assert "carry 5 names: 3 personal names, 1 divine name, 1 title." in top
    assert "| [[wiki/names/semitic/_index\\|Semitic]] | 3 | 3 |" in top
    assert "| Names | 1 |" in names.summaries(SMALL)["wiki/names/hurrian"]


def test_every_names_folder_has_a_title():
    titles = names.titles(SMALL)
    assert set(titles) == set(names.descs(SMALL))
    assert titles["wiki/names"] == "Linear A Names"
    assert titles["wiki/names/hurrian/roots"] == "Hurrian roots"
    assert "wiki/names/unread/roots" not in titles   # a layer with no root has no roots folder


def test_no_names_no_pages():
    empty = build([], [])
    assert names.pages(empty) == {} and names.descs(empty) == {} and names.summaries(empty) == {}
    assert names.titles(empty) == {}


def test_the_map_draws_one_dot_per_name_at_each_site_and_labels_only_the_larger_sites():
    both = name("KU-RA", sites=["Haghia Triada", "Zakros"])
    built = names.Names(build([both, name("DA-NA"), name("PA-DE", affiliation="hurrian"),
                               name("SI-DU", sites=["Zakros"]), name("TU-MA", sites=["Thera"]),
                               name("NO-WA", sites=[])], []))
    at = names_map.by_site(built)
    # a name found at two sites stands at both; one with no site is kept apart from the sites
    assert [n["token"] for n in at["Zakros"]] == ["KU-RA", "SI-DU"]
    assert len(at["Haghia Triada"]) == 3 and "Thera" in at
    found = names_map.clusters(at)
    assert [c["site"] for c in found] == ["Haghia Triada", "Zakros"]   # the largest first, Crete only
    drawn = names_map.svg(built)
    for layer in ("semitic", "hurrian"):
        assert names_map.COLORS[layer] in drawn
    dots = sum(drawn.count(f'fill="{colour}"/>') for colour in set(names_map.COLORS.values()))
    assert dots >= sum(len(c["names"]) for c in found)
    assert "Haghia Triada" in drawn and "Zakros" not in drawn.split("<text")[1]   # three names earn a label
    assert names_map.svg(built) == drawn                                         # the same bytes twice


def test_the_map_refuses_a_site_it_has_no_place_for():
    with pytest.raises(ValueError, match="Atlantis"):
        names_map.by_site(names.Names(build([name("DA-NA", sites=["Atlantis"])], [])))


def test_the_shipped_map_is_the_asset_the_builder_writes_and_its_page_names_every_site():
    loaded = model.load(LINEAR_A_DATA)
    files = names.assets(loaded)
    assert list(files) == ["wiki/names/guide/crete.svg"]
    drawn = files["wiki/names/guide/crete.svg"]
    assert drawn.startswith("<svg") and "<script" not in drawn and "http" not in drawn.replace("http://www.w3.org", "")
    built = names.Names(loaded)
    path, text = names_map.page(built)
    assert path == "wiki/names/guide/map" and "crete.svg" in text
    for site in names_map.by_site(built):
        assert site in text or site == names_map.NO_SITE
