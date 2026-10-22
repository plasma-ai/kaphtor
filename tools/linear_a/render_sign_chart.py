#!/usr/bin/env python3
"""Render Linear A glyph charts and a sign table from data/linear-a/sign-registry.json.

For reading signs off edition photographs (GORILA, RILA-S1) by eye: OCR turns
inline Linear A glyphs into Latin look-alikes, so match the photographed sign
against these charts instead.

Assigned codepoints in the Linear A block that the registry lacks (AB164, the
vessels with no SigLA entry, A663, A664, the A711–A732 letter signs, A800–A807)
are added from the Unicode names list with status UNICODE_ONLY; the registry
itself is not changed.

Writes into --out (default: the user cache, `CACHE/linear-a/sign-charts/`):
  {ab-syllabograms,a3xx-signs,logograms-fractions}.png
  linear-a-sign-table.md

Existing outputs are copied into `--backups` (default `tools.paths.BACKUPS`) before rewrite.

  uv run --extra render tools/linear_a/render_sign_chart.py [--out DIR] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Pillow is not installed: install the render extra (uv sync --extra render)", file=sys.stderr)
    sys.exit(1)

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = "tools.linear_a"

from ..core.data_cache import sign_value_entries
from ..paths import BACKUPS, CACHE, LINEAR_A_DATA, REPO, NotInCheckout, require

SIGN_REGISTRY = LINEAR_A_DATA / "sign-registry.json"
SIGN_VALUES = LINEAR_A_DATA / "sign_values.json"
GLYPH_FONT = REPO / "assets/fonts/NotoSansLinearA-Regular.ttf"
OUT_DIR = CACHE / "linear-a" / "sign-charts"
TABLE_NAME = "linear-a-sign-table.md"
LABEL_FONTS = [
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/Library/Fonts/Arial Unicode.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]

GROUPS = [
    ("ab", "ab-syllabograms.png", "AB syllabograms (AB01–AB87)", 12),
    ("a3xx", "a3xx-signs.png", "A300-series signs (A301–A371, AB302)", 12),
    ("logo", "logograms-fractions.png",
     "Logograms, vessels, complex signs, fractions (AB100+, A400–A1001)", 14),
]
CELL_W, CELL_H, GLYPH_PX, MARGIN, TITLE_H = 118, 150, 76, 24, 56
# resolution_summary keys whose registry row carries no name: PA₃ = AB56, ZU = AB79 (GORILA).
KEY_ALIASES = {"PA₃": "AB56", "ZU": "AB79"}
LINEAR_A_BLOCK = range(0x10600, 0x10780)
# Fallback labels for the sex variants, as SigLA writes them (AB21/OVISf …); the registry rows carry the same names.
VARIANT_LABELS = {"AB21F": "OVISf", "AB21M": "OVISm", "AB22F": "CAPf", "AB22M": "CAPm", "AB23M": "BOSm"}


def read(path: Path):
    return json.loads(require(path, path.name).read_text(encoding="utf-8"))


def sign_number(ab: str) -> int:
    return int(re.match(r"A?B?(\d+)", ab).group(1))


def group_of(ab: str) -> str:
    n = sign_number(ab)
    if ab.startswith("AB") and n < 100:
        return "ab"
    if 300 <= n < 400:
        return "a3xx"
    return "logo"


def project_values(signs: list[dict]) -> tuple[dict[str, str], list[str]]:
    """Map registry ab_number -> project value from sign_values.json resolution_summary."""
    rs = read(SIGN_VALUES)["resolution_summary"]
    by_name = {}
    for s in signs:
        if s.get("name") and sign_number(s["ab_number"]) < 700:
            by_name.setdefault(s["name"].upper(), s["ab_number"])
    fraction_by_name = {s["name"].upper(): s["ab_number"] for s in signs
                        if s.get("name") and 700 <= sign_number(s["ab_number"]) < 800}
    numbers = {s["ab_number"] for s in signs}
    out, unmatched = {}, []
    entries = []
    for summary_key, kind in (("phonemic", "phonemic"), ("logograms", "logogram"), ("fractions", "fraction")):
        resolved = set(rs.get(summary_key, []))
        entries += [(e, kind, e not in resolved) for e in sign_value_entries(rs, summary_key)]
    for entry, kind, proposed in entries:
        is_fraction = kind == "fraction"
        key, _, value = entry.partition("=")
        value = value.split(" (")[0].strip()
        key = key.strip()
        ab = None
        if is_fraction:
            ab = fraction_by_name.get(key.upper())
        else:
            m = re.fullmatch(r"\*?A?(\d+)([A-Z]*)", key)
            if m:
                n, suf = int(m.group(1)), m.group(2)
                cands = ((f"AB{n:02d}", f"AB{n}", f"A{n}{suf}", f"A{n}") if suf in ("", "VAS")
                         else (f"AB{n:02d}{suf}", f"AB{n}{suf}", f"A{n}{suf}"))
                for cand in cands + (f"A{n}-VAS", f"A{n}VAS"):
                    if cand in numbers:
                        ab = cand
                        break
            else:
                ab = KEY_ALIASES.get(key) or by_name.get(key.upper())
        if ab:
            label = (f"{key} = {value}" + (" (logogram)" if kind == "logogram" else "")
                     + (" (proposed)" if proposed else ""))
            # A dual-function sign keeps both values: syllabic first, then logogram.
            out[ab] = f"{out[ab]}; {label}" if ab in out else label
        else:
            unmatched.append(entry)
    return out, unmatched


def unicode_only_signs(signs: list[dict]) -> list[dict]:
    """Registry-shaped rows for assigned Linear A codepoints the registry lacks.

    'LINEAR A SIGN AB021F' -> AB21F; 'A401-VAS' stays; 'A709-2 L2' -> A709-2, name L2."""
    have = {(s.get("unicode_codepoint") or (s.get("rendering") or {}).get("unicode") or "").upper()
            for s in signs}
    out = []
    for cp in LINEAR_A_BLOCK:
        name = unicodedata.name(chr(cp), "")
        code = f"U+{cp:04X}"
        if not name.startswith("LINEAR A SIGN ") or code in have:
            continue
        label = name.removeprefix("LINEAR A SIGN ")
        number, _, tail = label.partition(" ")
        number = re.sub(r"^(A?B?)0+(?=\d)", r"\1", number)
        out.append({
            "ab_number": number,
            "name": tail or VARIANT_LABELS.get(number) or ("VAS" if number.endswith("-VAS") else ""),
            "unicode_codepoint": code,
            "unicode_glyph": chr(cp),
            "rendering": {"unicode_name": name, "unicode_status": "UNICODE_ONLY"},
        })
    return out


def load_label_font(size: int):
    for path in LABEL_FONTS:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default(size=size)


def is_tofu(font, glyph: str, notdef_mask: bytes) -> bool:
    mask = font.getmask(glyph)
    return mask.getbbox() is None or bytes(mask) == notdef_mask


def chart_fallback(project: str) -> str:
    """Label for a sign with no conventional name: GORILA key (PA₃, ZU) or the project value, with ? when the
    value is proposed, not resolved."""
    if not project:
        return ""
    project = project.split("; ")[0]  # a dual-function sign is charted by its first (syllabic) value
    mark = "?" if project.endswith(" (proposed)") else ""
    key, _, value = project.removesuffix(" (proposed)").partition(" = ")
    if re.fullmatch(r"\*?A?\d+\w*", key):
        return value.replace(" (logogram)", "") + mark
    return key + mark


def render_chart(rows: list[dict], title: str, cols: int, glyph_font, label_font, small_font):
    n_rows = -(-len(rows) // cols)
    width = MARGIN * 2 + cols * CELL_W
    height = MARGIN * 2 + TITLE_H + n_rows * CELL_H
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    draw.text((MARGIN, MARGIN), title, fill="black", font=label_font)
    draw.text((MARGIN, MARGIN + 26), "Noto Sans Linear A · data/sign-registry.json · "
              "red = conventional label, else project value (? = proposed)", fill="#555", font=small_font)
    top = MARGIN + TITLE_H
    for i, r in enumerate(rows):
        x0 = MARGIN + (i % cols) * CELL_W
        y0 = top + (i // cols) * CELL_H
        draw.rectangle([x0, y0, x0 + CELL_W, y0 + CELL_H], outline="#bbb")
        gx = x0 + CELL_W / 2
        draw.text((gx, y0 + 52), r["glyph"], fill="black", font=glyph_font, anchor="mm")
        draw.text((gx, y0 + 104), r["number"], fill="black", font=label_font, anchor="mm")
        label = r["value"] or chart_fallback(r["project"]) or "—"
        label = label if len(label) <= 14 else label[:13] + "…"
        draw.text((gx, y0 + 128), label, fill="#a02020", font=small_font, anchor="mm")
    return img


def md_cell(s: str) -> str:
    return (s or "—").replace("|", "\\|")


def build_table(rows: list[dict], counts: dict[str, int], unmatched: list[str]) -> str:
    lines = [
        "# Linear A Sign Table",
        "",
        ("Generated by `tools/linear_a/render_sign_chart.py` from `data/linear-a/sign-registry.json`, with "
         "project values from `data/linear-a/sign_values.json` → `resolution_summary`. Do not edit by hand; "
         "rerun the script."),
        "",
        ("Use it to read signs off edition photographs (GORILA, RILA-S1). OCR turns inline Linear A "
         "glyphs into Latin look-alikes, so identify a photographed sign by eye against the charts, "
         "then take its number and value from the rows below."),
        "",
        "Charts (Noto Sans Linear A):",
        "",
    ]
    for key, fname, title, _ in GROUPS:
        lines.append(f"- [{title}]({fname})—{counts[key]} glyphs")
    lines += [
        "",
        ("Columns: **Value** is the conventional label (Unicode/GORILA; Linear B-derived for AB "
         "signs). **Project** is the project value in `resolution_summary`, where one exists, "
         "marked (proposed) when it is not resolved. "
         "**Status** is the registry's Unicode status; `IMAGE_ONLY` and `REVIEW_REQUIRED` signs "
         "have no standard codepoint and appear in no chart. `UNICODE_ONLY` rows are assigned Linear A "
         "codepoints with no registry entry, named from the Unicode names list."),
        "",
        ("AB12 (*so*) has no Linear A codepoint. Its proposed Linear A form is \\*363/\\*364 "
         "(unresolved)."),
        "",
    ]
    for key, _, title, _ in GROUPS:
        lines += [f"## {title}", "",
                  "| Sign | Value | Project | Codepoint | Glyph | Unicode name | Status |",
                  "|---|---|---|---|---|---|---|"]
        for r in rows:
            if r["group"] != key:
                continue
            lines.append("| " + " | ".join(md_cell(x) for x in (
                r["number"], r["value"], r["project"], r["codepoint"], r["glyph"],
                r["unicode_name"], r["status"])) + " |")
        lines.append("")
    if unmatched:
        lines += ["## Project values with no registry row", "",
                  "Variant or composite keys in `resolution_summary` that have no sign of their own here:", ""]
        lines += [f"- {md_cell(u)}" for u in unmatched]
        lines.append("")
    return "\n".join(lines)


def backup(path: Path, stamp: str, backups: Path) -> Path | None:
    if not path.exists():
        return None
    backups.mkdir(parents=True, exist_ok=True)
    dest = backups / f"{path.stem}-{stamp}{path.suffix}"
    shutil.copy2(path, dest)
    return dest


def main() -> int:
    """Exit 2 with the file's name when a data file is not in the checkout."""
    try:
        return _run()
    except NotInCheckout as e:
        print(f"stopped: {e}", file=sys.stderr)
        return 2


def _run() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--dry-run", action="store_true", help="report what would be written; write nothing")
    p.add_argument("--out", type=Path, default=OUT_DIR, help="folder for the charts and table (default: the cache)")
    p.add_argument("--backups", type=Path, default=BACKUPS, help="where existing outputs are copied first")
    args = p.parse_args()
    chart_dir, table_path = args.out, args.out / TABLE_NAME

    signs = read(SIGN_REGISTRY)["signs"]
    extra = unicode_only_signs(signs)
    signs = sorted(signs + extra, key=lambda s: (sign_number(s["ab_number"]), s["ab_number"]))
    project, unmatched = project_values(signs)

    glyph_font = ImageFont.truetype(str(require(GLYPH_FONT, GLYPH_FONT.name)), GLYPH_PX)
    label_font = load_label_font(18)
    small_font = load_label_font(14)
    notdef_mask = bytes(glyph_font.getmask(""))

    rows, tofu = [], []
    for s in signs:
        r = s.get("rendering", {})
        glyph = s.get("unicode_glyph") or r.get("unicode_glyph") or ""
        row = {
            "number": s["ab_number"],
            "group": group_of(s["ab_number"]),
            "value": s.get("name", ""),
            "project": project.get(s["ab_number"], ""),
            "codepoint": s.get("unicode_codepoint") or r.get("unicode") or "",
            "glyph": glyph,
            "unicode_name": r.get("unicode_name", ""),
            "status": r.get("unicode_status", ""),
        }
        if glyph and is_tofu(glyph_font, glyph, notdef_mask):
            tofu.append(s["ab_number"])
        rows.append(row)

    charts, counts = {}, {}
    for key, fname, title, cols in GROUPS:
        drawn = [r for r in rows if r["group"] == key and r["glyph"] and r["number"] not in tofu]
        counts[key] = len(drawn)
        charts[chart_dir / fname] = render_chart(
            drawn, f"Linear A—{title}", cols, glyph_font, label_font, small_font)
    table = build_table(rows, counts, unmatched)

    print(f"{len(rows) - len(extra)} registry signs + {len(extra)} Unicode-only; glyph cells: "
          + ", ".join(f"{k} {counts[k]}" for k, *_ in GROUPS))
    print(f"no glyph (table only): {sum(1 for r in rows if not r['glyph'])}")
    print(f"tofu: {tofu or 'none'}")
    print(f"project values matched {len(project)}, unmatched {len(unmatched)}: {unmatched}")
    for path, img in charts.items():
        print(f"chart {path} {img.size[0]}x{img.size[1]}")
    if args.dry_run:
        print("dry run: nothing written")
        return 0

    stamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
    chart_dir.mkdir(parents=True, exist_ok=True)
    for path, img in charts.items():
        if (b := backup(path, stamp, args.backups)):
            print(f"backup {b}")
        img.save(path, optimize=True)
    if (b := backup(table_path, stamp, args.backups)):
        print(f"backup {b}")
    table_path.write_text(table, encoding="utf-8")
    print(f"wrote {table_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
