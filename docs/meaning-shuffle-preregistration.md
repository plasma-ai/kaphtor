---
name: docs/meaning-shuffle-preregistration
title: "Meaning-Shuffle Test: Pre-Registration"
desc: The meaning-shuffle test's pre-registration, a draft for signature: hypothesis, word set, statistic, null, the calibration rerun before the run, competitor arms and how to read the result.
tags: [docs]
authors: "di Mino"
status: "DRAFT FOR SIGNATURE (calibrated on synthetic words; no distance on a real anchored word)"
created: 2026-10-28T23:30:00Z
updated: 2026-10-28T23:30:00Z
---

# Meaning-Shuffle Test: Pre-Registration

> [!NOTE]
> The text names files by their paths in the research tree it was written in. In this repository they are:
>
> | Named here | In this repository |
> |---|---|
> | `lib/meaning_shuffle.py` (`ms`), `semantic_gate` | `tools/core/` |
> | `scripts/validation/` | `tools/linear_a/validation/` |
> | `references/ref-root-match-engine.md` | [shoresh-preregistration.md](shoresh-preregistration.md) |
> | `corpus.json` | `data/linear-a/` |
>
> The calibration and power study (`POWER.md`, its reports) and the result page are not in this repository. The
> registered run binds the research index; this repository's index reads fewer lexica, and its rival-language files
> carry no glosses, so a run here is a reproduction of the Semitic arm.

Shoresh asks of one word whether it is closer to a Semitic root than its own decoys are. At two or three consonants
the answer is almost never yes, and per-word verdicts do not add up. This test asks the corpus-level question: do
the Linear A words that stand beside a logogram lie nearer Semitic roots whose meaning fits that logogram than roots
that fit another logogram's? Shuffling the contexts among the words keeps the words, the lexicon and its density
fixed and moves only the pairing of word and meaning (Baxter & Manaster Ramer 1999; Kessler 2001). The same test is
run against Luwian, Egyptian and Hurrian.

Everything below was fixed on synthetic words before any distance was taken on a real anchored word. The
calibration and power study is `artifacts/meaning-shuffle-2026-10-28/POWER.md` in the research tree (findings 1–21);
the numbers here are its.

## 0. Status

Not run. The run needs this document signed (§11), the index rebuilt and checked current, and the calibration of §5
passed on the frozen inputs. `scripts/validation/meaning_shuffle.py` refuses to run without `--prereg` naming this
file, and stamps its sha256 into the report with those of every input.

## 1. Hypothesis

H₁: Linear A words, read through the registered sign values, lie nearer Semitic roots of their own context than the
same words paired with the contexts of other words. H₀: the pairing of word and context carries no information about
distance; any assignment of the observed contexts to the words is as likely as the observed one.

A rejection of H₀ is evidence that the words and the Semitic lexicon share meaning-matched form beyond what the
lexicon's density, the words' shapes and the contexts' breadths produce. It is not by itself evidence that Semitic
fits better than another language (§7).

## 2. Word set, contexts and key set

- **Words:** every syllabic word type in `corpus.json` standing beside a logogram (`ms.anchored(corpus,
  "logogram")`), less the gold set (§9) and any word with a sign the registered values leave unmapped, which is
  listed, never shortened (A5). On the calibrated inputs this is 84 words in 7 contexts, after 23 gold words and 35
  unmapped words were set aside. The count at the run is reported; a word set that differs from the calibrated one
  is reported with its difference.
- **Context:** a word's context is the set of semantic domains of the logograms beside it (`semantic_gate`, the tagger
  frozen by A18). Contexts are compared as sets.
- **Distance:** D[w][C] is the best gated distance from w to a Semitic root cluster whose domains fit C
  (`ms.semitic_distance`, Shoresh's engine, its sign readings under A11, A20 and A21).
- **Key set:** the primary key set of Shoresh's A4 (the gold set's frozen `primary_index_exclusions`). The full index
  is reported beside it (§6).
- **Index:** the full research index, with its contact lexica, rebuilt from the current inputs and checked current
  (no `--allow-stale`). A run of this repository's public copy, whose index reads fewer lexica, is a reproduction and
  is reported as one, never in place of the registered run.

## 3. Statistic (primary)

T_cap = −Σ_w min(D[w][ctx(w)], c), with **c = 0.5**: each word's own-context distance, capped, so a near match counts
by how near it is and a far one counts as the cap. Larger is better for H₁.

Chosen on synthetic power alone (POWER.md finding 21), by a rule written before its run (finding 19): among the
statistics calibrated on every one of five decoy pools, the one with the highest mean power at 40 planted words.

| Statistic | Type I, five pools | Worst KS p | Power, 40 planted | 20 | 10 |
|---|---|---|---|---|---|
| **T_cap, c = 0.5** | 0.038–0.045 | 0.069 | **0.726** (0.703–0.753) | 0.301 | 0.130 |
| T_cap, c = 1 | 0.039–0.050 | 0.035 | 0.664 | 0.267 | 0.124 |
| T_rank | 0.033–0.052 | 0.198 | 0.482 | 0.202 | 0.102 |

## 4. Null and p

- **Shuffle:** the contexts are permuted among the words, keeping their multiset, inside the **fine strata**: a word
  moves only among words of the same sign count (5 standing for 5 or more), skeleton length and reading count, what
  family B keeps of a word (A3, A11). A word alone in its stratum falls back to its sign count (`ms.fine_strata`;
  ruled 2026-10-28, Tom: "Sure").
- **N = 10,000** permutations, seed 20261028.
- **p = (1 + #{T_perm ≥ T_obs}) / (1 + N)**, one-sided, ties counted against H₁. This is the p the calibration
  measured.
- **α = 0.05.**

## 5. Calibration on the frozen inputs (before the run)

Before any distance on a real word, the calibration of finding 21 is rerun on the frozen inputs:
`meaning_shuffle_power.py --fresh-null --null-per-slot 1000 --calib-runs 1000 --runs 1000` at seeds 20261028–20261032,
every arm. Each decoy enters a run once until its slot's pool is spent, so the runs are independent draws of the
null. The registered statistic passes if, on every pool, its Semitic type I is at most 0.064 (α plus two standard
errors at 1,000 runs) and its KS p against U(0, 1) at least 0.01. Short of that, nothing is computed on real
words until a dated amendment.

## 6. Secondary and sensitivities

One secondary test, read beside the primary and never in its place: **T_rank**, Σ_w the rank of D[w][ctx(w)] among
D[w][C] over all contexts, a word's own-context advantage free of the size of its distances; the primary's words,
strata, N, seed and α.

Reported beside them, never tested, since the calibration covers neither: the full index (`--full-index`, A4's
exclusions back in); the length strata (sign count alone); `--conventional-values`, every sign by its Linear B value
and a word with a sign Linear B gives no value unmapped (A20); `--set all`, the words anchored by document type as
well. None of these replaces or rescues the primary.

## 7. Competitor arms and cross-talk

- **Arms:** Luwian, Egyptian and Hurrian, each run with the primary's words, statistic, strata, N, seed and α, each
  against its own lexicon gated by its own glosses (`--competitors`). Each arm is reported with its own p.
- **No hurdle** (ruled 2026-10-28, Tom: "It doesn't have to beat each competitor. It should be objective."): no
  competitor result gates the Semitic one.
- **Cross-talk is reported, never a gate** (ruled 2026-10-28, Tom: "Sure"). Measured on synthetic plants under the
  registered statistic: no cross-talk exceeds 0.064. Egyptian plants read 0.062 on the Semitic test at 40 planted,
  Luwian and Hurrian plants stay below α, and the competitors' tests read 0.016–0.051 on Semitic plants. A
  competitor's cross-talk can account for a Semitic positive only if that competitor's own test also rejects on the
  real words; if both reject, both are reported and neither is ranked. The same rule reads a competitor's positive.
- **Own power,** at the registered statistic: Luwian 0.847 at 14 planted, Egyptian 0.777 at 20 and 0.999 at 40,
  Hurrian 1.000 at 10 (Hurrian fills at most 14 slots). A competitor that does not reject was able to.
- **Shoresh's A15 stands** (ruled 2026-10-28, Tom: "Sure"): this section covers the corpus test only.

## 8. Reading the result

| Primary p | Reading |
|---|---|
| < 0.05 | H₀ rejected: the words lie nearer Semitic roots of their own context than chance pairings do. Read with §7. |
| ≥ 0.05 | H₀ stands. Not evidence against H₁: at the registered statistic the test detects 40 genuine matches among 84 words 73% of the time, 20 matches 30% of the time. |

The result is published whichever way it falls, with the secondary and every sensitivity, arm and cross-talk
figure, in `artifacts/meaning-shuffle-2026-10-28/RESULT.md`.

## 9. Gold words

The gold set's words are set aside and counted (ruled 2026-10-28, Tom: "drop the gold words for now"). Every tier
3–4 Semitic word is in the gold set, so the primary tests the tier 1–2 residue and the unread words. `--gold-run`
is not registered here.

## 10. Known limits

- **Confounds carried by sign content** (site and scribe habits, a word opening with its logogram's own sign): family
  B randomises sign identity, so the calibration cannot see them.
- **Sign values chosen with Semitic readings in view:** 10 of the 84 words read through a proposed primary value and
  10 more carry an alternate. The conventional-values run (§6) shows what rests on Linear B's values alone.
- **The tagger reads English glosses,** so a lexicon glossed in another language fits fewer contexts.
- **A word written as logograms alone** (`*21F-*118`) is in the word set, as it was in the calibration.
- **Power:** the Semitic arm is the weakest of the four; a relation carried by 20 of the 84 words goes undetected
  70% of the time.

## 11. Freeze and signature

The run report stamps the sha256 of this file, the index, `corpus.json`, the gold set and the tagger. Amendments
are dated and made before the run.

Signed: ______________________ (di Mino)    Date: ______________

## Sources

- W. H. Baxter & A. Manaster Ramer, "Beyond lumping and splitting: probabilistic issues in historical linguistics,"
  Symposium on Time Depth in Historical Linguistics, Cambridge 1999.
- B. Kessler, *The Significance of Word Lists*, CSLI 2001.
- B. Kessler, "The Mathematical Assessment of Long-Range Linguistic Relationships," *Language and Linguistics
  Compass* 2 (2008), doi:10.1111/j.1749-818x.2008.00083.x.
- `references/ref-root-match-engine.md` (Shoresh: A3, A4, A5, A11, A15, A18, A20, A21);
  `lib/meaning_shuffle.py`, `scripts/validation/meaning_shuffle.py`, `scripts/validation/meaning_shuffle_power.py`.
