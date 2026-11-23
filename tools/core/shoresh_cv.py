"""Shoresh Amendment A24: Vocalized CV distance (d_cv*) and Bayesian marginal log-likelihood (ΔLL).

Complements Shoresh's consonant-skeleton d* (which must mark <=2-consonant words UNINFORMATIVE under §3)
by preserving Linear A vowels in CV (series, vowel) alignment and replacing raw min-distance with
log-mean-exp marginal log-likelihood over bounded candidate sets (analytically penalizing dictionary size).

Pure Python standard library only (passes isolated -I -S import checks).

Attribution: di Mino
"""
from __future__ import annotations

import math
import random
from typing import Any

CONSONANT_SERIES = ("D", "J", "K", "M", "N", "P", "Q", "R", "S", "T", "W", "Z")
VOWELS = frozenset("aeiou")
WordCV = tuple[tuple[str, str], ...]

_CONS_TO_SERIES = {
    "p": "P", "b": "P", "f": "P",
    "t": "T", "ṭ": "T", "ṯ": "T", "θ": "T",
    "d": "D", "ḏ": "D", "ḍ": "D",
    "k": "K", "g": "K", "ḫ": "K", "x": "K", "ġ": "K", "γ": "K", "ʁ": "K",
    "q": "Q", "kʷ": "Q",
    "s": "S", "š": "S", "ś": "S", "ṣ": "S",
    "z": "Z", "ẓ": "Z",
    "r": "R", "l": "R",
    "m": "M",
    "n": "N",
    "w": "W",
    "y": "J", "j": "J",
    "ʾ": "", "ʿ": "", "h": "", "ḥ": "",
}


def cv_from_syllables(word: str) -> WordCV:
    """Parse a hyphenated Linear A/B transliteration (e.g. 'KU-RO', 'A-KA-NU') into (series, vowel) keys."""
    out: list[tuple[str, str]] = []
    for raw in word.strip().upper().split("-"):
        tok = raw.strip()
        if not tok:
            continue
        if tok.startswith("*"):
            out.append((tok, ""))
            continue
        # Strip trailing numeric doublet suffixes (e.g. RA2 -> RA, PA3 -> PA)
        base = tok.rstrip("0123456789₀₁₂₃₄₅₆₇₈₉")
        if len(base) == 1 and base.lower() in VOWELS:
            out.append(("", base.lower()))
        elif len(base) >= 2 and base[-1].lower() in VOWELS:
            out.append((base[:-1], base[-1].lower()))
        else:
            out.append((tok, ""))
    return tuple(out)


def cv_distance(x: WordCV, y: WordCV) -> float:
    """Normalized CV edit distance in [0, 1] (Kernel D metric).

    - Exact (series, vowel) match: 0.0
    - Same consonant series, different vowel: 0.35 (dead-vowel / vocalization shift)
    - Different consonant series, same vowel: 0.85
    - Different series and vowel: 1.0
    - Insertion/deletion: 0.75
    """
    m, n = len(x), len(y)
    if m == 0 and n == 0:
        return 0.0
    if x == y:
        return 0.0
    prev = [0.75 * j for j in range(n + 1)]
    cur = [0.0] * (n + 1)
    for i in range(1, m + 1):
        xi = x[i - 1]
        xi0, xi1 = xi
        cur[0] = 0.75 * i
        for j in range(1, n + 1):
            yj = y[j - 1]
            if xi == yj:
                sub = 0.0
            elif xi0 == yj[0]:
                sub = 0.35
            elif xi1 and xi1 == yj[1]:
                sub = 0.85
            else:
                sub = 1.0
            v1 = prev[j] + 0.75
            v2 = cur[j - 1] + 0.75
            v3 = prev[j - 1] + sub
            best = v1 if v1 <= v2 else v2
            if v3 < best:
                best = v3
            cur[j] = best
        prev, cur = cur, prev
    return prev[n] / max(m, n)


def bayesian_marginal_ll(query: WordCV, candidates: list[WordCV], beta: float = 6.0) -> tuple[float, float]:
    """Return (marginal_ll, min_d_cv) over a candidate synset using log-mean-exp.

    Analytically penalizes larger candidate sets: adding non-matching synonyms lowers marginal_ll
    by log(1 / |candidates|), preventing dictionary-size inflation.
    """
    if not candidates:
        return -math.inf, 1.0
    dists = [cv_distance(query, c) for c in candidates]
    min_d = min(dists)
    max_neg = max(-beta * d for d in dists)
    lme = max_neg + math.log(sum(math.exp(-beta * d - max_neg) for d in dists) / len(dists))
    return lme, min_d


def permute_cv(word: WordCV, mapping: dict[str, str]) -> WordCV:
    """Permute consonant series labels while holding vowels and opaque signs fixed."""
    return tuple((mapping.get(s, s), v) for s, v in word)


def score_vocalic_set(
    words_and_candidates: list[tuple[WordCV, dict[str, list[WordCV]]]],
    languages: tuple[str, ...] = ("semitic", "greek", "anatolian", "hurrian"),
    beta: float = 6.0,
    n_perm: int = 1000,
    seed: int = 20261122,
) -> dict[str, Any]:
    """Score one or more Linear A words jointly across languages with consonant-series grid permutations.

    Returns per-language LL, min_d_cv mean, Z_perm, p_perm, winner, and Semitic ΔLL over best rival.
    """
    obs_ll: dict[str, float] = {lang: 0.0 for lang in languages}
    obs_d: dict[str, list[float]] = {lang: [] for lang in languages}
    for w, by_lang in words_and_candidates:
        for lang in languages:
            ll, md = bayesian_marginal_ll(w, by_lang[lang], beta=beta)
            obs_ll[lang] += ll
            obs_d[lang].append(md)

    rng = random.Random(seed)
    perm_lls: dict[str, list[float]] = {lang: [] for lang in languages}
    ge: dict[str, int] = {lang: 0 for lang in languages}
    for _ in range(n_perm):
        shuf = list(CONSONANT_SERIES)
        rng.shuffle(shuf)
        mp = dict(zip(CONSONANT_SERIES, shuf))
        for lang in languages:
            acc = 0.0
            for w, by_lang in words_and_candidates:
                ll, _ = bayesian_marginal_ll(permute_cv(w, mp), by_lang[lang], beta=beta)
                acc += ll
            perm_lls[lang].append(acc)
            if acc >= obs_ll[lang] - 1e-12:
                ge[lang] += 1

    out_langs: dict[str, Any] = {}
    for lang in languages:
        arr = perm_lls[lang]
        mean = sum(arr) / len(arr)
        var = sum((x - mean) ** 2 for x in arr) / len(arr)
        sd = math.sqrt(var) if var > 1e-12 else 1e-9
        out_langs[lang] = {
            "ll": round(obs_ll[lang], 4),
            "mean_d_cv": round(sum(obs_d[lang]) / len(obs_d[lang]), 4) if obs_d[lang] else 1.0,
            "z_perm": round((obs_ll[lang] - mean) / sd, 3),
            "p_perm": round((1 + ge[lang]) / (n_perm + 1), 5),
        }
    winner = max(languages, key=lambda l: out_langs[l]["z_perm"])
    rivals = [l for l in languages if l != "semitic"]
    best_rival = max(rivals, key=lambda l: out_langs[l]["ll"]) if rivals else None
    dll_sem = round(out_langs["semitic"]["ll"] - out_langs[best_rival]["ll"], 4) if ("semitic" in out_langs and best_rival) else None
    return {
        "winner": winner,
        "semitic_delta_ll": dll_sem,
        "best_rival": best_rival,
        "n_perm": n_perm,
        "beta": beta,
        "languages": out_langs,
    }
