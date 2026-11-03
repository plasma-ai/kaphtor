#!/usr/bin/env python3
"""Build sign_positions.jsonl: one row per sign position in data/linear-a/corpus.json.

The position model a visual check of an inscription compares against. It is generated, not shipped: it writes to
the user cache (tools.paths.CACHE/linear-a, or --out), never into the repository.

Key: doc/i/j. i indexes the record's transliteratedWords (the anchor tools/core/positional.py
uses); j indexes positional._bare(token).split("-"). A break segment
(`]-NE`, `WA-[`, `[…]`) keeps its slot and emits no row; *402-VS takes the index of its
number. Token class, erasure and lines come from positional; sign codes from
tools/core/sign_crosswalk.py, by glyph first (corpus `words` align with transliteratedWords).

Kinds: sign, ligature, fraction, numeral, divider, lacuna (exactly one lost sign, [?]),
break (a break of unknown length: a lone 𐝫, [, ], […] or empty token), unresolved.
Damage, primary state by precedence lost > restored > partial > dotted > none, every
state found kept in `marks` with two non-damage marks:
  lost          [?]
  restored      every letter of the sign inside editorial brackets
  partial       a ligature whose label keeps a lost component (VIR+[?])
  dotted        combining underdot (uncertain reading)
  beside_break  next to a break: a bracket in the sign's segment, a restored, lost or
                break neighbour, or a 𐝫 beside its glyph (the sign itself is intact)
  erased        inside [[ ]]
`entry_line` counts the transliteration's line entries, not the lines on the object.

SigLA (data/linear-a/sigla_db.json, documents keyed to the record by corpus_key, in the record's
join order, a fragment dropped when a join document covers it) is attached by a unit-cost
alignment (tools/core/root_match.alignment). Classes: equal, alternative (SigLA reads one of an
ambiguous row's other candidates), variant (same base sign, variant letter differs),
partial (a ligature with a lost component against its surviving part), component (one side
reads parts of a composite the other side reads whole, by the registry row's `components`),
both_lost, lacuna (one side reads what the other has lost or left unread), open (a side
unresolved or unvalued), erasure (erased against live), substitution. SigLA has no numerals or dividers, so those never align; fractions align
only for documents in which SigLA records any.

Read-only on every source. The old output is copied into --backups (default tools.paths.BACKUPS) before it is
replaced; the build refuses to drop a key (--allow-drop) or to point a surviving key at a different sign
(--allow-change). No network, no model.

    uv run tools/linear_a/build_sign_positions.py --dry-run [--report PATH]
    uv run tools/linear_a/build_sign_positions.py [--out DIR] [--report PATH]

--report writes a Markdown disagreement report to a new file (refuses an existing path);
with --dry-run it is the only thing written.

Attribution: di Mino
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = "tools.linear_a"

from ..core import positional
from ..core.root_match import alignment
from ..core.safe_write import backup_file, write_atomic
from ..core.sign_crosswalk import (
    OVERRIDES_PATH,
    UNDERDOT,
    Crosswalk,
    base_code,
    default_crosswalk,
    is_klasma,
    lashon_dir,
)
from ..paths import BACKUPS, CACHE, LINEAR_A_DATA, NotInCheckout, require

CORPUS = LINEAR_A_DATA / "corpus.json"
SIGLA_DB = LINEAR_A_DATA / "sigla_db.json"
REGISTRY = LINEAR_A_DATA / "sign-registry.json"
OUT_DIR = CACHE / "linear-a"
OUT_NAME = "sign_positions.jsonl"
INDEX_NAME = "sign_positions.index.json"

D = positional.DAMAGE
ZWJ = "‍"
SIGNLIKE = ("word", "mixed", "single_sign", "logogram", "measure", "other")
ALIGNED_KINDS = ("sign", "ligature", "fraction", "lacuna", "unresolved")
DAMAGE_ORDER = ("lost", "restored", "partial", "dotted")
BREAK_PARTS = ("", "…")
MATCH_CLASSES = ("equal", "alternative", "variant", "partial", "component", "both_lost", "lacuna", "open",
                 "erasure", "substitution")
Components = dict[str, tuple[str, ...]]        # composite code -> its parts, as the registry row states them
OPEN_PREFIXES = ("unresolved:", "sigla_unresolved:", "fraction_unvalued:")


# --- per token ------------------------------------------------------------------

def _segment_depths(text: str) -> list[list[tuple[str, int]]]:
    """Characters of each hyphen part with their bracket depth; a token that opens on "]" starts inside a break."""
    first = next((ch for ch in text if ch in "[]"), "")
    depth = 1 if first == "]" else 0
    parts: list[list[tuple[str, int]]] = [[]]
    for ch in text:
        if ch == "-":
            parts.append([])
        elif ch == "[":
            depth += 1
            parts[-1].append((ch, depth))
        elif ch == "]":
            parts[-1].append((ch, depth))
            depth = max(depth - 1, 0)
        else:
            parts[-1].append((ch, depth))
    return parts


def split_signs(token: str) -> list[dict]:
    """Signs of one token, each with j (its index in positional._bare(token).split("-")) and bracket state."""
    text = token.strip()
    if positional.is_erased(text):
        text = text[2:-2]
    bare_parts = positional._bare(text).split("-")
    depth_parts = _segment_depths(text)
    states: list[str] = []          # per part: sign | restored | lost | break | merged
    signs: list[dict] = []
    for j, (bare, chars) in enumerate(zip(bare_parts, depth_parts)):
        bare = bare.strip()
        raw = "".join(ch for ch, _ in chars)
        ellipsis = "…" in bare and bare.replace("…", "").strip() != ""
        if ellipsis:                                         # SI…, …NA: a break fused to the sign
            bare = bare.replace("…", "").strip()
        if bare in BREAK_PARTS:
            states.append("break")
            continue
        if bare == "VS" and signs and signs[-1]["j"] == j - 1 and signs[-1]["label"].startswith("*"):
            signs[-1]["label"] += "-VS"
            states.append("merged")
            continue
        letters = [(ch, d) for ch, d in chars if ch not in "[]"]
        lost = bare == "?"
        restored = not lost and bool(letters) and all(d > 0 for _, d in letters)
        signs.append({"j": j, "label": "?" if lost else bare, "lost": lost, "restored": restored,
                      "dotted": UNDERDOT in raw, "bracket": "[" in raw or "]" in raw or ellipsis,
                      "beside_break": False})
        states.append("lost" if lost else "restored" if restored else "sign")
    for sign in signs:
        if sign["lost"] or sign["restored"]:
            continue
        neighbours = [states[k] for k in (sign["j"] - 1, sign["j"] + 1) if 0 <= k < len(states)]
        sign["beside_break"] = sign["bracket"] or any(s in ("break", "lost", "restored") for s in neighbours)
    return signs


def assign_glyphs(signs: list[dict], glyph: str) -> list[dict]:
    """Glyph and break-adjacency per sign. A lost sign consumes one 𐝫; break segments consume none. If the
    walk does not come out exactly, no sign gets a glyph: a half-right alignment would mislabel signs silently."""
    chars = [ch for ch in (glyph or "") if ch != ZWJ and not ch.isspace()]
    empty = [{"glyph": None, "beside_break": False} for _ in signs]
    out = [dict(e) for e in empty]
    gi = 0
    for idx, sign in enumerate(signs):
        if sign["lost"]:
            if gi < len(chars) and chars[gi] == D:
                gi += 1
            continue
        before = False
        while gi < len(chars) and chars[gi] == D:
            before, gi = True, gi + 1
        if gi >= len(chars):
            return empty
        out[idx]["glyph"] = chars[gi]
        gi += 1
        out[idx]["beside_break"] = before or (gi < len(chars) and chars[gi] == D)
    if any(ch != D for ch in chars[gi:]):
        return empty
    return out


def _damage(marks: list[str]) -> str:
    return next((m for m in DAMAGE_ORDER if m in marks), "none")


def _resolution_fields(res) -> dict:
    fields = {"kind": res.kind, "codes": list(res.codes), "rule": res.rule}
    if res.ambiguous:
        fields["ambiguous"] = True
        fields["alternatives"] = [list(a) for a in res.alternatives]
    if res.note:
        fields["note"] = res.note
    return fields


def _numeral(value: int | None) -> dict | None:
    if value is None:
        return None
    th, rest = divmod(value, 1000)
    hu, rest = divmod(rest, 100)
    te, un = divmod(rest, 10)
    return {"value": value, "thousands": th, "hundreds": hu, "tens": te, "units": un, "strokes": th + hu + te + un}


# --- per record ------------------------------------------------------------------

def record_rows(doc: str, record: dict, cw: Crosswalk) -> list[dict]:
    tokens = [positional._text(t) for t in (record.get("transliteratedWords") or [])]
    line_of = {i: n for n, (a, b) in enumerate(positional.line_spans(tokens), 1) for i in range(a, b + 1)}
    rows: list[dict] = []
    for row in positional.classify(record):
        i, token, cls = row["i"], row["token"], row["class"]
        if cls == "line_break":
            continue
        base = {"doc": doc, "i": i, "entry_line": line_of.get(i), "token": token, "token_class": cls,
                "erased": row["erased"], "token_damaged": row["damaged"]}
        erased_mark = ["erased"] if row["erased"] else []

        if cls in SIGNLIKE:
            signs = split_signs(token)
            if not signs:
                rows.append({**base, "key": f"{doc}/{i}/0", "j": 0, "label": token, "glyph": None, "kind": "break",
                             "codes": [], "rule": "structural", "damage": "none", "marks": erased_mark})
                continue
            for sign, g in zip(signs, assign_glyphs(signs, row["glyph"])):
                marks = [m for m in ("lost", "restored", "dotted") if sign[m]]
                entry = {**base, "key": f"{doc}/{i}/{sign['j']}", "j": sign["j"], "label": sign["label"],
                         "glyph": g["glyph"]}
                if sign["lost"]:
                    entry.update(kind="lacuna", codes=[], rule="structural")
                else:
                    res = cw.resolve(sign["label"], glyph=g["glyph"])
                    entry.update(_resolution_fields(res))
                    if res.kind == "ligature" and cw.has_lost_slot(sign["label"]):
                        marks.append("partial")
                    if res.kind == "numeral":
                        num = _numeral(positional.numeral_value(g["glyph"] or sign["label"]))
                        if num:
                            entry["numeral"] = num
                if not (sign["lost"] or sign["restored"]) and (sign["beside_break"] or g["beside_break"]):
                    marks.append("beside_break")
                entry.update(damage=_damage(marks), marks=marks + erased_mark)
                rows.append(entry)
            continue

        parts = split_signs(token)
        label = parts[0]["label"] if len(parts) == 1 else positional._bare(token).strip()
        entry = {**base, "key": f"{doc}/{i}/0", "j": 0, "label": label, "glyph": row["glyph"] or None}
        restored = len(parts) == 1 and parts[0]["restored"]
        marks = ["restored"] if restored else []
        if not restored and (row["damaged"] or "[" in token or "]" in token):
            marks.append("beside_break")
        if cls == "numeral":
            entry.update(kind="numeral", codes=[], rule="structural")
            num = _numeral(positional.numeral_value(token))
            if num:
                entry["numeral"] = num
        elif cls == "fraction":
            entry.update(_resolution_fields(cw.resolve(label, glyph=row["glyph"] or None, token_class="fraction")))
            entry["kind"] = "fraction"
            value = positional.fraction_value(label)
            if value is not None:
                entry["fraction_value"] = str(value)
            entry["raw_fraction"] = row["raw_fraction"]
        elif cls in ("divider", "rule"):
            entry.update(kind="divider", codes=[], rule="structural")
        elif "?" in token:                                   # [?] standing alone: one lost sign
            entry.update(kind="lacuna", codes=[], rule="structural")
            marks = ["lost"]
        else:                                                # 𐝫, [, ], None, empty: a break of unknown length
            entry.update(kind="break", codes=[], rule="structural")
            marks = []
        entry.update(damage=_damage(marks), marks=marks + erased_mark)
        rows.append(entry)
    return rows


# --- SigLA ------------------------------------------------------------------

def _norm_id(sigla_id: str) -> str:
    return re.sub(r"\s+", "", sigla_id)


def _join_parts(key: str) -> list[str]:
    """'HTZd157+156' -> ['HTZd157', 'HTZd156']; 'KH79+89' -> ['KH79', 'KH89']."""
    parts = key.split("+")
    prefix = re.match(r"^\D*", parts[0]).group(0)
    return [parts[0]] + [prefix + p if p[:1].isdigit() else p for p in parts[1:]]


def sigla_positions(docs: list[dict], corpus_key: str, cw: Crosswalk) -> list[dict]:
    """SigLA positions of a record's documents in the record's join order, codes resolved to the registry.

    A document whose id is one part of another matched document's join is dropped (KH 79 inside KH 79+89).
    A read position whose code the crosswalk cannot resolve keeps its SigLA code under `unresolved`."""
    joins = {_norm_id(d["sigla_id"]): set(_join_parts(_norm_id(d["sigla_id"]))) for d in docs
             if "+" in d["sigla_id"]}
    kept = [d for d in docs if not any(_norm_id(d["sigla_id"]) in parts and _norm_id(d["sigla_id"]) != jid
                                       for jid, parts in joins.items())]
    order = _join_parts(corpus_key)

    def rank(d: dict) -> tuple[int, str]:
        nid = _norm_id(d["sigla_id"])
        return (order.index(nid) if nid in order else (-1 if nid == corpus_key else len(order)), d["sigla_id"])

    out = []
    for d in sorted(kept, key=rank):
        for p in d["positions"]:
            unit = {"doc": d["sigla_id"], "pos": p["position"], "code": None, "read": p.get("read"),
                    "certain": p.get("certain"), "erased": bool(p.get("erased")), "hidden": bool(p.get("hidden"))}
            if p.get("read") and p.get("signs"):
                sign = p["signs"][0]
                label = sign.get("sign_id") or sign["code"]
                res = cw.resolve(label)
                if res.codes:
                    unit["code"] = "+".join(res.codes)
                else:
                    unit["unresolved"] = label
            out.append(unit)
    return out


def match_class(a: str, b: str, distinct_letters: frozenset[str] = frozenset(),
                components: Components | None = None) -> str:
    """Class of one aligned pair. A corpus key may list an ambiguous row's candidates, primary first ('A559|A561')."""
    erased_a, erased_b = a.startswith("erased:"), b.startswith("erased:")
    a, b = a.removeprefix("erased:"), b.removeprefix("erased:")
    options = a.split("|")
    a = options[0]
    if a == b == "?":
        return "both_lost"                    # neither reads a sign, erased or not
    if erased_a != erased_b:
        return "erasure"
    if a == b:
        return "equal"
    if b in options[1:]:
        return "alternative"                  # SigLA reads one of the row's other candidates
    if a.startswith(OPEN_PREFIXES) or b.startswith(OPEN_PREFIXES):
        return "open"
    if "?" in (a, b):
        return "lacuna"
    for lig, other in ((a, b), (b, a)):
        surviving = [c for c in lig.split("+") if c != "?"]
        if "?" in lig.split("+") and surviving == other.split("+"):
            return "partial"                  # VIR+[?] against SigLA's VIR: they agree on what survives
    for whole, other in ((a, b), (b, a)):
        parts = (components or {}).get(whole)
        if parts and not collections.Counter(other.split("+")) - collections.Counter(parts):
            return "component"                # A717 DD against A703 D: one side reads parts of the other's composite
    if ("+" not in a + b and base_code(a) == base_code(b)
            and a not in distinct_letters and b not in distinct_letters):
        return "variant"
    return "substitution"


def _sub_cost(a: str, b: str, components: Components | None = None) -> float:
    cls = match_class(a, b, components=components)
    if cls == "erasure":
        # The same sign, erased in one source: pair it. A different sign: dearer than skipping the erased
        # trace (0.3) and the corpus sign (1.0), so a live sign is never forced onto someone else's erasure.
        same = a.removeprefix("erased:").split("|")[0] == b.removeprefix("erased:")
        return 0.5 if same else 1.5
    return {"equal": 0.0, "both_lost": 0.0, "alternative": 0.1, "variant": 0.25, "partial": 0.25,
            "component": 0.25, "lacuna": 0.5, "open": 0.75}.get(cls, 1.0)


def _ins_cost(b: str) -> float:
    return 0.3 if b.startswith("erased:") else 1.0


def _corpus_units(rows: list[dict], with_fractions: bool,
                  components: Components | None = None) -> list[tuple[dict, str]]:
    units: list[tuple[dict, str]] = []
    for r in rows:
        kind = r["kind"]
        if kind not in ALIGNED_KINDS or (kind == "fraction" and not with_fractions):
            continue
        prefix = "erased:" if r.get("erased") else ""
        if kind == "fraction" and components and any(c in components for c in r["codes"]):
            # SigLA writes a klasma composite part by part (JE as J, E): expand A732 to A707, A704 to meet it.
            parts = [p for c in r["codes"] for p in components.get(c, (c,))]
            units.extend((r, prefix + p) for p in parts)
            continue
        if kind == "lacuna":
            units.append((r, prefix + "?"))
        elif kind == "unresolved":
            units.append((r, f"{prefix}unresolved:{r['label']}"))
        elif not r["codes"]:
            units.append((r, f"{prefix}fraction_unvalued:{r['label']}"))
        elif len(r["codes"]) > 1 and (kind == "fraction" or all(is_klasma(c) for c in r["codes"])):
            if with_fractions:
                units.extend((r, prefix + c) for c in r["codes"])
        elif r.get("ambiguous") and all(len(alt) == 1 for alt in r.get("alternatives", [])):
            options = [r["codes"][0]] + [alt[0] for alt in r["alternatives"] if alt[0] != r["codes"][0]]
            units.append((r, prefix + "|".join(options)))
        else:
            units.append((r, prefix + "+".join(r["codes"])))
    return units


def _sigla_key(p: dict) -> str:
    prefix = "erased:" if p.get("erased") else ""
    if p.get("code"):
        return prefix + p["code"]
    if p.get("unresolved"):
        return f"{prefix}sigla_unresolved:{p['unresolved']}"
    return prefix + "?"


def attach_sigla(rows: list[dict], sigla: list[dict], distinct_letters: frozenset[str] = frozenset(),
                 components: Components | None = None) -> dict:
    """Pair corpus sign rows with SigLA positions; adds `sigla` (a list, one entry per paired unit) to paired rows."""
    with_fractions = any(p.get("code") and all(is_klasma(c) for c in p["code"].split("+")) for p in sigla)
    whole = {c for p in sigla if p.get("code") for c in p["code"].split("+")}
    units = _corpus_units(rows, with_fractions, {c: v for c, v in (components or {}).items() if c not in whole})
    a = tuple(key for _, key in units)
    b = tuple(_sigla_key(p) for p in sigla)
    stats = dict.fromkeys(MATCH_CLASSES + ("corpus_unpaired", "sigla_unpaired"), 0)
    for ia, ib in alignment(a, b, sub=lambda x, y: _sub_cost(x, y, components), ins=_ins_cost):
        if ia is None:
            stats["sigla_unpaired"] += 1
        elif ib is None:
            stats["corpus_unpaired"] += 1
        else:
            match = match_class(a[ia], b[ib], distinct_letters, components)
            pb = sigla[ib]
            pair = {k: pb.get(k) for k in ("doc", "pos", "code", "read", "certain", "erased", "hidden")}
            if pb.get("unresolved"):
                pair["unresolved"] = pb["unresolved"]
            units[ia][0].setdefault("sigla", []).append(pair | {"match": match})
            stats[match] += 1
    return stats


# --- build ------------------------------------------------------------------

def changed_keys(old: dict[str, tuple], new: dict[str, tuple]) -> list[str]:
    """Keys present in both whose (token, label) differ: the key now names a different sign."""
    return sorted(k for k in old.keys() & new.keys() if old[k] != new[k])


def _sha(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def build(corpus: dict, sigla_db: dict, cw: Crosswalk) -> tuple[list[dict], dict]:
    by_key: dict[str, list[dict]] = collections.defaultdict(list)
    docs = sigla_db.get("documents", {})
    for d in (docs.values() if isinstance(docs, dict) else docs):
        if d.get("corpus_key"):
            by_key[d["corpus_key"]].append(d)
    distinct = frozenset(code for s in positional.lettered_syllabograms() for code in cw.resolve(s).codes)
    components = {c: cw.components(c) for c in cw.codes if cw.components(c)}
    rows, per_doc = [], {}
    for doc, record in corpus.items():
        recs = record_rows(doc, record, cw)
        tw, words = record.get("transliteratedWords") or [], record.get("words") or []
        info = {"rows": len(recs), "sigla_docs": len(by_key.get(doc, [])), "align": None,
                "unaligned": len(tw) != len(words), "empty_transliteration": not tw and bool(words),
                "sigla_unresolved": []}
        if by_key.get(doc):
            sp = sigla_positions(by_key[doc], doc, cw)
            info["align"] = attach_sigla(recs, sp, distinct, components)
            info["sigla_unresolved"] = [p["unresolved"] for p in sp if p.get("unresolved")]
        per_doc[doc] = info
        rows.extend(recs)
    return rows, per_doc


def report(rows: list[dict], per_doc: dict, meta: dict) -> str:
    kinds = collections.Counter(r["kind"] for r in rows)
    damage = collections.Counter(r["damage"] for r in rows)
    marks = collections.Counter(m for r in rows for m in r.get("marks", []))
    signish = [r for r in rows if r["token_class"] in SIGNLIKE and r["kind"] not in ("lacuna", "break")]
    glyphed = sum(1 for r in signish if r["glyph"])
    unresolved = collections.Counter(r["label"] for r in rows if r["kind"] == "unresolved")
    sigla_unres = collections.Counter(c for v in per_doc.values() for c in v.get("sigla_unresolved", []))
    conflicts = [r for r in rows if "label/glyph disagree" in r.get("note", "")]
    composites = collections.Counter(f"{r['label']} → {'+'.join(r['codes'])}" for r in rows
                                     if "composite glyph against component label" in r.get("note", ""))
    stand_ins = collections.Counter(r["label"] for r in rows if "more than one sign" in r.get("note", ""))
    explained = ("label/glyph disagree", "composite glyph", "more than one sign")
    ambiguous = collections.Counter(r["label"] for r in rows if r.get("ambiguous")
                                    and not any(e in r.get("note", "") for e in explained))
    shown = ("substitution", "lacuna", "open", "erasure", "partial", "component", "variant", "alternative")
    pairs: dict[str, collections.Counter] = {m: collections.Counter() for m in shown}
    pair_ex: dict[tuple, str] = {}
    for r in rows:
        for s in r.get("sigla", []):
            if s["match"] in pairs:
                corpus_side = "?" if r["kind"] == "lacuna" else ("+".join(r["codes"]) or r["label"])
                pair = (corpus_side, s.get("code") or s.get("unresolved") or "?")
                pairs[s["match"]][pair] += 1
                pair_ex.setdefault(pair, r["key"])
    totals = collections.Counter()
    for v in per_doc.values():
        if v["align"]:
            totals.update(v["align"])
    aligned = [(d, v) for d, v in per_doc.items() if v["align"]]

    def disagreements(v: dict) -> int:
        a = v["align"]
        return sum(a[k] for k in ("substitution", "lacuna", "open", "erasure", "corpus_unpaired", "sigla_unpaired"))

    worst = sorted((dv for dv in aligned if disagreements(dv[1])), key=lambda dv: (-disagreements(dv[1]), dv[0]))[:40]
    multi = sorted(d for d, v in per_doc.items() if v["sigla_docs"] > 1)
    unaligned = sorted(d for d, v in per_doc.items() if v["unaligned"])
    src = meta["sources"]

    def short(name: str) -> str:
        return (src.get(name) or "absent")[:12]

    def pair_table(match: str, limit: int) -> list[str]:
        if not pairs[match]:
            return ["None."]
        return ["| Corpus | SigLA | Count | Example |", "|---|---|---|---|",
                *[f"| {a} | {b} | {n} | `{pair_ex[(a, b)]}` |" for (a, b), n in pairs[match].most_common(limit)]]

    def listing(counter: collections.Counter) -> str:
        return ", ".join(f"`{k}` ×{n}" for k, n in counter.most_common()) or "none"

    lines = [
        "# Sign position model: build report",
        "",
        (f"Built {meta['built']} from corpus.json `{short('corpus.json')}`, sigla_db.json `{short('sigla_db.json')}`, "
         f"sign-registry.json `{short('sign-registry.json')}`, ideograms.js `{short('ideograms.js')}`."),
        "",
        f"{len(rows)} rows over {len(per_doc)} records. Kinds: "
        + (", ".join(f"{k} {n}" for k, n in kinds.most_common()) or "none") + ".",
        "Damage: " + (", ".join(f"{k} {n}" for k, n in damage.most_common()) or "none")
        + ". Marks: " + (", ".join(f"{k} {n}" for k, n in marks.most_common()) or "none") + ".",
        (f"Glyph assigned to {glyphed} of {len(signish)} resolved sign rows "
         f"({100 * glyphed / max(len(signish), 1):.1f}%)."),
        "",
        "## Corpus against SigLA",
        "",
        f"{len(aligned)} records have SigLA documents ({len(multi)} with more than one). Aligned units: "
        + ", ".join(f"{totals[k]} {k.replace('_', ' ')}" for k in MATCH_CLASSES)
        + f"; {totals['corpus_unpaired']} corpus-only, {totals['sigla_unpaired']} SigLA-only.",
        "",
        ("Classes: alternative = SigLA reads one of an ambiguous row's other candidates; "
         "variant = same base sign, variant letter differs; partial = a ligature with a lost component "
         "against its surviving part; component = one side reads parts of a composite the other reads whole "
         "(A717 DD against A703 D); lacuna = one side reads what the other has lost or left unread; open = a side "
         "unresolved or unvalued; erasure = an erased sign against a live one."),
        "",
        "### Substitutions", "", *pair_table("substitution", 80), "",
        "### Lacunae", "", *pair_table("lacuna", 40), "",
        "### Open", "", *pair_table("open", 30), "",
        "### Erasure", "", *pair_table("erasure", 30), "",
        "### Partial", "", *pair_table("partial", 20), "",
        "### Component", "", *pair_table("component", 20), "",
        "### Alternative (SigLA reads one of an ambiguous row's other candidates)", "",
        *pair_table("alternative", 20), "",
        "### Variants", "", *pair_table("variant", 30), "",
        "### Records with the most disagreements",
        "",
        "| Record | " + " | ".join(k.replace("_", " ").capitalize() for k in MATCH_CLASSES)
        + " | Corpus-only | SigLA-only | SigLA docs |",
        "|---" * (len(MATCH_CLASSES) + 4) + "|",
        *[f"| {d} | " + " | ".join(str(v["align"][k]) for k in MATCH_CLASSES + ("corpus_unpaired", "sigla_unpaired"))
          + f" | {v['sigla_docs']} |" for d, v in worst],
        "",
        "## Label and glyph",
        "",
        "Label and glyph disagree (the row keeps the glyph's code first and the label's in `alternatives`):",
        "",
        *([f"- `{r['key']}` {r['label']} — {r['note']}" for r in conflicts] or ["None."]),
        "",
        "Composite glyph against component label (GORILA composite numbering, not a reading conflict): "
        + listing(composites) + ".",
        "",
        f"Glyph drawn for more than one sign: {listing(stand_ins)}.",
        "",
        f"Other ambiguous labels: {listing(ambiguous)}.",
        "",
        "## Open labels and records",
        "",
        f"Corpus labels unresolved (absent from sign-registry.json or unparsed): {listing(unresolved)}.",
        "",
        f"SigLA codes unresolved: {listing(sigla_unres)}.",
        "",
        "Records whose words and transliteratedWords differ in length (no glyphs assigned): "
        + (", ".join(f"`{d}`" for d in unaligned) or "none") + ".",
        "",
    ]
    return "\n".join(lines)


def _read_rows(path: Path) -> dict[str, tuple]:
    if not path.exists():
        return {}
    out = {}
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                row = json.loads(line)
                out[row["key"]] = (row.get("token"), row.get("label"))
    return out


def main(argv: list[str] | None = None) -> int:
    """Exit 2 with the file's name when an input is not in the checkout, or when the build would lose keys."""
    try:
        return _run(argv)
    except NotInCheckout as e:
        print(f"stopped: {e}", file=sys.stderr)
        return 2


def _run(argv: list[str] | None) -> int:
    ap = argparse.ArgumentParser(description="Build sign_positions.jsonl from corpus.json and sigla_db.json.")
    ap.add_argument("--dry-run", action="store_true", help="report; write no data file")
    ap.add_argument("--allow-drop", action="store_true", help="permit dropping keys the old file holds")
    ap.add_argument("--allow-change", action="store_true",
                    help="permit a surviving key's token or label to change")
    ap.add_argument("--report", type=Path, help="write a Markdown report to this new file")
    ap.add_argument("--out", type=Path, default=OUT_DIR, help="folder for the rows and index files (default: the cache)")
    ap.add_argument("--backups", type=Path, default=BACKUPS, help="where the old files are copied first")
    args = ap.parse_args(argv)
    out, index = args.out / OUT_NAME, args.out / INDEX_NAME

    if args.report and args.report.exists():
        print(f"refusing: report {args.report} exists", file=sys.stderr)
        return 2
    corpus = json.loads(require(CORPUS, "corpus.json").read_text(encoding="utf-8"))
    sigla_db = json.loads(require(SIGLA_DB, "sigla_db.json").read_text(encoding="utf-8"))
    rows, per_doc = build(corpus, sigla_db, default_crosswalk())
    lashon = lashon_dir()
    meta = {
        "description": ("One row per sign position in data/linear-a/corpus.json, keyed doc/i/j (transliteratedWords "
                        "index; index in positional._bare(token).split('-')); built by "
                        "tools/linear_a/build_sign_positions.py."),
        "built": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sources": {"corpus.json": _sha(CORPUS), "sigla_db.json": _sha(SIGLA_DB),
                    "sign-registry.json": _sha(REGISTRY), "sign_crosswalk_overrides.json": _sha(OVERRIDES_PATH),
                    "ideograms.js": _sha(lashon / "ideograms.js") if lashon else None},
        "rows": len(rows),
        "records": len(per_doc),
        "kinds": dict(collections.Counter(r["kind"] for r in rows).most_common()),
    }
    print(f"{len(rows)} rows over {len(per_doc)} records: "
          + ", ".join(f"{k} {n}" for k, n in meta["kinds"].items()))

    if args.report:
        with args.report.open("x", encoding="utf-8") as fh:
            fh.write(report(rows, per_doc, meta))
        print(f"report: {args.report}")

    old = _read_rows(out)
    new = {r["key"]: (r["token"], r["label"]) for r in rows}
    dropped = sorted(old.keys() - new.keys())
    changed = changed_keys(old, new)
    refuse = False
    if dropped and not args.allow_drop:
        print(f"refusing: {len(dropped)} keys would be dropped (e.g. {dropped[:5]}); pass --allow-drop",
              file=sys.stderr)
        refuse = True
    if changed and not args.allow_change:
        print(f"refusing: {len(changed)} keys would name a different sign (e.g. {changed[:5]}); pass --allow-change",
              file=sys.stderr)
        refuse = True
    if refuse:
        return 2
    if args.dry_run:
        print("dry run: no data file written")
        return 0
    for path in (out, index):
        if path.exists():
            print(f"backup: {backup_file(path, args.backups)}")
    target = write_atomic(out, "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    write_atomic(index, json.dumps(meta, ensure_ascii=False, indent=1) + "\n")
    print(f"wrote {target} and {index.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
