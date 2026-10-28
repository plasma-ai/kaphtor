"""Option B: morphological inventories, pair alignment and residue explanation
(PROTOCOL-B §§4–5).

Everything here is arm-symmetric: one alignment (§5.1) computed once per pair
of forms, and one generator that asks whether an arm's inventory produces the
affix residues of a form. No dictionary is consulted anywhere in this module.

Signs are compared at the (consonant, vowel) level through vendor/skeleton.py
so that homographic sign names (*301 = NA = (n, a); RA2 = (l, a)) never
matter; a sign with no decomposition keeps its name and matches only itself.

Attribution: di Mino.
"""
from __future__ import annotations

import itertools
import sys
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # scripts/
from common import paths  # noqa: E402
import skeleton  # noqa: E402
import render_la  # noqa: E402

Segment = tuple[str | None, str | None]
CV = tuple[str | None, str | None]

MAX_CHAIN_LEN = 3          # morphemes per side (PROTOCOL-B §5.3: ≤ 1 per class, ≤ 3 classes)
MAX_RESIDUE_SIGNS = 4      # longer residues are never explained
MIN_RUN = 2                # §5.1: a pair is scorable when its common run has ≥ 2 identical signs
ARMS = ("cs", "nws_floor", "luwian", "hurrian", "egyptian")


# ---------------------------------------------------------------------------
# signs
# ---------------------------------------------------------------------------

def sign_cv(sign: str) -> CV | str:
    d = skeleton._lookup_sign(sign)
    return (d[0], d[1]) if d is not None else sign


def word_cv(word) -> tuple:
    """Hyphenated string or sign tuple -> tuple of CV keys."""
    signs = word.split("-") if isinstance(word, str) else list(word)
    return tuple(sign_cv(s) for s in signs if s)


def _vowel_of(cvkey) -> str | None:
    return cvkey[1] if isinstance(cvkey, tuple) else None


def _cons_of(cvkey) -> str | None:
    return cvkey[0] if isinstance(cvkey, tuple) else None


# ---------------------------------------------------------------------------
# inventories
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Morpheme:
    id: str
    kind: str                       # "prefix" | "suffix"
    position: int                   # order class within its side (1-based)
    phonemic: tuple[Segment, ...]
    cost: float
    innovation_id: str | None
    attested_in: tuple[str, ...]
    function: str


@dataclass
class Inventory:
    arm: str
    variant: str                    # "base" | "ext"
    prefixes: list[Morpheme]
    suffixes: list[Morpheme]
    classes: dict[str, list[str]]   # {"prefix": [class names], "suffix": [...]}
    meta: dict = field(default_factory=dict)

    def morpheme(self, mid: str) -> Morpheme:
        for m in self.prefixes + self.suffixes:
            if m.id == mid:
                return m
        raise KeyError(mid)


def load_inventory(arm: str, variant: str = "base", *, with_sabaic: bool = False) -> Inventory:
    """data/paradigm/<arm>.json -> Inventory. ``base`` keeps cost-0 morphemes
    only; ``ext`` keeps the priced innovations too. ``with_sabaic`` admits the
    morphemes attested only in Ancient South Arabian (PROTOCOL-B §2, §4.3)."""
    raw = paths.load_data(f"paradigm/{arm}.json")
    pre, suf = [], []
    for m in raw["morphemes"]:
        if m["cost"] > 0 and variant != "ext":
            continue
        if m.get("sabaic_only") and not with_sabaic:
            continue
        mm = Morpheme(m["id"], m["kind"], int(m["position"]),
                      tuple((s[0], s[1]) for s in m["phonemic"]), float(m["cost"]),
                      m.get("innovation_id"), tuple(m.get("attested_in", ())), m.get("function", ""))
        (pre if mm.kind == "prefix" else suf).append(mm)
    return Inventory(arm, variant, pre, suf, raw["classes"], raw.get("_meta", {}))


# ---------------------------------------------------------------------------
# chains and their realizations
# ---------------------------------------------------------------------------

def _chains(morphemes: list[Morpheme]) -> list[tuple[Morpheme, ...]]:
    """Every ordered chain of ≤ MAX_CHAIN_LEN morphemes with at most one
    morpheme per position class, classes in ascending order. The empty chain
    is included."""
    by_pos: dict[int, list[Morpheme]] = {}
    for m in morphemes:
        by_pos.setdefault(m.position, []).append(m)
    positions = sorted(by_pos)
    out: list[tuple[Morpheme, ...]] = [()]
    for k in range(1, min(MAX_CHAIN_LEN, len(positions)) + 1):
        for combo in itertools.combinations(positions, k):
            for choice in itertools.product(*(by_pos[p] for p in combo)):
                out.append(tuple(choice))
    return out


def _segments(chain: tuple[Morpheme, ...]) -> list[Segment]:
    segs: list[Segment] = []
    for m in chain:
        segs.extend(m.phonemic)
    return render_la.fuse_segments(segs)


def _cvs_of_render(rendered) -> list[tuple[str, ...]]:
    return [tuple(sign_cv(s) for s in v) for v in render_la.sign_variants(rendered)]


class SuffixIndex:
    """rendered-residue -> cheapest chain, for one inventory.

    Two tables: ``consumed[v][residue]`` for chains whose first segment is a
    bare vowel v that the stem-final sign absorbs (the boundary vowel of
    §5.1), and ``plain[prev_vowel][residue]`` for chains rendered after a
    stem that already ends in a full CV sign with nucleus ``prev_vowel``.
    A vowel-initial chain also appears in ``plain`` rendered with its vowel
    as a bare vowel sign (the non-fused case, TE + U-TI-NU)."""

    VOWELS = ("a", "e", "i", "o", "u")

    def __init__(self, inv: Inventory):
        self.inv = inv
        self.consumed: dict[str, dict[tuple, tuple[float, tuple[str, ...]]]] = {v: {} for v in self.VOWELS}
        self.plain: dict[str | None, dict[tuple, tuple[float, tuple[str, ...]]]] = {v: {} for v in self.VOWELS + (None,)}
        arm = inv.arm
        for chain in _chains(inv.suffixes):
            cost = sum(m.cost for m in chain)
            ids = tuple(m.id for m in chain)
            segs = _segments(chain)
            if not segs:
                for v in self.VOWELS + (None,):
                    self._put(self.plain[v], (), cost, ids)
                continue
            if len(segs) > MAX_RESIDUE_SIGNS + 1:
                continue
            first = segs[0]
            if first[0] is None and first[1] is not None:
                v = first[1]
                rest = segs[1:]
                if rest:
                    for cvs in _cvs_of_render(render_la.render_segments(rest, arm, prev_vowel=v)):
                        self._put(self.consumed[v], cvs, cost, ids)
                else:
                    self._put(self.consumed[v], (), cost, ids)
                # non-fused realization: the vowel stands as a bare vowel sign
                for pv in self.VOWELS + (None,):
                    for cvs in _cvs_of_render(render_la.render_segments(segs, arm, prev_vowel=pv)):
                        self._put(self.plain[pv], cvs, cost, ids)
            else:
                for pv in self.VOWELS + (None,):
                    for cvs in _cvs_of_render(render_la.render_segments(segs, arm, prev_vowel=pv)):
                        self._put(self.plain[pv], cvs, cost, ids)

    @staticmethod
    def _put(table, key, cost, ids):
        if len(key) > MAX_RESIDUE_SIGNS:
            return
        cur = table.get(key)
        if cur is None or cost < cur[0]:
            table[key] = (cost, ids)


class PrefixIndex:
    """rendered prefix residue -> cheapest chain, per next-vowel context
    (the stem's first nucleus supplies the regressive echo for a bare
    consonant at the chain's end)."""

    VOWELS = SuffixIndex.VOWELS

    def __init__(self, inv: Inventory):
        self.inv = inv
        self.table: dict[str | None, dict[tuple, tuple[float, tuple[str, ...]]]] = {v: {} for v in self.VOWELS + (None,)}
        for chain in _chains(inv.prefixes):
            cost = sum(m.cost for m in chain)
            ids = tuple(m.id for m in chain)
            segs = _segments(chain)
            if not segs:
                for v in self.VOWELS + (None,):
                    SuffixIndex._put(self.table[v], (), cost, ids)
                continue
            if len(segs) > MAX_RESIDUE_SIGNS + 1:
                continue
            for nv in self.VOWELS + (None,):
                r = render_la.render_segments(segs, inv.arm, next_vowel=nv, word_final=False)
                for cvs in _cvs_of_render(r):
                    SuffixIndex._put(self.table[nv], cvs, cost, ids)


_INDEX_CACHE: dict[tuple, tuple[PrefixIndex, SuffixIndex]] = {}


def indices(inv: Inventory) -> tuple[PrefixIndex, SuffixIndex]:
    key = (inv.arm, inv.variant, tuple(m.id for m in inv.prefixes), tuple(m.id for m in inv.suffixes))
    if key not in _INDEX_CACHE:
        _INDEX_CACHE[key] = (PrefixIndex(inv), SuffixIndex(inv))
    return _INDEX_CACHE[key]


# ---------------------------------------------------------------------------
# alignment (§5.1)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Side:
    """One form's residues relative to the common run."""
    prefix: tuple                    # CV keys before the run
    boundary: str | None             # vowel of the boundary sign (shared consonant, different vowel), else None
    suffix: tuple                    # CV keys after the run (and after the boundary sign)
    run_first_vowel: str | None      # nucleus of the run's first sign (prefix context)
    run_last_vowel: str | None       # nucleus of the last identical run sign (suffix context)
    word_final_after_run: bool       # residue empty ⇒ the run (or boundary) ends the word


@dataclass(frozen=True)
class Alignment:
    run_len: int
    boundary_consonant: str | None
    f: Side
    g: Side


def _longest_common_run(a: tuple, b: tuple) -> tuple[int, int, int]:
    """(start_a, start_b, length) of the longest common contiguous run of
    identical CV keys; leftmost in a, then in b, on ties."""
    best = (0, 0, 0)
    for i in range(len(a)):
        for j in range(len(b)):
            k = 0
            while i + k < len(a) and j + k < len(b) and a[i + k] == b[j + k]:
                k += 1
            if k > best[2]:
                best = (i, j, k)
    return best


def align_pair(f, g) -> Alignment | None:
    """§5.1. ``f`` and ``g`` are sign tuples or hyphenated strings. Returns
    None when the pair is not scorable (common run shorter than MIN_RUN)."""
    a, b = word_cv(f), word_cv(g)
    i, j, k = _longest_common_run(a, b)
    if k < MIN_RUN:
        return None
    ea, eb = i + k, j + k
    boundary_c = None
    bv_a = bv_b = None
    if ea < len(a) and eb < len(b):
        ca, cb = a[ea], b[eb]
        if (isinstance(ca, tuple) and isinstance(cb, tuple) and ca[0] is not None
                and ca[0] == cb[0] and ca[1] != cb[1]):
            boundary_c = ca[0]
            bv_a, bv_b = ca[1], cb[1]
            ea += 1
            eb += 1
    run_first = _vowel_of(a[i])
    run_last = _vowel_of(a[i + k - 1])
    side_a = Side(a[:i], bv_a, a[ea:], run_first, run_last, ea == len(a))
    side_b = Side(b[:j], bv_b, b[eb:], run_first, run_last, eb == len(b))
    return Alignment(k, boundary_c, side_a, side_b)


# ---------------------------------------------------------------------------
# explanation (§5.3)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Explanation:
    cost: float
    prefix_chain: tuple[str, ...]
    suffix_chain: tuple[str, ...]
    boundary_by: str                 # "morpheme" | "dead_vowel" | "none"


def explain_side(side: Side, inv: Inventory, *, strict: bool = True) -> Explanation | None:
    """Cheapest explanation of one form's residues by ``inv``; None if the
    inventory does not generate them. ``strict=False`` compares consonants
    only (the ``cons`` ablation)."""
    pidx, sidx = indices(inv)
    pre_key = _key(side.prefix, strict)
    ptab = pidx.table.get(side.run_first_vowel, pidx.table[None])
    pbest = _lookup(ptab, pre_key, strict)
    if pbest is None:
        return None
    suf_key = _key(side.suffix, strict)
    cands: list[tuple[float, tuple[str, ...], str]] = []
    if side.boundary is None:
        tab = sidx.plain.get(side.run_last_vowel, sidx.plain[None])
        hit = _lookup(tab, suf_key, strict)
        if hit is not None:
            cands.append((hit[0], hit[1], "none"))
    else:
        v = side.boundary
        # (i) the boundary vowel is a dead vowel of the stem-final consonant
        dead_ok = (v == "u" and side.word_final_after_run) or (v == side.run_last_vowel)
        if not strict:
            dead_ok = True
        if dead_ok:
            tab = sidx.plain.get(v, sidx.plain[None])
            hit = _lookup(tab, suf_key, strict)
            if hit is not None:
                cands.append((hit[0], hit[1], "dead_vowel"))
        # (ii) the boundary vowel is the first vowel of a vowel-initial chain
        if strict:
            hit = _lookup(sidx.consumed.get(v, {}), suf_key, strict)
            if hit is not None:
                cands.append((hit[0], hit[1], "morpheme"))
        else:
            for vv in sidx.consumed:
                hit = _lookup(sidx.consumed[vv], suf_key, strict)
                if hit is not None:
                    cands.append((hit[0], hit[1], "morpheme"))
    if not cands:
        return None
    cost, chain, how = min(cands, key=lambda t: t[0])
    return Explanation(pbest[0] + cost, pbest[1], chain, how)


def _key(cvs: tuple, strict: bool) -> tuple:
    if strict:
        return tuple(cvs)
    return tuple((_cons_of(c) if isinstance(c, tuple) else c) for c in cvs)


def _lookup(table: dict, key: tuple, strict: bool):
    if strict:
        return table.get(key)
    best = None
    for k, val in table.items():
        if _key(k, False) == key and (best is None or val[0] < best[0]):
            best = val
    return best


# ---------------------------------------------------------------------------
# free inventory (§5.2)
# ---------------------------------------------------------------------------

@dataclass
class FreeInventory:
    prefixes: set = field(default_factory=set)
    suffixes: set = field(default_factory=set)     # (boundary vowel or None, residue)

    def add_side(self, s: Side) -> None:
        self.prefixes.add(s.prefix)
        self.suffixes.add((s.boundary, s.suffix))

    def explains(self, s: Side) -> bool:
        """Both residues in the inventory; an empty residue always counts as in (§5.2)."""
        pre_ok = not s.prefix or s.prefix in self.prefixes
        suf_ok = (s.boundary is None and not s.suffix) or (s.boundary, s.suffix) in self.suffixes
        return pre_ok and suf_ok


# ---------------------------------------------------------------------------
# attested-form check (selftest 1 / leakage matrix; PROTOCOL-B §8)
# ---------------------------------------------------------------------------

def fuse_with_origin(segments: list[Segment], origins: list[int]) -> tuple[list[Segment], list[tuple[int, ...]]]:
    out: list[Segment] = []
    orig: list[tuple[int, ...]] = []
    for (c, v), o in zip(segments, origins):
        if out and out[-1][1] is None and out[-1][0] is not None and c is None and v is not None:
            out[-1] = (out[-1][0], v)
            orig[-1] = orig[-1] + (o,)
        else:
            out.append((c, v))
            orig.append((o,))
    return out, orig


def form_sides(prefix_segs: list[Segment], stem_segs: list[Segment], suffix_segs: list[Segment],
               arm: str) -> tuple[Side, tuple[str, ...]]:
    """Render prefix+stem+suffix as one word and slice the affix signs off the
    stem signs exactly as align_pair would see them. Returns (Side, canonical
    signs of the whole word)."""
    segs = prefix_segs + stem_segs + suffix_segs
    origins = ([0] * len(prefix_segs)) + ([1] * len(stem_segs)) + ([2] * len(suffix_segs))
    fused, orig = fuse_with_origin(segs, origins)
    rendered = render_la.render_segments(fused, arm)
    signs = tuple(s for s, _, _ in rendered)
    cvs = [sign_cv(s) for s in signs]
    tags = [orig[i] for _, _, i in rendered]
    pre = tuple(cv for cv, t in zip(cvs, tags) if set(t) == {0})
    stem_idx = [n for n, t in enumerate(tags) if 1 in t]
    if not stem_idx:
        raise ValueError("stem rendered to no sign")
    last = stem_idx[-1]
    boundary = None
    if 2 in tags[last]:                     # stem-final consonant fused with a suffix vowel
        boundary = _vowel_of(cvs[last])
        run_last = _vowel_of(cvs[last - 1]) if last - 1 >= stem_idx[0] else None
    else:
        run_last = _vowel_of(cvs[last])
    suf = tuple(cv for cv, t in zip(cvs, tags) if set(t) == {2})
    run_first = _vowel_of(cvs[stem_idx[0]])
    side = Side(pre, boundary, suf, run_first, run_last, len(suf) == 0)
    return side, signs


NORMALIZE = {"cs": (("f", "p"),), "nws_floor": (("f", "p"),),
             "luwian": (("h", "ḫ"),), "hurrian": (("h", "ḫ"),), "egyptian": ()}


def normalize_latin(s: str, arm: str) -> str:
    """Transliteration conventions the arm's consonant table does not carry:
    Arabic f < *p (no F-series in the Semitic table); Anatolian/Hurrian h is
    the velar fricative written ḫ in the Luwian and Hurrian rules."""
    for a, b in NORMALIZE.get(arm, ()):
        s = s.replace(a, b)
    return s


def segs(s: str, arm: str = "cs") -> list[Segment]:
    return render_la.latin_to_segments(normalize_latin(s, arm))


def phonemic_to_segments(ph: list[list]) -> list[Segment]:
    return [(p[0], p[1]) for p in ph]


# ---------------------------------------------------------------------------
# the statistic (§5.1–5.4; B3)
# ---------------------------------------------------------------------------
# Amendment B3 (Tom, 2026-10-09, before any run): a training form identical to
# the held-out form (same CV keys) is not in its prediction set. Identity
# predicts a token under every arm and under every null that keeps recurrence,
# so A measures the variation only.

RIVALS = ("luwian", "hurrian", "egyptian")


@dataclass(frozen=True)
class Token:
    unit: str                        # inscription (family) or edition unit (controls)
    group: str                       # leave-one-out group: site (family) or unit (controls)
    slot: str                        # slot number (family) or lemma (controls)
    form: tuple[str, ...]            # sign names
    damaged: bool = False


@lru_cache(maxsize=200_000)
def _align(f: tuple, g: tuple) -> Alignment | None:
    return align_pair(f, g)


@lru_cache(maxsize=200_000)
def _cv(form: tuple) -> tuple:
    return word_cv(form)


_EXPLAIN: dict = {}


def _explains(side: Side, inv: Inventory, strict: bool) -> float | None:
    """Cost of the cheapest explanation of ``side`` by ``inv``, or None."""
    key = (id(inv), side, strict)
    if key not in _EXPLAIN:
        if len(_EXPLAIN) > 500_000:
            _EXPLAIN.clear()
        e = explain_side(side, inv, strict=strict)
        _EXPLAIN[key] = None if e is None else e.cost
    return _EXPLAIN[key]


def leave_one_group_out(tokens: list[Token]) -> list[frozenset[str]]:
    """Folds as sets of held-out units, one fold per group, groups sorted."""
    by: dict[str, set[str]] = {}
    for t in tokens:
        by.setdefault(t.group, set()).add(t.unit)
    return [frozenset(by[g]) for g in sorted(by)]


def random_splits(units: list[str], n_held: int, n_splits: int, seed: int) -> list[frozenset[str]]:
    """§5.4 secondary folds: ``n_splits`` random hold-outs of ``n_held`` units."""
    import numpy as np
    rng = np.random.default_rng(seed)
    units = sorted(units)
    return [frozenset(units[i] for i in rng.choice(len(units), size=n_held, replace=False))
            for _ in range(n_splits)]


def _training(tokens: list[Token]) -> tuple[dict[str, list[tuple]], FreeInventory]:
    """Distinct training forms per slot (one per CV key, first seen) and the
    free inventory over every scorable pair of them (§5.2)."""
    forms: dict[str, dict[tuple, tuple]] = {}
    for t in tokens:
        forms.setdefault(t.slot, {}).setdefault(_cv(t.form), t.form)
    free = FreeInventory()
    out = {}
    for slot, d in forms.items():
        fs = list(d.values())
        out[slot] = fs
        for a, b in itertools.combinations(fs, 2):
            al = _align(a, b)
            if al is not None:
                free.add_side(al.f)
                free.add_side(al.g)
    return out, free


def prediction_set(x: tuple, forms) -> list[Alignment]:
    """§5.1 with the B3 amendment: alignments of ``x`` with every training
    form at its slot that is not identical to it (CV level) and shares a run
    of ≥ 2 signs."""
    xcv = _cv(x)
    out = []
    for g in forms:
        if _cv(g) == xcv:
            continue
        al = _align(x, g)
        if al is not None:
            out.append(al)
    return out


def score(tokens: list[Token], invs: dict[str, Inventory], folds: list[frozenset[str]] | None = None,
          *, strict: bool = True, detail: bool = False) -> dict:
    """A_free, A_arm for every inventory in ``invs``, Δ and Δ_floor (§5.2–5.3).

    Per fold: held-out tokens are those of the fold's units; a token's
    prediction set is the training forms at its slot that differ from it and
    align with it (§5.1). A token with an empty set enters no denominator. It
    is predicted by ``free`` if its own residues are in the training
    inventory, and by an arm if the arm generates the residues of both forms
    of some pair; the arm's charge is the cheapest such pair's cost. A is the
    mean of the per-fold rates over folds with ≥ 1 scorable token."""
    if folds is None:
        folds = leave_one_group_out(tokens)
    arms = list(invs)
    rates: dict[str, list[float]] = {a: [] for a in ["free"] + arms}
    charge = {a: 0.0 for a in arms}
    n_total = 0
    rows = []
    for held in folds:
        train, free = _training([t for t in tokens if t.unit not in held])
        n = 0
        hits = {a: 0 for a in ["free"] + arms}
        for x in tokens:
            if x.unit not in held:
                continue
            pred = prediction_set(x.form, train.get(x.slot, ()))
            if not pred:
                continue
            n += 1
            if any(free.explains(al.f) for al in pred):
                hits["free"] += 1
            for a in arms:
                best = None
                for al in pred:
                    cf = _explains(al.f, invs[a], strict)
                    if cf is None:
                        continue
                    cg = _explains(al.g, invs[a], strict)
                    if cg is None:
                        continue
                    best = cf + cg if best is None else min(best, cf + cg)
                if best is not None:
                    hits[a] += 1
                    charge[a] += best
        n_total += n
        if n:
            for a in rates:
                rates[a].append(hits[a] / n)
        if detail:
            rows.append({"held_out": sorted(held), "scorable": n, **{f"hits_{a}": h for a, h in hits.items()}})
    A = {a: (sum(v) / len(v) if v else float("nan")) for a, v in rates.items()}
    out = {"A": A, "scorable": n_total, "folds_scored": len(rates["free"]), "charge": charge}
    rivals = [A[r] for r in RIVALS if r in A]
    if "cs" in A and rivals:
        out["delta"] = A["cs"] - max(rivals)
    if "nws_floor" in A and rivals:
        out["delta_floor"] = A["nws_floor"] - max(rivals)
    if detail:
        out["folds"] = rows
    return out


# ---------------------------------------------------------------------------
# tokens of the family (from Inscriptions, observed or simulated) and controls
# ---------------------------------------------------------------------------

def family_slot_index() -> dict[str, list[tuple[int, str, bool]]]:
    """inscription id -> [(token index, slot, damaged)] from the frozen family
    file. A slot listing several forms (KO Za 1 slot 2) yields one token each."""
    out: dict[str, list[tuple[int, str, bool]]] = {}
    for insc in paths.load_data("formula_family.json")["inscriptions"]:
        toks = insc["tokens"]
        used: set[int] = set()
        rows = []
        for slot, forms in insc["slots"].items():
            for f in forms:
                idx = next(i for i, t in enumerate(toks) if i not in used and t["linear_a"] == f)
                used.add(idx)
                rows.append((idx, slot, bool(toks[idx]["damaged"])))
        out[insc["id"]] = rows
    return out


def family_tokens(family, index: dict[str, list[tuple[int, str, bool]]], *,
                  drop_slots: tuple[str, ...] = (), drop_damaged: bool = False) -> list[Token]:
    """Slot tokens of a family (``nulls.Inscription`` list, observed or null);
    positions come from ``index``, so a null replicate is scored at exactly
    the observed slot positions."""
    out = []
    for insc in family:
        for idx, slot, dmg in index[insc.id]:
            if slot in drop_slots or (drop_damaged and dmg):
                continue
            out.append(Token(insc.id, insc.site or insc.id, slot, tuple(insc.words[idx]), dmg))
    return out


def window_tokens(w: dict) -> list[Token]:
    """A B2 control window: one token per recurring-lemma form, folds by unit."""
    lemmas = set(w["slots"])
    return [Token(u["unit"], u["unit"], t["lemma"], tuple(t["signs"].split("-")))
            for u in w["units"] for t in u["tokens"] if t["lemma"] in lemmas and t.get("signs")]


def d2_params(tokens: list[Token]) -> dict:
    """Observed residue inventory of the whole family for null D2 (§6): the
    distinct non-empty prefix and suffix residues over every scorable pair of
    distinct forms at a slot (a boundary sign belongs to the suffix residue),
    their lengths, and the shares of varied sides carrying a prefix only, a
    suffix only, or both."""
    forms: dict[str, dict[tuple, tuple]] = {}
    for t in tokens:
        forms.setdefault(t.slot, {}).setdefault(_cv(t.form), t.form)
    pre: dict[tuple, int] = {}
    suf: dict[tuple, int] = {}
    modes = [0, 0, 0]
    for d in forms.values():
        for a, b in itertools.combinations(list(d.values()), 2):
            al = _align(a, b)
            if al is None:
                continue
            for s in (al.f, al.g):
                sr = ((("boundary", s.boundary),) if s.boundary else ()) + s.suffix
                if s.prefix:
                    pre[s.prefix] = len(s.prefix)
                if sr:
                    suf[sr] = len(sr)
                if s.prefix and sr:
                    modes[2] += 1
                elif s.prefix:
                    modes[0] += 1
                elif sr:
                    modes[1] += 1
    tot = sum(modes) or 1
    return {"k_prefix": len(pre), "k_suffix": len(suf),
            "prefix_lengths": sorted(pre.values()), "suffix_lengths": sorted(suf.values()),
            "mode_p": [m / tot for m in modes]}
