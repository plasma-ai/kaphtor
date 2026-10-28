"""Hash-neighborhood matcher for arm lexical lookup.

``Arm``, ``GUTTURALS``, ``MAX_GUTTURAL_STRIP``, ``_devowel``, ``token_skeleton``,
``syllabic_signs``, and ``base_consonant_map`` are copied, with light adaptation
(imports repointed at the vendored ``phonetics``/``skeleton`` modules and the
package's own data layout), from:

    source: linear-a-decipherment/scripts/validation/blind_corpus_test.py
    source_sha256: 85d84c807e2e992e668b05d918ab11ab5d4889f565c1b3936156b56e33fbe823
    lines_copied: 112-148 (helpers), 235-292 (class Arm)
    copied: 2026-09-07

Extensions over the source for this package:

- ``Arm.__init__`` accepts ``disabled_pairs``: a collection of (a, b) phoneme
  pairs to strip from ``distances`` (checked both orders) before the cheap-
  substitution table is built, per INTERFACES.md "Transducer vs matcher: who
  owns which cost" — script-level neutralizations the transducer already
  charges must not also be charged by the matcher.
- ``Arm.best_matches_all(skel, budget)`` returns every hit at or under
  ``budget`` (not just the cheapest), deduplicated by ``ref``, sorted by cost.
  ``best_match`` (single-best, as in the source) is kept for parity/selftest use.

Attribution: di Mino.
"""
from __future__ import annotations

import itertools
import re
from collections import defaultdict
from typing import Iterable

from common import paths  # noqa: F401  (inserts vendor/ on sys.path as a side effect)

from phonetics import _tokenize_phonemes
from skeleton import SIGN_DECOMPOSITION, _lookup_sign

Entry = tuple[str, str, str, str | None, tuple[str, ...]]

MATCH_BUDGET = 0.3  # pre-registered primary threshold (raw weighted distance)
SENSITIVITY_BUDGET = 0.5  # pre-registered secondary threshold

# Mirrors phonetics.GUTTURAL_PHONEMES (NWS-relevant subset), as in the source.
GUTTURALS = ("ʔ", "ʿ", "ʾ", "h", "ḥ", "ḫ")
WEAK_RADICALS = ("y", "w")
MAX_GUTTURAL_STRIP = 3

# Unwritten-phoneme deletions are realised on the DB side of the index (a DB
# skeleton minus up to MAX_GUTTURAL_STRIP of these phonemes is indexed at the
# listed cost each) rather than as query-side insertions. The prices are the
# transducer's (data/transducer_rules.json: guttural_unwritten 0.1 cap 3,
# weak_radical_restore 0.1); parser.py asserts the two agree at load time, so
# the rule file stays the single price authority. Index-side deletion and
# query-side insertion reach the same DB skeleton at the same cost; only the
# enumeration size differs (35,974 query variants for a 6-phoneme residual
# with insertions enabled, versus a handful of dict lookups here).
DEFAULT_STRIP_COSTS: dict[str, float] = {**{g: 0.1 for g in GUTTURALS},
                                         **{w: 0.1 for w in WEAK_RADICALS}}

# Script-level neutralizations the transducer already prices (INTERFACES.md
# "Transducer vs matcher"). Disabled symmetrically in the matcher's distance
# table so a correspondence is never charged twice or at two different prices.
# ARM_DISABLED_PAIRS are the ones data/transducer_rules.json lists under
# _meta.matcher_disable_recommended (arm-scoped transducer rules that duplicate
# EGYPTIAN_DISTANCES / LUWIAN_DISTANCES entries); scoped so the Hurrian table's
# own p/f entry, which no transducer rule prices, is left alone.
DEFAULT_DISABLED_PAIRS: tuple[tuple[str, str], ...] = (
    ("t", "d"), ("k", "g"), ("p", "b"), ("s", "š"), ("t", "ṭ"),
    ("s", "ṣ"), ("z", "ṣ"), ("ṯ", "t"), ("ḏ", "d"),
)
ARM_DISABLED_PAIRS: dict[str, tuple[tuple[str, str], ...]] = {
    "egyptian": (("ꜣ", "ʾ"), ("ꜣ", "ʔ"), ("ꜥ", "ʿ"), ("j", "y"), ("f", "p")),
    "luwian": (("kw", "k"),),
}


def _devowel(form: str) -> tuple[str, ...]:
    """Consonantal skeleton of a romanized DB key, as canonical phoneme tuple."""
    vowels = set("aeiouāēīōūäëïöüăĕĭŏŭ")
    cons = "".join(ch for ch in form if ch.lower() not in vowels
                   and ch not in "*-_ ()[]0123456789.,'\"")
    return tuple(_tokenize_phonemes(cons))


def syllabic_signs(token: str) -> list[str]:
    """Leading run of resolvable syllabograms (drops fused ideogram tails like -OLIV)."""
    signs = []
    for comp in token.split("-"):
        if _lookup_sign(comp):
            signs.append(comp)
        else:
            break
    return signs


def token_skeleton(signs: list[str], cons_map: dict[str, str | None]) -> tuple[str, ...]:
    cons = []
    for s in signs:
        upper = s.upper().translate(str.maketrans("₂₃₄₅", "2345"))
        key = upper if upper in cons_map else re.sub(r"\d+$", "", upper)
        c = cons_map.get(key)
        if c:
            cons.append(c)
    return tuple(_tokenize_phonemes("".join(cons)))


def base_consonant_map() -> dict[str, str | None]:
    return {sign: decomp[0] for sign, decomp in SIGN_DECOMPOSITION.items()}


def _filter_disabled(
    distances: dict[tuple[str, str], float],
    disabled_pairs: Iterable[tuple[str, str]] | None,
) -> dict[tuple[str, str], float]:
    if not disabled_pairs:
        return dict(distances)
    disabled = set()
    for a, b in disabled_pairs:
        disabled.add((a, b))
        disabled.add((b, a))
    return {pair: cost for pair, cost in distances.items() if pair not in disabled}


class Arm:
    """One language arm: guttural-stripped DB index + cheap-substitution table."""

    def __init__(self, name: str, db: dict[tuple[str, ...], list[Entry]],
                 distances: dict[tuple[str, str], float],
                 disabled_pairs: Iterable[tuple[str, str]] | None = None,
                 strip_costs: dict[str, float] | None = None,
                 max_strip: int = MAX_GUTTURAL_STRIP):
        self.name = name
        self.db = db
        self.distances = _filter_disabled(distances, disabled_pairs)
        self.strip_costs = dict(DEFAULT_STRIP_COSTS if strip_costs is None else strip_costs)
        self.max_strip = max_strip
        # DB-side: stripped-variant index (unwritten gutturals / weak radicals
        # removed from the DB skeleton at strip_costs[phoneme] each, at most
        # max_strip deletions per skeleton); the cheapest route to each
        # stripped form is kept.
        self.index: dict[tuple[str, ...], list] = defaultdict(list)
        for skel, entries in db.items():
            strip_pos = [i for i, p in enumerate(skel) if p in self.strip_costs]
            seen: dict[tuple[str, ...], float] = {}
            for k in range(min(len(strip_pos), max_strip) + 1):
                for combo in itertools.combinations(strip_pos, k):
                    stripped = tuple(p for i, p in enumerate(skel) if i not in combo)
                    if not stripped:
                        continue
                    cost = sum(self.strip_costs[skel[i]] for i in combo)
                    prev = seen.get(stripped)
                    if prev is not None and prev <= cost:
                        continue
                    seen[stripped] = cost
            for stripped, cost in seen.items():
                self.index[stripped].append((cost, skel))
        # Query-side: cheap substitution partners (both orders), built to the
        # largest budget any caller uses; per-call budgets filter at generation.
        # The matcher generates at most double substitutions — a conservative
        # approximation of full DP (triple 0.1-subs totalling 0.3 are missed).
        self.cheap: dict[str, list[tuple[str, float]]] = defaultdict(list)
        max_budget = max(MATCH_BUDGET, SENSITIVITY_BUDGET)
        for (a, b), c in self.distances.items():
            if c <= max_budget:
                self.cheap[a].append((b, c))
                self.cheap[b].append((a, c))

    def _variants(self, skel: tuple[str, ...], budget: float):
        yield skel, 0.0
        n = len(skel)
        for i in range(n):
            for b, c in self.cheap.get(skel[i], ()):
                if c > budget:
                    continue
                v1 = skel[:i] + (b,) + skel[i + 1:]
                yield v1, c
                for j in range(i + 1, n):
                    for b2, c2 in self.cheap.get(skel[j], ()):
                        if c + c2 <= budget:
                            yield v1[:j] + (b2,) + v1[j + 1:], c + c2

    def best_match(self, skel: tuple[str, ...], budget: float = MATCH_BUDGET):
        """Return (cost, source, ref, meaning, role) or None."""
        best = None
        seen: dict[tuple[str, ...], float] = {}
        for variant, sub_cost in self._variants(skel, budget):
            prev = seen.get(variant)
            if prev is not None and prev <= sub_cost:
                continue
            seen[variant] = sub_cost
            for strip_cost, orig in self.index.get(variant, ()):
                total = sub_cost + strip_cost
                if total <= budget and (best is None or total < best[0]):
                    entry = self.db[orig][0]
                    best = (total, *entry)
        return best

    def best_matches_all(
        self, skel: tuple[str, ...], budget: float = MATCH_BUDGET,
    ) -> list[tuple[float, Entry]]:
        """Every DB hit at or under ``budget``, deduplicated by ``ref``, cheapest first."""
        seen_variant: dict[tuple[str, ...], float] = {}
        best_by_ref: dict[str, tuple[float, Entry]] = {}
        for variant, sub_cost in self._variants(skel, budget):
            prev = seen_variant.get(variant)
            if prev is not None and prev <= sub_cost:
                continue
            seen_variant[variant] = sub_cost
            for strip_cost, orig in self.index.get(variant, ()):
                total = sub_cost + strip_cost
                if total > budget:
                    continue
                for entry in self.db[orig]:
                    ref = entry[1]
                    prior = best_by_ref.get(ref)
                    if prior is None or total < prior[0]:
                        best_by_ref[ref] = (total, entry)
        return sorted(best_by_ref.values(), key=lambda pair: pair[0])
