"""Shoresh root index: every Semitic root key, projected once into what Linear A can write.

``semitic_roots.json`` and the Semitic contact lexica are read into SQLite (stdlib only, so cognate_search can
load it):

  roots              Number, PS headword, meaning
  analogues          Number, language, branch, the Analogues string as filed (citations included)
  unkeyed_analogues  Number, language, text, reason: an Analogues entry that gave no key (placeholder, no_form,
                     no_key, not_a_string), so a branch the index cannot count is listed, never silently lost
  lexemes            one row per contact-lexicon entry: lexicon, language, branch, form, meaning, POS, onomastic
                     flag, cognates as filed, sha256 of the row
  root_keys          one row per radical key: kind ps | weak | reflex (a Number) or lexeme (a lexeme id),
                     language, branch, radicals, shadow key, flags (phrase, overlong, onomastic, proxy_supplement,
                     no_class:<letter> ...)
  lexeme_links       lexeme → Number, with its basis: fk (the lexicon's own semitic_roots_ref), root_key_exact or
                     root_key_reduced (match_root_key against every PS key the lexeme's consonants can continue),
                     and whether the glosses share a word. Links are evidence for clustering, never a merge on
                     sound alone.
  record_hashes      sha256 per Number per field (Proto-Semitic, Meaning, Notes, Analogues/<language>)
  provenance         sha256 of every input (data and key-logic code), git head, build time, counts

The shadow key folds each radical into the consonant classes Linear A's syllabary keeps apart (SHADOW_CLASS) and
drops the gutturals, which Linear A spells optionally: *š-m-ʿ, Hebrew šmʿ and Akkadian šmʾ (šemû) all fall in
bucket SM. Retrieval is a hash lookup over the key and its one-deletion neighbours; the fine contrasts (values
beyond Linear B such as PA₃ = b, proposed, and *118 = ṭ, speculative; the sibilant series, the gutturals) are scored afterwards, never at retrieval.
Keys come from the existing resolvers: ps_radical_keys and weak_variants for headwords, analogue_forms and
daughter_root_pattern for reflexes and lexemes, semitic_notation underneath.

    from tools.core.root_index import RootIndex, shadow_key
    idx = RootIndex.load()                    # raises IndexStale if any input changed since the build
    idx.candidates(shadow_key(("š", "m", "ʿ"))[0])
    RootIndex.load(include_lexemes=False)     # semitic_roots keys only; lexicon edits do not make it stale

Attribution: di Mino
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import subprocess
import unicodedata
from collections import Counter
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from itertools import combinations, islice, product
from pathlib import Path
from typing import Any

try:
    from ..paths import CACHE, CONTACT_DATA, REPO, SEMITIC_ROOTS_DATA, require
    from .semitic_root_schema import (
        _CORRESPONDENCES,
        RootPattern,
        analogue_forms,
        daughter_root_pattern,
        is_analogue_language_key,
        language_branch,
        match_root_key,
        ps_radical_keys,
        roots_records,
        weak_variants,
    )
except ImportError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from tools.core.semitic_root_schema import (
        _CORRESPONDENCES,
        RootPattern,
        analogue_forms,
        daughter_root_pattern,
        is_analogue_language_key,
        language_branch,
        match_root_key,
        ps_radical_keys,
        roots_records,
        weak_variants,
    )
    from tools.paths import CACHE, CONTACT_DATA, REPO, SEMITIC_ROOTS_DATA, require

CORE_DIR = Path(__file__).resolve().parent
CONTACT_DIR = CONTACT_DATA
DEFAULT_ROOTS = SEMITIC_ROOTS_DATA / "semitic_roots.json"
DEFAULT_INDEX = CACHE / "root_index.sqlite"     # built locally from the shipped data; never in the repository
SCHEMA_VERSION = 3
MISSING = "missing"            # lexicon_sha256 of a lexicon absent at build time: its arrival makes the index stale
MAX_KEY_RADICALS = 6           # longer lexeme keys are compounds, phrases or prose: kept, flagged overlong

# Files whose change can change a key. A rebuilt index is stale the moment any of them differs.
KEY_LOGIC_FILES = (
    _CORRESPONDENCES,
    CORE_DIR / "semitic_root_schema.py",
    CORE_DIR / "semitic_notation.py",
    CORE_DIR / "root_index.py",
)

# Retrieval classes. Linear A keeps K (k g q), P (p b), R (r l) and m n w y apart; T folds t d ṭ although Linear A
# writes a D series, because Semitic t/d/ṭ alternate across branches and the contrast is scored, not retrieved;
# one broad S/Z class (which PS sibilant a sign continues is scored, never assumed). Daughter-only reflexes join
# the class of their PS source: Arabic/Geʿez f < *p, ǧ < *g, ḍ < *ṣ́, Ethiopic palatals, MSA laterals.
SHADOW_CLASS: dict[str, str] = {
    **dict.fromkeys(("k", "g", "q", "ǧ"), "K"),
    **dict.fromkeys(("t", "d", "ṭ", "ɗ"), "T"),
    **dict.fromkeys(("p", "b", "f", "v"), "P"),
    **dict.fromkeys(("r", "l"), "R"),
    **dict.fromkeys(("s", "z", "ṣ", "š", "ś", "ṯ", "ḏ", "ẓ", "ṣ́", "s₁", "s₂", "s₃", "ḍ", "ź", "ž", "č", "č̣",
                     "ḏ̣", "ǯ", "j", "c"), "S"),
    "m": "M", **dict.fromkeys(("n", "ñ", "ň"), "N"), "w": "W", "y": "Y",
    "ɫ": "R",
}
# Optional slots: dropped from the shadow key, restored in rescoring (cognate_search's guttural transparency).
# ʁ (Harsusi) and γ (Modern Aramaic transcription) write ġ.
GUTTURALS = frozenset(("ʾ", "ʿ", "h", "ḥ", "ḫ", "ġ", "x", "ʁ", "γ"))
# Vowel letters the radical tokenizer passes through in Modern Aramaic transcriptions (dɨdwā, dıba).
_VOWEL_LEAKS = frozenset(("ɨ", "ı"))

# Semitic Analogues languages the correspondence table has no proxy for, given the nearest column under the
# table's own convention (proxies follow phonology, not subgrouping: Amorite → Hebrew). Proposed for
# semitic_correspondences.json; kept here until adopted there. Keys built through one carry proxy_supplement.
# Palaeosyrian is written in cuneiform that marks neither voicing nor emphasis: its keys also carry
# script_underdetermined.
PROXY_SUPPLEMENT = {
    "Moabite": "Hebrew", "Nabataean": "Aramaic", "Modern South Arabian": "Mehri", "East Semitic": "Akkadian",
    "Palaeosyrian": "Akkadian", "Lihyanite": "Arabic", "Pre-Islamic North Arabian": "Arabic",
}
_UNDERDETERMINED_SCRIPT = frozenset({"Palaeosyrian"})
# Afroasiatic and loan comparanda filed under Analogues. Indexed (branch non_semitic) so the engine can show
# them, never counted as Semitic attestation.
NON_SEMITIC = frozenset({"Egyptian", "Greek", "Libyco-Berber", "Cushitic", "West Cushitic", "Hausa", "Oromo",
                         "Tuareg"})


@dataclass(frozen=True)
class Lexicon:
    """One contact lexicon: where it is, the language its forms are read as (through branch_of), the
    semitic_notation scheme, and the fields that carry a root or form, in order (every non-empty one is keyed)."""
    name: str
    path: Path
    language: str
    scheme: str
    fields: tuple[str, ...]
    onomastic: bool = False


# Semitic contact lexica. Not indexed: huehnergard_glossary (already merged into ugaritic_lexicon),
# krahmalkov_glossary and tomback_extracted (superseded by the merged phoenician_lexicon), cultic_register (no
# language field), mari_onomastics (26 name elements). Egyptian, Luwian and Hurrian are the competitor indexes
# (competitors.py), Greek is not a source language. The CAD headwords, Gelb's Amorite glossary, Harding's
# Arabian names and the Phoenician drawn from the Anchor Bible commentaries are closed sources and are not listed.
LEXICA: tuple[Lexicon, ...] = (
    Lexicon("ugaritic", CONTACT_DIR / "ugaritic_lexicon.jsonl", "Ugaritic", "ugaritic", ("normalized",)),
    Lexicon("hebrew", CONTACT_DIR / "hebrew_lexicon.jsonl", "Hebrew", "hebrew", ("root", "normalized")),
    Lexicon("aramaic", CONTACT_DIR / "aramaic_lexicon.jsonl", "Aramaic", "aramaic", ("root", "normalized")),
    Lexicon("syriac", CONTACT_DIR / "syriac_lexicon.jsonl", "Syrian Aramaic", "aramaic", ("root",)),
    Lexicon("geez", CONTACT_DIR / "geez_lexicon.jsonl", "Geez", "geez_latin", ("root", "normalized")),
    Lexicon("south_arabian", CONTACT_DIR / "south_arabian_lexicon.jsonl", "Epigraphic South Arabian", "dasi",
            ("normalized",)),
    Lexicon("phoenician", CONTACT_DIR / "phoenician_lexicon.jsonl", "Phoenician", "phoenician",
            ("root", "normalized")),
    Lexicon("akkadian", CONTACT_DIR / "akkadian_lexicon.jsonl", "Akkadian", "akkadian",
            ("root_consonants", "normalized")),
    Lexicon("amarna", CONTACT_DIR / "amarna_canaanite.jsonl", "Canaanite", "hebrew", ("normalized",)),
    Lexicon("amorite_vocabulary", CONTACT_DIR / "amorite_vocabulary.jsonl", "Amorite", "amorite_gk",
            ("root", "form_original")),
    Lexicon("phoenician_onomasticon", CONTACT_DIR / "phoenician_onomasticon.jsonl", "Phoenician", "phoenician",
            ("normalized",), onomastic=True),
)
# Entries in an ordinary lexicon that are names, by their own POS tag.
ONOMASTIC_POS = frozenset({"personal_name", "proper_noun", "GN", "PN", "DN", "RN", "TN", "toponym",
                           "divine_name", "ethnonym", "name_element", "royal_name"})


class IndexStale(RuntimeError):
    """An input changed after the index was built. Never answered from the old index."""


# ---------------------------------------------------------------------------
# keys
# ---------------------------------------------------------------------------

def _base_letter(r: str) -> str:
    """The radical without combining marks or subscripts: spirantised ḇ ḵ p̄, MSA s̃ ẓ̂ c̣, Tigre ş."""
    return "".join(ch for ch in unicodedata.normalize("NFD", r)
                   if not unicodedata.category(ch).startswith("M") and ch not in "₀₁₂₃₄₅₆₇₈₉")


def _classify(r: str) -> str | None:
    """Class letter, "" for an optional slot, None when the radical has no Linear A class."""
    for cand in (r, unicodedata.normalize("NFC", r), _base_letter(r)):
        if cand in GUTTURALS or cand in _VOWEL_LEAKS:
            return ""
        if cand in SHADOW_CLASS:
            return SHADOW_CLASS[cand]
    return None


def shadow_key(radicals: Iterable[str]) -> tuple[str, tuple[str, ...]]:
    """(shadow, radicals with no class). Gutturals drop; a radical with no class (Greek letters in non-Semitic
    comparanda) keeps a '?' slot and is reported. A marked letter takes its base letter's class."""
    out, unmapped = [], []
    for r in radicals:
        cls = _classify(r)
        if cls is None:
            unmapped.append(r)
            cls = "?"
        out.append(cls)
    return "".join(out), tuple(unmapped)


def deletion_neighbours(shadow: str) -> set[str]:
    """The key and every string one class shorter. Two keys within one class edit share a member; so do a few
    two-edit pairs (AXB / ABC share AB), which rescoring discards. A superset, never a miss."""
    return {shadow} | {shadow[:i] + shadow[i + 1:] for i in range(len(shadow))}


def _deletions(shadow: str, up_to: int) -> list[str]:
    """The key and every string up to `up_to` classes shorter, sorted."""
    out = {shadow}
    for k in range(1, min(up_to, len(shadow)) + 1):
        for drop in combinations(range(len(shadow)), k):
            out.add("".join(c for i, c in enumerate(shadow) if i not in drop))
    return sorted(out)


def branch_of(language: str) -> tuple[str | None, str | None, list[str]]:
    """(branch, language to read the form as, flags)."""
    if language in NON_SEMITIC:
        return "non_semitic", language, []
    branch = language_branch(language)
    if branch:
        return branch, language, []
    if language in PROXY_SUPPLEMENT:
        flags = ["proxy_supplement"] + (["script_underdetermined"] if language in _UNDERDETERMINED_SCRIPT else [])
        return PROXY_SUPPLEMENT[language], PROXY_SUPPLEMENT[language], flags
    return None, language, []


@dataclass(frozen=True)
class KeyRow:
    number: str | None        # the semitic_roots Number; None for a lexeme key
    kind: str                 # ps | weak | reflex | lexeme
    label: str | None         # weak-variant label (I-w/y, hollow, III-weak, geminate ...)
    language: str             # "Proto-Semitic" for ps and weak keys
    branch: str | None
    radicals: tuple[str, ...]
    shadow: str
    form: str                 # the headword, reflex or lexicon form the key was read from
    flags: tuple[str, ...] = field(default=())
    lexeme_id: str | None = None


def _nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def _sha(value: Any) -> str:
    return hashlib.sha256(_nfc(json.dumps(value, ensure_ascii=False, sort_keys=True)).encode()).hexdigest()


class _Keys:
    """Collects KeyRows for one record or lexeme, deduplicated on (kind, language, radicals)."""

    def __init__(self, number: str | None, lexeme_id: str | None = None):
        self.number, self.lexeme_id = number, lexeme_id
        self.rows: list[KeyRow] = []
        self._seen: set[tuple[str, str, tuple[str, ...]]] = set()

    def add(self, kind: str, label: str | None, language: str, branch: str | None, radicals: Iterable[str],
            form: str, flags: Iterable[str] = ()) -> None:
        radicals = tuple(radicals)
        if not radicals or (kind, language, radicals) in self._seen:
            return
        self._seen.add((kind, language, radicals))
        shadow, unmapped = shadow_key(radicals)
        flags = list(flags) + [f"no_class:{u}" for u in unmapped]
        if kind == "lexeme" and len(radicals) > MAX_KEY_RADICALS:
            flags.append("overlong")
        self.rows.append(KeyRow(self.number, kind, label, language, branch, radicals, shadow, form,
                                tuple(dict.fromkeys(flags)), self.lexeme_id))


def _record_keys(rec: dict[str, Any]) -> tuple[list[KeyRow], list[tuple[str, str, Any]]]:
    """(keys, gaps). A gap is an Analogues entry that gave no key: (language, reason, text as filed)."""
    number = str(rec["Number"])
    ps = rec.get("Proto-Semitic") or ""
    keys = _Keys(number)
    gaps: list[tuple[str, str, Any]] = []
    ps_keys = ps_radical_keys(ps)
    for key in ps_keys:
        keys.add("ps", None, "Proto-Semitic", "PS", key, ps)
    for key in ps_keys:
        for variant, label in weak_variants(key).items():
            if variant not in ps_keys:
                keys.add("weak", label, "Proto-Semitic", "PS", variant, ps)

    for language, text in (rec.get("Analogues") or {}).items():
        if not is_analogue_language_key(language) or text in (None, "", [], {}):
            continue
        if not isinstance(text, str):
            gaps.append((language, "not_a_string", text))
            continue
        if not text.strip():
            continue
        if not re.search(r"[^\W\d_]", text):
            gaps.append((language, "placeholder", text))               # +, --, ?: presence marks, no form
            continue
        branch, read_as, extra = branch_of(language)
        forms, scheme = analogue_forms(_nfc(text), number, language)
        if not forms:
            gaps.append((language, "no_form", text))
            continue
        n_before = len(keys.rows)
        for form in forms:
            pattern = daughter_root_pattern(form, read_as, scheme)
            flags = [f for f in pattern.flags if not (extra and f == "no_branch")] + extra
            for tokens in pattern.tokens:
                keys.add("reflex", None, language, branch, tokens, form, flags)
        if len(keys.rows) == n_before and not any(k.kind == "reflex" and k.language == language for k in keys.rows):
            gaps.append((language, "no_key", text))
    return keys.rows, gaps


def record_keys(rec: dict[str, Any]) -> list[KeyRow]:
    """Every key of one semitic_roots record, PS first, deduplicated on (kind, language, radicals)."""
    return _record_keys(rec)[0]


def record_key_gaps(rec: dict[str, Any]) -> list[tuple[str, str]]:
    """(language, reason) for every Analogues entry of one record that gave no key."""
    return [(language, reason) for language, reason, _ in _record_keys(rec)[1]]


def record_hashes(rec: dict[str, Any]) -> dict[str, str]:
    """sha256 per field of one record, over NFC JSON with sorted keys. Analogues hash per language."""
    out = {f: _sha(rec[f]) for f in ("Proto-Semitic", "Meaning", "Notes") if f in rec}
    for language, text in (rec.get("Analogues") or {}).items():
        out[f"Analogues/{language}"] = _sha(text)
    return out


# ---------------------------------------------------------------------------
# lexemes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Lexeme:
    id: str                   # "<lexicon>:<the entry's own id>"
    lexicon: str
    language: str
    branch: str | None
    form: str
    meaning: str
    pos: str | None
    onomastic: bool
    cognates: Any
    refs: tuple[str, ...]     # the entry's own semitic_roots_ref Numbers
    sha256: str
    forms: tuple[str, ...]    # the keyed field values
    phrase: bool = False      # the entry's form is several words (aban kitti, ina qāti): keyed, never linked


def iter_lexemes(lex: Lexicon, data: bytes | None = None, skipped: Counter | None = None) -> Iterator[Lexeme]:
    """Entries of one lexicon, from `data` when given (the bytes already hashed) or the file. A repeated id gets
    #2, #3 ... (the first free suffix, so every entry keeps a distinct id; the suffix follows file order, an
    entry without an id is line<N>); CAD ghost words drop and are counted in `skipped`."""
    used: set[str] = set()
    branch = branch_of(lex.language)[0]
    text = (data if data is not None else lex.path.read_bytes()).decode("utf-8")
    for line_no, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except ValueError as e:
            raise ValueError(f"{lex.path.name}:{line_no}: {e}") from e
        if rec.get("ghost"):
            if skipped is not None:
                skipped["ghost"] += 1
            continue
        base = f"{lex.name}:{rec.get('id') or f'line{line_no}'}"
        lid, n = base, 1
        while lid in used:
            n += 1
            lid = f"{base}#{n}"
        used.add(lid)
        forms = tuple(dict.fromkeys(_nfc(str(rec[f])).strip() for f in lex.fields
                                    if isinstance(rec.get(f), str) and rec[f].strip()))
        pos = rec.get("pos")
        refs = rec.get("semitic_roots_ref")
        refs = [] if refs in (None, "", []) else refs if isinstance(refs, list) else [refs]
        form = str(rec.get("form_original") or rec.get("headword") or rec.get("form") or (forms[0] if forms else ""))
        yield Lexeme(
            lid, lex.name, lex.language, branch, form,
            str(rec.get("meaning") or rec.get("gloss") or ""), pos if isinstance(pos, str) else None,
            lex.onomastic or pos in ONOMASTIC_POS, rec.get("cognates"),
            tuple(str(r) for r in refs if str(r).strip()), _sha(rec), forms, _is_phrase(form))


_HOMOGRAPH_NUMERAL = re.compile(r"\s+[IVX]+$")                    # ʾB I, ʾY III
_WORD_GAP = re.compile(r"[^\W\d_]\s+[^\W\d_]")                    # letter, space, letter (not ḤT ́M)


def _is_phrase(form: str) -> bool:
    """Several words in one of the form's comma-separated alternatives: aban kitti, ʾḤR ʾŠ, אָבֵל הַשִּׁטִּים."""
    return any(_WORD_GAP.search(part.strip()) for part in _HOMOGRAPH_NUMERAL.sub("", form.strip()).split(","))


def lexeme_keys(lexeme: Lexeme, scheme: str) -> tuple[list[KeyRow], list[RootPattern]]:
    """(keys, the RootPattern of each keyed form). Every reading daughter_root_pattern gives is a key."""
    _, read_as, extra = branch_of(lexeme.language)
    keys = _Keys(None, lexeme.id)
    patterns = []
    for form in lexeme.forms:
        pattern = daughter_root_pattern(form, read_as, scheme)
        patterns.append(pattern)
        flags = [f for f in pattern.flags if not (extra and f == "no_branch")] + extra
        if lexeme.onomastic:
            flags.append("onomastic")
        if lexeme.phrase:
            flags.append("phrase")
        for tokens in pattern.tokens:
            keys.add("lexeme", None, lexeme.language, lexeme.branch, tokens, form, flags)
    return keys.rows, patterns


_GLOSS_STOP = frozenset({"the", "and", "for", "with", "from", "one", "who", "which", "that", "this", "something",
                         "someone", "etc", "esp", "also", "make", "cause", "become", "have", "been", "into", "out",
                         "name", "word", "kind", "type", "used", "see", "not", "its", "his", "her", "our"})


def gloss_words(text: str) -> set[str]:
    """Content words of a gloss, cut to five letters so gather / gathering / gathered meet."""
    return {w[:5] for w in re.findall(r"[a-z]{3,}", (text or "").lower()) if w not in _GLOSS_STOP}


# ---------------------------------------------------------------------------
# linking
# ---------------------------------------------------------------------------

_LINK_RANK = {"fk": 0, "fk_dangling": 0, "root_key_exact": 1, "root_key_reduced": 2}
_MAX_SHADOW_COMBOS = 64
_LINK_DELETIONS = 1


class _PSLookup:
    """PS keys by shadow, and by every shadow one class shorter (a PS weak radical or geminate the daughter
    lost, *qwm → qm)."""

    def __init__(self) -> None:
        self.exact: dict[str, list[tuple[str, tuple[str, ...]]]] = {}
        self.one_short: dict[str, list[tuple[str, tuple[str, ...]]]] = {}

    def add(self, number: str, radicals: tuple[str, ...], shadow: str) -> None:
        self.exact.setdefault(shadow, []).append((number, radicals))
        for v in sorted(deletion_neighbours(shadow) - {shadow}):
            self.one_short.setdefault(v, []).append((number, radicals))

    def candidates(self, shadows: Iterable[str]) -> list[tuple[str, tuple[str, ...]]]:
        """PS keys a daughter with one of these shadows can continue: the same shadow, the shadow with one
        daughter class absorbed (maktab for *ktb), or one PS class lost. match_root_key allows up to MAX_ABSORB
        absorptions, but those visible in the shadow are tried up to _LINK_DELETIONS (a second deletion adds about
        57k reduced links at 1.3% gloss agreement)."""
        out: dict[tuple[str, tuple[str, ...]], None] = {}
        for s in sorted(set(shadows)):
            for v in _deletions(s, _LINK_DELETIONS):
                out.update(dict.fromkeys(self.exact.get(v, ())))
            out.update(dict.fromkeys(self.one_short.get(s, ())))
        return list(out)


def _pattern_shadows(pattern: RootPattern) -> set[str]:
    """Every shadow of the PS sources a daughter pattern's consonants can continue (Aramaic t → *t or *ṯ gives
    T and S), with the daughter's own surface shadows."""
    out = {shadow_key(t)[0] for t in pattern.tokens}
    for sets in pattern.patterns:
        choices = [sorted({"?" if (c := _classify(p)) is None else c for p in s} or {"?"}) for s in sets]
        out.update("".join(combo) for combo in islice(product(*choices), _MAX_SHADOW_COMBOS))
    return out


def _link_lexeme(lexeme: Lexeme, patterns: list[RootPattern], lookup: _PSLookup, numbers: set[str],
                 cache: dict[tuple, str | None]) -> dict[str, str]:
    """Number → basis. The lexicon's own refs are fk and never overwritten; otherwise the best sound match over
    every keyed form and every PS key it can continue (exact beats reduced). A phrase gets no sound links."""
    links = {ref: "fk" if ref in numbers else "fk_dangling" for ref in lexeme.refs}
    if lexeme.phrase:
        return links
    for form, pattern in zip(lexeme.forms, patterns):
        for number, ps_key in lookup.candidates(_pattern_shadows(pattern)):
            current = links.get(number)
            if current in ("fk", "fk_dangling", "root_key_exact"):
                continue
            ck = (ps_key, form, lexeme.language, lexeme.lexicon)
            if ck not in cache:
                cache[ck] = match_root_key(ps_key, pattern)
            res = cache[ck]
            if res and _LINK_RANK[f"root_key_{res}"] < _LINK_RANK.get(current or "", 9):
                links[number] = f"root_key_{res}"
    return links


# ---------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------

_SCHEMA = """
CREATE TABLE provenance (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE roots (number TEXT PRIMARY KEY, ps TEXT, meaning TEXT);
CREATE TABLE analogues (number TEXT, language TEXT, branch TEXT, text TEXT, PRIMARY KEY (number, language));
CREATE TABLE unkeyed_analogues (number TEXT, language TEXT, text TEXT, reason TEXT NOT NULL,
                                PRIMARY KEY (number, language));
CREATE TABLE lexemes (id TEXT PRIMARY KEY, lexicon TEXT NOT NULL, language TEXT NOT NULL, branch TEXT,
                      form TEXT, meaning TEXT, pos TEXT, onomastic INTEGER NOT NULL, cognates TEXT,
                      sha256 TEXT NOT NULL);
CREATE TABLE root_keys (id INTEGER PRIMARY KEY, number TEXT, lexeme_id TEXT, kind TEXT NOT NULL, label TEXT,
                        language TEXT NOT NULL, branch TEXT, radicals TEXT NOT NULL, shadow TEXT NOT NULL,
                        form TEXT, flags TEXT);
CREATE INDEX root_keys_shadow ON root_keys (shadow);
CREATE INDEX root_keys_number ON root_keys (number);
CREATE TABLE lexeme_links (lexeme_id TEXT NOT NULL, number TEXT NOT NULL, basis TEXT NOT NULL,
                           gloss_overlap INTEGER NOT NULL, PRIMARY KEY (lexeme_id, number));
CREATE INDEX lexeme_links_number ON lexeme_links (number);
CREATE TABLE record_hashes (number TEXT, field TEXT, sha256 TEXT NOT NULL, PRIMARY KEY (number, field));
"""


def _sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return _sha_bytes(path.read_bytes())


def _portable(path: Path) -> str:
    """Repository-relative inside the repository, so an index built on a snapshot of it (§7.7) checks the live
    files. Anything else stays absolute."""
    path = path.resolve()
    try:
        return str(path.relative_to(REPO))
    except ValueError:
        return str(path)


def _resolve(stored: str) -> Path:
    p = Path(stored)
    return p if p.is_absolute() else REPO / p


def _key_logic_hashes() -> dict[str, str]:
    """sha256 per key-logic file; MISSING for one not in the checkout (the correspondence table before it ships),
    whose arrival makes an index stale. write_index refuses to build without it."""
    return {_portable(p): sha256_file(p) if p.exists() else MISSING for p in KEY_LOGIC_FILES}


def input_hashes(roots_path: Path) -> dict[str, str]:
    return {_portable(roots_path): sha256_file(roots_path), **_key_logic_hashes()}


def lexicon_hashes(lexica: Iterable[Lexicon]) -> dict[str, str]:
    """sha256 per lexicon file; MISSING for one that does not exist."""
    return {_portable(lx.path): sha256_file(lx.path) if lx.path.exists() else MISSING for lx in lexica}


# The key-logic code this process runs. Keys come from the modules as imported (and the correspondence table as
# first read, lru_cached): a build after the files change on disk would stamp new hashes on old keys.
_KEY_LOGIC_AT_IMPORT = _key_logic_hashes()


def _git_head() -> str | None:
    try:
        return subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"],
                              capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _parse_records(data: bytes, name: str) -> list[dict[str, Any]]:
    records = roots_records(json.loads(data.decode("utf-8")))
    dupes = sorted(n for n, c in Counter(str(r["Number"]) for r in records).items() if c > 1)
    if dupes:
        raise ValueError(f"duplicate Numbers in {name}: {dupes[:10]}")
    return records


def load_records(roots_path: Path) -> list[dict[str, Any]]:
    return _parse_records(roots_path.read_bytes(), roots_path.name)


def _insert_keys(conn: sqlite3.Connection, rows: list[KeyRow]) -> None:
    conn.executemany("INSERT INTO root_keys (number, lexeme_id, kind, label, language, branch, radicals, shadow,"
                     " form, flags) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                     [(r.number, r.lexeme_id, r.kind, r.label, r.language, r.branch, " ".join(r.radicals),
                       r.shadow, r.form, ",".join(r.flags)) for r in rows])


def write_index(out_path: Path, roots_path: Path, lexica: Iterable[Lexicon] = LEXICA, *,
                allow_missing: bool = False) -> dict[str, Any]:
    """Build the index at out_path, which must not exist (FileExistsError), and is removed again if the build
    fails. Returns the provenance written. Every input is hashed from the same bytes that are parsed and checked
    again at the end; any change in between raises IndexStale. A missing lexicon raises FileNotFoundError unless
    allow_missing (then it is recorded as MISSING, and its arrival makes the index stale). A missing roots file
    or key-logic file raises NotInCheckout naming it. Callers own backup and the atomic rename
    (build_root_index.py writes to a temp path, then renames)."""
    lexica = tuple(lexica)
    if out_path.exists():
        raise FileExistsError(f"{out_path} exists; write_index never opens an existing file")
    for p in (*KEY_LOGIC_FILES, roots_path):
        require(p, p.name)
    drifted = sorted(p for p, sha in _KEY_LOGIC_AT_IMPORT.items()
                     if not _resolve(p).exists() or sha256_file(_resolve(p)) != sha)
    if drifted:
        raise IndexStale(f"key-logic files changed since this process imported them ({', '.join(drifted)}); "
                         "build in a fresh process")
    absent = [lx for lx in lexica if not lx.path.exists()]
    if absent and not allow_missing:
        raise FileNotFoundError("lexicon missing: " + ", ".join(str(lx.path) for lx in absent)
                                + " (allow_missing=True / --allow-missing records it as MISSING)")
    roots_bytes = roots_path.read_bytes()
    hashes_before = {_portable(roots_path): _sha_bytes(roots_bytes), **_key_logic_hashes()}
    records = _parse_records(roots_bytes, roots_path.name)
    conn = sqlite3.connect(out_path)
    try:
        conn.executescript(_SCHEMA)
        n_keys = 0
        lookup = _PSLookup()
        meanings: dict[str, set[str]] = {}
        gap_counts: Counter = Counter()
        for rec in records:
            number = str(rec["Number"])
            conn.execute("INSERT INTO roots VALUES (?, ?, ?)", (number, rec.get("Proto-Semitic"), rec.get("Meaning")))
            meanings[number] = gloss_words(rec.get("Meaning") or "")
            for language, text in (rec.get("Analogues") or {}).items():
                conn.execute("INSERT INTO analogues VALUES (?, ?, ?, ?)",
                             (number, language, branch_of(language)[0], text if isinstance(text, str) else
                              json.dumps(text, ensure_ascii=False)))
            rows, gaps = _record_keys(rec)
            _insert_keys(conn, rows)
            n_keys += len(rows)
            for r in rows:
                if r.kind == "ps":
                    lookup.add(number, r.radicals, r.shadow)
            conn.executemany("INSERT INTO unkeyed_analogues VALUES (?, ?, ?, ?)",
                             [(number, language, text if isinstance(text, str) else
                               json.dumps(text, ensure_ascii=False), reason) for language, reason, text in gaps])
            gap_counts.update(reason for _, reason, _ in gaps)
            conn.executemany("INSERT INTO record_hashes VALUES (?, ?, ?)",
                             [(number, f, s) for f, s in record_hashes(rec).items()])

        lex_counts: dict[str, dict[str, int]] = {}
        lex_before: dict[str, str] = {}
        link_counts = dict.fromkeys(("fk", "fk_dangling", "root_key_exact", "root_key_reduced"), 0)
        cache: dict[tuple, str | None] = {}
        numbers = set(meanings)
        for lx in lexica:
            if not lx.path.exists():
                lex_before[_portable(lx.path)] = MISSING
                lex_counts[lx.name] = {"missing": 1}
                continue
            data = lx.path.read_bytes()
            lex_before[_portable(lx.path)] = _sha_bytes(data)
            c = lex_counts.setdefault(lx.name, {"lexemes": 0, "keys": 0, "linked": 0, "keyless": 0, "ghost": 0,
                                                "phrase": 0, "overlong_keys": 0})
            skipped: Counter = Counter()
            for lexeme in iter_lexemes(lx, data, skipped):
                conn.execute("INSERT INTO lexemes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                             (lexeme.id, lexeme.lexicon, lexeme.language, lexeme.branch, lexeme.form,
                              lexeme.meaning, lexeme.pos, int(lexeme.onomastic),
                              None if lexeme.cognates in (None, [], {}, "") else
                              json.dumps(lexeme.cognates, ensure_ascii=False), lexeme.sha256))
                rows, patterns = lexeme_keys(lexeme, lx.scheme)
                _insert_keys(conn, rows)
                c["lexemes"] += 1
                c["keys"] += len(rows)
                c["keyless"] += not rows
                c["phrase"] += lexeme.phrase
                c["overlong_keys"] += sum("overlong" in r.flags for r in rows)
                links = _link_lexeme(lexeme, patterns, lookup, numbers, cache)
                c["linked"] += bool(links)
                words = gloss_words(lexeme.meaning)
                conn.executemany("INSERT INTO lexeme_links VALUES (?, ?, ?, ?)",
                                 [(lexeme.id, n, b, int(bool(words & meanings.get(n, set()))))
                                  for n, b in sorted(links.items())])
                for b in links.values():
                    link_counts[b] += 1
            c["ghost"] = skipped["ghost"]
            n_keys += c["keys"]

        if input_hashes(roots_path) != hashes_before or lexicon_hashes(lexica) != lex_before:
            raise IndexStale("an input changed while the index was being built; nothing kept")
        provenance = {
            "schema_version": SCHEMA_VERSION,
            "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "git_head": _git_head(),
            "roots_path": _portable(roots_path),
            "input_sha256": hashes_before,
            "lexicon_sha256": lex_before,
            "lexica": {lx.name: _portable(lx.path) for lx in lexica},
            "counts": {"roots": len(records), "keys": n_keys, "unkeyed_analogues": dict(sorted(gap_counts.items())),
                       "lexica": lex_counts, "links": link_counts},
        }
        conn.executemany("INSERT INTO provenance VALUES (?, ?)",
                         [(k, json.dumps(v, ensure_ascii=False)) for k, v in provenance.items()])
        conn.commit()
    except BaseException:
        conn.close()
        out_path.unlink(missing_ok=True)
        raise
    conn.close()
    return provenance


# ---------------------------------------------------------------------------
# load
# ---------------------------------------------------------------------------

def _ro(path: Path) -> sqlite3.Connection:
    """Read-only; a file URI, so ?, # and % in the path are escaped and a missing file is never created."""
    return sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)


def read_provenance(path: Path) -> dict[str, Any]:
    conn = _ro(path)
    try:
        return {k: json.loads(v) for k, v in conn.execute("SELECT key, value FROM provenance")}
    finally:
        conn.close()


def stale_inputs(path: Path, *, include_lexemes: bool = True) -> list[str]:
    """Inputs whose sha256 no longer matches the index's provenance: a file changed, deleted, or (a lexicon
    recorded MISSING) arrived. Lexicon files count only with include_lexemes."""
    prov = read_provenance(path)
    stored = dict(prov["input_sha256"])
    if include_lexemes:
        stored.update(prov.get("lexicon_sha256", {}))
    changed = []
    for p, sha in stored.items():
        fp = _resolve(p)
        now = sha256_file(fp) if fp.exists() else MISSING
        if now != sha:
            changed.append(p)
    return changed


def _stored(path: Path) -> tuple[dict[str, dict[str, str]], dict[str, set[tuple[str, str, str, str]]],
                                 dict[str, dict[str, str]]]:
    """Record hashes, keys (kind, language, radicals, shadow) per Number, and lexeme sha256 per lexicon."""
    conn = _ro(path)
    try:
        hashes: dict[str, dict[str, str]] = {}
        for number, fld, sha in conn.execute("SELECT number, field, sha256 FROM record_hashes"):
            hashes.setdefault(number, {})[fld] = sha
        keys: dict[str, set[tuple[str, str, str, str]]] = {}
        for number, kind, language, radicals, shadow in conn.execute(
                "SELECT number, kind, language, radicals, shadow FROM root_keys WHERE number IS NOT NULL"):
            keys.setdefault(number, set()).add((kind, language, radicals, shadow))
        lexemes: dict[str, dict[str, str]] = {}
        for lid, lexicon, sha in conn.execute("SELECT id, lexicon, sha256 FROM lexemes"):
            lexemes.setdefault(lexicon, {})[lid] = sha
    finally:
        conn.close()
    return hashes, keys, lexemes


def _field_changes(old: dict[str, str], new: dict[str, str]) -> list[str]:
    out = []
    for f in sorted(set(old) | set(new)):
        if f not in new:
            out.append(f"-{f}")
        elif f not in old:
            out.append(f"+{f}")
        elif old[f] != new[f]:
            out.append(f"~{f}")
    return out


def built_lexica(provenance: dict[str, Any]) -> tuple[list[Lexicon], list[str]]:
    """The lexica an index was built from (each LEXICA spec at the path recorded in its provenance), and the
    names provenance records that LEXICA no longer specifies."""
    specs = {lx.name: lx for lx in LEXICA}
    recorded = provenance.get("lexica", {})
    return ([replace(specs[name], path=_resolve(p)) for name, p in recorded.items() if name in specs],
            sorted(name for name in recorded if name not in specs))


def _ps_keys_now(records: dict[str, dict[str, Any]]) -> dict[tuple[str, str], set[str]]:
    out: dict[tuple[str, str], set[str]] = {}
    for n, rec in records.items():
        for key in ps_radical_keys(rec.get("Proto-Semitic") or ""):
            out.setdefault((" ".join(key), shadow_key(key)[0]), set()).add(n)
    return out


def diff_index(index_path: Path = DEFAULT_INDEX, roots_path: Path = DEFAULT_ROOTS,
               lexica: Iterable[Lexicon] | None = None) -> dict[str, Any]:
    """Read-only comparison of the current inputs with what the index was built from (§7.3, parts 1-2).

    records: added, removed, and modified Numbers with their field changes (+ added, - dropped, ~ edited);
    a record whose only change is Notes is notes_only, since Notes never make keys. nfc_only: the file changed
    but no record differs once normalised to NFC (--check still reports it stale).
    keys: per Number, keys gained and lost, and the shadow buckets entered and left. When key-logic code or the
    correspondence table changed, every Number is re-keyed. A removed Number whose PS key is a current PS key of
    another Number is listed as a possible merge into it (an Analogues reflex alone is not).
    lexica: per lexicon whose file changed, the entry ids added, removed and modified (default: the lexica the
    index was built from); lexica_unknown: lexica the index records that LEXICA no longer specifies."""
    provenance = read_provenance(index_path)
    unknown: list[str] = []
    if lexica is None:
        lexica, unknown = built_lexica(provenance)
    lexica = list(lexica)
    old_hashes, old_keys, old_lexemes = _stored(index_path)
    records = {str(r["Number"]): r for r in load_records(roots_path)}
    new_hashes = {n: record_hashes(r) for n, r in records.items()}

    added = sorted(set(new_hashes) - set(old_hashes))
    removed = sorted(set(old_hashes) - set(new_hashes))
    modified = {n: ch for n in sorted(set(new_hashes) & set(old_hashes))
                if (ch := _field_changes(old_hashes[n], new_hashes[n]))}
    notes_only = sorted(n for n, ch in modified.items() if {c[1:] for c in ch} == {"Notes"})
    roots_built = provenance["input_sha256"].get(_portable(roots_path))
    roots_now = sha256_file(roots_path)

    logic_now = _key_logic_hashes()
    logic_changed = sorted(p for p, sha in logic_now.items() if provenance["input_sha256"].get(p) != sha)
    rekey = set(new_hashes) | set(old_hashes) if logic_changed else \
        set(added) | set(removed) | (set(modified) - set(notes_only))

    keys: dict[str, dict[str, list]] = {}
    for n in sorted(rekey):
        new = {(k.kind, k.language, " ".join(k.radicals), k.shadow) for k in record_keys(records[n])} \
            if n in records else set()
        old = old_keys.get(n, set())
        if new == old:
            continue
        keys[n] = {
            "gained": sorted(new - old), "lost": sorted(old - new),
            "shadow_gained": sorted({k[3] for k in new} - {k[3] for k in old}),
            "shadow_lost": sorted({k[3] for k in old} - {k[3] for k in new}),
        }
    merges: dict[str, list[str]] = {}
    if removed:
        ps_now = _ps_keys_now(records)
        for n in removed:
            into = set().union(*(ps_now.get((k[2], k[3]), set()) for k in old_keys.get(n, ()) if k[0] == "ps"))
            if into - {n}:
                merges[n] = sorted(into - {n})

    lex_diff: dict[str, dict[str, Any]] = {}
    stored_lex = provenance.get("lexicon_sha256", {})
    for lx in lexica:
        p = _portable(lx.path)
        now = sha256_file(lx.path) if lx.path.exists() else MISSING
        if now == stored_lex.get(p, MISSING):
            continue
        old = old_lexemes.get(lx.name, {})
        new = {x.id: x.sha256 for x in iter_lexemes(lx)} if now != MISSING else {}
        lex_diff[lx.name] = {
            "added": sorted(set(new) - set(old)), "removed": sorted(set(old) - set(new)),
            "modified": sorted(i for i in set(new) & set(old) if new[i] != old[i]),
        }
    return {
        "index": _portable(index_path), "built_at": provenance.get("built_at"),
        "roots_sha256_built": roots_built, "roots_sha256_now": roots_now,
        "nfc_only": roots_now != roots_built and not (added or removed or modified),
        "key_logic_changed": logic_changed,
        "records": {"added": added, "removed": removed, "modified": modified, "notes_only": notes_only},
        "keys": keys, "possible_merges": merges, "lexica": lex_diff, "lexica_unknown": unknown,
    }


@dataclass
class RootIndex:
    path: Path
    provenance: dict[str, Any]
    keys: list[KeyRow]
    _buckets: dict[str, list[int]]
    lexemes: dict[str, dict[str, Any]] = field(default_factory=dict)
    links: dict[str, list[tuple[str, str, bool]]] = field(default_factory=dict)   # lexeme id → (Number, basis, gloss)
    checked: bool = True      # False when loaded with check_inputs=False: answers may come from changed inputs

    @classmethod
    def load(cls, path: Path = DEFAULT_INDEX, *, check_inputs: bool = True,
             include_lexemes: bool = True) -> RootIndex:
        if not path.exists():
            raise FileNotFoundError(f"{path} not built: run build_root_index.py")
        prov = read_provenance(path)
        version = prov.get("schema_version")
        if version != SCHEMA_VERSION:
            raise IndexStale(f"index schema v{version}, this code reads v{SCHEMA_VERSION}: rebuild with "
                             "build_root_index.py --force")
        if check_inputs and path.resolve() == DEFAULT_INDEX.resolve() and \
                prov.get("roots_path") != _portable(DEFAULT_ROOTS):
            raise IndexStale(f"the default index was built from {prov.get('roots_path')}, not "
                             f"{_portable(DEFAULT_ROOTS)}: it would never see edits to the live file; rebuild")
        if check_inputs:
            changed = stale_inputs(path, include_lexemes=include_lexemes)
            if changed:
                names = ", ".join(Path(p).name for p in changed)
                raise IndexStale(f"index stale ({names} changed): run build_root_index.py --diff")
        where = "" if include_lexemes else " WHERE number IS NOT NULL"
        conn = _ro(path)
        try:
            provenance = {k: json.loads(v) for k, v in conn.execute("SELECT key, value FROM provenance")}
            keys = [KeyRow(number, kind, label, language, branch, tuple(radicals.split()), shadow, form,
                           tuple(f for f in (flags or "").split(",") if f), lexeme_id)
                    for number, lexeme_id, kind, label, language, branch, radicals, shadow, form, flags
                    in conn.execute("SELECT number, lexeme_id, kind, label, language, branch, radicals, shadow,"
                                    f" form, flags FROM root_keys{where} ORDER BY id")]
            lexemes: dict[str, dict[str, Any]] = {}
            links: dict[str, list[tuple[str, str, bool]]] = {}
            if include_lexemes:
                for lid, lexicon, language, branch, form, meaning, pos, onomastic in conn.execute(
                        "SELECT id, lexicon, language, branch, form, meaning, pos, onomastic FROM lexemes"):
                    lexemes[lid] = {"lexicon": lexicon, "language": language, "branch": branch, "form": form,
                                    "meaning": meaning, "pos": pos, "onomastic": bool(onomastic)}
                for lid, number, basis, gloss in conn.execute(
                        "SELECT lexeme_id, number, basis, gloss_overlap FROM lexeme_links ORDER BY lexeme_id, number"):
                    links.setdefault(lid, []).append((number, basis, bool(gloss)))
        finally:
            conn.close()
        buckets: dict[str, list[int]] = {}
        for i, k in enumerate(keys):
            for v in deletion_neighbours(k.shadow):
                buckets.setdefault(v, []).append(i)
        return cls(path, provenance, keys, buckets, lexemes, links, check_inputs)

    @property
    def bucket_count(self) -> int:
        return len(self._buckets)

    def candidates(self, shadow: str, radius: int = 1) -> list[KeyRow]:
        """Keys whose shadow is within `radius` class edits (0 or 1; superset at 1, see deletion_neighbours).
        Radius 1 needs a shadow of two classes or more: a one-class shadow is one edit from every key of two
        classes or fewer, which is the UNINFORMATIVE case, not a candidate set."""
        if radius == 0:
            return [self.keys[i] for i in self._buckets.get(shadow, ()) if self.keys[i].shadow == shadow]
        if radius != 1:
            raise ValueError("radius must be 0 or 1")
        if len(shadow) < 2:
            raise ValueError(f"radius 1 on a {len(shadow)}-class shadow is UNINFORMATIVE; query radius 0")
        hits: set[int] = set()
        for v in deletion_neighbours(shadow):
            hits.update(self._buckets.get(v, ()))
        return [self.keys[i] for i in sorted(hits)]
