#!/usr/bin/env python3
"""D7 S3 on Linear A (docs/d7-structural-preregistration.md, signed by di Mino 2026-11-02): Schrijver's -RE beside -TE
(claims 5 and 6).

    d7_s3_linear_a.py --out FILE [--perm 10000] [--seed 20261102] [--corpus data/linear-a/corpus.json]

Words: the corpus's distinct multi-sign words (a hyphen, not a numeral: null_model_audit.load_corpus_words' rule),
each kept only if one witness has no lost sign ([ ] ?) and no damage mark (𐝫), the onomasticon's intact rule. A
word broken at its end may have lost the final sign S3 counts. Signs are taken as written, in the gold guard's
canonical spelling (RA₂ apart from RA). The whole corpus is primary (T2).

Counts and null: the controls' own (d7_structural_controls.s3_counts, permute_finals, s3_test). Narrow: X-TE and
X-RE both words (primary, T3). Broad: TE~TI, RE~RI. Second count: X and X-TE both words. Final signs are permuted
among words of the same sign count, 10,000 times; observed, expected and p for each count.

Report-only: reads the corpus, writes only --out, and refuses an existing --out. Exit 2 for an existing --out, 3 for
an unreadable corpus.

Attribution: di Mino
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    __package__ = "tools.linear_a.validation"

from ...paths import LINEAR_A_DATA
from .check_unread_words import surface_damage
from .d7_structural_controls import SEED, s3_test
from .root_match_phase0 import sign_group_key

CORPUS = LINEAR_A_DATA / "corpus.json"
NARROW = (("TE",), ("RE",))
BROAD = (("TE", "TI"), ("RE", "RI"))
PERM = 10000
LOST = re.compile(r"[\[\]?]")


def intact_types(corpus: dict) -> tuple[set[tuple[str, ...]], Counter]:
    """The word types with at least one clean witness, and a count of the witnesses set aside and why."""
    types: set[tuple[str, ...]] = set()
    why: Counter = Counter()
    for d in corpus.values():
        tw = d.get("transliteratedWords") or []
        uw = d.get("words") or []
        aligned = len(uw) == len(tw)
        for i, raw in enumerate(tw):
            if not isinstance(raw, str) or "-" not in raw or raw.replace("-", "").strip().isdigit():
                continue
            if LOST.search(raw):
                why["lost sign"] += 1
                continue
            if not aligned:
                why["no aligned unicode"] += 1
            elif surface_damage(uw[i]):
                why["damage mark"] += 1
                continue
            key = sign_group_key(raw)
            if len(key) >= 2:
                types.add(key)
    return types, why


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--perm", type=int, default=PERM)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--corpus", type=Path, default=CORPUS)
    args = ap.parse_args(argv)
    if args.out.exists():
        print(f"{args.out} exists; never overwritten", file=sys.stderr)
        return 2
    try:
        raw = args.corpus.read_bytes()
        corpus = json.loads(raw.decode("utf-8"))
    except (OSError, ValueError, UnicodeDecodeError) as e:
        print(f"corpus unreadable: {e}", file=sys.stderr)
        return 3
    t0 = time.time()
    types, why = intact_types(corpus)
    words = sorted(types)
    report = {
        "draft": "docs/d7-structural-preregistration.md",
        "args": {"perm": args.perm, "seed": args.seed, "corpus": str(args.corpus)},
        "sha256": {"corpus.json": hashlib.sha256(raw).hexdigest()},
        "types": len(words),
        "witnesses_set_aside": dict(why),
        "narrow": s3_test(words, *NARROW, args.perm, args.seed),
        "broad": s3_test(words, *BROAD, args.perm, args.seed),
    }
    report["seconds"] = round(time.time() - t0, 1)
    with args.out.open("x", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
