"""D7 structural follow-on, controls only (docs/d7-structural-preregistration.md, rulings T1–T5): S1's edge alternation
and S3's -RE/-TE counts on each rival language's own running text. No Linear A word is read.
"""
from __future__ import annotations

import json
import random
import subprocess
import sys
from pathlib import Path

from shoresh_inputs import SHORESH

from tools.linear_a.validation import d7_structural_controls as d7

SCRIPT = Path(d7.__file__)


class TestKeys:
    def test_cuneiform_geminate_across_a_sign_boundary_collapses(self):
        assert d7.cuneiform_key("ḫa-at-ti-li") == (False, ("ḫ", "t", "l"))

    def test_cuneiform_repeat_across_a_vowel_stays(self):
        assert d7.cuneiform_key("ta-ta-ra") == (False, ("t", "t", "r"))

    def test_cuneiform_initial_vowel_and_index_accents(self):
        assert d7.cuneiform_key("ú-wa-aš") == (True, ("w", "š"))
        assert d7.cuneiform_key("e-eš-ša₂") == (True, ("š",))

    def test_cuneiform_logograms_determinatives_and_damage_are_out(self):
        for s in ("LUGAL", "mI-ni-DIŠKUR", "ḫa-[at]-ti", "ḫa-x-ti", "ša…", "ka-a-ru-u?", "", "a"):
            assert d7.cuneiform_key(s) is None, s

    def test_ugaritic_letters_are_consonants_and_aleph_vowels_drop(self):
        assert d7.ugaritic_key("ʾibsn") == (False, ("ʾ", "b", "s", "n"))
        assert d7.ugaritic_key("ṯql") == (False, ("ṯ", "q", "l"))
        assert d7.ugaritic_key("⸢ʾi⸣sʿ") is None and d7.ugaritic_key("b") is None   # one token: below S1's two

    def test_egyptian_separators_weak_radicals_and_names(self):
        assert d7.egyptian_key("nswt-bj,tj") == (False, ("n", "s", "w", "t", "b", "j", "t", "j"))
        assert d7.egyptian_key("mri̯") == (False, ("m", "r", "j"))
        assert d7.egyptian_key("Jmn") is None             # a name, as a determinative takes one out of cuneiform
        assert d7.egyptian_key("21.t") is None and d7.egyptian_key("(1)") is None


class TestSeries:
    pytestmark = SHORESH                              # lb_series reads the sign registry

    def test_gutturals_and_an_initial_vowel_are_bare_vowel_tokens(self):
        sub = d7.rm._sub
        assert d7.series_tokens((True, ("ḫ", "t", "ʾ")), sub, d7.lb_series()) == ("V", "V", "t", "V")

    def test_each_consonant_takes_its_arm_s_series(self):
        sub = d7.rm._sub
        assert d7.series_tokens((False, ("l", "ṣ")), sub, d7.lb_series()) == ("r", "z")


class TestSpelling:
    pytestmark = SHORESH

    def test_an_initial_vowel_is_a_first_vowel_sign_and_the_spelling_is_seeded(self):
        series = d7.lb_series()
        a = d7.spell_key((True, ("t", "r")), random.Random(5), series, d7.rm._sub)
        assert a == d7.spell_key((True, ("t", "r")), random.Random(5), series, d7.rm._sub)
        assert len(a) == 3 and a[0] in {"A", "E", "I", "O", "U"}
        assert d7.spell_key((False, ("t", "r")), random.Random(5), series, d7.rm._sub)[0][0] == "T"


class TestEdges:
    def test_left_and_right_pairs(self):
        words = {("t", "k"), ("w", "t", "k"), ("t", "k", "n"), ("a", "b", "t", "k"), ("t", "k", "m", "m")}
        assert d7.edge_pairs(words) == (2, 2)

    def test_the_shorter_word_needs_two_tokens_and_edges_at_most_two(self):
        assert d7.edge_pairs({("t",), ("w", "t")}) == (0, 0)
        assert d7.edge_pairs({("t", "k"), ("a", "b", "c", "t", "k")}) == (0, 0)

    def test_share_and_no_pairs(self):
        assert d7.l_share(3, 1) == 0.75 and d7.l_share(0, 0) is None

    def test_samples_are_seeded_and_short_sets_are_flagged(self):
        types = [("t", "k"), ("w", "t", "k"), ("t", "k", "n"), ("m", "n"), ("w", "m", "n")]
        a = d7.sample_shares(types, 4, 20, 7)
        assert a == d7.sample_shares(types, 4, 20, 7) and len(a["shares"]) == 20
        assert d7.sample_shares(types, 9, 20, 7) == {"limited": True, "types": 5}

    def test_central_interval(self):
        lo, hi = d7.interval([i / 100 for i in range(101)])      # linear interpolation, numpy's default
        assert (lo, hi) == (0.025, 0.975)
        assert d7.interval([]) is None


class TestGate:
    def test_disjoint_from_both_passes(self):
        iv = {"hattic": (0.6, 0.7), "ugaritic": (0.3, 0.5), "hurrian": (0.1, 0.2)}
        assert d7.gate(iv) == {"hurrian": True, "ugaritic": True, "passes": True}

    def test_overlap_with_ugaritic_fails_the_semitic_question(self):
        iv = {"hattic": (0.4, 0.7), "ugaritic": (0.3, 0.5), "hurrian": (0.1, 0.2)}
        assert d7.gate(iv) == {"hurrian": True, "ugaritic": False, "passes": False}

    def test_a_missing_interval_fails(self):
        assert d7.gate({"hattic": (0.4, 0.7), "ugaritic": None, "hurrian": (0.1, 0.2)})["passes"] is False


class TestS3:
    WORDS = frozenset({("A", "TE"), ("A", "RE"), ("A",), ("KU", "TE"), ("KU",), ("PA", "RE"), ("SI", "TI"), ("SI", "RI")})

    def test_narrow_counts(self):
        assert d7.s3_counts(self.WORDS, ("TE",), ("RE",)) == {"te_re": 1, "bare_te": 2}

    def test_broad_counts_take_ti_and_ri(self):
        assert d7.s3_counts(self.WORDS, ("TE", "TI"), ("RE", "RI")) == {"te_re": 2, "bare_te": 2}

    def test_the_permutation_keeps_final_sign_frequencies_by_length(self):
        rng = random.Random(1)
        perm = d7.permute_finals(sorted(self.WORDS), rng)
        by_len = lambda ws: sorted((len(w), w[-1]) for w in ws)
        assert by_len(perm) == by_len(sorted(self.WORDS))

    def test_permutation_p_is_seeded(self):
        a = d7.s3_test(sorted(self.WORDS), ("TE",), ("RE",), 200, 3)
        assert a == d7.s3_test(sorted(self.WORDS), ("TE",), ("RE",), 200, 3)
        assert 0 < a["te_re"]["p"] <= 1 and a["te_re"]["observed"] == 1


class TestCli:
    def test_refuses_an_existing_out(self, tmp_path):
        out = tmp_path / "x.json"
        out.write_text("{}", encoding="utf-8")
        r = subprocess.run([sys.executable, str(SCRIPT), "--out", str(out)], capture_output=True, text=True)
        assert r.returncode == 2 and "never overwritten" in r.stderr
        assert json.loads(out.read_text(encoding="utf-8")) == {}

    def test_there_is_no_linear_a_mode(self):
        src = SCRIPT.read_text(encoding="utf-8")
        assert "corpus.json" not in src and "--linear-a" not in src
