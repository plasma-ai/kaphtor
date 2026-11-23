"""Protocol C, phase C2: null R, the structure null (§8.1).

Each test type keeps its core, the positions inside a run of two or more signs shared with a partner. Every other
position is drawn again from the frequencies of the fold's training signs, opaque signs included, at the same
length. Partners and hits are then found again by the same code. One draw of every type makes one replicate, and
every arm scores the same draws.

`run` returns, for each decider, the number of hit types in each replicate. B = 10,000 and seed 20261101 are the
registered values; the tests pass smaller ones on made-up corpora. Nothing here reads a Linear A form.

Attribution: di Mino
"""
from __future__ import annotations

import random

SEED, B = 20261101, 10_000
SEED_A6, TRIES = 20261201, 200


def redraw(x: tuple, core: frozenset[int], signs: list, weights: list[int], rng: random.Random) -> tuple:
    free = [i for i in range(len(x)) if i not in core]
    if not free or not signs:
        return x
    out = list(x)
    for i, s in zip(free, rng.choices(signs, weights, k=len(free))):
        out[i] = s
    return tuple(out)


def redraw_same_core(pool, x: tuple, left_out, core, signs, weights, rng: random.Random, kept: dict) -> tuple:
    """A redraw of x whose core is x's own (§16 A6 item 1), or x itself after TRIES draws that all changed it.
    `kept` remembers, for this type, whether a drawn form kept the core."""
    for _ in range(TRIES):
        y = redraw(x, core, signs, weights, rng)
        if y not in kept:
            kept[y] = pool.core(y, left_out) == core
        if kept[y]:
            return y
    kept["gave up"] = kept.get("gave up", 0) + 1
    return x


def run_fixed(pool, types: list[tuple], deciders: dict, b: int = B, seed: int = SEED_A6,
              report: dict | None = None) -> dict[str, list[int]]:
    """Null R as amended by A6: §8.1's redraw, kept only when the redrawn form has the type's own core. Returns
    {name: hit types per replicate}; `report`, if given, receives the number of replicates that gave up."""
    rng = random.Random(seed)
    counts = {name: [0] * b for name in deciders}
    gave_up = 0
    for x in types:
        left_out = pool.docs(x)
        core = pool.core(x, left_out)
        signs, weights = pool.unigram(left_out)
        kept: dict = {}
        known: dict[tuple, tuple[bool, ...]] = {}
        for n in range(b):
            y = redraw_same_core(pool, x, left_out, core, signs, weights, rng, kept)
            if y not in known:
                partners = pool.partners(y, left_out)
                known[y] = tuple(decide(partners, left_out) for decide in deciders.values())
            for name, got in zip(deciders, known[y]):
                counts[name][n] += got
        gave_up += kept.get("gave up", 0)
    if report is not None:
        report["gave_up"] = gave_up
    return counts


def run(pool, types: list[tuple], deciders: dict, b: int = B, seed: int = SEED) -> dict[str, list[int]]:
    """§8.1 as signed, kept for the record: A6 found it cannot be exceeded and replaced it with `run_fixed`.
    `deciders` maps a name to f(partners, left_out) -> bool. Returns {name: hit types per replicate}."""
    rng = random.Random(seed)
    counts = {name: [0] * b for name in deciders}
    for x in types:
        left_out = pool.docs(x)
        core = pool.core(x, left_out)
        signs, weights = pool.unigram(left_out)
        known: dict[tuple, tuple[bool, ...]] = {}
        for n in range(b):
            y = redraw(x, core, signs, weights, rng)
            if y not in known:
                partners = pool.partners(y, left_out)
                known[y] = tuple(decide(partners, left_out) for decide in deciders.values())
            for name, got in zip(deciders, known[y]):
                counts[name][n] += got
    return counts
