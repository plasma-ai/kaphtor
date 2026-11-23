"""Unit tests for Kernel I (Unsupervised Bound-Affix Morphology & Margin-Permutation Null)."""
from __future__ import annotations

import morphology_i as mi


def test_extract_bound_affixes_distinguishes_prefixing_and_suffixing():
    # Prefixing toy language: stems (K,a)-(R,u), (P,a)-(T,i) with prefixes (J,a)-, (T,a)-
    pre_words = [
        (("K", "a"), ("R", "u")),
        (("J", "a"), ("K", "a"), ("R", "u")),
        (("T", "a"), ("K", "a"), ("R", "u")),
        (("P", "a"), ("T", "i")),
        (("J", "a"), ("P", "a"), ("T", "i")),
        (("N", "a"), ("P", "a"), ("T", "i")),
    ]
    # Suffixing toy language: same stems with suffixes -(S,i), -(N,o)
    suf_words = [
        (("K", "a"), ("R", "u")),
        (("K", "a"), ("R", "u"), ("S", "i")),
        (("K", "a"), ("R", "u"), ("N", "o")),
        (("P", "a"), ("T", "i")),
        (("P", "a"), ("T", "i"), ("S", "i")),
        (("P", "a"), ("T", "i"), ("N", "o")),
    ]
    f_pre = mi.extract_bound_affixes(pre_words)
    f_suf = mi.extract_bound_affixes(suf_words)
    assert f_pre["pre_rate"] > 0.8
    assert f_suf["pre_rate"] < 0.2
    assert f_pre["pre_c_counts"]["J"] >= 2
    assert f_suf["suf_c_counts"]["S"] >= 2


def test_evaluate_corpus_recovers_own_family_and_margin_null():
    alphabet = [(c, v) for c in mi.CONSONANT_SERIES for v in ("a", "i", "u", "e", "o")]
    sem_train = [
        (("K", "a"), ("R", "u")),
        (("J", "a"), ("K", "a"), ("R", "u")),
        (("T", "a"), ("K", "a"), ("R", "u")),
        (("K", "a"), ("R", "u"), ("T", "i")),
        (("P", "a"), ("L", "a")),
        (("J", "a"), ("P", "a"), ("L", "a")),
        (("N", "a"), ("P", "a"), ("L", "a")),
        (("P", "a"), ("L", "a"), ("M", "a")),
        (("D", "a"), ("M", "u")),
        (("J", "a"), ("D", "a"), ("M", "u")),
        (("D", "a"), ("M", "u"), ("T", "i")),
    ]
    grk_train = [
        (("K", "a"), ("R", "u")),
        (("K", "a"), ("R", "u"), ("S", "i")),
        (("K", "a"), ("R", "u"), ("N", "o")),
        (("P", "a"), ("L", "a")),
        (("P", "a"), ("L", "a"), ("S", "i")),
        (("P", "a"), ("L", "a"), ("P", "i")),
        (("D", "a"), ("M", "u")),
        (("D", "a"), ("M", "u"), ("S", "i")),
        (("D", "a"), ("M", "u"), ("N", "o")),
    ]
    models = {
        "semitic": mi.BoundAffixModel(mi.extract_bound_affixes(sem_train), alphabet),
        "greek": mi.BoundAffixModel(mi.extract_bound_affixes(grk_train), alphabet),
    }
    res_s = mi.evaluate_corpus(sem_train, models, n_perm=200, seed=42)
    assert res_s["winner_joint_cv"] == "semitic"
    assert res_s["families"]["semitic"]["margin_obs"] > 0
    assert res_s["families"]["semitic"]["p_margin_perm"] <= 0.05

    res_g = mi.evaluate_corpus(grk_train, models, n_perm=200, seed=42)
    assert res_g["winner_joint_cv"] == "greek"
    assert res_g["families"]["greek"]["margin_obs"] > 0
    assert res_g["families"]["greek"]["p_margin_perm"] <= 0.05
