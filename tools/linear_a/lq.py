#!/usr/bin/env python3
"""lq — Linear A Query. Ad-hoc DuckDB SQL across all decipherment data files.

A view whose file is not in the checkout is left out; a query that uses it stops with the file's name (exit 2).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import duckdb
except ImportError:
    print("duckdb is not installed: install the sql extra (uv sync --extra sql)", file=sys.stderr)
    sys.exit(1)

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = "tools.linear_a"

from ..paths import CONTACT_DATA, LINEAR_A_DATA, SEMITIC_ROOTS_DATA, NotInCheckout, require

_corpus_cache: dict | None = None
_translations_cache: dict | None = None
_missing: dict[str, Path] = {}  # view or table name -> the file it would read, for each one left out


def _load_corpus() -> dict:
    global _corpus_cache
    if _corpus_cache is None:
        path = require(LINEAR_A_DATA / "corpus.json", "corpus.json")
        _corpus_cache = json.loads(path.read_text(encoding="utf-8"))
    return _corpus_cache


def _load_translations() -> dict:
    global _translations_cache
    if _translations_cache is None:
        path = require(LINEAR_A_DATA / "translations.json", "translations.json")
        raw = json.loads(path.read_text(encoding="utf-8"))
        _translations_cache = raw.get("translations", raw)
    return _translations_cache


# unread_words verdicts are read from the hand-written note. "Not readable" = signs illegible (lost, dotted, worn);
# "No reading." = legible, no reading survives; "Not a word" = segmentation artefact.
# Older notes end "Key K-R: no reading.", "name indexes match at chance." or
# "No name match (key …)."; these count as no_reading.
UNREAD_VERDICTS = ("no_reading", "not_readable", "not_a_word", "held", "other", "unreviewed")
_NOT_A_WORD = re.compile(r"\bNot a word\b")
_VERDICT_PHRASES = (
    ("not_readable", re.compile(r"\bNot readable\b")),
    ("no_reading", re.compile(r"\b[Nn]o reading\b|\bmatch at chance\b|\bNo name match\b")),
    ("held", re.compile(r"\bHeld\.")),
)


def classify_unread_note(note: str | None) -> str:
    """Verdict of an unread_words note: "Not a word" first, else the last verdict phrase."""
    if not note:
        return "unreviewed"
    if _NOT_A_WORD.search(note):
        return "not_a_word"
    verdict, last = "other", -1
    for name, pattern in _VERDICT_PHRASES:
        for m in pattern.finditer(note):
            if m.start() > last:
                verdict, last = name, m.start()
    return verdict


def unread_rows(entries: list[dict]) -> list[dict]:
    return [{
        "word": e["word"],
        "verdict": classify_unread_note(e.get("note")),
        "status": e.get("status"),
        "role": e.get("role"),
        "signs": e.get("signs"),
        "frequency": e.get("frequency"),
        "attestations": list(e.get("attestations") or []),
        "sites": list(e.get("sites") or []),
        "cross_site": e.get("cross_site"),
        "damaged": sorted(e.get("surface_damage") or {}),
        "note": e.get("note"),
    } for e in entries]


def _create_unread_table(con: duckdb.DuckDBPyConnection) -> None:
    # A table, not a view: the verdict is computed in Python from the note text.
    path = LINEAR_A_DATA / "unread_words.json"
    if not path.exists():
        _missing["unread"] = path
        return
    rows = unread_rows(json.loads(path.read_text(encoding="utf-8"))["entries"])
    con.execute("""
        CREATE TABLE unread (
            word VARCHAR, verdict VARCHAR, status VARCHAR, role VARCHAR, signs INTEGER,
            frequency INTEGER, attestations VARCHAR[], sites VARCHAR[], cross_site BOOLEAN,
            damaged VARCHAR[], note VARCHAR)
    """)
    if rows:
        cols = list(rows[0])
        con.executemany(f"INSERT INTO unread VALUES ({', '.join('?' * len(cols))})",
                        [[r[c] for c in cols] for r in rows])


# View name -> (file, how it is read). "entries" / "roots": a JSON object whose `entries` / `roots` array holds one
# row each; "object":
# the file is one JSON value; "lines": newline-delimited JSON. corpus.json and translations.json are dict-of-dicts,
# loaded in Python, not as views.
VIEWS: dict[str, tuple[Path, str]] = {
    "lexicon": (LINEAR_A_DATA / "lexicon.json", "entries"),
    "onomasticon": (LINEAR_A_DATA / "onomasticon.json", "entries"),
    "signs": (LINEAR_A_DATA / "sign_values.json", "object"),
    "semitic_roots": (SEMITIC_ROOTS_DATA / "semitic_roots.json", "roots"),
    "egyptian": (CONTACT_DATA / "egyptian_lexicon.jsonl", "lines"),
    "hurrian": (CONTACT_DATA / "hurrian_lexicon.jsonl", "lines"),
    "anatolian": (CONTACT_DATA / "anatolian_lexicon.jsonl", "lines"),
    "ugaritic": (CONTACT_DATA / "ugaritic_lexicon.jsonl", "lines"),
    "amorite": (CONTACT_DATA / "amorite_onomasticon.jsonl", "lines"),
    "hebrew": (CONTACT_DATA / "hebrew_lexicon.jsonl", "lines"),
    "aramaic": (CONTACT_DATA / "aramaic_lexicon.jsonl", "lines"),
    "geez": (CONTACT_DATA / "geez_lexicon.jsonl", "lines"),
    "south_arabian": (CONTACT_DATA / "south_arabian_lexicon.jsonl", "lines"),
}


def _create_views(con: duckdb.DuckDBPyConnection) -> None:
    for name, (path, form) in VIEWS.items():
        if not path.exists():
            _missing[name] = path
            continue
        quoted = str(path).replace("'", "''")
        if form in ("entries", "roots"):
            source = f"read_json_auto('{quoted}', maximum_object_size=104857600) j, UNNEST(j.{form}) AS t(e)"
        elif form == "object":
            source = f"read_json_auto('{quoted}', maximum_object_size=104857600)"
        else:
            source = f"read_json_auto('{quoted}', format='newline_delimited', maximum_object_size=104857600)"
        con.execute(f"CREATE VIEW {name} AS SELECT {'e.*' if form in ('entries', 'roots') else '*'} FROM {source}")


def _not_in_checkout(error: Exception) -> NotInCheckout | None:
    """The NotInCheckout for a catalog error on a view or table left out because its file is not here."""
    for name, path in _missing.items():
        if re.search(rf"\b{name}\b", str(error)):
            return NotInCheckout(f"{path.name} is not in this checkout (looked for {path}; the {name} view reads it)")
    return None


def _get_connection() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(":memory:")
    _create_views(con)
    _create_unread_table(con)
    return con


def _show(con: duckdb.DuckDBPyConnection, query: str, params=None, as_json: bool = False) -> None:
    try:
        if params:
            con.execute(query, params)
        else:
            con.execute(query)
    except duckdb.Error as e:
        missing = _not_in_checkout(e) if isinstance(e, duckdb.CatalogException) else None
        if missing:
            raise missing from None
        print(f"SQL error: {e}", file=sys.stderr)
        sys.exit(1)
    if con.description is None:
        print("(statement executed, no results)")
        return
    cols = [d[0] for d in con.description]
    rows = con.fetchall()
    if as_json:
        print(json.dumps([dict(zip(cols, row)) for row in rows], indent=2, default=str))
    elif not rows:
        print("(no results)")
    else:
        widths = [len(c) for c in cols]
        for row in rows:
            for i, val in enumerate(row):
                widths[i] = max(widths[i], min(len(str(val)), 60))
        hdr = " | ".join(c.ljust(widths[i]) for i, c in enumerate(cols))
        print(hdr)
        print("-+-".join("-" * w for w in widths))
        for row in rows:
            vals = []
            for i, val in enumerate(row):
                s = str(val) if val is not None else ""
                if len(s) > 60:
                    s = s[:57] + "..."
                vals.append(s.ljust(widths[i]))
            print(" | ".join(vals))
    return rows


def cmd_sql(args: argparse.Namespace) -> None:
    con = _get_connection()
    _show(con, args.query, as_json=args.json)


def cmd_word(args: argparse.Namespace) -> None:
    con = _get_connection()
    pattern = f"%{args.pattern}%"
    # corpus_forms holds raw corpus spellings of entries keyed by resolved readings
    # (JA-HA ← JA-*21F); linear_a_form holds the Linear A transposition of entries
    # keyed by Egyptian group-writing (YM'N ← JA-MI-NI). Columns exist only once
    # some entry carries them.
    lex_cols = {row[0] for row in con.execute("DESCRIBE lexicon").fetchall()}
    clauses = ["word ILIKE ?"]
    if "corpus_forms" in lex_cols:
        clauses.append("array_to_string(corpus_forms, ' ') ILIKE ?")
    if "linear_a_form" in lex_cols:
        clauses.append("linear_a_form ILIKE ?")
    _show(con, f"""
        SELECT word, reading, root, meaning, confidence, category, language_layer
        FROM lexicon WHERE {' OR '.join(clauses)} ORDER BY confidence, word
    """, [pattern] * len(clauses), as_json=args.json)
    if not args.json:
        print("\n--- Onomasticon ---")
    _show(con, """
        SELECT token, type, affiliation, reading, meaning, frequency
        FROM onomasticon WHERE token ILIKE ? ORDER BY frequency DESC
    """, [pattern], as_json=args.json)


def cmd_root(args: argparse.Namespace) -> None:
    con = _get_connection()
    pattern = f"%{args.root}%"
    _show(con, """
        SELECT word, reading, root, meaning, confidence, category
        FROM lexicon WHERE root ILIKE ? ORDER BY confidence, word
    """, [pattern], as_json=args.json)


def _iget(d: dict, key: str) -> tuple[str, dict] | tuple[None, None]:
    if key in d:
        return key, d[key]
    key_up = key.upper()
    for k, v in d.items():
        if k.upper() == key_up:
            return k, v
    return None, None


def cmd_inscription(args: argparse.Namespace) -> None:
    corpus = _load_corpus()
    _, corp = _iget(corpus, args.id)
    if corp:
        if args.json:
            print(json.dumps({k: corp.get(k) for k in ("name", "site", "support", "context", "transliteratedWords")}, indent=2, default=str))
        else:
            print(f"Corpus: {corp.get('name','')} | {corp.get('site','')} | {corp.get('support','')} | {corp.get('context','')}")
            print(f"Words:  {corp.get('transliteratedWords','')}")
    else:
        print(f"No corpus entry for {args.id}", file=sys.stderr)

    trans = _load_translations()
    _, entry = _iget(trans, args.id)
    if entry:
        t = entry.get("translation", "")
        c = entry.get("confidence", "")
        if args.json:
            print(json.dumps({"translation": t, "confidence": c}, indent=2, default=str))
        else:
            print(f"\nTranslation: {t}")
            print(f"Confidence:  {c}")
        if not args.json:
            for w in entry.get("words", []):
                print(f"  {w.get('linear_a',''):30s} → {w.get('gloss') or w.get('meaning', '')}")


def cmd_site(args: argparse.Namespace) -> None:
    corpus = _load_corpus()
    pattern = args.site.upper()
    hits: dict[str, list[str]] = {}
    for name, rec in corpus.items():
        site = rec.get("site", "")
        if pattern in name.upper() or pattern in site.upper():
            words = rec.get("transliteratedWords", [])
            if isinstance(words, list):
                for w in words:
                    if w and w not in ("\n", "𐄁") and "𐝫" not in w:
                        hits.setdefault(w, []).append(name)
    if not hits:
        print(f"No inscriptions matching site pattern '{args.site}'")
        return
    sorted_hits = sorted(hits.items(), key=lambda x: (-len(x[1]), x[0]))
    if args.json:
        print(json.dumps([{"word": w, "count": len(names), "inscriptions": names} for w, names in sorted_hits], indent=2))
    else:
        print(f"{'word':30s} | {'count':5s} | inscriptions")
        print("-" * 30 + "-+-" + "-" * 5 + "-+-" + "-" * 40)
        for w, names in sorted_hits[:50]:
            print(f"{w:30s} | {len(names):5d} | {', '.join(names[:5])}{'...' if len(names) > 5 else ''}")


TIER_MAP = {"CONFIRMED": 4, "PROBABLE": 3, "CANDIDATE": 2, "SPECULATIVE": 1, "REJECTED": 0}
TIER_NAMES = {v: k for k, v in TIER_MAP.items()}


def cmd_field(args: argparse.Namespace) -> None:
    con = _get_connection()
    tier_filter = ""
    params = [args.field]
    if args.tier is not None:
        tier_name = TIER_NAMES.get(args.tier, "")
        if not tier_name:
            print(f"Unknown tier {args.tier}. Use 0-4.", file=sys.stderr)
            sys.exit(1)
        tier_filter = " AND confidence = ?"
        params.append(tier_name)
    _show(con, f"""
        SELECT word, meaning, confidence, root, language_layer
        FROM lexicon WHERE semantic_field = ?{tier_filter}
        AND confidence != 'REJECTED'
        ORDER BY
            CASE confidence
                WHEN 'CONFIRMED' THEN 0 WHEN 'PROBABLE' THEN 1
                WHEN 'CANDIDATE' THEN 2 WHEN 'SPECULATIVE' THEN 3
            END, word
    """, params, as_json=args.json)


def cmd_tier(args: argparse.Namespace) -> None:
    con = _get_connection()
    tier_name = TIER_NAMES.get(args.tier, "")
    if not tier_name:
        print(f"Unknown tier {args.tier}. Use 0-4.", file=sys.stderr)
        sys.exit(1)
    field_filter = ""
    params = [tier_name]
    if args.field:
        field_filter = " AND semantic_field = ?"
        params.append(args.field)
    _show(con, f"""
        SELECT word, meaning, semantic_field, root, language_layer
        FROM lexicon WHERE confidence = ?{field_filter}
        ORDER BY semantic_field, word
    """, params, as_json=args.json)


def cmd_stats(args: argparse.Namespace) -> None:
    con = _get_connection()
    print("=== Entries by semantic field ===")
    _show(con, """
        SELECT semantic_field, COUNT(*) as count,
               ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) as pct
        FROM lexicon WHERE confidence != 'REJECTED'
        GROUP BY semantic_field ORDER BY count DESC
    """, as_json=args.json)
    print("\n=== Entries by confidence tier ===")
    _show(con, """
        SELECT confidence, COUNT(*) as count
        FROM lexicon WHERE confidence != 'REJECTED'
        GROUP BY confidence
        ORDER BY CASE confidence
            WHEN 'CONFIRMED' THEN 0 WHEN 'PROBABLE' THEN 1
            WHEN 'CANDIDATE' THEN 2 WHEN 'SPECULATIVE' THEN 3
        END
    """, as_json=args.json)
    print("\n=== Entries by language layer ===")
    _show(con, """
        SELECT language_layer, COUNT(*) as count
        FROM lexicon WHERE confidence != 'REJECTED'
        GROUP BY language_layer ORDER BY count DESC
    """, as_json=args.json)
    print("\n=== Field × Tier matrix ===")
    _show(con, """
        SELECT semantic_field,
               COUNT(*) FILTER (WHERE confidence = 'CONFIRMED') as C,
               COUNT(*) FILTER (WHERE confidence = 'PROBABLE') as P,
               COUNT(*) FILTER (WHERE confidence = 'CANDIDATE') as Ca,
               COUNT(*) FILTER (WHERE confidence = 'SPECULATIVE') as S,
               COUNT(*) as total
        FROM lexicon WHERE confidence != 'REJECTED'
        GROUP BY semantic_field ORDER BY total DESC
    """, as_json=args.json)


def cmd_audit(args: argparse.Namespace) -> None:
    con = _get_connection()
    print("=== Entries missing semantic_field ===")
    rows = _show(con, """
        SELECT word, meaning, confidence
        FROM lexicon WHERE confidence != 'REJECTED'
        AND (semantic_field IS NULL OR semantic_field = '')
        ORDER BY word
    """, as_json=args.json)
    if not rows:
        print("  ✓ All entries have semantic_field")
    print("\n=== Entries missing root ===")
    rows = _show(con, """
        SELECT word, meaning, confidence, semantic_field
        FROM lexicon WHERE confidence != 'REJECTED'
        AND (root IS NULL OR root = '')
        ORDER BY confidence, word
    """, as_json=args.json)
    print("\n=== Entries missing attestations ===")
    rows = _show(con, """
        SELECT word, meaning, confidence, semantic_field
        FROM lexicon WHERE confidence != 'REJECTED'
        AND (attestations IS NULL OR LEN(attestations) = 0)
        ORDER BY confidence, word
    """, as_json=args.json)


def cmd_xref(args: argparse.Namespace) -> None:
    con = _get_connection()
    word = args.word
    print(f"=== Cross-reference: {word} ===\n")

    lex = con.execute("""
        SELECT word, reading, root, meaning, confidence, category
        FROM lexicon WHERE word = ?
    """, [word]).fetchall()
    if lex:
        print("-- Lexicon --")
        for r in lex:
            print(f"  {r[0]:30s} {r[4]:12s} {r[3]}")

    ono = con.execute("""
        SELECT token, type, affiliation, reading, frequency
        FROM onomasticon WHERE token = ?
    """, [word]).fetchall()
    if ono:
        print("\n-- Onomasticon --")
        for r in ono:
            print(f"  {r[0]:30s} {r[1]:12s} aff={r[2]:10s} freq={r[4]}")

    corpus = _load_corpus()
    corp_hits = []
    for name, rec in corpus.items():
        words = rec.get("transliteratedWords", [])
        if isinstance(words, list) and word in words:
            corp_hits.append((name, rec.get("site", "")))
    if corp_hits:
        print(f"\n-- Corpus ({len(corp_hits)} inscriptions) --")
        for name, site in sorted(corp_hits):
            print(f"  {name:12s} {site}")


def cmd_unread(args: argparse.Namespace) -> None:
    con = _get_connection()
    clauses, params = [], []
    if args.verdict != "all":
        clauses.append("verdict = ?")
        params.append(args.verdict)
    if args.site:
        clauses.append("(array_to_string(sites, ' ') ILIKE ? OR array_to_string(attestations, ' ') ILIKE ?)")
        params += [f"%{args.site}%"] * 2
    if args.role:
        clauses.append("role = ?")
        params.append(args.role)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    cur = con.execute(f"SELECT * FROM unread {where} ORDER BY word", params)
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    if args.json:
        print(json.dumps(rows, indent=2, ensure_ascii=False, default=str))
        return
    counts = dict(con.execute("SELECT verdict, count(*) FROM unread GROUP BY verdict").fetchall())
    print(" | ".join(f"{v} {counts.get(v, 0)}" for v in UNREAD_VERDICTS))
    print(f"--- {len(rows)} shown ---\n")
    for r in rows:
        head = f"{r['word']}  [{r['verdict']}]  {r['role'] or r['status']}  {', '.join(r['attestations'])}"
        if r["damaged"]:
            head += f"  damaged: {', '.join(r['damaged'])}"
        print(head)
        if r["note"]:
            print(f"    {r['note']}")
        print()


def main():
    parser = argparse.ArgumentParser(
        prog="lq",
        description="Linear A Query — DuckDB SQL across decipherment data",
    )
    parser.add_argument("--json", action="store_true", help="JSON output")
    sub = parser.add_subparsers(dest="command")

    p_sql = sub.add_parser("sql", help="Raw SQL query")
    p_sql.add_argument("query", help="SQL query string")

    p_word = sub.add_parser("word", help="Lexicon + onomasticon lookup")
    p_word.add_argument("pattern", help="Word pattern (substring match)")

    p_root = sub.add_parser("root", help="All entries sharing a Semitic root")
    p_root.add_argument("root", help="Root pattern (e.g., 'k-n-s')")

    p_insc = sub.add_parser("inscription", help="Translation + corpus metadata")
    p_insc.add_argument("id", help="Inscription ID (e.g., HT1, APZa2)")

    p_site = sub.add_parser("site", help="All attestations from a site")
    p_site.add_argument("site", help="Site name or prefix (e.g., HT, APZ)")

    p_xref = sub.add_parser("xref", help="Cross-file join: lexicon ↔ translations ↔ onomasticon")
    p_xref.add_argument("word", help="Exact word token")

    p_field = sub.add_parser("field", help="Browse by semantic field")
    p_field.add_argument("field", help="Semantic field (e.g., divine, commodity, ritual)")
    p_field.add_argument("--tier", type=int, help="Filter by tier (0-4)")

    p_tier = sub.add_parser("tier", help="Browse by confidence tier")
    p_tier.add_argument("tier", type=int, help="Tier number (4=CONFIRMED, 3=PROBABLE, 2=CANDIDATE, 1=SPECULATIVE)")
    p_tier.add_argument("--field", help="Filter by semantic field")

    sub.add_parser("stats", help="Summary statistics")

    sub.add_parser("audit", help="Find entries with missing metadata")

    p_unread = sub.add_parser("unread", help="Unread words by verdict (default: no reading)")
    p_unread.add_argument("--verdict", choices=UNREAD_VERDICTS + ("all",), default="no_reading",
                          help="Verdict read from the note (default: no_reading)")
    p_unread.add_argument("--site", help="Site name or inscription substring (e.g., Zakros, HT21)")
    p_unread.add_argument("--role", help="Role (e.g., personal_name, toponym)")
    p_unread.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help="JSON output")

    known_cmds = {"sql", "word", "root", "inscription", "site", "xref", "field", "tier", "stats", "audit", "unread", "-h", "--help", "--json"}
    if len(sys.argv) > 1 and sys.argv[1] not in known_cmds:
        query_parts = [a for a in sys.argv[1:] if a != "--json"]
        args = argparse.Namespace(command="sql", query=" ".join(query_parts), json="--json" in sys.argv)
    else:
        args = parser.parse_args()
        if args.command is None:
            parser.print_help()
            sys.exit(0)

    dispatch = {
        "sql": cmd_sql,
        "word": cmd_word,
        "root": cmd_root,
        "inscription": cmd_inscription,
        "site": cmd_site,
        "xref": cmd_xref,
        "field": cmd_field,
        "tier": cmd_tier,
        "stats": cmd_stats,
        "audit": cmd_audit,
        "unread": cmd_unread,
    }
    try:
        dispatch[args.command](args)
    except duckdb.CatalogException as e:
        missing = _not_in_checkout(e)
        if missing is None:
            raise
        print(f"stopped: {missing}", file=sys.stderr)
        return 2
    except NotInCheckout as e:
        print(f"stopped: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
