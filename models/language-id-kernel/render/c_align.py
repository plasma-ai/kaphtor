"""Protocol C, phase C2: sign keys, the pairwise alignment and the pool of forms (§4, §6.2, §6.3, §8.1).

A word is a tuple of sign keys. A sign with a secure Linear B value has the key (series, vowel); every other sign
is opaque and keeps its name (render/signs-a5-proposed.json). `align` is Paradigm B's §5.1 alignment, which §6.3
carries over: the longest common run of identical keys, leftmost on ties, and, where the signs after the run share
a consonant and differ in vowel, that sign as the boundary. `Pool` holds the distinct forms with their documents
and answers a fold's questions: its training forms, a type's partners and core, the training signs' frequencies
and the free arm's residue inventory.

Nothing here reads a Linear A form; the tests build pools from made-up words.

Attribution: di Mino
"""
from __future__ import annotations

import collections
import json
from dataclasses import dataclass, field
from pathlib import Path

RENDER_DIR = Path(__file__).resolve().parent
MIN_RUN = 2                                       # §3.5: m = 2
_DIGITS = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")

Word = tuple


def load_signs(render_dir: Path = RENDER_DIR) -> dict[str, tuple[str, str]]:
    raw = json.loads((render_dir / "signs-a5-proposed.json").read_text(encoding="utf-8"))
    table = {v.upper(): ("", v) for v in raw["vowels"]}
    for series, vowels in raw["series"].items():
        table.update({series + v.upper(): (series, v) for v in vowels})
    table.update({name: tuple(key) for name, key in raw["single_value_doublets"].items()})
    return table


def keys(word, signs: dict) -> Word:
    """A hyphenated word, or a list of sign names, as sign keys."""
    names = word.split("-") if isinstance(word, str) else word
    names = [n.strip().upper().translate(_DIGITS) for n in names if n.strip()]
    return tuple(signs.get(n, n) for n in names)


def _vowel(key) -> str | None:
    return key[1] if isinstance(key, tuple) else None


@dataclass(frozen=True)
class Side:
    """One form's residues around the common run."""
    prefix: Word
    boundary: tuple[str, str] | None      # the sign after the run that shares its consonant with the other form's
    suffix: Word                          # the signs after the run and the boundary
    run_first: object                     # the run's first key: the prefix's context
    run_last_vowel: str | None            # the vowel of the run's last sign: the suffix's context


@dataclass(frozen=True)
class Alignment:
    run_len: int
    f: Side
    g: Side


def longest_run(a: Word, b: Word) -> tuple[int, int, int]:
    """(start in a, start in b, length) of the longest common run; leftmost in a, then in b, on ties."""
    best = (0, 0, 0)
    for i in range(len(a)):
        for j in range(len(b)):
            n = 0
            while i + n < len(a) and j + n < len(b) and a[i + n] == b[j + n]:
                n += 1
            if n > best[2]:
                best = (i, j, n)
    return best


def align(a: Word, b: Word, m: int = MIN_RUN) -> Alignment | None:
    i, j, n = longest_run(a, b)
    return None if n < m else align_at(a, b, i, j, n)


def align_at(a: Word, b: Word, i: int, j: int, n: int) -> Alignment:
    """The residues of a and b around a given common run: n signs from position i of a and j of b."""
    ea, eb = i + n, j + n
    ba = bb = None
    if ea < len(a) and eb < len(b):
        ca, cb = a[ea], b[eb]
        if isinstance(ca, tuple) and isinstance(cb, tuple) and ca[0] and ca[0] == cb[0] and ca[1] != cb[1]:
            ba, bb, ea, eb = ca, cb, ea + 1, eb + 1
    last = _vowel(a[i + n - 1])
    return Alignment(n, Side(a[:i], ba, a[ea:], a[i], last), Side(b[:j], bb, b[eb:], a[i], last))


def maximal_runs(a: Word, b: Word, m: int = MIN_RUN) -> set[int]:
    """The positions of a inside any maximal common run with b of at least m signs."""
    covered: set[int] = set()
    prev = [0] * (len(b) + 1)
    for i in range(len(a)):
        row = [0] * (len(b) + 1)
        for j in range(len(b)):
            if a[i] == b[j]:
                row[j + 1] = prev[j] + 1
                if row[j + 1] >= m:
                    covered.update(range(i - row[j + 1] + 1, i + 1))
        prev = row
    return covered


@dataclass
class Free:
    """The free arm's inventory: the residues of a fold's training pairs (Paradigm B §5.2)."""
    prefixes: set = field(default_factory=set)
    suffixes: set = field(default_factory=set)

    def add(self, s: Side) -> None:
        self.prefixes.add(s.prefix)
        self.suffixes.add((s.boundary, s.suffix))

    def explains(self, s: Side) -> bool:
        """Both residues in the inventory; an empty residue always counts as in."""
        return (not s.prefix or s.prefix in self.prefixes) and (
            (s.boundary is None and not s.suffix) or (s.boundary, s.suffix) in self.suffixes)


class Pool:
    """Distinct forms and the documents each stands in. A fold is named by the documents it leaves out."""

    def __init__(self, tokens, m: int = MIN_RUN):
        self.m = m
        self._docs: dict[Word, set[str]] = {}
        self._counts: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
        for doc, form in tokens:
            self._docs.setdefault(form, set()).add(doc)
            self._counts[doc].update(form)
        self._order = {form: n for n, form in enumerate(self._docs)}
        self._by_pair: dict[tuple, list[Word]] = collections.defaultdict(list)
        for form in self._docs:
            for pair in set(zip(form, form[1:])):
                self._by_pair[pair].append(form)
        self._pairs: list[tuple[Word, Word, Alignment]] | None = None
        self._free: dict[frozenset[str], Free] = {}

    def docs(self, form: Word) -> frozenset[str]:
        return frozenset(self._docs.get(form, ()))

    def training(self, left_out: frozenset[str]) -> list[Word]:
        return [f for f, d in self._docs.items() if d - left_out]

    def _candidates(self, x: Word, left_out: frozenset[str]) -> list[Word]:
        """Training forms other than x that share two adjacent signs with it, in the pool's order."""
        found = {g for pair in set(zip(x, x[1:])) for g in self._by_pair.get(pair, ())
                 if g != x and self._docs[g] - left_out}
        return sorted(found, key=self._order.__getitem__)

    def partners(self, x: Word, left_out: frozenset[str]) -> list[tuple[Word, Alignment]]:
        out = []
        for g in self._candidates(x, left_out):
            al = align(x, g, self.m)
            if al is not None:
                out.append((g, al))
        return out

    def core(self, x: Word, left_out: frozenset[str]) -> frozenset[int]:
        covered: set[int] = set()
        for g in self._candidates(x, left_out):
            covered |= maximal_runs(x, g, self.m)
        return frozenset(covered)

    def unigram(self, left_out: frozenset[str]) -> tuple[list, list[int]]:
        """The signs of the training tokens and how often each stands, opaque signs included."""
        total: collections.Counter = collections.Counter()
        for doc, counts in self._counts.items():
            if doc not in left_out:
                total.update(counts)
        signs = sorted(total, key=repr)
        return signs, [total[s] for s in signs]

    def free(self, left_out: frozenset[str]) -> Free:
        if left_out in self._free:
            return self._free[left_out]
        if self._pairs is None:
            self._pairs = []
            for a in self._docs:
                for b in self._candidates(a, frozenset()):
                    if self._order[a] < self._order[b]:
                        al = align(a, b, self.m)
                        if al is not None:
                            self._pairs.append((a, b, al))
        inv = Free()
        for a, b, al in self._pairs:
            if self._docs[a] - left_out and self._docs[b] - left_out:
                inv.add(al.f)
                inv.add(al.g)
        self._free[left_out] = inv
        return inv
