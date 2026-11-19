#!/usr/bin/env python3
"""How often does the classifier's Hattic layer (tools/linear_a/ventris_propagate.py --hattic) win by chance?

Report-only: prints, never writes. The classifier runs over the corpus with the Hattic keys as they are, then with
the same keys scrambled: every key keeps its length, and the consonants of all keys are dealt out again at random
(--seeds runs). A scrambled list has Hattic's sounds and key lengths and none of its words, so the words it wins
are the layer's chance rate. The real list says something only where it wins more.

    uv run tools/linear_a/validation/hattic_layer_null.py [--seeds 20] [--json]
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    __package__ = "tools.linear_a.validation"

from ...core import competitors as cp
from .. import ventris_propagate as vp


def scrambled(space: cp.CompetitorSpace, seed: int) -> cp.CompetitorSpace:
    """The space with every key's consonants dealt out again: lengths and the pool of consonants kept."""
    rng = random.Random(seed)
    keys = sorted(space.keys)
    pool = [t for k in keys for t in k]
    rng.shuffle(pool)
    out: dict[tuple[str, ...], list[str]] = {}
    at = 0
    for k in keys:
        out.setdefault(tuple(pool[at:at + len(k)]), []).extend(space.keys[k])
        at += len(k)
    return cp.CompetitorSpace(space.name, out, space.distances, True)


def hattic_words(space: cp.CompetitorSpace | None) -> dict[str, float]:
    """{word: its Hattic score} for the words not in the lexicon that the classifier gives to Hattic."""
    vp._get_hattic_space()
    (real, run_tokens), entries = vp._HATTIC_CACHE
    vp._HATTIC_CACHE = ((space or real, run_tokens), entries)
    try:
        data = vp.run_propagation(min_score=0.0, max_results=10 ** 9, lang_opts=vp.LanguageOptions(hattic=True))
    finally:
        vp._HATTIC_CACHE = ((real, run_tokens), entries)
    return {r["word"]: r["language"]["scores"]["Hattic"] for r in data["results"]
            if r.get("status") != "known" and r.get("language", {}).get("decision") == "Hattic"}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seeds", type=int, default=20)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    space = vp._get_hattic_space()
    real = hattic_words(None)
    null = [len(hattic_words(scrambled(space, seed))) for seed in range(args.seeds)]
    at_least = sum(n >= len(real) for n in null)
    report = {"keys": len(space.keys), "words_won_by_hattic": len(real), "scrambled_runs": args.seeds,
              "scrambled_words_won": null, "scrambled_mean": round(sum(null) / len(null), 2) if null else None,
              "p_scrambled_at_least_real": round((at_least + 1) / (args.seeds + 1), 4),
              "words": dict(sorted(real.items(), key=lambda kv: -kv[1]))}
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for k, v in report.items():
            print(f"{k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
