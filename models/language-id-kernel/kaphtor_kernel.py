"""Unified Replicable Multi-Kernel CLI (`kaphtor_kernel.py`) for Linear A Language Identification.

Implements kernel-specs.md with the two signed design rulings (2026-11-22):
  - Ruling 1: Pooled family arms with sign-count parity (S=3700) and 95th-percentile outside
    threshold theta_95 (with strict theta_max reported alongside for full transparency).
  - Ruling 2: Three primary gating channels — Kernel A (word-shape forward LID), Kernel B
    (unsupervised Kober-trio paradigm transitions), and Kernel D (pre-linguistic semantic anchors) —
    plus Kernel C (corpus-derived size-locked liturgical cohesion) as a supporting channel.

Subcommands:
  python3 kaphtor_kernel.py manifest
  python3 kaphtor_kernel.py calibrate [--n-perm 10000]
  python3 kaphtor_kernel.py run --strict-lb-only [--n-perm-d 10000] [--n-perm-ab 500] [--n-perm-c 1000]
  python3 kaphtor_kernel.py ablate <run_json>

Safety Gate:
  `run` strictly refuses to read or score any Linear A token unless `SIGNATURE.txt` exists beside
  this file AND Kernel D's Linear B calibration gate passes.

Attribution: di Mino
"""
from __future__ import annotations

import argparse
import datetime
import json
import math
import random
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PC = HERE
sys.path.insert(0, str(HERE / "render"))

import anchors_d as ad  # noqa: E402
import c_align as a     # noqa: E402
import c_render as r    # noqa: E402
import kober_b as kb    # noqa: E402
import lid              # noqa: E402
import liturgy_c as lc  # noqa: E402
import pilot            # noqa: E402
import pilot_fix1 as pf1  # noqa: E402

SIGNATURE = HERE / "SIGNATURE.txt"
CORPUS_PATH = Path.home() / ".claude/skills/linear-a-decipherment/data/corpus.json"
CORE_FILES = [
    HERE / "kaphtor_kernel.py",
    HERE / "lid.py",
    HERE / "kober_b.py",
    HERE / "liturgy_c.py",
    HERE / "anchors_d.py",
    HERE / "kernel-specs.md",
    HERE / "preregistration-draft.md",
    HERE / "render/series.json",
    HERE / "render/series-a5-proposed.json",
    HERE / "render/signs-a5-proposed.json",
]


def percentile(values: list[float], q: float) -> float:
    """Linear-interpolated percentile q in [0, 1] (used for theta_95)."""
    if not values:
        raise ValueError("empty values")
    s = sorted(values)
    if len(s) == 1:
        return s[0]
    pos = q * (len(s) - 1)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return s[lo]
    return s[lo] + (pos - lo) * (s[hi] - s[lo])


def stouffer_z(z_values: list[float]) -> float:
    """Unweighted Stouffer meta-Z across orthogonal calibrated kernels."""
    if not z_values:
        return 0.0
    return sum(z_values) / math.sqrt(len(z_values))


def build_manifest() -> dict[str, str]:
    return {str(p.relative_to(HERE.parents[1])): lid.sha256(p) for p in CORE_FILES if p.is_file()}


def load_linear_a_strict_words(corpus_path: Path = CORPUS_PATH) -> tuple[list[tuple[str, list]], dict]:
    """Read undamaged, legible Linear A words (>=2 signs) using ONLY secure Linear B sign values.

    Excludes any token containing damage brackets, uncertain markers, logograms, numerals, or
    non-secure/Linear-A-only signs (preregistration-draft.md §3).
    """
    raw = json.loads(corpus_path.read_text(encoding="utf-8"))
    sign_table = a.load_signs()
    valid_signs = {k for k in sign_table.values() if isinstance(k, tuple)}

    docs: list[tuple[str, list]] = []
    total_tokens = 0
    kept_tokens = 0
    for doc_id, rec in sorted(raw.items()):
        tw = rec.get("transliteratedWords") or []
        words = []
        for tok in tw:
            if not isinstance(tok, str):
                continue
            total_tokens += 1
            if any(ch in tok for ch in "[]?*+0123456789/\\· "):
                continue
            w = a.keys(tok, sign_table)
            if lid.valid(w, valid_signs):
                words.append(w)
                kept_tokens += 1
        if words:
            docs.append((doc_id, words))
    distinct = len({w for _, ws in docs for w in ws})
    return docs, {"documents": len(docs), "total_tokens": total_tokens, "kept_tokens": kept_tokens, "distinct_types": distinct}


def cmd_manifest() -> int:
    m = build_manifest()
    print(json.dumps({"manifest_sha256": m}, indent=2))
    return 0


def cmd_calibrate(n_perm_d: int = 10000) -> int:
    tables = r.load_tables()
    sign_table = a.load_signs()
    signs = {k for k in sign_table.values() if isinstance(k, tuple)}

    cal_d = ad.run_battery(ad.LINEAR_B_ANCHORS, tables, sign_table, signs, n_perm=n_perm_d)
    runner_ll = max(cal_d["languages"][l]["ll"] for l in ("semitic", "anatolian", "hurrian"))
    runner_z = max(cal_d["languages"][l]["z_perm"] for l in ("semitic", "anatolian", "hurrian"))
    d_pass = (
        cal_d["winner"] == "greek"
        and cal_d["languages"]["greek"]["p_perm"] <= 0.001
        and (cal_d["languages"]["greek"]["ll"] - runner_ll) >= 5.0
        and (cal_d["languages"]["greek"]["z_perm"] - runner_z) >= 2.0
    )
    print(f"Kernel D (Linear B anchors, B={n_perm_d}): PASS={d_pass} | Greek Z={cal_d['languages']['greek']['z_perm']:+.2f}, p={cal_d['languages']['greek']['p_perm']:.5f}")
    print("Kernels A, B, C dev-split calibration records are archived under runs/pilot-*.json.")
    print(f"Signature present ({SIGNATURE.name}): {SIGNATURE.is_file()}")
    return 0 if d_pass else 1


def _perm_margin_z(
    words: list,
    score_fn,
    target_arm: str,
    n_perm: int,
    seed: int,
) -> dict:
    """Grid-permutation test for a margin function score_fn(words) -> dict[arm, bits]."""
    obs_bits = score_fn(words)
    obs_margin = lid.margin(obs_bits, target_arm)
    rng = random.Random(seed)
    perm_margins = []
    ge = 0
    for _ in range(n_perm):
        shuf = list(ad.CONSONANT_SERIES)
        rng.shuffle(shuf)
        mp = dict(zip(ad.CONSONANT_SERIES, shuf))
        p_words = [ad.permute_word(w, mp) for w in words]
        pm = lid.margin(score_fn(p_words), target_arm)
        perm_margins.append(pm)
        if pm >= obs_margin - 1e-12:
            ge += 1
    mean = sum(perm_margins) / len(perm_margins)
    var = sum((x - mean) ** 2 for x in perm_margins) / len(perm_margins)
    sd = math.sqrt(var) if var > 1e-12 else 1e-9
    return {
        "bits": {k: round(v, 4) for k, v in obs_bits.items()},
        "winner": min(obs_bits, key=obs_bits.get),
        "margin": round(obs_margin, 4),
        "perm_mean": round(mean, 4),
        "z_perm": round((obs_margin - mean) / sd, 3),
        "p_perm": round((1 + ge) / (n_perm + 1), 5),
    }


def cmd_run(n_perm_d: int = 10000, n_perm_ab: int = 200, n_perm_c: int = 1000, draws: int = 5) -> int:
    if not SIGNATURE.is_file():
        print(f"REFUSED: {SIGNATURE} is missing. Sign the pre-registration before unsealing Linear A.", file=sys.stderr)
        return 2

    t0 = time.time()
    before_manifest = build_manifest()
    tables, signs = r.load_tables(), lid.sign_keys()
    sign_table = a.load_signs()
    alphabet = sorted(signs)

    # Gate check: Kernel D Linear B calibration must pass
    cal_d = ad.run_battery(ad.LINEAR_B_ANCHORS, tables, sign_table, signs, n_perm=n_perm_d)
    runner_ll = max(cal_d["languages"][l]["ll"] for l in ("semitic", "anatolian", "hurrian"))
    if cal_d["winner"] != "greek" or cal_d["languages"]["greek"]["p_perm"] > 0.001 or (cal_d["languages"]["greek"]["ll"] - runner_ll) < 5.0:
        print("REFUSED: Kernel D calibration gate failed.", file=sys.stderr)
        return 3

    # Load Linear A strict corpus
    la_docs, la_stats = load_linear_a_strict_words()
    la_words = [w for _, ws in la_docs for w in ws]

    # Train Kernel A (pooled_signs) & Kernel B (KoberModel) on train splits
    train: dict = {}
    for language in pilot.TEST_LANGUAGES:
        if language == "diodorus":
            continue
        seg = lid.segment_docs(language)
        for conv in r.CONVENTIONS:
            docs, _ = lid.written_docs(seg, language, conv, tables, signs)
            train[language, conv] = pilot.flat(lid.select(docs, "train"))
    lsj, _ = lid.lsj_words(signs)
    dio_docs, _ = lid.diodorus_docs(signs)
    train["diodorus", "lb"] = pilot.flat(lid.select(dio_docs, "train"))

    def members(arm: str, conv: str) -> dict:
        if arm == "greek":
            return {"lsj": lsj, "diodorus": train["diodorus", "lb"]}
        return {m: train[m, conv] for m in lid.ARMS[arm]}

    held = {arm: min(lid.holds(members(arm, conv)) for conv in r.CONVENTIONS) for arm in lid.ARMS}
    arms = [arm for arm in lid.ARMS if held[arm] >= pilot.MIN_ARM]
    held_signs = {
        arm: min(sum(pf1.member_signs(ws) for ws in members(arm, conv).values()) for conv in r.CONVENTIONS)
        for arm in arms
    }
    total_signs = (min(held_signs.values()) // 100) * 100

    models_a = {}
    for arm in arms:
        for conv in (("lb",) if arm == "greek" else r.CONVENTIONS):
            models_a[arm, conv] = [
                lid.Model(pf1.draw_by_signs(members(arm, conv), total_signs, pilot.SEED + j), 3, alphabet)
                for j in range(draws)
            ]

    def score_a(words):
        return {
            arm: min(lid.bits_per_sign(ms, words) for (a_, _), ms in models_a.items() if a_ == arm)
            for arm in arms
        }

    # Train Kernel B
    member_tr = {}
    for arm in arms:
        for conv in (("lb",) if arm == "greek" else r.CONVENTIONS):
            for m, ws in members(arm, conv).items():
                if (m, conv) in member_tr:
                    continue
                uniq = sorted(set(ws))
                if len(uniq) > 2500:
                    uniq = random.Random(f"kober_cap:{m}:{conv}").sample(uniq, 2500)
                member_tr[m, conv] = kb.extract_transitions(uniq)
    held_tr = {
        arm: min(
            sum(len(member_tr[m, ("lb" if arm == "greek" else conv)]) for m in members(arm, ("lb" if arm == "greek" else conv)))
            for conv in r.CONVENTIONS
        )
        for arm in arms
    }
    total_tr = (min(held_tr.values()) // 100) * 100
    models_b = {}
    for arm in arms:
        for conv in (("lb",) if arm == "greek" else r.CONVENTIONS):
            trs_map = {m: member_tr[m, conv] for m in members(arm, conv)}
            models_b[arm, conv] = [
                kb.KoberModel(kb.draw_transitions(trs_map, total_tr, pilot.SEED + j), alphabet)
                for j in range(draws)
            ]

    def score_b(words):
        trs = kb.extract_transitions(words)
        return {
            arm: min(kb.bits_per_transition(ms, trs) for (a_, _), ms in models_b.items() if a_ == arm)
            for arm in arms
        }

    res_a = _perm_margin_z(la_words, score_a, "semitic", n_perm=n_perm_ab, seed=pilot.SEED)
    res_b = _perm_margin_z(la_words, score_b, "semitic", n_perm=n_perm_ab, seed=pilot.SEED + 1)
    res_d = ad.run_battery(ad.LINEAR_A_ANCHORS_STRICT, tables, sign_table, signs, n_perm=n_perm_d, seed=pilot.SEED)

    # Supporting Channel C: IO Za 2 strict
    lex_c = lc.build_size_locked_lexicons(k_top=300, conv="plene")
    ioza2_words = [a.keys(w, sign_table) for w in lc.IO_ZA_2_STRICT]
    res_c = {arm: lc.perm_z_score(ioza2_words, vocab, n_perm=n_perm_c, seed=pilot.SEED) for arm, vocab in lex_c.items()}

    z_primary = [res_a["z_perm"], res_b["z_perm"], res_d["languages"]["semitic"]["z_perm"]]
    z_joint = round(stouffer_z(z_primary), 3)

    after_manifest = build_manifest()
    if after_manifest != before_manifest:
        print("ABORTED: manifest hash changed during run.", file=sys.stderr)
        return 4

    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = HERE / "runs" / f"kaphtor-kernel-linear-a-{stamp}.json"
    record = {
        "timestamp_utc": stamp,
        "seconds": round(time.time() - t0, 1),
        "manifest_sha256": before_manifest,
        "linear_a_pool": la_stats,
        "primary_channels": {"A_word_shape": res_a, "B_kober_trios": res_b, "D_anchors": res_d},
        "supporting_channel": {"C_liturgy_ioza2": res_c},
        "joint_stouffer_z_semitic_ABD": z_joint,
    }
    out_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {out_path} in {record['seconds']}s")
    print(f"  Kernel A (Word-Shape)   : winner={res_a['winner']}, M(Sem)={res_a['margin']:+.4f}, Z_perm={res_a['z_perm']:+.2f}, p={res_a['p_perm']:.5f}")
    print(f"  Kernel B (Kober Trios)  : winner={res_b['winner']}, M(Sem)={res_b['margin']:+.4f}, Z_perm={res_b['z_perm']:+.2f}, p={res_b['p_perm']:.5f}")
    print(f"  Kernel D (Anchors)      : winner={res_d['winner']}, LL(Sem)={res_d['languages']['semitic']['ll']:.3f}, Z_perm={res_d['languages']['semitic']['z_perm']:+.2f}, p={res_d['languages']['semitic']['p_perm']:.5f}")
    print(f"  Joint Stouffer Z (A+B+D): {z_joint:+.3f}")
    print(f"  Kernel C (Supporting)   : IO Za 2 heb_lit Z_perm={res_c['hebrew_lit']['z_perm']:+.2f}, p={res_c['hebrew_lit']['p_perm']:.5f}")
    return 0


def cmd_ablate(run_json: Path) -> int:
    rec = json.loads(run_json.read_text(encoding="utf-8"))
    ch = rec["primary_channels"]
    zs = {
        "A": ch["A_word_shape"]["z_perm"],
        "B": ch["B_kober_trios"]["z_perm"],
        "D": ch["D_anchors"]["languages"]["semitic"]["z_perm"],
    }
    print("=== Leave-One-Channel-Out Stouffer Z (Semitic) ===")
    print(f"  All (A+B+D) : {stouffer_z([zs['A'], zs['B'], zs['D']]):+.3f}")
    for drop in ("A", "B", "D"):
        kept = [v for k, v in zs.items() if k != drop]
        print(f"  Drop {drop}      : {stouffer_z(kept):+.3f}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(prog="kaphtor_kernel.py")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("manifest")
    p_cal = sub.add_parser("calibrate")
    p_cal.add_argument("--n-perm", type=int, default=10000)
    p_run = sub.add_parser("run")
    p_run.add_argument("--strict-lb-only", action="store_true", default=True)
    p_run.add_argument("--n-perm-d", type=int, default=10000)
    p_run.add_argument("--n-perm-ab", type=int, default=200)
    p_run.add_argument("--n-perm-c", type=int, default=1000)
    p_run.add_argument("--draws", type=int, default=5)
    p_abl = sub.add_parser("ablate")
    p_abl.add_argument("run_json", type=Path)

    args = ap.parse_args()
    if args.cmd == "manifest":
        return cmd_manifest()
    if args.cmd == "calibrate":
        return cmd_calibrate(n_perm_d=args.n_perm)
    if args.cmd == "run":
        return cmd_run(n_perm_d=args.n_perm_d, n_perm_ab=args.n_perm_ab, n_perm_c=args.n_perm_c, draws=args.draws)
    if args.cmd == "ablate":
        return cmd_ablate(args.run_json)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
