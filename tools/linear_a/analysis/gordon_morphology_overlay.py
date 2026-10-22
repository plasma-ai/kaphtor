#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Gordon morphology overlay for Linear A.

Scans the local corpus and optional translation/status records for registered
Gordon morphology templates. This tool never promotes signs; it exports
occurrence evidence and optional sign-constraint queues only.

    uv run tools/linear_a/analysis/gordon_morphology_overlay.py [--translations FILE] [--json]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    __package__ = "tools.linear_a.analysis"

from ...paths import LINEAR_A_DATA, NotInCheckout, require

DATA = LINEAR_A_DATA
HARD_EXCLUSIONS = {"*411": "non_phonetic_or_segmentation", "VS": "non_phonetic_or_segmentation"}
SUBSCRIPT_TRANSLATION = str.maketrans({"₀": "0", "₁": "1", "₂": "2", "₃": "3", "₄": "4", "₅": "5", "₆": "6", "₇": "7", "₈": "8", "₉": "9"})


def load_json(path: Path, default: Any = None) -> Any:
    if not path or not path.exists():
        return default
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def canonical_word(word: Any, strip_digits: bool = False) -> str:
    text = str(word or "").translate(SUBSCRIPT_TRANSLATION).upper()
    text = text.replace("𐄁", "").strip()
    text = re.sub(r"[^A-Z0-9*?\\-]+", "", text).strip("-")
    if strip_digits:
        text = re.sub(r"(?<=[A-Z])\d+", "", text)
    return text


def sign_syllables(word: Any) -> list[str]:
    return [part for part in canonical_word(word, False).split("-") if part]


def template_match(word: Any, template_id: str) -> bool:
    form = canonical_word(word, False)
    stripped = canonical_word(word, True)
    sylls = sign_syllables(word)
    forms = {form, stripped}
    if not form:
        return False
    if template_id == "an_gentilic_name":
        return any(f.endswith(("-NA", "-NE")) for f in forms)
    if template_id == "feminine_ti":
        return any(f.endswith("-TI") for f in forms)
    if template_id == "feminine_atu":
        return any(f.endswith(("-A-TU", "-NA-TU", "-TU-NA")) for f in forms)
    if template_id == "plural_mina_pina":
        return any("MI-NA" in f or "PI-NA" in f or "NA-MI-NA" in f or "MA-PI-NA" in f for f in forms)
    if template_id == "relative_du":
        return "DU" in sylls
    if template_id == "shafel_yasa":
        return any(f.startswith(("JA-SA", "A-SA", "SA-SA")) for f in forms)
    if template_id == "votive_ytn_tna":
        # TA-NU-A-TI is REJECTED in the lexicon (Gordon's reading; GORILA IV reads
        # TA-NU-MU-TI, MU not A). It stays in this set so the votive_ytn_tna template
        # still matches citations of Gordon's form; it is not a live reading.
        return any(f in {"JA-TA-NO", "YA-TA-NO", "A-TA-NO", "TA-NU-A-TI", "TA-NU-A", "TA-NU"}
                   or f.startswith(("JA-TA-NO", "YA-TA-NO", "A-TA-NO")) for f in forms)
    return False


def corpus_records(corpus: Any) -> dict[str, dict[str, Any]]:
    rows = corpus.values() if isinstance(corpus, dict) else corpus
    out = {}
    for row in rows or []:
        name = row.get("name") or (row.get("names") or [""])[0]
        if name:
            out[name] = row
    return out


def translation_records(path: Path | None) -> list[dict[str, Any]]:
    """Per-inscription records from a --translations file (a list, or a dict of records); none without one."""
    if path is None:
        return []
    data = load_json(require(path, str(path)), [])
    return data if isinstance(data, list) else list(data.values())


def records_from_corpus(corpus: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    records = []
    for name, row in corpus.items():
        words = [canonical_word(w) for w in row.get("transliteratedWords", []) if canonical_word(w)]
        records.append({
            "inscription_id": name,
            "site": row.get("site", ""),
            "support": row.get("support", ""),
            "register": "",
            "findspot": row.get("findspot", ""),
            "normalized_text": " ".join(words),
            "formula_family_ids": [],
            "token_analysis": [{"normalized_token": w, "formula_role": "", "syntax_role": ""} for w in words],
            "confidence": "",
            "source_record": "corpus",
        })
    return records


def scan_occurrences(args: argparse.Namespace) -> list[dict[str, Any]]:
    templates = load_json(require(DATA / "gordon_morphology_templates.json", "gordon_morphology_templates.json"))
    if args.template:
        templates = [t for t in templates if t["template_id"] == args.template]
    corpus = corpus_records(load_json(require(DATA / "corpus.json", "corpus.json")))
    records = translation_records(Path(args.translations).expanduser() if args.translations else None) or records_from_corpus(corpus)
    occurrences = []
    for record in records:
        inscription_id = record.get("inscription_id") or record.get("name") or ""
        corpus_row = corpus.get(inscription_id, {})
        site = record.get("site") or corpus_row.get("site", "")
        support = record.get("support") or corpus_row.get("support", "")
        register = record.get("register") or record.get("translation_mode") or ""
        findspot = record.get("findspot") or corpus_row.get("findspot", "")
        if args.site and args.site.lower() not in site.lower():
            continue
        if args.support and args.support.lower() not in support.lower():
            continue
        if args.register and args.register.lower() not in register.lower():
            continue
        token_analysis = record.get("token_analysis") or []
        tokens = [t.get("normalized_token") or t.get("raw_token") or "" for t in token_analysis if isinstance(t, dict)]
        if not tokens:
            tokens = str(record.get("normalized_text") or "").split()
        for idx, token in enumerate(tokens):
            for template in templates:
                if not template_match(token, template["template_id"]):
                    continue
                sylls = sign_syllables(token)
                occurrence = {
                    "occurrence_id": f"{inscription_id}:{idx}:{template['template_id']}",
                    "inscription_id": inscription_id,
                    "site": site,
                    "support": support,
                    "register": register,
                    "findspot": findspot,
                    "formula_family": record.get("formula_family_ids") or [],
                    "language_status_layer": (record.get("language_layer_analysis") or {}).get("classification") or "",
                    "matched_template": template["template_id"],
                    "matched_word": canonical_word(token, False),
                    "matched_word_stripped": canonical_word(token, True),
                    "signs": sylls,
                    "hard_exclusion_signs": [s for s in sylls if s in HARD_EXCLUSIONS],
                    "candidate_or_unknown_signs": [s for s in sylls if s.startswith("*")],
                    "prior_translation_status_class": record.get("confidence") or record.get("translation_readiness_label") or "",
                    "source_artifact": args.translations or "corpus.json",
                }
                if args.include_neighbors:
                    occurrence["neighboring_words"] = {
                        "previous": tokens[idx - 1] if idx else "",
                        "next": tokens[idx + 1] if idx + 1 < len(tokens) else "",
                    }
                if args.source_provenance:
                    occurrence["template_source_provenance"] = template.get("source_provenance", [])
                occurrences.append(occurrence)
    return occurrences


def export_sign_constraints(occurrences: list[dict[str, Any]]) -> dict[str, Any]:
    permitted = ["*21F", "*34", "*314", "*323", "*118", "*47", "*305", "*164", "*28B", "*188", "*331", "*903", "*802"]
    rows = []
    for sign in permitted:
        hits = [o for o in occurrences if sign in o.get("signs", [])]
        action = "no_action"
        if hits:
            action = "review_queue"
        rows.append({
            "sign": sign,
            "morphology_sensitive_occurrences": len(hits),
            "templates": sorted({o["matched_template"] for o in hits}),
            "action": action,
            "promotion_allowed": False,
            "required_before_exact_rerun": "independent non-morphological evidence plus exact-rerun gate",
        })
    hard = [{"sign": sign, "status": status, "promotion_allowed": False, "rerun_allowed": False} for sign, status in HARD_EXCLUSIONS.items()]
    return {"rerun_queue": [], "review_queue": [r for r in rows if r["action"] == "review_queue"], "no_action": [r for r in rows if r["action"] == "no_action"], "hard_exclusions": hard}


def main() -> int:
    try:
        _run()
    except NotInCheckout as e:
        print(f"stopped: {e}", file=sys.stderr)
        return 2
    return 0


def _run() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--template")
    parser.add_argument("--site")
    parser.add_argument("--support")
    parser.add_argument("--register")
    parser.add_argument("--translations")
    parser.add_argument("--include-neighbors", action="store_true")
    parser.add_argument("--source-provenance", action="store_true")
    parser.add_argument("--no-promotion", action="store_true", default=True)
    parser.add_argument("--export-sign-constraints", action="store_true")
    args = parser.parse_args()
    occurrences = scan_occurrences(args)
    output = {
        "tool": "gordon_morphology_overlay",
        "promotion_allowed": False,
        "occurrence_count": len(occurrences),
        "template_counts": Counter(o["matched_template"] for o in occurrences),
        "occurrences": occurrences,
    }
    if args.export_sign_constraints:
        output["sign_constraints"] = export_sign_constraints(occurrences)
    if args.json:
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        print(f"Gordon morphology overlay: {len(occurrences)} occurrences")
        for template, count in output["template_counts"].most_common():
            print(f"  {template}: {count}")


if __name__ == "__main__":
    sys.exit(main())
