#!/usr/bin/env python3
"""Download Sedra's weekly data release and build from it a Syriac lexicon for the root index, on this machine only.

Sedra (Beth Mardutho: The Syriac Institute; ed. George A. Kiraz and James Bennett) publishes its verified lexicon
every week as gzipped JSON Lines tables, listed in https://sedra.bethmardutho.org/downloads/latest.json with each
file's size and SHA-256. Its data is under CC BY-NC 4.0, so this repository ships none of it: the shipped Syriac slot
holds English Wiktionary's roots (data/contact/syriac_lexicon.md). This tool fetches the six tables the build needs
(roots, lexemes, glosses, languages, category_types, etymologies), checks each against the manifest, and writes under
CACHE/sedra/<release>/:

    raw/<table>.jsonl.gz          the release's files, as published
    syriac_lexicon.jsonl          one row per lexeme with a root, in the shipped Syriac file's schema
    data/                         an overlay of DATA whose contact/syriac_lexicon.jsonl is the file above and whose
                                  every other file and folder links to DATA's own

Point the root index at the overlay with KAPHTOR_DATA and give the index its own file, so the default index stays
the shipped configuration:

    KAPHTOR_DATA=<release>/data uv run tools/linear_a/build_root_index.py --allow-missing --out <release>/root_index.sqlite
    KAPHTOR_DATA=<release>/data uv run tools/linear_a/root_match.py WORD --index <release>/root_index.sqlite

A row is a lexeme that is not merged into another, has a root, and whose root Sedra classes `semitic` or
`proper_name`; Sedra's `loanword`, `phrase` and `particle` roots are left out, since they name no Semitic radicals.
The root is Sedra's consonants in Latin, letter for letter as tools/core/sedra.py reads Syriac. `normalized` is the
West Syriac vocalized lexeme read through sedra.py, or empty where Sedra gives no vocalization or writes a sign sedra.py
does not read. `meaning` joins the English glosses in Sedra's order. A proper-noun category, or a proper-name root,
makes the row a name (`personal_name`, `toponym` or `proper_noun`), which the root index flags.

`etymology` lists what Sedra's etymologies table records for the lexeme (language, source word, meaning), in Sedra's
order. Sedra records there both the words a lexeme was borrowed from and Greek words that translate native ones, so
the record alone marks nothing: a row's semantic domain is `loan` only when sedra_loans.json, beside this file, rules
its lexeme a loan. The root index does not read the domain; loans stay in the build.

Requests: one at a time, ten seconds apart (Sedra's robots.txt asks for a Crawl-delay of 10 and for these files
instead of the site), with a User-Agent that names this project and nothing else. A file already in raw/ with the
manifest's hash is not fetched again; a file whose size or hash differs is deleted and the run stops.

Credit (the release's README): Sedra, edited by George A. Kiraz and James Bennett. Beth Mardutho: The Syriac
Institute. Data release <release>. CC BY-NC 4.0: for non-commercial use, with credit to Sedra and Beth Mardutho.

Usage:
    uv run tools/linear_a/fetch_sedra.py                  # newest release: fetch, check, build
    uv run tools/linear_a/fetch_sedra.py --from DIR --release 2026-10-25   # build from tables already in DIR
    uv run tools/linear_a/fetch_sedra.py --dry-run        # read the manifest and say what would be fetched
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import html
import json
import re
import shutil
import sys
import time
import unicodedata
import urllib.request
from collections import Counter, defaultdict
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = "tools.linear_a"

from ..core.contact_lexicon import validate_entry
from ..core.sedra import LETTERS, MARKS, VOWELS, to_latin
from ..paths import CACHE, DATA

BASE = "https://sedra.bethmardutho.org"
MANIFEST = BASE + "/downloads/latest.json"
UA = {"User-Agent": "kaphtor/1.0 (Semitic contact lexicon build)"}
CRAWL_DELAY = 10.0
TABLES = ("roots", "lexemes", "glosses", "languages", "category_types", "etymologies")
OUT_DIR = CACHE / "sedra"
SLOT = Path("contact") / "syriac_lexicon.jsonl"
RULINGS = Path(__file__).with_name("sedra_loans.json")

ROOT_KINDS = {"semitic", "proper_name"}
# Sedra's category_types names → the contact lexica's pos; the name classes are ones root_index.ONOMASTIC_POS flags
POS = {"noun": "noun", "substantive": "noun", "verb": "verb", "denominative": "verb", "adjective": "adj",
       "adjective of place": "adj", "participle adjective": "adj", "demonym": "adj", "adverb": "adv",
       "adverb ending with aiyt": "adv", "numeral": "num", "particle": "particle", "pronoun": "pron",
       "preposition": "prep", "interjection": "intj", "idiom": "phrase", "proper noun": "proper_noun",
       "proper noun (individual's name; e.g. Ephrem)": "personal_name",
       "proper noun (place name)": "toponym", "proper noun (nations; e.g. Huns)": "proper_noun"}

SYRIAC_LATIN = {syr: lat for syr, lat in LETTERS.values()}
# Unicode Syriac → the SEDRA codes sedra.to_latin reads (the inverse of its to_syriac)
TO_CODE = {syr: code for code, (syr, _) in LETTERS.items()}
TO_CODE.update({syr: code for code, (syr, _) in VOWELS.items()})
TO_CODE.update({syr: code for code, syr in MARKS.items()})
TO_CODE[" "] = "-"


class ReleaseError(RuntimeError):
    """The manifest or a downloaded file is not what Sedra published."""


# --- download -------------------------------------------------------------------------------------------------

def _get(url: str, timeout: int = 120) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as resp:
        return resp.read()


def manifest_files(manifest: dict[str, Any]) -> tuple[str, dict[str, dict[str, Any]]]:
    """The release (the date in its paths) and the manifest entry of each table the build needs."""
    files = {f["table"]: f for f in manifest.get("files", []) if "/sedra4/" not in f.get("path", "")}
    missing = [t for t in TABLES if t not in files]
    if missing:
        raise ReleaseError(f"manifest lists no {', '.join(missing)}")
    releases = {Path(files[t]["path"]).parent.name for t in TABLES}
    if len(releases) != 1:
        raise ReleaseError(f"manifest mixes releases: {sorted(releases)}")
    return releases.pop(), {t: files[t] for t in TABLES}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fetch(files: dict[str, dict[str, Any]], raw: Path, get: Callable[[str], bytes] = _get,
          sleep: Callable[[float], None] = time.sleep) -> list[str]:
    """Download each table not already in `raw` with the manifest's hash; returns the tables fetched."""
    raw.mkdir(parents=True, exist_ok=True)
    fetched = []
    for table, f in files.items():
        path = raw / f"{table}.jsonl.gz"
        if path.exists() and _sha256(path) == f["sha256"]:
            continue
        if fetched:
            sleep(CRAWL_DELAY)
        path.write_bytes(get(BASE + f["path"]))
        fetched.append(table)
        if path.stat().st_size != f["bytes"] or _sha256(path) != f["sha256"]:
            path.unlink()
            raise ReleaseError(f"{table}: size or SHA-256 differs from the manifest; file deleted")
    return fetched


# --- build ----------------------------------------------------------------------------------------------------

def read_table(raw: Path, table: str) -> list[dict[str, Any]]:
    with gzip.open(raw / f"{table}.jsonl.gz", "rt", encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def latin_root(syriac: str) -> str | None:
    """Sedra's root consonants as hyphenated Latin; None if a sign is not a Syriac letter."""
    letters = [SYRIAC_LATIN.get(ch) for ch in unicodedata.normalize("NFC", syriac)]
    return "-".join(letters) if letters and None not in letters else None


def latin_form(vocalized: str | None) -> str:
    """The vocalized lexeme in Latin through sedra.to_latin; empty where a sign has no SEDRA code."""
    if not vocalized:
        return ""
    try:
        return to_latin("".join(TO_CODE[ch] for ch in unicodedata.normalize("NFD", vocalized)))
    except (KeyError, ValueError):
        return ""


def _gloss(g: dict[str, Any]) -> str:
    """A gloss with its prefix and postfix, without the bidi marks and closing stops Sedra's imports carry, so that
    `air` and `air\N{RIGHT-TO-LEFT MARK}.` are one gloss, and without its HTML: the tags go
    (`<span class="selectableFont">` around a Syriac word, `<em>`), their text and the characters its entities name
    stay."""
    text = " ".join(p for p in (g.get("prefix"), g.get("meaning"), g.get("postfix")) if p)
    text = html.unescape(re.sub(r"<[^>]*>", "", text))
    return re.sub(r"\s+", " ", re.sub(r"[\N{LEFT-TO-RIGHT MARK}\N{RIGHT-TO-LEFT MARK}]", "", text)).strip().rstrip(".;, ").strip()


def load_rulings(path: Path = RULINGS) -> dict[str, dict[str, str]]:
    """sedra_loans.json: `loans` (lexeme id → the language it was borrowed from) and `not_loans` (lexeme id → why the
    etymology Sedra records is not its source)."""
    return json.loads(path.read_text(encoding="utf-8"))


def _etymology(e: dict[str, Any], languages: dict[int, str]) -> dict[str, str]:
    item = {"language": languages.get(e.get("language_id"), ""), "source_word": (e.get("source_word") or "").strip(),
            "meaning": (e.get("meaning") or "").strip()}
    return {k: v for k, v in item.items() if v}


def build_rows(tables: dict[str, list[dict[str, Any]]], release: str,
               rulings: dict[str, dict[str, str]] | None = None) -> tuple[list[dict[str, Any]], Counter]:
    """The lexicon rows and a tally of what was left out and why, and of how the etymologies were ruled."""
    rulings = load_rulings() if rulings is None else rulings
    roots = {r["id"]: r for r in tables["roots"]}
    english = {lang["id"] for lang in tables["languages"] if lang.get("iso_code") == "eng"}
    languages = {lang["id"]: lang.get("name", "") for lang in tables["languages"]}
    categories = {c["id"]: c["name"] for c in tables["category_types"]}
    glosses: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for g in tables["glosses"]:
        if g.get("language_id") in english:
            glosses[g["lexeme_id"]].append(g)
    etymologies: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for e in sorted(tables["etymologies"], key=lambda e: (e.get("sort_order") or 0, e["id"])):
        etymologies[e["lexeme_id"]].append(e)
    source = f"Sedra (Beth Mardutho), data release {release}"
    rows, tally = [], Counter()
    for lex in sorted(tables["lexemes"], key=lambda r: r["id"]):
        root = roots.get(lex.get("root_id"))
        if lex.get("is_merged") or lex.get("merged_into_id"):
            tally["merged lexeme"] += 1
            continue
        if root is None:
            tally["no root"] += 1
            continue
        if root.get("kind") not in ROOT_KINDS:
            tally[f"{root.get('kind')} root"] += 1
            continue
        latin = latin_root(root["syriac"])
        if latin is None:
            tally["root not in Syriac letters"] += 1
            continue
        pos = POS.get(categories.get(lex.get("category_type_id")), "unknown")
        if pos == "unknown" and root["kind"] == "proper_name":
            pos = "proper_noun"
        form = latin_form(lex.get("syriac_vocalized"))
        tally["no vocalized form read"] += not form
        seen: dict[str, str] = {}
        for g in sorted(glosses.get(lex["id"], []), key=lambda g: (g.get("sort_order") or 0, g["id"])):
            if s := _gloss(g):
                seen.setdefault(s.casefold(), s)
        meaning = "; ".join(seen.values())
        tally["no English gloss"] += not meaning
        key = str(lex["id"])
        loan = key in rulings["loans"]
        etymology = [_etymology(e, languages) for e in etymologies.get(lex["id"], [])]
        if loan:
            tally["loan (ruled)"] += 1
        elif etymology:
            tally["etymology ruled not a loan" if key in rulings["not_loans"] else "etymology not ruled"] += 1
        row = {
            "id": f"syr:sedra:{lex['id']}",
            "language": "Aramaic",
            "language_family": "Northwest Semitic",
            "dialect_labels": ["Syriac"],
            "form_original": lex.get("syriac_vocalized") or lex["syriac"],
            "form_consonantal": lex["syriac"],
            "normalized": form,
            "root": latin,
            "root_original": root["syriac"],
            "meaning": meaning,
            "pos": pos,
            "semantic_domain": ["loan" if loan else "general"],
            "match_keys": list(dict.fromkeys(k for k in (latin, latin.replace("-", ""), form) if k)),
            "source_refs": [{"source": source, "page": None, "lexeme": lex["id"], "root": root["id"]}],
            "review_status": "machine_imported",
        }
        if etymology:
            row["etymology"] = etymology
        rows.append(row)
    for row in rows:
        errors = validate_entry(row, "Aramaic")
        if errors:
            raise ReleaseError("; ".join(errors))
    return rows, tally


def write_overlay(release_dir: Path, lexicon: Path, data: Path = DATA) -> Path:
    """release_dir/data: every entry of `data` linked, except contact/, whose files are linked one by one with the
    Syriac slot pointing at `lexicon`. Rebuilt from scratch each run."""
    overlay = release_dir / "data"
    if overlay.is_symlink() or overlay.is_file():
        overlay.unlink()
    elif overlay.exists():
        shutil.rmtree(overlay)
    (overlay / "contact").mkdir(parents=True)
    for entry in sorted(data.iterdir()):
        if entry.name != "contact":
            (overlay / entry.name).symlink_to(entry.resolve())
    for entry in sorted((data / "contact").iterdir()):
        if entry.name != SLOT.name:
            (overlay / "contact" / entry.name).symlink_to(entry.resolve())
    (overlay / SLOT).symlink_to(lexicon.resolve())
    return overlay


def build(raw: Path, release_dir: Path, release: str) -> tuple[Path, int, Counter]:
    tables = {t: read_table(raw, t) for t in TABLES}
    rows, tally = build_rows(tables, release)
    lexicon = release_dir / SLOT.name
    lexicon.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    return write_overlay(release_dir, lexicon), len(rows), tally


def _report(release_dir: Path, overlay: Path, n: int, tally: Counter) -> None:
    print(f"{n:,} rows → {release_dir / SLOT.name}")
    for reason, k in sorted(tally.items(), key=lambda kv: -kv[1]):
        print(f"  {reason}: {k:,}")
    index = release_dir / "root_index.sqlite"
    print(f"\nKAPHTOR_DATA={overlay} uv run tools/linear_a/build_root_index.py --allow-missing --out {index}")
    print(f"KAPHTOR_DATA={overlay} uv run tools/linear_a/root_match.py WORD --index {index}")
    print("\nSedra (ed. Kiraz and Bennett), Beth Mardutho: CC BY-NC 4.0. Keep these files to non-commercial use.")


def main(argv: Iterable[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--dir", type=Path, default=OUT_DIR, help=f"where releases go (default {OUT_DIR})")
    ap.add_argument("--from", dest="src", type=Path,
                    help="build from <table>.jsonl.gz files already in this folder")
    ap.add_argument("--release", help="with --from: the release date the files are from (YYYY-MM-DD)")
    ap.add_argument("--dry-run", action="store_true", help="read the manifest only")
    args = ap.parse_args(list(argv) if argv is not None else None)
    if args.src and not args.release:
        ap.error("--from needs --release")
    try:
        if args.src:
            release = args.release
            release_dir = args.dir / release
            release_dir.mkdir(parents=True, exist_ok=True)
            overlay, n, tally = build(args.src, release_dir, release)
        else:
            release, files = manifest_files(json.loads(_get(MANIFEST, timeout=30)))
            if args.dry_run:
                for t, f in files.items():
                    print(f"{t}: {f['bytes']:,} bytes, {f['rows']:,} rows  {BASE}{f['path']}")
                print(f"release {release} → {args.dir / release}")
                return 0
            release_dir = args.dir / release
            time.sleep(CRAWL_DELAY)                    # the manifest was the first request
            fetched = fetch(files, release_dir / "raw")
            print(f"release {release}: fetched {', '.join(fetched) or 'nothing (all files current)'}")
            overlay, n, tally = build(release_dir / "raw", release_dir, release)
    except (ReleaseError, OSError) as e:
        print(f"fetch_sedra: {e}", file=sys.stderr)
        return 1
    _report(release_dir, overlay, n, tally)
    return 0


if __name__ == "__main__":
    sys.exit(main())
