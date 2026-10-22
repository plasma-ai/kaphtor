#!/usr/bin/env python3
"""Null model audit for the skeleton matcher.

Tests whether Linear A corpus skeletons match roots at a rate
exceeding what random consonant sequences would achieve.

Two permutation modes:
  skeleton-permutation (default): Pool all consonants from corpus skeletons,
    shuffle, redistribute into synthetic skeletons preserving length distribution,
    match against real roots. Tests whether Linear A's specific consonant
    sequences are unusually close to the target language's roots.

  root-shuffle (confirmatory): Permute consonants within each real root,
    match real corpus skeletons against the shuffled roots. Tests whether
    the specific ORDER of consonants matters.

Five language targets:
  nws (default), luwian, egyptian, hurrian, cross-compare (all four).

Site-class stratification:
  --site-class {peak_sanctuary,palace,town,cycladic,all} filters corpus
  skeletons by archaeological site type before running the audit.

Usage:
    uv run tools/linear_a/validation/null_model_audit.py [--iterations 1000] [--json] [--save]
    uv run tools/linear_a/validation/null_model_audit.py --quick   # 50 iterations
    uv run tools/linear_a/validation/null_model_audit.py --mode root-shuffle
    uv run tools/linear_a/validation/null_model_audit.py --language luwian --quick
    uv run tools/linear_a/validation/null_model_audit.py --language cross-compare --quick --json
    uv run tools/linear_a/validation/null_model_audit.py --site-class peak_sanctuary --language cross-compare --quick
    uv run tools/linear_a/validation/null_model_audit.py --frequency-class hapax --language cross-compare --quick
    uv run tools/linear_a/validation/null_model_audit.py --frequency-class repeated --language cross-compare --quick
    uv run tools/linear_a/validation/null_model_audit.py --exclude-names --language cross-compare --quick
    uv run tools/linear_a/validation/null_model_audit.py --length-class medium --language cross-compare --quick
    uv run tools/linear_a/validation/null_model_audit.py --verb-lens --quick
    uv run tools/linear_a/validation/null_model_audit.py --verb-lens --iterations 1000 --seed 1961 --save
"""

import argparse
import json
import math
import random
import re
import sys
import time
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    __package__ = "tools.linear_a.validation"

from ...core import run_saver
from ...core.phonetics import (
    EGYPTIAN_DISTANCES,
    GUTTURAL_PHONEMES,
    LUWIAN_DISTANCES,
    SEMITIC_DISTANCES,
    _tokenize_phonemes,
    weighted_levenshtein,
)
from ...core.semitic_root_schema import roots_records
from ...core.skeleton import extract_skeleton
from ...paths import LINEAR_A_DATA, SEMITIC_ROOTS_DATA, NotInCheckout, require

THRESHOLDS = [0.3, 0.5, 0.7, 1.0]
MAX_ROOT_LEN = 5  # only generate/compare roots with 2-5 consonants

LANGUAGE_CONFIGS = {
    "nws": {"file": "semitic_roots.json", "field": "Proto-Semitic", "label": "NWS (Proto-Semitic)"},
    "luwian": {"file": "luwian_roots.json", "field": "Consonantal_Root", "label": "Luwian/Anatolian"},
    "egyptian": {"file": "egyptian_roots.json", "field": "Consonantal_Root", "label": "Egyptian"},
    "hurrian": {"file": "hurrian_roots.json", "field": "Consonantal_Root", "label": "Hurrian"},
}

LANGUAGE_DISTANCE_TABLES = {
    "nws": SEMITIC_DISTANCES,
    "luwian": LUWIAN_DISTANCES,
    "egyptian": EGYPTIAN_DISTANCES,
    "hurrian": None,  # no Hurrian-specific table; uses default costs
}


def _extract_consonantal_root(form: str) -> str:
    """Canonical root extraction from ventris_propagate.py."""
    s = form.strip()
    s = unicodedata.normalize("NFC", s)
    s = re.sub(r"^\*", "", s)
    s = re.sub(r"\(.*?\)", "", s)
    s = re.sub(r"\d+$", "", s)
    s = s.split(",")[0].split(" ")[0]
    if "/*" in s:
        s = s.split("/*")[0]
    s = s.replace("/", "")
    s = s.replace("-", "").replace("_", "")
    vowels = set("aeiouāēīōūäëïöüăĕĭŏŭ")
    root = "".join(c for c in s if c.lower() not in vowels and c not in "* V")
    return root.lower()


def load_site_classes() -> dict[str, list[str]]:
    """Load site-class taxonomy from data/linear-a/site_classes.json.

    Returns mapping of class_name -> list of site names.
    """
    path = require(LINEAR_A_DATA / "site_classes.json", "site_classes.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    return {cls: info["sites"] for cls, info in data["classes"].items()}


def load_corpus_skeletons(
    site_filter: set[str] | None = None,
    frequency_class: str = "all",
    length_class: str = "all",
    min_skeleton_len: int | None = None,
) -> tuple[list[str], dict]:
    """Load corpus and extract unique polysyllabic word skeletons.

    Args:
        site_filter: If provided, only include words from inscriptions at these sites.
        frequency_class: "all" (default), "hapax" (count==1), or "repeated" (count>=2).
        length_class: "all" (default), "short" (1-2 cons), "medium" (3 cons), "long" (4+ cons).
        min_skeleton_len: If set, exclude skeletons with fewer than N consonants.
            Applied after length_class. Useful for content-word-only filtering (N=3
            excludes particles and prepositions absent from administrative registers).

    Returns (skeletons, meta) where meta contains filtering statistics.
    """
    corpus_path = require(LINEAR_A_DATA / "corpus.json", "corpus.json")
    corpus = json.loads(corpus_path.read_text(encoding="utf-8"))

    # First pass: count ALL word occurrences across ALL inscriptions (before site filtering)
    global_freq: Counter = Counter()
    for inscription in corpus.values():
        for w in inscription.get("transliteratedWords", []):
            if "-" in w and not w.startswith("*") and not w.replace("-", "").isdigit():
                global_freq[w] += 1

    total_inscriptions = 0
    filtered_inscriptions = 0
    words = set()
    for inscription in corpus.values():
        total_inscriptions += 1
        if site_filter is not None:
            site = inscription.get("site", "")
            if site not in site_filter:
                continue
        filtered_inscriptions += 1
        for w in inscription.get("transliteratedWords", []):
            if "-" in w and not w.startswith("*") and not w.replace("-", "").isdigit():
                if frequency_class == "hapax" and global_freq[w] != 1 or frequency_class == "repeated" and global_freq[w] < 2:
                    continue
                words.add(w)

    all_skeletons = []
    for w in sorted(words):
        skel = extract_skeleton(w)
        if skel and len(skel) >= 2:
            all_skeletons.append(skel)

    length_breakdown = Counter()
    for s in all_skeletons:
        n = len(_tokenize_phonemes(s))
        if n <= 2:
            length_breakdown["short"] += 1
        elif n == 3:
            length_breakdown["medium"] += 1
        else:
            length_breakdown["long"] += 1

    if length_class == "short":
        skeletons = [s for s in all_skeletons if len(_tokenize_phonemes(s)) <= 2]
    elif length_class == "medium":
        skeletons = [s for s in all_skeletons if len(_tokenize_phonemes(s)) == 3]
    elif length_class == "long":
        skeletons = [s for s in all_skeletons if len(_tokenize_phonemes(s)) >= 4]
    else:
        skeletons = all_skeletons

    pre_min_count = len(skeletons)
    if min_skeleton_len is not None and min_skeleton_len > 1:
        skeletons = [s for s in skeletons if len(_tokenize_phonemes(s)) >= min_skeleton_len]

    hapax_count = sum(1 for w, c in global_freq.items() if c == 1)
    repeated_count = sum(1 for w, c in global_freq.items() if c >= 2)

    meta = {
        "total_inscriptions": total_inscriptions,
        "filtered_inscriptions": filtered_inscriptions,
        "site_filter": sorted(site_filter) if site_filter else None,
        "frequency_class": frequency_class,
        "length_class": length_class,
        "min_skeleton_len": min_skeleton_len,
        "min_skeleton_len_filtered": pre_min_count - len(skeletons) if min_skeleton_len else 0,
        "frequency_breakdown": {
            "hapax": hapax_count,
            "repeated": repeated_count,
            "total_unique": len(global_freq),
        },
        "length_breakdown": dict(length_breakdown),
    }
    return skeletons, meta


def _is_onomastic(entry: dict) -> bool:
    """Detect proper-name entries (PN/GN/DN) in root databases."""
    meaning = entry.get("Meaning", "")
    if re.search(r'\((?:PN|GN|DN)\)', meaning):
        return True
    for v in entry.get("Analogues", {}).values():
        if re.search(r'\((?:PN|GN|DN)\)', str(v)):
            return True
    return False


def load_roots(language: str = "nws", exclude_names: bool = False) -> tuple[list[str], dict]:
    """Load and analyze a root database.

    Args:
        language: Key into LANGUAGE_CONFIGS (nws, luwian, egyptian, hurrian).
        exclude_names: If True, filter out onomastic entries (PN/GN/DN).

    Returns (root_consonants, statistics) where statistics contains
    length distribution and per-position consonant frequencies.
    """
    config = LANGUAGE_CONFIGS[language]
    if language == "nws":
        roots_path = require(SEMITIC_ROOTS_DATA / config["file"], config["file"])
        raw_roots = roots_records(json.loads(roots_path.read_text(encoding="utf-8")))
    else:
        roots_path = require(LINEAR_A_DATA / config["file"], config["file"])
        raw_roots = json.loads(roots_path.read_text(encoding="utf-8"))

    root_consonants = []
    length_counts: Counter = Counter()
    pos_freqs: dict[int, Counter] = defaultdict(Counter)
    onomastic_filtered = 0

    field = config["field"]
    for entry in raw_roots:
        if exclude_names and _is_onomastic(entry):
            onomastic_filtered += 1
            continue
        val = entry.get(field, "")
        if not val:
            continue
        cons = _extract_consonantal_root(val)
        tokens = _tokenize_phonemes(cons)
        if not tokens or len(tokens) < 2 or len(tokens) > MAX_ROOT_LEN:
            continue

        root_consonants.append(cons)
        length_counts[len(tokens)] += 1
        for i, t in enumerate(tokens):
            pos_freqs[i][t] += 1

    guttural_count = sum(
        1 for r in root_consonants
        if any(t in GUTTURAL_PHONEMES for t in _tokenize_phonemes(r))
    )

    stats = {
        "language": language,
        "label": config["label"],
        "total": len(root_consonants),
        "onomastic_filtered": onomastic_filtered,
        "exclude_names": exclude_names,
        "guttural_count": guttural_count,
        "guttural_pct": guttural_count / len(root_consonants) * 100 if root_consonants else 0,
        "length_dist": dict(length_counts),
        "pos_freqs": {k: dict(v) for k, v in pos_freqs.items()},
    }
    return root_consonants, stats


def generate_synthetic_skeletons(real_skeletons: list[str]) -> list[str]:
    """Shuffle corpus consonant pool into synthetic skeletons.

    Preserves: total consonant inventory, skeleton length distribution.
    Randomizes: which consonants appear in which skeleton.
    """
    skeleton_lengths = []
    all_consonants = []
    for s in real_skeletons:
        tokens = _tokenize_phonemes(s)
        skeleton_lengths.append(len(tokens))
        all_consonants.extend(tokens)

    random.shuffle(all_consonants)

    synthetic = []
    idx = 0
    for length in skeleton_lengths:
        synthetic.append("".join(all_consonants[idx:idx + length]))
        idx += length
    return synthetic


def generate_shuffled_roots(real_roots: list[str]) -> list[str]:
    """Permute consonants within each root (preserves per-root inventory)."""
    shuffled = []
    for root in real_roots:
        tokens = list(_tokenize_phonemes(root))
        random.shuffle(tokens)
        shuffled.append("".join(tokens))
    return shuffled


def count_matches(
    skeletons: list[str],
    roots: list[str],
    threshold: float,
    guttural_transparent: bool = True,
) -> int:
    """Count how many skeletons match at least one root within threshold."""
    matched = 0
    for skel in skeletons:
        skel_len = len(_tokenize_phonemes(skel))
        for root in roots:
            root_tokens = _tokenize_phonemes(root)
            if abs(len(root_tokens) - skel_len) > 2:
                continue
            dist = weighted_levenshtein(skel, root, guttural_transparent=guttural_transparent)
            if dist <= threshold:
                matched += 1
                break
    return matched


def count_matches_multi(
    skeletons: list[str],
    roots: list[str],
    thresholds: list[float],
    guttural_transparent: bool = True,
    distances: dict | None = None,
) -> dict[float, int]:
    """Count matches at all thresholds in a single pass (4× faster).

    Args:
        distances: Language-specific substitution cost table. None = SEMITIC_DISTANCES (default).
    """
    sorted_thresholds = sorted(thresholds)
    counts = {t: 0 for t in thresholds}

    root_cache = [(r, _tokenize_phonemes(r)) for r in roots]

    for skel in skeletons:
        skel_len = len(_tokenize_phonemes(skel))
        best_dist = float("inf")
        for root, root_tokens in root_cache:
            if abs(len(root_tokens) - skel_len) > 2:
                continue
            dist = weighted_levenshtein(
                skel, root, distances=distances,
                guttural_transparent=guttural_transparent,
            )
            if dist < best_dist:
                best_dist = dist
                if best_dist <= sorted_thresholds[0]:
                    break
        for t in thresholds:
            if best_dist <= t:
                counts[t] += 1
    return counts


def run_audit(
    iterations: int = 1000,
    seed: int | None = None,
    mode: str = "skeleton-permutation",
    guttural_transparent: bool = True,
    language: str = "nws",
    site_filter: set[str] | None = None,
    min_skeleton_len: int | None = None,
    frequency_class: str = "all",
    native_distances: bool = False,
    exclude_names: bool = False,
    length_class: str = "all",
) -> dict:
    if seed is None:
        seed = random.randint(0, 2**32 - 1)
    random.seed(seed)

    label = LANGUAGE_CONFIGS[language]["label"]

    print("Loading corpus skeletons...", file=sys.stderr)
    skeletons, corpus_meta = load_corpus_skeletons(
        site_filter=site_filter, frequency_class=frequency_class,
        length_class=length_class, min_skeleton_len=min_skeleton_len,
    )
    if frequency_class != "all":
        fb = corpus_meta["frequency_breakdown"]
        print(f"  Frequency class: {frequency_class} "
              f"(hapax={fb['hapax']}, repeated={fb['repeated']}, total={fb['total_unique']})",
              file=sys.stderr)
    if length_class != "all":
        print(f"  Length class: {length_class} ({len(skeletons)} skeletons)", file=sys.stderr)
    if min_skeleton_len and corpus_meta.get("min_skeleton_len_filtered", 0) > 0:
        print(f"  Min skeleton len: {min_skeleton_len} (excluded {corpus_meta['min_skeleton_len_filtered']} short skeletons)", file=sys.stderr)
    if site_filter:
        print(f"  Site filter: {sorted(site_filter)}", file=sys.stderr)
        print(f"  Inscriptions: {corpus_meta['filtered_inscriptions']}/{corpus_meta['total_inscriptions']}", file=sys.stderr)

    print(f"Loading {label} root database...", file=sys.stderr)
    real_roots, stats = load_roots(language, exclude_names=exclude_names)
    if exclude_names and stats["onomastic_filtered"] > 0:
        print(f"  Excluded {stats['onomastic_filtered']} onomastic entries (PN/GN/DN)", file=sys.stderr)

    print(f"Corpus: {len(skeletons)} skeletons", file=sys.stderr)
    print(f"{label} roots: {stats['total']} (2-{MAX_ROOT_LEN} consonants, "
          f"{stats['guttural_pct']:.1f}% guttural)", file=sys.stderr)
    print(f"Mode: {mode}", file=sys.stderr)

    dist_table = LANGUAGE_DISTANCE_TABLES.get(language) if native_distances else None
    dist_label = f"native ({language.upper()})" if native_distances and dist_table else "uniform (SEMITIC)"

    print(f"Seed: {seed}", file=sys.stderr)
    print(f"Guttural transparent: {guttural_transparent}", file=sys.stderr)
    print(f"Distance table: {dist_label}", file=sys.stderr)

    print(f"Scoring real {label} database...", file=sys.stderr)
    real_matches = count_matches_multi(skeletons, real_roots, THRESHOLDS,
                                       guttural_transparent=guttural_transparent,
                                       distances=dist_table)
    for t in THRESHOLDS:
        print(f"  threshold {t}: {real_matches[t]}/{len(skeletons)} "
              f"({real_matches[t]/len(skeletons)*100:.1f}%)", file=sys.stderr)

    random_matches: dict[float, list[int]] = {t: [] for t in THRESHOLDS}

    print(f"\nRunning {iterations} null model iterations...", file=sys.stderr)
    t0 = time.time()

    for i in range(iterations):
        if mode == "skeleton-permutation":
            synthetic_skeletons = generate_synthetic_skeletons(skeletons)
            multi = count_matches_multi(synthetic_skeletons, real_roots, THRESHOLDS,
                                        guttural_transparent=guttural_transparent,
                                        distances=dist_table)
        elif mode == "root-shuffle":
            shuffled = generate_shuffled_roots(real_roots)
            multi = count_matches_multi(skeletons, shuffled, THRESHOLDS,
                                        guttural_transparent=guttural_transparent,
                                        distances=dist_table)
        else:
            raise ValueError(f"Unknown mode: {mode}")

        for t in THRESHOLDS:
            random_matches[t].append(multi[t])

        if (i + 1) % 10 == 0:
            elapsed = time.time() - t0
            rate = (i + 1) / elapsed
            eta = (iterations - i - 1) / rate
            print(f"  {i+1}/{iterations} ({rate:.1f}/s, ETA {eta:.0f}s)", file=sys.stderr)

    total_time = time.time() - t0

    results = {}
    for t in THRESHOLDS:
        vals = random_matches[t]
        n = len(vals)
        mean = sum(vals) / n
        variance = sum((v - mean) ** 2 for v in vals) / max(n - 1, 1)
        std = math.sqrt(variance)
        real = real_matches[t]

        z_score = (real - mean) / std if std > 0 else float("inf")
        p_value = _z_to_p(z_score)
        cohens_d = (real - mean) / std if std > 0 else float("inf")

        # Bonferroni-adjusted significance (4 thresholds tested)
        bonferroni_sig = z_score > 2.50

        results[t] = {
            "real_matches": real,
            "real_pct": round(real / len(skeletons) * 100, 1),
            "random_mean": round(mean, 1),
            "random_std": round(std, 2),
            "random_min": min(vals),
            "random_max": max(vals),
            "random_p5": sorted(vals)[max(0, n // 20)],
            "random_p95": sorted(vals)[min(n - 1, n * 19 // 20)],
            "z_score": round(z_score, 2),
            "p_value": p_value,
            "significant": z_score > 2.0,
            "bonferroni_significant": bonferroni_sig,
            "cohens_d": round(cohens_d, 2),
        }

    result = {
        "language": language,
        "language_label": label,
        "mode": mode,
        "seed": seed,
        "guttural_transparent": guttural_transparent,
        "native_distances": native_distances,
        "frequency_class": frequency_class,
        "length_class": length_class,
        "exclude_names": exclude_names,
        "iterations": iterations,
        "corpus_skeletons": len(skeletons),
        "real_roots": stats["total"],
        "onomastic_filtered": stats.get("onomastic_filtered", 0),
        "guttural_pct": round(stats["guttural_pct"], 1),
        "thresholds": results,
        "elapsed_seconds": round(total_time, 1),
    }
    if corpus_meta.get("frequency_breakdown"):
        result["frequency_breakdown"] = corpus_meta["frequency_breakdown"]
    if corpus_meta.get("length_breakdown"):
        result["length_breakdown"] = corpus_meta["length_breakdown"]
    if corpus_meta.get("site_filter"):
        result["site_filter"] = corpus_meta["site_filter"]
        result["filtered_inscriptions"] = corpus_meta["filtered_inscriptions"]
        result["total_inscriptions"] = corpus_meta["total_inscriptions"]
    return result


def _z_to_p(z: float) -> float:
    """Approximate one-tailed p-value from Z-score."""
    if z == float("inf"):
        return 0.0
    if z < 0:
        return 1.0
    # Abramowitz and Stegun approximation
    t = 1.0 / (1.0 + 0.2316419 * abs(z))
    d = 0.3989422804014327
    p = d * math.exp(-z * z / 2.0) * t * (
        0.319381530 + t * (-0.356563782 + t * (1.781477937 + t * (-1.821255978 + t * 1.330274429)))
    )
    return round(p, 6)


def print_report(audit: dict) -> None:
    results = audit["thresholds"]
    n_skel = audit["corpus_skeletons"]
    mode = audit.get("mode", "skeleton-permutation")
    lang_label = audit.get("language_label", "NWS (Proto-Semitic)")

    mode_desc = {
        "skeleton-permutation": f"Shuffle corpus skeletons, match against real {lang_label} roots",
        "root-shuffle": f"Shuffle consonants within each {lang_label} root, match real skeletons",
    }

    print(f"Null Model Audit Results — {lang_label}")
    print("=" * 70)
    print(f"Language:         {lang_label}")
    print(f"Mode:             {mode}")
    print(f"                  {mode_desc.get(mode, mode)}")
    print(f"Iterations:       {audit['iterations']}")
    print(f"Corpus skeletons: {n_skel}")
    print(f"Real roots:       {audit['real_roots']} (2-{MAX_ROOT_LEN} consonants)")
    print(f"Seed:             {audit.get('seed', 'unknown')}")
    print(f"Guttural transp.: {audit.get('guttural_transparent', True)}")
    print(f"Guttural density: {audit['guttural_pct']:.1f}%")
    print(f"Elapsed:          {audit['elapsed_seconds']:.0f}s")
    print()

    short_label = audit.get("language", "nws").upper()
    for t in THRESHOLDS:
        r = results[str(t)] if isinstance(next(iter(results)), str) else results[t]
        sig = "✓ SIGNIFICANT" if r["significant"] else "✗ NOT SIGNIFICANT"
        print(f"Threshold ≤ {t}")
        print(f"  Real {short_label}:  {r['real_matches']:>4}/{n_skel} ({r['real_pct']:.1f}%)")
        print(f"  Random mean: {r['random_mean']:>7.1f} ± {r['random_std']:.2f}")
        print(f"  Random range: [{r['random_min']}, {r['random_max']}]  "
              f"(5th-95th: [{r['random_p5']}, {r['random_p95']}])")
        print(f"  Z-score:     {r['z_score']:>7.2f}  (p = {r['p_value']:.6f})")
        print(f"  Cohen's d:   {r.get('cohens_d', r['z_score']):>7.2f}")
        print(f"  Verdict:     {sig}")

        # ASCII histogram
        real = r["real_matches"]
        rmean = r["random_mean"]
        rmax = max(real, r["random_p95"]) + 5
        scale = 40 / rmax if rmax > 0 else 1
        bar_real = "█" * max(1, int(real * scale))
        bar_mean = "█" * max(1, int(rmean * scale))
        bar_p95 = "█" * max(1, int(r["random_p95"] * scale))
        print(f"  Real {short_label}:  |{bar_real}| {real}")
        print(f"  Random mean: |{bar_mean}| {r['random_mean']:.0f}")
        print(f"  Random 95th: |{bar_p95}| {r['random_p95']}")
        print()

    # Overall verdict
    mode = audit.get("mode", "skeleton-permutation")
    t05 = results[0.5] if 0.5 in results else results.get("0.5", {})
    if t05.get("significant"):
        print(f"OVERALL VERDICT ({mode}): {lang_label} match rate EXCEEDS random at the 0.5 threshold.")
        print("The framework's CANDIDATE tier is built on statistically significant signal.")
    else:
        z = t05.get("z_score", 0)
        print(f"OVERALL VERDICT ({mode}): {lang_label} match rate does NOT significantly exceed random (Z={z:.2f}).")
        print("Cross-language comparison needed — relative advantage may still be decisive.")


def run_cross_compare(
    iterations: int = 1000,
    seed: int | None = None,
    mode: str = "skeleton-permutation",
    guttural_transparent: bool = True,
    site_filter: set[str] | None = None,
    frequency_class: str = "all",
    native_distances: bool = False,
    exclude_names: bool = False,
    length_class: str = "all",
    min_skeleton_len: int | None = None,
) -> dict:
    """Run null model audit against all four language databases."""
    if seed is None:
        seed = random.randint(0, 2**32 - 1)

    t0 = time.time()
    languages = {}
    for lang in LANGUAGE_CONFIGS:
        print(f"\n{'='*70}", file=sys.stderr)
        print(f"Cross-compare: {LANGUAGE_CONFIGS[lang]['label']}", file=sys.stderr)
        print(f"{'='*70}", file=sys.stderr)
        languages[lang] = run_audit(
            iterations=iterations,
            seed=seed,
            mode=mode,
            guttural_transparent=guttural_transparent,
            language=lang,
            site_filter=site_filter,
            min_skeleton_len=min_skeleton_len,
            frequency_class=frequency_class,
            native_distances=native_distances,
            exclude_names=exclude_names,
            length_class=length_class,
        )
    total_time = time.time() - t0

    # Compute NWS advantage at each threshold
    comparison = {"best_at": {}}
    for t in THRESHOLDS:
        t_key = t
        z_scores = {}
        for lang, result in languages.items():
            r = result["thresholds"]
            val = r.get(t_key, r.get(str(t_key), {}))
            z_scores[lang] = val.get("z_score", 0)

        best_lang = max(z_scores, key=z_scores.get)
        others_max = max(z for l, z in z_scores.items() if l != "nws") if len(z_scores) > 1 else 0
        comparison["best_at"][str(t)] = {
            "best_language": best_lang,
            "best_z": round(z_scores[best_lang], 2),
            "nws_z": round(z_scores.get("nws", 0), 2),
            "nws_advantage": round(z_scores.get("nws", 0) - others_max, 2),
        }

    return {
        "mode": "cross-compare",
        "sub_mode": mode,
        "seed": seed,
        "guttural_transparent": guttural_transparent,
        "native_distances": native_distances,
        "frequency_class": frequency_class,
        "length_class": length_class,
        "exclude_names": exclude_names,
        "iterations": iterations,
        "languages": languages,
        "comparison": comparison,
        "elapsed_seconds": round(total_time, 1),
    }


def print_comparison(cross: dict) -> None:
    """Print human-readable cross-language comparison table."""
    languages = cross["languages"]
    comparison = cross["comparison"]

    print()
    freq_cls = cross.get("frequency_class", "all")
    freq_tag = f", freq={freq_cls}" if freq_cls != "all" else ""
    len_cls = cross.get("length_class", "all")
    len_tag = f", len={len_cls}" if len_cls != "all" else ""
    names_tag = ", excl-names" if cross.get("exclude_names") else ""
    print("Cross-Language Null Model Comparison")
    print(f"({cross['sub_mode']}, {cross['iterations']} iterations, "
          f"seed={cross.get('seed', '?')}, "
          f"gutturals={'ON' if cross.get('guttural_transparent', True) else 'OFF'}"
          f"{freq_tag}{len_tag}{names_tag})")
    print("=" * 78)
    print()

    # Header
    header = f"{'Language':<24}"
    for t in THRESHOLDS:
        header += f"{'≤ ' + str(t):>13}"
    print(header)
    print("-" * 78)

    # One row per language
    for lang in LANGUAGE_CONFIGS:
        result = languages[lang]
        label = LANGUAGE_CONFIGS[lang]["label"]
        n_roots = result["real_roots"]
        row = f"{label} ({n_roots})"
        row = f"{row:<24}"
        for t in THRESHOLDS:
            r = result["thresholds"]
            val = r.get(t, r.get(str(t), {}))
            z = val.get("z_score", 0)
            p = val.get("p_value", 1)
            sig = "*" if val.get("significant", False) else " "
            row += f"  Z={z:>5.2f}{sig} p={p:.3f}"
        print(row)

    print()
    print("-" * 78)

    # NWS advantage summary
    print("\nNWS Advantage (Z_NWS - max(Z_others)):")
    for t in THRESHOLDS:
        c = comparison["best_at"].get(str(t), {})
        adv = c.get("nws_advantage", 0)
        best = c.get("best_language", "?")
        marker = " ← NWS BEST" if best == "nws" else f" ← {LANGUAGE_CONFIGS.get(best, {}).get('label', best)} BEST"
        print(f"  ≤ {t}: {adv:+.2f}{marker}")

    # Overall verdict
    t05 = comparison["best_at"].get("0.5", {})
    t07 = comparison["best_at"].get("0.7", {})
    print()
    if t05.get("best_language") == "nws" and t07.get("best_language") == "nws":
        adv_05 = t05.get("nws_advantage", 0)
        adv_07 = t07.get("nws_advantage", 0)
        print("VERDICT: NWS is the best-fit language family.")
        print(f"  NWS advantage: +{adv_05:.2f} at ≤0.5, +{adv_07:.2f} at ≤0.7")
        print("  Even without standalone 2σ significance, the relative advantage")
        print("  over real competing languages strengthens the NWS hypothesis.")
    else:
        print("VERDICT: NWS is NOT the best-fit language family at all thresholds.")
        print("  Review results — a competing language may explain Linear A better.")

    print(f"\nTotal elapsed: {cross['elapsed_seconds']:.0f}s")


def save_run(audit: dict) -> Path:
    is_cross = audit.get("mode") == "cross-compare"
    lang = audit.get("language", "nws") if not is_cross else "cross-compare"
    label = lang
    if audit.get("mode") == "verb-lens-shuffle":
        label = "verb-lens"
    elif audit.get("mode") == "affix-doublet-shuffle":
        label = "affix-lens"

    params = {
        "mode": audit.get("sub_mode", audit.get("mode", "skeleton-permutation")),
        "language": lang,
        "iterations": audit["iterations"],
        "thresholds": THRESHOLDS,
        "max_root_len": MAX_ROOT_LEN,
        "frequency_class": audit.get("frequency_class", "all"),
        "length_class": audit.get("length_class", "all"),
        "exclude_names": audit.get("exclude_names", False),
    }
    if audit.get("mode") == "verb-lens-shuffle":
        # Template statuses change the default model — a verb-lens run is not
        # reproducible without the seed and the template set it actually used.
        params.update({
            "seed": audit.get("seed"),
            "include_speculative": audit.get("include_speculative", False),
            "match_threshold": audit.get("match_threshold"),
            "corpus_words": audit.get("corpus_words"),
            "template_penalties": audit.get("template_penalties", {}),
            "template_statuses": audit.get("template_statuses", {}),
        })
    elif audit.get("mode") == "affix-doublet-shuffle":
        params.update({
            "seed": audit.get("seed"),
            "template_file": audit.get("template_file"),
            "vocabulary_size": audit.get("vocabulary_size"),
            "template_statuses": audit.get("template_statuses", {}),
        })

    # For cross-compare, stringify all nested threshold keys
    save_data = dict(audit)
    if is_cross and "languages" in save_data:
        for result in save_data["languages"].values():
            if "thresholds" in result:
                result["thresholds"] = {str(k): v for k, v in result["thresholds"].items()}
    elif "thresholds" in save_data:
        save_data["thresholds"] = {str(k): v for k, v in save_data["thresholds"].items()}

    return run_saver.save_run("null-model-audit", params, save_data, label=label)


# ---------------------------------------------------------------------------
# Verb-lens calibration
#
# The verb lens (tools/core/verb_morphology.py) strips template-licensed affixes from
# transliterations before skeleton matching. Its false-positive risk lives at
# the SIGN level (JA-, TA-, U-NA- are frequent word-initial signs), so the
# consonant-pool shuffle used by the skeleton modes operates below the level
# the templates act on and cannot serve as its null. This mode instead
# permutes sign order WITHIN each word — preserving every word's own sign
# inventory and length — and runs the deparser on both sides. Signal is
# real-only enrichment: templates that fire and match roots on real word
# forms but not on sign-shuffled forms are capturing positional morphology;
# templates that fire equally on shuffled forms are capturing sign frequency.
# ---------------------------------------------------------------------------

VERB_LENS_MATCH_THRESHOLD = 0.5  # per-template match reporting threshold


def load_corpus_words() -> list[str]:
    """Load unique multi-sign corpus transliterations.

    Unlike the skeleton loaders, words with a leading numbered sign are kept:
    recognized syllabograms like *28B and *301 are parseable and excluding
    them would make templates anchored on them (yi_28b_prefix) impossible to
    calibrate. Words the deparser cannot parse (logogram sequences, lacunae,
    unknown signs) enter the list but are skipped symmetrically on the real
    and shuffled sides, so they cannot bias the enrichment measurement.
    """
    corpus_path = require(LINEAR_A_DATA / "corpus.json", "corpus.json")
    corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
    words = set()
    for inscription in corpus.values():
        for w in inscription.get("transliteratedWords", []):
            if "-" in w and not w.replace("-", "").isdigit():
                words.add(w)
    return sorted(words)


def shuffle_word_signs(word: str) -> str:
    """Permute sign order within one transliteration (the verb-lens null unit)."""
    signs = word.split("-")
    random.shuffle(signs)
    return "-".join(signs)


def _r2_collapse(skeleton: str) -> str:
    """Collapse adjacent duplicate phonemes (mirrors the production
    _verb_lens_candidates R2-collapse for geminate-template parses)."""
    tokens = _tokenize_phonemes(skeleton)
    if not tokens:
        return skeleton
    out = [tokens[0]]
    for t in tokens[1:]:
        if t != out[-1]:
            out.append(t)
    return "".join(out)


def _verb_lens_pass(
    words: list[str],
    root_cache: list[tuple[str, list[str]]],
    dist_cache: dict[str, float],
    include_speculative: bool = False,
    geminate_template_ids: frozenset[str] = frozenset(),
) -> dict:
    """Run the deparser over a word list and match residuals against roots.

    Returns per-pass counts: words parsed, per-template fire/match counts
    (a word counts once per template regardless of parse multiplicity), and
    joint matched-word counts at each threshold (any parse's residual within
    threshold of any root — mirrors 'word gains a lens candidate' semantics).

    Geminate-template parses are also scored on their R2-collapsed skeleton,
    matching production candidate generation (an audit that skipped the
    collapse would under-measure d_ja_geminate exactly where --verb-lens
    finds matches). Broader morphophonological composition (iii-weak strips
    etc.) remains outside the audit — a stated limitation, applied equally
    to real and shuffled sides.
    """
    from ...core.verb_morphology import verbal_parses

    def best_dist(skel: str) -> float:
        d = dist_cache.get(skel)
        if d is None:
            n = len(_tokenize_phonemes(skel))
            d = float("inf")
            for root, toks in root_cache:
                if abs(len(toks) - n) > 2:
                    continue
                cand = weighted_levenshtein(skel, root, guttural_transparent=True)
                if cand < d:
                    d = cand
                    # Early break is safe because only threshold indicator
                    # functions consume this value and 0.3 is the lowest
                    # threshold reported; it would be unsafe if exact minima
                    # were ever reported directly.
                    if d <= min(THRESHOLDS):
                        break
            dist_cache[skel] = d
        return d

    parsed = 0
    fires: Counter = Counter()
    tmpl_matched: Counter = Counter()
    joint = {t: 0 for t in THRESHOLDS}

    for w in words:
        parses = verbal_parses(w, include_speculative=include_speculative)
        if not parses:
            continue
        parsed += 1
        word_best = float("inf")
        fired: set[str] = set()
        tmpl_best: dict[str, float] = {}
        for p in parses:
            d = best_dist(p.residual_skeleton)
            if geminate_template_ids and any(r in geminate_template_ids for r in p.rules):
                collapsed = _r2_collapse(p.residual_skeleton)
                if collapsed != p.residual_skeleton:
                    d = min(d, best_dist(collapsed))
            word_best = min(word_best, d)
            for rule_id in p.rules:
                fired.add(rule_id)
                tmpl_best[rule_id] = min(tmpl_best.get(rule_id, float("inf")), d)
        fires.update(fired)
        for t in THRESHOLDS:
            if word_best <= t:
                joint[t] += 1
        for rule_id, d in tmpl_best.items():
            if d <= VERB_LENS_MATCH_THRESHOLD:
                tmpl_matched[rule_id] += 1

    return {"parsed": parsed, "fires": fires, "tmpl_matched": tmpl_matched, "joint": joint}


def _null_summary(real_val: int, vals: list[int]) -> dict:
    """Real-vs-null summary statistics for one counter.

    `relation` disambiguates the zero-variance cases a z-score cannot
    (real above / equal to / below a degenerate null distribution), and
    `empirical_p` is the one-tailed add-one permutation p-value whose floor
    1/(n+1) is honest about what a finite permutation test can resolve.
    """
    n = len(vals)
    mean = sum(vals) / n
    variance = sum((v - mean) ** 2 for v in vals) / max(n - 1, 1)
    std = math.sqrt(variance)
    relation = "above" if real_val > mean else ("equal" if real_val == mean else "below")
    z = (real_val - mean) / std if std > 0 else None
    empirical_p = (1 + sum(1 for v in vals if v >= real_val)) / (n + 1)
    p95_idx = max(0, math.ceil(0.95 * n) - 1)  # nearest-rank
    return {
        "real": real_val,
        "null_mean": round(mean, 1),
        "null_std": round(std, 2),
        "null_p95": sorted(vals)[p95_idx],
        "z_score": round(z, 2) if z is not None else None,
        "relation": relation,
        "p_value": _z_to_p(z) if z is not None else None,
        "empirical_p": round(empirical_p, 6),
        "enrichment": round(real_val / mean, 2) if mean > 0 else None,
    }


def run_verb_lens_audit(
    iterations: int = 1000,
    seed: int | None = None,
    include_speculative: bool = False,
    words: list[str] | None = None,
) -> dict:
    """Real-vs-shuffled calibration of the verb-morphology lens.

    Lens ON both sides; the null permutes sign order within each word.
    Reports joint inflation (the penalty-recalibration target) and
    per-template inflation in the guttural_audit critical/influenced style.
    """
    from ...core.verb_morphology import load_templates

    if seed is None:
        seed = random.randint(0, 2**32 - 1)
    random.seed(seed)

    if words is None:
        print("Loading corpus transliterations...", file=sys.stderr)
        words = load_corpus_words()
    print(f"Corpus words: {len(words)}", file=sys.stderr)

    real_roots, stats = load_roots("nws")
    root_cache = [(r, _tokenize_phonemes(r)) for r in real_roots]
    print(f"NWS roots: {stats['total']}", file=sys.stderr)

    templates = [
        t for t in load_templates()
        if t.status == "active" or include_speculative
    ]
    template_ids = [t.id for t in templates]
    penalties = {t.id: t.penalty for t in templates}
    statuses = {t.id: t.status for t in templates}
    geminate_ids = frozenset(t.id for t in templates if t.require_geminate)
    print(f"Templates: {len(templates)} "
          f"({'active+speculative' if include_speculative else 'active only'})",
          file=sys.stderr)
    print(f"Seed: {seed}", file=sys.stderr)

    dist_cache: dict[str, float] = {}

    print("Scoring real corpus with lens ON...", file=sys.stderr)
    real = _verb_lens_pass(words, root_cache, dist_cache, include_speculative,
                           geminate_template_ids=geminate_ids)
    print(f"  parsed {real['parsed']}/{len(words)}, "
          f"matched@{VERB_LENS_MATCH_THRESHOLD}: {real['joint'][VERB_LENS_MATCH_THRESHOLD]}",
          file=sys.stderr)

    null_parsed: list[int] = []
    null_joint: dict[float, list[int]] = {t: [] for t in THRESHOLDS}
    null_fires: dict[str, list[int]] = {tid: [] for tid in template_ids}
    null_matched: dict[str, list[int]] = {tid: [] for tid in template_ids}

    print(f"\nRunning {iterations} sign-shuffle null iterations...", file=sys.stderr)
    t0 = time.time()
    for i in range(iterations):
        shuffled = [shuffle_word_signs(w) for w in words]
        null = _verb_lens_pass(shuffled, root_cache, dist_cache, include_speculative,
                               geminate_template_ids=geminate_ids)
        null_parsed.append(null["parsed"])
        for t in THRESHOLDS:
            null_joint[t].append(null["joint"][t])
        for tid in template_ids:
            null_fires[tid].append(null["fires"].get(tid, 0))
            null_matched[tid].append(null["tmpl_matched"].get(tid, 0))
        if (i + 1) % 50 == 0:
            elapsed = time.time() - t0
            rate = (i + 1) / elapsed
            eta = (iterations - i - 1) / rate
            print(f"  {i+1}/{iterations} ({rate:.1f}/s, ETA {eta:.0f}s)", file=sys.stderr)
    total_time = time.time() - t0

    _summary = _null_summary

    joint_results = {
        str(t): _summary(real["joint"][t], null_joint[t]) for t in THRESHOLDS
    }

    per_template = {}
    for tid in template_ids:
        fires_summary = _summary(real["fires"].get(tid, 0), null_fires[tid])
        match_summary = _summary(real["tmpl_matched"].get(tid, 0), null_matched[tid])
        real_m = match_summary["real"]
        z = match_summary["z_score"]
        ratio = match_summary["enrichment"]
        if real_m >= 3 and z is not None and z >= 2.0:
            verdict = "ENRICHED"       # positional morphology signal above chance
        elif z is not None and z <= -1.5:
            verdict = "ANTI-ENRICHED"  # matches shuffled words better than real ones
        elif real_m < 3:
            verdict = "SPARSE"         # too few real matches to calibrate either way
        elif ratio is not None and ratio < 1.2:
            verdict = "INFLATED"       # fires as readily on shuffled words: sign frequency
        else:
            verdict = "NEUTRAL"
        per_template[tid] = {
            "penalty": penalties[tid],
            "status": statuses[tid],
            "fires": fires_summary,
            "matched": match_summary,
            "verdict": verdict,
        }

    return {
        "mode": "verb-lens-shuffle",
        "language": "nws",
        "language_label": LANGUAGE_CONFIGS["nws"]["label"],
        "seed": seed,
        "include_speculative": include_speculative,
        "iterations": iterations,
        "corpus_words": len(words),
        "real_roots": stats["total"],
        "match_threshold": VERB_LENS_MATCH_THRESHOLD,
        "template_penalties": penalties,
        "template_statuses": statuses,
        "parse_rate": _summary(real["parsed"], null_parsed),
        "joint": joint_results,
        "per_template": per_template,
        "elapsed_seconds": round(total_time, 1),
    }


def print_verb_lens_report(audit: dict) -> None:
    n_words = audit["corpus_words"]
    print("Verb-Lens Null Calibration — sign-shuffle within words")
    print("=" * 74)
    print(f"Corpus words:     {n_words}")
    print(f"NWS roots:        {audit['real_roots']}")
    print(f"Iterations:       {audit['iterations']}")
    print(f"Seed:             {audit['seed']}")
    print(f"Templates:        {'active+speculative' if audit['include_speculative'] else 'active only'}")
    print(f"Elapsed:          {audit['elapsed_seconds']:.0f}s")
    print()

    pr = audit["parse_rate"]
    print(f"Parse rate:  real {pr['real']}/{n_words}  "
          f"null {pr['null_mean']} ± {pr['null_std']}  "
          f"Z={pr['z_score']}  enrichment ×{pr['enrichment']}")
    print()

    print("Joint inflation (any template, word matched at threshold):")
    for t_key, r in audit["joint"].items():
        z = f"{r['z_score']}" if r["z_score"] is not None else r["relation"]
        print(f"  ≤ {t_key}: real {r['real']:>3}  null {r['null_mean']:>6.1f} ± {r['null_std']:<6.2f} "
              f"(p95 {r['null_p95']})  Z={z}  emp-p={r['empirical_p']:.6f}  ×{r['enrichment']}")
    print()

    print(f"Per-template calibration (matched at ≤ {audit['match_threshold']}):")
    header = (f"  {'template':<18}{'pen':>5}{'fires R/N':>12}{'match R/N':>12}"
              f"{'Z':>7}{'ratio':>7}  verdict")
    print(header)
    print("  " + "-" * (len(header) - 2))
    def _sort_z(kv):
        m = kv[1]["matched"]
        z = m["z_score"]
        if z is not None:
            return -z
        # zero null variance: sort by relation (above-null first, below-null last)
        return {"above": -999.0, "equal": 500.0, "below": 999.0}[m["relation"]]

    for tid, r in sorted(audit["per_template"].items(), key=_sort_z):
        f, m = r["fires"], r["matched"]
        z = f"{m['z_score']:.2f}" if m["z_score"] is not None else m["relation"]
        ratio = f"{m['enrichment']:.2f}" if m["enrichment"] is not None else "—"
        print(f"  {tid:<18}{r['penalty']:>5.2f}"
              f"{f['real']:>6}/{f['null_mean']:<5.1f}"
              f"{m['real']:>6}/{m['null_mean']:<5.1f}"
              f"{z:>7}{ratio:>7}  {r['verdict']}")
    print()

    j05 = audit["joint"]["0.5"]
    if (j05["z_score"] is not None and j05["z_score"] >= 2.0) or (
            j05["z_score"] is None and j05["relation"] == "above"):
        print(f"OVERALL VERDICT: lens matches on real word forms EXCEED the sign-shuffle "
              f"null at ≤0.5 (Z={j05['z_score']}, emp-p={j05['empirical_p']:.6f}, ×{j05['enrichment']}).")
        print("Positional verbal morphology carries signal beyond sign frequency.")
    else:
        print(f"OVERALL VERDICT: lens matches do NOT exceed the sign-shuffle null "
              f"(Z={j05['z_score']} at ≤0.5, emp-p={j05['empirical_p']:.6f}).")
        print("Templates are matching sign frequency, not morphology — keep the lens OFF.")
    print("Note: when the active template set was itself recalibrated from this corpus,")
    print("treat the joint statistic as descriptive of the recalibrated instrument —")
    print("the a-priori anchor templates carry the confirmatory weight.")


# ---------------------------------------------------------------------------
# Affix-lens calibration
#
# The affix-doublet miner (tools/linear_a/analysis/affix_doublet_miner.py) counts
# corpus pairs where a base word and its affixed form are BOTH independently
# attested. Its false-positive risk is sign frequency: a common final sign
# will "pair" words by chance. The null permutes sign order within each
# vocabulary word — same instrument as --verb-lens — and recounts pairs.
# Templates that pair on real word forms but not on sign-shuffled forms are
# capturing positional morphology; templates that pair equally on shuffled
# forms are capturing sign frequency.
# ---------------------------------------------------------------------------


def run_affix_lens_audit(
    iterations: int = 1000,
    seed: int | None = None,
    template_file: Path | None = None,
    vocab: list[str] | None = None,
) -> dict:
    """Real-vs-shuffled calibration of the affix-doublet miner.

    Every affix template is calibrated regardless of status — the inventory
    lands all-speculative by design, and this audit is the measurement that
    moves penalties (verb-lens recalibration precedent).
    """
    from ..analysis.affix_doublet_miner import (
        count_template_pairs,
        load_affix_templates,
        load_corpus_vocab,
    )

    if seed is None:
        seed = random.randint(0, 2**32 - 1)
    random.seed(seed)

    if vocab is None:
        print("Loading corpus vocabulary...", file=sys.stderr)
        vocab = load_corpus_vocab()
    print(f"Vocabulary: {len(vocab)} unique undamaged word forms", file=sys.stderr)

    templates = load_affix_templates(template_file)
    print(f"Templates: {len(templates)}", file=sys.stderr)
    print(f"Seed: {seed}", file=sys.stderr)

    real_counts = {t["id"]: count_template_pairs(vocab, t) for t in templates}

    null_counts: dict[str, list[int]] = {t["id"]: [] for t in templates}
    print(f"\nRunning {iterations} sign-shuffle null iterations...", file=sys.stderr)
    t0 = time.time()
    for i in range(iterations):
        shuffled = [shuffle_word_signs(w) for w in vocab]
        for t in templates:
            null_counts[t["id"]].append(count_template_pairs(shuffled, t))
        if (i + 1) % 100 == 0:
            elapsed = time.time() - t0
            rate = (i + 1) / elapsed
            eta = (iterations - i - 1) / rate
            print(f"  {i+1}/{iterations} ({rate:.1f}/s, ETA {eta:.0f}s)", file=sys.stderr)
    total_time = time.time() - t0

    per_template = {}
    for t in templates:
        tid = t["id"]
        pair_summary = _null_summary(real_counts[tid], null_counts[tid])
        real_p = pair_summary["real"]
        z = pair_summary["z_score"]
        ratio = pair_summary["enrichment"]
        if real_p >= 3 and (
                (z is not None and z >= 2.0)
                or (z is None and pair_summary["relation"] == "above")):
            verdict = "ENRICHED"       # positional morphology signal above chance
        elif z is not None and z <= -1.5:
            verdict = "ANTI-ENRICHED"  # pairs assemble more readily on shuffled forms
        elif real_p < 3:
            verdict = "SPARSE"         # too few real pairs to calibrate either way
        elif ratio is not None and ratio < 1.2:
            verdict = "INFLATED"       # pairs as readily on shuffled forms: sign frequency
        else:
            verdict = "NEUTRAL"
        per_template[tid] = {
            "family": t.get("family"),
            "penalty": t["penalty"],
            "status": t["status"],
            "position": t["affix"]["position"],
            "pairs": pair_summary,
            "confounds": t.get("confounds", []),
            "verdict": verdict,
        }

    return {
        "mode": "affix-doublet-shuffle",
        "seed": seed,
        "iterations": iterations,
        "template_file": str(template_file) if template_file else "data/affix_templates.json",
        "vocabulary_size": len(vocab),
        "statistic": "both-members-attested doublet pairs (final_vowel: alternating stems)",
        "template_statuses": {t["id"]: t["status"] for t in templates},
        "per_template": per_template,
        "one_sided_isogloss_caveat": (
            "The *s > *h isogloss test is one-sided: post-shift -hu/-ha with the h "
            "dropped surfaces as bare final vowels, indistinguishable from case "
            "vowels. Enriched -SU/-SA pairs are evidence of pre-shift retention; "
            "their absence is NOT evidence of post-shift innovation."
        ),
        "elapsed_seconds": round(total_time, 1),
    }


def print_affix_lens_report(audit: dict) -> None:
    print("Affix-Lens Null Calibration — sign-shuffle within words, doublet pair counts")
    print("=" * 78)
    print(f"Vocabulary:       {audit['vocabulary_size']} unique undamaged word forms")
    print(f"Template file:    {audit['template_file']}")
    print(f"Iterations:       {audit['iterations']}")
    print(f"Seed:             {audit['seed']}")
    print(f"Statistic:        {audit['statistic']}")
    print(f"Elapsed:          {audit['elapsed_seconds']:.0f}s")
    print()

    header = (f"  {'template':<16}{'family':<12}{'pos':<13}{'pairs R/N':>12}"
              f"{'Z':>8}{'emp-p':>10}{'ratio':>7}  verdict")
    print(header)
    print("  " + "-" * (len(header) - 2))

    def _sort_z(kv):
        p = kv[1]["pairs"]
        z = p["z_score"]
        if z is not None:
            return -z
        return {"above": -999.0, "equal": 500.0, "below": 999.0}[p["relation"]]

    for tid, r in sorted(audit["per_template"].items(), key=_sort_z):
        p = r["pairs"]
        z = f"{p['z_score']:.2f}" if p["z_score"] is not None else p["relation"]
        ratio = f"{p['enrichment']:.2f}" if p["enrichment"] is not None else "—"
        print(f"  {tid:<16}{r['family']:<12}{r['position']:<13}"
              f"{p['real']:>5}/{p['null_mean']:<6.1f}"
              f"{z:>8}{p['empirical_p']:>10.6f}{ratio:>7}  {r['verdict']}")
    print()
    print("NOTE: " + audit["one_sided_isogloss_caveat"])


# ---------------------------------------------------------------------------
# Historical-metathesis lens calibration
#
# --historical-lens (cognate_search.HISTORICAL_METATHESIS_RULES) adds
# attested-metathesis skeleton variants (ṯr↔rṯ, ml↔lm, wl↔lw; Rendsburg 2022)
# to the Semitic searches. Its false-positive risk lives at the skeleton
# level: any tr/rt-bearing word gains a second lookup. The null permutes
# consonant order WITHIN each skeleton — preserving inventory and length —
# and measures LENS-ONLY GAIN on both sides: words whose surface skeleton
# misses at a threshold but whose swapped variant (penalty included) hits.
# A swap of a shuffled skeleton is just another shuffle of the same
# consonants, so chance-level gain is fully represented in the null;
# real-only enrichment means real sign order metathesizes onto roots above
# chance. With every rule penalty ≥ 0.35, gains at the 0.3 threshold are
# impossible by construction — the CANDIDATE gate, made visible.
# ---------------------------------------------------------------------------

METATHESIS_LENS_MATCH_THRESHOLD = 0.5


def _metathesis_pass(
    skeletons: list[str],
    root_cache: list[tuple[str, list[str]]],
    dist_cache: dict[str, float],
) -> dict:
    """Score one skeleton list: how many words gain a root match ONLY via a
    registered metathesis variant (surface misses the threshold, swapped
    variant + penalty clears it).

    Unlike _verb_lens_pass, best_dist keeps exact minima (early break only
    at 0.0): the lens comparison adds the rule penalty to the variant
    distance, so an approximate sub-0.3 minimum would misclassify at the
    0.5 threshold.
    """
    from ..cognate_search import _generate_historical_skeletons

    def best_dist(skel: str) -> float:
        d = dist_cache.get(skel)
        if d is None:
            n = len(_tokenize_phonemes(skel))
            d = float("inf")
            for root, toks in root_cache:
                if abs(len(toks) - n) > 2:
                    continue
                cand = weighted_levenshtein(skel, root, guttural_transparent=True)
                if cand < d:
                    d = cand
                    if d <= 0.0:
                        break
            dist_cache[skel] = d
        return d

    with_variants = 0
    gained = {t: 0 for t in THRESHOLDS}
    rule_gained: Counter = Counter()

    for skel in skeletons:
        variants = _generate_historical_skeletons(skel)
        if not variants:
            continue
        with_variants += 1
        surface = best_dist(skel)
        lens_best, lens_rule = float("inf"), None
        for v, penalty, rule in variants:
            eff = best_dist(v) + penalty
            if eff < lens_best:
                lens_best, lens_rule = eff, rule
        for t in THRESHOLDS:
            if lens_best <= t < surface:
                gained[t] += 1
        if (lens_best <= METATHESIS_LENS_MATCH_THRESHOLD
                < surface and lens_rule is not None):
            rule_gained[lens_rule] += 1

    return {"with_variants": with_variants, "gained": gained,
            "rule_gained": rule_gained}


def run_metathesis_lens_audit(
    iterations: int = 1000,
    seed: int | None = None,
) -> dict:
    """Real-vs-shuffled calibration of --historical-lens.

    Lens ON both sides; the null shuffles consonant order within each
    corpus skeleton. Reports lens-only gain inflation per threshold and
    per registered rule.
    """
    from ..cognate_search import HISTORICAL_METATHESIS_RULES

    if seed is None:
        seed = random.randint(0, 2**32 - 1)
    random.seed(seed)

    print("Loading corpus skeletons...", file=sys.stderr)
    skeletons, _corpus_meta = load_corpus_skeletons()
    print(f"Corpus skeletons: {len(skeletons)}", file=sys.stderr)

    real_roots, stats = load_roots("nws")
    root_cache = [(r, _tokenize_phonemes(r)) for r in real_roots]
    print(f"NWS roots: {stats['total']}", file=sys.stderr)
    print(f"Seed: {seed}", file=sys.stderr)

    dist_cache: dict[str, float] = {}

    print("Scoring real corpus with lens ON...", file=sys.stderr)
    real = _metathesis_pass(skeletons, root_cache, dist_cache)
    print(f"  variant-bearing {real['with_variants']}/{len(skeletons)}, "
          f"lens-only gain@{METATHESIS_LENS_MATCH_THRESHOLD}: "
          f"{real['gained'][METATHESIS_LENS_MATCH_THRESHOLD]}", file=sys.stderr)

    rule_names = [r["rule"] for r in HISTORICAL_METATHESIS_RULES]
    null_with: list[int] = []
    null_gained: dict[float, list[int]] = {t: [] for t in THRESHOLDS}
    null_rule: dict[str, list[int]] = {rn: [] for rn in rule_names}

    tokenized = [_tokenize_phonemes(s) for s in skeletons]
    print(f"\nRunning {iterations} within-skeleton shuffle iterations...", file=sys.stderr)
    t0 = time.time()
    for i in range(iterations):
        shuffled = ["".join(random.sample(toks, len(toks))) for toks in tokenized]
        null = _metathesis_pass(shuffled, root_cache, dist_cache)
        null_with.append(null["with_variants"])
        for t in THRESHOLDS:
            null_gained[t].append(null["gained"][t])
        for rn in rule_names:
            null_rule[rn].append(null["rule_gained"].get(rn, 0))
        if (i + 1) % 10 == 0:
            elapsed = time.time() - t0
            rate = (i + 1) / elapsed
            eta = (iterations - i - 1) / rate
            print(f"  {i+1}/{iterations} ({rate:.1f}/s, ETA {eta:.0f}s)", file=sys.stderr)
    total_time = time.time() - t0

    per_rule = {}
    for rule in HISTORICAL_METATHESIS_RULES:
        rn = rule["rule"]
        summary = _null_summary(real["rule_gained"].get(rn, 0), null_rule[rn])
        real_g = summary["real"]
        z = summary["z_score"]
        if real_g >= 3 and z is not None and z >= 2.0:
            verdict = "ENRICHED"
        elif real_g < 3:
            verdict = "SPARSE"
        elif summary["enrichment"] is not None and summary["enrichment"] < 1.2:
            verdict = "INFLATED"
        else:
            verdict = "NEUTRAL"
        per_rule[rn] = {
            "penalty": rule["penalty"],
            "source": rule["source"],
            "gained": summary,
            "verdict": verdict,
        }

    return {
        "mode": "metathesis-lens-shuffle",
        "language": "nws",
        "language_label": LANGUAGE_CONFIGS["nws"]["label"],
        "seed": seed,
        "iterations": iterations,
        "corpus_skeletons": len(skeletons),
        "real_roots": stats["total"],
        "match_threshold": METATHESIS_LENS_MATCH_THRESHOLD,
        "variant_rate": _null_summary(real["with_variants"], null_with),
        "gained": {str(t): _null_summary(real["gained"][t], null_gained[t])
                   for t in THRESHOLDS},
        "per_rule": per_rule,
        "elapsed_seconds": round(total_time, 1),
    }


def print_metathesis_lens_report(audit: dict) -> None:
    n = audit["corpus_skeletons"]
    print("Historical-Metathesis Lens Calibration — within-skeleton shuffle")
    print("=" * 74)
    print(f"Corpus skeletons: {n}")
    print(f"NWS roots:        {audit['real_roots']}")
    print(f"Iterations:       {audit['iterations']}")
    print(f"Seed:             {audit['seed']}")
    print(f"Elapsed:          {audit['elapsed_seconds']:.0f}s")
    print()
    vr = audit["variant_rate"]
    print(f"Variant-bearing words: real {vr['real']}/{n}  "
          f"null {vr['null_mean']} ± {vr['null_std']}")
    print()
    print("Lens-only gain (surface misses threshold, swapped variant + penalty hits):")
    for t_key, r in audit["gained"].items():
        z = f"{r['z_score']}" if r["z_score"] is not None else r["relation"]
        ratio = f"×{r['enrichment']}" if r["enrichment"] is not None else "—"
        print(f"  ≤ {t_key}: real {r['real']:>3}  null {r['null_mean']:>6.1f} ± {r['null_std']:<6.2f} "
              f"(p95 {r['null_p95']})  Z={z}  emp-p={r['empirical_p']:.6f}  {ratio}")
    print()
    print(f"Per-rule gain at ≤ {audit['match_threshold']}:")
    for rn, r in audit["per_rule"].items():
        g = r["gained"]
        z = f"{g['z_score']}" if g["z_score"] is not None else g["relation"]
        print(f"  {rn:<20} pen {r['penalty']:.2f}  real {g['real']:>3}  "
              f"null {g['null_mean']:>5.1f} ± {g['null_std']:<5.2f}  Z={z}  {r['verdict']}")
        print(f"    {r['source']}")


def main() -> int:
    """Exit 2 with the file's name when a data file is not in the checkout."""
    try:
        _run()
    except NotInCheckout as e:
        print(f"stopped: {e}", file=sys.stderr)
        return 2
    return 0


def _run():
    parser = argparse.ArgumentParser(description="Null Model Audit")
    parser.add_argument("--iterations", type=int, default=1000,
                        help="Number of null model iterations (default: 1000)")
    parser.add_argument("--quick", action="store_true",
                        help="Quick mode: 50 iterations for sanity check")
    parser.add_argument("--mode", choices=["skeleton-permutation", "root-shuffle"],
                        default="skeleton-permutation",
                        help="Null model type (default: skeleton-permutation)")
    parser.add_argument("--language",
                        choices=["nws", "luwian", "egyptian", "hurrian", "cross-compare"],
                        default="nws",
                        help="Root database to test against (default: nws)")
    parser.add_argument("--no-gutturals", action="store_true",
                        help="Disable guttural transparency (test without the 0.1 cost)")
    parser.add_argument("--site-class",
                        choices=["peak_sanctuary", "palace", "town", "cycladic",
                                 "funerary", "levantine", "all"],
                        default="all",
                        help="Filter corpus by archaeological site class (default: all)")
    parser.add_argument("--site-filter", type=str, default=None,
                        help="Comma-separated site names to include (overrides --site-class)")
    parser.add_argument("--frequency-class",
                        choices=["all", "hapax", "repeated"],
                        default="all",
                        help="Filter corpus by word frequency: hapax (1x), repeated (2+x), all (default)")
    parser.add_argument("--native-distances", action="store_true",
                        help="Use language-specific distance tables (LUWIAN_DISTANCES, etc.)")
    parser.add_argument("--exclude-names", action="store_true",
                        help="Exclude onomastic entries (PN/GN/DN) from root databases")
    parser.add_argument("--length-class",
                        choices=["all", "short", "medium", "long"],
                        default="all",
                        help="Filter corpus skeletons by consonant length: short (1-2), medium (3), long (4+)")
    parser.add_argument("--min-skeleton-len", type=int, default=None,
                        help="Minimum consonant count for corpus skeletons. "
                             "Use 3 for content-word-only filtering (excludes particles/prepositions)")
    parser.add_argument("--verb-lens", action="store_true",
                        help="Calibrate the verb-morphology lens against a "
                             "sign-shuffle-within-word null. NWS roots only.")
    parser.add_argument("--include-speculative", action="store_true",
                        help="Include speculative-tier templates in --verb-lens calibration")
    parser.add_argument("--affix-lens", action="store_true",
                        help="Calibrate the affix-doublet miner against a "
                             "sign-shuffle-within-word null (pair-count statistic)")
    parser.add_argument("--metathesis-lens", action="store_true",
                        help="Calibrate --historical-lens (attested-metathesis skeleton "
                             "variants) against a within-skeleton consonant-shuffle null. "
                             "NWS roots only.")
    parser.add_argument("--template-file", type=Path, default=None,
                        help="Affix-template JSON for --affix-lens "
                             "(default: data/affix_templates.json)")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--save", action="store_true", help="Save run to data/runs/")
    parser.add_argument("--seed", type=int, default=None,
                        help="Random seed for reproducibility")
    args = parser.parse_args()

    frequency_class = args.frequency_class

    iterations = 50 if args.quick else args.iterations

    if args.include_speculative and not args.verb_lens:
        parser.error("--include-speculative only applies to --verb-lens calibration")

    if args.template_file and not args.affix_lens:
        parser.error("--template-file only applies to --affix-lens calibration")

    if args.affix_lens:
        if args.verb_lens:
            parser.error("--affix-lens and --verb-lens are separate calibrations")
        if args.language not in ("nws",):
            parser.error("--affix-lens mines corpus-internal doublets; "
                         "--language does not apply")
        for flag, default in (("mode", "skeleton-permutation"), ("site_class", "all"),
                              ("frequency_class", "all"), ("length_class", "all"),
                              ("site_filter", None), ("min_skeleton_len", None),
                              ("exclude_names", False), ("no_gutturals", False),
                              ("native_distances", False)):
            if getattr(args, flag) != default:
                parser.error(f"--affix-lens does not compose with --{flag.replace('_', '-')}")
        if iterations < 2:
            parser.error("--affix-lens needs at least 2 iterations "
                         "(sample standard deviation is undefined below that)")
        audit = run_affix_lens_audit(
            iterations=iterations,
            seed=args.seed,
            template_file=args.template_file,
        )
        if args.json:
            print(json.dumps(audit, indent=2, ensure_ascii=False))
        else:
            print_affix_lens_report(audit)
        if args.save:
            run_dir = save_run(audit)
            print(f"\nRun saved to: {run_dir}", file=sys.stderr)
        return

    if args.metathesis_lens:
        if args.verb_lens or args.affix_lens:
            parser.error("--metathesis-lens is a separate calibration")
        if args.language not in ("nws",):
            parser.error("--metathesis-lens calibrates against NWS roots only "
                         "(the lens models attested Semitic metathesis)")
        for flag, default in (("mode", "skeleton-permutation"), ("site_class", "all"),
                              ("frequency_class", "all"), ("length_class", "all"),
                              ("site_filter", None), ("min_skeleton_len", None),
                              ("exclude_names", False), ("no_gutturals", False),
                              ("native_distances", False)):
            if getattr(args, flag) != default:
                parser.error(f"--metathesis-lens does not compose with --{flag.replace('_', '-')}")
        if iterations < 2:
            parser.error("--metathesis-lens needs at least 2 iterations "
                         "(sample standard deviation is undefined below that)")
        audit = run_metathesis_lens_audit(iterations=iterations, seed=args.seed)
        if args.json:
            print(json.dumps(audit, indent=2, ensure_ascii=False))
        else:
            print_metathesis_lens_report(audit)
        if args.save:
            run_dir = save_run(audit)
            print(f"\nRun saved to: {run_dir}", file=sys.stderr)
        return

    if args.verb_lens:
        if args.language not in ("nws",):
            parser.error("--verb-lens calibrates against NWS roots only "
                         "(the lens models Semitic verbal morphology)")
        for flag, default in (("mode", "skeleton-permutation"), ("site_class", "all"),
                              ("frequency_class", "all"), ("length_class", "all"),
                              ("site_filter", None), ("min_skeleton_len", None),
                              ("exclude_names", False), ("no_gutturals", False),
                              ("native_distances", False)):
            if getattr(args, flag) != default:
                parser.error(f"--verb-lens does not compose with --{flag.replace('_', '-')}")
        if iterations < 2:
            parser.error("--verb-lens needs at least 2 iterations "
                         "(sample standard deviation is undefined below that)")
        audit = run_verb_lens_audit(
            iterations=iterations,
            seed=args.seed,
            include_speculative=args.include_speculative,
        )
        if args.json:
            print(json.dumps(audit, indent=2, ensure_ascii=False))
        else:
            print_verb_lens_report(audit)
        if args.save:
            run_dir = save_run(audit)
            print(f"\nRun saved to: {run_dir}", file=sys.stderr)
        return

    site_filter = None
    if args.site_filter:
        site_filter = {s.strip() for s in args.site_filter.split(",")}
    elif args.site_class and args.site_class != "all":
        site_classes = load_site_classes()
        if args.site_class in site_classes:
            site_filter = set(site_classes[args.site_class])
            print(f"Site class '{args.site_class}': {sorted(site_filter)}", file=sys.stderr)
        else:
            print(f"Unknown site class: {args.site_class}", file=sys.stderr)
            sys.exit(1)

    if args.language == "cross-compare":
        cross = run_cross_compare(
            iterations=iterations,
            seed=args.seed,
            mode=args.mode,
            guttural_transparent=not args.no_gutturals,
            site_filter=site_filter,
            frequency_class=frequency_class,
            native_distances=args.native_distances,
            exclude_names=args.exclude_names,
            length_class=args.length_class,
            min_skeleton_len=args.min_skeleton_len,
        )

        if args.json:
            # Stringify all threshold keys for JSON
            cross_json = dict(cross)
            for result in cross_json.get("languages", {}).values():
                if "thresholds" in result:
                    result["thresholds"] = {str(k): v for k, v in result["thresholds"].items()}
            print(json.dumps(cross_json, indent=2, ensure_ascii=False))
        else:
            print_comparison(cross)

        if args.save:
            cross_save = dict(cross)
            for result in cross_save.get("languages", {}).values():
                if "thresholds" in result:
                    result["thresholds"] = {str(k): v for k, v in result["thresholds"].items()}
            run_dir = save_run(cross_save)
            print(f"\nRun saved to: {run_dir}", file=sys.stderr)
    else:
        audit = run_audit(
            iterations=iterations,
            seed=args.seed,
            mode=args.mode,
            guttural_transparent=not args.no_gutturals,
            language=args.language,
            site_filter=site_filter,
            min_skeleton_len=args.min_skeleton_len,
            frequency_class=frequency_class,
            native_distances=args.native_distances,
            exclude_names=args.exclude_names,
            length_class=args.length_class,
        )

        if args.json:
            audit_json = dict(audit)
            audit_json["thresholds"] = {str(k): v for k, v in audit["thresholds"].items()}
            print(json.dumps(audit_json, indent=2, ensure_ascii=False))
        else:
            print_report(audit)

        if args.save:
            audit_save = dict(audit)
            audit_save["thresholds"] = {str(k): v for k, v in audit["thresholds"].items()}
            run_dir = save_run(audit_save)
            print(f"\nRun saved to: {run_dir}", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
