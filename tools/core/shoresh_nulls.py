"""The pieces of the project's validation scripts that Shoresh reuses (see SHORESH.md): the L6 root key and name
test (null_model_audit), the gold guard's spelling and the decoy family B draw (root_match_phase0, §6 A3), the null A
consonant permutation (blind_corpus_test), and the stops that may geminate (cognate_search).

Each is copied without change, so Shoresh's nulls stay the ones pre-registered; load_corpus_words alone reads its
corpus through tools/paths.py. The ported validation scripts keep their own copies of the same functions.

Attribution: di Mino
"""
from __future__ import annotations

import json
import random
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Callable, Sequence

try:
    from ..paths import require
    from .corpus_utils import CORPUS_PATH
    from .phonetics import _tokenize_phonemes
    from .skeleton import _SUBSCRIPT_MAP, SIGN_DECOMPOSITION, _lookup_sign, extract_skeleton
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from tools.paths import require
    from tools.core.corpus_utils import CORPUS_PATH
    from tools.core.phonetics import _tokenize_phonemes
    from tools.core.skeleton import _SUBSCRIPT_MAP, SIGN_DECOMPOSITION, _lookup_sign, extract_skeleton

GEMINABLE_STOPS = {"t", "d", "k", "q", "p", "b"}


def _extract_consonantal_root(form: str) -> str:
    """Canonical root extraction from ventris_propagate.py."""
    s = form.strip()
    s = unicodedata.normalize("NFC", s)
    s = re.sub(r"^\*", "", s)
    s = re.sub(r"\(.*?\)", "", s)
    s = re.sub(r"\d+$", "", s)
    s = s.split(",")[0].split(" ")[0]
    if "/*" in s:
        s = s.split("/*")[0]
    s = s.replace("/", "")
    s = s.replace("-", "").replace("_", "")
    vowels = set("aeiouāēīōūäëïöüăĕĭŏŭ")
    root = "".join(c for c in s if c.lower() not in vowels and c not in "* V")
    return root.lower()


def _is_onomastic(entry: dict) -> bool:
    """Detect proper-name entries (PN/GN/DN) in root databases."""
    meaning = entry.get("Meaning", "")
    if re.search(r'\((?:PN|GN|DN)\)', meaning):
        return True
    for v in entry.get("Analogues", {}).values():
        if re.search(r'\((?:PN|GN|DN)\)', str(v)):
            return True
    return False


def load_corpus_words() -> list[str]:
    """Load unique multi-sign corpus transliterations.

    Unlike the skeleton loaders, words with a leading numbered sign are kept:
    recognized syllabograms like *28B and *301 are parseable and excluding
    them would make templates anchored on them (yi_28b_prefix) impossible to
    calibrate. Words the deparser cannot parse (logogram sequences, lacunae,
    unknown signs) enter the list but are skipped symmetrically on the real
    and shuffled sides, so they cannot bias the enrichment measurement.
    """
    corpus = json.loads(require(CORPUS_PATH, "corpus.json").read_text(encoding="utf-8"))
    words = set()
    for inscription in corpus.values():
        for w in inscription.get("transliteratedWords", []):
            if "-" in w and not w.replace("-", "").isdigit():
                words.add(w)
    return sorted(words)


def sign_group_key(word: str) -> tuple[str, ...]:
    """A sign group as the gold guard compares it: signs upper-cased, subscripts as digits (A-PA₃ = a-pa3)."""
    return tuple(s.upper().translate(_SUBSCRIPT_MAP) for s in word.strip().split("-") if s)


def loud_skeleton(word: str) -> tuple[str, list[str]]:
    """(skeleton, signs with no decomposition). Never shortens a word silently: a caller excludes any word
    whose second element is non-empty (§6 A1)."""
    consonants, unmapped = [], []
    for sign in word.split("-"):
        decomp = _lookup_sign(sign)
        if decomp is None:
            unmapped.append(sign)
        elif decomp[0]:
            consonants.append(decomp[0])
    return "".join(consonants), unmapped


def _skel_len(word: str) -> int:
    return len(_tokenize_phonemes(extract_skeleton(word)))


def _ocp_ok(word: str) -> bool:
    """No two identical consonants adjacent in the skeleton (the Semitic OCP on C1/C2)."""
    toks = _tokenize_phonemes(extract_skeleton(word))
    return all(a != b for a, b in zip(toks, toks[1:]))


def position_tables(words: list[str]) -> dict[str, tuple[tuple[str, ...], tuple[int, ...]]]:
    """Sign frequencies by position (initial, medial, final) over the mapped corpus words."""
    tables: dict[str, Counter] = {"initial": Counter(), "medial": Counter(), "final": Counter()}
    for w in words:
        signs = w.split("-")
        if len(signs) < 2 or loud_skeleton(w)[1]:
            continue
        tables["initial"][signs[0]] += 1
        tables["final"][signs[-1]] += 1
        tables["medial"].update(signs[1:-1])
    return {k: tuple(zip(*sorted(c.items()))) for k, c in tables.items()}


def fabricate(rng: random.Random, n_signs: int, skel_len: int, tables: dict, real: set[str],
              tries: int = 500, tokens: Callable[[str], Sequence[str]] | None = None, ocp: bool = True) -> str | None:
    """A position-matched pseudo-word (§6 A3, decoy family B): initial, medial and final signs drawn from their
    own corpus distributions, the source's sign count and skeleton length, OCP kept, not a real word. tokens(w)
    gives the skeleton's tokens; by default _skel_len and _ocp_ok's, as the gold set was built (Shoresh passes its
    own, one per letter). ocp=False (A17, the tokens path only) lets two identical consonants stand side by side,
    for a source word that has them."""
    for _ in range(tries):
        signs = [rng.choices(*tables["initial"])[0]]
        signs += rng.choices(*tables["medial"], k=max(0, n_signs - 2)) if n_signs > 2 else []
        if n_signs > 1:
            signs.append(rng.choices(*tables["final"])[0])
        w = "-".join(signs)
        if w in real:
            continue
        if tokens is None:
            if _skel_len(w) == skel_len and _ocp_ok(w):
                return w
            continue
        toks = tokens(w)
        if len(toks) == skel_len and (not ocp or all(a != b for a, b in zip(toks, toks[1:]))):
            return w
    return None


def base_consonant_map() -> dict[str, str | None]:
    return {sign: decomp[0] for sign, decomp in SIGN_DECOMPOSITION.items()}


def permuted_cons_map(rng: random.Random) -> dict[str, str | None]:
    """Null A: permute consonant assignments across consonant-bearing signs."""
    cmap = base_consonant_map()
    signs = [s for s, c in cmap.items() if c]
    cons = [cmap[s] for s in signs]
    rng.shuffle(cons)
    for s, c in zip(signs, cons):
        cmap[s] = c
    return cmap
