#!/usr/bin/env python3
"""Shoresh pre-gold checks (tools/core/SHORESH.md, §6 amendments). Report-only: reads the index, corpus and
sign data, and writes nothing but the --out report, which must not exist. Run on a frozen snapshot (§7.7).

  a12   d* over retrieved keys (RootIndex.candidates, one class edit) against brute force over every eligible
        key, on --n corpus words drawn with --seed. Every miss is listed with the key that beats retrieval.
  a9    planted-signal power: PS keys attested in ≥ 2 Semitic branches and linked to no Linear A lexicon entry,
        spelled in Linear A orthography and queried like corpus words on the primary index (A4). Power is the
        share with p_max < 0.05 per skeleton length; a bucket under 0.5 is labelled underpowered. Competitor power
        (A15), both ways: how often a competitor (tools/core/competitors.py) reaches p_max < 0.05 on the Semitic plants
        (it would block them), and each competitor's power on --planted keys of its own, spelled open with the
        series chosen on its own table (keys with a consonant no series writes under 1.0 are counted, not planted).

Spelling (A9): the C/V pattern of the headword's first alternative, its consonant slots filled with the key's
radicals in order; a headword with no vowel or a different slot count is spelled all-open instead (counted). A
consonant before another consonant, or word-final without a trailing hyphen, is a coda and is omitted; a trailing
hyphen takes an ending vowel. Signs are those whose engine value is their Linear B value (no project value, A4).
A consonant with no series takes the cheapest substitution, then its shadow class (b → p, ṭ → t, l → r). ʾ ʿ h ḥ
onsets are bare vowel signs; ḫ and ġ, which have a written series, are written or not by a seeded coin.

Usage (from a frozen copy of the repository; the index defaults to the user cache):
  uv run tools/linear_a/validation/root_match_checks.py a12 --index root_index.snapshot.sqlite --out a12.json
  uv run tools/linear_a/validation/root_match_checks.py a9 --index root_index.snapshot.sqlite --workers 8 --out a9.json

Attribution: di Mino
"""
from __future__ import annotations

import argparse
import json
import multiprocessing
import os
import random
import re
import sys
import time
from collections import Counter
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    __package__ = "tools.linear_a.validation"

from ...core import root_match as rm
from ...core.competitors import load_all as load_competitors
from ...core.root_index import DEFAULT_INDEX, IndexStale, RootIndex, record_keys, sha256_file, shadow_key
from ...core.semitic_root_schema import roots_records
from ...paths import REPO, SEMITIC_ROOTS_DATA, NotInCheckout, require
from .null_model_audit import load_corpus_words
from .root_match_phase0 import (
    DATA_DIR,
    GOLD_V3_PATH,
    _git_head,
    _rel,
    changed_inputs,
    fold_gutturals,
    frozen_index_exclusions,
    gold_guard,
    input_hashes,
    parse_lexicon_root,
    reading_key,
    sign_group_key,
)

A12_N = 500
A9_N = 200                  # planted keys
A9_MIN_BRANCHES = 2
UNDERPOWERED = 0.5
ENDING_VOWELS = "aiu"       # V placeholders and the vowel a trailing hyphen takes
LB_CONSONANTS = {"D": "d", "J": "y", "K": "k", "M": "m", "N": "n", "P": "p", "Q": "q", "R": "r", "S": "s", "T": "t",
                 "W": "w", "Z": "z"}
_ENGINE: rm.Shoresh | None = None      # set in the parent before the pool forks; workers only read it
# --workers > 1 forks a ProcessPoolExecutor: rows keep input order, and a worker that dies (OOM, a kill) raises
# BrokenProcessPool, so no report is written, where multiprocessing.Pool would wait forever for the lost task.


def _hashes(index_path: Path) -> dict[str, str | None]:
    out = input_hashes()
    core = REPO / "tools" / "core"
    for p in (core / "root_match.py", core / "root_index.py", GOLD_V3_PATH,
              core / "competitors.py", DATA_DIR / "hurrian_roots.json"):
        out[_rel(p)] = sha256_file(p) if p.exists() else None
    try:
        name = _rel(index_path)
    except ValueError:
        name = str(index_path)
    out[name] = sha256_file(index_path) if index_path.exists() else None
    return out


def write_report(path: Path, payload: dict[str, Any], before: dict[str, str | None], seed: int) -> None:
    """As root_match_phase0.write_fixture: refused if an input changed during the run; exclusive link, so an
    existing report is never overwritten and a crash never leaves half a file."""
    index = Path(payload["index"])
    changed = changed_inputs(before, _hashes(index))
    if changed:
        sys.exit(f"inputs changed during the run, report NOT written: {changed}")
    payload["provenance"] = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "generator": "tools/linear_a/validation/root_match_checks.py",
        "git_head": _git_head(),
        "seed": seed,
        "input_sha256": before,
    }
    text = json.dumps(payload, ensure_ascii=False, indent=1, allow_nan=False) + "\n"
    tmp = path.with_name(f"{path.name}.tmp-{os.getpid()}")
    try:
        with open(tmp, "x", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.link(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)
    print(f"wrote {path}")


# ---------------------------------------------------------------------------
# A12
# ---------------------------------------------------------------------------

def _gold_test(gold: set[tuple[str, ...]] | Callable[[str], bool]) -> Callable[[str], bool]:
    """gold as a word test: gold_guard's is_gold as given, or a set of sign_group_key tuples matched by name or by
    reading (A14), so KA-*301-SI is held back with KA-NA-SI."""
    if callable(gold):
        return gold
    readings = {k for k in (reading_key("-".join(g)) for g in gold) if k is not None}
    return lambda w: sign_group_key(w) in gold or (reading_key(w) or ()) in readings


def sample_words(words: list[str], n: int, seed: int, engine: rm.Shoresh,
                 gold: set[tuple[str, ...]] | Callable[[str], bool]) -> tuple[list[str], Counter]:
    """n distinct corpus words whose every sign decomposes and that are not gold-set sign groups (A14), drawn in a
    seeded order; the rest are counted."""
    is_gold = _gold_test(gold)
    order = sorted(set(words))
    random.Random(seed).shuffle(order)
    out: list[str] = []
    skipped: Counter = Counter()
    for w in order:
        if len(out) == n:
            break
        if is_gold(w):
            skipped["gold"] += 1
            continue
        try:
            vs = rm.variants(engine.word_readings(w), w)
        except rm.UnmappedSign:
            skipped["unmapped_sign"] += 1
            continue
        if not vs:
            skipped["no_consonant"] += 1
            continue
        out.append(w)
    return out, skipped


def _argmin(engine: rm.Shoresh, vs: list[rm.Variant], target: float) -> dict[str, Any]:
    """The key and variant that reach the brute-force minimum (misses only)."""
    for v in vs:
        for e in {id(e): e for e in engine._entry_of.values()}.values():
            if abs(rm.distance(v.tokens, e.tokens) + v.penalty - target) <= rm._EPS:
                key = engine._keys_of[id(e)][0]
                return {"variant": "".join(v.tokens), "rule": v.rule, "penalty": v.penalty,
                        "key": "".join(e.tokens), "key_form": key.form, "key_language": key.language,
                        "key_shadow": key.shadow, "clusters": sorted(e.clusters)}
    return {}


def a12_one(word: str) -> dict[str, Any]:
    engine = _ENGINE
    assert engine is not None
    vs = rm.variants(engine.word_readings(word), word)
    t0 = time.perf_counter()
    retrieved = engine.d_star(vs)
    t1 = time.perf_counter()
    brute = engine.brute_force_d_star(vs, retrieved)
    t2 = time.perf_counter()
    hits, _ = engine.clusters(word, top=1)
    shown = hits[0].distance if hits else rm.INF
    skel = rm.skeleton_of(engine.word_readings(word)[0])
    row: dict[str, Any] = {
        "word": word, "skeleton": skel, "consonants": len(rm.phonemes(skel)),
        "retrieved": rm._num(retrieved), "brute": rm._num(brute), "clusters_min": rm._num(shown),
        "miss": brute < retrieved, "paths_agree": shown == retrieved,
        "ms_retrieved": round((t1 - t0) * 1000, 2), "ms_brute": round((t2 - t1) * 1000, 2),
    }
    if row["miss"]:
        row["beaten_by"] = _argmin(engine, vs, brute)
    return row


def run_a12(args: argparse.Namespace) -> None:
    global _ENGINE
    out = Path(args.out)
    if out.exists():
        sys.exit(f"{out} exists; never overwritten")
    index_path = require(Path(args.index).resolve(), "the root index (build it with build_root_index.py)")
    before = _hashes(index_path)
    index = RootIndex.load(index_path)
    _ENGINE = rm.Shoresh(index, names=args.names)
    words, skipped = sample_words(load_corpus_words(), args.n, args.seed, _ENGINE, gold_guard())
    t0 = time.perf_counter()
    if args.workers > 1:
        with ProcessPoolExecutor(args.workers, mp_context=multiprocessing.get_context("fork")) as pool:
            rows = list(pool.map(a12_one, words, chunksize=4))
    else:
        rows = [a12_one(w) for w in words]
    misses = [r for r in rows if r["miss"]]
    disagree = [r for r in rows if not r["paths_agree"]]
    by_len: dict[int, Counter] = {}
    for r in rows:
        by_len.setdefault(r["consonants"], Counter()).update(n=1, miss=int(r["miss"]))
    summary = {
        "queries": len(rows), "misses": len(misses), "path_disagreements": len(disagree), "skipped": dict(skipped),
        "by_consonants": {str(k): dict(v) for k, v in sorted(by_len.items())},
        "seconds": round(time.perf_counter() - t0, 1),
    }
    print(json.dumps(summary, ensure_ascii=False))
    for r in misses:
        b = r["beaten_by"]
        print(f"  MISS {r['word']}: retrieved {r['retrieved']} brute {r['brute']} by {b.get('key_form')} "
              f"({b.get('key_language')}, shadow {b.get('key_shadow')}) clusters {b.get('clusters')}")
    for r in disagree:
        print(f"  PATHS {r['word']}: d_star {r['retrieved']} clusters {r['clusters_min']}")
    write_report(out, {"check": "A12", "index": str(index_path), "names": args.names, "n": args.n,
                       "summary": summary, "misses": misses, "rows": rows}, before, args.seed)


# ---------------------------------------------------------------------------
# A9
# ---------------------------------------------------------------------------

def lb_series() -> dict[str, dict[str, str]]:
    """consonant → vowel → sign, for the CV grid signs whose engine value is their Linear B value."""
    out: dict[str, dict[str, str]] = {}
    for letter, c in LB_CONSONANTS.items():
        for v in "aeiou":
            sign = letter + v.upper()
            try:
                if rm.sign_decomposition(sign) == (c, v):
                    out.setdefault(c, {})[v] = sign
            except rm.UnmappedSign:
                continue
    return out


def series_consonant(c: str, series: dict[str, dict[str, str]], sub=rm._sub) -> str:
    """The series a consonant is written with: its own, else the cheapest substitution under sub (Shoresh's table,
    or a competitor's for its own plants), then its shadow class."""
    if c in series:
        return c
    cls = shadow_key((c,))[0]
    return min(series, key=lambda x: (sub(c, x), shadow_key((x,))[0] != cls, x))


_OPTIONAL = re.compile(r"\([^)]*\)")
_ALT_SPLIT = re.compile(r"\s*(?:~|\{\}|,|;|\s)\s*")
_VOWELS = frozenset("aeiouVə")


def headword_pattern(form: str, radicals: tuple[str, ...]) -> tuple[list[tuple[str, str]], bool] | None:
    """The headword's first alternative as [("C", radical) | ("V", vowel)] with the key's radicals in its
    consonant slots, and whether a trailing hyphen asks for an ending vowel; None when the slots do not fit."""
    first = _ALT_SPLIT.split(_OPTIONAL.sub("|", form.strip()), maxsplit=1)[0]   # "|": g(a)w must not fuse to gw
    toks = [t for t in rm._tokenize_phonemes(first) if t not in ("*", "ʷ", "_", "|")]
    trailing = bool(toks) and toks[-1] == "-"
    seq: list[str] = []
    skip = False
    for t in toks:
        if skip:                    # the alternative after a slash: w/n → w
            skip = False
            continue
        if t == "/":
            skip = True
            continue
        if t != "-":
            seq.append(t)
    slots = [("V", "e" if t == "ə" else t) if t in _VOWELS else ("C", t) for t in seq]
    consonant_slots = [i for i, (k, _) in enumerate(slots) if k == "C"]
    if len(consonant_slots) != len(radicals) or len(consonant_slots) == len(slots):
        return None
    for i, r in zip(consonant_slots, radicals):
        slots[i] = ("C", r)
    return slots, trailing


def open_pattern(radicals: tuple[str, ...]) -> tuple[list[tuple[str, str]], bool]:
    return [x for r in radicals for x in (("C", r), ("V", "V"))], False


def spell(pattern: list[tuple[str, str]], trailing: bool, rng: random.Random,
          series: dict[str, dict[str, str]], sub=rm._sub) -> str:
    """Linear A spelling of a C/V pattern: open syllables written, codas omitted, gutturals as bare vowels (the
    script's rule, on Shoresh's table whatever sub is); sub picks the series of any other consonant."""
    items = list(pattern) + ([("V", "V")] if trailing else [])
    signs: list[str] = []
    i = 0
    while i < len(items):
        kind, x = items[i]
        if kind == "V":
            signs.append(_vowel(x, rng).upper())
            i += 1
            continue
        if i + 1 >= len(items) or items[i + 1][0] != "V":
            i += 1                  # coda: omitted
            continue
        v = _vowel(items[i + 1][1], rng)
        c = x
        if c in rm.GUTTURAL_PHONEMES:
            written = series_consonant(c, series)
            c = written if rm._sub(x, written) < 1.0 and rng.random() < 0.5 else None
        if c is None:
            signs.append(v.upper())
        else:
            row = series[series_consonant(c, series, sub)]
            signs.append(row[v] if v in row else row[rng.choice(sorted(row))])
        i += 2
    return "-".join(signs)


def _vowel(v: str, rng: random.Random) -> str:
    return rng.choice(ENDING_VOWELS) if v == "V" else v


_HYPHENATED = re.compile(r"[^\s\d()+/,;:~=]+(?:-[^\s\d()+/,;:~=]+)+")


def lexicon_keys(entries: list[dict[str, Any]]) -> set[tuple[str, ...]]:
    """Every guttural-folded root key a lexicon entry's root field names, compounds included (b-ṭ-n + š-m-n)."""
    out: set[tuple[str, ...]] = set()
    for e in entries:
        for m in _HYPHENATED.findall(str(e.get("root") or "")):
            for key in parse_lexicon_root(m):
                out.add(fold_gutturals(key))
    return out


def eligible_records(records: list[dict[str, Any]], linked: set[tuple[str, ...]],
                     exclusions: dict[str, str]) -> tuple[list[tuple[str, Any]], Counter]:
    """(Number, first PS key) for records in the primary index with reflexes in ≥ 2 Semitic branches and no key
    a lexicon entry names; the rest counted by reason."""
    out, why = [], Counter()
    for rec in records:
        n = str(rec["Number"])
        keys = record_keys(rec)
        ps = [k for k in keys if k.kind == "ps"]
        if n in exclusions:
            why[exclusions[n]] += 1
        elif not ps:
            why["no_ps_key"] += 1
        elif len({k.branch for k in keys if k.kind == "reflex" and k.branch not in (None, "non_semitic")}) \
                < A9_MIN_BRANCHES:
            why["under_two_branches"] += 1
        elif any(fold_gutturals(k.radicals) in linked for k in keys if k.kind in ("ps", "weak")):
            why["lexicon_linked"] += 1
        else:
            out.append((n, ps[0]))
    return out, why


def plant(number: str, key: Any, seed: int, series: dict[str, dict[str, str]]) -> dict[str, Any]:
    rng = rm._rng(seed, number, "plant")
    fitted = headword_pattern(key.form, key.radicals)
    pattern, trailing = fitted if fitted else open_pattern(key.radicals)
    return {"number": number, "form": key.form, "radicals": " ".join(key.radicals),
            "spelled_from": "headword" if fitted else "open", "word": spell(pattern, trailing, rng, series)}


def plant_all(eligible: list[Any], k: int, seed: int, series: dict[str, dict[str, str]],
              gold: set[tuple[str, ...]] | Callable[[str], bool],
              make=None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """k planted words from the eligible items in a seeded order, by Number; a spelling that is a gold-set sign
    group is set aside, never queried (A14), and the next item is planted in its place. make spells one item
    (default: a semitic_roots (Number, PS key) pair through plant)."""
    make = make or (lambda item: plant(item[0], item[1], seed, series))
    is_gold = _gold_test(gold)
    order = list(eligible)
    random.Random(seed).shuffle(order)
    planted, skipped = [], []
    for item in order:
        if len(planted) == k:
            break
        p = make(item)
        (skipped if is_gold(p["word"]) else planted).append(p)
    return sorted(planted, key=lambda p: p["number"]), skipped


def writable(key: tuple[str, ...], series: dict[str, dict[str, str]], sub) -> bool:
    """Every token is a guttural (the script's rule decides it) or has a series at a substitution cost under 1.0."""
    return all(t in rm.GUTTURAL_PHONEMES or sub(t, series_consonant(t, series, sub)) < 1.0 for t in key)


def plant_competitor(space: Any, key: tuple[str, ...], numbers: list[str], seed: int,
                     series: dict[str, dict[str, str]]) -> dict[str, Any]:
    """A competitor key spelled the A9 way (A15): open pattern, series chosen on the competitor's own table."""
    rng = rm._rng(seed, f"{space.name}:{''.join(key)}", "plant")
    pattern, trailing = open_pattern(key)
    return {"competitor": space.name, "number": numbers[0], "numbers": numbers, "key": "".join(key),
            "radicals": " ".join(key), "spelled_from": "open",
            "word": spell(pattern, trailing, rng, series, space.sub)}


def a9_one(job: tuple[dict[str, Any], int, int]) -> dict[str, Any]:
    planted, n, seed = job
    engine = _ENGINE
    assert engine is not None
    r = engine.query(planted["word"], n=n, seed=seed, top=0,       # every cluster, so ties at d* are all seen
                     breadth_check=False)
    comp = {k: c["p_max"] for k, c in r.competitors.items()}
    row = {**planted, "skeleton": r.skeleton, "consonants": r.consonants, "d_star": rm._num(r.d_star),
           "p_max": r.p_max, "deciding_family": r.deciding_family, "verdict": r.verdict,
           "detected": r.p_max is not None and r.p_max < rm.P_SIGNAL,
           "best": r.best.number if r.best else None,
           "recovered": "competitor" not in planted and
           any(h.number == planted["number"] and h.distance <= r.d_star for h in r.clusters),
           "uniqueness": r.uniqueness, "saturation": r.saturation,
           "families": {k: {"n": f.n, "below": f.below, "tied": f.tied, "p": f.p} for k, f in r.families.items()},
           "competitors": comp, "semitic_specific": r.semitic_specific,
           "competitor_fired": sorted(k for k, p in comp.items() if p is not None and p < rm.P_SIGNAL)}
    if "competitor" in planted:
        own = comp.get(planted["competitor"])
        row["own_d_star"] = r.competitors.get(planted["competitor"], {}).get("d_star")
        row["own_detected"] = own is not None and own < rm.P_SIGNAL
    return row


def power_summary(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Power per skeleton length: share detected (p_max < 0.05); under UNDERPOWERED, labelled."""
    buckets: dict[int, list[dict[str, Any]]] = {}
    for r in rows:
        buckets.setdefault(r["consonants"], []).append(r)
    out = {}
    for k in sorted(buckets):
        b = buckets[k]
        power = sum(r["detected"] for r in b) / len(b)
        blocked = sum(bool(r.get("competitor_fired")) for r in b)
        out[str(k)] = {"n": len(b), "detected": sum(r["detected"] for r in b), "power": round(power, 4),
                       "recovered": sum(r["recovered"] for r in b), "underpowered": power < UNDERPOWERED,
                       "verdicts": dict(Counter(r["verdict"] for r in b)),
                       "competitor_fired": dict(Counter(c for r in b for c in r.get("competitor_fired", ()))),
                       "blocked": blocked, "blocked_share": round(blocked / len(b), 4)}
    return out


def competitor_power_summary(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """A15: one competitor's planted words, per skeleton length: the share its own p_max puts under 0.05 (power,
    labelled under UNDERPOWERED), and the share the Semitic statistic puts there too."""
    buckets: dict[int, list[dict[str, Any]]] = {}
    for r in rows:
        buckets.setdefault(r["consonants"], []).append(r)
    out = {}
    for k in sorted(buckets):
        b = buckets[k]
        power = sum(r["own_detected"] for r in b) / len(b)
        out[str(k)] = {"n": len(b), "detected": sum(r["own_detected"] for r in b), "power": round(power, 4),
                       "underpowered": power < UNDERPOWERED, "semitic_detected": sum(r["detected"] for r in b)}
    return out


def run_a9(args: argparse.Namespace) -> None:
    global _ENGINE
    out = Path(args.out)
    if out.exists():
        sys.exit(f"{out} exists; never overwritten")
    index_path = require(Path(args.index).resolve(), "the root index (build it with build_root_index.py)")
    before = _hashes(index_path)
    records = roots_records(json.loads(require(SEMITIC_ROOTS_DATA / "semitic_roots.json", "semitic_roots.json")
                                       .read_text(encoding="utf-8")))
    entries = json.loads(require(DATA_DIR / "lexicon.json", "lexicon.json").read_text(encoding="utf-8"))["entries"]
    exclusions = frozen_index_exclusions(GOLD_V3_PATH)        # A4's frozen list (A13, A17), never recomputed
    eligible, why = eligible_records(records, lexicon_keys(entries), exclusions)
    gold, series = gold_guard(), lb_series()
    planted, gold_skipped = plant_all(eligible, args.planted, args.seed, series, gold)
    spaces = load_competitors(args.names)
    comp_planted: dict[str, list[dict[str, Any]]] = {}
    comp_info: dict[str, dict[str, Any]] = {}
    for s in spaces:
        items = [(k, nums) for k, nums in sorted(s.keys.items()) if writable(k, series, s.sub)]
        comp_planted[s.name], skipped = plant_all(
            items, args.planted, args.seed, series, gold,
            make=lambda it, s=s: plant_competitor(s, it[0], it[1], args.seed, series))
        comp_info[s.name] = {"keys": len(s.keys), "dropped": s.dropped, "unwritable": len(s.keys) - len(items),
                             "gold_skipped": [{"key": p["key"], "word": p["word"]} for p in skipped]}
    index = RootIndex.load(index_path)
    _ENGINE = rm.Shoresh(index, names=args.names, exclude=exclusions, competitors=spaces)
    jobs = [(p, args.n, args.seed) for p in planted + [p for s in spaces for p in comp_planted[s.name]]]
    t0 = time.perf_counter()
    if args.workers > 1:
        with ProcessPoolExecutor(args.workers, mp_context=multiprocessing.get_context("fork")) as pool:
            rows = list(pool.map(a9_one, jobs, chunksize=1))
    else:
        rows = [a9_one(j) for j in jobs]
    semitic = [r for r in rows if "competitor" not in r]
    for name, info in comp_info.items():
        own = [r for r in rows if r.get("competitor") == name]
        info.update(planted=len(own), by_consonants=competitor_power_summary(own))
    summary = {
        "planted": len(semitic), "eligible": len(eligible), "ineligible": dict(why),
        "gold_skipped": [{"number": p["number"], "word": p["word"]} for p in gold_skipped],
        "spelled_from": dict(Counter(r["spelled_from"] for r in semitic)),
        "power_by_consonants": power_summary(semitic),
        "competitor_power": comp_info,
        "a4_absent": sorted(set(exclusions) - {k.number for k in index.keys if k.number is not None}),
        "seconds": round(time.perf_counter() - t0, 1),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    write_report(out, {"check": "A9", "index": str(index_path), "names": args.names, "n": args.n,
                       "summary": summary, "rows": rows}, before, args.seed)


def main() -> int:
    try:
        _run()
    except (NotInCheckout, IndexStale) as e:
        print(f"stopped: {e}", file=sys.stderr)
        return 2
    return 0


def _run() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("a12", help="retrieval against brute force on corpus words")
    a.add_argument("--index", default=str(DEFAULT_INDEX))
    a.add_argument("--n", type=int, default=A12_N)
    a.add_argument("--seed", type=int, default=rm.SEED)
    a.add_argument("--names", action="store_true", help="count onomastic lexemes (§1)")
    a.add_argument("--workers", type=int, default=1)
    a.add_argument("--out", required=True)
    p = sub.add_parser("a9", help="planted-signal power on the primary index")
    p.add_argument("--index", default=str(DEFAULT_INDEX))
    p.add_argument("--planted", type=int, default=A9_N)
    p.add_argument("--n", type=int, default=rm.DEFAULT_N, help="decoys per family")
    p.add_argument("--seed", type=int, default=rm.SEED)
    p.add_argument("--names", action="store_true", help="count onomastic lexemes (§1)")
    p.add_argument("--workers", type=int, default=1)
    p.add_argument("--out", required=True)
    args = parser.parse_args()
    if args.cmd == "a12":
        run_a12(args)
    elif args.cmd == "a9":
        run_a9(args)


if __name__ == "__main__":
    sys.exit(main())
