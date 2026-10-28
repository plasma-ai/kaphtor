"""Shoresh (שֹׁרֶשׁ): is a Linear A sign group closer to a Semitic root than chance, and to which root?

The statistic, decoys, p-values and verdicts were pre-registered (§§1-4 and the §6 amendments, which bind where they
differ; tools/core/SHORESH.md says what each id fixes). This module implements the sound statistic and its null:

  d*(w)   min over root clusters, skeleton variants v and retrieved keys k of weighted_levenshtein(v, k) + penalty(v)
          (§1), with Shoresh's own table (A11: SEMITIC_DISTANCES plus k ↔ ḫ at 0.3), over every reading of a
          polyphonic sign (A11), over the keys retrieved within one class edit (A12).
  p_F     (1 + #{decoys with d* ≤ d*(w)}) / (1 + N_F) for family A (sign shuffle), B (position-matched fabrication,
          A3) and C (sign-value permutation). p_max = max over the families that count (A1: p_A counts only from 100
          distinct sign orders up).

A cluster is one semitic_roots Number: its PS and weak keys, its Analogues reflexes, and the contact lexemes that
join it (fk, or an exact sound link with gloss overlap; §8). Unjoined lexemes are never a cluster of their own
here. Onomastic lexemes count only with names=True (§1).

The competitor null (§2, A15) runs the same counting on the same decoys against competitors.py's Luwian,
Egyptian and Hurrian spaces when the engine is given them; it never touches the Semitic p or the verdict.

Each shown cluster carries its sound laws: the branches whose reflexes of the nearest PS
headword the Linear A spelling is consistent with, each reflex spelled as the script would spell it. They never touch
d*, p or the verdict.

POS (§3.2) gates verbal-template parses only. None of Shoresh's variants is one (the verb lens is outside d*), so the
POS condition holds vacuously; each cluster shows the POS it inherits from its joined contact lexemes.

The semantic gate (§3.1, A10, A18, A19) scores d*_sem over the clusters that fit the word's context and gates every
decoy by that same context; a control scores under the context of the word it was made from (context_of). It never
touches d*, p or the phonological verdict; CONVERGENT needs it, p_max < 0.01 and the competitor null.

Report-only: nothing here writes anywhere.

Attribution: di Mino
"""
from __future__ import annotations

import hashlib
import itertools
import math
import random
import re
import sys
import unicodedata
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field, replace
from functools import cache, lru_cache
from pathlib import Path
from typing import Any

try:
    from .corpus_utils import load_corpus
    from .phonetics import GUTTURAL_INSERT_COST, GUTTURAL_PHONEMES, SEMITIC_DISTANCES, _tokenize_phonemes
    from .root_index import RootIndex, _ro, shadow_key
    from .semantic_gate import Contexts, cluster_domains, fits
    from .semitic_root_schema import _correspondences
    from .shoresh_nulls import GEMINABLE_STOPS, fabricate, load_corpus_words, permuted_cons_map, position_tables
    from .skeleton import _SUBSCRIPT_MAP, SIGN_DECOMPOSITION, SIGN_STATUS, _lookup_sign, extract_skeleton, load_registry
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from tools.core.corpus_utils import load_corpus
    from tools.core.phonetics import GUTTURAL_INSERT_COST, GUTTURAL_PHONEMES, SEMITIC_DISTANCES, _tokenize_phonemes
    from tools.core.root_index import RootIndex, _ro, shadow_key
    from tools.core.semantic_gate import Contexts, cluster_domains, fits
    from tools.core.semitic_root_schema import _correspondences
    from tools.core.shoresh_nulls import (
        GEMINABLE_STOPS,
        fabricate,
        load_corpus_words,
        permuted_cons_map,
        position_tables,
    )
    from tools.core.skeleton import (
        _SUBSCRIPT_MAP,
        SIGN_DECOMPOSITION,
        SIGN_STATUS,
        _lookup_sign,
        extract_skeleton,
        load_registry,
    )

SEED = 20261016
DEFAULT_N = 1000
P_SIGNAL = 0.05             # §3 NO_SIGNAL at or above
P_CONVERGENT = 0.01         # §3 CONVERGENT below (with the gates)
MIN_ORDERS_FOR_A = 100      # A1
INFORMATIVE_MIN = 3         # §3 UNINFORMATIVE at two consonants or fewer
SATURATION_D = 0.3          # §3 a family-B decoy at d* ≤ 0.3 counts toward saturation
SATURATION_SHARE = 0.9      # §3 UNINFORMATIVE above this share
UNIQUENESS_SLACK = 0.05     # §1 k(d*): clusters within d* + 0.05
MAX_READINGS = 8            # polyphonic readings per word, primary first
FABRICATE_CALLS = 20        # family B redraws per decoy when the polyphonic-slot count does not match
FABRICATE_GIVE_UP = 25      # family B stops after this many failed decoys with none found
# A mixed block: Akkadian translation equivalents filed among cognates. Display flag only, never an exclusion.
AKKADIAN_EQUIVALENT_BLOCK = range(2700, 2793)

# A11: Shoresh's own table. SEMITIC_DISTANCES itself is never changed (cognate_search and its golden record).
SHORESH_DISTANCES: dict[tuple[str, str], float] = {**SEMITIC_DISTANCES, ("k", "ḫ"): 0.3}

_A_NUMBER = re.compile(r"A\d{3,}")      # Linear A sign numbers; _lookup_sign would strip them to the vowel A
_UNATTESTED = frozenset({"PS", "non_semitic"})     # key branches that are no Semitic branch (reconstruction, other family)
INF = math.inf
_EPS = 1e-9         # slack on a limit derived by subtraction; never decides a comparison on its own


class UnmappedSign(ValueError):
    """A sign with no decomposition. The word is never shortened to fit (A5)."""


# ---------------------------------------------------------------------------
# distance: weighted_levenshtein on pre-tokenised strings, with an optional cutoff
# ---------------------------------------------------------------------------

def _sub(a: str, b: str) -> float:
    if a == b:
        return 0.0
    return SHORESH_DISTANCES.get((a, b), SHORESH_DISTANCES.get((b, a), 1.0))


@cache
def _sub_cached(a: str, b: str) -> float:
    return _sub(a, b)


def _ins(t: str) -> float:
    return GUTTURAL_INSERT_COST if t in GUTTURAL_PHONEMES else 1.0


def _q(x: float) -> float:
    """A sum of costs on a 1e-9 grid, so 0.1 + 0.1 + 0.1 and 0.3 compare equal: §2 counts a decoy at d* as a tie.
    The costs are multiples of 0.05, so no two distinct sums meet on the grid."""
    return round(x, 9)


# The index's gutturals (root_index.GUTTURALS) in the engine's notation: x is ḫ, ʁ and γ are ġ.
_ENGINE_CANON = {"x": "ḫ", "ʁ": "ġ", "γ": "ġ"}


def letters(s: str) -> list[str]:
    """s in NFD, one string per letter: each base character with the combining marks after it."""
    out: list[str] = []
    for ch in unicodedata.normalize("NFD", s):
        if out and unicodedata.category(ch).startswith("M"):
            out[-1] += ch
        else:
            out.append(ch)
    return out


def letter_token(letter: str) -> str | None:
    """One letter (letters()) as the engine's token: subscript digits and other non-letters are None, x, ʁ and γ
    are read as the index reads them."""
    toks = [t for t in _tokenize_phonemes(letter) if t.isalpha()]
    return _ENGINE_CANON.get(toks[0], toks[0]) if toks else None


def phonemes(s: str) -> tuple[str, ...]:
    """s as the engine's tokens, one per letter: each NFD letter with its marks is tokenised alone, so no two
    letters merge (_tokenize_phonemes on a joined string reads k+w as kw, t+s as ṣ, and s+ḥ as š, NFD ḥ being h
    plus a mark). Subscript digits drop (Sabaic s₁ is s); x, ʁ and γ are read as the index reads them."""
    return tuple(t for t in map(letter_token, letters(s)) if t)


def levenshtein(t1: tuple[str, ...], t2: tuple[str, ...], sub, ins, cutoff: float = INF) -> float:
    """weighted_levenshtein's recurrence, in its order, on token tuples, with substitution cost sub(a, b), insertion
    cost ins(t) and deletion at 1.0. With a cutoff, returns INF as soon as every cell of a row exceeds it (no path
    can come back under it): the result is exact whenever it is ≤ cutoff."""
    m = len(t2)
    prev = [0.0] * (m + 1)
    for j in range(1, m + 1):
        prev[j] = prev[j - 1] + ins(t2[j - 1])
    for i in range(1, len(t1) + 1):
        a = t1[i - 1]
        cur = [prev[0] + 1.0] + [0.0] * m
        for j in range(1, m + 1):
            b = t2[j - 1]
            cur[j] = min(prev[j] + 1.0, cur[j - 1] + ins(b), prev[j - 1] + sub(a, b))
        if min(cur) > cutoff:
            return INF
        prev = cur
    return prev[m] if prev[m] <= cutoff else INF


def distance(t1: tuple[str, ...], t2: tuple[str, ...], cutoff: float = INF) -> float:
    """weighted_levenshtein(s1, s2, SHORESH_DISTANCES, guttural_transparent=True) on token tuples: identical values."""
    return levenshtein(t1, t2, _sub_cached, _ins, cutoff)


def alignment(t1: tuple[str, ...], t2: tuple[str, ...], sub=_sub_cached, ins=_ins) -> list[tuple[int | None, int | None]]:
    """One minimum-cost path of levenshtein(t1, t2, sub, ins) as index pairs: (i, j) substitutes, (i, None) deletes
    t1[i], (None, j) inserts t2[j]. Ties go to substitution, then deletion (display only; the cost is levenshtein's)."""
    n, m = len(t1), len(t2)
    table = [[0.0] * (m + 1) for _ in range(n + 1)]
    for j in range(1, m + 1):
        table[0][j] = table[0][j - 1] + ins(t2[j - 1])
    for i in range(1, n + 1):
        table[i][0] = table[i - 1][0] + 1.0
        for j in range(1, m + 1):
            table[i][j] = min(table[i - 1][j] + 1.0, table[i][j - 1] + ins(t2[j - 1]),
                              table[i - 1][j - 1] + sub(t1[i - 1], t2[j - 1]))
    path: list[tuple[int | None, int | None]] = []
    i, j = n, m
    while i or j:
        if i and j and table[i][j] == table[i - 1][j - 1] + sub(t1[i - 1], t2[j - 1]):
            i, j = i - 1, j - 1
            path.append((i, j))
        elif i and table[i][j] == table[i - 1][j] + 1.0:
            i -= 1
            path.append((i, None))
        else:
            j -= 1
            path.append((None, j))
    return path[::-1]


def _lower_bound(n: int, m: int, m_visible: int) -> float:
    """No edit path costs less: each skeleton token beyond the key's length is deleted at 1.0, and each
    non-guttural key token beyond the skeleton's length is inserted at 1.0."""
    return max(n - m, 0) + max(m_visible - n, 0)


# ---------------------------------------------------------------------------
# signs, readings, variants
# ---------------------------------------------------------------------------

def _canon(sign: str) -> str:
    return sign.upper().translate(_SUBSCRIPT_MAP)


_LINEAR_B_GRID = re.compile(r"[DJKMNPQRSTWZ]?[AEIOU]|RA2")    # sign names Linear B gives a CV value
# The tentative Linear B values of three signs Linear B leaves untransliterated, where the engine reads beyond them:
# *56 pa₃, *65 ju, *79 zu (ju and zu: Davis 2026, 174 n. 641). Melena reads *56 as pa₂, a labial sonorant (ᵐb), and
# *79 as wo₂ (Melena, The Untransliterated Syllabograms, §§5, 15).
LINEAR_B_VALUES: dict[str, tuple[str | None, str]] = {"PA3": ("p", "a"), "JU": ("y", "u"), "ZU": ("z", "u")}
# A21: signs that write their consonants before every vowel, as Old Babylonian PI writes wa, we, wi and wu
# (Huehnergard 2011, 69). ZU writes ṯ, ḏ and ṯ̣ so, and *305 writes ḏa beside it.
FULL_SERIES = ("ZU",)


def _table_key(sign: str) -> str:
    upper = _canon(sign)
    return upper if upper in SIGN_DECOMPOSITION else re.sub(r"\d+$", "", upper)


def _beyond_linear_b(sign: str) -> bool:
    """The value _lookup_sign reads for the sign is not its Linear B value and not resolved: listed in SIGN_STATUS,
    or, failing closed, a sign off the Linear B grid that SIGN_STATUS does not list."""
    key = _table_key(sign)
    status = SIGN_STATUS.get(key)
    return status != "resolved" if status else not _LINEAR_B_GRID.fullmatch(key)


def conventional_consonant_map() -> dict[str, str | None]:
    """Each sign's consonant as a conventional run reads it, the signs it leaves unmapped out (family C's base)."""
    out: dict[str, str | None] = {}
    for sign in SIGN_DECOMPOSITION:
        try:
            out[sign] = sign_decomposition(sign, conventional=True)[0]
        except UnmappedSign:
            continue
    return out


def sign_decomposition(sign: str, conventional: bool = False) -> tuple[str | None, str]:
    """(consonant or None, vowel), loud: a Linear A sign number (A303) or an unknown sign raises. With conventional,
    a sign whose value goes beyond Linear B, unless resolved, reads its Linear B value, and raises where Linear B
    gives none (A5)."""
    if _A_NUMBER.fullmatch(_canon(sign)):
        raise UnmappedSign(sign)
    decomp = _lookup_sign(sign)
    if decomp is not None and conventional and _beyond_linear_b(sign):
        decomp = LINEAR_B_VALUES.get(_table_key(sign))
    if decomp is None:
        raise UnmappedSign(sign)
    return decomp[0] or None, decomp[1]


@lru_cache(maxsize=1)
def _registry() -> dict:
    return load_registry()


def sign_options(sign: str, registry: dict | None = None,
                 conventional: bool = False) -> list[tuple[str | None, str]]:
    """The sign's readings that differ in consonant, primary first (QA → q, z; RA₂ → l, r). With conventional,
    Linear B values only: the alternates whose status is conventional (RA₂ → r), and no value beyond Linear B."""
    primary = sign_decomposition(sign, conventional)
    out = [primary]
    reg = _registry() if registry is None else registry
    upper = _canon(sign)
    data = reg.get(upper) or reg.get(re.sub(r"\d+$", "", upper))
    for r in (data or {}).get("readings", []):
        c = r.get("consonant")
        if conventional and r.get("status") != "conventional":
            continue
        if not r.get("is_primary") and c and c not in {o[0] for o in out}:
            out.append((c, primary[1]))
    return out


def readings(signs: list[list[tuple[str | None, str]]]) -> list[list[tuple[str | None, str]]]:
    """Every combination of per-sign options, primary first, at most MAX_READINGS. Over the cap, the combinations
    fewest steps down the signs' options are kept, ties broken by the signs and not their places, so a word and its
    shuffles keep the same readings (ZU-QA-RA₂ reads ZU as ḏ, and RA₂-QA-ZU reads RA₂ as r)."""
    combos = itertools.product(*signs)
    if math.prod(len(o) for o in signs) <= MAX_READINGS:
        return [list(r) for r in combos]

    def rank(r: tuple) -> tuple:
        steps = [(str(o), o.index(c)) for o, c in zip(signs, r)]     # a sign is its options, not its primary
        return sum(i for _, i in steps), sorted(s for s in steps if s[1])
    return [list(r) for r in sorted(combos, key=rank)[:MAX_READINGS]]


def skeleton_of(cv: list[tuple[str | None, str]]) -> str:
    return "".join(c for c, _ in cv if c)


@dataclass(frozen=True)
class Variant:
    tokens: tuple[str, ...]
    penalty: float
    rule: str
    reading: int        # index into the word's readings; 0 is the primary reading


def morph_variants(toks: tuple[str, ...], cv: list[tuple[str | None, str]]) -> list[tuple[tuple[str, ...], float, str]]:
    """cognate_search._generate_morphophonological_skeletons's rules (§1), in its order and with its penalties, on
    the skeleton's tokens: the shared generator tokenises the joined skeleton, which merges k+w and t+s, and so
    loses or misplaces its rules on such words. toks holds one token per consonant sign of cv."""
    out = [(toks, 0.0, "surface")]
    if not cv:
        return out
    if cv[0][0] is None and len(toks) >= 2:
        out.append((("n",) + toks, 0.15, "i_nun_assimilation"))
    if len(toks) >= 3 and toks[-1] in ("t", "s", "n"):
        out.append((toks[:-1], 0.20, "iii_weak_suffix_strip"))
    if len(toks) >= 2 and toks[-1] != "n":
        out.append((toks + ("n",), 0.20, "final_n_loss_restoration"))
    seen = {t for t, _, _ in out}
    k = 0
    for i, (c, v) in enumerate(cv):
        if c is None:
            continue
        if i + 1 < len(cv) and (c, v) == cv[i + 1] and c in GEMINABLE_STOPS and k + 1 < len(toks):
            for variant, penalty, rule in ((toks[:k] + ("n",) + toks[k + 1:], 0.15, "geminate_nun_restoration"),
                                           (toks[:k] + toks[k + 1:], 0.25, "degemination")):
                if variant not in seen and (rule != "degemination" or len(variant) >= 2):
                    out.append((variant, penalty, rule))
                    seen.add(variant)
        k += 1
    return out


def variants(word_readings: list[list[tuple[str | None, str]]], transliteration: str = "") -> list[Variant]:
    """The morphophonological variants (§1) of every reading, cheapest penalty per skeleton (transliteration is
    kept for callers; the rules read the signs)."""
    best: dict[tuple[str, ...], Variant] = {}
    for ri, cv in enumerate(word_readings):
        for toks, penalty, rule in morph_variants(phonemes(skeleton_of(cv)), cv):
            if toks and (toks not in best or penalty < best[toks].penalty):
                best[toks] = Variant(toks, penalty, rule, ri)
    return sorted(best.values(), key=lambda v: (v.penalty, v.reading, v.tokens))


def word_signs(word: str) -> list[str]:
    return [s for s in word.split("-") if s]


def _skeleton_tokens(word: str) -> tuple[str, ...]:
    """The primary skeleton's tokens as fabricate counts them for family B: extract_skeleton, one per letter."""
    return phonemes(extract_skeleton(word))


def written_consonants(registry: dict, conventional: bool = False) -> frozenset[str]:
    """Every consonant some sign's reading writes: the script's inventory (with conventional, Linear B values)."""
    out: set[str] = set()
    for sign in registry:
        try:
            opts = sign_options(sign, registry, conventional)
        except UnmappedSign:
            continue
        out.update(t for c, _ in opts if c for t in phonemes(c))
    return frozenset(out)


# ---------------------------------------------------------------------------
# sound laws: which branches' reflexes the spelling is consistent with (report-only)
# ---------------------------------------------------------------------------

def spelled(c: str, written: frozenset[str], sub=_sub) -> str | None:
    """How the script spells consonant c: itself if written, else its cheapest substitute under sub, then its
    shadow class (A9's series rule, root_match_checks.series_consonant). A guttural with no substitute under 1.0
    goes unwritten (None)."""
    if c in written:
        return c
    cls = shadow_key((c,))[0]
    best = min(written, key=lambda x: (sub(c, x), shadow_key((x,))[0] != cls, x))
    return None if c in GUTTURAL_PHONEMES and sub(c, best) >= 1.0 else best


def _reflex_token(alternant: str) -> str | None:
    """A table reflex in the engine's notation: Ø is loss, subscript digits drop (Sabaic s₁), one token or None."""
    if alternant == "Ø":
        return None
    toks = phonemes(alternant)
    return toks[0] if len(toks) == 1 else None


def sound_laws(la: tuple[str, ...], radicals: tuple[str, ...], table: dict[str, Any],
               written: frozenset[str], sub=_sub) -> dict[str, Any]:
    """The branches a match to a PS headword is consistent with, through the script's spelling
    (report-only, never in d*, p or the verdict). la aligns with the headword's radicals on Shoresh's
    cost. For each aligned radical, each branch's reflex (Huehnergard Table 3.2, forward) is spelled as the script
    would spell it (spelled); a branch is consistent where that equals the Linear A consonant. A radical is
    diagnostic only when some branches are consistent and some are not; one where every branch is consistent says
    nothing about the script's choice, one where none is, unexplained. The profile is the branches consistent at
    every diagnostic radical (None without one). Insertions, deletions and Linear A consonants the script does not
    write (a restored guttural, a variant's phoneme) are skipped. Geers' law is not checked."""
    owner = [k for k, r in enumerate(radicals) for _ in phonemes(r)]
    toks = tuple(t for r in radicals for t in phonemes(r))
    forward = {unicodedata.normalize("NFC", k): v for k, v in table["forward"].items()}
    branches = table["branches"]
    rows: list[dict[str, Any]] = []
    profile: list[str] | None = None
    for i, j in alignment(la, toks):
        if i is None or j is None or la[i] not in written:
            continue
        r = unicodedata.normalize("NFC", radicals[owner[j]])
        cells = forward.get("*" + r)
        row: dict[str, Any] = {"radical": owner[j] + 1, "ps": "*" + r, "la": la[i]}
        if cells is None:
            rows.append({**row, "status": "not_in_table"})
            continue
        consistent = [b for b in branches if b in cells and la[i] in
                      {spelled(t, written, sub) for t in map(_reflex_token, cells[b]["alternants"]) if t}]
        status = ("unexplained" if not consistent else
                  "not_diagnostic" if len(consistent) == sum(b in cells for b in branches) else "diagnostic")
        rows.append({**row, "status": status, "consistent": consistent,
                     "uncertain": [b for b in consistent if cells[b].get("uncertain")]})
        if status == "diagnostic":
            profile = consistent if profile is None else [b for b in profile if b in consistent]
    return {"radicals": "-".join(radicals), "positions": rows, "profile": profile}


# ---------------------------------------------------------------------------
# the index, as Shoresh reads it
# ---------------------------------------------------------------------------

def joined_clusters(index: RootIndex, lexeme_id: str) -> tuple[str, ...]:
    """The Numbers a lexeme joins (§8): fk, or an exact sound link with gloss overlap."""
    return tuple(sorted(n for n, basis, gloss in index.links.get(lexeme_id, ())
                        if basis == "fk" or (basis == "root_key_exact" and gloss)))


def semitic_specific(p_max: float, competitor_ps: Iterable[float | None]) -> bool:
    """§2: the Semitic p_max is a signal and no competitor's is (each at or above 0.05, none missing)."""
    return p_max < P_SIGNAL and all(c is not None and c >= P_SIGNAL for c in competitor_ps)


def verdict_of(consonants: int, saturation: float | None, p_max: float | None, p_max_sem: float | None,
               specific: bool | None) -> str:
    """§3. CONVERGENT needs p_max < 0.01, the gated p_max < 0.01 (A10, A18) and the competitor null run with no
    competitor at a signal (specific True); POS holds vacuously (§3.2). Without any of them, no CONVERGENT."""
    if consonants < INFORMATIVE_MIN or (saturation is not None and saturation > SATURATION_SHARE):
        return "UNINFORMATIVE"
    if p_max is None or p_max >= P_SIGNAL:
        return "NO_SIGNAL"
    if p_max < P_CONVERGENT and p_max_sem is not None and p_max_sem < P_CONVERGENT and specific is True:
        return "CONVERGENT"
    return "PHONOLOGICAL_ONLY"


@dataclass
class _Entry:
    tokens: tuple[str, ...]
    visible: int
    clusters: frozenset[str]


@dataclass
class ClusterHit:
    number: str
    distance: float
    variant_rule: str
    reading: int
    key_kind: str
    key_language: str
    key_form: str
    branches: tuple[str, ...]
    flags: tuple[str, ...] = ()
    gloss_free: tuple[str, ...] = ()     # branches from the record's own keys and fk-joined lexemes (A12)
    sound_laws: dict[str, Any] | None = None     # sound_laws() against the nearest PS headword; None: not computed
    pos: tuple[str, ...] = ()            # §3.2: inherited from the joined contact lexemes (display only)


@dataclass
class FamilyResult:
    family: str
    n: int
    below: int          # decoys with d* < d*(w)
    tied: int           # decoys with d* = d*(w)
    p: float
    in_p_max: bool
    note: str = ""
    orders: int | None = None

    def p_randomised(self, u: float) -> float:
        """A8: (#{d < d*} + U · (#{d = d*} + 1)) / (N + 1), for the calibration check."""
        return (self.below + u * (self.tied + 1)) / (self.n + 1)


@dataclass
class Result:
    word: str
    skeleton: str
    consonants: int
    d_star: float
    best: ClusterHit | None
    clusters: list[ClusterHit]
    uniqueness: int
    families: dict[str, FamilyResult]
    p_max: float | None
    deciding_family: str | None
    saturation: float | None
    verdict: str
    notes: list[str] = field(default_factory=list)
    breadth: dict[str, Any] = field(default_factory=dict)
    competitors: dict[str, dict[str, Any]] = field(default_factory=dict)
    competitor_margin: float | None = None      # lowest competitor p_max minus the Semitic p_max
    semitic_specific: bool | None = None        # Semitic p_max < 0.05 and every competitor p_max ≥ 0.05
    semantic: dict[str, Any] = field(default_factory=dict)   # the gate (§3.1, A10, A18): context, d*_sem, its p

    def to_json(self) -> dict[str, Any]:
        def hit(h: ClusterHit | None) -> dict[str, Any] | None:
            return None if h is None else {**h.__dict__, "distance": _num(h.distance)}
        return {
            "word": self.word, "skeleton": self.skeleton, "consonants": self.consonants,
            "d_star": _num(self.d_star), "best": hit(self.best), "clusters": [hit(c) for c in self.clusters],
            "uniqueness": self.uniqueness, "breadth": self.breadth,
            "families": {k: {**f.__dict__, "p": round(f.p, 6)} for k, f in self.families.items()},
            "p_max": self.p_max, "deciding_family": self.deciding_family, "saturation": self.saturation,
            "verdict": self.verdict, "notes": self.notes, "competitors": self.competitors,
            "competitor_margin": self.competitor_margin, "semitic_specific": self.semitic_specific,
            "semantic": self.semantic, "footer": "Enters at SPECULATIVE.",
        }


def _num(x: float) -> float | None:
    return None if x == INF else round(x, 6)


def _rng(seed: int, word: str, family: str) -> random.Random:
    """Per-word, per-family stream (§2): sha256(seed ‖ word ‖ family), independent of batch order."""
    digest = hashlib.sha256(f"{seed}\x00{word}\x00{family}".encode()).digest()
    return random.Random(int.from_bytes(digest[:8], "big"))


def bh_q(pvalues: list[float | None]) -> list[float | None]:
    """Benjamini–Hochberg q over p_max for a batch (§2); a word with no p_max gets none and is not counted."""
    tested = sorted((p, i) for i, p in enumerate(pvalues) if p is not None)
    m = len(tested)
    out: list[float | None] = [None] * len(pvalues)
    running = 1.0
    for rank in range(m, 0, -1):
        p, i = tested[rank - 1]
        running = min(running, p * m / rank)
        out[i] = running
    return out


def d_star_over(min_distance, vs: list[Variant], cutoff: float = INF) -> float:
    """min over variants of min_distance + penalty, exact when ≤ cutoff, else INF. Every comparison is made on the
    sum distance + penalty on the _q grid, the value the real word's d* is made of, so a decoy that ties it is
    counted as a tie however its sum was reached (the per-variant limit carries _EPS slack against the
    subtraction's rounding)."""
    best = INF
    for v in vs:
        limit = min(best, cutoff) - v.penalty + _EPS
        if limit < 0:
            continue
        d = _q(min_distance(v.tokens, limit) + v.penalty)
        best = min(best, d)
    return best if best <= cutoff else INF


def distinct_orders(signs: list[str]) -> int:
    counts = Counter(signs)
    out = math.factorial(len(signs))
    for c in counts.values():
        out //= math.factorial(c)
    return out


class Shoresh:
    """The sound statistic and its null over one RootIndex (loaded with lexemes, so clusters can join them)."""

    def __init__(self, index: RootIndex, *, names: bool = False, exclude: Iterable[str] = (),
                 corpus_words: list[str] | None = None, registry: dict | None = None,
                 competitors: Iterable[Any] = (), correspondences: dict[str, Any] | None = None,
                 contexts: Contexts | None = None, conventional: bool = False):
        """competitors: competitors.CompetitorSpace objects (§2), queried on the real word's own decoys.
        correspondences: the sound-law table (default data/semitic-roots/semitic_correspondences.json). contexts: the
        attested contexts of the semantic gate (A18; default: data/linear-a/corpus.json, read on first use).
        conventional: Linear B values only (sign_options), for the real word and its decoys; a word with a sign
        Linear B gives no value is unmapped (A5), and family B draws no such sign."""
        self.index = index
        self.conventional = conventional
        self._contexts = contexts
        self._cluster_domains: dict[str, frozenset[str]] | None = None
        self.competitors = list(competitors)
        self._sound_table = correspondences
        self._written: frozenset[str] | None = None
        self._ps_keys: dict[str, list] = {}       # Number → its PS headword keys (sound laws)
        self.names = names
        self.exclude = frozenset(exclude)
        self.registry = _registry() if registry is None else registry
        self._corpus_words = corpus_words
        self._tables: dict | None = None
        entries: dict[tuple[str, ...], _Entry] = {}
        self._entry_of: dict[int, _Entry] = {}
        self._keys_of: dict[int, list] = {}      # id(entry) → the KeyRows behind it, for display
        self._branches: dict[str, set[str]] = {}
        self._branches_free: dict[str, set[str]] = {}
        for key in index.keys:
            if key.kind == "ps" and key.number is not None:
                self._ps_keys.setdefault(key.number, []).append(key)
            clusters = self._key_clusters(key)
            if not clusters:
                continue
            toks = tuple(t for r in key.radicals for t in phonemes(r))
            if not toks:
                continue
            e = entries.get(toks)
            if e is None:
                e = entries[toks] = _Entry(toks, sum(t not in GUTTURAL_PHONEMES for t in toks), frozenset())
            e.clusters = e.clusters | clusters
            self._entry_of[id(key)] = e
            self._keys_of.setdefault(id(e), []).append(key)
            if key.branch and key.branch not in _UNATTESTED:
                for n in clusters:
                    self._branches.setdefault(n, set()).add(key.branch)
                for n in clusters if key.number is not None else clusters & self._fk_clusters(key):
                    self._branches_free.setdefault(n, set()).add(key.branch)
        self._pos: dict[str, set[str]] = {}       # §3.2: Number → the POS of the lexemes that join it
        for lid in index.links:
            meta = index.lexemes.get(lid, {})
            if meta.get("pos") and not (meta.get("onomastic") and not self.names):
                for n in joined_clusters(index, lid):
                    self._pos.setdefault(n, set()).add(meta["pos"])
        self._shadow_memo: dict[tuple[str, int], list[_Entry]] = {}
        self._min_memo: dict[tuple[str, ...], tuple[float, float]] = {}   # tokens → (value, exact up to)
        self._shapes: dict[tuple[int, int], list[_Entry]] | None = None  # brute force only

    def _key_clusters(self, key) -> frozenset[str]:
        if key.number is not None:
            nums = (key.number,)
        else:
            meta = self.index.lexemes.get(key.lexeme_id or "", {})
            if meta.get("onomastic") and not self.names:
                return frozenset()
            nums = joined_clusters(self.index, key.lexeme_id or "")
        return frozenset(n for n in nums if n not in self.exclude)

    def _fk_clusters(self, key) -> frozenset[str]:
        return frozenset(n for n, basis, _ in self.index.links.get(key.lexeme_id or "", ()) if basis == "fk")

    # --- retrieval ---

    def _retrieve(self, toks: tuple[str, ...]) -> list[_Entry]:
        shadow, _ = shadow_key(toks)
        radius = 1 if len(shadow) >= 2 else 0
        memo_key = (shadow, radius)
        hit = self._shadow_memo.get(memo_key)
        if hit is None:
            seen: dict[int, _Entry] = {}
            for key in self.index.candidates(shadow, radius):
                e = self._entry_of.get(id(key))
                if e is not None:
                    seen[id(e)] = e
            hit = self._shadow_memo[memo_key] = sorted(seen.values(), key=lambda e: (len(e.tokens), e.tokens))
        return hit

    def min_distance(self, toks: tuple[str, ...], cutoff: float = INF) -> float:
        """The exact min over retrieved keys, on the _q grid, if it is ≤ cutoff, else INF (A12 retrieval)."""
        memo = self._min_memo.get(toks)
        if memo is not None:
            value, exact_to = memo
            if value < INF:                 # a found minimum is exact
                return value if value <= cutoff else INF
            if exact_to >= cutoff:          # nothing at or under exact_to, so nothing at or under cutoff
                return INF
        n = len(toks)
        best = INF
        for e in sorted(self._retrieve(toks), key=lambda e: _lower_bound(n, len(e.tokens), e.visible)):
            limit = min(best, cutoff) + _EPS
            if _lower_bound(n, len(e.tokens), e.visible) > limit:
                break
            d = _q(distance(toks, e.tokens, limit))
            if d < best:
                best = d
                if best == 0.0:
                    break
        self._min_memo[toks] = (best, cutoff if best == INF else INF)
        return best if best <= cutoff else INF

    def d_star(self, vs: list[Variant], cutoff: float = INF) -> float:
        return d_star_over(self.min_distance, vs, cutoff)

    def brute_force_d_star(self, vs: list[Variant], cutoff: float = INF) -> float:
        """A12's check: the same minimum over every eligible key, no retrieval; exact when ≤ cutoff, else INF.
        Entries are bucketed by (length, visible length), so the lower bound skips whole buckets."""
        if self._shapes is None:
            shapes: dict[tuple[int, int], list[_Entry]] = {}
            for e in {id(e): e for e in self._entry_of.values()}.values():
                shapes.setdefault((len(e.tokens), e.visible), []).append(e)
            self._shapes = shapes
        best = INF
        for v in vs:
            n = len(v.tokens)
            for (m, visible), bucket in self._shapes.items():
                limit = min(best, cutoff) - v.penalty + _EPS
                if _lower_bound(n, m, visible) > limit:
                    continue
                for e in bucket:
                    d = _q(distance(v.tokens, e.tokens, limit) + v.penalty)
                    if d < best:
                        best = d
                        limit = min(best, cutoff) - v.penalty + _EPS
        return best if best <= cutoff else INF

    def top_breadth(self, vs: list[Variant]) -> tuple[float, int, int]:
        """(exact d*, branch breadth, gloss-free breadth) of the broadest cluster at d* (A12, display only)."""
        best, tops = INF, []
        for v in vs:
            n = len(v.tokens)
            for e in self._retrieve(v.tokens):
                limit = best - v.penalty + _EPS
                if _lower_bound(n, len(e.tokens), e.visible) > limit:
                    continue
                d = _q(distance(v.tokens, e.tokens, limit) + v.penalty)
                if d == INF:
                    continue
                if d < best:
                    best, tops = d, [e]
                elif d == best:
                    tops.append(e)
        numbers = {n for e in tops for n in e.clusters}
        return (best, max((len(self._branches.get(n, ())) for n in numbers), default=0),
                max((len(self._branches_free.get(n, ())) for n in numbers), default=0))

    def _breadth(self, real: list[Variant], decoys: list[list[Variant]]) -> dict[str, Any]:
        _, gated, free = self.top_breadth(real)
        out: dict[str, Any] = {"branches": gated, "gloss_free": free}
        rows = [self.top_breadth(vs) for vs in decoys]
        rows = [(g, f) for d, g, f in rows if d != INF]
        if rows:
            out["decoys_B"] = {
                "n": len(rows),
                "mean": round(sum(g for g, _ in rows) / len(rows), 4),
                "share_ge": round(sum(g >= gated for g, _ in rows) / len(rows), 4),
                "mean_gloss_free": round(sum(f for _, f in rows) / len(rows), 4),
                "share_ge_gloss_free": round(sum(f >= free for _, f in rows) / len(rows), 4),
            }
        return out

    # --- the real word ---

    def word_readings(self, word: str) -> list[list[tuple[str | None, str]]]:
        return readings([sign_options(s, self.registry, self.conventional) for s in word_signs(word)])

    @property
    def written(self) -> frozenset[str]:
        """The sound laws' inventory, as A9 spells: the Linear B grid's consonants, and the consonants a FULL_SERIES
        sign writes before every vowel (A21: ZU's ṯ, ḏ and ẓ; a conventional run reads ZU as zu alone)."""
        if self._written is None:
            full = {t for s in FULL_SERIES if s in self.registry
                    for c, _ in sign_options(s, self.registry, self.conventional) if c for t in phonemes(c)}
            self._written = written_consonants(self.registry, conventional=True) | full
        return self._written

    def sound_laws(self, number: str, la: tuple[str, ...]) -> dict[str, Any] | None:
        """sound_laws() of la against the cluster's nearest PS headword key (weak keys are the engine's own
        constructs and are not used); None for a cluster with no PS headword."""
        heads = self._ps_keys.get(number)
        if not heads:
            return None
        if self._sound_table is None:
            self._sound_table = _correspondences()
        key = min(heads, key=lambda k: (distance(la, tuple(t for r in k.radicals for t in phonemes(r))),
                                        k.radicals))
        return {"headword": key.form, **sound_laws(la, key.radicals, self._sound_table, self.written)}

    def clusters(self, word: str, top: int = 10, laws: int | None = None) -> tuple[list[ClusterHit], list[Variant]]:
        """Every retrieved cluster with its best distance, ranked by distance, then branch breadth (display only;
        ties are counted by `uniqueness`, never broken for the statistic). The first `laws` hits (default: every
        hit returned) carry their sound laws."""
        rs = self.word_readings(word)
        vs = variants(rs, word)
        best: dict[str, tuple[float, Variant, _Entry]] = {}
        for v in vs:
            for e in self._retrieve(v.tokens):
                d = _q(distance(v.tokens, e.tokens) + v.penalty)
                for n in e.clusters:
                    if n not in best or d < best[n][0]:
                        best[n] = (d, v, e)
        hits = []
        for n, (d, v, e) in best.items():
            key = next(k for k in self._keys_of[id(e)] if n in self._key_clusters(k))
            flags = ("akkadian_equivalent_block",) if n.isdigit() and int(n) in AKKADIAN_EQUIVALENT_BLOCK else ()
            hits.append(ClusterHit(n, d, v.rule, v.reading, key.kind, key.language, key.form,
                                   tuple(sorted(self._branches.get(n, ()))), flags,
                                   tuple(sorted(self._branches_free.get(n, ()))),
                                   pos=tuple(sorted(self._pos.get(n, ())))))
        ranked = sorted(hits, key=lambda h: (h.distance, -len(h.branches), h.number))
        ranked = ranked[:top] if top else ranked
        for i in range(len(ranked) if laws is None else min(laws, len(ranked))):
            h = ranked[i]
            ranked[i] = replace(h, sound_laws=self.sound_laws(h.number, best[h.number][1].tokens))
        return ranked, vs

    # --- decoys ---

    def _reading_count(self, signs: list[str]) -> int:
        return math.prod(len(sign_options(s, self.registry, self.conventional)) for s in signs)

    def family_a(self, word: str, n: int, seed: int) -> tuple[list[list[str]], int]:
        signs = word_signs(word)
        orders = distinct_orders(signs)
        if orders == 1:                 # one sign repeated: no other order exists, sampled or enumerated
            return [], orders
        if orders - 1 <= n and len(signs) <= 8:
            perms = sorted({p for p in itertools.permutations(signs) if list(p) != signs})
            return [list(p) for p in perms], orders
        rng = _rng(seed, word, "A")
        out = []
        while len(out) < n:
            s = signs[:]
            rng.shuffle(s)
            if s != signs:
                out.append(s)
        return out, orders

    def _corpus(self) -> tuple[dict, set[str]]:
        if self._tables is None:
            if self._corpus_words is None:
                self._corpus_words = load_corpus_words()
            self._tables = position_tables(self._corpus_words)
        return self._tables, set(self._corpus_words or ())

    def family_b(self, word: str, n: int, seed: int) -> tuple[list[list[str]], int]:
        """A3: root_match_phase0.fabricate, with the word's number of readings kept (A11; ZU's four count as two
        two-way slots, A20). Returns the
        decoys and the number of draws that found no match (reported, never padded). A17: the OCP holds only if the
        word keeps it; a word with two identical consonants side by side gets decoys that may have them too. A
        conventional run checks the OCP on its own readings (fabricate's tokens are the engine's values)."""
        signs = word_signs(word)
        toks = phonemes(skeleton_of(self.word_readings(word)[0]))
        skel_len = len(toks)
        ocp = all(a != b for a, b in itertools.pairwise(toks))
        ocp_here = ocp and self.conventional
        count = self._reading_count(signs)
        tables, real = self._corpus()
        rng = _rng(seed, word, "B")
        out, gaps = [], 0
        for i in range(n):
            if gaps >= FABRICATE_GIVE_UP and not out:
                gaps += n - i           # the shape is not fabricable: report the whole family as gaps
                break
            for _ in range(FABRICATE_CALLS):
                fab = fabricate(rng, len(signs), skel_len, tables, real, tokens=_skeleton_tokens,
                                ocp=ocp and not self.conventional)
                if fab is None:
                    continue
                fs = word_signs(fab)
                try:
                    ftoks = phonemes(skeleton_of(self.word_readings(fab)[0]))
                    if self._reading_count(fs) == count and len(ftoks) == skel_len and \
                            (not ocp_here or all(a != b for a, b in itertools.pairwise(ftoks))):
                        out.append(fs)
                        break
                except UnmappedSign:
                    continue
            else:
                gaps += 1
        return out, gaps

    def family_c(self, word: str, n: int, seed: int) -> list[list[list[tuple[str | None, str]]]]:
        """§2 C: blind_corpus_test.permuted_cons_map applied to the same signs. A polyphonic sign keeps its number
        of readings; its alternates take the permuted consonant of another, randomly chosen consonant sign, redrawn
        until it differs from the sign's other readings (sign_options keeps only readings that differ). A
        conventional run permutes the Linear B values (conventional_consonant_map)."""
        signs = word_signs(word)
        opts = [sign_options(s, self.registry, self.conventional) for s in signs]
        rng = _rng(seed, word, "C")
        out = []
        base = conventional_consonant_map() if self.conventional else None
        for _ in range(n):
            cmap = permuted_cons_map(rng, base)
            consonant_signs = sorted(s for s, c in cmap.items() if c)
            per_sign = []
            for s, o in zip(signs, opts):
                c = self._permuted(cmap, s)
                alts: list[tuple[str | None, str]] = []
                have = {c}
                for _ in o[1:] if c else ():
                    a = cmap[rng.choice(consonant_signs)]
                    while a in have:
                        a = cmap[rng.choice(consonant_signs)]
                    have.add(a)
                    alts.append((a, o[0][1]))
                per_sign.append([(c, o[0][1])] + alts)
            out.append(readings(per_sign))
        return out

    @staticmethod
    def _permuted(cmap: dict[str, str | None], sign: str) -> str | None:
        upper = _canon(sign)
        if upper in cmap:
            return cmap[upper]
        base = re.sub(r"\d+$", "", upper)
        if base in cmap and base != upper and not _A_NUMBER.fullmatch(upper):
            return cmap[base]
        raise UnmappedSign(sign)

    # --- the query ---

    def _count(self, decoy_variants: Iterable[list[Variant]], d_star: float,
               saturation_at: float | None = None) -> tuple[int, int, int, int]:
        """(n, below, tied, at or under saturation_at)."""
        cutoff = d_star if saturation_at is None else max(d_star, saturation_at)
        n = below = tied = saturated = 0
        for vs in decoy_variants:
            d = self.d_star(vs, cutoff)
            n += 1
            if d < d_star:
                below += 1
            elif d == d_star:
                tied += 1
            if saturation_at is not None and d <= saturation_at:
                saturated += 1
        return n, below, tied, saturated

    def _variants_of(self, signs: list[str]) -> list[Variant]:
        w = "-".join(signs)
        return variants(self.word_readings(w), w)

    def unlinked_near(self, word: str, d: float) -> list[tuple[float, str]]:
        """§8 display only (A17): (distance, lexeme id) of each lexeme with a key and no link to any Number that
        lies within d of one of the word's variants, nearest first; onomastic ones only with names. Such a lexeme
        is never a cluster: it enters no d*, p or breadth."""
        if d == INF:
            return []
        best: dict[str, float] = {}
        for v in variants(self.word_readings(word), word):
            shadow, _ = shadow_key(v.tokens)
            for key in self.index.candidates(shadow, 1 if len(shadow) >= 2 else 0):
                lid = key.lexeme_id
                if key.number is not None or not lid or self.index.links.get(lid):
                    continue
                if self.index.lexemes.get(lid, {}).get("onomastic") and not self.names:
                    continue
                toks = tuple(t for r in key.radicals for t in phonemes(r))
                dd = _q(distance(v.tokens, toks, d - v.penalty + _EPS) + v.penalty)
                if dd <= d and dd < best.get(lid, INF):
                    best[lid] = dd
        return sorted((dd, lid) for lid, dd in best.items())

    # --- the semantic gate (§3.1, A10, A18) ---

    @staticmethod
    def _live_contexts() -> Contexts:
        return Contexts(load_corpus())

    @property
    def contexts(self) -> Contexts:
        if self._contexts is None:
            self._contexts = self._live_contexts()
        return self._contexts

    def _domains(self) -> dict[str, frozenset[str]]:
        """Number → its domains: the record's Meaning, read from the index file so it matches the keys loaded, and
        the glosses of its joined contact lexemes, onomastica always out (A18)."""
        if self._cluster_domains is None:
            conn = _ro(self.index.path)
            try:
                meanings = dict(conn.execute("SELECT number, meaning FROM roots"))
            finally:
                conn.close()
            glosses: dict[str, list[str]] = {}
            for lid in self.index.links:
                meta = self.index.lexemes.get(lid, {})
                if meta.get("onomastic") or not meta.get("meaning"):
                    continue
                for n in joined_clusters(self.index, lid):
                    glosses.setdefault(n, []).append(meta["meaning"])
            self._cluster_domains = cluster_domains(meanings, glosses)
        return self._cluster_domains

    def _gated(self, fit: frozenset[str]):
        """min_distance over the retrieved keys of fitting clusters only, exact and memoised per token tuple."""
        memo: dict[tuple[str, ...], float] = {}

        def gated(toks: tuple[str, ...], cutoff: float = INF) -> float:
            best = memo.get(toks)
            if best is None:
                n = len(toks)
                best = INF
                for e in sorted(self._retrieve(toks), key=lambda e: _lower_bound(n, len(e.tokens), e.visible)):
                    if not e.clusters & fit:
                        continue
                    if _lower_bound(n, len(e.tokens), e.visible) > best + _EPS:
                        break
                    d = _q(distance(toks, e.tokens, best + _EPS))
                    if d < best:
                        best = d
                        if best == 0.0:
                            break
                memo[toks] = best
            return best
        return gated

    def _semantic(self, word: str, vs: list[Variant], d: float, hits: list[ClusterHit],
                  decoys_of: dict[str, list[list[Variant]]], in_p_max: dict[str, bool],
                  context_of: str | None = None) -> dict[str, Any]:
        """d*_sem over the clusters that fit the word's context, and its p in every family that was drawn, each
        decoy gated by the real word's context (A10, A18; the §2 counting rules, A17 included). context_of: the
        word whose context a control inherits (§4, A19), in place of the queried spelling's own."""
        source = context_of or word
        attested, known = self.contexts.attestations(source)
        ctx = self.contexts.context(source)
        out: dict[str, Any] = {"context": sorted(ctx) if ctx else None, "context_of": context_of,
                               "attestations": attested, "known": known, "fitting": 0, "d_star": None,
                               "families": {}, "p_max": None, "deciding_family": None}
        if ctx is None or d == INF:
            return out
        domains = self._domains()
        fit = frozenset(n for n, doms in domains.items() if fits(doms, ctx))
        out["fitting"] = sum(h.number in fit for h in hits)
        gated = self._gated(fit)
        ds = d_star_over(gated, vs)
        if ds == INF:
            return out
        out["d_star"] = _num(ds)
        for k, decoys in decoys_of.items():
            nn = below = tied = 0
            for dvs in decoys:
                x = d_star_over(gated, dvs, ds)
                nn += 1
                if x < ds:
                    below += 1
                elif x == ds:
                    tied += 1
            out["families"][k] = {"n": nn, "below": below, "tied": tied, "p": round((1 + below + tied) / (1 + nn), 6),
                                  "in_p_max": in_p_max[k]}
        counted = {k: f["p"] for k, f in out["families"].items() if f["in_p_max"]}
        if counted:
            out["p_max"] = max(counted.values())
            out["deciding_family"] = max(counted, key=lambda k: (counted[k], k))
        return out

    def query(self, word: str, n: int = DEFAULT_N, seed: int = SEED, families: str = "ABC",
              top: int = 10, breadth_check: bool = True, competitors: bool = True,
              context_of: str | None = None) -> Result:
        """The word against its decoys. breadth_check adds A12's breadth line (an exact pass over family B);
        it never touches p or the verdict. competitors runs the competitor null (§2) on the very same decoys when
        the engine holds competitor spaces; it never touches the Semitic p or the verdict either. context_of:
        for a control, the word whose context the semantic gate uses (§4, A19)."""
        hits, vs = self.clusters(word, top=0, laws=top or None)
        rs0 = self.word_readings(word)[0]
        skel = skeleton_of(rs0)
        consonants = len(phonemes(skel))
        d = min((h.distance for h in hits), default=INF)
        run_comp = competitors and bool(self.competitors)
        notes = [("POS (§3.2): no verbal-template parse is used (the verb lens is outside d*), so the POS condition "
                  "holds vacuously; each cluster shows the POS its joined lexemes give it"),
                 ("sound laws: branches consistent through the script's spelling (Huehnergard Table 3.2), "
                  "report-only; Geers' law not checked")]
        if not run_comp:
            notes.append("competitor null (§2) not run")
            notes.append("CONVERGENT needs the competitor null (§2): unavailable in this run")
        total_readings = self._reading_count(word_signs(word))
        if total_readings > MAX_READINGS:
            notes.append(f"{total_readings} readings: the {MAX_READINGS} nearest the primary are queried (A17)")
        uniq =sum(1 for h in hits if h.distance <= d + UNIQUENESS_SLACK) if d != INF else 0
        fams: dict[str, FamilyResult] = {}
        saturation = None
        if d == INF:
            notes.append("no cluster retrieved within one class edit")
        breadth: dict[str, Any] = {}
        draw = d != INF or run_comp
        decoys_of: dict[str, list[list[Variant]]] = {}     # the decoys, drawn once, for both nulls
        in_p_max: dict[str, bool] = {}
        if "A" in families and draw:
            decoys, orders = self.family_a(word, n, seed)
            decoys_of["A"] = [self._variants_of(s) for s in decoys]
            in_p_max["A"] = orders >= MIN_ORDERS_FOR_A
            if d != INF:
                nn, below, tied, _ = self._count(decoys_of["A"], d)
                fams["A"] = FamilyResult("A", nn, below, tied, (1 + below + tied) / (1 + nn),
                                         orders >= MIN_ORDERS_FOR_A, orders=orders,
                                         note="" if orders >= MIN_ORDERS_FOR_A else
                                         f"{orders} sign orders: an order check, not in p_max (A1)")
        if ("B" in families and draw) or d != INF:     # A17: the saturation gate is checked whether or not B counts
            decoys, gaps = self.family_b(word, n, seed)
            b_variants = [self._variants_of(s) for s in decoys]
            if "B" in families:
                decoys_of["B"] = b_variants
                in_p_max["B"] = True
            if d != INF:
                nn, below, tied, sat = self._count(b_variants, d, saturation_at=SATURATION_D)
                saturation = sat / nn if nn else None
                if "B" not in families:
                    notes.append("family B drawn for the saturation gate only (A17), not in p_max")
                else:
                    fams["B"] = FamilyResult("B", nn, below, tied, (1 + below + tied) / (1 + nn), True,
                                             note=f"{gaps} draws found no matching decoy" if gaps else "")
                    if not nn:
                        notes.append("family B built no decoy: p_B = 1 enters p_max (A17)")
                    if breadth_check:
                        breadth = self._breadth(vs, b_variants)
        if "C" in families and draw:
            decoys_of["C"] = [variants(r, word) for r in self.family_c(word, n, seed)]
            in_p_max["C"] = True
            if d != INF:
                nn, below, tied, _ = self._count(decoys_of["C"], d)
                fams["C"] = FamilyResult("C", nn, below, tied, (1 + below + tied) / (1 + nn), True)
        counted = {k: f.p for k, f in fams.items() if f.in_p_max}     # A17: a family with no decoy counts at p = 1
        p_max = max(counted.values()) if counted else None
        deciding = max(counted, key=lambda k: (counted[k], k)) if counted else None
        comp: dict[str, dict[str, Any]] = {}
        margin = specific = None
        if run_comp:
            for space in self.competitors:
                comp[space.name] = self._competitor(space, vs, decoys_of, in_p_max)
            cps = [c["p_max"] for c in comp.values()]
            if p_max is not None and None not in cps:
                margin = round(min(cps) - p_max, 6)
            if p_max is not None:
                specific = semitic_specific(p_max, cps)
        semantic = self._semantic(word, vs, d, hits, decoys_of, in_p_max, context_of)
        source = f", inherited from {context_of} (A19)" if context_of else ""
        if semantic["context"] is None:
            notes.append(f"semantic gate (A10, A18): no semantic evidence ({semantic['known']} of "
                         f"{semantic['attestations']} attestations with a known context{source}); "
                         "never CONVERGENT (§3.1)")
        else:
            notes.append(f"semantic gate (A10, A18): context {', '.join(semantic['context'])} from "
                         f"{semantic['known']} of {semantic['attestations']} attestations{source}")
        verdict = verdict_of(consonants, saturation, p_max, semantic["p_max"], specific)
        if d != INF and not breadth:
            _, gated, free = self.top_breadth(vs)
            breadth = {"branches": gated, "gloss_free": free}
        return Result(word, skel, consonants, d, hits[0] if hits else None, hits[:top] if top else hits, uniq,
                      fams, p_max, deciding, saturation, verdict, notes, breadth, comp, margin, specific, semantic)

    @staticmethod
    def _competitor(space: Any, vs: list[Variant], decoys_of: dict[str, list[list[Variant]]],
                    in_p_max: dict[str, bool]) -> dict[str, Any]:
        """One competitor's d*, per-family p and p_max (§2): the Semitic counting rules on the same decoys."""
        d = space.d_star(vs)
        out: dict[str, Any] = {"d_star": _num(d), "nearest": space.nearest(vs) if d != INF else None,
                               "families": {}, "p_max": None, "deciding_family": None}
        if d == INF:
            return out
        for k, decoys in decoys_of.items():
            nn = below = tied = 0
            for dvs in decoys:
                c = space.classify(dvs, d)
                nn += 1
                if c < 0:
                    below += 1
                elif c == 0:
                    tied += 1
            out["families"][k] = {"n": nn, "below": below, "tied": tied, "p": round((1 + below + tied) / (1 + nn), 6),
                                  "in_p_max": in_p_max[k]}
        counted = {k: f["p"] for k, f in out["families"].items() if f["in_p_max"]}   # A17, as for the Semitic p
        if counted:
            out["p_max"] = max(counted.values())
            out["deciding_family"] = max(counted, key=lambda k: (counted[k], k))
        return out


# ---------------------------------------------------------------------------
# rebuild impact (§7.3, items 3 and 4): build_root_index.py --diff --impact / --preview, display only
# ---------------------------------------------------------------------------

def changed_tokens(old: Shoresh, new: Shoresh) -> tuple[set[tuple[str, ...]], set[tuple[str, ...]]]:
    """(changed, moved): the keys (as token tuples) whose clusters differ between two engines or whose root's
    domains differ (its Meaning or a joined gloss: the semantic gate, A19), and the other keys of a Number whose
    branches, gloss-free branches or POS differ. A changed key can move d*, the clusters at it, d*_sem and the
    verdict; a moved one only breadth and the order of tied clusters."""
    def table(engine: Shoresh) -> dict[tuple[str, ...], frozenset[str]]:
        return {e.tokens: e.clusters for e in engine._entry_of.values()}
    a, b = table(old), table(new)
    changed = {t for t in a.keys() | b.keys() if a.get(t) != b.get(t)}
    da, db = old._domains(), new._domains()
    redomained = {n for n in da.keys() | db.keys() if da.get(n, frozenset()) != db.get(n, frozenset())}
    changed |= {t for tab in (a, b) for t, clusters in tab.items() if clusters & redomained}
    numbers = {n for attr in ("_branches", "_branches_free", "_pos")
               for n in getattr(old, attr).keys() | getattr(new, attr).keys()
               if getattr(old, attr).get(n) != getattr(new, attr).get(n)}
    moved = {t for tab in (a, b) for t, clusters in tab.items() if clusters & numbers} - changed
    return changed, moved


def impact_words(old: Shoresh, new: Shoresh, words: Iterable[str]) -> tuple[list[str], list[str], list[str]]:
    """(impacted, breadth_only, unmapped). Impacted: a variant retrieves a changed key under either engine, or the
    two engines retrieve different keys for it (a key-logic change: same tokens, other stored shadows), so d*
    and the clusters at it can change. Breadth only: a variant retrieves a moved key and none changed. p,
    saturation and so the verdict can move for any word, since its decoys query the whole index (§7.3, A19).
    Retrieval only: no distance is computed. The caller sets gold-set words aside first."""
    changed, moved = changed_tokens(old, new)
    hit: list[str] = []
    breadth: list[str] = []
    unmapped: list[str] = []
    for w in words:
        try:
            vs = old._variants_of(word_signs(w))
        except UnmappedSign:
            unmapped.append(w)
            continue
        before = {e.tokens for v in vs for e in old._retrieve(v.tokens)}
        after = {e.tokens for v in vs for e in new._retrieve(v.tokens)}
        got = before | after
        if got & changed or before != after:
            hit.append(w)
        elif got & moved:
            breadth.append(w)
    return hit, breadth, unmapped
