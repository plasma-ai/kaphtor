#!/usr/bin/env python3
"""ANE query: DuckDB SQL across the ancient Near East corpora.

Two views read data this repository ships: `akkadian` (data/ane/akkadian_literary.jsonl, the ORACC CAMS/GKAB
glossary) and `egytext_docs` (data/share-alike/egyptian/egyptian_documents.jsonl, the ORAEC/TLA documents). Every
other view reads a corpus built locally under data/ (data/ingest/ for the raw and derived layers); a command whose
corpus is not in the checkout stops with exit 2 and names the path it looked for.

Views:
    akkadian         ORACC CAMS/GKAB literary glossary (lemmata)
    egytext_docs     ORAEC/TLA Egyptian documents
    egytext_sents    ORAEC/TLA sentences, German translations (data/share-alike/egyptian/)
    terms            data/ane/biblical-terms/*.json concordances, one row per occurrence
    quran            QAC morphology roots (data/share-alike/quran/quran_roots.jsonl)
    quran_text       ayahs (data/ane/quran_text.jsonl)
    epigraphy        data/ane/{arabian,south_arabian}_epigraphy.jsonl (OCIANA and DASI entries)
    aramaic          data/ane/aramaic_texts.jsonl (Biblical, Qumran, Targumic, Syriac passages)
    aramaic_tokens   annotated word rows from the ETCBC DSS and Targum sources
    cuneiform_docs   ORACC editions, CDLI ATF transcriptions and SEAL records (data/ingest/cuneiform/derived/)
    cuneiform_tokens token and lemma rows unnested from the annotated ORACC editions
    cdli_catalogue   CDLI object metadata, including objects without transcription
    seal             SEAL literary records (CC BY-NC-ND)
    seal_tokens      SEAL word spans with lemma, transliteration, meaning and line
    ociana           the official OCIANA Ancient North Arabian inscription export
    isicily          I.Sicily records whose main or other language is Punic, Phoenician or Hebrew
    ebl              eBL transliterated-fragment snapshot
    achemenet        Achaemenid Babylonian documents and automatic token analyses
    elisir           ELISIR pilot Eblaite lexical entries
    ugaritdb         Ugarit Texts Database catalogue metadata (not full texts)
    dapca            released DAPCA Late Bronze tablet editions; dapca_lines, dapca_tokens
    eupt             EUPT Ugaritic editions and annotations, by evidence layer
    oldassyrian      CDLI-derived Old Assyrian documents and words
    tlhdig           TLHdig Anatolian documents and word analyses, Hurrian included
    cypriot          IG XV 1 Cypriot-syllabic EpiDoc records
    dasi             the DASI OAI roster with derived EpiDoc and Dublin Core search fields
    ahi              Oxford Ancient Hebrew Inscriptions (AHI/AHI2) records
    hebrew           OSHB/WLC word morphology; hebrew_verses, the verse text

Usage:
    python3 tools/ane/aneq.py stats
    python3 tools/ane/aneq.py egytext oraec7
    python3 tools/ane/aneq.py egytext sinuhe
    python3 tools/ane/aneq.py egytext tribute --dynasty 18
    python3 tools/ane/aneq.py egytext kftjw --sentences
    python3 tools/ane/aneq.py sql "SELECT pos, count(*) FROM akkadian GROUP BY 1 ORDER BY 2 DESC"
    python3 tools/ane/aneq.py term tehom
    python3 tools/ane/aneq.py quran m-n-y
    python3 tools/ane/aneq.py quran 53:20
    python3 tools/ane/aneq.py epi mnt
    python3 tools/ane/aneq.py aramaic mlk
    python3 tools/ane/aneq.py aramaic mlk --tokens --corpus dss --preserved-only
    python3 tools/ane/aneq.py aramaic "Genesis 1:1" --corpus etcbc_targum_59_neofiti_base
    python3 tools/ane/aneq.py cuneiform P338317
    python3 tools/ane/aneq.py cuneiform šemû --tokens
    python3 tools/ane/aneq.py seal šēmû --tokens
    python3 tools/ane/aneq.py ociana 'l mnt' --script Safaitic
    python3 tools/ane/aneq.py isicily qbr --language xpu
    python3 tools/ane/aneq.py ebl 'ta-i' --period 'Old Babylonian'
    python3 tools/ane/aneq.py achemenet liq-bu-u₂
    python3 tools/ane/aneq.py elisir nab-ḫu
    python3 tools/ane/aneq.py ugaritdb 1.23 --language Ugaritic
    python3 tools/ane/aneq.py dapca 'ta-' --tokens
    python3 tools/ane/aneq.py eupt mlk --layer tokens
    python3 tools/ane/aneq.py oldassyrian ta-i --words --preserved-only
    python3 tools/ane/aneq.py tlhdig ta-i --words --language Hur --preserved-only
    python3 tools/ane/aneq.py cypriot Amathus --place Amathus
    python3 tools/ane/aneq.py dasi ṣdq --kind epi --language Sabaic
    python3 tools/ane/aneq.py dasi Tʾlb --field entities --site Riyām
    python3 tools/ane/aneq.py ahi brk
    python3 tools/ane/aneq.py ahi 4.122
    python3 tools/ane/aneq.py hebrew ברא
    python3 tools/ane/aneq.py hebrew Ruth.2.8 --verses

All subcommands accept --json.

Attribution: di Mino
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path

try:
    import duckdb
except ImportError:
    print("duckdb is not installed: install the sql extra (uv sync --extra sql)", file=sys.stderr)
    sys.exit(1)

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = "tools.ane"

from ..paths import ANE_DATA, DATA, REPO, SHARE_ALIKE, NotInCheckout, require
from .ane_keys import HEB_ROMAN, expand, fold_pattern, loose_key, parse_query

INGEST = DATA / "ingest"
TERMS_GLOB = ANE_DATA / "biblical-terms" / "*.json"
AKKADIAN = ANE_DATA / "akkadian_literary.jsonl"
QURAN_ROOTS = SHARE_ALIKE / "quran" / "quran_roots.jsonl"
QURAN_TEXT = ANE_DATA / "quran_text.jsonl"
EPIGRAPHY = [ANE_DATA / "arabian_epigraphy.jsonl", ANE_DATA / "south_arabian_epigraphy.jsonl"]
ARAMAIC = ANE_DATA / "aramaic_texts.jsonl"
ARAMAIC_MANIFEST = ANE_DATA / "aramaic_texts.manifest.json"
ARAMAIC_DB = ANE_DATA / "aramaic_texts.duckdb"
EGY_DOCS = SHARE_ALIKE / "egyptian" / "egyptian_documents.jsonl"
EGY_SENTS = SHARE_ALIKE / "egyptian" / "egyptian_sentences.jsonl"
CUNEIFORM_DERIVED = INGEST / "cuneiform" / "derived"
ORACC_DOCS = CUNEIFORM_DERIVED / "oracc_documents.jsonl"
CDLI_TEXTS = CUNEIFORM_DERIVED / "cdli_texts.jsonl"
CDLI_CATALOGUE = CUNEIFORM_DERIVED / "cdli_catalogue.jsonl"
SEAL_RECORDS = CUNEIFORM_DERIVED / "seal_records.jsonl"
OPEN_SEMITIC = INGEST / "open-semitic"
OCIANA_FULL = OPEN_SEMITIC / "derived/ociana/records.jsonl"
ISICILY_SEMITIC = OPEN_SEMITIC / "derived/isicily-semitic/records.jsonl"
EBL_FRAGMENTS = OPEN_SEMITIC / "derived/ebl-fragments/records.jsonl"
ACHEMENET_RECORDS = OPEN_SEMITIC / "derived/achemenet-babylonian/records.jsonl"
ELISIR_RECORDS = OPEN_SEMITIC / "derived/elisir-eblaite-lexicon/records.jsonl"
UGARITDB_RECORDS = OPEN_SEMITIC / "ugarit-texts-database/derived/records.jsonl"
DAPCA_RECORDS = OPEN_SEMITIC / "dapca/records.jsonl"
AHI_RECORDS = OPEN_SEMITIC / "ancient-hebrew-inscriptions/derived/records.jsonl"
EUPT_DERIVED = OPEN_SEMITIC / "eupt-production/derived"
EUPT_DOCUMENTS = EUPT_DERIVED / "documents.jsonl"
EUPT_LINES = EUPT_DERIVED / "facsimile_lines.jsonl"
EUPT_UNITS = EUPT_DERIVED / "philology_units.jsonl"
EUPT_TOKENS = EUPT_DERIVED / "tokens.jsonl"
EUPT_ANNOTATIONS = EUPT_DERIVED / "annotations.jsonl"
HEBREW_DERIVED = INGEST / "hebrew/derived"
HEBREW_WORDS = HEBREW_DERIVED / "oshb_words.jsonl"
HEBREW_VERSES = HEBREW_DERIVED / "oshb_verses.jsonl"
HEBREW_ROOTS = HEBREW_DERIVED / "oshb_lemma_roots.jsonl"
OLD_ASSYRIAN_DERIVED = OPEN_SEMITIC / "old-assyrian/derived"
OLD_ASSYRIAN_DOCS = OLD_ASSYRIAN_DERIVED / "documents.jsonl"
OLD_ASSYRIAN_WORDS = OLD_ASSYRIAN_DERIVED / "words.jsonl"
TLHDIG_DERIVED = INGEST / "anatolian/tlhdig-0.3/derived"
TLHDIG_DOCS = TLHDIG_DERIVED / "documents.jsonl"
TLHDIG_WORDS = TLHDIG_DERIVED / "words.jsonl"
CYPRIOT_DERIVED = INGEST / "aegean/cypriot-syllabic-ig-xv-1/derived"
CYPRIOT_RECORDS = CYPRIOT_DERIVED / "records.jsonl"
DASI_RECORDS = OPEN_SEMITIC / "dasi-csai/derived/records.jsonl"

MAX_OBJ = "maximum_object_size=104857600"


# --json provenance: the files the last get_connection opened, and how each is identified. Files up to
# SHA_LIMIT bytes carry their sha256; larger ones (the Hebrew words, DASI, the Aramaic cache) size and mtime,
# since hashing them would cost seconds a call.
OPENED: list[str] = []
SHA_LIMIT = 25_000_000
PROVENANCE: dict | None = None
# View name -> the file or files it would read, for each view left out because they are not in the checkout.
MISSING: dict[str, str] = {}


class OpenedFiles:
    """Forwards to a DuckDB connection and notes each absolute path a statement quotes (CREATE VIEW, ATTACH)."""

    def __init__(self, con):
        self.con, self.paths = con, []

    def execute(self, sql, *args):
        self.paths += [p for p in re.findall(r"'(/[^']*)'", sql) if p not in self.paths]
        return self.con.execute(sql, *args)

    def __getattr__(self, name):
        return getattr(self.con, name)


def shown(path: Path) -> str:
    """A path as provenance gives it: relative to the repository when inside it."""
    return str(path.relative_to(REPO)) if path.is_relative_to(REPO) else str(path)


def provenance(query: str | None) -> dict:
    """The files OPENED (globs expanded), each with bytes, mtime and, when small enough, sha256; and the query
    as typed, normalised and in its mode."""
    files = []
    for p in OPENED:
        path = Path(p)
        for f in sorted(path.parent.glob(path.name)) if any(c in path.name for c in "*?[") else [path]:
            st = f.stat()
            entry = {"file": shown(f), "bytes": st.st_size, "mtime": int(st.st_mtime)}
            if st.st_size <= SHA_LIMIT:
                entry["sha256"] = hashlib.sha256(f.read_bytes()).hexdigest()
            files.append(entry)
    out = {"files": files}
    if query:
        parsed = parse_query(query)
        out["query"] = {"typed": query, "normalized": parsed.text, "mode": parsed.mode}
    return out


def quoted(path: Path) -> str:
    """A path as an SQL string literal."""
    return "'" + str(path).replace("'", "''") + "'"


def left_out(views: tuple[str, ...], *paths: Path) -> None:
    """Note views whose files are not in the checkout, so a query that names one can say so."""
    for view in views:
        MISSING[view] = ", ".join(map(str, paths))


def jsonl_view(con, view: str, path: Path, *derived: str) -> bool:
    """CREATE VIEW `view` over the JSONL at `path`; when the file is absent, the view and the views `derived`
    from it are left out."""
    if not path.exists():
        left_out((view, *derived), path)
        return False
    con.execute(f"""
        CREATE VIEW {view} AS
        SELECT * FROM read_json_auto({quoted(path)}, format='newline_delimited',
                                     union_by_name=true, {MAX_OBJ})
    """)
    return True


def get_connection(cmd: str | None = None) -> duckdb.DuckDBPyConnection:
    global OPENED
    con = OpenedFiles(duckdb.connect(":memory:"))
    # DuckDB 2.0 refuses the arrow lambda (k -> ...); refusing it here too keeps 1.x runs honest.
    con.execute("SET lambda_syntax = 'DISABLE_SINGLE_ARROW'")
    OPENED = con.paths

    def need(*names):
        return cmd is None or cmd in names or cmd in {"sql", "stats"}

    if need("term"):
        if list(TERMS_GLOB.parent.glob(TERMS_GLOB.name)):
            con.execute(f"""
                CREATE VIEW terms AS
                SELECT j.term, j.transliteration, j.root,
                       sc.category AS category, occ.reference AS reference,
                       occ.hebrew AS hebrew, occ.context AS context
                FROM read_json_auto({quoted(TERMS_GLOB)}, union_by_name=true, {MAX_OBJ}) j,
                UNNEST(j.semantic_categories) AS c(sc),
                UNNEST(c.sc.occurrences) AS o(occ)
            """)
        else:
            left_out(("terms",), TERMS_GLOB)
    if need("akkadian"):
        jsonl_view(con, "akkadian", AKKADIAN)
    if need("quran"):
        jsonl_view(con, "quran", QURAN_ROOTS)
        jsonl_view(con, "quran_text", QURAN_TEXT)
    if need("epi"):
        epi_files = [p for p in EPIGRAPHY if p.exists()]
        if epi_files:
            paths = ", ".join(quoted(p) for p in epi_files)
            con.execute(f"""
                CREATE VIEW epigraphy AS
                SELECT * FROM read_json_auto([{paths}], format='newline_delimited',
                                             union_by_name=true, {MAX_OBJ})
            """)
        else:
            left_out(("epigraphy",), *EPIGRAPHY)
    if need("aramaic"):
        if not ARAMAIC.exists():
            left_out(("aramaic", "aramaic_tokens"), ARAMAIC)
        else:
            use_cache = False
            if ARAMAIC_DB.exists() and ARAMAIC_MANIFEST.exists():
                manifest = json.loads(ARAMAIC_MANIFEST.read_text(encoding="utf-8"))
                expected_json_hash = manifest.get("sha256")
                con.execute(f"ATTACH {quoted(ARAMAIC_DB)} AS aramaic_cache (READ_ONLY)")
                cached_json_hash = con.execute(
                    "SELECT value FROM aramaic_cache.metadata WHERE key='json_sha256'"
                ).fetchone()
                use_cache = bool(cached_json_hash and cached_json_hash[0] == expected_json_hash)
                if not use_cache:
                    con.execute("DETACH aramaic_cache")
            if use_cache:
                con.execute("CREATE VIEW aramaic AS SELECT * FROM aramaic_cache.aramaic")
                con.execute("CREATE VIEW aramaic_tokens AS SELECT * FROM aramaic_cache.aramaic_tokens")
            else:
                jsonl_view(con, "aramaic", ARAMAIC)
                con.execute("""
                    CREATE VIEW aramaic_tokens AS
                    SELECT a.id AS passage_id, a.corpus_id, a.source_corpus,
                           a.dialect, a.period, a.reference,
                           COALESCE(
                             trim(both '"' from CAST(token.node AS VARCHAR)),
                             trim(both '"' from CAST(token.index AS VARCHAR))
                           ) AS node,
                           trim(both '"' from CAST(token.surface AS VARCHAR)) AS surface,
                           trim(both '"' from CAST(token.consonantal AS VARCHAR)) AS consonantal,
                           trim(both '"' from CAST(token.normalized AS VARCHAR)) AS normalized,
                           trim(both '"' from CAST(token.normalized_ascii AS VARCHAR)) AS normalized_ascii,
                           trim(both '"' from CAST(token.lexeme AS VARCHAR)) AS lexeme,
                           trim(both '"' from CAST(token.root AS VARCHAR)) AS root,
                           trim(both '"' from CAST(token.root_normalized AS VARCHAR)) AS root_normalized,
                           trim(both '"' from CAST(token.gloss AS VARCHAR)) AS gloss,
                           trim(both '"' from CAST(token.part_of_speech AS VARCHAR)) AS part_of_speech,
                           trim(both '"' from CAST(token.gender AS VARCHAR)) AS gender,
                           trim(both '"' from CAST(token.number AS VARCHAR)) AS number,
                           trim(both '"' from CAST(token.state AS VARCHAR)) AS state,
                           trim(both '"' from CAST(token.verbal_stem AS VARCHAR)) AS verbal_stem,
                           trim(both '"' from CAST(token.language AS VARCHAR)) AS automatic_language,
                           TRY_CAST(token.model_score_aramaic AS DOUBLE) AS model_score_aramaic,
                           trim(both '"' from CAST(token.classification_method AS VARCHAR)) AS classification_method,
                           TRY_CAST(token.preservation_affected AS BOOLEAN) AS preservation_affected,
                           TRY_CAST(token.preserved AS BOOLEAN) AS preserved,
                           TRY_CAST(token.reconstructed AS BOOLEAN) AS reconstructed,
                           TRY_CAST(token.uncertainty_max AS INTEGER) AS uncertainty_max,
                           TRY_CAST(token.missing_sign_count AS INTEGER) AS missing_sign_count,
                           trim(both '"' from CAST(token.surface_original AS VARCHAR)) AS surface_original
                    FROM aramaic a, UNNEST(a.tokens) AS u(token)
                """)
    if need("egytext"):
        jsonl_view(con, "egytext_docs", EGY_DOCS)
        jsonl_view(con, "egytext_sents", EGY_SENTS)
    if need("cuneiform", "seal"):
        if jsonl_view(con, "cuneiform_oracc", ORACC_DOCS, "cuneiform_tokens"):
            con.execute("""
                CREATE VIEW cuneiform_tokens AS
                SELECT d.id AS document_id, d.canonical_id, d.source_project,
                       d.designation, d.period, d.provenience, d.genre,
                       token.ref AS token_ref, token.frag, token.form, token.norm,
                       token.cf, token.gw, token.sense, token.pos, token.epos,
                       token.lang, token.damaged
                FROM cuneiform_oracc d, UNNEST(d.tokens) AS u(token)
            """)
        jsonl_view(con, "cuneiform_cdli_texts", CDLI_TEXTS)
        jsonl_view(con, "cdli_catalogue", CDLI_CATALOGUE)
        if jsonl_view(con, "seal", SEAL_RECORDS, "seal_tokens"):
            con.execute("""
                CREATE VIEW seal_tokens AS
                SELECT d.id AS document_id, d.canonical_id AS seal_no,
                       d.designation, d.tablet_siglum, d.text_status,
                       token.line, token.transliteration, token.lemma,
                       token.meaning, token.surface
                FROM seal d, UNNEST(d.tokens) AS u(token)
            """)
    if need("ociana"):
        jsonl_view(con, "ociana", OCIANA_FULL)
    if need("isicily"):
        jsonl_view(con, "isicily", ISICILY_SEMITIC)
    if need("ebl"):
        jsonl_view(con, "ebl", EBL_FRAGMENTS)
    if need("achemenet") and jsonl_view(con, "achemenet", ACHEMENET_RECORDS, "achemenet_tokens"):
        con.execute("""
            CREATE VIEW achemenet_tokens AS
            SELECT d.id AS document_id, d.canonical_id, d.collection,
                   d.citation, d.document_order, token.*
            FROM achemenet d, UNNEST(d.tokens) AS u(token)
        """)
    if need("elisir"):
        jsonl_view(con, "elisir", ELISIR_RECORDS)
    if need("ugaritdb"):
        jsonl_view(con, "ugaritdb", UGARITDB_RECORDS)
    if need("dapca") and jsonl_view(con, "dapca", DAPCA_RECORDS, "dapca_lines", "dapca_tokens"):
        con.execute("""
            CREATE VIEW dapca_lines AS
            SELECT d.id AS document_id, d.tablet_id,
                   d.metadata.tablet AS tablet, d.metadata.inventory AS inventory,
                   d.metadata.site_ancient AS site, d.metadata.language AS language,
                   d.metadata.genre AS genre, d.metadata.subtype AS subtype,
                   line.face, line.label, line.text, line.tokens
            FROM dapca d, UNNEST(d.lines) AS u(line)
        """)
        con.execute("""
            CREATE VIEW dapca_tokens AS
            SELECT document_id, tablet_id, tablet, inventory, site, language,
                   genre, subtype, face, label,
                   token.word_id, token.lemma_id, token.named_lemma_id,
                   token.word_class, token.surface
            FROM dapca_lines, UNNEST(tokens) AS u(token)
        """)
    if need("ahi"):
        jsonl_view(con, "ahi", AHI_RECORDS)
    if need("eupt"):
        eupt = (("eupt_documents", EUPT_DOCUMENTS), ("eupt_lines", EUPT_LINES), ("eupt_units", EUPT_UNITS),
                ("eupt_tokens", EUPT_TOKENS), ("eupt_annotations", EUPT_ANNOTATIONS))
        if all(path.exists() for _, path in eupt):
            for view, path in eupt:
                jsonl_view(con, view, path)
        else:
            left_out(tuple(view for view, _ in eupt), *(path for _, path in eupt if not path.exists()))
    if need("hebrew"):
        jsonl_view(con, "hebrew", HEBREW_WORDS)
        jsonl_view(con, "hebrew_verses", HEBREW_VERSES)
    if need("oldassyrian"):
        if OLD_ASSYRIAN_DOCS.exists() and OLD_ASSYRIAN_WORDS.exists():
            jsonl_view(con, "old_assyrian_documents", OLD_ASSYRIAN_DOCS)
            jsonl_view(con, "old_assyrian_words", OLD_ASSYRIAN_WORDS)
        else:
            left_out(("old_assyrian_documents", "old_assyrian_words"), OLD_ASSYRIAN_DOCS, OLD_ASSYRIAN_WORDS)
    if need("tlhdig"):
        if TLHDIG_DOCS.exists() and TLHDIG_WORDS.exists():
            jsonl_view(con, "tlhdig_documents", TLHDIG_DOCS)
            jsonl_view(con, "tlhdig_words", TLHDIG_WORDS)
        else:
            left_out(("tlhdig_documents", "tlhdig_words"), TLHDIG_DOCS, TLHDIG_WORDS)
    if need("cypriot"):
        jsonl_view(con, "cypriot_syllabic", CYPRIOT_RECORDS)
    if need("dasi"):
        jsonl_view(con, "dasi", DASI_RECORDS)
    if need("cuneiform", "seal"):
        branches: list[str] = []
        if ORACC_DOCS.exists():
            branches.append("""
                SELECT id, canonical_id, source_family, source_project,
                       designation, language, period, provenience, genre, subgenre,
                       transliteration, token_count, source_url, license, license_url,
                       review_status
                FROM cuneiform_oracc
            """)
        if CDLI_TEXTS.exists():
            if CDLI_CATALOGUE.exists():
                branches.append("""
                    SELECT t.id, t.canonical_id, t.source_family,
                           NULLIF(trim(both '"' from CAST(t.source_project AS VARCHAR)), 'null'),
                           COALESCE(t.designation, c.designation),
                           COALESCE(c.language, t.language_code), c.period,
                           c.provenience, c.genre, NULL,
                           t.transliteration, NULL, t.source_url,
                           'CDLI Terms of Use', 'https://cdli.earth/terms-of-use',
                           t.review_status
                    FROM cuneiform_cdli_texts t
                    LEFT JOIN cdli_catalogue c USING (canonical_id)
                """)
            else:
                branches.append("""
                    SELECT id, canonical_id, source_family,
                           NULLIF(trim(both '"' from CAST(source_project AS VARCHAR)), 'null'),
                           designation, language_code, NULL, NULL, NULL, NULL,
                           transliteration, NULL, source_url,
                           'CDLI Terms of Use', 'https://cdli.earth/terms-of-use',
                           review_status
                    FROM cuneiform_cdli_texts
                """)
        if SEAL_RECORDS.exists():
            branches.append("""
                SELECT id, canonical_id, source_family, source_project,
                       designation, 'Akkadian', NULL, NULL, 'Literary', NULL,
                       transliteration, token_count, source_url, license, license_url,
                       review_status
                FROM seal
            """)
        if branches:
            con.execute("CREATE VIEW cuneiform_docs AS " + " UNION ALL ".join(branches))
        else:
            left_out(("cuneiform_docs",), ORACC_DOCS, CDLI_TEXTS, SEAL_RECORDS)
    return con.con


def require_any(paths: list[Path], dataset: str) -> None:
    """NotInCheckout naming every path when none of them exists."""
    if not any(p.exists() for p in paths):
        raise NotInCheckout(f"{dataset} is not in this checkout (looked for {', '.join(map(str, paths))})")


def run(con, query: str, as_json: bool):
    show(*fetch(con, query), as_json)


def run_folding(con, build, as_json: bool, loose: bool):
    """`build(folded)` gives the query with or without its folded tier. The folded tier joins when
    --loose asks for it, or when nothing matches strictly as a whole form (as query_proper_names has it):
    as typed, in notation, or in a spelling the view stores folded. A substring or gloss match alone leaves
    room for a folded name above it."""
    query = build(loose)
    cols, rows = fetch(con, query)
    at = cols.index("match_basis") if "match_basis" in cols else None
    whole = any(r[at] <= FOLDED for r in rows) if at is not None else bool(rows)
    if not whole and not loose and build(True) != query:
        cols, rows = fetch(con, build(True))
    show(cols, rows, as_json)


def fetch(con, query: str):
    try:
        result = con.execute(query)
    except duckdb.CatalogException as e:
        # A view left out because its file is not here: name the file.
        for view, paths in MISSING.items():
            if re.search(rf"\b{view}\b", str(e)):
                raise NotInCheckout(f"{view} is not in this checkout (looked for {paths})") from None
        print(f"SQL error: {e}", file=sys.stderr)
        sys.exit(1)
    except duckdb.Error as e:
        print(f"SQL error: {e}", file=sys.stderr)
        sys.exit(1)
    cols = [d[0] for d in result.description]
    rows = result.fetchall()
    limit = LIMIT_CLAUSE.search(query)
    if limit and len(rows) == int(limit.group(1)):
        total = con.execute(f"SELECT count(*) FROM ({query[:limit.start()]})").fetchone()[0]
        if total > len(rows):
            print(f"showing {len(rows)} of {total}", file=sys.stderr)
    return cols, rows


def show(cols, rows, as_json: bool):
    if as_json:
        extra = {"provenance": PROVENANCE} if PROVENANCE else {}
        json.dump([dict(zip(cols, r)) | extra for r in rows], sys.stdout,
                  ensure_ascii=False, indent=2, default=str)
        print()
        return
    if not rows:
        print("(no results)")
        return
    widths = [max(len(str(c)), max((len(str(r[i])[:60]) for r in rows), default=0))
              for i, c in enumerate(cols)]
    print(" | ".join(str(c).ljust(w) for c, w in zip(cols, widths)))
    print("-+-".join("-" * w for w in widths))
    for r in rows:
        print(" | ".join(str(v)[:60].replace("\n", " ").ljust(w) for v, w in zip(r, widths)))


def esc(s: str) -> str:
    """Escape for interpolation inside a LIKE pattern (paired with ESCAPE '\\')."""
    return (s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            .replace("'", "''"))


def sql_string(value: str) -> str:
    """A plainly quoted string literal, for = and list_contains (never LIKE)."""
    return "'" + value.replace("'", "''") + "'"


def sql_strings(values) -> str:
    """A VARCHAR[] literal of plainly quoted strings, for = / list_contains / list_has_any (never LIKE)."""
    return "[" + ", ".join("'" + v.replace("'", "''") + "'" for v in sorted(values)) + "]::VARCHAR[]"


def view_keys(query: str, view: str) -> str:
    """The query spelled in every notation `view` stores (ane_keys), as a VARCHAR[] literal."""
    return sql_strings(expand(parse_query(query), view))


def contains_any(field: str, keys: str) -> str:
    """True when `field` holds any of `keys` (a view_keys literal) as a substring; no LIKE wildcards."""
    return f"coalesce(list_bool_or(list_transform({keys}, lambda k: contains({field}, k))), FALSE)"


REGEX_META = re.compile(r"([.^$*+?()\[\]{}|\\])")


def gloss_hit(field: str, query: str, prefix: bool = False) -> str:
    """True when `field` holds the query as a whole word, an English plural allowed (king, kings); with
    `prefix`, as the start of a word (German compounds: König, Königssohn). A word edge is any non-letter, so
    mn is not found inside COLUMNS or ṯmn. A root-mode query (m-n-y, √mny) never matches a gloss."""
    if parse_query(query).mode == "root":
        return "FALSE"
    word = REGEX_META.sub(r"\\\1", unicodedata.normalize("NFC", query).strip().lower())
    tail = "" if prefix else r"(e?s)?([^\p{L}]|$)"
    pattern = sql_string(r"(^|[^\p{L}])" + word + tail)
    return f"regexp_matches(lower({field}), {pattern})"


FINAL_FORMS = str.maketrans("ךםןףץ", "כמנפצ")
# A typed radical as the Hebrew letter it writes. ש is š and ś alike: the table's roots are compared unpointed.
HEBREW_LETTER = {**{latin: letter for letter, latin in HEB_ROMAN.items() if letter not in "ךםןףץ"},
                 "ʾ": "א", "ʿ": "ע", "ś": "ש", "s1": "ש", "s2": "ש", "s3": "ס"}


def hebrew_root_lemmas(query: str) -> list[str]:
    """OSHB main lemmas whose BDB root in oshb_lemma_roots.jsonl has the query's radicals, typed in Hebrew
    letters (points and final forms ignored) or transliterated."""
    letters = "".join(
        unicodedata.normalize("NFD", u)[0] if "א" <= unicodedata.normalize("NFD", u)[0] <= "ת"
        else HEBREW_LETTER.get(u, u)
        for u in parse_query(query).radicals).translate(FINAL_FORMS)
    with HEBREW_ROOTS.open(encoding="utf-8") as stream:
        rows = (json.loads(line) for line in stream if line.strip())
        return [r["lemma"] for r in rows
                if r["root_consonantal"] and r["root_consonantal"].translate(FINAL_FORMS) == letters]


def plain_query(query: str) -> str:
    """The query composed (NFC) and without the root sign, for fields searched as typed."""
    return unicodedata.normalize("NFC", query).replace("√", "")


LIMIT_CLAUSE = re.compile(r"\s+LIMIT\s+(\d+)\s*$")

# Match basis, ranked: how a row matched the query, closest first. 4 is a substring of a form or an element
# of a name. Text views (ahi, dasi, Hebrew verses) search substrings throughout, so there the tier says how
# the query's spelling matched: as typed, in the view's notation, or folded. Bases 3 and 6 belong to views that
# are not in this repository; the numbers are kept so the others keep their meaning.
EXACT, NOTATION, FOLDED, SUBSTRING, GLOSS = 0, 1, 2, 4, 5


def sql_loose(field: str) -> str:
    """ane_keys.loose_key in SQL, for stored values: the same fold, without a Python call per row (the two must
    agree on every view's stored keys)."""
    return (f"regexp_replace(regexp_replace(regexp_replace(lower(strip_accents({field})), "
            f"'s[123¹²³₁₂₃]', 's', 'g'), '[ʾʔʼʿʕ‘`ᶜ''’]', '''', 'g'), '[-. ⸗=^:√*]', '', 'g')")


def sql_marks_kept(field: str) -> str:
    """ane_keys.marks_kept in SQL (the two must agree on every view's stored keys)."""
    return (f"regexp_replace(regexp_replace(regexp_replace(lower({field}), "
            f"'s[123¹²³₁₂₃]', 's', 'g'), '[ʾʔʼʿʕ‘`ᶜ''’]', '''', 'g'), '[-. ⸗=^:√*]', '', 'g')")


def loose_query(query: str) -> tuple[str, str] | None:
    """The query's folded key and fold pattern as SQL literals, or None when nothing is left to fold."""
    key = loose_key(query)
    return (sql_string(key), sql_string(fold_pattern(query))) if key else None


def text_query(query: str) -> tuple[str, str] | None:
    """loose_query for running text, searched with its word breaks written | (text_words): each word of the
    query folded on its own and the words joined by |, so no match spans two words."""
    words = query.split()
    keys = [loose_key(w) for w in words]
    if not words or not all(keys):
        return None
    return sql_string("|".join(keys)), sql_string(r"\|".join(fold_pattern(w) for w in words))


def text_words(field: str) -> str:
    """`field` with each run of whitespace written | (DASI's own line divider), which the fold keeps."""
    return f"regexp_replace({field}, '\\s+', '|', 'g')"


def folded_field(field: str, lq: tuple[str, str]) -> str:
    """True when `field` folds to the query's key and keeps every mark the query was typed with (the
    equality is the cheap test; the pattern refuses mwṯ for mwt)."""
    return f"({sql_loose(field)} = {lq[0]} AND regexp_full_match({sql_marks_kept(field)}, {lq[1]}))"


def folded_keys_hold(lq: tuple[str, str]) -> str:
    """True when one of the row's match_keys passes folded_field."""
    return f"len(list_filter(match_keys, lambda k: {folded_field('k', lq)})) > 0"


def matched(tiers: list[tuple[int, str]], fold: str | None = None) -> tuple[str, str]:
    """For (tier, condition) pairs, plus the folded condition when given: the WHERE condition (any holds)
    and the match_basis column (the lowest tier that holds)."""
    ordered = sorted(tiers + ([(FOLDED, fold)] if fold else []), key=lambda t: t[0])
    where = "(" + " OR ".join(f"({c})" for _, c in ordered) + ")"
    column = "CASE " + " ".join(f"WHEN {c} THEN {n}" for n, c in ordered) + " END AS match_basis"
    return where, column


# stats: (label, view, count expression, condition) for each row, given when its view exists.
STATS = (
    ("terms (occurrences)", "terms", "count(*)", ""),
    ("terms (distinct)", "terms", "count(DISTINCT transliteration)", ""),
    ("akkadian", "akkadian", "count(*)", ""),
    ("quran (roots)", "quran", "count(*)", ""),
    ("quran_text (ayahs)", "quran_text", "count(*)", ""),
    ("epigraphy (inscriptions)", "epigraphy", "count(*)", ""),
    ("aramaic (passages)", "aramaic", "count(*)", ""),
    ("aramaic (structured token rows)", "aramaic_tokens", "count(*)", ""),
    ("egytext (documents)", "egytext_docs", "count(*)", ""),
    ("egytext (sentences)", "egytext_sents", "count(*)", ""),
    ("cuneiform (ORACC editions)", "cuneiform_oracc", "count(*)", ""),
    ("cuneiform (ORACC tokens)", "cuneiform_tokens", "count(*)", ""),
    ("cuneiform (CDLI texts)", "cuneiform_cdli_texts", "count(*)", ""),
    ("cuneiform (CDLI catalogue)", "cdli_catalogue", "count(*)", ""),
    ("cuneiform (SEAL records)", "seal", "count(*)", ""),
    ("cuneiform (SEAL tokens)", "seal_tokens", "count(*)", ""),
    ("OCIANA (inscriptions)", "ociana", "count(*)", ""),
    ("I.Sicily (Semitic records)", "isicily", "count(*)", ""),
    ("eBL (fragments)", "ebl", "count(*)", ""),
    ("Achemenet Babylonian (documents)", "achemenet", "count(*)", ""),
    ("Achemenet Babylonian (automatic tokens)", "achemenet_tokens", "count(*)", ""),
    ("ELISIR (pilot lexical entries)", "elisir", "count(*)", ""),
    ("Ugarit Texts Database (metadata)", "ugaritdb", "count(*)", ""),
    ("DAPCA (released editions)", "dapca", "count(*)", ""),
    ("DAPCA (word spans)", "dapca_tokens", "count(*)", ""),
    ("Ancient Hebrew Inscriptions", "ahi", "count(*)", ""),
    ("EUPT (documents)", "eupt_documents", "count(*)", ""),
    ("EUPT (facsimile lines)", "eupt_lines", "count(*)", ""),
    ("EUPT (philology units)", "eupt_units", "count(*)", ""),
    ("EUPT (tokens)", "eupt_tokens", "count(*)", ""),
    ("EUPT (annotations)", "eupt_annotations", "count(*)", ""),
    ("Hebrew (OSHB words)", "hebrew", "count(*)", ""),
    ("Hebrew (OSHB verses)", "hebrew_verses", "count(*)", ""),
    ("Old Assyrian (documents; CDLI-derived)", "old_assyrian_documents", "count(*)", ""),
    ("Old Assyrian (words; CDLI-derived)", "old_assyrian_words", "count(*)", ""),
    ("TLHdig (documents)", "tlhdig_documents", "count(*)", ""),
    ("TLHdig (word analyses)", "tlhdig_words", "count(*)", ""),
    ("IG XV 1 (Cypriot syllabic records)", "cypriot_syllabic", "count(*)", ""),
    ("DASI OAI (all roster records)", "dasi", "count(*)", ""),
    ("DASI OAI (active epigraphs)", "dasi", "count(*)", " WHERE record_kind = 'epi' AND NOT deleted"),
)


def stats(con, as_json: bool) -> None:
    """Row counts for every view in the checkout; the views left out are named on stderr, one line a file."""
    present = {r[0] for r in con.execute("SELECT view_name FROM duckdb_views() WHERE NOT internal").fetchall()}
    parts = [f"SELECT {sql_string(label)} AS view, {expr} AS rows FROM {view}{where}"
             for label, view, expr, where in STATS if view in present]
    by_paths: dict[str, list[str]] = {}
    for view, paths in MISSING.items():
        by_paths.setdefault(paths, []).append(view)
    for paths, views in by_paths.items():
        print(f"not in this checkout: {', '.join(views)} (looked for {paths})", file=sys.stderr)
    if not parts:
        print("(no datasets in this checkout)")
        return
    run(con, "\nUNION ALL ".join(parts), as_json)


def main() -> int:
    ap = argparse.ArgumentParser(description="DuckDB SQL across the ANE corpora")
    ap.add_argument("--json", action="store_true", help="JSON output")
    ap.add_argument("--loose", action="store_true",
                    help="also match with marks, aleph/ayin and separators folded (otherwise only when "
                         "nothing matches strictly)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("sql", help="Raw SQL query")
    p.add_argument("query")

    p = sub.add_parser("term", help="Concordance lookup by transliteration, Hebrew, or root")
    p.add_argument("query")

    p = sub.add_parser("quran", help="Quran root (m-n-y), ayah (53:20), or gloss keyword")
    p.add_argument("query")

    p = sub.add_parser("epi", help="Arabian epigraphy (OCIANA/DASI) by transliteration or keyword")
    p.add_argument("query")

    p = sub.add_parser("aramaic", help="Ancient/classical Aramaic passages or annotated word/root rows")
    p.add_argument("query", nargs="?", default="")
    p.add_argument("--tokens", action="store_true", help="search annotated ETCBC token/root rows")
    p.add_argument("--corpus", help="restrict to corpus_id substring")
    p.add_argument("--dialect", help="restrict to dialect substring")
    p.add_argument("--period", help="restrict to period substring")
    p.add_argument("--preserved-only", action="store_true",
                   help="exclude reconstructed, uncertain, corrected, removed, alternative, vacat, or "
                        "missing-sign DSS readings")
    p.add_argument("--limit", type=int, default=60, help="max rows (default 60)")

    p = sub.add_parser("egytext", help="Egyptian texts (ORAEC/TLA) by oraecid, title, lemma, or translation "
                                       "keyword (German)")
    p.add_argument("query", nargs="?", default="")
    p.add_argument("--period", help="filter by period (e.g. 'New Kingdom')")
    p.add_argument("--dynasty", help="filter by dynasty number (e.g. '18')")
    p.add_argument("--genre", help="filter by genre slug (e.g. 'stele', 'papyrus_scroll')")
    p.add_argument("--sentences", action="store_true", help="search sentences instead of documents")
    p.add_argument("--limit", type=int, default=40, help="max rows (default 40)")

    p = sub.add_parser("cuneiform", help="Local ORACC/CDLI/SEAL texts by ID, metadata, transliteration, or lemma")
    p.add_argument("query", nargs="?", default="")
    p.add_argument("--tokens", action="store_true", help="search annotated ORACC tokens/lemmata")
    p.add_argument("--project", help="restrict to an ORACC project (substring)")
    p.add_argument("--period", help="restrict by period (substring)")
    p.add_argument("--genre", help="restrict by genre (substring)")
    p.add_argument("--provenience", help="restrict by provenience (substring)")
    p.add_argument("--limit", type=int, default=40, help="max rows (default 40)")

    p = sub.add_parser("seal", help="SEAL records or annotated word spans")
    p.add_argument("query", nargs="?", default="")
    p.add_argument("--tokens", action="store_true", help="search lemma/transliteration/meaning spans")
    p.add_argument("--limit", type=int, default=40, help="max rows (default 40)")

    p = sub.add_parser("ociana", help="Full OCIANA corpus by siglum, transliteration, translation, or commentary")
    p.add_argument("query", nargs="?", default="")
    p.add_argument("--script", help="restrict by script label, e.g. Safaitic or Hismaic")
    p.add_argument("--limit", type=int, default=60, help="max rows (default 60)")

    p = sub.add_parser("isicily", help="I.Sicily Punic/Phoenician/Hebrew records")
    p.add_argument("query", nargs="?", default="")
    p.add_argument("--language", help="restrict by main/other language code, e.g. xpu or he")
    p.add_argument("--limit", type=int, default=60, help="max rows (default 60)")

    p = sub.add_parser("ebl", help="eBL transliterated fragments by ID, ATF, description, or publication")
    p.add_argument("query", nargs="?", default="")
    p.add_argument("--period", help="restrict by period label")
    p.add_argument("--limit", type=int, default=60, help="max rows (default 60)")

    p = sub.add_parser("achemenet", help="Achaemenid Babylonian documents or automatically analyzed tokens")
    p.add_argument("query", nargs="?", default="")
    p.add_argument("--documents", action="store_true", help="search document IDs/citations instead of tokens")
    p.add_argument("--collection", help="restrict to a source collection, e.g. CT55 or Murashu")
    p.add_argument("--limit", type=int, default=60, help="max rows (default 60)")

    p = sub.add_parser("elisir", help="ELISIR pilot Eblaite lexical entries")
    p.add_argument("query", nargs="?", default="")
    p.add_argument("--limit", type=int, default=60, help="max rows (default 60)")

    p = sub.add_parser("ugaritdb", help="Ugarit Texts Database catalogue metadata (not full texts)")
    p.add_argument("query", nargs="?", default="")
    p.add_argument("--ktu", help="require an exact KTU3 identifier")
    p.add_argument("--excavation", help="require an exact RS/RIH siglum or parsed excavation number")
    p.add_argument("--language", help="restrict by a source language label")
    p.add_argument("--script", help="restrict by a source script label")
    p.add_argument("--limit", type=int, default=60, help="max rows (default 60)")

    p = sub.add_parser("dapca", help="Released DAPCA Late Bronze editions or word spans")
    p.add_argument("query", nargs="?", default="")
    p.add_argument("--tokens", action="store_true", help="search word spans rather than lines")
    p.add_argument("--site", help="restrict by ancient site")
    p.add_argument("--genre", help="restrict by genre")
    p.add_argument("--limit", type=int, default=60, help="max rows (default 60)")

    p = sub.add_parser("ahi", help="Oxford Ancient Hebrew Inscriptions by number or transcription")
    p.add_argument("query", nargs="?", default="")
    p.add_argument("--part", type=int, choices=(1, 2), help="restrict to AHI Part 1 or 2")
    p.add_argument("--empty", action="store_true", help="show only records with an empty text field")
    p.add_argument("--limit", type=int, default=60, help="max rows (default 60)")

    p = sub.add_parser("eupt", help="EUPT public Ugaritic editions by evidence layer")
    p.add_argument("query", nargs="?", default="")
    p.add_argument(
        "--layer", choices=("units", "tokens", "facsimile", "annotations", "documents"),
        default="units", help="evidence layer to search (default units)",
    )
    p.add_argument("--document", choices=("KTU 1.14", "KTU 1.15", "KTU 1.16"))
    p.add_argument("--limit", type=int, default=60, help="max rows (default 60)")

    p = sub.add_parser("oldassyrian", help="Old Assyrian Text-Fabric documents or word rows (CDLI-derived)")
    p.add_argument("query", nargs="?", default="")
    p.add_argument("--words", action="store_true", help="search word rows instead of documents")
    p.add_argument("--preserved-only", action="store_true",
                   help="exclude damaged, uncertain, supplied, missing, or excised word rows")
    p.add_argument("--genre", help="restrict documents by genre")
    p.add_argument("--limit", type=int, default=60, help="max rows (default 60)")

    p = sub.add_parser("tlhdig", help="TLHdig Anatolian documents or analyzed word rows")
    p.add_argument("query", nargs="?", default="")
    p.add_argument("--words", action="store_true", help="search word rows instead of documents")
    p.add_argument("--language", help="restrict by TLH code, e.g. Hur, Hit, Luw, Akk")
    p.add_argument("--cth", help="restrict by CTH number fragment")
    p.add_argument("--preserved-only", action="store_true", help="exclude damaged or uncertain word rows")
    p.add_argument("--limit", type=int, default=60, help="max rows (default 60)")

    p = sub.add_parser("cypriot", help="IG XV 1 Cypriot-syllabic EpiDoc records")
    p.add_argument("query", nargs="?", default="")
    p.add_argument("--place", help="restrict by find/origin place")
    p.add_argument("--limit", type=int, default=60, help="max rows (default 60)")

    p = sub.add_parser("dasi", help="Complete DASI OAI epigraph and object records")
    p.add_argument("query", nargs="?", default="")
    p.add_argument("--kind", choices=("epi", "obj"), help="restrict to epigraphs or objects")
    p.add_argument("--language", help="restrict by DASI language code or label")
    p.add_argument("--site", help="restrict by ancient or modern place name")
    p.add_argument("--genre", help="restrict by textual typology")
    p.add_argument("--period", help="restrict by DASI period code")
    p.add_argument(
        "--resolution",
        choices=("primary", "fallback", "upstream_orphan", "deleted"),
        help="restrict by local payload resolution",
    )
    p.add_argument("--has-translation", action="store_true")
    p.add_argument(
        "--field",
        choices=(
            "all", "title", "text", "translation", "bibliography", "entities",
            "identifiers", "personal-names", "theonyms", "places", "organizations",
            "commentary",
        ),
        default="all",
        help="field searched by QUERY (default all)",
    )
    p.add_argument("--limit", type=int, default=60, help="max rows (default 60)")

    p = sub.add_parser("hebrew", help="Full OSHB/WLC words or verses by form, lemma, morphology, or reference")
    p.add_argument("query", nargs="?", default="")
    p.add_argument("--verses", action="store_true", help="search verse text instead of word rows")
    p.add_argument("--book", help="restrict by OSIS book code, e.g. Ps or Ruth")
    p.add_argument("--lemma", help="restrict by OSHB/Strong lemma component")
    p.add_argument("--root", help="restrict to words whose lemma has this BDB root (b-r-ʾ, ברא)")
    p.add_argument("--morph", help="restrict by OSHB morphology substring")
    p.add_argument("--limit", type=int, default=60, help="max rows (default 60)")

    sub.add_parser("stats", help="Row counts for the views in this checkout")

    args = ap.parse_args()
    if hasattr(args, "limit") and args.limit <= 0:
        ap.error("--limit must be a positive integer")
    try:
        query(args)
    except NotInCheckout as e:
        print(f"stopped: {e}", file=sys.stderr)
        return 2
    return 0


def query(args: argparse.Namespace) -> None:
    global PROVENANCE
    con = get_connection(args.cmd)
    PROVENANCE = provenance(None if args.cmd in ("sql", "stats") else getattr(args, "query", None)) \
        if args.json else None

    if args.cmd == "sql":
        run(con, args.query, args.json)
    elif args.cmd == "stats":
        stats(con, args.json)
    elif args.cmd == "term":
        if "terms" in MISSING:
            raise NotInCheckout(f"the biblical-term concordances are not in this checkout (looked for {TERMS_GLOB})")
        q = esc(args.query)
        keys = view_keys(args.query, "term")
        typed = sql_string(plain_query(args.query))
        lq = loose_query(args.query)
        tiers = [
            (EXACT, f"transliteration = lower({typed})"),
            (EXACT, f"replace(root, '-', '') = replace({typed}, '-', '')"),
            (NOTATION, f"list_contains({keys}, root)"),
            # The term is pointed; a query without points is compared with the points dropped.
            (NOTATION, contains_any("regexp_replace(term, '[֑-ׇ]', '', 'g')",
                                    view_keys(args.query, "hebrew"))),
            (SUBSTRING, f"term LIKE '%{q}%' ESCAPE '\\'"),
        ]

        def build(folded):
            where, basis = matched(tiers, folded_field("root", lq) if folded and lq else None)
            return f"""SELECT term, transliteration, root, category, reference, hebrew, {basis}
                       FROM terms WHERE {where}
                       ORDER BY match_basis, transliteration"""
        run_folding(con, build, args.json, args.loose)
    elif args.cmd == "quran":
        if re.fullmatch(r"\d+:\d+", args.query):
            require(QURAN_TEXT, "quran_text.jsonl")
            s, a = args.query.split(":")
            # The text ships without its English translation; the column is shown when a local build has it.
            present = {r[0] for r in con.execute("DESCRIBE quran_text").fetchall()}
            cols = ", ".join(c for c in ("id", "surah_name", "form_original", "meaning", "match_keys") if c in present)
            run(con, f"""SELECT {cols}
                         FROM quran_text WHERE surah = {int(s)} AND ayah = {int(a)}""", args.json)
        else:
            require(QURAN_ROOTS, "quran_roots.jsonl")
            typed = sql_string(plain_query(args.query))
            bare = sql_string(plain_query(args.query).replace("-", ""))
            keys = view_keys(args.query, "quran")
            lq = loose_query(args.query)
            tiers = [
                (EXACT, f"replace(normalized, '-', '') = {bare}"),
                (EXACT, f"list_contains(match_keys, {typed})"),
                (NOTATION, f"list_has_any(match_keys, {keys})"),
                (GLOSS, gloss_hit("meaning", args.query)),
            ]

            def build(folded):
                fold = folded_keys_hold(lq) if lq else None
                where, basis = matched(tiers, fold if folded and lq else None)
                return f"""SELECT id, normalized, frequency, meaning AS glosses,
                                  ayah_refs[1:8] AS sample_ayahs, {basis}
                           FROM quran WHERE {where}
                           ORDER BY match_basis, frequency DESC"""
            run_folding(con, build, args.json, args.loose)
    elif args.cmd == "epi":
        require_any(EPIGRAPHY, "the Arabian epigraphy index")
        q = esc(args.query.lower())
        typed = sql_string(plain_query(args.query).lower())
        keys = view_keys(args.query, "epi")
        lq = loose_query(args.query)
        tiers = [
            (EXACT, f"list_contains(match_keys, {typed})"),
            (NOTATION, f"list_has_any(match_keys, {keys})"),
            (SUBSTRING, f"lower(form_original) LIKE '%{q}%' ESCAPE '\\'"),
            (SUBSTRING, f"lower(normalized) LIKE '%{q}%' ESCAPE '\\'"),
            (GLOSS, gloss_hit("meaning", args.query)),
        ]

        def build(folded):
            fold = folded_keys_hold(lq) if lq else None
            where, basis = matched(tiers, fold if folded and lq else None)
            return f"""SELECT id, language, substr(form_original, 1, 50) AS transliteration,
                              meaning AS translation, provenance, source_refs, {basis}
                       FROM epigraphy WHERE {where}
                       ORDER BY match_basis, id"""
        run_folding(con, build, args.json, args.loose)
    elif args.cmd == "aramaic":
        require(ARAMAIC, "aramaic_texts.jsonl")
        typed = plain_query(args.query)
        q = esc(typed)
        q_lower = esc(typed.lower())
        filters = []
        if args.corpus:
            filters.append(f"corpus_id ILIKE '%{esc(args.corpus)}%' ESCAPE '\\'")
        if args.dialect:
            filters.append(f"dialect ILIKE '%{esc(args.dialect)}%' ESCAPE '\\'")
        if args.period:
            filters.append(f"period ILIKE '%{esc(args.period)}%' ESCAPE '\\'")
        if args.preserved_only:
            if args.tokens:
                filters.append("COALESCE(preservation_affected, FALSE) = FALSE")
            else:
                filters.append("COALESCE(affected_token_count, 0) = 0")
        if args.tokens:
            lq = loose_query(args.query)
            tiers = []
            if args.query:
                root_bare = sql_string(re.sub(r"[-.\s]", "", typed.lower()))
                tiers = [
                    (EXACT, f"replace(lower(root), '-', '') = {root_bare}"),
                    (EXACT, f"replace(lower(root_normalized), '-', '') = {root_bare}"),
                    (NOTATION, f"list_contains({view_keys(args.query, 'aramaic')}, root_normalized)"),
                    (SUBSTRING, f"surface ILIKE '%{q}%' ESCAPE '\\'"),
                    (SUBSTRING, f"consonantal ILIKE '%{q}%' ESCAPE '\\'"),
                    (SUBSTRING, f"normalized ILIKE '%{q_lower}%' ESCAPE '\\'"),
                    (SUBSTRING, f"normalized_ascii ILIKE '%{q_lower}%' ESCAPE '\\'"),
                    (SUBSTRING, f"lexeme ILIKE '%{q}%' ESCAPE '\\'"),
                    (SUBSTRING, f"root ILIKE '%{q}%' ESCAPE '\\'"),
                    (GLOSS, gloss_hit("gloss", args.query)),
                ]

            def build(folded):
                basis, order, where = "", "", list(filters)
                if tiers:
                    condition, basis = matched(
                        tiers, folded_field("root_normalized", lq) if folded and lq else None)
                    where.append(condition)
                    basis, order = f", {basis}", "match_basis, "
                return f"""SELECT corpus_id, reference, passage_id, node, surface, consonantal,
                                  normalized, lexeme, root,
                                  root_normalized,
                                  gloss, part_of_speech, verbal_stem,
                                  automatic_language, model_score_aramaic,
                                  classification_method, preserved, reconstructed,
                                  uncertainty_max, missing_sign_count{basis}
                           FROM aramaic_tokens WHERE {" AND ".join(where) if where else "TRUE"}
                           ORDER BY {order}corpus_id, reference LIMIT {args.limit}"""
            run_folding(con, build, args.json, args.loose)
        else:
            if args.query:
                filters.append(
                    f"(form_original ILIKE '%{q}%' ESCAPE '\\' "
                    f"OR form_unicode ILIKE '%{q}%' ESCAPE '\\' "
                    f"OR normalized ILIKE '%{q_lower}%' ESCAPE '\\' "
                    f"OR normalized_ascii ILIKE '%{q_lower}%' ESCAPE '\\' "
                    f"OR reference ILIKE '%{q}%' ESCAPE '\\')"
                )
            where = " AND ".join(filters) if filters else "TRUE"
            run(con, f"""SELECT corpus_id, reference, dialect,
                                  substr(COALESCE(form_unicode, form_original), 1, 120) AS text,
                                  token_count, orthographic_word_count,
                                  affected_token_count, review_status
                           FROM aramaic WHERE {where}
                           ORDER BY corpus_id, reference LIMIT {args.limit}""", args.json)
    elif args.cmd == "egytext":
        require(EGY_DOCS, "egyptian_documents.jsonl")
        if args.sentences:
            require(EGY_SENTS, "egyptian_sentences.jsonl")
        q = esc(args.query)
        filters = []
        if args.period:
            filters.append(f"period = '{esc(args.period)}'")
        if args.dynasty:
            filters.append(f"dynasty = '{esc(args.dynasty)}'")
        if args.genre:
            filters.append(f"genre = '{esc(args.genre)}'")
        if args.sentences:
            # Sentence search: lemma/transliteration or translation keyword.
            # Document-level filters apply via a join on document_id.
            doc_filter = ""
            if filters:
                doc_filter = (" AND document_id IN "
                              f"(SELECT id FROM egytext_docs WHERE {' AND '.join(filters)})")
            lq = loose_query(args.query)
            tiers = [
                (EXACT, f"list_contains(match_keys, {sql_string(plain_query(args.query).lower())})"),
                (NOTATION, f"list_has_any(match_keys, {view_keys(args.query, 'egytext')})"),
                (SUBSTRING, f"transliteration ILIKE '%{q}%' ESCAPE '\\'"),
                (GLOSS, gloss_hit("meaning", args.query, prefix=True)),
            ] if q else []

            def build(folded):
                where, basis, order = "TRUE", "", ""
                if tiers:
                    fold = folded_keys_hold(lq) if lq else None
                    where, basis = matched(tiers, fold if folded and lq else None)
                    basis, order = f", {basis}", "match_basis, "
                return f"""SELECT id, oraecid, sentence_index AS n,
                                  substr(transliteration, 1, 60) AS transliteration,
                                  meaning AS translation_de{basis}
                           FROM egytext_sents
                           WHERE {where}{doc_filter}
                           ORDER BY {order}oraecid, n LIMIT {args.limit}"""
            run_folding(con, build, args.json, args.loose)
        else:
            conds = list(filters)
            if q:
                if re.fullmatch(r"oraec\d+", args.query):
                    conds.append(f"id = 'egytext:doc:{q}'")
                else:
                    conds.append(f"(normalized LIKE '%{esc(args.query.lower())}%' ESCAPE '\\'"
                                 f" OR list_contains(match_keys, '{esc(args.query.lower())}')"
                                 f" OR meaning ILIKE '%{q}%' ESCAPE '\\'"
                                 f" OR bibliography ILIKE '%{q}%' ESCAPE '\\')")
            if not conds:
                conds.append("TRUE")
            title_rank = (f"(normalized LIKE '%{esc(args.query.lower())}%' ESCAPE '\\') DESC, "
                          if q else "")
            run(con, f"""SELECT replace(id, 'egytext:doc:', '') AS oraecid,
                                title, period, dynasty, genre,
                                sentence_count AS sents
                         FROM egytext_docs
                         WHERE {' AND '.join(conds)}
                         ORDER BY {title_rank}oraecid LIMIT {args.limit}""", args.json)
    elif args.cmd == "cuneiform":
        require_any([ORACC_DOCS, CDLI_TEXTS, SEAL_RECORDS], "the cuneiform corpus")
        q = esc(args.query)
        filters = []
        if args.project:
            filters.append(f"source_project ILIKE '%{esc(args.project)}%' ESCAPE '\\'")
        if args.period:
            filters.append(f"period ILIKE '%{esc(args.period)}%' ESCAPE '\\'")
        if args.genre:
            filters.append(f"genre ILIKE '%{esc(args.genre)}%' ESCAPE '\\'")
        if args.provenience:
            filters.append(f"provenience ILIKE '%{esc(args.provenience)}%' ESCAPE '\\'")
        if args.tokens:
            require(ORACC_DOCS, "the ORACC token corpus")
            if args.query:
                filters.append(
                    f"(frag ILIKE '%{q}%' ESCAPE '\\' OR form ILIKE '%{q}%' ESCAPE '\\' "
                    f"OR norm ILIKE '%{q}%' ESCAPE '\\' OR cf ILIKE '%{q}%' ESCAPE '\\' "
                    f"OR gw ILIKE '%{q}%' ESCAPE '\\' OR sense ILIKE '%{q}%' ESCAPE '\\')"
                )
            where = " AND ".join(filters) if filters else "TRUE"
            run(con, f"""SELECT canonical_id, source_project, token_ref, frag, norm,
                                  cf, gw, sense, pos, lang, damaged
                           FROM cuneiform_tokens WHERE {where}
                           ORDER BY canonical_id, token_ref LIMIT {args.limit}""", args.json)
        else:
            if args.query:
                filters.append(
                    f"(canonical_id = upper('{q}') OR designation ILIKE '%{q}%' ESCAPE '\\' "
                    f"OR transliteration ILIKE '%{q}%' ESCAPE '\\')"
                )
            where = " AND ".join(filters) if filters else "TRUE"
            run(con, f"""SELECT id, canonical_id, source_family, source_project,
                                  designation, language, period, provenience, genre,
                                  substr(transliteration, 1, 120) AS text
                           FROM cuneiform_docs WHERE {where}
                           ORDER BY canonical_id LIMIT {args.limit}""", args.json)
    elif args.cmd == "seal":
        require(SEAL_RECORDS, "the SEAL corpus")
        q = esc(args.query)
        if args.tokens:
            where = "TRUE" if not q else (
                f"transliteration ILIKE '%{q}%' ESCAPE '\\' "
                f"OR lemma ILIKE '%{q}%' ESCAPE '\\' "
                f"OR meaning ILIKE '%{q}%' ESCAPE '\\' "
                f"OR surface ILIKE '%{q}%' ESCAPE '\\'"
            )
            run(con, f"""SELECT seal_no, designation, line, transliteration,
                                  lemma, meaning, surface
                           FROM seal_tokens WHERE {where}
                           ORDER BY TRY_CAST(seal_no AS INTEGER), line
                           LIMIT {args.limit}""", args.json)
        else:
            where = "TRUE" if not q else (
                f"canonical_id = '{q}' OR designation ILIKE '%{q}%' ESCAPE '\\' "
                f"OR tablet_siglum ILIKE '%{q}%' ESCAPE '\\' "
                f"OR transliteration ILIKE '%{q}%' ESCAPE '\\' "
                f"OR translation ILIKE '%{q}%' ESCAPE '\\'"
            )
            run(con, f"""SELECT canonical_id AS seal_no, designation, tablet_siglum,
                                  text_status, token_count,
                                  substr(transliteration, 1, 120) AS text,
                                  source_url
                           FROM seal WHERE {where}
                           ORDER BY TRY_CAST(canonical_id AS INTEGER)
                           LIMIT {args.limit}""", args.json)
    elif args.cmd == "ociana":
        require(OCIANA_FULL, "the OCIANA index")
        q = esc(args.query)
        filters = []
        if args.script:
            filters.append(f"script ILIKE '%{esc(args.script)}%' ESCAPE '\\'")
        if q:
            filters.append(
                f"(canonical_id ILIKE '%{q}%' ESCAPE '\\' OR siglum ILIKE '%{q}%' ESCAPE '\\' "
                f"OR transliteration ILIKE '%{q}%' ESCAPE '\\' "
                f"OR normalized ILIKE '%{esc(parse_query(args.query).text)}%' ESCAPE '\\' "
                f"OR translation ILIKE '%{q}%' ESCAPE '\\' "
                f"OR apparatus ILIKE '%{q}%' ESCAPE '\\' "
                f"OR commentary ILIKE '%{q}%' ESCAPE '\\')"
            )
        where = " AND ".join(filters) if filters else "TRUE"
        run(con, f"""SELECT canonical_id, siglum, script,
                              transliteration, translation, site, source_url
                       FROM ociana WHERE {where}
                       ORDER BY source_order LIMIT {args.limit}""", args.json)
    elif args.cmd == "isicily":
        require(ISICILY_SEMITIC, "the I.Sicily Semitic index")
        q = esc(args.query)
        filters = []
        if args.language:
            language = esc(args.language)
            filters.append(f"(main_language = '{language}' OR list_contains(other_languages, '{language}'))")
        if q:
            filters.append(
                f"(canonical_id ILIKE '%{q}%' ESCAPE '\\' OR title ILIKE '%{q}%' ESCAPE '\\' "
                f"OR text ILIKE '%{q}%' ESCAPE '\\' OR repository ILIKE '%{q}%' ESCAPE '\\' "
                f"OR origin_place ILIKE '%{q}%' ESCAPE '\\')"
            )
        where = " AND ".join(filters) if filters else "TRUE"
        run(con, f"""SELECT canonical_id, main_language, other_languages,
                              substr(text, 1, 100) AS text, origin_date,
                              origin_place, repository, source_url
                       FROM isicily WHERE {where}
                       ORDER BY source_order LIMIT {args.limit}""", args.json)
    elif args.cmd == "ebl":
        require(EBL_FRAGMENTS, "the eBL fragment index")
        q = esc(args.query)
        filters = []
        if args.period:
            filters.append(f"period ILIKE '%{esc(args.period)}%' ESCAPE '\\'")
        if q:
            filters.append(
                f"(canonical_id ILIKE '%{q}%' ESCAPE '\\' OR museum_number ILIKE '%{q}%' ESCAPE '\\' "
                f"OR publication ILIKE '%{q}%' ESCAPE '\\' OR description ILIKE '%{q}%' ESCAPE '\\' "
                f"OR atf ILIKE '%{q}%' ESCAPE '\\')"
            )
        where = " AND ".join(filters) if filters else "TRUE"
        run(con, f"""SELECT id, canonical_id, period, publication,
                              substr(description, 1, 80) AS description,
                              substr(atf, 1, 140) AS atf, line_count, source_url
                       FROM ebl WHERE {where}
                       ORDER BY source_order LIMIT {args.limit}""", args.json)
    elif args.cmd == "achemenet":
        require(ACHEMENET_RECORDS, "the Achemenet Babylonian index")
        q = esc(args.query)
        filters = []
        if args.collection:
            filters.append(f"collection ILIKE '%{esc(args.collection)}%' ESCAPE '\\'")
        if args.documents:
            if q:
                filters.append(
                    f"(canonical_id ILIKE '%{q}%' ESCAPE '\\' OR citation ILIKE '%{q}%' ESCAPE '\\')"
                )
            where = " AND ".join(filters) if filters else "TRUE"
            run(con, f"""SELECT id, canonical_id, collection, citation,
                                  token_count, annotation_status, source_url
                           FROM achemenet WHERE {where}
                           ORDER BY collection, document_order LIMIT {args.limit}""", args.json)
        else:
            if q:
                filters.append(
                    f"(form ILIKE '%{q}%' ESCAPE '\\' OR lemma ILIKE '%{q}%' ESCAPE '\\' "
                    f"OR english ILIKE '%{q}%' ESCAPE '\\' OR normalized_form ILIKE '%{q}%' ESCAPE '\\')"
                )
            where = " AND ".join(filters) if filters else "TRUE"
            run(con, f"""SELECT document_id, canonical_id, collection, citation,
                                  token_id, form, lemma, xpos, english, score, lock
                           FROM achemenet_tokens WHERE {where}
                           ORDER BY collection, document_order, TRY_CAST(token_id AS INTEGER)
                           LIMIT {args.limit}""", args.json)
    elif args.cmd == "elisir":
        require(ELISIR_RECORDS, "the ELISIR index")
        q = esc(args.query)
        where = "TRUE" if not q else (
            f"canonical_label ILIKE '%{q}%' ESCAPE '\\' OR definition ILIKE '%{q}%' ESCAPE '\\' "
            f"OR sense_reference ILIKE '%{q}%' ESCAPE '\\' OR editorial_note ILIKE '%{q}%' ESCAPE '\\'"
        )
        run(con, f"""SELECT id, canonical_label, part_of_speech,
                              definition, sense_reference, editorial_note,
                              len(attestations) AS attestation_count, source_url
                       FROM elisir WHERE {where}
                       ORDER BY source_order LIMIT {args.limit}""", args.json)
    elif args.cmd == "ugaritdb":
        require(UGARITDB_RECORDS, "the Ugarit Texts Database index")
        q = esc(args.query)
        filters = []
        if args.ktu:
            filters.append(f"ktu3 = '{esc(args.ktu)}'")
        if args.excavation:
            excavation = esc(args.excavation)
            filters.append(
                f"(lower(excavation_siglum) = lower('{excavation}') "
                f"OR list_contains(excavation_numbers_cleared, '{excavation}') "
                f"OR list_contains(excavation_numbers_utdb, '{excavation}') "
                f"OR excavation_numbers_sau = '{excavation}')"
            )
        if args.language:
            filters.append(
                f"CAST(languages AS VARCHAR) ILIKE '%{esc(args.language)}%' ESCAPE '\\'"
            )
        if args.script:
            filters.append(
                f"CAST(scripts AS VARCHAR) ILIKE '%{esc(args.script)}%' ESCAPE '\\'"
            )
        if q:
            filters.append(
                f"(dataset_row_id = '{q}' OR ktu3 ILIKE '%{q}%' ESCAPE '\\' "
                f"OR search_text ILIKE '%{q}%' ESCAPE '\\')"
            )
        where = " AND ".join(filters) if filters else "TRUE"
        run(con, f"""SELECT id, excavation_siglum, excavation_numbers_cleared,
                              excavation_numbers_utdb, ktu3, languages, scripts,
                              sau_genre, rsti_object_type,
                              coalesce(nullif(sau_findspot, ''), nullif(teo_findspot, ''),
                                       archive_general_area) AS findspot,
                              source_url
                       FROM ugaritdb WHERE {where}
                       ORDER BY CASE WHEN ktu3 = '{q}' THEN 0 ELSE 1 END,
                                source_order LIMIT {args.limit}""", args.json)
    elif args.cmd == "dapca":
        require(DAPCA_RECORDS, "the DAPCA index")
        q = esc(args.query)
        filters = []
        if args.site:
            filters.append(f"site ILIKE '%{esc(args.site)}%' ESCAPE '\\'")
        if args.genre:
            filters.append(f"genre ILIKE '%{esc(args.genre)}%' ESCAPE '\\'")
        if args.tokens:
            if q:
                filters.append(f"surface ILIKE '%{q}%' ESCAPE '\\'")
            where = " AND ".join(filters) if filters else "TRUE"
            run(con, f"""SELECT tablet_id, tablet, inventory, site, genre,
                                  face, label, surface, lemma_id,
                                  named_lemma_id, word_class
                           FROM dapca_tokens WHERE {where}
                           ORDER BY tablet_id, face, label LIMIT {args.limit}""", args.json)
        else:
            if q:
                filters.append(
                    f"(tablet ILIKE '%{q}%' ESCAPE '\\' OR inventory ILIKE '%{q}%' ESCAPE '\\' "
                    f"OR text ILIKE '%{q}%' ESCAPE '\\')"
                )
            where = " AND ".join(filters) if filters else "TRUE"
            run(con, f"""SELECT tablet_id, tablet, inventory, site, language,
                                  genre, subtype, face, label, substr(text, 1, 120) AS text
                           FROM dapca_lines WHERE {where}
                           ORDER BY tablet_id, face, label LIMIT {args.limit}""", args.json)
    elif args.cmd == "ahi":
        require(AHI_RECORDS, "the AHI index")
        q = esc(args.query)
        filters = []
        if args.part:
            filters.append(f"part = {args.part}")
        if args.empty:
            filters.append("is_empty")
        basis, order = "", ""
        if q:
            # search_ascii is the words folded as loose_key folds them (ʾ and ʿ both '); the query is folded
            # word by word to match, so its word breaks survive.
            folded = " ".join(k for k in (loose_key(w) for w in args.query.split()) if k)
            condition, basis = matched([
                (EXACT, f"ahi_number = {sql_string(args.query)}"),
                (EXACT, f"raw_text ILIKE '%{q}%' ESCAPE '\\'"),
                (EXACT, f"search_unicode ILIKE '%{q}%' ESCAPE '\\'"),
                (NOTATION, contains_any("search_unicode", view_keys(args.query, "ahi"))),
                *([(FOLDED, contains_any("search_ascii", sql_strings([folded])))] if folded else []),
            ])
            filters.append(condition)
            basis, order = f", {basis}", "match_basis, "
        where = " AND ".join(filters) if filters else "TRUE"
        run(con, f"""SELECT id, ahi_number, part,
                              substr(raw_text, 1, 180) AS raw_text,
                              substr(search_unicode, 1, 120) AS search_unicode,
                              is_empty, source_url{basis}
                       FROM ahi WHERE {where}
                       ORDER BY {order}part, source_order LIMIT {args.limit}""", args.json)
    elif args.cmd == "eupt":
        for path in (EUPT_DOCUMENTS, EUPT_LINES, EUPT_UNITS, EUPT_TOKENS, EUPT_ANNOTATIONS):
            require(path, "the EUPT index")
        q = esc(args.query)
        filters = []
        if args.document:
            column = "label" if args.layer == "documents" else "document"
            filters.append(f"{column} = '{esc(args.document)}'")
        if args.layer == "documents":
            if q:
                filters.append(
                    f"(label ILIKE '%{q}%' ESCAPE '\\' OR citation ILIKE '%{q}%' ESCAPE '\\' "
                    f"OR CAST(metadata_plain AS VARCHAR) ILIKE '%{q}%' ESCAPE '\\')"
                )
            where = " AND ".join(filters) if filters else "TRUE"
            run(con, f"""SELECT label, version_status, facsimile_line_count,
                                  philology_unit_count, token_count, annotation_count,
                                  manifest_url
                           FROM eupt_documents WHERE {where}
                           ORDER BY label LIMIT {args.limit}""", args.json)
        elif args.layer == "facsimile":
            if q:
                filters.append(
                    f"(location ILIKE '%{q}%' ESCAPE '\\' OR transcription ILIKE '%{q}%' ESCAPE '\\' "
                    f"OR commentary ILIKE '%{q}%' ESCAPE '\\')"
                )
            where = " AND ".join(filters) if filters else "TRUE"
            run(con, f"""SELECT document, location,
                                  substr(transcription, 1, 140) AS transcription,
                                  substr(commentary, 1, 120) AS commentary, source_url
                           FROM eupt_lines WHERE {where}
                           ORDER BY document, source_order LIMIT {args.limit}""", args.json)
        elif args.layer == "tokens":
            if q:
                # A LUPT label matches whole, with or without its homonym numeral ("mlk", "mlk I"); a German
                # gloss matches at a word start (König, Königtum).
                label = sql_string(unicodedata.normalize("NFC", args.query).strip().lower())
                glosses = "array_to_string(lemma_glosses_de, ' | ')"
                filters.append(
                    f"(surface ILIKE '%{q}%' ESCAPE '\\' OR morphology ILIKE '%{q}%' ESCAPE '\\' "
                    f"OR lemma ILIKE '%{q}%' ESCAPE '\\' "
                    f"OR len(list_filter(lemma_labels, lambda x: lower(x) = {label} "
                    f"OR lower(regexp_replace(x, '\\s+[IVX]+$', '')) = {label})) > 0 "
                    f"OR {gloss_hit(glosses, args.query, prefix=True)})"
                )
            where = " AND ".join(filters) if filters else "TRUE"
            run(con, f"""SELECT id, document, locations, surface, morphology, lemma, lemma_labels,
                                  lemma_glosses_de, unit_id, facsimile_corresp
                           FROM eupt_tokens WHERE {where}
                           ORDER BY document, unit_id, token_order_in_unit LIMIT {args.limit}""", args.json)
        elif args.layer == "annotations":
            if q:
                filters.append(
                    f"(body_type ILIKE '%{q}%' ESCAPE '\\' OR body_text ILIKE '%{q}%' ESCAPE '\\' "
                    f"OR CAST(targets AS VARCHAR) ILIKE '%{q}%' ESCAPE '\\')"
                )
            where = " AND ".join(filters) if filters else "TRUE"
            run(con, f"""SELECT document, body_type, substr(body_text, 1, 160) AS body_text,
                                  targets, id
                           FROM eupt_annotations WHERE {where}
                           ORDER BY document, source_order LIMIT {args.limit}""", args.json)
        else:
            if q:
                filters.append(
                    f"(list_contains(locations, '{q}') OR vocalization ILIKE '%{q}%' ESCAPE '\\' "
                    f"OR translation_de ILIKE '%{q}%' ESCAPE '\\' "
                    f"OR translation_en ILIKE '%{q}%' ESCAPE '\\' "
                    f"OR commentary ILIKE '%{q}%' ESCAPE '\\')"
                )
            where = " AND ".join(filters) if filters else "TRUE"
            run(con, f"""SELECT document, locations, vocalization, translation_en, translation_de,
                                  substr(commentary, 1, 100) AS commentary
                           FROM eupt_units WHERE {where}
                           ORDER BY document, source_order LIMIT {args.limit}""", args.json)
    elif args.cmd == "oldassyrian":
        require(OLD_ASSYRIAN_DOCS, "the Old Assyrian document index")
        require(OLD_ASSYRIAN_WORDS, "the Old Assyrian word index")
        q = esc(args.query)
        filters = []
        if args.words:
            if q:
                filters.append(f"(atf ILIKE '%{q}%' ESCAPE '\\' OR unicode ILIKE '%{q}%' ESCAPE '\\' "
                               f"OR pnumber = upper('{q}'))")
            if args.preserved_only:
                filters.append("preserved")
            where = " AND ".join(filters) if filters else "TRUE"
            run(con, f"""SELECT pnumber, position, atf, unicode, language,
                                  damaged, uncertain, supplied, missing, excised, preserved
                           FROM old_assyrian_words WHERE {where}
                           ORDER BY pnumber, position LIMIT {args.limit}""", args.json)
        else:
            if q:
                filters.append(f"(pnumber = upper('{q}') OR transliteration ILIKE '%{q}%' ESCAPE '\\')")
            if args.genre:
                filters.append(f"genre ILIKE '%{esc(args.genre)}%' ESCAPE '\\'")
            where = " AND ".join(filters) if filters else "TRUE"
            run(con, f"""SELECT pnumber, period, genre, subgenre, word_count,
                                  substr(transliteration, 1, 160) AS transliteration,
                                  independent_witness, review_status
                           FROM old_assyrian_documents WHERE {where}
                           ORDER BY pnumber LIMIT {args.limit}""", args.json)
    elif args.cmd == "tlhdig":
        require(TLHDIG_DOCS, "the TLHdig document index")
        require(TLHDIG_WORDS, "the TLHdig word index")
        q = esc(args.query)
        filters = []
        if args.cth:
            filters.append(f"cth ILIKE '%{esc(args.cth)}%' ESCAPE '\\'")
        if args.words:
            if q:
                filters.append(
                    f"(surface ILIKE '%{q}%' ESCAPE '\\' OR trans ILIKE '%{q}%' ESCAPE '\\' "
                    f"OR selected_analysis ILIKE '%{q}%' ESCAPE '\\' OR document ILIKE '%{q}%' ESCAPE '\\')"
                )
            if args.language:
                filters.append(f"language_normalized = '{esc(args.language)}'")
            if args.preserved_only:
                filters.append("preserved")
            where = " AND ".join(filters) if filters else "TRUE"
            run(con, f"""SELECT document, cth, line, position, language_normalized AS language,
                                  surface, trans, selected_analysis, damaged, uncertain, preserved
                           FROM tlhdig_words WHERE {where}
                           ORDER BY document, position LIMIT {args.limit}""", args.json)
        else:
            if q:
                filters.append(
                    f"(document ILIKE '%{q}%' ESCAPE '\\' OR transliteration ILIKE '%{q}%' ESCAPE '\\' "
                    f"OR list_contains(publications, '{q}') OR list_contains(inventory_numbers, '{q}'))"
                )
            if args.language:
                filters.append(f"list_contains(languages, '{esc(args.language)}')")
            where = " AND ".join(filters) if filters else "TRUE"
            run(con, f"""SELECT document, cth, publications, inventory_numbers, languages,
                                  line_count, word_count, substr(transliteration, 1, 180) AS transliteration,
                                  review_status
                           FROM tlhdig_documents WHERE {where}
                           ORDER BY document LIMIT {args.limit}""", args.json)
    elif args.cmd == "cypriot":
        require(CYPRIOT_RECORDS, "the IG XV 1 index")
        q = esc(args.query)
        filters = []
        if q:
            filters.append(
                f"(designation ILIKE '%{q}%' ESCAPE '\\' OR title ILIKE '%{q}%' ESCAPE '\\' "
                f"OR place ILIKE '%{q}%' ESCAPE '\\' OR CAST(editions AS VARCHAR) ILIKE '%{q}%' ESCAPE '\\')"
            )
        if args.place:
            filters.append(f"place ILIKE '%{esc(args.place)}%' ESCAPE '\\'")
        where = " AND ".join(filters) if filters else "TRUE"
        run(con, f"""SELECT record_id, designation, place, date, support, editions,
                              translations, source_url, review_status
                       FROM cypriot_syllabic WHERE {where}
                       ORDER BY number LIMIT {args.limit}""", args.json)
    elif args.cmd == "dasi":
        require(DASI_RECORDS, "the DASI index")
        q = esc(args.query.casefold())
        lq = text_query(args.query)
        tiers = []
        filters = [] if args.resolution == "deleted" else ["NOT deleted"]
        if args.kind:
            filters.append(f"record_kind = '{args.kind}'")
        if args.language:
            language = esc(args.language)
            filters.append(
                f"(CAST(languages AS VARCHAR) ILIKE '%{language}%' ESCAPE '\\' "
                f"OR CAST(language_codes AS VARCHAR) ILIKE '%{language}%' ESCAPE '\\')"
            )
        if args.site:
            filters.append(
                f"(CAST(place_names AS VARCHAR) ILIKE '%{esc(args.site)}%' ESCAPE '\\' "
                f"OR CAST(coverage AS VARCHAR) ILIKE '%{esc(args.site)}%' ESCAPE '\\')"
            )
        if args.genre:
            filters.append(
                f"CAST(textual_typology AS VARCHAR) ILIKE '%{esc(args.genre)}%' ESCAPE '\\'"
            )
        if args.period:
            filters.append(
                f"(CAST(period_codes AS VARCHAR) ILIKE '%{esc(args.period)}%' ESCAPE '\\' "
                f"OR CAST(origin_dates AS VARCHAR) ILIKE '%{esc(args.period)}%' ESCAPE '\\')"
            )
        if args.resolution:
            filters.append(f"resolution = '{args.resolution}'")
        if args.has_translation:
            filters.append("has_translation")
        if q:
            search_fields = {
                "all": "search_text",
                "title": "concat_ws(' ', title, CAST(alternate_titles AS VARCHAR))",
                "text": "transcription_plain",
                "translation": "translation_text",
                "bibliography": "bibliography_text",
                "entities": "CAST(entity_names AS VARCHAR)",
                "identifiers": "concat_ws(' ', CAST(identifier_values AS VARCHAR), "
                               "CAST(inventory_numbers AS VARCHAR), CAST(dois AS VARCHAR))",
                "personal-names": "CAST(personal_names AS VARCHAR)",
                "theonyms": "concat_ws(' ', CAST(theonyms AS VARCHAR), CAST(divine_epithets AS VARCHAR))",
                "places": "concat_ws(' ', CAST(place_names AS VARCHAR), CAST(attested_place_names AS VARCHAR), "
                          "CAST(coverage AS VARCHAR))",
                "organizations": "concat_ws(' ', CAST(tribes AS VARCHAR), CAST(groups AS VARCHAR), "
                                 "CAST(states AS VARCHAR), CAST(ethnonyms AS VARCHAR))",
                "commentary": "concat_ws(' ', commentary, apparatus, inline_apparatus_text)",
            }
            expression = search_fields[args.field]
            tiers = [
                (EXACT, f"lower({expression}) LIKE '%{q}%' ESCAPE '\\'"),
                (NOTATION, contains_any(f"lower({expression})", view_keys(args.query, "dasi"))),
            ]
        named_field_values = {
            "identifiers": "concat_ws('; ', array_to_string(identifier_values, '; '), "
                           "array_to_string(inventory_numbers, '; '), array_to_string(dois, '; '))",
            "entities": "array_to_string(entity_names, '; ')",
            "personal-names": "array_to_string(personal_names, '; ')",
            "theonyms": "concat_ws('; ', array_to_string(theonyms, '; '), array_to_string(divine_epithets, '; '))",
            "places": "concat_ws('; ', array_to_string(place_names, '; '), "
                      "array_to_string(attested_place_names, '; '), array_to_string(coverage, '; '))",
            "organizations": "concat_ws('; ', array_to_string(tribes, '; '), array_to_string(groups, '; '), "
                             "array_to_string(states, '; '), array_to_string(ethnonyms, '; '))",
        }
        matched_values = named_field_values.get(args.field)
        matched_select = (
            f"{matched_values} AS matched_values," if matched_values else ""
        )

        def build(folded):
            conditions, basis = list(filters), ""
            if tiers:
                # The text holds the query: its folded key inside, the pattern found inside, word by word.
                words = text_words(expression)
                fold = (f"(contains({sql_loose(words)}, {lq[0]}) "
                        f"AND regexp_matches({sql_marks_kept(words)}, {lq[1]}))") if lq else None
                condition, basis = matched(tiers, fold if folded else None)
                conditions.append(condition)
            where = " AND ".join(conditions) if conditions else "TRUE"
            return f"""SELECT identifier, record_kind, title,
                              array_to_string(
                                  list_transform(languages, lambda item:
                                      coalesce(nullif(item.code, ''), item.label)),
                                  ', '
                              ) AS languages,
                              array_to_string(place_names, '; ') AS places,
                              array_to_string(textual_typology, '; ') AS genre,
                              {matched_select}
                              substr(CASE WHEN record_kind = 'epi'
                                          THEN transcription_plain
                                          ELSE array_to_string(descriptions, '; ')
                                     END, 1, 180) AS evidence,
                              critical_counts.supplied AS supplied,
                              critical_counts.unclear AS unclear,
                              critical_counts.gap AS gaps,
                              resolution, source_url, raw_path{f", {basis}" if q else ""}
                       FROM dasi WHERE {where}
                       ORDER BY CASE
                                  WHEN lower(identifier) = '{q}' THEN 0
                                  WHEN lower(title) = '{q}' THEN 1
                                  ELSE 2
                                END,
                                {"match_basis, " if q else ""}record_kind, record_number
                       LIMIT {args.limit}"""
        run_folding(con, build, args.json, args.loose)
    elif args.cmd == "hebrew":
        require(HEBREW_WORDS, "the OSHB word index")
        require(HEBREW_VERSES, "the OSHB verse index")
        q = esc(args.query)
        # A pointed query, spelled without its points, for the consonantal fields.
        unpointed = view_keys(args.query, "hebrew") if q else None
        filters = []
        if args.book:
            filters.append(f"book = '{esc(args.book)}'")
        basis, order = "", ""
        if args.verses:
            if q:
                condition, basis = matched([
                    (EXACT, f"reference ILIKE '%{q}%' ESCAPE '\\'"),
                    (EXACT, f"surface LIKE '%{q}%' ESCAPE '\\'"),
                    (EXACT, f"consonantal LIKE '%{q}%' ESCAPE '\\'"),
                    (NOTATION, contains_any("consonantal", unpointed)),
                ])
                filters.append(condition)
                basis, order = f", {basis}", "match_basis, "
            where = " AND ".join(filters) if filters else "TRUE"
            run(con, f"""SELECT reference, substr(surface, 1, 160) AS text,
                                  substr(consonantal, 1, 160) AS consonantal,
                                  token_count, source_url{basis}
                           FROM hebrew_verses WHERE {where}
                           ORDER BY {order}book_order, reference LIMIT {args.limit}""", args.json)
        else:
            if args.lemma:
                lemma = esc(args.lemma)
                filters.append(f"list_contains(lemma_parts, '{lemma}')")
            if args.root:
                require(HEBREW_ROOTS, "the OSHB lemma-root table")
                OPENED.append(str(HEBREW_ROOTS))
                PROVENANCE = provenance(args.query) if args.json else None
                filters.append(f"list_contains({sql_strings(hebrew_root_lemmas(args.root))}, lemma_parts[-1])")
            if args.morph:
                filters.append(f"morphology ILIKE '%{esc(args.morph)}%' ESCAPE '\\'")
            if q:
                # A word is the query whole, or one of its own parts (ב/ראשית holds ראשית); a reference is a
                # locator, found inside. Inside a word or lemma, the query is part of it.
                typed = sql_string(args.query)
                condition, basis = matched([
                    (EXACT, f"immutable_word_id = {typed}"),
                    (EXACT, f"reference ILIKE '%{q}%' ESCAPE '\\'"),
                    (EXACT, f"surface = {typed} OR list_contains(surface_parts, {typed})"),
                    (EXACT, f"consonantal = {typed} OR consonantal_joined = {typed}"),
                    (EXACT, f"list_contains(string_split(consonantal, '/'), {typed})"),
                    (EXACT, f"lower(lemma) = lower({typed}) OR list_contains(lemma_parts, {typed})"),
                    (NOTATION, f"list_contains({unpointed}, consonantal_joined)"),
                    (NOTATION, f"list_has_any({unpointed}, string_split(consonantal, '/'))"),
                    (SUBSTRING, f"surface LIKE '%{q}%' ESCAPE '\\'"),
                    (SUBSTRING, f"consonantal LIKE '%{q}%' ESCAPE '\\'"),
                    (SUBSTRING, f"consonantal_joined LIKE '%{q}%' ESCAPE '\\'"),
                    (SUBSTRING, f"lemma ILIKE '%{q}%' ESCAPE '\\'"),
                    (SUBSTRING, contains_any("consonantal_joined", unpointed)),
                ])
                filters.append(condition)
                basis, order = f", {basis}", "match_basis, "
            where = " AND ".join(filters) if filters else "TRUE"
            run(con, f"""SELECT reference, word_index, surface, consonantal,
                                  lemma, morphology, immutable_word_id{basis}
                           FROM hebrew WHERE {where}
                           ORDER BY {order}book_order, reference, word_index LIMIT {args.limit}""", args.json)


if __name__ == "__main__":
    raise SystemExit(main())
