#!/usr/bin/env python3
"""Shoresh (שֹׁרֶשׁ): is a Linear A sign group closer to a Semitic root than its own decoys, and to which root?

Report-only: prints, never writes. The statistic, decoys and verdicts are pre-registered in
docs/shoresh-preregistration.md (§§1-4, §6 amendments). Every result enters at SPECULATIVE. The competitor null
(§2, A15) runs against Luwian, Egyptian and Hurrian on the same decoys unless --no-competitors. The semantic gate
(§3.1, A10, A18) reads each word's attested contexts from data/linear-a/corpus.json; CONVERGENT needs p_max and the gated
p_max under 0.01 and the competitor null run and passed. POS (§3.2) holds vacuously, since no variant is a
verbal-template parse. --calibrate (§7.4) runs the gold set and is not built here.

Usage:
  uv run tools/linear_a/root_match.py SI-KI-NE
  uv run tools/linear_a/root_match.py SI-KI-NE KA-PA --n 1000 --json
  uv run tools/linear_a/root_match.py --file words.txt --full-index      # secondary result: no A4 exclusions
  uv run tools/linear_a/root_match.py DA-ME --families BC --top 5 --no-breadth
  uv run tools/linear_a/root_match.py SI-KI-NE --explain --top 3          # reflexes, citations, joined lexemes, sound laws
  uv run tools/linear_a/root_match.py --sweep unread --top 50 --workers 8  # unread_words.json ranked by q (run on a snapshot)

--sweep unread queries every entry of data/linear-a/unread_words.json, sets gold-set words aside (counted, never queried),
ranks by Benjamini–Hochberg q and stamps the report with the sha256 of the word list and of the index (§7.1).
--top is then the number of ranked rows shown; --json carries every row. A sweep is a long run: read a frozen
snapshot (§7.7).

--explain prints, under each cluster, the record as indexed (PS headword, meaning, every Analogues row with its
citation), the contact lexemes that join it, those linked to it that do not ("possible cognate of N", §8), and
under each word the lexemes with no root link at or under its d*; none of these enters d*, p or breadth. Each
cluster also gets its sound laws: for each aligned radical of the nearest PS headword,
the branches whose reflex (Huehnergard Table 3.2), spelled as the script would spell it, matches the Linear A sign.
A radical is diagnostic when some branches match and some do not; the profile is the branches that match at every
diagnostic radical. Report-only, never in d*, p or the verdict; Geers' law is not checked.

A gold-set word (tests/fixtures/root_match_gold.v3.json) is refused before the index loads: an engine number on gold
freezes the §6 amendments. The guard compares sign names and the engine's readings, so KU2-RO and KU-*310-SU are
held back with KU-RO and KU-NI-SU. --gold-run lifts the guard for the gold run itself.

Words are queried in canonical spelling (upper case, subscripts as digits). Every report is stamped with the sha256
of the index, of the gold set (none under --gold-run), of data/linear-a/corpus.json and of the frozen tagger, each
hashed from the bytes read. --top 0 shows every cluster, or every sweep row.

Exit status: 0; 1 if a word had an unmapped sign (reported, never shortened); 2 if the index is stale, missing or
changed while loading or before its Meanings were read, or a rival-language file is not in the checkout; 3 if a
word is in the gold set or the gold set is unreadable or malformed; 4 if data/linear-a/corpus.json is unreadable or
the tagger is not the one A18 froze; 5 if data/linear-a/unread_words.json is not in the checkout (--sweep unread).

Attribution: di Mino
"""
from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = "tools.linear_a"

from ..core import root_match as rm
from ..core import semantic_gate as sg
from ..core.root_index import DEFAULT_INDEX, IndexStale, RootIndex, _ro
from ..paths import LINEAR_A_DATA, NotInCheckout
from .validation.root_match_phase0 import GOLD_V3_PATH, gold_guard, gold_sign_groups, sign_group_key  # noqa: F401

GOLD = GOLD_V3_PATH     # the guard's gold set; read at call time
UNREAD = LINEAR_A_DATA / "unread_words.json"      # --sweep unread
CORPUS = LINEAR_A_DATA / "corpus.json"            # the semantic gate's contexts (A18)
_RUN: dict[str, Any] = {}   # engine + query options, set in the parent before the pool forks; workers only read it


def primary_exclusions() -> dict[str, str]:
    """A4's frozen list from the gold set the guard reads (A13, A17); ValueError or OSError if it has none."""
    from .validation.root_match_phase0 import frozen_index_exclusions
    return frozen_index_exclusions(GOLD)


def competitor_spaces(names: bool) -> list[Any]:
    from ..core.competitors import load_all
    return load_all(names)


def index_record(index: RootIndex, number: str) -> dict[str, Any] | None:
    """The record as indexed (display only): PS headword, meaning and every Analogues row, citations in its text;
    None for a Number the index does not hold. Read from the index file, so it matches the keys loaded. Kept out of
    tools/core/root_index.py, a key-logic file: any edit there makes every built index stale."""
    conn = _ro(index.path)
    try:
        row = conn.execute("SELECT ps, meaning FROM roots WHERE number = ?", (number,)).fetchone()
        if row is None:
            return None
        analogues = [{"language": language, "branch": branch, "text": text} for language, branch, text in
                     conn.execute("SELECT language, branch, text FROM analogues WHERE number = ? "
                                  "ORDER BY branch, language", (number,))]
    finally:
        conn.close()
    return {"number": number, "ps": row[0], "meaning": row[1], "analogues": analogues}


SHOWN = 8      # --explain text: possible cognates and unlinked lexemes listed per cluster or word; --json has all


def cluster_lexemes(index: RootIndex, names: bool) -> tuple[dict[str, list[dict[str, Any]]],
                                                            dict[str, list[dict[str, Any]]]]:
    """(joined, possible): Number → the contact lexemes that join its cluster (rm.joined_clusters: fk, or an exact
    sound link with gloss overlap), and Number → those linked to it that do not join it, exact links first (§8,
    A17: "possible cognate of N", display only). Onomastic ones only with names, as the engine counts them."""
    joined_of: dict[str, list[dict[str, Any]]] = {}
    possible_of: dict[str, list[dict[str, Any]]] = {}
    for lid, links in index.links.items():
        meta = index.lexemes.get(lid, {})
        if meta.get("onomastic") and not names:
            continue
        joined = set(rm.joined_clusters(index, lid))
        for number, basis, _ in links:
            row = {"id": lid, "lexicon": meta.get("lexicon"), "form": meta.get("form"),
                   "meaning": meta.get("meaning"), "basis": basis}
            (joined_of if number in joined else possible_of).setdefault(number, []).append(row)
    for rows in possible_of.values():
        rows.sort(key=lambda x: (x["basis"] != "root_key_exact", x["id"]))
    return joined_of, possible_of


def explain(results: list[dict[str, Any]], index: RootIndex, names: bool, engine: rm.Shoresh) -> None:
    """--explain: each shown cluster gets its record as indexed (headword, meaning, Analogues with their citations),
    its joined lexemes and its possible cognates; each word gets the unlinked lexemes at or under its d* (§8, A17).
    The sound laws are already on each cluster. None of it touches d*, p or the verdict."""
    joined, possible = cluster_lexemes(index, names)
    records: dict[str, dict[str, Any] | None] = {}
    for r in results:
        if "error" in r:
            continue
        for h in r.get("clusters", ()):
            if h["number"] not in records:
                records[h["number"]] = index_record(index, h["number"])
            h["record"] = records[h["number"]]
            h["joined"] = joined.get(h["number"], [])
            h["possible"] = possible.get(h["number"], [])
        d = rm.INF if r["d_star"] is None else r["d_star"]
        r["unlinked"] = []
        for dist, lid in engine.unlinked_near(r["word"], d):
            meta = index.lexemes.get(lid, {})
            r["unlinked"].append({"id": lid, "lexicon": meta.get("lexicon"), "form": meta.get("form"),
                                  "meaning": meta.get("meaning"), "distance": dist})


def _one(word: str) -> dict[str, Any]:
    try:
        return _RUN["engine"].query(word, **_RUN["opts"]).to_json()
    except rm.UnmappedSign as e:
        return {"word": word, "error": f"unmapped sign {e.args[0]}: the word is never shortened (A5)"}


def unread_words(path: Path) -> tuple[list[str], str]:
    """--sweep unread: every listed entry of data/linear-a/unread_words.json, in file order, and the sha256 of the very
    bytes parsed (§7.1), so a write during the sweep cannot change what the stamp names."""
    raw = path.read_bytes()
    return [e["word"] for e in json.loads(raw.decode("utf-8"))["entries"]], hashlib.sha256(raw).hexdigest()


def corpus_contexts(path: Path) -> tuple[sg.Contexts, str]:
    """The semantic gate's contexts from data/linear-a/corpus.json, and the sha256 of the very bytes parsed (§7.1)."""
    raw = path.read_bytes()
    return sg.Contexts(json.loads(raw.decode("utf-8"))), hashlib.sha256(raw).hexdigest()


class IndexChanged(RuntimeError):
    """The index file changed between its load and the read of its Meanings."""


def canonical(word: str) -> str:
    """The spelling queried and seeded: signs upper-cased, subscripts as digits, empty segments dropped (the gold
    guard's sign_group_key), so ka-na-si and KA-NA-SI get the same decoys and the same p."""
    return "-".join(sign_group_key(word))


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def ranked(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sweep order: by BH q, then p_max, then word; words with no p after them, unmapped words last."""
    def key(r: dict[str, Any]) -> tuple:
        if "error" in r:
            return (2, 0.0, 0.0, r["word"])
        q, p = r.get("bh_q"), r.get("p_max")
        return (0 if p is not None else 1, q if q is not None else (p if p is not None else 0.0),
                p if p is not None else 0.0, r["word"])
    return sorted(results, key=key)


def run(words: list[str], *, index: RootIndex, exclusions: dict[str, str] | None, n: int, seed: int,
        families: str, names: bool, top: int, breadth: bool, corpus_words: list[str] | None = None,
        competitors: list[Any] = (), explained: bool = False, workers: int = 1,
        contexts: Any = None, index_sha: str | None = None) -> dict[str, Any]:
    """exclusions: the A4 Numbers left out (primary result), or None for the full index (secondary).
    competitors: competitors.CompetitorSpace objects for the competitor null (§2), or none. explained: --explain.
    contexts: semantic_gate.Contexts for the semantic gate (A18), or None for data/linear-a/corpus.json.
    The contexts, the tagger and the clusters' Meanings are read once, in the parent, before a pool forks; with
    index_sha, the index must still hash to it once its Meanings are read (IndexChanged otherwise), so the
    Meanings come from the very file whose keys were loaded. A changed tagger raises TaggerChanged here, before
    any word is queried.
    workers > 1 forks a pool over the same engine; every word's decoys come from its own seeded stream, so the
    results equal a serial run. A worker that dies (OOM, a kill) raises BrokenProcessPool rather than hanging."""
    engine = rm.Shoresh(index, names=names, exclude=exclusions or (), corpus_words=corpus_words,
                        competitors=competitors, contexts=contexts)
    _ = engine.contexts, engine._domains()
    if index_sha is not None and _sha256(index.path) != index_sha:
        raise IndexChanged(f"{index.path} changed before its Meanings were read; rerun on a frozen snapshot "
                           "(§7.7)")
    _RUN.update(engine=engine,
                opts={"n": n, "seed": seed, "families": families, "top": top, "breadth_check": breadth})
    if workers > 1:
        with ProcessPoolExecutor(workers, mp_context=multiprocessing.get_context("fork")) as pool:
            results = list(pool.map(_one, words))
    else:
        results = [_one(w) for w in words]
    if len(results) > 1:
        qs = rm.bh_q([r.get("p_max") for r in results])
        for r, q in zip(results, qs):
            if "error" not in r:
                r["bh_q"] = q
    if explained:
        explain(results, index, names, _RUN["engine"])
    out = {"index": str(index.path), "index_checked": index.checked,
           "key_set": "full (secondary)" if exclusions is None else f"primary (A4: {len(exclusions)} Numbers out)",
           "n": n, "seed": seed, "families": families, "names": names,
           "competitors": {c.name: len(c.keys) for c in competitors}, "results": results}
    if exclusions is not None:                       # A17: listed Numbers the index no longer holds
        held = {k.number for k in index.keys if k.number is not None}
        out["a4_absent"] = sorted(n for n in exclusions if n not in held)
    return out


def _fmt(x: float | None) -> str:
    return "—" if x is None else f"{x:.4g}"


def _semantic_lines(s: dict[str, Any]) -> list[str]:
    """The semantic gate (§3.1, A10, A18): the word's context, d*_sem over the clusters that fit it, and its p."""
    if not s:
        return []
    seen = f"{s['known']} of {s['attestations']} attestations"
    if s["context"] is None:
        return [f"  semantic: no semantic evidence ({seen} with a known context)"]
    head = f"  semantic: context {', '.join(s['context'])} ({seen}); {s['fitting']} retrieved clusters fit"
    if s["d_star"] is None:
        return [head, "  semantic: no fitting cluster retrieved, so no d*_sem and no CONVERGENT"]
    fams = "  ".join(f"{k}: p={_fmt(f['p'])}{'' if f['in_p_max'] else ' (not in p_max)'}"
                     for k, f in s["families"].items())
    return [head, f"  semantic: d*_sem={_fmt(s['d_star'])}  p_max_sem={_fmt(s['p_max'])} "
                  f"({s['deciding_family'] or '—'})  {fams}".rstrip()]


def _explained(h: dict[str, Any]) -> list[str]:
    rec = h.get("record")
    lines = [f"           {rec['ps'] or '—'} {rec['meaning'] or ''}".rstrip() if rec else
             "           (record not in the index)"]
    for a in (rec or {}).get("analogues", ()):
        lines.append(f"           {a['language']} ({a['branch'] or '—'}): {a['text']}")
    for lx in h.get("joined", ()):
        lines.append(f"           joined {lx['id']} {lx['form'] or '—'} '{lx['meaning'] or ''}' ({lx['basis']})")
    possible = h.get("possible", ())
    for lx in possible[:SHOWN]:
        lines.append(f"           possible cognate of {h['number']}: {lx['id']} {lx['form'] or '—'} "
                     f"'{lx['meaning'] or ''}' ({lx['basis']})")
    if len(possible) > SHOWN:
        lines.append(f"           … {len(possible) - SHOWN} more possible cognates")
    sl = h.get("sound_laws")
    if sl is None:
        lines.append("           sound laws: not computed (no PS headword)")
        return lines
    cells = []
    for p in sl["positions"]:
        cell = f"{p['ps']}:{p['la']} {p['status'].replace('_', ' ')}"
        if p["status"] == "diagnostic":
            cell += " (" + ", ".join(b + ("?" if b in p["uncertain"] else "") for b in p["consistent"]) + ")"
        cells.append(cell)
    lines.append(f"           sound laws vs {sl['headword']} ({sl['radicals']}): " + ("; ".join(cells) or "—"))
    profile = sl["profile"]
    lines.append("           profile: " + ("— (no diagnostic radical)" if profile is None else
                                           "none (the diagnostic radicals disagree)" if not profile else
                                           ", ".join(profile)))
    return lines


def render_sweep(report: dict[str, Any], rows: int) -> list[str]:
    """rows: ranked rows shown; 0 shows every row."""
    s = report["sweep"]
    rows = rows or len(report["results"])
    lines = [(f"sweep {s['source']} (sha256 {s['sha256'][:12]}): {s['listed']} listed, {s['skipped_gold']} gold-set "
              f"words skipped, {len(report['results'])} queried; index sha256 {s['index_sha256'][:12]}"),
             f"{'rank':>4}  {'word':<22} {'verdict':<17} {'p_max':>7} {'q':>7} {'d*':>5}  top cluster"]
    for i, r in enumerate(report["results"][:rows], 1):
        if "error" in r:
            lines.append(f"{i:>4}  {r['word']:<22} {r['error']}")
            continue
        b = r.get("best") or {}
        top = f"{b['number']} {b['key_form']} ({b['key_language']})" if b else "—"
        lines.append(f"{i:>4}  {r['word']:<22} {r['verdict']:<17} {_fmt(r['p_max']):>7} {_fmt(r.get('bh_q')):>7} "
                     f"{_fmt(r['d_star']):>5}  {top}")
    if len(report["results"]) > rows:
        lines.append(f"      … {len(report['results']) - rows} more (--top, or --json for all)")
    lines.append("Every result enters at SPECULATIVE.")
    return lines


def render(report: dict[str, Any], rows: int = 50) -> str:
    """rows: ranked rows shown for a sweep (--top)."""
    lines = [f"index {report['index']}" + ("" if report["index_checked"] else "  [UNCHECKED: stale inputs]"),
             f"key set {report['key_set']}; N={report['n']} per family; seed {report['seed']}"]
    if report.get("a4_absent"):
        lines.append(f"A4 lists Numbers the index no longer holds: {', '.join(report['a4_absent'])}")
    if report.get("gold_run"):
        lines.append("GOLD RUN: gold-set guard off (--gold-run)")
    if report.get("sweep"):
        return "\n".join(lines + render_sweep(report, rows))
    for r in report["results"]:
        lines.append("")
        if "error" in r:
            lines.append(f"{r['word']}: {r['error']}")
            continue
        q = f"  q={_fmt(r['bh_q'])}" if "bh_q" in r else ""
        lines.append(f"{r['word']}  skeleton {r['skeleton']} ({r['consonants']} consonants)  d*={_fmt(r['d_star'])}"
                     f"  {r['verdict']}  p_max={_fmt(r['p_max'])} ({r['deciding_family'] or '—'}){q}")
        for k, f in r["families"].items():
            extra = f"  {f['note']}" if f["note"] else ""
            lines.append(f"  {k}: n={f['n']} below={f['below']} tied={f['tied']} p={_fmt(f['p'])}"
                         f"{'' if f['in_p_max'] else ' (not in p_max)'}{extra}")
        if r["saturation"] is not None:
            lines.append(f"  saturation (B at d ≤ {rm.SATURATION_D}): {r['saturation']:.3f}")
        b = r.get("breadth") or {}
        if b:
            vs = b.get("decoys_B")
            versus = (f"; B decoys ≥ it: {vs['share_ge']:.3f} (gloss-free {vs['share_ge_gloss_free']:.3f})"
                      if vs else "")
            lines.append(f"  breadth {b['branches']} branches, gloss-free {b['gloss_free']}{versus}")
        lines.append(f"  uniqueness k(d*+{rm.UNIQUENESS_SLACK}) = {r['uniqueness']}")
        for name, c in (r.get("competitors") or {}).items():
            near = c.get("nearest") or {}
            lines.append(f"  competitor {name}: d*={_fmt(c['d_star'])} p_max={_fmt(c['p_max'])} "
                         f"({c['deciding_family'] or '—'})  nearest {near.get('key', '—')} {near.get('numbers', '')}")
        if r.get("competitors"):
            spec = {True: "yes", False: "no", None: "—"}[r["semitic_specific"]]
            lines.append(f"  competitor margin {_fmt(r['competitor_margin'])}; Semitic-specific: {spec}")
        lines.extend(_semantic_lines(r.get("semantic") or {}))
        for h in r["clusters"]:
            flags = f"  [{', '.join(h['flags'])}]" if h["flags"] else ""
            lines.append(f"    {h['number']:>6}  {_fmt(h['distance']):>5}  {h['key_form']} ({h['key_language']}, "
                         f"{h['key_kind']}; {h['variant_rule']})  {len(h['branches'])} br{flags}")
            if "record" in h:
                lines.extend(_explained(h))
        unlinked = r.get("unlinked", ())
        for lx in unlinked[:SHOWN]:
            lines.append(f"    unlinked {lx['id']} {lx['form'] or '—'} '{lx['meaning'] or ''}' d={_fmt(lx['distance'])}"
                         "  (no root link: never in d*)")
        if len(unlinked) > SHOWN:
            lines.append(f"    … {len(unlinked) - SHOWN} more unlinked lexemes at or under d*")
        for note in r["notes"]:
            lines.append(f"  note: {note}")
        lines.append(f"  {r['footer']}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("words", nargs="*")
    parser.add_argument("--file", help="one sign group per line")
    parser.add_argument("--n", type=int, default=rm.DEFAULT_N, help="decoys per family")
    parser.add_argument("--seed", type=int, default=rm.SEED)
    parser.add_argument("--families", default="ABC")
    parser.add_argument("--names", action="store_true", help="count onomastic lexemes (§1)")
    parser.add_argument("--full-index", action="store_true", help="secondary result: no A4 exclusions")
    parser.add_argument("--index", default=str(DEFAULT_INDEX))
    parser.add_argument("--allow-stale", action="store_true",
                        help="load a stale index anyway; every result is marked index_checked false")
    parser.add_argument("--top", type=int, default=10)
    parser.add_argument("--no-breadth", action="store_true", help="skip A12's exact breadth pass over family B")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--gold-run", action="store_true", help="lift the gold-set guard: the gold run only")
    parser.add_argument("--no-competitors", action="store_true", help="skip the competitor null (§2)")
    parser.add_argument("--explain", action="store_true",
                        help="per cluster: the record's reflexes with their citations, joined lexemes, possible "
                             "cognates, sound laws; per word: unlinked lexemes at or under d*")
    parser.add_argument("--sweep", choices=["unread"],
                        help="rank data/linear-a/unread_words.json by BH q, gold-set words skipped; --top = rows shown")
    parser.add_argument("--workers", type=int, default=1, help="processes (forked over one engine)")
    args = parser.parse_args(argv)
    words = list(args.words)
    if args.file:
        words += [ln.strip() for ln in Path(args.file).read_text(encoding="utf-8").splitlines() if ln.strip()]
    if args.sweep and words:
        parser.error("--sweep takes no sign groups and no --file")
    unread_sha = None
    if args.sweep:
        if not UNREAD.exists():
            print(f"stopped: {UNREAD.name} is not in this checkout", file=sys.stderr)
            return 5
        words, unread_sha = unread_words(UNREAD)
    given = {canonical(w): w.strip() for w in reversed(words)}      # canonical → as typed, for messages
    words = [c for c in map(canonical, words) if c]
    if not words:
        parser.error("no sign group given")
    if set(args.families) - set("ABC") or not args.families:
        parser.error("--families takes letters from ABC")
    if args.workers < 1:
        parser.error("--workers takes 1 or more")
    if args.top < 0:
        parser.error("--top takes 0 (every cluster, every sweep row) or more")
    listed = len(words)
    skipped: list[str] = []
    gold_sha = None
    if not args.gold_run:
        try:
            gold_bytes = GOLD.read_bytes()
            is_gold = gold_guard(GOLD)
        except (OSError, ValueError, UnicodeDecodeError) as e:
            print(f"gold set unreadable, so no word can be checked against it: {e}", file=sys.stderr)
            return 3
        gold_sha = hashlib.sha256(gold_bytes).hexdigest()
        hits = [w for w in words if is_gold(w)]      # by name or by reading (A14)
        if hits and args.sweep:                      # a sweep sets gold words aside and counts them
            skipped, words = hits, [w for w in words if not is_gold(w)]
        elif hits:
            print(f"refused, gold-set words before the gold run (§6): {', '.join(given[w] for w in hits)}\n"
                  "(--gold-run is for the gold run itself)", file=sys.stderr)
            return 3
    try:
        competitors = [] if args.no_competitors else competitor_spaces(args.names)
    except NotInCheckout as e:
        print(f"stopped: {e}; the competitor null (§2) reads it (--no-competitors runs without it)", file=sys.stderr)
        return 2
    index_path = Path(args.index)
    try:
        index_sha = _sha256(index_path)
        index = RootIndex.load(index_path, check_inputs=not args.allow_stale)
    except IndexStale as e:
        print(f"{e}\n(or pass --allow-stale to read it anyway, marked unchecked)", file=sys.stderr)
        return 2
    except OSError as e:
        print(f"index unreadable: {e}", file=sys.stderr)
        return 2
    if _sha256(index_path) != index_sha:
        print(f"{index_path} changed while it was loading; rerun on a frozen snapshot (§7.7)", file=sys.stderr)
        return 2
    try:
        exclusions = None if args.full_index else primary_exclusions()
    except (OSError, ValueError, UnicodeDecodeError) as e:
        print(f"no primary key set: {e} (--full-index gives the secondary result)", file=sys.stderr)
        return 3
    try:
        contexts, corpus_sha = corpus_contexts(CORPUS)
    except (OSError, ValueError, UnicodeDecodeError) as e:
        print(f"corpus unreadable, so the semantic gate has no contexts: {e}", file=sys.stderr)
        return 4
    try:
        report = run(words, index=index, exclusions=exclusions, n=args.n,
                     seed=args.seed, families=args.families, names=args.names, top=1 if args.sweep else args.top,
                     breadth=not args.no_breadth,
                     competitors=competitors,
                     explained=args.explain, workers=args.workers, contexts=contexts, index_sha=index_sha)
    except sg.TaggerChanged as e:
        print(f"semantic gate refused: {e}", file=sys.stderr)
        return 4
    except IndexChanged as e:
        print(str(e), file=sys.stderr)
        return 2
    report.update(gold_run=args.gold_run, index_sha256=index_sha, gold_sha256=gold_sha, corpus_sha256=corpus_sha,
                  tagger_sha256=sg.TAGGER_SHA256)
    if args.sweep:                                   # stamped with what it read (§7.1)
        report["results"] = ranked(report["results"])
        report["sweep"] = {"source": f"data/linear-a/{UNREAD.name}", "sha256": unread_sha,
                           "listed": listed, "skipped_gold": len(skipped), "index_sha256": index_sha,
                           "gold_sha256": gold_sha, "corpus_sha256": corpus_sha}
    print(json.dumps(report, ensure_ascii=False, indent=1) if args.json else render(report, args.top))
    return 1 if any("error" in r for r in report["results"]) else 0


if __name__ == "__main__":
    sys.exit(main())
