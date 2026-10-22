"""Contact language lexicon loader, validator, normalizer, and matcher.

Handles Egyptian, Anatolian, Hurrian, Amarna Canaanite, and Ugaritic JSONL databases
stored in data/contact/. Each JSONL file is a curated source-of-truth; indexes are
generated lookup caches keyed by normalized match_keys.
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any, Literal, TypedDict

ContactLanguage = Literal["Egyptian", "Anatolian", "Canaanite", "Hurrian", "Ugaritic", "Amorite", "Ancient Greek", "Hebrew", "Aramaic", "Geʿez", "South Arabian"]

VALID_REVIEW_STATUSES = frozenset({
    "seed_pending_source_page",
    "machine_imported",
    "machine_generated",
    "human_reviewed",
    "hand_curated",
    "accepted",
    "rejected",
})

VALID_SEMANTIC_DOMAINS = frozenset({
    "divine_name", "toponym", "ethnonym", "material_culture",
    "maritime", "cult", "loan", "aegean_interface", "canaanite_loan",
    "title", "general", "personal_name", "royal_name", "name_element",
    "metrology", "month_name",
    # Lexical domains added for Hurrian vocabulary expansion
    "kinship", "verbal_root", "nominal_root", "grammatical_morpheme",
    "numeral", "adjective", "body", "nature", "agriculture",
    # Lexical domains added for the Melchert (CLL) / Laroche (GLH) merges
    "military", "governance", "social", "water", "architecture",
    "commodity", "administrative", "temporal",
})

try:
    from ..paths import CONTACT_DATA
except ImportError:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from tools.paths import CONTACT_DATA

_CONTACT_DIR = CONTACT_DATA


# ---------------------------------------------------------------------------
# Egyptian normalization: Manuel de Codage (ASCII) → Unicode transliteration
# ---------------------------------------------------------------------------

_MDC_UNAMBIGUOUS: dict[str, str] = {
    "A": "ꜣ",   # alef
    "H": "ḥ",   # het
    "X": "ẖ",   # soft kha (lowercase in output)
    "S": "š",   # shin
    "T": "ṯ",   # teth
    "D": "ḏ",   # djed
}

_MDC_AMBIGUOUS: dict[str, str] = {
    "a": "ꜥ",   # ain — also a normal Latin vowel
    "x": "ḫ",   # kha — also a normal Latin consonant
}

MDC_TO_UNICODE: dict[str, str] = {**_MDC_UNAMBIGUOUS, **_MDC_AMBIGUOUS}

# Loose alias: map Egyptological phonemes to Semitic equivalents for
# cross-language matching. Strict canonical preserves ꜣ/ꜥ.
EGYPTIAN_TO_SEMITIC: dict[str, str] = {
    "ꜣ": "ʾ",
    "ꜥ": "ʿ",
}


def normalize_egyptian(form: str, *, loose: bool = False) -> str:
    """Normalize an Egyptian transliteration.

    Strict mode (default): MdC→Unicode, lowercase, strip whitespace/hyphens.
    Loose mode: additionally maps ꜣ→ʾ and ꜥ→ʿ for Semitic comparison.

    Ambiguous MdC characters (a, x) are only converted when unambiguous MdC
    uppercase characters (A, H, S, T, D, X) are present, preventing corruption
    of Latinized forms like "kunusha".
    """
    result = form
    is_mdc = any(c in _MDC_UNAMBIGUOUS for c in form)
    for mdc, uni in _MDC_UNAMBIGUOUS.items():
        result = result.replace(mdc, uni)
    if is_mdc:
        for mdc, uni in _MDC_AMBIGUOUS.items():
            result = result.replace(mdc, uni)
    result = result.lower().strip()
    result = re.sub(r"[\s\-]+", "", result)
    if loose:
        for egy, sem in EGYPTIAN_TO_SEMITIC.items():
            result = result.replace(egy, sem)
    return result


def normalize_anatolian(form: str) -> str:
    """Normalize an Anatolian form: lowercase, strip diacritics, collapse whitespace."""
    result = form.lower().strip()
    nfkd = unicodedata.normalize("NFKD", result)
    stripped = "".join(c for c in nfkd if not unicodedata.category(c).startswith("M"))
    return re.sub(r"[\s\-]+", "", stripped)


def normalize_hurrian(form: str) -> str:
    """Normalize Hurrian forms and names for contact matching."""
    result = form.lower().strip()
    result = result.replace("š", "sh").replace("ḫ", "h").replace("Ḫ", "h")
    nfkd = unicodedata.normalize("NFKD", result)
    stripped = "".join(c for c in nfkd if not unicodedata.category(c).startswith("M"))
    stripped = re.sub(r"[ꜣꜥʔʾʿ']", "", stripped)
    return re.sub(r"[\s\-_.=]+", "", stripped)


_AMORITE_CONSONANT_MAP: dict[str, str] = {
    "j": "y",           # Gelb's j = /y/
    "ʕ": "ʿ", "ˤ": "ʿ", "ᶜ": "ʿ",
    "ʔ": "ʾ",
    # Gelb's computer encoding prints gutturals as superscript digits; the
    # OCR renders them variously: ³ = ʔ; ¹/⁴/⁹ = ʕ (verified against ʕamm-
    # and ʔab- element rows in §6)
    "³": "ʾ", "¹": "ʿ", "⁴": "ʿ", "⁹": "ʿ",
    # typographic apostrophes standing for ʿayin (Golinets 'Ammu-yepu')
    "'": "ʿ", "‘": "ʿ", "’": "ʿ",
    "ḓ": "ḏ", "ż": "ẓ", "ç": "ṣ", "ş": "ṣ",
}


def normalize_amorite(form: str) -> str:
    """Normalize a Gelb AS 21 Amorite form for contact matching.

    Gelb's transliteration as OCR renders it: j for /y/, ʕ/ʔ gutturals
    (ʔ sometimes as superscript 3), macron vowels often surfacing as
    tilde vowels (ũ ĩ ẽ ã). Folds to lowercase canonical, strips morpheme
    boundaries (+ - * =) and uncertainty marks.

    DESIGN CONSTRAINTS (differ from normalize_ugaritic — deliberate):
    - NFKD stripping collapses š/ṣ/ṭ/ẓ into their plain letters, which the
      syllabary merges; this lexicon is therefore NOT suitable for precise
      Amorite-internal lookups where ŠMR vs SMR must stay distinct — use
      form_original for that. ḏ is kept: the speculative value of *305 is ḏ, and folding it to d
      puts every ZA/ZU word a full edit away (d~z is unpriced, ḏ~z 0.2).
    - All typographic apostrophes map to ʿayin, which is what ' means in
      Gelb (via ᶜ) and Golinets. Any future source in which ' means alef
      must be re-marked to ʾ at ingest, or its normalizations will carry
      the wrong guttural.
    """
    result = form.strip().strip("/").lower()
    result = re.sub(r"\s*\(.*?\)\s*", "", result)
    result = re.sub(r"\^\{(\d)\}", r"\1", result)  # markdown superscript → digit
    result = result.replace("²", "ʾ")  # Gelb's non-initial ʔ OCRs as ²
    for src, tgt in _AMORITE_CONSONANT_MAP.items():
        result = result.replace(src, tgt)
    # tilde/macron vowels → plain (NFKD strips combining marks below); ḏ survives
    nfkd = unicodedata.normalize("NFKD", result.replace("ḏ", ""))
    result = "".join(c for c in nfkd if not unicodedata.category(c).startswith("M")).replace("", "ḏ")
    result = re.sub(r"[?!]", "", result)
    result = re.sub(r"\d+", "", result)  # cuneiform homophone indices — not phonemes
    return re.sub(r"[\s\-_.+*=/]+", "", result)


def normalize_canaanite(form: str) -> str:
    """Normalize a Canaanite (Amarna) form: lowercase, strip subscripts/hyphens."""
    result = form.lower().strip()
    result = re.sub(r"[₂₃₄₅]", "", result)
    result = re.sub(r"[\s\-]+", "", result)
    return result


_GREEK_TRANSLIT: dict[str, str] = {
    "α": "a", "β": "b", "γ": "g", "δ": "d", "ε": "e", "ζ": "z",
    "η": "e", "θ": "th", "ι": "i", "κ": "k", "λ": "l", "μ": "m",
    "ν": "n", "ξ": "x", "ο": "o", "π": "p", "ρ": "r", "σ": "s",
    "ς": "s", "τ": "t", "υ": "u", "φ": "ph", "χ": "kh", "ψ": "ps",
    "ω": "o", "ϝ": "w", "ϛ": "st", "ϙ": "q",
}


def normalize_greek(form: str) -> str:
    """Normalize a Greek form for contact matching.

    Accepts polytonic Greek script or Latin transliteration. Strips
    diacritics/breathings, folds long vowels (η→e, ω→o), and maps letters
    with the same table that built the lexicon's Greek keys — query-side
    and ingest-side keys must stay in lockstep.
    """
    decomposed = unicodedata.normalize("NFD", form.lower().strip())
    out = []
    for ch in decomposed:
        if unicodedata.combining(ch):
            continue
        out.append(_GREEK_TRANSLIT.get(ch, ch if ch.isalnum() else ""))
    return "".join(out)


_UGARITIC_CONSONANT_MAP: dict[str, str] = {
    "ṯ": "θ", "ḏ": "ḏ", "ṭ": "ṭ", "ṣ": "ṣ",
    "ḥ": "ḥ", "ḫ": "ḫ", "ġ": "ġ",
    "ˤ": "ʿ", "ʕ": "ʿ", "ʔ": "ʾ",
    "š": "š", "ś": "ś",
}


def normalize_ugaritic(form: str) -> str:
    """Normalize a Ugaritic form: map DULAT/CUC consonants to PS canonical, strip slashes/hyphens."""
    result = form.lower().strip().strip("/").strip("*")
    result = re.sub(r"\s*\(.*?\)\s*", "", result)
    for src, tgt in _UGARITIC_CONSONANT_MAP.items():
        result = result.replace(src, tgt)
    result = re.sub(r"[\s\-_.=/]+", "", result)
    return result


def normalize_hebrew(form: str) -> str:
    """Normalize a Hebrew form for contact matching.

    Strips niqqud and cantillation, folds to lowercase Latin transliteration
    when already romanized, collapses whitespace/hyphens.
    """
    result = form.strip()
    nfkd = unicodedata.normalize("NFD", result)
    result = "".join(
        c for c in nfkd
        if unicodedata.category(c) not in ("Mn",)
        or "֑" <= c <= "ׇ"  # keep Hebrew letters, strip combining marks
    )
    result = re.sub(r"[֑-ׇ]", "", result)
    result = result.lower()
    result = re.sub(r"[\s\-_.]+", "", result)
    return result


def normalize_aramaic(form: str) -> str:
    """Normalize an Aramaic form for contact matching.

    Handles both square-script and romanized input. Strips niqqud,
    collapses whitespace/hyphens, folds to lowercase.
    """
    result = form.strip()
    nfkd = unicodedata.normalize("NFD", result)
    result = "".join(
        c for c in nfkd
        if unicodedata.category(c) not in ("Mn",)
        or "֑" <= c <= "ׇ"
    )
    result = re.sub(r"[֑-ׇ]", "", result)
    result = result.lower()
    result = re.sub(r"[\s\-_.]+", "", result)
    return result


_GEEZ_CONSONANT_TABLE: dict[str, str] = {
    "ḥ": "ḥ", "ḫ": "ḫ", "ṣ": "ṣ", "ṭ": "ṭ", "ḍ": "ḍ",
    "š": "š", "ś": "ś", "ẓ": "ẓ",
    "ʿ": "ʿ", "ʾ": "ʾ", "ʔ": "ʾ", "ˤ": "ʿ", "ʕ": "ʿ",
}


def normalize_geez(form: str) -> str:
    """Normalize a Geʿez form for contact matching.

    Accepts romanized transliteration (CDG/Dillmann conventions).
    Preserves emphatics and gutturals, strips morpheme boundaries.
    """
    result = form.lower().strip()
    for src, tgt in _GEEZ_CONSONANT_TABLE.items():
        result = result.replace(src, tgt)
    result = re.sub(r"[\s\-_.=]+", "", result)
    return result


_SOUTH_ARABIAN_SIBILANT_INDEX: dict[str, str] = {
    "¹": "1", "₁": "1",
    "²": "2", "₂": "2",
    "³": "3", "₃": "3",
}


def normalize_south_arabian(form: str) -> str:
    """Normalize an Ancient South Arabian (DASI) form for contact matching.

    DASI transliteration marks the three ASA sibilant series with indices
    (s¹ s² s³, sometimes subscript s₁ s₂ s₃) that reflect distinct
    Proto-Semitic phonemes (s¹ = PS *š, s² = PS *ś, s³ = PS *s). The
    indices are preserved as ASCII digits (s1/s2/s3) so the three series
    never collapse during cross-linguistic matching. Strips lacuna
    brackets ([...], [.]), editorial dots, and word dividers; NFC-folds
    and lowercases.
    """
    result = unicodedata.normalize("NFC", form).lower().strip()
    result = re.sub(r"\[[^\]]*\]", "", result)  # lacunae: [...], [.], [. .]
    result = result.replace("[", "").replace("]", "")
    for src_ch, tgt in _SOUTH_ARABIAN_SIBILANT_INDEX.items():
        result = result.replace(src_ch, tgt)
    return re.sub(r"[\s\-_.=/]+", "", result)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

_REQUIRED_COMMON = {"id", "language", "normalized", "match_keys", "meaning",
                    "semantic_domain", "source_refs", "review_status"}

_REQUIRED_EGYPTIAN = _REQUIRED_COMMON | {"transliteration_unicode"}
_REQUIRED_ANATOLIAN = _REQUIRED_COMMON | {"form_original", "language_family"}
_REQUIRED_CANAANITE = _REQUIRED_COMMON | {"form", "pos", "source_corpus"}
_REQUIRED_HURRIAN = _REQUIRED_COMMON | {"form_original", "language_family"}
_REQUIRED_UGARITIC = _REQUIRED_COMMON | {"form_original", "language_family"}
_REQUIRED_AMORITE = _REQUIRED_COMMON | {"form_original", "language_family"}
_REQUIRED_GREEK = _REQUIRED_COMMON | {"form_original", "language_family"}
_REQUIRED_HEBREW = _REQUIRED_COMMON | {"form_original", "language_family"}
_REQUIRED_ARAMAIC = _REQUIRED_COMMON | {"form_original", "language_family"}
_REQUIRED_GEEZ = _REQUIRED_COMMON | {"form_original", "language_family"}
_REQUIRED_SOUTH_ARABIAN = _REQUIRED_COMMON | {"form_original", "language_family"}


class ValidationError(Exception):
    pass


def validate_entry(entry: dict[str, Any], language: ContactLanguage) -> list[str]:
    """Validate a single JSONL entry. Returns list of error strings (empty = valid)."""
    errors: list[str] = []
    entry_id = entry.get("id", "<no id>")

    if language == "Egyptian":
        required = _REQUIRED_EGYPTIAN
    elif language == "Anatolian":
        required = _REQUIRED_ANATOLIAN
    elif language == "Hurrian":
        required = _REQUIRED_HURRIAN
    elif language == "Ugaritic":
        required = _REQUIRED_UGARITIC
    elif language == "Amorite":
        required = _REQUIRED_AMORITE
    elif language == "Ancient Greek":
        required = _REQUIRED_GREEK
    elif language == "Hebrew":
        required = _REQUIRED_HEBREW
    elif language == "Aramaic":
        required = _REQUIRED_ARAMAIC
    elif language == "Geʿez":
        required = _REQUIRED_GEEZ
    elif language == "South Arabian":
        required = _REQUIRED_SOUTH_ARABIAN
    else:
        required = _REQUIRED_CANAANITE

    for field in required:
        if field not in entry:
            errors.append(f"{entry_id}: missing required field '{field}'")

    status = entry.get("review_status")
    if status and status not in VALID_REVIEW_STATUSES:
        errors.append(f"{entry_id}: invalid review_status '{status}'")

    domains = entry.get("semantic_domain", [])
    if not isinstance(domains, list):
        errors.append(f"{entry_id}: semantic_domain must be a list")
    else:
        for d in domains:
            if d not in VALID_SEMANTIC_DOMAINS:
                errors.append(f"{entry_id}: unknown semantic_domain '{d}'")

    source_refs = entry.get("source_refs", [])
    if not isinstance(source_refs, list):
        errors.append(f"{entry_id}: source_refs must be a list")

    match_keys = entry.get("match_keys", [])
    if not isinstance(match_keys, list) or len(match_keys) == 0:
        errors.append(f"{entry_id}: match_keys must be a non-empty list")

    return errors


def validate_lexicon(entries: list[dict[str, Any]], language: ContactLanguage) -> list[str]:
    """Validate a full lexicon. Returns all errors; checks for duplicate IDs."""
    errors: list[str] = []
    seen_ids: set[str] = set()

    for entry in entries:
        entry_errors = validate_entry(entry, language)
        errors.extend(entry_errors)

        eid = entry.get("id")
        if eid:
            if eid in seen_ids:
                errors.append(f"{eid}: duplicate ID")
            seen_ids.add(eid)

    return errors


# ---------------------------------------------------------------------------
# Loading and indexing
# ---------------------------------------------------------------------------

def load_lexicon(path: Path) -> list[dict[str, Any]]:
    """Load a JSONL lexicon file. Returns list of parsed entries."""
    entries: list[dict[str, Any]] = []
    if not path.exists():
        return entries
    with open(path) as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise ValidationError(f"{path.name}:{line_num}: invalid JSON: {e}")
    return entries


def build_contact_index(entries: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Build a lookup index keyed by match_keys → list of matching entries."""
    index: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        for key in entry.get("match_keys", []):
            key_lower = key.lower()
            if key_lower not in index:
                index[key_lower] = []
            index[key_lower].append(entry)
    return index


class ContactMatch(TypedDict):
    matched: bool
    entry_id: str
    meaning: str
    language: str
    confidence: str
    method: str


NO_MATCH: ContactMatch = {
    "matched": False,
    "entry_id": "",
    "meaning": "",
    "language": "",
    "confidence": "",
    "method": "",
}


def match_contact_term(
    normalized_form: str,
    language: ContactLanguage,
    indexes: dict[str, dict[str, list[dict[str, Any]]]],
) -> ContactMatch:
    """Look up a contact term against the appropriate lexicon index.

    Tries exact match on normalized form, then loose normalization for Egyptian.
    """
    lang_key_map = {"Ancient Greek": "greek", "Geʿez": "geez", "South Arabian": "south_arabian"}
    lang_key = lang_key_map.get(language, language.lower())
    index = indexes.get(lang_key, {})
    if not index:
        return NO_MATCH

    if language == "Egyptian":
        form_lower = normalize_egyptian(normalized_form)
    elif language == "Anatolian":
        form_lower = normalize_anatolian(normalized_form)
    elif language == "Hurrian":
        form_lower = normalize_hurrian(normalized_form)
    elif language == "Canaanite":
        form_lower = normalize_canaanite(normalized_form)
    elif language == "Ugaritic":
        form_lower = normalize_ugaritic(normalized_form)
    elif language == "Ancient Greek":
        form_lower = normalize_greek(normalized_form)
    elif language == "Hebrew":
        form_lower = normalize_hebrew(normalized_form)
    elif language == "Aramaic":
        form_lower = normalize_aramaic(normalized_form)
    elif language == "Geʿez":
        form_lower = normalize_geez(normalized_form)
    elif language == "South Arabian":
        form_lower = normalize_south_arabian(normalized_form)
    else:
        form_lower = normalized_form.lower()

    hits = index.get(form_lower, [])
    if not hits and language == "Egyptian":
        loose = normalize_egyptian(normalized_form, loose=True)
        hits = index.get(loose, [])

    if hits:
        best = hits[0]
        return ContactMatch(
            matched=True,
            entry_id=best["id"],
            meaning=best["meaning"],
            language=best["language"],
            confidence=best.get("review_status", "unknown"),
            method="contact_lexicon",
        )

    if not hits and language in ("Egyptian", "Anatolian", "Hurrian"):
        root_idx = _build_root_index(index)
        try:
            from .morphology_dispatch import fuzzy_candidates
        except ImportError:
            from morphology_dispatch import fuzzy_candidates

        candidates = fuzzy_candidates(form_lower, language, root_idx)
        if candidates:
            best_candidate = candidates[0]
            entry_hits = index.get(best_candidate.reduced_skeleton, [])
            if entry_hits:
                best = entry_hits[0]
                return ContactMatch(
                    matched=True,
                    entry_id=best["id"],
                    meaning=best["meaning"],
                    language=best["language"],
                    confidence=best_candidate.confidence,
                    method=f"fuzzy_{best_candidate.method}",
                )

    return NO_MATCH


def _build_root_index(
    contact_index: dict[str, list[dict[str, Any]]],
) -> dict[str, list[str]]:
    """Convert a contact index into the shape morphology engines expect.

    Maps each match_key to a list of entry IDs.
    """
    root_idx: dict[str, list[str]] = {}
    for key, entries in contact_index.items():
        root_idx[key] = [e["id"] for e in entries]
    return root_idx


Normalizer = Any  # Callable[[str], str] — avoid typing import


def enrich_match_keys(
    entries: list[dict[str, Any]],
    normalizer: Normalizer,
    source_field: str = "normalized",
    extra_normalizers: list[Normalizer] | None = None,
) -> int:
    """Add normalized forms to match_keys for all entries.

    Applies `normalizer` (and any `extra_normalizers`) to `source_field` and
    every existing match_key. Returns count of keys added.
    """
    all_normalizers = [normalizer] + (extra_normalizers or [])
    added = 0
    for entry in entries:
        existing = {k.lower() for k in entry.get("match_keys", [])}
        new_keys: list[str] = []

        source = entry.get(source_field, "")
        for norm_fn in all_normalizers:
            if source:
                norm = norm_fn(source)
                if norm and norm not in existing:
                    new_keys.append(norm)
                    existing.add(norm)

            for key in list(entry.get("match_keys", [])):
                norm = norm_fn(key)
                if norm and norm not in existing:
                    new_keys.append(norm)
                    existing.add(norm)

        if new_keys:
            entry["match_keys"].extend(new_keys)
            added += len(new_keys)

    return added


def verify_critical_terms(
    index: dict[str, list[dict[str, Any]]],
    critical_terms: list[str],
    normalizer: Normalizer,
) -> tuple[list[str], list[str]]:
    """Check that all critical terms resolve in the index. Returns (passed, failed)."""
    passed: list[str] = []
    failed: list[str] = []
    for term in critical_terms:
        norm = normalizer(term)
        if norm in index or term.lower() in index:
            passed.append(term)
        else:
            failed.append(term)
    return passed, failed


def load_all_contact_indexes(
    contact_dir: Path | None = None,
) -> dict[str, dict[str, list[dict[str, Any]]]]:
    """Load and index all contact lexicons from the data/contact/ directory."""
    d = contact_dir or _CONTACT_DIR
    indexes: dict[str, dict[str, list[dict[str, Any]]]] = {}

    egyptian_path = d / "egyptian_lexicon.jsonl"
    if egyptian_path.exists():
        entries = load_lexicon(egyptian_path)
        indexes["egyptian"] = build_contact_index(entries)

    eg_et_path = d / "egyptian_execration_toponyms.jsonl"
    if eg_et_path.exists():
        et_entries = load_lexicon(eg_et_path)
        et_index = build_contact_index(et_entries)
        if "egyptian" in indexes:
            for k, v in et_index.items():
                indexes["egyptian"].setdefault(k, []).extend(v)
        else:
            indexes["egyptian"] = et_index

    anatolian_path = d / "anatolian_lexicon.jsonl"
    if anatolian_path.exists():
        entries = load_lexicon(anatolian_path)
        indexes["anatolian"] = build_contact_index(entries)

    hurrian_path = d / "hurrian_lexicon.jsonl"
    if hurrian_path.exists():
        entries = load_lexicon(hurrian_path)
        indexes["hurrian"] = build_contact_index(entries)

    canaanite_path = d / "amarna_canaanite.jsonl"
    if canaanite_path.exists():
        entries = load_lexicon(canaanite_path)
        indexes["canaanite"] = build_contact_index(entries)

    ugaritic_path = d / "ugaritic_lexicon.jsonl"
    if ugaritic_path.exists():
        entries = load_lexicon(ugaritic_path)
        indexes["ugaritic"] = build_contact_index(entries)

    greek_path = d / "greek_lexicon.jsonl"
    if greek_path.exists():
        entries = load_lexicon(greek_path)
        # Enrich so multiword heads ("καὶ γάρ" → kaigar) match the same
        # keys normalize_greek produces at query time.
        enrich_match_keys(entries, normalize_greek, source_field="form_original")
        indexes["greek"] = build_contact_index(entries)

    hebrew_path = d / "hebrew_lexicon.jsonl"
    if hebrew_path.exists():
        entries = load_lexicon(hebrew_path)
        indexes["hebrew"] = build_contact_index(entries)

    aramaic_path = d / "aramaic_lexicon.jsonl"
    if aramaic_path.exists():
        entries = load_lexicon(aramaic_path)
        indexes["aramaic"] = build_contact_index(entries)

    geez_path = d / "geez_lexicon.jsonl"
    if geez_path.exists():
        entries = load_lexicon(geez_path)
        indexes["geez"] = build_contact_index(entries)

    south_arabian_path = d / "south_arabian_lexicon.jsonl"
    if south_arabian_path.exists():
        entries = load_lexicon(south_arabian_path)
        indexes["south_arabian"] = build_contact_index(entries)

    return indexes
