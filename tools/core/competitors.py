"""Shoresh competitor null (§2, A15; see SHORESH.md): the same d* and p_max against the Luwian, Egyptian and Hurrian root lists.

The keys are the L6 test's (shoresh_nulls, from null_model_audit): the `Consonantal_Root` of each entry through
`_extract_consonantal_root`, accented vowels it leaves removed too, and kept only when what remains is letters (the
OCR-damaged Hurrian keys are not) with at least two tokens. Names are out unless names=True, as onomastica are on
the Semitic side (§1): L6's `_is_onomastic`, Hurrian name categories, Egyptian entries with name elements, toponyms.
Each competitor has its own table, guttural transparency as in L6, and an exact search over every key; the real
word and its decoys are the ones the Semitic statistic uses.

Report-only: reads the three data files, writes nothing.

Attribution: di Mino
"""
from __future__ import annotations

import json
import sys
import unicodedata
from collections import Counter
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

try:
    from ..paths import LINEAR_A_DATA, require
    from . import root_match as rm
    from .phonetics import (
        EGYPTIAN_DISTANCES,
        GUTTURAL_INSERT_COST,
        GUTTURAL_PHONEMES,
        LUWIAN_DISTANCES,
        SEMITIC_DISTANCES,
    )
    from .shoresh_nulls import _extract_consonantal_root, _is_onomastic
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from tools.core import root_match as rm
    from tools.core.phonetics import (
        EGYPTIAN_DISTANCES,
        GUTTURAL_INSERT_COST,
        GUTTURAL_PHONEMES,
        LUWIAN_DISTANCES,
        SEMITIC_DISTANCES,
    )
    from tools.core.shoresh_nulls import _extract_consonantal_root, _is_onomastic
    from tools.paths import LINEAR_A_DATA, require

DATA_DIR = LINEAR_A_DATA        # where data_cache.data_path keeps the Egyptian, Luwian and Hurrian roots
_HURRIAN_NAMES = frozenset({"personal_name", "royal_name", "name_element", "divine_name", "toponym"})


@dataclass(frozen=True)
class Spec:
    name: str
    file: str
    distances: dict[tuple[str, str], float]
    guttural_transparent: bool = True       # L6: Linear A cannot write a guttural, whatever the language
    digraphs: bool = True                   # bare ts, sh, kw, gw are one phoneme in this file's romanisation


COMPETITORS = (
    Spec("luwian", "luwian_roots.json", LUWIAN_DISTANCES),       # LUWIAN_DISTANCES prices kw and gw
    Spec("egyptian", "egyptian_roots.json", EGYPTIAN_DISTANCES, digraphs=False),   # one letter per phoneme
    Spec("hurrian", "hurrian_roots.json", SEMITIC_DISTANCES),     # no Hurrian table: weighted_levenshtein's default
)
_DIGRAPHS = {"ts": "ṣ", "sh": "š", "kw": "kw", "gw": "gw"}       # _tokenize_phonemes's bare-letter digraphs


def is_name(entry: dict[str, Any]) -> bool:
    if _is_onomastic(entry) or entry.get("Name_Elements"):
        return True
    if _HURRIAN_NAMES & set(str(entry.get("Category") or "").split(",")):
        return True
    return "toponym" in (entry.get("semantic_field") or ())


def run_tokens(run: str, digraphs: bool = True) -> tuple[str, ...]:
    """A consonant run one token per letter (rm.letter_token). With digraphs, two bare letters ts, sh, kw or gw
    are one token, as the shared tokeniser reads them; a letter with a mark never joins one (Egyptian msḥ is
    m s ḥ, not m š: NFD ḥ is h plus a mark)."""
    ls = rm.letters(run)
    out: list[str] = []
    i = 0
    while i < len(ls):
        pair = ls[i] + ls[i + 1] if i + 1 < len(ls) else ""
        if digraphs and pair in _DIGRAPHS:
            out.append(_DIGRAPHS[pair])
            i += 2
            continue
        t = rm.letter_token(ls[i])
        if t:
            out.append(t)
        i += 1
    return tuple(out)


def key_of(entry: dict[str, Any], digraphs: bool = True) -> tuple[str, ...] | None:
    """L6's extraction, with each vowel and the ⸗ boundary first marked "|", so the consonants on either side are
    tokenised apart: "tessub" is t s s b, not ṣ s b. Inside a run, run_tokens."""
    raw = "".join("|" if unicodedata.normalize("NFD", c)[0].lower() in "aeiou" or c == "⸗" else c
                  for c in str(entry.get("Consonantal_Root") or ""))
    runs = [r for r in _extract_consonantal_root(raw).split("|") if r]
    if not runs or not all(r.isalpha() for r in runs):
        return None
    toks = tuple(t for r in runs for t in run_tokens(r, digraphs))
    return toks if len(toks) >= 2 else None


class _Node:
    __slots__ = ("children", "end")

    def __init__(self) -> None:
        self.children: dict[str, _Node] = {}
        self.end = False


class CompetitorSpace:
    """One competitor's keys, searched exactly over a trie: one DP row per key prefix, shared by every key that
    starts with it, and a branch dropped once its row can no longer come under the limit. Each cell is the min of
    the operands `distance` uses, so the values are identical. The Semitic side's cutoff memo sits on top."""

    def __init__(self, name: str, keys: dict[tuple[str, ...], list[str]], distances: dict[tuple[str, str], float],
                 guttural_transparent: bool = True, dropped: dict[str, int] | None = None):
        self.name = name
        self.keys = keys                            # tokens → the Numbers that carry them
        self.dropped = dict(dropped or {})

        @cache
        def sub(a: str, b: str) -> float:
            return 0.0 if a == b else distances.get((a, b), distances.get((b, a), 1.0))

        self._sub = self.sub = sub              # public, so a caller can pick a competitor's substitution series
        self._ins =(lambda t: GUTTURAL_INSERT_COST if t in GUTTURAL_PHONEMES else 1.0) if guttural_transparent \
            else (lambda t: 1.0)
        self._root = _Node()
        for k in keys:
            node = self._root
            for t in k:
                node = node.children.setdefault(t, _Node())
            node.end = True
        self._memo: dict[tuple[str, ...], tuple[float, float]] = {}

    def distance(self, t1: tuple[str, ...], t2: tuple[str, ...], cutoff: float = rm.INF) -> float:
        return rm.levenshtein(t1, t2, self._sub, self._ins, cutoff)

    def min_distance(self, toks: tuple[str, ...], cutoff: float = rm.INF) -> float:
        """The exact min over every key, on the engine's _q grid, if it is ≤ cutoff, else INF."""
        memo = self._memo.get(toks)
        if memo is not None:
            value, exact_to = memo
            if value < rm.INF:
                return value if value <= cutoff else rm.INF
            if exact_to >= cutoff:
                return rm.INF
        best, _ = self._search(toks, cutoff)
        best = rm._q(best)
        self._memo[toks] = (best, cutoff if best == rm.INF else rm.INF)
        return best if best <= cutoff else rm.INF

    def classify(self, vs: list[rm.Variant], d: float) -> int:
        """-1, 0 or 1 as the decoy's d* is below, equal to or above d: the comparison d_star_over's value would
        give, made on the same sums, with the search stopped at the first key that lands strictly below."""
        tied = False
        for v in vs:
            limit = d - v.penalty + rm._EPS
            if limit < 0:
                continue
            memo = self._memo.get(v.tokens)
            if memo is not None and memo[0] == rm.INF and memo[1] >= limit:
                continue
            if memo is not None and memo[0] < rm.INF:
                x = memo[0]
            else:
                x, exact = self._search(v.tokens, limit, (v.penalty, d))
                x = rm._q(x)
                if exact:
                    self._memo[v.tokens] = (x, limit if x == rm.INF else rm.INF)
            if x == rm.INF or x > limit:
                continue
            s = rm._q(x + v.penalty)
            if s < d:
                return -1
            if s == d:
                tied = True
        return 0 if tied else 1

    def _search(self, toks: tuple[str, ...], cutoff: float,
                below: tuple[float, float] | None = None) -> tuple[float, bool]:
        """(min over keys of distance(toks, key), exact when ≤ cutoff, else INF; True). With below = (penalty, d),
        stops at the first key whose distance + penalty < d and returns (that distance, False). Rows run over key
        prefixes, columns over toks: cell (key[:j], toks[:i]) = min(delete toks[i-1] at 1.0, insert key[j-1],
        substitute). The limit carries _EPS slack, so a sum that lands on the cutoff on the _q grid stays in."""
        n = len(toks)
        limit = cutoff + rm._EPS
        sub, ins = self._sub, self._ins
        costs: dict[str, tuple[float, list[float]]] = {}       # key token → (insertion, substitution per tok)
        best = rm.INF
        start = [float(i) for i in range(n + 1)]
        stack = [(t, child, start) for t, child in self._root.children.items()]
        pop, push = stack.pop, stack.extend
        while stack:
            b, node, prev = pop()
            c = costs.get(b)
            if c is None:
                c = costs[b] = (ins(b), [sub(a, b) for a in toks])
            ib, sb = c
            left = prev[0] + ib
            cur = [left]
            low = left
            for i in range(n):                  # min of the three operands, compared inline
                x = left + 1.0
                y = prev[i + 1] + ib
                x = min(x, y)
                y = prev[i] + sb[i]
                x = min(x, y)
                cur.append(x)
                left = x
                low = min(low, x)
            if node.end and left < best and left <= limit:
                best = left
                if below is not None and rm._q(best + below[0]) < below[1]:
                    return best, False
                if best == 0.0:
                    break
            if node.children and low < best and low <= limit:
                push((t, child, cur) for t, child in node.children.items())
        return (best if best <= limit else rm.INF), True

    def d_star(self, vs: list[rm.Variant], cutoff: float = rm.INF) -> float:
        return rm.d_star_over(self.min_distance, vs, cutoff)

    def nearest(self, vs: list[rm.Variant]) -> dict[str, Any] | None:
        """The key at d* with its Numbers and variant rule, for display."""
        d_star = self.d_star(vs)
        best: tuple[float, tuple[str, ...], rm.Variant] | None = None
        for v in vs:
            limit = d_star - v.penalty + rm._EPS
            if limit < 0:
                continue
            for k in sorted(self.keys):
                d = rm._q(self.distance(v.tokens, k, limit) + v.penalty)
                if d != rm.INF and (best is None or d < best[0]):
                    best = (d, k, v)
        if best is None:
            return None
        d, k, v = best
        return {"key": "".join(k), "numbers": self.keys[k], "distance": rm._num(d), "variant_rule": v.rule}


def load(spec: Spec, names: bool = False, data_dir: Path = DATA_DIR) -> CompetitorSpace:
    entries = json.loads(require(data_dir / spec.file, spec.file).read_text(encoding="utf-8"))
    keys: dict[tuple[str, ...], list[str]] = {}
    dropped: Counter = Counter()
    for e in entries:
        if not names and is_name(e):
            dropped["name"] += 1
            continue
        k = key_of(e, spec.digraphs)
        if k is None:
            dropped["no_key"] += 1
            continue
        keys.setdefault(k, []).append(str(e.get("Number")))
    return CompetitorSpace(spec.name, keys, spec.distances, spec.guttural_transparent, dropped)


def load_all(names: bool = False, data_dir: Path = DATA_DIR) -> list[CompetitorSpace]:
    return [load(s, names, data_dir) for s in COMPETITORS]
