#!/usr/bin/env python3
"""Build, check or diff the Shoresh root index from semitic_roots.json and the Semitic contact lexica
(tools/core/root_index.py LEXICA).

The index is derived data, built in the user cache (`CACHE/root_index.sqlite`), never in the repository; no input
is ever written. Building refuses an existing index unless --force, and --force backs the old one up first
(root_index.sqlite.bak-<UTC stamp, µs>-<pid>, created exclusively); after a successful build only the 3 newest
stamped backups are kept. One build at a time (root_index.sqlite.lock). The new index is written to a temp file
beside the target, checked against the inputs, and only then renamed into place, so a failed or stale build leaves
the old one intact. A lexicon file that is missing fails the build unless --allow-missing.

    uv run tools/linear_a/build_root_index.py              # first build
    uv run tools/linear_a/build_root_index.py --check      # read-only: is the index current?
    uv run tools/linear_a/build_root_index.py --diff       # read-only: what changed since the build (§7.3)
    uv run tools/linear_a/build_root_index.py --diff --impact    # + the corpus words a rebuild can move (~45 s)
    uv run tools/linear_a/build_root_index.py --diff --preview   # + their top cluster and verdict, before and after
    uv run tools/linear_a/build_root_index.py --force      # rebuild, old index backed up

Long builds and --calibrate runs read a frozen snapshot (docs/shoresh-preregistration.md §7.7).

Attribution: di Mino
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import tempfile
import time
from collections.abc import Callable, Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = "tools.linear_a"

from ..core.root_index import (
    DEFAULT_INDEX,
    DEFAULT_ROOTS,
    LEXICA,
    IndexStale,
    Lexicon,
    RootIndex,
    diff_index,
    stale_inputs,
    write_index,
)

KEEP_BACKUPS = 3
_BACKUP_STAMP = re.compile(r"\.bak-(\d{8}T\d{6})(?:\.(\d{6}))?Z(?:-\d+)?")


def _backup(out: Path) -> Path:
    """Copy `out` to a backup name that cannot already exist (exclusive create; never overwrites)."""
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")
    backup = out.with_name(f"{out.name}.bak-{stamp}-{os.getpid()}")
    with out.open("rb") as src, backup.open("xb") as dst:
        shutil.copyfileobj(src, dst)
    shutil.copystat(out, backup)
    return backup


def _rotate_backups(out: Path) -> list[Path]:
    """Delete stamped build backups beyond the KEEP_BACKUPS newest; any other `.bak-` name is left alone."""
    stamped = []
    for p in out.parent.glob(f"{out.name}.bak-*"):
        m = _BACKUP_STAMP.fullmatch(p.name[len(out.name):])
        if m:
            stamped.append(((m[1], m[2] or "000000"), p))
    old = [p for _, p in sorted(stamped, reverse=True)[KEEP_BACKUPS:]]
    for p in old:
        p.unlink()
    return old


def _cleanup(tmp: Path) -> None:
    for p in (tmp, tmp.with_name(tmp.name + "-journal")):
        p.unlink(missing_ok=True)


def build(out: Path, roots: Path, force: bool, lexica: Iterable[Lexicon] = LEXICA, *,
          allow_missing: bool = False) -> int:
    out.parent.mkdir(parents=True, exist_ok=True)
    lock = out.with_name(out.name + ".lock")
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        holder = lock.read_text(encoding="utf-8", errors="replace").strip() or "?"
        print(f"{lock.name} held by pid {holder}: another build is running (remove the lock if it is not)",
              file=sys.stderr)
        return 1
    with os.fdopen(fd, "w") as fh:
        fh.write(str(os.getpid()))
    try:
        return _build_locked(out, roots, force, tuple(lexica), allow_missing)
    finally:
        lock.unlink(missing_ok=True)


def _build_locked(out: Path, roots: Path, force: bool, lexica: tuple[Lexicon, ...], allow_missing: bool) -> int:
    if out.exists() and not force:
        print(f"{out} exists; --check or --diff to inspect it, --force to rebuild (backs it up first)",
              file=sys.stderr)
        return 1
    tmp = out.with_name(f"{out.name}.tmp-{os.getpid()}")
    t0 = time.perf_counter()
    try:
        provenance = write_index(tmp, roots, lexica, allow_missing=allow_missing)
        built = time.perf_counter() - t0
        t1 = time.perf_counter()
        idx = RootIndex.load(tmp)                     # stale against the live inputs: never installed
        loaded = time.perf_counter() - t1
        if out.exists() and not force:
            print(f"{out} appeared during the build (another process?); not replaced, nothing kept",
                  file=sys.stderr)
            _cleanup(tmp)
            return 1
        if out.exists():
            print(f"backed up {out.name} -> {_backup(out).name}")
        os.replace(tmp, out)
    except BaseException:
        _cleanup(tmp)
        raise
    for p in _rotate_backups(out):
        print(f"removed old backup {p.name} (keeping the {KEEP_BACKUPS} newest)")
    c = provenance["counts"]
    print(f"wrote {out}: {c['roots']} roots, {c['keys']} keys, {out.stat().st_size / 1e6:.1f} MB; "
          f"build {built:.1f}s, load {loaded * 1000:.0f} ms, {idx.bucket_count} buckets")
    gaps = c.get("unkeyed_analogues", {})
    if gaps:
        print("  unkeyed Analogues entries (table unkeyed_analogues): "
              + ", ".join(f"{reason} {n}" for reason, n in gaps.items()))
    for name, lc in c["lexica"].items():
        if "missing" in lc:
            print(f"  {name}: MISSING (recorded; the file's arrival makes the index stale)")
            continue
        extra = ", ".join(f"{lc[k]} {k}" for k in ("keyless", "ghost", "phrase", "overlong_keys") if lc.get(k))
        print(f"  {name}: {lc['lexemes']} lexemes, {lc['keys']} keys, {lc['linked']} linked"
              + (f" ({extra})" if extra else ""))
    print("  links: " + ", ".join(f"{b} {n}" for b, n in c["links"].items()))
    return 0


def check(out: Path) -> int:
    if not out.exists():
        print(f"{out} not built")
        return 1
    changed = stale_inputs(out)
    if changed:
        print("stale; changed since the build:\n  " + "\n  ".join(changed))
        return 1
    print("current")
    return 0


def _print_diff(d: dict) -> None:
    rec = d["records"]
    print(f"index built {d['built_at']}; semitic_roots sha {str(d['roots_sha256_built'])[:8]} -> "
          f"{d['roots_sha256_now'][:8]}")
    if d.get("nfc_only"):
        print("the file changed but no record differs after NFC normalisation (--check still reports it stale)")
    if d["key_logic_changed"]:
        print("key logic changed (every Number re-keyed): " + ", ".join(d["key_logic_changed"]))
    print(f"records: +{len(rec['added'])} -{len(rec['removed'])} ~{len(rec['modified'])} "
          f"({len(rec['notes_only'])} notes only)")
    for n in rec["added"]:
        print(f"  + {n}")
    for n in rec["removed"]:
        merge = d["possible_merges"].get(n)
        print(f"  - {n}" + (f"  (possible merge into {', '.join(merge)})" if merge else ""))
    for n, changes in rec["modified"].items():
        print(f"  ~ {n}: {' '.join(changes)}")
    print(f"keys: {len(d['keys'])} Numbers re-keyed")
    for n, k in d["keys"].items():
        g = ", ".join(f"{kind}:{lang}:{rad}" for kind, lang, rad, _ in k["gained"])
        lost = ", ".join(f"{kind}:{lang}:{rad}" for kind, lang, rad, _ in k["lost"])
        print(f"  {n}: +[{g}] -[{lost}]  buckets +{k['shadow_gained']} -{k['shadow_lost']}")
    for name, ld in d["lexica"].items():
        print(f"lexicon {name}: +{len(ld['added'])} -{len(ld['removed'])} ~{len(ld['modified'])}")
        for sign, ids in (("+", ld["added"]), ("-", ld["removed"]), ("~", ld["modified"])):
            for i in ids[:20]:
                print(f"  {sign} {i}")
            if len(ids) > 20:
                print(f"  {sign} ... {len(ids) - 20} more")
    if d.get("lexica_unknown"):
        print("lexica the index records but LEXICA no longer specifies (not diffed): "
              + ", ".join(d["lexica_unknown"]))
    if "impact" in d:
        _print_impact(d["impact"])


IMPACT_SHOWN = 50      # impacted words listed in the text (--json has all)


def impact_inputs() -> tuple[list[str], Callable[[str], bool], dict[str, str], list[str]]:
    """(words, gold guard, A4 exclusions, corpus words) as root_match.py reads them: every corpus word, the gold
    set's guard by name or reading (A14, A16) and its frozen primary_index_exclusions (A17; ValueError if absent)."""
    from .validation.null_model_audit import load_corpus_words
    from .validation.root_match_phase0 import GOLD_V3_PATH, frozen_index_exclusions, gold_guard
    words = load_corpus_words()
    return words, gold_guard(GOLD_V3_PATH), frozen_index_exclusions(GOLD_V3_PATH), words


def impact(out: Path, roots: Path, lexica: Iterable[Lexicon], words: list[str], *, is_gold: Callable[[str], bool],
           exclusions: Iterable[str] = (), preview_n: int | None = None, corpus_words: list[str] | None = None,
           allow_missing: bool = False) -> dict[str, Any]:
    """§7.3 items 3 and 4. The current inputs are built into a temporary index, removed afterwards (nothing in the
    repository is written), and the engine over it is compared with the engine over the built index. Gold-set words
    are set aside before either engine sees them. Words go in canonical spelling, as root_match.py queries and
    seeds them (A16). preview_n: each impacted word is also queried on both indexes, with that many decoys per
    family (families ABC, seed SEED, no competitors, so never CONVERGENT)."""
    from ..core import root_match as rm
    from .validation.root_match_phase0 import sign_group_key
    asked = list(dict.fromkeys(c for c in ("-".join(sign_group_key(w)) for w in words) if c))
    kept = [w for w in asked if not is_gold(w)]
    exclude = frozenset(exclusions)
    out_d: dict[str, Any] = {"words": len(asked), "gold_set_aside": len(asked) - len(kept), "excluded": len(exclude)}
    with tempfile.TemporaryDirectory(prefix="root_index_impact_") as tmp:
        new_path = Path(tmp) / "root_index.sqlite"
        write_index(new_path, roots, lexica, allow_missing=allow_missing)
        old, new = (rm.Shoresh(RootIndex.load(p, check_inputs=False), exclude=exclude, corpus_words=corpus_words)
                    for p in (out, new_path))
        out_d["impacted"], out_d["breadth_only"], out_d["unmapped"] = rm.impact_words(old, new, kept)
        if preview_n is not None:
            out_d["preview_n"] = preview_n
            out_d["preview"] = []
            for w in out_d["impacted"]:
                row: dict[str, Any] = {"word": w}
                for side, engine in (("before", old), ("after", new)):
                    j = engine.query(w, n=preview_n, top=1, breadth_check=False, competitors=False).to_json()
                    row[side] = {"top": (j["best"] or {}).get("number"), "d_star": j["d_star"],
                                 "verdict": j["verdict"], "p_max": j["p_max"]}
                out_d["preview"].append(row)
    return out_d


def _print_impact(r: dict[str, Any]) -> None:
    def fmt(x: float | None) -> str:
        return "—" if x is None else f"{x:.4g}"

    def side(s: dict[str, Any]) -> str:
        return f"{s['top'] or '—'} d*={fmt(s['d_star'])} {s['verdict']} p_max={fmt(s['p_max'])}"

    gold = r["gold_set_aside"]
    print(f"impact: {len(r['impacted'])} of {r['words'] - gold} words retrieve a changed key "
          f"({gold} gold word{'' if gold == 1 else 's'} set aside, {len(r['unmapped'])} unmapped)"
          f"; key set primary (A4: {r['excluded']} Numbers out)")
    print(f"  {len(r['breadth_only'])} more words retrieve a key whose root gained or lost a branch or POS: "
          "breadth and the order of tied clusters only")
    print("  note: only the impacted words can change d* and the clusters at d*; p, saturation and so the verdict "
          "can move for any word, since the decoys query the whole index")
    if "preview" in r:
        print(f"preview (N={r['preview_n']} per family, families ABC, no competitors, so no CONVERGENT):")
        for row in r["preview"]:
            print(f"  {row['word']}  before {side(row['before'])}  after {side(row['after'])}")
        return
    for w in r["impacted"][:IMPACT_SHOWN]:
        print(f"  {w}")
    if len(r["impacted"]) > IMPACT_SHOWN:
        print(f"  ... {len(r['impacted']) - IMPACT_SHOWN} more")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="read-only: report whether the index is current")
    mode.add_argument("--diff", action="store_true", help="read-only: record and key diff since the build")
    mode.add_argument("--force", action="store_true", help="rebuild an existing index (backs it up first)")
    ap.add_argument("--json", action="store_true", help="--diff as JSON")
    ap.add_argument("--impact", action="store_true",
                    help="with --diff: the corpus words a rebuild can move (a temporary build, ~45 s; §7.3)")
    ap.add_argument("--preview", action="store_true",
                    help="with --diff: --impact plus each word's top cluster and verdict, before and after")
    ap.add_argument("--n", type=int, help="with --preview: decoys per family (default 1000)")
    ap.add_argument("--allow-missing", action="store_true",
                    help="build even if a lexicon file is missing (recorded as MISSING)")
    ap.add_argument("--roots", type=Path, default=DEFAULT_ROOTS)
    ap.add_argument("--out", type=Path, default=DEFAULT_INDEX)
    args = ap.parse_args()
    if args.json and not args.diff:
        ap.error("--json goes with --diff")
    if (args.impact or args.preview) and not args.diff:
        ap.error("--impact and --preview go with --diff")
    if args.n is not None and (not args.preview or args.n < 1):
        ap.error("--n goes with --preview and is at least 1")
    if args.check:
        return check(args.out)
    if args.diff:
        if not args.out.exists():
            print(f"{args.out} not built", file=sys.stderr)
            return 1
        d = diff_index(args.out, args.roots)
        if args.impact or args.preview:
            from ..core.root_match import DEFAULT_N
            try:
                words, is_gold, exclusions, corpus = impact_inputs()
                d["impact"] = impact(args.out, args.roots, LEXICA, words, is_gold=is_gold, exclusions=exclusions,
                                     preview_n=(args.n or DEFAULT_N) if args.preview else None,
                                     corpus_words=corpus, allow_missing=args.allow_missing)
            except (IndexStale, FileNotFoundError, ValueError) as e:
                print(e, file=sys.stderr)
                return 1
        if args.json:
            print(json.dumps(d, ensure_ascii=False, indent=1))
        else:
            _print_diff(d)
        return 0
    try:
        return build(args.out, args.roots, args.force, LEXICA, allow_missing=args.allow_missing)
    except (IndexStale, FileNotFoundError) as e:
        print(e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
