#!/usr/bin/env python3
"""Query, list, compare, and export saved Ventris Engine runs.

Usage:
    ventris_runs.py list [--type decode|propagation] [--limit N]
    ventris_runs.py show <run_id> [--summary] [--json]
    ventris_runs.py diff <run_id_a> <run_id_b> [--json]
    ventris_runs.py export <run_id> [--out PATH]
    ventris_runs.py latest [--type decode|propagation] [--json]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = "tools.linear_a"

from ..core.run_saver import RUNS_DIR, diff_runs, list_runs, load_run


def cmd_list(args):
    runs = list_runs(run_type=args.type, limit=args.limit)
    if not runs:
        print("No saved runs found.")
        return

    if args.json:
        print(json.dumps(runs, indent=2, ensure_ascii=False))
        return

    print(f"{'RUN ID':<35} {'TYPE':<14} {'TIMESTAMP':<22} {'LABEL':<20} {'CANDIDATES'}")
    print("─" * 110)
    for r in runs:
        counts = r.get("counts", {})
        nc = counts.get("new_candidates", counts.get("total_results", "?"))
        label = r.get("label") or ""
        ts = r["timestamp"][:19].replace("T", " ")
        print(f"{r['run_id']:<35} {r['run_type']:<14} {ts:<22} {label:<20} {nc}")


def cmd_show(args):
    try:
        prov, output = load_run(args.run_id)
    except FileNotFoundError:
        print(f"Run '{args.run_id}' not found in {RUNS_DIR}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        if args.summary:
            print(json.dumps(prov, indent=2, ensure_ascii=False))
        else:
            print(json.dumps({"provenance": prov, "output": output}, indent=2, ensure_ascii=False, default=str))
        return

    print(f"Run: {prov['run_id']}")
    print(f"Type: {prov['run_type']}")
    print(f"Time: {prov['timestamp']}")
    if prov.get("label"):
        print(f"Label: {prov['label']}")
    print(f"Corpus hash: {prov['corpus_hash']}")
    print(f"Lexicon hash: {prov['lexicon_hash']}")
    print(f"Git: {prov['git']['commit']} {'(dirty)' if prov['git'].get('dirty') else '(clean)'}")
    print()

    print("Parameters:")
    for k, v in prov["parameters"].items():
        print(f"  {k}: {v}")
    print()

    print("Results:")
    for k, v in prov["counts"].items():
        print(f"  {k}: {v}")

    if not args.summary:
        print()
        results = output.get("results", output.get("cross_validated", []))
        new = [r for r in results if r.get("status") != "known"]
        if new:
            print("Top 20 new candidates:")
            print(f"  {'WORD':<25} {'SKELETON':<10} {'BEST ROOT':<12} {'MEANING':<30} {'LANG':<10} {'SCORE'}")
            print("  " + "─" * 95)
            for r in new[:20]:
                word = r.get("word", "?")
                skel = r.get("skeleton", "?")
                root = r.get("best_root", "?")
                meaning = (r.get("best_meaning") or "?")[:28]
                lang = (r.get("language", {}) or {}).get("decision", "?")
                score = r.get("score", 0)
                print(f"  {word:<25} {skel:<10} {root:<12} {meaning:<30} {lang:<10} {score:.3f}")


def cmd_diff(args):
    try:
        result = diff_runs(args.run_id_a, args.run_id_b)
    except FileNotFoundError as e:
        print(f"Run not found: {e}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    print(f"Comparing {args.run_id_a} vs {args.run_id_b}")
    print(f"  A candidates: {result['a_count']}")
    print(f"  B candidates: {result['b_count']}")
    print(f"  Shared: {result['shared_count']}")
    print(f"  Only in A: {len(result['only_in_a'])}")
    print(f"  Only in B: {len(result['only_in_b'])}")

    if result["only_in_a"]:
        print(f"\nOnly in A ({len(result['only_in_a'])}):")
        for w in result["only_in_a"][:30]:
            print(f"  - {w}")
        if len(result["only_in_a"]) > 30:
            print(f"  ... and {len(result['only_in_a']) - 30} more")

    if result["only_in_b"]:
        print(f"\nOnly in B ({len(result['only_in_b'])}):")
        for w in result["only_in_b"][:30]:
            print(f"  + {w}")
        if len(result["only_in_b"]) > 30:
            print(f"  ... and {len(result['only_in_b']) - 30} more")


def cmd_export(args):
    try:
        _, output = load_run(args.run_id)
    except FileNotFoundError:
        print(f"Run '{args.run_id}' not found", file=sys.stderr)
        sys.exit(1)

    out_path = Path(args.out) if args.out else Path(f"{args.run_id}-export.json")
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    print(f"Exported to {out_path}")


def cmd_latest(args):
    runs = list_runs(run_type=args.type, limit=1)
    if not runs:
        print("No saved runs found.", file=sys.stderr)
        sys.exit(1)

    run_id = runs[0]["run_id"]
    prov, output = load_run(run_id)

    if args.json:
        print(json.dumps({"provenance": prov, "output": output}, indent=2, ensure_ascii=False, default=str))
    else:
        print(f"Latest run: {run_id}")
        print(f"Type: {prov['run_type']}, Time: {prov['timestamp'][:19]}")
        counts = prov.get("counts", {})
        for k, v in counts.items():
            print(f"  {k}: {v}")


def main():
    parser = argparse.ArgumentParser(description="Query saved Ventris Engine runs")
    sub = parser.add_subparsers(dest="command")

    p_list = sub.add_parser("list", help="List saved runs")
    p_list.add_argument("--type", choices=["decode", "propagation"], default=None)
    p_list.add_argument("--limit", type=int, default=20)
    p_list.add_argument("--json", action="store_true")

    p_show = sub.add_parser("show", help="Show details of a saved run")
    p_show.add_argument("run_id")
    p_show.add_argument("--summary", action="store_true", help="Provenance only, no results")
    p_show.add_argument("--json", action="store_true")

    p_diff = sub.add_parser("diff", help="Compare two runs")
    p_diff.add_argument("run_id_a")
    p_diff.add_argument("run_id_b")
    p_diff.add_argument("--json", action="store_true")

    p_export = sub.add_parser("export", help="Export run output to a file")
    p_export.add_argument("run_id")
    p_export.add_argument("--out", type=str, default=None)

    p_latest = sub.add_parser("latest", help="Show the most recent run")
    p_latest.add_argument("--type", choices=["decode", "propagation"], default=None)
    p_latest.add_argument("--json", action="store_true")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    {"list": cmd_list, "show": cmd_show, "diff": cmd_diff, "export": cmd_export, "latest": cmd_latest}[args.command](args)


if __name__ == "__main__":
    main()
