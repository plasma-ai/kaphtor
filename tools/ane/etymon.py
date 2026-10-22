#!/usr/bin/env python3
"""Etymon: a root dossier.

Given a Semitic root, gather every local attestation into one provenance-stamped evidence dossier: the
Proto-Semitic roots, the Linear A lexicon and onomasticon (through lq.py), the contact lexicons, the Quranic
Arabic roots (QAC), the Arabian epigraphy entries (OCIANA, DASI) and the Egyptian sentences (ORAEC/TLA).

The dossier gathers; it never judges. Every hit carries its source path and match mode, so adjudication stays a
human step. A source that is not in this checkout is named in its section's note, with the path looked for.

Usage:
    python3 tools/ane/etymon.py ROOT (--out DIR | --stdout) [options]

    python3 tools/ane/etymon.py š-m-ʿ --keywords hear,listen --stdout
    python3 tools/ane/etymon.py m-l-k --keywords king --out DIR
    python3 tools/ane/etymon.py b-n --fuzzy --stdout

Options:
    --keywords A,B,C   Comma-separated terms for the meaning-field search
    --fuzzy            Also run cognate_search.py --reverse (slower, wider net)
    --out DIR          Write dossier.json and dossier.md into DIR (a new DIR-2, DIR-3 … if it exists)
    --stdout           Print the JSON to stdout and write nothing

Attribution: di Mino
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import unicodedata
from datetime import UTC, datetime
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = "tools.ane"

from ..core.root_index import LEXICA
from ..paths import ANE_DATA, CONTACT_DATA, LINEAR_A_DATA, REPO, SEMITIC_ROOTS_DATA, SHARE_ALIKE
from .ane_keys import units

LQ = REPO / "tools" / "linear_a" / "lq.py"
COGNATE_SEARCH = REPO / "tools" / "linear_a" / "cognate_search.py"
QURAN_ROOTS = SHARE_ALIKE / "quran" / "quran_roots.jsonl"
EPIGRAPHY_CORPORA = [ANE_DATA / "arabian_epigraphy.jsonl",
                     ANE_DATA / "south_arabian_epigraphy.jsonl"]
EGY_SENTS = SHARE_ALIKE / "egyptian" / "egyptian_sentences.jsonl"

# The Semitic contact lexica are the root index's (tools/core/root_index.py LEXICA, read only): its files and the
# fields that carry a root or form. The competitor lexica it does not index follow.
COMPETITOR_LEXICONS = tuple((name, CONTACT_DATA / f"{name}.jsonl", ("normalized", "form_original"))
                            for name in ("egyptian_lexicon", "hurrian_lexicon", "anatolian_lexicon"))


def contact_lexicons() -> list:
    """(name, path, fields) for each contact lexicon."""
    return [(lx.name, lx.path, lx.fields) for lx in LEXICA] + list(COMPETITOR_LEXICONS)


# Conservative diacritic fold for recall on contact-lexicon transcriptions.
# Deliberately excludes q↔k and emphatic↔plain velar mergers — too loose.
# CUC normalizes with Greek letters (θ, ð) and half-ring glottals (ʾ, ʿ) — fold those too.
# Arabic additions: ḍ (ḍād) and ǧ (ǧīm — regular Semitic *g reflex) for quran_roots.jsonl.
FOLD = {"ṯ": "t", "ṭ": "t", "ḫ": "h", "ḥ": "h", "ḏ": "d", "š": "s", "ś": "s", "ṣ": "s", "ẓ": "z", "ǵ": "g", "ġ": "g",
        "θ": "t", "ð": "d", "ʾ": "ʔ", "ʿ": "ʕ", "ḍ": "d", "ǧ": "g",
        # Egyptological transliteration (TLA/ORAEC): aleph, ayin, yod. The j→y fold is global by design: j is
        # yod in Egyptian and Hurrian transcription; the few Arabic romanisations that write ǧīm as j are
        # folded too, and folded matches are labelled "folded" for the adjudicator to discount.
        "ꜣ": "ʔ", "ꜥ": "ʕ", "ꞽ": "y", "j": "y"}


def root_consonants(root: str) -> list:
    """'k-n-s', '√kns', 'K.N.S' → ['k','n','s']; 'ʔṯr' → ['ʔ','ṯ','r']. Read through ane_keys: composed, the root
    sign and star dropped, case folded, a mark kept on its letter; the signs stay as typed."""
    text = unicodedata.normalize("NFC", root).replace("√", "").replace("*", "").strip().casefold()
    return [u for u in units(text) if u not in "-. "]


def fold_char(c: str) -> str:
    return FOLD.get(c, c)


def is_subsequence(cons: list, text: str, folded: bool = False) -> bool:
    """True if cons appear in order within text, inside a bounded window.

    The window (2×root length + 1) keeps short roots from matching arbitrary
    prose — an unbounded subsequence test for m-n would hit 'monument'.
    Biconsonantal roots stay noisy even so; hits are tagged short-root
    downstream so the adjudicator discounts them.
    """
    text = unicodedata.normalize("NFC", text or "").lower()
    if any(len(c) > 1 for c in cons):  # an indexed sibilant (s1) is one letter of the text too
        text = units(text)
    if folded:
        text = [fold_char(c) for c in text]
        cons = [fold_char(c) for c in cons]
    max_span = 2 * len(cons) + 1
    for start, ch in enumerate(text):
        if ch != cons[0]:
            continue
        i, pos = 1, start
        for j in range(start + 1, min(len(text), start + max_span)):
            if i < len(cons) and text[j] == cons[i]:
                i += 1
                pos = j
        if i == len(cons) and pos - start + 1 <= max_span:
            return True
    return False


def contiguous_hit(cons: list, text: str, folded: bool = False) -> bool:
    """For consonantal text (inscriptions): the root's letters together inside one word of `text`, so a root
    never joins the ends of two words (b-n-m in "bn mnt")."""
    if folded:
        cons = [fold_char(c) for c in cons]
    skeleton = "".join(cons)
    for word in re.split(r"[\s\-]+", unicodedata.normalize("NFC", text or "").lower()):
        letters = units(word)  # s¹, s₁ and s1 read alike
        if folded:
            letters = [fold_char(c) for c in letters]
        if skeleton in "".join(letters):
            return True
    return False


def keyword_hit(text, keyword: str, prefix: bool = False) -> bool:
    """`keyword` as a whole word of `text`, an English plural allowed (king, kings — not kingdom); with
    `prefix`, as the start of a word (German compounds: König, Königssohn). Case-insensitive."""
    tail = "" if prefix else r"(?:e?s)?(?!\w)"
    return re.search(rf"(?<!\w){re.escape(keyword)}{tail}", text or "", re.IGNORECASE) is not None


def is_keyword_hit(hit: dict) -> bool:
    """A hit found by a keyword, not by the root's consonants."""
    return "keyword" in str(hit.get("match_mode", ""))


def not_in_checkout(path: Path) -> str:
    return f"not in this checkout (looked for {path})"


# The ledger: per file read, its records and undecodable lines (read_jsonl); files up to SHA_LIMIT bytes carry
# their sha256, larger ones size and mtime.
SCANNED: dict[str, dict] = {}
SHA_LIMIT = 25_000_000


def read_jsonl(path):
    """Each record of a JSONL file, its records and undecodable lines counted in SCANNED."""
    tally = SCANNED[str(path)] = {"records": 0, "decode_skips": 0}
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                tally["decode_skips"] += 1
                continue
            tally["records"] += 1
            yield entry


def ledger(sections: list) -> dict:
    """What the dossier read: each section's file (sha256, or size and mtime when large), records, decode
    skips, method and note; and the contact files no section reads."""
    sources = []
    for sec in sections:
        path = Path(sec["path"])
        entry = {"source": sec["source"], "path": sec["path"], "method": sec["method"]}
        if path.is_file():
            st = path.stat()
            entry |= {"bytes": st.st_size, "mtime": int(st.st_mtime)}
            if st.st_size <= SHA_LIMIT:
                entry["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        entry |= SCANNED.get(sec["path"], {})
        if sec.get("note"):
            entry["note"] = sec["note"]
        sources.append(entry)
    read = {str(p) for _n, p, _f in contact_lexicons()}
    unwired = sorted(p.stem for p in CONTACT_DATA.glob("*.jsonl") if str(p) not in read and ".bak" not in p.name)
    return {"sources": sources, "unwired": unwired}


def now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def section(source: str, path: str, method: str, hits: list, note: str = "") -> dict:
    sec = {"source": source, "path": path, "method": method,
           "retrieved_at": now_iso(), "count": len(hits),
           "consonant_count": sum(1 for h in hits if not is_keyword_hit(h)), "hits": hits}
    if note:
        sec["note"] = note
    return sec


def run_json(cmd: list):
    """Run a command, parse stdout as JSON; return (data, error)."""
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=180, check=False)
        if out.returncode != 0:
            return None, (out.stderr or out.stdout).strip()[:300]
        return json.loads(out.stdout), None
    except (json.JSONDecodeError, subprocess.TimeoutExpired, OSError) as e:
        return None, str(e)[:300]


def sql_like(s: str) -> str:
    """Escape for interpolation inside a LIKE pattern (pair with ESCAPE '\\')."""
    return (s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            .replace("'", "''"))


def gather_proto_semitic(cons: list, keywords: list) -> dict:
    pattern = "%" + "%".join(sql_like(c) for c in cons) + "%"
    kw_clause = ""
    if keywords:
        likes = " OR ".join(f"meaning ILIKE '%{sql_like(k)}%' ESCAPE '\\'" for k in keywords)
        kw_clause = f" OR {likes}"
    query = (f'SELECT id AS "Number", ps AS "Proto-Semitic", meaning AS "Meaning", notes AS "Notes" '
             f"FROM semitic_roots WHERE ps LIKE '{pattern}' ESCAPE '\\'{kw_clause}")
    data, err = run_json([sys.executable, str(LQ), "--json", "sql", query])
    # Each row names how it matched: the root's consonants in order, or a keyword as a whole word of its
    # Meaning; a row the SQL substring let through on neither count is dropped.
    in_order = re.compile(".*".join(re.escape(c) for c in cons))
    hits = []
    for row in data if isinstance(data, list) else []:
        if in_order.search(str(row.get("Proto-Semitic") or "")):
            hits.append({**row, "match_mode": "root"})
        elif any(keyword_hit(row.get("Meaning"), k) for k in keywords):
            hits.append({**row, "match_mode": "meaning-keyword"})
    return section("Proto-Semitic roots", str(SEMITIC_ROOTS_DATA / "semitic_roots.json"),
                   f"lq.py sql: {query}", hits, note=err or "")


def gather_linear_a(root: str, fuzzy: bool) -> list:
    sections = []
    data, err = run_json([sys.executable, str(LQ), "--json", "root", root])
    hits = data if isinstance(data, list) else []
    sections.append(section("Linear A lexicon (exact root field)",
                            str(LINEAR_A_DATA / "lexicon.json"),
                            f"lq.py root {root}", hits, note=err or ""))
    if fuzzy:
        bare = root.replace("-", "")
        data, err = run_json([sys.executable, str(COGNATE_SEARCH),
                              "--reverse", bare, "--json"])
        hits = data if isinstance(data, list) else (data.get("matches", []) if isinstance(data, dict) else [])
        sections.append(section("Linear A corpus (fuzzy reverse cognate search)",
                                str(COGNATE_SEARCH),
                                f"cognate_search.py --reverse {bare}",
                                hits, note=err or "adjudication required — fuzzy matches only"))
    return sections


def gather_onomasticon(cons: list) -> dict:
    pattern = "%" + "%".join(sql_like(c) for c in cons) + "%"
    query = (f"SELECT token, normalized, type, affiliation, reading, meaning, frequency "
             f"FROM onomasticon WHERE normalized LIKE '{pattern}' ESCAPE '\\' "
             f"OR reading LIKE '{pattern}' ESCAPE '\\'")
    data, err = run_json([sys.executable, str(LQ), "--json", "sql", query])
    hits = data if isinstance(data, list) else []
    return section("Linear A onomasticon", str(LINEAR_A_DATA / "onomasticon.json"),
                   f"lq.py sql: {query}", hits, note=err or "")


def gather_contact_lexicons(cons: list, keywords: list) -> list:
    sections = []
    for name, path, declared in contact_lexicons():
        if not path.exists():
            sections.append(section(name.replace("_", " "), str(path), "jsonl scan", [],
                                    note=not_in_checkout(path)))
            continue
        hits = []
        for entry in read_jsonl(path):
            fields = [v for f in declared for v in (entry.get(f) if isinstance(entry.get(f), list)
                                                    else [entry.get(f)]) if isinstance(v, str)]
            fields += entry.get("match_keys") or []
            mode = None
            if any(is_subsequence(cons, t) for t in fields if t):
                mode = "strict"
            elif any(is_subsequence(cons, t, folded=True) for t in fields if t):
                mode = "folded"
            elif any(keyword_hit(entry.get("meaning"), k) for k in keywords):
                mode = "meaning-keyword"
            if mode in ("strict", "folded") and len(cons) < 3:
                mode += "+short-root"  # biconsonantal matches are high-collision — discount
            if mode:
                hits.append({"match_mode": mode,
                             "form": entry.get("form_original") or entry.get("normalized"),
                             "normalized": entry.get("normalized"),
                             "meaning": entry.get("meaning"),
                             "pos": entry.get("pos"),
                             "source_refs": entry.get("source_refs")})
        sections.append(section(name.replace("_", " "), str(path),
                                f"consonant-subsequence scan of {', '.join(declared)} and match_keys "
                                "(strict, then diacritic-folded) + meaning keywords", hits))
    return sections


def _scan_jsonl(path: Path, cons: list, keywords: list, extra_fields: tuple, matcher=None) -> list:
    """Contact-lexicon-style scan of a standard-schema JSONL: consonant subsequence (or `matcher`)
    over normalized/form_original/match_keys (strict, then folded), else meaning keyword."""
    matcher = matcher or is_subsequence
    hits = []
    for entry in read_jsonl(path):
        fields = [entry.get("normalized", ""), entry.get("form_original", "")]
        fields += entry.get("match_keys") or []
        mode = None
        if any(matcher(cons, t) for t in fields if t):
            mode = "strict"
        elif any(matcher(cons, t, folded=True) for t in fields if t):
            mode = "folded"
        elif any(keyword_hit(f, k) for k in keywords for f in fields if f):
            mode = "name-keyword"
        elif any(keyword_hit(entry.get("meaning"), k) for k in keywords):
            mode = "meaning-keyword"
        if mode in ("strict", "folded") and len(cons) < 3:
            mode += "+short-root"  # biconsonantal matches are high-collision — discount
        if mode:
            hit = {"match_mode": mode,
                   "form": entry.get("form_original") or entry.get("normalized"),
                   "normalized": entry.get("normalized"),
                   "meaning": entry.get("meaning"),
                   "source_refs": entry.get("source_refs")}
            for k in extra_fields:
                if entry.get(k) not in (None, "", []):
                    hit[k] = entry[k][:8] if isinstance(entry[k], list) else entry[k]
            hits.append(hit)
    return hits


def gather_quran_roots(cons: list, keywords: list) -> dict:
    if not QURAN_ROOTS.exists():
        return section("Quranic Arabic roots (QAC)", str(QURAN_ROOTS), "jsonl scan", [],
                       note=not_in_checkout(QURAN_ROOTS))
    hits = _scan_jsonl(QURAN_ROOTS, cons, keywords, ("frequency", "ayah_refs"))
    return section("Quranic Arabic roots (QAC)", str(QURAN_ROOTS),
                   "consonant-subsequence scan (strict, then diacritic-folded) + gloss keywords",
                   hits)


def gather_arabian_epigraphy(cons: list, keywords: list) -> list:
    sections = []
    for path in EPIGRAPHY_CORPORA:
        name = ("Arabian epigraphy — OCIANA" if "south" not in path.name
                else "Arabian epigraphy — DASI (South Arabian)")
        if not path.exists():
            sections.append(section(name, str(path), "jsonl scan", [], note=not_in_checkout(path)))
            continue
        hits = _scan_jsonl(path, cons, keywords, ("language", "provenance", "query"), matcher=contiguous_hit)
        sections.append(section(name, str(path),
                                "the root's letters together within one word (strict, then diacritic-folded) "
                                "+ translation keywords", hits))
    return sections


def gather_egyptian_texts(cons: list, keywords: list, cap: int = 60) -> dict:
    """Egyptian sentence records (ORAEC/TLA): per-lemma consonant subsequence over match_keys; a sentence-level
    scan of 101k records would flood any short root."""
    if not EGY_SENTS.exists():
        return section("Egyptian texts (ORAEC/TLA)", str(EGY_SENTS), "jsonl scan", [],
                       note=not_in_checkout(EGY_SENTS))
    strict, other = [], []
    for entry in read_jsonl(EGY_SENTS):
        words = entry.get("match_keys") or []
        matched = [w for w in words if is_subsequence(cons, w)]
        mode = "strict"
        if not matched:
            matched = [w for w in words if is_subsequence(cons, w, folded=True)]
            mode = "folded"
        # The translations are German: a keyword may start a compound (König, Königssohn).
        if not matched and any(keyword_hit(entry.get("meaning"), k, prefix=True) for k in keywords):
            matched, mode = ["(translation)"], "meaning-keyword"
        if not matched:
            continue
        if mode != "meaning-keyword" and len(cons) < 3:
            mode += "+short-root"
        (strict if mode.startswith("strict") else other).append(
            {"match_mode": mode, "matched_lemmas": matched[:6],
             "oraecid": entry.get("oraecid"),
             "sentence": entry.get("sentence_index"),
             "transliteration": (entry.get("transliteration") or "")[:100],
             "meaning": (entry.get("meaning") or "")[:120]})
    # The cap keeps strict matches first, whatever the file order.
    hits, truncated = (strict + other)[:cap], max(0, len(strict) + len(other) - cap)
    note = f"capped at {cap} sentences ({truncated} further matches dropped)" if truncated else ""
    return section("Egyptian texts (ORAEC/TLA)", str(EGY_SENTS),
                   "per-lemma consonant-subsequence over Egyptological match_keys + German translation keywords",
                   hits, note=note)


def fresh_dir(base: Path) -> Path:
    """`base`, or base-2, base-3 … when it exists: a dossier never overwrites another."""
    if not base.exists():
        return base
    n = 2
    while base.with_name(f"{base.name}-{n}").exists():
        n += 1
    return base.with_name(f"{base.name}-{n}")


def render_markdown(dossier: dict) -> str:
    lines = [f"# Etymon Dossier: {dossier['root']}",
             "",
             f"Generated {dossier['generated_at']} by etymon.py — **gathered evidence only, no adjudication**.",
             ""]
    for sec in dossier["sections"]:
        lines.append(f"## {sec['source']} — {sec['count']} hit(s)")
        lines.append("")
        lines.append(f"*Source:* `{sec['path']}`  ")
        lines.append(f"*Method:* {sec['method']}  ")
        if sec.get("note"):
            lines.append(f"*Note:* {sec['note']}  ")
        lines.append("")
        for hit in sec["hits"][:40]:
            desc = " | ".join(str(v) for k, v in hit.items()
                              if v and k not in ("source_refs", "match_mode"))
            mode = f" `[{hit['match_mode']}]`" if hit.get("match_mode") else ""
            lines.append(f"- {desc}{mode}")
        if sec["count"] > 40:
            lines.append(f"- … {sec['count'] - 40} more in the JSON dossier")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Assemble a cross-corpus evidence dossier for a Semitic root")
    ap.add_argument("root", help="Semitic root, hyphenated or bare (š-m-ʿ, √mlk, bn)")
    ap.add_argument("--keywords", default="", help="Comma-separated keywords for the meaning-field search")
    ap.add_argument("--fuzzy", action="store_true", help="Also run cognate_search.py --reverse (slower)")
    where = ap.add_mutually_exclusive_group(required=True)
    where.add_argument("--out", type=Path, help="Write dossier.json and dossier.md into this directory")
    where.add_argument("--stdout", action="store_true", help="Print JSON to stdout, write nothing")
    args = ap.parse_args()

    cons = root_consonants(args.root)
    if len(cons) < 2:
        print("Error: single-consonant roots match everything — give at least two consonants.", file=sys.stderr)
        return 1
    if len(cons) < 3:
        print(f"Note: {args.root} is biconsonantal — subsequence hits are tagged "
              f"'+short-root' and need heavier discounting at adjudication.", file=sys.stderr)
    keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]

    root = "-".join(cons)          # the root as read (√kns, K.N.S → k-n-s) for the root-field lookups
    sections = [gather_proto_semitic(cons, keywords)]
    sections += gather_linear_a(root, args.fuzzy)
    sections.append(gather_onomasticon(cons))
    sections += gather_contact_lexicons(cons, keywords)
    sections.append(gather_quran_roots(cons, keywords))
    sections += gather_arabian_epigraphy(cons, keywords)
    sections.append(gather_egyptian_texts(cons, keywords))

    dossier = {
        "root": args.root,
        "root_read": root,
        "consonants": cons,
        "keywords": keywords,
        "generated_at": now_iso(),
        "generator": "etymon.py (kaphtor)",
        "discipline": "gather, never judge",
        "sections": sections,
        "ledger": ledger(sections),
    }

    if args.stdout:
        json.dump(dossier, sys.stdout, ensure_ascii=False, indent=2)
        print()
        return 0

    out_dir = fresh_dir(args.out)
    out_dir.mkdir(parents=True)
    (out_dir / "dossier.json").write_text(json.dumps(dossier, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "dossier.md").write_text(render_markdown(dossier), encoding="utf-8")

    total = sum(s["count"] for s in sections)
    by_consonants = sum(s["consonant_count"] for s in sections)
    nonempty = sum(1 for s in sections if s["count"])
    print(f"Dossier: {out_dir}")
    print(f"{total} hits across {nonempty}/{len(sections)} corpora ({by_consonants} by the root's consonants, "
          f"{total - by_consonants} by keyword):")
    for s in sections:
        print(f"  {s['count']:>4}  {s['source']}" + (f"  [{s['note']}]" if s.get("note") else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
