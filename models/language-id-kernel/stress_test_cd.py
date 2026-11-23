"""Stress-test battery for Kernels D (Pre-Linguistic Anchors) and C (Liturgical Cohesion).

Requires SIGNATURE.txt (signed 2026-11-22).
Runs:
  1. Kernel D Leave-One-Anchor-Out (10,000 grid permutations each) + Trade-Loanword Drop ablation.
  2. Kernel C on IO Za 2 alone, Full 33-inscription Libation Formula Family (undamaged distinct types),
     and Formula Family excluding IO Za 2's 7 words (2,000 grid permutations each).

Writes full JSON output to runs/stress-test-cd-2026-11-22.json.

Attribution: di Mino
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PC = HERE
sys.path.insert(0, str(HERE / "render"))

import anchors_d as ad  # noqa: E402
import c_align as a     # noqa: E402
import c_render as r    # noqa: E402
import liturgy_c as lc  # noqa: E402

SIGNATURE = HERE / "SIGNATURE.txt"
FORMULA_FAMILY = HERE.parents[1] / "ioza2-adjudication/data/formula_family.json"


def load_formula_family_types(sign_table: dict) -> tuple[list[str], list[str]]:
    """Return (all undamaged distinct formula types >= 2 signs, subset excluding IO Za 2's 7 forms)."""
    raw = json.loads(FORMULA_FAMILY.read_text(encoding="utf-8"))
    seen: list[str] = []
    seen_set: set[str] = set()
    for ins in raw.get("inscriptions", []):
        for tok in ins.get("tokens", []):
            if tok.get("damaged"):
                continue
            la = tok.get("linear_a", "").strip()
            if not la or any(ch in la for ch in "[]?+0123456789/\\· "):
                # Note: allow *301 etc. (a.keys keeps them as opaque symbols)
                if "*" not in la:
                    continue
            keys = a.keys(la, sign_table)
            if len(keys) >= 2 and la not in seen_set:
                seen_set.add(la)
                seen.append(la)
    ioza2_set = set(lc.IO_ZA_2_STRICT)
    non_ioza2 = [w for w in seen if w not in ioza2_set]
    return seen, non_ioza2


def main() -> int:
    if not SIGNATURE.is_file():
        print("REFUSED: SIGNATURE.txt missing.", file=sys.stderr)
        return 2

    t0 = time.time()
    tables = r.load_tables()
    sign_table = a.load_signs()
    signs = {k for k in sign_table.values() if isinstance(k, tuple)}

    # ---- 1. Kernel D Stress Tests (10,000 grid perms each) ----
    d_runs = {}
    subsets: list[tuple[str, list[tuple[str, str]]]] = [("FULL_8", ad.LINEAR_A_ANCHORS_STRICT)]
    for idx, (form, concept) in enumerate(ad.LINEAR_A_ANCHORS_STRICT):
        subsets.append((f"DROP_{form}", [x for j, x in enumerate(ad.LINEAR_A_ANCHORS_STRICT) if j != idx]))
    # Trade-loanword ablation: drop A-KA-NU, KU-NI-SU, KA-DI (3 classic Levantine trade terms)
    trade3 = {"A-KA-NU", "KU-NI-SU", "KA-DI"}
    subsets.append(("DROP_3_TRADE_LOANS", [x for x in ad.LINEAR_A_ANCHORS_STRICT if x[0] not in trade3]))
    # Arithmetic only (KU-RO, KI-RO)
    subsets.append(("ARITHMETIC_ONLY_2", [x for x in ad.LINEAR_A_ANCHORS_STRICT if x[1] in ("TOTAL", "DEFICIT")]))

    print("=== Kernel D Stress Tests (B=10,000 consonant-grid permutations) ===", flush=True)
    for label, anc in subsets:
        res = ad.run_battery(anc, tables, sign_table, signs, n_perm=10000, seed=20261122)
        sem = res["languages"]["semitic"]
        runner_lang = max(("greek", "anatolian", "hurrian"), key=lambda l: res["languages"][l]["ll"])
        dll = sem["ll"] - res["languages"][runner_lang]["ll"]
        d_runs[label] = {
            "n_anchors": len(anc),
            "winner": res["winner"],
            "sem_ll": sem["ll"],
            "runner_up": runner_lang,
            "dLL": round(dll, 3),
            "sem_z": sem["z_perm"],
            "sem_p": sem["p_perm"],
        }
        print(
            f"  {label:20s} (n={len(anc)}) | winner={res['winner']:9s} | dLL={dll:+6.2f} (vs {runner_lang:9s}) "
            f"| Z_perm={sem['z_perm']:+6.2f} | p_perm={sem['p_perm']:.5f}",
            flush=True,
        )

    # ---- 2. Kernel C Stress Tests (2,000 grid perms each) ----
    all_fam, non_ioza2_fam = load_formula_family_types(sign_table)
    lex_c = lc.build_size_locked_lexicons(k_top=300, conv="plene")
    c_targets = [
        ("IO_ZA_2_7", lc.IO_ZA_2_STRICT),
        ("FORMULA_FAMILY_ALL", all_fam),
        ("FORMULA_FAMILY_EXCL_IOZA2", non_ioza2_fam),
    ]
    c_runs = {}
    print("\n=== Kernel C Stress Tests (K=300 size-locked, B=2,000 consonant-grid perms) ===", flush=True)
    for label, forms in c_targets:
        parsed = [a.keys(w, sign_table) for w in forms]
        res_arms = {arm: lc.perm_z_score(parsed, vocab, n_perm=2000, seed=20261122) for arm, vocab in lex_c.items()}
        winner = max(res_arms, key=lambda arm: res_arms[arm]["z_perm"])
        c_runs[label] = {"n_types": len(forms), "winner": winner, "arms": res_arms}
        h = res_arms["hebrew_lit"]
        print(
            f"  {label:26s} (n={len(forms):2d}) | winner={winner:13s} "
            f"| heb_lit score={h['score']:.4f} Z={h['z_perm']:+6.2f} p={h['p_perm']:.5f}",
            flush=True,
        )
        for arm, s in res_arms.items():
            if arm != "hebrew_lit":
                print(f"      {arm:14s}: score={s['score']:.4f} Z={s['z_perm']:+6.2f} p={s['p_perm']:.5f}", flush=True)

    out_path = HERE / "runs" / "stress-test-cd-2026-11-22.json"
    record = {
        "seconds": round(time.time() - t0, 1),
        "kernel_d_stress": d_runs,
        "kernel_c_stress": c_runs,
        "formula_family_types": all_fam,
    }
    out_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nWrote {out_path} in {record['seconds']}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
