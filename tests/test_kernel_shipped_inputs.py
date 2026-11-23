"""The language identification suite reads its LSJ and Linear B inputs from the checkout.

Guards the two defaults (`KAPHTOR_LSJ_JSONL`, `KAPHTOR_LINEAR_B_JSONL`): each names a shipped file, the readers
return the counts the signed runs were made on, and the Greek speller is found without a path outside the repository.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
KERNEL = REPO / "models/language-id-kernel"
sys.path.insert(0, str(KERNEL))
sys.path.insert(0, str(KERNEL / "render"))

import c_align
import c_texts
import lid


def test_defaults_name_shipped_files():
    for path in (lid.LSJ, lid.DIODORUS, lid.LATIN, c_texts.LINEAR_B, c_texts.EUPT, c_texts.OSHB):
        assert path.is_file(), path
        assert REPO in path.resolve().parents, f"{path} is outside the repository"


def test_diodorus_and_eupt_reader_counts():
    _, dio_stats = lid.diodorus_docs(lid.sign_keys())
    assert dio_stats == {"documents": 2465, "words": 81026, "left_out": 40531}
    ug = lid.segment_docs("ugaritic")
    assert len(ug) == 23
    assert sum(sum(w is not None for w in ws) for _, ws in ug) == 1618


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
