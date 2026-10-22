# tools/linear_a/ingest

Builders for the contact-language lexicons the comparative tools read from `data/contact/`. The lexicons are not
shipped: each builder reads its source under that source's terms, keeps downloads in the user cache, and backs up
any lexicon before it rewrites it.

| Script | Builds from |
|---|---|
| `ingest_hurrian_lexical.py` | Reviewed Hurrian and Urartian candidates, into the Hurrian lexicon (a dry run by default) |
| `ingest_lsj.py` | The Liddell–Scott–Jones Greek lexicon, from Logeion's corrected TEI fetched beforehand |
| `ingest_oracc_amarna.py` | ORACC's Amarna corpus (`aemw/amarna`), downloaded from ORACC, into the Canaanite lexicon |
| `ingest_tla.py` | The Thesaurus Linguae Aegyptiae's SRU API, into the Egyptian lexicon (`--dry-run` to preview) |
