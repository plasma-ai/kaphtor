"""Cut the shipped reference inputs of the ten-kernel suite from their full source files.

Each cut retains only the fields read by the kernels, under each source's open license:

  data/share-alike/greek/lsj_lb_keys.jsonl             LSJ headwords + Linear B keys (CC BY-SA 4.0)
  data/share-alike/greek/lsj_glosses.jsonl             LSJ Linear B keys + primary glosses (CC BY-SA 4.0)
  data/share-alike/greek/diodorus_1_5.jsonl            Perseus Diodorus Books 1-5 sections (CC BY-SA 4.0)
  data/share-alike/linear-b/linear_b_tokens.jsonl      PY/KN syllabic tokens, DAMOS-verified (CC BY-NC-SA 4.0)
  data/share-alike/ugaritic/eupt_tokens.jsonl          EUPT vocalized Ugaritic tokens (CC BY-SA 4.0)
  data/share-alike/hebrew/oshb_words.jsonl             OSHB pointed Hebrew/Aramaic words (CC BY 4.0)
  data/share-alike/latin/latinf_forms.jsonl            LiLa LatInfLexi inflected Latin forms (CC BY-SA 4.0)
  data/share-alike/anatolian/tlhdig_docs.jsonl         TLHdig 0.3 preserved docs: Hit/Luw/Hur/Hat/Bo-Akk (CC BY 4.0)
  data/share-alike/cuneiform/oracc_akkadian.jsonl      ORACC Old/Standard Babylonian CC0 docs (CC0 1.0)
  data/share-alike/cuneiform/oracc_sumerian.jsonl      ORACC ePSD2/ETCSRI Sumerian CC0 docs (CC0 1.0)
  data/share-alike/cuneiform/sumerian_epsd2_lexicon.jsonl  Clean vocalized Sumerian ePSD2 glossed lemmas (CC0 1.0)

--check compares what the sources give with the shipped files and writes nothing. Without it, an existing output
is never overwritten: move it aside first.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LSJ_OUT = REPO / "data/share-alike/greek/lsj_lb_keys.jsonl"
LSJ_GLOSS_OUT = REPO / "data/share-alike/greek/lsj_glosses.jsonl"
DIODORUS_OUT = REPO / "data/share-alike/greek/diodorus_1_5.jsonl"
LINEAR_B_OUT = REPO / "data/share-alike/linear-b/linear_b_tokens.jsonl"
EUPT_OUT = REPO / "data/share-alike/ugaritic/eupt_tokens.jsonl"
OSHB_OUT = REPO / "data/share-alike/hebrew/oshb_words.jsonl"
LATIN_OUT = REPO / "data/share-alike/latin/latinf_forms.jsonl"
TLHDIG_OUT = REPO / "data/share-alike/anatolian/tlhdig_docs.jsonl"
ORACC_AKK_OUT = REPO / "data/share-alike/cuneiform/oracc_akkadian.jsonl"
ORACC_SUX_OUT = REPO / "data/share-alike/cuneiform/oracc_sumerian.jsonl"
EPSD2_LEX_OUT = REPO / "data/share-alike/cuneiform/sumerian_epsd2_lexicon.jsonl"
TLH_CODES = ("Akk", "Hit", "Hur", "Hat", "Hattian", "Luw")
AKK_CODES = ("akk-x-oldbab", "akk-x-stdbab")
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


def lsj_gloss_lines(source: Path) -> list[str]:
    """One line per glossed LSJ entry: lb_key and primary English meaning (<=120 chars)."""
    out = []
    for row in _rows(source):
        lb_key = row.get("lb_key")
        meaning = str(row.get("meaning") or "")[:120]
        if lb_key and meaning:
            out.append(json.dumps({"lb_key": lb_key, "meaning": meaning}, ensure_ascii=False))
    return out


def tlhdig_lines(source: Path) -> list[str]:
    """Grouped per (document_id, language) preserved transcriptions for Hittite/Luwian/Hurrian/Hattic/Bo-Akk."""
    grouped: dict[tuple[str, str], list[str]] = {}
    for row in _rows(source):
        lang = row.get("language")
        if lang in TLH_CODES and row.get("preserved") and row.get("trans"):
            grouped.setdefault((row["document_id"], lang), []).append(row["trans"])
    return [
        json.dumps({"document_id": doc_id, "language": lang, "words": words}, ensure_ascii=False)
        for (doc_id, lang), words in grouped.items()
    ]


def oracc_lines(source: Path, codes: tuple[str, ...]) -> list[str]:
    """Clean normalized tokens per CC0 ORACC document for the requested language codes."""
    out = []
    for row in _rows(source):
        if "CC0" not in str(row.get("license") or ""):
            continue
        toks = [
            {"lang": t["lang"], "norm": t["norm"]}
            for t in (row.get("tokens") or [])
            if t.get("lang") in codes and not t.get("damaged") and t.get("norm")
        ]
        if toks:
            out.append(json.dumps({"canonical_id": str(row["canonical_id"]), "tokens": toks}, ensure_ascii=False))
    return out


_SUX_FORM_OK = re.compile(r"[a-zšḫŋĝṭṣʾʿāēīōūâêîôû\- ]+")
_SUX_GLOSS_SKIP = frozenset({"0", "00", "1", "unmng", "x", "X", "n"})


def epsd2_lexicon_lines(source: Path) -> list[str]:
    """Unique clean vocalized Sumerian ePSD2 lemmas extracted from CC0 ORACC Sumerian documents."""
    lex: dict[str, str] = {}
    for row in _rows(source):
        if "CC0" not in str(row.get("license") or ""):
            continue
        for t in row.get("tokens") or []:
            if t.get("lang") != "sux" or t.get("damaged"):
                continue
            cf = str(t.get("cf") or "").strip()
            gw = str(t.get("gw") or t.get("sense") or "").strip()
            if not cf or not gw or gw in _SUX_GLOSS_SKIP:
                continue
            if not re.search(r"[a-zA-Z]{2,}", gw) or not _SUX_FORM_OK.fullmatch(cf):
                continue
            if cf not in lex:
                lex[cf] = gw
    return [
        json.dumps({"normalized": cf, "meaning": gw}, ensure_ascii=False)
        for cf, gw in sorted(lex.items())
    ]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--lsj", type=Path, help="the full LSJ lexicon, one JSON object per line")
    ap.add_argument("--lsj-glosses", type=Path, help="cut slim LSJ glosses for Kernel J from the full LSJ lexicon")
    ap.add_argument("--linear-b", type=Path, help="the full Linear B token list, one JSON object per line")
    ap.add_argument("--diodorus", type=Path, help="Perseus TEI XML of Diodorus Siculus Books 1-5")
    ap.add_argument("--eupt", type=Path, help="the full EUPT Ugaritic tokens.jsonl")
    ap.add_argument("--oshb", type=Path, help="the full OSHB oshb_words.jsonl")
    ap.add_argument("--latin", type=Path, help="the full LiLa LatInfLexi-forms.csv")
    ap.add_argument("--tlhdig", type=Path, help="the full TLHdig words.jsonl (CC BY 4.0)")
    ap.add_argument("--oracc-akk", type=Path, help="the full ORACC oracc_documents.jsonl (CC0 Akkadian)")
    ap.add_argument("--oracc-sux", type=Path, help="the full ORACC Sumerian ePSD2/ETCSRI supplement (CC0)")
    ap.add_argument("--check", action="store_true", help="compare with the shipped files; write nothing")
    args = ap.parse_args()
    if not any((args.lsj, args.lsj_glosses, args.linear_b, args.diodorus, args.eupt, args.oshb, args.latin, args.tlhdig, args.oracc_akk, args.oracc_sux)):
        ap.error("give at least one input flag")
    rc = 0
    if args.lsj:
        rc |= _emit(lsj_lines(args.lsj), LSJ_OUT, args.check)
    if args.lsj_glosses:
        rc |= _emit(lsj_gloss_lines(args.lsj_glosses), LSJ_GLOSS_OUT, args.check)
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
    if args.tlhdig:
        rc |= _emit(tlhdig_lines(args.tlhdig), TLHDIG_OUT, args.check)
    if args.oracc_akk:
        rc |= _emit(oracc_lines(args.oracc_akk, AKK_CODES), ORACC_AKK_OUT, args.check)
    if args.oracc_sux:
        rc |= _emit(oracc_lines(args.oracc_sux, ("sux",)), ORACC_SUX_OUT, args.check)
        rc |= _emit(epsd2_lexicon_lines(args.oracc_sux), EPSD2_LEX_OUT, args.check)
    return rc


if __name__ == "__main__":
    sys.exit(main())
