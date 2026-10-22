# Linear A tests

Tests for the shared library in `tools/core/` and the commands in `tools/linear_a/`. The unit tests use no data
files: every input is written inline, so they run on a fresh clone. The `data` tests read the shipped files.

| Test | Covers |
|---|---|
| `test_phonetics.py` | `phonetics`: canonical mapping of non-standard letters (θ, ġ, đ, Syriac), the ġ distance table, and a regression for entries those letters once hid |
| `test_greek_spelling.py` | `greek_spelling`: `greek_to_lb` and `lb_token_to_key`, with a regression for syllables and doublets the Linear A sign table dropped |
| `test_anatolian_morphology.py` | `anatolian_morphology`: suffix stripping, confidence downgrade, no prefixes, guards, deduplication, toponym constants |
| `test_egyptian_morphology.py` | `egyptian_morphology`: suffix, prefix and combined stripping, confidence downgrade, guards, deduplication |
| `test_morphology_dispatch.py` | `morphology_dispatch`: routing by language, and its re-exports |
| `test_sedra.py` | `sedra`: SEDRA III ASCII to Syriac script and to Latin notation, on real vocalised words, and its errors |
| `test_shoresh_imports.py` | the Shoresh modules import in an isolated interpreter with only this repository on the path, and the frozen tagger matches its pinned hash |
| `test_shoresh_nulls.py` | `shoresh_nulls`: root keys, the name test and the decoy draws, pinned to the private originals' output on the same input (a two-document fixture) |
| `test_semitic_roots_v2.py` | the shipped `semitic_roots.json` (schema 2) reads as the records the root index keys on (`roots_records`), through `root_index.load_records` and `data_cache.semitic_roots`; a withheld reflex has no Analogues entry; the private list format passes through; another schema version is refused |
| `test_core_data_paths.py` | the `tools/core` loaders read from `data/linear-a/`, `data/contact/` and `data/semitic-roots/` (through `tools/paths.py`), a missing dataset is named (the site profiles and verb templates too), and saved runs go to the cache, not the repository |
| `test_lookups.py` | the `tools/linear_a` lookups, run as commands: Eteocretan counts that keep the forgery apart, notes and lexicon matches, no process wording; onomasticon tokens and filters; dating filters by period and corpus form; saved runs listed, shown, compared and exported from the cache; a missing dataset named with exit 2; and (data) the shipped files |
| `test_lq.py` | `lq`, run as a command: word and raw SQL queries, an inscription's confidence and every word's gloss, unread counts by verdict, a view or the lexicon not in the checkout named with exit 2, and (data) the shipped lexicon. Skipped without duckdb |
| `test_run_index.py` | a saved `null_model_audit` or `guttural_audit` run leaves the run index listable by `run_type` (runs in a tmp folder) |
| `test_analysis_units.py` | `gordon_morphology_overlay` strips sign subscripts in the stripped form; `lb_roc_calibration` calibrates a separating feature at its boundary, backs up the thresholds it replaces, and stops with exit 2 when the feature file is missing |
| `test_check_unread_words.py` | `check_unread_words`: role labels and readings that only spell the signs are not readings, a hyphen beside a bracket does not split a broken form, a speculative syllabogram (*21F) stays inside its word, and a listed word the lexicon reads must stand whole in an intact token on a tablet its entry cites |
| `test_skeleton_status.py` | `skeleton.SIGN_STATUS` uses only resolved, proposed and speculative, names table signs only, and (live) agrees with `sign_values.json`'s `resolution_summary` |

Run with `PYTHONDONTWRITEBYTECODE=1 uv run --with pytest python -m pytest tests/linear_a`.
