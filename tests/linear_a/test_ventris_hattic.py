"""The classifier's Hattic layer (tools/linear_a/ventris_propagate.py, --hattic): the registered rival arm's keys
and table (tools/core/competitors.py) scored as the Luwian and Egyptian arms are, off unless asked for. Read-only:
the only data read is data/linear-a/hattic_roots.json.
"""
from __future__ import annotations

from tools.core import competitors as cp
from tools.linear_a import ventris_propagate as vp
from tools.linear_a.validation import hattic_layer_null as null

SIX = {"NWS", "Hurrian_name", "Egyptian", "Luwian", "toponym", "substrate"}
ON = vp.LanguageOptions(hattic=True)
NWS = [{"root": "kns", "score": 0.6, "meaning": "gather"}]


def classify(opts=None, nws=NWS, **kw):
    kw.setdefault("egyptian_matches", [])
    kw.setdefault("luwian_matches", [])
    return vp.classify_language("KA-NA-SI", ["KA", "NA", "SI"], nws, "clay_tablet", {}, skeleton="kns",
                                skeleton_conf=0.8, lang_opts=opts, **kw)


def test_the_layer_is_off_unless_asked_for():
    assert vp.LanguageOptions().hattic is False
    assert set(classify()["scores"]) == SIX == set(classify(vp.LanguageOptions())["scores"])
    assert classify() == classify(vp.LanguageOptions()) == classify(vp.LanguageOptions(), hattic_matches=[
        {"root": "kns", "score": 0.99}])                      # a match handed in is not read while the layer is off


def test_an_arm_with_no_match_changes_no_other_score():
    off, on = classify(), classify(ON, hattic_matches=[])
    assert set(on["scores"]) == SIX | {"Hattic"} and on["scores"]["Hattic"] == 0.0
    assert {k: v for k, v in on["scores"].items() if k != "Hattic"} == off["scores"]
    assert (on["decision"], on["confidence"]) == (off["decision"], off["confidence"])


def test_a_hattic_match_is_scored_like_the_other_rival_arms():
    strong = [{"root": "kns", "score": 0.72, "meaning": "x", "language": "Hattic"}]
    as_hattic = classify(ON, nws=[], hattic_matches=strong)
    as_luwian = classify(ON, nws=[], hattic_matches=[], luwian_matches=[{**strong[0], "language": "Luwian"}])
    assert as_hattic["decision"] == "Hattic" and as_luwian["decision"] == "Luwian"
    assert as_hattic["scores"]["Hattic"] == as_luwian["scores"]["Luwian"]         # same prior, same likelihood
    assert abs(sum(as_hattic["scores"].values()) - 1.0) < 0.01
    both = classify(ON, hattic_matches=strong)                 # against a Semitic match of 0.6 at a tablet's priors
    assert both["scores"]["Hattic"] > 0 and both["scores"]["NWS"] > 0


def test_semitic_only_reads_no_hattic():
    opts = vp.LanguageOptions(mode="semitic-only", hattic=True)
    assert classify(opts, hattic_matches=[{"root": "kns", "score": 0.9}])["scores"].get("Hattic", 0.0) == 0.0


def test_the_site_prior_is_the_same_at_every_site():
    profiles = {"schema_version": 1, "categories": sorted(SIX),
                "default": {"languages": {c: 1 / 6 for c in SIX}, "site_weight": 0.35},
                "sites": {"Haghia Triada": {"languages": {**{c: 0.02 for c in SIX}, "NWS": 0.9}, "site_weight": 0.35},
                          "Knossos": {"languages": {**{c: 0.1 for c in SIX}, "Luwian": 0.5}, "site_weight": 0.35}}}
    opts = vp.LanguageOptions(hattic=True, use_site_priors=True, site_profiles=profiles)
    priors = {site: vp._compute_composite_prior("Hattic", "clay_tablet", site, opts, vp._LANG_TO_TT_KEY)
              for site in ("Haghia Triada", "Knossos", "a site not in the file")}
    assert len(set(priors.values())) == 1
    luwian = {site: vp._compute_composite_prior("Luwian", "clay_tablet", site, opts, vp._LANG_TO_TT_KEY)
              for site in ("Haghia Triada", "Knossos")}
    assert luwian["Knossos"] > luwian["Haghia Triada"]         # the test can tell a flat prior from one that moves
    assert vp._LANG_TO_TT_KEY["Hattic"] == vp._LANG_TO_TT_KEY["Luwian"] == vp._LANG_TO_TT_KEY["Egyptian"]


def test_the_keys_and_the_table_are_the_registered_arm_s():
    spec = next(s for s in cp.COMPETITORS if s.name == "hattic")
    registered = cp.load(spec)
    space = vp._get_hattic_space()
    assert space.keys == registered.keys and len(space.keys) > 200
    assert space.distances == cp.table(spec) and space.distances[("k", "ḫ")] == cp.K_FRICATIVE


def test_scoring_against_the_hattic_keys():
    space = vp._get_hattic_space()
    key = next(k for k in sorted(space.keys) if len(k) == 3 and not set(k) & set("ḫhʿʔḥ"))
    hit = vp.score_against_hattic_roots("".join(key), 0.8)[0]
    assert (hit["root"], hit["distance"], hit["language"]) == ("".join(key), 0.0, "Hattic")
    assert hit["score"] == 0.8                                 # (1 / (1 + 0)) × confidence, three consonants, same length
    assert hit["numbers"] == space.keys[key] and hit["lemma"]      # the shipped file carries no Meaning
    two = next(k for k in sorted(space.keys) if len(k) == 2 and not set(k) & set("ḫhʿʔḥ"))
    assert vp.score_against_hattic_roots("".join(two), 0.8)[0]["score"] == 0.24    # two consonants: × 0.3
    assert vp.score_against_hattic_roots("k", 0.8) == [] and vp.score_against_hattic_roots("", 0.8) == []
    far = vp.score_against_hattic_roots("qqqq", 0.8)
    assert all(m["distance"] <= 1.5 for m in far)
    ranked = vp.score_against_hattic_roots("".join(key), 0.8)
    assert [m["score"] for m in ranked] == sorted((m["score"] for m in ranked), reverse=True) and len(ranked) <= 5


def test_a_word_is_classed_hattic_only_through_the_flag(monkeypatch):
    """propagate_word hands the arm to the classifier and to the display only when the layer is on."""
    calls = []
    monkeypatch.setattr(vp, "score_against_hattic_roots", lambda s, c, max_distance=1.5: calls.append(s) or [])
    classify(vp.LanguageOptions())                             # off: never scored
    assert calls == []
    vp.classify_language("KA-NA-SI", ["KA", "NA", "SI"], NWS, "clay_tablet", {}, skeleton="kns", skeleton_conf=0.8,
                         egyptian_matches=[], luwian_matches=[], lang_opts=ON)
    assert calls == ["kns"]                                    # on, and no matches handed in: scored from the skeleton


def test_the_scrambled_null_keeps_lengths_and_consonants_and_changes_the_words():
    space = vp._get_hattic_space()
    a, b = null.scrambled(space, 1), null.scrambled(space, 2)
    assert a.keys != space.keys and a.keys != b.keys
    assert sorted(t for k in a.keys for t in k) != [] and {len(k) for k in a.keys} <= {len(k) for k in space.keys}
    assert null.scrambled(space, 1).keys == a.keys                      # a seed gives one list
    assert sum(len(ns) for ns in a.keys.values()) == sum(len(ns) for ns in space.keys.values())
    assert a.distances == space.distances
