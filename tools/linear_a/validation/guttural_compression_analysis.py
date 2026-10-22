#!/usr/bin/env python3
"""Guttural Compression Analysis.

Quantifies how guttural transparency compresses Z-scores per language.
Reads paired saved null-model runs, one with guttural transparency and one
without, and computes compression ratios to determine whether the Luwian > NWS
finding is partially a measurement artifact of the guttural mechanism.

Make the four runs with null_model_audit.py, each with --save, with and without
--no-gutturals, for --language nws and --language luwian; ventris_runs.py list
names them.

Usage:
    uv run tools/linear_a/validation/guttural_compression_analysis.py \\
        --nws ON_RUN OFF_RUN --luwian ON_RUN OFF_RUN [--json]
"""

import argparse
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    __package__ = "tools.linear_a.validation"

from ...core.run_saver import RUNS_DIR
from ...paths import NotInCheckout, require

THRESHOLDS = ["0.3", "0.5", "0.7", "1.0"]


def load_run(run_id: str) -> dict:
    path = require(RUNS_DIR / run_id / "output.json", f"saved run {run_id}")
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    try:
        _run()
    except NotInCheckout as e:
        print(f"stopped: {e}", file=sys.stderr)
        return 2
    return 0


def _run():
    parser = argparse.ArgumentParser(description="Guttural Compression Analysis")
    parser.add_argument("--nws", nargs=2, required=True, metavar=("ON_RUN", "OFF_RUN"),
                        help="NWS null-model runs with and without guttural transparency")
    parser.add_argument("--luwian", nargs=2, required=True, metavar=("ON_RUN", "OFF_RUN"),
                        help="Luwian null-model runs with and without guttural transparency")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()
    paired_runs = {"nws": args.nws, "luwian": args.luwian}

    results = {}
    for lang, (run_on, run_off) in paired_runs.items():
        on_data = load_run(run_on)
        off_data = load_run(run_off)

        guttural_pct = on_data.get("guttural_pct", 0)

        compressions = {}
        for t in THRESHOLDS:
            z_on = on_data["thresholds"][t]["z_score"]
            z_off = off_data["thresholds"][t]["z_score"]

            ratio = (z_off - z_on) / abs(z_off) if z_off != 0 else 0.0

            compressions[t] = {
                "z_gutt_on": z_on,
                "z_gutt_off": z_off,
                "delta": round(z_off - z_on, 3),
                "compression_ratio": round(ratio, 3),
            }

        results[lang] = {
            "guttural_pct": guttural_pct,
            "iterations": on_data["iterations"],
            "thresholds": compressions,
        }

    if args.json:
        print(json.dumps(results, indent=2))
        return

    print("Guttural Compression Analysis")
    print("=" * 75)
    print()
    print("Compression ratio = (Z_off - Z_on) / |Z_off|")
    print("Positive = gutturals compress (lower) the Z-score")
    print("Negative = gutturals inflate the Z-score")
    print()

    for lang, data in results.items():
        print(f"{lang.upper()} (guttural density: {data['guttural_pct']:.1f}%)")
        print(f"  {'Threshold':<12} {'Z (gutt ON)':>12} {'Z (gutt OFF)':>13} {'Delta':>8} {'Compression':>13}")
        print(f"  {'-'*60}")
        for t in THRESHOLDS:
            c = data["thresholds"][t]
            print(f"  ≤{t:<10} {c['z_gutt_on']:>12.2f} {c['z_gutt_off']:>13.2f} "
                  f"{c['delta']:>+8.3f} {c['compression_ratio']:>12.1%}")
        print()

    nws = results.get("nws", {}).get("thresholds", {})
    luw = results.get("luwian", {}).get("thresholds", {})
    print("Cross-Language Compression Comparison:")
    print(f"  {'Threshold':<12} {'NWS Compress':>14} {'Luwian Compress':>16} {'Ratio NWS/Luw':>15}")
    print(f"  {'-'*60}")
    for t in THRESHOLDS:
        nc = nws.get(t, {}).get("compression_ratio", 0)
        lc = luw.get(t, {}).get("compression_ratio", 0)
        ratio_str = f"{nc/lc:.1f}×" if lc != 0 else "N/A"
        print(f"  ≤{t:<10} {nc:>13.1%} {lc:>15.1%} {ratio_str:>15}")

    print()
    nws_gp = results.get("nws", {}).get("guttural_pct", 0)
    luw_gp = results.get("luwian", {}).get("guttural_pct", 0)
    print(f"Guttural density: NWS={nws_gp:.1f}%, Luwian={luw_gp:.1f}% "
          f"(ratio: {nws_gp/luw_gp:.1f}×)" if luw_gp > 0 else "")
    print()
    print("If NWS compression is 3-4× Luwian's, the Luwian dominance finding")
    print("is partially a measurement artifact of guttural transparency.")


if __name__ == "__main__":
    sys.exit(main())
