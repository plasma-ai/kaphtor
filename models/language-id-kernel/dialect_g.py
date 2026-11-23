"""Kernel G: Dialectal Sound-Law Coherence (Palaikastro vs. Central Crete, B=10,000 rule perms).

Tests whether the attested cross-site sign substitutions between Central Crete (IO/KO/SY/TL/VRY)
and Eastern Crete (Palaikastro: PK Za 11, PK Za 12, PK Za 4) match attested Northwest Semitic
phonological sound laws (y- > ʾ- glide loss, *-aya > -ē monophthongization, *ṯ > š/t sibilant-dental
isogloss, mimation expansion -MA -> -MI-NA) better than 10,000 random sound-substitution rule bundles
of equal size/complexity.

Attribution: di Mino
"""
from __future__ import annotations

import argparse
import math
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "render"))
import c_align as a  # noqa: E402

SIGNATURE = HERE / "SIGNATURE.txt"

# Observed Central Crete <-> Palaikastro minimal pairs in the Libation Formula (strictly from GORILA)
PALAIKASTRO_PAIRS: list[tuple[str, str, str]] = [
    ("JA-SA-SA-RA-ME", "A-SA-SA-RA-ME", "initial_glide_loss"),
    ("JA-DI-KI-TU", "A-DI-KI-TE-TE", "initial_glide_loss"),
    ("A-TA-I-*301-WA-JA", "A-TA-I-*301-WA-E", "diphthong_contraction"),
    ("U-NA-RU-KA-NA-SI", "U-NA-RU-KA-NA-TI", "interdental_isogloss"),
    ("I-PI-NA-MA", "I-PI-NA-MI-NA", "enclitic_expansion"),
]

# Attested NWS phonological sign-level correspondences (Central -> Palaikastro)
NWS_ISOGLOSS_RULES: set[tuple[tuple[str, str], tuple[str, str]]] = {
    (("J", "a"), ("", "a")),   # initial y- > ʾ- (Amarna Canaanite / Phoenician glide reduction)
    (("J", "a"), ("", "e")),   # *-aya > -ē monophthongization (Phoenician contraction)
    (("S", "i"), ("T", "i")),  # *ṯ > š vs. t (Canaanite/Phoenician interdental split)
    (("M", "a"), ("M", "i")),  # bound mimation vowel raising before -NA
}


def extract_diff_pairs(pairs: list[tuple[str, str, str]], sign_table: dict) -> list[tuple[tuple[str, str], tuple[str, str]]]:
    """Extract the first differing (central_key, pk_key) pair for each minimal pair."""
    diffs = []
    for c_word, pk_word, _ in pairs:
        ck = a.keys(c_word, sign_table)
        pk = a.keys(pk_word, sign_table)
        # Find differing sign positions (aligning from start if prefix differs, else from end)
        found = None
        for x, y in zip(ck, pk):
            if x != y and isinstance(x, tuple) and isinstance(y, tuple):
                found = (x, y)
                break
        if found is None and len(ck) != len(pk):
            for x, y in zip(reversed(ck), reversed(pk)):
                if x != y and isinstance(x, tuple) and isinstance(y, tuple):
                    found = (x, y)
                    break
        if found:
            diffs.append(found)
    return diffs


def run_dialect_test(n_perm: int = 10000, seed: int = 20261122) -> dict:
    sign_table = a.load_signs()
    valid_keys = sorted({k for k in sign_table.values() if isinstance(k, tuple)})
    diffs = extract_diff_pairs(PALAIKASTRO_PAIRS, sign_table)
    obs_hits = sum(d in NWS_ISOGLOSS_RULES for d in diffs)
    rule_size = len(NWS_ISOGLOSS_RULES)

    # Null: 10,000 random phonological rule bundles of exact size `rule_size` over valid CV keys
    rng = random.Random(seed)
    ge = 0
    perm_hits = []
    for _ in range(n_perm):
        # Draw rule_size random distinct ordered (k1 != k2) substitution rules
        rules = set()
        while len(rules) < rule_size:
            k1, k2 = rng.sample(valid_keys, 2)
            rules.add((k1, k2))
        h = sum(d in rules for d in diffs)
        perm_hits.append(h)
        if h >= obs_hits:
            ge += 1
    mean = sum(perm_hits) / len(perm_hits)
    sd = math.sqrt(sum((x - mean) ** 2 for x in perm_hits) / len(perm_hits)) or 1e-9
    return {
        "n_pairs": len(diffs),
        "rule_bundle_size": rule_size,
        "obs_hits": obs_hits,
        "perm_mean": round(mean, 5),
        "z_perm": round((obs_hits - mean) / sd, 3),
        "p_perm": round((1 + ge) / (n_perm + 1), 5),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-perm", type=int, default=10000)
    args = ap.parse_args()
    if not SIGNATURE.is_file():
        print("REFUSED: SIGNATURE.txt missing.", file=sys.stderr)
        return 2
    res = run_dialect_test(n_perm=args.n_perm)
    print(
        f"=== Kernel G (Palaikastro Dialect Sound-Law Coherence, B={args.n_perm}) ===\n"
        f"  hits={res['obs_hits']}/{res['n_pairs']} (rule_size={res['rule_bundle_size']}) "
        f"| perm_mean={res['perm_mean']:.5f} | Z_perm={res['z_perm']:+.2f} | p_perm={res['p_perm']:.5f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
