"""Linear B administrative slot model for cross-script validation.

Parses the LiBER corpus (5,638 documents, 50,612 tokens) to build a
positional frequency model: what token types (syllabic/ideogram/number)
appear at each position within each administrative domain.

Linear B series letters encode administrative domains:
  A = personnel, C/D = livestock, E = grain, F = oil/offerings,
  G/M = commodities, J = metals, K/L/O = textiles, N = flax,
  S = weapons/armor, Ta/U = vessels, Un = offering/ritual

The core structural pattern across all domains:
  Position 0 → 65-98% syllabic (personal names or toponyms)
  Position 1+ → alternating ideograms (commodity markers) and numbers (quantities)

Used by hypothesis_test.py Phase 4 to validate Linear A candidate readings
against the Linear B administrative comparandum.
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

_IDEOGRAM_RE = re.compile(r'^[A-Z][A-Z+*0-9]*$')
_NUMBER_RE = re.compile(r'^[\d]+')
_SYLLABIC_RE = re.compile(r'^[a-z]')

_SERIES_TO_DOMAIN: dict[str, str] = {}
for _s in ['A','Aa','Ab','Ac','Ad','Ae','Ag','Ai','Ak','Al','Am','An','Ap','As','Au','Aq','Ar']:
    _SERIES_TO_DOMAIN[_s] = 'PERSONNEL'
for _s in ['B','Bg','Bk','Bo']:
    _SERIES_TO_DOMAIN[_s] = 'TEXTILE_ACCOUNT'
for _s in ['C','Ca','Cb','Cc','Ce','Cf','Cg','Ch','Cn','Co','Cp','Cr']:
    _SERIES_TO_DOMAIN[_s] = 'LIVESTOCK'
for _s in ['D','Da','Db','Dc','Dd','De','Df','Dg','Dh','Dk','Dl','Dm','Dn','Do','Dp','Dq','Dv']:
    _SERIES_TO_DOMAIN[_s] = 'LIVESTOCK'
for _s in ['E','Ea','Eb','Ed','Ef','En','Eo','Ep','Eq','Er','Es','Eu']:
    _SERIES_TO_DOMAIN[_s] = 'GRAIN'
for _s in ['F','Fa','Fg','Fh','Fn','Fo','Fp','Fr','Fs','Fu']:
    _SERIES_TO_DOMAIN[_s] = 'OIL_OFFERING'
for _s in ['G','Ga','Ge','Gg','Gm','Gn','Go','Gq','Gv']:
    _SERIES_TO_DOMAIN[_s] = 'COMMODITY'
for _s in ['J','Ja','Jn','Jo']:
    _SERIES_TO_DOMAIN[_s] = 'METAL'
for _s in ['K','L','La','Lc','Ld','Le','Ln']:
    _SERIES_TO_DOMAIN[_s] = 'TEXTILE'
for _s in ['M','Ma','Mb','Mc','Mn']:
    _SERIES_TO_DOMAIN[_s] = 'COMMODITY'
for _s in ['N','Na','Nc','Ng','Nn','Np']:
    _SERIES_TO_DOMAIN[_s] = 'FLAX'
for _s in ['O','Oa','Ob','Od','Oe','Og','Oi','On']:
    _SERIES_TO_DOMAIN[_s] = 'TEXTILE'
for _s in ['Pa','Pn','Pp']:
    _SERIES_TO_DOMAIN[_s] = 'COMMODITY'
for _s in ['Qa']:
    _SERIES_TO_DOMAIN[_s] = 'COMMODITY'
for _s in ['R','Ra']:
    _SERIES_TO_DOMAIN[_s] = 'COMMODITY'
for _s in ['S','Sa','Sc','Sd','Se','Sf','Sg','Sh','Si','Sk','Sl','Sm','So','Sp','Sq']:
    _SERIES_TO_DOMAIN[_s] = 'WEAPON_ARMOR'
for _s in ['Ta','Tn']:
    _SERIES_TO_DOMAIN[_s] = 'VESSEL'
for _s in ['U','Ua','Ub','Uc','Ud','Ue','Uf','Uh','Ui']:
    _SERIES_TO_DOMAIN[_s] = 'VESSEL'
for _s in ['Un']:
    _SERIES_TO_DOMAIN[_s] = 'OFFERING_RITUAL'
for _s in ['V','Va','Vc','Vd','Ve','Vf','Vn','Vs']:
    _SERIES_TO_DOMAIN[_s] = 'MISCELLANEOUS'
for _s in ['W','Wa','Wb','Wh','Wm','Wn','Wo','Wp','Wr','Ws','Wt','Wv']:
    _SERIES_TO_DOMAIN[_s] = 'SEALING'

SKIP_SERIES = {'X', 'Xa', 'Xd', 'Xe', 'Xf', 'Xg', 'Xn', 'Z', 'Zg', 'Zh'}

# Map Linear A semantic categories to expected Linear B slot behavior
LA_ROLE_TO_LB_SLOT = {
    "PERSONAL_NAME": "SYLLABIC",
    "TOPONYM": "SYLLABIC",
    "NAME_TITLE": "SYLLABIC",
    "CULTIC_RECIPIENT": "SYLLABIC",
    "COMMODITY_LABEL": "IDEOGRAM",
    "QUANTITY_OR_MEASURE": "NUMBER",
    "ACCOUNTING_PARTICLE": "SYLLABIC",
    "ACCOUNTING_TOTAL": "SYLLABIC",
    "VERB_ACTION": "SYLLABIC",
    "VESSEL_MARK": "SYLLABIC",
}

# Map Linear A formula families to closest Linear B administrative domains
LA_FAMILY_TO_LB_DOMAIN = {
    "offering_formula": "OIL_OFFERING",
    "commodity_accounting_row": "GRAIN",
    "accounting_or_measure": "GRAIN",
    "accounting_total": "GRAIN",
    "name_list": "PERSONNEL",
    "vessel_inscription": "VESSEL",
    "ritual_dedication": "OFFERING_RITUAL",
}


def _classify_token(tok: str) -> str | None:
    clean = tok.strip('[].,;?\' ')
    if not clean or clean == 'vacat':
        return None
    if _IDEOGRAM_RE.match(clean):
        return 'IDEOGRAM'
    if _NUMBER_RE.match(clean):
        return 'NUMBER'
    if _SYLLABIC_RE.match(clean):
        return 'SYLLABIC'
    return 'OTHER'


def build_slot_model(corpus_path: Path) -> dict[str, dict]:
    """Build positional frequency model from LiBER corpus.

    Args:
        corpus_path: Path to liber_linear_b_documents.jsonl

    Returns:
        {domain: {position_str: {"total": int, "distribution": {type: prob}}}}
    """
    model: dict[str, dict[int, Counter]] = defaultdict(lambda: defaultdict(Counter))

    with open(corpus_path) as f:
        for line in f:
            doc = json.loads(line)
            raw_series = doc.get('series', '?')
            series_base = re.sub(r'\(\d+\)', '', raw_series).strip()
            if series_base in SKIP_SERIES:
                continue

            domain = _SERIES_TO_DOMAIN.get(series_base, 'UNKNOWN')

            for ln in doc.get('lines', []):
                meaningful = []
                for tok in ln.get('tokens', []):
                    tc = _classify_token(tok)
                    if tc:
                        meaningful.append(tc)

                for pos, tc in enumerate(meaningful[:8]):
                    model[domain][pos][tc] += 1

    output: dict[str, dict] = {}
    for domain, positions in model.items():
        pos_data = {}
        for pos in sorted(positions.keys()):
            total = sum(positions[pos].values())
            dist = {tc: round(c / total, 4) for tc, c in positions[pos].most_common()}
            pos_data[str(pos)] = {"total": total, "distribution": dist}
        output[domain] = pos_data

    return output


def validate_candidate(
    word: str,
    la_role: str,
    la_formula_family: str | None,
    la_position: int | None,
    slot_model: dict[str, dict],
) -> dict[str, Any]:
    """Check if a Linear A candidate's role is structurally consistent with Linear B.

    Compares the candidate's semantic role and formula position against the
    Linear B slot model to determine whether the same type of word appears
    in the corresponding position in Linear B tablets.

    Args:
        word: Linear A word
        la_role: Semantic role (PERSONAL_NAME, TOPONYM, COMMODITY_LABEL, etc.)
        la_formula_family: Linear A formula family (offering_formula, etc.) or None
        la_position: Position within the formula (0-indexed) or None
        slot_model: Output of build_slot_model()

    Returns:
        {
            "word": str,
            "la_role": str,
            "expected_lb_token_type": str,
            "lb_domain": str,
            "lb_position": int,
            "lb_rate_at_position": float,
            "lb_background_rate": float,
            "verdict": "CONVERGENT" | "NEUTRAL" | "DIVERGENT" | "INSUFFICIENT_DATA",
            "explanation": str,
        }
    """
    expected_type = LA_ROLE_TO_LB_SLOT.get(la_role)
    if expected_type is None:
        return {
            "word": word,
            "la_role": la_role,
            "expected_lb_token_type": None,
            "lb_domain": None,
            "lb_position": None,
            "lb_rate_at_position": None,
            "lb_background_rate": None,
            "verdict": "INSUFFICIENT_DATA",
            "explanation": f"No Linear B token type mapping for role {la_role}",
        }

    lb_domain = LA_FAMILY_TO_LB_DOMAIN.get(la_formula_family or "", "GRAIN")
    lb_pos = la_position if la_position is not None else 0

    domain_data = slot_model.get(lb_domain, {})
    pos_data = domain_data.get(str(lb_pos), {})
    dist = pos_data.get("distribution", {})
    total = pos_data.get("total", 0)

    if total < 20:
        return {
            "word": word,
            "la_role": la_role,
            "expected_lb_token_type": expected_type,
            "lb_domain": lb_domain,
            "lb_position": lb_pos,
            "lb_rate_at_position": None,
            "lb_background_rate": None,
            "verdict": "INSUFFICIENT_DATA",
            "explanation": f"Only {total} observations at {lb_domain} pos {lb_pos}",
        }

    rate = dist.get(expected_type, 0.0)

    bg_total = 0
    bg_hits = 0
    for d_positions in slot_model.values():
        for p_data in d_positions.values():
            p_dist = p_data.get("distribution", {})
            p_total = p_data.get("total", 0)
            bg_total += p_total
            bg_hits += round(p_dist.get(expected_type, 0) * p_total)
    bg_rate = bg_hits / bg_total if bg_total > 0 else 0

    # Strength depends on whether the position is discriminating:
    # Position 0 is 65-98% SYLLABIC across all domains — weak test for name/toponym
    # Position 1+ drops to 20-45% SYLLABIC — much more discriminating
    discriminating = (lb_pos >= 1) or (expected_type != "SYLLABIC")

    if rate >= 0.60:
        verdict = "CONVERGENT"
        strength = "STRONG" if discriminating else "WEAK"
        explanation = f"{expected_type} at {lb_domain} pos {lb_pos}: {rate:.0%} (bg={bg_rate:.0%}) — {'discriminating' if discriminating else 'expected at pos 0'}"
    elif rate >= 0.30:
        verdict = "NEUTRAL"
        strength = "MODERATE" if discriminating else "WEAK"
        explanation = f"{expected_type} at {lb_domain} pos {lb_pos}: {rate:.0%} (bg={bg_rate:.0%}) — present but not dominant"
    elif rate >= 0.05:
        verdict = "NEUTRAL"
        strength = "WEAK"
        explanation = f"{expected_type} at {lb_domain} pos {lb_pos}: {rate:.0%} (bg={bg_rate:.0%}) — minor presence"
    else:
        verdict = "DIVERGENT"
        strength = "STRONG"
        explanation = f"{expected_type} at {lb_domain} pos {lb_pos}: {rate:.0%} (bg={bg_rate:.0%}) — rarely appears here"

    return {
        "word": word,
        "la_role": la_role,
        "expected_lb_token_type": expected_type,
        "lb_domain": lb_domain,
        "lb_position": lb_pos,
        "lb_rate_at_position": round(rate, 4),
        "lb_background_rate": round(bg_rate, 4),
        "verdict": verdict,
        "strength": strength,
        "explanation": explanation,
    }


_cached_model: dict[str, dict] | None = None
_cached_path: Path | None = None


def load_slot_model(corpus_path: Path) -> dict[str, dict]:
    """Load or build the slot model, with caching."""
    global _cached_model, _cached_path
    resolved = corpus_path.resolve()
    if _cached_model is not None and _cached_path == resolved:
        return _cached_model
    _cached_model = build_slot_model(resolved)
    _cached_path = resolved
    return _cached_model
