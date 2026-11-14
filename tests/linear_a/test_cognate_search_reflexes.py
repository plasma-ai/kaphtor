"""cognate_search reads the whole of semitic_roots.json: a header's alternates one by one, an uncached word by
live search, a cache only while it matches the roots file, and the language cells through the root index.

The cache and the index of every test are written in tmp_path; the header and cache tests read the shipped roots.
MI-NA-TI and KU-KA-RU are test strings. No network.
"""
from __future__ import annotations

import json
import unicodedata

import pytest
from shoresh_inputs import SHORESH

from tools.core import root_index
from tools.linear_a import cognate_search as cs

pytestmark = SHORESH

RECORDS = [
    {"Number": "1097", "Proto-Semitic": "*kakkar-/*kikkar-", "Meaning": "'round loaf, disk; talent'",
     "Analogues": {"Ugaritic": "kkr 'talent' (DULAT 430)", "Hebrew": "kikkār 'round loaf, disk' (HALOT 473)"}},
    {"Number": "9001", "Proto-Semitic": "*lbn", "Meaning": "'white'", "Analogues": {"Arabic": "laban 'milk'"}},
]


@pytest.mark.parametrize("header, want", [
    ("*kakkar-/*kikkar-", ["kkkr"]),                       # two starred forms: one skeleton each, here the same
    ("*pas-/*pis-", ["ps"]),
    ("*zapp-/*zabb-", ["zpp", "zbb"]),
    ("*paraš- {} *paras-", ["prš", "prs"]),
    ("*napr- 1, *npr 2", ["npr"]),
    ("*dūd- < *dVwVd-", ["dd", "dwd"]),
    ("*w/nVpVṯ-", ["wpṯ", "npṯ"]),                         # one letter or the other
    ("*mi/ut-", ["mt"]),                                   # a vowel alternation leaves one skeleton
    ("*ytn ~ *ntn", ["ytn", "ntn"]),                       # the old separator still splits
    ("*ʔab-", ["ʔb"]),
])
def test_header_alternates_are_read_one_by_one(header, want):
    assert cs._extract_root_consonant_variants(header) == want


def test_no_shipped_header_is_glued_into_one_skeleton():
    """Every skeleton read from an alternating header is as long as one form in it, or one letter longer (the ʾ
    restored before a bare initial vowel). Letters are counted without their marks."""
    glued = []
    for rec in cs.load_semitic_roots():
        header = rec.get("Proto-Semitic") or ""
        if not any(sep in header for sep in ("/", "{}", ",", "<")):
            continue
        letters = max(len(cs._header_letters(part)) for part in cs._header_parts(header))
        for skel in cs._extract_root_consonant_variants(header):
            if sum(1 for ch in skel if not unicodedata.category(ch).startswith("M")) > letters + 1:
                glued.append((header, skel))
    assert glued == []


def _cache(tmp_path, monkeypatch, words, roots_sha):
    path = tmp_path / "cognate_cache.json"
    path.write_text(json.dumps(words), encoding="utf-8")
    (tmp_path / "cognate_cache.json.provenance.json").write_text(
        json.dumps({"semitic_roots_sha256": roots_sha}), encoding="utf-8")
    monkeypatch.setattr(cs, "CACHE_FILE", path)
    cs._cache_is_current.cache_clear()


CACHED_ROW = {"root": "*cached-", "language": "Proto-Semitic", "meaning": "from the cache", "distance": 0.0}


def _proto(result):
    return [m["root"] for m in result["matches"] if m["method"] == "proto_semitic"]


def test_a_word_the_cache_lacks_is_searched_live(tmp_path, monkeypatch):
    _cache(tmp_path, monkeypatch, {"KU-NI-SU": [CACHED_ROW]}, cs._sha256_file(root_index.DEFAULT_ROOTS))
    result = cs.search_cognates("MI-NA-TI")
    assert _proto(result) and "*cached-" not in _proto(result)
    assert result["proto_semitic_source"] == "live"


def test_a_current_cache_answers_a_word_it_holds(tmp_path, monkeypatch):
    _cache(tmp_path, monkeypatch, {"MI-NA-TI": [CACHED_ROW]}, cs._sha256_file(root_index.DEFAULT_ROOTS))
    result = cs.search_cognates("MI-NA-TI")
    assert _proto(result) == ["*cached-"]
    assert result["proto_semitic_source"] == "cache"


def test_a_cache_built_from_another_roots_file_is_not_read(tmp_path, monkeypatch):
    _cache(tmp_path, monkeypatch, {"MI-NA-TI": [CACHED_ROW]}, "0" * 64)
    result = cs.search_cognates("MI-NA-TI")
    assert _proto(result) and "*cached-" not in _proto(result)
    assert result["proto_semitic_source"] == "live (cache stale)"


@pytest.fixture
def index(tmp_path, monkeypatch):
    roots = tmp_path / "semitic_roots.json"
    roots.write_text(json.dumps(RECORDS, ensure_ascii=False), encoding="utf-8")
    path = tmp_path / "x.sqlite"
    root_index.write_index(path, roots, lexica=())
    monkeypatch.setattr(root_index, "DEFAULT_INDEX", path)
    cs._reflex_keys.cache_clear()
    yield path
    cs._reflex_keys.cache_clear()


def test_a_reflex_in_a_language_cell_is_found(index):
    """Ugaritic kkr sits in the cells of *kakkar-/*kikkar-, whose header skeleton is kkkr."""
    rows = cs._search_reflexes_multi([("kkr", 0.0, "surface")], 40)
    row = next(r for r in rows if r["number"] == "1097")
    assert (row["method"], row["distance"], row["root"]) == ("reflex", 0.0, "*kakkar-/*kikkar-")
    assert (row["language"], row["form"]) == ("Ugaritic", "kkr")        # Ugaritic before Hebrew on a tie
    assert "9001" not in [r["number"] for r in rows]


def test_reflex_rows_are_added_on_request_and_change_no_other_row(index):
    on = cs.search_cognates("KU-KA-RU", top_n=40, use_cache=False, include_reflexes=True)
    off = cs.search_cognates("KU-KA-RU", top_n=40, use_cache=False)
    assert any(m["method"] == "reflex" and m["number"] == "1097" for m in on["matches"])
    assert not any(m["method"] == "reflex" for m in off["matches"])
    assert [m for m in on["matches"] if m["method"] != "reflex"] == off["matches"]


def test_a_missing_index_gives_no_reflex_rows_and_says_so(tmp_path, monkeypatch):
    monkeypatch.setattr(root_index, "DEFAULT_INDEX", tmp_path / "absent.sqlite")
    cs._reflex_keys.cache_clear()
    result = cs.search_cognates("KU-KA-RU", use_cache=False, include_reflexes=True)
    cs._reflex_keys.cache_clear()
    assert not any(m["method"] == "reflex" for m in result["matches"])
    assert "not built" in result["reflex_note"]


def test_an_index_built_from_other_roots_gives_no_reflex_rows_and_says_so(index, tmp_path):
    (tmp_path / "semitic_roots.json").write_text(json.dumps(RECORDS[:1], ensure_ascii=False), encoding="utf-8")
    cs._reflex_keys.cache_clear()
    result = cs.search_cognates("KU-KA-RU", use_cache=False, include_reflexes=True)
    assert not any(m["method"] == "reflex" for m in result["matches"])
    assert "index stale" in result["reflex_note"]
