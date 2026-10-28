#!/usr/bin/env python3
"""Meaning-shuffle calibration and power (tools/core/meaning_shuffle.py simulate), on synthetic words only.

  uv run tools/linear_a/validation/meaning_shuffle_power.py --out power.json [--allow-stale] \
      [--set logogram|all] [--null-per-slot 40] [--plants-per-pool 40] [--calib-runs 1000] [--calib-perm 199] \
      [--runs 200] [--n-perm 499] [--k 5,10,20,40] [--tau 0,0.5,1] [--cap 1,2] [--seed 20261028] \
      [--no-competitors] [--conventional-values] [--fresh-null]

The slots are the anchored words' contexts and lengths; the anchored words themselves get no distance. Each slot's
null pool is family B of its word (A3: its sign count and skeleton length, the corpus's sign frequencies). A planted
word is a root spelled by A9's rules (plant for the Semitic side, plant_competitor for Luwian, Egyptian and
Hurrian), its domains fitting the slot's context and its sign count the slot's (5 standing for 5 or more). Any
fabricated or planted spelling that is a corpus word or a gold-set word is dropped before a distance is taken, and
counted. --conventional-values reads Linear B values only (tools/linear_a/root_match.py): a slot word with a sign
Linear B gives no value is unmapped, and no decoy draws such a sign (plants are spelled on the Linear B grid already).

Calibration: nothing planted, every test, the shuffle unstratified, by length and by the fine strata (length,
skeleton length and reading count, what family B keeps; a stratum of one slot falls back to its length); the type I
error at alpha and a
KS test of the p-values against U(0, 1). A run draws each slot's null row from its pool with replacement, so a fixed
pool is calibrated given that pool; --fresh-null draws each decoy once until the pool is spent, and with a pool of at
least the run count (pools_below_runs counts the slots short of it) the runs are independent draws of the null. Power: each arm's plants at each k, read by the Semitic test and the arm's
own; the Semitic plants by every competitor's test too (cross-talk both ways). A plant word fills at most one slot a
run, as a word list holds each word once, so an arm with few plants plants fewer than k (planted, planted_range; the
k it falls short at, plant_limited). k80 is the planted count at the least k whose power reaches 0.8. The same seed draws the same slots and plants for every test, so the tests are compared on the same runs.

The competitor arm gates each rival-language key by its entry's Meaning. The shipped Luwian, Egyptian and Hurrian
files carry no Meaning, so here the run stops with exit 2 unless --no-competitors; KAPHTOR_DATA points it at a data
folder whose rival files carry glosses (the corpus, roots and lexicon are read from there too).

Writes only --out, which must not exist; prints progress to stderr. The input hashes in the report are those of the
bytes loaded. Exit status: 0; 2 on a bad argument, if --out exists or cannot be written, an input is not in this
checkout, the index is stale, unreadable or changed while loading, or a rival-language file is unusable or carries
no glosses; 3 if the gold set is unreadable; 4 if the corpus, semitic_roots.json or lexicon.json is unreadable or of
the wrong shape, the tagger is not the one A18 froze, or no anchored word is left; 5 if a slot's word has no
fabricable decoy.

Attribution: di Mino
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sqlite3
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    __package__ = "tools.linear_a.validation"

from ...core import meaning_shuffle as ms
from ...core import root_match as rm
from ...core import semantic_gate as sg
from ...core.competitors import COMPETITORS, DATA_DIR
from ...core.root_index import DEFAULT_INDEX, IndexStale, RootIndex
from ...core.semitic_root_schema import roots_records
from ...paths import LINEAR_A_DATA, SEMITIC_ROOTS_DATA, NotInCheckout, require
from .meaning_shuffle import NoGlosses, competitor_spaces
from .root_match_checks import eligible_records, lb_series, lexicon_keys, plant, plant_competitor, writable
from .root_match_phase0 import GOLD_V3_PATH, frozen_index_exclusions, gold_guard, sign_group_key

GOLD = GOLD_V3_PATH
CORPUS = LINEAR_A_DATA / "corpus.json"
ROOTS = SEMITIC_ROOTS_DATA / "semitic_roots.json"
LEXICON = LINEAR_A_DATA / "lexicon.json"
RIVALS = DATA_DIR
CORPUS_WORDS: list[str] | None = None     # family B's sign tables; None: the engine reads the corpus's words
SEED = 20261028
shape = ms.shape


def _sha256(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def _read(path: Path, dataset: str) -> tuple[Any, str]:
    """A JSON file and the sha256 of the very bytes parsed; NotInCheckout if it is not there."""
    data = require(path, dataset).read_bytes()
    return json.loads(data.decode("utf-8")), hashlib.sha256(data).hexdigest()


def _list_of_objects(xs: Any, what: str) -> list[dict]:
    if not isinstance(xs, list) or not all(isinstance(x, dict) for x in xs):
        raise TypeError(f"{what} is not a list of objects")
    return xs


def _log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def k80(curve: dict[int, float], planted: dict[int, float]) -> float | None:
    """The planted count (mean over runs) at the least k whose power reaches 0.8, or None."""
    k = next((k for k in sorted(curve) if curve[k] >= 0.8), None)
    return None if k is None else planted[k]


def pool_by_shape(items: list[tuple[str, frozenset[str]]], contexts: list[frozenset[str]], cap: int,
                  seed: int) -> dict[tuple[int, int], list[str]]:
    """(context index, shape) → up to cap planted words whose domains fit the context, a seeded sample."""
    pools: dict[tuple[int, int], list[str]] = {}
    for word, doms in items:
        for c, ctx in enumerate(contexts):
            if sg.fits(doms, ctx):
                pools.setdefault((c, shape(word)), []).append(word)
    rng = random.Random(seed)
    return {key: sorted(rng.sample(sorted(set(ws)), min(cap, len(set(ws))))) for key, ws in sorted(pools.items())}


def scorers(taus: list[float], caps: list[float]) -> dict[str, Any]:
    out: dict[str, Any] = {"rank": ms.rank_row}
    for t in taus:
        out[f"count_{t:g}"] = lambda r, t=t: ms.count_row(r, t)
    for c in caps:
        out[f"cap_{c:g}"] = lambda r, c=c: ms.cap_row(r, c)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--set", choices=["logogram", "all"], default="logogram")
    ap.add_argument("--null-per-slot", type=int, default=40)
    ap.add_argument("--plants-per-pool", type=int, default=40)
    ap.add_argument("--calib-runs", type=int, default=1000)
    ap.add_argument("--calib-perm", type=int, default=199)
    ap.add_argument("--runs", type=int, default=200)
    ap.add_argument("--n-perm", type=int, default=499)
    ap.add_argument("--k", default="5,10,20,40")
    ap.add_argument("--tau", default="0,0.5,1")
    ap.add_argument("--cap", default="1,2")
    ap.add_argument("--alpha", type=float, default=0.05)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--index", default=str(DEFAULT_INDEX))
    ap.add_argument("--allow-stale", action="store_true")
    ap.add_argument("--no-competitors", action="store_true")
    ap.add_argument("--fresh-null", action="store_true",
                    help="each decoy enters once until its slot's pool is spent (ms.null_draws), not with replacement")
    ap.add_argument("--conventional-values", action="store_true",
                    help="Linear B values only (rm.sign_options): slots, decoys and plants")
    args = ap.parse_args(argv)
    try:
        ks = [int(x) for x in args.k.split(",") if x]
        taus = [float(x) for x in args.tau.split(",") if x]
        caps = [float(x) for x in args.cap.split(",") if x]
    except ValueError as e:
        ap.error(f"--k takes integers, --tau and --cap numbers, comma-separated: {e}")
    if not ks or min(ks) < 1:
        ap.error("--k takes one or more k of 1 or more")
    if not taus:
        ap.error("--tau takes one or more thresholds")
    if not caps or min(caps) <= 0:
        ap.error("--cap takes one or more caps above 0")
    for name in ("null_per_slot", "plants_per_pool", "calib_runs", "calib_perm", "runs", "n_perm"):
        if getattr(args, name) < 1:
            ap.error(f"--{name.replace('_', '-')} takes 1 or more")
    if not 0 < args.alpha < 1:
        ap.error("--alpha lies strictly between 0 and 1")
    if args.out.exists():
        print(f"{args.out} exists; never overwritten", file=sys.stderr)
        return 2
    try:
        args.out.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print(f"--out cannot be written: {e}", file=sys.stderr)
        return 2
    t0 = time.perf_counter()

    try:
        corpus, corpus_sha = _read(CORPUS, "corpus.json")
        ms.check_corpus(corpus)
        ctx_of = ms.anchored(corpus, args.set)
        raw_roots, roots_sha = _read(ROOTS, "semitic_roots.json")
        records = _list_of_objects(roots_records(raw_roots), ROOTS.name)
        raw_lexicon, lexicon_sha = _read(LEXICON, "lexicon.json")
        if not isinstance(raw_lexicon, dict):
            raise TypeError(f"{LEXICON.name} is not an object")
        entries = _list_of_objects(raw_lexicon.get("entries"), f"{LEXICON.name} entries")
        sg.tagger()
    except NotInCheckout as e:
        print(f"stopped: {e}", file=sys.stderr)
        return 2
    except (OSError, ValueError, TypeError, AttributeError, UnicodeDecodeError, sg.TaggerChanged) as e:
        print(f"input unusable: {e}", file=sys.stderr)
        return 4
    try:
        gold_sha = _sha256(GOLD)
        is_gold = gold_guard(GOLD, conventional=args.conventional_values)
        exclusions = frozen_index_exclusions(GOLD)
    except (OSError, ValueError, UnicodeDecodeError) as e:
        print(f"gold set unreadable: {e}", file=sys.stderr)
        return 3
    try:
        rival_sha = {} if args.no_competitors else {s.file: _sha256(RIVALS / s.file) for s in COMPETITORS}
        competitors = [] if args.no_competitors else competitor_spaces(RIVALS)
    except NotInCheckout as e:
        print(f"stopped: {e}", file=sys.stderr)
        return 2
    except NoGlosses as e:
        print(f"stopped: {e}; the competitor arm gates on them (or pass --no-competitors)", file=sys.stderr)
        return 2
    except (OSError, ValueError, TypeError, KeyError, AttributeError, UnicodeDecodeError) as e:
        print(f"rival-language file unusable: {e}", file=sys.stderr)
        return 2
    index_path = Path(args.index)
    try:
        index_sha = _sha256(require(index_path, "the root index (build it with build_root_index.py)"))
        index = RootIndex.load(index_path, check_inputs=not args.allow_stale)
    except NotInCheckout as e:
        print(f"stopped: {e}", file=sys.stderr)
        return 2
    except IndexStale as e:
        print(f"{e}\n(or pass --allow-stale)", file=sys.stderr)
        return 2
    except (OSError, ValueError, sqlite3.DatabaseError) as e:
        print(f"index unreadable: {e}", file=sys.stderr)
        return 2
    if _sha256(index_path) != index_sha:
        print(f"{index_path} changed while it was loading; rerun on a frozen snapshot", file=sys.stderr)
        return 2
    engine = rm.Shoresh(index, exclude=exclusions, corpus_words=CORPUS_WORDS, contexts=sg.Contexts(corpus),
                        conventional=args.conventional_values)
    real = {sign_group_key(w) for d in corpus.values() for w in d.get("transliteratedWords", []) if isinstance(w, str)}

    def usable(w: str) -> bool:
        return sign_group_key(w) not in real and not is_gold(w)

    words, unmapped, gold_aside = [], [], 0
    for w in sorted(ctx_of):
        if is_gold(w):
            gold_aside += 1
            continue
        try:
            engine.word_readings(w)
        except rm.UnmappedSign:
            unmapped.append(w)
            continue
        words.append(w)
    if not words:
        print(f"no slot: no anchored word left ({gold_aside} gold set aside, {len(unmapped)} unmapped)",
              file=sys.stderr)
        return 4
    contexts = sorted({ctx_of[w] for w in words}, key=sorted)
    slot_ctx = [contexts.index(ctx_of[w]) for w in words]
    slot_shape = [shape(w) for w in words]
    slot_fine = ms.fine_strata([ms.fine_key(engine, w) for w in words])
    plant_of = list(zip(slot_ctx, slot_shape, strict=True))
    dropped: Counter = Counter()

    # --- the words: fabricated nulls and planted roots (spellings only) ---
    null_words, gaps = [], 0
    for w in words:
        fabs, g = engine.family_b(w, args.null_per_slot, args.seed)
        gaps += g
        spelled = ["-".join(f) for f in fabs]
        keep = [f for f in spelled if usable(f)]
        dropped["null: a corpus or gold word"] += len(spelled) - len(keep)
        if not keep:
            print(f"no fabricable decoy for the slot of shape {shape(w)} in context {sorted(ctx_of[w])} "
                  f"(--null-per-slot {args.null_per_slot})", file=sys.stderr)
            return 5
        null_words.append(keep)
    _log(f"{len(words)} slots, {len(contexts)} contexts; {sum(map(len, null_words))} fabricated words "
         f"({time.perf_counter() - t0:.0f}s)")

    series = lb_series(conventional=args.conventional_values)
    eligible, ineligible = eligible_records(records, lexicon_keys(entries), exclusions)
    doms = engine._domains()
    items = []
    for n, key in eligible:
        d = doms.get(n, frozenset())
        if not d:
            dropped["semitic: no domain"] += 1
            continue
        w = plant(n, key, args.seed, series)["word"]
        if usable(w):
            items.append((w, d))
        else:
            dropped["semitic: a corpus or gold word"] += 1
    pools = {"semitic": pool_by_shape(items, contexts, args.plants_per_pool, args.seed)}
    tests: dict[str, ms.Distance] = {"semitic": ms.semitic_distance(engine)}
    for spec, space, cd in competitors:
        items = []
        for key, nums in sorted(space.keys.items()):
            d = frozenset().union(*(cd.get(n, frozenset()) for n in nums))
            if not d:
                dropped[f"{space.name}: no domain"] += 1
                continue
            if not writable(key, series, space.sub):
                dropped[f"{space.name}: not writable"] += 1
                continue
            w = plant_competitor(space, key, nums, args.seed, series)["word"]
            if usable(w):
                items.append((w, d))
            else:
                dropped[f"{space.name}: a corpus or gold word"] += 1
        pools[space.name] = pool_by_shape(items, contexts, args.plants_per_pool, args.seed)
        tests[space.name] = ms.competitor_distance(space, spec, cd, engine)
    readers = {arm: (list(tests) if arm == "semitic" else ["semitic", arm]) for arm in pools}

    # --- the distance rows: synthetic words only ---
    rows: dict[str, dict[str, list[float]]] = {t: {} for t in tests}

    def row(t: str, w: str) -> list[float]:
        r = rows[t].get(w)
        if r is None:
            r = rows[t][w] = [tests[t](w, c) for c in contexts]
        return r

    for t in tests:
        t1 = time.perf_counter()
        needed = [w for ws in null_words for w in ws]
        needed += [w for arm, rd in readers.items() if t in rd for ws in pools[arm].values() for w in ws]
        for w in needed:
            row(t, w)
        _log(f"rows for the {t} test: {len(rows[t])} words ({time.perf_counter() - t1:.0f}s)")

    def null_rows(t: str) -> list[list[list[float]]]:
        return [[rows[t][w] for w in ws] for ws in null_words]

    def plant_rows(t: str, arm: str) -> dict[tuple[int, int], list[list[float]]]:
        return {key: [rows[t][w] for w in ws] for key, ws in pools[arm].items()}

    sc = scorers(taus, caps)
    strata = {"none": None, "length": [str(s) for s in slot_shape], "fine": slot_fine}

    # --- calibration ---
    calibration: dict[str, Any] = {}
    for t in tests:
        for sname, st in strata.items():
            t1 = time.perf_counter()
            out = ms.simulate(slot_ctx, null_rows(t), {}, 0, args.calib_runs, args.calib_perm, args.seed, sc,
                              alpha=args.alpha, strata=st, keep_p=True, fresh_null=args.fresh_null)
            calibration[f"{t} / {sname}"] = {
                name: {"type_i": v["power"], "ks_d": round(ms.ks_uniform(v["p"])[0], 4),
                       "ks_p": round(ms.ks_uniform(v["p"])[1], 4),
                       "p_deciles": [round(sorted(v["p"])[int(q * (len(v["p"]) - 1))], 4) for q in
                                     (0.1, 0.25, 0.5, 0.75, 0.9)]}
                for name, v in out.items()}
            _log(f"calibration {t} / {sname} ({time.perf_counter() - t1:.0f}s)")

    # --- power ---
    power: dict[str, Any] = {}
    for arm, rd in readers.items():
        plantable = sum(1 for key in plant_of if pools[arm].get(key))
        for t in rd:
            for sname, st in strata.items():
                t1 = time.perf_counter()
                curve: dict[str, dict[int, float]] = {name: {} for name in sc}
                planted, planted_range = {}, {}
                for k in ks:
                    out = ms.simulate(slot_ctx, null_rows(t), plant_rows(t, arm), k, args.runs, args.n_perm,
                                      args.seed, sc, alpha=args.alpha, plant_of=plant_of, strata=st,
                                      plant_ids={key: list(ws) for key, ws in pools[arm].items()},
                                      fresh_null=args.fresh_null)
                    first = next(iter(out.values()))
                    planted[k], planted_range[k] = first["planted"], [first["planted_min"], first["planted_max"]]
                    for name, v in out.items():
                        curve[name][k] = v["power"]
                power[f"{arm} plants / {t} test / {sname}"] = {
                    "plantable_slots": plantable, "planted": planted, "planted_range": planted_range,
                    "plant_limited": [k for k in ks if planted[k] < k],
                    "curves": {name: {"power": c, "k80": k80(c, planted)} for name, c in curve.items()}}
                _log(f"power {arm} / {t} / {sname} ({time.perf_counter() - t1:.0f}s)")

    report = {
        "set": args.set, "seed": args.seed, "alpha": args.alpha, "fresh_null": args.fresh_null,
        "sign_values": "conventional" if args.conventional_values else "all",
        "args": {**vars(args), "out": str(args.out)},
        "sha256": {"index": index_sha, "corpus": corpus_sha, "gold": gold_sha, "semitic_roots": roots_sha,
                   "lexicon": lexicon_sha, "tagger": sg.TAGGER_SHA256, **rival_sha},
        "index_checked": index.checked,
        "slots": {"n": len(words), "gold_set_aside": gold_aside, "unmapped": unmapped,
                  "contexts": [sorted(c) for c in contexts],
                  "per_context": dict(Counter(str(c) for c in slot_ctx)),
                  "per_shape": dict(Counter(str(s) for s in slot_shape)),
                  "per_fine_stratum": dict(Counter(slot_fine)),
                  "per_context_shape": dict(Counter(f"{c} {s}" for c, s in plant_of))},
        "null": {"per_slot": [len(ws) for ws in null_words], "family_b_gaps": gaps,
                 "pools_below_runs": sum(len(ws) < max(args.calib_runs, args.runs) for ws in null_words)},
        "pools": {arm: {f"{c} {s}": len(ws) for (c, s), ws in p.items()} for arm, p in pools.items()},
        "semitic_eligible": len(eligible), "semitic_ineligible": dict(ineligible), "dropped": dict(dropped),
        "calibration": calibration, "power": power, "seconds": round(time.perf_counter() - t0, 1),
    }
    try:
        with args.out.open("x", encoding="utf-8") as f:       # never overwritten, even by a file made mid-run
            f.write(json.dumps(report, ensure_ascii=False, indent=1) + "\n")
    except FileExistsError:
        print(f"{args.out} appeared during the run; never overwritten", file=sys.stderr)
        return 2
    _log(f"written {args.out} ({report['seconds']}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
