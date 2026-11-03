#!/usr/bin/env python3
"""D7 structural follow-on, controls only: S1's edge alternation and S3's -RE/-TE counts on each rival language's own
running text (docs/d7-structural-preregistration.md, rulings T1-T5). No Linear A word is read here: S3's Linear A run
is d7_s3_linear_a.py.

    d7_structural_controls.py --out FILE [--sizes 500,1000,1500,2000] [--draws 1000] [--perm 2000] [--seed 20261102]

Texts (none ships in this repository; the paths are tools/ane/aneq.py's):
- Hattic, Hurrian and Luwian: TLHdig 0.3's word rows, `preserved` only.
- Ugaritic: AEMW/Ugarit's wholly alphabetic documents.
- Egyptian: ORAEC/TLA's sentence transliterations.

Every word becomes a key: a flag for a written initial vowel, then its consonants. A cuneiform geminate written
across a sign boundary (at-ti) is one consonant; the alphabetic scripts write none.

S1 reads each key as the series that writes it. A guttural or an initial vowel is a bare-vowel token V; any other
consonant takes the series its own arm's table picks (A9's series_consonant; the Semitic table for Ugaritic, each
competitor's loaded table for the rivals). L, the left-edge share of one- and two-token edge pairs, is drawn at each
size, and the gate asks whether Hattic's central 95% interval is clear of Ugaritic's and of Hurrian's.

S3 spells each key with A9's competitor speller (open pattern, one seeded spelling per type) and counts the X-TE/X-RE
and X/X-TE stems against a permutation of final signs within each word length. On these texts it calibrates the null
only: the speller drops codas, so Hattic's reduced =l and =t go unwritten.

Report-only: reads the three text layers, writes only --out, and refuses an existing --out. Exit 2 for an existing
--out, 3 for a text layer not in this checkout.

Attribution: di Mino
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import time
import unicodedata
from collections import Counter, defaultdict
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    __package__ = "tools.linear_a.validation"

from ...ane.aneq import EGY_SENTS as EGYPTIAN
from ...ane.aneq import ORACC_DOCS, TLHDIG_WORDS
from ...core import competitors as cp
from ...core import root_match as rm
from .root_match_checks import competitor_series, lb_series, open_pattern, series_consonant, spell

SEED = 20261102
TLH_CODES = {"hattic": ("Hat", "Hattian"), "hurrian": ("Hur",), "luwian": ("Luw",)}
LANGUAGES = ("ugaritic", "hattic", "hurrian", "luwian", "egyptian")
Key = tuple[bool, tuple[str, ...]]

_VOWELS = frozenset("aeiou")
_SUBSCRIPTS = frozenset("₀₁₂₃₄₅₆₇₈₉")    # sign indices (ša₂), not numerals
_DAMAGE = frozenset("[]⸢⸣<>{}()?!…+x*/|#")
_WEAK = {"i̯": "j", "u̯": "w"}            # Egyptological weak radicals (NFD i, u with the inverted breve below)


def _base(letter: str) -> str:
    return unicodedata.normalize("NFD", letter)[0]


def _valid(initial: bool, cons: list[str]) -> Key | None:
    return (initial, tuple(cons)) if cons and len(cons) + initial >= 2 else None


def cuneiform_key(surface: str) -> Key | None:
    """A TLHdig surface (signs joined by "-"): None for a logogram, a determinative (any capital), a number or a
    damage mark. Sign-index accents and subscripts drop; vowels drop, an initial one kept as the flag."""
    s = unicodedata.normalize("NFC", surface or "")
    if not s or any(c in _DAMAGE or (c.isdigit() and c not in _SUBSCRIPTS) or c.isupper() for c in s):
        return None
    signs = [sg for sg in s.split("-") if sg]
    cons: list[str] = []
    initial = False
    for i, sign in enumerate(signs):
        toks = [rm.letter_token(lt) for lt in rm.letters(sign)]
        toks = [t for t in toks if t]
        if not toks:
            return None
        if i == 0 and toks[0] in _VOWELS:
            initial = True
        cs = [t for t in toks if t not in _VOWELS]
        if cs and cons and cons[-1] == cs[0] and _ends_in_consonant(signs[i - 1]):
            cs = cs[1:]                     # at-ti: the geminate is written, not spoken twice
        cons.extend(cs)
    return _valid(initial, cons)


def _ends_in_consonant(sign: str) -> bool:
    toks = [t for t in (rm.letter_token(lt) for lt in rm.letters(sign)) if t]
    return bool(toks) and toks[-1] not in _VOWELS


def ugaritic_key(word: str) -> Key | None:
    """An AEMW alphabetic word: the aleph signs' vowels (ʾa, ʾi, ʾu) drop; damage or a number gives None."""
    if not word or any(c in _DAMAGE or c.isdigit() for c in word):
        return None
    toks = [t for t in (rm.letter_token(lt) for lt in rm.letters(word)) if t]
    return _valid(False, [t for t in toks if t not in _VOWELS])


def egyptian_key(word: str) -> Key | None:
    """An ORAEC transliteration word: separators (, . - =) drop, i̯ and u̯ are j and w. A capitalised word is a
    name and gives None, as a determinative takes a name out of the cuneiform texts; a number or damage, too."""
    if not word or word[0].isupper() or any(c in _DAMAGE or c.isdigit() for c in word):
        return None
    cons: list[str] = []
    for lt in rm.letters(word.replace(",", "").replace(".", "").replace("-", "").replace("=", "")):
        t = _WEAK.get(unicodedata.normalize("NFC", lt)) or rm.letter_token(lt)
        if t is None:
            continue
        if t in _VOWELS:
            return None
        cons.append(t)
    return _valid(False, cons)


def series_tokens(key: Key, sub: Callable[[str, str], float], series: dict[str, dict[str, str]]) -> tuple[str, ...]:
    initial, cons = key
    out = ["V"] if initial else []
    for c in cons:
        out.append("V" if c in rm.GUTTURAL_PHONEMES else series_consonant(c, series, sub))
    return tuple(out)


def spell_key(key: Key, rng: random.Random, series: dict[str, dict[str, str]],
              sub: Callable[[str, str], float]) -> tuple[str, ...]:
    """A9's competitor spelling of a key (open pattern), with a written initial vowel as a first vowel sign."""
    initial, cons = key
    pattern, trailing = open_pattern(cons)
    if initial:
        pattern = [("V", "V"), *pattern]
    return tuple(spell(pattern, trailing, rng, series, sub).split("-"))


def edge_pairs(words: Iterable[tuple[str, ...]]) -> tuple[int, int]:
    """(left, right): pairs in which the longer word is the shorter, of at least two tokens, with one or two tokens
    added before it (left) or after it (right)."""
    ws = set(words)
    left = right = 0
    for u in ws:
        for k in (1, 2):
            if len(u) - k < 2:
                continue
            left += u[k:] in ws
            right += u[:-k] in ws
    return left, right


def l_share(left: int, right: int) -> float | None:
    return left / (left + right) if left + right else None


def sample_shares(types: list[tuple[str, ...]], n: int, draws: int, seed: int) -> dict[str, Any]:
    if len(types) < n:
        return {"limited": True, "types": len(types)}
    rng = random.Random(seed)
    pool = sorted(types)
    shares = [l_share(*edge_pairs(rng.sample(pool, n))) for _ in range(draws)]
    return {"limited": False, "types": len(types), "shares": shares}


def interval(xs: list[float]) -> tuple[float, float] | None:
    """The central 95% interval, linear interpolation between order statistics (numpy's default)."""
    v = sorted(x for x in xs if x is not None)
    if not v:
        return None

    def q(p: float) -> float:
        pos = p * (len(v) - 1)
        lo = int(pos)
        hi = min(lo + 1, len(v) - 1)
        return round(v[lo] + (v[hi] - v[lo]) * (pos - lo), 6)
    return q(0.025), q(0.975)


def gate(iv: dict[str, tuple[float, float] | None]) -> dict[str, bool]:
    """T4: Hattic's interval disjoint from Hurrian's and from Ugaritic's; both, or S1 is not run on Linear A."""
    h = iv.get("hattic")

    def clear(other: str) -> bool:
        o = iv.get(other)
        return h is not None and o is not None and (h[1] < o[0] or o[1] < h[0])
    out = {"hurrian": clear("hurrian"), "ugaritic": clear("ugaritic")}
    out["passes"] = out["hurrian"] and out["ugaritic"]
    return out


def s3_counts(words: Iterable[tuple[str, ...]], te: tuple[str, ...], re: tuple[str, ...]) -> dict[str, int]:
    ws = set(words)
    stems_te = {w[:-1] for w in ws if len(w) >= 2 and w[-1] in te}
    stems_re = {w[:-1] for w in ws if len(w) >= 2 and w[-1] in re}
    return {"te_re": len(stems_te & stems_re), "bare_te": len(stems_te & ws)}


def permute_finals(words: list[tuple[str, ...]], rng: random.Random) -> list[tuple[str, ...]]:
    """The words with their final signs shuffled among the words of the same length."""
    by_len: dict[int, list[int]] = defaultdict(list)
    for i, w in enumerate(words):
        by_len[len(w)].append(i)
    out = list(words)
    for idx in by_len.values():
        finals = [words[i][-1] for i in idx]
        rng.shuffle(finals)
        for i, f in zip(idx, finals):
            out[i] = words[i][:-1] + (f,)
    return out


def s3_test(words: list[tuple[str, ...]], te: tuple[str, ...], re: tuple[str, ...], n_perm: int,
            seed: int) -> dict[str, dict[str, float]]:
    obs = s3_counts(words, te, re)
    rng = random.Random(seed)
    sums: Counter = Counter()
    ge: Counter = Counter()
    for _ in range(n_perm):
        c = s3_counts(permute_finals(words, rng), te, re)
        for k, v in c.items():
            sums[k] += v
            ge[k] += v >= obs[k]
    return {k: {"observed": obs[k], "expected": round(sums[k] / n_perm, 3), "p": round((1 + ge[k]) / (1 + n_perm), 4)}
            for k in obs}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_keys() -> tuple[dict[str, Counter], dict[str, Counter]]:
    """language → Counter of keys (types), and language → Counter of what dropped and why."""
    keys: dict[str, Counter] = {lang: Counter() for lang in LANGUAGES}
    dropped: dict[str, Counter] = {lang: Counter() for lang in LANGUAGES}
    code_of = {c: lang for lang, cs in TLH_CODES.items() for c in cs}
    with TLHDIG_WORDS.open(encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            lang = code_of.get(r.get("language_normalized"))
            if lang is None:
                continue
            if not r.get("preserved"):
                dropped[lang]["not preserved"] += 1
                continue
            k = cuneiform_key(r.get("surface") or "")
            if k is None:
                dropped[lang]["no key"] += 1
            else:
                keys[lang][k] += 1
    with ORACC_DOCS.open(encoding="utf-8") as f:
        for line in f:
            if '"aemw/ugarit"' not in line:
                continue
            d = json.loads(line)
            tl = d.get("token_languages") or {}
            if d.get("source_project") != "aemw/ugarit" or not tl or not all(t.startswith("uga") for t in tl):
                continue
            for ln in d.get("lines") or []:
                for w in str(ln.get("text") or "").split():
                    k = ugaritic_key(w)
                    if k is None:
                        dropped["ugaritic"]["no key"] += 1
                    else:
                        keys["ugaritic"][k] += 1
    with EGYPTIAN.open(encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            for w in str(d.get("transliteration") or "").split():
                k = egyptian_key(w)
                if k is None:
                    dropped["egyptian"]["no key"] += 1
                else:
                    keys["egyptian"][k] += 1
    return keys, dropped


def subs() -> dict[str, Callable[[str, str], float]]:
    """Each language's substitution cost: the Semitic table for Ugaritic, each competitor's loaded table (D14)."""
    out: dict[str, Callable[[str, str], float]] = {"ugaritic": rm._sub}
    for s in cp.COMPETITORS:
        out[s.name] = cp.load(s).sub
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--sizes", default="500,1000,1500,2000")
    ap.add_argument("--draws", type=int, default=1000)
    ap.add_argument("--perm", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=SEED)
    args = ap.parse_args(argv)
    if args.out.exists():
        print(f"{args.out} exists; never overwritten", file=sys.stderr)
        return 2
    sizes = [int(x) for x in args.sizes.split(",") if x]
    missing = [str(p) for p in (TLHDIG_WORDS, ORACC_DOCS, EGYPTIAN) if not p.exists()]
    if missing:
        print(f"text layer not in this checkout: {', '.join(missing)}", file=sys.stderr)
        return 3
    t0 = time.time()
    keys, dropped = read_keys()
    series = lb_series()
    rival_series = competitor_series(series)
    sub = subs()
    report: dict[str, Any] = {
        "draft": "docs/d7-structural-preregistration.md", "args": {**vars(args), "out": str(args.out)},
        "sha256": {p.name: _sha256(p) for p in (TLHDIG_WORDS, ORACC_DOCS, EGYPTIAN)},
        "types": {lang: len(keys[lang]) for lang in LANGUAGES},
        "dropped": {lang: dict(dropped[lang]) for lang in LANGUAGES}, "s1": {}, "s3": {}}
    for lang in LANGUAGES:
        ser = series if lang == "ugaritic" else rival_series
        s1_types = sorted({series_tokens(k, sub[lang], ser) for k in keys[lang]})
        s1_types = [t for t in s1_types if len(t) >= 2]
        full = l_share(*edge_pairs(s1_types))
        per_size = {}
        for n in sizes:
            s = sample_shares(s1_types, n, args.draws, args.seed)
            if s["limited"]:
                per_size[str(n)] = s
                continue
            xs = [x for x in s["shares"] if x is not None]
            per_size[str(n)] = {"limited": False, "mean": round(sum(xs) / len(xs), 4) if xs else None,
                                "interval": interval(xs), "no_pairs": len(s["shares"]) - len(xs)}
        report["s1"][lang] = {"series_types": len(s1_types), "L_full": full and round(full, 4), "sizes": per_size}
        rng = random.Random(args.seed)
        spelled = sorted({spell_key(k, rng, ser, sub[lang]) for k in sorted(keys[lang])})
        report["s3"][lang] = {
            "spelled_types": len(spelled),
            "narrow": s3_test(spelled, ("TE",), ("RE",), args.perm, args.seed),
            "broad": s3_test(spelled, ("TE", "TI"), ("RE", "RI"), args.perm, args.seed)}
        print(f"{lang}: {len(keys[lang])} keys, {len(s1_types)} series types ({time.time() - t0:.0f}s)",
              file=sys.stderr)
    report["gate"] = {str(n): gate({lang: report["s1"][lang]["sizes"][str(n)].get("interval") for lang in LANGUAGES})
                      for n in sizes}
    report["seconds"] = round(time.time() - t0, 1)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"written {args.out} ({report['seconds']}s)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
