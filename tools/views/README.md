# tools/views

The record wiki's builder: Markdown pages generated from the Linear A data files, which stay canonical. Stdlib only,
and read-only on the data.

| Module | What it does |
|---|---|
| `counts.py` | every count the wiki prints: documents from records (`doc_id`), the census classes from `census_classes.json`, complete translations |
| `model.py` | loads a data folder, normalizes the two translation schemas, gives page paths (`slug`, `word_path`, `doc_path`, `sign_path`) and sign status by kind (refusing a review verdict it does not know), matches a form's signs to their records with subscripts read as digits (`sign_parts`, `sign_keys`), and builds the reverse indexes |
| `markdown.py` | escaping, wikilinks and tables, frontmatter that reads back as JSON, the page skeleton, and `splice`, which replaces the builder's keys (on their own lines) and block in a page on disk and keeps every other line verbatim |
| `render.py` | the word, inscription and sign pages, as (path, text); `pages` gives them all in path order, and `collect` refuses two pages on one path, case aside. `name`, `sources` and the timestamps are left to `wiki update`, and a word is linked only when it has a page |
| `ledgers.py` | the ledger pages: `counts` (headline counts and the census classes, never a stored `stats` block), `standing` (every reading by tier, with its score), `by_site`, `by_root` (a lossy browse key, no root links) and `by_sign` |
| `aegean.py` | the Eteocretan inscriptions with their word analyses, and the Phaistos Disc with a page per sign; each set only when its files are in the data folder |
| `roots.py` | the Semitic root pages, one per record of `semitic_roots.json` in the `semitic-roots/` folder beside the data folder, at `wiki/semitic-roots/<first radical>/<id>_<meaning>`: the reconstruction and meaning with their basis and SED entry, each reflex as shipped with its sources and what was withheld, and the project's note; no Linear A links (a key match is a lead, never identity); and each radical folder's desc |
| `indexes.py` | the descs of the folders the builder fills (an inscription site, its series, a word's first sign), with no counts, a "(?)" site read as a doubtful attribution, and `overrides.json`'s hand descs in place of generated ones; `build.py` writes one only where a folder's `_index.md` has none or `wiki update`'s placeholder |
| `build.py` | the command: `python -m tools.views.build --data DIR --out WIKI`, which checks by default and writes nothing; `--write` writes missing and stale pages and missing folder descs after a backup (to `tools.paths.BACKUPS`, outside the repository), and refuses uncommitted or foreign pages and orphans without `--prune`; either mode stops before touching a file when a page path would leave the wiki folder |
| `census_doc.py` | the generated blocks of `docs/corpus-census.md`: `python -m tools.views.census_doc --data DIR` checks them, `--write` rewrites them after a copy |
| `overrides.json` | presentation only: folders for corpus keys the series pattern cannot read (an empty series files a key directly under its site), file names set by hand, and folder descs set by hand where the generated one would mislead (the Keftiu spell's `LMP/`) |

Tests: `tests/views/`.
