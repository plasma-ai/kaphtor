"""Protocol C, phase C3: the known-language texts of the calibration gate (§9.1), word by word.

Each loader reads a held edition in its own order and gives every clean word as segments, the renderer's input;
Linear B needs no renderer, since the edition already gives signs. A word with a damage mark, a logogram, a
numeral or a letter outside the language's alphabet is left out and counted. `words` writes a language's text as
sign keys under one spelling convention.

| Language | Held source | Vowels |
|---|---|---|
| hebrew | OSHB (morphhb), pointed, through protocol-d/scripts/pointed.py | the Masoretic points |
| ugaritic | EUPT, KTU 1.14 to 1.16, the edition's vocalisation | the editors' |
| greek | Linear B occurrences verified against DAMOS, PY and KN, clean words | written by the scribes |
| luwian | TLHdig 0.3 bound transcription, preserved words; ACLT's transcriptions of six hieroglyphic texts | the cuneiform's, the editors' |
| hurrian | TLHdig 0.3 bound transcription, preserved words | the cuneiform's |
| egyptian | ORAEC sentences, Egyptological consonants | a filler e after every consonant (§13 limit 7) |

§9.1 names the Copenhagen Ugaritic Corpus and ACLT. The Copenhagen corpus is consonantal, and a word without
vowels cannot be written in a syllabary, so the vocalised edition held (EUPT) stands for Ugaritic. ACLT is held
for seven texts only, so TLHdig's cuneiform Luwian comes first and ACLT's texts after it.

No Linear A is read here.

Attribution: di Mino
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

import c_align as a
import c_render as r

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[2] / "protocol-d" / "scripts"))
import pointed  # noqa: E402  (Protocol D's reader of pointed Hebrew; read, never edited)

import os
ANE = Path(
    os.environ.get("KAPHTOR_ANE_DIR", str(Path.home() / ".claude/skills/ancient-near-east-research/data"))
)
OSHB = Path(
    os.environ.get("KAPHTOR_OSHB_JSONL", str(HERE.parents[3] / "data/share-alike/hebrew/oshb_words.jsonl"))
)
EUPT = Path(
    os.environ.get("KAPHTOR_EUPT_JSONL", str(HERE.parents[3] / "data/share-alike/ugaritic/eupt_tokens.jsonl"))
)
TLHDIG = ANE / "ingest/anatolian/tlhdig-0.3/derived/words.jsonl"
ORAEC = ANE / "egyptian_sentences.jsonl"
LINEAR_B = Path(
    os.environ.get(
        "KAPHTOR_LINEAR_B_JSONL",
        str(HERE.parents[3] / "data/share-alike/linear-b/linear_b_tokens.jsonl"),
    )
)
ACLT = HERE.parents[3] / "artifacts/jss-rejection-research-2026-10-09/acquisitions/A1-luwian/texts"
ACLT_TEXTS = ("KARATEPE1", "KARKAMIS_A11A", "KARKAMIS_A11BC", "KARKAMIS_A6", "SULTANHAN", "TOPADA")
LANGUAGES = ("ugaritic", "hebrew", "greek", "luwian", "egyptian", "hurrian")

_VOWELS = set("aeiou")
_LONG = str.maketrans("âêîôûāēīōū", "aeiouaeiou")
_UGARITIC = set("ʾʿbgdhwzḥṭyklmnsṣpqrštṯḏẓġḫ") | _VOWELS
_CUNEIFORM = set("bdgḫhklmnprsštwyzf") | _VOWELS
_EGYPTIAN = set("ꜣjyꜥwbpfmnrhḥḫẖzsšqkgtṯdḏ")
_EGY_DROP = str.maketrans("", "", "(),.=-")
_TRANSCRIPTION = re.compile(r"transcription=([^;]+)")


def _letters(text: str) -> list[str]:
    return list(unicodedata.normalize("NFC", text))


def ugaritic_segments(surface: str) -> list[str] | None:
    """EUPT's vocalised word, or None when it is marked, broken or holds a cover letter."""
    word = unicodedata.normalize("NFC", surface).replace("ˀ", "ʾ").replace("ˁ", "ʿ").translate(_LONG)
    word = word.replace("-", "")
    return list(word) if word and set(word) <= _UGARITIC and set(word) & _VOWELS else None


def cuneiform_segments(trans: str) -> list[str] | None:
    """TLHdig's bound transcription of a Luwian or Hurrian word, or None for a logogram, numeral or mixed word."""
    word = unicodedata.normalize("NFC", trans).translate(_LONG)
    return list(word) if word and set(word) <= _CUNEIFORM and set(word) & _VOWELS else None


def egyptian_segments(token: str) -> list[str] | None:
    """An ORAEC token as consonants, each followed by the filler e. i̯ is j and u̯ is w, as the edition means."""
    word = unicodedata.normalize("NFC", unicodedata.normalize("NFD", token).lower())
    word = word.replace("i̯", "j").replace("u̯", "w").translate(_EGY_DROP)
    if not word or not set(word) <= _EGYPTIAN:
        return None
    out: list[str] = []
    for c in word:
        out += [c, "e"]
    return out


def hebrew_segments(surface: str) -> list[str] | None:
    """One OSHB word, its morpheme slashes removed, through Protocol D's reader of the points."""
    word = pointed.strip_accents(surface.replace("/", ""))
    try:
        pairs = pointed.segments(word)
    except (KeyError, ValueError, IndexError):
        return None
    out = [s for pair in pairs for s in pair if s]
    return out if out and set(out) & _VOWELS else None


def _rows(path: Path):
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            yield json.loads(line)


def segments(language: str) -> tuple[list[list[str]], int]:
    """(the text's clean words in the edition's order, the number of words left out)."""
    out: list[list[str] | None] = []
    if language == "hebrew":
        out = [hebrew_segments(row["surface"]) for row in _rows(OSHB) if row.get("language", "H") == "H"]
    elif language == "ugaritic":
        out = [ugaritic_segments(row["surface"]) for row in _rows(EUPT)]
    elif language in ("luwian", "hurrian"):
        code = {"luwian": "Luw", "hurrian": "Hur"}[language]
        out = [cuneiform_segments(row["trans"]) if row.get("preserved") and row.get("trans") else None
               for row in _rows(TLHDIG) if row.get("language") == code]
        if language == "luwian":
            for name in ACLT_TEXTS:
                for unit in json.loads((ACLT / f"{name}.json").read_text(encoding="utf-8"))["units"]:
                    for token in unit["tokens"]:
                        found = _TRANSCRIPTION.search(token.get("gloss") or "")
                        out.append(None if token.get("damaged") or not found
                                   else cuneiform_segments(found.group(1).strip().lower().replace("=", "")))
    elif language == "egyptian":
        out = [egyptian_segments(part) for row in _rows(ORAEC) for token in row["transliteration"].split()
               for part in token.split("-")]                       # a hyphen joins the words of a compound
    else:
        raise ValueError(language)
    kept = [w for w in out if w]
    return kept, len(out) - len(kept)


def linear_b(signs: dict) -> tuple[list[tuple], int]:
    """Clean syllabic words of the Pylos and Knossos tablets, in tablet, line and token order, as sign keys."""
    rows = [row for row in _rows(LINEAR_B) if row["document_id"][:2] in ("PY", "KN") and row["token_type"] == "syllabic"]
    rows.sort(key=lambda row: (row["document_id"], str(row["line_id"]), row["token_index"]))
    clean = [row for row in rows if row.get("editorial_status") == "clean"
             and str(row.get("source_status", "")).startswith("DAMOS_VERIFIED")]
    return [a.keys(row["token_normalized"], signs) for row in clean], len(rows) - len(clean)


def words(language: str, convention: str, t: r.Tables, signs: dict) -> tuple[list[tuple], dict]:
    """The language's text as sign keys under one convention, with the counts of what was left out."""
    if language == "greek":
        out, left = linear_b(signs)
        return out, {"words": len(out), "left_out": left, "unwritable": 0}
    segs, left = segments(language)
    written = [r.word(s, language, t, convention) for s in segs]
    out = [w for w in written if w]
    return out, {"words": len(out), "left_out": left, "unwritable": len(written) - len(out)}
