"""Kernel B: Unsupervised Kober-Trio / Paradigm-Delta Forward Model (KERNEL-SPECS.md §3).

Automatically extracts stem-sharing word pairs and Kober clusters (pairs, trios, n-tuples) from any
corpus of CV sign-key words using Protocol C's c_align.align, without hand-picking any paradigm.
Trains a hierarchical Witten-Bell generative model over (polarity, affix_edge_1 <-> affix_edge_2)
transitions and scores any test corpus in mean bits per extracted transition.

Nothing here reads a Linear A form or the gate split.

Attribution: di Mino
"""
from __future__ import annotations

import collections
import math
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "render"))
import c_align as a  # noqa: E402

Word = tuple
Edge = tuple[tuple, str | None, tuple]  # (prefix_keys, boundary_vowel, suffix_keys)
Polarity = tuple[bool, bool, bool]      # (has_prefix, has_boundary_vowel, has_suffix)
Transition = tuple[Polarity, Edge, Edge]

POLARITIES = (
    (True, False, False),
    (False, True, False),
    (False, False, True),
    (True, True, False),
    (True, False, True),
    (False, True, True),
    (True, True, True),
)


def _edge(side: a.Side) -> Edge:
    bv = side.boundary[1] if side.boundary is not None else None
    return (side.prefix, bv, side.suffix)


def _valid_affix(side: a.Side, max_side: int = 2, max_total: int = 3) -> bool:
    n_pre = len(side.prefix)
    n_suf = len(side.suffix)
    return n_pre <= max_side and n_suf <= max_side and (n_pre + n_suf) <= max_total


def _polarity(e1: Edge, e2: Edge) -> Polarity:
    return (
        bool(e1[0] or e2[0]),
        (e1[1] is not None) or (e2[1] is not None),
        bool(e1[2] or e2[2]),
    )


def extract_transitions(
    words: list[Word],
    min_run: int = 2,
    max_side: int = 2,
    max_total: int = 3,
    max_partners: int = 12,
) -> list[Transition]:
    """Unsupervised extraction of stem-sharing morphological transitions from distinct word types.

    Finds:
      1. Pairs sharing a contiguous run of >= min_run signs (via c_align.align), with affix-sized residues.
      2. 2+-sign stem-final vowel alternations sharing w[:-1] and final consonant series (e.g. SA-RU ~ SA-RO ~ SA-RA2).

    Each word keeps at most `max_partners` partners (longest shared runs first) to prevent noisy hubs.
    Returns canonicalized (polarity, edge1, edge2) transitions.
    """
    types = sorted(set(words))
    if len(types) < 2:
        return []

    by_bigram: dict[tuple, list[int]] = collections.defaultdict(list)
    by_stem_cons: dict[tuple, list[int]] = collections.defaultdict(list)

    for idx, w in enumerate(types):
        if len(w) >= min_run:
            for bg in set(zip(w, w[1:])):
                by_bigram[bg].append(idx)
        if len(w) >= 2 and isinstance(w[-1], tuple) and w[-1][0]:
            by_stem_cons[(w[:-1], w[-1][0])].append(idx)

    # Candidate pairs per word, keeping longest run first
    partner_hits: dict[int, dict[int, tuple[int, Transition]]] = collections.defaultdict(dict)

    def _register(i: int, j: int, run_len: int, e1: Edge, e2: Edge) -> None:
        if e1 == e2:
            return
        pair = (e1, e2) if e1 < e2 else (e2, e1)
        pol = _polarity(pair[0], pair[1])
        if not any(pol):
            return
        tr: Transition = (pol, pair[0], pair[1])
        prev = partner_hits[i].get(j)
        if prev is None or run_len > prev[0]:
            partner_hits[i][j] = (run_len, tr)
            partner_hits[j][i] = (run_len, tr)

    # 1. Bigram-indexed alignments (run >= min_run)
    seen_pairs: set[tuple[int, int]] = set()
    for idxs in by_bigram.values():
        if len(idxs) > 80:
            # Extremely high-frequency bigrams are sampled deterministically to stay O(N)
            idxs = idxs[:80]
        for p in range(len(idxs)):
            i = idxs[p]
            wi = types[i]
            for q in range(p + 1, len(idxs)):
                j = idxs[q]
                key = (i, j) if i < j else (j, i)
                if key in seen_pairs:
                    continue
                seen_pairs.add(key)
                wj = types[j]
                al = a.align(wi, wj, m=min_run)
                if al is None:
                    continue
                if _valid_affix(al.f, max_side, max_total) and _valid_affix(al.g, max_side, max_total):
                    _register(i, j, al.run_len, _edge(al.f), _edge(al.g))

    # 2. Stem-final consonant-series vowel alternations (catches 2-sign Kober trios like SA-RU ~ SA-RO ~ SA-RA)
    for idxs in by_stem_cons.values():
        if len(idxs) < 2:
            continue
        if len(idxs) > 40:
            idxs = idxs[:40]
        for p in range(len(idxs)):
            i = idxs[p]
            wi = types[i]
            for q in range(p + 1, len(idxs)):
                j = idxs[q]
                wj = types[j]
                if wi[-1][1] == wj[-1][1]:
                    continue
                e1: Edge = ((), wi[-1][1], ())
                e2: Edge = ((), wj[-1][1], ())
                _register(i, j, len(wi) - 1, e1, e2)

    # Cap partners per word (longest shared runs first) and collect unique (i < j) transitions
    kept_pairs: set[tuple[int, int]] = set()
    transitions: list[Transition] = []
    for i, nbrs in partner_hits.items():
        ranked = sorted(nbrs.items(), key=lambda kv: (-kv[1][0], kv[0]))[:max_partners]
        for j, (_, tr) in ranked:
            pair_id = (i, j) if i < j else (j, i)
            if pair_id not in kept_pairs:
                kept_pairs.add(pair_id)
                transitions.append(tr)
    return transitions


def extract_clusters(words: list[Word], min_run: int = 2) -> list[list[Word]]:
    """Connected components of stem-sharing words (Kober pairs/trios/n-tuples), sorted largest first."""
    types = sorted(set(words))
    adj: dict[int, set[int]] = collections.defaultdict(set)
    by_bigram: dict[tuple, list[int]] = collections.defaultdict(list)
    by_stem_cons: dict[tuple, list[int]] = collections.defaultdict(list)
    for idx, w in enumerate(types):
        if len(w) >= min_run:
            for bg in set(zip(w, w[1:])):
                by_bigram[bg].append(idx)
        if len(w) >= 2 and isinstance(w[-1], tuple) and w[-1][0]:
            by_stem_cons[(w[:-1], w[-1][0])].append(idx)

    for idxs in by_bigram.values():
        if len(idxs) > 80:
            idxs = idxs[:80]
        for p in range(len(idxs)):
            for q in range(p + 1, len(idxs)):
                i, j = idxs[p], idxs[q]
                al = a.align(types[i], types[j], m=min_run)
                if al and _valid_affix(al.f) and _valid_affix(al.g):
                    adj[i].add(j)
                    adj[j].add(i)
    for idxs in by_stem_cons.values():
        if 2 <= len(idxs) <= 40:
            for p in range(len(idxs)):
                for q in range(p + 1, len(idxs)):
                    i, j = idxs[p], idxs[q]
                    if types[i][-1][1] != types[j][-1][1]:
                        adj[i].add(j)
                        adj[j].add(i)

    visited: set[int] = set()
    clusters: list[list[Word]] = []
    for i in sorted(adj):
        if i in visited:
            continue
        comp, stack = [], [i]
        visited.add(i)
        while stack:
            u = stack.pop()
            comp.append(types[u])
            for v in adj[u]:
                if v not in visited:
                    visited.add(v)
                    stack.append(v)
        clusters.append(sorted(comp))
    clusters.sort(key=lambda c: (-len(c), c[0]))
    return clusters


class KoberModel:
    """Hierarchical Witten-Bell model over extracted morphological transitions (polarity, edge1, edge2).

    P(pol, e1, e2) = P(pol) * P(e1, e2 | pol)
    where P(e1, e2 | pol) backs off via Witten-Bell to P(e1) * P(e2), and each unseen edge backs off
    to an affix-sign unigram model over the fixed CV alphabet (so unseen edges receive well-calibrated
    probabilities proportional to their length and sign distribution).
    """

    def __init__(self, transitions: list[Transition], alphabet: list):
        self.v_signs = len(alphabet)
        self.v_vowels = 5
        self.pol_counts: collections.Counter = collections.Counter()
        self.pair_by_pol: dict[Polarity, collections.Counter] = collections.defaultdict(collections.Counter)
        self.pair_totals: dict[Polarity, int] = collections.defaultdict(int)
        self.edge_counts: collections.Counter = collections.Counter()
        self.sign_counts: collections.Counter = collections.Counter()
        self.pre_len_counts: collections.Counter = collections.Counter()
        self.suf_len_counts: collections.Counter = collections.Counter()
        self.bv_counts: collections.Counter = collections.Counter()

        for pol, e1, e2 in transitions:
            self.pol_counts[pol] += 1
            self.pair_by_pol[pol][(e1, e2)] += 1
            self.pair_totals[pol] += 1
            for e in (e1, e2):
                self.edge_counts[e] += 1
                self.pre_len_counts[len(e[0])] += 1
                self.suf_len_counts[len(e[2])] += 1
                self.bv_counts[e[1]] += 1
                for sk in e[0]:
                    self.sign_counts[sk] += 1
                for sk in e[2]:
                    self.sign_counts[sk] += 1

        self.total_tr = sum(self.pol_counts.values())
        self.total_edges = sum(self.edge_counts.values())
        self.total_signs = sum(self.sign_counts.values())

    def _p_sign(self, sk) -> float:
        p0 = 1.0 / self.v_signs
        if not self.total_signs:
            return p0
        t = len(self.sign_counts)
        return (self.sign_counts.get(sk, 0) + t * p0) / (self.total_signs + t)

    def _p_edge_backoff(self, edge: Edge) -> float:
        pre, bv, suf = edge
        # Length priors (0, 1, 2)
        p_pre_len = (self.pre_len_counts.get(len(pre), 0) + 1.0) / (self.total_edges + 3.0)
        p_suf_len = (self.suf_len_counts.get(len(suf), 0) + 1.0) / (self.total_edges + 3.0)
        p_bv = (self.bv_counts.get(bv, 0) + 1.0) / (self.total_edges + self.v_vowels + 1.0)
        p = p_pre_len * p_suf_len * p_bv
        for sk in pre:
            p *= self._p_sign(sk)
        for sk in suf:
            p *= self._p_sign(sk)
        return p

    def _p_edge(self, edge: Edge) -> float:
        p_bo = self._p_edge_backoff(edge)
        if not self.total_edges:
            return p_bo
        t = len(self.edge_counts)
        return (self.edge_counts.get(edge, 0) + t * p_bo) / (self.total_edges + t)

    def prob(self, tr: Transition) -> float:
        pol, e1, e2 = tr
        # Polarity probability
        p0_pol = 1.0 / len(POLARITIES)
        if self.total_tr:
            t_pol = len(self.pol_counts)
            p_pol = (self.pol_counts.get(pol, 0) + t_pol * p0_pol) / (self.total_tr + t_pol)
        else:
            p_pol = p0_pol

        # Pair probability given polarity, backing off to independent edges
        p_indep = self._p_edge(e1) * self._p_edge(e2)
        seen = self.pair_by_pol.get(pol)
        if seen:
            t_pair = len(seen)
            n_pair = self.pair_totals[pol]
            p_pair = (seen.get((e1, e2), 0) + t_pair * p_indep) / (n_pair + t_pair)
        else:
            p_pair = p_indep
        return max(p_pol * p_pair, 1e-300)

    def log2(self, tr: Transition) -> float:
        return math.log2(self.prob(tr))


def bits_per_transition(models: list[KoberModel], transitions: list[Transition]) -> float:
    """Mean bits per transition across `models`. Returns 0.0 if `transitions` is empty."""
    if not transitions:
        return 0.0
    n = len(transitions)
    return sum(-sum(m.log2(tr) for tr in transitions) / n for m in models) / len(models)


def draw_transitions(member_transitions: dict[str, list[Transition]], total: int, seed: int) -> list[Transition]:
    """Sample `total` transitions in equal shares across arm members (mirroring lid.draw)."""
    out: list[Transition] = []
    left, waiting = total, len(member_transitions)
    for name in sorted(member_transitions, key=lambda n: (len(member_transitions[n]), n)):
        pool = member_transitions[name]
        take = min(len(pool), left // waiting)
        if take > 0:
            out.extend(random.Random(f"{seed}:kober:{name}").sample(pool, take))
        left -= take
        waiting -= 1
    return out
