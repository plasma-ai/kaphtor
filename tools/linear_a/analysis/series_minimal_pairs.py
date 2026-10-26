#!/usr/bin/env python3
"""Minimal pairs between consonant series in the Linear A corpus, against a slot-matched permutation null.

Two words are a minimal pair for series a and b when they differ in one sign only, and there one has aV and the
other bV with the same vowel (KU-DA / KU-TA is a D-T pair). Free variation between two series gives more such pairs
than the series' frequencies predict; a series kept apart gives none beyond them.

Words: the distinct words of `corpus.json` with two or more signs, every one of them a syllabic sign: a word holding
a damage mark ([ ] ?), a logogram (PU-VIN), a ligature (MA+RU-ME), a numeral or an alternative reading ((TI/E)) is
left out.
A sign enters the test when it is a plain consonant-vowel syllable of the series D J K M N P Q R S T W Z; indexed
signs (TA₂, PA₃), vowels, CwV and CjV signs (NWA) and numbered signs (*301, A559) stay fixed.

Null: within each slot class (word length, sign position, vowel), the consonants of that class are shuffled among
the words that hold it. Each series keeps its exact count in every slot; only the tie between a consonant and the
rest of its word is broken. A shuffle that makes two words one counts them once, as the data does. p_upper =
P(null >= observed) and p_lower = P(null <= observed), each with the +1 correction; neither is corrected for the
number of series pairs. The totals over all pairs (`all_pairs`) show how far the lexicon as a whole runs above or
below the null, against which a single pair's ratio should be read.

Read-only over `data/`. Writes `minimal_pairs.json` and `minimal_pairs.md` under `--out`, never inside `data/` and
never over an existing file.

Usage:
    uv run python tools/linear_a/analysis/series_minimal_pairs.py --out /path/to/outdir [--focus D-T] [--permutations N]
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    __package__ = "tools.linear_a.analysis"

from ...core.corpus_utils import CORPUS_PATH, extract_words
from ...paths import DATA, NotInCheckout, require

SERIES = "DJKMNPQRSTWZ"
SYLLABLE = re.compile(rf"([{SERIES}])([AEIOU])")
SYLLABOGRAM = re.compile(rf"\*\d+[A-Z]?|A\d+[A-Z]?|[{SERIES}]?[WJ]?(?:[AEIOU]|AU|AI)[₂₃]?|PTE")
DEFAULT_SEED = 1961
OUTPUTS = ("minimal_pairs.json", "minimal_pairs.md")

Sign = tuple[str | None, str]          # (series, vowel) for a plain CV syllable, else (None, sign)


def word_types(corpus: dict) -> dict[str, list[str]]:
    """Each intact, wholly syllabic word of two or more signs, with the records it occurs in."""
    seen = defaultdict(set)
    for rec in extract_words(corpus):
        if len(rec["signs"]) >= 2 and all(SYLLABOGRAM.fullmatch(s) for s in rec["word"].split("-")):
            seen[rec["word"]].add(rec["doc_id"])
    return {w: sorted(docs) for w, docs in sorted(seen.items())}


def parse(word: str) -> list[Sign]:
    out = []
    for sign in word.split("-"):
        m = SYLLABLE.fullmatch(sign)
        out.append((m.group(1), m.group(2)) if m else (None, sign))
    return out


def count_pairs(words: list[list[Sign]], examples: dict | None = None) -> Counter:
    """Unordered pairs of distinct words differing in one CV sign with the same vowel, by series pair (a, b), a < b;
    a word listed twice counts once, so the two words of a pair always differ in series. With `examples`, the index
    pairs of the words are collected under each series pair."""
    first = {}
    for k, w in enumerate(words):
        first.setdefault(tuple(w), k)
    distinct = sorted(first.values())
    counts = Counter()
    for i in range(max(map(len, words), default=0)):
        groups = defaultdict(list)
        for k in distinct:
            w = words[k]
            if i < len(w) and w[i][0] is not None:
                groups[(len(w), tuple(w[:i]), w[i][1], tuple(w[i + 1:]))].append((w[i][0], k))
        for members in groups.values():
            for (a, j), (b, k) in itertools.combinations(members, 2):
                key = tuple(sorted((a, b)))
                counts[key] += 1
                if examples is not None:
                    examples[key].append((j, k))
    return counts


def slot_classes(words: list[list[Sign]]) -> dict[tuple[int, int, str], list[int]]:
    """The words holding a CV sign in each (length, position, vowel) class."""
    slots = defaultdict(list)
    for k, w in enumerate(words):
        for i, (s, v) in enumerate(w):
            if s is not None:
                slots[(len(w), i, v)].append(k)
    return dict(slots)


def shuffled(words: list[list[Sign]], slots: dict, rng: random.Random) -> list[list[Sign]]:
    """The words with each slot class's consonants permuted among its holders."""
    out = [list(w) for w in words]
    for (_, i, vowel), holders in slots.items():
        series = [words[k][i][0] for k in holders]
        rng.shuffle(series)
        for k, s in zip(holders, series):
            out[k][i] = (s, vowel)
    return out


def _order(row: dict) -> tuple:
    """Rank by observed/null, a pair the null never makes (null mean 0) above every ratio, and 0/0 last."""
    if row["ratio"] is not None:
        value = row["ratio"]
    else:
        value = math.inf if row["observed"] else -1
    return -value, row["pair"]


def run(found: dict[str, list[str]], permutations: int, seed: int, focus: tuple[str, str] = ("D", "T")) -> dict:
    """Observed and null pair counts for every series pair, ranked by observed/null."""
    names = list(found)
    words = [parse(w) for w in names]
    slots = slot_classes(words)
    signs = Counter(s for w in words for s, _ in w if s is not None)
    examples = defaultdict(list)
    observed = count_pairs(words, examples)
    pairs = list(itertools.combinations(sorted(signs), 2))
    rng = random.Random(seed)
    totals, ge, le = Counter(), Counter(), Counter()
    for _ in range(permutations):
        null = count_pairs(shuffled(words, slots, rng))
        for p in pairs:
            totals[p] += null[p]
            ge[p] += null[p] >= observed[p]
            le[p] += null[p] <= observed[p]
    rows = []
    for p in pairs:
        mean = totals[p] / permutations
        rows.append({"pair": "-".join(p), "signs": [signs[p[0]], signs[p[1]]], "observed": observed[p],
                     "null_mean": round(mean, 3), "ratio": round(observed[p] / mean, 3) if mean else None,
                     "p_upper": round((ge[p] + 1) / (permutations + 1), 4),
                     "p_lower": round((le[p] + 1) / (permutations + 1), 4)})
    rows.sort(key=_order)
    for rank, r in enumerate(rows, 1):
        r["rank_by_ratio"] = rank
    key = tuple(sorted(focus))
    return {"word_types": len(words), "series_signs": dict(sorted(signs.items())), "slot_classes": len(slots),
            "permutations": permutations, "seed": seed, "series_pairs": len(pairs),
            "all_pairs": {"observed": sum(observed[p] for p in pairs),
                          "null_mean": round(sum(totals[p] for p in pairs) / permutations, 3)},
            "focus": next((r for r in rows if r["pair"] == "-".join(key)), None),
            "focus_pairs": [{"words": [names[j], names[k]], "records": [found[names[j]], found[names[k]]]}
                            for j, k in sorted(examples[key])],
            "pairs": rows}


def table(result: dict) -> str:
    total = result["all_pairs"]
    lines = ["# Series minimal pairs", "",
             (f"corpus.json sha256 {result['corpus_sha256']}; {result['word_types']} word types, "
              f"{result['slot_classes']} slot classes, {result['permutations']} permutations, seed {result['seed']}; "
              f"all pairs: observed {total['observed']}, null mean {total['null_mean']}. "
              "p-values are not corrected for the number of series pairs; a pair the null never makes has no ratio "
              "and ranks first."), "",
             "| rank | pair | signs | observed | null mean | observed/null | p (excess) | p (deficit) |",
             "|---|---|---|---|---|---|---|---|"]
    for r in result["pairs"]:
        ratio = "—" if r["ratio"] is None else r["ratio"]
        lines.append(f"| {r['rank_by_ratio']} | {r['pair']} | {r['signs'][0]}, {r['signs'][1]} | {r['observed']} "
                     f"| {r['null_mean']} | {ratio} | {r['p_upper']} | {r['p_lower']} |")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    """Exit 2 with the file's name when the corpus is not in the checkout."""
    try:
        return _run(argv)
    except NotInCheckout as e:
        print(f"stopped: {e}", file=sys.stderr)
        return 2


def _run(argv: list[str] | None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, required=True, help="Output directory (outside data/)")
    parser.add_argument("--focus", default="D-T", help="The series pair to report, as A-B (default: D-T)")
    parser.add_argument("--permutations", type=int, default=10_000, help="Null permutations (default: 10000)")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="Reproducible random seed")
    parser.add_argument("--json", action="store_true", help="Print the focus pair's result as JSON")
    args = parser.parse_args(argv)
    focus = tuple(args.focus.upper().split("-"))
    if len(focus) != 2 or not all(len(s) == 1 and s in SERIES for s in focus) or focus[0] == focus[1]:
        parser.error(f"--focus takes two different series from {SERIES}, as A-B")
    if args.permutations < 1:
        parser.error("at least one permutation is required")
    out = args.out.expanduser().resolve()
    if out.is_relative_to(DATA.resolve()):
        print(f"refused: {out} is inside {DATA}; choose an --out outside data/", file=sys.stderr)
        return 1
    if out.exists() and not out.is_dir():
        print(f"refused: {out} is a file; choose a directory for --out", file=sys.stderr)
        return 1
    existing = [name for name in OUTPUTS if (out / name).exists()]
    if existing:
        print(f"refused: {', '.join(existing)} already in {out}; choose another --out", file=sys.stderr)
        return 1
    raw = require(CORPUS_PATH, "corpus.json").read_bytes()
    result = run(word_types(json.loads(raw)), args.permutations, args.seed, focus)
    result = {"corpus_sha256": hashlib.sha256(raw).hexdigest(), **result}
    out.mkdir(parents=True, exist_ok=True)
    (out / OUTPUTS[0]).write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (out / OUTPUTS[1]).write_text(table(result), encoding="utf-8")
    f = result["focus"]
    if f is None:
        missing = [s for s in focus if s not in result["series_signs"]]
        print(f"no word holds a {' or '.join(missing)} syllable; nothing to report for {'-'.join(focus)}")
    elif args.json:
        print(json.dumps({"focus": f, "focus_pairs": result["focus_pairs"]}, ensure_ascii=False, indent=2))
    else:
        total = result["all_pairs"]
        print(f"{result['word_types']} word types, {result['slot_classes']} slot classes, "
              f"{result['series_pairs']} series pairs, {result['permutations']} permutations; all pairs: observed "
              f"{total['observed']}, null mean {total['null_mean']}")
        print(f"{'-'.join(focus)}: observed {f['observed']}, null mean {f['null_mean']}, observed/null {f['ratio']}, "
              f"p (excess) {f['p_upper']}, p (deficit) {f['p_lower']}, rank {f['rank_by_ratio']} of "
              f"{result['series_pairs']}")
        for pair in result["focus_pairs"]:
            print("  " + " / ".join(pair["words"]))
        print(f"wrote: {out / OUTPUTS[0]}")
        print(f"wrote: {out / OUTPUTS[1]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
