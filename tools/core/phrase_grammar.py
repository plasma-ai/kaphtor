"""Phrase grammar loader.

Loads the WORD_ROLE_DOSSIER and FORMULA_FAMILY_CLUSTERS from a
phrase-grammar directory and exposes word→role lookups,
role compatibility scoring, and formula family membership.

Used by:
- ventris_propagate.py (--phrase-grammar flag for slot-role priors)
- hypothesis_test.py (slot compatibility testing)
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

SUBSCRIPT_TO_DIGIT = str.maketrans({
    "₀": "0", "₁": "1", "₂": "2", "₃": "3", "₄": "4",
    "₅": "5", "₆": "6", "₇": "7", "₈": "8", "₉": "9",
})

STRIP_SUBSCRIPTS = str.maketrans("", "", "₀₁₂₃₄₅₆₇₈₉")

ROLE_COMPATIBILITY: dict[str, set[str]] = {
    "PERSONAL_NAME": {"PERSONAL_NAME", "TOPONYM", "CULTIC_RECIPIENT"},
    "TOPONYM": {"PERSONAL_NAME", "TOPONYM"},
    "CULTIC_RECIPIENT": {"PERSONAL_NAME", "CULTIC_RECIPIENT"},
    "VERB_ACTION": {"VERB_ACTION", "UNKNOWN_FORMULA_ELEMENT"},
    "COMMODITY_LABEL": {"COMMODITY_LABEL"},
    "ACCOUNTING_TOTAL": {"ACCOUNTING_TOTAL"},
    "QUANTITY_OR_MEASURE": {"QUANTITY_OR_MEASURE", "COMMODITY_LABEL"},
    "VESSEL_MARK": {"VESSEL_MARK"},
    "NON_PHONETIC_OR_CONTEXTUAL": set(),
    "ROUNDel_OR_SEALING_MARK": set(),
}

SEMANTIC_KEYWORDS: dict[str, str] = {
    "grain": "COMMODITY_LABEL",
    "wheat": "COMMODITY_LABEL",
    "emmer": "COMMODITY_LABEL",
    "barley": "COMMODITY_LABEL",
    "olive": "COMMODITY_LABEL",
    "oil": "COMMODITY_LABEL",
    "wine": "COMMODITY_LABEL",
    "honey": "COMMODITY_LABEL",
    "fig": "COMMODITY_LABEL",
    "wool": "COMMODITY_LABEL",
    "textile": "COMMODITY_LABEL",
    "cloth": "COMMODITY_LABEL",
    "bronze": "COMMODITY_LABEL",
    "copper": "COMMODITY_LABEL",
    "gold": "COMMODITY_LABEL",
    "silver": "COMMODITY_LABEL",
    "water": "COMMODITY_LABEL",
    "field": "COMMODITY_LABEL",
    "buck": "COMMODITY_LABEL",
    "goat": "COMMODITY_LABEL",
    "sheep": "COMMODITY_LABEL",
    "ox": "COMMODITY_LABEL",
    "cattle": "COMMODITY_LABEL",
    "pig": "COMMODITY_LABEL",
    "horse": "COMMODITY_LABEL",
    "total": "ACCOUNTING_TOTAL",
    "all": "ACCOUNTING_TOTAL",
    "sum": "ACCOUNTING_TOTAL",
    "town": "TOPONYM",
    "village": "TOPONYM",
    "city": "TOPONYM",
    "earth": "TOPONYM",
    "mountain": "TOPONYM",
    "house": "TOPONYM",
    "gate": "TOPONYM",
    "place": "TOPONYM",
    "give": "VERB_ACTION",
    "offer": "VERB_ACTION",
    "dedicate": "VERB_ACTION",
    "pour": "VERB_ACTION",
    "heart": "VERB_ACTION",
    "hand": "VERB_ACTION",
    "eye": "VERB_ACTION",
    "mouth": "VERB_ACTION",
    "fire": "VERB_ACTION",
    "smith": "PERSONAL_NAME",
    "servant": "PERSONAL_NAME",
    "mother": "PERSONAL_NAME",
    "father": "PERSONAL_NAME",
    "son": "PERSONAL_NAME",
    "daughter": "PERSONAL_NAME",
    "lord": "CULTIC_RECIPIENT",
    "king": "CULTIC_RECIPIENT",
    "goddess": "CULTIC_RECIPIENT",
    "god": "CULTIC_RECIPIENT",
}


class PhraseGrammar:
    """Loaded phrase grammar model with word→role lookups and scoring."""

    def __init__(
        self,
        word_roles: dict[str, dict],
        formula_families: list[dict],
    ):
        self._word_roles = word_roles
        self._formula_families = formula_families
        self._word_to_families: dict[str, list[str]] = {}
        self._build_family_index()

    def _build_family_index(self) -> None:
        for fam in self._formula_families:
            fam_id = fam["family_id"]
            for frame in fam.get("top_frames", []):
                for doc_id in frame.get("inscriptions", []):
                    self._word_to_families.setdefault(doc_id, [])
                    if fam_id not in self._word_to_families[doc_id]:
                        self._word_to_families[doc_id].append(fam_id)

    def get_role(self, word: str) -> str | None:
        entry = self._lookup(word)
        return entry["role"] if entry else None

    def get_role_entry(self, word: str) -> dict | None:
        return self._lookup(word)

    def get_families_for_doc(self, doc_id: str) -> list[str]:
        return self._word_to_families.get(doc_id, [])

    def infer_semantic_category(self, meaning: str) -> str | None:
        if not meaning:
            return None
        meaning_lower = meaning.lower()
        for keyword, role in SEMANTIC_KEYWORDS.items():
            if re.search(r'\b' + re.escape(keyword) + r'\b', meaning_lower):
                return role
        return None

    def score_compatibility(self, word: str, meaning: str) -> tuple[float, dict]:
        """Score how well a candidate meaning fits this word's phrase-grammar role.

        Returns (score_adjustment, details) where score_adjustment is:
          +0.10  MATCH — inferred category matches assigned role
          +0.05  COMPATIBLE — inferred category is compatible (e.g., TOPONYM in PERSONAL_NAME slot)
           0.00  NEUTRAL — no data, unknown role, or undetermined category
          -0.10  MISMATCH — inferred category contradicts assigned role
        """
        entry = self._lookup(word)
        if not entry:
            return 0.0, {"verdict": "NO_DATA", "role": None, "inferred": None}

        role = entry["role"]
        inferred = self.infer_semantic_category(meaning)

        if role == "UNKNOWN_FORMULA_ELEMENT":
            return 0.0, {
                "verdict": "UNKNOWN_ROLE",
                "role": role,
                "inferred": inferred,
            }

        if inferred is None:
            return 0.0, {
                "verdict": "UNDETERMINED",
                "role": role,
                "inferred": None,
            }

        if inferred == role:
            return 0.10, {
                "verdict": "MATCH",
                "role": role,
                "inferred": inferred,
            }

        compatible_set = ROLE_COMPATIBILITY.get(role, set())
        if inferred in compatible_set:
            return 0.05, {
                "verdict": "COMPATIBLE",
                "role": role,
                "inferred": inferred,
            }

        return -0.10, {
            "verdict": "MISMATCH",
            "role": role,
            "inferred": inferred,
        }

    @property
    def word_count(self) -> int:
        return len(self._word_roles)

    @property
    def family_count(self) -> int:
        return len(self._formula_families)

    def role_distribution(self) -> dict[str, int]:
        return dict(Counter(
            e["role"] for e in self._word_roles.values()
            if isinstance(e, dict) and "role" in e
        ))

    # -----------------------------------------------------------------------
    # UNKNOWN_FORMULA_ELEMENT decomposition
    # -----------------------------------------------------------------------

    # Token types that are numerics or fractions (produced by the pattern builder).
    _NUM_TOKENS: frozenset[str] = frozenset({"<NUM>", "<FRAC>"})
    # Token types that are commodity ideograms.
    _COMMODITY_TOKENS: frozenset[str] = frozenset({"<COMMODITY>"})
    # Tokens that carry a word but are already classified (KNOWN or CANDIDATE).
    _CLASSIFIED_TOKENS: frozenset[str] = frozenset({"<KNOWN_WORD>", "<CANDIDATE>"})
    # The word-slot token an UNKNOWN word would occupy.
    _UNKNOWN_TOKEN: str = "<WORD>"

    def _pattern_tokens(self, pattern: str) -> list[str]:
        """Split a template pattern string into individual tokens.

        Angle-bracketed tokens, Unicode ideograms, and bare alphanumeric
        fragments are returned as separate elements.  Whitespace is consumed.
        """
        if not pattern or pattern == "None":
            return []
        return re.findall(r"<[^>]+>|[^\s]+", pattern)

    def _subrole_for_word_slot(self, tokens: list[str], slot_idx: int, family: str) -> str:
        """Derive a subrole for the <WORD> token at *slot_idx* inside *tokens*.

        Rules:
          name_title_or_short_formula  → NAME_TITLE (position 0 before any NUM/COMMODITY)
          commodity_accounting_row     → COMMODITY_LABEL if next meaningful token is
                                         <COMMODITY> or <NUM>; else PERSONAL_NAME
          accounting_total             → ACCOUNTING_PARTICLE if a <KNOWN_WORD> precedes it
          accounting_or_measure        → NAME_TITLE if first word-like position;
                                         QUANTITY_OR_MEASURE if a <NUM>/<FRAC> follows
          vessel_mark                  → VESSEL_MARK
          sealing_formula              → NAME_TITLE
          unknown_recurrent_formula    → LOW_INFORMATION_UNKNOWN
        """
        if family == "vessel_mark":
            return "VESSEL_MARK"
        if family == "sealing_formula":
            return "NAME_TITLE"
        if family == "unknown_recurrent_formula":
            return "LOW_INFORMATION_UNKNOWN"

        # Build a compact view of what comes after and before this slot.
        after_tokens = tokens[slot_idx + 1:]
        before_tokens = tokens[:slot_idx]

        # Immediate follower (skip non-semantic filler like bare Unicode glyphs).
        immediate_after: str | None = None
        for tok in after_tokens:
            if tok.startswith("<") or tok in ("—", "𐄁", "𐝫", "𐝓"):
                immediate_after = tok
                break

        has_known_before = any(t == "<KNOWN_WORD>" for t in before_tokens)
        any_num_before = any(t in self._NUM_TOKENS for t in before_tokens)

        # First meaningful word slot: nothing numeric before this position.
        is_first_position = not any_num_before and not any(
            t in self._COMMODITY_TOKENS for t in before_tokens
        )

        if family == "name_title_or_short_formula":
            return "NAME_TITLE"

        if family == "accounting_total":
            if has_known_before:
                return "ACCOUNTING_PARTICLE"
            return "NAME_TITLE"

        if family == "commodity_accounting_row":
            if immediate_after in self._COMMODITY_TOKENS | self._NUM_TOKENS:
                return "COMMODITY_LABEL"
            return "PERSONAL_NAME"

        if family == "accounting_or_measure":
            if is_first_position:
                return "NAME_TITLE"
            if immediate_after in self._NUM_TOKENS:
                return "QUANTITY_OR_MEASURE"
            # Word sandwiched between known markers without a direct numeric
            # successor—treat as personal name (typical row-header position).
            return "PERSONAL_NAME"

        return "LOW_INFORMATION_UNKNOWN"

    def decompose_unknown_roles(
        self,
        corpus: dict[str, dict],
        inscription_templates: list[dict],
    ) -> dict[str, str]:
        """Decompose UNKNOWN_FORMULA_ELEMENT words into discriminating subroles.

        Parameters
        ----------
        corpus:
            doc_id → corpus entry dict containing ``transliteratedWords``.
        inscription_templates:
            List of template index entries; each has ``inscription``, ``pattern``,
            and ``family`` keys.

        Returns
        -------
        dict mapping each UNKNOWN_FORMULA_ELEMENT word to a subrole string.
        """
        # --- 1. Build reverse index: normalized_word → set of doc_ids ----------
        word_to_docs: dict[str, set[str]] = defaultdict(set)
        for doc_id, entry in corpus.items():
            for raw in entry.get("transliteratedWords", []):
                w = raw.strip()
                if not w or w == "\n":
                    continue
                # Normalize subscripts as _lookup does.
                for form in {w, w.translate(SUBSCRIPT_TO_DIGIT), w.translate(STRIP_SUBSCRIPTS)}:
                    if form:
                        word_to_docs[form].add(doc_id)

        # --- 2. Build forward index: doc_id → template entry --------------------
        doc_to_template: dict[str, dict] = {}
        for tmpl in inscription_templates:
            insc = tmpl.get("inscription", "")
            if insc:
                doc_to_template[insc] = tmpl

        # --- 3. Collect UNKNOWN_FORMULA_ELEMENT words ---------------------------
        unknown_words = [
            w for w, e in self._word_roles.items()
            if isinstance(e, dict) and e.get("role") == "UNKNOWN_FORMULA_ELEMENT"
        ]

        result: dict[str, str] = {}
        unknown_word_set = set(unknown_words)

        for word in unknown_words:
            # Gather all doc_ids this word appears in (using subscript variants).
            doc_ids: set[str] = set()
            for form in {word, word.translate(SUBSCRIPT_TO_DIGIT), word.translate(STRIP_SUBSCRIPTS)}:
                doc_ids |= word_to_docs.get(form, set())

            if not doc_ids:
                result[word] = "LOW_INFORMATION_UNKNOWN"
                continue

            # Accumulate subrole votes across all inscription appearances.
            subroles: list[str] = []
            for doc_id in doc_ids:
                tmpl = doc_to_template.get(doc_id)
                if tmpl is None:
                    continue
                family = tmpl.get("family", "unknown_recurrent_formula")
                tokens = self._pattern_tokens(tmpl.get("pattern", ""))

                # Find the word-slot indices; an UNKNOWN word maps to <WORD>.
                word_slot_indices = [
                    i for i, t in enumerate(tokens) if t == self._UNKNOWN_TOKEN
                ]

                if not word_slot_indices:
                    # Inscription has no <WORD> slots—pattern may be fully known.
                    # Apply family-only rules that do not need positional context.
                    _family_defaults = {
                        "vessel_mark": "VESSEL_MARK",
                        "sealing_formula": "NAME_TITLE",
                        "name_title_or_short_formula": "NAME_TITLE",
                        "unknown_recurrent_formula": "LOW_INFORMATION_UNKNOWN",
                        "accounting_total": "ACCOUNTING_PARTICLE",
                        "commodity_accounting_row": "PERSONAL_NAME",
                        "accounting_or_measure": "NAME_TITLE",
                    }
                    subroles.append(_family_defaults.get(family, "LOW_INFORMATION_UNKNOWN"))
                    continue

                # Align this word to its positional <WORD> slot by finding
                # its ordinal index among unknown words in the inscription.
                if len(word_slot_indices) == 1:
                    slot_idx = word_slot_indices[0]
                else:
                    insc_entry = corpus.get(doc_id, {})
                    insc_words = [
                        w.strip() for w in insc_entry.get("transliteratedWords", [])
                        if w.strip() and w.strip() != "\n"
                    ]
                    word_ordinal = 0
                    for iw in insc_words:
                        iw_forms = {iw, iw.translate(SUBSCRIPT_TO_DIGIT), iw.translate(STRIP_SUBSCRIPTS)}
                        if iw_forms & {word, word.translate(SUBSCRIPT_TO_DIGIT), word.translate(STRIP_SUBSCRIPTS)}:
                            break
                        if iw_forms & unknown_word_set:
                            word_ordinal += 1
                    slot_idx = word_slot_indices[min(word_ordinal, len(word_slot_indices) - 1)]
                subroles.append(self._subrole_for_word_slot(tokens, slot_idx, family))

            if not subroles:
                result[word] = "LOW_INFORMATION_UNKNOWN"
                continue

            # --- 4. Resolve votes -----------------------------------------------
            counter = Counter(subroles)
            non_low_info = {r: c for r, c in counter.items() if r != "LOW_INFORMATION_UNKNOWN"}

            if not non_low_info:
                result[word] = "LOW_INFORMATION_UNKNOWN"
                continue

            # Plurality vote; ties default to the alphabetically first subrole
            # (deterministic, avoids random ordering).
            top_subrole = max(non_low_info, key=lambda r: (non_low_info[r], r))
            top_count = non_low_info[top_subrole]

            # Check for a conflict: another non-LOW subrole tied with the winner
            # and semantically incompatible.
            competing = [r for r, c in non_low_info.items() if r != top_subrole and c >= top_count]
            _compat_groups: list[frozenset[str]] = [
                frozenset({"NAME_TITLE", "PERSONAL_NAME", "ACCOUNTING_PARTICLE", "VESSEL_MARK"}),
                frozenset({"COMMODITY_LABEL", "QUANTITY_OR_MEASURE"}),
            ]
            conflict = False
            for rival in competing:
                same_group = any(
                    top_subrole in g and rival in g for g in _compat_groups
                )
                if not same_group:
                    conflict = True
                    break

            result[word] = "LOW_INFORMATION_UNKNOWN" if conflict else top_subrole

        return result

    def _lookup(self, word: str) -> dict | None:
        if word in self._word_roles:
            return self._word_roles[word]
        digit_form = word.translate(SUBSCRIPT_TO_DIGIT)
        if digit_form != word and digit_form in self._word_roles:
            return self._word_roles[digit_form]
        stripped = word.translate(STRIP_SUBSCRIPTS)
        if stripped != word and stripped in self._word_roles:
            return self._word_roles[stripped]
        return None


_cached: PhraseGrammar | None = None
_cached_path: Path | None = None


def load_inscription_templates(artifacts_dir: Path) -> list[dict]:
    """Load INSCRIPTION_TEMPLATE_INDEX.json from *artifacts_dir*.

    Returns the raw list of template dicts (inscription, pattern, family, …).
    Raises FileNotFoundError if the file is absent.
    """
    path = artifacts_dir / "linear-a-phrase-grammar" / "INSCRIPTION_TEMPLATE_INDEX.json"
    if not path.exists():
        raise FileNotFoundError(f"Inscription template index not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_phrase_grammar(artifacts_dir: Path) -> PhraseGrammar:
    """Load phrase grammar from artifacts directory. Cached per resolved path."""
    global _cached, _cached_path
    resolved = artifacts_dir.resolve()
    if _cached is not None and _cached_path == resolved:
        return _cached

    wrd_path = artifacts_dir / "linear-a-phrase-grammar" / "WORD_ROLE_DOSSIER.json"
    ffc_path = artifacts_dir / "linear-a-phrase-grammar" / "FORMULA_FAMILY_CLUSTERS.json"

    if not wrd_path.exists():
        raise FileNotFoundError(f"Word role dossier not found: {wrd_path}")

    raw_roles = json.loads(wrd_path.read_text(encoding="utf-8"))
    word_roles: dict[str, dict] = {}
    for entry in raw_roles:
        w = entry.get("word", "")
        if w:
            word_roles[w] = entry

    formula_families: list[dict] = []
    if ffc_path.exists():
        formula_families = json.loads(ffc_path.read_text(encoding="utf-8"))

    _cached = PhraseGrammar(word_roles, formula_families)
    _cached_path = resolved
    return _cached


def clear_cache() -> None:
    global _cached, _cached_path
    _cached = None
    _cached_path = None
