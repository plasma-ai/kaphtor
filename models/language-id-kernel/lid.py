"""Language identification by forward spelling (PREREGISTRATION-DRAFT.md): readers, the split, the model, the statistic.

A word is a tuple of sign keys, (series, vowel). Known languages are spelled into the syllabary by Protocol C's
renderer, read in place and never edited; Linear B tablets are taken as written; LSJ's lemmas come in the Linear B
spelling the skill holds. A Witten-Bell n-gram model of sign keys is trained on each arm, and a text's fit under an
arm is the mean bits per sign over its distinct word types.

Nothing here reads a Linear A form. The Arabic reader is a simplification for control texts, offered as no
philology.

Attribution: di Mino
"""
from __future__ import annotations

import collections
import hashlib
import json
import math
import os
import random
import sys
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "render"))
import c_align as a   # noqa: E402  (Protocol C's sign keys; read, never edited)
import c_render as r  # noqa: E402  (Protocol C's renderer)
import c_texts as ct  # noqa: E402  (Protocol C's readers of the held editions)

SIGNATURE = HERE / "SIGNATURE.txt"
QURAN = ct.ANE / "ingest/quran/quran-uthmani-numbered.txt"
LSJ = Path(
    os.environ.get(
        "KAPHTOR_LSJ_JSONL",
        str(Path.home() / ".claude/skills/linear-a-decipherment/data/contact/greek_lexicon.jsonl"),
    )
)
END, BOS = "<end>", "<bos>"
VOWELS = "aeiou"
TRACES = ct.ANE / "ingest/open-semitic/derived/traces-geez/tokens.jsonl"
ORACC_DIR = ct.ANE / "ingest/cuneiform/derived"
LATIN = Path(os.environ.get("KAPHTOR_LATIN_CSV", "LatInfLexi-forms.csv"))
# Akkadian in the Semitic arm comes from ORACC's normalised Old and Standard Babylonian, outside Boğazköy. The
# Boğazköy Akkadian of TLHdig is a test text only ("akkadian_bo"): it shows what a source's writing does.
TLH = {"akkadian_bo": ("Akk",), "hittite": ("Hit",), "hurrian": ("Hur",), "hattic": ("Hat", "Hattian"),
       "luwian": ("Luw",)}
ORACC = {"akkadian": ("oracc_documents.jsonl", ("akk-x-oldbab", "akk-x-stdbab")),
         "sumerian": ("oracc_documents_supplement_sumerian_epsd2_etcsri.jsonl", ("sux",)),
         "urartian": ("oracc_documents_supplement_ckst_csik_ecut.jsonl", ("xur",))}
ARAMAIC = ct.ANE / "aramaic_texts.jsonl"
SYRIAC_CORPORA = ("ephrem_nisibis", "ephrem_works")
# Perseus's Greek text of Diodorus (tlg0060.tlg001.perseus-grc5.xml): not shipped; name its path in KAPHTOR_DIODORUS_XML
DIODORUS = Path(os.environ.get("KAPHTOR_DIODORUS_XML", "tlg0060.tlg001.perseus-grc5.xml"))
ARMS = {"semitic": ("hebrew", "akkadian", "arabic", "aramaic", "syriac", "geez", "ugaritic"),
        "anatolian": ("hittite", "luwian"), "greek": ("lsj", "diodorus"), "hurrian": ("hurrian", "urartian"),
        "hattic": ("hattic",), "sumerian": ("sumerian",), "latin": ("latin",)}
ARM_OF = {member: arm for arm, members in ARMS.items() for member in members if member != "lsj"}
ARM_OF.update({"greek": "greek", "akkadian_bo": "semitic"})

Word = tuple
_TLH_CACHE: dict = {}


# ---- the split -------------------------------------------------------------------------------------------------

def part(document: str) -> str:
    """gate, dev or train, fixed by the document's id (§5)."""
    n = int(hashlib.sha256(document.encode("utf-8")).hexdigest()[:8], 16) % 4
    return ("gate", "dev", "train", "train")[n]


def select(docs: list, which: str, signature: Path = SIGNATURE) -> list:
    """The documents of one part. The gate part is refused until the pre-registration is signed."""
    if which == "gate" and not signature.is_file():
        raise PermissionError("the gate part is closed: no signature stands beside the pre-registration")
    return [(d, words) for d, words in docs if part(d) == which]


# ---- words -----------------------------------------------------------------------------------------------------

def sign_keys() -> set:
    """The keys a sign writes: Protocol C's table of secure Linear B values."""
    return {k for k in a.load_signs().values() if isinstance(k, tuple)}


def valid(word: Word, signs: set) -> bool:
    return len(word) >= 2 and all(isinstance(k, tuple) and k in signs for k in word)


def glide(word: Word, signs: set) -> Word:
    """The script's glide rule (§3): a vowel sign after i is written with j, after u with w, where a sign exists.
    It names no language and is applied to every rule-spelled source; tablets are taken as written."""
    out = [word[0]]
    for key in word[1:]:
        series = {"i": "J", "u": "W"}.get(out[-1][1]) if key[0] == "" else None
        out.append((series, key[1]) if series and (series, key[1]) in signs else key)
    return tuple(out)


_THREE = {"e": "i", "o": "u"}


def three_vowels(word: Word) -> Word:
    """The three-vowel tier: e with i, o with u, for every source alike. It takes a source's way of writing
    vowels (cuneiform writes no o) out of the comparison."""
    return tuple((series, _THREE.get(vowel, vowel)) for series, vowel in word)


_SERIES = {c: c.upper() for c in "dkmnprstwzjq"}


def lsj_keys(lb_key: str) -> Word | None:
    """An LSJ lemma's Linear B spelling ("kuruso") as sign keys, or None when it is no run of open syllables."""
    out, i = [], 0
    while i < len(lb_key):
        c = lb_key[i]
        if c in VOWELS:
            out.append(("", c))
            i += 1
        elif c in _SERIES and i + 1 < len(lb_key) and lb_key[i + 1] in VOWELS:
            out.append((_SERIES[c], lb_key[i + 1]))
            i += 2
        else:
            return None
    return tuple(out) or None


_AR_CONS = {"ء": "ʾ", "أ": "ʾ", "إ": "ʾ", "ؤ": "ʾ", "ئ": "ʾ", "ب": "b", "ت": "t", "ة": "t", "ث": "ṯ", "ج": "g",
            "ح": "ḥ", "خ": "ḫ", "د": "d", "ذ": "ḏ", "ر": "r", "ز": "z", "س": "s", "ش": "š", "ص": "ṣ", "ض": "d",
            "ط": "ṭ", "ظ": "ẓ", "ع": "ʿ", "غ": "ġ", "ف": "f", "ق": "q", "ك": "k", "ل": "l", "م": "m", "ن": "n",
            "ه": "h", "و": "w", "ي": "y", "ى": "y"}
_AR_VOWEL = {"َ": ("a",), "ُ": ("u",), "ِ": ("i",), "ً": ("a", "n"), "ٌ": ("u", "n"),
             "ٍ": ("i", "n")}
_AR_SUKUN, _AR_SHADDA, _AR_DAGGER, _AR_HAMZA = {"ْ", "ۡ"}, "ّ", "ٰ", {"ٔ", "ٕ"}
_AR_SILENT = {"ا", "ٱ", "ـ", "ٓ", "ۥ", "ۦ"} | {chr(c) for c in range(0x06D6, 0x06EE)}
_AR_MARKS = set(_AR_VOWEL) | _AR_SUKUN | {_AR_SHADDA, _AR_DAGGER}
_AR_LONG = {"و": "u", "ي": "i", "ى": "i"}


_AR_WASLA = "ٱ"
_AR_SEVEN = {("س", "م"), ("ب", "ن"), ("م", "ر"), ("ث", "ن")}     # ism, ibn, imruʾ, iṯnāni and their feminines


def _wasla_vowel(word: str) -> str:
    """The vowel a word-initial alif wasla is spoken with when the word stands alone: a in the article; u in a
    verb whose stem vowel is u; i elsewhere, and in the seven nouns."""
    if word[1:2] == "ل":
        return "a"
    letters = [i for i, ch in enumerate(word) if i and ch in _AR_CONS]
    if len(letters) >= 2:
        if (word[letters[0]], word[letters[1]]) in _AR_SEVEN:
            return "i"
        end = letters[2] if len(letters) > 2 else len(word)
        if "ُ" in word[letters[1]:end]:
            return "u"
    return "i"


def arabic_segments(word: str) -> list[str] | None:
    """One vocalised Arabic word as consonants and short vowels. A long vowel is its short vowel, a doubled
    consonant is written once, tanwin is a vowel and n. Alif wasla at the head of a word takes the vowel it is
    spoken with when the word stands alone, since each word is scored alone; inside a word it is silent. None
    for any other character."""
    word = unicodedata.normalize("NFC", word)
    out: list[str] = []
    if word[:1] == _AR_WASLA:
        out.append(_wasla_vowel(word))
    for i, ch in enumerate(word):
        nxt = word[i + 1] if i + 1 < len(word) else ""
        if ch == "آ":
            out += ["ʾ", "a"]
        elif ch in _AR_CONS:
            bare = nxt not in _AR_MARKS
            if bare and ch in _AR_LONG and out and out[-1] == _AR_LONG[ch]:
                continue                                    # waw after u, ya after i: the vowel's length
            if bare and ch == "ى":
                continue                                    # alif maqsura: the length of a
            out.append(_AR_CONS[ch])
        elif ch in _AR_VOWEL:
            out += _AR_VOWEL[ch]
        elif ch == _AR_DAGGER:
            if not out or out[-1] != "a":
                out.append("a")
        elif ch in _AR_HAMZA:
            out.append("ʾ")
        elif ch in _AR_SUKUN or ch == _AR_SHADDA or ch in _AR_SILENT:
            continue
        else:
            return None
    return out if out and set(out) & set(VOWELS) else None


_GEEZ = str.maketrans({"ǝ": "e", "ṗ": "p", "ḍ": "ṣ", "ḵ": "k", "ñ": "n", "č": "t", "ǧ": "g", "ž": "z", "-": ""})
_GEEZ_OK = set("abdefghiklmnopqrstuwyzāśšʷʾʿḥḫṣṭ")
_NORM_OK = ct._UGARITIC | ct._CUNEIFORM | set("ejo")
_NORM = str.maketrans({"ŋ": "g", "ĝ": "g", "=": "", "-": ""})
_LATIN = {"c": ["k"], "q": ["k"], "x": ["k", "s"], "y": ["i"], "v": ["w"]}
_LATIN_OK = set("abdefghilmnoprstuz")


def geez_segments(transliteration: str) -> list[str] | None:
    """A TraCES transliteration as segments. The sixth-order vowel is e; the labiovelars of q and ḫ go with kʷ;
    a proclitic's hyphen is removed. None for any other character."""
    word = unicodedata.normalize("NFC", transliteration).lower().replace("qʷ", "kʷ").replace("ḫʷ", "kʷ")
    word = word.translate(_GEEZ)
    return list(word) if word and set(word) <= _GEEZ_OK and set(word) & set("aeiouā") else None


def norm_segments(norm: str) -> list[str] | None:
    """An ORACC normalised form as segments. A form with a capital (a name or a logogram) is left out: no
    capital is in the letters allowed."""
    word = unicodedata.normalize("NFC", norm).translate(ct._LONG).translate(_NORM)
    return list(word) if word and set(word) <= _NORM_OK and set(word) & set(VOWELS) else None


def latin_segments(orth: str) -> list[str] | None:
    """A Latin form in its dictionary spelling: vowel length dropped, c and q as k, x as ks, qu as kw."""
    word = "".join(ch for ch in unicodedata.normalize("NFD", orth.lower()) if not unicodedata.combining(ch))
    out: list[str] = []
    for i, ch in enumerate(word):
        if ch == "u" and i and word[i - 1] == "q":
            out.append("w")
        elif ch in _LATIN:
            out += _LATIN[ch]
        elif ch in _LATIN_OK:
            out.append(ch)
        else:
            return None
    return out if out and set(out) & set(VOWELS) else None


_SYR_CONS = {"ܐ": "ʾ", "ܒ": "b", "ܓ": "g", "ܕ": "d", "ܗ": "h", "ܘ": "w", "ܙ": "z", "ܚ": "ḥ", "ܛ": "ṭ", "ܝ": "y",
             "ܟ": "k", "ܠ": "l", "ܡ": "m", "ܢ": "n", "ܣ": "s", "ܥ": "ʿ", "ܦ": "p", "ܨ": "ṣ", "ܩ": "q", "ܪ": "r",
             "ܫ": "š", "ܬ": "t"}
_SYR_VOWEL = {"ܰ": "a", "ܳ": "a", "ܶ": "e", "ܺ": "i", "ܽ": "u"}   # the West Syriac five
_SYR_OCCULTANS = "̱"
_SYR_SILENT = {"̈", "̇", "̣", "̥", "̊", "ܼ", "ܿ", "݀", "݁", "ـ"}
_SYR_LONG = {"ܘ": ("u",), "ܝ": ("i", "e")}


def syriac_segments(token: str) -> list[str] | None:
    """One West Syriac word with its vowel points as consonants and vowels. Zqapha is a; waw after u and yod
    after i or e are the vowel's length; a letter under the linea occultans is silent. None for a word with no
    vowel point or with any other character. A simplification for control texts, offered as no philology."""
    word = unicodedata.normalize("NFC", token)
    word = "".join(ch for ch in word if not unicodedata.category(ch).startswith("P") and not "܀" <= ch <= "܍")
    out: list[str] = []
    for i, ch in enumerate(word):
        nxt = word[i + 1] if i + 1 < len(word) else ""
        if ch in _SYR_CONS:
            if ch in _SYR_LONG and nxt not in _SYR_VOWEL and out and out[-1] in _SYR_LONG[ch]:
                continue
            out.append(_SYR_CONS[ch])
        elif ch in _SYR_VOWEL:
            out.append(_SYR_VOWEL[ch])
        elif ch == _SYR_OCCULTANS:
            if out and out[-1] not in VOWELS:
                out.pop()
        elif ch not in _SYR_SILENT:
            return None
    return out if out and set(out) & set(VOWELS) else None


_GREEK = {"α": "a", "β": "b", "γ": "g", "δ": "d", "ε": "e", "ζ": "z", "η": "e", "θ": "th", "ι": "i", "κ": "k",
          "λ": "l", "μ": "m", "ν": "n", "ξ": "x", "ο": "o", "π": "p", "ρ": "r", "σ": "s", "ς": "s", "τ": "t",
          "υ": "u", "φ": "ph", "χ": "kh", "ψ": "ps", "ω": "o"}


def greek_translit(word: str) -> str | None:
    """An alphabetic Greek word in the transliteration LSJ's entries carry in the skill: accents, breathings and
    the iota subscript dropped, vowel length unmarked. None for a word with a letter that is not Greek."""
    out = []
    for ch in unicodedata.normalize("NFD", word.lower()):
        if unicodedata.combining(ch) or unicodedata.category(ch).startswith("P") or ch in "᾽ʼ’":
            continue
        if ch not in _GREEK:
            return None
        out.append(_GREEK[ch])
    return "".join(out) or None


def greek_keys(word: str, signs: set) -> Word | None:
    """An alphabetic Greek word as sign keys, by the skill's Greek-to-Linear-B speller (the one that made LSJ's
    `lb_key`) and the glide rule; None when it is no valid word."""
    sys.path.append(str(LSJ.parents[2] / "lib"))
    import greek_spelling                                     # the skill's speller; read, never edited
    translit = greek_translit(word)
    keys = lsj_keys(greek_spelling.greek_to_lb(translit)) if translit else None
    keys = glide(keys, signs) if keys else None
    return keys if keys and valid(keys, signs) else None


def diodorus_docs(signs: set) -> tuple[list, dict]:
    """Diodorus 1 to 5 (Perseus TEI), a section as the document: inflected Greek spelled by rule."""
    import xml.etree.ElementTree as ET
    out, left = [], 0
    for div in ET.parse(DIODORUS).getroot().iter():
        if div.tag.endswith("div") and div.get("subtype") == "section":
            base = div.get("{http://www.w3.org/XML/1998/namespace}base", "").rsplit(":", 1)[-1]
            words = [greek_keys(token, signs) for token in "".join(div.itertext()).split()]
            left += sum(w is None for w in words)
            words = [w for w in words if w]
            if words:
                out.append((f"diodorus:{base}.{div.get('n')}", words))
    return out, {"documents": len(out), "words": sum(len(w) for _, w in out), "left_out": left}


# ---- readers: every source as documents of words in the edition's order -----------------------------------------

def _hebrew_doc(reference: str) -> str:
    for sep in (":", "."):
        if sep in reference:
            return reference.rsplit(sep, 1)[0]
    return reference


def segment_docs(language: str) -> list[tuple[str, list]]:
    """(document id, the document's words as segments or None where a word is left out), in order."""
    docs: dict[str, list] = collections.OrderedDict()
    if language in ("hebrew", "aramaic"):                    # OSHB marks each word's language in its morphology
        mark = {"hebrew": "H", "aramaic": "A"}[language]
        for row in ct._rows(ct.OSHB):
            if str(row.get("morphology") or "H")[:1] == mark:
                doc = _hebrew_doc(row["reference"]) if language == "hebrew" else row["reference"]
                docs.setdefault(doc, []).append(ct.hebrew_segments(row["surface"]))
    elif language == "ugaritic":                             # three tablets: the column is the document
        for row in ct._rows(ct.EUPT):
            column = str((row.get("locations") or [""])[0]).split(" ")[0]
            docs.setdefault(f"{row['document']} {column}", []).append(ct.ugaritic_segments(row["surface"]))
    elif language == "geez":                                 # 23 works: a run of twenty passages is the document
        for row in ct._rows(TRACES):
            block = int(row["passage"]) // 20 if str(row.get("passage", "")).isdigit() else 0
            docs.setdefault(f"{row['document_source_id']}:{block}", []).append(geez_segments(row["transliteration"]))
    elif language in ORACC:
        name, codes = ORACC[language]
        for row in ct._rows(ORACC_DIR / name):
            for token in row.get("tokens") or []:
                if token.get("lang") in codes:
                    seg = None if token.get("damaged") or not token.get("norm") else norm_segments(token["norm"])
                    docs.setdefault(str(row["canonical_id"]), []).append(seg)
    elif language == "syriac":                               # Ephrem, pointed in the West Syriac way; a stanza
        for row in ct._rows(ARAMAIC):
            if row.get("corpus_id") in SYRIAC_CORPORA:
                for token in row["form_original"].split():
                    docs.setdefault(f"{row['corpus_id']}:{row['reference']}", []).append(syriac_segments(token))
    elif language == "latin":                                # paradigm forms: the lexeme is the document
        import csv
        with open(LATIN, encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                docs.setdefault(row["lexeme"], []).append(latin_segments(row["orth_form"]))
    elif language == "arabic":
        with open(QURAN, encoding="utf-8") as fh:
            for line in fh:
                sura, _, text = line.rstrip("\n").split("|", 2) if line.count("|") >= 2 else ("", "", "")
                for token in text.split():
                    docs.setdefault(f"quran:{sura}", []).append(arabic_segments(token))
    elif language in TLH:
        if not _TLH_CACHE:                                   # one pass over the file serves all five languages
            code = {c: name for name, codes in TLH.items() for c in codes}
            for row in ct._rows(ct.TLHDIG):
                name = code.get(row.get("language"))
                if name:
                    seg = ct.cuneiform_segments(row["trans"]) if row.get("preserved") and row.get("trans") else None
                    _TLH_CACHE.setdefault(name, collections.OrderedDict()).setdefault(row["document_id"], []).append(seg)
        docs = _TLH_CACHE.get(language, docs)
    else:
        raise ValueError(language)
    return list(docs.items())


def written_docs(seg_docs: list, language: str, convention: str, t: r.Tables, signs: set) -> tuple[list, dict]:
    """Segment documents as documents of valid words under one convention, with the count of words left out."""
    out, left = [], 0
    for doc, segs in seg_docs:
        words = []
        for s in segs:
            w = r.word(s, language, t, convention) if s else None
            w = glide(w, signs) if w else None
            if w and valid(w, signs):
                words.append(w)
            else:
                left += 1
        if words:
            out.append((doc, words))
    return out, {"documents": len(out), "words": sum(len(w) for _, w in out), "left_out": left}


def linear_b_docs(signs: set) -> tuple[list, dict]:
    """Clean, DAMOS-verified syllabic words of the Pylos and Knossos tablets, by tablet, as written."""
    table = a.load_signs()
    rows = [row for row in ct._rows(ct.LINEAR_B)
            if row["document_id"][:2] in ("PY", "KN") and row["token_type"] == "syllabic"]
    rows.sort(key=lambda row: (row["document_id"], str(row["line_id"]), row["token_index"]))
    docs: dict[str, list] = collections.OrderedDict()
    left = 0
    for row in rows:
        ok = row.get("editorial_status") == "clean" and str(row.get("source_status", "")).startswith("DAMOS_VERIFIED")
        w = a.keys(row["token_normalized"], table) if ok else None
        if w and valid(w, signs):
            docs.setdefault(row["document_id"], []).append(w)
        else:
            left += 1
    out = list(docs.items())
    return out, {"documents": len(out), "words": sum(len(w) for _, w in out), "left_out": left}


def lsj_words(signs: set) -> tuple[list, dict]:
    """LSJ's lemmas in Linear B spelling as valid words. Training material only."""
    out, left = [], 0
    for row in ct._rows(LSJ):
        w = lsj_keys(row.get("lb_key") or "")
        w = glide(w, signs) if w else None
        if w and valid(w, signs):
            out.append(w)
        else:
            left += 1
    return out, {"words": len(out), "left_out": left}


# ---- the model -------------------------------------------------------------------------------------------------

class Model:
    """An interpolated n-gram model (Witten-Bell) of sign keys within the word, over a fixed alphabet."""

    def __init__(self, words, order: int, alphabet):
        self.order = order
        self.v = len(alphabet) + 1                           # the keys and the end symbol
        self.counts = [collections.defaultdict(collections.Counter) for _ in range(order)]
        for w in words:
            seq = (BOS,) * (order - 1) + tuple(w) + (END,)
            for i in range(order - 1, len(seq)):
                for k in range(order):
                    self.counts[k][seq[i - k:i]][seq[i]] += 1
        self.totals = [{c: sum(d.values()) for c, d in level.items()} for level in self.counts]

    def prob(self, context, symbol) -> float:
        context = tuple(context)[-(self.order - 1):] if self.order > 1 else ()
        p = 1.0 / self.v
        for k in range(len(context) + 1):
            ctx = context[len(context) - k:]
            seen = self.counts[k].get(ctx)
            if seen:
                types = len(seen)
                p = (seen.get(symbol, 0) + types * p) / (self.totals[k][ctx] + types)
        return p

    def log2(self, word) -> float:
        seq = (BOS,) * (self.order - 1) + tuple(word) + (END,)
        n = self.order - 1
        return sum(math.log2(self.prob(seq[i - n:i], seq[i])) for i in range(n, len(seq)))


def bits_per_sign(models, words) -> float:
    """Mean bits per sign (the end symbol counted) over the text's distinct word types, averaged over models."""
    types = list(dict.fromkeys(words))
    signs = sum(len(w) + 1 for w in types)
    return sum(-sum(m.log2(w) for w in types) / signs for m in models) / len(models)


def draw(members: dict, total: int, seed: int) -> list:
    """`total` distinct word types in equal shares from an arm's members, by seed. A member that holds fewer
    than its share gives all it has, and the others make up the difference."""
    types = {name: sorted(set(words)) for name, words in members.items()}
    out: list = []
    left, waiting = total, len(types)
    for name in sorted(types, key=lambda n: (len(types[n]), n)):
        take = min(len(types[name]), left // waiting)
        out += random.Random(f"{seed}:{name}").sample(types[name], take)
        left, waiting = left - take, waiting - 1
    return out


def holds(members: dict) -> int:
    """The distinct word types an arm's members hold between them."""
    return sum(len(set(words)) for words in members.values())


# ---- the statistic ---------------------------------------------------------------------------------------------

def margin(fit: dict, arm: str, absent: tuple = ()) -> float:
    """M(arm, text): the best rival's bits per sign minus the arm's. Positive means the arm fits best."""
    rivals = [h for name, h in fit.items() if name != arm and name not in absent]
    if not rivals:
        raise ValueError("no rival arm to compare with")
    return min(rivals) - fit[arm]


def threshold(null_margins) -> float:
    """θ: the highest margin any text of a wrong language reached."""
    return max(null_margins)


def power(margins, theta: float) -> float:
    return sum(m > theta for m in margins) / len(margins)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()
