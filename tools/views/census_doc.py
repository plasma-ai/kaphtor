"""The generated blocks of the census reference, `docs/corpus-census.md`.

    python -m tools.views.census_doc --data DIR [--doc FILE] [--check | --write] [--backups DIR]

The reference is prose with named blocks between `<!-- BEGIN kaphtor:census NAME -->` and
`<!-- END kaphtor:census NAME -->`. Every number drawn from the data sits in a block, computed from `corpus.json`
and `census_classes.json` through `counts`; the prose keeps the editions' own figures. `--check`, the default, writes
nothing and exits 1 when a block is stale. `--write` copies the file into `--backups` (by default
`tools.paths.BACKUPS`, outside the repository) and rewrites the blocks only. A file missing a block, or naming one this tool does not make, is refused.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import time
from collections import Counter
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = "tools.views"

from ..paths import BACKUPS, REPO, NotInCheckout, require
from . import counts
from .model import natural

DOC = REPO / "docs" / "corpus-census.md"
BLOCK = re.compile(r"(<!-- BEGIN kaphtor:census (\S+) -->\n)(.*?)(<!-- END kaphtor:census \2 -->)", re.DOTALL)


def _keys(keys) -> str:
    return ", ".join(f"`{k}`" for k in keys)


def _table(head: list[str], rows: list[list[str]], align: str = "") -> list[str]:
    rule = "|" + "|".join(align or "---" for _ in head) + "|" if not align else align
    return ["| " + " | ".join(head) + " |", rule, *("| " + " | ".join(r) + " |" for r in rows)]


def blocks(corpus: dict, classes: dict) -> dict[str, list[str]]:
    """Block name -> its lines. ValueError if the class file does not fit the corpus, or the GORILA V check fails."""
    documents = counts.documents(corpus)
    klass = counts.classify(corpus, classes)
    by_class = Counter(klass.values())
    accepted, doubtful = classes["rila_s1_accepted"], classes["rila_s1_doubtful"]
    listed = classes["rila_s1_listed_not_counted"]
    out: dict[str, list[str]] = {}

    sides = sum(1 for r in corpus.values() if r.get("sigla_sides"))
    merged_into = sum(1 for r in corpus.values() if r.get("merged_records"))
    out["corpus"] = [(
        f"`corpus.json` holds **{len(corpus):,} records**, which group into **{len(documents):,} documents**. "
        f"SigLA's per-face records are folded into the record they describe (`sigla_sides`, {sides} records), and "
        f"second records of an object into their keeper (`merged_records`, {merged_into} records), each kept as a "
        "full snapshot.")]

    unlabelled = sorted(k for k, r in corpus.items() if not r.get("source_provenance"))
    labelled = sum(1 for keys in documents.values() if any(corpus[k].get("source_provenance") == "GORILA"
                                                            for k in keys))
    out["labels"] = [
        "Every record carries `source_provenance`" + (f" except {_keys(unlabelled)}" if unlabelled else "")
        + f". {labelled:,} documents carry the label `GORILA`."]

    held = [s for s, v in accepted.items() if v["keys"]]
    out["rila-accepted"] = [f"{len(held)} of the {len(accepted)} are held.", ""] + _table(
        ["RILA-S1", "Corpus key(s)", "Note"],
        [[s, _keys(v["keys"]) or "not held", v["note"]] for s, v in accepted.items()])

    held_d = [s for s, keys in doubtful.items() if keys]
    listed_held = [(s, keys) for s, keys in listed.items() if keys]
    out["rila-doubtful"] = [
        f"The corpus holds {len(held_d)} of the {len(doubtful)}, as {sum(len(k) for k in doubtful.values())} records.",
        ""] + _table(["RILA-S1", "Corpus key(s)"], [[s, _keys(k) or "not held"] for s, k in doubtful.items()]) + [
        "", "Listed by RILA-S1 but not counted, held in the corpus: "
        + "; ".join(f"{_keys(k)} ({s})" for s, k in listed_held) + "."]

    several = [(s, sorted({counts.doc_id(k) for k in v["keys"]}, key=natural)) for s, v in accepted.items()]
    several = [(s, d) for s, d in several if len(d) > 1]
    out["classes"] = _table(["Class", "Documents"], [[c, f"{by_class[c]:,}"] for c in counts.CLASSES],
                            "|---|---:|") + [f"| **Total** | **{sum(by_class.values()):,}** |", "",
                                             f"The {len(accepted)} RILA-S1 documents count as "
                                             f"{by_class['RILA-S1 accepted']} here, since "
                                             + "; ".join(f"{s} is held as {len(d)} documents ({_keys(d)})"
                                                         for s, d in several) + "."]

    identified = sorted(classes["gorila_unlabelled"], key=natural)
    since = [d for d in identified if klass.get(d) == "GORILA, labelled"]
    out["gorila-unlabelled"] = [
        f"GORILA V identifies {len(identified)} documents that lineara.xyz held without the label `GORILA`."
        + (f" {len(since)} of them now carry it ({_keys(since)}), so the class counts "
           f"{by_class['GORILA, unlabelled']}." if since else "")]

    gv = classes["gorila_v"]
    two = len(gv["records_holding_two_sigla"])
    rows = [["GORILA, labelled", by_class["GORILA, labelled"]],
            ["GORILA, unlabelled", by_class["GORILA, unlabelled"]],
            ["second sigla in one record (" + _keys(gv["records_holding_two_sigla"]) + ")", two],
            ["RILA-S1 accepted (" + _keys(gv["rila_s1_accepted"]) + ")", len(gv["rila_s1_accepted"])],
            ["RILA-S1 doubtful (" + _keys(gv["rila_s1_doubtful"]) + ")", len(gv["rila_s1_doubtful"])]]
    total = sum(n for _, n in rows)
    if total != gv["documents"]:
        raise ValueError(f"the GORILA V check gives {total}, not {gv['documents']}")
    out["gorila-check"] = _table(["Class", "GORILA documents"], [[c, f"{n:,}"] for c, n in rows if n], "|---|---:|") + [
        f"| **Total** | **{total:,}** |"]

    keepers: dict[str, list[str]] = {}
    for drop, keeper in classes["merged"].items():
        keepers.setdefault(keeper, []).append(drop)
    out["merged"] = [f"{len(classes['merged'])} second records of {len(keepers)} objects:", ""] + _table(
        ["Second record", "Keeper"], [[_keys(drops), f"`{k}`"] for k, drops in keepers.items()])

    outside = sorted(classes["outside_editions"], key=natural)
    out["outside-editions"] = [(f"These {len(outside)} documents fall outside both GORILA and RILA-S1: "
                                f"{_keys(outside)}.")]
    return out


BLOCKS = ("corpus", "labels", "rila-accepted", "rila-doubtful", "classes", "gorila-unlabelled", "gorila-check",
          "merged", "outside-editions")


def splice(text: str, fresh: dict[str, list[str]]) -> str:
    names = [m.group(2) for m in BLOCK.finditer(text)]
    if sorted(names) != sorted(BLOCKS):
        missing, extra = sorted(set(BLOCKS) - set(names)), sorted(set(names) - set(BLOCKS))
        raise ValueError(f"the census blocks do not match: missing {missing}, unknown {extra}, found {names}")
    return BLOCK.sub(lambda m: m.group(1) + "\n".join(fresh[m.group(2)]) + "\n" + m.group(4), text)


def main(argv: list[str] | None = None) -> int:
    """Exit 2 with the file's name when a data file is not in the checkout."""
    try:
        return _run(argv)
    except NotInCheckout as e:
        print(f"stopped: {e}", file=sys.stderr)
        return 2


def _run(argv: list[str] | None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--data", type=Path, required=True, help="the folder holding the Linear A data files")
    parser.add_argument("--doc", type=Path, default=DOC, help="the census reference (default: docs/corpus-census.md)")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="report only; the default")
    mode.add_argument("--write", action="store_true", help="rewrite the blocks")
    parser.add_argument("--backups", type=Path, default=BACKUPS, help="where --write copies the file first")
    args = parser.parse_args(argv)

    read = lambda name: json.loads(require(args.data / name, name).read_text(encoding="utf-8"))
    text = args.doc.read_text(encoding="utf-8")
    new = splice(text, blocks(read("corpus.json"), read("census_classes.json")))
    if new == text:
        print(f"{args.doc.name}: current")
        return 0
    stale = [m.group(2) for m, n in zip(BLOCK.finditer(text), BLOCK.finditer(new)) if m.group(3) != n.group(3)]
    if not args.write:
        print(f"{args.doc.name}: stale blocks: {', '.join(stale)}")
        return 1
    args.backups.mkdir(parents=True, exist_ok=True)
    saved = args.backups / f"{args.doc.stem}-{time.strftime('%Y%m%d-%H%M%S')}{args.doc.suffix}"
    shutil.copy2(args.doc, saved)
    args.doc.write_text(new, encoding="utf-8")
    print(f"{args.doc.name}: rewrote {', '.join(stale)}; the old file is {saved}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
