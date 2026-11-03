"""D7 S3 on Linear A (docs/d7-structural-preregistration.md, signed by di Mino 2026-11-02): the X-TE/X-RE and X/X-TE
counts over the corpus's intact word types, against the controls' own permutation null.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tools.linear_a.validation import d7_s3_linear_a as s3
from tools.linear_a.validation import d7_structural_controls as d7

SCRIPT = Path(s3.__file__)
MARK = "\U0001076B"


def doc(translit: list[str], uni: list[str] | None = None) -> dict:
    return {"transliteratedWords": translit, "words": uni if uni is not None else ["x"] * len(translit)}


class TestIntactTypes:
    def test_a_lost_sign_or_a_damage_mark_on_the_only_witness_drops_the_word(self):
        corpus = {"A": doc(["KU-RO", "[KU]-TE", "PA-RE"], ["a", "b", "c" + MARK])}
        types, why = s3.intact_types(corpus)
        assert types == {("KU", "RO")}
        assert why["lost sign"] == 1 and why["damage mark"] == 1

    def test_a_clean_second_witness_keeps_the_word(self):
        corpus = {"A": doc(["PA-RE"], [MARK + "c"]), "B": doc(["PA-RE"], ["c"])}
        assert s3.intact_types(corpus)[0] == {("PA", "RE")}

    def test_numerals_single_signs_and_separators_are_not_words(self):
        corpus = {"A": doc(["TE", "5", "1-2", "\n", "𐄁", "KA-TE", "KU-", "-RE"])}
        assert s3.intact_types(corpus)[0] == {("KA", "TE")}      # a stray hyphen leaves one sign, not a word

    def test_signs_take_the_gold_guards_canonical_spelling(self):
        corpus = {"A": doc(["ra₂-te", "RA-TE"])}
        assert s3.intact_types(corpus)[0] == {("RA2", "TE"), ("RA", "TE")}

    def test_an_unaligned_unicode_layer_is_counted(self):
        corpus = {"A": {"transliteratedWords": ["KU-TE", "VIN"], "words": ["x"]}}
        types, why = s3.intact_types(corpus)
        assert types == {("KU", "TE")} and why["no aligned unicode"] == 1


class TestCounting:
    def test_the_counting_is_the_controls_own(self):
        assert s3.s3_test is d7.s3_test

    def test_the_registered_sign_sets(self):
        assert s3.NARROW == (("TE",), ("RE",)) and s3.BROAD == (("TE", "TI"), ("RE", "RI"))


class TestCli:
    def test_refuses_an_existing_out(self, tmp_path):
        out = tmp_path / "x.json"
        out.write_text("{}", encoding="utf-8")
        r = subprocess.run([sys.executable, str(SCRIPT), "--out", str(out)], capture_output=True, text=True)
        assert r.returncode == 2 and "never overwritten" in r.stderr
        assert json.loads(out.read_text(encoding="utf-8")) == {}

    def test_a_small_corpus_gives_its_counts(self, tmp_path):
        corpus = tmp_path / "corpus.json"
        corpus.write_text(json.dumps({"A": doc(["KU-TE", "KU-RE", "KU-RO", "KU-RO-TE", "SI-TI", "SI-RI", "MA-NA"])}),
                          encoding="utf-8")
        out = tmp_path / "s3.json"
        r = subprocess.run([sys.executable, str(SCRIPT), "--out", str(out), "--corpus", str(corpus), "--perm", "50"],
                           capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        rep = json.loads(out.read_text(encoding="utf-8"))
        assert rep["types"] == 7
        assert rep["narrow"]["te_re"]["observed"] == 1          # KU-TE / KU-RE
        assert rep["broad"]["te_re"]["observed"] == 2           # + SI-TI / SI-RI
        assert rep["narrow"]["bare_te"]["observed"] == 1        # KU-RO / KU-RO-TE
        assert rep["args"]["seed"] == 20261102 and len(rep["sha256"]["corpus.json"]) == 64
