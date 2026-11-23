"""Protocol C, phase C3: pseudo-corpora of known language (§9.1) and their shuffled-edge twins (§9.2 G-c).

`cut` takes a text as a list of words in order, each already written as sign keys, and cuts it into K
pseudo-corpora. A pseudo-corpus is a run of pseudo-documents whose sizes are drawn from the Linear A pool's own
document sizes, filled with consecutive words until it holds the registered number of distinct forms. The K
corpora follow one another through the text; when the text runs out the cut starts again at its beginning, and
the corpora from there on are marked as overlapping.

`shuffle_edges` gives a corpus with every type's edges drawn again as null R draws them (§8.1): the core is kept,
the other positions come from the fold's training signs.

A word of fewer than two signs is no word here, as in §7 D6.

Attribution: di Mino
"""
from __future__ import annotations

import random

import c_align as a
import null_r

SEED, K = 20261104, 20


def cut(words: list[tuple], sizes: list[int], n_types: int, k: int = K, seed: int = SEED) -> list[dict]:
    """K pseudo-corpora as {"tokens": [(document, word)], "overlaps": bool}."""
    words = [w for w in words if len(w) >= 2]
    if len(set(words)) < n_types:
        raise ValueError(f"the text has {len(set(words))} distinct words of two signs or more; {n_types} are needed")
    rng = random.Random(seed)
    out, at, wrapped = [], 0, False
    for j in range(k):
        tokens: list[tuple[str, tuple]] = []
        seen: set[tuple] = set()
        doc = 0
        while len(seen) < n_types:
            for _ in range(rng.choice(sizes)):
                if at == len(words):
                    at, wrapped = 0, True
                tokens.append((f"p{j:02d}-{doc:04d}", words[at]))
                seen.add(words[at])
                at += 1
                if len(seen) == n_types:
                    break
            doc += 1
        out.append({"tokens": tokens, "overlaps": wrapped})
    return out


def mean_signs(tokens: list[tuple[str, tuple]]) -> float:
    types = set(w for _, w in tokens)
    return sum(map(len, types)) / len(types)


def shuffle_edges(tokens: list[tuple[str, tuple]], seed: int) -> list[tuple[str, tuple]]:
    """Every type keeps its core and has its other positions drawn again; all its tokens change together."""
    pool = a.Pool(tokens)
    rng = random.Random(seed)
    new: dict[tuple, tuple] = {}
    for x in dict.fromkeys(w for _, w in tokens):
        left_out = pool.docs(x)
        new[x] = null_r.redraw_same_core(pool, x, left_out, pool.core(x, left_out), *pool.unigram(left_out), rng, {})
    return [(d, new[w]) for d, w in tokens]
