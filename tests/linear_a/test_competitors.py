"""Tests for tools/core/competitors.py, the Shoresh competitor null (§2, A15). Spaces are built from hand-written
entries, and the engine runs on a tmp_path index; TestShippedFiles reads the three rival-language files, read-only."""
from __future__ import annotations

import json
import random

import pytest
import test_root_match as trm  # the shared records and corpus words; pytest puts this folder on the path
from shoresh_inputs import SHORESH

from tools.core import competitors as cp
from tools.core import root_match as rm
from tools.core.phonetics import (
    EGYPTIAN_DISTANCES,
    LUWIAN_DISTANCES,
    _tokenize_phonemes,
    weighted_levenshtein,
)
from tools.core.root_index import RootIndex, write_index

pytestmark = SHORESH

ALPHABET = ["k", "q", "g", "ḫ", "ḥ", "ʿ", "h", "t", "d", "s", "š", "z", "l", "r", "n", "m", "p", "b", "w", "y", "ꜣ"]


def _space(keys: list[str], distances=LUWIAN_DISTANCES, transparent: bool = True,
           name: str = "test") -> cp.CompetitorSpace:
    out: dict[tuple[str, ...], list[str]] = {}
    for i, k in enumerate(keys):
        out.setdefault(tuple(_tokenize_phonemes(k)), []).append(str(i))
    return cp.CompetitorSpace(name, out, distances, transparent)


def _stable(rng: random.Random, lo: int = 1, hi: int = 6) -> tuple[str, ...]:
    """A token tuple that survives joining and re-tokenising, so weighted_levenshtein sees the same tokens."""
    while True:
        q = tuple(rng.choice(ALPHABET) for _ in range(rng.randint(lo, hi)))
        if tuple(_tokenize_phonemes("".join(q))) == q:
            return q


class TestKeys:
    @pytest.mark.parametrize("root, key", [("tessub", ("t", "s", "s", "b")), ("tsb", ("ṣ", "b")),
                                           ("kawa", ("k", "w")), ("kwr", ("kw", "r")), ("šú", None), ("šúr", ("š", "r")),
                                           ("snbtj⸗fj", ("s", "n", "b", "t", "j", "f", "j")), ("ḥr(w)", ("ḥ", "r")),
                                           ("13)ffzlkks,srxv60:2", None), ("l(prhpssgn", None), ("1hzzn", None),
                                           ("a", None), ("", None)])
    def test_l6_extraction_letters_only_two_tokens(self, root, key):
        assert cp.key_of({"Consonantal_Root": root}) == key

    @pytest.mark.parametrize("root, digraphs, key", [("msḥ", True, ("m", "s", "ḥ")), ("sḫt", True, ("s", "ḫ", "t")),
                                                     ("nts", False, ("n", "t", "s")), ("bꜣkw", False, ("b", "ꜣ", "k", "w")),
                                                     ("gwš", False, ("g", "w", "š")), ("nts", True, ("n", "ṣ")),
                                                     ("kwr", True, ("kw", "r"))])
    def test_a_marked_letter_never_joins_a_digraph_and_egyptian_has_none(self, root, digraphs, key):
        entry = {"Consonantal_Root": root}
        assert (cp.key_of(entry) if digraphs else cp.key_of(entry, digraphs=False)) == key

    def test_egyptian_is_read_without_digraphs(self):
        assert {s.name: s.digraphs for s in cp.COMPETITORS} == {"luwian": True, "egyptian": False, "hurrian": True}

    def test_a_sum_that_rounds_to_the_cutoff_ties(self):
        space = _space(["ḥʿhkt"])
        vs = [rm.Variant(("k", "t"), 0.0, "surface", 0)]
        assert space.distance(("k", "t"), ("ḥ", "ʿ", "h", "k", "t")) != 0.3      # the float sum
        assert space.min_distance(("k", "t"), 0.3) == 0.3 == space.d_star(vs)
        assert _space(["ḥʿhkt"]).classify(vs, 0.3) == 0
        assert space.nearest(vs)["distance"] == 0.3

    @pytest.mark.parametrize("entry", [{"Meaning": "Tarhunt (DN)"}, {"Analogues": {"x": "a name (PN)"}},
                                       {"Category": "personal_name"}, {"Category": "nominal_root,royal_name"},
                                       {"Name_Elements": ["Amun"]}, {"semantic_field": ["toponym"]}])
    def test_names(self, entry):
        assert cp.is_name(entry)

    @pytest.mark.parametrize("entry", [{"Meaning": "chair"}, {"Category": "verbal_root"}, {"Name_Elements": []},
                                       {"semantic_field": ["body"]}])
    def test_not_names(self, entry):
        assert not cp.is_name(entry)

    def test_load_drops_names_unless_asked_and_merges_shared_keys(self, tmp_path):
        rows = [{"Number": "1", "Consonantal_Root": "tessub", "Category": "divine_name"},
                {"Number": "2", "Consonantal_Root": "tasub", "Category": "nominal_root"},
                {"Number": "3", "Consonantal_Root": "tasb"},
                {"Number": "4", "Consonantal_Root": "13)ffz"}]
        (tmp_path / "x.json").write_text(json.dumps(rows), encoding="utf-8")
        spec = cp.Spec("x", "x.json", LUWIAN_DISTANCES)
        space = cp.load(spec, data_dir=tmp_path)
        assert space.keys == {("t", "s", "b"): ["2", "3"]} and space.dropped == {"name": 1, "no_key": 1}
        named = cp.load(spec, names=True, data_dir=tmp_path)
        assert named.keys == {("t", "s", "s", "b"): ["1"], ("t", "s", "b"): ["2", "3"]}


class TestSearch:
    @pytest.mark.parametrize("distances, transparent", [(LUWIAN_DISTANCES, True), (EGYPTIAN_DISTANCES, True),
                                                        (LUWIAN_DISTANCES, False)])
    def test_trie_equals_the_naive_minimum_with_and_without_cutoff(self, distances, transparent):
        rng = random.Random(3)
        keys = ["".join(_stable(rng, 2, 5)) for _ in range(150)]
        space = _space(keys, distances, transparent)
        for _ in range(200):
            q = _stable(rng)
            naive = min(weighted_levenshtein("".join(q), k, distances=distances, guttural_transparent=transparent)
                        for k in keys)
            assert space._search(q, rm.INF) == (naive, True)
            cut = rng.choice([0.0, 0.3, 0.7, 1.2, 2.0])
            assert space._search(q, cut)[0] == (naive if rm._q(naive) <= cut else rm.INF)    # on the _q grid

    def test_insertion_cost_follows_the_guttural_flag(self):
        assert _space(["kḥn"], transparent=True).min_distance(("k", "n")) == pytest.approx(0.1)
        assert _space(["kḥn"], transparent=False).min_distance(("k", "n")) == 1.0

    def test_classify_agrees_with_d_star_and_leaves_the_memo_exact(self):
        rng = random.Random(4)
        keys = ["".join(_stable(rng, 2, 4)) for _ in range(120)]
        for _ in range(150):
            vs = [rm.Variant(_stable(rng, 1, 5), rng.choice([0.0, 0.15, 0.2]), "r", 0) for _ in range(rng.randint(1, 3))]
            ref = _space(keys)
            d = ref.d_star(vs) + rng.choice([-0.3, -0.15, 0.0, 0.0, 0.15, 0.3])
            exact = ref.d_star(vs, d)
            want = -1 if exact < d else (0 if exact == d else 1)
            fresh = _space(keys)
            assert fresh.classify(vs, d) == want
            for v in vs:                                  # what classify memoised still answers exactly
                assert fresh.min_distance(v.tokens) == ref.min_distance(v.tokens)

    def test_nearest_names_the_key_at_d_star(self):
        space = _space(["mlk", "knš", "kns"])
        vs = [rm.Variant(("k", "n", "s"), 0.0, "surface", 0)]
        assert space.nearest(vs) == {"key": "kns", "numbers": ["2"], "distance": 0.0, "variant_rule": "surface"}


@pytest.fixture(scope="module")
def index(tmp_path_factory) -> RootIndex:
    d = tmp_path_factory.mktemp("competitors")
    roots = d / "semitic_roots.json"
    roots.write_text(json.dumps(trm.RECORDS, ensure_ascii=False), encoding="utf-8")
    write_index(d / "root_index.sqlite", roots, lexica=())
    return RootIndex.load(d / "root_index.sqlite")


def _engine(index: RootIndex, spaces=()) -> rm.Shoresh:
    return rm.Shoresh(index, corpus_words=trm.CORPUS, competitors=spaces)


class TestEngine:
    def test_the_semitic_result_is_untouched(self, index):
        plain = _engine(index).query("KA-NA-SI", n=60).to_json()
        with_c = _engine(index, [_space(["kns", "mlk"]), _space(["prt"])]).query("KA-NA-SI", n=60).to_json()
        for k in ("d_star", "families", "p_max", "deciding_family", "saturation", "verdict", "clusters", "breadth"):
            assert with_c[k] == plain[k], k
        assert plain["competitors"] == {} and "competitor null (§2) not run" in plain["notes"]
        assert not any("competitor" in n for n in with_c["notes"])

    @pytest.mark.parametrize("word", ["KA-NA-SI", "KA-NU"])
    def test_the_semitic_keys_as_a_competitor_give_the_semitic_numbers(self, index, word):
        eng = _engine(index)
        keys = {e.tokens: sorted(e.clusters) for e in {id(e): e for e in eng._entry_of.values()}.values()}
        mirror = cp.CompetitorSpace("mirror", keys, rm.SHORESH_DISTANCES, True)
        r = _engine(index, [mirror]).query(word, n=60)
        c = r.competitors["mirror"]
        assert c["d_star"] == rm._num(r.d_star) and c["p_max"] == round(r.p_max, 6)
        for k, f in r.families.items():
            assert (c["families"][k]["n"], c["families"][k]["below"], c["families"][k]["tied"]) == \
                   (f.n, f.below, f.tied) and c["families"][k]["in_p_max"] == f.in_p_max
        if word == "KA-NU":                                    # d* = 1.0: decoys tie it, so ties are tested
            assert any(f.tied for f in r.families.values())

    def test_margin_and_semitic_specific(self, index):
        far = _engine(index, [_space(["prt", "ggg"])]).query("KA-NA-SI", n=100)
        assert far.p_max < rm.P_SIGNAL and far.competitors["test"]["p_max"] >= rm.P_SIGNAL
        assert far.semitic_specific is True
        assert far.competitor_margin == round(far.competitors["test"]["p_max"] - far.p_max, 6)
        near = _engine(index, [_space(["kns"], name="a"), _space(["prt"], name="b")]).query("KA-NA-SI", n=100)
        ps = [c["p_max"] for c in near.competitors.values()]
        assert min(ps) < rm.P_SIGNAL <= max(ps) and near.semitic_specific is False
        assert near.competitor_margin == round(min(ps) - near.p_max, 6)

    def test_competitor_runs_when_no_semitic_key_is_retrieved(self, index):
        r = _engine(index, [_space(["ptrkd"])]).query("PA-TA-RA-KA-DA", n=30)
        assert r.d_star == rm.INF and r.families == {} and r.p_max is None
        assert r.competitors["test"]["d_star"] == 0.0 and r.competitors["test"]["families"]["B"]["n"] > 0
        assert r.semitic_specific is None and r.competitor_margin is None

    def test_switched_off_per_query(self, index):
        r = _engine(index, [_space(["kns"])]).query("KA-NA-SI", n=30, competitors=False)
        assert r.competitors == {} and r.semitic_specific is None
        assert "competitor null (§2) not run" in r.notes


class TestShippedFiles:
    def test_three_competitors_with_letter_keys_and_no_names(self):
        spaces = {s.name: s for s in cp.load_all()}
        assert list(spaces) == ["luwian", "egyptian", "hurrian"]
        for s in spaces.values():
            assert s.keys and all(len(k) >= 2 and "".join(k).isalpha() for k in s.keys)
        hurrian = json.loads((cp.DATA_DIR / "hurrian_roots.json").read_text(encoding="utf-8"))
        # the shipped file holds the lexical entries only, so no name can reach the key space
        assert not [e["Number"] for e in hurrian if cp.is_name(e)]
        assert {n for ns in spaces["hurrian"].keys.values() for n in ns} <= {str(e["Number"]) for e in hurrian}
