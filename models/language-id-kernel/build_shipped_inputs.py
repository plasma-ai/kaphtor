"""Cut the two shipped inputs of the suite from their full source files.

The kernels read one field of the LSJ lexicon and seven fields of the Linear B token list. This script writes
those fields, and nothing else, to the two files the kernels read by default:

  data/share-alike/greek/lsj_lb_keys.jsonl          every LSJ entry: id, headword, Linear B spelling
  data/share-alike/linear-b/linear_b_tokens.jsonl   every syllabic token of the Pylos and Knossos tablets

The Linear B file keeps a token's text only where the source marks it verified against DAMOS; the other rows keep
their place and their status with an empty text, so the counts the kernels report of what they leave out stay as
they were. Row order is the source's.

Usage:
  python3 build_shipped_inputs.py --lsj FULL_LSJ.jsonl --linear-b FULL_TOKENS.jsonl [--check]

--check compares what the sources give with the shipped files and writes nothing. Without it, an existing output
is never overwritten: move it aside first.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LSJ_OUT = REPO / "data/share-alike/greek/lsj_lb_keys.jsonl"
DIODORUS_OUT = REPO / "data/share-alike/greek/diodorus_1_5.jsonl"
LINEAR_B_OUT = REPO / "data/share-alike/linear-b/linear_b_tokens.jsonl"
EUPT_OUT = REPO / "data/share-alike/ugaritic/eupt_tokens.jsonl"
OSHB_OUT = REPO / "data/share-alike/hebrew/oshb_words.jsonl"
LATIN_OUT = REPO / "data/share-alike/latin/latinf_forms.jsonl"
SITES = ("PY", "KN")
VERIFIED = "DAMOS_VERIFIED"


def _rows(path: Path):
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            yield json.loads(line)


def lsj_lines(source: Path) -> list[str]:
    """One line per LSJ entry, in source order: its id, its headword and its Linear B spelling."""
    out = []
    for row in _rows(source):
        slim = {"id": row["id"], "form_original": row.get("form_original"), "lb_key": row.get("lb_key")}
        out.append(json.dumps(slim, ensure_ascii=False))
    return out


def linear_b_lines(source: Path) -> list[str]:
    """One line per syllabic token of a Pylos or Knossos tablet, in source order."""
    out = []
    for row in _rows(source):
        if row["document_id"][:2] not in SITES or row["token_type"] != "syllabic":
            continue
        status = str(row.get("source_status", ""))
        slim = {
            "document_id": row["document_id"],
            "line_id": row["line_id"],
            "token_index": row["token_index"],
            "token_type": row["token_type"],
            "editorial_status": row.get("editorial_status"),
            "source_status": status,
            "token_normalized": row["token_normalized"] if status.startswith(VERIFIED) else "",
        }
        out.append(json.dumps(slim, ensure_ascii=False))
    return out


def _sha(lines: list[str]) -> str:
    return hashlib.sha256(("\n".join(lines) + "\n").encode("utf-8")).hexdigest()


def _emit(lines: list[str], out: Path, check: bool) -> int:
    digest = _sha(lines)
    if check:
        if not out.is_file():
            print(f"missing    {out.relative_to(REPO)}")
            return 1
        shipped = hashlib.sha256(out.read_bytes()).hexdigest()
        same = shipped == digest
        print(f"{'current' if same else 'differs':10} {out.relative_to(REPO)}  {len(lines)} rows  sha256 {digest}")
        return 0 if same else 1
    if out.exists():
        print(f"{out} exists; move it aside first (this script never overwrites).", file=sys.stderr)
        return 2
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "x", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"wrote      {out.relative_to(REPO)}  {len(lines)} rows  sha256 {digest}")
    return 0


def diodorus_lines(source: Path) -> list[str]:
    """One line per Perseus TEI section of Diodorus Siculus Books 1-5: doc_id and plain Greek text."""
    out = []
    for div in ET.parse(source).getroot().iter():
        if div.tag.endswith("div") and div.get("subtype") == "section":
            base = div.get("{http://www.w3.org/XML/1998/namespace}base", "").rsplit(":", 1)[-1]
            text = " ".join("".join(div.itertext()).split())
            if text:
                out.append(json.dumps({"doc_id": f"diodorus:{base}.{div.get('n')}", "text": text}, ensure_ascii=False))
    return out


def eupt_lines(source: Path) -> list[str]:
    """One line per EUPT Ugaritic token: document, first location, and vocalized surface."""
    out = []
    for row in _rows(source):
        slim = {
            "document": row["document"],
            "locations": (row.get("locations") or [""])[:1],
            "surface": row["surface"],
        }
        out.append(json.dumps(slim, ensure_ascii=False))
    return out


def oshb_lines(source: Path) -> list[str]:
    """One line per OSHB Hebrew/Aramaic word: reference, morphology code, and pointed surface."""
    out = []
    for row in _rows(source):
        slim = {
            "reference": row["reference"],
            "morphology": row.get("morphology") or "H",
            "surface": row["surface"],
        }
        out.append(json.dumps(slim, ensure_ascii=False))
    return out


def latin_lines(source: Path) -> list[str]:
    """One line per LatInfLexi inflected form: lexeme and orthographic form."""
    out = []
    with open(source, encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            out.append(json.dumps({"lexeme": row["lexeme"], "orth_form": row["orth_form"]}, ensure_ascii=False))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--lsj", type=Path, help="the full LSJ lexicon, one JSON object per line")
    ap.add_argument("--linear-b", type=Path, help="the full Linear B token list, one JSON object per line")
    ap.add_argument("--diodorus", type=Path, help="Perseus TEI XML of Diodorus Siculus Books 1-5")
    ap.add_argument("--eupt", type=Path, help="the full EUPT Ugaritic tokens.jsonl")
    ap.add_argument("--oshb", type=Path, help="the full OSHB oshb_words.jsonl")
    ap.add_argument("--latin", type=Path, help="the full LiLa LatInfLexi-forms.csv")
    ap.add_argument("--check", action="store_true", help="compare with the shipped files; write nothing")
    args = ap.parse_args()
    if not any((args.lsj, args.linear_b, args.diodorus, args.eupt, args.oshb, args.latin)):
        ap.error("give at least one input flag")
    rc = 0
    if args.lsj:
        rc |= _emit(lsj_lines(args.lsj), LSJ_OUT, args.check)
    if args.linear_b:
        rc |= _emit(linear_b_lines(args.linear_b), LINEAR_B_OUT, args.check)
    if args.diodorus:
        rc |= _emit(diodorus_lines(args.diodorus), DIODORUS_OUT, args.check)
    if args.eupt:
        rc |= _emit(eupt_lines(args.eupt), EUPT_OUT, args.check)
    if args.oshb:
        rc |= _emit(oshb_lines(args.oshb), OSHB_OUT, args.check)
    if args.latin:
        rc |= _emit(latin_lines(args.latin), LATIN_OUT, args.check)
    return rc


if __name__ == "__main__":
    sys.exit(main())
