# tools/linear_a/analysis

The Ventris Engine's phases and the corpus analyses. Each is also a command: run it from the repository root with
`--help` for its options. Outputs go to `--out` or the user cache, never into `data/`.

| Script | Purpose |
|---|---|
| `ventris_stats.py` | Sign census and the statistics the engine starts from |
| `ventris_grid.py` | Sign-value confidence grid |
| `ventris_paradigms.py` | Morphological paradigm detection |
| `ventris_morphology.py` | Morphological feature analysis |
| `ventris_ideograms.py` | Readings tested against the logograms beside them |
| `ventris_toponyms.py` | Place-name hypotheses tested against the corpus |
| `affix_doublet_miner.py` | Pairs of corpus forms that differ by one affix, both attested |
| `sign_analysis.py` | Sign patterns across the corpus |
| `slot_grammar.py` | Positional profile of word sequences |
| `orthographic_audit.py` | Spellings checked against Linear B conventions |
| `series_minimal_pairs.py` | Word pairs differing only by consonant series (KU-DA / KU-TA), against a slot-matched null |
| `fraction_arithmetic.py` | Fraction-sign arithmetic |
| `morphology_sign_constraints.py` | Sign constraints from morphology and held-out validation |
| `branch_distribution.py` | Branch distribution of the lexicon and the census of conjugated verbs |
| `wy_isogloss_sweep.py` | The initial *w/*y isogloss, against a null model |
| `luwian_detector.py` | Corpus words closer to Luwian than to Northwest Semitic |
| `amorite_grammar_sweep.py`, `amorite_template_match.py` | The onomasticon against Amorite grammar and name templates |
| `gordon_morphology_overlay.py` | Gordon's morphology laid over the corpus |
| `lb_onomastic_bridge.py` | Names carried from Linear A into Linear B |
| `lb_roc_calibration.py` | Thresholds for `logogram_analyzer.py --calibrated`, calibrated on Linear B |
