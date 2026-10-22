"""Build the record wiki from the Linear A data files, or check that it is current.

    python -m tools.views.build --data DIR --out WIKI [--check | --write [--prune]] [--backups DIR]

`--data` is the folder holding corpus.json, lexicon.json and the rest; `--out` is the wiki folder (page paths drop
their leading `wiki/`). The data is only read.

`--check` is the default. It writes nothing, and proves it with a (path, size, mtime) snapshot taken before and
after. It exits 1 when a page is missing, stale or orphaned, when a page lacks the builder's block, or when a page
holds text outside its block (that text belongs in the data, and is never deleted).

`--write` writes the missing and stale pages, and nothing else. It refuses, writing nothing, when the wiki folder
has uncommitted changes (inside git) or holds pages it did not write (outside git), and when there are orphans and
no `--prune`. Before it changes or deletes a page it tars the page's current text into `--backups` (by default
`tools.paths.BACKUPS`, outside the repository). `--prune` deletes orphaned pages and reports those that look moved.

Folder indexes belong to `wiki update`, with one exception: the builder writes the `desc` of the folders it fills
(`indexes.py`), only where an index has none or `wiki update`'s placeholder, and creates a desc-only index where none
exists. The check counts each such folder as pending.

Either mode stops with ValueError, before touching a file, when two pages share a path (case aside) or a page path
leaves the wiki folder.
"""
from __future__ import annotations

import argparse
import io
import os
import subprocess
import sys
import tarfile
import time
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = "tools.views"

from ..paths import BACKUPS, NotInCheckout
from . import aegean, indexes, markdown, model, render, roots

INDEX = "_index.md"
SHOWN = 10


def file_for(out: Path, path: str) -> Path:
    """The file of a page path; ValueError for a path that would land outside `out`."""
    target = out / (path.removeprefix("wiki/") + ".md")
    if not target.resolve().is_relative_to(out.resolve()):
        raise ValueError(f"page path {path!r} leaves the wiki folder")
    return target


def snapshot(folder: Path) -> dict:
    if not folder.exists():
        return {}
    return {str(p): (p.stat().st_size, p.stat().st_mtime_ns) for p in sorted(folder.rglob("*")) if p.is_file()}


def wiki_files(out: Path) -> list[Path]:
    """The Markdown pages in the wiki folder; `_index.md` files belong to `wiki update` and are left alone, and so are
    dot folders inside the wiki (an editor's settings). Dot folders above it, such as `~/.config`, do not count."""
    if not out.exists():
        return []
    return sorted(p for p in out.rglob("*.md")
                  if p.name != INDEX and not any(s.startswith(".") for s in p.relative_to(out).parts))


def git_dirty(out: Path) -> list[str] | None:
    """Uncommitted changes under `out`, or None when `out` is not inside a git work tree."""
    probe = out if out.exists() else out.parent
    inside = subprocess.run(["git", "-C", str(probe), "rev-parse", "--is-inside-work-tree"], capture_output=True,
                            text=True, check=False)
    if inside.returncode != 0 or inside.stdout.strip() != "true":
        return None
    status = subprocess.run(["git", "-C", str(probe), "status", "--porcelain", "--", str(out)], capture_output=True,
                            text=True, check=True)
    return [line for line in status.stdout.splitlines() if line.strip()]


def plan(data: Path, out: Path) -> dict:
    """What a write would do, worked out without writing anything."""
    loaded = model.load(data)
    roots_data = Path(data).parent / "semitic-roots"     # the repository's layout: data/linear-a, data/semitic-roots
    pages = render.collect([*render.pages(loaded).items(), *aegean.pages(data).items(),
                            *roots.pages(roots_data).items()])
    fresh = {file_for(out, path): text for path, text in sorted(pages.items())}
    result = {"fresh": fresh, "missing": [], "stale": [], "current": [], "orphaned": [], "unmarked": [],
              "outside": [], "texts": {}, "indexes": {}}
    for folder, desc in {**indexes.descs(loaded), **roots.descs(roots_data)}.items():
        target = file_for(out, folder + "/" + INDEX.removesuffix(".md"))
        if not target.exists():
            result["indexes"][target] = markdown.frontmatter({"desc": desc}) + "\n"
            continue
        existing = target.read_text(encoding="utf-8")
        if markdown.parse_frontmatter(existing).get("desc") in (None, "", indexes.PLACEHOLDER):
            result["texts"][target] = existing
            result["indexes"][target] = markdown.set_frontmatter(existing, {"desc": desc})
    for target in sorted(fresh):
        if not target.exists():
            result["missing"].append(target)
            continue
        existing = target.read_text(encoding="utf-8")
        result["texts"][target] = existing
        if not markdown.is_generated(existing):
            result["unmarked"].append(target)
            continue
        if markdown.outside_text(existing):
            result["outside"].append(target)
        merged = markdown.splice(existing, fresh[target], render.OWNED_KEYS)
        (result["current"] if merged == existing else result["stale"]).append(target)
        result["texts"][target] = existing
    for target in wiki_files(out):
        if target in fresh:
            continue
        existing = target.read_text(encoding="utf-8")
        result["texts"][target] = existing
        (result["orphaned"] if markdown.is_generated(existing) else result["unmarked"]).append(target)
    result["unmarked"].sort()
    return result


def report(result: dict, out: Path) -> None:
    for name in ("missing", "stale", "orphaned", "unmarked", "outside", "indexes"):
        paths = list(result[name])
        if paths:
            label = {"unmarked": "without the builder's block", "outside": "with text outside the block",
                     "indexes": "folder indexes without a desc"}.get(name, name)
            print(f"{len(paths)} {label}:")
            for p in paths[:SHOWN]:
                print(f"  {p.relative_to(out)}")
            if len(paths) > SHOWN:
                print(f"  … and {len(paths) - SHOWN} more")
    print(f"{len(result['fresh'])} pages: {len(result['current'])} current, {len(result['stale'])} stale, "
          f"{len(result['missing'])} missing; {len(result['orphaned'])} orphaned")


def moved(result: dict) -> list[tuple[Path, Path]]:
    """Orphans whose title is the title of a missing page: a renamed form or key."""
    titles = {markdown.parse_frontmatter(result["fresh"][p]).get("title"): p for p in result["missing"]}
    pairs = []
    for orphan in result["orphaned"]:
        title = markdown.parse_frontmatter(result["texts"][orphan]).get("title")
        if title in titles:
            pairs.append((orphan, titles[title]))
    return pairs


def backup(paths: list[Path], texts: dict, out: Path, backups: Path) -> Path | None:
    if not paths:
        return None
    backups.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    target = backups / f"wiki-{stamp}.tar"
    n = 1
    while target.exists():
        n += 1
        target = backups / f"wiki-{stamp}-{n}.tar"
    with tarfile.open(target, "w") as tar:
        for p in paths:
            body = texts[p].encode("utf-8")
            info = tarfile.TarInfo(str(p.relative_to(out)))
            info.size, info.mtime = len(body), int(p.stat().st_mtime)
            tar.addfile(info, io.BytesIO(body))
    return target


def write(target: Path, text: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_name(f".{target.name}.tmp")
    temp.write_text(text, encoding="utf-8")
    os.replace(temp, target)


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
    parser.add_argument("--out", type=Path, required=True, help="the wiki folder")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="report only; the default")
    mode.add_argument("--write", action="store_true", help="write missing and stale pages")
    parser.add_argument("--prune", action="store_true", help="with --write, delete orphaned pages")
    parser.add_argument("--backups", type=Path, help="where --write tars the pages it changes")
    args = parser.parse_args(argv)
    if args.prune and not args.write:
        parser.error("--prune needs --write")
    out = args.out.resolve()

    if not args.write:
        before = snapshot(out), snapshot(args.data)
        result = plan(args.data, out)
        report(result, out)
        if (snapshot(out), snapshot(args.data)) != before:
            raise RuntimeError("the check changed files on disk")
        problems = ("missing", "stale", "orphaned", "unmarked", "outside", "indexes")
        return 1 if any(result[name] for name in problems) else 0

    dirty = git_dirty(out)
    if dirty:
        print(f"refused: the wiki folder has {len(dirty)} uncommitted change(s); commit or restore them first")
        return 1
    result = plan(args.data, out)
    if result["unmarked"]:
        print(f"refused: {len(result['unmarked'])} page(s) without the builder's block, which it will not touch:")
        for p in result["unmarked"][:SHOWN]:
            print(f"  {p.relative_to(out)}")
        return 1
    if result["orphaned"] and not args.prune:
        print(f"refused: {len(result['orphaned'])} orphaned page(s); rerun with --prune to delete them:")
        for p in result["orphaned"][:SHOWN]:
            print(f"  {p.relative_to(out)}")
        return 1
    for old, new in moved(result):
        print(f"moved: {old.relative_to(out)} -> {new.relative_to(out)}")
    changed = (result["stale"] + (result["orphaned"] if args.prune else [])
               + [t for t in result["indexes"] if t in result["texts"]])
    saved = backup(changed, result["texts"], out, (args.backups or BACKUPS).resolve())
    if saved:
        print(f"backed up {len(changed)} page(s) to {saved}")
    for target in result["missing"]:
        write(target, result["fresh"][target])
    for target in result["stale"]:
        write(target, markdown.splice(result["texts"][target], result["fresh"][target], render.OWNED_KEYS))
    for target, text in result["indexes"].items():
        write(target, text)
    for target in result["orphaned"] if args.prune else []:
        target.unlink()
    print(f"wrote {len(result['missing'])} new and {len(result['stale'])} changed page(s)"
          + (f", and {len(result['indexes'])} folder desc(s)" if result["indexes"] else "")
          + (f"; deleted {len(result['orphaned'])}" if args.prune and result["orphaned"] else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
