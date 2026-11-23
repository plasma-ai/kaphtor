"""Shoresh Amendment A25: Kober-cluster coupling and Kernel C/D domain annotations.

Connects Shoresh's per-word scoring to the verified four-kernel probabilistic suite
(`models/language-id-kernel/`):
  1. Unsupervised Kober-cluster extraction (stem-sharing pairs/trios & affix-transition polarity)
     and Stouffer cluster coupling across inflected forms of the same stem.
  2. Pre-linguistic semantic anchor tagging (`KERNEL_D_ANCHORED`) for arithmetic and
     logogram-adjacent anchors verified at Z_perm = +7.37, p = 0.00010 (10,000 grid perms).
  3. Peak-sanctuary libation formula tagging (`KERNEL_C_LITURGICAL`) referencing the size-locked
     (K=300) Dirichlet log-odds liturgical cohesion channel (IO Za 2: Z_perm = +2.91 to +3.05).

Pure Python standard library only (passes isolated -I -S import checks).

Attribution: di Mino
"""
from __future__ import annotations

import collections
import math
from typing import Any

try:
    from .shoresh_cv import WordCV, cv_from_syllables
except ImportError:
    from tools.core.shoresh_cv import WordCV, cv_from_syllables

ANCHOR_SLOTS: dict[str, dict[str, Any]] = {
    "KU-RO": {"concept": "TOTAL", "basis": "arithmetic summation (9/16 testable faces)"},
    "KI-RO": {"concept": "DEFICIT", "basis": "arithmetic remainder outside KU-RO (HT 34, HT 123+124a)"},
    "A-KA-NU": {"concept": "VESSEL_CUP", "basis": "inked inside a bowl (KN Zc 7)"},
    "SU-PU": {"concept": "VESSEL_CUP", "basis": "adjacent to vessel logogram (HT 31)"},
    "PA-TA-QE": {"concept": "VESSEL_CUP", "basis": "adjacent to vessel logogram (HT 31)"},
    "KA-DI": {"concept": "VESSEL_CUP", "basis": "precedes VIN on ZA 15b"},
    "KU-NI-SU": {"concept": "GRAIN", "basis": "adjacent to GRA logogram (HT 86a)"},
    "PA-RA": {"concept": "GRAIN", "basis": "heads grain-only entries (HT 128a)"},
}

KERNEL_D_SUMMARY: dict[str, Any] = {
    "full_8": {"winner": "semitic", "delta_ll": 13.58, "z_perm": 7.37, "p_perm": 0.00010, "n_perm": 10000},
    "drop_3_trade_loans": {"winner": "semitic", "delta_ll": 7.53, "z_perm": 6.22, "p_perm": 0.00010, "n_perm": 10000},
    "arithmetic_only_2": {"winner": "semitic", "delta_ll": 2.61, "z_perm": 4.59, "p_perm": 0.00640, "n_perm": 10000},
}

IO_ZA_2_SLOTS: dict[str, int] = {
    "A-TA-I-*301-WA-JA": 1,
    "JA-DI-KI-TU": 2,
    "JA-SA-SA-RA-ME": 3,
    "U-NA-KA-NA-SI": 4,
    "I-PI-NA-MA": 5,
    "SI-RU-TE": 6,
    "TA-NA-RA-TE-U-TI-NU": 7,
}

KERNEL_C_SUMMARY: dict[str, Any] = {
    "io_za_2": {"winner": "hebrew_lit", "k_top": 300, "z_perm": 2.91, "p_perm": 0.03248, "n_perm": 2000},
}


def _longest_run(a: WordCV, b: WordCV) -> tuple[int, int, int]:
    best = (0, 0, 0)
    for i in range(len(a)):
        for j in range(len(b)):
            n = 0
            while i + n < len(a) and j + n < len(b) and a[i + n] == b[j + n]:
                n += 1
            if n > best[2]:
                best = (i, j, n)
    return best


def _shares_kober_stem(a: WordCV, b: WordCV, min_run: int = 2, max_side: int = 2) -> bool:
    if a == b:
        return False
    # 1. Stem-final consonant-series vowel alternation (e.g. SA-RU ~ SA-RO ~ SA-RA)
    if len(a) == len(b) and len(a) >= 2 and a[:-1] == b[:-1] and a[-1][0] and a[-1][0] == b[-1][0] and a[-1][1] != b[-1][1]:
        return True
    # 2. Shared contiguous run >= min_run with affix-sized residues
    i, j, n = _longest_run(a, b)
    if n < min_run:
        return False
    return i <= max_side and j <= max_side and (len(a) - i - n) <= max_side and (len(b) - j - n) <= max_side


def extract_kober_clusters(words: list[str], min_run: int = 2) -> list[list[str]]:
    """Unsupervised extraction of connected Kober clusters (pairs, trios, n-tuples) from hyphenated words."""
    uniq = sorted({w.strip().upper() for w in words if w and w.strip()})
    cvs = [cv_from_syllables(w) for w in uniq]
    adj: dict[int, set[int]] = collections.defaultdict(set)
    for i in range(len(uniq)):
        for j in range(i + 1, len(uniq)):
            if _shares_kober_stem(cvs[i], cvs[j], min_run=min_run):
                adj[i].add(j)
                adj[j].add(i)

    visited: set[int] = set()
    clusters: list[list[str]] = []
    for i in sorted(adj):
        if i in visited:
            continue
        comp, stack = [], [i]
        visited.add(i)
        while stack:
            u = stack.pop()
            comp.append(uniq[u])
            for v in adj[u]:
                if v not in visited:
                    visited.add(v)
                    stack.append(v)
        clusters.append(sorted(comp))
    clusters.sort(key=lambda c: (-len(c), c[0]))
    return clusters


def couple_cluster_z(z_scores: list[float]) -> float:
    """Stouffer meta-Z across members of a Kober paradigm cluster."""
    if not z_scores:
        return 0.0
    return round(sum(z_scores) / math.sqrt(len(z_scores)), 4)


def annotate_word(word: str, corpus_words: list[str] | None = None) -> dict[str, Any]:
    """Return Amendment A25 kernel-bridge metadata for a Linear A word."""
    norm = word.strip().upper()
    flags: list[str] = []
    out: dict[str, Any] = {}

    if norm in ANCHOR_SLOTS:
        flags.append("KERNEL_D_ANCHORED")
        out["anchor"] = {**ANCHOR_SLOTS[norm], "kernel_d": KERNEL_D_SUMMARY}

    if norm in IO_ZA_2_SLOTS:
        flags.append("KERNEL_C_LITURGICAL")
        out["liturgical"] = {"io_za_2_slot": IO_ZA_2_SLOTS[norm], "kernel_c": KERNEL_C_SUMMARY}

    if corpus_words:
        clusters = extract_kober_clusters(corpus_words)
        member_of = next((c for c in clusters if norm in c), None)
        if member_of:
            flags.append("KOBER_TRIO" if len(member_of) >= 3 else "KOBER_PAIR")
            out["kober_cluster"] = member_of

    out["flags"] = flags
    return out


def enrich_result(result_json: dict[str, Any], corpus_words: list[str] | None = None) -> dict[str, Any]:
    """Attach `kernel_bridge` metadata to a Shoresh Result.to_json() dict without altering existing keys."""
    word = str(result_json.get("word", ""))
    return {**result_json, "kernel_bridge": annotate_word(word, corpus_words=corpus_words)}
