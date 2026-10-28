#!/usr/bin/env python3
"""Option B runner (PROTOCOL-B §§5–6, §9–10).

  null      Monte Carlo replicates of the family under D, D2 or D2×2, scored by
            paradigm.score with the same folds as the observed family
  observed  the family and every B2 control window (refuses before the B freeze)
  gate      G1–G3 from an observed run and its null runs; the §10 posterior
            only if G1 and G2 pass

Production budgets and seeds are PROTOCOL-B §6's; --B and --seed are honoured
only with --debug. Configuration flags select the ablations of §11; the gate
configuration is strict / base / leave-one-site-out.

Run: uv run python scripts/run_paradigm.py null --null D2 --debug --B 1000
Attribution: di Mino.
"""
from __future__ import annotations

import argparse
import json
import math
import multiprocessing as mp
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import paths  # noqa: E402
from common import nulls, paradigm, stats  # noqa: E402

BASE_SEED = 20260908
NULL_SEED = {"D": BASE_SEED + 5, "D2": BASE_SEED + 6, "D2x2": BASE_SEED + 7}
NULL_B = {"D": 10_000, "D2": 10_000, "D2x2": 10_000}
SPLIT_SEED, N_SPLITS, N_HELD = BASE_SEED + 11, 1000, 8
FAMILY_MEAN_SIGNS, BAND = 3.59, 0.5
FREEZE_REASON = "refreeze_reason: option B freeze"
STATS = ("A_free", "A_cs", "A_nws_floor", "A_luwian", "A_hurrian", "A_egyptian", "delta", "delta_floor")
PRIORS = (0.02, 0.05, 0.10, 0.25, 0.50)
SCHEMES = {"uniform": {"H_ISO": 1, "luwian": 1, "hurrian": 1, "egyptian": 1, "H3": 1},
           "archaeology": {"H_ISO": 0.40 + 0.05, "luwian": 0.20, "hurrian": 0.10, "egyptian": 0.10, "H3": 0.15},
           "nws_skeptic": {"H_ISO": 0.30 + 0.10, "luwian": 0.10, "hurrian": 0.05, "egyptian": 0.05, "H3": 0.40}}

_G: dict = {}   # worker globals (fork)


def frozen() -> bool:
    return paths.PROTOCOL.exists() and FREEZE_REASON in paths.PROTOCOL.read_text()


def config_from_args(args) -> dict:
    return {"strict": not args.cons, "variant": "ext" if args.ext else "base", "with_sabaic": args.with_sabaic,
            "folds": args.folds, "drop_slots": tuple(args.drop_slot or ()), "drop_damaged": args.drop_damaged}


def config_tag(cfg: dict) -> str:
    parts = ["strict" if cfg["strict"] else "cons", cfg["variant"]]
    if cfg["with_sabaic"]:
        parts.append("sabaic")
    if cfg["folds"] != "lso":
        parts.append(cfg["folds"])
    if cfg["drop_slots"]:
        parts.append("drop" + "".join(cfg["drop_slots"]))
    if cfg["drop_damaged"]:
        parts.append("nodmg")
    return "-".join(parts)


def inventories(cfg: dict) -> dict[str, paradigm.Inventory]:
    """cs and nws_floor in the configured variant; rivals always base (a rival
    arm has no ext inventory, PROTOCOL-B §4.3)."""
    invs = {"cs": paradigm.load_inventory("cs", cfg["variant"], with_sabaic=cfg["with_sabaic"]),
            "nws_floor": paradigm.load_inventory("nws_floor", cfg["variant"])}
    for r in paradigm.RIVALS:
        invs[r] = paradigm.load_inventory(r, "base")
    for inv in invs.values():
        paradigm.indices(inv)
    return invs


def family_folds(cfg: dict, toks: list[paradigm.Token]) -> list[frozenset[str]]:
    if cfg["folds"] == "lso":
        return paradigm.leave_one_group_out(toks)
    units = sorted({i.id for i in nulls.observed_family()})
    return paradigm.random_splits(units, N_HELD, N_SPLITS, SPLIT_SEED)


def vector(res: dict) -> tuple[float, ...]:
    A = res["A"]
    return (A["free"], A["cs"], A["nws_floor"], A["luwian"], A["hurrian"], A["egyptian"],
            res["delta"], res["delta_floor"])


# ---------------------------------------------------------------------------
# null replicates
# ---------------------------------------------------------------------------

def setup(cfg: dict, null: str) -> None:
    """Everything a replicate needs, built once (in the parent, before fork)."""
    fam = nulls.observed_family()
    _G["cfg"] = cfg
    _G["null"] = null
    _G["family"] = fam
    _G["index"] = paradigm.family_slot_index()
    _G["invs"] = inventories(cfg)
    _G["model"] = nulls.SignModel(nulls.corpus_syllabic_words({i.id for i in fam}))
    obs_toks = paradigm.family_tokens(fam, _G["index"], drop_slots=cfg["drop_slots"], drop_damaged=cfg["drop_damaged"])
    _G["folds"] = family_folds(cfg, obs_toks)
    _G["d2"] = paradigm.d2_params(obs_toks)
    _G["rate"] = nulls._observed_variation_rate(fam)


def replicate(seed: int) -> tuple[float, ...]:
    rng = np.random.default_rng(seed)
    cfg, d2 = _G["cfg"], _G["d2"]
    if _G["null"] == "D":
        fam = nulls.null_d(_G["model"], rng, _G["family"], _G["rate"])
    else:
        scale = 2 if _G["null"] == "D2x2" else 1
        pre, suf = nulls.draw_affix_inventory(_G["model"], rng, scale * d2["k_prefix"], scale * d2["k_suffix"],
                                              d2["prefix_lengths"], d2["suffix_lengths"])
        fam = nulls.null_d2(_G["model"], rng, _G["family"], pre, suf, d2["mode_p"], _G["rate"])
    toks = paradigm.family_tokens(fam, _G["index"], drop_slots=cfg["drop_slots"], drop_damaged=cfg["drop_damaged"])
    return vector(paradigm.score(toks, _G["invs"], _G["folds"], strict=cfg["strict"]))


def run_null(cfg: dict, null: str, B: int, seed: int, workers: int) -> np.ndarray:
    setup(cfg, null)
    seeds = [seed * 1_000_003 + i for i in range(B)]
    if workers > 1:
        with mp.get_context("fork").Pool(workers) as pool:
            vecs = pool.map(replicate, seeds, chunksize=max(1, B // (workers * 8)))
    else:
        vecs = [replicate(s) for s in seeds]
    return np.array(vecs, dtype=float)


# ---------------------------------------------------------------------------
# observed family and controls
# ---------------------------------------------------------------------------

def run_observed(cfg: dict) -> dict:
    invs = inventories(cfg)
    fam = nulls.observed_family()
    idx = paradigm.family_slot_index()
    toks = paradigm.family_tokens(fam, idx, drop_slots=cfg["drop_slots"], drop_damaged=cfg["drop_damaged"])
    fres = paradigm.score(toks, invs, family_folds(cfg, toks), strict=cfg["strict"], detail=True)
    windows = []
    for line in paths.CONTROLS.joinpath("controls_b.jsonl").read_text().splitlines():
        w = json.loads(line)
        if "_meta" in w:
            continue
        r = paradigm.score(paradigm.window_tokens(w), invs, strict=cfg["strict"])
        windows.append({"id": w["id"], "class": w["class"], "language": w["language"],
                        "mean_signs": w["mean_signs"], "n_pairs": w["n_pairs"],
                        **dict(zip(STATS, vector(r))), "scorable": r["scorable"], "charge": r["charge"]})
    return {"family": {**dict(zip(STATS, vector(fres))), "scorable": fres["scorable"],
                       "folds_scored": fres["folds_scored"], "charge": fres["charge"], "folds": fres["folds"],
                       "d2_params": paradigm.d2_params(toks)},
            "controls": windows}


# ---------------------------------------------------------------------------
# gate (§9) and posterior (§10)
# ---------------------------------------------------------------------------

SEMITIC = ("H1_semitic_prayer", "H3_semitic_nonprayer")


def _ok(x) -> bool:
    return x is not None and not (isinstance(x, float) and math.isnan(x))


def gate(obs: dict, nullv: dict[str, np.ndarray]) -> dict:
    fam, wins = obs["family"], obs["controls"]
    col = {s: i for i, s in enumerate(STATS)}
    out: dict = {}

    d = nullv["D"][:, col["A_free"]]
    p95 = float(np.nanpercentile(d, 95))
    out["G1"] = {"A_free_family": fam["A_free"], "D_p95": p95, "D_mean": float(np.nanmean(d)),
                 **{k: v for k, v in stats.mc_p(fam["A_free"], d[~np.isnan(d)]).items() if k in ("r", "p", "p_ci95")},
                 "pass": bool(fam["A_free"] > p95)}

    usable = [w for w in wins if _ok(w["delta"])]
    pos = [w for w in usable if w["class"] in SEMITIC]
    neg = [w for w in usable if w["class"] not in SEMITIC]
    g2 = {"windows_scored": len(usable), "windows_unscorable": len(wins) - len(usable),
          "n_semitic": len(pos), "n_other": len(neg)}
    for stat in ("delta", "A_cs"):
        pv, nv = np.array([w[stat] for w in pos]), np.array([w[stat] for w in neg])
        pl, nl = np.array([w["mean_signs"] for w in pos]), np.array([w["mean_signs"] for w in neg])
        a, npairs = stats.auc_length_matched(pv, nv, pl, nl, BAND)
        lo, hi = stats.bootstrap_auc_length_matched(pv, nv, pl, nl, BAND)
        g2[f"auc_lm_{stat}"] = {"auc": a, "ci95": [lo, hi], "pairs": npairs, "auc_unmatched": stats.auc(pv, nv)}
    h1 = [w for w in usable if w["class"] == "H1_semitic_prayer"]
    lb_over = []
    for w in usable:
        if w["class"] != "NEG_linear_b":
            continue
        band = [x["delta"] for x in h1 if abs(x["mean_signs"] - w["mean_signs"]) <= BAND + 1e-12]
        if band and w["delta"] > float(np.median(band)):
            lb_over.append({"id": w["id"], "delta": w["delta"], "h1_band_median": float(np.median(band))})
    g2["linear_b_above_h1_band_median"] = lb_over
    g2["pass"] = bool(g2["auc_lm_delta"]["auc"] >= 0.85 and g2["auc_lm_delta"]["ci95"][0] > 0.50
                      and g2["auc_lm_A_cs"]["auc"] >= 0.75 and not lb_over)
    out["G2"] = g2

    d2 = nullv["D2"][:, col["delta"]]
    h1_acs = [w["A_cs"] for w in h1]
    rivals = {r: fam[f"A_{r}"] for r in paradigm.RIVALS}
    out["G3"] = {"delta_family": fam["delta"], "D2_delta_p95": float(np.nanpercentile(d2, 95)),
                 **{k: v for k, v in stats.mc_p(fam["delta"], d2[~np.isnan(d2)]).items() if k in ("r", "p", "p_ci95")},
                 "A_cs_family": fam["A_cs"], "H1_A_cs_median": float(np.median(h1_acs)) if h1_acs else None,
                 "A_rivals_family": rivals,
                 "delta_above_D2_p95": bool(fam["delta"] > np.nanpercentile(d2, 95)),
                 "A_cs_at_least_H1_median": bool(h1_acs and fam["A_cs"] >= np.median(h1_acs)),
                 "A_cs_above_every_rival": bool(all(fam["A_cs"] > v for v in rivals.values()))}
    if "D2x2" in nullv:
        d22 = nullv["D2x2"][:, col["delta"]]
        out["G3"]["D2x2"] = {k: v for k, v in stats.mc_p(fam["delta"], d22[~np.isnan(d22)]).items() if k in ("r", "p")}

    # class summaries (reported whatever the gates say)
    summ = {}
    for cls in sorted({w["class"] for w in wins}):
        ws = [w for w in usable if w["class"] == cls]
        summ[cls] = {s: (float(np.mean([w[s] for w in ws])) if ws else None) for s in STATS}
        summ[cls]["n"] = len(ws)
    out["class_means"] = summ

    lik = {}
    if out["G1"]["pass"] and out["G2"]["pass"]:
        x = fam["delta"]
        groups = {"H1": [w["delta"] for w in usable if w["class"] == "H1_semitic_prayer"],
                  "H3": [w["delta"] for w in usable if w["class"] == "H3_semitic_nonprayer"],
                  "luwian": [w["delta"] for w in usable if w["language"] == "luwian"],
                  "egyptian": [w["delta"] for w in usable if w["language"] == "egyptian"],
                  "H_ISO": list(d2[~np.isnan(d2)])}
        for bw in (0.5, 1.0, 1.5):
            L = {k: stats.likelihood_with_bound(np.array(v), x, bw) for k, v in groups.items() if v}
            alts = {k: L[k]["pdf"] for k in L if k != "H1"}
            lik[f"bw{bw}"] = {"likelihoods": L,
                              "grid": stats.posterior_grid(L["H1"]["pdf"], alts, SCHEMES, PRIORS)}
        lik["note"] = "hurrian has no control windows: its weight is renormalized over the supplied alternatives"
    out["posterior"] = lik or None
    return out


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def write_run(name: str, result: dict, argv_vars: dict, arrays: dict[str, np.ndarray] | None = None) -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = paths.RUNS / f"{ts}-paradigm-{name}"
    run_dir.mkdir(parents=True, exist_ok=False)
    for k, a in (arrays or {}).items():
        np.save(run_dir / f"{k}.npy", a)
    (run_dir / "results.json").write_text(json.dumps(result, indent=1, ensure_ascii=False, default=str))
    (run_dir / "manifest.json").write_text(json.dumps(
        {"argv": sys.argv, "ts": ts, "sha256sums": paths.sha256(paths.SHA_FILE) if paths.SHA_FILE.exists() else None},
        indent=1))
    entries = json.loads(paths.MANIFEST.read_text()) if paths.MANIFEST.exists() else []
    entries.append({"ts": ts, "script": "run_paradigm.py", "args": argv_vars,
                    "out": str(run_dir.relative_to(paths.PKG)),
                    "results_sha256": paths.sha256(run_dir / "results.json")})
    paths.MANIFEST.write_text(json.dumps(entries, indent=1, default=str))
    return run_dir


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["null", "observed", "gate"])
    ap.add_argument("--null", choices=list(NULL_SEED))
    ap.add_argument("--B", type=int)
    ap.add_argument("--seed", type=int)
    ap.add_argument("--debug", action="store_true", help="allow --B/--seed for nulls; never unblinds observed")
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--cons", action="store_true")
    ap.add_argument("--ext", action="store_true")
    ap.add_argument("--with-sabaic", action="store_true")
    ap.add_argument("--folds", choices=["lso", "random"], default="lso")
    ap.add_argument("--drop-slot", action="append")
    ap.add_argument("--drop-damaged", action="store_true")
    ap.add_argument("--observed-run", help="gate: runs/<dir> of the observed run")
    ap.add_argument("--null-runs", nargs="+", help="gate: runs/<dir> of the D, D2 (and D2x2) runs")
    args = ap.parse_args()
    cfg = config_from_args(args)
    tag = config_tag(cfg)

    if args.cmd == "null":
        if not args.null:
            ap.error("--null is required")
        if not args.debug and not frozen():
            print("PROTOCOL.md carries no option B freeze record; production null runs refuse to start (use --debug)")
            return 2
        B = (args.B or 1000) if args.debug else NULL_B[args.null]
        seed = args.seed if (args.debug and args.seed is not None) else NULL_SEED[args.null]
        t0 = time.time()
        arr = run_null(cfg, args.null, B, seed, args.workers)
        wall = time.time() - t0
        summ = {s: {"mean": float(np.nanmean(arr[:, j])), "sd": float(np.nanstd(arr[:, j], ddof=1)),
                    "p95": float(np.nanpercentile(arr[:, j], 95)), "nan": int(np.isnan(arr[:, j]).sum())}
                for j, s in enumerate(STATS)}
        res = {"null": args.null, "B": B, "seed": seed, "config": cfg, "d2_params": _G["d2"],
               "variation_rate": _G["rate"], "summary": summ, "wall_s": wall, "debug": args.debug}
        d = write_run(f"null-{args.null}-{tag}-B{B}-s{seed}" + ("-debug" if args.debug else ""), res, vars(args),
                      {"null_vectors": arr})
        print(f"{args.null} {tag} B={B} seed={seed} wall={wall:.1f}s -> {d.name}")
        for s, v in summ.items():
            print(f"  {s:<12} mean={v['mean']:.3f} sd={v['sd']:.3f} p95={v['p95']:.3f} nan={v['nan']}")
        return 0

    if args.cmd == "observed":
        if not frozen():
            print("PROTOCOL.md carries no option B freeze record; the observed run stays blind until B4")
            return 2
        t0 = time.time()
        res = run_observed(cfg)
        res.update({"config": cfg, "wall_s": time.time() - t0})
        d = write_run(f"observed-{tag}", res, vars(args))
        f = res["family"]
        print(f"observed {tag} -> {d.name}")
        print("  family  " + "  ".join(f"{s}={f[s]:.3f}" for s in STATS) + f"  scorable={f['scorable']}")
        return 0

    if not (args.observed_run and args.null_runs):
        ap.error("gate needs --observed-run and --null-runs")
    obs = json.loads((paths.PKG / args.observed_run / "results.json").read_text())
    nullv = {}
    for r in args.null_runs:
        meta = json.loads((paths.PKG / r / "results.json").read_text())
        nullv[meta["null"]] = np.load(paths.PKG / r / "null_vectors.npy")
    res = gate(obs, nullv)
    res.update({"observed_run": args.observed_run, "null_runs": args.null_runs})
    d = write_run(f"gate-{tag}", res, vars(args))
    print(json.dumps({k: res[k] for k in ("G1", "G2", "G3")}, indent=1, default=str))
    print(f"-> {d.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
