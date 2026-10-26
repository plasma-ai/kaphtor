# Shoresh: the ids in the code

Shoresh (`root_match.py`, `root_index.py`, `competitors.py`, `semantic_gate.py`) asks whether a Linear A sign group
is closer to a Semitic root than chance. Its test was specified before it was run on the gold set, and the code cites
that specification by section (§) and amendment (A). An amendment binds where it differs from a section. This page
says what each id fixes; the specification itself, with its baseline and dated amendments, is
[docs/shoresh-preregistration.md](../../docs/shoresh-preregistration.md), and how to build the index, run the command
and read its output is [docs/shoresh-usage.md](../../docs/shoresh-usage.md).

## Sections

| Id | Fixes |
|---|---|
| §0 | Why the engine reports calibrated p-values rather than raw distances |
| §1 | The statistic d\*(w): the minimum over root clusters, skeleton variants and keys of `weighted_levenshtein` (guttural-transparent, `SEMITIC_DISTANCES`) plus the variant's penalty. The verb and historical lenses stay out of d\*; onomastic clusters are out unless `--names` |
| §2 | Three decoy families per word, N = 1,000 each, seeded per word: A, sign shuffle; B, matched fabrication; C, sign-value permutation. p\_F = (1 + #{decoys with d\* ≤ d\*(w)}) / (1 + N\_F); the verdict uses p\_max over the families. Also the competitor null (Luwian, Egyptian, Hurrian) |
| §3 | Verdicts, first rule that applies: `UNINFORMATIVE` (≤ 2 consonants, or more than 90% of family-B decoys at d\* ≤ 0.3), `NO_SIGNAL` (p\_max ≥ 0.05), `CONVERGENT` (p\_max < 0.01, semantic fit, POS where a verbal parse is used, every competitor p\_max ≥ 0.05), else `PHONOLOGICAL_ONLY`. Report-only |
| §3.1 | The semantic gate fails closed: an unknown context is "no semantic evidence" and can never be `CONVERGENT` |
| §3.2 | A verbal-template parse counts only if the matched lexeme is a verb or participle |
| §4 | Success criteria on the gold set (positives, negatives, controls): recovery, discrimination, control false positives, calibration, real minus shuffled, speed |
| §5 | The baseline of the earlier matcher, measured before Shoresh |
| §6 | The amendments below |
| §7.3 | `build_root_index.py --diff`, read-only: record diff, key diff, the impact set (words whose d\* can change) and an impact preview |
| §7.7 | Long runs read a frozen copy of the data, not the live files |
| §8 | What the index holds, and how a lexeme joins a cluster: by `fk`, or by an exact sound link with gloss overlap |

## Amendments

| Id | Fixes |
|---|---|
| A1 | A word with fewer than 100 distinct sign orders reports family A as an order check, outside p\_max |
| A2 | The primary result is Linear A real-minus-shuffled minus Linear B real-minus-shuffled, with a bootstrap 95% lower bound above 0 |
| A3 | Family B is position-matched: initial, medial and final signs drawn from their own distributions, same sign count and skeleton length, OCP kept, never a corpus word |
| A4 | The primary key set leaves out a fixed list of index records (roots added to fit the corpus, and records with no Semitic-branch reflex); the full index is the secondary result |
| A5 | The gold set uses informative rows only (≥ 3 consonants); a word with an undecomposed sign is excluded with its reason, never shortened |
| A6 | Ranks are expected ranks under random tie-breaking; hit@5 and MRR are non-inferiority tests against the baseline |
| A7 | Discrimination is a paired bootstrap of the AUC difference against the baseline |
| A8 | Calibration is checked on 1,000 held-out family-B draws with randomised tie-breaking: KS at α = 0.01, share below 0.05 in [0.035, 0.065] |
| A9 | Planted-signal power: 200 Semitic roots spelled in Linear A orthography and queried like corpus words; a length bucket below 0.5 power is labelled underpowered |
| A10 | The semantic gate is part of the statistic: d\*\_sem over clusters whose meaning fits the context, computed the same way for every decoy |
| A11 | Shoresh's own distance table (`SEMITIC_DISTANCES` plus k ↔ ḫ at 0.3); every reading of a polyphonic sign is queried; the lenses stay out of d\* |
| A12 | d\* is taken over keys retrieved within one class edit, checked against an exhaustive search; branch breadth is reported, never scored |
| A13 | The gold set and baseline in use, with lexicon spellings aliased to corpus signs: `tests/fixtures/root_match_gold.v3.json` and `root_match_baseline.v3.json`, shipped as deposited |
| A14 | How planted words are spelled and chosen for A9; how A12 breadth is counted; gold-set words are never queried outside the gold run |
| A15 | The competitor null's keys, name exclusions, tables and statistic, and competitor power both ways |
| A16 | Tokenisation one letter at a time; ties compared on a 1e-9 grid; family A and C edge cases; the gold guard by name or reading |
| A17 | The OCP kept only if the real word keeps it; the A4 list read, never recomputed; an empty family enters p\_max at 1; at most 8 readings, primary first; root clusters only |
| A18 | The semantic gate's context (adjacent logogram by its conventional identification, then document type), the logogram and document maps, and the frozen domain tagger |
| A19 | Adjacency skips line breaks and dividers; spelling variants and fused logograms; controls scored under their positive's context |

## Other ids

| Id | Fixes |
|---|---|
| L6 | The earlier competing-language test (`null_model_audit.py`), whose key extraction, defaults and guttural transparency the competitor null keeps |
