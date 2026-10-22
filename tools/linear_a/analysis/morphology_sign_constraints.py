#!/usr/bin/env python3
"""Export sign constraints from morphology and held-out validation.

Morphology may route future reruns/reviews, but this tool never promotes signs.

Usage:
    uv run tools/linear_a/analysis/morphology_sign_constraints.py --sign-implications IMPLICATIONS.json \
        [--heldout-results BY_SITE.json] [--support-heldout-results BY_SUPPORT.json]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    __package__ = "tools.linear_a.analysis"

from ...paths import NotInCheckout, require
from ..sign_proposer import load_rejected_values

PERMITTED = ["*21F", "*34", "*314", "*323", "*118", "*47", "*305", "*164", "*28B", "*188", "*331", "*903", "*802"]
HARD = {
    "JU": "review_only_do_not_resolve_ra_re",
    "*411": "non_phonetic_or_segmentation_do_not_treat_as_ordinary_syllable",
    "VS": "non_phonetic_or_segmentation_do_not_treat_as_ordinary_syllable",
}


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def export_constraints(
    sign_implications_path: Path, heldout_path: Path | None, support_heldout_path: Path | None = None
) -> dict[str, Any]:
    implications = load_json(sign_implications_path, [])
    by_sign = {row.get("sign"): row for row in implications if isinstance(row, dict)}
    heldout = load_json(heldout_path, {}) if heldout_path and heldout_path.exists() else {}
    support_heldout = (
        load_json(support_heldout_path, {}) if support_heldout_path and support_heldout_path.exists() else {}
    )
    heldout_supported = (
        heldout.get("decision") == "PARADIGM_SUPPORTED"
        and heldout.get("precision_like_weighted", 0) >= 0.25
        and support_heldout.get("decision") == "PARADIGM_SUPPORTED"
        and support_heldout.get("precision_like_weighted", 0) >= 0.25
    )
    rerun_queue = []
    review_queue = []
    no_action = []
    for sign in PERMITTED:
        row = by_sign.get(sign, {})
        occurrences = row.get("morphology_sensitive_occurrences", 0)
        templates = row.get("templates_involved", [])
        independent_basis = []
        if heldout_supported and "shafel_yasa" in templates:
            independent_basis.append("site_and_support_heldout_formula_support")
        if row.get("direct_anchor_proximity"):
            independent_basis.append("direct_anchor_proximity")
        record = {
            "sign": sign,
            "morphology_sensitive_occurrences": occurrences,
            "templates": templates,
            "independent_non_morphological_evidence": independent_basis,
            "promotion_allowed": False,
            "permitted_future_exact_rerun_values": [],
            "evidence_basis": row.get("sample_occurrences", [])[:5],
        }
        if occurrences and independent_basis:
            record["action"] = "rerun_queue"
            record["blocked_reason"] = "future exact rerun required before any sign decision"
            rerun_queue.append(record)
        elif occurrences:
            record["action"] = "review_queue"
            record["blocked_reason"] = "morphology context only; independent non-morphological evidence absent"
            review_queue.append(record)
        else:
            record["action"] = "no_action"
            record["blocked_reason"] = "no morphology-sensitive occurrences"
            no_action.append(record)
    rejected = load_rejected_values()
    hard_exclusions = [
        {
            "sign": sign,
            "status": "rejected_value_do_not_revive",
            "value": record["value"],
            "decision": record["decision"],
            "promotion_allowed": False,
            "rerun_allowed": False,
        }
        for sign, records in rejected.items()
        for record in records
    ]
    hard_exclusions += [
        {"sign": sign, "status": reason, "promotion_allowed": False, "rerun_allowed": False}
        for sign, reason in HARD.items()
    ]
    enforcement = {f"{e['sign']}={e['value']}_not_rerun_or_revived": True for e in hard_exclusions if "value" in e}
    enforcement.update({
        "JU_ra_re_not_resolved": True,
        "*411_VS_not_ordinary_syllables": True,
    })
    return {
        "promotion_allowed": False,
        "rerun_queue": rerun_queue,
        "review_queue": review_queue,
        "no_action": no_action,
        "hard_exclusions": hard_exclusions,
        "hard_exclusion_enforcement": enforcement,
    }


def main() -> int:
    """Exit 2 with the file's name when an input file is not found."""
    try:
        _run()
    except NotInCheckout as e:
        print(f"stopped: {e}", file=sys.stderr)
        return 2
    return 0


def _run() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sign-implications", type=Path, required=True,
                        help="JSON list of per-sign morphology implications (sign, morphology_sensitive_occurrences, "
                             "templates_involved, sample_occurrences, direct_anchor_proximity)")
    parser.add_argument("--heldout-results", type=Path,
                        help="Site held-out validation result (decision, precision_like_weighted)")
    parser.add_argument("--support-heldout-results", type=Path,
                        help="Support held-out validation result (decision, precision_like_weighted)")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    sign_implications = require(args.sign_implications, args.sign_implications.name)
    output = export_constraints(sign_implications, args.heldout_results, args.support_heldout_results)
    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
