#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Calibrate logogram analyzer thresholds from Linear B controls.

Reads a labelled feature file (default `data/linear-a/lb_calibration_features.json`,
not shipped) and writes ROC thresholds and weights to --output (default: the user
cache, `CACHE/linear-a/lb_calibration_thresholds.json`). `logogram_analyzer.py
--calibrated` reads `data/linear-a/lb_calibration_thresholds.json`; pass that path
as --output to install a run. An existing output is copied into BACKUPS first.

    uv run tools/linear_a/analysis/lb_roc_calibration.py [--input FILE] [--output FILE] [--verbose]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    __package__ = "tools.linear_a.analysis"

from ...paths import CACHE, LINEAR_A_DATA, REPO, NotInCheckout, require
from ..ingest.ingest_oracc_amarna import backup_existing

DEFAULT_INPUT = LINEAR_A_DATA / "lb_calibration_features.json"
DEFAULT_OUTPUT = CACHE / "linear-a" / "lb_calibration_thresholds.json"

FEATURE_DIRECTIONS = {
    "numeric_follower_rate": "gte",
    "window_class_entropy": "lte",
    "standalone_count": "gte",
    "site_concentration": "gte",
    "std_position": "lte",
    "fraction_follower_rate": "gte",
}

NEUTRAL_FEATURES = {"mean_position"}
MIN_DISCRIMINATING_AUC = 0.55
FPR_FLOOR = 0.01


def resolve_path(path: Path) -> Path:
    if path.is_absolute():
        return path
    return REPO / path


def load_payload(path: Path) -> dict:
    try:
        payload = json.loads(require(path, path.name).read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"input file is not valid JSON: {path}: {exc}") from exc

    if not isinstance(payload, dict):
        raise SystemExit("input JSON must be an object")
    if not isinstance(payload.get("features"), list):
        raise SystemExit("input JSON must contain a features list")
    return payload


def label_counts(rows: list[dict]) -> tuple[int, int]:
    positives = sum(1 for row in rows if row.get("label") == 1)
    negatives = sum(1 for row in rows if row.get("label") == 0)
    if positives == 0 or negatives == 0:
        raise SystemExit(
            f"calibration requires both labels; found positives={positives}, negatives={negatives}"
        )
    return positives, negatives


def extract_feature_values(rows: list[dict], name: str) -> list[tuple[float, int]]:
    values = []
    for index, row in enumerate(rows, start=1):
        label = row.get("label")
        if label not in (0, 1):
            raise SystemExit(f"row {index} has invalid label: {label!r}")
        try:
            value = float(row[name])
        except KeyError as exc:
            raise SystemExit(f"row {index} is missing feature {name!r}") from exc
        except (TypeError, ValueError) as exc:
            raise SystemExit(f"row {index} has non-numeric {name!r}: {row.get(name)!r}") from exc
        if math.isnan(value) or math.isinf(value):
            raise SystemExit(f"row {index} has non-finite {name!r}: {value!r}")
        values.append((value, int(label)))
    return values


def grouped_counts(values: list[tuple[float, int]]) -> dict[float, list[int]]:
    groups: dict[float, list[int]] = defaultdict(lambda: [0, 0])
    for value, label in values:
        groups[value][label] += 1
    return groups


def sweep_thresholds(
    values: list[tuple[float, int]],
    direction: str,
    positives: int,
    negatives: int,
) -> list[dict]:
    groups = grouped_counts(values)
    ordered_values = sorted(groups, reverse=(direction == "gte"))

    tp = 0
    fp = 0
    records = []
    for threshold in ordered_values:
        neg_count, pos_count = groups[threshold]
        tp += pos_count
        fp += neg_count
        tpr = tp / positives
        fpr = fp / negatives
        records.append(
            {
                "threshold": threshold,
                "tpr": tpr,
                "fpr": fpr,
                "youden_j": tpr - fpr,
                "tp": tp,
                "fp": fp,
                "fn": positives - tp,
                "tn": negatives - fp,
            }
        )
    return records


def auc_from_records(records: list[dict]) -> float:
    points = [(0.0, 0.0)]
    points.extend((record["fpr"], record["tpr"]) for record in records)
    points.append((1.0, 1.0))
    points.sort(key=lambda point: (point[0], point[1]))

    auc = 0.0
    previous_fpr, previous_tpr = points[0]
    for fpr, tpr in points[1:]:
        auc += (fpr - previous_fpr) * (tpr + previous_tpr) / 2
        previous_fpr, previous_tpr = fpr, tpr
    return auc


def optimal_record(records: list[dict], direction: str) -> dict:
    sign = -1 if direction == "gte" else 1
    return max(
        records,
        key=lambda record: (
            record["youden_j"],
            record["tpr"],
            -record["fpr"],
            sign * record["threshold"],
        ),
    )


def likelihood_weight(tpr: float, fpr: float, auc: float) -> float:
    if auc < MIN_DISCRIMINATING_AUC or tpr <= 0:
        return 0.0
    return max(0.0, math.log2(tpr / max(fpr, FPR_FLOOR)))


def calibrate_feature(
    values: list[tuple[float, int]],
    name: str,
    direction: str,
    positives: int,
    negatives: int,
) -> tuple[dict, list[dict]]:
    records = sweep_thresholds(values, direction, positives, negatives)
    auc = auc_from_records(records)
    best = optimal_record(records, direction)
    weight = likelihood_weight(best["tpr"], best["fpr"], auc)

    result = {
        "threshold": best["threshold"],
        "direction": direction,
        "tpr": best["tpr"],
        "fpr": best["fpr"],
        "auc": auc,
        "youden_j": best["youden_j"],
        "weight": weight,
    }
    return result, records


def print_feature_summary(name: str, result: dict) -> None:
    print(
        f"{name}: AUC={result['auc']:.4f} "
        f"threshold={result['threshold']:.6g} "
        f"direction={result['direction']} "
        f"TPR={result['tpr']:.4f} FPR={result['fpr']:.4f} "
        f"J={result['youden_j']:.4f} weight={result['weight']:.4f}",
        file=sys.stderr,
    )


def print_roc_table(name: str, records: list[dict]) -> None:
    print(f"\nROC sweep: {name}", file=sys.stderr)
    print(
        f"{'threshold':>12} {'tpr':>8} {'fpr':>8} {'youden_j':>9} "
        f"{'tp':>6} {'fp':>6} {'fn':>6} {'tn':>6}",
        file=sys.stderr,
    )
    for record in records:
        print(
            f"{record['threshold']:>12.6g} {record['tpr']:>8.4f} "
            f"{record['fpr']:>8.4f} {record['youden_j']:>9.4f} "
            f"{record['tp']:>6} {record['fp']:>6} "
            f"{record['fn']:>6} {record['tn']:>6}",
            file=sys.stderr,
        )


def candidate_features(payload: dict) -> list[str]:
    metadata_features = payload.get("metadata", {}).get("features")
    if isinstance(metadata_features, list):
        return [str(name) for name in metadata_features]
    return list(FEATURE_DIRECTIONS) + sorted(NEUTRAL_FEATURES)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Calibrate ROC thresholds and log-likelihood weights for Linear B logogram features."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help="Calibration feature JSON (default: data/linear-a/lb_calibration_features.json)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Output threshold JSON (default: CACHE/linear-a/lb_calibration_thresholds.json)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print per-feature ROC tables to stderr.",
    )
    return parser.parse_args()


def main() -> int:
    try:
        _run()
    except NotInCheckout as e:
        print(f"stopped: {e}", file=sys.stderr)
        return 2
    return 0


def _run() -> None:
    args = parse_args()
    input_path = resolve_path(args.input)
    output_path = resolve_path(args.output)

    payload = load_payload(input_path)
    rows = payload["features"]
    positives, negatives = label_counts(rows)

    feature_results = {}
    skipped = {}
    for name in candidate_features(payload):
        if name in NEUTRAL_FEATURES:
            skipped[name] = "neutral positional feature"
            print(f"{name}: skipped ({skipped[name]})", file=sys.stderr)
            continue
        direction = FEATURE_DIRECTIONS.get(name)
        if direction is None:
            skipped[name] = "no configured threshold direction"
            print(f"{name}: skipped ({skipped[name]})", file=sys.stderr)
            continue

        values = extract_feature_values(rows, name)
        unique_values = {value for value, _label in values}
        if len(unique_values) < 2:
            skipped[name] = f"all values identical ({unique_values.pop()!r})"
            print(f"{name}: skipped ({skipped[name]})", file=sys.stderr)
            continue

        result, records = calibrate_feature(values, name, direction, positives, negatives)
        feature_results[name] = result
        print_feature_summary(name, result)
        if args.verbose:
            print_roc_table(name, records)

    output = {
        "metadata": {
            "source": str(input_path.relative_to(REPO) if input_path.is_relative_to(REPO) else input_path),
            "generated": datetime.now(UTC).isoformat(),
            "total_positives": positives,
            "total_negatives": negatives,
            "skipped_features": skipped,
        },
        "features": feature_results,
    }

    backup_existing(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote: {output_path}", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
