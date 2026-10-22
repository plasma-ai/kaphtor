# tools/core

Shared library for the Linear A tools: skeleton extraction, morphology, phonetic distance, null models, the Shoresh
root matcher and the data loaders. Every module imports from this repository alone. `frozen/` holds code kept byte
for byte at a pinned hash (see its README).

| Module | Purpose |
|---|---|
| `anatolian_morphology.py` | Conservative fuzzy Anatolian (Luwian/Hittite) morphology matching |
| `competitors.py` | Shoresh competitor null: the same statistics against the Luwian, Egyptian and Hurrian root lists |
| `contact_lexicon.py` | Contact-language lexicon loader, validator, normalizer and matcher |
| `corpus_utils.py` | Shared corpus word-extraction utilities |
| `data_cache.py` | Shared data cache and loaders, including `sign_value_entries` for sign values |
| `egyptian_morphology.py` | Conservative fuzzy Egyptian morphology matching via affix stripping |
| `greek_spelling.py` | Greek → Linear B CV spelling converter |
| `linear_b_slots.py` | Linear B administrative slot model for cross-script validation |
| `morphology_dispatch.py` | Language-aware morphology dispatcher |
| `normalization.py` | Semitic lexicon normalization and lookup |
| `null_model.py` | Permutation null models for hypothesis tests |
| `phonetics.py` | Weighted Levenshtein distance with language-specific sound-shift costs |
| `phrase_grammar.py` | Phrase grammar loader |
| `root_index.py` | Shoresh root index: every Semitic root key, projected into what Linear A can write |
| `root_match.py` | Shoresh: is a Linear A sign group closer to a Semitic root than chance, and to which root? The § and A ids in the Shoresh modules are glossed in [`SHORESH.md`](SHORESH.md) |
| `run_saver.py` | Run persistence, under the cache (`CACHE/linear-a/runs/`), never in the repository |
| `sedra.py` | SEDRA III ASCII to Syriac script and Latin notation |
| `semantic_gate.py` | Shoresh semantic gate: a word's context domains against a root's senses |
| `semitic_morphology.py` | Conservative fuzzy Semitic skeleton matching via affix stripping |
| `semitic_notation.py` | Per-source transliteration normalisers for Semitic root comparison |
| `semitic_root_schema.py` | Schema rules for `semitic_roots.json` |
| `shoresh_nulls.py` | Shoresh's pre-registered nulls, copied unchanged from the validation scripts: the root key and name test, the gold guard's spelling, decoy family B and the null A consonant permutation |
| `site_profiles.py` | Loader and validator for per-site language prior profiles |
| `skeleton.py` | Consonantal skeleton extraction from Linear A transliterations. `SIGN_STATUS` gives the standing of every value beyond Linear B: only AU is resolved, and the rest are proposed or speculative values |
| `types.py` | Domain types for the Linear A pipeline |
| `verb_morphology.py` | Verb-morphology deparser: exposes Semitic roots inside inflected forms |
