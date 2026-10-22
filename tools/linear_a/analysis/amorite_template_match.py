#!/usr/bin/env python3
"""Amorite name-template matcher.

Tests Linear A onomasticon tokens against the two-element Amorite
sentence-name template (ELEMENT1 + ELEMENT2) using the Gelb AS 21 catalog:
openers (ʿammī-, ʾabī-, ʾilī-, mutī-, šumu-, niqmī-, yaʿqub-...) are the
first elements attested ≥ MIN_OPENER_FREQ times in the 6,662-name catalog;
finals are the full second-element inventory plus glossary stems.

Comparison happens in the Linear A equivalence class: gutturals dropped and
geminates collapsed on the Amorite side (that is what the open syllabary
does to them), then weighted Levenshtein per half, length-weighted.

Usage:
  uv run tools/linear_a/analysis/amorite_template_match.py A-MI-DA-U [--top 5] [--json]
  uv run tools/linear_a/analysis/amorite_template_match.py --onomasticon [--min-score 0.25] [--json]
      Batch mode: rank template fits for every onomasticon token
      (report only — never writes affiliations).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    __package__ = "tools.linear_a.analysis"

from ...core.phonetics import weighted_levenshtein
from ...core.skeleton import extract_full
from ...paths import CONTACT_DATA, LINEAR_A_DATA, NotInCheckout, require

MIN_OPENER_FREQ = 5
GUTTURALS = "ʿʾhḥḫġ"


def la_reduce(form: str, fold_vowels: bool = False) -> str:
    """Reduce an Amorite form to its Linear A CV equivalence class:
    drop gutturals, collapse geminates. With fold_vowels, all vowels merge
    to a — vowel wobble is philologically cheap (Golinets on the Amorite
    theme vowel) where consonant substitution is dear, and the plain
    Levenshtein prices them identically; folding restores the asymmetry."""
    s = "".join(c for c in form if c not in GUTTURALS)
    s = re.sub(r"([bcdfgklmnpqrstwyzšṣṭḏẓ])\1", r"\1", s)
    if fold_vowels:
        s = re.sub(r"[eiou]", "a", s)
    return s


def load_inventories():
    openers: Counter = Counter()
    finals: Counter = Counter()
    path = require(CONTACT_DATA / "amorite_onomasticon.jsonl", "amorite_onomasticon.jsonl")
    for line in path.read_text(encoding="utf-8").splitlines():
        e = json.loads(line)
        els = e.get("name_elements") or []
        if len(els) >= 2:
            if els[0]:
                openers[els[0]] += 1
            for el in els[1:]:
                if el and len(el) >= 2:
                    finals[el] += 1
        elif e.get("pos") in ("verbal_stem", "verbal_root", "noun") and e.get("normalized"):
            finals[e["normalized"]] += 0  # present but unweighted
    # Openers must reduce to ≥3 characters: single-syllable "openers" (la,
    # ki, du, pa, si...) are prepositional/particle elements from Gelb rows
    # like LA+GARR-UM, not name-openers, and they dominate the noise band.
    open_inv = {k: v for k, v in openers.items()
                if v >= MIN_OPENER_FREQ and len(la_reduce(k)) >= 3}
    final_inv = dict(finals)
    return open_inv, final_inv


def token_vocalized(translit: str) -> list[str]:
    """CV string per syllable of a Linear A transliteration."""
    out = []
    for c, v in extract_full(translit):
        out.append((c or "") + (v or ""))
    return out


_REDUCED_CACHE: dict[int, tuple[list, list]] = {}


def _reduced_inventories(open_inv: dict, final_inv: dict, fold: bool):
    """Precompute reductions once — the inventories are constant across the
    batch, and per-split recomputation cost ~2.2M redundant la_reduce calls."""
    key = (id(open_inv), id(final_inv), fold)
    cached = _REDUCED_CACHE.get(key)
    if cached is None:
        cached = (
            [(la_reduce(o, fold), o, f) for o, f in open_inv.items()],
            [(la_reduce(x, fold), x, n) for x, n in final_inv.items()
             if len(la_reduce(x)) >= 2],
        )
        _REDUCED_CACHE[key] = cached
    return cached


def score_token(translit: str, open_inv: dict, final_inv: dict, top: int = 5,
                fold_vowels: bool = True):
    syls = token_vocalized(translit)
    if len(syls) < 3:
        return []
    open_red, final_red = _reduced_inventories(open_inv, final_inv, fold_vowels)
    results = []
    for i in range(1, len(syls) - 1):
        first, second = "".join(syls[:i]), "".join(syls[i:])
        if fold_vowels:
            first = re.sub(r"[eiou]", "a", first)
            second = re.sub(r"[eiou]", "a", second)
        best_open = min(
            ((weighted_levenshtein(first, ro) / max(len(first), 2), o, f)
             for ro, o, f in open_red),
            default=None,
        )
        best_final = min(
            ((weighted_levenshtein(second, rx) / max(len(second), 2), x, n)
             for rx, x, n in final_red),
            default=None,
        )
        if not best_open or not best_final:
            continue
        d1, o, of = best_open
        d2, x, xf = best_final
        combined = round((d1 * len(first) + d2 * len(second)) / (len(first) + len(second)), 3)
        results.append({
            "split": f"{'-'.join(syls[:i])} | {'-'.join(syls[i:])}",
            "opener": o, "opener_freq": of, "opener_dist": round(d1, 3),
            "final": x, "final_freq": xf, "final_dist": round(d2, 3),
            "score": combined,
        })
    results.sort(key=lambda r: r["score"])
    return results[:top]


def main() -> int:
    try:
        return _run()
    except NotInCheckout as e:
        print(f"stopped: {e}", file=sys.stderr)
        return 2


def _run() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("token", nargs="?", help="Linear A transliteration (e.g. A-MI-DA-U)")
    ap.add_argument("--onomasticon", action="store_true", help="Batch over all onomasticon tokens")
    ap.add_argument("--min-score", type=float, default=0.25,
                    help="Batch mode: report tokens whose best fit scores at or below this")
    ap.add_argument("--top", type=int, default=5)
    ap.add_argument("--strict-vowels", action="store_true",
                    help="Disable vowel folding (price vowel substitutions like consonants)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    fold = not args.strict_vowels

    open_inv, final_inv = load_inventories()

    if args.onomasticon:
        ono = json.loads(require(LINEAR_A_DATA / "onomasticon.json", "onomasticon.json").read_text(encoding="utf-8"))
        entries = ono.get("entries", ono)
        rows = entries if isinstance(entries, list) else list(entries.values())
        report = []
        for r in rows:
            tok = r.get("token") if isinstance(r, dict) else None
            if not tok:
                continue
            fits = score_token(tok, open_inv, final_inv, top=1, fold_vowels=fold)
            if fits and fits[0]["score"] <= args.min_score:
                report.append({"token": tok,
                               "affiliation": r.get("affiliation"),
                               "type": r.get("type"),
                               **fits[0]})
        report.sort(key=lambda r: r["score"])
        if args.json:
            print(json.dumps(report, ensure_ascii=False, indent=1))
        else:
            print(f"openers: {len(open_inv)} | finals: {len(final_inv)} | "
                  f"fits ≤ {args.min_score}: {len(report)}")
            for r in report:
                print(f"  {r['token']:20s} {r['split']:26s} "
                      f"= {r['opener']}+{r['final']:14s} score {r['score']}"
                      f"  [{r.get('affiliation')}]")
        return 0

    if not args.token:
        ap.error("provide a token or --onomasticon")
    fits = score_token(args.token, open_inv, final_inv, top=args.top, fold_vowels=fold)
    if args.json:
        print(json.dumps(fits, ensure_ascii=False, indent=1))
    else:
        print(f"{args.token} — template fits (openers {len(open_inv)}, finals {len(final_inv)}):")
        for f in fits:
            print(f"  {f['split']:26s} = {f['opener']} (×{f['opener_freq']}, d={f['opener_dist']}) "
                  f"+ {f['final']} (×{f['final_freq']}, d={f['final_dist']})  → {f['score']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
