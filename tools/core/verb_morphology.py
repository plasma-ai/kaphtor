"""Verb-morphology deparser: expose Semitic roots hidden inside inflected forms.

Report-only — never writes affiliations or promotes entries. Enumerates
template-licensed affix strips at the transliteration level (where vowel
structure is still visible), returning residual skeletons for downstream
cognate matching. Templates live in data/verb_templates.json; each parse
carries the template's penalty, which downstream callers add to Levenshtein
distance exactly like the existing morphophonological-rule penalties.

Test words: A-TA-I-*301-WA-JA (16 attestations; proposed as a Gt of √n-w-y,
the ʾa- prefix and -t- augment around the root) and TA-NA-RA-TE-U-TI-NU (IO Za
2; proposed as a 3fs N-stem of √r-ṣ-y inside ta-na- and the -ū-tī-nū energic
chain). Neither proposed root shows at skeleton level without the strip.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

try:
    from .semitic_morphology import RADICAL_EXCEPTIONS
    from .skeleton import _SUBSCRIPT_MAP, _lookup_sign, extract_skeleton
except ImportError:
    from semitic_morphology import RADICAL_EXCEPTIONS
    from skeleton import _SUBSCRIPT_MAP, _lookup_sign, extract_skeleton

try:
    from ..paths import LINEAR_A_DATA, require
except ImportError:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from tools.paths import LINEAR_A_DATA, require

TEMPLATES_PATH = LINEAR_A_DATA / "verb_templates.json"

# Lacuna and uncertainty marks: tokens carrying these are damaged readings,
# so affix stripping would parse restorations rather than attested signs.
LACUNA_CHARS = ("[", "]", "?")


@dataclass(frozen=True)
class VerbTemplate:
    id: str
    stem: str
    description: str
    prefix_signs: tuple[str, ...]
    infix_sign: str | None
    infix_max_offset: int
    suffix_signs: tuple[str, ...]
    affix_consonants_removed: tuple[str, ...]
    vocalization: str
    penalty: float
    evidence: str
    min_residual_radicals: int
    restorable_radicals: tuple[str, ...]
    require_geminate: bool
    layer_scope: tuple[str, ...]
    status: str
    # Opt-in restoration controls; both default off, so templates that predate
    # them keep restoring R1 on every parse (their calibrations assume it).
    restore_only_if_short: bool = False  # restore only below the radical floor
    require_restoration: bool = False    # the unrestored parse is not licensed

    @property
    def specificity(self) -> int:
        """Number of pattern signs — longer patterns win penalty ties."""
        return len(self.prefix_signs) + (1 if self.infix_sign else 0) + len(self.suffix_signs)


@dataclass(frozen=True)
class VerbParse:
    template_id: str
    stem: str
    transliteration: str
    residual_signs: tuple[str, ...]
    residual_skeleton: str
    surface_skeleton: str
    stripped_prefix: tuple[str, ...]
    stripped_infix: str | None
    stripped_suffix: tuple[str, ...]
    restored_radical: str | None
    penalty: float
    vocalization: str
    evidence: str
    rules: tuple[str, ...] = field(default_factory=tuple)

    @property
    def rule(self) -> str:
        return "verb_lens:" + "+".join(self.rules)


def load_templates(path: Path | None = None) -> list[VerbTemplate]:
    """Load and validate the template inventory.

    Raises ValueError on schema violations, including any template whose
    prefix is a single pure-vowel sign — bare-vowel strips are root-internal
    phonology, not morphology; multi-sign vowel-initial patterns
    (A-TA-, U-NA-) are fine because a specific attested template licenses them.
    """
    path = path or TEMPLATES_PATH
    data = json.loads(require(path, path.name).read_text(encoding="utf-8"))
    templates: list[VerbTemplate] = []
    seen_ids: set[str] = set()
    for raw in data["templates"]:
        pattern = raw["surface_pattern"]
        t = VerbTemplate(
            id=raw["id"],
            stem=raw["stem"],
            description=raw["description"],
            prefix_signs=tuple(pattern["prefix_signs"]),
            infix_sign=pattern["infix_sign"],
            infix_max_offset=pattern["infix_max_offset"],
            suffix_signs=tuple(pattern["suffix_signs"]),
            affix_consonants_removed=tuple(raw["affix_consonants_removed"]),
            vocalization=raw["vocalization"],
            penalty=raw["penalty"],
            evidence=raw["evidence"],
            min_residual_radicals=raw["min_residual_radicals"],
            restorable_radicals=tuple(raw["restorable_radicals"]),
            require_geminate=raw["require_geminate"],
            layer_scope=tuple(raw["layer_scope"]),
            status=raw["status"],
            restore_only_if_short=raw.get("restore_only_if_short", False),
            require_restoration=raw.get("require_restoration", False),
        )
        if t.id in seen_ids:
            raise ValueError(f"template {t.id}: duplicate id")
        seen_ids.add(t.id)
        if not t.prefix_signs and not t.suffix_signs:
            raise ValueError(f"template {t.id}: pattern strips nothing")
        if t.prefix_signs and t.suffix_signs:
            # Parses compose one prefix template with one suffix template;
            # a template carrying both would never have its suffix applied.
            raise ValueError(f"template {t.id}: define prefix and suffix as separate templates")
        if t.infix_sign and not t.prefix_signs:
            raise ValueError(f"template {t.id}: infix requires a prefix anchor")
        if t.infix_sign and t.infix_max_offset < 1:
            raise ValueError(f"template {t.id}: infix_max_offset must be >= 1 to ever match")
        if len(t.prefix_signs) == 1 and _sign_consonant(t.prefix_signs[0]) is None:
            raise ValueError(f"template {t.id}: single pure-vowel prefix is prohibited")
        if t.penalty not in (0.10, 0.25, 0.40):
            raise ValueError(f"template {t.id}: penalty {t.penalty} outside defined tiers")
        if t.status not in ("active", "speculative"):
            raise ValueError(f"template {t.id}: unknown status {t.status!r}")
        for flag in ("restore_only_if_short", "require_restoration"):
            if getattr(t, flag) and not (t.prefix_signs and t.restorable_radicals):
                raise ValueError(f"template {t.id}: {flag} needs a prefix and restorable_radicals")
        templates.append(t)
    return templates


_TEMPLATE_CACHE: dict[Path, list[VerbTemplate]] = {}


def _templates(path: Path | None = None) -> list[VerbTemplate]:
    key = path or TEMPLATES_PATH
    if key not in _TEMPLATE_CACHE:
        _TEMPLATE_CACHE[key] = load_templates(key)
    return _TEMPLATE_CACHE[key]


def _normalize_sign(sign: str) -> str:
    return sign.upper().translate(_SUBSCRIPT_MAP)


def _sign_consonant(sign: str) -> str | None:
    decomp = _lookup_sign(sign)
    return decomp[0] if decomp else None


def _signs_match(token_sign: str, pattern_sign: str) -> bool:
    return _normalize_sign(token_sign) == _normalize_sign(pattern_sign)


def _consonants(signs: tuple[str, ...]) -> list[str]:
    """Per-sign consonant list (pure-vowel signs contribute nothing)."""
    result = []
    for s in signs:
        c = _sign_consonant(s)
        if c:
            result.append(c)
    return result


def _has_geminate(signs: tuple[str, ...]) -> bool:
    """Two successive signs sharing a consonant — the CV spelling of a doubled radical."""
    prev = None
    for s in signs:
        c = _sign_consonant(s)
        if c is not None:
            if c == prev:
                return True
            prev = c
    return False


def _apply_prefix_template(t: VerbTemplate, signs: tuple[str, ...]) -> list[tuple[str, ...]]:
    """Return residual sign tuples after applying t's prefix (and infix) pattern.

    Multiple residuals arise when the infix is licensed at more than one
    offset (strong-root Gt has it after R1, weak-I Gt immediately after the
    prefix).
    """
    n = len(t.prefix_signs)
    if len(signs) <= n:
        return []
    if not all(_signs_match(signs[i], t.prefix_signs[i]) for i in range(n)):
        return []
    rest = signs[n:]
    if t.infix_sign is None:
        return [rest]
    residuals = []
    for offset in range(min(t.infix_max_offset, len(rest))):
        if _signs_match(rest[offset], t.infix_sign):
            residual = rest[:offset] + rest[offset + 1:]
            if residual:
                residuals.append(residual)
    return residuals


def verbal_parses(
    transliteration: str,
    include_speculative: bool = False,
    templates_path: Path | None = None,
) -> list[VerbParse]:
    """Enumerate template-licensed verbal parses of a Linear A word.

    Returns [] rather than raising on malformed input: damaged tokens
    (lacuna marks) and tokens containing signs absent from
    SIGN_DECOMPOSITION cannot be parsed honestly. Each parse
    combines at most one prefix template (with its infix) and one suffix
    template, checks the residual-radical floor after ALL
    stripping, and requires 3+ residual radicals unless the original word
    has 4+ signs. Prefix strips are suppressed when the surface
    skeleton is a protected root in RADICAL_EXCEPTIONS.

    Results are sorted by (effective penalty, longer pattern first),
    deduplicated on (residual skeleton, stem).
    """
    token = transliteration.strip()
    if not token or any(ch in token for ch in LACUNA_CHARS):
        return []
    raw_signs = tuple(token.split("-"))
    if "" in raw_signs:  # double dash or edge dash: malformed data entry, not a word
        return []
    if len(raw_signs) < 2:
        return []
    # Normalize once so residual_signs display uniformly (ja-ta-no → JA-TA-NO)
    signs = tuple(_normalize_sign(s) for s in raw_signs)
    if any(_lookup_sign(s) is None for s in signs):
        return []

    surface_skeleton = extract_skeleton(token)
    protected = surface_skeleton in RADICAL_EXCEPTIONS

    all_templates = [
        t for t in _templates(templates_path)
        if t.status == "active" or include_speculative
    ]
    # Protected roots (mlk, ntn, thm…) suppress prefix strips only — matching
    # fuzzy_skeleton_candidates, where exceptions guard prefixes, not suffixes.
    prefix_templates: list[VerbTemplate | None] = [None]
    if not protected:
        prefix_templates += [t for t in all_templates if t.prefix_signs]
    suffix_templates: list[VerbTemplate | None] = [None] + [
        t for t in all_templates if t.suffix_signs and not t.prefix_signs
    ]

    min_radicals_floor = 2 if len(signs) >= 4 else 3

    parses: list[VerbParse] = []
    for pre in prefix_templates:
        if pre is None:
            pre_residuals = [signs]
        else:
            pre_residuals = _apply_prefix_template(pre, signs)
        for pre_residual in pre_residuals:
            for suf in suffix_templates:
                if pre is None and suf is None:
                    continue
                residual = pre_residual
                if suf is not None:
                    k = len(suf.suffix_signs)
                    if len(residual) <= k or not all(
                        _signs_match(residual[-k + i], suf.suffix_signs[i]) for i in range(k)
                    ):
                        continue
                    residual = residual[:-k]
                if not residual:
                    continue

                applied = [t for t in (pre, suf) if t is not None]
                penalty = round(sum(t.penalty for t in applied), 4)
                min_required = max(
                    [t.min_residual_radicals for t in applied] + [min_radicals_floor]
                )
                if any(t.require_geminate for t in applied) and not _has_geminate(residual):
                    continue

                radicals = _consonants(residual)
                variants: list[tuple[list[str], str | None]] = []
                if pre is None or not pre.require_restoration:
                    variants.append((radicals, None))
                if pre is not None and not (
                    pre.restore_only_if_short and len(radicals) >= min_required
                ):
                    for r in pre.restorable_radicals:
                        variants.append(([r] + radicals, r))

                for variant_radicals, restored in variants:
                    if len(variant_radicals) < min_required:
                        continue
                    parses.append(VerbParse(
                        template_id="+".join(t.id for t in applied),
                        stem=(pre or suf).stem,
                        transliteration=token,
                        residual_signs=residual,
                        residual_skeleton="".join(variant_radicals),
                        surface_skeleton=surface_skeleton,
                        stripped_prefix=pre.prefix_signs if pre else (),
                        stripped_infix=pre.infix_sign if pre else None,
                        stripped_suffix=suf.suffix_signs if suf else (),
                        restored_radical=restored,
                        penalty=penalty,
                        vocalization=(pre or suf).vocalization,
                        evidence="; ".join(t.evidence for t in applied),
                        rules=tuple(t.id for t in applied),
                    ))

    specificity = {p: 0 for p in parses}
    by_template = {t.id: t for t in all_templates}
    for p in parses:
        specificity[p] = sum(by_template[r].specificity for r in p.rules)

    parses.sort(key=lambda p: (p.penalty, -specificity[p], p.template_id))

    seen: set[tuple[str, str]] = set()
    unique: list[VerbParse] = []
    for p in parses:
        key = (p.residual_skeleton, p.stem)
        if key not in seen:
            seen.add(key)
            unique.append(p)
    return unique


def format_parse(p: VerbParse) -> str:
    """One-line rendering for the VERBAL PARSES output section."""
    strips = []
    if p.stripped_prefix:
        strips.append("-".join(p.stripped_prefix) + "-")
    if p.stripped_infix:
        strips.append(f"-{p.stripped_infix}-")
    if p.stripped_suffix:
        strips.append("-" + "-".join(p.stripped_suffix))
    restored = f" (+{p.restored_radical} restored as R1)" if p.restored_radical else ""
    return (
        f"{p.transliteration}: {p.stem} [{', '.join(strips)}] -> "
        f"residual {'-'.join(p.residual_signs)} = "
        f"{'-'.join(p.residual_skeleton)}{restored} "
        f"(penalty {p.penalty:.2f}, {p.rule})"
    )
