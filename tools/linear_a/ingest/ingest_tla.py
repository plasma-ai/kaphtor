#!/usr/bin/env python3
"""Ingest TLA (Thesaurus Linguae Aegyptiae) data into the Egyptian contact lexicon.

Queries the TLA SRU API and optionally the HF Late Egyptian corpus to enrich
data/contact/egyptian_lexicon.jsonl with machine-imported entries. API responses are
cached in the user cache (`CACHE/tla`), never in the repository; the lexicon is copied
into `tools.paths.BACKUPS` before entries are appended. When SRU returns fewer than 10
candidates, hand-curated entries from data/contact/review/tla_curated_fallback.jsonl
(optional) are added.

Usage:
    python3 tools/linear_a/ingest/ingest_tla.py              # full run
    python3 tools/linear_a/ingest/ingest_tla.py --dry-run     # show what would be imported
    python3 tools/linear_a/ingest/ingest_tla.py --use-cache   # skip API, use cached XML only

Attribution: di Mino
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    __package__ = "tools.linear_a.ingest"

from ...ane.query_portal_common import ssl_context
from ...core.contact_lexicon import validate_entry
from ...paths import BACKUPS, CACHE, CONTACT_DATA, NotInCheckout, require

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
LEXICON_PATH = CONTACT_DATA / "egyptian_lexicon.jsonl"
CACHE_DIR = CACHE / "tla"
QUERY_CACHE_DIR = CACHE_DIR / "lemma_queries"
HF_CACHE_PATH = CACHE_DIR / "tla_late_egyptian.jsonl"

SRU_BASE = "https://textplus.thesaurus-linguae-aegyptiae.de/sru"
USER_AGENT = "kaphtor/1.0 (lexicon ingest)"

# ---------------------------------------------------------------------------
# SRU query definitions — each tuple: (filename_stem, query_string)
# ---------------------------------------------------------------------------
SRU_QUERIES: list[tuple[str, str]] = [
    ("kftj", "lemma=kftj*"),
    ("aamu", "lemma=ꜥꜣmw*"),
    ("hau", "lemma=ḥꜣw*"),
    ("mnw", "lemma=mnw*"),
    ("qdsh", "lemma=qdš*"),
    ("nb_baseform", "baseform=nb"),
    ("hr_baseform", "baseform=ḥr"),
    ("imn_baseform", "baseform=ꞽmn"),
    ("propn", "pos=PROPN"),
    ("trans_ship", "translation=/lang=eng ship"),
    ("trans_sea", "translation=/lang=eng sea"),
    ("trans_copper", "translation=/lang=eng copper"),
    ("trans_crete", "translation=/lang=eng Crete"),
]

# Maximum records per SRU request
SRU_MAX_RECORDS = 250

# ---------------------------------------------------------------------------
# Contact-relevant semantic domain classification
# ---------------------------------------------------------------------------

# Keywords in translations/glosses that signal contact-relevant entries.
# Maps keyword patterns → semantic domains.
DOMAIN_KEYWORDS: dict[str, list[str]] = {
    # Divine names and cult
    r"(?i)\b(god|goddess|deity|divine|divin|sacred|holy|temple|shrine|chapel|cult|priest|ritual|offer|incense|libation)\b": ["divine_name", "cult"],
    r"(?i)\b(amun|amon|atum|hathor|horus|isis|osiris|ptah|seth|thoth|re|ra|mut|min|nut|geb|khnum|sobek|neith|sekhmet|bastet|anubis|maat|qudshu|qedeshet|reshep|resheph|astarte|baal|anat)\b": ["divine_name"],
    # Toponyms and ethnonyms
    r"(?i)\b(crete|cretan|keftiu|aegean|cyprus|byblos|ugarit|sidon|tyre|canaan|retjenu|syria|punt|nubia|hatti|mitanni|alashiya|memphis|thebes|karnak)\b": ["toponym"],
    r"(?i)\b(asiatic|foreigner|people|tribe|land of|country)\b": ["ethnonym"],
    r"(?i)\b(haunebut|ḥꜣw|kftj)\b": ["ethnonym", "toponym"],
    # Maritime
    r"(?i)\b(ship|boat|vessel|sail|oar|mast|anchor|port|harbour|harbor|sea|ocean|wave|navigate|voyage|fleet)\b": ["maritime"],
    # Material culture
    r"(?i)\b(copper|bronze|tin|gold|silver|lapis|turquoise|ivory|ebony|cedar|oil|wine|grain|textile|dye|purple|murex|pottery|vase|amphora|jar|faience|glass)\b": ["material_culture"],
    # Cult (additional)
    r"(?i)\b(festival|feast|procession|oracle|prophet|seer|dream|vision|blessing|curse|oath|covenant)\b": ["cult"],
}

# Query stems that carry intrinsic domain assignments
QUERY_DOMAIN_HINTS: dict[str, list[str]] = {
    "kftj": ["toponym", "ethnonym"],
    "aamu": ["ethnonym"],
    "hau": ["ethnonym"],
    "mnw": ["divine_name"],
    "qdsh": ["divine_name", "cult"],
    "nb_baseform": ["title"],
    "hr_baseform": ["divine_name"],
    "imn_baseform": ["divine_name"],
    "trans_ship": ["maritime"],
    "trans_sea": ["maritime"],
    "trans_copper": ["material_culture"],
    "trans_crete": ["toponym"],
}

# The domains an entry must fall in to be imported.
RELEVANT_DOMAINS = {"divine_name", "toponym", "ethnonym", "material_culture",
                    "maritime", "cult", "title", "loan", "aegean_interface"}


def classify_domains(text: str, query_stem: str, pos: str = "") -> list[str]:
    """Classify an entry into contact-relevant semantic domains based on its
    translation/gloss text, originating query, and POS tag.

    Returns empty list for entries that are not contact-relevant, filtering them
    out of the import pipeline.
    """
    domains: set[str] = set()
    keyword_matched = False

    # Scan translation text for keyword matches
    for pattern, dom_list in DOMAIN_KEYWORDS.items():
        if re.search(pattern, text):
            domains.update(dom_list)
            keyword_matched = True

    # Apply query-level hints only when corroborated:
    # - For divine_name/toponym/ethnonym queries: require PROPN POS or keyword match
    # - For material/maritime translation queries: always apply (the query IS the filter)
    hints = QUERY_DOMAIN_HINTS.get(query_stem, [])
    if hints:
        translation_queries = {"trans_ship", "trans_sea", "trans_copper", "trans_crete"}
        if query_stem in translation_queries:
            # Translation queries are inherently filtered — apply hints directly
            domains.update(hints)
        elif pos in ("PROPN",) or keyword_matched:
            # For lemma/baseform queries, only apply if POS confirms or keywords matched
            domains.update(hints)
        # Otherwise: query hint alone is insufficient for non-PROPN, non-keyword entries

    relevant = domains & RELEVANT_DOMAINS
    return sorted(relevant) if relevant else []


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

def http_get(url: str, *, timeout: float) -> tuple[bytes, str]:
    """GET `url` with the project User-Agent. Returns (body, charset); raises on HTTP errors."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout, context=ssl_context()) as response:
        return response.read(), response.headers.get_content_charset() or "utf-8"


# ---------------------------------------------------------------------------
# SRU API interaction
# ---------------------------------------------------------------------------

def build_sru_url(query: str, start_record: int = 1) -> str:
    """Build a TLA SRU query URL."""
    params = {
        "queryType": "lex",
        "query": query,
        "maximumRecords": str(SRU_MAX_RECORDS),
        "startRecord": str(start_record),
    }
    return f"{SRU_BASE}?{urllib.parse.urlencode(params)}"


def fetch_sru_xml(query_stem: str, query: str, *, use_cache: bool = False) -> str | None:
    """Fetch SRU XML for a query. Returns XML string or None on failure.

    Caches responses to QUERY_CACHE_DIR/<stem>.xml.
    """
    cache_path = QUERY_CACHE_DIR / f"{query_stem}.xml"

    # Return cached if available
    if cache_path.exists():
        print(f"  [cache] {query_stem}: using cached {cache_path.name}")
        return cache_path.read_text(encoding="utf-8")

    if use_cache:
        print(f"  [skip]  {query_stem}: no cache, --use-cache mode")
        return None

    url = build_sru_url(query)
    print(f"  [fetch] {query_stem}: {url}")

    try:
        body, charset = http_get(url, timeout=30)
        xml_text = body.decode(charset, errors="replace")

        # Cache the response
        QUERY_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(xml_text, encoding="utf-8")
        print(f"  [cache] saved {cache_path.name} ({len(xml_text)} bytes)")

        # Rate-limit: 1s between requests
        time.sleep(1.0)
        return xml_text

    except Exception as e:  # noqa: BLE001 — a failed query is reported and skipped; the others still run
        print(f"  [error] {query_stem}: {e}")
        return None


# ---------------------------------------------------------------------------
# XML parsing — FCS-lex format
# ---------------------------------------------------------------------------

# TLA SRU returns XML in the FCS (Federated Content Search) lexicon format.
# Namespace handling is forgiving — we strip namespaces for simpler XPath.

def strip_ns(xml_text: str) -> str:
    """Remove XML namespace prefixes for easier parsing."""
    # Remove xmlns declarations
    cleaned = re.sub(r'\sxmlns[^"]*"[^"]*"', '', xml_text)
    # Remove namespace prefixes from tags
    cleaned = re.sub(r'<(/?)[\w]+:', r'<\1', cleaned)
    return cleaned


def parse_sru_response(xml_text: str, query_stem: str) -> list[dict[str, Any]]:
    """Parse SRU XML response into candidate entry dicts.

    The TLA SRU API returns CLARIN FCS-lex format:
      searchRetrieveResponse > records > record > recordData >
        Resource > ResourceFragment > DataView > Entry > Field > Value

    Each returned dict has:
      tla_lemma_id, transliteration, pos, translations (list of str),
      hieroglyphs, tla_url, query_stem
    """
    if not xml_text:
        return []

    cleaned = strip_ns(xml_text)

    try:
        root = ET.fromstring(cleaned)
    except ET.ParseError as e:
        print(f"  [parse] {query_stem}: XML parse error: {e}")
        return []

    # Check numberOfRecords
    num_el = root.find(".//numberOfRecords")
    if num_el is not None and num_el.text:
        try:
            if int(num_el.text) == 0:
                return []
        except ValueError:
            pass

    results: list[dict[str, Any]] = []

    # Find all record elements (namespace-stripped)
    records = root.findall(".//record")

    for record in records:
        # Each record contains a DataView with type "application/x-clarin-fcs-lex+xml"
        # which holds an Entry element with Field/Value children
        parsed = _parse_fcs_lex_record(record, query_stem)
        if parsed:
            results.append(parsed)

    return results


def _parse_fcs_lex_record(record_el: ET.Element, query_stem: str) -> dict[str, Any] | None:
    """Parse a single FCS-lex record from the TLA SRU response.

    Structure (after namespace stripping):
      record > recordData > Resource > ResourceFragment > DataView > Entry
      Entry contains Field elements with @type attribute, each holding Value elements.

    Field types:
      entryId   — TLA lemma ID
      lemma     — transliteration (preferred) + hieroglyphs
      translation — glosses in deu/eng/fra/ara
      pos       — part of speech (TLA-native + UPOS)
      ref       — URL to TLA lemma page
      baseform  — root form
      related   — related lemmas
      gender    — grammatical gender
    """
    lemma_id = ""
    transliteration = ""
    hieroglyphs = ""
    pos = ""
    translations: list[str] = []
    tla_url = ""

    # Find all Entry elements (there may be one per DataView)
    for entry_el in record_el.iter():
        tag = entry_el.tag.split("}")[-1] if "}" in entry_el.tag else entry_el.tag
        if tag != "Entry":
            continue

        # Iterate over Field children
        for field in entry_el:
            field_tag = field.tag.split("}")[-1] if "}" in field.tag else field.tag
            if field_tag != "Field":
                continue

            field_type = field.get("type", "")

            for value in field:
                val_tag = value.tag.split("}")[-1] if "}" in value.tag else value.tag
                if val_tag != "Value":
                    continue

                text = (value.text or "").strip()
                lang = value.get("lang", "") or value.get("{http://www.w3.org/XML/1998/namespace}lang", "")

                if field_type == "entryId":
                    lemma_id = text

                elif field_type == "lemma":
                    if "Egyp" in lang:
                        # Hieroglyphic rendering
                        if text:
                            hieroglyphs = text
                    elif value.get("preferred") == "true" or "Latn" in lang:
                        # Latin-script transliteration (preferred)
                        if text:
                            transliteration = text
                    elif not transliteration and text:
                        transliteration = text

                elif field_type == "translation":
                    if text:
                        # Prefer English, but collect all
                        if "eng" in lang:
                            translations.insert(0, text)
                        else:
                            translations.append(text)

                elif field_type == "pos":
                    # Prefer UPOS value (e.g. PROPN, NOUN)
                    vocab_ref = value.get("vocabValueRef", "")
                    if text and ("universaldependencies" in vocab_ref or not pos):
                        pos = text

                elif field_type == "ref" and text and "thesaurus-linguae-aegyptiae.de" in text:
                    tla_url = text

        break  # Only process first Entry per record

    if not transliteration:
        return None

    # Deduplicate translations preserving order
    seen: set[str] = set()
    unique_translations: list[str] = []
    for t in translations:
        if t not in seen:
            seen.add(t)
            unique_translations.append(t)

    result: dict[str, Any] = {
        "tla_lemma_id": lemma_id,
        "transliteration": transliteration,
        "pos": pos,
        "translations": unique_translations,
        "query_stem": query_stem,
    }
    if hieroglyphs:
        result["hieroglyphs"] = hieroglyphs
    if tla_url:
        result["tla_url"] = tla_url

    return result


# ---------------------------------------------------------------------------
# HF dataset interaction (attestation counts)
# ---------------------------------------------------------------------------

def fetch_hf_corpus(*, use_cache: bool = False) -> Path | None:
    """Download the HF Late Egyptian corpus JSONL. Returns path or None."""
    if HF_CACHE_PATH.exists():
        print(f"  [cache] HF corpus: using cached {HF_CACHE_PATH.name}")
        return HF_CACHE_PATH

    if use_cache:
        print("  [skip]  HF corpus: no cache, --use-cache mode")
        return None

    # HF datasets API — download the first split
    hf_repo = "thesaurus-linguae-aegyptiae/tla-late_egyptian-v19-premium"
    # Try the HF datasets REST API
    api_url = (
        "https://datasets-server.huggingface.co/rows"
        f"?dataset={urllib.parse.quote(hf_repo)}&config=default&split=train&offset=0&length=100"
    )

    print(f"  [fetch] HF corpus: {api_url}")
    try:
        body, _ = http_get(api_url, timeout=60)
        data = json.loads(body)

        # Write rows as JSONL
        rows = data.get("rows", [])
        if not rows:
            print("  [warn]  HF corpus: no rows returned")
            return None

        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with open(HF_CACHE_PATH, "w", encoding="utf-8") as f:
            for row in rows:
                row_data = row.get("row", row)
                f.write(json.dumps(row_data, ensure_ascii=False) + "\n")

        print(f"  [cache] saved {HF_CACHE_PATH.name} ({len(rows)} rows)")
        return HF_CACHE_PATH

    except Exception as e:  # noqa: BLE001 — attestation counts are optional; the import runs without them
        print(f"  [error] HF corpus download failed: {e}")
        return None


def count_lemma_attestations(hf_path: Path | None) -> dict[str, int]:
    """Count lemma occurrences in the HF corpus. Returns {transliteration: count}."""
    counts: dict[str, int] = {}
    if not hf_path or not hf_path.exists():
        return counts

    print("  [parse] counting lemma attestations from HF corpus...")
    try:
        with open(hf_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue

                # Filter to Bronze Age window (dateNotBefore >= -1550)
                date_nb = row.get("dateNotBefore")
                if date_nb is not None:
                    try:
                        if int(date_nb) < -1550:
                            continue
                    except (ValueError, TypeError):
                        pass

                # Parse lemmatization field: pipe-separated "ID|transliteration" pairs
                lemmatization = row.get("lemmatization", "")
                if not lemmatization:
                    continue

                for token in lemmatization.split():
                    parts = token.split("|")
                    if len(parts) >= 2:
                        translit = parts[1].strip()
                        if translit:
                            counts[translit] = counts.get(translit, 0) + 1

    except Exception as e:  # noqa: BLE001 — attestation counts are optional; the import runs without them
        print(f"  [error] HF attestation counting failed: {e}")

    print(f"  [done]  {len(counts)} unique lemmas counted")
    return counts


# ---------------------------------------------------------------------------
# Entry generation
# ---------------------------------------------------------------------------

def normalize_transliteration(raw: str) -> str:
    """Normalize a TLA transliteration to our canonical form.

    Lowercase, strip hyphens/spaces, preserve Unicode Egyptological chars.
    """
    result = raw.lower().strip()
    result = re.sub(r"[\s\-]+", "", result)
    return result


def generate_match_keys(transliteration: str, normalized: str) -> list[str]:
    """Generate match_keys from transliteration variants."""
    keys: set[str] = set()
    keys.add(normalized)
    keys.add(transliteration.lower().strip())

    # Add hyphen-stripped version
    no_hyphen = re.sub(r"[\-]", "", transliteration.lower().strip())
    if no_hyphen != normalized:
        keys.add(no_hyphen)

    # Add MdC-style variant (reverse some Unicode → ASCII)
    mdc_reverse = normalized
    for mdc, uni in [("A", "ꜣ"), ("a", "ꜥ"), ("H", "ḥ"), ("x", "ḫ"),
                     ("S", "š"), ("T", "ṯ"), ("D", "ḏ")]:
        mdc_reverse = mdc_reverse.replace(uni, mdc)
    if mdc_reverse != normalized:
        keys.add(mdc_reverse)

    return sorted(keys)


def _build_source_ref(lemma_id: str, tla_url: str) -> dict[str, str]:
    """Build a source_refs entry for TLA."""
    ref: dict[str, str] = {"work": "TLA"}
    if lemma_id:
        ref["ref"] = f"lemma {lemma_id}"
    else:
        ref["ref"] = "SRU query"
    if tla_url:
        ref["url"] = tla_url
    return ref


def build_entry(
    candidate: dict[str, Any],
    attestation_counts: dict[str, int],
) -> dict[str, Any] | None:
    """Build a lexicon entry from a parsed SRU candidate. Returns None if not contact-relevant."""
    translit = candidate["transliteration"]
    normalized = normalize_transliteration(translit)
    translations = candidate.get("translations", [])
    gloss_text = "; ".join(translations) if translations else ""
    query_stem = candidate.get("query_stem", "")

    # Classify into contact-relevant domains
    pos = candidate.get("pos", "")
    domains = classify_domains(gloss_text + " " + translit, query_stem, pos=pos)
    if not domains:
        return None  # Not contact-relevant

    # Build meaning string
    meaning = gloss_text if gloss_text else f"[{translit}]"

    # Generate ID
    lemma_id = candidate.get("tla_lemma_id", "")
    if lemma_id:
        entry_id = f"egy:tla:{lemma_id}"
    else:
        # Fallback: use normalized form
        safe_norm = re.sub(r"[^a-z0-9]", "_", normalized)
        entry_id = f"egy:tla:{safe_norm}"

    entry: dict[str, Any] = {
        "id": entry_id,
        "language": "Egyptian",
        "transliteration_unicode": translit,
        "normalized": normalized,
        "match_keys": generate_match_keys(translit, normalized),
        "meaning": meaning,
        "semantic_domain": domains,
        "attestation_periods": ["New Kingdom"],
        "source_refs": [_build_source_ref(lemma_id, candidate.get("tla_url", ""))],
        "review_status": "machine_imported",
    }

    # Optional TLA-specific fields
    if lemma_id:
        entry["tla_lemma_id"] = lemma_id
    if candidate.get("hieroglyphs"):
        entry["hieroglyphs"] = candidate["hieroglyphs"]
    if candidate.get("tla_url"):
        entry["tla_url"] = candidate["tla_url"]

    # Add attestation count from HF corpus if available
    attest_count = attestation_counts.get(translit, 0) or attestation_counts.get(normalized, 0)
    if attest_count > 0:
        entry["tla_attestation_count_sample"] = attest_count

    # POS if available
    if candidate.get("pos"):
        entry["pos"] = candidate["pos"]

    return entry


# ---------------------------------------------------------------------------
# Curated fallback entries
# ---------------------------------------------------------------------------
CURATED_FALLBACK_PATH = CONTACT_DATA / "review" / "tla_curated_fallback.jsonl"


def _load_curated_fallback() -> list[dict[str, Any]]:
    """Load curated fallback entries from JSONL data file."""
    entries: list[dict[str, Any]] = []
    if not CURATED_FALLBACK_PATH.exists():
        return entries
    with open(CURATED_FALLBACK_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def load_existing_ids(lexicon_path: Path) -> set[str]:
    """Load existing entry IDs from the lexicon to avoid duplicates."""
    ids: set[str] = set()
    if not lexicon_path.exists():
        return ids
    with open(lexicon_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                ids.add(entry.get("id", ""))
            except json.JSONDecodeError:
                pass
    return ids


def load_existing_normalized(lexicon_path: Path) -> set[str]:
    """Load existing normalized forms to avoid semantic duplicates."""
    norms: set[str] = set()
    if not lexicon_path.exists():
        return norms
    with open(lexicon_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                norms.add(entry.get("normalized", ""))
            except json.JSONDecodeError:
                pass
    return norms


def main() -> int:
    """Exit 2 with the file's name when a data file is not in the checkout."""
    try:
        return _run()
    except NotInCheckout as e:
        print(f"stopped: {e}", file=sys.stderr)
        return 2


def _run() -> int:
    parser = argparse.ArgumentParser(
        description="Ingest TLA data into Egyptian contact lexicon"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would be imported without writing"
    )
    parser.add_argument(
        "--use-cache", action="store_true",
        help="Skip API calls, use only cached data"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("TLA Ingestion Pipeline")
    print("=" * 60)
    print(f"  Lexicon:  {LEXICON_PATH}")
    print(f"  Cache:    {CACHE_DIR}")
    print(f"  Dry run:  {args.dry_run}")
    print(f"  Cache-only: {args.use_cache}")
    print()

    # Load existing data to avoid duplicates
    require(LEXICON_PATH, LEXICON_PATH.name)
    existing_ids = load_existing_ids(LEXICON_PATH)
    existing_norms = load_existing_normalized(LEXICON_PATH)
    print(f"Existing entries: {len(existing_ids)} IDs, {len(existing_norms)} normalized forms")
    print()

    # Ensure the cache directory exists
    QUERY_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # --- Phase 1: SRU API queries ---
    print("Phase 1: SRU API queries")
    print("-" * 40)

    all_candidates: list[dict[str, Any]] = []

    for stem, query in SRU_QUERIES:
        xml_text = fetch_sru_xml(stem, query, use_cache=args.use_cache)
        if xml_text:
            parsed = parse_sru_response(xml_text, stem)
            print(f"  [result] {stem}: {len(parsed)} entries parsed")
            all_candidates.extend(parsed)
        else:
            print(f"  [none]   {stem}: no data")

    print(f"\nTotal SRU candidates: {len(all_candidates)}")

    # If SRU returned very few results, supplement with curated fallback
    if len(all_candidates) < 10:
        curated = _load_curated_fallback()
        print(f"\n  [fallback] SRU returned <10 results; adding {len(curated)} curated entries")
        sru_translits = {c["transliteration"] for c in all_candidates}
        for entry in curated:
            if entry["transliteration"] not in sru_translits:
                all_candidates.append(entry)
        print(f"  [total]    {len(all_candidates)} candidates after fallback")

    print()

    # --- Phase 2: HF attestation counts (optional) ---
    print("Phase 2: HF attestation counts")
    print("-" * 40)

    hf_path = fetch_hf_corpus(use_cache=args.use_cache)
    attestation_counts = count_lemma_attestations(hf_path)
    print()

    # --- Phase 3: Build and filter entries ---
    print("Phase 3: Build and filter entries")
    print("-" * 40)

    new_entries: list[dict[str, Any]] = []
    skipped_existing = 0
    skipped_irrelevant = 0
    skipped_duplicate_norm = 0
    skipped_cap = 0

    seen_ids_this_run: set[str] = set()

    # Cap per-query contribution to avoid flooding from broad queries.
    # Lemma/baseform queries: 10 max. Translation queries: 5 max. PROPN: 15 max.
    query_caps: dict[str, int] = {
        "kftj": 10, "aamu": 10, "hau": 10, "mnw": 10, "qdsh": 10,
        "nb_baseform": 8, "hr_baseform": 5, "imn_baseform": 8,
        "propn": 15,
        "trans_ship": 5, "trans_sea": 5, "trans_copper": 5, "trans_crete": 5,
    }
    query_counts: dict[str, int] = {}

    for candidate in all_candidates:
        entry = build_entry(candidate, attestation_counts)

        if entry is None:
            skipped_irrelevant += 1
            continue

        entry_id = entry["id"]
        entry_norm = entry["normalized"]

        # Enforce per-query cap BEFORE dedup checks. This ensures idempotency:
        # the same candidates are counted against caps regardless of whether
        # they were already imported in a prior run.
        q_stem = candidate.get("query_stem", "")
        cap = query_caps.get(q_stem, 10)
        current_count = query_counts.get(q_stem, 0)
        if current_count >= cap:
            skipped_cap += 1
            continue
        query_counts[q_stem] = current_count + 1

        # Skip if ID already exists in lexicon
        if entry_id in existing_ids:
            skipped_existing += 1
            continue

        # Skip if normalized form already exists (semantic duplicate)
        if entry_norm in existing_norms:
            skipped_existing += 1
            continue

        # Skip if we already generated this ID in this run
        if entry_id in seen_ids_this_run:
            skipped_duplicate_norm += 1
            continue

        errors = validate_entry(entry, "Egyptian")
        if errors:
            print(f"  [invalid] {entry_id}: {errors}")
            continue

        new_entries.append(entry)
        seen_ids_this_run.add(entry_id)
        existing_norms.add(entry_norm)  # prevent duplicates within this batch

    print(f"  New entries to import: {len(new_entries)}")
    print(f"  Skipped (existing):    {skipped_existing}")
    print(f"  Skipped (irrelevant):  {skipped_irrelevant}")
    print(f"  Skipped (duplicate):   {skipped_duplicate_norm}")
    print(f"  Skipped (cap):         {skipped_cap}")
    print()

    # --- Phase 4: Output ---
    if args.dry_run:
        print("Phase 4: DRY RUN — entries that would be imported:")
        print("-" * 40)
        for entry in new_entries:
            print(f"  {entry['id']}: {entry['transliteration_unicode']} — {entry['meaning']}")
            print(f"    domains: {entry['semantic_domain']}")
        print(f"\nTotal: {len(new_entries)} entries would be appended to {LEXICON_PATH.name}")
    else:
        print("Phase 4: Appending to lexicon")
        print("-" * 40)

        if not new_entries:
            print("  No new entries to write.")
        else:
            stamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
            BACKUPS.mkdir(parents=True, exist_ok=True)
            backup = BACKUPS / f"{LEXICON_PATH.stem}-{stamp}{LEXICON_PATH.suffix}"
            shutil.copy2(LEXICON_PATH, backup)
            print(f"  Backed up {LEXICON_PATH.name} → {backup}")

            with open(LEXICON_PATH, "a", encoding="utf-8") as f:
                for entry in new_entries:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            print(f"  Appended {len(new_entries)} entries to {LEXICON_PATH.name}")

            # Final count
            final_count = len(existing_ids) + len(new_entries)
            print(f"  Total lexicon entries: {final_count}")

    print()
    print("=" * 60)
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
