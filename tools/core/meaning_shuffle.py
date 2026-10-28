"""Meaning-shuffle test: the corpus-level companion to Shoresh (Baxter & Manaster Ramer 1999; Kessler 2001).

Each anchored Linear A word is paired with its context (the domains of its adjacent logogram, or its document type:
semantic_gate). D[i][j] is word i's best distance to a root whose domains fit context j. The statistic is computed
on the real pairing and on N pairings with the contexts shuffled among the words, the multiset of contexts kept
(and, given strata, shuffled only inside each stratum). A language related to the words' language pairs words with
roots of their own meaning more often than chance. Every pairing searches the same lexicon, so a density common to
all words cancels; a context's breadth does not when it goes with the words' shape (a broad context fits more
roots, and helps most the short words with many near keys). Strata by length or by what family B keeps of a word
(fine_strata), and the calibration run on fabricated words of each slot's shape with nothing planted (simulate,
k = 0), measure that. D is computed once and every permutation re-indexes it.

Report-only: no data file is read or written here; tools/linear_a/validation/meaning_shuffle.py is the command.

Attribution: di Mino
"""
from __future__ import annotations

import json
import math
import random
import statistics
import sys
from collections import Counter
from collections.abc import Callable, Hashable, Iterable, Sequence
from pathlib import Path

try:
    from . import root_match as rm
    from .competitors import CompetitorSpace
    from .semantic_gate import Contexts, fits, tagger
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from tools.core import root_match as rm
    from tools.core.competitors import CompetitorSpace
    from tools.core.semantic_gate import Contexts, fits, tagger

INF = rm.INF
Context = frozenset[str]
Distance = Callable[[str, Context], float]
MAX_SHAPE = 5          # sign counts of 5 or more share a shape


# --- the words and their contexts ---

def shape(word: str) -> int:
    """A word's sign count, 5 standing for 5 or more: the length stratum, and the plant key's length."""
    return min(len(word.split("-")), MAX_SHAPE)


def fine_key(engine: rm.Shoresh, word: str) -> tuple[int, int, int]:
    """A word's (shape, skeleton length, reading count), what family B keeps of it (A3, A11)."""
    return (shape(word), len(rm.phonemes(rm.skeleton_of(engine.word_readings(word)[0]))),
            engine._reading_count(rm.word_signs(word)))


def fine_strata(keys: Sequence[tuple[int, int, int]]) -> list[str]:
    """The fine strata, one per fine_key. A stratum of one word cannot permute, so it falls back to its shape."""
    n = Counter(keys)
    return [f"{s}|{k}|{r}" if n[(s, k, r)] > 1 else str(s) for s, k, r in keys]


def check_corpus(corpus: object) -> None:
    """The shape Contexts reads: document id → document, its transliteratedWords a list of strings; TypeError if not."""
    if not isinstance(corpus, dict):
        raise TypeError("the corpus is not an object of documents")
    for k, doc in corpus.items():
        if not isinstance(doc, dict):
            raise TypeError(f"document {k} is not an object")
        words = doc.get("transliteratedWords", [])
        if not isinstance(words, list) or not all(isinstance(w, str) for w in words):
            raise TypeError(f"document {k}: transliteratedWords is not a list of strings")


def anchored(corpus: dict[str, dict], source: str = "logogram") -> dict[str, Context]:
    """Word (canonical sign-group spelling) → its context. source "logogram": attestations next to a mapped logogram
    only; "all": the document type counts too, as in the Shoresh gate (A18). Words with no known context are out."""
    if source not in ("logogram", "all"):
        raise ValueError(f"source {source!r}: logogram or all")
    if source == "logogram":
        corpus = {k: {**doc, "support": ""} for k, doc in corpus.items()}      # "" maps to no document context
    ctx = Contexts(corpus)
    out: dict[str, Context] = {}
    for key in ctx._of:                         # the canonical keys Contexts holds
        word = "-".join(key)
        c = ctx.context(word)
        if c:
            out[word] = c
    return out


# --- the distance table ---

def context_matrix(words: Sequence[str], contexts: Sequence[Context], dist: Distance) -> list[list[float]]:
    """D[i][j] = dist(words[i], contexts[j])."""
    return [[dist(w, c) for c in contexts] for w in words]


# --- statistics: larger is stronger evidence ---

def t_count(D: Sequence[Sequence[float]], assign: Sequence[int], tau: float) -> int:
    """Words within tau of a root of their assigned context (Baxter & Manaster Ramer's count)."""
    return sum(D[i][a] <= tau + rm._EPS for i, a in enumerate(assign))


def t_rank(D: Sequence[Sequence[float]], assign: Sequence[int]) -> float:
    """Kessler's own-meaning advantage, summed: per word, the share of the other contexts its assigned one beats,
    a tie counting half. A word as near to every context (or to none) scores 0.5 whatever its pairing."""
    total = 0.0
    for i, a in enumerate(assign):
        row, own = D[i], D[i][a]
        others = [x for j, x in enumerate(row) if j != a]
        if not others:
            continue
        total += (sum(x > own for x in others) + 0.5 * sum(x == own for x in others)) / len(others)
    return total


def t_cap(D: Sequence[Sequence[float]], assign: Sequence[int], cap: float) -> float:
    """Minus the sum of each word's distance to its assigned context, capped at cap: a near match counts by how near
    it is, and a word with none (INF) costs cap whatever its pairing."""
    return -sum(min(D[i][a], cap) for i, a in enumerate(assign))


# --- the null ---

def permutations(assign: Sequence[int], n: int, seed: int,
                 strata: Sequence[object] | None = None) -> Iterable[list[int]]:
    """n shuffles of assign, each keeping its multiset; with strata, labels move only among words of one stratum."""
    rng = random.Random(seed)
    groups: dict[object, list[int]] = {}
    for i in range(len(assign)):
        groups.setdefault(strata[i] if strata is not None else None, []).append(i)
    for _ in range(n):
        out = list(assign)
        for idx in groups.values():
            labels = [assign[i] for i in idx]
            rng.shuffle(labels)
            for i, lab in zip(idx, labels):
                out[i] = lab
        yield out


def p_value(observed: float, null: Sequence[float]) -> float:
    """(1 + #{null ≥ observed}) / (1 + N): one-sided, the observed pairing counted among the permutations."""
    return (1 + sum(x >= observed - 1e-12 for x in null)) / (1 + len(null))


def shuffle_test(D: Sequence[Sequence[float]], assign: Sequence[int], stat: Callable[[Sequence[Sequence[float]],
                 Sequence[int]], float], n: int, seed: int, strata: Sequence[object] | None = None) -> dict:
    observed = stat(D, assign)
    null = [stat(D, perm) for perm in permutations(assign, n, seed, strata)]
    return {"observed": observed, "p": round(p_value(observed, null), 6), "n": n, "seed": seed,
            "null_mean": round(statistics.fmean(null), 6) if null else None,
            "null_sd": round(statistics.pstdev(null), 6) if null else None}


# --- additive scores: every statistic sums one value per word, so a row's scores are computed once ---

def rank_row(row: Sequence[float]) -> list[float]:
    """t_rank's term for one word under each possible context."""
    return [t_rank([row], [a]) for a in range(len(row))]


def count_row(row: Sequence[float], tau: float) -> list[float]:
    """t_count's term for one word under each possible context."""
    return [1.0 if x <= tau + rm._EPS else 0.0 for x in row]


def cap_row(row: Sequence[float], cap: float) -> list[float]:
    """t_cap's term for one word under each possible context."""
    return [-min(x, cap) for x in row]


def _at(row: Sequence[float], j: int) -> float:
    return row[j]


def null_draws(sizes: Sequence[int], runs: int, rng: random.Random) -> list[list[int]]:
    """Each run's decoy for every slot (sizes: each slot's pool). A slot walks a shuffled order of its pool, so no
    decoy repeats before the pool is spent; each further pass is shuffled anew, so reuse is even."""
    if any(n < 1 for n in sizes):
        raise ValueError("a slot's null pool is empty")
    cols = []
    for n in sizes:
        col: list[int] = []
        while len(col) < runs:
            order = list(range(n))
            rng.shuffle(order)
            col += order
        cols.append(col[:runs])
    return [[c[r] for c in cols] for r in range(runs)]


def simulate(slot_ctx: Sequence[int], null_pool: Sequence[Sequence[Sequence[float]]],
             plant_pool: dict[Hashable, Sequence[Sequence[float]]], k: int, runs: int, n_perm: int, seed: int,
             scorers: dict[str, Callable[[Sequence[float]], list[float]]], alpha: float = 0.05,
             plant_of: Sequence[Hashable] | None = None, strata: Sequence[object] | None = None,
             keep_p: bool = False, plant_ids: dict[Hashable, Sequence[Hashable]] | None = None,
             fresh_null: bool = False) -> dict[str, dict]:
    """Power by simulation. Each run gives every slot a row from its own null pool (fabricated words of that slot's
    shape), then up to k slots, taken in random order among those whose plant key has plants, a planted word's row;
    the contexts are shuffled n_perm times (inside each stratum, given strata). A slot's plant key is its context, or
    plant_of[i] (its context and length, so plants keep the slot's shape). A word list holds each word once, so a
    plant fills at most one slot a run: plant_ids names each plant (a word in two pools is one plant), else each
    pool entry is its own; a slot whose pool is spent keeps its null row. Slots are filled one by one in that random
    order, so a run can plant fewer than k though a fuller fill exists (a slot taking x, which only a later slot could
    use, leaves that slot null). A null row is drawn with replacement; with fresh_null each decoy enters once until
    its slot's pool is spent (null_draws), so runs whose pools hold a decoy each are independent draws of the null.
    Per scorer: the share of runs with p < alpha, the planted count (mean, min, max), and with keep_p every run's p
    (k = 0: the null calibration)."""
    rng = random.Random(seed)
    key_of = list(slot_ctx) if plant_of is None else list(plant_of)
    plantable = [i for i, key in enumerate(key_of) if plant_pool.get(key)]
    ids = {key: list(plant_ids[key]) if plant_ids is not None else [(key, j) for j in range(len(rows))]
           for key, rows in plant_pool.items()}
    if any(len(ids[key]) != len(rows) for key, rows in plant_pool.items()):
        raise ValueError("plant_ids names a different number of plants than a pool holds")
    cache: dict[tuple, list[float]] = {}           # keyed on where a row came from, never on the object
    ps: dict[str, list[float]] = {name: [] for name in scorers}
    counts: list[int] = []
    draws = null_draws([len(p) for p in null_pool], runs, rng) if fresh_null else None
    for r in range(runs):
        src = [("null", i, draws[r][i] if draws is not None else rng.randrange(len(null_pool[i])))
               for i in range(len(slot_ctx))]
        n, used = 0, set()
        if k:
            for i in rng.sample(plantable, len(plantable)):
                if n == k:
                    break
                free = [j for j, w in enumerate(ids[key_of[i]]) if w not in used]
                if free:
                    j = free[rng.randrange(len(free))]
                    used.add(ids[key_of[i]][j])
                    src[i] = ("plant", key_of[i], j)
                    n += 1
        counts.append(n)
        perms = list(permutations(slot_ctx, n_perm, rng.randrange(2 ** 32), strata))
        for name, scorer in scorers.items():
            S = []
            for kind, at, j in src:
                key = (name, kind, at, j)
                s = cache.get(key)
                if s is None:
                    s = cache[key] = scorer((null_pool if kind == "null" else plant_pool)[at][j])
                S.append(s)
            observed = sum(map(_at, S, slot_ctx))
            null = [sum(map(_at, S, p)) for p in perms]
            ps[name].append(p_value(observed, null))
    planted = {"planted": round(sum(counts) / runs, 2), "planted_min": min(counts, default=0),
               "planted_max": max(counts, default=0)}
    return {name: {"power": round(sum(p < alpha for p in v) / runs, 4), "runs": runs, **planted, "n_perm": n_perm,
                   **({"p": v} if keep_p else {})}
            for name, v in ps.items()}


def kolmogorov_tail(lam: float) -> float:
    """Q(λ) = P(√n·D > λ) as n grows: 2 Σ_{j≥1} (−1)^(j−1) e^(−2 j² λ²), 1 at λ ≤ 0."""
    if lam <= 0:
        return 1.0
    total = sum((-1) ** (j - 1) * math.exp(-2 * j * j * lam * lam) for j in range(1, 101))
    return max(0.0, min(1.0, 2 * total))


def ks_uniform(ps: Sequence[float]) -> tuple[float, float]:
    """One-sample Kolmogorov–Smirnov against U(0, 1): (D, asymptotic p). Permutation p-values are discrete, so D
    has a floor near 1/(n_perm + 1); with n_perm ≥ 499 it is small beside the critical 1.36/√runs."""
    if not ps:
        raise ValueError("no p-values")
    xs, n = sorted(ps), len(ps)
    d = max(max((i + 1) / n - x, x - i / n) for i, x in enumerate(xs))
    return d, kolmogorov_tail(math.sqrt(n) * d)


# --- distances: the Semitic side through Shoresh, competitors through their own spaces ---

def semitic_distance(engine: rm.Shoresh) -> Distance:
    """Shoresh's gated d* (the A10/A18 gate: Numbers whose domains fit the context), memoised per context."""
    gated: dict[Context, Callable] = {}
    variants: dict[str, list[rm.Variant]] = {}

    def dist(word: str, ctx: Context) -> float:
        g = gated.get(ctx)
        if g is None:
            fit = frozenset(n for n, doms in engine._domains().items() if fits(doms, ctx))
            g = gated[ctx] = engine._gated(fit)
        vs = variants.get(word)
        if vs is None:
            vs = variants[word] = rm.variants(engine.word_readings(word), word)
        return rm.d_star_over(g, vs)
    return dist


def competitor_domains(spec, data_dir: Path) -> dict[str, frozenset[str]]:
    """Number → the frozen tagger's domains over the entry's Meaning (the gloss Shoresh's Semitic side tags too)."""
    classify = tagger().classify
    rows = json.loads((data_dir / spec.file).read_text(encoding="utf-8"))
    rows = rows if isinstance(rows, list) else list(rows.values())
    out: dict[str, frozenset[str]] = {}
    for r in rows:
        if isinstance(r, dict):
            if r.get("Number") is None:
                raise ValueError(f"{spec.file}: an entry has no Number, so its domains would pool with every other")
            n = str(r["Number"])
            out[n] = out.get(n, frozenset()) | frozenset(classify(str(r.get("Meaning") or "")))
    return out


def competitor_distance(space, spec, domains: dict[str, frozenset[str]], engine: rm.Shoresh) -> Distance:
    """A competitor's d* over its keys whose Numbers fit the context; the words' variants are the Semitic side's."""
    spaces: dict[Context, CompetitorSpace] = {}
    variants: dict[str, list[rm.Variant]] = {}

    def dist(word: str, ctx: Context) -> float:
        s = spaces.get(ctx)
        if s is None:
            keys = {k: ns for k, ns in space.keys.items() if any(fits(domains.get(n, frozenset()), ctx) for n in ns)}
            s = spaces[ctx] = CompetitorSpace(space.name, keys, spec.distances, spec.guttural_transparent)
        vs = variants.get(word)
        if vs is None:
            vs = variants[word] = rm.variants(engine.word_readings(word), word)
        return s.d_star(vs) if s.keys else INF
    return dist
