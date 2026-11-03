"""Sign labels from every vocabulary in the project, resolved to sign-registry.json codes.

Four vocabularies name the same signs differently:
  corpus transliteratedWords  KA, PA₃, *21F, OLE+KI, *411-VS   (with glyphs in `words`)
  SigLA (sigla_db.json)        AB8, A411, A7092, N800 (variant letter kept apart: code AB21 + variant f)
  SigLA crop manifest          AB08, A411b, A7092
  lineara sign boxes           RA₂, *900 (word divider), ¹⁄₂
Registry codes are AB08, A411VASB, A709-2, AB21F (name OVISf), and some signs have no
registry name at all (AB56 = PA₃), so names alone cannot bridge them.

Routes, first hit wins: override, glyph, structural class, code, star form, whole label
(lineara label -> glyph -> registry, then registry name), X/Y alternatives, ligature,
rendered fraction. A glyph hit is checked against the label: a disagreement, a glyph that
lineara draws for more than one GORILA sign, and a ligature whose label keeps a lost
component are all reported, never settled silently. A label no route resolves is
`unresolved`, never guessed. Hand fixes go in data/linear-a/sign_crosswalk_overrides.json so
that no rebuild reverts them. The lineara labels come from a lashon-ha-kretan checkout named by
LASHON_HA_KRETAN_DIR; without one that route is off and `has_lineara` is False.
"""
from __future__ import annotations

import json
import os
import re
import unicodedata
from dataclasses import dataclass, field, replace
from functools import lru_cache
from pathlib import Path

from ..paths import LINEAR_A_DATA
from . import positional
from .data_cache import _load
from .js_parser import parse_string_pairs

OVERRIDES_PATH = LINEAR_A_DATA / "sign_crosswalk_overrides.json"
ZWJ = "‍"
UNDERDOT = "̣"
SUB = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")
_TO_SUB = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")      # QA2 -> QA₂ for lineara label lookup
KINDS = ("sign", "ligature", "fraction", "divider", "numeral", "lacuna", "unresolved")
LOST = ("?", "…", "")

_AB_RE = re.compile(r"^AB0*(\d{1,3})([A-Za-z]?)$")
_A_RE = re.compile(r"^A(\d{3,4})([A-Za-z]?)$")
_A709_RE = re.compile(r"^A709-?(\d)$")
_STAR_RE = re.compile(r"^\*(\d{2,3})([A-Za-z]?)$")
_VESSEL_RE = re.compile(r"^\*(\d{3})-VS$")
_VAS_SUFFIX_RE = re.compile(r"^\*?A?(\d{3})VAS([A-Z]?)$")    # *406VAS, A406VASB
_LETTER_RE = re.compile(r"(?:(?<=\d)|(?<=VAS))[A-Z]$")      # AB131A, A309A, A411VASB
_KLASMA_RE = re.compile(r"^A7\d\d(?:-\d)?$")                 # GORILA 700 series: A701 … A732 JE, A709-2
_COMPOSITE_RE = re.compile(r"^A[56]\d\d[A-Z]?$")


def lashon_dir() -> Path | None:
    """The lashon-ha-kretan checkout named by LASHON_HA_KRETAN_DIR (as tools/linear_a/inscription_image.py reads it)."""
    env = os.environ.get("LASHON_HA_KRETAN_DIR")
    return Path(env) if env else None


def is_klasma(code: str) -> bool:
    return bool(_KLASMA_RE.match(code))


def is_composite(code: str) -> bool:
    """GORILA complex-sign numbers (A501–A699: ligatures and composites with their own number)."""
    return bool(_COMPOSITE_RE.match(code))


def base_code(code: str) -> str:
    """AB131A -> AB131, A309A -> A309, A411VASB -> A411VAS. Klasma indices (A709-2) stay distinct."""
    return _LETTER_RE.sub("", code)


@dataclass(frozen=True)
class Resolution:
    """`codes` is the sign (or a ligature's components in order). When the label is ambiguous,
    `alternatives` lists every distinct candidate and `codes` is the first of them; a caller
    that holds more evidence (an aligned glyph, a token class, a SigLA reading) chooses among them."""
    label: str
    kind: str
    codes: tuple[str, ...] = ()
    rule: str = "none"
    ambiguous: bool = False
    note: str = ""
    alternatives: tuple[tuple[str, ...], ...] = ()

    def __post_init__(self) -> None:
        if not self.alternatives and self.codes:
            object.__setattr__(self, "alternatives", (self.codes,))


def _join_notes(*notes: str) -> str:
    return "; ".join(n for n in notes if n)


def _clean(raw: str) -> str:
    """Combining marks (the underdot of an uncertain reading) and stray quotes are not part of the sign."""
    text = "".join(ch for ch in unicodedata.normalize("NFD", raw) if not unicodedata.combining(ch))
    return unicodedata.normalize("NFC", text).strip().strip("'\"")


@dataclass
class Crosswalk:
    registry: list[dict]
    lineara_pairs: list[tuple[str, str]]
    overrides: dict[str, dict] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.codes = {s["ab_number"] for s in self.registry}
        self._upper = {c.upper(): c for c in self.codes}
        self.name_of = {s["ab_number"]: (s.get("name") or "").strip() for s in self.registry}
        self.by_glyph = {s["unicode_glyph"]: s["ab_number"] for s in self.registry if s.get("unicode_glyph")}
        self._components = {s["ab_number"]: tuple(s["components"]) for s in self.registry if s.get("components")}
        self.by_name: dict[str, list[str]] = {}
        for code, name in self.name_of.items():
            if name:
                self.by_name.setdefault(name.upper().translate(SUB), []).append(code)
        self.label_glyphs: dict[str, list[str]] = {}
        self.glyph_labels: dict[str, list[str]] = {}
        for glyph, label in self.lineara_pairs:
            self.label_glyphs.setdefault(label, []).append(glyph)
            self.glyph_labels.setdefault(glyph, [])
            if label not in self.glyph_labels[glyph]:
                self.glyph_labels[glyph].append(label)
        self._stand_in_cache: dict[str, tuple[tuple[str, ...], ...]] = {}
        for label, spec in self.overrides.items():
            unknown = [c for c in spec.get("codes", []) if c not in self.codes and c != "?"]
            if unknown or spec.get("kind") not in KINDS:
                raise ValueError(f"override {label!r}: kind {spec.get('kind')!r}, unknown codes {unknown}")

    @property
    def has_lineara(self) -> bool:
        return bool(self.lineara_pairs)

    def components(self, code: str) -> tuple[str, ...]:
        """A composite sign's parts as its registry row states them (A717 DD -> A703, A703); () otherwise."""
        return self._components.get(code, ())

    # -- entry point ----------------------------------------------------------

    def resolve(self, label: str, glyph: str | None = None, token_class: str | None = None) -> Resolution:
        """Resolve one sign label. The returned label is the input as given; notes record what was normalised."""
        raw = (label or "").strip()
        res = self._resolve(raw, glyph, token_class)
        if UNDERDOT in raw:
            res = replace(res, note=_join_notes("dotted (uncertain) in source", res.note))
        return res

    def _resolve(self, raw: str, glyph: str | None, token_class: str | None) -> Resolution:
        text = _clean(raw)
        for key in (raw, text):
            if key in self.overrides:
                spec = self.overrides[key]
                return Resolution(raw, spec["kind"], tuple(spec.get("codes", [])), "override",
                                  note=spec.get("note", ""))
        if glyph:
            hit = self._from_glyph(raw, glyph, "glyph")
            if hit:
                return self._check_glyph(raw, text, glyph, hit, token_class)
        return self._resolve_label(raw, text, token_class)

    # -- glyph route and its checks --------------------------------------------

    def _from_glyph(self, label: str, glyph: str, rule: str) -> Resolution | None:
        chars = [ch for ch in glyph if ch not in (positional.DAMAGE, ZWJ) and not ch.isspace()]
        if not chars:
            return None
        if chars == [positional.DIVIDER]:
            return Resolution(label, "divider", (), rule)
        if positional._is_aegean_number("".join(chars)):
            return Resolution(label, "numeral", (), rule)
        if not all(ch in self.by_glyph for ch in chars):
            return None
        codes = tuple(self.by_glyph[ch] for ch in chars)
        if positional.is_raw_fraction("".join(chars)):
            kind = "fraction"
        else:
            kind = "sign" if len(codes) == 1 else "ligature"
        return Resolution(label, kind, codes, rule)

    def _stand_ins(self, glyph: str) -> tuple[tuple[str, ...], ...]:
        """Registry codes of every other GORILA sign lineara draws with this one glyph (MA+RU, *558, *560 as
        A559). Labels of a klasmatogram glyph resolve in fraction context; the glyph's own sign and its
        lettered variants (VIN for VINa) are not stand-ins."""
        if glyph not in self._stand_in_cache:
            own = self.by_glyph.get(glyph)
            cls = "fraction" if own and is_klasma(own) else None
            found: list[tuple[str, ...]] = []
            for label in self.glyph_labels.get(glyph, []):
                res = self._resolve_label(label, _clean(label), cls, use_lineara=False)
                if res.kind not in ("sign", "fraction") or len(res.codes) != 1 or res.codes in found:
                    continue
                if own and base_code(res.codes[0]) == base_code(own):
                    continue
                found.append(res.codes)
            self._stand_in_cache[glyph] = tuple(found)
        return self._stand_in_cache[glyph]

    @staticmethod
    def has_lost_slot(label: str) -> bool:
        """VIR+[?], QA2+[?]+PU: a ligature label with a lost component."""
        parts = positional._bare(_clean(label)).split("+")
        return len(parts) > 1 and any(p.strip() in LOST for p in parts)

    def _check_glyph(self, raw: str, text: str, glyph: str, hit: Resolution, token_class: str | None) -> Resolution:
        if hit.kind in ("divider", "numeral"):
            return hit
        chars = [ch for ch in glyph if ch not in (positional.DAMAGE, ZWJ) and not ch.isspace()]
        # VIR+[?]: the glyph shows the surviving part and the label keeps the lost component. A GORILA complex
        # sign drawn by its own glyph (A510 for "QA2+[?]+PU") is the complete composite, unless the label's
        # surviving parts are exactly that glyph.
        partial = False
        surviving: tuple[str, ...] = ()
        if self.has_lost_slot(text) and "?" not in hit.codes:
            surviving = tuple(c for p in positional._bare(text).split("+") if p.strip() not in LOST
                              for c in self._resolve_label(p, _clean(p), "single_sign").codes)
            partial = surviving == hit.codes or not (len(hit.codes) == 1 and is_composite(hit.codes[0]))
        codes = hit.codes + ("?",) if partial else hit.codes
        kind = "ligature" if partial else hit.kind
        alts = [codes]
        notes = ["ligature component lost"] if partial else []
        if len(chars) == 1:
            stand_ins = [c + ("?",) if partial else c for c in self._stand_ins(chars[0])]
            stand_ins = [c for c in stand_ins if c not in alts]
            if stand_ins:
                alts += stand_ins
                notes.append("glyph drawn for more than one sign")
        label_res = self._resolve_label(raw, text, token_class)
        # A label naming the base of the glyph's own variant (*309 for glyph A309A) is less specific, not in conflict;
        # a label with no resolved code (HIDE+[?], HIDE no registry name) is no evidence either way.
        compatible = codes in label_res.alternatives or (
            len(codes) == 1 and any(len(a) == 1 and a[0] == base_code(codes[0]) for a in label_res.alternatives))
        if partial:
            compatible = not surviving or surviving == hit.codes
        informative = any(c != "?" for c in label_res.codes)
        if label_res.kind not in ("unresolved", "lacuna") and informative and not compatible:
            alts += [a for a in label_res.alternatives if a not in alts]
            reads = "+".join(label_res.codes)
            if len(hit.codes) == 1 and is_composite(hit.codes[0]) and len(label_res.codes) > 1 and not partial:
                # GORILA composite numbers against component names: a numbering question, not a reading conflict.
                notes.append(f"composite glyph against component label (label reads {reads})")
            else:
                notes.append(f"label/glyph disagree (label reads {reads})")
        if len(alts) == 1:
            return Resolution(raw, kind, codes, "glyph", note=_join_notes(*notes))
        return Resolution(raw, kind, codes, "glyph", ambiguous=True, note=_join_notes(*notes),
                          alternatives=tuple(alts))

    # -- label routes ------------------------------------------------------------

    def _code(self, bare: str) -> str | None:
        up = bare.upper()
        if up in self._upper:
            return self._upper[up]
        m = _AB_RE.match(up)
        if m:
            return self._upper.get(f"AB{int(m.group(1)):02d}{m.group(2)}")
        m = _A709_RE.match(up)
        if m:
            return self._upper.get(f"A709-{m.group(1)}")
        m = _A_RE.match(up)
        if m:
            num, letter = m.groups()
            return self._upper.get(f"A{num}VAS{letter}") or self._upper.get(f"A{num}{letter}")
        return None

    def _star(self, bare: str) -> str | None:
        m = _VESSEL_RE.match(bare) or _VAS_SUFFIX_RE.match(bare.upper())
        if m:
            return self._upper.get(f"A{m.group(1)}VAS{m.group(2) if m.lastindex == 2 else ''}")
        m = _STAR_RE.match(bare.upper())
        if m:
            num, letter = m.groups()
            return (self._upper.get(f"AB{int(num):02d}{letter}")
                    or self._upper.get(f"A{num.zfill(3)}{letter}")
                    or self._upper.get(f"A{num.zfill(3)}VAS{letter}"))
        return None

    def _name_targets(self, bare: str) -> list[str]:
        key = bare.upper().translate(SUB)
        return list(self.by_name.get(key) or self.by_name.get(key.lstrip("*"), []))

    @staticmethod
    def _prefer(pool: list[str]) -> list[str]:
        """A base sign beats its lettered variants (AB120 over AB120B)."""
        shortest = min(len(t) for t in pool)
        return sorted(t for t in pool if len(t) == shortest)

    def _by_name(self, bare: str, token_class: str | None) -> tuple[str, ...]:
        targets = self._name_targets(bare)
        if len(targets) <= 1:
            return tuple(targets)
        klasma = [t for t in targets if is_klasma(t)]
        signs = [t for t in targets if not is_klasma(t)]
        pool = klasma if token_class == "fraction" and klasma else (signs or targets)
        return tuple(self._prefer(pool))

    def _resolve_label(self, raw: str, text: str, token_class: str | None, use_lineara: bool = True) -> Resolution:
        explicit = token_class is not None
        bare = positional._bare(text).strip()
        cls = token_class or positional.token_class(text)
        if cls in ("divider", "line_break", "rule") or bare == positional.DIVIDER:
            return Resolution(raw, "divider", (), "structural")
        if cls == "numeral":
            return Resolution(raw, "numeral", (), "structural")
        if cls == "lacuna" or bare in LOST:
            return Resolution(raw, "lacuna", (), "structural")

        code = self._code(bare)
        if code:
            return Resolution(raw, "fraction" if is_klasma(code) else "sign", (code,), "code")
        code = self._star(bare)
        if code:
            return Resolution(raw, "sign", (code,), "star")

        if cls == "fraction":
            # Klasmatogram letters (A = A701, J = A707) share labels with syllabograms; in a fraction
            # context only a klasmatogram or a rendered value will do, never a syllable.
            klasma = [t for t in self._name_targets(bare) if is_klasma(t)]
            if klasma:
                return Resolution(raw, "fraction", (klasma[0],), "registry_name", ambiguous=len(klasma) > 1,
                                  alternatives=tuple((k,) for k in klasma))
            whole = self._whole_label(raw, bare, cls, use_lineara)
            if whole and whole.kind == "fraction":
                return whole
            value = positional.fraction_value(bare.lstrip("≈").strip())
            if value is not None:
                return Resolution(raw, "fraction", (), "structural", note=f"rendered value {value}")
            return Resolution(raw, "unresolved", note="fraction context: no klasmatogram")

        # Whole label before any split: SUS+SI+RE is one registry sign, not a ligature of three.
        whole = self._whole_label(raw, bare, cls, use_lineara)
        if whole:
            if not explicit:
                whole = self._flag_class_collision(whole, bare)
            return whole

        if "/" in bare:
            alt = self._alternatives(raw, bare)
            if alt:
                return alt

        if "+" in bare:
            parts = [self._resolve_label(p, _clean(p), "single_sign", use_lineara) for p in bare.split("+")]
            codes = tuple(p.codes[0] if len(p.codes) == 1 else "?" for p in parts)
            missing = [p.label for p in parts if p.kind != "lacuna" and len(p.codes) != 1]
            note = f"unresolved component(s): {', '.join(missing)}" if missing else ""
            kind = "fraction" if all(c != "?" and is_klasma(c) for c in codes) else "ligature"
            if any(p.ambiguous for p in parts):
                note = _join_notes(note, "a component label is ambiguous")
            return Resolution(raw, kind, codes, "ligature", note=note)

        value = positional.fraction_value(bare.lstrip("≈").strip())
        if value is not None:
            return Resolution(raw, "fraction", (), "structural", note=f"rendered value {value}")
        return Resolution(raw, "unresolved")

    def _whole_label(self, raw: str, bare: str, cls: str, use_lineara: bool) -> Resolution | None:
        """lineara label (label -> glyph -> registry), then registry name, for the label as one unit."""
        if use_lineara:
            for key in (raw, bare, bare.translate(_TO_SUB)):
                glyphs = self.label_glyphs.get(key)
                if not glyphs:
                    continue
                hits = [r for r in (self._from_glyph(raw, g, "lineara_label") for g in glyphs) if r]
                if hits:
                    alts = tuple(dict.fromkeys(h.codes for h in hits))     # distinct, in file order
                    return Resolution(raw, hits[0].kind, alts[0], "lineara_label", ambiguous=len(alts) > 1,
                                      alternatives=alts)
        targets = self._by_name(bare, cls)
        if targets:
            kind = "fraction" if all(is_klasma(t) for t in targets) else "sign"
            return Resolution(raw, kind, targets[:1], "registry_name", ambiguous=len(targets) > 1,
                              alternatives=tuple((t,) for t in targets))
        return None

    def _flag_class_collision(self, res: Resolution, bare: str) -> Resolution:
        """With no token class from the caller, a name shared by a syllabogram and a klasmatogram
        (A = AB08 or A701) stays ambiguous: the label alone cannot say which."""
        names = self._name_targets(bare)
        if not (any(is_klasma(t) for t in names) and any(not is_klasma(t) for t in names)):
            return res
        alts = list(res.alternatives)
        alts += [(t,) for t in self._prefer([t for t in names if is_klasma(t)]) if (t,) not in alts]
        alts += [(t,) for t in self._prefer([t for t in names if not is_klasma(t)]) if (t,) not in alts]
        return replace(res, ambiguous=len(alts) > 1, alternatives=tuple(alts))

    def _alternatives(self, raw: str, bare: str) -> Resolution | None:
        """AB131/VINA, AB21/OVISF: alternative names for one sign; the trailing letter is SigLA's variant tag."""
        first, second = bare.split("/", 1)
        base = self._code(first) or self._star(first)
        if base:
            name = self.name_of.get(base, "").upper()
            sec = second.upper()
            if name and sec.startswith(name) and len(sec) == len(name) + 1:
                variant = self._upper.get(base.upper() + sec[-1])
                if variant:
                    return Resolution(raw, "sign", (variant,), "alternatives")
        parts = [self._resolve_label(p, _clean(p), "single_sign") for p in (first, second) if p]
        found = sorted({p.codes for p in parts if p.kind == "sign" and len(p.codes) == 1})
        if not found:
            return None
        if len(found) == 2:
            a, b = found[0][0], found[1][0]
            for plain, lettered in ((a, b), (b, a)):
                if _LETTER_RE.sub("", lettered) == plain:      # a base sign and its own lettered variant
                    return Resolution(raw, "sign", (lettered,), "alternatives")
        return Resolution(raw, "sign", found[0], "alternatives", ambiguous=len(found) > 1, alternatives=tuple(found))


def _load_overrides(path: Path = OVERRIDES_PATH) -> dict[str, dict]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8")).get("overrides", {})


@lru_cache(maxsize=1)
def default_crosswalk() -> Crosswalk:
    """Registry and overrides from data/linear-a/, lineara labels from lashon-ha-kretan if present."""
    lashon = lashon_dir()
    ideograms = lashon / "ideograms.js" if lashon else None
    pairs = parse_string_pairs(ideograms, "ideogram_to_ascii") if ideograms and ideograms.exists() else []
    return Crosswalk(_load("sign-registry")["signs"], pairs, _load_overrides())
