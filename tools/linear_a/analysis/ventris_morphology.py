#!/usr/bin/env python3
"""Morphological feature analysis for Linear A.

Detects six Semitic morphological features: mimation, A-prefix verbs, -NA
demonstrative, feminine -TI/-TU case alternation, JA-/A- prefix alternation,
and construct state candidates. Luwian and Egyptian pattern detectors are
also available.

Usage:
    uv run python tools/linear_a/analysis/ventris_morphology.py
    uv run python tools/linear_a/analysis/ventris_morphology.py --prefix-pairs --verbose
    uv run python tools/linear_a/analysis/ventris_morphology.py --luwian-all --json
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    __package__ = "tools.linear_a.analysis"

from ...core.corpus_utils import extract_words, load_corpus
from ...paths import NotInCheckout


def detect_mimation(words: list[dict]) -> list[dict]:
    """Find -MA/-MU endings that may preserve archaic Semitic mimation.

    Mimation (-m on nouns) is archaic — preserved in Old Babylonian and
    Ugaritic, lost in later Canaanite. Its presence in Linear A would
    date the language to an early NWS stratum.
    """
    word_set = {w["word"] for w in words}
    word_sites = defaultdict(set)
    for w in words:
        word_sites[w["word"]].add(w["site"])

    hits = []
    seen = set()
    for w in words:
        signs = w["signs"]
        if len(signs) < 3:
            continue
        final = signs[-1]
        if final not in ("MA", "MU"):
            continue
        stem = "-".join(signs[:-1])
        key = (stem, final)
        if key in seen:
            continue
        seen.add(key)

        bare_exists = stem in word_set
        other_endings = []
        for ending in ("U", "A", "I", "TE", "TI", "TU", "NA", "NE"):
            candidate = f"{stem}-{ending}"
            if candidate in word_set:
                other_endings.append(candidate)

        hits.append({
            "word": w["word"],
            "stem": stem,
            "ending": final,
            "bare_stem_exists": bare_exists,
            "other_forms": other_endings,
            "sites": sorted(word_sites[w["word"]]),
            "feature": "mimation",
        })

    return hits


def detect_a_prefix_verbs(words: list[dict]) -> list[dict]:
    """Find A-prefix words and classify as potential aqtul (1cs) forms.

    In NWS, the A- prefix marks 1cs imperfective (aqtul). Cross-reference
    with JA- variants to identify yaqtul/aqtul alternation.
    """
    word_set = {w["word"] for w in words}
    word_sites = defaultdict(set)
    for w in words:
        word_sites[w["word"]].add(w["site"])

    hits = []
    seen = set()
    for w in words:
        signs = w["signs"]
        if len(signs) < 2 or signs[0] != "A":
            continue
        if w["word"] in seen:
            continue
        seen.add(w["word"])

        remainder = "-".join(signs[1:])
        ja_variant = f"JA-{remainder}"
        ja_exists = ja_variant in word_set

        hits.append({
            "word": w["word"],
            "remainder": remainder,
            "ja_variant": ja_variant if ja_exists else None,
            "ja_exists": ja_exists,
            "sites": sorted(word_sites[w["word"]]),
            "feature": "a_prefix",
        })

    return hits


def detect_demonstrative_na(words: list[dict]) -> list[dict]:
    """Find -NA endings and distinguish demonstrative from other uses.

    The Semitic demonstrative suffix -na ("this") is attested in Ugaritic.
    If the bare stem also exists, -NA is more likely demonstrative than
    part of the root.
    """
    word_set = {w["word"] for w in words}
    word_sites = defaultdict(set)
    for w in words:
        word_sites[w["word"]].add(w["site"])

    hits = []
    seen = set()
    for w in words:
        signs = w["signs"]
        if len(signs) < 2 or signs[-1] != "NA":
            continue
        if w["word"] in seen:
            continue
        seen.add(w["word"])

        stem = "-".join(signs[:-1])
        bare_exists = stem in word_set

        hits.append({
            "word": w["word"],
            "stem": stem,
            "bare_stem_exists": bare_exists,
            "likely_demonstrative": bare_exists,
            "sites": sorted(word_sites[w["word"]]),
            "feature": "demonstrative_na",
        })

    return hits


def detect_feminine_case_alternation(words: list[dict]) -> list[dict]:
    """Find -TI/-TU pairs on the same stem.

    If both STEM-TI and STEM-TU exist, this may preserve genitive (-ti)
    vs. nominative (-tu) case marking on feminine nouns — a distinction
    lost in later Canaanite but preserved in Ugaritic.
    """
    word_set = {w["word"] for w in words}
    word_sites = defaultdict(set)
    for w in words:
        word_sites[w["word"]].add(w["site"])

    stems_with_ti = set()
    stems_with_tu = set()
    for w in words:
        signs = w["signs"]
        if len(signs) < 2:
            continue
        stem = "-".join(signs[:-1])
        if signs[-1] == "TI":
            stems_with_ti.add(stem)
        elif signs[-1] == "TU":
            stems_with_tu.add(stem)

    shared = stems_with_ti & stems_with_tu
    hits = []
    for stem in sorted(shared):
        ti_word = f"{stem}-TI"
        tu_word = f"{stem}-TU"
        te_word = f"{stem}-TE"
        hits.append({
            "stem": stem,
            "ti_form": ti_word,
            "tu_form": tu_word,
            "te_exists": te_word in word_set,
            "ti_sites": sorted(word_sites.get(ti_word, set())),
            "tu_sites": sorted(word_sites.get(tu_word, set())),
            "feature": "feminine_case_alternation",
        })

    return hits


def detect_prefix_alternation(words: list[dict]) -> list[dict]:
    """Find JA-STEM / A-STEM pairs (yaqtul/aqtul alternation).

    The JA-SA-SA-RA-ME / A-SA-SA-RA-ME pair is the anchor case. If both
    JA-X and A-X exist for the same stem X, this suggests a productive
    yaqtul (3ms) / aqtul (1cs) verbal paradigm.
    """
    word_sites = defaultdict(set)
    for w in words:
        word_sites[w["word"]].add(w["site"])

    ja_stems = {}
    a_stems = {}
    for w in words:
        signs = w["signs"]
        if len(signs) < 2:
            continue
        remainder = "-".join(signs[1:])
        if signs[0] == "JA":
            ja_stems[remainder] = w["word"]
        elif signs[0] == "A":
            a_stems[remainder] = w["word"]

    shared = set(ja_stems.keys()) & set(a_stems.keys())
    hits = []
    for remainder in sorted(shared):
        ja_word = ja_stems[remainder]
        a_word = a_stems[remainder]
        hits.append({
            "stem": remainder,
            "ja_form": ja_word,
            "a_form": a_word,
            "ja_sites": sorted(word_sites.get(ja_word, set())),
            "a_sites": sorted(word_sites.get(a_word, set())),
            "feature": "prefix_alternation",
        })

    return hits


def detect_construct_state(words: list[dict]) -> list[dict]:
    """Find words appearing in both full (STEM-U/A/I) and bare (STEM) forms.

    In Semitic, the construct state (bound form) drops the case vowel:
    *malku (abs.) → *malk- (cstr.) "king of..." If STEM-U and STEM both
    exist, STEM may be a construct form.
    """
    word_set = {w["word"] for w in words}
    word_counter = Counter(w["word"] for w in words)
    word_sites = defaultdict(set)
    for w in words:
        word_sites[w["word"]].add(w["site"])

    hits = []
    checked = set()
    for w in words:
        signs = w["signs"]
        if len(signs) < 3:
            continue
        final = signs[-1]
        if final not in ("U", "A", "I"):
            continue
        stem = "-".join(signs[:-1])
        if stem in checked:
            continue
        checked.add(stem)

        if stem in word_set:
            case_forms = {}
            for cv in ("U", "A", "I"):
                candidate = f"{stem}-{cv}"
                if candidate in word_set:
                    case_forms[cv] = {
                        "word": candidate,
                        "count": word_counter[candidate],
                    }

            hits.append({
                "stem": stem,
                "bare_count": word_counter[stem],
                "bare_sites": sorted(word_sites[stem]),
                "case_forms": case_forms,
                "feature": "construct_state",
            })

    hits.sort(key=lambda x: -x["bare_count"])
    return hits


# --- Luwian morphological detectors ---

LUWIAN_ASSA_ENDINGS = (("A", "SA"), ("A", "SI"), ("A", "SA", "RA"))
LUWIAN_WANNI_ENDINGS = (("WA", "NI"), ("WA", "NA"))
LUWIAN_ZITI_ENDINGS = (("ZI", "TI"), ("SI", "TI"))
LUWIAN_SUFFIX_ENDINGS = (("A", "TI"), ("A", "DI"), ("NI", "ZI"), ("AN", "TI"), ("U", "NA"))
LUWIAN_WACKERNAGEL = ("WA", "MU", "DU", "AN", "MI", "DI")


def _match_sign_ending(
    signs: list[str], ending: tuple[str, ...],
) -> bool:
    """Check if a sign list ends with the given ending tuple (sign-boundary safe)."""
    elen = len(ending)
    if len(signs) <= elen:
        return False
    return tuple(signs[-elen:]) == ending


def detect_luwian_assa_toponym(words: list[dict]) -> list[dict]:
    """Find -A-SA / -A-SI / -A-SA-RA endings (Luwian place-name suffix *-assa*)."""
    word_sites = defaultdict(set)
    for w in words:
        word_sites[w["word"]].add(w["site"])

    hits = []
    seen = set()
    for w in words:
        if w["word"] in seen:
            continue
        for ending in LUWIAN_ASSA_ENDINGS:
            if _match_sign_ending(w["signs"], ending):
                seen.add(w["word"])
                stem = "-".join(w["signs"][:-len(ending)])
                hits.append({
                    "word": w["word"],
                    "stem": stem,
                    "ending": "-".join(ending),
                    "sites": sorted(word_sites[w["word"]]),
                    "feature": "luwian_assa_toponym",
                })
                break

    return hits


def detect_luwian_wanni_ethnic(words: list[dict]) -> list[dict]:
    """Find -WA-NI / -WA-NA endings (Luwian ethnic *-wanni-*)."""
    word_sites = defaultdict(set)
    for w in words:
        word_sites[w["word"]].add(w["site"])

    hits = []
    seen = set()
    for w in words:
        if w["word"] in seen:
            continue
        for ending in LUWIAN_WANNI_ENDINGS:
            if _match_sign_ending(w["signs"], ending):
                seen.add(w["word"])
                stem = "-".join(w["signs"][:-len(ending)])
                hits.append({
                    "word": w["word"],
                    "stem": stem,
                    "ending": "-".join(ending),
                    "sites": sorted(word_sites[w["word"]]),
                    "feature": "luwian_wanni_ethnic",
                })
                break

    return hits


def detect_luwian_ziti_theophoric(words: list[dict]) -> list[dict]:
    """Find -ZI-TI / -SI-TI endings (Luwian theophoric *-ziti*)."""
    word_sites = defaultdict(set)
    for w in words:
        word_sites[w["word"]].add(w["site"])

    hits = []
    seen = set()
    for w in words:
        if w["word"] in seen:
            continue
        for ending in LUWIAN_ZITI_ENDINGS:
            if _match_sign_ending(w["signs"], ending):
                seen.add(w["word"])
                stem = "-".join(w["signs"][:-len(ending)])
                hits.append({
                    "word": w["word"],
                    "stem": stem,
                    "ending": "-".join(ending),
                    "sites": sorted(word_sites[w["word"]]),
                    "feature": "luwian_ziti_theophoric",
                })
                break

    return hits


def detect_luwian_i_mutation(words: list[dict]) -> list[dict]:
    """Find STEM-I where STEM-A also exists (Luwian i-mutation: a→i shift)."""
    word_set = {w["word"] for w in words}
    word_sites = defaultdict(set)
    for w in words:
        word_sites[w["word"]].add(w["site"])

    hits = []
    checked = set()
    for w in words:
        signs = w["signs"]
        if len(signs) < 2 or signs[-1] != "I":
            continue
        stem = "-".join(signs[:-1])
        if stem in checked:
            continue
        checked.add(stem)

        a_form = f"{stem}-A"
        if a_form in word_set:
            hits.append({
                "stem": stem,
                "i_form": w["word"],
                "a_form": a_form,
                "i_sites": sorted(word_sites[w["word"]]),
                "a_sites": sorted(word_sites[a_form]),
                "feature": "luwian_i_mutation",
            })

    return hits


def detect_luwian_wackernagel(words: list[dict]) -> list[dict]:
    """Find Wackernagel-position clitics (WA/MU/DU/AN/MI/DI in 2nd sign position)."""
    word_sites = defaultdict(set)
    for w in words:
        word_sites[w["word"]].add(w["site"])

    hits = []
    seen = set()
    for w in words:
        signs = w["signs"]
        if len(signs) < 3 or w["word"] in seen:
            continue
        if signs[1] in LUWIAN_WACKERNAGEL:
            seen.add(w["word"])
            hits.append({
                "word": w["word"],
                "clitic": signs[1],
                "position": 2,
                "signs": signs,
                "sites": sorted(word_sites[w["word"]]),
                "feature": "luwian_wackernagel",
            })

    return hits


def detect_luwian_suffix_cluster(words: list[dict]) -> list[dict]:
    """Find Luwian derivational suffix clusters (-A-TI, -A-DI, -NI-ZI, etc.)."""
    word_sites = defaultdict(set)
    for w in words:
        word_sites[w["word"]].add(w["site"])

    hits = []
    seen = set()
    for w in words:
        if w["word"] in seen:
            continue
        for ending in LUWIAN_SUFFIX_ENDINGS:
            if _match_sign_ending(w["signs"], ending):
                seen.add(w["word"])
                stem = "-".join(w["signs"][:-len(ending)])
                hits.append({
                    "word": w["word"],
                    "stem": stem,
                    "ending": "-".join(ending),
                    "sites": sorted(word_sites[w["word"]]),
                    "feature": "luwian_suffix_cluster",
                })
                break

    return hits


# --- Egyptian morphological detectors ---

EGYPTIAN_RA_ENDINGS = (("RE",),)
EGYPTIAN_AMUN_ENDINGS = (("MU", "NI"), ("ME", "NI"))
EGYPTIAN_PTAH_PATTERN = ("PA", "TA")
EGYPTIAN_THOTH_PATTERN = ("DU", "TI")
EGYPTIAN_HATHOR_ENDINGS = (("HA", "TU"),)
EGYPTIAN_NSWT_PATTERNS = (("NI", "SU"), ("NE", "SU"))


def _match_sign_beginning(
    signs: list[str], beginning: tuple[str, ...],
) -> bool:
    """Check if a sign list starts with the given beginning tuple (sign-boundary safe)."""
    blen = len(beginning)
    if len(signs) <= blen:
        return False
    return tuple(signs[:blen]) == beginning


def detect_egyptian_ra_theophoric(words: list[dict]) -> list[dict]:
    """Find -RE endings with ≥3 signs (Egyptian Ra-compound names)."""
    word_sites = defaultdict(set)
    for w in words:
        word_sites[w["word"]].add(w["site"])

    hits = []
    seen = set()
    for w in words:
        if w["word"] in seen:
            continue
        signs = w["signs"]
        if len(signs) >= 3:
            for ending in EGYPTIAN_RA_ENDINGS:
                if _match_sign_ending(signs, ending):
                    seen.add(w["word"])
                    stem = "-".join(signs[:-len(ending)])
                    hits.append({
                        "word": w["word"],
                        "stem": stem,
                        "ending": "-".join(ending),
                        "sites": sorted(word_sites[w["word"]]),
                        "feature": "egyptian_ra_theophoric",
                    })
                    break

    return hits


def detect_egyptian_amun_theophoric(words: list[dict]) -> list[dict]:
    """Find -MU-NI / -ME-NI endings (Egyptian Amun-compound names, jmn)."""
    word_sites = defaultdict(set)
    for w in words:
        word_sites[w["word"]].add(w["site"])

    hits = []
    seen = set()
    for w in words:
        if w["word"] in seen:
            continue
        for ending in EGYPTIAN_AMUN_ENDINGS:
            if _match_sign_ending(w["signs"], ending):
                seen.add(w["word"])
                stem = "-".join(w["signs"][:-len(ending)])
                hits.append({
                    "word": w["word"],
                    "stem": stem,
                    "ending": "-".join(ending),
                    "sites": sorted(word_sites[w["word"]]),
                    "feature": "egyptian_amun_theophoric",
                })
                break

    return hits


def detect_egyptian_ptah_theophoric(words: list[dict]) -> list[dict]:
    """Find PA-TA at beginning or end (Egyptian Ptah-compound names, ptḥ)."""
    word_sites = defaultdict(set)
    for w in words:
        word_sites[w["word"]].add(w["site"])

    hits = []
    seen = set()
    for w in words:
        if w["word"] in seen:
            continue
        signs = w["signs"]
        matched = False
        if _match_sign_ending(signs, EGYPTIAN_PTAH_PATTERN):
            matched = True
            stem = "-".join(signs[:-len(EGYPTIAN_PTAH_PATTERN)])
            position = "suffix"
        elif _match_sign_beginning(signs, EGYPTIAN_PTAH_PATTERN):
            matched = True
            stem = "-".join(signs[len(EGYPTIAN_PTAH_PATTERN):])
            position = "prefix"
        if matched:
            seen.add(w["word"])
            hits.append({
                "word": w["word"],
                "stem": stem,
                "ending": "-".join(EGYPTIAN_PTAH_PATTERN),
                "position": position,
                "sites": sorted(word_sites[w["word"]]),
                "feature": "egyptian_ptah_theophoric",
            })

    return hits


def detect_egyptian_thoth_theophoric(words: list[dict]) -> list[dict]:
    """Find DU-TI at beginning or end (Egyptian Thoth-compound names, ḏḥwtj)."""
    word_sites = defaultdict(set)
    for w in words:
        word_sites[w["word"]].add(w["site"])

    hits = []
    seen = set()
    for w in words:
        if w["word"] in seen:
            continue
        signs = w["signs"]
        matched = False
        if _match_sign_ending(signs, EGYPTIAN_THOTH_PATTERN):
            matched = True
            stem = "-".join(signs[:-len(EGYPTIAN_THOTH_PATTERN)])
            position = "suffix"
        elif _match_sign_beginning(signs, EGYPTIAN_THOTH_PATTERN):
            matched = True
            stem = "-".join(signs[len(EGYPTIAN_THOTH_PATTERN):])
            position = "prefix"
        if matched:
            seen.add(w["word"])
            hits.append({
                "word": w["word"],
                "stem": stem,
                "ending": "-".join(EGYPTIAN_THOTH_PATTERN),
                "position": position,
                "sites": sorted(word_sites[w["word"]]),
                "feature": "egyptian_thoth_theophoric",
            })

    return hits


def detect_egyptian_hathor_theophoric(words: list[dict]) -> list[dict]:
    """Find -HA-TU endings (Egyptian Hathor-compound names, ḥwt-ḥr)."""
    word_sites = defaultdict(set)
    for w in words:
        word_sites[w["word"]].add(w["site"])

    hits = []
    seen = set()
    for w in words:
        if w["word"] in seen:
            continue
        for ending in EGYPTIAN_HATHOR_ENDINGS:
            if _match_sign_ending(w["signs"], ending):
                seen.add(w["word"])
                stem = "-".join(w["signs"][:-len(ending)])
                hits.append({
                    "word": w["word"],
                    "stem": stem,
                    "ending": "-".join(ending),
                    "sites": sorted(word_sites[w["word"]]),
                    "feature": "egyptian_hathor_theophoric",
                })
                break

    return hits


def detect_egyptian_nswt_royal(words: list[dict]) -> list[dict]:
    """Find NI-SU / NE-SU substring (Egyptian royal title nswt)."""
    word_sites = defaultdict(set)
    for w in words:
        word_sites[w["word"]].add(w["site"])

    hits = []
    seen = set()
    for w in words:
        if w["word"] in seen:
            continue
        signs = w["signs"]
        if len(signs) < 3:
            continue
        for pattern in EGYPTIAN_NSWT_PATTERNS:
            plen = len(pattern)
            for i in range(len(signs) - plen + 1):
                if tuple(signs[i:i + plen]) == pattern:
                    seen.add(w["word"])
                    hits.append({
                        "word": w["word"],
                        "pattern": "-".join(pattern),
                        "position": i,
                        "sites": sorted(word_sites[w["word"]]),
                        "feature": "egyptian_nswt_royal",
                    })
                    break
            if w["word"] in seen:
                break

    return hits


def format_report(results: dict, top_n: int | None = 20) -> str:
    lines = []
    lines.append("Ventris Engine — Morphological Feature Analysis")
    lines.append("=" * 65)
    lines.append("")

    def cap(seq: list) -> list:
        return seq if top_n is None else seq[:top_n]

    for feature_name, feature_data in results["features"].items():
        hits = feature_data["hits"]
        lines.append(f"## {feature_data['label']} ({len(hits)} attestations)")
        lines.append("-" * 50)

        if feature_name == "mimation":
            for h in cap(hits):
                other = ", ".join(h["other_forms"][:3]) if h["other_forms"] else "—"
                bare = "✓" if h["bare_stem_exists"] else "✗"
                lines.append(
                    f"  {h['word']:<25} stem={h['stem']:<15} "
                    f"bare={bare}  other=[{other}]  {', '.join(h['sites'][:2])}"
                )

        elif feature_name == "a_prefix":
            paired = [h for h in hits if h["ja_exists"]]
            unpaired = [h for h in hits if not h["ja_exists"]]
            if paired:
                lines.append(f"  With JA- variant ({len(paired)}):")
                for h in cap(paired):
                    lines.append(
                        f"    {h['word']:<25} ↔ {h['ja_variant']:<25} {', '.join(h['sites'][:2])}"
                    )
            lines.append(f"  Without JA- variant: {len(unpaired)}")

        elif feature_name == "demonstrative_na":
            likely = [h for h in hits if h["likely_demonstrative"]]
            lines.append(f"  Likely demonstrative (bare stem exists): {len(likely)}")
            for h in cap(likely):
                lines.append(
                    f"    {h['word']:<25} stem={h['stem']:<15} {', '.join(h['sites'][:2])}"
                )

        elif feature_name == "feminine_case_alternation":
            for h in cap(hits):
                te = " +TE" if h["te_exists"] else ""
                lines.append(
                    f"  {h['stem']:<20} → {h['ti_form']} / {h['tu_form']}{te}"
                )

        elif feature_name == "prefix_alternation":
            for h in cap(hits):
                lines.append(
                    f"  {h['ja_form']:<25} ↔ {h['a_form']:<25} "
                    f"JA@{', '.join(h['ja_sites'][:2])}  A@{', '.join(h['a_sites'][:2])}"
                )

        elif feature_name == "construct_state":
            for h in cap(hits):
                cases = " ".join(
                    f"{cv}={info['word']}(×{info['count']})"
                    for cv, info in sorted(h["case_forms"].items())
                )
                lines.append(
                    f"  {h['stem']:<20} bare(×{h['bare_count']})  {cases}  "
                    f"{', '.join(h['bare_sites'][:2])}"
                )

        elif feature_name in ("luwian_assa_toponym", "luwian_wanni_ethnic",
                              "luwian_ziti_theophoric", "luwian_suffix_cluster"):
            for h in cap(hits):
                lines.append(
                    f"  {h['word']:<25} stem={h['stem']:<15} "
                    f"ending={h['ending']}  {', '.join(h['sites'][:2])}"
                )

        elif feature_name == "luwian_i_mutation":
            for h in cap(hits):
                lines.append(
                    f"  {h['stem']:<20} → {h['i_form']} / {h['a_form']}  "
                    f"I@{', '.join(h['i_sites'][:2])}  A@{', '.join(h['a_sites'][:2])}"
                )

        elif feature_name == "luwian_wackernagel":
            for h in cap(hits):
                lines.append(
                    f"  {h['word']:<25} clitic={h['clitic']} pos=2  "
                    f"{', '.join(h['sites'][:2])}"
                )

        elif feature_name in ("egyptian_ra_theophoric", "egyptian_amun_theophoric",
                              "egyptian_hathor_theophoric"):
            for h in cap(hits):
                lines.append(
                    f"  {h['word']:<25} stem={h['stem']:<15} "
                    f"ending={h['ending']}  {', '.join(h['sites'][:2])}"
                )

        elif feature_name in ("egyptian_ptah_theophoric", "egyptian_thoth_theophoric"):
            for h in cap(hits):
                pos = h.get("position", "suffix")
                lines.append(
                    f"  {h['word']:<25} stem={h['stem']:<15} "
                    f"ending={h['ending']} ({pos})  {', '.join(h['sites'][:2])}"
                )

        elif feature_name == "egyptian_nswt_royal":
            for h in cap(hits):
                lines.append(
                    f"  {h['word']:<25} pattern={h['pattern']} pos={h['position']}  "
                    f"{', '.join(h['sites'][:2])}"
                )

        lines.append("")

    summary = results["summary"]
    lines.append("Summary")
    lines.append("-" * 50)
    for k, v in summary.items():
        lines.append(f"  {k:<30} {v}")

    return "\n".join(lines)


def main() -> int:
    """Exit 2 with the file's name when a data file is not in the checkout."""
    try:
        _run()
    except NotInCheckout as e:
        print(f"stopped: {e}", file=sys.stderr)
        return 2
    return 0


def _run():
    parser = argparse.ArgumentParser(
        description="Morphological feature analysis for Linear A"
    )
    semitic = parser.add_argument_group("Semitic detectors")
    semitic.add_argument("--mimation", action="store_true", help="Mimation only")
    semitic.add_argument("--a-prefix", action="store_true", help="A-prefix verbs only")
    semitic.add_argument("--demonstrative", action="store_true", help="Demonstrative -NA only")
    semitic.add_argument("--feminine-case", action="store_true", help="Feminine -TI/-TU alternation only")
    semitic.add_argument("--prefix-pairs", action="store_true", help="JA-/A- prefix pairs only")
    semitic.add_argument("--construct", action="store_true", help="Construct state candidates only")

    luwian = parser.add_argument_group("Luwian detectors")
    luwian.add_argument("--luwian-assa", action="store_true", help="Luwian -assa toponym suffix only")
    luwian.add_argument("--luwian-wanni", action="store_true", help="Luwian -wanni ethnic suffix only")
    luwian.add_argument("--luwian-ziti", action="store_true", help="Luwian -ziti theophoric only")
    luwian.add_argument("--luwian-imut", action="store_true", help="Luwian i-mutation pairs only")
    luwian.add_argument("--luwian-wack", action="store_true", help="Luwian Wackernagel clitics only")
    luwian.add_argument("--luwian-suffix", action="store_true", help="Luwian suffix clusters only")
    luwian.add_argument("--luwian-all", action="store_true", help="All Luwian detectors")

    egyptian = parser.add_argument_group("Egyptian detectors")
    egyptian.add_argument("--egyptian-ra", action="store_true", help="Egyptian Ra-theophoric only")
    egyptian.add_argument("--egyptian-amun", action="store_true", help="Egyptian Amun-theophoric only")
    egyptian.add_argument("--egyptian-ptah", action="store_true", help="Egyptian Ptah-theophoric only")
    egyptian.add_argument("--egyptian-thoth", action="store_true", help="Egyptian Thoth-theophoric only")
    egyptian.add_argument("--egyptian-hathor", action="store_true", help="Egyptian Hathor-theophoric only")
    egyptian.add_argument("--egyptian-nswt", action="store_true", help="Egyptian royal nswt pattern only")
    egyptian.add_argument("--egyptian-all", action="store_true", help="All Egyptian detectors")

    parser.add_argument("--top", type=int, default=20, help="Max hits per feature (default: 20)")
    parser.add_argument("--verbose", action="store_true", help="Show all hits (no --top limit)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()
    if args.verbose:
        args.top = None

    corpus = load_corpus()
    words = extract_words(corpus)

    filters = {
        "mimation": args.mimation,
        "a_prefix": args.a_prefix,
        "demonstrative_na": args.demonstrative,
        "feminine_case_alternation": args.feminine_case,
        "prefix_alternation": args.prefix_pairs,
        "construct_state": args.construct,
        "luwian_assa_toponym": args.luwian_assa or args.luwian_all,
        "luwian_wanni_ethnic": args.luwian_wanni or args.luwian_all,
        "luwian_ziti_theophoric": args.luwian_ziti or args.luwian_all,
        "luwian_i_mutation": args.luwian_imut or args.luwian_all,
        "luwian_wackernagel": args.luwian_wack or args.luwian_all,
        "luwian_suffix_cluster": args.luwian_suffix or args.luwian_all,
        "egyptian_ra_theophoric": args.egyptian_ra or args.egyptian_all,
        "egyptian_amun_theophoric": args.egyptian_amun or args.egyptian_all,
        "egyptian_ptah_theophoric": args.egyptian_ptah or args.egyptian_all,
        "egyptian_thoth_theophoric": args.egyptian_thoth or args.egyptian_all,
        "egyptian_hathor_theophoric": args.egyptian_hathor or args.egyptian_all,
        "egyptian_nswt_royal": args.egyptian_nswt or args.egyptian_all,
    }
    run_all = not any(filters.values())

    detectors = {
        "mimation": (detect_mimation, "Mimation (-MA/-MU endings)"),
        "a_prefix": (detect_a_prefix_verbs, "A-Prefix Verbs (aqtul class)"),
        "demonstrative_na": (detect_demonstrative_na, "Demonstrative -NA"),
        "feminine_case_alternation": (detect_feminine_case_alternation, "Feminine Case Alternation (-TI/-TU)"),
        "prefix_alternation": (detect_prefix_alternation, "Prefix Alternation (JA-/A-)"),
        "construct_state": (detect_construct_state, "Construct State Candidates"),
        "luwian_assa_toponym": (detect_luwian_assa_toponym, "Luwian -assa Toponym Suffix"),
        "luwian_wanni_ethnic": (detect_luwian_wanni_ethnic, "Luwian -wanni Ethnic Suffix"),
        "luwian_ziti_theophoric": (detect_luwian_ziti_theophoric, "Luwian -ziti Theophoric"),
        "luwian_i_mutation": (detect_luwian_i_mutation, "Luwian i-Mutation (a→i pairs)"),
        "luwian_wackernagel": (detect_luwian_wackernagel, "Luwian Wackernagel Clitics"),
        "luwian_suffix_cluster": (detect_luwian_suffix_cluster, "Luwian Suffix Clusters"),
        "egyptian_ra_theophoric": (detect_egyptian_ra_theophoric, "Egyptian Ra-Theophoric"),
        "egyptian_amun_theophoric": (detect_egyptian_amun_theophoric, "Egyptian Amun-Theophoric"),
        "egyptian_ptah_theophoric": (detect_egyptian_ptah_theophoric, "Egyptian Ptah-Theophoric"),
        "egyptian_thoth_theophoric": (detect_egyptian_thoth_theophoric, "Egyptian Thoth-Theophoric"),
        "egyptian_hathor_theophoric": (detect_egyptian_hathor_theophoric, "Egyptian Hathor-Theophoric"),
        "egyptian_nswt_royal": (detect_egyptian_nswt_royal, "Egyptian Royal nswt"),
    }

    results = {"features": {}, "summary": {}}
    for name, (func, label) in detectors.items():
        if run_all or filters.get(name):
            hits = func(words)
            results["features"][name] = {"label": label, "hits": hits}
            results["summary"][label] = len(hits)

    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        print(format_report(results, top_n=args.top))


if __name__ == "__main__":
    sys.exit(main())
