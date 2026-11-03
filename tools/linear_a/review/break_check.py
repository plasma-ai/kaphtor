#!/usr/bin/env python3
"""Break-check page: does a word end where the record says it does?

For each attestation, SigLA's drawing with the word's signs boxed and three signs either side numbered; between
signs, the measured space in median sign widths for that document and whether SigLA divides there (red at the
word's own edges); the Unicode line with SigLA's divisions; the full SigLA record; the edition photograph and
facsimile. Rulings recorded in the spec show as badges and a progress panel, so the page doubles as the ledger.

The spec (JSON) names the words. A tab lists its items, or takes them from a source:

    {"title": "Break check",
     "tabs": [{"id": "hold", "title": "Hold list", "items": [{"word": "NU-TI", "keys": ["HT84", "ZA9"]}]},
              {"id": "archive", "title": "Archived → unread", "source": "archive_unread", "restored": ["A-RU-RA"]}],
     "spans": {"RU-PI-*305-MI|PE2": [3, 9]},
     "rulings": {"NU-TI": {"outcome": "unread", "kind": "unread", "text": "Broken before NU on both witnesses."}}}

An item may carry "form" (the record's form, when it differs from the word) and "notes" (plain text). Source
"archive_unread": every lexicon_archive.json entry with an unread_words.json record, and each word in "restored"
from lexicon.json. "spans" boxes a stretch SigLA reads otherwise (first and last SigLA position).

    uv run tools/linear_a/review/break_check.py SPEC.json --fetch   # fetch missing SigLA drawings (1 request/s), then build
    uv run tools/linear_a/review/break_check.py SPEC.json --out DIR # build from what is held, into DIR

The page goes to CACHE/review/SPEC-stem/ (or --out), never into the repository: the SigLA drawings are SigLA's
(CC BY-NC-SA 4.0), and edition photographs (--edition-images) carry their own rights. Read-only on the data;
writes only the page folder's index.html and images/.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    __package__ = "tools.linear_a.review"

from ...paths import CACHE, LINEAR_A_DATA, REPO
from . import review_core as rc
from .review_core import esc

DEFAULTS = {
    "data": LINEAR_A_DATA,
    "builder": REPO / "tools/linear_a/build_sigla_db.py",
    "database_js": LINEAR_A_DATA / "sigla/database.js",
    "sign_map": LINEAR_A_DATA / "sigla-sign-map.json",
    "out": CACHE / "review",
}


def _p(x: str | None) -> Path | None:
    return Path(x).expanduser() if x else None


def paragraphs(text: str) -> str:
    return "".join(f"<p>{esc(t)}</p>" for t in text.split("\n\n") if t.strip())


def archive_unread(rv: rc.Review, restored: list[str]) -> list[dict]:
    """Every lexicon_archive.json entry with an unread_words.json record, and each restored lexicon word."""
    data = rv.src.data
    if not (data / "lexicon_archive.json").exists():
        raise SystemExit(f"source archive_unread needs lexicon_archive.json, not in {data}")
    arch, unread = rc.entries(data / "lexicon_archive.json"), rc.entries(data / "unread_words.json")

    def core(w):
        return "-".join(rc.tokens(w)).replace("?", "").replace("--", "-").strip("-")

    by_core: dict[str, list] = {}
    for u in unread:
        by_core.setdefault(core(u["word"]), []).append(u)
    items = []
    for a in arch:
        rj = a.get("rejection") or {}
        reason = rj.get("reason", "") if isinstance(rj, dict) else str(rj)
        found = list(by_core.get(core(a["word"]), []))
        if not found and "unread_words" in reason:   # the reason names the longer form now listed as unread
            found = sorted((u for u in unread if u["word"] in reason and core(a["word"]) in core(u["word"])),
                           key=lambda u: -len(u["word"]))[:1]
        for u in found:
            notes = (f'<div class="rec"><p><b>Archived:</b> {esc(a["word"])} · {esc(str(a.get("confidence")))}'
                     f'{" · " + esc(a.get("reading") or "") if a.get("reading") else ""}'
                     f'{" ‘" + esc(a.get("meaning") or "") + "’" if a.get("meaning") else ""}</p>'
                     f'<p><b>Reason:</b> {esc(reason)}</p>'
                     f'<p><b>Unread record</b> {esc(u["word"])} ({esc(u.get("status", ""))}): {esc(u.get("note", ""))}</p></div>')
            for k in u.get("attestations") or a.get("attestations") or []:
                items.append({"word": a["word"], "form": u["word"], "key": k, "notes_html": notes})
    lexicon = {e["word"]: e for e in rc.entries(data / "lexicon.json")}
    for w in restored:
        e = lexicon.get(w)
        if e is None:
            raise SystemExit(f"restored word {w} is not in lexicon.json")
        notes = (f'<div class="rec"><p><b>Restored to the lexicon:</b> {esc(w)} · {esc(str(e.get("confidence")))} · '
                 f'{esc(e.get("reading") or "")} ‘{esc(e.get("meaning") or "")}’</p>'
                 f'<p><b>Lexicon note:</b> {esc(e.get("note", ""))}</p></div>')
        for k in e.get("attestations") or []:
            items.append({"word": w, "title": f"{w} (restored)", "form": w, "key": k, "notes_html": notes})
    return items


def tab_items(rv: rc.Review, tab: dict) -> list[dict]:
    if tab.get("source") == "archive_unread":
        return archive_unread(rv, tab.get("restored", []))
    if tab.get("source"):
        raise SystemExit(f"unknown source {tab['source']!r}")
    out = []
    for it in tab["items"]:
        for k in it["keys"]:
            out.append({"word": it["word"], "form": it.get("form", it["word"]), "key": k,
                        "notes_html": paragraphs(it.get("notes", ""))})
    return out


def card(rv: rc.Review, item: dict, best: tuple | None, cid: str, ruling: dict | None) -> str:
    title, form, key = item.get("title", item["word"]), item["form"], item["key"]
    badge, rline = rc.ruling_html(ruling)
    form_line = f' <span class="muted">record form</span> <span class="doc">{esc(form)}</span>' if form != item["word"] else ""
    notes = rline + item.get("notes_html", "")
    photos = f'<details><summary>Edition photograph and facsimile</summary>{rc.edition_figures(rv, key)}</details>'
    if best is None:
        return (f'<section class="card" id="{cid}"><header><h2>{esc(title)}</h2>{form_line}<span class="doc">{esc(key)}</span>'
                f'<span class="flag warn">not in SigLA</span>{badge}</header>{notes}{rc.edition_figures(rv, key)}</section>')
    sid, _i, n, _ln = best[:4]
    whole = best[4] if len(best) > 4 else None
    ntok = len(rc.tokens(form))
    before, after = rc.edges(rv, best)
    match = (f"this face holds {n} of the word's {whole} signs; SigLA files each face as its own document" if whole
             else "SigLA reads this stretch otherwise: the whole stretch is boxed" if n is None
             else "all signs match" if n == ntok else f"{n} of {ntok} signs match SigLA's reading")
    word_ps = rc.word_positions(rv, best)
    return f'''<section class="card" id="{cid}">
<header><h2>{esc(title)}</h2>{form_line}<span class="doc">{esc(sid)} <span class="muted">({esc(key)})</span></span>
<span class="flag{"" if n == ntok and not whole else " warn"}">{esc(match)}</span>{badge}</header>
<dl class="facts"><div><dt>Before</dt><dd>{esc(before)}</dd></div><div><dt>After</dt><dd>{esc(after)}</dd></div>
<div><dt>SigLA word</dt><dd>{esc(rc.sigla_word(rv, best))}</dd></div><div><dt>Positions</dt><dd>{", ".join(map(str, word_ps))}</dd></div></dl>
{notes}
{rc.views(rv, best, form)}
{rc.strip(rv, best, with_gaps=True)}
{unicode_lines(rv, best)}
{rc.sigla_record(rv, best)}
{photos}
</section>'''


def unicode_lines(rv: rc.Review, best: tuple) -> str:
    """Each line holding the word, in Unicode, the word outlined and SigLA's divisions as ·."""
    sid = best[0]
    d = rv.db[sid]
    pos, rects = d["positions"], rv.geo.get(sid, {"rects": {}})["rects"]
    lines = rc.lines_of(pos, rects)
    line_of = {p: li for li, l in enumerate(lines) for p in l}
    word_ps = rc.word_positions(rv, best)
    word_of = {p: wi for wi, w in enumerate(d["words"]) for p in w["positions"]}
    by_pos = {p["position"]: p for p in pos}
    out = []
    for li in sorted({line_of[p] for p in word_ps if p in line_of}):
        parts, last_w = [], object()
        for pp in lines[li]:
            p = by_pos[pp]
            s = p["signs"][0] if p["signs"] else None
            gch = (rv.glyph(s) or s["code"]) if s else "[?]"
            w = word_of.get(pp, ("solo", pp))
            sep = "" if not parts or w == last_w else '<span class="sep">·</span>'
            parts.append(sep + f'<span class="{"hl" if pp in word_ps else ""}" title="#{pp} {esc(rv.label(p))}">{esc(gch)}</span>')
            last_w = w
        out.append(f'<div class="uline" lang="und-Lina">{"".join(parts)}</div>')
    return f'<div class="ulines">{"".join(out)}</div>'


CSS = """
:root{--bg:#faf8f4;--fg:#1d1b18;--muted:#6f6a62;--card:#ffffff;--line:#e3ddd2;--accent:#b4442c;--accent-soft:rgba(180,68,44,.16);--nb:#2f6f8f;--warn:#9a6a00;--ok:#2e7d4f}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#16150f;--fg:#ece7dd;--muted:#a39d92;--card:#201f19;--line:#38352c;--accent:#e2765c;--accent-soft:rgba(226,118,92,.2);--nb:#6fb3d4;--warn:#e0b040;--ok:#6cc690}}
:root[data-theme="dark"]{--bg:#16150f;--fg:#ece7dd;--muted:#a39d92;--card:#201f19;--line:#38352c;--accent:#e2765c;--accent-soft:rgba(226,118,92,.2);--nb:#6fb3d4;--warn:#e0b040;--ok:#6cc690}
*{box-sizing:border-box} body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 "Iowan Old Style","Palatino Linotype",Georgia,serif}
main{max-width:1180px;margin:0 auto;padding:24px 16px 80px} h1{font-size:26px;margin:0 0 4px} .lede{color:var(--muted);margin:0 0 14px}
[role=tablist]{display:flex;gap:6px;border-bottom:1px solid var(--line);margin:0 0 18px;position:sticky;top:0;background:var(--bg);z-index:2;padding-top:8px}
[role=tab]{font:inherit;font-weight:600;background:none;border:1px solid transparent;border-bottom:none;padding:8px 14px;border-radius:8px 8px 0 0;color:var(--muted);cursor:pointer}
[role=tab][aria-selected=true]{color:var(--fg);border-color:var(--line);background:var(--card);margin-bottom:-1px} .count{font-weight:400;color:var(--muted)}
a{color:var(--nb)} nav ol{columns:3 220px;padding-left:24px;margin:0 0 24px} .muted{color:var(--muted)} .warn{color:var(--warn)}
.card,.progress{background:var(--card)} .card{border:1px solid var(--line);border-radius:10px;padding:16px;margin:0 0 22px}
.card header{display:flex;flex-wrap:wrap;gap:10px;align-items:baseline} .card h2{margin:0;font-size:22px}
.doc{font-family:ui-monospace,Menlo,monospace;font-size:14px} .flag{font-size:13px;color:var(--muted)} .flag.warn{color:var(--warn)}
.facts{display:flex;flex-wrap:wrap;gap:6px 26px;margin:10px 0} .facts div{display:flex;gap:8px} dt{color:var(--muted)} dd{margin:0;font-weight:600}
.rec{font-size:14px;border-left:3px solid var(--line);padding:2px 12px;margin:8px 0 12px} .rec p{margin:4px 0}
.views{display:grid;grid-template-columns:minmax(0,3fr) minmax(0,1fr);gap:12px;align-items:start} .views figure{margin:0}
@media (max-width:720px){.views{grid-template-columns:1fr}}
svg{width:100%;height:auto;background:#fff;border:1px solid var(--line);border-radius:6px} svg.zoom{max-height:520px}
rect.w{fill:var(--accent-soft);stroke:var(--accent);stroke-width:8} rect.n{fill:none;stroke:var(--nb);stroke-width:5;stroke-dasharray:22 14}
svg text{font:bold 48px ui-monospace,Menlo,monospace;paint-order:stroke;stroke:#fff;stroke-width:10} text.w{fill:var(--accent)} text.n{fill:var(--nb)}
svg.full rect.w{stroke-width:14}
.strip{display:flex;gap:4px;overflow-x:auto;padding:12px 2px 6px;align-items:stretch}
.sign{flex:0 0 112px;border:1px solid var(--line);border-radius:8px;padding:6px;text-align:center}
.sign.in{border:2px solid var(--accent);background:var(--accent-soft)}
.crop{height:96px;display:flex;align-items:center;justify-content:center;background:#fff;border-radius:4px} .crop img{max-height:92px;max-width:100px}
.uni{font:34px/1.2 "Noto Sans Linear A",sans-serif;margin-top:4px} .sign.in .uni{color:var(--accent)}
.lab{font-weight:700;font-family:ui-monospace,Menlo,monospace;font-size:13px} .meta{font-size:11px;color:var(--muted)}
.flags span{display:inline-block;font-size:11px;border:1px solid var(--warn);color:var(--warn);border-radius:4px;padding:0 4px;margin:2px 1px 0}
.gap{flex:0 0 74px;display:flex;flex-direction:column;justify-content:center;text-align:center;font-size:11px;color:var(--muted)}
.gap.edge{color:var(--accent);font-weight:700} .gap .div{display:block;margin-top:4px}
.ulines{margin:10px 0 4px} .uline{font:28px/1.6 "Noto Sans Linear A",sans-serif;word-break:break-all}
.hl{background:var(--accent-soft);outline:2px solid var(--accent);border-radius:3px} .uline .sep{color:var(--muted);padding:0 4px}
details summary{cursor:pointer;color:var(--muted);margin-top:8px} .photos{display:flex;flex-wrap:wrap;gap:12px;margin-top:8px}
.photos figure{margin:0;max-width:min(100%,480px)} .photos img{max-width:100%;border:1px solid var(--line);border-radius:6px;background:#fff}
figcaption{font-size:12px;color:var(--muted)} .legend span{margin-right:16px}
.meta-grid{display:grid;grid-template-columns:max-content 1fr;gap:2px 14px;font-size:13px;margin:8px 0} .meta-grid dd{font-weight:400;word-break:break-all}
.swords{font-family:ui-monospace,Menlo,monospace;font-size:13px}
.tablewrap{overflow-x:auto} table{border-collapse:collapse;font:12px ui-monospace,Menlo,monospace;width:100%}
th,td{border-bottom:1px solid var(--line);padding:3px 6px;text-align:left;white-space:nowrap} th{color:var(--muted);font-weight:600}
tr.hl td{background:var(--accent-soft)} tr.hl{outline:none}
""" + rc.RULING_CSS

LEDE = ("Each word on SigLA's drawing: the word's signs in solid boxes, three signs either side dashed and numbered. "
        "Between signs the measured space in median sign widths for that document (negative means the boxes overlap) "
        "and whether SigLA divides there; red gap labels mark the word's own edges. The Unicode line shows the whole "
        "line, the word outlined, SigLA's divisions as ·. Under each card, the full SigLA record and the edition "
        "photograph and facsimile.")

CREDITS = ("Drawings, sign crops and the SigLA record: SigLA (sigla.phis.me), © 2020– Ester Salgarella and Simon "
           "Castellan, CC BY-NC-SA 4.0. Photographs and facsimiles: as each record's imageRights states.")


def build(spec: dict, rv: rc.Review) -> tuple[str, list[str]]:
    rulings = spec.get("rulings", {})
    spans = {tuple(k.split("|")): tuple(v) for k, v in spec.get("spans", {}).items()}
    tabs, anchors, report = [], {}, []
    for tab in spec["tabs"]:
        cards, toc = [], []
        for j, item in enumerate(tab_items(rv, tab)):
            picks = rv.find(item["form"], item["key"], spans.get((item["form"], item["key"]))) or [None]
            for k, best in enumerate(picks):
                cid = f'{tab["id"]}-{j}-{k}'
                r = rulings.get(item["word"])
                cards.append(card(rv, item, best, cid, r))
                status = ("not in SigLA" if best is None else "part, on this face" if len(best) > 4 else
                          "" if best[2] == len(rc.tokens(item["form"])) else "check")
                face = f" {best[0]}" if best and len(picks) > 1 else ""
                if r:
                    anchors.setdefault(item["word"], []).append((cid, f'{tab["title"]}, {item["key"]}{face}'))
                rtag = f' <span class="ruled {esc(r["kind"])}">{esc(r["outcome"])}</span>' if r else ""
                toc.append(f'<li><a href="#{cid}">{esc(item.get("title", item["word"]))}</a> <span class="muted">'
                           f'{esc(item["key"])}{esc(face)}</span>{f" <span class=warn>{status}</span>" if status else ""}{rtag}</li>')
        tabs.append((tab["id"], tab["title"], cards, toc))
        report.append(f'{tab["title"]}: {len(cards)} cards')
    words = {it["word"] for t in spec["tabs"] for it in t.get("items", [])}
    progress = rc.progress_html(rulings, anchors, len(words) or None)
    return page(spec, tabs, progress), report


def page(spec: dict, tabs: list, progress: str) -> str:
    buttons = "".join(f'<button role="tab" data-tab="{t}" aria-selected="{"true" if k == 0 else "false"}">{esc(title)} '
                      f'<span class="count">{len(cards)}</span></button>' for k, (t, title, cards, _) in enumerate(tabs))
    panels = "".join(f'<div class="panel" role="tabpanel" id="panel-{t}"{"" if k == 0 else " hidden"}><nav><ol>{"".join(toc)}</ol></nav>'
                     f'{"".join(cards)}</div>' for k, (t, _, cards, toc) in enumerate(tabs))
    title = spec.get("title", "Break check")
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title><style>{CSS}</style></head><body><main>
<h1>{esc(title)}</h1>
<p class="lede">{esc(spec.get("lede", LEDE))}</p>
<p class="legend muted"><span style="color:var(--accent)">■ the word</span><span style="color:var(--nb)">┅ neighbours</span></p>
{progress}
<div role="tablist">{buttons}</div>
{panels}
<p class="muted">{esc(CREDITS)}</p>
</main>
<script>
const tabs=[...document.querySelectorAll('[role=tab]')];
function show(id){{tabs.forEach(t=>t.setAttribute('aria-selected',t.dataset.tab===id));
document.querySelectorAll('.panel').forEach(p=>p.hidden=p.id!=='panel-'+id);}}
tabs.forEach(t=>t.addEventListener('click',()=>{{show(t.dataset.tab);history.replaceState(null,'','#'+t.dataset.tab)}}));
const h=location.hash.slice(1); if(h){{const tab=h.split('-')[0]; if(document.getElementById('panel-'+tab)){{show(tab); const el=document.getElementById(h); if(el) el.scrollIntoView();}}}}
</script></body></html>'''


def source_args(ap: argparse.ArgumentParser, defaults: dict) -> None:
    for k in ("data", "builder", "database_js", "sign_map"):
        ap.add_argument(f"--{k.replace('_', '-')}", default=str(defaults[k]))
    ap.add_argument("--edition-images", help="root of the corpus records' images / facsimileImages paths")
    ap.add_argument("--crops", help="SigLA sign crops: CROPS/{SigLA id}/{SigLA id}_{position}.png")
    ap.add_argument("--sigla-images", help="folder of SigLA drawings already held, {SigLA id}.png")


def sources(a) -> rc.Sources:
    return rc.Sources(data=Path(a.data), builder=Path(a.builder), database_js=Path(a.database_js),
                      sign_map=Path(a.sign_map), edition_images=_p(a.edition_images), crops=_p(a.crops),
                      sigla_images=_p(a.sigla_images))


def out_dir(a, forbid: Path | None) -> Path:
    """The output folder: --out, else defaults["out"]/SPEC-stem; never inside `forbid` (a repository)."""
    out = (Path(a.out).expanduser() if a.out else Path(a.out_root) / Path(a.spec).stem).resolve()
    if forbid and out.is_relative_to(forbid.resolve()):
        raise SystemExit(f"--out {out} is inside {forbid}; review pages are written outside the repository")
    out.mkdir(parents=True, exist_ok=True)
    return out


def main(defaults: dict = DEFAULTS, forbid: Path | None = REPO, builder=None, doc: str | None = None) -> None:
    ap = argparse.ArgumentParser(description=(doc or __doc__).splitlines()[0])
    ap.add_argument("spec", help="the page's spec, JSON")
    ap.add_argument("--out", required="out" not in defaults, help="folder for index.html and images/")
    ap.set_defaults(out_root=str(defaults.get("out", "")))
    ap.add_argument("--fetch", action="store_true", help="fetch missing SigLA drawings (1 request/s)")
    source_args(ap, defaults)
    a = ap.parse_args()
    out = out_dir(a, forbid)
    rv = rc.Review(sources(a), out, fetch=a.fetch)
    html_text, report = (builder or build)(json.loads(Path(a.spec).read_text(encoding="utf-8")), rv)
    (out / "index.html").write_text(html_text, encoding="utf-8")
    print("\n".join(report))
    print(f"wrote {out / 'index.html'}")


if __name__ == "__main__":
    main()
