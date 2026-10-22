#!/usr/bin/env python3
"""Hapax analysis for the Linear A decipherment pipeline.

Loads the corpus, determines matched vs unmatched words from the most recent
decode/propagation run (or the lexicon as fallback), then reports frequency
distribution, average word length, initial sign distribution, and site
concentration—split by match status.

Usage:
    uv run tools/linear_a/validation/hapax_analysis.py [--json] [--save] [--gap-report]
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    __package__ = "tools.linear_a.validation"

from ...core import run_saver
from ...paths import CACHE, LINEAR_A_DATA, NotInCheckout, require

# context_search owns the *-sign → phonemic resolution map.
from ..context_search import load_sign_resolution_map, resolve_word_signs

CORPUS_PATH = LINEAR_A_DATA / "corpus.json"
LEXICON_PATH = LINEAR_A_DATA / "lexicon.json"
GAP_REPORT_PATH = CACHE / "linear-a" / "vocabulary_gap.json"


# ---------------------------------------------------------------------------
# Filtering helpers — mirror ventris_stats.py to stay in sync.
# ---------------------------------------------------------------------------

_IDEOGRAM_KEYWORDS = {
    "GRA", "OLE", "VIN", "FIC", "CYP", "ARE", "AUR", "BOS",
    "CAP", "CER", "EQU", "FAR", "HOR", "NI", "OVI", "SUS",
    "TELA", "LUNA", "SOL", "LANA", "VAS",
}

# Fraction characters that appear as numeric tokens.
_FRACTION_CHARS = set("½¼¾⅓⅔⅕⅖⅗⅘⅙⅚⅛⅜⅝⅞")


def _is_syllabographic(token: str) -> bool:
    """Return True if token is a syllabographic word (not ideogram/numeral/separator).

    A syllabographic word must:
    - Contain at least one hyphen (multi-sign), e.g. "A-KA-RU", "KU-NI-SU".
    - Not start with "*" followed by only digits (undeciphered sign codes like *307).
    - Not be a known ideogram abbreviation (possibly with + modifier).
    - Not be purely numeric or a fraction character.
    """
    if not token or token == "\n":
        return False

    # Skip single-character Unicode above ASCII (rendered Linear A glyphs).
    if len(token) == 1 and ord(token) > 127:
        return False

    # Skip fraction/numeric tokens.
    if all(c in _FRACTION_CHARS or c.isdigit() or c in "./, " for c in token):
        return False

    stripped = token.strip()

    # Skip tokens that are purely numeric.
    if stripped.replace(",", "").replace(".", "").isdigit():
        return False

    # Must have a hyphen — single-sign tokens (KU, RO, etc.) are excluded
    # per the task spec: "syllabographic if it contains at least one hyphen".
    if "-" not in stripped:
        return False

    # Skip *NNN undeciphered sign codes.
    if stripped.startswith("*") and stripped[1:].replace("+", "").replace("-", "").isdigit():
        return False

    # Skip ideogram abbreviations — check each hyphen-segment.
    upper = stripped.upper()
    base = upper.lstrip("*")
    # Check if the whole token (stripped of modifier suffixes) is an ideogram.
    clean = base.rstrip("+").split("+")[0]
    if clean in _IDEOGRAM_KEYWORDS:
        return False
    # Also check component parts for compound ideograms like "OLE+U".
    parts = upper.replace("+", "-").split("-")
    return parts[0].rstrip("+") not in _IDEOGRAM_KEYWORDS


# ---------------------------------------------------------------------------
# Corpus loading
# ---------------------------------------------------------------------------

def load_corpus() -> dict:
    return json.loads(require(CORPUS_PATH, "corpus.json").read_text(encoding="utf-8"))


def extract_syllabographic_tokens(corpus: dict) -> list[dict]:
    """Return a flat list of syllabographic word occurrences.

    Each entry: {"word": str, "doc_id": str, "site": str, "signs": list[str]}
    Words are upper-cased; hyphens preserved (KU-NI-SU, not ["KU","NI","SU"]).
    """
    tokens: list[dict] = []
    for doc_id, doc in corpus.items():
        site = doc.get("site", "unknown")
        for raw_token in doc.get("transliteratedWords", []):
            if not isinstance(raw_token, str):
                continue
            token = raw_token.strip()
            if _is_syllabographic(token):
                word = token.upper()
                tokens.append({
                    "word": word,
                    "doc_id": doc_id,
                    "site": site,
                    "signs": word.split("-"),
                })
    return tokens


# ---------------------------------------------------------------------------
# Run loading — matched word set
# ---------------------------------------------------------------------------

def _latest_run_of_type(run_types: tuple[str, ...]) -> dict | None:
    index = run_saver.load_index()
    candidates = [r for r in index.get("runs", []) if r.get("run_type") in run_types]
    if not candidates:
        return None
    return max(candidates, key=lambda r: r.get("timestamp", ""))


def _load_run_output(run_id: str) -> dict:
    run_dir = run_saver.RUNS_DIR / run_id
    output_path = run_dir / "output.json"
    if not output_path.exists():
        raise FileNotFoundError(f"output.json missing for run: {run_id}")
    return json.loads(output_path.read_text(encoding="utf-8"))


def get_matched_words_from_run(run_meta: dict) -> set[str]:
    """Extract the set of words that received a match from a saved run.

    Propagation runs store a flat `results` list; each entry has a `word` field.
    Status "known" = confirmed match; other statuses (new_candidate, etc.) are
    also matched—any entry present in results means the engine found a reading.

    Decode runs store `cross_validated` (fully validated words) and also embed
    matched words inside `propagation` stats, but not as a per-word list.
    Fall back to cross_validated words only if no results list found.
    """
    run_id = run_meta["run_id"]
    output = _load_run_output(run_id)

    matched: set[str] = set()

    # Propagation runs: use results list directly.
    results = output.get("results")
    if results:
        for entry in results:
            w = entry.get("word", "").strip().upper()
            if w:
                matched.add(w)
        return matched

    # Decode runs: use cross_validated list.
    cross_validated = output.get("cross_validated", [])
    for entry in cross_validated:
        # cross_validated entries have a nested "propagation" dict with "word".
        prop = entry.get("propagation", {})
        w = prop.get("word", entry.get("word", "")).strip().upper()
        if w:
            matched.add(w)

    return matched


def get_matched_words_from_lexicon() -> set[str]:
    """Fallback: treat every word in lexicon.json as matched.

    Includes each entry's ``corpus_forms``—the raw corpus spellings of entries
    keyed by a resolved reading (JA-HA ← JA-*21F) or unsubscripted form
    (KI-RE-TA ← KI-RE-TA₂).
    """
    lex = json.loads(require(LEXICON_PATH, "lexicon.json").read_text(encoding="utf-8"))
    entries = lex.get("entries", [])
    matched: set[str] = set()
    for entry in entries:
        for w in [entry.get("word", ""), *entry.get("corpus_forms", [])]:
            w = w.strip().upper()
            if w:
                matched.add(w)
    return matched


def _canonical_resolved(word: str) -> str:
    """Resolved display uses Y for /y/ (*28B → YI); lexicon keys use J (JI-NU-MA-RE)."""
    return "-".join("J" + p[1:] if len(p) == 2 and p[0] == "Y" else p for p in word.split("-"))


def expand_matched_by_sign_resolution(
    matched: set[str], corpus_words, sign_map: dict[str, str],
) -> tuple[set[str], dict[str, str]]:
    """Count a corpus word with *-signs as matched when its resolved form is a lexicon key.

    Returns (expanded matched set, {corpus_word: lexicon_key} for each alias used).
    Signs below the resolution-map confidence floor never resolve, so they stay in the gap.
    """
    expanded = set(matched)
    audit: dict[str, str] = {}
    for w in corpus_words:
        if w in matched or "*" not in w:
            continue
        key = _canonical_resolved(resolve_word_signs(w, sign_map))
        if key != w and key in matched:
            expanded.add(w)
            audit[w] = key
    return expanded, audit


def resolve_matched_set(mode: str = "auto") -> tuple[set[str], str]:
    """Return (matched_word_set, source_description).

    Modes:
      auto     — most recent decode/propagation run; falls back to lexicon (legacy default)
      lexicon  — lexicon.json only (current curated ground truth)
      union    — run matches ∪ lexicon words (truest gap: unmatched by engine AND uncurated)
    """
    if mode == "lexicon":
        return get_matched_words_from_lexicon(), "lexicon.json"

    run_matched: set[str] = set()
    run_source = None
    run_meta = _latest_run_of_type(("decode", "propagation"))
    if run_meta:
        try:
            run_matched = get_matched_words_from_run(run_meta)
            run_source = f"run:{run_meta['run_id']} ({run_meta['run_type']})"
        except (FileNotFoundError, KeyError, json.JSONDecodeError) as e:
            print(f"[warn] Could not load run '{run_meta['run_id']}': {e} — falling back to lexicon",
                  file=sys.stderr)

    if mode == "union":
        lex = get_matched_words_from_lexicon()
        source = f"{run_source} ∪ lexicon.json" if run_source else "lexicon.json"
        return run_matched | lex, source

    # auto (legacy)
    if run_source:
        return run_matched, run_source
    return get_matched_words_from_lexicon(), "lexicon.json"


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def build_frequency_table(tokens: list[dict]) -> Counter:
    """Count occurrences of each unique word across all tokens."""
    return Counter(t["word"] for t in tokens)


def frequency_bucket(count: int) -> str:
    if count == 1:
        return "hapax"
    if count == 2:
        return "dis"
    if count <= 5:
        return "3-5"
    if count <= 10:
        return "6-10"
    return "10+"


def average_sign_length(words: list[str]) -> float:
    if not words:
        return 0.0
    return sum(len(w.split("-")) for w in words) / len(words)


def initial_sign_distribution(words: list[str], top_n: int = 10) -> list[tuple[str, int]]:
    counter: Counter = Counter()
    for w in words:
        signs = w.split("-")
        if signs:
            counter[signs[0]] += 1
    return counter.most_common(top_n)


def site_distribution(tokens: list[dict], word_set: set[str], top_n: int = 10) -> list[tuple[str, int]]:
    """Count how many tokens (not unique types) from word_set appear at each site."""
    counter: Counter = Counter()
    for t in tokens:
        if t["word"] in word_set:
            counter[t["site"]] += 1
    return counter.most_common(top_n)


def run_analysis(tokens: list[dict], freq: Counter, matched_words: set[str]) -> dict:
    """Compute the full hapax analysis and return a result dict."""
    all_unique = set(freq.keys())
    unmatched_words = all_unique - matched_words
    matched_in_corpus = all_unique & matched_words

    def split_by_freq(word_set: set[str]) -> dict:
        hapax = [w for w in word_set if freq[w] == 1]
        dis = [w for w in word_set if freq[w] == 2]
        three_plus = [w for w in word_set if freq[w] >= 3]
        return {"hapax": hapax, "dis": dis, "3plus": three_plus}

    unmatched_split = split_by_freq(unmatched_words)
    matched_split = split_by_freq(matched_in_corpus)

    # Site distribution — focus on unmatched tokens.
    unmatched_site_dist = site_distribution(tokens, unmatched_words, top_n=10)

    # Initial sign distribution.
    unmatched_initial = initial_sign_distribution(list(unmatched_words), top_n=10)
    matched_initial = initial_sign_distribution(list(matched_in_corpus), top_n=10)

    # Overall frequency buckets for all words.
    buckets: Counter = Counter(frequency_bucket(c) for c in freq.values())

    # Build detailed per-word records for non-hapax unmatched words
    gap_words = sorted(
        unmatched_split["dis"] + unmatched_split["3plus"],
        key=lambda w: -freq[w],
    )
    gap_details = []
    for word in gap_words:
        occurrences = [t for t in tokens if t["word"] == word]
        gap_details.append({
            "word": word,
            "frequency": freq[word],
            "signs": len(word.split("-")),
            "inscriptions": sorted({t["doc_id"] for t in occurrences}),
            "sites": sorted({t["site"] for t in occurrences}),
        })

    return {
        "corpus": {
            "total_inscriptions": len({t["doc_id"] for t in tokens}),
            "total_tokens": len(tokens),
            "unique_words": len(all_unique),
        },
        "frequency_distribution": {
            "hapax": buckets["hapax"],
            "dis": buckets["dis"],
            "3-5": buckets["3-5"],
            "6-10": buckets["6-10"],
            "10+": buckets["10+"],
        },
        "matched": {
            "total": len(matched_in_corpus),
            "hapax": len(matched_split["hapax"]),
            "dis": len(matched_split["dis"]),
            "3plus": len(matched_split["3plus"]),
            "avg_length": average_sign_length(list(matched_in_corpus)),
            "initial_signs": matched_initial,
        },
        "unmatched": {
            "total": len(unmatched_words),
            "hapax": len(unmatched_split["hapax"]),
            "dis": len(unmatched_split["dis"]),
            "3plus": len(unmatched_split["3plus"]),
            "avg_length": average_sign_length(list(unmatched_words)),
            "initial_signs": unmatched_initial,
            "site_distribution": unmatched_site_dist,
        },
        "real_vocabulary_gap": len(unmatched_split["dis"]) + len(unmatched_split["3plus"]),
        "gap_details": gap_details,
    }


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

_SITE_ABBR: dict[str, str] = {
    "Haghia Triada": "HT",
    "Khania": "KH",
    "Zakros": "ZA",
    "Palaikastro": "PK",
    "Iouktas": "IO",
    "Knossos": "KN",
    "Phaistos": "PH",
    "Malia": "MA",
    "Arkhanes": "AR",
    "Troullos": "TR",
}


def _pct(n: int, total: int) -> str:
    if total == 0:
        return "  0%"
    return f"{100 * n // total:3d}%"


def print_report(result: dict, source: str) -> None:
    c = result["corpus"]
    fd = result["frequency_distribution"]
    m = result["matched"]
    u = result["unmatched"]

    total_words = c["unique_words"]
    total_tok = c["total_tokens"]
    total_inscrip = c["total_inscriptions"]

    print()
    print("Hapax Analysis Report")
    print("=====================")
    print(f"Corpus: {total_words:,} unique words across {total_inscrip:,} inscriptions "
          f"({total_tok:,} tokens)")
    print(f"Match source: {source}")
    print()

    print("Frequency Distribution (All Words):")
    print(f"  Hapax (1×):     {fd['hapax']:5,} words ({_pct(fd['hapax'], total_words)})")
    print(f"  Dis (2×):       {fd['dis']:5,} words ({_pct(fd['dis'], total_words)})")
    print(f"  3-5×:           {fd['3-5']:5,} words ({_pct(fd['3-5'], total_words)})")
    print(f"  6-10×:          {fd['6-10']:5,} words ({_pct(fd['6-10'], total_words)})")
    print(f"  10+×:           {fd['10+']:5,} words ({_pct(fd['10+'], total_words)})")
    print()


    print("Matched vs Unmatched:")
    print(f"  {'':18s}{'Matched':>10}   {'Unmatched':>10}")
    print(f"  {'Total:':18s}{m['total']:>10,}   {u['total']:>10,}")
    print(f"  {'Hapax:':18s}{m['hapax']:>6,} ({_pct(m['hapax'], m['total'])})   "
          f"{u['hapax']:>6,} ({_pct(u['hapax'], u['total'])})")
    print(f"  {'Dis:':18s}{m['dis']:>6,} ({_pct(m['dis'], m['total'])})   "
          f"{u['dis']:>6,} ({_pct(u['dis'], u['total'])})")
    print(f"  {'3+:':18s}{m['3plus']:>6,} ({_pct(m['3plus'], m['total'])})   "
          f"{u['3plus']:>6,} ({_pct(u['3plus'], u['total'])})")
    print(f"  {'Avg length:':18s}{m['avg_length']:>9.1f}s   {u['avg_length']:>9.1f}s")
    print()

    print(f"Real vocabulary gap (non-hapax unmatched): {result['real_vocabulary_gap']:,} words")
    print()

    # Site distribution — top 10 unmatched.
    site_dist = u["site_distribution"]
    if site_dist:
        print("Site concentration of unmatched (top 10):")
        parts = []
        for site, count in site_dist[:10]:
            abbr = _SITE_ABBR.get(site, site[:6])
            parts.append(f"  {abbr}: {count:,}")
        print("\n".join(parts))
        print()

    # Initial sign distributions.
    print("Initial sign frequency — Matched (top 10):")
    for sign, cnt in m["initial_signs"]:
        bar = "█" * min(cnt // 2, 30)
        print(f"  {sign:<8} {cnt:4,}  {bar}")
    print()

    print("Initial sign frequency — Unmatched (top 10):")
    for sign, cnt in u["initial_signs"]:
        bar = "█" * min(cnt // 2, 30)
        print(f"  {sign:<8} {cnt:4,}  {bar}")
    print()


def _save_hapax_run(result: dict, source: str) -> Path:
    """Save hapax analysis output to the run cache."""
    output = result.copy()
    output["match_source"] = source
    return run_saver.save_run("hapax_analysis", {"match_source": source}, output, label="hapax-legomena")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Hapax legomena analysis for the Linear A corpus.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON result instead of formatted report.",
    )
    p.add_argument(
        "--save",
        action="store_true",
        help="Save output to the run cache.",
    )
    p.add_argument(
        "--gap-report",
        action="store_true",
        help="Append a dated vocabulary gap report (non-hapax unmatched words) to vocabulary_gap.json "
             "in the user cache.",
    )
    p.add_argument(
        "--match-source",
        choices=("auto", "lexicon", "union"),
        default="auto",
        help="Matched-word source: auto=latest run (legacy), lexicon=curated lexicon only, union=run ∪ lexicon.",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    try:
        _run(argv)
    except NotInCheckout as e:
        print(f"stopped: {e}", file=sys.stderr)
        return 2
    return 0


def _run(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    corpus = load_corpus()
    if not corpus:
        print("Error: corpus.json is empty.", file=sys.stderr)
        sys.exit(1)

    tokens = extract_syllabographic_tokens(corpus)

    if not tokens:
        print("Warning: no syllabographic tokens extracted from corpus.", file=sys.stderr)

    freq = build_frequency_table(tokens)

    # Resolve matched word set.
    matched_words, source = resolve_matched_set(args.match_source)
    key_audit: dict[str, str] = {}
    if args.match_source in ("lexicon", "union"):
        matched_words, key_audit = expand_matched_by_sign_resolution(
            matched_words, freq.keys(), load_sign_resolution_map())

    # Run analysis.
    result = run_analysis(tokens, freq, matched_words)
    if key_audit:
        result["lexicon_key_audit"] = key_audit

    if args.json:
        output = result.copy()
        output["match_source"] = source
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        print_report(result, source)

    if args.save:
        run_dir = _save_hapax_run(result, source)
        print(f"Saved: {run_dir}", file=sys.stderr)

    if args.gap_report:
        _write_gap_report(result, source)


def _write_gap_report(result: dict, source: str) -> None:
    """Write or append a dated vocabulary gap entry to vocabulary_gap.json in the user cache."""
    gap_path = GAP_REPORT_PATH
    gap_path.parent.mkdir(parents=True, exist_ok=True)

    now = datetime.now(UTC)
    entry = {
        "date": now.strftime("%Y-%m-%d"),
        "timestamp": now.isoformat(),
        "match_source": source,
        "total_gap_words": result["real_vocabulary_gap"],
        "total_unmatched": result["unmatched"]["total"],
        "total_hapax_unmatched": result["unmatched"]["hapax"],
        "words": result["gap_details"],
    }

    if gap_path.exists():
        existing = json.loads(gap_path.read_text(encoding="utf-8"))
    else:
        existing = {"description": "Non-hapax unmatched words — the real vocabulary gap", "reports": []}

    existing["reports"].append(entry)

    gap_path.write_text(
        json.dumps(existing, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Gap report appended to: {gap_path} ({entry['total_gap_words']} words)", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
