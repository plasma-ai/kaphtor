# tools/linear_a/validation

Checks on the method and the data. Each is a command: run it from the repository root with `--help`. `--save` runs go
through `tools/core/run_saver.py`, so `ventris_runs.py` lists them.

| Script | Checks |
|---|---|
| `null_model_audit.py` | Permutation nulls for the skeleton matcher and its lenses |
| `root_match_phase0.py` | The Shoresh gold set and baselines; its `gold*` and `baseline*` commands write fixtures |
| `root_match_checks.py` | The Shoresh pre-gold checks (`docs/shoresh-preregistration.md`) |
| `meaning_shuffle.py` | The meaning-shuffle test; refused without its signed pre-registration (`--prereg`) |
| `meaning_shuffle_power.py` | The meaning-shuffle test's calibration and power, on fabricated and planted words only; writes `--out` |
| `blind_corpus_test.py` | Readings of untranslated inscriptions with the lexicon locked |
| `hapax_analysis.py` | The forms attested once |
| `db_composition_audit.py` | The make-up of the comparison databases |
| `guttural_audit.py`, `guttural_compression_analysis.py` | Whether guttural matches inflate the scores |
| `check_unread_words.py` | Drift between `unread_words.json` and the corpus; writes nothing |
