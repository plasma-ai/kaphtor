# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Branch-distribution matrix and conjugated-verb census for the lexicon.

Joins every lexicon/onomasticon item to its Proto-Semitic root (cognate cache
primary path, skeleton fallback), reads branch attestation from the SED
``Analogues`` columns plus the entry's own cognates, and classifies each item's
cross-Semitic distribution:

    EAST_ONLY                  attested only in East Semitic (Akkadian/Eblaite)
    SOUTH_ONLY                 attested only in South Semitic (Ethiopic + MSA)
    EAST_SOUTH_NO_CENTRALWEST  East + South, absent from Arabic and NWS
    CENTRAL_NON_NWS            Arabic attested, absent from NWS
    NWS_ATTESTED               any NWS attestation (incl. contact-sweep demotions)
    PAN_SEMITIC                NWS + East + (South or Arabic)
    NO_ROOT_MATCH              no root claimed, or no join at any threshold

Non-NWS candidates are double-checked by a direct sweep of the five NWS
contact lexicons (Hebrew, Ugaritic, Aramaic, Phoenician, Krahmalkov) with
NWS merger variants (interdentals, laterals, emphatics) — a root absent from
SED's NWS columns but present in the contact lexicons is NOT exclusive.

Also harvests every conjugated verbal form across lexicon.json and
translations.json into a work-list for stem/conjugation classification.

The cognate cache is the one cognate_search.py --build-cache writes to the user
cache. Read-only over the data — writes only to --out.

    uv run tools/linear_a/analysis/branch_distribution.py --out DIR [--json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    __package__ = "tools.linear_a.analysis"

from ...core.semitic_root_schema import roots_records
from ...paths import CONTACT_DATA, LINEAR_A_DATA, SEMITIC_ROOTS_DATA, NotInCheckout, require
from ..cognate_search import CACHE_FILE as COGNATE_CACHE

CACHE_DISTANCE_MAX = 0.3

# SED Analogues language keys → branch, over every language key the roots
# carry; keys not listed fall to OTHER and are reported, never silently used.
LANG_BRANCH: dict[str, str] = {
    # East Semitic
    "Akkadian": "EAST",
    "Eblaitic": "EAST",
    "Assyro-Babylonian": "EAST",
    "East Semitic": "EAST",
    "Palaeosyrian": "EAST",
    # South Semitic: Ethiopic
    "Geez": "SOUTH",
    "Ge'ez": "SOUTH",
    "Ethiopic": "SOUTH",
    "Tigre": "SOUTH",
    "Tigrinya": "SOUTH",
    "Amharic": "SOUTH",
    "Old Amharic": "SOUTH",
    "Gurage": "SOUTH",
    "Harari": "SOUTH",
    "East Ethiopic": "SOUTH",
    "Argobba": "SOUTH",
    "Gafat": "SOUTH",
    # South Semitic: Modern South Arabian
    "Mehri": "SOUTH",
    "Jibbali": "SOUTH",
    "Soqotri": "SOUTH",
    "Harsusi": "SOUTH",
    "Modern South Arabian": "SOUTH",
    # Epigraphic South Arabian — tracked apart; never carries a SOUTH verdict alone
    "Epigraphic South Arabian": "ESA",
    "Sabaic": "ESA",
    "Old Sabaean": "ESA",
    # Central Semitic, non-NWS
    "Arabic": "ARABIC",
    "Modern Arabic": "ARABIC",
    "Classical Arabic": "ARABIC",
    "Pre-Islamic North Arabian": "ARABIC",
    "Lihyanite": "ARABIC",
    # Northwest Semitic
    "Hebrew": "NWS",
    "Ugaritic": "NWS",
    "Phoenician": "NWS",
    "Punic": "NWS",
    "Canaanite": "NWS",
    "Amorite": "NWS",
    "Moabite": "NWS",
    "Aramaic": "NWS",
    "Syrian Aramaic": "NWS",
    "Judaic Aramaic": "NWS",
    "Mandaic Aramaic": "NWS",
    "Biblical Aramaic": "NWS",
    "Modern Aramaic": "NWS",
    "Nabataean": "NWS",
    "Syriac": "NWS",
    # Non-Semitic / bookkeeping columns
    "Egyptian": "IGNORE",
    "Greek": "IGNORE",
    "Libyco-Berber": "IGNORE",
    "Cushitic": "IGNORE",
    "West Cushitic": "IGNORE",
    "Hausa": "IGNORE",
    "Oromo": "IGNORE",
    "Tuareg": "IGNORE",
    "Notes": "IGNORE",
    "Semitic": "IGNORE",
    "Proto-Semitic": "IGNORE",
}

# Onomasticon affiliation classes admitted to the Semitic item pool.
SEM_AFFILIATIONS = {
    "semitic", "canaanite", "nws", "NWS", "northwest_semitic", "amorite",
    "east_semitic", "akkadian_contact", "egyptian_nws_hybrid", "egyptian_nws",
    "hurrian_semitic_hybrid",
}

NWS_CONTACT_FILES = (
    "hebrew_lexicon.jsonl",
    "ugaritic_lexicon.jsonl",
    "aramaic_lexicon.jsonl",
    "phoenician_lexicon.jsonl",
    "krahmalkov_glossary.jsonl",
)

VERBAL_MARKERS = re.compile(
    r"\b(tG|Gt|tD|[GDŠN]-stem|imperfective|perfective|imperative|jussive|"
    r"participle|infinitive|verbal noun|energic|yaqtul|suffix conjugation|"
    r"prefix conjugation|cohortative|1cs|2[mf]s|3[mf]s|3[mf]p|1cp)\b",
)

# Transliteration variants folded before skeleton comparison.
CONSONANT_FOLD = str.maketrans({
    "ʾ": "ʔ", "ʿ": "ʕ", "’": "ʔ", "‘": "ʕ",
    "ĝ": "g", "ǵ": "ġ",
})

VOWELS = set("aeiouāēīōūăĕĭŏŭəǝ")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tokenize_consonants(s: str) -> tuple[str, ...]:
    """Consonantal skeleton of a root string, diacritics preserved.

    Combining marks attach to their base (ṭ, ṣ, š, ḏ…); vowels, hyphens,
    asterisks, and template placeholders (V, parenthesised material) drop.
    """
    s = s.strip().translate(CONSONANT_FOLD)
    s = re.sub(r"\(.*?\)", "", s)
    for digraph, mono in (("sh", "š"), ("th", "ṯ"), ("kh", "ḫ"), ("gh", "ġ"), ("dh", "ḏ"), ("ts", "ṣ")):
        s = s.replace(digraph, mono)
    s = unicodedata.normalize("NFC", s)
    out: list[str] = []
    for ch in s:
        if ch in "*-–—/ 0123456789#":
            continue
        if ch.lower() in VOWELS or ch == "V":
            continue
        if unicodedata.combining(ch) and out:
            out[-1] += ch
            continue
        if ch.isalpha() or ch in "ʔʕ":
            out.append(ch.lower() if ch not in "ʔʕ" else ch)
    return tuple(out)


NON_PS_MARKERS = re.compile(
    r"Egyptian|Akk\.|Akkadian|Pre-Greek|Hurrian|Luwian|Kubaba|disputed|"
    r"clitic|logographic|substrate|Greek",
    re.IGNORECASE,
)


def _root_like(token: str) -> bool:
    """True for root-notation tokens: hyphenated radicals, ≤2 base chars each."""
    token = token.lstrip("√*").rstrip(".,;")
    if "-" not in token:
        return False
    for seg in token.split("-"):
        base = [c for c in unicodedata.normalize("NFC", seg) if not unicodedata.combining(c)]
        if not 1 <= len(base) <= 2:
            return False
    return True


def parse_claimed_roots(root_field: str) -> tuple[list[str], bool]:
    """Extract root-notation components from a freeform lexicon root field.

    Compounds split on '+', alternatives on '/' and '(or …)'; prose descriptors
    and contact-language references ('Akk. mātu', 'wsỉr (Egyptian)') are dropped.
    Returns (components, has_non_ps_reference).
    """
    if not root_field or not root_field.strip():
        return [], False
    field = root_field.strip()
    non_ps = bool(NON_PS_MARKERS.search(field))
    field = re.sub(r"\(or ([^)]+)\)", r"/ \1", field)
    field = re.sub(r'"[^"]*"', "", field)
    parts: list[str] = []
    for chunk in re.split(r"[+/]", field):
        chunk = chunk.strip()
        if not chunk:
            continue
        num = re.search(r"PS #\d+", chunk)
        if num:
            parts.append(chunk)
            continue
        found = False
        for tok in chunk.split():
            if _root_like(tok):
                parts.append(tok.lstrip("√").rstrip(".,;"))
                found = True
                break
        # Bare single-radical components of compounds (e.g. 'ḏ + l-w-y')
        if not found and len(chunk) <= 2 and not NON_PS_MARKERS.search(chunk):
            parts.append(chunk)
    return parts, non_ps


class RootJoiner:
    """Join claimed roots to SED entries via cognate_cache, then skeletons."""

    def __init__(self, semitic_roots: list[dict], cognate_cache: dict[str, list[dict]]):
        self.by_ps_string = {r["Proto-Semitic"]: r for r in semitic_roots}
        self.by_number = {r["Number"]: r for r in semitic_roots}
        self.by_skeleton: dict[tuple[str, ...], list[dict]] = {}
        for r in semitic_roots:
            self.by_skeleton.setdefault(tokenize_consonants(r["Proto-Semitic"]), []).append(r)
        self.cache = cognate_cache

    def join(self, word: str, claimed: str) -> tuple[str, list[dict]]:
        """Return (method, matched SED entries) for one claimed root component."""
        num = re.search(r"PS #(\d+)", claimed)
        if num and num.group(1) in self.by_number:
            return "number_ref", [self.by_number[num.group(1)]]
        skel = tokenize_consonants(claimed)
        if not skel:
            return "NO_ROOT", []
        hits = [
            h for h in self.cache.get(word, [])
            if h.get("language") == "Proto-Semitic"
            and h.get("distance", 99) <= CACHE_DISTANCE_MAX
            and tokenize_consonants(h["root"]) == skel
            and h["root"] in self.by_ps_string
        ]
        if hits:
            hits.sort(key=lambda h: h["distance"])
            return "cache", [self.by_ps_string[h["root"]] for h in hits]
        direct = self.by_skeleton.get(skel, [])
        if direct:
            return "skeleton", direct
        # Weak-radical leniency: allow the SED string to carry one final w/y
        # the claimed skeleton lacks (III-weak roots cited without the glide).
        lenient = self.by_skeleton.get(skel + ("y",), []) + self.by_skeleton.get(skel + ("w",), [])
        if lenient:
            return "skeleton_weak", lenient
        return "JOIN_FAILED", []


def branches_of_root(root_entry: dict) -> tuple[set[str], set[str]]:
    """Branch set + unknown language keys from one SED entry's Analogues."""
    branches: set[str] = set()
    unknown: set[str] = set()
    for lang in (root_entry.get("Analogues") or {}):
        b = LANG_BRANCH.get(lang)
        if b is None:
            unknown.add(lang)
        elif b != "IGNORE":
            branches.add(b)
    return branches, unknown


def branches_of_cognates(cognates: dict[str, str] | None) -> set[str]:
    if not cognates:
        return set()
    out: set[str] = set()
    for lang in cognates:
        b = LANG_BRANCH.get(lang)
        if b and b != "IGNORE":
            out.add(b)
    return out


def classify(branches: set[str]) -> str:
    if not branches:
        return "NO_ROOT_MATCH"
    if "NWS" in branches:
        if "EAST" in branches and ("SOUTH" in branches or "ARABIC" in branches):
            return "PAN_SEMITIC"
        return "NWS_ATTESTED"
    if "ARABIC" in branches:
        return "CENTRAL_NON_NWS"
    east, south = "EAST" in branches, "SOUTH" in branches
    if east and south:
        return "EAST_SOUTH_NO_CENTRALWEST"
    if east:
        return "EAST_ONLY"
    if south:
        return "SOUTH_ONLY"
    if branches == {"ESA"}:
        return "ESA_ONLY"
    return "NO_ROOT_MATCH"


# NWS merger variants: how a PS consonant may surface in the NWS contact
# lexicons' consonantal match_keys (Hebrew/Aramaic mergers, alphabetic gaps).
NWS_REFLEXES: dict[str, tuple[str, ...]] = {
    "ṯ": ("ṯ", "š", "t", "th"),
    "ḏ": ("ḏ", "z", "d"),
    "ẓ": ("ẓ", "ṣ", "ṭ", "z"),
    "ś": ("ś", "š", "s"),
    "ḍ": ("ḍ", "ṣ", "ʕ", "q"),
    "ḫ": ("ḫ", "ḥ", "h", "x"),
    "ġ": ("ġ", "ʕ", "g"),
    "ʔ": ("ʔ", "ʾ", ""),
    "ʕ": ("ʕ", "ʿ", ""),
    "w": ("w", "y", "v"),
    "p": ("p", "f"),
}


def nws_variant_keys(skel: tuple[str, ...]) -> set[str]:
    """All plausible NWS consonant-string realizations of a PS skeleton."""
    keys = {""}
    for c in skel:
        reflexes = NWS_REFLEXES.get(c, (c,))
        keys = {k + r for k in keys for r in reflexes}
        if len(keys) > 4096:
            break
    return keys


class NWSContactIndex:
    """Union of consonantal match keys across the five NWS contact lexicons."""

    SAMPLES_PER_KEY = 3

    def __init__(self, contact_dir: Path):
        self.keys: dict[str, set[str]] = {}
        self.samples: dict[str, dict[str, list[dict]]] = {}
        self.hashes: dict[str, str] = {}
        for fname in NWS_CONTACT_FILES:
            path = require(contact_dir / fname, fname)
            bucket: set[str] = set()
            samples: dict[str, list[dict]] = {}
            with open(path, encoding="utf-8") as fh:
                for line in fh:
                    try:
                        row = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    row_keys: set[str] = set()
                    for k in ("normalized", "headword_normalized", "root", "root_normalized"):
                        v = row.get(k)
                        if isinstance(v, str) and v:
                            row_keys.add(v.replace("-", "").lower())
                    for mk in row.get("match_keys") or []:
                        if isinstance(mk, str):
                            row_keys.add(mk.replace("-", "").lower())
                    bucket |= row_keys
                    for rk in row_keys:
                        rows = samples.setdefault(rk, [])
                        if len(rows) < self.SAMPLES_PER_KEY:
                            rows.append({
                                "form": row.get("form_original") or row.get("headword") or "",
                                "normalized": row.get("normalized") or row.get("headword_normalized") or rk,
                                "meaning": (row.get("meaning") or "")[:120],
                            })
            self.keys[fname] = bucket
            self.samples[fname] = samples
            self.hashes[fname] = _sha256(path)

    def sweep(self, skel: tuple[str, ...]) -> dict[str, dict]:
        variants = nws_variant_keys(skel)
        out: dict[str, dict] = {}
        for fname, bucket in self.keys.items():
            lang = fname.split("_")[0]
            matched = variants & bucket
            rows: list[dict] = []
            for key in sorted(matched):
                for s in self.samples[fname].get(key, []):
                    if s not in rows:
                        rows.append(s)
                if len(rows) >= self.SAMPLES_PER_KEY:
                    break
            out[lang] = {"hit": bool(matched), "samples": rows[: self.SAMPLES_PER_KEY]}
        return out


def harvest_verbs(lexicon: list[dict], translations: dict[str, dict]) -> list[dict]:
    forms: dict[str, dict] = {}
    for e in lexicon:
        if e.get("confidence") == "REJECTED":
            continue
        blob = " ".join(str(e.get(k, "")) for k in ("meaning", "note", "category"))
        markers = sorted(set(VERBAL_MARKERS.findall(blob)))
        if not markers and not str(e.get("category", "")).startswith("verb"):
            continue
        forms[e["word"]] = {
            "word": e["word"],
            "reading": e.get("reading"),
            "root": e.get("root"),
            "gloss": e.get("meaning"),
            "markers": markers,
            "sources": ["lexicon"],
            "attestations": e.get("attestations", []),
            "note": e.get("note"),
        }
    for insc, t in translations.items():
        for w in t.get("words", []):
            if not isinstance(w, dict):
                continue
            blob = (w.get("gloss") or "") + " " + (w.get("note") or "")
            markers = sorted(set(VERBAL_MARKERS.findall(blob)))
            if not markers:
                continue
            la = w.get("linear_a")
            if not la:
                continue
            if la in forms:
                f = forms[la]
                if "translations" not in f["sources"]:
                    f["sources"].append("translations")
                f.setdefault("translation_attestations", []).append(insc)
                f["markers"] = sorted(set(f["markers"]) | set(markers))
            else:
                forms[la] = {
                    "word": la,
                    "reading": w.get("reading"),
                    "root": None,
                    "gloss": w.get("gloss"),
                    "markers": markers,
                    "sources": ["translations"],
                    "translation_attestations": [insc],
                    "note": w.get("note"),
                }
    return sorted(forms.values(), key=lambda f: f["word"])


def build_items(lexicon: list[dict], onomasticon: list[dict]) -> list[dict]:
    """Merge active lexicon entries with Semitic-affiliated onomasticon tokens."""
    items: dict[str, dict] = {}
    for e in lexicon:
        if e.get("confidence") == "REJECTED":
            continue
        items[e["word"]] = {
            "word": e["word"],
            "source": "lexicon",
            "reading": e.get("reading"),
            "root_field": e.get("root") or "",
            "meaning": e.get("meaning"),
            "confidence": e.get("confidence"),
            "category": e.get("category"),
            "cognates": e.get("cognates"),
            "attestations": e.get("attestations", []),
        }
    for o in onomasticon:
        if o.get("affiliation") not in SEM_AFFILIATIONS:
            continue
        ref = o.get("lexicon_ref")
        if ref and ref in items:
            items[ref].setdefault("onomasticon", {}).update(
                {"type": o.get("type"), "affiliation": o.get("affiliation")}
            )
            continue
        tok = o["token"]
        if tok in items:
            items[tok].setdefault("onomasticon", {}).update(
                {"type": o.get("type"), "affiliation": o.get("affiliation")}
            )
            continue
        items[tok] = {
            "word": tok,
            "source": "onomasticon",
            "reading": o.get("reading"),
            "root_field": "",
            "meaning": o.get("meaning"),
            "confidence": o.get("affiliation_confidence"),
            "category": o.get("type"),
            "cognates": None,
            "attestations": o.get("attestations", []),
            "onomasticon": {"type": o.get("type"), "affiliation": o.get("affiliation")},
        }
    return sorted(items.values(), key=lambda x: x["word"])


def run(data_dir: Path, contact_dir: Path, out_dir: Path, cache_path: Path = COGNATE_CACHE,
        roots_dir: Path = SEMITIC_ROOTS_DATA) -> dict:
    inputs = {"lexicon.json": data_dir / "lexicon.json", "onomasticon.json": data_dir / "onomasticon.json",
              "cognate_cache.json": cache_path, "semitic_roots.json": roots_dir / "semitic_roots.json",
              "translations.json": data_dir / "translations.json"}
    for name, path in inputs.items():
        require(path, name if name != "cognate_cache.json"
                else "the cognate cache (build it with cognate_search.py --build-cache)")

    def read(name: str):
        return json.loads(inputs[name].read_text(encoding="utf-8"))

    lexicon = read("lexicon.json")["entries"]
    onomasticon = read("onomasticon.json")["entries"]
    cache = read("cognate_cache.json")
    semitic_roots = roots_records(read("semitic_roots.json"))
    translations = read("translations.json")["translations"]

    joiner = RootJoiner(semitic_roots, cache)
    nws_index = NWSContactIndex(contact_dir)

    items = build_items(lexicon, onomasticon)
    matrix: list[dict] = []
    unknown_langs: Counter = Counter()
    class_counts: Counter = Counter()
    method_counts: Counter = Counter()

    for item in items:
        components, non_ps_ref = parse_claimed_roots(item["root_field"])
        comp_records: list[dict] = []
        all_branches: set[str] = set()
        for comp in components:
            method, matched = joiner.join(item["word"], comp)
            method_counts[method] += 1
            branches: set[str] = set()
            roots_out = []
            for r in matched:
                b, unk = branches_of_root(r)
                unknown_langs.update(unk)
                branches |= b
                roots_out.append({
                    "number": r["Number"],
                    "ps": r["Proto-Semitic"],
                    "meaning": r["Meaning"],
                    "branches": sorted(b),
                })
            comp_records.append({
                "claimed": comp,
                "skeleton": "-".join(tokenize_consonants(comp)),
                "join_method": method,
                "sed_roots": roots_out,
                "branches": sorted(branches),
            })
            all_branches |= branches
        cog_branches = branches_of_cognates(item.get("cognates"))
        all_branches |= cog_branches

        cls = classify(all_branches)
        if cls == "NO_ROOT_MATCH":
            if not components and non_ps_ref:
                cls = "NON_SEMITIC_REFERENCE"
            elif not item["root_field"].strip():
                cls = "NO_ROOT_MATCH"
            elif components:
                cls = "JOIN_FAILED"
        record: dict[str, Any] = {
            "word": item["word"],
            "source": item["source"],
            "reading": item["reading"],
            "meaning": item["meaning"],
            "confidence": item["confidence"],
            "category": item["category"],
            "root_field": item["root_field"],
            "components": comp_records,
            "cognate_dict_branches": sorted(cog_branches),
            "branches": sorted(all_branches),
            "distribution_class": cls,
            "is_compound": len(components) > 1,
            "non_ps_reference": non_ps_ref,
        }
        if item.get("onomasticon"):
            record["onomasticon"] = item["onomasticon"]

        # NWS contact sweep for every non-NWS candidate with a joined skeleton
        if cls in ("EAST_ONLY", "SOUTH_ONLY", "EAST_SOUTH_NO_CENTRALWEST",
                   "CENTRAL_NON_NWS", "ESA_ONLY"):
            sweeps = {}
            demoted = False
            for comp in comp_records:
                skel = tuple(comp["skeleton"].split("-")) if comp["skeleton"] else ()
                if not skel:
                    continue
                hit_map = nws_index.sweep(skel)
                sweeps[comp["claimed"]] = hit_map
                if any(v["hit"] for v in hit_map.values()):
                    demoted = True
            record["nws_contact_sweep"] = sweeps
            record["non_nws_candidate"] = True
            if demoted:
                record["distribution_class"] = "NWS_ATTESTED"
                record["demoted_by_contact_sweep"] = True
                cls = "NWS_ATTESTED"

        class_counts[record["distribution_class"]] += 1
        matrix.append(record)

    verb_forms = harvest_verbs(lexicon, translations)

    manifest = {
        "generated_by": "branch_distribution.py",
        "data_dir": str(data_dir),
        "contact_dir": str(contact_dir),
        "input_hashes": {name: _sha256(path) for name, path in inputs.items()},
        "nws_contact_hashes": nws_index.hashes,
        "cache_distance_max": CACHE_DISTANCE_MAX,
        "item_count": len(matrix),
        "class_counts": dict(class_counts),
        "join_method_counts": dict(method_counts),
        "unknown_analogue_languages": dict(unknown_langs),
        "verb_form_count": len(verb_forms),
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "branch_matrix.json", "w", encoding="utf-8") as fh:
        json.dump({"manifest": manifest, "items": matrix}, fh, ensure_ascii=False, indent=1)
    with open(out_dir / "verb_forms.json", "w", encoding="utf-8") as fh:
        json.dump({"manifest": {k: manifest[k] for k in ("generated_by", "input_hashes", "verb_form_count")},
                   "forms": verb_forms}, fh, ensure_ascii=False, indent=1)
    return manifest


def main() -> int:
    try:
        _run()
    except NotInCheckout as e:
        print(f"stopped: {e}", file=sys.stderr)
        return 2
    return 0


def _run() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--data-dir", type=Path, default=LINEAR_A_DATA,
                    help="Directory holding lexicon/onomasticon/translations JSON")
    ap.add_argument("--roots-dir", type=Path, default=SEMITIC_ROOTS_DATA,
                    help="Directory holding semitic_roots.json")
    ap.add_argument("--cognate-cache", type=Path, default=COGNATE_CACHE,
                    help="The cognate cache cognate_search.py --build-cache writes")
    ap.add_argument("--contact-dir", type=Path, default=CONTACT_DATA,
                    help="Directory holding the NWS contact JSONLs")
    ap.add_argument("--out", type=Path, required=True, help="Output directory")
    ap.add_argument("--json", action="store_true", help="Print manifest as JSON")
    args = ap.parse_args()

    manifest = run(args.data_dir, args.contact_dir, args.out, args.cognate_cache, args.roots_dir)
    if args.json:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
    else:
        print(f"items: {manifest['item_count']}")
        print("classes:")
        for cls, n in sorted(manifest["class_counts"].items(), key=lambda x: -x[1]):
            print(f"  {cls:28s} {n}")
        print("join methods:", manifest["join_method_counts"])
        if manifest["unknown_analogue_languages"]:
            print("UNKNOWN Analogue languages:", manifest["unknown_analogue_languages"])
        print(f"verb forms: {manifest['verb_form_count']}")


if __name__ == "__main__":
    sys.exit(main())
