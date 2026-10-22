#!/usr/bin/env python3
"""Guttural Inflation Audit.

Measures how much the guttural transparency mechanism (GUTTURAL_INSERT_COST=0.1)
inflates match quality across all lexicon entries. For each entry with a root,
computes weighted Levenshtein distance with and without guttural transparency,
then reports per-tier inflation rates.

Usage:
    uv run tools/linear_a/validation/guttural_audit.py [--json] [--save] [--threshold 0.5]
"""

import argparse
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    __package__ = "tools.linear_a.validation"

from ...core import run_saver
from ...core.phonetics import (
    GUTTURAL_PHONEMES,
    _tokenize_phonemes,
    weighted_levenshtein,
)
from ...core.skeleton import extract_skeleton
from ...paths import LINEAR_A_DATA, NotInCheckout, require


def load_lexicon() -> list[dict]:
    lex_path = require(LINEAR_A_DATA / "lexicon.json", "lexicon.json")
    data = json.loads(lex_path.read_text(encoding="utf-8"))
    return data["entries"]


def has_guttural(root_clean: str) -> bool:
    tokens = _tokenize_phonemes(root_clean)
    return any(t in GUTTURAL_PHONEMES for t in tokens)


def audit_entry(entry: dict, threshold: float) -> dict | None:
    word = entry.get("word", "")
    root = entry.get("root", "")
    if not root or not word:
        return None

    skeleton = extract_skeleton(word)
    if not skeleton:
        return None

    root_clean = root.replace("-", "")
    if not root_clean or len(root_clean) < 1:
        return None

    dist_with = weighted_levenshtein(skeleton, root_clean, guttural_transparent=True)
    dist_without = weighted_levenshtein(skeleton, root_clean, guttural_transparent=False)
    delta = dist_without - dist_with

    root_has_guttural = has_guttural(root_clean)

    critical = dist_with <= threshold and dist_without > threshold
    influenced = delta > 0.0

    return {
        "word": word,
        "reading": entry.get("reading", ""),
        "root": root,
        "skeleton": skeleton,
        "confidence": entry.get("confidence", "?"),
        "dist_with_guttural": round(dist_with, 3),
        "dist_without_guttural": round(dist_without, 3),
        "delta": round(delta, 3),
        "root_has_guttural": root_has_guttural,
        "guttural_critical": critical,
        "guttural_influenced": influenced,
    }


def run_audit(threshold: float = 0.5) -> dict:
    entries = load_lexicon()
    tiers = ["CONFIRMED", "PROBABLE", "CANDIDATE", "SPECULATIVE"]
    results_by_tier: dict[str, list[dict]] = {t: [] for t in tiers}
    skipped = 0

    for entry in entries:
        result = audit_entry(entry, threshold)
        if result is None:
            skipped += 1
            continue
        tier = result["confidence"]
        if tier in results_by_tier:
            results_by_tier[tier].append(result)

    summary = {}
    all_critical = []
    for tier in tiers:
        results = results_by_tier[tier]
        total = len(results)
        critical = [r for r in results if r["guttural_critical"]]
        influenced = [r for r in results if r["guttural_influenced"]]
        with_guttural_root = [r for r in results if r["root_has_guttural"]]

        avg_delta = (
            sum(r["delta"] for r in results) / total if total > 0 else 0.0
        )
        avg_delta_influenced = (
            sum(r["delta"] for r in influenced) / len(influenced)
            if influenced
            else 0.0
        )

        summary[tier] = {
            "total": total,
            "roots_with_gutturals": len(with_guttural_root),
            "guttural_influenced": len(influenced),
            "guttural_critical": len(critical),
            "pct_critical": round(len(critical) / total * 100, 1) if total else 0.0,
            "pct_influenced": round(len(influenced) / total * 100, 1) if total else 0.0,
            "avg_delta": round(avg_delta, 3),
            "avg_delta_influenced": round(avg_delta_influenced, 3),
        }
        all_critical.extend(critical)

    return {
        "threshold": threshold,
        "skipped_no_root": skipped,
        "summary": summary,
        "critical_entries": sorted(all_critical, key=lambda x: -x["delta"]),
        "all_results": {t: results_by_tier[t] for t in tiers},
    }


def print_report(audit: dict) -> None:
    threshold = audit["threshold"]
    summary = audit["summary"]
    critical = audit["critical_entries"]
    tiers = ["CONFIRMED", "PROBABLE", "CANDIDATE", "SPECULATIVE"]

    print(f"Guttural Inflation Audit (threshold={threshold})")
    print("=" * 60)
    print(f"Skipped (no root): {audit['skipped_no_root']}")
    print()

    print(f"{'Tier':<14} {'Total':>5} {'Gutt Root':>9} {'Influenced':>10} {'Critical':>8} {'%Crit':>6} {'AvgΔ':>6}")
    print("-" * 60)
    for tier in tiers:
        s = summary[tier]
        print(
            f"{tier:<14} {s['total']:>5} {s['roots_with_gutturals']:>9} "
            f"{s['guttural_influenced']:>10} {s['guttural_critical']:>8} "
            f"{s['pct_critical']:>5.1f}% {s['avg_delta']:>6.3f}"
        )
    print()

    total_all = sum(summary[t]["total"] for t in tiers)
    total_critical = sum(summary[t]["guttural_critical"] for t in tiers)
    total_influenced = sum(summary[t]["guttural_influenced"] for t in tiers)
    print(f"Overall: {total_critical}/{total_all} critical ({total_critical/total_all*100:.1f}%), "
          f"{total_influenced}/{total_all} influenced ({total_influenced/total_all*100:.1f}%)")
    print()

    if critical:
        print("Entries that ONLY match below threshold because of guttural transparency:")
        print(f"{'Word':<20} {'Skeleton':<8} {'Root':<12} {'Conf':<12} {'d(with)':>8} {'d(w/o)':>8} {'Δ':>6}")
        print("-" * 76)
        for r in critical:
            print(
                f"{r['word']:<20} {r['skeleton']:<8} {r['root']:<12} {r['confidence']:<12} "
                f"{r['dist_with_guttural']:>8.3f} {r['dist_without_guttural']:>8.3f} {r['delta']:>6.3f}"
            )
    else:
        print("No entries are guttural-critical at this threshold.")

    print()

    # Verdict
    candidate_pct = summary["CANDIDATE"]["pct_critical"]
    if candidate_pct < 10:
        verdict = "MINIMAL — guttural transparency does not meaningfully inflate CANDIDATE matches"
    elif candidate_pct < 20:
        verdict = "LOW — guttural transparency has modest effect, consider flagging dependent entries"
    elif candidate_pct < 40:
        verdict = "MODERATE — recalibrate GUTTURAL_INSERT_COST or add 'guttural_dependent' flags"
    else:
        verdict = "HIGH — recalibrate GUTTURAL_INSERT_COST from 0.1 to 0.3+, reassess all dependent CANDIDATEs"

    print(f"Verdict (CANDIDATE tier): {verdict}")
    print(f"  CANDIDATE critical rate: {candidate_pct:.1f}%")

    confirmed_pct = summary["CONFIRMED"]["pct_critical"]
    if confirmed_pct > 0:
        print(f"  ⚠ {summary['CONFIRMED']['guttural_critical']} CONFIRMED entries are also guttural-critical")
        print("    (these should have ideographic confirmation independent of distance)")


def save_run(audit: dict) -> Path:
    output = {
        "summary": audit["summary"],
        "critical_entries": audit["critical_entries"],
        "skipped_no_root": audit["skipped_no_root"],
    }
    return run_saver.save_run("guttural-audit", {"threshold": audit["threshold"]}, output)


def main() -> int:
    try:
        _run()
    except NotInCheckout as e:
        print(f"stopped: {e}", file=sys.stderr)
        return 2
    return 0


def _run():
    parser = argparse.ArgumentParser(description="Guttural Inflation Audit")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--save", action="store_true", help="Save the run to the run cache")
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.5,
        help="Distance threshold for 'critical' classification (default: 0.5)",
    )
    args = parser.parse_args()

    audit = run_audit(threshold=args.threshold)

    if args.json:
        output = {
            "summary": audit["summary"],
            "critical_entries": audit["critical_entries"],
            "skipped_no_root": audit["skipped_no_root"],
            "threshold": audit["threshold"],
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        print_report(audit)

    if args.save:
        run_dir = save_run(audit)
        print(f"\nRun saved to: {run_dir}", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
