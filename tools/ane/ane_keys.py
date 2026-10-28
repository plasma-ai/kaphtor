"""Query-side notation: parse what a scholar types, then spell it the way each view stores its keys.

The data is never folded. `expand` returns the few exact strings a view stores for a query, so ṣ and s stay
distinct and an SQL `IN (...)` can test them. VIEW_NOTATION declares each view's convention.

    from ane_keys import parse_query, expand
    expand(parse_query("ʾ-m-r"), "quran")     # {'ʔmr', 'ʔ-m-r'}

di Mino
"""
from __future__ import annotations

import itertools
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Hebrew -> Semitic consonantal romanization (skill convention, cf. quran match_keys).
HEB_ROMAN = {
    "א": "ʔ", "ב": "b", "ג": "g", "ד": "d", "ה": "h", "ו": "w", "ז": "z",
    "ח": "ḥ", "ט": "ṭ", "י": "y", "כ": "k", "ך": "k", "ל": "l", "מ": "m",
    "ם": "m", "נ": "n", "ן": "n", "ס": "s", "ע": "ʕ", "פ": "p", "ף": "p",
    "צ": "ṣ", "ץ": "ṣ", "ק": "q", "ר": "r", "ש": "š", "ת": "t",
}

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.paths import ANE_DATA as PROPER_NAMES
from tools.paths import SHARE_ALIKE

# Signs a scholar may type for aleph and ayin. The ASCII apostrophe and the curly quote are
# written for both, so they stay ambiguous and expand to every sign the view stores for either.
ALEPHS = "ʾʔʼ"
AYINS = "ʿʕ‘`ᶜ"
AMBIGUOUS = "'’"
SIBILANT = {"1": "s1", "2": "s2", "3": "s3", "¹": "s1", "²": "s2", "³": "s3", "₁": "s1", "₂": "s2", "₃": "s3"}
UNIT = re.compile(r"s[123¹²³₁₂₃]|.[̀-֑ͯ-ׇً-ٰٟ]*", re.DOTALL)
SEPARATORS = "-. "
# English-keyboard digraphs for single letters. Each is read both ways, since s + h is also a sequence.
ASCII_DIGRAPHS = {"sh": "š", "kh": "ḫ", "th": "ṯ", "dh": "ḏ", "gh": "ġ"}
DIGRAPH = re.compile(f"({'|'.join(ASCII_DIGRAPHS)})")

# Sibilant schemes: how a view writes the indexed sibilants s1 s2 s3. A key is spelled in one scheme throughout;
# schemes are never mixed within a key.
DIGIT = {"s1": "s1", "s2": "s2", "s3": "s3"}

ARABIC = ("؀", "ۿ")
HEBREW = ("א", "ת")

# Hebrew points, accents and punctuation; the consonantal fields store none of them.
HEBREW_MARK = re.compile("[֑-ׇ]")
SHIN_DOTS = "ׁׂ"
# Hebrew letters read as canonical Latin, then spelled in the view's signs: an unpointed shin may be š or ś.
HEB_LATIN = {**HEB_ROMAN, "א": "ʾ", "ע": "ʿ", "ש": ("š", "ś"), "שׁ": "š", "שׂ": "ś"}
# Manuel de Codage capitals and letters that stand for Egyptological signs.
MDC = {"A": "ꜣ", "a": "ꜥ", "H": "ḥ", "x": "ḫ", "X": "ẖ", "S": "š", "T": "ṯ", "D": "ḏ", "i": "j"}

VIEW_NOTATION: dict[str, dict] = {
    # Jīm is stored as ǧ; a typed j can mean nothing else here.
    "quran": {"paths": ("QURAN_ROOTS",), "aleph": ("ʔ",), "ayin": ("ʿ",), "schemes": (DIGIT,),
              "letters": {"j": ("ǧ",)}, "shape": ("bare", "hyphen"), "script": ARABIC,
              "alphabet": "-bdfhklmnqrstwyzġšǧʔʿḍḏḥḫṣṭṯẓ"},
    "epi": {"paths": ("EPIGRAPHY",), "aleph": ("ʾ",), "ayin": ("ʿ",), "schemes": (DIGIT,),
            "shape": ("bare",), "alphabet": "123bdfghklmnqrstwyzġśšʾʿḍḏḥḫṣṭṯẓ"},
    # The views below search a field other than match_keys, by equality or as a substring.
    # OSHB words: a pointed query is matched to the unpointed consonantal field.
    "hebrew": {"paths": ("HEBREW_WORDS",), "field": "consonantal_joined", "aleph": ("ʾ",), "ayin": ("ʿ",),
               "schemes": (DIGIT,), "strip_marks": True, "shape": ("typed",), "script": HEBREW, "alphabet": ""},
    # ORAEC/TLA keys hold German translation words beside the transliteration, so the alphabet is wide.
    # ẖ is stored composed; h + U+0331 is spelled too, in case a source writes it decomposed.
    "egytext": {"paths": ("EGY_SENTS", "EGY_DOCS"), "aleph": ("ʾ",), "ayin": ("ꜥ", "ʿ"), "schemes": (DIGIT,),
                "letters": {"ȝ": ("ꜣ",), "ỉ": ("j",), "ẖ": ("ẖ", "ẖ")}, "mdc": MDC, "shape": ("typed",),
                "alphabet": " !$&'()+,-.0123456789:;=?[]_abcdefghijklmnopqrstuvwxyz§ßäèéöüāīšūʾʿ̯̱"
                            "ḏḥḫṣṯẖ“„⸮〈〉ꜣꜥ"},
    # ETCBC Targum tokens; only they carry root_normalized. Yod is stored y; a typed j (ETCBC's J) is read as yod.
    "aramaic": {"paths": ("ARAMAIC_DB",), "table": "aramaic_tokens", "field": "root_normalized",
                "aleph": ("ʾ",), "ayin": ("ʿ",), "schemes": (DIGIT,), "romanise": HEB_LATIN,
                "letters": {"j": ("y",)}, "shape": ("bare",), "alphabet": "bdghklmnpqrstwyzšśʾʿḥṣṭ"},
    "dasi": {"paths": ("DASI_RECORDS",), "field": "transcription_plain", "census_casefold": True,
             "aleph": ("ʾ",), "ayin": ("ʿ",), "schemes": ({"s1": "s¹", "s2": "s²", "s3": "s³"},),
             "shape": ("bare", "typed"), "alphabet": " #-./0123456789bdfghiklmnqrstwyz|²³¹ġʾʿ̱ḍḏḥḫṣṭṯẓ"},
    "ahi": {"paths": ("AHI_RECORDS",), "field": "search_unicode", "aleph": ("ʾ",), "ayin": ("ʿ",),
            "schemes": (DIGIT,), "romanise": HEB_LATIN, "shape": ("bare", "typed"),
            "alphabet": " bdghklmnpqrstwyzšśʾʿḥṣṭ"},
    "term": {"paths": ("TERMS_GLOB",), "field": "root", "aleph": ("ʔ",), "ayin": ("ʕ",), "schemes": (DIGIT,),
             "shape": ("hyphen",), "alphabet": "-bdghklmnpqrstwyzšśʔʕḥṣṭṯ"},
    # query_proper_names searches this as a substring of the folded record text.
    # PNM: Egyptian names in transliteration; ꜣ and ꜥ are the Egyptological aleph and ayin.
    "pnm": {"paths": (PROPER_NAMES / "pnm-v6" / "tables" / "personal_names.jsonl",), "field": "personal_name",
            "aleph": ("ꜣ",), "ayin": ("ꜥ",), "schemes": (DIGIT,),
            "letters": {"ȝ": ("ꜣ",), "ỉ": ("j",), "=": ("⸗",)}, "mdc": MDC, "shape": ("typed",),
            "alphabet": " ()-.?[]bdfghjkmnpqrstwšẖḏḥḫṯ⸗ꜣꜥ", "known_strays": {"o": 1}},
    # TLA v18 lemmas: yod is ꞽ (U+A7BD), ʾ TLA's own sign beside ꜣ, + joins a compound; i̯ and H̱ carry
    # combining marks. Pḏ.wt-9, the Nine Bows, is the one digit.
    "tla": {"paths": (SHARE_ALIKE / "tla-v18-names" / "lemmas.jsonl",), "field": "lemma", "census_casefold": True,
            "aleph": ("ꜣ", "ʾ"), "ayin": ("ꜥ",), "schemes": (DIGIT,),
            "letters": {"ȝ": ("ꜣ",), "ỉ": ("ꞽ",), "j": ("ꞽ",), "ẖ": ("ẖ", "ẖ"), "⸗": ("=",)}, "mdc": MDC,
            "shape": ("typed",), "alphabet": " +-.=bdfghikmnpqrstwyzšʾ̯̱ḏḥḫṯẖꜣꜥꞽ", "known_strays": {"9": 1}},
}


@dataclass
class Parsed:
    query: str
    mode: str                      # "root" or "form"
    text: str                      # cleaned query with its separators, for spellings stored as typed
    radicals: list[str] = field(default_factory=list)


def units(s: str) -> list[str]:
    """One token per letter: marks stay on their base, an indexed sibilant (s¹, s₁, s1) is one token."""
    out = []
    for u in UNIT.findall(unicodedata.normalize("NFD", s)):
        if u[0] == "s" and len(u) == 2 and u[1] in SIBILANT:
            out.append(SIBILANT[u[1]])
        else:
            out.append(unicodedata.normalize("NFC", u))
    return out


def canonical_sign(u: str) -> str:
    if u in ALEPHS:
        return "ʾ"
    if u in AYINS:
        return "ʿ"
    if u in AMBIGUOUS:
        return "'"
    return u


def spaced_letters(s: str, sep: str) -> bool:
    parts = s.split(sep)
    return len(parts) > 1 and all(len(units(p)) == 1 for p in parts)


def parse_query(q: str) -> Parsed:
    """NFC, strip √ and *, casefold (Hebrew and Arabic have no case), decide root or form mode,
    and split into radicals."""
    s = unicodedata.normalize("NFC", q).strip()
    root = "√" in s
    s = s.replace("√", "").replace("*", "").casefold()
    root = root or "-" in s or spaced_letters(s, ".")
    if spaced_letters(s, " "):          # م ن ي, a b d: letters typed apart
        s = s.replace(" ", "")
    text = "".join(canonical_sign(u) for u in units(s))
    radicals = [canonical_sign(u) for u in units(s) if u not in SEPARATORS]
    return Parsed(query=q, mode="root" if root else "form", text=text, radicals=radicals)


def options(u: str, row: dict, scheme: dict) -> tuple[str, ...]:
    table = row.get("romanise")
    if table and u[0] in table:
        # Hebrew points are dropped with the letter's marks; a shin or sin dot picks the reading.
        dots = "".join(ch for ch in u if ch in SHIN_DOTS)
        value = table.get(u[0] + dots, table[u[0]])
        latin = (value,) if isinstance(value, str) else value
        return tuple(dict.fromkeys(o for v in latin for o in options(v, row, scheme)))
    if row.get("strip_marks"):
        return (HEBREW_MARK.sub("", u),)
    if u == "ʾ":
        return row["aleph"]
    if u == "ʿ":
        return row["ayin"]
    if u == "'":
        return tuple(dict.fromkeys(row["aleph"] + row["ayin"]))
    if u in scheme:
        return (scheme[u],)
    return row.get("letters", {}).get(u, (u,))


def spellings(tokens: list[str], row: dict, scheme: dict) -> set[str]:
    return {"".join(p) for p in itertools.product(*(options(u, row, scheme) for u in tokens))}


def digraph_readings(text: str) -> set[str]:
    """`text` with each ASCII digraph read as its letter or kept as two letters: shdh → šḏ, šdh, shḏ, shdh."""
    parts = DIGRAPH.split(text)
    return {"".join(p) for p in itertools.product(*((part, ASCII_DIGRAPHS[part]) if part in ASCII_DIGRAPHS
                                                    else (part,) for part in parts))}


def expand(parsed: Parsed, view: str) -> set[str]:
    """The exact strings `view` may store for this query: spelled in each sibilant scheme the view uses, in
    each key shape it stores (bare, hyphen between letters, or as typed with its separators), with the view's
    signs. A view that reads Manuel de Codage also spells the query's MdC reading, taken before casefolding;
    the other views also read its ASCII digraphs."""
    row = VIEW_NOTATION[view]
    out: set[str] = set()
    queries = [parsed]
    if "mdc" in row:
        # Per letter unit, so a marked letter (TLA's i̯) is not read as its bare MdC base.
        queries.append(parse_query("".join(row["mdc"].get(u, u) for u in units(parsed.query))))
    else:
        queries += [parse_query(t) for t in sorted(digraph_readings(parsed.text) - {parsed.text})]
    for p, scheme in itertools.product(queries, row["schemes"]):
        bare = spellings(p.radicals, row, scheme)
        if "bare" in row["shape"]:
            out |= bare
        if "hyphen" in row["shape"]:
            # Letter by letter, so s1 and a letter with its marks stay whole.
            out |= {"-".join(unicodedata.normalize("NFC", u) for u in units(b)) for b in bare}
        if "typed" in row["shape"]:
            out |= spellings(units(p.text), row, scheme)
    return {k for k in out if k}


# Separators and the ASCII mark signs ^ and :, dropped from folded keys.
LOOSE_DROP = set("-. ⸗=^:√*")


def loose_key(s: str) -> str:
    """The folded key (match basis 2), applied to both the query and the stored value at comparison time:
    case, marks, the aleph/ayin distinction, sibilant indexes and separators are dropped. Egyptian ꜣ and ꜥ
    are letters of their own and stay. Lower-cased, not casefolded (ß stays ß), as aneq's SQL twin does."""
    out = []
    for u in units(unicodedata.normalize("NFC", s).lower()):
        if u in SIBILANT.values():
            out.append("s")
        elif canonical_sign(u) in "ʾʿ'":
            out.append("'")
        elif u not in LOOSE_DROP:
            out.append("".join(c for c in unicodedata.normalize("NFD", u) if not unicodedata.combining(c)))
    return "".join(out)


# The folded tier's second test. loose_key would let mwṯ reach mwt; a mark the scholar typed is meant, so a
# bare query letter stands for any marked form of it but a marked one only for itself. Stored values are
# compared with case, the aleph/ayin signs, sibilant indexes and separators folded and every mark kept, by
# string operations only, so aneq's SQL twin (sql_marks_kept) matches marks_kept exactly.
SIGNS = re.compile("[ʾʔʼʿʕ‘`ᶜ'’]")
INDEX = re.compile("s[123¹²³₁₂₃]")
SEPARATOR = re.compile("[-. ⸗=^:√*]")
MARK_BLOCKS = ((0x0300, 0x036F), (0x0591, 0x05C7), (0x0610, 0x061A), (0x064B, 0x065F), (0x0670, 0x0670),
               (0x06D6, 0x06ED), (0x1AB0, 0x1AFF), (0x1DC0, 0x1DFF), (0x20D0, 0x20FF), (0xFE20, 0xFE2F))


def char_class(cps) -> str:
    """A regex class of these code points, consecutive runs written as ranges."""
    runs: list[list[int]] = []
    for cp in sorted(cps):
        if runs and cp == runs[-1][1] + 1:
            runs[-1][1] = cp
        else:
            runs.append([cp, cp])
    return "[" + "".join(chr(a) if a == b else f"{chr(a)}-{chr(b)}" for a, b in runs) + "]"


MARKS = char_class(cp for lo, hi in MARK_BLOCKS for cp in range(lo, hi + 1)
                   if unicodedata.category(chr(cp)) in ("Mn", "Me"))
# Each lower-case base letter's precomposed marked forms: s → ṣ, š, ś …
MARKED: dict[str, str] = {}
for _cp in itertools.chain(range(0x00C0, 0x0250), range(0x1E00, 0x1F00), range(0xA720, 0xA800)):
    _d = unicodedata.normalize("NFD", chr(_cp))
    if len(_d) > 1 and chr(_cp) == chr(_cp).lower():
        MARKED[_d[0]] = MARKED.get(_d[0], "") + chr(_cp)


def marks_kept(s: str) -> str:
    """`s` lower-cased, its aleph/ayin signs written ', sibilant indexes and separators dropped; marks kept."""
    return SEPARATOR.sub("", SIGNS.sub("'", INDEX.sub("s", s.lower())))


def fold_pattern(query: str) -> str:
    """A regex over marks_kept(stored) for the folded tier: each bare letter of the query matches any
    marked form of it (composed or decomposed), each marked letter only itself."""
    out = []
    for u in units(marks_kept(unicodedata.normalize("NFC", query))):
        d = unicodedata.normalize("NFD", u)
        if len(d) > 1:
            forms = dict.fromkeys((unicodedata.normalize("NFC", u), d))
            out.append("(?:" + "|".join(re.escape(f) for f in forms) + ")")
        else:
            out.append("[" + re.escape(d + MARKED.get(d, "")) + "]" + MARKS + "*")
    return "".join(out)


def declared(view: str, ch: str) -> bool:
    row = VIEW_NOTATION[view]
    lo_hi = row.get("script")
    return ch in row["alphabet"] or bool(lo_hi and lo_hi[0] <= ch <= lo_hi[1])
