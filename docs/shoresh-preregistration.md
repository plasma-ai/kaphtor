---
name: docs/shoresh-preregistration
title: "Shoresh (שֹׁרֶשׁ) Root-Match Engine"
desc: The full pre-registration of the Shoresh root-match engine, with its Phase 0 baseline and the dated amendments A1–A19.
tags: [docs]
authors: "di Mino"
status: "PRE-REGISTERED (engine built; no gold run)"
created: 2026-10-25T21:45:00Z
updated: 2026-10-26T00:26:00Z
---

# Shoresh (שֹׁרֶשׁ) Root-Match Engine

> [!NOTE]
> This is the pre-registration as written, with its amendment dates, which show that each amendment came before any
> engine number on the gold set. [SHORESH.md](../tools/core/SHORESH.md) glosses the section and amendment ids the
> code cites. The text names files by their paths in the research tree it was written in. In this repository they
> are:
>
> | Named here | In this repository |
> |---|---|
> | `lib/root_match.py`, `lib/root_index.py`, `lib/competitors.py`, `lib/semantic_gate.py`, `lib/phonetics.py`, `lib/phrase_grammar.py`, `lib/semitic_root_schema.py`, `lib/semitic_notation.py` | `tools/core/` |
> | `scripts/root_match.py`, `scripts/build/build_root_index.py`, `cognate_search.py`, `hypothesis_test.py` | `tools/linear_a/` |
> | `scripts/validation/` | `tools/linear_a/validation/` |
> | `scripts/maintenance/tag_semantic_fields.py` (sha256 7f7c5225) | `tools/core/frozen/tag_semantic_fields.py`, byte-identical |
> | `semitic_roots.json`, `semitic_correspondences.json` | `data/semitic-roots/` |
> | `corpus.json`, `lexicon.json`, `sign_values.json`, `luwian_roots.json`, `egyptian_roots.json`, `hurrian_roots.json` | `data/linear-a/` |
> | `tests/fixtures/root_match_gold.v3.json`, `root_match_baseline.v3.json` | the same paths, byte-identical |
> | `data/root_index.sqlite` | built locally, in `$XDG_CACHE_HOME/kaphtor/` (by default `~/.cache/kaphtor/`) |
>
> The text was written for two private research skills, and some of its wording ("both skills", "dual-written") and
> commands describe that setup. Not in this repository: the v1 and v2 fixtures, `cognate_search_golden.json`,
> `slot_grammar.json`, `campaign_workspace.json` (the project's log of findings), `linear-a-constraints.md`, the
> reference pages named in §§0 and 3.2, and the tests named in §7.6. `root_match.py --calibrate` (§§7.4, 7.6), the
> gold run, is not built yet.
>
> The index here is not the one the baseline and §8's counts (15 lexica, 80,314 lexemes, 113,990 keys) were measured
> on. This repository's index reads 11 contact lexica, leaving out as closed the CAD headwords, Gelb's Amorite
> glossary, Harding's Arabian names and the Phoenician drawn from the Anchor Bible commentaries. Of those 11, five ship
> ([data/contact/](../data/contact/_index.md)): Hebrew, Aramaic and Amarna Canaanite, and, in place of the private
> SEDRA Syriac and the Huehnergard-glossary and Anchor Bible Akkadian, open lexica in the same slots (English
> Wiktionary's Classical Syriac; ORACC's CAMS/GKAB glossary). The index is built with `--allow-missing`, and the roots
> file withholds the glosses and notes of closed sources. A joined lexeme's keys enter d\*, so d\*, p and the
> verdicts of a run here can differ from the private configuration's. Measured on the unread words
> (`root_match.py --sweep unread`: 470 listed, 3 gold-set words skipped, 141 refused under A5, 326 scored), with
> this repository's roots file under both: this index and one built from all eleven private lexica give every word
> the same verdict, 317 the same best cluster and 323 the same d\*, and p_max differs by more than 0.05 on 3. No
> gold-set word was run, so the gold run's numbers on this index are not measured.
>
> The frontmatter is this repository's. In the text, two lines differ from the original: §7.7's clone command, which
> named the private skill folders, and §4's sign-off, which named the author by first name. A blank line now opens
> each of five lists, which does not change how they render.

`cognate_search.py` answers *what is this close to*. Shoresh answers *is it closer than chance, to which root, through which sound laws, and does the meaning fit*. A sign group goes in. What comes out is a ranked set of **root clusters**: one Proto-Semitic number with its reflexes across branches. Each cluster carries empirical p-values from three decoy families, a check against competitor languages, and a verdict that is report-only.

Report-only means Shoresh never writes to the lexicon, `semitic_roots.json` or `campaign_workspace.json`. Every result enters at SPECULATIVE. Promotion stays with `hypothesis_test.py` and the four tests (`linear-a-constraints.md`).

This document was written **before the engine was built**. Sections 1–4 fix the statistic, the decoys, the verdict thresholds and the success criteria. They change only through a dated amendment in §6 that gives its reason, and never after gold-set numbers for the engine have been seen.

## 0. Why calibration, not distance

Distance alone is saturated, and that is the defect Shoresh exists to fix:

- **Blind corpus test.** At budget 0.3 with guttural transparency, the NWS skeleton database matches about 90% of any consonant sequence. The bulk score on the 24 never-cited inscriptions was Z=−0.72 against the sign-value-permutation null (`scripts/validation/blind_corpus_test.py`).
- **Bulk skeleton null, 2026-10-12.** 784 skeletons against 3,844 roots at d<0.3: real 69.9% vs random 67.9% ± 8.1, Z=1.95. This is not Bonferroni-significant.
- **Where signal does survive:** structured by position (peak-sanctuary formula, Z=5.99–8.39, `ref-peak-sanctuary-statistical-validation.md`) or at exact match with onomastica excluded.

A distance on its own is therefore not evidence. A distance that **beats the word's own decoys** is.

## 1. Test statistic (primary, pre-registered)

The primary statistic is

**d\*(w) = min over clusters c, over skeleton variants v of w, over keys k of c, of [weighted_levenshtein(v, k) + penalty(v)]**

- **weighted_levenshtein** is `lib/phonetics.weighted_levenshtein`, called with `guttural_transparent=True` and `SEMITIC_DISTANCES`.
- **The variants v** are the surface skeleton plus `_generate_morphophonological_skeletons`, with their existing penalties.
- **The keys k** are a cluster's PS radical keys (`ps_radical_keys`) and the radical keys of its reflexes in the `Analogues` field and in the linked contact lexemes.
- **The lenses** (verb, historical) are excluded from d\*. They are reported in their own sections, as in `cognate_search`.
- **Onomastic clusters** (Amorite, Arabian and Phoenician onomastica) are excluded unless `--names` is passed. The blind test found signal only with the Amorite name list excluded.

For each word, the same retrieval radius, variant set and key set apply to the real word and to every decoy. Uniqueness is reported but stays out of d\*. It is k(d\*), the number of clusters with distance ≤ d\* + 0.05, and ranking is tie-aware.

## 2. Decoy families and p-values

Each word gets N = 1,000 decoys per family by default. The seed is `sha256(seed ‖ word)`, so the decoys are reproducible for each word and do not depend on batch order.

| Family | Construction | Controls for |
|---|---|---|
| **A. Sign shuffle** | Permute the word's own signs. When the word has fewer distinct permutations than N, use all of them, and report the real decoy count and the p-floor 1/(1 + n). | Consonant inventory. Same multiset, wrong order. |
| **B. Matched fabrication** | Same sign count. Signs are drawn from corpus sign frequencies (`null_model_audit.load_corpus_words`). Vowel-only signs (hidden guttural or onset slots) stay in their original positions. A decoy is rejected if it puts identical consonants next to each other where the original has none (OCP), or if it is a real corpus word. | Length and onset structure, with the 48.6% guttural density preserved. This replaces the v1 independent-consonant generator, which violated the OCP. |
| **C. Sign-value permutation** | Apply `blind_corpus_test.permuted_cons_map` to the same sign sequence. | The sign-value grid itself. Does the reading system beat a scrambled one? |

The p-value for each family is

p\_F = (1 + #{decoys with d\* ≤ d\*(w)}) / (1 + N\_F)

The verdict uses **p\_max = max(p\_A, p\_B, p\_C)**, the most conservative of the three. Batch runs also report Benjamini–Hochberg q over p\_max.

**Competitor null.** d\* and p\_max are recomputed against the Luwian, Egyptian and Hurrian indexes, each with its own distance table (`LUWIAN_DISTANCES`, `EGYPTIAN_DISTANCES`). The competitor margin is reported per word, as the per-word counterpart of the L6 competing-language test.

## 3. Verdicts (report-only, never tiers)

The first rule that applies wins:

| Verdict | Condition |
|---|---|
| `UNINFORMATIVE` | The skeleton has ≤ 2 consonants, **or** more than 90% of family-B decoys reach d\* ≤ 0.3 (saturated neighbourhood). |
| `NO_SIGNAL` | p\_max ≥ 0.05 |
| `CONVERGENT` | All four hold: p\_max < 0.01; the top cluster's meaning is compatible with the word's context (§3.1); POS is consistent where a verbal parse is used; and every competitor has p\_max ≥ 0.05. |
| `PHONOLOGICAL_ONLY` | Any other result with p\_max < 0.05. |

**3.1 Semantic fit fails closed.** Context means three things: the adjacent logogram, the slot role (`lib/phrase_grammar.py`, `data/comparative_corpora/linear_a/slot_grammar.json`) and the document type. The cluster's meaning is tagged with the domain tagger in `scripts/maintenance/tag_semantic_fields.py`.

- If the context is unknown, the result is "no semantic evidence". It is not counted as a mismatch, and it cannot be `CONVERGENT`.
- This gate stops KU-RO "total" from coming back as \*kur- "ball".

**3.2 POS.** A verbal-template parse counts only if the matched lexeme's POS is `verb` or `participle`. PS clusters carry no POS of their own and inherit it from their linked contact lexemes. This targets the 64% false-discovery rate the verb lens showed (`ref-verb-morphology-lens.md`).

## 4. Success criteria on the gold set

**The gold set** is `tests/fixtures/root_match_gold.json`, built by `scripts/validation/root_match_phase0.py gold`. It has three parts:

- 82 positives: tier ≥ 3 Semitic lexicon entries with a parseable root;
- 33 negatives: 15 REJECTED, plus 18 entries on a non-Semitic layer at tier ≥ 2;
- 164 controls: one sign shuffle and one corpus-frequency fabrication per positive.

The positives were found by the old matcher, so they are circular. **They measure recall only.** False-positive rates come from the negatives and the controls.

Controls inherit the context of the positive they were made from. That way the `CONVERGENT` gate is tested under the same conditions as the real word.

Shoresh passes when all of the following hold:

1. **Recovery is not worse.** Exact-key hit@5 and MRR on positives are ≥ the Phase 0 baseline (§5). Reflex indexing must not cost any PS recovery.
2. **Discrimination is better.** The AUC of p\_max, positives against fabricated controls, is greater than the baseline AUC of best PS distance against the same controls.
3. **Control false positives.** At most 5% of the controls (sign-shuffle and fabricated pooled) come out `CONVERGENT`.
4. **Calibration.** p\_B on the fabricated controls is approximately uniform: a KS test against U(0,1) at α = 0.01 does not reject, and the share with p\_B < 0.05 lies in [0.02, 0.08].
5. **Real minus shuffled.** The share of positives with p\_max < 0.05, minus the share of sign-shuffle controls with p\_max < 0.05, is reported. It must be greater than 0. This is the figure that matters.
6. **Speed.** A warm query without the null takes under 250 ms. A query with N = 1,000 for all three families takes under 5 s.

Results go to `campaign_workspace.json` as a technique finding, with di Mino's sign-off, dual-written.

## 5. Phase 0 baseline (measured, pre-Shoresh)

The baseline is `tests/fixtures/root_match_baseline.json`, from `root_match_phase0.py baseline`. It measures the Proto-Semitic layer of `cognate_search.search_cognates(use_cache=False)`.

The shim regression target is `tests/fixtures/cognate_search_golden.json`: 200 corpus words in two flag configs. The Phase 3 shim must reproduce it exactly.

**Input state.** Skill HEAD `bec4f346`, `semitic_roots.json` sha `b3eb5faa` (3,787 records), `lexicon.json` sha `cc975aaf`, seed 20261016. All three fixtures were built in one pass on a frozen snapshot (§7.7), 2026-10-16 14:55–15:41 EDT. The full input hashes are in each fixture's `provenance`.

**Gold set.** 81 positives, 33 negatives (18 non-Semitic layer, 15 REJECTED), 162 controls (81 sign shuffles, 81 fabrications), 46 excluded with reasons.

**Root recovery** (positives, top 20 PS matches):

| Key match | hit@1 | hit@5 | hit@20 | MRR |
|---|---|---|---|---|
| Exact | 0.222 | 0.358 | 0.457 | 0.288 |
| Guttural-folded | 0.272 | 0.457 | 0.519 | 0.356 |

| Skeleton length (exact) | n | hit@1 | hit@5 | MRR |
|---|---|---|---|---|
| 2 | 32 | 0.031 | 0.219 | 0.117 |
| 3 | 32 | 0.406 | 0.469 | 0.454 |
| 4+ | 17 | 0.235 | 0.412 | 0.296 |

**Discrimination** (best PS distance; AUC = P(positive closer than control), ties count half):

| Class | n | AUC vs positives | Share with a match at d < 0.3 |
|---|---|---|---|
| Positives | 81 | — | 0.802 |
| Sign shuffle | 81 | 0.538 | 0.691 |
| Fabricated | 81 | 0.566 | 0.704 |
| Non-Semitic layer | 18 | 0.595 | 0.778 |
| REJECTED | 15 | 0.577 | 0.667 |

**Latency.** CLI, cold process, all ten language flags, `--no-cache`, 20 words: p50 7.45 s, p95 10.36 s, max 10.65 s, peak RSS 461.5 MB. Machine load average was 5.7–6.8 from concurrent sessions. An in-process call with the cache off takes 6–13 s.

**Reading.** The positives were found by this matcher, so they are circular, and it still separates them from shuffles of their own signs at AUC 0.54. Seven in ten shuffles and fabrications get a PS match at d < 0.3. The real-minus-shuffled margin at d < 0.3 is 11.1 points, and §4 criterion 5 is measured against it. A 1,000-decoy null at today's cost would take more than two hours per word.

**Baseline v2** (§6 A2–A7). This is `tests/fixtures/root_match_baseline.v2.json` on `root_match_gold.v2.json`, both built on one frozen snapshot of both skills (§7.7), 2026-10-16 20:45 UTC, with `semitic_roots.json` sha `42167a4e` (3,783 records). The gold set holds:

- 76 positives, 49 of them informative and 35 informative with Linear B values only;
- 31 negatives (17 non-Semitic layer, 14 REJECTED);
- 128 controls, with 24 left as logged gaps;
- 197 Linear B Greek negatives, 4 Semitic loans and 201 Linear B shuffles;
- 157 exclusions, 116 of them for unmapped signs, mostly Linear B WO, JO, QO and ZO, which have no Linear A value.

| Recovery, expected rank | n | hit@1 | hit@5 | hit@20 | MRR |
|---|---|---|---|---|---|
| All positives | 76 | 0.224 | 0.421 | 0.500 | 0.304 |
| Informative | 49 | 0.327 | 0.469 | 0.551 | 0.390 |
| Informative, Linear B values only | 35 | 0.371 | 0.486 | 0.543 | 0.425 |

| Class (informative) | n | Share with a match at d < 0.3 | AUC vs informative positives [95% CI] |
|---|---|---|---|
| Positives | 49 | 0.673 | — |
| Sign shuffle | 48 | 0.479 | 0.621 [0.505, 0.722] |
| Fabricated (position-matched) | 45 | 0.533 | 0.611 [0.496, 0.720] |
| Linear B Greek | 197 | 0.482 | 0.642 [0.561, 0.724] |
| Linear B shuffles | 201 | 0.478 | 0.648 [0.559, 0.729] |
| Linear B Semitic loans | 4 | 0.750 | 0.421 [0.184, 0.673] |

**Real minus shuffled at d < 0.3.** Linear A gives +0.194 (49 real, 48 shuffled) and Linear B +0.010 (197 against 197). The difference is +0.184, with a 95% interval of [−0.039, 0.392]. The old matcher gives Greek vocabulary a Semitic match as often as it gives one to Greek shuffles. Linear A beats its shuffles by 19 points, but at this n the gap over Linear B is not separable from zero.

**Baseline v3** (§6 A13) supersedes v2 as the reference. It is `root_match_baseline.v3.json` on `root_match_gold.v3.json`, one frozen snapshot of both skills, 2026-10-16 21:15 UTC, `semitic_roots.json` sha `42167a4e`. Against v2:

- PI-\*34-TE (p-q-t) and \*34-TI-RI (q-t-r) enter through the QI → \*34 alias. SI-DU-\*34-KU-MI now maps but stays out, because its root `ṣ-d-q + Hurrian -kummi` is not a parseable key.
- Lexicon edits since v2 dropped AU-TA (now tier 1) and the negative SU-KI-RI-TE-SE-JA.
- That leaves 77 positives (51 informative, 35 of them Linear B values only), 30 negatives, 126 controls with 28 gaps, the same 197 + 4 + 201 Linear B rows, and 155 exclusions.

| Measure (informative) | v2 | v3 |
|---|---|---|
| hit@5 / MRR, n | 0.469 / 0.390, 49 | 0.471 / 0.394, 51 |
| Share at d < 0.3: positives, sign shuffles, fabricated | 0.673, 0.479, 0.533 | 0.686, 0.449, 0.489 |
| AUC vs Linear B Greek [95% CI] | 0.642 [0.561, 0.724] | 0.645 [0.562, 0.720] |
| Real minus shuffled: Linear A, Linear B | +0.194, +0.010 | +0.237, +0.046 |
| Difference A − B [95% CI] | +0.184 [−0.039, 0.392] | +0.192 [−0.028, 0.395] |

A2's criterion is measured against the v3 figure.

## 6. Amendments

**2026-10-16, A1–A12** (A13–A19 follow). These come from a five-reviewer audit of Phase 0 and Phase 1, held before any engine existed. They were adopted before baseline v2 (§5) was measured, and no engine number has been seen. Where an amendment and §§1–4 disagree, the amendment binds.

| # | Replaces | Rule | Reason |
|---|---|---|---|
| A1 | §2 p\_max | For a word with fewer than 100 distinct sign orders, p\_A is reported as an order check and left out of p\_max, so the verdict uses max(p\_B, p\_C). From 100 orders up, p\_max = max(p\_A, p\_B, p\_C) as before. | Family A's floor of 1/n makes the verdicts unreachable. 61 of 81 v1 positives could never get below 0.05, and only 4 below 0.01. The controls had the same floors, so criteria 3 and 5 passed without testing anything. |
| A2 | §4 criterion 5 | The primary result is **Linear A real-minus-shuffled minus Linear B real-minus-shuffled**. Each margin is the share of informative real words with p\_max < 0.05 minus the share of their own shuffles. Shoresh passes if the bootstrap 95% lower bound (2,000 seeded resamples) is above 0. The Linear B Greek negatives join the criterion 3 pool. The four Mycenaean Semitic loans are reported without a pass mark (n = 4). The full-corpus p\_max distribution is reported against U(0,1). | Positives are sign orders analysts already matched, and the variant rules key on position (I-nun, III-weak, +n). Any real language would beat its own shuffles. Linear B goes through the same orthography and is known to be Greek, so it measures that effect. |
| A3 | §2 family B | Family B is position-matched. Initial, medial and final signs are drawn from their own corpus distributions. The decoy keeps the word's sign count and skeleton length, keeps the OCP, and is not a corpus word. The generator is `root_match_phase0.fabricate`, the same function that made the gold v2 fabrications. | The v1 family B drew the final sign from global frequencies, which hands the positional morphology (‑NA, ‑TI, ‑JA) to the real word for free. The v1 gold fabrications came from a third generator. |
| A4 | §1 key set | The primary statistic runs on the index minus gold v2's `primary_index_exclusions`: 35 campaign additions (Numbers 2964–2998) and 24 records with no Semitic-branch reflex, such as 2968 \*mīnōs-, which has only a Greek analogue. The full index is the secondary result. Among the positives, the primary stratum is `lb_values_only`: no sign whose value the campaign resolved (`sign_values.json` `resolution_summary`, phonemic). | No decoy can detect a target set that was fitted to the corpus. Such roots enter only as a secondary result. |
| A5 | §4 gold set | The gold set is `root_match_gold.v2.json`. Criteria 2–5 use informative rows only (≥ 3 consonants). Shuffles never repeat their source's skeleton, and no control repeats any skeleton in the set. A word with a sign that has no decomposition is excluded with its reason and never shortened. PI-QI-TE stays out until QI's identity is settled. REJECTED entries are reported descriptively and are not false-positive evidence. | v1 had 32 positives of ≤ 2 consonants, 10 shuffles that duplicated their source's skeleton (A-KA-NU → NU-KA-A), and PI-QI-TE silently read as p-t. REJECTED entries were proposed because they matched. |
| A6 | §4 criterion 1 | Ranks are expected ranks under random tie-breaking over the full PS list, B + (T + 1)/(G + 1). Shoresh must reach hit@5 and MRR of at least baseline v2 minus 0.05 on informative positives (non-inferiority, about two words at n = 49). | KU-NI-SU, KU-RO and KI-RO sat at distance 0 with a full top 20 and still had no rank, because the top-20 cut breaks ties by Number. |
| A7 | §4 criterion 2 | A paired bootstrap of the AUC difference (Shoresh p\_max against baseline v2 best distance, the same rows) on fabricated and Linear B controls. Shoresh passes if the point estimate is above 0 and the 95% lower bound is above −0.05. | At 81 against 81 the AUC's standard error is about 0.045, so a bare "AUC > 0.566" can pass on noise. |
| A8 | §4 criterion 4 | Calibration is checked on 1,000 held-out family-B draws, not on gold rows, with randomised tie-breaking: p = (#{d < d\*} + U·(#{d = d\*} + 1)) / (N + 1). It passes if KS against U(0,1) at α = 0.01 does not reject and the share below 0.05 lies in [0.035, 0.065]. | At n = 81, even a calibrated p misses [0.02, 0.08] about 19% of the time. Ties at d\* = 0 make an untied p super-uniform. |
| A9 | before any gold run | **Planted-signal power.** 200 PS keys attested in ≥ 2 Semitic branches and linked to no Linear A lexicon entry are spelled in Linear A orthography: CV signs, codas omitted, gutturals optional. They are queried like corpus words. Power is the share with p\_max < 0.05, by skeleton length. A length bucket with power below 0.5 is labelled underpowered in every report, and competitor power is reported the same way. | The key set grew from about 3.8k to 114k keys, so ties pile up at d\* = 0. No power analysis existed. |
| A10 | §3.1 | **The semantic gate is part of the statistic.** d\*\_sem is the minimum over clusters whose meaning fits the context. It is computed the same way for every decoy, and `CONVERGENT` requires p on d\*\_sem < 0.01. Context means the adjacent logogram and the document type. The slot role from `phrase_grammar` is shown but does not count, because it was built on the project's own readings. | Without this, the p-value covers "some cluster at d\*" and the meaning check then picks among many tied clusters after the fact. |
| A11 | §1 scoring | Shoresh rescores with its own table: `SEMITIC_DISTANCES`, plus k ↔ ḫ at 0.3, the cost of t ↔ ṯ. `SEMITIC_DISTANCES` itself stays unchanged, so `cognate_search` and its golden record are untouched. **Polyphony:** every reading of a polyphonic sign is queried and d\* is the minimum over readings. Families A and C apply the same expansion, and family B keeps the word's number of polyphonic slots. **Lenses:** `_generate_historical_skeletons` stays out of d\*. This document binds where the plan differs. | Linear B ku-ru-so < ḫurāṣu writes ḫ with the K series, but k ↔ ḫ cost 1.0. Polyphony had not been pre-registered, so a polyphonic real word got extra chances. The metathesis variants partly recreate shuffles. |
| A12 | §1 retrieval | d\* is the minimum over keys retrieved within one class edit (`RootIndex.candidates`), not over all clusters. Before the gold run it is checked against brute force on 500 corpus queries, and every miss is listed. Branch breadth is reported against the decoys' top-cluster breadth and as a gloss-free count. Which family decides p\_max is reported per word. | Cheap cross-class pairs plus one omission fall outside radius 1, as in "tk" against ṯ-k-l. The test stays valid because real and decoy words are retrieved alike. Gloss agreement varies by lexicon, from Aramaic at 24.6% to CAD at 1.9%, so gloss-gated breadth leans toward Northwest Semitic. |
| A13 | A4–A7 gold set and baseline | **2026-10-16, after baseline v2, before any engine number.** The gold set is `root_match_gold.v3.json` and the reference baseline is `root_match_baseline.v3.json`. Wherever A4–A7 name gold v2 or baseline v2, read v3. v3 rewrites lexicon spellings of campaign values in corpus signs (`LEXICON_SIGN_ALIASES`, QI → \*34, checked against the `resolution_summary` entry "\*34=QI"), and keeps the lexicon spelling as `lexicon_word`. Linear B's QI is AB21 and is not aliased. | The lexicon writes PI-QI-TE where the corpus writes PI-\*34-TE, and the \*34 record cites these very words. A5's hold on PI-QI-TE was a builder gap, not an open sign identity. |
| A14 | A9 spelling, A12 breadth | **2026-10-16, after the A12 check ran, before A9 and before any p or verdict on a gold word.** **A9 eligibility:** a record qualifies if it is in the primary index (A4), has a PS key and has reflexes in ≥ 2 Semitic branches, and if no PS or weak key of it (gutturals folded) is named in a lexicon `root` field, the parts of compounds included (b-ṭ-n + š-m-n). The planted key is the record's first PS key. **A9 spelling:** the pattern is the headword's first alternative. Parenthesised segments drop out, the first of two slash alternatives stays, ə reads e, and the key's radicals fill the consonant slots. A headword with no vowel, or with consonant slots that do not match the radicals, is spelled open: each radical takes a vowel drawn from a, i, u. A trailing hyphen adds an ending vowel from a, i, u. A consonant before a vowel is written as a CV sign and a coda is omitted. Only grid signs whose engine value is their Linear B value are used: D K M N P R S T with five vowels, J Q Z with a and e, W with a e i. A consonant with no series takes its cheapest substitution, ties broken by shadow class: b → P, g → K, l → R, š ś → S, ṭ → T, ṣ ṯ ḏ ẓ → Z. ʾ ʿ h ḥ are written as a bare vowel sign. ḫ and ġ are written with the K series or as a bare vowel, by a coin. A vowel the series lacks becomes one it has. Every draw is seeded by Number. Each planted word is queried with every cluster kept, and the report gives beside power whether the planted Number is among the clusters at d\*. **A12 breadth:** a branch counts once per cluster. Gated breadth is the record's own reflex branches plus the language of every lexeme that joins the cluster (§8: fk, or an exact sound link with gloss overlap). Gloss-free breadth is the record's own reflex branches plus fk-joined lexemes only. PS and non-Semitic keys are no branch. A word's breadth is that of its broadest cluster at d\*, and it is reported as the share of family-B decoys whose broadest cluster at their own d\* is at least as broad, leaving out decoys with no retrieved key. Breadth never enters p or the verdict. **Gold overlap:** the A12 check's 500 corpus queries held 54 gold words (42 positives, 7 negatives, 4 excluded, 1 control). For these only retrieved and brute-force d\* were computed, with no decoy, p or verdict, and none was among the four misses. From here on no check queries a gold-set sign group: a word in any section of the gold set, in corpus or lexicon spelling, compared sign by sign with subscripts read as digits. An A12 rerun skips such words and counts them. A9 draws eligible records in a seeded order and sets aside any planted spelling that is a gold-set sign group, lists it in the report and plants the next record in its place. The gold set is a hashed input of both reports. | A9 fixed "CV signs, codas omitted, gutturals optional" but not the vowels, the sign set, the eligibility test or which gutturals. A11 already prices k ↔ ḫ at 0.3, and ʾ ʿ h ḥ have no cheap series. A12 named both breadth counts without defining them, and the first build counted the PS headword as a branch, one too many for every cluster. A12 drew its sample from the corpus without screening the gold set. Its d\* on those rows is the kind of number baseline v3 already reports for every gold row. `root_match.py` now refuses gold words. |
| A15 | §2 competitor null | **2026-10-16, before A9 and before any p on a gold word.** **Keys:** each entry's `Consonantal_Root` in `luwian_roots.json`, `egyptian_roots.json` and `hurrian_roots.json`, through L6's `_extract_consonantal_root`, with every vowel and the ⸗ boundary first marked so the consonants on either side are tokenised apart. A key must be letters only, with at least two tokens. **Names** are out unless `--names`: L6's `_is_onomastic`, the Hurrian personal, royal, divine, name-element and toponym categories, Egyptian entries with name elements, and toponyms. **Tables:** `LUWIAN_DISTANCES`, `EGYPTIAN_DISTANCES`, and for Hurrian `SEMITIC_DISTANCES`, weighted_levenshtein's default as in L6. All three are guttural-transparent, as in L6. **Statistic:** the search is exact over every key. Each competitor takes the real word's readings, its variants and the Semitic test's own decoys, with the §2 p formula, A1 and p\_max over the families that count. Reported per word: d\*, per-family p, p\_max, the nearest key, the margin (lowest competitor p\_max minus the Semitic p\_max) and `semitic_specific` (Semitic p\_max < 0.05 and every competitor p\_max ≥ 0.05). **A9 competitor power**, both ways. Cross-talk is the share of Semitic plants, per skeleton length, on which a competitor reaches p\_max < 0.05. Own power takes, for each competitor, up to 200 of its keys in a seeded order, spelled open (A14) with each consonant's series chosen on that competitor's own table and gutturals by the script's rule. A key with a consonant that no series writes below cost 1.0 is counted and not planted. Power is the share with that competitor's p\_max < 0.05, and a bucket below 0.5 is labelled underpowered. The Semitic p\_max on these plants is reported too, and the A14 gold set-aside applies. | §2 named the indexes and tables but not the keys, the names, the transparency, or what competitor power measures. `hurrian_roots.json` holds 717 Nuzi personal names among 947 entries and 427 OCR-damaged keys. Tokenising after vowel removal makes false digraphs: tessub became ṣ s b. L6 is the counterpart §2 names, so its extraction, defaults and transparency are kept. A competitor gate that cannot fire passes every word, and own power shows whether it can. |
| A16 | A11 tokens, §2 ties and decoys, A14 guard, A5 informative, §3.2 POS | **2026-10-17, before A9 and before any p on a gold word.** **Tokens:** every key, skeleton and variant is tokenised one letter at a time. A letter with its combining marks is one token, no two letters merge, subscript digits drop (Sabaic s₁ is s), and x, ʁ and γ read as ḫ, ġ and ġ, the index's own guttural classes. The §1 morphophonological rules apply to these tokens in `cognate_search`'s order and with its penalties. Competitor keys follow the same rule, except that Luwian and Hurrian keep their bare-letter digraphs ts, sh, kw and gw, which `LUWIAN_DISTANCES` prices as units. A letter with a mark never joins a digraph, and Egyptian has none. Family B counts skeleton length and the OCP on the same tokens. **Ties:** every distance-plus-penalty sum is compared on a 1e-9 grid, so a decoy whose sum equals d\* is a tie however it was reached (§2's ≤). **Family C:** a polyphonic sign's alternate readings are redrawn until they differ from its other readings, as the real word's do. **Family A:** a word of one sign repeated has no other order and no family-A decoy. **Gold guard (A14):** a word is a gold-set sign group by name or by reading, each sign's readings as the engine reads them, so KU2-RO, KU-RO9 and KU-\*310-SU are held back with KU-RO and KU-NI-SU. A gold file without its seven sections as non-empty lists refuses every word. Words are queried in canonical spelling. **Gold set (A5):** gold v3 stays as built and hashed. Its `skeleton_len` and `informative` fields were counted with the old tokeniser, so at the gold run every row's consonant count, and with it `informative` (≥ 3), is recounted on the engine's tokens; the stored fields are not rewritten. 16 rows change length and 6 cross the line, each from 2 to 3: the negative TU-SU-PU₂, the control JA-TA-SE, and the Linear B shuffles RO-A-KO-WE, A-NU-KO-WI, KU-WE-RE and TE-SU-RA. **POS (§3.2):** no Shoresh variant is a verbal-template parse (the verb lens is outside d\*), so the POS condition holds vacuously. Each cluster shows the POS its joined lexemes give it, for display only. | The shared tokeniser read joined strings, so k+w became kw, t+s became ṣ and s+ḥ became š. KU-WA-NA could not retrieve \*k-w-n, and a T-S word lost a consonant, so a three-consonant word could fall to UNINFORMATIVE: 2,395 index keys were merged this way. A further 4,478 South Arabian keys carried a subscript token priced as a consonant, and Egyptian msḥ was m š. A15 fixed the vowel gaps only. Float sums broke ties: 0.1 + 0.1 + 0.1 exceeds 0.3, so tied decoys counted above d\*, p came out anti-conservative and saturation undercounted. The guard compared sign names while the engine reads values, so 184 gold sign groups had an unguarded twin, none of them queried. Gold v3 was built with the same tokeniser; recounting at the gold run keeps the deposited file and its hash. One test lifted the guard on KU-RO with the competitor null on: competitor d\* and p for KU-RO, on a synthetic Semitic index, were computed on each test run, captured by pytest and never displayed. That exposure is recorded here and does not freeze the amendments. The test now uses a synthetic gold word. A12 shares the engine's tokens, so it is rerun on a fresh snapshot. |
| A17 | A3 OCP, A4 key set, §2 p\_max, §3 saturation, A11 readings, §8 clusters | **2026-10-17, after the A16 rerun of A12, before A9 and before any p on a gold word.** **OCP (A3):** family B keeps the OCP only if the real word keeps it. A word with two identical consonants side by side gets decoys that may have them too (`fabricate(..., ocp=False)`); the gold builder's default is unchanged. **A4:** the primary key set leaves out the gold set's frozen `primary_index_exclusions` (gold v3, equal to v2's, A13), read and never recomputed. A listed Number the index no longer holds is reported (`a4_absent`). A gold file without the list refuses the primary result; `--full-index` still gives the secondary one. **p\_max (§2):** a family that counts and built no decoy enters p\_max at p = 1, and the report says so. The competitor null follows the same rule. **Saturation (§3):** the gate is always checked. When family B is not among the requested families it is still drawn, for the gate only, and stays out of p\_max. **Readings (A11):** at most 8 readings of a polyphonic word are queried, primary first (`MAX_READINGS`), and a word with more says how many it has. **Clusters (§8):** the statistic runs on root clusters only. A lexeme joins a cluster by `fk`, or by `root_key_exact` with gloss overlap. Any other lexeme is never a cluster and never enters d\*, p or breadth; it is shown as "possible cognate of N", or as unlinked. | Family B's OCP rejected every geminate decoy, so a geminate word (KA-NA-NA for \*knn, one of A9's spellings) stood out from its own decoys and A9 would overstate power on it. The code recomputed A4's list from live data while A4 names a fixed list; they agree today (59 Numbers), but the roots file is merged and renumbered daily. An empty family B silently left p\_max, the anti-conservative direction: on a test index, KA-NA-SI with no family-B decoys came out at p\_max 0.0099 (PHONOLOGICAL\_ONLY) where p\_B = 1 gives NO\_SIGNAL. Saturation was skipped under `--families AC`, so UNINFORMATIVE could not fire there. A11's "every reading" was capped at 8 in the code. §8 left unjoined lexemes as their own clusters; on the 2026-10-17 snapshot that would add 19,845 keys to the engine's 9,666, 13,373 of them from lexemes with no link at all, and A9 and A12 have measured only root clusters. |
| A18 | A10 semantic gate, §3.1 | **2026-10-17, before A9 and before any p on a gold word.** **Context** is a word's adjacent logogram and its document type (A10), read from `corpus.json`. **Adjacent logogram:** the logogram immediately after the word, ligatures pooled with their base sign. It counts only by its conventional identification, anchored outside this project (Linear B ideograms, GORILA conventions); the project's own readings of a logogram never count. The map: GRA → agriculture, food\_drink; CYP → flora, food\_drink; OLE → food\_drink, agriculture; VIR → administrative, kinship; VIN → food\_drink, agriculture; OLIV → flora, food\_drink, agriculture; \*21M, \*22F, \*22M, \*23M → fauna; HIDE → fauna, textile; \*131B, \*131C (GORILA's wine class) → food\_drink; \*118 (Linear B TALENT) → metrology, metallurgy, and NI (Linear B FIC) → flora, food\_drink, each only where it stands as a logogram followed by a number. Single syllabograms after a word count for nothing. **Document type:** stone vessel, libation table, metal, stone and ivory objects → ritual\_cultic, deity; clay vessel, pithoid jar, inked inscription → pottery\_vessel, food\_drink; tablets, lames, bars, roundels, nodules, sealings, architecture, graffiti, stelae and clay reels → unknown. **Combination:** a mapped adjacent logogram gives its own domains only; otherwise the document type's; otherwise the context is unknown ("no semantic evidence", §3.1). **Multiple attestations:** a word's context is the union of the domains its attestations give; an attestation with an unknown context adds nothing, and a word whose every attestation is unknown has no semantic evidence. **A cluster's domains** are those `classify()` in `scripts/maintenance/tag_semantic_fields.py` (sha256 7f7c5225 at this amendment, frozen with it) gives the record's Meaning together with the glosses of its joined contact lexemes (§8; onomastica out). A cluster with no domain never fits. **Fit:** a cluster fits when its domains meet the context's. d\*\_sem is the minimum over fitting clusters; every decoy is gated by the real word's context and scored the same way, in every family, and p on d\*\_sem follows the §2 counting rules (A17 included). **Known noise, accepted:** a heading or recipient word before a logogram (HT 13 KA-U-DE-TA VIN) takes the commodity's domains; the tagger's keyword hits include false ones ("lead along" as metallurgy; "lord" and "king" as administrative). Both cost power, not calibration, since decoys pass the same gate. | A10 named the context and the tagger but not the map, the combination, the tag source or the independence rule, so the gate could not be built without choices made after the fact. On the 2026-10-17 snapshot the tagger gives a domain to 32.0% of Meanings, 40.2% with the joined glosses; the gate fails closed, so the rest can never be `CONVERGENT`. |
| A19 | A18, §4, §7.3 | **2026-10-17, before A9 and before any p on a gold word.** **Adjacency:** line breaks and word dividers (𐄁) between a word and the next token are layout and are skipped, so the logogram "immediately after" a word is the next sign group or logogram. **Spellings:** a mapped sign's spelling variants count as that sign: \*OLIV as OLIV, VINb and VINc as \*131B and \*131C. **Fused tokens:** a hyphenated token whose last element is a mapped logogram or one of its ligatures, other than \*118 and NI, is the word before it followed by that logogram (X-VIN reads as X VIN). **Map:** \*21F (ewe, Linear B OVISf) → fauna, with \*21M, \*22F, \*22M and \*23M. **Controls:** each sign-shuffle and fabricated control is scored under the context of the positive it was made from (§4), which the calibration passes to the engine with the query. Each Linear B Greek negative (A2) takes the context of a gold positive drawn with replacement under the run's seed. The gold negatives are Linear A words and keep their own contexts. **Impact set (§7.3):** a key of a root whose domains changed (its Meaning or a joined gloss) counts as changed. Only words in the impact set can change d\* and the clusters at d\*; p, saturation and so the verdict can move for any word, since the decoys query the whole index. **Coverage note (2026-10-25):** the support "Amygdaloid stone seal" (CRZg3), which entered the corpus after the table was ruled, is unknown, as the other seals are; CRZg3 carries logograms only, so no word's context changes. | The review of the A18 build found three things. The next-raw-token rule gave 104 logogram contexts, where the counts A18 was ruled on (161) had skipped line breaks and dividers. Controls with no corpus attestation got no context, so criterion 3 passed by construction. And §7.3 claimed that a verdict could change only inside the impact set. |

## 7. Updates to `semitic_roots.json`: detection and recalibration

`semitic_roots.json` changes wave by wave: audit batches, gap fills, twin merges, citation repairs. Shoresh treats every change as an event it can detect and measure. It never absorbs a change silently.

### 7.1 What goes stale, and what does not

| Artefact | Stale after a data change? | Why |
|---|---|---|
| Per-query p-values | **No.** They are computed live. | The decoys run against the current index, so the null always describes the database being queried. |
| `root_index.sqlite` | **Yes.** It refuses to load. | The input sha256 is checked at load time (§7.2). |
| Saturation thresholds (the 90% rule in `UNINFORMATIVE`) | Possibly. | Adding keys can make neighbourhoods denser. They are re-measured in §7.4. |
| Gold-set metrics (§4–5) | **Yes.** | Recovery and discrimination depend on the database. They are re-measured in §7.4. |
| `cognate_search_golden.json` | **Yes**, by construction. | It is a snapshot taken against fixed input hashes. It is not regenerated because data changed (§7.5). |
| Saved sweeps and batch outputs | **Yes.** | Each is stamped with the index sha it was computed against. |

### 7.2 Detecting a change

The index stores provenance for each record, not only a hash of the whole file:

- `provenance` holds the sha256 of every input file, the git commit and the build time. The inputs include the key logic as well as the data: `semitic_correspondences.json`, `lib/semitic_root_schema.py`, `lib/semitic_notation.py` and `lib/root_index.py`. A change to any of them re-keys every Number.
- `record_hashes` holds, for each `Number`, the sha256 of the canonical record. Canonical means the NFC-normalised JSON with sorted keys, hashed separately for each field: `Proto-Semitic`, `Meaning`, each `Analogues[language]`, and `Notes`.

When the file hash at load time does not match, the tool stops with `index stale: run build_root_index.py --diff`. It does not fall back to stale results, which is what happened with `cognate_cache.json`: it was built against 3,979 roots and kept being read after the file changed.

### 7.3 `build_root_index.py --diff` (read-only)

This compares the current inputs with the record hashes stored in the index and prints the following, without writing anything:

1. **Record diff.** Numbers added, removed or modified. For a modified record it shows which fields changed: the headword, the meaning, analogue languages added, dropped or edited, and Notes. Edits to Notes alone never change keys, and they are reported as `notes_only`.
2. **Key diff.** The radical keys and shadow keys gained or lost, per cluster. Merges show up as one cluster absorbing another's keys. A removed Number whose PS keys reappear as gains on another Number is listed as a possible merge into it.
3. **Impact set** (from Phase 2, since it needs the query-side skeleton). The corpus words whose skeleton variants fall inside the retrieval radius of any key that was gained or lost, or whose root's domains changed (A19). Only these words can change d\* and the clusters at d\*; p, saturation and so the verdict can move for any word, since the decoys query the whole index. The shadow-key buckets make this set cheap to compute.
4. **Impact preview** (from Phase 2). For the impact set only: the top cluster and verdict before and after. The "before" side uses the old index and the "after" side a temporary new one.

### 7.4 Recalibration after a rebuild

Run `root_match.py --calibrate` after `build_root_index.py` (rebuild, with backup). It writes a **new** record, `data/runs/root_match_calibration/<date>-<index_sha8>.json`, and never overwrites an earlier one. The record contains:

- the saturation curve: the share of family-B decoys with d\* ≤ 0.3, by skeleton length;
- the gold metrics from §4 (recovery, AUC, control false-positive rate, KS calibration, real minus shuffled);
- a diff against the previous calibration record.

**Gate.** It mirrors the hold rule of the semitic-roots audit:

- A wave is flagged **less discriminating** if family-B saturation at d ≤ 0.3 rises by more than 1 point, or if real minus shuffled shrinks.
- A flag is information to bring to the wave's review. It is not an automatic revert. Denser neighbourhoods can be correct, for example when a real root was missing.

If saturation crosses the `UNINFORMATIVE` threshold for some length bucket, the threshold itself is reported, but it changes only through an amendment in §6.

### 7.5 The shim regression survives data changes

The Phase 3 acceptance test is **differential**, not frozen. It loads the pre-shim `cognate_search.py` from its git commit (`git show <commit>:scripts/cognate_search.py`) and compares it with the shim on the *current* data. A data update therefore never causes a spurious failure, and the test never needs a regenerated golden record.

The frozen `cognate_search_golden.json` remains a second check. It is enforced only when the current hashes of its **data** inputs equal its provenance hashes. The code under test (`cognate_search.py` and the shim) is excluded from that comparison, because the shim changes it by design. Otherwise the check is skipped, with the reason given. It is regenerated only for a cause named in the commit.

### 7.6 Update checklist

```bash
uv run scripts/build/build_root_index.py --diff            # what changed, which words it touches
uv run scripts/build/build_root_index.py --force           # rebuild (backs up the old index first)
uv run scripts/root_match.py --calibrate                   # new calibration record + gate
uv run pytest tests/test_root_index.py tests/test_root_match.py tests/test_cognate_search_shim.py
```

### 7.7 Long runs read a frozen snapshot

Several sessions edit the live data at once. On 2026-10-16, `semitic_roots.json`, `lexicon.json` and `corpus.json` were dual-written in the middle of a 44-minute golden run, and the input guard refused to write the fixture. Any run longer than a few minutes, meaning fixtures, `--calibrate` and sweeps, therefore reads an APFS copy-on-write clone of the skill. The clone is instant and costs no disk. The run's outputs are copied back as new files.

```bash
SNAP=<scratch>/snapshot-$(date +%Y%m%dT%H%M); mkdir -p "$SNAP"
cp -cR <linear-a-decipherment> <ancient-near-east-research> "$SNAP"/
(cd "$SNAP/linear-a-decipherment" && uv run scripts/root_match.py --calibrate)   # then cp -n the new record back
```

Both skills are cloned. The Arabian onomasticon lives in the ANE skill, and the index, the harness and `cognate_search` all read it as a sibling folder. Without the second clone, a snapshot build either fails or, with `--allow-missing`, records the lexicon as MISSING. An index built on the snapshot stores skill-relative paths (`data/…`, `../ancient-near-east-research/…`), so after copy-back it checks the live files.

A symlinked tree does not work for this, because the modules resolve `Path(__file__).resolve()` back to the live data.

## 8. The index: what it holds and how lexemes join a cluster

`data/root_index.sqlite` is built by `scripts/build/build_root_index.py` and loaded by `lib/root_index.py`. It is SQLite because the skill is stdlib-only.

**Contents.** The index holds 3,783 roots and 113,990 keys in schema v3. They cover the PS headword, weak variants, the reflexes of all 48 Analogues languages, and 80,314 lexemes from 15 Semitic contact lexica. The onomastica are flagged `onomastic`. The `LEXICA` docstring in `lib/root_index.py` lists what is left out and why.

Nothing drops silently:

- **`unkeyed_analogues`** lists each Analogues entry that gave no key, with a reason: 79 `no_form` (citation-only strings), 30 `placeholder` (+, --, ?) and 8 `no_key`. Before the second-read fallback in `analogue_forms` there were 677. That fallback handles the qualifier `(?) šbr`, the optional prefix `(tä)däbärä`, `'abbā` read as ʾabbā, and a lone capitalised form such as `Abba` or root-atlas `ŠMʿ`.
- **Per-lexicon counts** record keyless lexemes, CAD ghosts, phrases and overlong keys.
- **Flags.** A lexeme whose form is several words (`aban kitti`, `ʾḤR ʾŠ`, Hebrew place names) is flagged `phrase` and gets no sound link. A lexeme key with more than six radicals is flagged `overlong`. Palaeosyrian keys carry `script_underdetermined`.

**Speed.** The build takes 39 s and the file is 64 MB. Loading takes 75 ms with roots only (`include_lexemes=False`, which is what `cognate_search` uses) and about 540 ms with lexemes.

**Links.** A link from a lexeme to a Number has a basis:

| Basis | Meaning | Count | Gloss shared |
|---|---|---|---|
| `fk` | The lexicon names the Number itself (`semitic_roots_ref`). It is never overwritten by sound. | 1,083 | 14.9% |
| `fk_dangling` | The named Number does not exist. The last three (anchor\_bible zbl → K0460, a merged 'dung' twin; rʿmlk → K0372 and 116, a removed 'friend' record and a clone of 61) were repointed: rʿmlk now names 61 and 52. | 0 | — |
| `root_key_exact` | `match_root_key` matches a PS key radical for radical. The best basis over all of a lexeme's forms wins. | 41,447 | 8.9% |
| `root_key_reduced` | The same, but only with absorptions. | 204,989 | 1.5% |

Random root–lexeme pairs share a gloss 0.12% of the time.

**Lookup.** A lexeme is tried against every PS key its consonants can continue, not only those that share its surface bucket. Each PS source of each consonant gives a shadow: Aramaic t → \*t or \*ṯ gives T and S, and Hebrew y → \*w or \*y gives Y and W. Each shadow is then tried as it stands, with one daughter class absorbed (maktab → \*ktb), or with one PS class lost (\*qwm → qm).

Against the bucket-only build:

- 2,073 new exact links, with 10.9% gloss agreement, against 8.8% for the old exact links;
- 603 reduced links upgraded to exact.

Absorbing a second daughter class would have added 57k reduced links at 1.3% agreement, for 26 s more build, so the lookup stops at one (`_LINK_DELETIONS`).

Sound links are many-to-many. Even explicit `fk` links share a gloss word with the root's Meaning only 15% of the time, because Dillmann's glosses are in Latin and French and sources word things differently.

**Cluster policy for the engine.**

- A lexeme joins a root's cluster by `fk`, or by `root_key_exact` together with gloss overlap.
- Every other link is shown as "possible cognate of N". Such a lexeme is never a cluster of its own (A17): the statistic runs on root clusters only.
- Clusters are never merged on sound alone.

In bucket `KNS`, for example, Hebrew כָּנַס "to gather" joins *kanVs- (2763). Akkadian *kunāšu* "emmer", *kanāšum* "bow down" and *kīniš* "truly" are exact sound links too, but they stay outside the cluster, shown as possible cognates (A17). The cost is that Latin-glossed cognates such as Geʿez *ከነሰ* "congregare" stay outside the cluster, so branch breadth is undercounted.

**Cognate fields.** `cognates` is kept raw for display: the CAD stance notes, the Hebrew and Aramaic strings, and the Geʿez entries in Arabic script. None of them names a Number, so none makes a link.

## Phase 0 fixtures

```bash
uv run scripts/validation/root_match_phase0.py gold       # tests/fixtures/root_match_gold.json
uv run scripts/validation/root_match_phase0.py golden     # tests/fixtures/cognate_search_golden.json
uv run scripts/validation/root_match_phase0.py baseline   # tests/fixtures/root_match_baseline.json
uv run scripts/validation/root_match_phase0.py gold-v2      # tests/fixtures/root_match_gold.v2.json (§6 A1-A5)
uv run scripts/validation/root_match_phase0.py baseline-v2  # tests/fixtures/root_match_baseline.v2.json
uv run scripts/validation/root_match_phase0.py gold-v3      # tests/fixtures/root_match_gold.v3.json (§6 A13)
uv run scripts/validation/root_match_phase0.py baseline-v3  # tests/fixtures/root_match_baseline.v3.json
```

Each fixture is written to a temp file and linked into place. It is never overwritten, and a crash never leaves half of one behind. Each fixture carries the sha256 of every tracked input, hashed before and after the run. The tracked inputs are every data file and module that `search_cognates`, the gold rules and the corpus loader read, including the ANE onomasticon. A missing input is recorded as missing, so its arrival counts as a change. If any input changes while the run is in progress, the fixture is not written.

A baseline refuses a gold set built from other inputs, and a failed CLI call stops the latency run instead of being timed. Run every fixture of a version on one snapshot (§7.7).
