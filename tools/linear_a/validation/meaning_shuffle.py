#!/usr/bin/env python3
"""Meaning-shuffle test (tools/core/meaning_shuffle.py): anchored Linear A words against Semitic roots gated by
each word's context, the contexts shuffled among the words; the same test against each competitor with
--competitors.

  uv run tools/linear_a/validation/meaning_shuffle.py --prereg docs/meaning-shuffle-preregistration.md \
      --stat rank|count|cap [--tau 0.5] [--cap 1] [--set logogram|all] \
      [--strata source|length|source-length|fine] [--n 10000] [--seed 20261028] [--competitors] \
      [--conventional-values]

Report-only: prints JSON, writes nothing. The run is refused without --prereg naming the signed pre-registration,
whose sha256 is stamped with those of the index, the corpus, the gold set and the frozen tagger. Gold-set words are
set aside and counted unless --gold-run. The primary key set leaves A4's Numbers out, as Shoresh. --strata length
shuffles contexts only among words of one sign count (5 standing for 5 or more, as in the power study): a broad
context fits more roots, and short words gain most from it. --strata fine shuffles only among words of one sign
count, skeleton length and reading count, what family B keeps (A3, A11), a word alone in its stratum falling back
to its sign count. --stat cap sums each word's own-context distance capped
at --cap, so a near match counts by how near it is. --conventional-values reads Linear B values only
(tools/linear_a/root_match.py): a word with a sign Linear B gives no value joins the unmapped list.

--competitors gates each rival-language key by its entry's Meaning. The shipped Luwian, Egyptian and Hurrian files
carry no Meaning, so here the command stops with exit 2; KAPHTOR_DATA points it at a data folder whose rival files
carry glosses (the corpus, roots and lexicon are read from there too).

Exit status: 0; 2 if the index is stale, unreadable or changed while loading, or a rival-language file is not in
the checkout, unreadable or without glosses (--competitors); 3 if the gold set or the A4 list read from it is
unreadable; 4 if data/linear-a/corpus.json is unreadable or of the wrong shape, or the tagger is not the one A18
froze; 5 without a pre-registration file.

Attribution: di Mino
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    __package__ = "tools.linear_a.validation"

from ...core import meaning_shuffle as ms
from ...core import root_match as rm
from ...core import semantic_gate as sg
from ...core.competitors import COMPETITORS, DATA_DIR, load
from ...core.root_index import DEFAULT_INDEX, IndexStale, RootIndex
from ...paths import LINEAR_A_DATA, NotInCheckout
from .root_match_phase0 import GOLD_V3_PATH, frozen_index_exclusions, gold_guard

GOLD = GOLD_V3_PATH
CORPUS = LINEAR_A_DATA / "corpus.json"
RIVALS = DATA_DIR
SEED = 20261028


class NoGlosses(ValueError):
    """A rival-language file whose entries carry no Meaning: no key fits any context, so every distance is INF."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def strata_of(words: list[str], logo: set[str], mode: str, engine: rm.Shoresh | None = None) -> list[str] | None:
    """Each word's stratum: none, source (logogram- or document-anchored), length (sign count), both, or fine (what
    family B keeps, read through engine)."""
    if mode == "none":
        return None
    if mode == "fine":
        return ms.fine_strata([ms.fine_key(engine, w) for w in words])
    source = ["logogram" if w in logo else "document" for w in words]
    length = [str(ms.shape(w)) for w in words]                     # the power study's shapes: 5 is 5 or more
    return {"source": source, "length": length,
            "source-length": [f"{s} {n}" for s, n in zip(source, length, strict=True)]}[mode]


def competitor_spaces(data_dir: Path) -> list[tuple[Any, Any, dict[str, frozenset[str]]]]:
    """(spec, space, Number → domains) for each competitor, names out as on the Semitic side."""
    out = []
    for s in COMPETITORS:
        space = load(s, data_dir=data_dir)
        doms = ms.competitor_domains(s, data_dir)
        if not any(doms.values()):
            raise NoGlosses(f"{s.file} carries no glosses (Meaning), so no key fits any context")
        out.append((s, space, doms))
    return out


def one_test(words: list[str], ctx_of: dict[str, frozenset[str]], dist: ms.Distance, stat: str, tau: float | None,
             cap: float | None, n: int, seed: int, strata: list[str] | None) -> dict[str, Any]:
    contexts = sorted(set(ctx_of.values()), key=sorted)
    assign = [contexts.index(ctx_of[w]) for w in words]
    D = ms.context_matrix(words, contexts, dist)
    f = {"rank": ms.t_rank, "count": lambda D, a: ms.t_count(D, a, tau), "cap": lambda D, a: ms.t_cap(D, a, cap)}[stat]
    out = ms.shuffle_test(D, assign, f, n, seed, strata)
    out["words_with_a_match"] = sum(any(x < rm.INF for x in row) for row in D)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--prereg", type=Path, help="the signed pre-registration (required)")
    ap.add_argument("--set", choices=["logogram", "all"], default="logogram")
    ap.add_argument("--stat", choices=["rank", "count", "cap"], required=True)
    ap.add_argument("--tau", type=float, help="T_count's threshold (with --stat count)")
    ap.add_argument("--cap", type=float, help="T_cap's cap on a distance (with --stat cap)")
    ap.add_argument("--strata", choices=["none", "source", "length", "source-length", "fine"], default="none",
                    help="source: shuffle only among logogram-anchored or among document-anchored words; "
                         "length: only among words of one sign count; fine: of one sign count, skeleton length and "
                         "reading count")
    ap.add_argument("--n", type=int, default=10_000)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--competitors", action="store_true")
    ap.add_argument("--index", default=str(DEFAULT_INDEX))
    ap.add_argument("--allow-stale", action="store_true")
    ap.add_argument("--full-index", action="store_true", help="secondary result: no A4 exclusions")
    ap.add_argument("--gold-run", action="store_true", help="keep the gold-set words in")
    ap.add_argument("--conventional-values", action="store_true",
                    help="Linear B values only (rm.sign_options): a word with a sign Linear B gives no value is unmapped")
    args = ap.parse_args(argv)
    if args.stat == "count" and args.tau is None:
        ap.error("--stat count needs --tau")
    if args.stat == "cap" and not (args.cap or 0) > 0:
        ap.error("--stat cap needs a --cap above 0")
    if args.n < 1:
        ap.error("--n takes 1 or more")
    if args.prereg is None or not args.prereg.is_file():
        print("refused: no pre-registration file (--prereg); no distance is computed on real words before it is "
              "signed", file=sys.stderr)
        return 5
    try:
        corpus_raw = CORPUS.read_bytes()
        corpus = json.loads(corpus_raw.decode("utf-8"))
        ms.check_corpus(corpus)
        ctx_of = ms.anchored(corpus, args.set)
        logo = set(ms.anchored(corpus, "logogram"))
        contexts = sg.Contexts(corpus)
        sg.tagger()
    except (OSError, ValueError, TypeError, UnicodeDecodeError, sg.TaggerChanged) as e:
        print(f"corpus or tagger unusable: {e}", file=sys.stderr)
        return 4
    gold_sha, set_aside = None, []
    if not args.gold_run:
        try:
            gold_sha = _sha256(GOLD)
            is_gold = gold_guard(GOLD, conventional=args.conventional_values)
        except (OSError, ValueError, UnicodeDecodeError) as e:
            print(f"gold set unreadable: {e}", file=sys.stderr)
            return 3
        set_aside = sorted(w for w in ctx_of if is_gold(w))
        ctx_of = {w: c for w, c in ctx_of.items() if w not in set_aside}
    try:
        competitors = competitor_spaces(RIVALS) if args.competitors else []
    except NotInCheckout as e:
        print(f"stopped: {e}; --competitors reads it", file=sys.stderr)
        return 2
    except NoGlosses as e:
        print(f"stopped: {e}; the competitor arm gates on them", file=sys.stderr)
        return 2
    except (OSError, ValueError, UnicodeDecodeError) as e:
        print(f"rival-language file unreadable: {e}", file=sys.stderr)
        return 2
    index_path = Path(args.index)
    try:
        index_sha = _sha256(index_path)
        index = RootIndex.load(index_path, check_inputs=not args.allow_stale)
    except IndexStale as e:
        print(f"{e}\n(or pass --allow-stale)", file=sys.stderr)
        return 2
    except (OSError, ValueError, sqlite3.DatabaseError) as e:
        print(f"index unreadable: {e}", file=sys.stderr)
        return 2
    if _sha256(index_path) != index_sha:
        print(f"{index_path} changed while it was loading; rerun on a frozen snapshot (§7.7)", file=sys.stderr)
        return 2
    try:
        exclusions = None if args.full_index else frozen_index_exclusions(GOLD)
    except (OSError, ValueError, UnicodeDecodeError) as e:
        print(f"no primary key set (the A4 list): {e} (--full-index gives the secondary result)", file=sys.stderr)
        return 3
    engine = rm.Shoresh(index, exclude=exclusions or (), contexts=contexts, conventional=args.conventional_values)
    unmapped = []
    for w in sorted(ctx_of):
        try:
            engine.word_readings(w)
        except rm.UnmappedSign:
            unmapped.append(w)              # listed, never shortened (A5)
    words = [w for w in sorted(ctx_of) if w not in unmapped]
    ctx_of = {w: ctx_of[w] for w in words}
    strata = strata_of(words, logo, args.strata, engine)
    run = {"stat": args.stat, "tau": args.tau, "cap": args.cap, "n": args.n, "seed": args.seed, "strata": strata}
    report: dict[str, Any] = {
        "set": args.set, "stat": args.stat, "tau": args.tau, "cap": args.cap, "n": args.n, "seed": args.seed,
        "strata": args.strata, "sign_values": "conventional" if args.conventional_values else "all",
        "words": len(words), "contexts": len(set(ctx_of.values())), "gold_set_aside": len(set_aside),
        "unmapped": unmapped,
        "key_set": "full (secondary)" if exclusions is None else f"primary (A4: {len(exclusions)} Numbers out)",
        "sha256": {"prereg": _sha256(args.prereg), "index": index_sha, "corpus": hashlib.sha256(corpus_raw).hexdigest(),
                   "gold": gold_sha, "tagger": sg.TAGGER_SHA256},
        "index_checked": index.checked,
        "semitic": one_test(words, ctx_of, ms.semitic_distance(engine), **run),
    }
    if competitors:
        report["competitors"] = {space.name: one_test(words, ctx_of, ms.competitor_distance(space, spec, doms, engine),
                                                      **run)
                                 for spec, space, doms in competitors}
    print(json.dumps(report, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
