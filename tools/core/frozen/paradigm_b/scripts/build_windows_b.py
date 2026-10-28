#!/usr/bin/env python3
"""PROTOCOL-B phase B2: control windows (PROTOCOL-B §7, DECISIONS.md 2026-10-09 amendment).

Three steps:

  snapshot   derive lemmatized token streams from the cited editions into
             data/snapshot/b2_control_tokens.jsonl (the only step that reads
             outside the package; every source is hashed into _meta)
  build      render the streams with the frozen renderer, cut windows, write
             controls/controls_b.jsonl and controls/render_log_b.json
  selftest   the window rules on hand-built units (exit 1 on failure)

Window rules (amendment): unit = inscription, tablet, sentence or edition
line/§/verse; slot = the edition's or dictionary's lemma, never surface
similarity; window = contiguous non-overlapping units of one stream whose
recurring-lemma tokens (lemma with >= 2 distinct rendered forms; a repeated
identical form counted once per unit) number 6-12
and come from >= 2 lemmas (§7); scorable pairs (§5.1) >= 4, trailing units
dropped while > 12; folds leave-one-unit-out; at most 24 windows per source.

Run: IOZA2_PREFREEZE=1 uv run python scripts/build_windows_b.py {snapshot|build|selftest}
Attribution: di Mino.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import paths  # noqa: E402
from common import paradigm  # noqa: E402
import render_la as R  # noqa: E402

SCRIPT = "scripts/build_windows_b.py"
ATTRIBUTION = "di Mino"
REPO = paths.PKG.parent
SKILL_LA = Path("linear-a-decipherment/data")
CAMPAIGN = REPO / "artifacts/jss-rejection-research-2026-10-09"
TOKENS = "b2_control_tokens.jsonl"

MIN_FORMS, MAX_FORMS, MIN_LEMMAS = 6, 12, 2
MIN_PAIRS, MAX_PAIRS = 4, 12
MAX_WINDOWS_PER_SOURCE = 24

UG_DAMAGE = re.compile(r"[\[\]x?<>()\-]")
LB_SERIES = re.compile(r"^(PY|KN) ")  # §7 NEG series extended to every DAMOS-verified PY and KN tablet (amendment 6)


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# snapshot: lemmatized token streams
# ---------------------------------------------------------------------------

def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def tok(cls, language, source, stream, unit, surface, lemma, render_input, arm):
    return {"class": cls, "language": language, "source": source, "stream": stream, "unit": unit,
            "surface": surface, "lemma": lemma, "input": render_input, "arm": arm}


def ugaritic_tokens(tablets: list[str], cls: str, sources: dict) -> list[dict]:
    """Copenhagen Ugaritic Corpus auto_parsing 0.2.7: unit = the file's KTU line
    marker, lemma = the DULAT column; a token whose parse rows disagree on the
    lemma, or that carries damage or no DULAT lemma, is dropped."""
    out = []
    base = REPO / "sources/ugaritic/copenhagen-ugaritic-corpus/auto_parsing/0.2.7"
    for name in tablets:
        f = base / f"{name}.tsv"
        sources[str(f.relative_to(REPO))] = sha(f)
        unit, rows = None, {}
        order = []
        for line in f.read_text(encoding="utf-8").splitlines()[1:]:
            if line.startswith("# "):
                unit = line[2:].split("\t")[0].strip()
                continue
            cols = line.split("\t")
            if len(cols) < 4 or not cols[0].strip():
                continue
            key = (unit, cols[0])
            if key not in rows:
                rows[key] = {"surface": cols[1], "dulat": set(), "bad": False}
                order.append(key)
            dulat = cols[3].strip()
            if not dulat or dulat == "?" or "NOT FOUND" in (cols[6] if len(cols) > 6 else ""):
                rows[key]["bad"] = True
            rows[key]["dulat"].add(dulat)
        for key in order:
            r = rows[key]
            surf = r["surface"].replace("ˤ", "ʿ")
            if r["bad"] or len(r["dulat"]) != 1 or not surf or UG_DAMAGE.search(surf):
                continue
            out.append(tok(cls, "ugaritic", f"CUC {name}", name, key[0], surf,
                           "ug:" + next(iter(r["dulat"])), surf, "nws"))
    return out


def hebrew_tokens(book: str, cls: str, sources: dict) -> list[dict]:
    """OSHB morphhb (CC BY 4.0): unit = verse, lemma = the main Strong's lemma
    (prefixed particles before '/' stripped); the graphic word keeps its proclitics."""
    bs = _load_module("build_samples", CAMPAIGN / "method/duhoux-replication/build_samples.py")
    f = REPO / f"sources/hebrew/oshb-morphhb/{book}.xml"
    sources[str(f.relative_to(REPO))] = sha(f)
    sources["build_samples.py (hebrew_word)"] = sha(CAMPAIGN / "method/duhoux-replication/build_samples.py")
    ns = {"o": "http://www.bibletechnologies.net/2003/OSIS/namespace"}
    root = ET.parse(f).getroot()
    out = []
    for verse in root.iter("{%s}verse" % ns["o"]):
        vid = verse.get("osisID")
        chapter = ".".join(vid.split(".")[:2])
        for w in verse.iter("{%s}w" % ns["o"]):
            text = "".join(w.itertext()).replace("/", "")
            lemma = (w.get("lemma") or "").split("/")[-1].strip()
            if not text or not re.match(r"^\d", lemma):
                continue
            latin = R.dedupe_geminates(bs.hebrew_word(text))
            if not latin:
                continue
            out.append(tok(cls, "hebrew", f"OSHB {book}", chapter, vid, text, "heb:" + lemma, latin, "nws"))
    return out


def luwian_tokens(cls: str, sources: dict) -> list[dict]:
    """ACLT2 lane A1: unit = the edition's §, lemma = ACLT lemma; KARATEPE 1 uses the
    Hu. witness only (the Ho. duplicate would repeat every clause)."""
    bs = _load_module("build_samples", CAMPAIGN / "method/duhoux-replication/build_samples.py")
    out = []
    for p in sorted((CAMPAIGN / "acquisitions/A1-luwian/texts").glob("*.json")):
        sources[str(p.relative_to(REPO))] = sha(p)
        d = json.loads(p.read_text())
        for u in d["units"]:
            if d["text_id"] == "KARATEPE1" and not u["unit_id"].startswith("Hu."):
                continue
            for t in u["tokens"]:
                g = t.get("gloss") or ""
                if t.get("damaged") or not t.get("lemma") or "language=hittite" in g:
                    continue
                m = re.search(r"transcription=([^;\n]+)", g)
                if "cuneiform" in d.get("language", ""):
                    latin = bs.cuneiform_to_latin(t["form"])
                elif m:
                    latin = m.group(1).strip().lower().replace("=", "")
                else:
                    latin = None
                if not latin:
                    continue
                latin = latin.replace("š", "s").replace("h", "ḫ").replace("ḫḫ", "ḫ")
                latin = re.sub(r"[^a-zḫ]", "", latin)
                if latin:
                    out.append(tok(cls, "luwian", f"ACLT {d['text_id']}", d["text_id"],
                                   f"{d['text_id']} {u['unit_id']}", t["form"], "luw:" + t["lemma"],
                                   R.dedupe_geminates(latin), "luwian"))
    return out


def egyptian_tokens(cls: str, sources: dict) -> list[dict]:
    """ORAEC ḥtp-dj-nswt sentences (stage-3 snapshot): unit = sentence, lemma = the
    ORAEC lemma id aligned by position; a sentence whose token and lemma counts
    differ, or that carries damage marks, is skipped. One formula stream."""
    p = paths.SNAPSHOT / "egyptian_htp_dj_nswt.jsonl"
    sources[str(p.relative_to(REPO))] = sha(p)
    out = []
    for line in p.open():
        s = json.loads(line)
        words = s["normalized"].split()
        lemmas = s.get("lemma_ids") or []
        if len(words) != len(lemmas) or any(m in s["normalized"] for m in ("[", "⯑", "⸢")):
            continue
        for w, lid in zip(words, lemmas):
            cons = R.egyptian_consonant_skeleton(w)
            if cons and lid:
                out.append(tok(cls, "egyptian", "ORAEC htp-dj-nswt", "htp-dj-nswt", s["id"], w,
                               f"egy:{lid}", cons, "egyptian"))
    return out


def lb_lemma(gloss: dict) -> str | None:
    """DMic headword; a 'V. en X' cross-reference files the form under X, and the
    enclitic note '(+ -qe)' is DMic's own grouping of the host lemma."""
    dm = (gloss or {}).get("dmic") or {}
    lemma = dm.get("lemma")
    if not lemma:
        return None
    m = re.match(r"\s*V\. en \*?([a-z0-9*₂₃-]+)", dm.get("classification") or "")
    if m:
        lemma = m.group(1)
    return re.sub(r"\s*\(\+[^)]*\)", "", lemma).strip()


def lb_surface(form: str) -> str:
    return form.strip("⸤⸥'")


def lb_form_lemmas(sources: dict) -> dict[str, str]:
    """Attested form -> DMic lemma, from the translated tablets' per-token DMic glosses
    and DMic's own articles (keyed by attested form). A form given two lemmas, or an
    article whose headword carries an edition bracket, is dropped."""
    seen: dict[str, set[str]] = {}
    f = SKILL_LA / "linear_b_document_translations.json"
    sources[str(f)] = sha(f)
    d = json.loads(f.read_text())
    for r in d.get("translations", d).values():
        for ln in r.get("lines", []):
            for t in ln.get("tokens", []):
                lemma = lb_lemma(t.get("gloss"))
                if lemma:
                    seen.setdefault(lb_surface(t["normalized"]), set()).add(lemma)
    g = SKILL_LA / "linear_b_greek_glosses.json"
    sources[str(g)] = sha(g)
    for form, art in json.loads(g.read_text())["entries"].items():
        if re.search(r"[\[\]]", art["dmic_lemma"]):
            continue
        lemma = lb_lemma({"dmic": {"lemma": art["dmic_lemma"], "classification": art.get("classification")}})
        if lemma:
            seen.setdefault(form, set()).add(lemma)
    return {form: next(iter(s)) for form, s in seen.items() if len(s) == 1}


LB_VERIFIED = {"DAMOS_VERIFIED_EXACT", "DAMOS_VERIFIED_VARIANTS"}


def linear_b_tokens(cls: str, sources: dict) -> list[dict]:
    """Every DAMOS-verified PY and KN tablet, lemmatized by DMic: unit = tablet,
    stream = site + series."""
    lemmas = lb_form_lemmas(sources)
    f = SKILL_LA / "linear_b_token_occurrences.jsonl"
    sources[str(f)] = sha(f)

    def num_key(doc_id):
        return [int(x) if x.isdigit() else x for x in re.split(r"(\d+)", doc_id)]

    by_doc: dict[str, list[dict]] = {}
    with f.open() as fh:
        for line in fh:
            t = json.loads(line)
            if (LB_SERIES.match(t["document_id"]) and t["source_status"] in LB_VERIFIED
                    and t["token_type"] == "syllabic" and t["editorial_status"] == "clean"):
                by_doc.setdefault(t["document_id"], []).append(t)
    out = []
    for doc_id in sorted(by_doc, key=num_key):
        stream = " ".join(doc_id.split()[:2])
        for t in by_doc[doc_id]:
            surf = lb_surface(t["token_normalized"])
            lemma = lemmas.get(surf)
            if lemma and surf and not re.search(r"[\[\]]", surf):
                out.append(tok(cls, "mycenaean_greek", "DAMOS/DMic", stream, doc_id, surf,
                               "lb:" + lemma, surf, "linear_b_direct"))
    return out


def snapshot() -> int:
    sources: dict = {}
    toks: list[dict] = []
    toks += ugaritic_tokens(["KTU 1.119", "KTU 1.40", "KTU 1.41", "KTU 1.87", "KTU 1.14", "KTU 1.23"],
                            "H1_semitic_prayer", sources)
    toks += hebrew_tokens("Ps", "H1_semitic_prayer", sources)
    ug_prose = sorted(p.stem for p in (REPO / "sources/ugaritic/copenhagen-ugaritic-corpus/auto_parsing/0.2.7")
                      .glob("KTU [23].*.tsv"))
    ug_prose.sort(key=lambda s: [int(x) if x.isdigit() else x for x in re.split(r"[ .]", s)])
    toks += ugaritic_tokens(ug_prose, "H3_semitic_nonprayer", sources)
    toks += luwian_tokens("H2_luwian", sources)
    toks += egyptian_tokens("H2_egyptian", sources)
    toks += linear_b_tokens("NEG_linear_b", sources)
    out = paths.SNAPSHOT / TOKENS
    meta = {"_meta": {"built_by": SCRIPT + " snapshot", "built_at": datetime.now(timezone.utc).isoformat(),
                      "inputs": sources, "attribution": ATTRIBUTION}}
    with out.open("w") as fh:
        fh.write(json.dumps(meta, ensure_ascii=False) + "\n")
        for t in toks:
            fh.write(json.dumps(t, ensure_ascii=False) + "\n")
    by = {}
    for t in toks:
        by[(t["class"], t["source"].split()[0])] = by.get((t["class"], t["source"].split()[0]), 0) + 1
    for k, v in sorted(by.items()):
        print(f"  {k[0]:22s} {k[1]:8s} {v:6d} tokens")
    print(f"wrote {out.relative_to(paths.PKG)} ({len(toks)} tokens)")
    return 0


# ---------------------------------------------------------------------------
# window cutting (pure; exercised by selftest)
# ---------------------------------------------------------------------------

def once_per_unit(tokens: list[dict]) -> list[dict]:
    """Amendment (7): a repeated identical form (same lemma, same rendering) counts
    once per unit, as each family inscription carries one token per slot."""
    seen, out = set(), []
    for t in tokens:
        key = (t["lemma"], t["signs"])
        if key not in seen:
            seen.add(key)
            out.append(t)
    return out


def qualifying(units: list[dict]) -> list[dict]:
    """Tokens of lemmas with >= 2 distinct rendered forms inside these units."""
    forms: dict[str, set] = {}
    for u in units:
        for t in u["tokens"]:
            forms.setdefault(t["lemma"], set()).add(t["signs"])
    keep = {lem for lem, f in forms.items() if len(f) >= 2}
    return [t for u in units for t in u["tokens"] if t["lemma"] in keep]


def scorable_pairs(tokens: list[dict]) -> list[tuple[str, str]]:
    by: dict[str, list[str]] = {}
    for t in tokens:
        by.setdefault(t["lemma"], []).append(t["signs"])
    out = []
    for forms in by.values():
        for a, b in combinations(forms, 2):
            if paradigm.align_pair(a, b) is not None:
                out.append((a, b))
    return out


def cut_windows(units: list[dict]) -> tuple[list[dict], list[dict]]:
    """Greedy, deterministic, edition order. Returns (windows, drop log)."""
    windows, drops = [], []
    i = 0
    while i < len(units):
        best = None
        for j in range(i, len(units)):
            q = qualifying(units[i:j + 1])
            if len(q) > MAX_FORMS:
                break
            if len(q) >= MIN_FORMS and len({t["lemma"] for t in q}) >= MIN_LEMMAS:
                best = j
        if best is None:
            i += 1
            continue
        j = best
        q = qualifying(units[i:j + 1])
        pairs = scorable_pairs(q)
        while len(pairs) > MAX_PAIRS and j > i:
            j -= 1
            q = qualifying(units[i:j + 1])
            pairs = scorable_pairs(q)
        span = f"{units[i]['unit']} .. {units[j]['unit']}"
        if len(q) < MIN_FORMS or len({t["lemma"] for t in q}) < MIN_LEMMAS:
            drops.append({"span": span, "reason": f"pair trim left {len(q)} forms"})
            i += 1
            continue
        if len(pairs) < MIN_PAIRS or len(pairs) > MAX_PAIRS:
            drops.append({"span": span, "reason": f"{len(pairs)} scorable pairs"})
            i += 1
            continue
        windows.append({"units": units[i:j + 1], "forms": q, "pairs": pairs, "span": span})
        i = j + 1
    return windows, drops


# ---------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------

def render_token(t: dict, log: list) -> str | None:
    arm = t["arm"]
    if arm == "linear_b_direct":
        notes: list[str] = []
        signs = R.lb_word_to_la_signs(t["input"], notes)
        return "-".join(signs) if signs and all(signs) else None
    if t["language"] == "ugaritic":
        segs, _ = R.default_vocalize(t["input"], R.NWS_OVERRIDES)
    elif arm == "egyptian":
        segs = R.default_vocalize_egyptian(t["input"])
    else:
        segs = R.latin_to_segments(t["input"])
    if not segs:
        return None
    try:
        rendering = R.render_word(t["surface"], segs, arm, log)
    except Exception as e:  # logged per token, never silently
        log.append({"word": t["surface"], "arm": arm, "error": repr(e)})
        return None
    return "-".join(rendering.canonical) if rendering.canonical else None


def build() -> int:
    rows = paths.load_snapshot(TOKENS, strict=True)
    meta, toks = rows[0]["_meta"], rows[1:]
    render_log: list = []
    failed = 0
    failed_tokens: list[dict] = []
    streams: dict[tuple, list[dict]] = {}
    for t in toks:
        signs = render_token(t, render_log)
        if not signs:
            failed += 1
            failed_tokens.append({k: t[k] for k in ("class", "language", "unit", "surface", "lemma")})
            continue
        key = (t["class"], t["language"], t["source"], t["stream"])
        units = streams.setdefault(key, [])
        if not units or units[-1]["unit"] != t["unit"]:
            units.append({"unit": t["unit"], "tokens": []})
        units[-1]["tokens"].append({"surface": t["surface"], "lemma": t["lemma"], "signs": signs})
    for units in streams.values():
        for u in units:
            u["tokens"] = once_per_unit(u["tokens"])

    out_rows, all_drops, per_source = [], [], {}
    for (cls, lang, source, stream), units in streams.items():
        windows, drops = cut_windows(units)
        all_drops += [{"class": cls, "stream": stream, **d} for d in drops]
        for w in windows:
            src_key = (cls, lang, source.split()[0])
            if per_source.get(src_key, 0) >= MAX_WINDOWS_PER_SOURCE:
                all_drops.append({"class": cls, "stream": stream, "span": w["span"],
                                  "reason": f"source cap {MAX_WINDOWS_PER_SOURCE}"})
                continue
            per_source[src_key] = per_source.get(src_key, 0) + 1
            slots: dict[str, list[str]] = {}
            for t in w["forms"]:
                slots.setdefault(t["lemma"], []).append(t["signs"])
            keep = set(slots)
            units_out = [{"unit": u["unit"],
                          "tokens": [t for t in u["tokens"] if t["lemma"] in keep]} for u in w["units"]]
            units_out = [u for u in units_out if u["tokens"]]
            n_signs = [len(t["signs"].split("-")) for t in w["forms"]]
            out_rows.append({
                "id": f"B-{cls.split('_')[0]}-{lang}-{len([r for r in out_rows if r['language'] == lang and r['class'] == cls]) + 1:02d}",
                "class": cls, "language": lang, "source": source, "citation": f"{stream}: {w['span']}",
                "fold": "leave-one-unit-out", "units": units_out, "slots": slots,
                "n_forms": len(w["forms"]), "n_lemmas": len(slots), "n_units": len(units_out),
                "n_pairs": len(w["pairs"]), "mean_signs": round(sum(n_signs) / len(n_signs), 3)})

    out = paths.CONTROLS / "controls_b.jsonl"
    head = {"_meta": {"built_by": SCRIPT + " build", "built_at": datetime.now(timezone.utc).isoformat(),
                      "inputs": {TOKENS: paths.sha256(paths.SNAPSHOT / TOKENS)},
                      "token_sources": meta["inputs"], "attribution": ATTRIBUTION,
                      "rules": {"forms": [MIN_FORMS, MAX_FORMS], "lemmas_min": MIN_LEMMAS,
                                "pairs": [MIN_PAIRS, MAX_PAIRS], "cap_per_source": MAX_WINDOWS_PER_SOURCE}}}
    with out.open("w") as fh:
        fh.write(json.dumps(head, ensure_ascii=False) + "\n")
        for r in out_rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    (paths.CONTROLS / "render_log_b.json").write_text(json.dumps(
        {"_meta": head["_meta"], "render_failures": failed, "render_failed_tokens": failed_tokens, "drops": all_drops, "log": render_log},
        ensure_ascii=False, indent=1))
    summary: dict = {}
    for r in out_rows:
        s = summary.setdefault((r["class"], r["language"]), [0, 0, 0.0])
        s[0] += 1
        s[1] += r["n_pairs"]
        s[2] += r["mean_signs"]
    print(f"render failures: {failed}; drops logged: {len(all_drops)}")
    for (cls, lang), (n, p, ms) in sorted(summary.items()):
        print(f"  {cls:22s} {lang:16s} windows={n:3d} mean pairs={p / n:5.1f} mean signs/word={ms / n:4.2f}")
    print(f"wrote {out.relative_to(paths.PKG)} ({len(out_rows)} windows)")
    return 0


# ---------------------------------------------------------------------------
# selftest
# ---------------------------------------------------------------------------

FAILS: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  [{'OK' if ok else 'FAIL'}] {name}{('  ' + detail) if detail else ''}")
    if not ok:
        FAILS.append(name)


def U(uid: str, *toks: tuple[str, str]) -> dict:
    return {"unit": uid, "tokens": [{"surface": s, "lemma": lem, "signs": s} for lem, s in toks]}


def selftest() -> int:
    # 1. identical repeats do not make a lemma recur; distinct forms do
    q = qualifying([U("u1", ("A", "KA-TA-RA"), ("A", "KA-TA-RA"), ("B", "SA-MA-NA"), ("B", "SA-MA-NA-TI"))])
    check("identical forms alone do not qualify a lemma", {t["lemma"] for t in q} == {"B"}, str(q))
    # 2. slots come from the lemma, never from shared signs
    p = scorable_pairs([{"lemma": "A", "signs": "KA-TA-RA"}, {"lemma": "B", "signs": "KA-TA-RA-SE"}])
    check("forms of different lemmas never pair", p == [], str(p))
    # 3. a well-formed window: 6 forms, 2 lemmas, >= 4 pairs
    units = [U("u1", ("A", "KA-TA-RA"), ("B", "SA-MA-NA")),
             U("u2", ("A", "KA-TA-RA-SE"), ("B", "SA-MA-NA-TI")),
             U("u3", ("A", "TA-KA-TA-RA"), ("B", "JA-SA-MA-NA")),
             U("u4", ("C", "PI-TO-RE"))]
    w, d = cut_windows(units)
    check("window forms from recurring lemmas", len(w) == 1 and len(w[0]["forms"]) == 6,
          f"{[(x['span'], len(x['forms']), len(x['pairs'])) for x in w]}")
    check("window keeps units contiguous", w and [u["unit"] for u in w[0]["units"]][:3] == ["u1", "u2", "u3"])
    # 4. fewer than 4 scorable pairs drops the window and logs it
    weak = [U("u1", ("A", "KA-TA"), ("B", "SA-MA"), ("A", "KA-TO"), ("B", "SA-MO")),
            U("u2", ("A", "KE-TA"), ("B", "SE-MA"))]
    w2, d2 = cut_windows(weak)
    check("< 4 scorable pairs: dropped and logged", w2 == [] and any("pairs" in x["reason"] for x in d2), str(d2))
    # 5. never more than 12 forms; windows do not overlap
    many = [U(f"u{k}", ("A", f"KA-TA-RA-{s}"), ("B", f"SA-MA-NA-{s}")) for k, s in
            enumerate(["SE", "TI", "NU", "JA", "WA", "RE", "MI", "TU", "KO", "PI"])]
    w3, _ = cut_windows(many)
    seen = [u["unit"] for x in w3 for u in x["units"]]
    check("<= 12 forms per window", all(len(x["forms"]) <= MAX_FORMS for x in w3),
          str([len(x["forms"]) for x in w3]))
    check("<= 12 pairs per window", all(len(x["pairs"]) <= MAX_PAIRS for x in w3),
          str([len(x["pairs"]) for x in w3]))
    check("windows do not overlap", len(seen) == len(set(seen)), str(seen))
    # 6. a repeated identical form counts once per unit, but once in each unit
    rep = once_per_unit([{"lemma": "A", "signs": "KA-TA"}, {"lemma": "A", "signs": "KA-TA"},
                         {"lemma": "B", "signs": "KA-TA"}, {"lemma": "A", "signs": "KA-TA-SE"}])
    check("identical form counted once per unit", [(t["lemma"], t["signs"]) for t in rep] ==
          [("A", "KA-TA"), ("B", "KA-TA"), ("A", "KA-TA-SE")], str(rep))
    across = qualifying([U("u1", ("A", "KA-TA-RA")), U("u2", ("A", "KA-TA-RA")), U("u3", ("A", "KA-TA-RA-SE"))])
    check("repeats in different units still count", len(across) == 3, str(across))
    # 7. Linear B DMic grouping
    check("DMic '(+ -qe)' groups the host lemma",
          lb_lemma({"dmic": {"lemma": "e-ke (+ -qe)", "classification": ""}}) == "e-ke")
    check("DMic 'V. en X' files the form under X",
          lb_lemma({"dmic": {"lemma": "a-mi-ni-so-de", "classification": "V. en a-mi-ni-so."}}) == "a-mi-ni-so")
    print("SELFTEST", "PASS" if not FAILS else f"FAIL {FAILS}")
    return 1 if FAILS else 0


def main(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else ""
    if cmd == "snapshot":
        return snapshot()
    if cmd == "build":
        return build()
    if cmd == "selftest":
        return selftest()
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
