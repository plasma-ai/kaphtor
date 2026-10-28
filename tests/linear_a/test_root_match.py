"""Tests for tools/core/root_match.py (Shoresh). Every index is built in tmp_path from hand-written records; corpus
words are passed in, so no test reads an index, the corpus or a lexicon from data/."""
from __future__ import annotations

import itertools
import json
import math
import random
import unicodedata
from dataclasses import replace
from itertools import pairwise
from pathlib import Path

import pytest
from shoresh_inputs import SHORESH

from tools.core import root_match as rm
from tools.core import semantic_gate as sg
from tools.core.phonetics import SEMITIC_DISTANCES, _tokenize_phonemes, weighted_levenshtein
from tools.core.root_index import LEXICA, RootIndex, write_index
from tools.core.shoresh_nulls import fabricate, position_tables
from tools.core.skeleton import SIGN_STATUS

pytestmark = SHORESH

RECORDS = [
    {"Number": "1", "Proto-Semitic": "*kanVs-", "Meaning": "'to gather'", "Analogues": {"Hebrew": "knš 'gather'"}},
    {"Number": "2", "Proto-Semitic": "*mVlk-", "Meaning": "'king'", "Analogues": {"Ugaritic": "mlk id."}},
    {"Number": "3", "Proto-Semitic": "*ʾab-", "Meaning": "'father'", "Analogues": {}},
    {"Number": "5", "Proto-Semitic": "*ʾil-", "Meaning": "'god'", "Analogues": {}},
]
PHOENICIAN = [
    {"id": "p1", "language": "Phoenician", "root": "kns", "normalized": "kns", "meaning": "assemble",
     "semitic_roots_ref": ["1"]},
    {"id": "p3", "language": "Phoenician", "root": "tnt", "normalized": "tnt", "meaning": "Tanit", "pos": "DN",
     "semitic_roots_ref": ["5"]},
]
HEBREW = [{"id": "h9", "language": "Hebrew", "root": "p-t-r", "normalized": "ptr", "meaning": "interpret",
           "pos": "verb"}]
CORPUS = ["KA-NA-SI", "MA-RU-KU", "PA-I-TO", "SU-KI-RI-TA", "DI-KI-TE", "KU-NI-SU", "JA-SA-SA-RA-ME", "I-DA-MA-TE",
          "A-SA-SA-RA", "TA-NA-TI", "KI-RO", "KU-RO", "PO-TO-KU-RO", "DA-ME", "TE-TU", "NA-DA-RE", "MI-NU-TE",
          "QA-RA2-TI", "SE-KI-NA", "RA2-QA-NU"]


def _lex(name: str, path: Path):
    return replace(next(lx for lx in LEXICA if lx.name == name), path=path)


def _jsonl(path: Path, rows: list[dict]) -> Path:
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    return path


@pytest.fixture(scope="module")
def index(tmp_path_factory) -> RootIndex:
    d = tmp_path_factory.mktemp("shoresh")
    roots = d / "semitic_roots.json"
    roots.write_text(json.dumps(RECORDS, ensure_ascii=False), encoding="utf-8")
    lexica = (_lex("phoenician", _jsonl(d / "phoenician.jsonl", PHOENICIAN)),
              _lex("hebrew", _jsonl(d / "hebrew.jsonl", HEBREW)))
    write_index(d / "root_index.sqlite", roots, lexica)
    return RootIndex.load(d / "root_index.sqlite")


def _engine(index: RootIndex, **kw) -> rm.Shoresh:
    kw.setdefault("contexts", sg.Contexts({}))           # A18: no attested context, never the live corpus
    return rm.Shoresh(index, corpus_words=CORPUS, **kw)


def _toks(s: str) -> tuple[str, ...]:
    return tuple(_tokenize_phonemes(s))


# --- distance ---

ALPHABET = ["k", "q", "g", "ḫ", "ḥ", "ʿ", "ʾ", "h", "t", "ṭ", "d", "s", "š", "ṣ", "z", "ṯ", "l", "r", "n", "m", "p",
            "b", "w", "y"]


class TestDistance:
    def test_shoresh_table_adds_k_kh_and_leaves_the_shared_table_alone(self):
        assert rm.SHORESH_DISTANCES[("k", "ḫ")] == 0.3
        assert ("k", "ḫ") not in SEMITIC_DISTANCES and ("ḫ", "k") not in SEMITIC_DISTANCES
        assert rm.distance(("k",), ("ḫ",)) == rm.distance(("ḫ",), ("k",)) == 0.3

    def test_equals_weighted_levenshtein_bit_for_bit(self):
        rng = random.Random(1)
        for _ in range(2000):
            s1 = "".join(rng.choices(ALPHABET, k=rng.randint(0, 5)))
            s2 = "".join(rng.choices(ALPHABET, k=rng.randint(0, 6)))
            assert rm.distance(_toks(s1), _toks(s2)) == \
                weighted_levenshtein(s1, s2, rm.SHORESH_DISTANCES, guttural_transparent=True), (s1, s2)

    def test_cutoff_is_exact_at_or_under_it_and_inf_above(self):
        rng = random.Random(2)
        for _ in range(2000):
            t1 = _toks("".join(rng.choices(ALPHABET, k=rng.randint(1, 5))))
            t2 = _toks("".join(rng.choices(ALPHABET, k=rng.randint(1, 6))))
            exact = rm.distance(t1, t2)
            for cutoff in (0.0, 0.3, exact, exact - 1e-12, 1.0, 2.5):
                assert rm.distance(t1, t2, cutoff) == (exact if exact <= cutoff else rm.INF), (t1, t2, cutoff)

    def test_lower_bound_never_exceeds_the_distance(self):
        rng = random.Random(3)
        for _ in range(2000):
            t1 = _toks("".join(rng.choices(ALPHABET, k=rng.randint(1, 5))))
            t2 = _toks("".join(rng.choices(ALPHABET, k=rng.randint(1, 6))))
            visible = sum(t not in rm.GUTTURAL_PHONEMES for t in t2)
            assert rm._lower_bound(len(t1), len(t2), visible) <= rm.distance(t1, t2) + 1e-12, (t1, t2)


# --- signs and readings ---

class TestSigns:
    def test_polyphonic_options_primary_first(self):
        assert rm.sign_options("QA") == [("q", "a"), ("z", "a")]
        assert rm.sign_options("RA2") == [("l", "a"), ("r", "a")]
        assert rm.sign_options("KA") == [("k", "a")]

    @pytest.mark.parametrize("sign", ["ZU", "ZU2", "zu"])
    def test_zu_reads_the_interdental_range(self, sign):              # ṯ, its Linear B value z, ḏ and ṯ̣ (keyed ẓ)
        assert rm.sign_options(sign) == [("ṯ", "u"), ("z", "u"), ("ḏ", "u"), ("ẓ", "u")]

    def test_zu_reads_four_ways_and_the_inventory_writes_its_range(self, index):
        assert _engine(index)._reading_count(["ZU", "TI"]) == 4
        assert _engine(index, conventional=True)._reading_count(["ZU", "TI"]) == 1
        assert {"ṯ", "ḏ", "ẓ"} <= rm.written_consonants(rm._registry())
        assert not {"ṯ", "ḏ", "ẓ"} & rm.written_consonants(rm._registry(), conventional=True)

    @pytest.mark.parametrize("sign", ["A303", "a303", "A301", "ZZ"])
    def test_sign_numbers_and_unknown_signs_raise(self, sign):
        with pytest.raises(rm.UnmappedSign):
            rm.sign_decomposition(sign)

    def test_readings_are_capped_with_the_primary_first(self):
        opts = [rm.sign_options(s) for s in ["QA", "RA2", "QA", "RA2"]]       # 16 combinations
        rs = rm.readings(opts)
        assert len(rs) == rm.MAX_READINGS
        assert rs[0] == [o[0] for o in opts]

    @pytest.mark.parametrize("signs", [["ZU", "QA", "RA2"], ["ZU", "QA", "RA2", "QA"]])   # 16 and 32 readings
    def test_the_cap_keeps_the_same_readings_wherever_the_signs_stand(self, signs):
        kept = []
        for order in sorted(set(itertools.permutations(signs))):
            rs = rm.readings([rm.sign_options(s) for s in order])
            assert len(rs) == rm.MAX_READINGS and rs[0] == [rm.sign_options(s)[0] for s in order]
            kept.append({frozenset(zip(order, r)) for r in rs})
        assert all(k == kept[0] for k in kept)

    def test_the_cap_tells_signs_apart_that_share_a_primary(self):
        # family C can give two signs one permuted primary; their ties must still follow the signs, not the places
        signs = {"X": [("t", "a"), ("k", "a"), ("g", "a"), ("b", "a")],
                 "Y": [("t", "a"), ("m", "a"), ("n", "a"), ("p", "a")],
                 "W": [("q", "a"), ("z", "a")]}             # 32 readings; the cap cuts between X's and Y's second steps
        kept = []
        for order in itertools.permutations(signs):
            rs = rm.readings([signs[s] for s in order])
            kept.append({frozenset(zip(order, r)) for r in rs})
        assert all(k == kept[0] for k in kept)

    def test_the_cap_reaches_every_sign_s_alternates(self):
        rs = rm.readings([rm.sign_options(s) for s in ["ZU", "QA", "RA2"]])
        chosen = {p for r in rs for p in zip(["ZU", "QA", "RA2"], r)}
        assert {("ZU", ("ḏ", "u")), ("RA2", ("r", "a")), ("QA", ("z", "a"))} <= chosen

    def test_under_the_cap_the_readings_keep_their_order(self):
        opts = [rm.sign_options(s) for s in ["QA", "ZU", "TI"]]                 # 8 readings
        assert rm.readings(opts) == [list(r) for r in itertools.product(*opts)]

    def test_variants_keep_the_cheapest_penalty_per_skeleton(self):
        vs = rm.variants(rm.readings([rm.sign_options(s) for s in ["QA", "RA2", "TI"]]), "QA-RA2-TI")
        assert len({v.tokens for v in vs}) == len(vs)
        assert vs[0].penalty == min(v.penalty for v in vs)
        assert {v.reading for v in vs} >= {0, 1}              # the alternates are reached, not only the primary

    def test_distinct_orders(self):
        assert rm.distinct_orders(["KA", "NA", "SI"]) == 6
        assert rm.distinct_orders(["SA", "SA", "RA"]) == 3
        assert rm.distinct_orders(["A", "B", "C", "D", "E", "F"]) == 720


class TestConventionalValues:
    """Linear B values only: a sign whose value goes beyond Linear B reads its Linear B value, or is unmapped (A5)
    where Linear B gives none; a resolved value stays, and an alternate is kept only if its status is conventional."""

    @pytest.mark.parametrize("sign", ["*306", "*118", "*86", "*314", "*28B"])
    def test_a_sign_linear_b_gives_no_value_is_unmapped(self, sign):
        assert rm.sign_options(sign)
        with pytest.raises(rm.UnmappedSign):
            rm.sign_options(sign, conventional=True)

    @pytest.mark.parametrize("sign,default,linear_b", [
        ("PA3", ("b", "a"), ("p", "a")), ("PA₃", ("b", "a"), ("p", "a")), ("JU", ("l", "u"), ("y", "u")),
        ("ZU", ("ṯ", "u"), ("z", "u")), ("ZU2", ("ṯ", "u"), ("z", "u"))])                   # ZU2 reads as ZU
    def test_a_linear_b_sign_reads_its_linear_b_value(self, sign, default, linear_b):
        assert rm.sign_options(sign)[0] == default
        assert rm.sign_options(sign, conventional=True) == [linear_b]

    def test_the_tentative_linear_b_values(self):                            # *56 pa₃, *65 ju, *79 zu
        assert rm.LINEAR_B_VALUES == {"PA3": ("p", "a"), "JU": ("y", "u"), "ZU": ("z", "u")}
        assert all(SIGN_STATUS[s] != "resolved" for s in rm.LINEAR_B_VALUES)

    def test_every_status_but_resolved_is_gated(self):
        for sign, status in SIGN_STATUS.items():
            if status == "resolved":
                assert rm.sign_options(sign, conventional=True) == rm.sign_options(sign), sign
            elif sign in rm.LINEAR_B_VALUES:
                assert rm.sign_decomposition(sign, conventional=True) == rm.LINEAR_B_VALUES[sign], sign
            else:
                with pytest.raises(rm.UnmappedSign):
                    rm.sign_decomposition(sign, conventional=True)

    def test_linear_b_values_stay(self):
        for sign in ("KA", "AU", "QA", "RA2", "ZA", "KI2"):
            assert rm.sign_options(sign, conventional=True)[0] == rm.sign_options(sign)[0], sign

    def test_only_conventional_alternates_are_kept(self):
        assert rm.sign_options("QA", conventional=True) == [("q", "a")]                 # z is di Mino's
        assert rm.sign_options("RA2", conventional=True) == [("l", "a"), ("r", "a")]    # r is Ventris's

    def test_the_written_inventory_follows(self):
        reg = {"JU": {"readings": []}, "*306": {"readings": []}, "KA": {"readings": []}}
        assert rm.written_consonants(reg) == {"l", "ʿ", "k"}
        assert rm.written_consonants(reg, conventional=True) == {"y", "k"}

    def test_the_engine_inventory_is_the_spelling_series(self, index):    # A9's spelling rule with A21's ZU
        reg = {"JU": {"readings": []}, "*306": {"readings": []}, "KA": {"readings": []}}
        assert _engine(index, registry=reg).written == {"y", "k"}
        assert _engine(index, registry=reg, conventional=True).written == {"y", "k"}
        assert _engine(index).written == frozenset("dklmnpqrstwyz") | {"ṯ", "ḏ", "ẓ"}   # ZU, before every vowel
        assert _engine(index, conventional=True).written == frozenset("dklmnpqrstwyz")
        assert rm.spelled("ṯ", _engine(index).written) == "ṯ"
        assert rm.spelled("ṯ", _engine(index, conventional=True).written) == "z"

    def test_the_engine_reads_conventionally(self, index):
        default, conv = _engine(index), _engine(index, conventional=True)
        assert len(default.word_readings("QA-RA2-TI")) == 4 and len(conv.word_readings("QA-RA2-TI")) == 2
        assert default.word_readings("KU-PA3-NU") == [[("k", "u"), ("b", "a"), ("n", "u")]]
        assert conv.word_readings("KU-PA3-NU") == [[("k", "u"), ("p", "a"), ("n", "u")]]
        assert default.word_readings("KA-*306-TI")
        with pytest.raises(rm.UnmappedSign):
            conv.word_readings("KA-*306-TI")
        assert conv.conventional and not default.conventional

    def test_family_b_decoys_hold_no_gated_sign(self, index):
        words = [*CORPUS, "PA3-NU-KA", "ZU-KA-NA", "KA-*306-TI", "JU-NA-SI", "TA-*118-RE"]
        conv = rm.Shoresh(index, corpus_words=words, contexts=sg.Contexts({}), conventional=True)
        default = rm.Shoresh(index, corpus_words=words, contexts=sg.Contexts({}))
        gated, linear_b = {"*306", "*118"}, {"PA3", "ZU", "JU"}
        fabs, _ = conv.family_b("KA-NA-SI", 200, 1)
        drawn = {s for f in fabs for s in f}
        assert fabs and not drawn & gated and drawn & linear_b      # Linear B's pa₃, ju, zu are drawn
        fabs, _ = default.family_b("KA-NA-SI", 200, 1)
        assert {s for f in fabs for s in f} & gated                  # the default draws them

    def test_family_b_keeps_the_ocp_on_the_values_the_run_reads(self, index):
        words = [*CORPUS, "PA-PA3-KO", "ZA-ZU-SI", "PA3-PE-SI", "RA2-JU-NA", "KA-JU", "RA2-NA"]
        conv = rm.Shoresh(index, corpus_words=words, contexts=sg.Contexts({}), conventional=True)
        default = rm.Shoresh(index, corpus_words=words, contexts=sg.Contexts({}))

        def toks(engine, fab):
            return rm.phonemes(rm.skeleton_of(engine.word_readings("-".join(fab))[0]))
        for word in ("KA-NA-SI", "RA2-NA"):
            for engine in (conv, default):
                fabs, _ = engine.family_b(word, 400, 1)
                assert fabs and all(a != b for f in fabs for a, b in pairwise(toks(engine, f))), (word, engine)
        assert ["RA2", "JU"] in conv.family_b("RA2-NA", 400, 1)[0]                 # l y: kept
        assert ["RA2", "JU"] not in default.family_b("RA2-NA", 400, 1)[0]          # l l: out

    def test_the_reading_count_follows(self, index):
        assert _engine(index)._reading_count(["QA", "TI"]) == 2
        assert _engine(index, conventional=True)._reading_count(["QA", "TI"]) == 1

    def test_family_c_permutes_linear_b_consonants_only(self, index):
        project_only = {"ʿ", "ḥ", "h", "ṭ", "ṯ", "ḏ", "b"}          # written by no Linear B sign
        def consonants(engine, word):
            return {c for rs in engine.family_c(word, 300, 1) for r in rs for c, _ in r if c}
        assert consonants(_engine(index), "DA-TA-RE") & project_only               # the default draws them
        assert consonants(_engine(index), "QA-RA2-TI") & project_only
        assert not consonants(_engine(index, conventional=True), "DA-TA-RE") & project_only
        assert not consonants(_engine(index, conventional=True), "QA-RA2-TI") & project_only

    def test_family_c_permutes_the_conventional_consonants(self):
        cmap = rm.conventional_consonant_map()
        assert {s: cmap[s] for s in ("PA3", "JU", "ZU", "AU", "KA", "A")} == {
            "PA3": "p", "JU": "y", "ZU": "z", "AU": "w", "KA": "k", "A": None}
        assert not {"*306", "*118", "*86", "*314"} & set(cmap)
        assert set(cmap) == {s for s in rm.SIGN_DECOMPOSITION if not rm._beyond_linear_b(s) or s in rm.LINEAR_B_VALUES}

    def test_the_gate_fails_closed(self, monkeypatch):
        monkeypatch.setitem(rm.SIGN_DECOMPOSITION, "*82", ("s", "i"))     # a new value with no SIGN_STATUS entry
        assert rm.sign_options("*82") == [("s", "i")]
        with pytest.raises(rm.UnmappedSign):
            rm.sign_options("*82", conventional=True)

    def test_every_value_off_the_linear_b_grid_has_a_status(self):
        lb = {"D": "d", "J": "y", "K": "k", "M": "m", "N": "n", "P": "p", "Q": "q", "R": "r", "S": "s", "T": "t",
              "W": "w", "Z": "z"}

        def linear_b(sign: str, decomp: tuple) -> bool:
            if sign == "RA2":
                return decomp == ("l", "a")
            if len(sign) == 1:
                return decomp == ("", sign.lower()) or decomp == (None, sign.lower())
            return len(sign) == 2 and lb.get(sign[0]) == decomp[0] and sign[1].lower() == decomp[1]
        off = sorted(s for s, d in rm.SIGN_DECOMPOSITION.items() if not linear_b(s, d))
        assert off and all(s in SIGN_STATUS for s in off), [s for s in off if s not in SIGN_STATUS]


# --- the index as Shoresh reads it ---

class TestClusters:
    def test_exact_root_scores_zero(self, index):
        hits, _ = _engine(index).clusters("KA-NA-SI")
        assert hits[0].number == "1" and hits[0].distance == 0.0

    def test_unjoined_lexeme_is_no_cluster(self, index):
        hits, _ = _engine(index).clusters("PA-TA-RA")          # Hebrew ptr links to no Number
        assert all(h.distance > 0 for h in hits)

    def test_onomastic_lexeme_counts_only_with_names(self, index):
        assert index.lexemes["phoenician:p3"]["onomastic"]
        without, _ = _engine(index).clusters("TA-NI-TE")
        with_names, _ = _engine(index, names=True).clusters("TA-NI-TE")
        assert not any(h.number == "5" and h.distance == 0.0 for h in without)
        assert any(h.number == "5" and h.distance == 0.0 for h in with_names)

    def test_the_akkadian_block_is_flagged_never_dropped(self, tmp_path):
        recs = [{"Number": "2776", "Proto-Semitic": "*sakVn-", "Meaning": "'to dwell'", "Analogues": {}},
                {"Number": "2793", "Proto-Semitic": "*sakVn-", "Meaning": "'to dwell'", "Analogues": {}}]
        roots = tmp_path / "semitic_roots.json"
        roots.write_text(json.dumps(recs, ensure_ascii=False), encoding="utf-8")
        write_index(tmp_path / "x.sqlite", roots, lexica=())
        hits = {h.number: h.flags for h in _engine(RootIndex.load(tmp_path / "x.sqlite")).clusters("SA-KA-NA")[0]}
        assert hits == {"2776": ("akkadian_equivalent_block",), "2793": ()}

    def test_exclude_removes_a_number_and_the_lexemes_that_join_it(self, index):
        hits, _ = _engine(index, exclude={"1"}).clusters("KA-NA-SI")
        assert "1" not in {h.number for h in hits}
        assert all(h.distance > 0 for h in hits)


@pytest.fixture(scope="module")
def breadth_engine(tmp_path_factory) -> rm.Shoresh:
    d = tmp_path_factory.mktemp("breadth")
    recs = [{"Number": "1", "Proto-Semitic": "*kanVs-", "Meaning": "'to gather'",
             "Analogues": {"Hebrew": "knš 'gather'", "Akkadian": "kanāšu 'submit'"}},
            {"Number": "4", "Proto-Semitic": "*kVnVs-", "Meaning": "'to sweep'", "Analogues": {}}]
    roots = d / "semitic_roots.json"
    roots.write_text(json.dumps(recs, ensure_ascii=False), encoding="utf-8")
    lexica = (
        _lex("ugaritic", _jsonl(d / "u.jsonl", [{"id": "u1", "language": "Ugaritic", "normalized": "kns",
                                                  "meaning": "to gather"}])),                 # exact + gloss: gated
        _lex("geez", _jsonl(d / "g.jsonl", [{"id": "g1", "language": "Geez", "root": "k-n-s",
                                              "meaning": "congregare", "semitic_roots_ref": ["1"]}])),      # fk
        _lex("aramaic", _jsonl(d / "a.jsonl", [{"id": "a1", "language": "Aramaic", "root": "k-n-s",
                                                 "meaning": "wipe"}])),                        # no gloss: unjoined
    )
    write_index(d / "x.sqlite", roots, lexica)
    return _engine(RootIndex.load(d / "x.sqlite"))


class TestBreadth:
    """A12: branch breadth gated by gloss overlap, and the gloss-free count. PS keys are no branch."""

    def test_gated_and_gloss_free_branches(self, breadth_engine):
        hit = next(h for h in breadth_engine.clusters("KA-NA-SI")[0] if h.number == "1")
        assert hit.branches == ("Akkadian", "Geez", "Hebrew", "Ugaritic")
        assert hit.gloss_free == ("Akkadian", "Geez", "Hebrew")

    def test_top_breadth_is_the_broadest_cluster_at_d_star(self, breadth_engine):
        vs = rm.variants(breadth_engine.word_readings("KA-NA-SI"), "KA-NA-SI")
        assert breadth_engine.top_breadth(vs) == (0.0, 4, 3)          # 1 and 4 tie at 0; 4 has no branches

    def test_ties_across_distinct_keys_all_count(self, tmp_path):
        recs = [{"Number": "1", "Proto-Semitic": "*kanVṭ-", "Meaning": "'a'", "Analogues": {}},
                {"Number": "2", "Proto-Semitic": "*kanVṯ-", "Meaning": "'b'",
                 "Analogues": {"Hebrew": "knš id.", "Arabic": "kanaṯa id."}},
                {"Number": "3", "Proto-Semitic": "*ḫanVt-", "Meaning": "'c'", "Analogues": {}}]
        roots = tmp_path / "semitic_roots.json"
        roots.write_text(json.dumps(recs, ensure_ascii=False), encoding="utf-8")
        write_index(tmp_path / "x.sqlite", roots, lexica=())
        engine = _engine(RootIndex.load(tmp_path / "x.sqlite"))
        vs = rm.variants(engine.word_readings("KA-NA-TI"), "KA-NA-TI")
        d, gated, _ = engine.top_breadth(vs)                          # t ~ ṭ, t ~ ṯ, k ~ ḫ: all 0.3
        assert d == 0.3 and gated == 2

    def test_query_reports_breadth_against_family_b(self, breadth_engine):
        r = breadth_engine.query("KA-NA-SI", n=40)
        assert r.breadth["branches"] == 4 and r.breadth["gloss_free"] == 3
        b = r.breadth["decoys_B"]
        decoys, _ = breadth_engine.family_b("KA-NA-SI", 40, rm.SEED)
        tops = [breadth_engine.top_breadth(breadth_engine._variants_of(s)) for s in decoys]
        tops = [(g, f) for d, g, f in tops if d != rm.INF]
        assert b["n"] == len(tops) > 0
        assert b["share_ge"] == round(sum(g >= 4 for g, _ in tops) / len(tops), 4)
        assert b["share_ge_gloss_free"] == round(sum(f >= 3 for _, f in tops) / len(tops), 4)
        assert r.to_json()["breadth"] == r.breadth

    def test_equal_breadth_counts_toward_the_share(self, breadth_engine):
        real = breadth_engine._variants_of(["KA", "NA", "SI"])
        other = breadth_engine._variants_of(["KA", "NA", "TI"])         # a second decoy, any breadth
        b = breadth_engine._breadth(real, [real, other])["decoys_B"]
        _, g_other, f_other = breadth_engine.top_breadth(other)
        assert b["n"] == 2
        assert b["share_ge"] == (1 + (g_other >= 4)) / 2 and b["share_ge_gloss_free"] == (1 + (f_other >= 3)) / 2
        assert b["mean"] == round((4 + g_other) / 2, 4)

    def test_breadth_never_moves_p_or_the_verdict(self, breadth_engine):
        on = breadth_engine.query("KA-NA-SI", n=40)
        off = breadth_engine.query("KA-NA-SI", n=40, breadth_check=False)
        assert "decoys_B" not in off.breadth and off.breadth["branches"] == 4
        assert {k: f.p for k, f in on.families.items()} == {k: f.p for k, f in off.families.items()}
        assert on.verdict == off.verdict


# --- d*: decision mode, memo, brute force ---

def _decoy_variant_sets(engine: rm.Shoresh, n: int = 300) -> list[list[rm.Variant]]:
    rng = random.Random(4)
    signs = ["KA", "NA", "SI", "MA", "RA", "KU", "TA", "NI", "TE", "QA", "RA2", "PA", "I", "A", "DI", "SA", "RU"]
    out = []
    for _ in range(n):
        w = "-".join(rng.choices(signs, k=rng.randint(2, 5)))
        out.append(rm.variants(engine.word_readings(w), w))
    return out


class TestDStar:
    def test_cutoff_mode_equals_exact_mode(self, index):
        exact_engine, cut_engine = _engine(index), _engine(index)
        for vs in _decoy_variant_sets(exact_engine):
            exact = exact_engine.d_star(vs)
            for cutoff in (0.0, 0.15, 0.3, 1.0, exact):
                assert cut_engine.d_star(vs, cutoff) == (exact if exact <= cutoff else rm.INF)

    def test_memo_answers_an_exact_query_after_a_cutoff_query(self, index):
        fresh, reused = _engine(index), _engine(index)
        sets = _decoy_variant_sets(fresh, 100)
        for vs in sets:
            reused.d_star(vs, 0.1)
        for vs in sets:
            assert reused.d_star(vs) == fresh.d_star(vs)

    def test_brute_force_is_the_naive_minimum_with_cutoff_semantics(self, index):
        engine = _engine(index)
        entries = {id(e): e for e in engine._entry_of.values()}.values()
        for vs in _decoy_variant_sets(engine, 150):
            naive = min((rm._q(rm.distance(v.tokens, e.tokens) + v.penalty) for v in vs for e in entries),
                        default=rm.INF)
            assert engine.brute_force_d_star(vs) == naive
            for cutoff in (0.0, 0.3, 1.0, naive):
                assert engine.brute_force_d_star(vs, cutoff) == (naive if naive <= cutoff else rm.INF)

    def test_retrieval_never_beats_brute_force_and_matches_it_when_near(self, index):
        engine = _engine(index)
        for vs in _decoy_variant_sets(engine):
            got, brute = engine.d_star(vs), engine.brute_force_d_star(vs)
            assert brute <= got
            if brute <= 0.3:
                assert got == brute


# --- decoy families ---

class TestFamilies:
    def test_family_a_enumerates_every_other_order_when_few(self, index):
        decoys, orders = _engine(index).family_a("KA-NA-SI", 1000, rm.SEED)
        assert orders == 6 and len(decoys) == 5 and len({tuple(d) for d in decoys}) == 5
        assert ["KA", "NA", "SI"] not in decoys

    def test_family_a_counts_repeated_signs_once(self, index):
        decoys, orders = _engine(index).family_a("SA-SA-RA", 1000, rm.SEED)
        assert orders == 3 and sorted(decoys) == [["RA", "SA", "SA"], ["SA", "RA", "SA"]]

    def test_family_a_samples_when_orders_exceed_n(self, index):
        decoys, orders = _engine(index).family_a("A-DI-KI-TE-TE-DU-PU-RE", 50, rm.SEED)
        assert orders > 50 and len(decoys) == 50

    def test_family_a_samples_never_return_the_word_itself(self, index):
        engine = _engine(index)
        for seed in range(20):                      # 6 orders, 3 draws: the sampling path, where repeats are likely
            decoys, _ = engine.family_a("KA-NA-SI", 3, seed)
            assert len(decoys) == 3 and ["KA", "NA", "SI"] not in decoys

    def test_family_a_under_100_orders_is_not_in_p_max(self, index):
        r = _engine(index).query("KA-NA-SI", n=20, families="A")
        assert r.families["A"].orders == 6 and not r.families["A"].in_p_max
        assert r.p_max is None and "A1" in r.families["A"].note

    def test_family_b_matches_shape_and_is_never_a_real_word(self, index):
        engine = _engine(index)
        word = "QA-RA2-TI"
        decoys, gaps = engine.family_b(word, 40, rm.SEED)
        skel = len(_tokenize_phonemes(rm.skeleton_of(engine.word_readings(word)[0])))
        assert len(decoys) + gaps == 40 and decoys
        for d in decoys:
            assert len(d) == 3 and "-".join(d) not in CORPUS
            assert engine._reading_count(d) == 4
            assert len(_tokenize_phonemes(rm.skeleton_of(engine.word_readings("-".join(d))[0]))) == skel

    @pytest.mark.parametrize("word,count", [("RU-ZU-NA", 4), ("QA-NU-TI", 2)])
    def test_family_b_keeps_the_word_s_number_of_readings(self, index, word, count):
        words = [*CORPUS, "RU-ZU-NA", "ZU-KA-NA", "KA-ZU-SI", "SI-RA2-ZU", "QA-NU-TI", "TI-QA-SE"]
        engine = rm.Shoresh(index, corpus_words=words, contexts=sg.Contexts({}))
        decoys, _ = engine.family_b(word, 300, rm.SEED)
        counts = {math.prod(len(rm.sign_options(s)) for s in d) for d in decoys}
        assert decoys and counts == {count}

    def test_family_b_reports_an_unfabricable_shape_as_gaps(self, index):
        decoys, gaps = _engine(index).family_b("QA-QA-QA-QA-QA-QA", 30, rm.SEED)
        assert decoys == [] and gaps == 30

    def test_family_c_keeps_signs_vowels_and_reading_count(self, index):
        engine = _engine(index)
        word = "QA-RA2-TI"
        real = engine.word_readings(word)
        for decoy in engine.family_c(word, 50, rm.SEED):
            assert len(decoy) == len(real)
            assert [v for _, v in decoy[0]] == [v for _, v in real[0]]

    def test_family_c_vowel_sign_stays_consonantless(self, index):
        for decoy in _engine(index).family_c("A-KA-NA", 20, rm.SEED):
            assert decoy[0][0] == (None, "a")


# --- the query ---

class TestQuery:
    def test_seeded_and_independent_of_batch_order(self, index):
        a = _engine(index)
        a.query("MA-RA-KU", n=30)
        first = a.query("KA-NA-SI", n=30).to_json()
        assert first == _engine(index).query("KA-NA-SI", n=30).to_json()

    def test_two_consonants_is_uninformative(self, index):
        assert _engine(index).query("KA-NU", n=30).verdict == "UNINFORMATIVE"

    def test_no_retrieved_cluster_is_no_signal(self, index):
        r = _engine(index).query("TE-TU-PI", n=30)
        assert r.d_star == rm.INF and r.p_max is None and r.verdict == "NO_SIGNAL" and not r.families

    def test_exact_root_with_enough_decoys_is_phonological_only(self, index):
        r = _engine(index).query("KA-NA-SI", n=100)
        assert r.d_star == 0.0 and r.p_max < rm.P_SIGNAL and r.verdict == "PHONOLOGICAL_ONLY"

    def test_too_few_decoys_cannot_reach_signal(self, index):
        r = _engine(index).query("KA-NA-SI", n=10)                     # p ≥ 1/11
        assert r.p_max >= rm.P_SIGNAL and r.verdict == "NO_SIGNAL"

    def test_p_counts_ties_and_takes_the_max_family(self, index):
        r = _engine(index).query("KA-NU", n=100)                       # d* = 1.0: decoys tie it
        counted = [f for f in r.families.values() if f.in_p_max]
        assert all(f.tied for f in counted) and len({f.p for f in counted}) > 1
        for f in r.families.values():
            assert f.p == (1 + f.below + f.tied) / (1 + f.n)
        assert r.p_max == max(f.p for f in counted)
        assert r.families[r.deciding_family].p == r.p_max

    def test_streams_are_per_word_and_per_family(self):
        draw = lambda w, f: rm._rng(rm.SEED, w, f).random()
        assert draw("KA-NA-SI", "A") == draw("KA-NA-SI", "A")
        assert len({draw("KA-NA-SI", f) for f in "ABC"}) == 3
        assert draw("KA-NA-SI", "B") != draw("MA-RA-KU", "B")
        assert rm._rng(rm.SEED + 1, "KA-NA-SI", "A").random() != draw("KA-NA-SI", "A")

    def test_result_is_never_convergent_and_says_so(self, index):
        j = _engine(index).query("KA-NA-SI", n=30).to_json()
        assert j["verdict"] != "CONVERGENT" and j["footer"] == "Enters at SPECULATIVE."
        assert any("no semantic evidence" in n for n in j["notes"])      # A18: no attested context
        json.dumps(j)                                                   # serialisable, INF as null


# --- POS (§3.2): inherited from the joined lexemes, display only ---

POS_LEXICON = [
    {"id": "q1", "language": "Phoenician", "root": "kns", "normalized": "kns", "meaning": "assemble", "pos": "verb",
     "semitic_roots_ref": ["1"]},                                                  # fk: joins
    {"id": "q2", "language": "Phoenician", "root": "kns", "normalized": "kns", "meaning": "assembly", "pos": "noun",
     "semitic_roots_ref": ["1"]},
    {"id": "q3", "language": "Phoenician", "root": "kns", "normalized": "kns", "meaning": "Kinnas", "pos": "DN",
     "semitic_roots_ref": ["1"]},                                                  # onomastic: only with names
    {"id": "q4", "language": "Phoenician", "root": "kns", "normalized": "kns", "meaning": "bright",
     "pos": "adjective"},                                                          # exact sound, no gloss: unjoined
]


@pytest.fixture(scope="module")
def pos_index(tmp_path_factory) -> RootIndex:
    d = tmp_path_factory.mktemp("pos")
    roots = d / "semitic_roots.json"
    roots.write_text(json.dumps(RECORDS[:1], ensure_ascii=False), encoding="utf-8")
    write_index(d / "x.sqlite", roots, (_lex("phoenician", _jsonl(d / "p.jsonl", POS_LEXICON)),))
    return RootIndex.load(d / "x.sqlite")


class TestPOS:
    def _pos(self, index, **kw):
        return next(h for h in _engine(index, **kw).clusters("KA-NA-SA")[0] if h.number == "1").pos

    def test_joined_lexemes_give_the_cluster_its_pos(self, pos_index):
        assert ("1", "root_key_exact", False) in pos_index.links["phoenician:q4"]       # linked, never joined
        assert self._pos(pos_index) == ("noun", "verb")

    def test_names_add_the_onomastic_pos(self, pos_index):
        assert self._pos(pos_index, names=True) == ("DN", "noun", "verb")

    def test_the_gate_is_vacuous_and_says_so(self, pos_index):
        r = _engine(pos_index).query("KA-NA-SA", n=30)
        assert any("holds vacuously" in n for n in r.notes) and r.verdict != "CONVERGENT"
        assert r.clusters[0].number == "1" and r.clusters[0].pos == ("noun", "verb")
        assert json.loads(json.dumps(r.to_json()))["clusters"][0]["pos"] == ["noun", "verb"]


# --- sound laws (plan Phase 2, feature 2; report-only) ---

WRITTEN = frozenset("rtpnkdsmzwqyl")


def _cell(*alts: str, uncertain: bool = False) -> dict:
    return {"printed": "/".join(alts), "alternants": list(alts), "later": None, "uncertain": uncertain}


TABLE = {
    "branches": ["A", "B", "C"],
    "forward": {
        "*ḏ": {"A": _cell("z"), "B": _cell("d"), "C": _cell("ḏ")},             # C's ḏ is spelled z
        "*k": {"A": _cell("k"), "B": _cell("k"), "C": _cell("k")},
        "*r": {"A": _cell("r"), "B": _cell("r"), "C": _cell("r")},
        "*d": {"A": _cell("d"), "B": _cell("d"), "C": _cell("d")},
        "*ṭ": {"A": _cell("ṭ"), "B": _cell("ṭ"), "C": _cell("ṭ")},
        "*ṯ": {"A": _cell("š", uncertain=True), "B": _cell("t"), "C": _cell("Ø")},
    },
}


@pytest.fixture(scope="module")
def laws_engine(tmp_path_factory) -> rm.Shoresh:
    d = tmp_path_factory.mktemp("laws")
    recs = [{"Number": "7", "Proto-Semitic": "*ḏakar-", "Meaning": "'male'", "Analogues": {"Aramaic": "dkr id."}},
            {"Number": "8", "Proto-Semitic": "*zVkr-", "Meaning": "'remember'", "Analogues": {}},
            {"Number": "9", "Proto-Semitic": "*ḏVbaḥ- 1, *dVbaḥ- 2", "Meaning": "'sacrifice'", "Analogues": {}},
            {"Number": "3", "Proto-Semitic": "*ʾab-", "Meaning": "'father'", "Analogues": {}}]       # has weak keys
    roots = d / "semitic_roots.json"
    roots.write_text(json.dumps(recs, ensure_ascii=False), encoding="utf-8")
    write_index(d / "x.sqlite", roots, lexica=())
    return _engine(RootIndex.load(d / "x.sqlite"), correspondences=TABLE)


class TestSoundLaws:
    def test_alignment_costs_exactly_the_distance_and_covers_both_sides(self):
        rng = random.Random(4)
        for _ in range(2000):
            t1 = _toks("".join(rng.choices(ALPHABET, k=rng.randint(0, 5))))
            t2 = _toks("".join(rng.choices(ALPHABET, k=rng.randint(0, 6))))
            path = rm.alignment(t1, t2)
            cost = 0.0
            for i, j in path:                    # step by step, as the table adds (sum() compensates since 3.12)
                cost += rm._sub(t1[i], t2[j]) if i is not None and j is not None else \
                    1.0 if j is None else rm._ins(t2[j])
            assert cost == rm.distance(t1, t2), (t1, t2, path)
            assert [i for i, _ in path if i is not None] == list(range(len(t1)))
            assert [j for _, j in path if j is not None] == list(range(len(t2)))

    def test_alignment_ties_go_to_substitution(self):
        assert rm.alignment(("k", "k"), ("k",)) == [(0, None), (1, 0)]      # not [(0, 0), (1, None)]

    def test_spelled_is_the_a9_series_rule(self):
        from tools.linear_a.validation.root_match_checks import series_consonant
        series = {c: {} for c in WRITTEN}
        for c in ALPHABET + ["ḏ", "ẓ", "ś", "ġ", "f"]:
            want = series_consonant(c, series)
            if c in rm.GUTTURAL_PHONEMES and rm._sub(c, want) >= 1.0:
                want = None                                              # unwritten: a bare vowel sign
            assert rm.spelled(c, WRITTEN) == want, c
        assert rm.spelled("ḫ", WRITTEN) == "k" and rm.spelled("ḥ", WRITTEN) is None

    def test_reflex_tokens(self):
        assert rm._reflex_token("Ø") is None
        assert rm._reflex_token("s₁") == "s"
        assert rm._reflex_token("ḏ") == "ḏ"

    def test_written_consonants_are_the_registry_readings(self):
        reg = {"KA": {"readings": []}, "QA": {"readings": [{"consonant": "z"}]}, "A303": {"readings": []}}
        assert rm.written_consonants(reg) == {"k", "q", "z"}

    def test_diagnostic_radicals_intersect_into_the_profile(self):
        out = rm.sound_laws(("z", "k", "s"), ("ḏ", "k", "ṯ"), TABLE, WRITTEN)
        rows = {r["ps"]: r for r in out["positions"]}
        assert rows["*ḏ"]["status"] == "diagnostic" and rows["*ḏ"]["consistent"] == ["A", "C"]
        assert rows["*k"]["status"] == "not_diagnostic" and rows["*k"]["consistent"] == ["A", "B", "C"]
        assert rows["*ṯ"]["consistent"] == ["A"] and rows["*ṯ"]["uncertain"] == ["A"]
        assert out["profile"] == ["A"] and out["radicals"] == "ḏ-k-ṯ"
        assert [r["radical"] for r in out["positions"]] == [1, 2, 3]
        assert rm.sound_laws(("s", "k", "z"), ("ṯ", "k", "ḏ"), TABLE, WRITTEN)["profile"] == ["A"]   # every one

    def test_the_other_spelling_picks_the_other_branch(self):
        assert rm.sound_laws(("d", "k", "r"), ("ḏ", "k", "r"), TABLE, WRITTEN)["profile"] == ["B"]

    def test_no_diagnostic_radical_means_no_profile(self):
        out = rm.sound_laws(("k", "r"), ("k", "r"), TABLE, WRITTEN)
        assert out["profile"] is None and {r["status"] for r in out["positions"]} == {"not_diagnostic"}

    def test_unexplained_and_not_in_table(self):
        rows = rm.sound_laws(("k", "p"), ("ṭ", "f"), TABLE, WRITTEN)["positions"]
        assert [(r["ps"], r["status"]) for r in rows] == [("*ṭ", "unexplained"), ("*f", "not_in_table")]
        assert rows[0]["consistent"] == []

    def test_unwritten_consonants_and_indels_are_skipped(self):
        assert rm.sound_laws(("ḥ", "k", "r"), ("ḥ", "k", "r"), TABLE, WRITTEN)["radicals"] == "ḥ-k-r"
        assert [r["ps"] for r in rm.sound_laws(("ḥ", "k", "r"), ("ḥ", "k", "r"), TABLE, WRITTEN)["positions"]] \
            == ["*k", "*r"]
        assert [r["ps"] for r in rm.sound_laws(("k", "r"), ("ḏ", "k", "r"), TABLE, WRITTEN)["positions"]] \
            == ["*k", "*r"]

    def test_hits_carry_their_laws(self, laws_engine):
        hits = {h.number: h.sound_laws for h in laws_engine.clusters("ZA-KA-RA")[0]}
        assert hits["7"]["headword"] == "*ḏakar-" and hits["7"]["profile"] == ["A"]    # C keeps ḏ, which ZU writes
        assert hits["8"]["profile"] is None                           # z for *z: every branch agrees

    def test_the_nearest_ps_headword_is_used(self, laws_engine):
        assert {k.radicals for k in laws_engine._ps_keys["9"]} == {("ḏ", "b", "ḥ"), ("d", "b", "ḥ")}
        hit = next(h for h in laws_engine.clusters("DA-PA")[0] if h.number == "9")
        assert hit.sound_laws["radicals"] == "d-b-ḥ"
        hit = next(h for h in laws_engine.clusters("ZA-PA")[0] if h.number == "9")
        assert hit.sound_laws["radicals"] == "ḏ-b-ḥ"                  # z ↔ ḏ 0.2, z ↔ d 1.0

    def test_weak_keys_are_never_the_headword(self, laws_engine):
        assert any(k.kind == "weak" and k.number == "3" for k in laws_engine.index.keys)
        assert all(k.kind == "ps" for ks in laws_engine._ps_keys.values() for k in ks)

    def test_laws_use_the_hits_own_variant(self, laws_engine):
        hits, vs = laws_engine.clusters("DA-PA")
        assert ("d", "p", "n") in {v.tokens for v in vs}                 # a longer variant exists, and loses
        hit = next(h for h in hits if h.number == "9")
        assert [(r["ps"], r["la"], r["status"]) for r in hit.sound_laws["positions"]] == \
            [("*d", "d", "not_diagnostic"), ("*b", "p", "not_in_table")]

    def test_only_the_first_laws_hits_are_computed(self, laws_engine):
        hits, _ = laws_engine.clusters("ZA-KA-RA", top=0, laws=1)
        assert len(hits) >= 2 and hits[0].sound_laws is not None
        assert all(h.sound_laws is None for h in hits[1:])

    def test_query_shows_laws_and_they_never_touch_the_statistic(self, laws_engine):
        r = laws_engine.query("ZA-KA-RA", n=30, top=2)
        assert all(h.sound_laws is not None for h in r.clusters) and r.best.sound_laws is not None
        blank = _engine(laws_engine.index, correspondences={"branches": [], "forward": {}}).query("ZA-KA-RA", n=30,
                                                                                                    top=2)
        assert [h.sound_laws["profile"] for h in blank.clusters] == [None, None]
        j, k = r.to_json(), blank.to_json()
        for field in ("d_star", "families", "p_max", "verdict", "uniqueness", "breadth"):
            assert j[field] == k[field], field
        assert any("Geers' law not checked" in n for n in j["notes"])
        json.dumps(j)


# --- tokens: one phoneme per letter; ties on rounded sums ---

TOKEN_RECORDS = [
    {"Number": "21", "Proto-Semitic": "*kawn-", "Meaning": "'to be'", "Analogues": {}},
    {"Number": "22", "Proto-Semitic": "*tasar-", "Meaning": "'to bind'", "Analogues": {}},
    {"Number": "23", "Proto-Semitic": "*šalām-", "Meaning": "'peace'", "Analogues": {"Sabaic": "s₁lm 'peace'"}},
    {"Number": "24", "Proto-Semitic": "*ḥaʿhakat-", "Meaning": "'a test record'", "Analogues": {}},
    {"Number": "25", "Proto-Semitic": "*ḫann-", "Meaning": "'grace'", "Analogues": {"Harari": "xāna 'grace'"}},
]


@pytest.fixture(scope="module")
def tok_engine(tmp_path_factory) -> rm.Shoresh:
    d = tmp_path_factory.mktemp("shoresh_tokens")
    roots = d / "semitic_roots.json"
    roots.write_text(json.dumps(TOKEN_RECORDS, ensure_ascii=False), encoding="utf-8")
    write_index(d / "root_index.sqlite", roots, ())
    return _engine(RootIndex.load(d / "root_index.sqlite"))


class TestTokens:
    @pytest.mark.parametrize("s, toks", [("kwn", ("k", "w", "n")), ("tsr", ("t", "s", "r")),
                                         ("gwr", ("g", "w", "r")), ("sḥq", ("s", "ḥ", "q")),
                                         ("s₁lm", ("s", "l", "m")), ("xbb", ("ḫ", "b", "b")),
                                         ("ṣ́dq", ("ṣ", "d", "q"))])
    def test_one_token_per_letter(self, s, toks):
        assert rm.phonemes(s) == toks
        assert rm.phonemes(unicodedata.normalize("NFD", s)) == toks

    def test_signs_are_never_merged_across(self):
        assert rm.variants([[("k", "u"), ("w", "a"), ("n", "a")]])[0].tokens == ("k", "w", "n")
        assert rm.variants([[("t", "a"), ("s", "i"), ("r", "e")]])[0].tokens == ("t", "s", "r")

    def test_index_keys_are_tokenised_per_radical(self, tok_engine):
        entries = {e.tokens for e in tok_engine._entry_of.values()}
        assert {("k", "w", "n"), ("t", "s", "r"), ("s", "l", "m"), ("ḫ", "n")} <= entries
        assert not any(t in ("kw", "ṣ", "₁", "x") for e in entries for t in e)

    def test_a_k_w_word_retrieves_its_root(self, tok_engine):
        hits, _ = tok_engine.clusters("KU-WA-NA")
        assert hits[0].number == "21" and hits[0].distance == 0.0

    def test_variant_rules_match_cognate_search_where_no_digraph_forms(self):
        from tools.linear_a.cognate_search import _generate_morphophonological_skeletons as gen
        for word in CORPUS + ["A-TA-NA", "TI-TI-KU", "DI-DI-KA-SE", "KU-KU-RA"]:
            cv = [rm.sign_options(s)[0] for s in rm.word_signs(word)]
            skel = rm.skeleton_of(cv)
            if len(_tokenize_phonemes(skel)) != len(skel):
                continue
            theirs = {tuple(_tokenize_phonemes(s)): (p, r) for s, p, r in reversed(gen(word, skel, cv))}
            ours = {t: (p, r) for t, p, r in reversed(rm.morph_variants(rm.phonemes(skel), cv))}
            assert ours == theirs, word

    def test_variant_rules_see_every_consonant_of_a_k_w_word(self):
        cv = [rm.sign_options(s)[0] for s in rm.word_signs("KU-WA-TI-TI-MA")]
        rules = {t: r for t, _, r in rm.morph_variants(rm.phonemes(rm.skeleton_of(cv)), cv)}
        assert rules[("k", "w", "n", "t", "m")] == "geminate_nun_restoration"
        assert rules[("k", "w", "t", "m")] == "degemination"
        cv = [rm.sign_options(s)[0] for s in rm.word_signs("MA-RA-TA-SA")]
        rules = {t: r for t, _, r in rm.morph_variants(rm.phonemes(rm.skeleton_of(cv)), cv)}
        assert rules[("m", "r", "t")] == "iii_weak_suffix_strip"

    def test_consonants_count_every_letter(self, tok_engine):
        assert tok_engine.query("TA-SA-RE", n=5, families="C").consonants == 3

    def test_a_sum_that_rounds_to_the_cutoff_is_at_it(self, tok_engine):
        ks = rm.Variant(("k", "t"), 0.0, "surface", 0)
        assert rm.distance(("k", "t"), ("ḥ", "ʿ", "h", "k", "t")) != 0.3      # the float sum: 0.30000000000000004
        assert tok_engine.min_distance(("k", "t"), 0.3) == 0.3
        assert tok_engine.d_star([ks], 0.3) == 0.3 == tok_engine.d_star([ks])
        assert tok_engine.brute_force_d_star([ks], 0.3) == 0.3
        assert tok_engine._count([[ks]], 0.3) == (1, 0, 1, 0)
        assert tok_engine._count([[ks]], 0.3, saturation_at=0.3)[3] == 1

    def test_penalised_sums_tie_too(self, tok_engine):
        md = lambda toks, cutoff: 0.1 if toks == ("x1",) else rm.INF
        vs = [rm.Variant(("x1",), 0.2, "final_n_loss_restoration", 0)]
        assert 0.1 + 0.2 != 0.3 and rm.d_star_over(md, vs, 0.3) == 0.3

    def test_clusters_report_the_rounded_distance(self, tok_engine):
        hits, _ = tok_engine.clusters("KA-TA")
        assert next(h for h in hits if h.number == "24").distance == 0.3


class TestDecoyEdges:
    def test_family_a_of_one_repeated_sign_is_empty(self, index):
        assert _engine(index).family_a("-".join(["KA"] * 9), 5, rm.SEED) == ([], 1)

    def test_family_c_alternates_are_distinct_readings(self, index):
        engine = _engine(index)
        word = "QA-RA2-TI"
        for decoy in engine.family_c(word, 300, rm.SEED):
            assert len({tuple(c for c, _ in r) for r in decoy}) == len(decoy)

    def test_fabricate_takes_the_engines_tokens(self):
        tables = position_tables(["KU-WA"])            # KU-WA is the only word these tables can draw
        per_letter = lambda w: rm.phonemes(rm.skeleton_of([rm.sign_options(s)[0] for s in rm.word_signs(w)]))
        assert fabricate(random.Random(0), 2, 2, tables, set(), tries=50, tokens=per_letter) == "KU-WA"
        assert fabricate(random.Random(0), 2, 2, tables, set(), tries=50) is None    # the shared count: kw is one


def _adjacent_equal(engine: rm.Shoresh, signs: list[str]) -> bool:
    toks = rm.phonemes(rm.skeleton_of(engine.word_readings("-".join(signs))[0]))
    return any(a == b for a, b in pairwise(toks))


class _Space:
    """A competitor space whose d* is 0 and that ranks every decoy above it."""
    name = "stub"

    def d_star(self, vs):
        return 0.0

    def nearest(self, vs):
        return "x"

    def classify(self, vs, d):
        return 1


class TestA17:
    def test_fabricate_drops_the_ocp_on_request(self):
        tables = position_tables(["TA-NA-NA"])         # the only word these tables can draw: t n n
        per_letter = lambda w: rm.phonemes(rm.skeleton_of([rm.sign_options(s)[0] for s in rm.word_signs(w)]))
        assert fabricate(random.Random(0), 3, 3, tables, set(), tries=50, tokens=per_letter) is None
        assert fabricate(random.Random(0), 3, 3, tables, set(), tries=50, tokens=per_letter, ocp=False) == "TA-NA-NA"
        assert fabricate(random.Random(0), 3, 3, tables, set(), tries=50, ocp=False) is None  # gold builder: kept

    def test_family_b_of_a_geminate_word_may_repeat_a_consonant(self, index):
        engine = _engine(index)
        geminate, _ = engine.family_b("TA-NA-NA", 300, rm.SEED)
        plain, _ = engine.family_b("TA-NA-KU", 300, rm.SEED)
        assert any(_adjacent_equal(engine, d) for d in geminate)
        assert plain and not any(_adjacent_equal(engine, d) for d in plain)

    def test_an_empty_family_b_stays_in_p_max_at_one(self, index, monkeypatch):
        engine = _engine(index)
        monkeypatch.setattr(engine, "family_b", lambda word, n, seed: ([], n))
        r = engine.query("KA-NA-SI", n=100)
        assert r.families["B"].n == 0 and r.families["B"].p == 1.0 and r.families["B"].in_p_max
        assert r.p_max == 1.0 and r.deciding_family == "B" and r.verdict == "NO_SIGNAL"
        assert any("family B built no decoy" in note for note in r.notes)

    def test_the_competitor_null_keeps_an_empty_family_b_too(self):
        vs = [rm.Variant(("k", "n", "s"), 0.0, "surface", 0)]
        out = rm.Shoresh._competitor(_Space(), vs, {"B": [], "C": [vs]}, {"B": True, "C": True})
        assert out["families"]["B"]["p"] == 1.0 and out["p_max"] == 1.0 and out["deciding_family"] == "B"

    def test_saturation_is_checked_without_family_b(self, index):
        engine = _engine(index)
        r = engine.query("KA-NA-SI", n=50, families="AC")
        assert "B" not in r.families and r.saturation is not None
        assert r.saturation == engine.query("KA-NA-SI", n=50).saturation
        assert any("saturation gate only" in note for note in r.notes)

    def test_a_word_over_the_reading_cap_says_so(self, index):
        engine = _engine(index)
        assert any("16 readings" in note and "A17" in note
                   for note in engine.query("QA-RA2-QA-RA2", n=5, families="C").notes)
        assert not any("readings" in note and "A17" in note for note in engine.query("QA-RA2-TI", n=5).notes)


# --- the semantic gate (§3.1, A10, A18) ---

GATE_RECORDS = [
    {"Number": "20", "Proto-Semitic": "*qVpVz-", "Meaning": "'wine'", "Analogues": {}},              # food_drink
    {"Number": "21", "Proto-Semitic": "*qVpVd-", "Meaning": "'to bless; temple'", "Analogues": {}},  # ritual_cultic
    {"Number": "22", "Proto-Semitic": "*qVpVn-", "Meaning": "'to remember'", "Analogues": {}},      # no domain alone
]
GATE_LEXICON = [
    {"id": "p20", "language": "Phoenician", "root": "qpn", "normalized": "qpn", "meaning": "sheep",
     "semitic_roots_ref": ["22"]},                                                    # joined gloss: fauna
    {"id": "p21", "language": "Phoenician", "root": "qpn", "normalized": "qpn", "meaning": "bull god", "pos": "DN",
     "semitic_roots_ref": ["22"]},                                                    # onomastic: never tagged
]


def _corpus(*docs) -> dict:
    return {f"X{i}": {"support": s, "transliteratedWords": list(t)} for i, (s, t) in enumerate(docs)}


@pytest.fixture(scope="module")
def gate_index(tmp_path_factory) -> RootIndex:
    d = tmp_path_factory.mktemp("gate")
    roots = d / "semitic_roots.json"
    roots.write_text(json.dumps(GATE_RECORDS, ensure_ascii=False), encoding="utf-8")
    write_index(d / "x.sqlite", roots, (_lex("phoenician", _jsonl(d / "p.jsonl", GATE_LEXICON)),))
    return RootIndex.load(d / "x.sqlite")


LINK_RECORDS = GATE_RECORDS + [
    {"Number": "23", "Proto-Semitic": "*ʕVlVm-", "Meaning": "'grain'", "Analogues": {}}]     # fits, never retrieved
LINK_LEXICON = [
    {"id": "p30", "language": "Phoenician", "root": "qpn", "normalized": "qpn", "meaning": "wine"},
]                                                     # an exact sound link to 22 with no gloss overlap: not joined


@pytest.fixture(scope="module")
def link_index(tmp_path_factory) -> RootIndex:
    d = tmp_path_factory.mktemp("link")
    roots = d / "semitic_roots.json"
    roots.write_text(json.dumps(LINK_RECORDS, ensure_ascii=False), encoding="utf-8")
    write_index(d / "x.sqlite", roots, (_lex("phoenician", _jsonl(d / "p.jsonl", LINK_LEXICON)),))
    return RootIndex.load(d / "x.sqlite")


class _FarSpace(_Space):
    """A competitor that ranks every decoy below its d*: p = 1, so it never blocks CONVERGENT."""
    def classify(self, vs, d):
        return -1


def _gate(index, contexts, **kw) -> rm.Shoresh:
    return rm.Shoresh(index, corpus_words=CORPUS, contexts=sg.Contexts(contexts), **kw)


WINE = _corpus(("Tablet", ["QE-PO-ZA", "VIN", "5"]))
TEMPLE = _corpus(("Stone vessel", ["QE-PO-ZA"]))


class TestSemanticGate:
    def test_cluster_domains_take_the_meaning_and_non_onomastic_joined_glosses(self, gate_index):
        doms = _gate(gate_index, {}, names=True)._domains()
        assert doms["20"] == {"food_drink"} and doms["21"] == {"ritual_cultic"}
        assert doms["22"] == {"fauna"}                                  # sheep, not the DN's deity

    def test_a_fitting_top_cluster_gives_d_sem_equal_to_d_star(self, gate_index):
        r = _gate(gate_index, WINE).query("QE-PO-ZA", n=50).to_json()
        sem = r["semantic"]
        assert sem["context"] == ["agriculture", "food_drink"] and (sem["attestations"], sem["known"]) == (1, 1)
        assert sem["d_star"] == r["d_star"] == 0.0 and sem["fitting"] >= 1

    def test_only_fitting_clusters_count(self, gate_index):
        r = _gate(gate_index, TEMPLE).query("QE-PO-ZA", n=50).to_json()
        dist = {c["number"]: c["distance"] for c in r["clusters"]}
        assert r["d_star"] == dist["20"] == 0.0
        assert r["semantic"]["d_star"] == dist["21"] > 0                # the temple root, not the wine root

    def test_decoys_are_gated_by_the_real_words_context(self, gate_index):
        engine = _gate(gate_index, TEMPLE)
        sem = engine.query("QE-PO-ZA", n=60, families="BC").to_json()["semantic"]
        fit = frozenset({"21"})
        ds = sem["d_star"]

        def gated(vs):                                                   # the oracle: fitting entries only
            return min((rm._q(rm.distance(v.tokens, e.tokens) + v.penalty) for v in vs
                        for e in engine._retrieve(v.tokens) if e.clusters & fit), default=rm.INF)
        decoys = {"B": [engine._variants_of(s) for s in engine.family_b("QE-PO-ZA", 60, rm.SEED)[0]],
                  "C": [rm.variants(r, "QE-PO-ZA") for r in engine.family_c("QE-PO-ZA", 60, rm.SEED)]}
        for k, dv in decoys.items():
            got = [gated(vs) for vs in dv]
            f = sem["families"][k]
            assert (f["n"], f["below"], f["tied"]) == (len(got), sum(g < ds for g in got), sum(g == ds for g in got))
            assert f["p"] == round((1 + f["below"] + f["tied"]) / (1 + f["n"]), 6)
        assert sem["p_max"] == max(f["p"] for f in sem["families"].values() if f["in_p_max"])
        counted = {k: f["p"] for k, f in sem["families"].items() if f["in_p_max"]}
        assert sem["deciding_family"] == max(counted, key=lambda k: (counted[k], k))

    def test_a_control_is_scored_under_its_positives_context(self, gate_index):
        """A19: a control has no attestation of its own; it takes the context of the word it was made from."""
        engine = _gate(gate_index, WINE)
        own = engine.query("QE-PA-ZA", n=30, competitors=False).to_json()["semantic"]
        assert own["context"] is None                                        # never a corpus word
        sem = engine.query("QE-PA-ZA", n=30, competitors=False, context_of="QE-PO-ZA").to_json()["semantic"]
        assert sem["context"] == ["agriculture", "food_drink"] and sem["context_of"] == "QE-PO-ZA"
        assert (sem["attestations"], sem["known"]) == (1, 1) and sem["d_star"] is not None
        r = engine.query("QE-PA-ZA", n=30, competitors=False, context_of="QE-PO-ZA").to_json()
        assert any("inherited from QE-PO-ZA (A19)" in n for n in r["notes"])

    def test_the_inherited_context_never_moves_the_phonological_result(self, gate_index):
        engine = _gate(gate_index, WINE)
        plain = engine.query("QE-PA-ZA", n=30).to_json()
        inherited = engine.query("QE-PA-ZA", n=30, context_of="QE-PO-ZA").to_json()
        assert plain["semantic"] != inherited["semantic"]                              # the premise
        for k in ("d_star", "families", "p_max", "saturation", "clusters", "verdict"):
            assert plain[k] == inherited[k]

    def test_no_attested_context_is_no_semantic_evidence(self, gate_index):
        r = _gate(gate_index, _corpus(("Nodule", ["QE-PO-ZA"]))).query("QE-PO-ZA", n=30,
                                                                       competitors=False).to_json()
        assert r["semantic"]["context"] is None and r["semantic"]["p_max"] is None
        assert any("no semantic evidence" in n for n in r["notes"]) and r["verdict"] != "CONVERGENT"
        assert any("(0 of 1 attestations with a known context)" in n for n in r["notes"])

    def test_no_fitting_cluster_leaves_d_sem_empty(self, gate_index):
        r = _gate(gate_index, _corpus(("Tablet", ["QE-PO-ZA", "VIR", "2"]))).query("QE-PO-ZA", n=30).to_json()
        assert r["semantic"]["context"] == ["administrative", "kinship"]
        assert r["semantic"]["d_star"] is None and r["semantic"]["p_max"] is None    # no root fits

    def test_convergent_needs_both_ps_below_001_and_the_competitors(self, gate_index):
        far = [_FarSpace()]
        conv = _gate(gate_index, WINE, competitors=far).query("QE-PO-ZA", n=300, families="BC")
        assert conv.p_max < rm.P_CONVERGENT and conv.semantic["p_max"] < rm.P_CONVERGENT
        assert conv.semitic_specific is True and conv.verdict == "CONVERGENT"
        temple = _gate(gate_index, TEMPLE, competitors=far).query("QE-PO-ZA", n=300, families="BC")
        assert temple.p_max == conv.p_max and temple.semantic["p_max"] >= rm.P_CONVERGENT
        assert temple.verdict == "PHONOLOGICAL_ONLY"
        near = _gate(gate_index, WINE, competitors=[_Space()]).query("QE-PO-ZA", n=300, families="BC")
        assert near.semitic_specific is False and near.verdict == "PHONOLOGICAL_ONLY"

    def test_a_family_outside_p_max_never_decides_the_gated_p(self, gate_index):
        r = _gate(gate_index, WINE, competitors=[_FarSpace()]).query("QE-PO-ZA", n=300)   # families ABC
        a = r.semantic["families"]["A"]
        assert not a["in_p_max"] and a["p"] >= rm.P_CONVERGENT                # 6 orders: an order check (A1)
        assert r.semantic["p_max"] < rm.P_CONVERGENT and r.verdict == "CONVERGENT"

    def test_p_max_must_be_under_001_too(self, tmp_path):
        recs = [{"Number": "20", "Proto-Semitic": "*karm-", "Meaning": "'wine'", "Analogues": {}},
                {"Number": "21", "Proto-Semitic": "*karVb-", "Meaning": "'to bless; temple'", "Analogues": {}},
                {"Number": "22", "Proto-Semitic": "*kVrVn-", "Meaning": "'to remember'", "Analogues": {}}]
        (tmp_path / "r.json").write_text(json.dumps(recs), encoding="utf-8")
        write_index(tmp_path / "x.sqlite", tmp_path / "r.json", ())
        ctx = _corpus(("Tablet", ["KA-RA-MA", "VIN", "5"]))
        r = _gate(RootIndex.load(tmp_path / "x.sqlite"), ctx, competitors=[_FarSpace()]).query(
            "KA-RA-MA", n=300, families="BC")
        assert rm.P_CONVERGENT <= r.p_max < rm.P_SIGNAL and r.semantic["p_max"] < rm.P_CONVERGENT   # the premise
        assert r.semitic_specific is True and r.verdict == "PHONOLOGICAL_ONLY"

    def test_without_the_competitor_null_it_fails_closed(self, gate_index):
        r = _gate(gate_index, WINE, competitors=[_FarSpace()]).query("QE-PO-ZA", n=300, families="BC",
                                                                     competitors=False)
        assert r.p_max < rm.P_CONVERGENT and r.semantic["p_max"] < rm.P_CONVERGENT
        assert r.verdict == "PHONOLOGICAL_ONLY"
        assert "CONVERGENT needs the competitor null (§2): unavailable in this run" in r.notes

    def test_the_gate_never_moves_the_phonological_result(self, gate_index):
        plain = _gate(gate_index, {}).query("QE-PO-ZA", n=50).to_json()
        gated = _gate(gate_index, TEMPLE).query("QE-PO-ZA", n=50).to_json()
        for k in ("d_star", "families", "p_max", "saturation", "clusters"):
            assert plain[k] == gated[k]

    def test_a_linked_lexeme_that_does_not_join_never_tags_the_cluster(self, link_index):
        """§8, A18: only joined lexemes give a cluster domains, never a bare sound link."""
        assert link_index.links["phoenician:p30"] == [("22", "root_key_exact", False)]   # the premise: linked ...
        assert rm.joined_clusters(link_index, "phoenician:p30") == ()                   # ... but not joined
        assert _gate(link_index, {})._domains()["22"] == frozenset()                  # 'to remember' alone

    def test_fitting_counts_the_retrieved_clusters_that_fit(self, link_index):
        sem = _gate(link_index, WINE).query("QE-PO-ZA", n=30, competitors=False).to_json()["semantic"]
        fit = {n for n, d in _gate(link_index, {})._domains().items() if d & {"agriculture", "food_drink"}}
        assert fit == {"20", "23"} and sem["fitting"] == 1                             # 23 is never retrieved

    @pytest.mark.live_contexts
    def test_the_live_corpus_is_read_when_no_contexts_are_given(self, gate_index, monkeypatch):
        monkeypatch.setattr(rm, "load_corpus", lambda: TEMPLE)      # the engine's binding of corpus_utils.load_corpus
        engine = rm.Shoresh(gate_index, corpus_words=CORPUS)
        assert engine.contexts.context("QE-PO-ZA") == {"ritual_cultic", "deity"}

    def test_engines_in_tests_never_read_the_live_corpus(self, gate_index, monkeypatch):
        """The conftest gives every engine an empty context unless a test asks for the live one."""
        monkeypatch.setattr(rm, "load_corpus", lambda: TEMPLE)
        assert rm.Shoresh(gate_index, corpus_words=CORPUS).contexts.context("QE-PO-ZA") is None


# --- the verdict's thresholds (§3), at their boundaries ---

class TestVerdict:
    @pytest.mark.parametrize("p_max, p_sem, specific, verdict", [
        (0.0099, 0.0099, True, "CONVERGENT"),
        (0.01, 0.0099, True, "PHONOLOGICAL_ONLY"),               # p_max at 0.01 is not under it
        (0.0099, 0.01, True, "PHONOLOGICAL_ONLY"),               # nor is the gated p
        (0.0099, None, True, "PHONOLOGICAL_ONLY"),               # no semantic evidence
        (0.0099, 0.0099, None, "PHONOLOGICAL_ONLY"),             # no competitor null
        (0.0099, 0.0099, False, "PHONOLOGICAL_ONLY"),
        (0.0499, None, None, "PHONOLOGICAL_ONLY"),
        (0.05, 0.0, True, "NO_SIGNAL"),                          # NO_SIGNAL at or above 0.05
        (None, None, None, "NO_SIGNAL")])
    def test_the_p_thresholds(self, p_max, p_sem, specific, verdict):
        assert rm.verdict_of(3, None, p_max, p_sem, specific) == verdict

    def test_the_uninformative_gates(self):
        assert rm.verdict_of(2, None, 0.001, 0.001, True) == "UNINFORMATIVE"           # two consonants
        assert rm.verdict_of(3, 0.9001, 0.001, 0.001, True) == "UNINFORMATIVE"         # above the share
        assert rm.verdict_of(3, 0.9, 0.001, 0.001, True) == "CONVERGENT"               # at it, not above

    @pytest.mark.parametrize("p_max, competitors, specific", [
        (0.0499, [0.05, 0.5], True),                             # a competitor at 0.05 is no signal
        (0.0499, [0.0499, 0.5], False),
        (0.0499, [None], False),
        (0.05, [0.5], False)])                                   # nor is the Semitic p at 0.05
    def test_semitic_specific(self, p_max, competitors, specific):
        assert rm.semitic_specific(p_max, competitors) is specific
