"""Protocol C, phase C2: the renderer (§5.5). One renderer for every arm, the controls and the nulls.

Two steps. `phonemes` and `symbols` take a morpheme's segments, in its grammar's own symbols, to consonant series
and vowels by render/series.json (fixed at C0) and render/series-a5-proposed.json (the symbols C0 did not foresee;
proposed, unsigned). `spell` writes a string of series and vowels as sign keys under one of two spelling
conventions: Linear B's omission rules, or plene spelling with echo vowels. A sign key is (series, vowel), with an
empty series for a vowel sign.

The speller is a small machine (`START`, `feed`, `finish`) so that the generator can test whether an inventory
writes a given residue without listing every chain: a consonant waits until the next vowel, or the end of the
chain, says how it is written.

Nothing here reads a Linear A form.

Attribution: di Mino
"""
from __future__ import annotations

import itertools
import json
import unicodedata
from dataclasses import dataclass
from pathlib import Path

RENDER_DIR = Path(__file__).resolve().parent
VOWELS = "aeiou"
STOPS = frozenset("PTDKQ")
FIRST_OMITTED = frozenset("SRMN")        # s, liquid and nasal, unwritten before a stop (§5.5 item 2)
CONVENTIONS = ("omission", "plene")
C0_VOWELS = {"ə": "e"}                   # stated in series.json's prose
_LENGTH = {"̄", "̆"}            # macron, breve: a long or anceps vowel is its short vowel

Key = tuple[str, str]
State = tuple[tuple[str, ...], "str | None"]


class UnmappedSegment(ValueError):
    """A segment the tables do not map. The renderer never guesses a series."""


@dataclass(frozen=True)
class Tables:
    map: dict[str, str]
    overrides: dict[str, dict[str, str]]
    vowels: dict[str, str]
    length_marks: tuple[str, ...]
    any_vowel: str


def _nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def load_tables(render_dir: Path = RENDER_DIR) -> Tables:
    base = json.loads((render_dir / "series.json").read_text(encoding="utf-8"))
    ext = json.loads((render_dir / "series-a5-proposed.json").read_text(encoding="utf-8"))
    clash = set(map(_nfc, base["map"])) & set(map(_nfc, ext["map"]))
    if clash:
        raise ValueError(f"the proposed rows restate C0 keys: {sorted(clash)}")
    table = {_nfc(k): v for k, v in {**base["map"], **ext["map"]}.items()}
    over: dict[str, dict[str, str]] = {}
    for source in (base["arm_overrides"], ext["arm_overrides"]):
        for arm, rows in source.items():
            over.setdefault(arm, {}).update({_nfc(k): v for k, v in rows.items()})
    vowels = {_nfc(k): v for k, v in {**C0_VOWELS, **ext["vowels"]}.items()}
    return Tables(table, over, vowels, tuple(ext["length_marks"]), ext["any_vowel"])


def _vowel(seg: str, t: Tables) -> str | None:
    for mark in t.length_marks:
        seg = seg.replace(mark, "")
    if seg in t.vowels:
        return t.vowels[seg]
    if seg == t.any_vowel:
        return seg
    base, *marks = unicodedata.normalize("NFD", seg)
    return base if base in VOWELS and set(marks) <= _LENGTH else None


def is_vowel(phoneme: str, t: Tables) -> bool:
    return phoneme in VOWELS or phoneme == t.any_vowel


def _series(cons: str, arm: str, t: Tables) -> str:
    """An arm's own row comes before the general one, and a doubled consonant is its single consonant."""
    n = len(cons) // 2
    half = cons[:n] if n and cons[:n] == cons[n:] else None
    for table in (t.overrides.get(arm, {}), t.map):
        if cons in table:
            return table[cons]
        if half in table:
            return table[half]
    raise UnmappedSegment(f"{arm}: no series for {cons!r}")


def phonemes(segments, arm: str, t: Tables) -> tuple[str, ...]:
    """One entry's segments as phonemes: vowels as a, e, i, o, u or the cover vowel; a digraph the builder split
    joined again; a doubled consonant written once. Consonants keep the grammar's symbol."""
    rows = t.overrides.get(arm, {})
    out: list[str] = []
    for seg in map(_nfc, segments):
        v = _vowel(seg, t)
        if v is not None:
            out.append(v)
        elif out and not is_vowel(out[-1], t) and (out[-1] == seg or len(out[-1] + seg) > 1 and (
                out[-1] + seg in rows or out[-1] + seg in t.map)):
            out[-1] = seg if out[-1] == seg else out[-1] + seg
        else:
            out.append(seg)
    for p in out:
        if not is_vowel(p, t):
            _series(p, arm, t)
    return tuple(out)


def symbols(phon, arm: str, t: Tables) -> list[tuple[str, ...]]:
    """Phonemes as series and vowels. A zero onset is dropped; the cover vowel gives one string per vowel."""
    slots: list[tuple[str, ...]] = []
    for p in phon:
        if p == t.any_vowel:
            slots.append(tuple(VOWELS))
        elif p in VOWELS:
            slots.append((p,))
        else:
            s = _series(p, arm, t)
            if s != "ZERO":
                slots.append((s,))
    return [tuple(c) for c in itertools.product(*slots)]


def word(segments, language: str, t: Tables, convention: str) -> tuple[Key, ...] | None:
    """A whole word of a known-language text as sign keys (§9.1), or None when it cannot be written: a segment the
    tables do not map, a cover vowel, or, under plene, no vowel for a consonant to take. `language` picks the
    arm's rows of the tables; a language with no rows of its own (Hebrew, Ugaritic) reads the general ones."""
    try:
        alts = symbols(phonemes(segments, language, t), language, t)
    except UnmappedSegment:
        return None
    if len(alts) != 1 or not alts[0]:
        return None
    return spell(alts[0], "suffix", convention)


def START(prev_vowel: str | None) -> State:
    """No consonant waiting; `prev_vowel` is the vowel before the chain, if the chain follows a stem."""
    return (), prev_vowel


def feed(state: State, symbol: str, convention: str) -> tuple[State, tuple[Key, ...]]:
    """Give the machine one series or vowel; get the new state and the signs now certain."""
    waiting, last = state
    if symbol not in VOWELS:
        return (waiting + (symbol,), last), ()
    if not waiting:
        return ((), symbol), (("", symbol),)
    out = [(c, symbol) for c, nxt in zip(waiting, waiting[1:])
           if not (convention == "omission" and c in FIRST_OMITTED and nxt in STOPS)]
    return ((), symbol), (*out, (waiting[-1], symbol))


def finish(state: State, side: str, convention: str, next_vowel: str | None = None,
           next_stop: bool = False) -> tuple[Key, ...] | None:
    """The signs of the consonants still waiting when the chain ends, or None when they cannot be written.

    A suffix ends the word: the consonants are unwritten (omission) or echo the vowel before them (plene). A
    prefix runs into the stem: each consonant takes the stem's first vowel, unless the omission rule drops it."""
    waiting, last = state
    if not waiting:
        return ()
    if side == "suffix":
        if convention == "omission":
            return ()
        return None if last is None else tuple((c, last) for c in waiting)
    out = []
    for i, c in enumerate(waiting):
        stop = waiting[i + 1] in STOPS if i + 1 < len(waiting) else next_stop
        if convention == "omission" and c in FIRST_OMITTED and stop:
            continue
        if next_vowel is None:
            return None
        out.append((c, next_vowel))
    return tuple(out)


def spell(symbols_: tuple[str, ...], side: str, convention: str, *, prev_vowel: str | None = None,
          next_vowel: str | None = None, next_stop: bool = False) -> tuple[Key, ...] | None:
    """A whole chain's sign keys under one convention, or None when the convention cannot write it."""
    state, out = START(prev_vowel), ()
    for s in symbols_:
        state, emitted = feed(state, s, convention)
        out += emitted
    tail = finish(state, side, convention, next_vowel, next_stop)
    return None if tail is None else out + tail
