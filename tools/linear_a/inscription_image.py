#!/usr/bin/env python3
"""Query Linear A inscription and facsimile images from a local lashon-ha-kretan checkout.

Set LASHON_HA_KRETAN_DIR to the checkout (the folder holding `images/`). data/linear-a/inscription_image_files.json
names each record's files there; corpus.json gives its site and context. The manifest `build` writes goes to the
user cache (CACHE/linear-a/inscription_images.json) unless --out names another file. The images are their
sources', not ours to redistribute.

Examples:
  inscription_image.py status
  inscription_image.py audit --json
  inscription_image.py build
  inscription_image.py HT87 --json
  inscription_image.py HT87 --kind facsimile --open
  inscription_image.py HT87 HT97a --copy-to source-packet/
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
from collections.abc import Iterable
from difflib import get_close_matches
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = "tools.linear_a"

from ..core.normalization import normalize_id
from ..paths import CACHE, LINEAR_A_DATA, NotInCheckout, require

CORPUS_PATH = LINEAR_A_DATA / "corpus.json"
FILES_PATH = LINEAR_A_DATA / "inscription_image_files.json"
MANIFEST_PATH = CACHE / "linear-a" / "inscription_images.json"

DEFAULT_LASHON_DIRS = [
    Path(os.environ["LASHON_HA_KRETAN_DIR"]) if os.environ.get("LASHON_HA_KRETAN_DIR") else None,
]

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}
KINDS = {"image", "facsimile"}

DISCLAIMER = (
    "Linear A readings remain evidence-gated. Image lookups provide source "
    "evidence for transcription review, not proof of decipherment."
)


def lashon_dir() -> Path:
    for path in DEFAULT_LASHON_DIRS:
        if path and (path / "images").exists():
            return path
    searched = [str(p) for p in DEFAULT_LASHON_DIRS if p]
    raise NotInCheckout("the lashon-ha-kretan images are not in this checkout (set LASHON_HA_KRETAN_DIR to a "
                        f"checkout holding images/; looked in {searched or 'nothing'})")


def load_corpus() -> dict:
    return json.loads(require(CORPUS_PATH, CORPUS_PATH.name).read_text(encoding="utf-8"))


def load_file_index() -> dict:
    """Each record's image files in a lashon-ha-kretan checkout: {id: {"inscription": [...], "facsimile": [...]}}."""
    return json.loads(require(FILES_PATH, FILES_PATH.name).read_text(encoding="utf-8"))["files"]


def safe_file_stem(value: str) -> str:
    keep = []
    for ch in value:
        if ch.isalnum() or ch in {"-", "_", "+", "."}:
            keep.append(ch)
        else:
            keep.append("_")
    return "".join(keep).strip("_") or "image"


def image_dimensions(path: Path) -> dict | None:
    """Return image dimensions for PNG/JPEG without external dependencies."""
    try:
        with path.open("rb") as f:
            sig = f.read(24)
            if sig.startswith(b"\x89PNG\r\n\x1a\n") and len(sig) >= 24:
                width, height = struct.unpack(">II", sig[16:24])
                return {"width": int(width), "height": int(height)}
            if sig[:2] == b"\xff\xd8":
                f.seek(2)
                while True:
                    marker_start = f.read(1)
                    if not marker_start:
                        return None
                    if marker_start != b"\xff":
                        continue
                    marker = f.read(1)
                    while marker == b"\xff":
                        marker = f.read(1)
                    if marker in {b"\xd8", b"\xd9"}:
                        continue
                    size_raw = f.read(2)
                    if len(size_raw) != 2:
                        return None
                    size = struct.unpack(">H", size_raw)[0]
                    if marker in {
                        b"\xc0",
                        b"\xc1",
                        b"\xc2",
                        b"\xc3",
                        b"\xc5",
                        b"\xc6",
                        b"\xc7",
                        b"\xc9",
                        b"\xca",
                        b"\xcb",
                        b"\xcd",
                        b"\xce",
                        b"\xcf",
                    }:
                        data = f.read(5)
                        if len(data) != 5:
                            return None
                        height, width = struct.unpack(">HH", data[1:5])
                        return {"width": int(width), "height": int(height)}
                    f.seek(size - 2, 1)
    except OSError:
        return None
    return None


def sha256(path: Path) -> str | None:
    try:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for block in iter(lambda: f.read(1024 * 1024), b""):
                h.update(block)
        return h.hexdigest()
    except OSError:
        return None


def file_record(inscription_id: str, kind: str, rel_path: str, root: Path) -> dict:
    path = root / rel_path
    exists = path.exists()
    rec = {
        "inscription_id": inscription_id,
        "kind": kind,
        "relative_path": rel_path,
        "absolute_path": str(path),
        "exists": exists,
        "suffix": path.suffix.lower(),
    }
    if exists:
        stat = path.stat()
        rec.update(
            {
                "bytes": stat.st_size,
                "sha256": sha256(path),
                "dimensions": image_dimensions(path),
            }
        )
    return rec


def build_manifest() -> dict:
    root = lashon_dir()
    corpus = load_corpus()
    index = load_file_index()
    records = {}
    all_files = []
    missing = []
    for inscription_id, entry in corpus.items():
        files = index.get(inscription_id, {})
        images = []
        for rel in files.get("inscription") or []:
            rec = file_record(inscription_id, "image", rel, root)
            images.append(rec)
            all_files.append(rec)
            if not rec["exists"]:
                missing.append(rec)
        facsimiles = []
        for rel in files.get("facsimile") or []:
            rec = file_record(inscription_id, "facsimile", rel, root)
            facsimiles.append(rec)
            all_files.append(rec)
            if not rec["exists"]:
                missing.append(rec)
        records[inscription_id] = {
            "id": inscription_id,
            "site": entry.get("site"),
            "support": entry.get("support"),
            "findspot": entry.get("findspot"),
            "context": entry.get("context"),
            "image_rights": entry.get("imageRights"),
            "image_rights_url": entry.get("imageRightsURL"),
            "images": images,
            "facsimiles": facsimiles,
            "has_any_reference": bool(images or facsimiles),
            "has_existing_image": any(r["exists"] for r in images),
            "has_existing_facsimile": any(r["exists"] for r in facsimiles),
        }
    manifest = {
        "disclaimer": DISCLAIMER,
        "generated_from": [str(FILES_PATH), str(CORPUS_PATH)],
        "lashon_ha_kretan_dir": str(root),
        "records": records,
        "summary": summarize(records, all_files, missing),
    }
    return manifest


def summarize(records: dict, all_files: list[dict], missing: list[dict] | None = None) -> dict:
    if missing is None:
        missing = [r for r in all_files if not r.get("exists")]
    image_refs = [r for r in all_files if r["kind"] == "image"]
    facsimile_refs = [r for r in all_files if r["kind"] == "facsimile"]
    return {
        "corpus_records": len(records),
        "records_with_any_image_ref": sum(1 for r in records.values() if r["has_any_reference"]),
        "records_with_inscription_ref": sum(1 for r in records.values() if r["images"]),
        "records_with_facsimile_ref": sum(1 for r in records.values() if r["facsimiles"]),
        "image_refs_total": len(image_refs),
        "image_refs_existing": sum(1 for r in image_refs if r["exists"]),
        "facsimile_refs_total": len(facsimile_refs),
        "facsimile_refs_existing": sum(1 for r in facsimile_refs if r["exists"]),
        "all_refs_total": len(all_files),
        "all_refs_existing": sum(1 for r in all_files if r["exists"]),
        "all_refs_missing": len(missing),
        "missing": [
            {
                "inscription_id": r["inscription_id"],
                "kind": r["kind"],
                "relative_path": r["relative_path"],
                "absolute_path": r["absolute_path"],
            }
            for r in missing
        ],
    }


def load_manifest(rebuild: bool = False) -> dict:
    """The cached manifest while it is current: built from these sources and this checkout, after their last change."""
    sources = [FILES_PATH, CORPUS_PATH]
    if not rebuild and MANIFEST_PATH.exists():
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        newest = max((p.stat().st_mtime for p in sources if p.exists()), default=0.0)
        if (manifest.get("generated_from") == [str(p) for p in sources]
                and manifest.get("lashon_ha_kretan_dir") == str(lashon_dir())
                and MANIFEST_PATH.stat().st_mtime >= newest):
            return manifest
    manifest = build_manifest()
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return manifest


def record_files(record: dict, kind: str) -> list[dict]:
    rows = []
    if kind in {"any", "image"}:
        rows.extend(record.get("images") or [])
    if kind in {"any", "facsimile"}:
        rows.extend(record.get("facsimiles") or [])
    return rows


def resolve_records(manifest: dict, ids: Iterable[str]) -> tuple[list[dict], list[dict]]:
    records = manifest["records"]
    ids = list(ids)
    norm_index: dict[str, list[str]] = {}
    for key in records:
        norm_index.setdefault(normalize_id(key), []).append(key)

    # CLI users often type IDs like `HT 87` without quotes. Treat the full
    # argument string as a single ID when that resolves exactly.
    if len(ids) > 1:
        joined = " ".join(ids)
        joined_matches = norm_index.get(normalize_id(joined), [])
        if len(joined_matches) == 1:
            return [records[joined_matches[0]]], []

    resolved = []
    missing = []
    for raw in ids:
        if raw in records:
            resolved.append(records[raw])
            continue
        matches = norm_index.get(normalize_id(raw), [])
        if len(matches) == 1:
            resolved.append(records[matches[0]])
            continue
        suggestions = get_close_matches(normalize_id(raw), norm_index.keys(), n=8, cutoff=0.65)
        suggested_ids = [sid for n in suggestions for sid in norm_index[n]]
        missing.append({"query": raw, "suggestions": suggested_ids})
    return resolved, missing


def print_json(payload: object) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


def format_record(record: dict, kind: str) -> str:
    lines = [
        f"# {record['id']}",
        "",
        DISCLAIMER,
        "",
        f"- site: {record.get('site') or ''}",
        f"- support: {record.get('support') or ''}",
        f"- findspot: {record.get('findspot') or ''}",
        f"- context: {record.get('context') or ''}",
        f"- rights: {record.get('image_rights') or ''}",
        f"- rights_url: {record.get('image_rights_url') or ''}",
        "",
    ]
    for file in record_files(record, kind):
        lines.extend(
            [
                f"## {file['kind']}",
                "",
                f"- exists: {file['exists']}",
                f"- path: {file['absolute_path']}",
                f"- relative_path: {file['relative_path']}",
                f"- bytes: {file.get('bytes', '')}",
                f"- dimensions: {file.get('dimensions') or ''}",
                f"- sha256: {file.get('sha256') or ''}",
                "",
            ]
        )
    return "\n".join(lines).rstrip()


def open_files(files: list[dict]) -> None:
    for file in files:
        if file.get("exists"):
            subprocess.run(["open", file["absolute_path"]], check=False)


def copy_files(records: list[dict], kind: str, out_dir: Path) -> list[dict]:
    out_dir.mkdir(parents=True, exist_ok=True)
    copied = []
    for record in records:
        for file in record_files(record, kind):
            if not file.get("exists"):
                continue
            src = Path(file["absolute_path"])
            dst = out_dir / f"{safe_file_stem(record['id'])}-{file['kind']}{src.suffix.lower()}"
            shutil.copy2(src, dst)
            copied.append({"inscription_id": record["id"], "kind": file["kind"], "source": str(src), "dest": str(dst)})
    return copied


def write_contact_sheet(records: list[dict], kind: str, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sections = [
        "<!doctype html><meta charset='utf-8'><title>Linear A Image Contact Sheet</title>",
        "<style>body{font-family:serif;margin:24px;} img{max-width:520px;max-height:520px;border:1px solid #ccc;} .card{margin:0 0 32px 0;page-break-inside:avoid;} code{font-size:12px;}</style>",
        f"<h1>Linear A Image Contact Sheet</h1><p>{DISCLAIMER}</p>",
    ]
    for record in records:
        for file in record_files(record, kind):
            sections.append("<div class='card'>")
            sections.append(f"<h2>{record['id']} - {file['kind']}</h2>")
            sections.append(f"<p>{record.get('site') or ''} | {record.get('support') or ''} | {record.get('context') or ''}</p>")
            if file.get("exists"):
                sections.append(f"<img src='file://{file['absolute_path']}' alt='{record['id']} {file['kind']}'>")
            else:
                sections.append("<p><strong>Missing file</strong></p>")
            sections.append(f"<p><code>{file['absolute_path']}</code></p>")
            sections.append("</div>")
    out_path.write_text("\n".join(sections), encoding="utf-8")
    return out_path


def cmd_status(args: argparse.Namespace) -> None:
    manifest = load_manifest(rebuild=args.rebuild)
    payload = {
        "manifest_path": str(MANIFEST_PATH),
        "lashon_ha_kretan_dir": manifest.get("lashon_ha_kretan_dir"),
        "summary": manifest["summary"],
        "disclaimer": DISCLAIMER,
    }
    print_json(payload)


def cmd_build(args: argparse.Namespace) -> None:
    manifest = build_manifest()
    out = Path(args.out) if args.out else MANIFEST_PATH
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print_json({"written": str(out), "summary": manifest["summary"], "disclaimer": DISCLAIMER})


def cmd_audit(args: argparse.Namespace) -> None:
    manifest = load_manifest(rebuild=args.rebuild)
    if args.json:
        print_json({"summary": manifest["summary"], "disclaimer": DISCLAIMER})
        return
    s = manifest["summary"]
    print(DISCLAIMER)
    print(f"Corpus records: {s['corpus_records']}")
    print(f"Records with image/facsimile refs: {s['records_with_any_image_ref']}")
    print(f"Inscription image refs: {s['image_refs_existing']}/{s['image_refs_total']}")
    print(f"Facsimile refs: {s['facsimile_refs_existing']}/{s['facsimile_refs_total']}")
    print(f"Missing refs: {s['all_refs_missing']}")
    for row in s["missing"]:
        print(f"- {row['inscription_id']} {row['kind']}: {row['relative_path']}")


def cmd_show(args: argparse.Namespace) -> None:
    manifest = load_manifest(rebuild=args.rebuild)
    records, missing = resolve_records(manifest, args.ids)
    if args.copy_to:
        copied = copy_files(records, args.kind, Path(args.copy_to))
    else:
        copied = []
    if args.contact_sheet:
        contact_sheet = str(write_contact_sheet(records, args.kind, Path(args.contact_sheet)))
    else:
        contact_sheet = None
    if args.open:
        files = [f for r in records for f in record_files(r, args.kind)]
        open_files(files)
    if args.json:
        print_json(
            {
                "disclaimer": DISCLAIMER,
                "records": records,
                "missing_queries": missing,
                "copied": copied,
                "contact_sheet": contact_sheet,
            }
        )
        return
    if missing:
        print("Unresolved queries:")
        for item in missing:
            print(f"- {item['query']}: suggestions {', '.join(item['suggestions'])}")
        print()
    for record in records:
        print(format_record(record, args.kind))
        print()
    if copied:
        print("Copied files:")
        for row in copied:
            print(f"- {row['inscription_id']} {row['kind']}: {row['dest']}")
    if contact_sheet:
        print(f"Contact sheet: {contact_sheet}")


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] not in {"status", "audit", "build", "show", "-h", "--help"}:
        sys.argv.insert(1, "show")

    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("status", help="Show manifest summary")
    p.add_argument("--rebuild", action="store_true", help="Rebuild manifest before reporting")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("build", help="Build inscription image manifest")
    p.add_argument("--out", help=f"Output path; default {MANIFEST_PATH}")
    p.set_defaults(func=cmd_build)

    p = sub.add_parser("audit", help="Audit image/facsimile coverage")
    p.add_argument("--json", action="store_true")
    p.add_argument("--rebuild", action="store_true", help="Rebuild manifest before reporting")
    p.set_defaults(func=cmd_audit)

    p = sub.add_parser("show", help="Show image records for inscription IDs")
    p.add_argument("ids", nargs="+")
    p.add_argument("--kind", choices=["any", "image", "facsimile"], default="any")
    p.add_argument("--json", action="store_true")
    p.add_argument("--open", action="store_true", help="Open existing files in the OS image viewer")
    p.add_argument("--copy-to", help="Copy existing images/facsimiles to this directory")
    p.add_argument("--contact-sheet", help="Write an HTML contact sheet to this path")
    p.add_argument("--rebuild", action="store_true", help="Rebuild manifest before reporting")
    p.set_defaults(func=cmd_show)

    args = parser.parse_args()
    try:
        args.func(args)
    except NotInCheckout as e:
        print(f"stopped: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
