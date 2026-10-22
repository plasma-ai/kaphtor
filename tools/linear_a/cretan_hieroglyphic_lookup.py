#!/usr/bin/env python3
"""Query the Cretan Hieroglyphic reference layer (data/linear-a/cretan-hieroglyphic/)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = "tools.linear_a"

from ..paths import LINEAR_A_DATA, NotInCheckout, require

BASE = LINEAR_A_DATA / "cretan-hieroglyphic"


def load(name: str):
    return json.loads(require(BASE / name, name).read_text(encoding="utf-8"))


PD_TARGET = "phaistos disc"
PD_FIELD = "phaistos_disc_correspondences"
PROJECT_BRIDGE_SOURCE = "di Mino sign bridge"   # the source the CH data gives the project's own sign bridge
TABLE_7_1_SOURCE = "Meissner & Salgarella 2024 Table 7.1"


def normalize_ch_sign(value: str) -> str:
    """Comparison key for a CH id: 'CH 40', 'ch_040' and 'CH_040' all give 'CH_040'. Stored ids mix cases."""
    wanted = value.strip().replace(" ", "_").upper()
    if wanted.startswith("CH_"):
        num, _, rest = wanted[3:].partition("_")
        digits = len(num) - len(num.lstrip("0123456789"))
        return "CH_" + num[:digits].zfill(3) + num[digits:] + (f"_{rest}" if rest else "")
    return wanted


def field_rows(sign: dict, field: str) -> list:
    """A comparanda list; 109 records store null in the LLM-opinion fields."""
    return sign.get(field) or []


def comparanda_for(sign: dict) -> dict:
    return {
        "ch_sign": sign["id"],
        "label": sign.get("label"),
        "comparanda_status": sign.get("comparanda_status"),
        "scholarly": {
            "linear_a": sign.get("scholarly_linear_a_comparanda", []),
            "linear_b": sign.get("scholarly_linear_b_comparanda", []),
            "phoenician": sign.get("scholarly_phoenician_comparanda", []),
            "egyptian": sign.get("scholarly_egyptian_comparanda", []),
            "phaistos_disc": sign.get("scholarly_phaistos_disc_comparanda", []),
        },
        "llm_opinion": {
            "visual": sign.get("llm_visual_comparanda_opinion", []),
            "phaistos_disc": sign.get("llm_phaistos_disc_visual_opinion", []),
            "rationale": sign.get("llm_palaeographic_rationale"),
        },
        PD_FIELD: field_rows(sign, PD_FIELD),
    }


def main() -> int:
    """Exit 2 with the file's name when a data file is not in the checkout."""
    try:
        _run()
    except NotInCheckout as e:
        print(f"stopped: {e}", file=sys.stderr)
        return 2
    return 0


def _run() -> None:
    parser = argparse.ArgumentParser(description="Lookup Cretan Hieroglyphic signs and CH->Linear A correspondences.")
    parser.add_argument("sign", nargs="?", help="CH sign id, e.g. CH_042 or CH 042")
    parser.add_argument("--linear-a", dest="linear_a", help="Linear A sign, e.g. AB08")
    parser.add_argument("--list", action="store_true", help="List all staged CH signs")
    parser.add_argument("--source-manifest", action="store_true", help="Print source manifest")
    parser.add_argument("--comparanda", action="store_true", help="Print cross-script comparanda for a CH sign")
    parser.add_argument("--target-system", help="Filter comparanda by target system, e.g. Egyptian or Phaistos Disc")
    parser.add_argument("--llm-opinion-only", action="store_true", help="Return only LLM visual-opinion comparanda")
    parser.add_argument("--scholarly-only", action="store_true", help="Return only source-backed/scholarly comparanda")
    parser.add_argument("--completion-audit", action="store_true", help="Summarize metadata completion status")
    parser.add_argument("--source-blocked", action="store_true", help="List source-blocked CH fields and comparanda")
    parser.add_argument("--chic-row", help="Lookup an imported CHIC inscription/object row by id")
    parser.add_argument("--3d", dest="three_d", metavar="CHIC_NNN",
                        help="Lookup ERC INSCRIBE 3D models for a CHIC record id (or --3d all for the manifest)")
    args = parser.parse_args()

    signs = load("cretan_hieroglyphic_signs.json")["records"]
    inscriptions = load("cretan_hieroglyphic_inscriptions.json")
    objects = load("cretan_hieroglyphic_objects.json")
    if args.source_manifest:
        print(json.dumps(load("cretan_hieroglyphic_source_manifest.json"), indent=2, ensure_ascii=False))
        return
    if args.three_d:
        manifest = load("inscribe_3d_models.json")
        if args.three_d.lower() == "all":
            print(json.dumps(manifest, indent=2, ensure_ascii=False))
            return
        hits = [m for m in manifest["models"] if args.three_d in m.get("chic_record_matches", [])]
        print(json.dumps({
            "query": args.three_d,
            "license": manifest["license"],
            "models": hits or [],
            "status": "ok" if hits else "no_3d_model_matched (5 manifest entries carry only CMS refs — try --3d all)",
        }, indent=2, ensure_ascii=False))
        return
    if args.completion_audit:
        required = [
            "metadata_completion_status",
            "scholarly_linear_a_comparanda",
            "scholarly_linear_b_comparanda",
            "scholarly_egyptian_comparanda",
            "scholarly_phaistos_disc_comparanda",
            "llm_visual_comparanda_opinion",
            "llm_phaistos_disc_visual_opinion",
            "source_blocked_fields",
        ]
        summary = {
            "sign_records_total": len(signs),
            "completed_sign_records": sum(1 for s in signs if s.get("metadata_completion_status")),
            "missing_required_by_sign": {
                s["id"]: [field for field in required if field not in s]
                for s in signs
                if any(field not in s for field in required)
            },
            "inscription_rows": len(inscriptions.get("records", [])),
            "inscription_status": inscriptions.get("status"),
            "object_rows": len(objects.get("records", [])),
            "object_status": objects.get("status"),
        }
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return
    if args.source_blocked:
        blocked = []
        for sign in signs:
            rows = []
            rows.extend(sign.get("source_blocked_fields", []))
            for field in [
                "scholarly_egyptian_comparanda",
                "scholarly_phaistos_disc_comparanda",
                "scholarly_phoenician_comparanda",
            ]:
                for rec in sign.get(field, []):
                    if rec.get("relationship_type") in {"source_blocked", "rejected_parallel"}:
                        rows.append({"field": field, **rec})
            if rows:
                blocked.append({"ch_sign": sign["id"], "label": sign.get("label"), "blocked_or_rejected": rows})
        print(json.dumps(blocked, indent=2, ensure_ascii=False))
        return
    if args.chic_row:
        wanted = args.chic_row
        hits = []
        for dataset_name, dataset in [("inscriptions", inscriptions), ("objects", objects)]:
            for row in dataset.get("records", []):
                ids = {str(row.get(k, "")) for k in ["id", "source_id", "object_id"]}
                if wanted in ids:
                    item = dict(row)
                    item["_dataset"] = dataset_name
                    hits.append(item)
        if hits:
            print(json.dumps(hits, indent=2, ensure_ascii=False))
        else:
            print(json.dumps({
                "query": wanted,
                "status": "not_imported_or_source_blocked",
                "inscription_status": inscriptions.get("status"),
                "object_status": objects.get("status"),
                "acquisition_requirements": {
                    "inscriptions": inscriptions.get("source_acquisition_queue") or inscriptions.get("source_blocked", {}),
                    "objects": objects.get("source_blocked", {}),
                },
            }, indent=2, ensure_ascii=False))
        return
    if args.list:
        for sign in signs:
            las = ",".join(c["linear_a_sign"] for c in sign.get("linear_a_correspondences", []))
            print(f'{sign["id"]}\t{sign.get("label") or ""}\t{sign.get("douros_pua") or ""}\t{las}')
        return
    if args.linear_a:
        hits = [s for s in signs if any(c.get("linear_a_sign") == args.linear_a for c in s.get("linear_a_correspondences", []))]
        print(json.dumps(hits, indent=2, ensure_ascii=False))
        return
    if args.target_system:
        target = args.target_system.lower()
        hits = []
        scholarly_fields = [
            "scholarly_linear_a_comparanda",
            "scholarly_linear_b_comparanda",
            "scholarly_phoenician_comparanda",
            "scholarly_egyptian_comparanda",
            "scholarly_phaistos_disc_comparanda",
        ]
        llm_fields = ["llm_visual_comparanda_opinion", "llm_phaistos_disc_visual_opinion"]
        fields = []
        if not args.llm_opinion_only:
            fields.extend(scholarly_fields)
        if not args.scholarly_only:
            fields.extend(llm_fields)
        for sign in signs:
            matches = []
            for field in fields:
                for rec in field_rows(sign, field):
                    if rec.get("target_system", "").lower() == target:
                        item = dict(rec)
                        item["field"] = field
                        matches.append(item)
            # Disc correspondence rows carry no target_system: Table 7.1 rows are scholarly, the project's own
            # bridge rows show only without a filter, and none are LLM opinion.
            if target == PD_TARGET and not args.llm_opinion_only:
                for rec in field_rows(sign, PD_FIELD):
                    if rec.get("source") not in (TABLE_7_1_SOURCE, PROJECT_BRIDGE_SOURCE):
                        print(f"{sign['id']}: unclassified {PD_FIELD} source {rec.get('source')!r}; "
                              f"expected {TABLE_7_1_SOURCE!r} or {PROJECT_BRIDGE_SOURCE!r}", file=sys.stderr)
                        sys.exit(2)
                    if args.scholarly_only and rec.get("source") == PROJECT_BRIDGE_SOURCE:
                        continue
                    matches.append({**rec, "field": PD_FIELD})
            if matches:
                hits.append({"ch_sign": sign["id"], "label": sign.get("label"), "matches": matches})
        print(json.dumps(hits, indent=2, ensure_ascii=False))
        return
    if args.sign:
        wanted = normalize_ch_sign(args.sign)
        hits = [s for s in signs if normalize_ch_sign(s["id"]) == wanted]
        if not hits:
            print(json.dumps({"error": "not_found", "query": args.sign}, indent=2, ensure_ascii=False))
            sys.exit(1)
        sign = hits[0]
        if args.comparanda:
            data = comparanda_for(sign)
            if args.scholarly_only:
                data.pop("llm_opinion", None)
            if args.llm_opinion_only:
                data.pop("scholarly", None)
            print(json.dumps(data, indent=2, ensure_ascii=False))
            return
        print(json.dumps(sign, indent=2, ensure_ascii=False))
        return
    parser.print_help()


if __name__ == "__main__":
    sys.exit(main())
