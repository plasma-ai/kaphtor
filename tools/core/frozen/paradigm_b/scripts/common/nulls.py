"""Null generators. Every generator yields inputs of exactly the shape the
observed data has — a list of inscriptions, each a list of sign-name words
with a damage mask — plus the consonant map to parse them with, so the same
`parser.score_all` runs on real and simulated data.

  A1  sign-value permutation over all consonant-bearing syllabograms
  A2  sign-value permutation restricted to the campaign-resolved signs
      (IO Za 2 scope: exhaustive *301 value sweep; family scope: permutation)
  B   frequency-matched iid sign resampling, word lengths and damage preserved
  C   add-α bigram Markov over syllabographic words (trained outside the family
      by default), lengths and damage preserved
  D   structured opaque-formula generator (H_ISO): one synthetic form per word
      TYPE drawn from C, instantiated across the family preserving slot
      occupancy, recurrence, variation rate and missingness; at IO Za 2 scope
      it reduces to C and says so
  D2  D with a random shared affix inventory in place of the one-sign
      substitution (PROTOCOL-B §6): a paradigm that is no language's
"""
from __future__ import annotations

import random
from collections import Counter, defaultdict
from dataclasses import dataclass

import numpy as np

from common import paths
from common.matcher import base_consonant_map, syllabic_signs  # provided by lexicon-arms component

DIVIDER = "𐄁"


@dataclass(frozen=True)
class Inscription:
    id: str
    words: tuple[tuple[str, ...], ...]      # sign names per word
    damage: tuple[tuple[int, ...], ...]     # damage_after_sign per word
    support: str | None = None
    site: str | None = None


def observed_ioza2() -> Inscription:
    t = paths.load_data("ioza2.json")
    words = tuple(tuple(w["signs"]) for w in t["tokens"])
    damage = tuple(tuple(w["damage_after_sign"]) for w in t["tokens"])
    return Inscription(t["id"], words, damage, t.get("support"), t.get("site"))


def observed_family() -> list[Inscription]:
    fam = paths.load_data("formula_family.json")
    out = []
    for insc in fam["inscriptions"]:
        words = tuple(tuple(tok["linear_a"].split("-")) for tok in insc["tokens"])
        damage = tuple(() for _ in insc["tokens"])  # family damage is boolean in the file; masks only for IO Za 2
        out.append(Inscription(insc["id"], words, damage, insc.get("support"), insc.get("site")))
    return out


# ---------------------------------------------------------------------------
# corpus statistics for B / C
# ---------------------------------------------------------------------------

def corpus_syllabic_words(exclude_ids: set[str] | None = None) -> list[tuple[str, ...]]:
    corpus = paths.load_snapshot("corpus.json")
    words: list[tuple[str, ...]] = []
    for cid, e in corpus.items():
        if exclude_ids and cid in exclude_ids:
            continue
        for w in e.get("transliteratedWords") or []:
            w = w.strip()
            if w in (DIVIDER, "\n", "") or not w[0].isalpha() and not w.startswith("*"):
                continue
            signs = syllabic_signs(w)
            if len(signs) >= 1 and len(signs) == len(w.split("-")):
                words.append(tuple(signs))
    return words


class SignModel:
    """Unigram (B) and add-α bigram (C) models over sign names."""

    def __init__(self, words: list[tuple[str, ...]], alpha: float = 0.5):
        self.alpha = alpha
        self.unigram = Counter(s for w in words for s in w)
        self.signs = sorted(self.unigram)
        self.idx = {s: i for i, s in enumerate(self.signs)}
        n = len(self.signs)
        self.start = np.full(n, alpha)
        self.trans = np.full((n, n), alpha)
        for w in words:
            if not w:
                continue
            self.start[self.idx[w[0]]] += 1
            for a, b in zip(w, w[1:]):
                self.trans[self.idx[a], self.idx[b]] += 1
        self.start /= self.start.sum()
        self.trans /= self.trans.sum(axis=1, keepdims=True)
        tot = sum(self.unigram.values())
        self.uni_p = np.array([self.unigram[s] / tot for s in self.signs])

    def sample_iid(self, rng: np.random.Generator, length: int) -> tuple[str, ...]:
        return tuple(self.signs[i] for i in rng.choice(len(self.signs), size=length, p=self.uni_p))

    def sample_markov(self, rng: np.random.Generator, length: int) -> tuple[str, ...]:
        if length == 0:
            return ()
        cur = int(rng.choice(len(self.signs), p=self.start))
        out = [cur]
        for _ in range(length - 1):
            cur = int(rng.choice(len(self.signs), p=self.trans[cur]))
            out.append(cur)
        return tuple(self.signs[i] for i in out)


# ---------------------------------------------------------------------------
# generators
# ---------------------------------------------------------------------------

def null_a1(rng: random.Random) -> dict[str, str | None]:
    """Permute consonant values across all consonant-bearing signs."""
    cmap = base_consonant_map()
    signs = [s for s, c in cmap.items() if c]
    cons = [cmap[s] for s in signs]
    rng.shuffle(cons)
    for s, c in zip(signs, cons):
        cmap[s] = c
    return cmap


def resolved_signs() -> list[str]:
    sv = paths.load_snapshot("sign_values.json")
    res = sv.get("resolution_summary", {}).get("phonemic", [])
    out = []
    for s in res:
        name = s if isinstance(s, str) else (s.get("sign") or s.get("id") or "")
        name = name.upper().replace("₂", "2").replace("₃", "3")
        out.append(name)
    return out


def null_a2_sweep_values(target_sign: str = "*301") -> list[dict[str, str | None]]:
    """IO Za 2 scope: every consonant value the syllabary offers for *301
    (the only campaign-resolved sign in the inscription), plus None."""
    cmap = base_consonant_map()
    values = sorted({c for c in cmap.values() if c})
    maps = []
    for v in values + [None]:
        m = dict(cmap)
        m[target_sign] = v
        maps.append(m)
    return maps


def null_a2_family(rng: random.Random) -> dict[str, str | None]:
    """Family scope: permute values only among the campaign-resolved signs."""
    cmap = base_consonant_map()
    signs = [s for s in resolved_signs() if s in cmap and cmap[s]]
    cons = [cmap[s] for s in signs]
    rng.shuffle(cons)
    for s, c in zip(signs, cons):
        cmap[s] = c
    return cmap


def null_b(model: SignModel, rng: np.random.Generator, insc: Inscription) -> Inscription:
    return Inscription(insc.id, tuple(model.sample_iid(rng, len(w)) for w in insc.words), insc.damage, insc.support, insc.site)


def null_c(model: SignModel, rng: np.random.Generator, insc: Inscription) -> Inscription:
    return Inscription(insc.id, tuple(model.sample_markov(rng, len(w)) for w in insc.words), insc.damage, insc.support, insc.site)


def null_d(model: SignModel, rng: np.random.Generator, family: list[Inscription],
           variation_rate: float | None = None) -> list[Inscription]:
    """H_ISO generator. Word TYPES (identical sign strings across the family)
    get one synthetic form each; every occurrence reuses it, then a single-sign
    substitution is applied at the family's observed variation rate so
    Palaikastro-style variants exist in the simulated family too."""
    types: dict[tuple[str, ...], tuple[str, ...]] = {}
    occurrences = Counter(w for insc in family for w in insc.words)
    if variation_rate is None:
        variation_rate = _observed_variation_rate(family)
    out = []
    for insc in family:
        new_words = []
        for w in insc.words:
            if w not in types:
                types[w] = model.sample_markov(rng, len(w))
            form = list(types[w])
            if occurrences[w] > 1 and form and rng.random() < variation_rate:
                i = int(rng.integers(len(form)))
                form[i] = model.sample_markov(rng, 1)[0]
            new_words.append(tuple(form))
        out.append(Inscription(insc.id, tuple(new_words), insc.damage, insc.support, insc.site))
    return out


def draw_affix_inventory(model: SignModel, rng: np.random.Generator, k_prefix: int, k_suffix: int,
                         prefix_lengths: list[int], suffix_lengths: list[int]) -> tuple[list[tuple[str, ...]], list[tuple[str, ...]]]:
    """k distinct prefix and k' distinct suffix residues from the bigram model,
    lengths drawn from the observed residue lengths (PROTOCOL-B §6, D2)."""
    def draw(k: int, lengths: list[int]) -> list[tuple[str, ...]]:
        out: list[tuple[str, ...]] = []
        tries = 0
        while len(out) < k and tries < 1000 * max(k, 1):
            r = model.sample_markov(rng, int(lengths[int(rng.integers(len(lengths)))]))
            tries += 1
            if r not in out:
                out.append(r)
        if len(out) < k:
            raise RuntimeError(f"could not draw {k} distinct residues")
        return out
    return draw(k_prefix, prefix_lengths), draw(k_suffix, suffix_lengths)


def null_d2(model: SignModel, rng: np.random.Generator, family: list[Inscription],
            prefixes: list[tuple[str, ...]], suffixes: list[tuple[str, ...]], mode_p: list[float],
            variation_rate: float | None = None) -> list[Inscription]:
    """PROTOCOL-B §6 D2. As ``null_d`` (one synthetic form per word TYPE,
    recurrence and slot positions kept), but a varied occurrence of a
    recurring type is its form plus one inventory prefix and/or suffix,
    chosen with probabilities ``mode_p`` = (prefix only, suffix only, both)."""
    types: dict[tuple[str, ...], tuple[str, ...]] = {}
    occurrences = Counter(w for insc in family for w in insc.words)
    if variation_rate is None:
        variation_rate = _observed_variation_rate(family)
    p = np.array([mode_p[0] if prefixes else 0.0, mode_p[1] if suffixes else 0.0,
                  mode_p[2] if prefixes and suffixes else 0.0])
    out = []
    for insc in family:
        new_words = []
        for w in insc.words:
            if w not in types:
                types[w] = model.sample_markov(rng, len(w))
            form = types[w]
            if occurrences[w] > 1 and form and p.sum() > 0 and rng.random() < variation_rate:
                m = int(rng.choice(3, p=p / p.sum()))
                pre = prefixes[int(rng.integers(len(prefixes)))] if m in (0, 2) else ()
                suf = suffixes[int(rng.integers(len(suffixes)))] if m in (1, 2) else ()
                form = pre + form + suf
            new_words.append(tuple(form))
        out.append(Inscription(insc.id, tuple(new_words), insc.damage, insc.support, insc.site))
    return out


def _observed_variation_rate(family: list[Inscription]) -> float:
    """Share of recurring word types that also occur as a one-sign variant
    (Hamming distance 1 at equal length, or one sign shorter/longer)."""
    types = Counter(w for insc in family for w in insc.words)
    recurring = [w for w, n in types.items() if n > 1]
    if not recurring:
        return 0.0
    varied = 0
    for w in recurring:
        for v in types:
            if v == w:
                continue
            if len(v) == len(w) and sum(a != b for a, b in zip(v, w)) == 1:
                varied += 1
                break
            if abs(len(v) - len(w)) == 1 and (v[:len(w)] == w or w[:len(v)] == v):
                varied += 1
                break
    return varied / len(recurring)


def family_slot_matrix(family: list[Inscription]) -> dict[str, int]:
    """Occupancy signature used by the selftest to verify D preserves structure."""
    return {insc.id: len(insc.words) for insc in family}
