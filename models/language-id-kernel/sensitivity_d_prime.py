"""Exploratory Post-Registration Sensitivity Study for Hypothetical Kernel D'.

Evaluates expanded pre-linguistic anchor tiers (n = 8 -> 13, zero KA-PA inflation; plus
an explicitly quarantined HT 140 KA-PA comparison row) using anchors_d.py's 100% FROZEN
pre-registered SYNSETS, cv_distance, and beta=6.0 scoring.

NEVER alters anchors_d.py or SIGNATURE.txt. Reproduces runs/kernel-d-sensitivity-2026-11-27.json
bit-for-bit on a fresh clone.

Attribution: di Mino
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "render"))

import anchors_d as ad  # noqa: E402
import c_align as a     # noqa: E402
import c_render as r    # noqa: E402

SIGNATURE = HERE / "SIGNATURE.txt"
ANCHORS_D_PATH = HERE / "anchors_d.py"

# Clean KA-PA-free anchor tiers (every added word has a literal HT 31 / HT 38 vessel drawing
# or arithmetic sum in corpus.json; KA-PA is quarantined separately below).
D_BASE_8: list[tuple[str, str]] = list(ad.LINEAR_A_ANCHORS_STRICT)

# Strict signs-a5-proposed.json, dropping contestable PA-RA header & adding blind untranslated DA-RO-PA (HT 38 *403-VS)
D_PURE_8: list[tuple[str, str]] = [x for x in D_BASE_8 if x[0] != "PA-RA"] + [
    ("DA-RO-PA", "VESSEL_CUP"),
]

# All strict signs-a5-proposed.json anchors (D_BASE_8 + blind untranslated DA-RO-PA; zero PA3, zero KA-PA)
D_STRICT_9: list[tuple[str, str]] = D_BASE_8 + [
    ("DA-RO-PA", "VESSEL_CUP"),
]

# HT 31 literal PA3 vessel drawings (sensitivity tiers folding opaque GORILA doublet AB 56 / PA3 -> PA)
HT31_PA3_VESSELS: list[tuple[str, str]] = [
    ("QA-PA₃", "VESSEL_CUP"),
    ("KA-RO-PA₃", "VESSEL_CUP"),
    ("SU-PA₃-RA", "VESSEL_CUP"),
]

D_VESSEL_11: list[tuple[str, str]] = D_PURE_8 + HT31_PA3_VESSELS
D_EXT_12: list[tuple[str, str]] = D_STRICT_9 + HT31_PA3_VESSELS
D_EXT_13_POTO: list[tuple[str, str]] = D_EXT_12 + [("PO-TO-KU-RO", "TOTAL")]

# Clean strict-LB (zero PA3, zero KA-PA) ablations
D_NO_LOANS_STRICT_6: list[tuple[str, str]] = [
    x for x in D_STRICT_9 if x[0] not in ("A-KA-NU", "KU-NI-SU", "KA-DI")
]
D_DROPK_STRICT_4: list[tuple[str, str]] = [
    ("SU-PU", "VESSEL_CUP"),
    ("PA-TA-QE", "VESSEL_CUP"),
    ("PA-RA", "GRAIN"),
    ("DA-RO-PA", "VESSEL_CUP"),
]

# PA3-folded (zero KA-PA) ablations
D_NO_LOANS_PA3_9: list[tuple[str, str]] = [
    x for x in D_EXT_12 if x[0] not in ("A-KA-NU", "KU-NI-SU", "KA-DI")
]
D_DROPK_PA3_6: list[tuple[str, str]] = D_DROPK_STRICT_4 + [
    ("QA-PA₃", "VESSEL_CUP"),
    ("SU-PA₃-RA", "VESSEL_CUP"),
]

# Quarantined comparison tier (includes disputed HT 140 oil-list KA-PA, which has ZERO vessel pictograms)
D_EXT_13_WITH_KAPA: list[tuple[str, str]] = D_EXT_12 + [("KA-PA", "VESSEL_CUP")]

TIERS: list[tuple[str, list[tuple[str, str]], bool, str]] = [
    ("D_BASE_8", D_BASE_8, False, "Signed Kernel D baseline (strict signs-a5-proposed.json)"),
    ("D_PURE_8", D_PURE_8, False, "Strict LB without PA-RA header + blind untranslated DA-RO-PA (HT 38 *403-VS)"),
    ("D_STRICT_9", D_STRICT_9, False, "All strict LB (D_BASE_8 + blind untranslated DA-RO-PA; zero PA3, zero KA-PA)"),
    ("D_VESSEL_11", D_VESSEL_11, True, "D_PURE_8 + 3 HT 31 PA3->PA doublet vessels (zero PA-RA, zero KA-PA)"),
    ("D_EXT_12", D_EXT_12, True, "D_STRICT_9 + 3 HT 31 PA3->PA doublet vessels (zero KA-PA)"),
    ("D_EXT_13_POTO", D_EXT_13_POTO, True, "D_EXT_12 + PO-TO-KU-RO (flags KU-RO compound overlap; zero KA-PA)"),
    ("D_NO_LOANS_STRICT_6", D_NO_LOANS_STRICT_6, False, "Strict-LB trade-loan removal (D_STRICT_9 minus A-KA-NU, KU-NI-SU, KA-DI; zero PA3)"),
    ("D_DROPK_STRICT_4", D_DROPK_STRICT_4, False, "Strict-LB K-free subset (SU-PU, PA-TA-QE, PA-RA, DA-RO-PA; zero PA3)"),
    ("D_NO_LOANS_PA3_9", D_NO_LOANS_PA3_9, True, "PA3-folded trade-loan removal (D_EXT_12 minus A-KA-NU, KU-NI-SU, KA-DI; zero KA-PA)"),
    ("D_DROPK_PA3_6", D_DROPK_PA3_6, True, "PA3-folded K-free subset (D_EXT_12 minus all K-series words; zero KA-PA)"),
    ("D_EXT_13_WITH_KAPA", D_EXT_13_WITH_KAPA, True, "Quarantined comparison: D_EXT_12 + disputed HT 140 oil-list KA-PA (no vessel drawing)"),
]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_tier(
    name: str,
    anchors: list[tuple[str, str]],
    pa3_folded: bool,
    scope: str,
    spelled: dict,
    sign_table: dict,
    n_perm: int = 10000,
    seed: int = 20261122,
    beta: float = 6.0,
) -> dict:
    st = dict(sign_table)
    if pa3_folded:
        st["PA3"] = ("P", "a")
    parsed = [(a.keys(w.replace("₃", "3") if pa3_folded else w, st), c) for w, c in anchors]
    if pa3_folded:
        # Also verify every token parsed cleanly to 2-tuples
        for w_raw, _ in anchors:
            ks = a.keys(w_raw.replace("₃", "3"), st)
            assert all(isinstance(k, tuple) and len(k) == 2 for k in ks), f"Opaque key in {w_raw}: {ks}"
    langs = ("semitic", "greek", "anatolian", "hurrian")
    obs_raw: dict[str, float] = {}
    det: dict[str, list[dict]] = {}
    for l in langs:
        obs_raw[l], det[l] = ad.score_anchors(parsed, spelled, l, beta=beta)

    rng = random.Random(seed)
    ps: dict[str, list[float]] = {l: [] for l in langs}
    ge: dict[str, int] = {l: 0 for l in langs}
    for _ in range(n_perm):
        shuf = list(ad.CONSONANT_SERIES)
        rng.shuffle(shuf)
        mp = dict(zip(ad.CONSONANT_SERIES, shuf))
        pa = [(ad.permute_word(w, mp), c) for w, c in parsed]
        for l in langs:
            ll, _ = ad.score_anchors(pa, spelled, l, beta=beta)
            ps[l].append(ll)
            if ll >= obs_raw[l] - 1e-12:
                ge[l] += 1

    out_langs = {}
    for l in langs:
        arr = ps[l]
        mu = sum(arr) / len(arr)
        sd = math.sqrt(sum((x - mu) ** 2 for x in arr) / len(arr)) or 1e-9
        out_langs[l] = {
            "ll": round(obs_raw[l], 4),
            "perm_mean": round(mu, 4),
            "perm_sd": round(sd, 4),
            "z_perm": round((obs_raw[l] - mu) / sd, 3),
            "p_perm": round((1 + ge[l]) / (n_perm + 1), 5),
            "details": det[l],
        }
    ranked = sorted(langs, key=lambda l: -obs_raw[l])
    # Full-precision delta_ll and Bayes factor (no 4-decimal rounding drift)
    dll_raw = obs_raw[ranked[0]] - obs_raw[ranked[1]]
    return {
        "tier": name,
        "scope": scope,
        "n": len(anchors),
        "pa3_folded": pa3_folded,
        "anchors": anchors,
        "winner": ranked[0],
        "runner_up": ranked[1],
        "delta_ll": round(dll_raw, 4),
        "bf": round(math.exp(dll_raw), 2),
        "languages": out_langs,
    }


def run_all(n_perm: int = 10000, seed: int = 20261122, beta: float = 6.0) -> dict:
    tables = r.load_tables()
    sign_table = a.load_signs()
    signs = {k for k in sign_table.values() if isinstance(k, tuple)}
    spelled = ad.spell_synsets(tables, signs)

    tiers_out = {}
    for name, anc, pa3_folded, scope in TIERS:
        tiers_out[name] = run_tier(
            name, anc, pa3_folded, scope, spelled, sign_table, n_perm=n_perm, seed=seed, beta=beta
        )
    return {
        "_meta": {
            "study": "Hypothetical Kernel D' Post-Registration Sensitivity Study",
            "status": "exploratory_sensitivity_only",
            "n_perm": n_perm,
            "seed": seed,
            "beta": beta,
            "frozen_synsets": True,
            "pa3_fold_rule": "PA3 -> ('P', 'a') only on tiers with pa3_folded=true (opaque in signs-a5-proposed.json §15 ruling 3)",
            "anchors_d_sha256": _sha256(ANCHORS_D_PATH),
            "signature_sha256": _sha256(SIGNATURE) if SIGNATURE.is_file() else None,
        },
        "tiers": tiers_out,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Exploratory Kernel D' sensitivity ladder (frozen anchors_d synsets).")
    ap.add_argument("--n-perm", type=int, default=10000)
    ap.add_argument("--seed", type=int, default=20261122)
    ap.add_argument("--beta", type=float, default=6.0)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if not SIGNATURE.is_file():
        print("REFUSED: SIGNATURE.txt not found beside pre-registration.", file=sys.stderr)
        return 2

    res = run_all(n_perm=args.n_perm, seed=args.seed, beta=args.beta)
    if args.json:
        print(json.dumps(res, indent=2))
        return 0

    print(f"=== Hypothetical Kernel D' Sensitivity Study (B={args.n_perm}, seed={args.seed}, frozen anchors_d SYNSETS) ===")
    for name, t in res["tiers"].items():
        s = t["languages"]["semitic"]
        ru = t["languages"][t["runner_up"]]
        print(
            f"{name:<20} n={t['n']:2d} PA3={str(t['pa3_folded']):<5} | {t['winner']:<7} vs {t['runner_up']:<9} | "
            f"dLL={t['delta_ll']:+7.4f} | BF={t['bf']:14,.1f}:1 | "
            f"Sem LL={s['ll']:+8.3f} Z={s['z_perm']:+6.2f} p={s['p_perm']:.5f} | RU Z={ru['z_perm']:+5.2f} p={ru['p_perm']:.5f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
