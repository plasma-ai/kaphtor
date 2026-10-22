#!/usr/bin/env python3
"""The Egyptian contact lexicon and roots: transliterations, hieroglyphs and their spelling candidates."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = "tools.linear_a"

from ..paths import CONTACT_DATA, LINEAR_A_DATA, NotInCheckout, require

CONTACT = CONTACT_DATA / "egyptian_lexicon.jsonl"
ROOTS = LINEAR_A_DATA / "egyptian_roots.json"

def read_jsonl(path):
    return [json.loads(line) for line in require(path, path.name).read_text(encoding="utf-8").splitlines()
            if line.strip()]
def has_hiero(text):
    return bool(text) and any(0x13000 <= ord(ch) <= 0x1345F for ch in str(text))
def emit(data):
    print(json.dumps(data, ensure_ascii=False, indent=2))
def cand_rows(row):
    return row.get("hieroglyph_candidates") or row.get("Hieroglyph_Candidates") or []
def main() -> int:
    """Exit 2 with the file's name when a data file is not in the checkout."""
    try:
        _run()
    except NotInCheckout as e:
        print(f"stopped: {e}", file=sys.stderr)
        return 2
    return 0
def _run():
    p = argparse.ArgumentParser(description="Query Egyptian contact/root metadata")
    p.add_argument("query", nargs="?")
    p.add_argument("--json", action="store_true")
    p.add_argument("--translit")
    p.add_argument("--ascii")
    p.add_argument("--root")
    p.add_argument("--hieroglyphs")
    p.add_argument("--glyph-candidate")
    p.add_argument("--mdc")
    p.add_argument("--gardiner")
    p.add_argument("--source-family")
    p.add_argument("--candidate-status")
    p.add_argument("--tla-id")
    p.add_argument("--pnm-id")
    p.add_argument("--missing-hieroglyphs", action="store_true")
    p.add_argument("--missing-spelling-candidates", action="store_true")
    p.add_argument("--source-blocked", action="store_true")
    p.add_argument("--review-required", action="store_true")
    p.add_argument("--completion-audit", action="store_true")
    p.add_argument("--limit", type=int, default=50)
    args = p.parse_args()
    contact = read_jsonl(CONTACT)
    roots = json.loads(require(ROOTS, ROOTS.name).read_text(encoding="utf-8"))
    if args.completion_audit:
        emit({
            "contact_total": len(contact),
            "contact_transliteration_unicode": sum(bool(r.get("transliteration_unicode")) for r in contact),
            "contact_transliteration_ascii": sum(bool(r.get("transliteration_ascii")) for r in contact),
            "contact_hieroglyphs": sum(has_hiero(r.get("hieroglyphs")) for r in contact),
            "contact_hieroglyph_candidates": sum(bool(r.get("hieroglyph_candidates")) for r in contact),
            "contact_missing_candidate_status": sum(not r.get("hieroglyph_candidate_status") for r in contact),
            "roots_total": len(roots),
            "roots_transliteration_unicode": sum(bool(r.get("Transliteration_Unicode")) for r in roots),
            "roots_transliteration_ascii": sum(bool(r.get("Transliteration_ASCII")) for r in roots),
            "roots_hieroglyphs": sum(bool(r.get("Hieroglyphs")) for r in roots),
            "roots_hieroglyph_candidates": sum(bool(r.get("Hieroglyph_Candidates")) for r in roots),
            "roots_missing_candidate_status": sum(not r.get("Hieroglyph_Candidate_Status") for r in roots),
        }); return
    rows = contact
    q = args.query
    if q:
        rows = [r for r in rows if q.lower() in json.dumps(r, ensure_ascii=False).lower()]
    if args.translit:
        rows = [r for r in rows if args.translit in str(r.get("transliteration_unicode", ""))]
    if args.ascii:
        rows = [r for r in rows if args.ascii in str(r.get("transliteration_ascii", ""))]
    if args.hieroglyphs:
        rows = [r for r in rows if args.hieroglyphs in str(r.get("hieroglyphs", ""))]
    if args.glyph_candidate:
        rows = [r for r in rows if any(args.glyph_candidate in str(c.get("unicode","")) for c in cand_rows(r))]
    if args.mdc:
        rows = [r for r in rows if args.mdc in [str(x) for x in r.get("manuel_de_codage", [])] or any(args.mdc == str(c.get("mdc","")) for c in cand_rows(r))]
    if args.gardiner:
        rows = [r for r in rows if args.gardiner in [str(x) for x in r.get("gardiner_sign_sequence", [])] or any(args.gardiner in [str(x) for x in c.get("gardiner_codes", [])] for c in cand_rows(r))]
    if args.source_family:
        rows = [r for r in rows if any(args.source_family.lower() == str(c.get("source_family","")).lower() for c in cand_rows(r))]
    if args.candidate_status:
        rows = [r for r in rows if r.get("hieroglyph_candidate_status") == args.candidate_status]
    if args.tla_id:
        rows = [r for r in rows if str(r.get("tla_lemma_id")) == args.tla_id]
    if args.pnm_id:
        rows = [r for r in rows if str(r.get("pnm_id")) == args.pnm_id]
    if args.missing_hieroglyphs:
        rows = [r for r in rows if not has_hiero(r.get("hieroglyphs"))]
    if args.missing_spelling_candidates:
        rows = [r for r in rows if not r.get("hieroglyph_candidates")]
    if args.source_blocked:
        rows = [r for r in rows if r.get("hieroglyph_source_status") == "SOURCE_BLOCKED" or r.get("hieroglyph_candidate_status") == "SOURCE_BLOCKED"]
    if args.review_required:
        rows = [r for r in rows if r.get("hieroglyph_source_status") == "REVIEW_REQUIRED" or r.get("hieroglyph_candidate_status") == "REVIEW_REQUIRED"]
    if args.root:
        root_rows = [r for r in roots if args.root in str(r.get("Consonantal_Root", "")) or args.root in str(r.get("Transliteration_Unicode", ""))]
        emit(root_rows[:args.limit]); return
    emit(rows[:args.limit])
if __name__ == "__main__":
    sys.exit(main())
