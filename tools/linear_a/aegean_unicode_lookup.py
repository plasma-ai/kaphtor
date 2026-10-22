#!/usr/bin/env python3
"""Linear A and Linear B signs by Unicode codepoint, glyph, value or token, and the rendering status of each."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = "tools.linear_a"

from ..paths import LINEAR_A_DATA, NotInCheckout, require

SIGN_REGISTRY = LINEAR_A_DATA / "sign-registry.json"
SIGLA_MAP = LINEAR_A_DATA / "sigla-sign-map.json"
LINEAR_B_MAP = LINEAR_A_DATA / "linear-b-sign-map.json"
OVERLAY = LINEAR_A_DATA / "linear_b_unicode_token_overlay.json"

def read(path):
    return json.loads(require(path, path.name).read_text(encoding="utf-8"))
def emit(x):
    print(json.dumps(x, ensure_ascii=False, indent=2))
def norm(s):
    s=str(s or "").upper().replace("*","A").replace(" ","").replace("-","")
    m=re.fullmatch(r"AB(\d{1,3})", s)
    if m: return "AB"+m.group(1).zfill(3)
    m=re.fullmatch(r"A(\d{1,3}[A-Z]?)", s)
    if m: return "A"+m.group(1)[:3].zfill(3)+m.group(1)[3:]
    m=re.fullmatch(r"B(\d{1,3}[A-Z]?)", s)
    if m: return "B"+m.group(1)[:3].zfill(3)+m.group(1)[3:]
    return s
def main() -> int:
    """Exit 2 with the file's name when a data file is not in the checkout."""
    try:
        _run()
    except NotInCheckout as e:
        print(f"stopped: {e}", file=sys.stderr)
        return 2
    return 0
def _run():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--linear-a")
    p.add_argument("--linear-b")
    p.add_argument("--value")
    p.add_argument("--token")
    p.add_argument("--unicode")
    p.add_argument("--glyph")
    p.add_argument("--missing-linear-a", action="store_true")
    p.add_argument("--missing-linear-b", action="store_true")
    p.add_argument("--review-required", action="store_true")
    p.add_argument("--completion-audit", action="store_true")
    p.add_argument("--limit", type=int, default=50)
    a=p.parse_args()
    la=read(SIGN_REGISTRY).get("signs", [])
    lb=read(LINEAR_B_MAP).get("signs", []) if LINEAR_B_MAP.exists() else []
    ov=read(OVERLAY).get("tokens", []) if OVERLAY.exists() else []
    if a.completion_audit:
        emit({
            "linear_a_total": len(la),
            "linear_a_status_counts": {k:sum(1 for r in la if r.get("rendering",{}).get("unicode_status")==k) for k in sorted({r.get("rendering",{}).get("unicode_status") for r in la})},
            "linear_a_missing_status": sum(1 for r in la if not r.get("rendering",{}).get("unicode_status")),
            "linear_b_sign_map_total": len(lb),
            "linear_b_status_counts": {k:sum(1 for r in lb if r.get("unicode_status")==k) for k in sorted({r.get("unicode_status") for r in lb})},
            "linear_b_token_overlay_total": len(ov),
            "linear_b_token_status_counts": {k:sum(1 for r in ov if r.get("mapping_status")==k) for k in sorted({r.get("mapping_status") for r in ov})},
        }); return
    rows=[]
    if a.linear_a:
        q=norm(a.linear_a)
        rows=[r for r in la if norm(r.get("ab_number"))==q or norm(r.get("name"))==q]
    elif a.linear_b:
        q=norm(a.linear_b)
        rows=[r for r in lb if norm(r.get("sign_number"))==q or norm(r.get("id"))==q]
    elif a.value:
        q=a.value.lower()
        rows=[r for r in lb if q==str(r.get("standard_value","")).lower() or q in [str(x).lower() for x in r.get("token_values",[])]]
    elif a.token:
        rows=[r for r in ov if r.get("token")==a.token]
    elif a.unicode:
        q=a.unicode.upper()
        rows=[r for r in lb if str(r.get("unicode","")).upper()==q] + [r for r in la if str(r.get("rendering",{}).get("unicode","")).upper()==q]
    elif a.glyph:
        rows=[r for r in lb if r.get("unicode_glyph")==a.glyph] + [r for r in la if r.get("rendering",{}).get("unicode_glyph")==a.glyph]
    elif a.missing_linear_a:
        rows=[r for r in la if r.get("rendering",{}).get("unicode_status")!="STANDARD_UNICODE"]
    elif a.missing_linear_b:
        rows=[r for r in lb if r.get("unicode_status")!="STANDARD_UNICODE"]
    elif a.review_required:
        rows=[r for r in la if r.get("rendering",{}).get("unicode_status")=="REVIEW_REQUIRED"] + [r for r in lb if r.get("unicode_status")=="REVIEW_REQUIRED"]
    emit(rows[:a.limit])
if __name__ == "__main__":
    sys.exit(main())
