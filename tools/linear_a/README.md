# tools/linear_a

The Linear A command-line tools. Each reads its data from `data/linear-a/` (contact lexica from `data/contact/`,
roots from `data/semitic-roots/`) through `tools/paths.py`; a tool whose dataset is not in the checkout names the file
it looked for and exits 2. Outputs, caches and saved runs go to `--out` or the user cache,
`$XDG_CACHE_HOME/kaphtor/` (else `~/.cache/kaphtor/`), never into the repository.

## Lookups

| Script | Purpose | Reads |
|---|---|---|
| `aegean_unicode_lookup.py` | Linear A and Linear B signs by value, token, codepoint or glyph; Linear A signs with no codepoint | `sign-registry.json`, `sigla-sign-map.json`, `linear-b-sign-map.json`; `linear_b_unicode_token_overlay.json` when present (not shipped yet) |
| `comparative_corpus.py` | The comparative Aegean and Near Eastern corpora: list, stats, search | `comparative_corpora/manifest.json` (not shipped yet) |
| `cretan_hieroglyphic_lookup.py` | Cretan Hieroglyphic signs, their Linear A correspondences and comparanda | `cretan-hieroglyphic/` (not shipped yet) |
| `egyptian_lookup.py` | The Egyptian contact lexicon by transliteration, root, hieroglyph or Gardiner number | `data/contact/egyptian_lexicon.jsonl`, `egyptian_roots.json` (not shipped yet) |
| `eteocretan_lookup.py` | The Eteocretan inscriptions and words, with the forged Psychro stone kept apart, and the Linear A lexicon entries that share a word's root | `eteocretan_inscriptions.json`, `eteocretan_word_analysis.json`, `lexicon.json` |
| `inscription_dating_lookup.py` | Inscription dates: by period, certainty, status or basis, or the inscriptions that write a given form | `inscription_dating_metadata.json` (not shipped yet), `corpus.json` |
| `linear_b_query.py` | The LiBER Linear B corpus: documents, ideograms, tokens, domains | `LINEAR_B_CORPUS_DIR`, else `linear_b_corpus/` (not shipped) |
| `lq.py` | DuckDB SQL over the data: raw queries, and `word`, `root`, `inscription`, `site`, `xref`, `field`, `tier`, `stats`, `audit`, `unread`. A view whose file is not in the checkout is left out, and a query that uses it names the file. Needs the `sql` extra | `lexicon.json`, `onomasticon.json`, `corpus.json`, `translations.json`, `unread_words.json`, `sign_values.json`, `semitic_roots.json`, `data/contact/` |
| `onomasticon_lookup.py` | The corpus onomasticon: one token, or entries by affiliation, type or provenance, and its counts | `onomasticon.json` |
| `phaistos_disc_lookup.py` | The Phaistos Disc: signs, groups, sides, patterns, positions, neighbours | `phaistos_disc.json`, `phaistos_disc_sign_map.json` (not shipped yet) |
| `sign_lookup.py` | One sign by AB number, phonetic value or codepoint, with each reading's status, polyphony and evolution | `sign-registry.json` |

## Search and analysis

| Script | Purpose | Reads |
|---|---|---|
| `analyze.py` | One inscription or a batch through skeleton, lexicon and cognate analysis; `--mode unknowns` lists frequent words with no lexicon entry | as `cognate_search.py` |
| `cognate_search.py` | Semitic and contact-language cognates for a word, a skeleton or a root (`--reverse`, which gives each corpus word's lexicon reading) | `corpus.json`, `lexicon.json`, `semitic_roots.json`, `data/contact/`; when present, `compound_morphemes.json`, `luwian_roots.json`, `egyptian_roots.json`, `verb_templates.json` and `data/ane/arabian_onomasticon.jsonl` (not shipped yet), else a lashon-ha-kretan checkout's corpus and roots (`LASHON_HA_KRETAN_DIR`) |
| `context_search.py` | Where a word, syllabic pattern or root occurs, with co-occurrence | as `cognate_search.py` |
| `hypothesis_test.py` | Cross-validated decode candidates tested against site, slot and neighbour evidence, with an optional null model | saved runs, `lexicon.json`, `corpus.json`, `linear-a-phrase-grammar/` |
| `logogram_analyzer.py` | Fifteen-section analysis of one logogram, or an audit of all | `sign_values.json`, `sign-registry.json`, `corpus.json`, `lexicon.json`; `site_language_profiles.json` when present (not shipped yet) |
| `build_root_index.py` | Builds, checks or diffs Shoresh's root index in the user cache (`CACHE/root_index.sqlite`). Until the Semitic contact lexica ship, build with `--allow-missing` | `semitic_roots.json`, `data/contact/` |
| `root_match.py` | Shoresh: is a sign group closer to a Semitic root than its own decoys (pre-registered in `tools/core/SHORESH.md`). Refuses gold-set words outside the gold run | the root index, the gold set `tests/fixtures/root_match_gold.v3.json`, `corpus.json`; the competitor lexica `luwian_roots.json`, `egyptian_roots.json` and `hurrian_roots.json` (not shipped yet: pass `--no-competitors`) |
| `sign_proposer.py` | Ranked candidate CV values for an undeciphered sign | `sign-registry.json`, `sign_values.json`, `corpus.json`, `missing_sound_map.json` (`--polyvalent`); `sign-evolution-map.json`, `rejected_sign_values.json` (not shipped yet) |
| `ventris_decode.py` | The Ventris Engine: statistics, grid, propagation, paradigms, ideograms, toponyms | `sign_values.json`, `corpus.json`, `lexicon.json`, `semitic_roots.json`, `morphemes.json` |
| `ventris_propagate.py` | Constraint propagation of sign values across the corpus | as `ventris_decode.py` |
| `ventris_runs.py` | Saved Ventris Engine runs: list, show, compare two, export one | the run cache, `CACHE/linear-a/runs/` |

`analysis/` holds the engine's phases, each also a command: `ventris_stats.py`, `ventris_grid.py`,
`ventris_paradigms.py`, `ventris_ideograms.py`, `ventris_toponyms.py`, `ventris_morphology.py`, and
`affix_doublet_miner.py`. Beside them: sign and spelling statistics (`sign_analysis.py`, `slot_grammar.py`,
`orthographic_audit.py`), the fraction signs (`fraction_arithmetic.py`), language-layer sweeps
(`luwian_detector.py`, `wy_isogloss_sweep.py`, `branch_distribution.py`, `amorite_grammar_sweep.py`,
`amorite_template_match.py`, `gordon_morphology_overlay.py`, `morphology_sign_constraints.py`), the Linear B name
bridge (`lb_onomastic_bridge.py`), and `lb_roc_calibration.py`, which writes the thresholds
`logogram_analyzer.py --calibrated` reads (pass `--output data/linear-a/lb_calibration_thresholds.json` to
install a run; the file it replaces is backed up first). By default outputs go to the user cache, not `data/`.

`validation/` holds `null_model_audit.py` (permutation nulls for the skeleton matcher and its lenses),
`root_match_phase0.py` (the Shoresh gold set and baselines; its `gold*` and `baseline*` commands write fixtures),
`root_match_checks.py` (the Shoresh pre-gold checks), the database and guttural audits (`db_composition_audit.py`,
`guttural_audit.py`, `guttural_compression_analysis.py`), `hapax_analysis.py`, `blind_corpus_test.py`, and
`check_unread_words.py`, which reports drift between `unread_words.json` and the corpus and writes nothing.
`--save` runs go through `tools/core/run_saver.py`, so `ventris_runs.py` lists them.

## Images, fetches and renders

| Script | Purpose | Reads, writes |
|---|---|---|
| `fetch_lgpn.py` | Lexicon of Greek Personal Names lookups, cached | network; `CACHE/lgpn/` |
| `fetch_sigla_drawings.py` | Mirrors the SigLA drawings named in the corpus. Needs the `fetch` extra | `corpus.json`; `CACHE/sigla/` |
| `inscription_image.py` | An inscription's photographs and facsimiles: list, open, copy, or a contact sheet, from a checkout of the image archive | `inscription_image_files.json`, `corpus.json`, `LASHON_HA_KRETAN_DIR`; `CACHE/linear-a/` |
| `render_sign_acrophony.py` | The CH → Linear A → Linear B → Semitic acrophony table | `sign-registry.json`; `cretan-hieroglyphic/`, `sign_acrophony_lineage.json` (not shipped yet); `--out` |
| `render_sign_chart.py` | Linear A glyph charts and the sign table. Needs the `render` extra | `sign_values.json`, `sign-registry.json`; `--out` |

Run one from the repository root, for example `uv run tools/linear_a/eteocretan_lookup.py --stats`.
