"""The language identification suite reads all eleven shipped reference inputs from the checkout.

Guards the default paths (`LSJ`, `LSJ_GLOSSES`, `DIODORUS`, `LATIN`, `LINEAR_B`, `EUPT`, `OSHB`, `TLHDIG`,
`ORACC_DIR` Akkadian/Sumerian, `SUMERIAN_LEX`, and `ORACC_LEVANT_NAMES`/`KASSITE_NAMES`): each names a shipped file,
the readers return the locked counts, and the Greek speller is found without a path outside the repository.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
KERNEL = REPO / "models/language-id-kernel"
sys.path.insert(0, str(KERNEL))
sys.path.insert(0, str(KERNEL / "render"))

import auto_anchors_j
import c_align
import c_render
import c_texts
import lid
import onomastics_h


def test_defaults_name_shipped_files():
    for path in (
        lid.LSJ,
        lid.DIODORUS,
        lid.LATIN,
        c_texts.LINEAR_B,
        c_texts.EUPT,
        c_texts.OSHB,
        c_texts.TLHDIG,
        lid.ORACC_DIR / "oracc_akkadian.jsonl",
        lid.ORACC_DIR / "oracc_sumerian.jsonl",
        auto_anchors_j.LSJ_GLOSSES,
        auto_anchors_j.SUMERIAN_LEX,
        onomastics_h.ORACC_LEVANT_NAMES,
        onomastics_h.KASSITE_NAMES,
    ):
        assert path.is_file(), path
        assert REPO in path.resolve().parents, f"{path} is outside the repository"


def test_diodorus_and_eupt_reader_counts():
    _, dio_stats = lid.diodorus_docs(lid.sign_keys())
    assert dio_stats == {"documents": 2465, "words": 81026, "left_out": 40531}
    ug = lid.segment_docs("ugaritic")
    assert len(ug) == 23
    assert sum(sum(w is not None for w in ws) for _, ws in ug) == 1618


def test_tlhdig_and_oracc_reader_counts():
    expected = {
        "hittite": (17631, 207306),
        "luwian": (140, 1054),
        "hurrian": (723, 9868),
        "hattic": (331, 2823),
        "akkadian_bo": (900, 15776),
        "akkadian": (1417, 72536),
        "sumerian": (1851, 7313),
    }
    for lang, (n_docs, n_clean) in expected.items():
        docs = lid.segment_docs(lang)
        assert len(docs) == n_docs, lang
        assert sum(sum(w is not None for w in ws) for _, ws in docs) == n_clean, lang


def test_kernel_j_and_h_shipped_lexica_and_names():
    with open(auto_anchors_j.LSJ_GLOSSES, encoding="utf-8") as fh:
        assert sum(1 for _ in fh) == 101410
    with open(auto_anchors_j.SUMERIAN_LEX, encoding="utf-8") as fh:
        assert sum(1 for _ in fh) == 3589
    tables, signs = c_render.load_tables(), lid.sign_keys()
    assert len(onomastics_h.extract_structural_roster_names()) == 57
    assert len(onomastics_h.load_oracc_levant_names(tables, signs, max_n=2000)) == 1314
    assert len(onomastics_h.load_kassite_names(tables, signs, max_n=5000)) == 3795


def test_linear_b_reader_counts():
    words, left_out = c_texts.linear_b(c_align.load_signs())
    assert (len(words), left_out) == (7883, 5371)


def test_lsj_reader_counts():
    words, stats = lid.lsj_words(lid.sign_keys())
    assert stats == {"words": 116431, "left_out": 699}
    assert len(words) == 116431


def test_greek_speller_is_found_in_the_repository():
    keys = lid.greek_keys("χρυσός", lid.sign_keys())
    assert keys == (("K", "u"), ("R", "u"), ("S", "o"))


def test_linear_b_text_only_on_rows_verified_against_damos():
    with open(c_texts.LINEAR_B, encoding="utf-8") as fh:
        rows = [json.loads(line) for line in fh]
    assert len(rows) == 13254
    for row in rows:
        verified = row["source_status"].startswith("DAMOS_VERIFIED")
        assert bool(row["token_normalized"]) == verified, row
