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
| `test_root_match.py` | Shoresh's engine (`root_match`): sign readings and tokens, d\*, the three decoy families and their edges, p and the verdict at its thresholds, breadth, POS, sound laws, the semantic gate in the engine, and A17; every index built in tmp_path from hand-written records |
| `test_competitors.py` | the competitor null (`competitors`): L6 keys and digraphs, the name test, the trie search against a naive minimum, the engine's competitor numbers, and the three shipped rival-language files (no Hurrian name among them) |
| `test_rival_roots.py` | the three shipped rival-language root files (`luwian_roots.json`, `egyptian_roots.json`, `hurrian_roots.json`): each file and its key space pinned by digest, every entry keyed, only the shipped fields, and a citation on every entry |
| `test_open_contact_lexica.py` | the open lexica in the root index's Syriac and Akkadian slots: each Syriac root is its Wiktionary letters read as `sedra.py` reads Syriac, Wiktionary's `name` is `proper_noun`, each Akkadian row is the CAMS/GKAB glossary's with ORACC's h written ḫ and every ORACC name class a `proper_noun`, and the index keys every row with a consonant |
| `test_fetch_sedra.py` | `fetch_sedra.py` on hand-made tables, offline: a row is a live lexeme with a Semitic or proper-name root, read in `sedra.py`'s Latin, with its English glosses once each, without Sedra's HTML, and names flagged; each row carries Sedra's etymologies, and only a lexeme `sedra_loans.json` rules a loan has the domain `loan`; the shipped rulings are well formed; requests wait the crawl delay and skip current files; a file unlike the manifest is deleted and stops the run; the overlay puts the build in the Syriac slot |
| `test_semantic_gate.py` | the semantic gate (`semantic_gate`): the logogram map and document-type table as ruled, word contexts, cluster domains, the frozen tagger, and every support string in the shipped corpus mapped |
| `test_root_index.py` | the root index (`root_index`) and `build_root_index.py`: record keys, candidates, lexeme links, staleness, diff, impact and preview, backups and the build contracts |
| `test_root_match_cli.py` | `root_match.py`, run in-process: reports, `--explain`, the gold guard by sign and by reading, `--sweep unread`, the stamped hashes, the worker pool, and exit 2, 3, 4 and 5 |
| `test_root_match_checks.py` | `validation/root_match_checks.py`: A9's speller, eligibility, power summaries and competitor plants, A12's report, the gold skip and the pool; neither check runs for real |
| `test_root_match_phase0.py` | `validation/root_match_phase0.py`: root parsing, skeletons and decoys, the gold guard, and fixtures that are never overwritten and never written from changed inputs |
| `test_shoresh_nulls.py` | `shoresh_nulls`: root keys, the name test and the decoy draws, pinned to the private originals' output on the same input (a two-document fixture) |
| `test_semitic_roots_v2.py` | the shipped `semitic_roots.json` (schema 2) reads as the records the root index keys on (`roots_records`), through `root_index.load_records` and `data_cache.semitic_roots`; a withheld reflex has no Analogues entry; the private list format passes through; another schema version is refused |
| `test_core_data_paths.py` | the `tools/core` loaders read from `data/linear-a/`, `data/contact/` and `data/semitic-roots/` (through `tools/paths.py`), a missing dataset is named (the site profiles and verb templates too), and saved runs go to the cache, not the repository |
| `test_lookups.py` | the `tools/linear_a` lookups, run as commands: Eteocretan counts that keep the forgery apart, notes and lexicon matches, no process wording; onomasticon tokens and filters; dating filters by period and corpus form; saved runs listed, shown, compared and exported from the cache; a missing dataset named with exit 2; and (data) the shipped files |
| `test_lq.py` | `lq`, run as a command: word and raw SQL queries, an inscription's confidence and every word's gloss, unread counts by verdict, a view or the lexicon not in the checkout named with exit 2, and (data) the shipped lexicon. Skipped without duckdb |
| `test_cognate_tools_read_the_lexicon.py` | `cognate_search`, `analyze` and `context_search` take a word's reading from `lexicon.json` and read no Gordon lexicon; lexicon lookups, word tokens, `root_match.py` naming a missing rival file with exit 2; and (data) `cognate_search` on the shipped lexicon |
| `test_run_index.py` | a saved `null_model_audit` or `guttural_audit` run leaves the run index listable by `run_type` (runs in a tmp folder) |
| `test_series_minimal_pairs.py` | `analysis/series_minimal_pairs.py`: a pair is two distinct words differing in one CV syllable with the same vowel, and a word a shuffle copies counts once; damaged, one-sign and non-syllabic words (logograms, ligatures, numerals, alternative readings) are left out; slot classes key on length, position and vowel, and the null's shuffle keeps every slot's series counts and the fixed signs; a planted alternation stands out and a planted separation falls short; p-values carry the +1 correction, and a pair the null never makes ranks first; a seed repeats its result; the command writes both files with the corpus's hash, reads the focus either way round, refuses a bad focus, an `--out` that is a file or inside `data/`, and any output already there, and exits 2 on a missing corpus; and (data) the shipped corpus's five D-T pairs |
| `test_analysis_units.py` | `gordon_morphology_overlay` strips sign subscripts in the stripped form; `lb_roc_calibration` calibrates a separating feature at its boundary, backs up the thresholds it replaces, and stops with exit 2 when the feature file is missing |
| `test_check_unread_words.py` | `check_unread_words`: role labels and readings that only spell the signs are not readings, a hyphen beside a bracket does not split a broken form, a speculative syllabogram (*21F) stays inside its word, and a listed word the lexicon reads must stand whole in an intact token on a tablet its entry cites |
| `test_skeleton_status.py` | `skeleton.SIGN_STATUS` uses only resolved, proposed and speculative, names table signs only, and (live) agrees with `sign_values.json`'s `resolution_summary` |

Most Shoresh tests are `data` tests: every index keys its records through the shipped correspondence table, every
word is read through the sign registry, and family B draws its decoys from the corpus. `shoresh_inputs.py` names the
nine files they read and skips them when one is not in the checkout. [`conftest.py`](conftest.py) gives every engine
built without contexts an empty one, and the command an empty corpus, unless a test is marked `live_contexts`.

Run with `PYTHONDONTWRITEBYTECODE=1 uv run --with pytest python -m pytest tests/linear_a`.
