#!/usr/bin/env python3
"""Word-in-context page: a word in every inscription that carries it.

For each word, one card per inscription: the corpus text line by line as Linear A glyphs over the
transliteration, damaged signs hatched, the word lit (only its own signs, where it sits inside a longer word);
the word's Unicode and code points with a copy button; SigLA's reading of the document line by line, its drawing
with the word boxed and three signs either side numbered, and SigLA's crop of each sign; the edition photograph
and facsimile. Each card is tagged: the word itself, broken, or inside a longer word, or as the spec rules it.

The spec (JSON):

    {"title": "Nine Words in Context",
     "words": ["PU₂-RE-JA", "SU-DU", "RU-DI"],
     "ruled": {"SU-DU|HT42+59": ["unread", "unread: A622 before it, may run on to a lost line"]},
     "rulings": {"SU-DU": {"outcome": "unread", "kind": "unread", "text": "..."}}}

"ruled" sets one card's tag (kind: whole | unread | broken | inside); "rulings" records a ruling on the word.

    uv run tools/linear_a/review/word_in_context.py SPEC.json --fetch   # fetch missing SigLA drawings, then build
    uv run tools/linear_a/review/word_in_context.py SPEC.json --out DIR # build from what is held, into DIR

The page goes to CACHE/review/SPEC-stem/ (or --out), never into the repository. Read-only on the data; writes
only the page folder's index.html and images/.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    __package__ = "tools.linear_a.review"

from ...paths import REPO
from . import break_check as bc
from . import review_core as rc
from .review_core import DAMAGE, esc

HERE = Path(__file__).resolve().parent
PIECE = re.compile(r"[^\-\[\]…]+|[\-\[\]…]")
KINDS = ["whole", "unread", "broken", "inside"]

LEDE = ("Every inscription in the corpus that carries one of these words. Each card sets out the corpus text line "
        "by line in Linear A Unicode with the word lit; then SigLA's own reading of the document, its drawing with the "
        "word boxed and three signs either side numbered, and SigLA's crop of each sign; then the edition photograph "
        "and facsimile. Where the word sits inside a longer word, only its own signs are lit.")


def signs_of(tok: str) -> list[str]:
    """Sign list of a transliterated token; brackets, ellipses and lost signs (?) removed."""
    return [p for p in PIECE.findall(tok) if p not in "-[]…" and p != "?"]


def slug(w: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", w.lower().replace("₂", "2").replace("₃", "3")).strip("-")


def find(rv: rc.Review, word: str, ruled: dict) -> list[dict]:
    target = signs_of(word)
    hits = []
    for key, r in rv.corpus.items():
        tw, uw = r.get("transliteratedWords") or [], r.get("words") or []
        if len(tw) != len(uw):
            continue
        for i, tok in enumerate(tw):
            if tok == "\n":
                continue
            s = signs_of(tok)
            for j in range(len(s) - len(target) + 1):
                if s[j:j + len(target)] == target:
                    exact = len(s) == len(target)
                    kind = "whole" if tok == word else ("broken" if exact else "inside")
                    kind, label = ruled.get(f"{word}|{key}", (kind, None))
                    hits.append({"key": key, "i": i, "j": j, "n": len(target), "exact": exact, "kind": kind,
                                 "tok": tok, "label": label})
                    break
    hits.sort(key=lambda h: (KINDS.index(h["kind"]), h["key"]))
    return hits


def cell_html(tok: str, uni: str, hit: dict | None) -> str:
    """One word cell: glyphs over transliteration, the hit's signs marked."""
    s = signs_of(tok)
    real = [ch for ch in uni if ch != DAMAGE]
    aligned = bool(s) and len(real) == len(s)
    glyphs, k = [], 0
    for ch in uni:
        if ch == DAMAGE:
            glyphs.append('<span class="dmg" title="damaged or lost sign"></span>')
            continue
        on = hit and aligned and hit["j"] <= k < hit["j"] + hit["n"]
        glyphs.append(f'<span class="g{" on" if on else ""}">{esc(ch)}</span>')
        k += 1
    cls = "cell" + (" hit" if hit else "") + (" whole" if hit and not aligned else "")
    if hit and aligned:
        parts, idx = [], 0
        for p in PIECE.findall(tok):
            if p in "-[]…" or p == "?":
                parts.append(esc(p))
                continue
            parts.append(f"<b>{esc(p)}</b>" if hit["j"] <= idx < hit["j"] + hit["n"] else esc(p))
            idx += 1
        lat = "".join(parts)
    else:
        lat = esc(tok)
    sep = " sep" if uni == "𐄁" else ""
    return f'<span class="{cls}{sep}"><span class="u">{"".join(glyphs)}</span><span class="t">{lat}</span></span>'


def sigla_block(rv: rc.Review, word: str, key: str, spans: dict) -> str:
    picks = rv.find(word, key, spans.get((word, key)))
    if not picks:
        return '<div class="sg none-sg"><h4>SigLA</h4><p class="none">SigLA does not hold this document.</p></div>'
    best = picks[0]
    sid, _i, n, ln = best[:4]
    match = ("SigLA reads this stretch otherwise" if n is None else "every sign matches" if n == ln
             else f"{n} of {ln} signs match")
    url = f'https://sigla.phis.me/document/{sid.replace(" ", "%20").replace("+", "%2B")}/'
    return f'''<div class="sg">
  <div class="sgh"><h4>SigLA <a href="{esc(url)}" target="_blank" rel="noopener">{esc(sid)}</a></h4>
    <span class="pill sgw">reads <b>{esc(rc.sigla_word(rv, best))}</b></span><span class="pill{"" if n == ln else " warn"}">{esc(match)}</span></div>
  <div class="sread">{rc.sigla_reading(rv, best)}</div>
  {rc.views(rv, best, word)}
  {rc.strip(rv, best, with_gaps=False)}
  {rc.sigla_record(rv, best)}
</div>'''


def card(rv: rc.Review, word: str, hit: dict, spans: dict) -> str:
    r = rv.corpus[hit["key"]]
    tw, uw = r["transliteratedWords"], r["words"]
    lines, cur, line_no, hit_line, word_in_line = [], [], 1, None, None
    for i, (tok, uni) in enumerate(zip(tw, uw)):
        if tok == "\n":
            lines.append(cur)
            cur, line_no = [], line_no + 1
            continue
        if i == hit["i"]:
            hit_line = line_no
            word_in_line = sum(1 for c in cur if c[0][:1].isalpha() or c[0][:1] in "[]*") + 1
        cur.append((tok, uni, hit if i == hit["i"] else None))
    lines.append(cur)
    rows = "".join(f'<div class="line{" here" if n == hit_line else ""}"><span class="ln">{n}</span>'
                   f'<div class="cells">{"".join(cell_html(t, u, h) for t, u, h in ln)}</div></div>'
                   for n, ln in enumerate(lines, 1))
    sig = r.get("sigla") or {}
    meta = [x for x in (r.get("site"), r.get("support"), sig.get("period") or r.get("context"),
                        r.get("findspot"), r.get("scribe")) if x]
    hit_uni = uw[hit["i"]].replace(DAMAGE, "")
    where = (f"Line {hit_line} of {len(lines)}" if len(lines) > 1 else "Single line") + f", word {word_in_line}"
    form = esc(hit["label"]) if hit["label"] else {
        "whole": "the word itself", "broken": f"broken: {esc(hit['tok'])}",
        "inside": f"inside {esc(hit['tok'])}", "unread": "unread"}[hit["kind"]]
    cps = " ".join(f"U+{ord(ch):04X}" for ch in hit_uni)
    return f'''
<article class="card">
  <header class="ch"><h3>{esc(hit["key"])}</h3><span class="pill {hit["kind"]}">{form}</span><span class="pos">{where}</span></header>
  <p class="meta">{esc(" · ".join(meta))}</p>
  <div class="text">{rows}</div>
  <p class="cp"><span class="big">{esc(hit_uni)}</span> <code>{cps}</code>
     <button type="button" class="copy" data-copy="{esc(hit_uni)}">Copy</button></p>
  {sigla_block(rv, word, hit["key"], spans)}
  <h4 class="gh">Edition</h4>
  {rc.edition_figures(rv, hit["key"])}
</article>'''


def gloss(lex: dict, word: str, hits: list) -> str:
    e = lex.get(word)
    if e:
        return (f'<p class="gloss"><i>{esc(e.get("reading") or "")}</i> “{esc(e.get("meaning") or "")}” '
                f'<span class="tier">{esc(e.get("confidence") or "")}</span></p>')
    for lw in sorted({re.sub(r"[\[\]…]|-\[\?\]", "", h["tok"]).strip("-") for h in hits if not h["exact"]}):
        e = lex.get(lw)
        if e:
            return (f'<p class="gloss">In the lexicon as {esc(lw)}: <i>{esc(e.get("reading") or "")}</i> '
                    f'“{esc(e.get("meaning") or "")}” <span class="tier">{esc(e.get("confidence") or "")}</span></p>')
    return ""


def build(spec: dict, rv: rc.Review) -> tuple[str, list[str]]:
    ruled = {k: tuple(v) for k, v in spec.get("ruled", {}).items()}
    spans = {tuple(k.split("|")): tuple(v) for k, v in spec.get("spans", {}).items()}
    rulings = spec.get("rulings", {})
    lex = {e["word"]: e for e in rc.entries(rv.src.data / "lexicon.json") if e.get("word")}
    sections, nav, anchors, report = [], [], {}, []
    for w in spec["words"]:
        hits = find(rv, w, ruled)
        kinds = [h["kind"] for h in hits]
        uni_word = ""
        for h in hits:
            if h["exact"]:
                uni_word = rv.corpus[h["key"]]["words"][h["i"]].replace(DAMAGE, "")
                break
        if not uni_word and hits:
            h = hits[0]
            u = [c for c in rv.corpus[h["key"]]["words"][h["i"]] if c != DAMAGE]
            uni_word = "".join(u[h["j"]:h["j"] + h["n"]])
        nav.append(f'<a href="#{slug(w)}"><span class="u">{esc(uni_word)}</span>{esc(w)}</a>')
        count = f"{len(hits)} inscription{'s' if len(hits) != 1 else ''}"
        parts = [f"{kinds.count(k)} {lab}" for k, lab in (("whole", "whole"), ("unread", "unread"), ("broken", "broken"),
                                                            ("inside", "inside a longer word")) if kinds.count(k)]
        if len(parts) > 1 or kinds[:1] != ["whole"]:
            count += " (" + ", ".join(parts) + ")"
        badge, rline = rc.ruling_html(rulings.get(w))
        if w in rulings:
            anchors.setdefault(w, []).append((slug(w), w))
        sections.append(f'''
<section id="{slug(w)}" class="word">
  <div class="wh"><span class="wu">{esc(uni_word)}</span>
    <div><h2>{esc(w)}</h2><p class="count">{count} {badge}</p>{gloss(lex, w, hits)}</div></div>
  {rline}
  {"".join(card(rv, w, h, spans) for h in hits)}
</section>''')
        report.append(f"{w}: {len(hits)} inscriptions")
    shell = (HERE / "word_in_context.html").read_text(encoding="utf-8")
    page = (shell.replace("{{TITLE}}", esc(spec.get("title", "Words in Context")))
            .replace("{{LEDE}}", esc(spec.get("lede", LEDE)))
            .replace("{{RULING_CSS}}", rc.RULING_CSS)
            .replace("{{PROGRESS}}", rc.progress_html(rulings, anchors, len(spec["words"])))
            .replace("{{NAV}}", "".join(nav)).replace("{{SECTIONS}}", "".join(sections))
            .replace("{{CREDITS}}", esc(bc.CREDITS)))
    return page, report


def main(defaults: dict = bc.DEFAULTS, forbid: Path | None = REPO) -> None:
    bc.main(defaults, forbid, builder=build, doc=__doc__)


if __name__ == "__main__":
    main()
