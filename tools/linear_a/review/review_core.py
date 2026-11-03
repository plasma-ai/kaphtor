"""Shared readers and card parts for the human-review pages: break check and word in context.

A review page puts one question about one word in front of a person, with every witness needed to answer it:
SigLA's drawing with the word boxed, SigLA's own reading and sign crops, the corpus text, and the edition's
photograph and facsimile. This module finds the word on SigLA's drawing and renders those parts. The two page
builders (break_check.py, word_in_context.py) add their own layout.

Read-only on the data. Writes only under the page's output folder: images/sigla (SigLA's whole-document drawings,
copied from a held folder or fetched at one request a second), images/crops and images/edition.
"""
from __future__ import annotations

import html
import importlib.util
import json
import re
import shutil
import statistics
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

esc = html.escape
UA = "ANE-Research-Script/1.0 (review-pages)"   # names the project only, no contact details
CONTEXT = 3                                      # signs shown either side of the word
DAMAGE = "\U0001076b"                            # the corpus's damaged-sign mark
ALIASES = {"PA₃": "AB56", "ZU": "AB79"}          # values the record writes for signs SigLA leaves without one


@dataclass
class Sources:
    """Where a page reads from. Only `data`, `builder`, `database_js` and `sign_map` are required."""
    data: Path                       # corpus.json, lexicon.json, unread_words.json, sigla_db.json
    builder: Path                    # build_sigla_db.py, whose Reader decodes database.js
    database_js: Path                # SigLA's database.js (image geometry lives only here)
    sign_map: Path                   # sigla-sign-map.json: ab_number -> unicode_glyph
    edition_images: Path | None = None   # root of the corpus records' `images` / `facsimileImages` paths
    crops: Path | None = None            # {crops}/{SigLA id}/{SigLA id}_{position}.png
    sigla_images: Path | None = None     # SigLA drawings already held: {dir}/{SigLA id}.png


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def entries(path: Path) -> list:
    """The record list of a data file: the file itself if a list, else its first list value."""
    x = json.loads(path.read_text(encoding="utf-8"))
    return x if isinstance(x, list) else next(v for v in x.values() if isinstance(v, list))


# --- matching a record form to SigLA's positions ------------------------------------------------------------

def undot(s: str) -> str:
    return unicodedata.normalize("NFC", "".join(c for c in unicodedata.normalize("NFD", s) if c != "̣"))


def tokens(word: str) -> list[str]:
    """A record form ('A-MA-RA-NẸ-[', ']-KU-MA-RO', 'WI-PI-[…]') -> its sign tokens, '?' for an unread sign."""
    w = undot(word).replace("[?]", "?").replace("[…]", "").replace("…", "")
    w = re.sub(r"[\[\]〚〛]", "", w).strip("- ")
    return [t for t in w.split("-") if t]


def token_matches(tok: str, p: dict) -> bool:
    if tok == "?":
        return not p["read"]
    if not p["read"]:
        return False
    s = p["signs"][0]
    if tok.upper() in ALIASES and s["code"] == ALIASES[tok.upper()]:
        return True
    if tok.startswith("*"):
        t = tok[1:].upper()
        return s["sign_id"] in (f"AB{t}", f"A{t}") or s["code"] in (f"AB{t}", f"A{t}")
    return bool(s["phon"]) and s["phon"].upper() == tok.upper()


def locate(toks: list[str], positions: list) -> tuple[int, int, int]:
    """(start index, matched signs, positions covered) of the best window for the signs. A window may run off
    either end of the document (a face holding part of a word); among equal matches the fuller window wins."""
    L = len(toks)
    best = (0, -1, 0)
    for i in range(-(L - 1), max(1, len(positions))):
        js = [j for j in range(L) if 0 <= i + j < len(positions)]
        n = sum(token_matches(toks[j], positions[i + j]) for j in js)
        if n > best[1] or (n == best[1] and len(js) > best[2]):
            best = (max(i, 0), n, len(js))
    return best


def lines_of(positions: list, rects: dict) -> list[list[int]]:
    """Group positions into lines: a new line where the centre drops by over half a sign height and x goes back."""
    hs = [rects[p["position"]][3] for p in positions if p["position"] in rects]
    mh = statistics.median(hs) if hs else 1
    lines, cur, prev = [], [], None
    for p in positions:
        r = rects.get(p["position"])
        if r is None:
            cur.append(p["position"])
            continue
        if prev is not None:
            dy = (r[1] + r[3] / 2) - (prev[1] + prev[3] / 2)
            if dy > 0.5 * mh and r[0] < prev[0]:
                lines.append(cur)
                cur = []
        cur.append(p["position"])
        prev = r
    if cur:
        lines.append(cur)
    return lines


def gap(a, c, mw, line_of) -> str:
    """The space between two positions, in median sign widths, or the line break between them."""
    if a is None or c is None:
        return "edge of the record"
    if line_of.get(a[0]) != line_of.get(c[0]):
        return "line break"
    ra, rc = a[1], c[1]
    if ra is None or rc is None:
        return "no box"
    return f"{(rc[0] - (ra[0] + ra[2])) / mw:+.2f} sign widths"


# --- the page's sources -----------------------------------------------------------------------------------

class Review:
    """Everything a page reads, loaded once."""

    def __init__(self, src: Sources, out: Path, fetch: bool = False):
        self.src, self.out, self.fetch_ok = src, out, fetch
        self.b = load_module(src.builder, "sigla_builder")
        self.db = json.loads((src.data / "sigla_db.json").read_text(encoding="utf-8"))["documents"]
        self.corpus = json.loads((src.data / "corpus.json").read_text(encoding="utf-8"))
        self.geo = self._geometry()
        m = json.loads(src.sign_map.read_text(encoding="utf-8"))
        signs = m["signs"] if isinstance(m["signs"], list) else list(m["signs"].values())
        self.gl = {s["ab_number"]: s.get("unicode_glyph") for s in signs if s.get("ab_number")}
        self.by_key: dict[str, list[str]] = {}
        for sid, d in self.db.items():
            if d["corpus_key"]:
                self.by_key.setdefault(d["corpus_key"], []).append(sid)

    def _geometry(self) -> dict:
        """SigLA id -> {"size": [w, h], "rects": {position: [x, y, w, h]}}, decoded from database.js."""
        b = self.b
        r = b.Reader(b.blob(self.src.database_js.read_text(encoding="utf-8"), "data"))
        v = r.read()
        r.finish()
        raw: dict = {}
        b._walk(v[0], raw)
        out = {}
        for doc, val in raw.items():
            rec = val[0]
            size = rec[3] if isinstance(rec[3], list) and len(rec[3]) == 2 else None
            out[doc] = {"size": size, "rects": {o[2]: o[7] for o in rec[4] if isinstance(o[7], list) and len(o[7]) == 4}}
        return out

    def label(self, p: dict) -> str:
        return self.b._label(p)

    def glyph(self, s: dict | None) -> str | None:
        return (self.gl.get(s["sign_id"]) or self.gl.get(s["code"])) if s else None

    # files the page shows, copied under out/images so the folder stands alone
    def rel(self, p: Path) -> str:
        return urllib.parse.quote(str(p.relative_to(self.out)))

    def drawing(self, sid: str) -> Path | None:
        dst = self.out / "images" / "sigla" / f"{sid}.png"
        if dst.exists() and dst.stat().st_size:
            return dst
        dst.parent.mkdir(parents=True, exist_ok=True)
        held = self.src.sigla_images / f"{sid}.png" if self.src.sigla_images else None
        if held and held.exists():
            shutil.copy2(held, dst)
            return dst
        if not self.fetch_ok:
            return None
        url = f"https://sigla.phis.me/document/{urllib.parse.quote(sid)}/{urllib.parse.quote(sid)}.png"
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=30) as resp:
                data = resp.read()
        except Exception as e:  # noqa: BLE001 - report and carry on; the card marks the drawing missing
            print(f"  {sid}: {e}", file=sys.stderr)
            return None
        dst.write_bytes(data)
        time.sleep(1.0)
        return dst

    def crop(self, sid: str, pos: int) -> Path | None:
        if not self.src.crops:
            return None
        src = self.src.crops / sid / f"{sid}_{pos}.png"
        if not src.exists():
            return None
        dst = self.out / "images" / "crops" / f"{sid}_{pos}.png"
        if not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        return dst

    def edition_images(self, key: str) -> list[tuple[str, Path]]:
        """(Photograph | Facsimile, local copy) for the corpus record's edition images that are held."""
        r = self.corpus.get(key) or {}
        out = []
        for f in (r.get("images") or []) + (r.get("facsimileImages") or []):
            src = self.src.edition_images / f if self.src.edition_images else None
            if not src or not src.exists():
                continue
            dst = self.out / "images" / "edition" / Path(f).name
            if not dst.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
            out.append(("Facsimile" if "Facsimile" in f else "Photograph", dst))
        return out

    def find(self, form: str, key: str, span: tuple[int, int] | None = None) -> list[tuple]:
        """The SigLA faces filed under the corpus key that hold the form: (SigLA id, start index, matched signs,
        positions covered[, signs in the word when the face holds only part of it]). `span` (first, last SigLA
        position) boxes a stretch SigLA reads otherwise than the record does."""
        toks = tokens(form)
        found = sorted(((sid, *locate(toks, self.db[sid]["positions"])) for sid in self.by_key.get(key, [])),
                       key=lambda f: (-f[2], -f[3]))
        if not found:
            return []
        if span:
            idx = [p["position"] for p in self.db[found[0][0]]["positions"]]
            return [(found[0][0], idx.index(span[0]), None, idx.index(span[1]) - idx.index(span[0]) + 1)]
        if found[0][2] == len(toks) or len(found) == 1:
            return [found[0]]
        # no one face holds the word (KH Wa: *86 on α, RO on γ): every face holding part of it, its own signs only
        out = []
        for sid, i, n, ln in (f for f in found if f[2] > 0):
            pos = self.db[sid]["positions"]
            hit = [j for j in range(len(pos)) if any(token_matches(t, pos[j]) for t in toks)]
            out.append((sid, hit[0], n, hit[-1] - hit[0] + 1, len(toks)) if hit else (sid, i, n, ln))
        return out or [found[0]]


# --- card parts -------------------------------------------------------------------------------------------

def word_positions(rv: Review, best: tuple) -> list[int]:
    sid, i, _n, ln = best[:4]
    return [p["position"] for p in rv.db[sid]["positions"][i:i + ln]]


def views(rv: Review, best: tuple, word: str) -> str:
    """SigLA's drawing twice: zoomed on the word and three signs either side (numbered), and whole."""
    sid, i, _n, ln = best[:4]
    pos, g = rv.db[sid]["positions"], rv.geo.get(sid, {"size": None, "rects": {}})
    rects, word_ps = g["rects"], word_positions(rv, best)
    ctx = pos[max(0, i - CONTEXT):min(len(pos), i + ln + CONTEXT)]
    img = rv.drawing(sid)
    if not (img and g["size"]):
        return '<p class="muted">SigLA drawing not held (build with --fetch).</p>'
    W, H = g["size"]
    src = rv.rel(img)
    boxes = []
    for p in ctx:
        r = rects.get(p["position"])
        if r:
            c = "w" if p["position"] in word_ps else "n"
            boxes.append(f'<rect class="{c}" x="{r[0]}" y="{r[1]}" width="{r[2]}" height="{r[3]}"/>'
                         f'<text class="{c}" x="{r[0] + 6}" y="{r[1] - 10}">{p["position"]}</text>')
    rs = [rects[p["position"]] for p in ctx if p["position"] in rects]
    zoom = '<p class="muted">No sign boxes for this stretch.</p>'
    if rs:
        pad = 0.9 * statistics.median([r[3] for r in rs])
        x0, y0 = max(0, min(r[0] for r in rs) - pad), max(0, min(r[1] for r in rs) - pad)
        x1, y1 = min(W, max(r[0] + r[2] for r in rs) + pad), min(H, max(r[1] + r[3] for r in rs) + pad)
        zoom = (f'<svg class="zoom" viewBox="{x0:.0f} {y0:.0f} {x1 - x0:.0f} {y1 - y0:.0f}" role="img" '
                f'aria-label="{esc(word)} on SigLA\'s drawing of {esc(sid)}, zoomed"><image href="{src}" x="0" y="0" '
                f'width="{W}" height="{H}"/>{"".join(boxes)}</svg>')
    full_boxes = "".join(f'<rect class="w" x="{rects[p][0]}" y="{rects[p][1]}" width="{rects[p][2]}" '
                         f'height="{rects[p][3]}"/>' for p in word_ps if p in rects)
    full = (f'<a href="{src}" target="_blank" rel="noopener"><svg class="full" viewBox="0 0 {W} {H}" role="img" '
            f'aria-label="whole drawing of {esc(sid)}"><image href="{src}" x="0" y="0" width="{W}" height="{H}"/>'
            f'{full_boxes}</svg></a>')
    return (f'<div class="views"><figure>{zoom}<figcaption>The word boxed, three signs either side numbered</figcaption>'
            f'</figure><figure>{full}<figcaption>Whole drawing</figcaption></figure></div>')


def sign_cell(rv: Review, sid: str, p: dict, in_word: bool) -> str:
    """One position: SigLA's crop, the Unicode glyph, SigLA's label, its sign id and role, and its flags."""
    s = p["signs"][0] if p["signs"] else None
    gch = rv.glyph(s)
    cp = rv.crop(sid, p["position"])
    flags = [f for f, on in (("unread", not p["read"]), ("uncertain", p["read"] and not p["certain"]),
                             ("erased", p["erased"]), ("hidden", p["hidden"]), ("role ?", not p["role_certain"])) if on]
    crop_html = (f'<img loading="lazy" src="{rv.rel(cp)}" alt="{esc(sid)} sign {p["position"]}">' if cp
                 else '<span class="muted">no crop</span>')
    return (f'<div class="sign{" in" if in_word else ""}"><div class="crop">{crop_html}</div>'
            f'<div class="uni" lang="und-Lina">{esc(gch) if gch else "□"}</div><div class="lab">{esc(rv.label(p))}</div>'
            f'<div class="meta">#{p["position"]} · {esc(s["sign_id"] if s else "—")} · {esc(p["role"])}</div>'
            f'<div class="flags">{" ".join(f"<span>{esc(f)}</span>" for f in flags)}</div></div>')


def strip(rv: Review, best: tuple, with_gaps: bool) -> str:
    """The word and three signs either side as cells; between them, when asked, the measured space and whether
    SigLA divides there (red at the word's own edges)."""
    sid, i, _n, ln = best[:4]
    d = rv.db[sid]
    pos, rects = d["positions"], rv.geo.get(sid, {"rects": {}})["rects"]
    word_ps = word_positions(rv, best)
    ctx = pos[max(0, i - CONTEXT):min(len(pos), i + ln + CONTEXT)]
    line_of = {p: li for li, l in enumerate(lines_of(pos, rects)) for p in l}
    ws = [rects[p["position"]][2] for p in pos if p["position"] in rects]
    mw = statistics.median(ws) if ws else 1
    word_of = {p: wi for wi, w in enumerate(d["words"]) for p in w["positions"]}
    cells, prev = [], None
    for p in ctx:
        pp = p["position"]
        cur = (pp, rects.get(pp))
        if prev and with_gaps:
            div = word_of.get(prev[0]) != word_of.get(pp) or word_of.get(pp) is None
            edge = (prev[0] in word_ps) != (pp in word_ps)
            cells.append(f'<div class="gap{" edge" if edge else ""}"><span class="g">{esc(gap(prev, cur, mw, line_of))}</span>'
                         f'<span class="div">{"SigLA divides" if div else "same SigLA word"}</span></div>')
        cells.append(sign_cell(rv, sid, p, pp in word_ps))
        prev = cur
    return f'<div class="strip">{"".join(cells)}</div>'


def edges(rv: Review, best: tuple) -> tuple[str, str]:
    """The measured space before and after the word."""
    sid, i, _n, ln = best[:4]
    pos, rects = rv.db[sid]["positions"], rv.geo.get(sid, {"rects": {}})["rects"]
    word_ps = word_positions(rv, best)
    line_of = {p: li for li, l in enumerate(lines_of(pos, rects)) for p in l}
    ws = [rects[p["position"]][2] for p in pos if p["position"] in rects]
    mw = statistics.median(ws) if ws else 1
    before = gap((pos[i - 1]["position"], rects.get(pos[i - 1]["position"])) if i else None,
                 (word_ps[0], rects.get(word_ps[0])), mw, line_of)
    after = gap((word_ps[-1], rects.get(word_ps[-1])),
                (pos[i + ln]["position"], rects.get(pos[i + ln]["position"])) if i + ln < len(pos) else None, mw, line_of)
    return before, after


def sigla_reading(rv: Review, best: tuple) -> str:
    """SigLA's words set out on its lines, the word's own lit."""
    sid = best[0]
    d = rv.db[sid]
    word_ps = set(word_positions(rv, best))
    line_of = {p: li for li, l in enumerate(lines_of(d["positions"], rv.geo.get(sid, {"rects": {}})["rects"])) for p in l}
    rows: dict[int, list[str]] = {}
    for w in d["words"]:
        if w["positions"]:
            on = bool(set(w["positions"]) & word_ps)
            rows.setdefault(line_of.get(w["positions"][0], 0), []).append(
                f'<span class="sw{" on" if on else ""}">{esc(w["text"])}</span>')
    return "".join(f'<div class="sl"><span class="ln">{li + 1}</span><div class="sws">{"".join(ws)}</div></div>'
                   for li, ws in sorted(rows.items()))


def sigla_word(rv: Review, best: tuple) -> str:
    word_ps = set(word_positions(rv, best))
    return " · ".join(w["text"] for w in rv.db[best[0]]["words"] if set(w["positions"]) & word_ps) or \
        "(outside SigLA's words)"


def sigla_record(rv: Review, best: tuple) -> str:
    """The whole sigla_db.json record, folded: metadata, SigLA's word division, every position with every field."""
    d = rv.db[best[0]]
    word_ps = set(word_positions(rv, best))
    seals = "; ".join(f'{s.get("cms") or "—"}, {s.get("motif") or "—"} (×{s.get("count")})' for s in d["seals"]) or "none"
    eu = str(d.get("edition_url") or "")
    edition = f'<a href="{esc(eu)}">{esc(eu)}</a>' if eu.startswith("http") else esc(eu or "—")
    meta = (f'<dl class="meta-grid"><dt>SigLA id</dt><dd>{esc(d["sigla_id"])}</dd><dt>corpus_key</dt>'
            f'<dd>{esc(str(d["corpus_key"]))} ({esc(str(d["corpus_match"]))})</dd><dt>Support</dt><dd>{esc(str(d["support"]))}</dd>'
            f'<dt>Site</dt><dd>{esc(str(d["site"]))}</dd><dt>Period</dt><dd>{esc(str(d["period"]))}</dd>'
            f'<dt>Dimensions</dt><dd>{esc(str(d["dimensions_cm"]))} cm</dd><dt>Edition</dt><dd>{edition}</dd>'
            f'<dt>Seals</dt><dd>{esc(seals)}</dd></dl>')
    words = " · ".join(f'<span class="{"hl" if set(w["positions"]) & word_ps else ""}">{esc(w["text"])}</span>'
                       for w in d["words"]) or "(no SigLA word division)"
    word_of = {p: wi for wi, w in enumerate(d["words"]) for p in w["positions"]}
    rows = []
    for p in d["positions"]:
        s = p["signs"][0] if p["signs"] else {}
        rows.append(
            f'<tr class="{"hl" if p["position"] in word_ps else ""}"><td>{p["position"]}</td><td>{esc(rv.label(p))}</td>'
            f'<td>{esc(s.get("code", "—"))}</td><td>{esc(s.get("sign_id", "—"))}</td><td>{esc(s.get("phon") or "—")}</td>'
            f'<td>{esc(s.get("name") or "—")}</td><td>{esc(s.get("variant") or "—")}</td><td>{esc(p["role"])}'
            f'{"" if p["role_certain"] else "?"}</td><td>{"—" if p["certain"] is None else ("yes" if p["certain"] else "no")}</td>'
            f'<td>{"yes" if p["erased"] else ""}</td><td>{"yes" if p["hidden"] else ""}</td>'
            f'<td>{"" if word_of.get(p["position"]) is None else word_of[p["position"]] + 1}</td></tr>')
    return (f'<details class="sigla"><summary>Full SigLA record (sigla_db.json)</summary>{meta}'
            f'<p class="swords"><b>SigLA words:</b> {words}</p><div class="tablewrap"><table><thead><tr><th>#</th><th>label</th>'
            f'<th>code</th><th>sign_id</th><th>phon</th><th>name</th><th>variant</th><th>role</th><th>certain</th>'
            f'<th>erased</th><th>hidden</th><th>word</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div></details>')


def edition_figures(rv: Review, key: str, rights_from: dict | None = None) -> str:
    imgs = rv.edition_images(key)
    if not imgs:
        return '<p class="muted">No edition photograph or facsimile held.</p>'
    figs = "".join(f'<figure><a href="{rv.rel(p)}" target="_blank" rel="noopener"><img loading="lazy" src="{rv.rel(p)}" '
                   f'alt="{esc(key)} {kind.lower()}"></a><figcaption>{kind}</figcaption></figure>' for kind, p in imgs)
    rights = (rv.corpus.get(key) or {}).get("imageRights") or ""
    return f'<div class="photos">{figs}</div>' + (f'<p class="muted rights">Images {esc(rights)}</p>' if rights else "")


# --- rulings ----------------------------------------------------------------------------------------------

def ruling_html(r: dict | None) -> tuple[str, str]:
    """(header badge, ruling line) for a ruling {"outcome", "kind": keep | unread, "text"}."""
    if not r:
        return "", ""
    return (f'<span class="ruled {esc(r["kind"])}">Ruled: {esc(r["outcome"])}</span>',
            f'<div class="ruling {esc(r["kind"])}"><b>Ruling:</b> {esc(r["text"])}</div>')


RULING_CSS = """
.ruled{display:inline-block;font:600 12px/1.6 ui-monospace,Menlo,monospace;border-radius:4px;padding:0 6px;border:1px solid}
.ruled.keep{color:var(--ok);border-color:var(--ok)} .ruled.unread{color:var(--warn);border-color:var(--warn)}
.ruling{font-size:14px;border-left:3px solid var(--warn);padding:6px 12px;margin:8px 0} .ruling.keep{border-color:var(--ok)}
.progress{border:1px solid var(--line);border-radius:10px;padding:12px 16px;margin:0 0 18px}
.progress h2{font-size:18px;margin:0 0 4px} .progress ol{margin:6px 0 0;padding-left:22px} .progress li{margin:4px 0}
"""


def progress_html(rulings: dict, anchors: dict, total: int | None = None) -> str:
    """The rulings so far, each with links to its cards."""
    if not rulings:
        return ""
    rows = "".join(
        f'<li><b>{esc(w)}</b> <span class="ruled {esc(r["kind"])}">{esc(r["outcome"])}</span> {esc(r["text"])} '
        f'<span class="muted">→</span> {" · ".join(f"<a href=#{c}>{esc(lbl)}</a>" for c, lbl in anchors.get(w, []))}</li>'
        for w, r in rulings.items())
    head = f"{len(rulings)} ruled" + (f" of {total} words" if total else "") + "; the rest await a ruling."
    return f'<section class="progress"><h2>Progress</h2><p class="muted">{esc(head)}</p><ol>{rows}</ol></section>'
