# ANE tests

Tests for the ancient Near East tools in `tools/ane/` and the name layers in `data/`. All eight run offline: the
parsers read inline HTML and XML fixtures, the request tests use stub clients, and the path tests, the notation census
and the name-layer checks read the shipped data or a fixture, so no test reaches a live site.

| Test | Covers |
|---|---|
| `test_data_paths.py` | `tools/paths.py`, `query_place_authorities`, `query_proper_names`: the clients, run as a user would, reach the shipped Pleiades, Trismegistos and PNM v6 data, and name a dataset that is not in the checkout (the held iDAI records among them); every portal client caches under the user cache, never the repo; iDAI refuses a delay under one second |
| `test_name_layers.py` | the Prosopographia Memphitica, TLA v18 names, Gauthier's DNG and Kassite name concordance files: each matches its `MANIFEST.json` outputs (rows and sha256), carries no private catalogue id or local path, and is listed by its folder's `_index.md` |
| `test_query_name_layers.py` | `query_proper_names` on those four layers: each source's own fields, the TLA yod and Manuel de Codage readings, the layers each has, and the volume and page each row prints |
| `test_place_authorities.py` | `query_place_authorities` on a fixture: a substring hit does not keep out a folded whole name, a whole-label match keeps the fold out, and there is no crosswalk view |
| `test_external_portal_queries.py` | `query_deaps`, `query_elephantine`, `query_rsti`: parsers keep record identity and rights fields, never follow pagination, refuse unfiltered calls and delays under one second |
| `test_ane_keys.py` | `ane_keys`, `aneq`: query parsing, each view's spellings (Manuel de Codage, ASCII digraphs, Hebrew romanisation), the folded key and fold pattern; a census of the keys each view stores (declared alphabet, aleph and ayin signs, aneq's SQL folds agreeing with `loose_key` and `marks_kept`), skipped view by view when that view's files are not in the checkout |
| `test_withheld_sources.py` | `ane_keys`, `query_proper_names`: no view or source for data this repository does not ship (the Sabaic dictionaries, Harding, the Kitāb al-Aṣnām, the Zohar, Pagan's Ebla names, the Egyptian foreign-name index), and the views that stay spell queries as before |
| `test_query_diconab.py` | `query_diconab`: parsers, conservative defaults, the refusals, the throttle on every live call, and auditable page requests |

Run with `PYTHONDONTWRITEBYTECODE=1 uv run --with pytest python -m pytest tests/ane`.
