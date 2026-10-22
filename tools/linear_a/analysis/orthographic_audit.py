#!/usr/bin/env python3
"""Orthographic audit of Linear A spellings against LB conventions.

Four audit modes test implications of Linear B orthographic rules for
Linear A Semitic readings: dead-vowel detection, dental voicing (DA/TA),
geminate/D-stem blindness, and final consonant preservation.

Read-only — no writes, promotions, or in-place modifications.

Usage:
    uv run tools/linear_a/analysis/orthographic_audit.py summary
    uv run tools/linear_a/analysis/orthographic_audit.py dead-vowels --min-attestations 2
    uv run tools/linear_a/analysis/orthographic_audit.py dental-voicing --tier 2 --json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    __package__ = "tools.linear_a.analysis"

from ...core.semitic_root_schema import roots_records
from ...core.skeleton import _lookup_sign, extract_skeleton
from ...paths import CONTACT_DATA, LINEAR_A_DATA, SEMITIC_ROOTS_DATA, NotInCheckout, require

DEFAULT_DATA_DIR = LINEAR_A_DATA
SEMITIC_ROOTS_PATH = SEMITIC_ROOTS_DATA / "semitic_roots.json"
UGARITIC_LEXICON_PATH = CONTACT_DATA / "ugaritic_lexicon.jsonl"

KNOWN_SUFFIXES = {"MA", "TI", "NI", "SI", "NA", "NU", "TE"}
SUFFIX_CONSONANTS = {"m", "t", "n", "s"}
VC_SIGNS = {"AU", "*310"}


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_corpus(data_dir: Path) -> dict[str, Any]:
    return json.loads(require(data_dir / "corpus.json", "corpus.json").read_text(encoding="utf-8"))


def load_lexicon(data_dir: Path) -> list[dict[str, Any]]:
    raw = json.loads(require(data_dir / "lexicon.json", "lexicon.json").read_text(encoding="utf-8"))
    return raw["entries"]


def load_semitic_roots(path: Path = SEMITIC_ROOTS_PATH) -> list[dict[str, Any]]:
    """The roots as records (Proto-Semitic, Analogues, ...), from either file format."""
    return roots_records(json.loads(require(path, path.name).read_text(encoding="utf-8")))


def load_ugaritic(path: Path = UGARITIC_LEXICON_PATH) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    entries = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NUMERAL_RE = re.compile(r"^[𐄇-𐄳𐝫𐝀-𐝆\d]+$")
_FRACTION_RE = re.compile(r"[⁄¹²³⁴⁵⁶⁷⁸⁹⁰₀₁₂₃₄₅₆₇₈₉]")
_DIVIDER = "𐄁"


def is_word_token(token: str) -> bool:
    if not token or token == _DIVIDER or token == "\n":
        return False
    if _NUMERAL_RE.match(token):
        return False
    if _FRACTION_RE.search(token) and "-" not in token:
        return False
    if token.strip() == "≈":
        return False
    return "+" not in token


def _parse_single_root(fragment: str) -> list[str] | None:
    """Parse one root fragment (no alternatives or compounds)."""
    fragment = re.sub(r'\s*"[^"]*".*$', "", fragment)
    fragment = re.sub(r"\s*\(.*$", "", fragment)
    radicals = [r.strip().lstrip("√") for r in fragment.split("-") if r.strip()]
    if not radicals:
        return None
    if not (2 <= len(radicals) <= 5) or not all(len(r) <= 3 for r in radicals):
        return None
    return radicals


@dataclass(frozen=True)
class RootHypothesis:
    raw: str
    radicals: tuple[str, ...]


def parse_root_hypotheses(
    raw: str | None, *, component: str = "first",
) -> list[RootHypothesis]:
    """Parse all root alternatives from a root field.

    Split on " / " then " or "; per alternative take the first (or last)
    " + " component; strip √, quoted glosses, parentheticals; drop
    unparseable alternatives; dedupe by radical tuple.
    """
    if not raw:
        return []
    alternatives = []
    for part in raw.split(" / "):
        alternatives.extend(part.split(" or "))

    seen: set[tuple[str, ...]] = set()
    result: list[RootHypothesis] = []
    for alt in alternatives:
        alt = alt.strip()
        if not alt:
            continue
        components = alt.split(" + ")
        frag = components[0].strip() if component == "first" else components[-1].strip()
        radicals = _parse_single_root(frag)
        if radicals is None:
            continue
        key = tuple(r.lower() for r in radicals)
        if key in seen:
            continue
        seen.add(key)
        result.append(RootHypothesis(raw=alt, radicals=key))
    return result


def parse_root(raw: str | None) -> list[str] | None:
    hyps = parse_root_hypotheses(raw)
    return list(hyps[0].radicals) if hyps else None


def parse_root_final_component(raw: str | None) -> list[str] | None:
    """Parse the last component of a compound root for final-consonant checks."""
    hyps = parse_root_hypotheses(raw, component="last")
    return list(hyps[0].radicals) if hyps else None


def clean_word(word: str) -> str:
    """Strip parenthetical annotations from word field."""
    return re.sub(r"\s*\(.*\)\s*$", "", word).strip()


def build_lexicon_index(entries: list[dict]) -> dict[str, list[dict]]:
    idx: dict[str, list[dict]] = defaultdict(list)
    for e in entries:
        if e.get("confidence") == "REJECTED":
            continue
        w = e.get("word", "")
        if w:
            idx[w].append(e)
            cleaned = clean_word(w)
            if cleaned != w:
                idx[cleaned].append(e)
    return idx


def _skeleton_consonants(word: str) -> list[tuple[str, str]]:
    """Return [(sign_name, consonant), ...] for signs with consonants."""
    result = []
    for sign in word.split("-"):
        decomp = _lookup_sign(sign)
        if decomp and decomp[0]:
            result.append((sign, decomp[0]))
    return result


# ---------------------------------------------------------------------------
# 1. Dead Vowels
# ---------------------------------------------------------------------------

def detect_dead_vowels(word: str) -> list[dict]:
    signs = word.split("-")
    decomps = []
    for s in signs:
        d = _lookup_sign(s)
        decomps.append((s, d))

    hits = []
    for i in range(len(decomps) - 1):
        s1, d1 = decomps[i]
        s2, d2 = decomps[i + 1]
        if d1 is None or d2 is None:
            continue
        if d1[0] is None or d2[0] is None:
            continue
        if s1 in VC_SIGNS or s2 in VC_SIGNS:
            continue
        if d1[1] == d2[1]:
            hits.append({
                "position": i,
                "sign_1": s1,
                "sign_2": s2,
                "consonant_1": d1[0],
                "consonant_2": d2[0],
                "shared_vowel": d1[1],
            })
    return hits


WEAK_RADICALS = frozenset({"w", "y", "ʾ", "ʿ", "h", "ʔ", "ʕ"})


def _root_predicts_cluster(root_radicals: list[str], c1: str, c2: str) -> str | None:
    """Return 'adjacent', 'weak_elided', or None."""
    normed = [r.lower() for r in root_radicals]
    for i in range(len(normed) - 1):
        if _consonant_matches(c1, normed[i]) and _consonant_matches(c2, normed[i + 1]):
            return "adjacent"
    for i in range(len(normed)):
        for j in range(i + 2, len(normed)):
            if (all(normed[k] in WEAK_RADICALS for k in range(i + 1, j))
                    and _consonant_matches(c1, normed[i]) and _consonant_matches(c2, normed[j])):
                return "weak_elided"
    return None


def _consonant_matches(sign_c: str, radical: str) -> bool:
    if sign_c == radical:
        return True
    merges = {
        ("s", "š"), ("s", "ś"), ("s", "ṣ"), ("s", "ṯ"), ("s", "sh"),
        ("z", "ḏ"), ("z", "ẓ"),
        ("k", "ḫ"), ("k", "ḥ"), ("k", "ʿ"), ("k", "h"), ("k", "g"),
        ("t", "ṭ"), ("t", "θ"), ("t", "ṯ"), ("d", "ḍ"), ("d", "ḏ"), ("d", "t"),
        ("p", "b"), ("n", "ṇ"),
        ("r", "l"),
        ("š", "sh"),
    }
    pair = (sign_c, radical)
    return pair in merges or (radical, sign_c) in merges


def audit_dead_vowels(
    corpus: dict, lexicon_idx: dict[str, list[dict]], min_attestations: int = 1,
) -> dict:
    word_hits: dict[str, dict] = {}
    word_sites: dict[str, list[str]] = defaultdict(list)
    word_counts: Counter = Counter()

    for insc_id, entry in corpus.items():
        tw = entry.get("transliteratedWords", [])
        if not isinstance(tw, list):
            continue
        for token in tw:
            if not is_word_token(token):
                continue
            word_counts[token] += 1
            word_sites[token].append(insc_id)
            if token in word_hits:
                continue
            hits = detect_dead_vowels(token)
            if hits:
                word_hits[token] = {"hits": hits}

    results = []
    for word, info in sorted(word_hits.items(), key=lambda x: -word_counts[x[0]]):
        count = word_counts[word]
        if count < min_attestations:
            continue
        lex_entries = lexicon_idx.get(word, [])
        for hit in info["hits"]:
            classification = "UNLEXED"
            lex_root = None
            cluster_basis = None
            if lex_entries:
                has_testable_root = False
                for le in lex_entries:
                    for hyp in parse_root_hypotheses(le.get("root")):
                        has_testable_root = True
                        basis = _root_predicts_cluster(list(hyp.radicals), hit["consonant_1"], hit["consonant_2"])
                        if basis:
                            classification = "CONFIRMED_DEAD"
                            cluster_basis = basis
                            lex_root = le.get("root")
                            break
                    if classification == "CONFIRMED_DEAD":
                        break
                if classification == "UNLEXED":
                    lex_root = next((le.get("root") for le in lex_entries if parse_root(le.get("root"))), lex_entries[0].get("root"))
                    classification = "UNACCOUNTED" if has_testable_root else "NO_TESTABLE_ROOT"

            sites = sorted(set(word_sites[word]))
            row = {
                "word": word,
                "position": hit["position"],
                "sign_1": hit["sign_1"],
                "sign_2": hit["sign_2"],
                "shared_vowel": hit["shared_vowel"],
                "lexicon_root": lex_root,
                "classification": classification,
                "attestation_count": count,
                "sites": sites[:10],
            }
            if cluster_basis:
                row["cluster_basis"] = cluster_basis
            results.append(row)

    unique_above_threshold = len({r["word"] for r in results})
    confirmed = [r for r in results if r["classification"] == "CONFIRMED_DEAD"]
    confirmed_by_basis = dict(Counter(r.get("cluster_basis", "adjacent") for r in confirmed))
    summary = {
        "total_corpus_words": sum(word_counts.values()),
        "unique_words_with_dead_vowel": unique_above_threshold,
        "total_hits": len(results),
        "by_classification": dict(Counter(r["classification"] for r in results)),
        "by_vowel": dict(Counter(r["shared_vowel"] for r in results)),
        "confirmed_by_basis": confirmed_by_basis,
    }
    return {"mode": "dead-vowels", "summary": summary, "results": results}


# ---------------------------------------------------------------------------
# 2. Dental Voicing
# ---------------------------------------------------------------------------

@dataclass
class RootAlignment:
    cost: int
    sign_options: list[set[int | None]]
    always_omitted: list[int]


def _align_skeleton_to_root(
    skel_consonants: list[str], root_radicals: list[str],
) -> RootAlignment:
    n = len(skel_consonants)
    m = len(root_radicals)
    if not n or not m:
        return RootAlignment(
            cost=n + m,
            sign_options=[{None} for _ in range(n)],
            always_omitted=list(range(m)),
        )

    INF = n + m + 1

    fwd = [[INF] * (m + 1) for _ in range(n + 1)]
    fwd[0][0] = 0
    for i in range(1, n + 1):
        fwd[i][0] = i
    for j in range(1, m + 1):
        fwd[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            skip = fwd[i - 1][j] + 1
            omit = fwd[i][j - 1] + 1
            best = min(skip, omit)
            if _consonant_matches(skel_consonants[i - 1], root_radicals[j - 1]):
                best = min(best, fwd[i - 1][j - 1])
            fwd[i][j] = best

    opt = fwd[n][m]

    bwd = [[INF] * (m + 1) for _ in range(n + 1)]
    bwd[n][m] = 0
    for i in range(n - 1, -1, -1):
        bwd[i][m] = n - i
    for j in range(m - 1, -1, -1):
        bwd[n][j] = m - j
    for i in range(n - 1, -1, -1):
        for j in range(m - 1, -1, -1):
            skip = bwd[i + 1][j] + 1
            omit = bwd[i][j + 1] + 1
            best = min(skip, omit)
            if _consonant_matches(skel_consonants[i], root_radicals[j]):
                best = min(best, bwd[i + 1][j + 1])
            bwd[i][j] = best

    sign_opts: list[set[int | None]] = [set() for _ in range(n)]
    matched_radicals: set[int] = set()

    for i in range(n):
        for j in range(m):
            if (_consonant_matches(skel_consonants[i], root_radicals[j])
                    and fwd[i][j] + bwd[i + 1][j + 1] == opt):
                sign_opts[i].add(j)
                matched_radicals.add(j)
        for j in range(m + 1):
            if fwd[i][j] + 1 + bwd[i + 1][j] == opt:
                sign_opts[i].add(None)
                break

    always_omitted = sorted(j for j in range(m) if j not in matched_radicals)

    return RootAlignment(cost=opt, sign_options=sign_opts, always_omitted=always_omitted)


def audit_dental_voicing(entries: list[dict], min_tier: int = 1) -> dict:
    results = []
    skipped: dict[str, int] = Counter()

    for entry in entries:
        confidence = entry.get("confidence", "")
        if confidence == "REJECTED":
            skipped["rejected"] += 1
            continue
        tier = entry.get("tier", 0)
        if tier < min_tier:
            skipped["below_tier"] += 1
            continue

        raw_word = entry.get("word", "")
        word = clean_word(raw_word)
        if "+" in word or "-" not in word:
            skipped["logogram_or_single"] += 1
            continue
        root_str = entry.get("root")

        hypotheses = parse_root_hypotheses(root_str)
        if root_str and " + " in root_str:
            non_compound = [h for h in hypotheses if " + " not in h.raw]
            if not non_compound:
                skipped["compound_root"] += 1
                continue
        else:
            non_compound = hypotheses
        if not non_compound:
            skipped["no_root"] += 1
            continue

        skel_parts = _skeleton_consonants(word)
        if not skel_parts:
            skipped["no_consonants"] += 1
            continue

        dental_signs = []
        for i, (sign_name, consonant) in enumerate(skel_parts):
            if consonant in ("d", "t"):
                dental_signs.append((i, sign_name, consonant))

        if not dental_signs:
            continue

        skel_cons = [c for _, c in skel_parts]

        for skel_idx, sign_name, sign_consonant in dental_signs:
            per_hyp_verdicts: list[str] = []
            all_aligned_radicals: set[str] = set()

            for hyp in non_compound:
                root_cons = list(hyp.radicals)
                aln = _align_skeleton_to_root(skel_cons, root_cons)
                options = aln.sign_options[skel_idx] if skel_idx < len(aln.sign_options) else {None}
                verdicts = set()
                for opt in options:
                    if opt is None:
                        verdicts.add("unclear")
                    else:
                        root_radical = root_cons[opt]
                        all_aligned_radicals.add(root_radical)
                        if (sign_consonant == root_radical
                                or (root_radical in ("d", "ḍ", "ḏ") and sign_consonant == "d")
                                or (root_radical in ("t", "ṭ", "θ", "ṯ") and sign_consonant == "t")):
                            verdicts.add("yes")
                        elif ((root_radical in ("d", "ḍ", "ḏ") and sign_consonant == "t")
                                or (root_radical in ("t", "ṭ", "θ", "ṯ") and sign_consonant == "d")):
                            verdicts.add("no")
                        elif _consonant_matches(sign_consonant, root_radical):
                            verdicts.add("yes")
                        else:
                            verdicts.add("unclear")

                if len(verdicts) == 1:
                    per_hyp_verdicts.append(next(iter(verdicts)))
                else:
                    per_hyp_verdicts.append("unclear")

            hyp_set = set(per_hyp_verdicts)
            if hyp_set == {"yes"}:
                match = "yes"
            elif hyp_set == {"no"}:
                match = "no"
            elif "yes" in hyp_set and "no" in hyp_set:
                match = "ambiguous"
            elif "yes" in hyp_set:
                match = "yes"
            elif "no" in hyp_set:
                match = "no"
            else:
                match = "unclear"

            all_radicals = sorted(all_aligned_radicals)
            ambiguous = len(all_aligned_radicals) > 1

            row: dict[str, Any] = {
                "word": word,
                "sign": sign_name,
                "sign_position": skel_idx,
                "sign_consonant": sign_consonant,
                "root": root_str,
                "root_radical": all_radicals[0] if len(all_radicals) == 1 else None,
                "root_radicals": all_radicals,
                "alignment_ambiguous": ambiguous,
                "match": match,
                "confidence_tier": tier,
                "reading": entry.get("reading", ""),
            }
            if len(non_compound) > 1:
                row["per_alternative"] = [
                    {"root": h.raw, "match": v}
                    for h, v in zip(non_compound, per_hyp_verdicts)
                ]
            results.append(row)

    mismatches = [r for r in results if r["match"] == "no"]
    ambiguous_alt = [r for r in results if r["match"] == "ambiguous"]
    summary = {
        "total_dental_signs": len(results),
        "matches": len([r for r in results if r["match"] == "yes"]),
        "mismatches": len(mismatches),
        "unclear": len([r for r in results if r["match"] == "unclear"]),
        "ambiguous": len(ambiguous_alt),
        "by_consonant": {
            "d": {"total": 0, "match": 0, "mismatch": 0, "unclear": 0, "ambiguous": 0},
            "t": {"total": 0, "match": 0, "mismatch": 0, "unclear": 0, "ambiguous": 0},
        },
    }
    for r in results:
        c = r["sign_consonant"]
        if c in summary["by_consonant"]:
            summary["by_consonant"][c]["total"] += 1
            if r["match"] == "yes":
                summary["by_consonant"][c]["match"] += 1
            elif r["match"] == "no":
                summary["by_consonant"][c]["mismatch"] += 1
            elif r["match"] == "ambiguous":
                summary["by_consonant"][c]["ambiguous"] += 1
            else:
                summary["by_consonant"][c]["unclear"] += 1

    return {
        "mode": "dental-voicing",
        "summary": summary,
        "results": results,
        "mismatches": mismatches,
        "skipped": dict(skipped),
    }


# ---------------------------------------------------------------------------
# 3. Geminates / D-stem
# ---------------------------------------------------------------------------

def _extract_d_stem_meanings(semitic_roots: list[dict]) -> dict[str, str]:
    d_stem_map: dict[str, str] = {}
    d_pattern = re.compile(r'\bD\s+”([^”]+)”')
    d_pattern2 = re.compile(r'\bD\s+[“”“]([^”””]+)[“””]')
    d_pattern3 = re.compile(r'\bD-stem\s+”([^”]+)”')

    for root in semitic_roots:
        ug = root.get("Analogues", {}).get("Ugaritic", "")
        if not ug:
            continue
        ps = root.get("Proto-Semitic", "")
        radicals = re.sub(r"[*\-ˀʔ()aeiouāēīōūVN]", "", ps).strip()

        m = d_pattern.search(ug)
        if not m:
            m = d_pattern2.search(ug)
        if not m:
            m = d_pattern3.search(ug)
        if m:
            root_key = radicals.lower().replace("ʕ", "ʿ")
            d_stem_map[root_key] = m.group(1)

    return d_stem_map


def audit_geminates(entries: list[dict], semitic_roots: list[dict]) -> dict:
    d_stem_meanings = _extract_d_stem_meanings(semitic_roots)

    results = []
    skipped: dict[str, int] = Counter()

    seen_geminate: set[tuple[str, str]] = set()

    for entry in entries:
        if entry.get("confidence") == "REJECTED":
            skipped["rejected"] += 1
            continue
        root_str = entry.get("root")
        hypotheses = parse_root_hypotheses(root_str)
        triliteral_hyps = [h for h in hypotheses if len(h.radicals) == 3]
        if not triliteral_hyps:
            skipped["not_triliteral"] += 1
            continue

        word = clean_word(entry.get("word", ""))
        reading = entry.get("reading", "")
        current_meaning = entry.get("meaning", "")

        skel = extract_skeleton(word)
        if not skel:
            skipped["empty_skeleton"] += 1
            continue

        for hyp in triliteral_hyps:
            radicals = list(hyp.radicals)
            middle = radicals[1]
            root_key = "".join(radicals).replace("ʕ", "ʿ")
            d_stem_meaning = d_stem_meanings.get(root_key)

            middle_count = sum(1 for c in skel if _consonant_matches(c, middle))

            dedup_key = (word, root_key)
            if middle_count == 1 and d_stem_meaning and dedup_key not in seen_geminate:
                seen_geminate.add(dedup_key)
                results.append({
                    "word": word,
                    "root": "-".join(radicals),
                    "middle_radical": middle,
                    "current_meaning": current_meaning,
                    "current_reading": reading,
                    "possible_d_stem_meaning": d_stem_meaning,
                    "confidence_tier": entry.get("tier", 0),
                    "note": f"Middle radical /{middle}/ written once — could hide D-stem geminate",
                })

    summary = {
        "total_candidates": len(results),
        "unique_roots": len({r["root"] for r in results}),
    }
    return {
        "mode": "geminates",
        "summary": summary,
        "results": results,
        "skipped": dict(skipped),
    }


# ---------------------------------------------------------------------------
# 4. Final Consonants
# ---------------------------------------------------------------------------

_STATUS_PRECEDENCE = {"preserved": 0, "suffix_obscured": 1, "ambiguous": 2, "dropped": 3}


def audit_final_consonants(entries: list[dict]) -> dict:
    results = []
    stats: dict[str, dict[str, int]] = defaultdict(lambda: {
        "preserved": 0, "suffix_obscured": 0, "dropped": 0, "ambiguous": 0, "total": 0,
    })
    skipped: dict[str, int] = Counter()

    for entry in entries:
        if entry.get("confidence") == "REJECTED":
            skipped["rejected"] += 1
            continue
        raw_word = entry.get("word", "")
        word = clean_word(raw_word)
        if "+" in word or "-" not in word:
            skipped["logogram_or_single"] += 1
            continue

        root_str = entry.get("root")
        hypotheses = parse_root_hypotheses(root_str, component="last")
        if not hypotheses:
            skipped["no_root"] += 1
            continue

        signs = word.split("-")
        last_sign = signs[-1]
        last_decomp = _lookup_sign(last_sign)
        last_consonant = last_decomp[0] if last_decomp else None

        per_hyp_statuses: list[tuple[str, str, str]] = []
        for hyp in hypotheses:
            final_radical = hyp.radicals[-1]

            if last_decomp is None:
                h_status = "ambiguous"
                h_note = f"Final sign {last_sign} undecomposable"
            elif last_consonant is None:
                penult = signs[-2]
                penult_decomp = _lookup_sign(penult)
                penult_c = penult_decomp[0] if penult_decomp else None
                if penult_c and _consonant_matches(penult_c, final_radical):
                    h_status = "preserved"
                    h_note = f"Final /{final_radical}/ at penultimate {penult}, pure vowel {last_sign} follows"
                else:
                    h_status = "ambiguous"
                    h_note = f"Final sign {last_sign} is pure vowel, penultimate {penult} does not match /{final_radical}/"
            elif last_consonant and _consonant_matches(last_consonant, final_radical):
                h_status = "preserved"
                h_note = ""
            else:
                penult = signs[-2]
                penult_decomp = _lookup_sign(penult)
                penult_c = penult_decomp[0] if penult_decomp else None
                if penult_c and _consonant_matches(penult_c, final_radical):
                    if last_sign.upper() in KNOWN_SUFFIXES or (last_consonant and last_consonant in SUFFIX_CONSONANTS):
                        h_status = "suffix_obscured"
                        h_note = f"Final /{final_radical}/ at penultimate {penult}, suffix {last_sign}"
                    else:
                        h_status = "ambiguous"
                        h_note = f"Penultimate {penult} matches /{final_radical}/, final {last_sign} unknown role"
                else:
                    h_status = "dropped"
                    h_note = f"Final sign {last_sign} (/{last_consonant}/) does not match root-final /{final_radical}/"

            per_hyp_statuses.append((h_status, h_note, final_radical))

        best = min(per_hyp_statuses, key=lambda x: _STATUS_PRECEDENCE.get(x[0], 99))
        status, note, final_radical = best
        alternatives_disagree = len({s for s, _, _ in per_hyp_statuses}) > 1

        stats[final_radical][status] += 1
        stats[final_radical]["total"] += 1

        row: dict[str, Any] = {
            "word": word,
            "root": root_str,
            "final_radical": final_radical,
            "final_sign": last_sign,
            "final_sign_consonant": last_consonant,
            "status": status,
            "note": note,
            "tier": entry.get("tier", 0),
        }
        if alternatives_disagree:
            row["alternatives_disagree"] = True
        results.append(row)

    stats_table = []
    for radical in sorted(stats.keys()):
        s = stats[radical]
        stats_table.append({
            "radical": radical,
            **s,
        })

    summary = {
        "total_audited": len(results),
        "preserved": sum(s["preserved"] for s in stats.values()),
        "suffix_obscured": sum(s["suffix_obscured"] for s in stats.values()),
        "dropped": sum(s["dropped"] for s in stats.values()),
        "ambiguous": sum(s["ambiguous"] for s in stats.values()),
    }
    return {
        "mode": "final-consonants",
        "summary": summary,
        "statistics": stats_table,
        "results": results,
        "skipped": dict(skipped),
    }


# ---------------------------------------------------------------------------
# 5. Summary
# ---------------------------------------------------------------------------

_READING_VOWELS = set("aeiouāēīōūáéíóúâêîôû")


def _reading_consonant_runs(reading: str) -> list[tuple[int, str, int]]:
    """(start_index, run, n_segments) for every consonant run in a reading.

    Combining marks (ṣ̂ = ṣ + U+0302) attach to their base letter rather
    than counting as segments; length/vowel tests run on base characters.
    Positions and n_segments count base segments, not codepoints, so the
    caller can test word-final position against the segment total.
    """
    decomposed = unicodedata.normalize("NFD", reading)
    segments: list[str] = []
    for ch in decomposed:
        if unicodedata.combining(ch):
            if segments:
                segments[-1] += ch
            continue
        segments.append(ch)

    def is_vowel(seg: str) -> bool:
        base = unicodedata.normalize("NFC", seg)
        return base.lower() in _READING_VOWELS or seg[0].lower() in "aeiou"

    runs: list[tuple[int, str, int]] = []
    current = ""
    start = 0
    n_segments = len(segments)
    for i, seg in enumerate(segments):
        if is_vowel(seg):
            if current:
                runs.append((start, unicodedata.normalize("NFC", current), n_segments))
                current = ""
        else:
            if not current:
                start = i
            current += seg
    if current:
        runs.append((start, unicodedata.normalize("NFC", current), n_segments))
    return runs


def audit_stress_syncope(entries: list[dict]) -> dict:
    """Report-only Proto-Semitic syllable-structure check over lexicon readings.

    PS syllables are CV/CV̄/CVC only — no clusters word-initially or -finally,
    no medial CCC (Huehnergard 2019 §2.3). A reading
    that collapses dead vowels into such a cluster over-applies syncope.
    Geminates and medial CC (VC.CV) are legal. Readings carrying editorial
    marks (spaces, parentheses, slashes, hyphens) are skipped — they encode
    annotations, not plain phonemic forms. No threshold is enforced.
    """
    flagged: list[dict] = []
    skipped = 0
    checked = 0
    for entry in entries:
        reading = str(entry.get("reading") or "")
        if not reading:
            skipped += 1
            continue
        if any(ch in reading for ch in " ()/-=[]?"):
            skipped += 1
            continue
        checked += 1
        violations = []
        for start, run, n_segments in _reading_consonant_runs(reading):
            run_len = sum(1 for ch in unicodedata.normalize("NFD", run)
                          if not unicodedata.combining(ch))
            if run_len < 2:
                continue
            if start == 0:
                violations.append(f"word-initial cluster '{run}'")
            elif start + run_len == n_segments:
                violations.append(f"word-final cluster '{run}' (PS allows final CVC only)")
            elif run_len > 2:
                violations.append(f"medial {run_len}-consonant run '{run}'")
        if violations:
            flagged.append({
                "word": entry.get("word"),
                "reading": reading,
                "tier": entry.get("tier"),
                "confidence": entry.get("confidence"),
                "violations": violations,
            })
    return {
        "audit": "stress-syncope",
        "rule": "PS syllables CV/CV̄/CVC only (Huehnergard 2019 §2.3): no initial or final clusters, no medial CCC",
        "checked": checked,
        "skipped_annotated_or_empty": skipped,
        "flagged": flagged,
        "flagged_count": len(flagged),
    }


def render_stress_syncope(report: dict) -> str:
    lines = [
        "Stress/Syncope Consistency (report-only)",
        "=" * 60,
        f"Rule:    {report['rule']}",
        (f"Checked: {report['checked']} plain readings "
         f"({report['skipped_annotated_or_empty']} annotated/empty skipped)"),
        f"Flagged: {report['flagged_count']}",
        "",
    ]
    for f in report["flagged"]:
        lines.append(f"  {f['word']}  {f['reading']}  "
                     f"[tier {f['tier']}, {f['confidence']}]")
        for v in f["violations"]:
            lines.append(f"      {v}")
    if not report["flagged"]:
        lines.append("  (no violations)")
    return "\n".join(lines)


def audit_summary(
    corpus: dict,
    entries: list[dict],
    semitic_roots: list[dict],
    min_attestations: int = 1,
    min_tier: int = 1,
) -> dict:
    lexicon_idx = build_lexicon_index(entries)
    dv = audit_dead_vowels(corpus, lexicon_idx, min_attestations)
    dt = audit_dental_voicing(entries, min_tier)
    gm = audit_geminates(entries, semitic_roots)
    fc = audit_final_consonants(entries)
    return {
        "mode": "summary",
        "dead_vowels": dv,
        "dental_voicing": dt,
        "geminates": gm,
        "final_consonants": fc,
    }


# ---------------------------------------------------------------------------
# Text rendering
# ---------------------------------------------------------------------------

def render_dead_vowels(report: dict) -> str:
    lines = ["DEAD VOWEL AUDIT", "=" * 60]
    s = report["summary"]
    lines.append(f"Corpus words scanned: {s['total_corpus_words']}")
    lines.append(f"Unique words with dead-vowel pairs: {s['unique_words_with_dead_vowel']}")
    lines.append(f"Total hits: {s['total_hits']}")
    lines.append(f"By classification: {s['by_classification']}")
    if s.get("confirmed_by_basis"):
        lines.append(f"Confirmed by basis: {s['confirmed_by_basis']}")
    lines.append(f"By vowel: {s['by_vowel']}")
    lines.append("")
    lines.append(f"{'Word':<20} {'Pos':>3} {'Signs':<14} {'V':>2} {'Root':<10} {'Class':<16} {'#':>4}")
    lines.append("-" * 75)
    for r in report["results"][:50]:
        pair = f"{r['sign_1']}-{r['sign_2']}"
        root = r["lexicon_root"] or "—"
        basis = f" [{r['cluster_basis']}]" if r.get("cluster_basis") == "weak_elided" else ""
        lines.append(
            f"{r['word']:<20} {r['position']:>3} {pair:<14} {r['shared_vowel']:>2} "
            f"{root:<10} {r['classification']:<16} {r['attestation_count']:>4}{basis}"
        )
    if len(report["results"]) > 50:
        lines.append(f"... and {len(report['results']) - 50} more")
    return "\n".join(lines)


def render_dental_voicing(report: dict) -> str:
    lines = ["DENTAL VOICING AUDIT", "=" * 60]
    s = report["summary"]
    lines.append(f"Total dental signs audited: {s['total_dental_signs']}")
    amb = s.get('ambiguous', 0)
    amb_str = f"  Ambiguous: {amb}" if amb else ""
    lines.append(f"Matches: {s['matches']}  Mismatches: {s['mismatches']}  Unclear: {s['unclear']}{amb_str}")
    for c in ("d", "t"):
        bc = s["by_consonant"][c]
        lines.append(f"  /{c}/: {bc['total']} total, {bc['match']} match, {bc['mismatch']} mismatch, {bc['unclear']} unclear")
    if report.get("skipped"):
        lines.append(f"Skipped: {report['skipped']}")
    lines.append("")

    mismatches = report.get("mismatches", [])
    if mismatches:
        lines.append("MISMATCHES (investigate):")
        lines.append(f"{'Word':<20} {'Sign':<8} {'Sgn':>3} {'Root':<12} {'Rad':>5} {'Tier':>4}")
        lines.append("-" * 55)
        for r in mismatches:
            rads = r.get("root_radicals", [r["root_radical"]] if r.get("root_radical") else ["?"])
            rad_str = "|".join(rads)
            lines.append(
                f"{r['word']:<20} {r['sign']:<8} /{r['sign_consonant']}/  "
                f"{r['root']:<12} /{rad_str}/  {r['confidence_tier']:>4}"
            )
    else:
        lines.append("No mismatches found.")

    return "\n".join(lines)


def render_geminates(report: dict) -> str:
    lines = ["GEMINATE / D-STEM AUDIT", "=" * 60]
    s = report["summary"]
    lines.append(f"Candidates found: {s['total_candidates']} (from {s['unique_roots']} roots)")
    if report.get("skipped"):
        lines.append(f"Skipped: {report['skipped']}")
    lines.append("")

    if report["results"]:
        lines.append(f"{'Word':<20} {'Root':<10} {'Mid':>3} {'Current':<25} {'D-stem':<25} {'T':>2}")
        lines.append("-" * 90)
        for r in report["results"]:
            cur = (r["current_meaning"] or "")[:24]
            dstem = (r["possible_d_stem_meaning"] or "")[:24]
            lines.append(
                f"{r['word']:<20} {r['root']:<10} /{r['middle_radical']}/  "
                f"{cur:<25} {dstem:<25} {r['confidence_tier']:>2}"
            )
    else:
        lines.append("No D-stem candidates found.")

    return "\n".join(lines)


def render_final_consonants(report: dict) -> str:
    lines = ["FINAL CONSONANT AUDIT", "=" * 60]
    s = report["summary"]
    lines.append(f"Total audited: {s['total_audited']}")
    lines.append(f"Preserved: {s['preserved']}  Suffix-obscured: {s['suffix_obscured']}  "
                 f"Dropped: {s['dropped']}  Ambiguous: {s['ambiguous']}")
    lines.append("")

    lines.append("Statistics by final radical:")
    lines.append(f"{'Rad':<7} {'Prsv':>5} {'Suff':>5} {'Drop':>5} {'Ambg':>5} {'Total':>6}")
    lines.append("-" * 37)
    for st in report["statistics"]:
        lines.append(
            f"/{st['radical']:<6} {st['preserved']:>5} {st['suffix_obscured']:>5} "
            f"{st['dropped']:>5} {st['ambiguous']:>5} {st['total']:>6}"
        )
    lines.append("")

    dropped = [r for r in report["results"] if r["status"] == "dropped"]
    if dropped:
        lines.append(f"DROPPED entries ({len(dropped)} — investigate):")
        lines.append(f"{'Word':<20} {'Root':<12} {'Fin Rad':>7} {'Fin Sign':<10} {'Fin C':>5} {'T':>3}")
        lines.append("-" * 60)
        for r in dropped[:30]:
            fc = r["final_sign_consonant"] or "?"
            lines.append(
                f"{r['word']:<20} {r['root']:<12} /{r['final_radical']:<5} "
                f"{r['final_sign']:<10} /{fc:<3}  {r['tier']:>3}"
            )
        if len(dropped) > 30:
            lines.append(f"... and {len(dropped) - 30} more")
    else:
        lines.append("No genuinely dropped final consonants found.")

    return "\n".join(lines)


def render_summary(report: dict) -> str:
    parts = [
        "ORTHOGRAPHIC AUDIT — SUMMARY",
        "=" * 60,
        "",
        render_dead_vowels(report["dead_vowels"]),
        "",
        render_dental_voicing(report["dental_voicing"]),
        "",
        render_geminates(report["geminates"]),
        "",
        render_final_consonants(report["final_consonants"]),
    ]
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="orthographic_audit",
        description="Audit Linear A spellings against LB orthographic conventions",
    )
    parser.add_argument(
        "--data-dir", type=Path, default=DEFAULT_DATA_DIR,
        help="Linear A data directory holding corpus.json and lexicon.json (default: data/linear-a/)",
    )
    parser.add_argument(
        "--semitic-roots", type=Path, default=SEMITIC_ROOTS_PATH,
        help="semitic_roots.json (default: data/semitic-roots/semitic_roots.json)",
    )

    sub = parser.add_subparsers(dest="mode", required=True)

    dv = sub.add_parser("dead-vowels", help="Detect adjacent same-vowel sign pairs")
    dv.add_argument("--json", action="store_true")
    dv.add_argument("--min-attestations", type=int, default=1)

    dt = sub.add_parser("dental-voicing", help="Audit DA/TA voicing against root radicals")
    dt.add_argument("--json", action="store_true")
    dt.add_argument("--tier", type=int, default=1)

    gm = sub.add_parser("geminates", help="Find potential D-stem/geminate readings")
    gm.add_argument("--json", action="store_true")

    fc = sub.add_parser("final-consonants", help="Audit final consonant preservation")
    fc.add_argument("--json", action="store_true")

    ss = sub.add_parser("stress-syncope",
                        help="Report-only PS syllable-structure check on lexicon readings")
    ss.add_argument("--json", action="store_true")

    sm = sub.add_parser("summary", help="Run all audits and produce combined report")
    sm.add_argument("--json", action="store_true")
    sm.add_argument("--min-attestations", type=int, default=1)
    sm.add_argument("--tier", type=int, default=1)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Exit 2 with the file's name when a data file is not in the checkout."""
    try:
        return _run(argv)
    except NotInCheckout as e:
        print(f"stopped: {e}", file=sys.stderr)
        return 2


def _run(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    data_dir = args.data_dir

    if args.mode == "dead-vowels":
        corpus = load_corpus(data_dir)
        entries = load_lexicon(data_dir)
        lexicon_idx = build_lexicon_index(entries)
        report = audit_dead_vowels(corpus, lexicon_idx, args.min_attestations)
        if args.json:
            print(json.dumps(report, indent=2, ensure_ascii=False))
        else:
            print(render_dead_vowels(report))

    elif args.mode == "dental-voicing":
        entries = load_lexicon(data_dir)
        report = audit_dental_voicing(entries, args.tier)
        if args.json:
            print(json.dumps(report, indent=2, ensure_ascii=False))
        else:
            print(render_dental_voicing(report))

    elif args.mode == "geminates":
        entries = load_lexicon(data_dir)
        semitic_roots = load_semitic_roots(args.semitic_roots)
        report = audit_geminates(entries, semitic_roots)
        if args.json:
            print(json.dumps(report, indent=2, ensure_ascii=False))
        else:
            print(render_geminates(report))

    elif args.mode == "final-consonants":
        entries = load_lexicon(data_dir)
        report = audit_final_consonants(entries)
        if args.json:
            print(json.dumps(report, indent=2, ensure_ascii=False))
        else:
            print(render_final_consonants(report))

    elif args.mode == "stress-syncope":
        entries = load_lexicon(data_dir)
        report = audit_stress_syncope(entries)
        if args.json:
            print(json.dumps(report, indent=2, ensure_ascii=False))
        else:
            print(render_stress_syncope(report))

    elif args.mode == "summary":
        corpus = load_corpus(data_dir)
        entries = load_lexicon(data_dir)
        semitic_roots = load_semitic_roots(args.semitic_roots)
        report = audit_summary(
            corpus, entries, semitic_roots,
            min_attestations=args.min_attestations,
            min_tier=args.tier,
        )
        if args.json:
            print(json.dumps(report, indent=2, ensure_ascii=False))
        else:
            print(render_summary(report))

    return 0


if __name__ == "__main__":
    sys.exit(main())
