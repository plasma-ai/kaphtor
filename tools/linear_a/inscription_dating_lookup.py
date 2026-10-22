#!/usr/bin/env python3
"""Query the Linear A inscription dating metadata overlay."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = "tools.linear_a"

from ..paths import LINEAR_A_DATA, NotInCheckout, require

DATING_PATH = LINEAR_A_DATA / "inscription_dating_metadata.json"
CORPUS_PATH = LINEAR_A_DATA / "corpus.json"


def load_json(path: Path) -> Any:
    with require(path, path.name).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def normalize_form(value: str) -> str:
    return (
        value.strip()
        .upper()
        .replace("₂", "2")
        .replace("₃", "3")
        .replace("₄", "4")
        .replace("_", "-")
    )


def load_records() -> dict[str, dict[str, Any]]:
    data = load_json(DATING_PATH)
    if isinstance(data, list):
        return {row["inscription_id"]: row for row in data}
    return data


def load_corpus() -> dict[str, dict[str, Any]]:
    data = load_json(CORPUS_PATH)
    if isinstance(data, list):
        return {row.get("name") or row.get("id"): row for row in data}
    return data


def matches_form(corpus_row: dict[str, Any], target: str) -> bool:
    target_norm = normalize_form(target)
    fields = [
        corpus_row.get("transliteratedWords", []),
        corpus_row.get("translatedWords", []),
    ]
    for field in fields:
        if isinstance(field, list):
            for token in field:
                if normalize_form(str(token)) == target_norm:
                    return True
        elif normalize_form(str(field)) == target_norm:
            return True
    return False


def filter_records(args: argparse.Namespace) -> list[dict[str, Any]]:
    records = load_records()
    corpus = load_corpus() if args.chronology_form else {}

    if args.inscription:
        row = records.get(args.inscription)
        return [row] if row else []

    rows = list(records.values())
    if args.period:
        rows = [row for row in rows if row.get("best_period_code") == args.period]
    if args.certainty:
        rows = [row for row in rows if row.get("best_date_certainty") == args.certainty]
    if args.status:
        rows = [row for row in rows if row.get("dating_status") == args.status]
    if args.basis:
        rows = [row for row in rows if row.get("dating_basis") == args.basis]
    if args.blank_structured_recovered:
        rows = [
            row
            for row in rows
            if not row.get("structured_context_code")
            and row.get("dating_status") != "NO_DATING_EVIDENCE_FOUND"
        ]
    if args.chronology_form:
        rows = [
            row
            for row in rows
            if matches_form(corpus.get(row.get("inscription_id"), {}), args.chronology_form)
        ]

    rows.sort(
        key=lambda row: (
            str(row.get("best_period_code") or "ZZZ"),
            str(row.get("inscription_id") or ""),
        )
    )
    return rows[: args.limit] if args.limit else rows


def emit_markdown(rows: list[dict[str, Any]]) -> None:
    print("| inscription | site | support | period | certainty | status | basis | findspot |")
    print("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for row in rows:
        print(
            "| {inscription_id} | {site} | {support} | {period} | {certainty} | {status} | {basis} | {findspot} |".format(
                inscription_id=row.get("inscription_id", ""),
                site=row.get("site", ""),
                support=row.get("support", ""),
                period=row.get("best_period_code", ""),
                certainty=row.get("best_date_certainty", ""),
                status=row.get("dating_status", ""),
                basis=row.get("dating_basis", ""),
                findspot=(row.get("best_findspot") or "").replace("|", "/"),
            )
        )


def main() -> int:
    """Exit 2 with the file's name when a data file is not in the checkout."""
    try:
        return _run()
    except NotInCheckout as e:
        print(f"stopped: {e}", file=sys.stderr)
        return 2


def _run() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inscription", help="Exact inscription ID, e.g. KNZc7")
    parser.add_argument("--period", help="Filter by best_period_code, e.g. LMIB")
    parser.add_argument("--certainty", help="Filter by best_date_certainty")
    parser.add_argument("--status", help="Filter by dating_status")
    parser.add_argument("--basis", help="Filter by dating_basis")
    parser.add_argument(
        "--blank-structured-recovered",
        action="store_true",
        help="Records with blank structured context but recovered dating evidence",
    )
    parser.add_argument(
        "--chronology-form",
        help="Filter by exact transliterated/translated corpus form, e.g. A-ZU-RA",
    )
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    rows = filter_records(args)
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    else:
        emit_markdown(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
