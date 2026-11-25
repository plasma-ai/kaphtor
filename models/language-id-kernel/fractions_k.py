"""Kernel K: Corazza-Ferrara Metrological Fraction Verification & Blind Accounting Language ID.

Three strictly insulated stages building directly on Corazza, Ferrara, Montecchi, Tamburini,
and Valério (2021, Journal of Archaeological Science 125: 105214):

  - Stage K0 (Language-Free Arithmetic & 3D Autopsy Ledger):
      Applies Corazza et al.'s published A700 fraction values to raw Aegean Unicode numerals
      and fraction glyphs in data/linear-a/corpus.json, compares exact sum-balance counts
      against the older Bennett/GORILA convention, and emits a machine-readable audit ledger
      of residual epigraphic conflicts (notably HT 123+124a *308-column H = A + 1/4, HT 89
      A732, MA 10b OMEGA, and L/A709 exclusion) for 3D/RTI re-examination.
  - Stage K1 (Blind Sum-Word Discovery):
      Scans all 1,719 corpus records with zero lexicon or linguistic assumptions for tokens
      followed by a numeral equal to the sum of preceding contiguous quantities. Surfaces
      KU-RO cleanly at rank #1 using Corazza et al.'s language-independent fraction table.
  - Stage K2 (Calibrated Accounting-Register Language ID):
      Evaluates ONLY the mathematically discovered accounting triad (KU-RO, PO-TO-KU-RO,
      KI-RO) against Kernel J's zero-curation open dictionaries (including CC0 ePSD2 Sumerian
      and LSJ Greek), calibrated on Mycenaean Linear B (TO-SO, O-PE-RO -> Greek). Gated by
      SIGNATURE.txt.

Attribution: di Mino
"""

from __future__ import annotations

import argparse
import json
import sys
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "render"))

import auto_anchors_j as aj  # noqa: E402
import c_align as a  # noqa: E402
import c_render as r  # noqa: E402
import lid  # noqa: E402

SIGNATURE = HERE / "SIGNATURE.txt"
CORPUS_PATH = REPO / "data/linear-a/corpus.json"

# Corazza, Ferrara, Montecchi, Tamburini & Valério (2021, JAS 125: 105214) Table 4 optimal values
# Keyed by Unicode Linear A fraction codepoints (U+10740..U+10755)
CORAZZA_2021: dict[int, Fraction] = {
    0x10746: Fraction(1, 2),  # A707 J
    0x10743: Fraction(1, 4),  # A704 E
    0x10744: Fraction(1, 8),  # A705 F
    0x10742: Fraction(1, 6),  # A703 D (supersedes GORILA 1/5)
    0x10741: Fraction(1, 5),  # A702 B (supersedes GORILA 1/3)
    0x10747: Fraction(1, 10),  # A708 K
    0x10745: Fraction(1, 16),  # A706 H (disputed on HT 123+124a *308)
    0x10740: Fraction(1, 24),  # A701 A (disputed on HT 123+124a *308)
    0x10749: Fraction(1, 20),  # A709-2 L2
    0x1074A: Fraction(1, 30),  # A709-3 L3
    0x1074B: Fraction(1, 40),  # A709-4 L4
    0x1074C: Fraction(1, 60),  # A709-6 L6
    0x1074E: Fraction(1, 12),  # A711 X (= AA)
    0x1074D: Fraction(2, 5),  # A710 W (= BB)
    0x10751: Fraction(53, 120),  # A714 ABB (1/24 + 2/5)
    0x10752: Fraction(2, 5),  # A715 BB (B+B)
    0x10755: Fraction(3, 4),  # A732 JE (J+E; 31x across 24 docs)
    0x10753: Fraction(1, 3),  # A717 DD (D+D)
}

BENNETT_LEGACY: dict[int, Fraction] = {
    **CORAZZA_2021,
    0x10741: Fraction(1, 3),  # B = 1/3
    0x10742: Fraction(1, 5),  # D = 1/5
    0x10753: Fraction(2, 5),  # DD = 2/5
    0x10747: Fraction(1, 16),  # K = 1/16
    0x10749: Fraction(1, 12),  # L2 = 1/12
}

# Language-free epigraphic conflict ledger for 3D/RTI re-examination
AUTOPSY_CONFLICTS: list[dict] = [
    {
        "tablet": "HT 123+124a",
        "column": "*308",
        "signs": ["A706 (H)", "A701 (A)"],
        "corazza_2021": {"H": "1/16", "A": "1/24"},
        "tablet_constraint": "H = A + 1/4 (incompatible with Corazza top-28 space under current GORILA reading)",
        "recommended_action": "3D/RTI autopsy of damaged *308-column numerals and fraction traces.",
    },
    {
        "tablet": "HT 123+124a",
        "column": "KI-RO 6",
        "signs": ["A711 (X)"],
        "corazza_2021": {"X": "1/12"},
        "tablet_constraint": "Fails to balance KI-RO 6 for any X < 1 under current reading.",
        "recommended_action": "Verify KI-RO column entry damage on original tablet / 3D scan.",
    },
    {
        "tablet": "KH 7a (Row 5) & HT 89",
        "column": "CYP+D 1 JE+L2 / CYP 2 JE",
        "signs": ["A732 (JE)", "A709-2 (L2)"],
        "corazza_2021": {"A732": "3/4 (composite J+E; 31x across 24 docs)", "L2": "1/20"},
        "tablet_constraint": (
            "KH 7a Row 5 preserves ration 1 + 3/4 + 1/20 = 1.80 against broken worker count [ ]18 "
            "(additive decimal -> 18 double-ration or 28/38 with lost trailing fraction); "
            "HT 89 pairs CYP 2 JE + NI 2 E = 5.0."
        ),
        "recommended_action": "3D/RTI autopsy of KH 7a Row 5 fracture margins & ductus check of A732 (J+E ligature) on HT 89.",
    },
    {
        "tablet": "MA 10b",
        "column": "MM IIIB (4-sided bar)",
        "signs": ["*405+OMEGA (A713)"],
        "corazza_2021": None,
        "tablet_constraint": (
            "Early Neopalatial MM IIIB 4-sided bar vessel-capacity ligature "
            "(GORILA V, 50-51; possibly CH 304); 0 intact sum equations."
        ),
        "recommended_action": "Cross-check against Cretan Hieroglyphic klasmatograms (Ferrara, Montecchi & Valério 2021/2022).",
    },
    {
        "tablet": "KN 49 / PH 7b / KH 96 / PH 10 / PH 12a / ZA 11a",
        "column": "L-series (8 corpus tokens across 6 docs)",
        "signs": ["A709 (L)"],
        "corazza_2021": {"L": "EXCLUDED (Spearman/chi2; Corazza et al. 2021 fn. 2)"},
        "tablet_constraint": (
            "Statistically rejected as an independent fraction sign by Corazza et al. 2021 "
            "(KN 49 = RILA-S1, 34-35, read L6 by SigLA; PH 7b has 0 L in SigLA)."
        ),
        "recommended_action": "Check whether the 8 corpus A709 tokens are damaged L2-L6 strokes at fracture edges.",
    },
]

LA_ACCOUNTING_PAIR: list[tuple[str, str]] = [
    ("KU-RO", "TOTAL"),
    ("KI-RO", "DEFICIT"),
]

LA_ACCOUNTING_TRIAD: list[tuple[str, str]] = [
    ("KU-RO", "TOTAL"),
    ("PO-TO-KU-RO", "TOTAL"),
    ("KI-RO", "DEFICIT"),
]

LB_ACCOUNTING_PAIR: list[tuple[str, str]] = [
    ("TO-SO", "TOTAL"),
    ("O-PE-RO", "DEFICIT"),
]


def parse_aegean_quantity(raw_token: str, fmap: dict[int, Fraction]) -> Fraction | None:
    """Parse raw Aegean Unicode numerals (U+10107..U+1012A) + Linear A fraction glyphs."""
    total = Fraction(0)
    saw = False
    for ch in raw_token:
        cp = ord(ch)
        if 0x10107 <= cp <= 0x1010F:
            total += cp - 0x10106
            saw = True
        elif 0x10110 <= cp <= 0x10118:
            total += (cp - 0x1010F) * 10
            saw = True
        elif 0x10119 <= cp <= 0x10121:
            total += (cp - 0x10118) * 100
            saw = True
        elif 0x10122 <= cp <= 0x1012A:
            total += (cp - 0x10121) * 1000
            saw = True
        elif cp in fmap:
            total += fmap[cp]
            saw = True
    return total if saw else None


def load_corpus_records(corpus_path: Path = CORPUS_PATH) -> dict[str, dict]:
    data = json.loads(corpus_path.read_text(encoding="utf-8"))
    docs = data.get("inscriptions") or data.get("documents") or data
    return docs if isinstance(docs, dict) else {d["name"]: d for d in docs}


def discover_sum_words(
    records: dict[str, dict],
    fmap: dict[int, Fraction] = CORAZZA_2021,
    min_target: int = 4,
) -> dict[str, list[dict]]:
    """Stage K1: Zero-lexicon scan surfacing candidate totalling words via exact suffix sums."""
    exact_hits: dict[str, list[dict]] = {}
    for name, doc in records.items():
        tw = [str(x) for x in (doc.get("transliteratedWords") or [])]
        ws = [str(x) for x in (doc.get("words") or [])]
        if len(tw) != len(ws):
            continue
        items: list[tuple[str, object]] = []
        i = 0
        while i < len(tw):
            tok, raw = tw[i], ws[i]
            if tok in ("\n", "𐄁", "—", "–", ""):
                i += 1
                continue
            has_syll_or_logo = any(0x10600 <= ord(c) <= 0x1073F for c in raw)
            val = None if has_syll_or_logo else parse_aegean_quantity(raw, fmap)
            if val is not None:
                j = i + 1
                while j < len(tw):
                    if tw[j] in ("𐄁", ""):
                        j += 1
                        continue
                    v2 = parse_aegean_quantity(ws[j], fmap)
                    if v2 is not None and not any(0x10600 <= ord(c) <= 0x1073F for c in ws[j]):
                        val += v2
                        j += 1
                    else:
                        break
                items.append(("NUM", val))
                i = j
            else:
                items.append(("TOK", tok))
                i += 1

        nums_so_far: list[Fraction] = []
        for idx, (kind, val) in enumerate(items):
            if kind == "NUM":
                nums_so_far.append(val)  # type: ignore[arg-type]
            elif kind == "TOK" and idx + 1 < len(items) and items[idx + 1][0] == "NUM":
                target: Fraction = items[idx + 1][1]  # type: ignore[assignment]
                if target >= min_target and len(nums_so_far) >= 2:
                    acc = Fraction(0)
                    for back in range(1, len(nums_so_far) + 1):
                        acc += nums_so_far[-back]
                        if back >= 2 and acc == target:
                            exact_hits.setdefault(str(val), []).append(
                                {
                                    "tablet": name,
                                    "total": float(target),
                                    "total_exact": str(target),
                                    "n_addends": back,
                                }
                            )
                            break
                        if acc > target:
                            break
    return exact_hits


def audit_compound_fraction_properness(records: dict[str, dict]) -> dict:
    """Stage K0b: Check Corazza et al. (2021) vs. Bennett legacy on compound fractions (< 1 constraint)."""
    corazza_gt1, bennett_gt1, eq1_repeated = [], [], []
    total = 0
    for name, doc in sorted(records.items()):
        ws = [str(x) for x in (doc.get("words") or [])]
        i = 0
        while i < len(ws):
            fchars = [ch for ch in ws[i] if 0x10740 <= ord(ch) <= 0x10755]
            j = i + 1
            if fchars and not any(0x10600 <= ord(c) <= 0x1073F for c in ws[i]):
                while j < len(ws):
                    fc2 = [ch for ch in ws[j] if 0x10740 <= ord(ch) <= 0x10755]
                    if fc2 and len(fc2) == len(ws[j].strip()):
                        fchars.extend(fc2)
                        j += 1
                    else:
                        break
                if len(fchars) >= 2 and all(ord(c) in CORAZZA_2021 for c in fchars):
                    total += 1
                    vc = sum(CORAZZA_2021[ord(c)] for c in fchars)
                    vb = sum(BENNETT_LEGACY[ord(c)] for c in fchars)
                    glyphs = "".join(fchars)
                    if vc > 1:
                        corazza_gt1.append({"tablet": name, "glyphs": glyphs, "value": str(vc)})
                    if vb > 1:
                        bennett_gt1.append({"tablet": name, "glyphs": glyphs, "value": str(vb)})
                    if vc == 1 and vb == 1:
                        eq1_repeated.append({"tablet": name, "glyphs": glyphs, "value": "1"})
            i = j if j > i + 1 else i + 1
    return {
        "n_compound_fractions": total,
        "corazza_2021_strict_gt1_violations": len(corazza_gt1),
        "bennett_legacy_strict_gt1_violations": len(bennett_gt1),
        "corazza_2021_gt1_witnesses": corazza_gt1,
        "bennett_legacy_gt1_witnesses": bennett_gt1,
        "repeated_unit_eq1_witnesses": eq1_repeated,
    }


def run_stage_k0_k1(corpus_path: Path = CORPUS_PATH) -> dict:
    """Run language-free Stage K0 (Corazza vs. legacy + properness + autopsy ledger) & Stage K1 (blind discovery)."""
    records = load_corpus_records(corpus_path)
    hits_corazza = discover_sum_words(records, CORAZZA_2021)
    hits_legacy = discover_sum_words(records, BENNETT_LEGACY)
    properness = audit_compound_fraction_properness(records)

    ranked = sorted(
        (
            {"word": w, "exact_sums": len(ev), "witnesses": ev}
            for w, ev in hits_corazza.items()
        ),
        key=lambda x: (-x["exact_sums"], x["word"]),
    )
    return {
        "n_records_scanned": len(records),
        "compound_fraction_properness": properness,
        "corazza_2021_top_candidates": ranked[:10],
        "corazza_kuro_exact_sums": len(hits_corazza.get("KU-RO", [])),
        "bennett_legacy_kuro_exact_sums": len(hits_legacy.get("KU-RO", [])),
        "top_discovered_sum_word": ranked[0]["word"] if ranked else None,
        "runner_up_exact_sums": ranked[1]["exact_sums"] if len(ranked) > 1 else 0,
        "autopsy_conflicts": AUTOPSY_CONFLICTS,
    }


def run_stage_k2(cap: int = 40, n_perm: int = 5000, seed: int = 20261124, beta: float = 6.0) -> dict:
    """Stage K2: Calibrated Kernel J open-dictionary LID on accounting-only words (deduplicated pair & triad)."""
    tables, signs = r.load_tables(), lid.sign_keys()
    sign_table = a.load_signs()
    synsets, counts = aj.extract_auto_synsets(tables, signs, max_per_concept=cap if cap > 0 else None)
    out: dict = {
        "cap": cap,
        "beta": beta,
        "n_perm": n_perm,
        "seed": seed,
        "synset_counts_accounting": {k: counts[k] for k in ("TOTAL", "DEFICIT") if k in counts},
        "calibration_linear_b": aj.run_battery(
            LB_ACCOUNTING_PAIR, synsets, sign_table, n_perm=n_perm, seed=seed, beta=beta
        ),
    }
    if SIGNATURE.exists():
        out["linear_a_accounting_pair_dedup"] = aj.run_battery(
            LA_ACCOUNTING_PAIR, synsets, sign_table, n_perm=n_perm, seed=seed, beta=beta
        )
        out["linear_a_accounting_triad"] = aj.run_battery(
            LA_ACCOUNTING_TRIAD, synsets, sign_table, n_perm=n_perm, seed=seed, beta=beta
        )
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Kernel K: Corazza-Ferrara Fractions & Blind Accounting LID.")
    ap.add_argument("--autopsy-conflicts", action="store_true", help="Print Stage K0 language-free conflict ledger only")
    ap.add_argument("--no-lid", action="store_true", help="Run strictly language-free Stages K0-K1 only")
    ap.add_argument("--cap", type=int, default=40)
    ap.add_argument("--n-perm", type=int, default=5000)
    ap.add_argument("--seed", type=int, default=20261124)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.autopsy_conflicts:
        print(json.dumps({"autopsy_conflicts": AUTOPSY_CONFLICTS}, indent=2))
        return 0

    k01 = run_stage_k0_k1()
    out: dict = {"stage_k0_k1_language_free": k01}
    if not args.no_lid:
        out["stage_k2_accounting_lid"] = run_stage_k2(cap=args.cap, n_perm=args.n_perm, seed=args.seed)

    if args.json:
        print(json.dumps(out, indent=2))
        return 0

    print("=== Kernel K: Corazza-Ferrara (2021) Fractions & Blind Accounting Discovery ===")
    print(f"Scanned {k01['n_records_scanned']} Linear A records (language-free):")
    for row in k01["corazza_2021_top_candidates"][:5]:
        tabs = [w["tablet"] for w in row["witnesses"][:6]]
        print(f"  {row['word']:<14} exact_sums={row['exact_sums']:2d}  tablets={tabs}")
    print(f"Autopsy conflicts logged for 3D/RTI verification: {len(k01['autopsy_conflicts'])}")

    if "stage_k2_accounting_lid" in out:
        k2 = out["stage_k2_accounting_lid"]
        for key in ("calibration_linear_b", "linear_a_accounting_pair_dedup", "linear_a_accounting_triad"):
            if key not in k2:
                continue
            b = k2[key]
            print(f"\n--- {key} (winner={b['winner']}, ΔLL={b['delta_ll']:+.3f}) ---")
            for lang, d in sorted(b["languages"].items(), key=lambda kv: -kv[1]["ll"]):
                print(f"  {lang:<12} LL={d['ll']:+8.3f}  Z={d['z_perm']:+6.2f}  p={d['p_perm']:.5f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
