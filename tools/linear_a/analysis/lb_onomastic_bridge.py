#!/usr/bin/env python3
"""LB Onomastic Bridge — systematic Linear A ↔ Linear B name continuity sweep.

Davis's ZA 10 observation (DA-I-PI-TA / PA-JA-RE / TA-NA-TE recurring as
non-Greek names on KN tablets) made systematic: every onomasticon token is
matched against the 6,706 DAMOS-verified Linear B token forms on the shared
CV phoneme string, with vowel-lenient distance, Greek-morphology flagging,
personnel-series context, and a syllable-shuffle null control.

Report-only: writes {candidates.jsonl, summary.json} to --out (default: the
user cache, `CACHE/linear-a/lb-bridge/`). Never touches onomasticon.json.

Usage:
  uv run tools/linear_a/analysis/lb_onomastic_bridge.py [--selftest] [--threshold 0.5] [--out DIR]
"""

from __future__ import annotations

import argparse
import json
import random
import re
import statistics
import sys
from collections import defaultdict
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    __package__ = "tools.linear_a.analysis"

from ...core.phonetics import weighted_levenshtein
from ...core.skeleton import _lookup_sign
from ...paths import CACHE, LINEAR_A_DATA, NotInCheckout, require

DATA_DIR = LINEAR_A_DATA
OUT_DIR = CACHE / "linear-a" / "lb-bridge"

THRESHOLD = 0.5  # allows two vowel substitutions on an otherwise identical frame
VOWELS = "aeiou"
# Vowel-lenient distance: vowel<->vowel substitution 0.25, everything else default.
VOWEL_DISTANCES = {(a, b): 0.25 for a in VOWELS for b in VOWELS if a != b}

# Greek morphological endings of Mycenaean names: flagged, not excluded — a
# Minoan name can surface with a Greek suffix in LB.
GREEK_ENDINGS = ("-i-jo", "-o-jo", "-e-u", "-me-no", "-wo-ko", "-da-mo", "-e-wi-ja")

LB_TOKEN_RE = re.compile(r"^[a-z][a-z0-9*]*(-[a-z0-9*]+)+$")
SERIES_RE = re.compile(r"^[A-Z]{2}\s+\$?([A-Za-z]+)")


def la_phonemes(token: str) -> str | None:
    """CV phoneme string for a Linear A token (None if any sign unresolvable)."""
    out = []
    for sign in token.split("-"):
        d = _lookup_sign(sign)
        if d is None:
            return None
        c, v = d
        out.append((c or "") + (v or ""))
    return "".join(out)


def lb_phonemes(token: str) -> str | None:
    """CV phoneme string for a Linear B token (naive LB values, subscripts stripped).

    Known limitation: special values (pu2, ra2, ra3, a2, a3...) are reduced to
    their base sign; matches through such signs are approximate by construction.
    """
    out = []
    for syl in token.split("-"):
        base = re.sub(r"[0-9*]+$", "", syl)
        if not base or not base.isalpha():
            return None
        out.append(base)
    # LB convention writes the palatal glide as j; LA sign decomposition uses y.
    return "".join(out).replace("j", "y")


def _read(name: str):
    return json.loads(require(DATA_DIR / name, name).read_text(encoding="utf-8"))


def load_onomasticon() -> list[dict]:
    data = _read("onomasticon.json")
    return data.get("entries", data)


def load_lb_index() -> dict[str, dict]:
    idx = _read("linear_b_token_context_index.json")
    return {tok: info for tok, info in idx.items()
            if LB_TOKEN_RE.match(tok.strip())}


def series_domains(documents: list[str], rules: dict[str, str]) -> set[str]:
    doms = set()
    for doc in documents:
        m = SERIES_RE.match(doc)
        if m:
            doms.add(rules.get(m.group(1)[0].upper(), "unknown"))
    return doms


def match_all(la_entries: list[dict], lb_forms: dict[str, str],
              threshold: float, count_only: bool = False) -> list[dict] | int:
    """Match every LA name token against LB forms, length-bucketed.

    count_only short-circuits at the first hit per entry and returns the
    matched-entry count — the fast path for null iterations.
    """
    by_len: dict[int, list[tuple[str, str]]] = defaultdict(list)
    for tok, ph in lb_forms.items():
        by_len[len(ph)].append((tok, ph))
    results = []
    count = 0
    for e in la_entries:
        token = e.get("token", "")
        ph = la_phonemes(token)
        if not ph or len(ph) < 4:  # <2 syllables: matches are noise
            continue
        hits = []
        for length in range(len(ph) - 1, len(ph) + 2):
            for lb_tok, lb_ph in by_len.get(length, ()):
                d = weighted_levenshtein(ph, lb_ph, VOWEL_DISTANCES)
                if d <= threshold:
                    if count_only:
                        count += 1
                        hits = None
                        break
                    hits.append((d, lb_tok, lb_ph))
            if count_only and hits is None:
                break
        if count_only or not hits:
            continue
        hits.sort()
        results.append({"la_token": token, "la_phonemes": ph,
                        "la_type": e.get("type"),
                        "la_affiliation": e.get("affiliation"),
                        "la_attestations": e.get("attestations", []),
                        "hits": hits[:5]})
    return count if count_only else results


def run(threshold: float, null_iters: int = 200, out_dir: Path = OUT_DIR) -> dict:
    entries = load_onomasticon()
    lb_index = load_lb_index()
    rules = _read("linear_b_administrative_domain_model.json")["domain_rules"]
    lb_forms = {tok: ph for tok in lb_index
                if (ph := lb_phonemes(tok)) and len(ph) >= 4}
    print(f"LA name tokens: {len(entries)} | LB forms: {len(lb_forms)}")

    observed = match_all(entries, lb_forms, threshold)

    # Enrich with context + Greek-morphology flag
    candidates = []
    for r in observed:
        best_d, lb_tok, lb_ph = r["hits"][0]
        info = lb_index[lb_tok]
        docs = info.get("documents", [])
        doms = series_domains(docs, rules)
        candidates.append({
            **{k: r[k] for k in ("la_token", "la_phonemes", "la_type",
                                 "la_affiliation", "la_attestations")},
            "lb_token": lb_tok, "lb_phonemes": lb_ph, "distance": round(best_d, 3),
            "exact": best_d == 0.0,
            "lb_document_count": info.get("document_count", 0),
            "lb_sample_documents": docs[:5],
            "lb_domains": sorted(doms),
            "personnel_context": "personnel" in doms,
            "greek_morphology": any(lb_tok.endswith(s) for s in GREEK_ENDINGS),
            "runner_up_hits": [{"lb_token": t, "d": round(d, 3)}
                               for d, t, _ in r["hits"][1:3]],
        })

    # Null control: shuffle syllable order within LA tokens, re-match (count only)
    rng = random.Random(2028)
    obs_count = len(observed)
    null_counts = []
    for i in range(null_iters):
        shuffled = []
        for e in entries:
            syls = e.get("token", "").split("-")
            if len(syls) >= 2:
                s = syls[:]
                rng.shuffle(s)
                shuffled.append({"token": "-".join(s), "type": e.get("type")})
        null_counts.append(match_all(shuffled, lb_forms, threshold,
                                     count_only=True))
        if (i + 1) % 20 == 0:
            print(f"  null iteration {i + 1}/{null_iters}", flush=True)
    mu = statistics.mean(null_counts)
    sd = statistics.stdev(null_counts) if len(null_counts) > 1 else 0.0
    z = (obs_count - mu) / sd if sd else 0.0
    p = (sum(1 for v in null_counts if v >= obs_count) + 1) / (null_iters + 1)

    exact = [c for c in candidates if c["exact"]]
    summary = {
        "threshold": threshold,
        "la_tokens_matched": obs_count,
        "exact_matches": len(exact),
        "personnel_context_matches": sum(1 for c in candidates
                                         if c["personnel_context"]),
        "greek_flagged": sum(1 for c in candidates if c["greek_morphology"]),
        "null_control": {"mean": mu, "sd": sd, "z": z, "p": p,
                         "n_iter": null_iters,
                         "note": "syllable-shuffle null: same signs, "
                                 "scrambled order"},
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "candidates.jsonl", "w", encoding="utf-8") as fh:
        fh.writelines(json.dumps(c, ensure_ascii=False) + "\n" for c in sorted(candidates, key=lambda c: c["distance"]))
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(json.dumps(summary, indent=1))
    print(f"Wrote {out_dir}/candidates.jsonl ({len(candidates)} candidates)")
    return summary


def selftest() -> int:
    failures = 0
    lb_index = load_lb_index()
    lb_forms = {tok: ph for tok in lb_index
                if (ph := lb_phonemes(tok)) and len(ph) >= 4}
    # Davis's ZA 10 controls + the one existing comparanda entry (PA-DE)
    controls = [("DA-I-PI-TA", "da-i-pi-ta", 0.0),
                ("PA-JA-RE", "pa-ja-ro", 0.25),
                ("PA-DE", "pa-de", 0.0)]
    for la, lb_expect, d_expect in controls:
        ph = la_phonemes(la)
        if ph is None:
            print(f"  [FAIL] {la}: unresolvable signs")
            failures += 1
            continue
        if lb_expect not in lb_forms:
            print(f"  [FAIL] control LB form {lb_expect} absent from index")
            failures += 1
            continue
        d = weighted_levenshtein(ph, lb_forms[lb_expect], VOWEL_DISTANCES)
        ok = abs(d - d_expect) < 1e-9
        if not ok:
            failures += 1
        print(f"  [{'OK' if ok else 'FAIL'}] {la} ~ {lb_expect}: "
              f"d={d} (expected {d_expect})")
    print(f"Selftest: {'PASS' if failures == 0 else f'{failures} FAILURES'}")
    return failures


def main() -> int:
    try:
        return _run()
    except NotInCheckout as e:
        print(f"stopped: {e}", file=sys.stderr)
        return 2


def _run() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--threshold", type=float, default=THRESHOLD)
    ap.add_argument("--null-iterations", type=int, default=200)
    ap.add_argument("--out", type=Path, default=OUT_DIR)
    args = ap.parse_args()
    if args.selftest:
        return 1 if selftest() else 0
    run(args.threshold, args.null_iterations, args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
