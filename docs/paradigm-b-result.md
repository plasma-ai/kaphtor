---
name: docs/paradigm-b-result
title: "Paradigm B: Result"
desc: The outcome of the held-out paradigm-prediction test as run under its freeze (G1 passed, G2 failed, so no posterior), the descriptive G3 figures, and the post-run review.
tags: [docs]
authors: "di Mino"
status: "RUN 2026-10-09 under SHA256SUMS f5d6733f…; stopped at G2"
created: 2026-10-29T00:00:00Z
updated: 2026-10-29T00:00:00Z
---

# Paradigm B: Result

This test does not establish the language. A successor protocol is in preparation.

Paradigm B asks whether one morphological inventory, fixed before the run, predicts the variant forms at the slots
of a held-out inscription of the Linear A libation formula family from the forms at the other sites
([pre-registration](paradigm-b-preregistration.md)). It ran once, on 2026-10-09, under the option B freeze
(SHA256SUMS `f5d6733f…`), in the gate configuration: strict vowels, base inventories, leave-one-site-out folds over
10 sites. Structure passed (G1). Calibration on texts of known language failed one of its three criteria (G2), and
under the protocol a G2 failure stops the test: no likelihood or posterior was computed. The G3 figures below come
from the same run and are descriptive only.

The runs are in `data/linear-a/paradigm-b/runs/`; `tools/linear_a/validation/paradigm_b.py reproduce` reruns them
from the frozen code and data ([reproduce.md](reproduce.md)).

## The family

57 held-out slot tokens are scorable (a training form identical to the held-out form is excluded, amendment 9). A
is the mean of the per-fold rates; the pooled hits are beside it.

| Arm | A (fold mean) | Pooled hits |
|---|---|---|
| free (no language) | 0.860 | 46/57 |
| Central Semitic (`cs`) | 0.890 | 45/57 |
| Northwest Semitic floor | 0.890 | 45/57 |
| Luwian | 0.110 | 10/57 |
| Hurrian | 0.311 | 14/57 |
| Egyptian | 0.263 | 17/57 |

Δ = A_cs − max(rivals) = +0.579 (Δ_floor +0.579). Pooled, Δ = 45/57 − 17/57 = +0.491.

## Gates

**G1 (structure): passed.** A_free is 0.860. Under null D, a copied formula with noise, A_free has mean 0.292 and
95th percentile 0.500; no replicate of 10,000 reached 0.860 (r = 0, p < 3×10⁻⁴).

**G2 (calibration): failed.** 126 of the 128 control windows were scored (B-H3-ugaritic-10 and B-NEG-14 have no
scorable token).

| Criterion | Value | Required | Result |
|---|---|---|---|
| Length-matched AUC(Δ), Semitic (67) against other (59) | 0.904 [0.809, 0.975], 782 pairs | ≥ 0.85, lower bound > 0.50 | met |
| Length-matched AUC(A_cs) | 0.931 [0.844, 0.989] | ≥ 0.75 | met |
| No Linear B window above the H1 median in its length band | B-NEG-mycenaean_greek-02: Δ 0.25 against a band median of 0.00 | none | not met |

B-NEG-mycenaean_greek-02 is KN Sd 4405 … 4483 (*a-ni-ja-pi* / *a-ni-ja*, *e-re-pa-te* / *e-re-pa*, *i-qi-ja*
rendered I / I-JA). `cs` explains one of its four folds and no rival explains any, so Δ = 0.25; the H1 median in its
band (2.6–3.6 signs per word, 29 windows) is 0.00 because 16 of those windows have Δ = 0. The stop was accepted as
frozen.

**G3 (family): not licensed; descriptive.**

| Check | Value | Met |
|---|---|---|
| Δ against null D2, a paradigm of no language | D2 95th percentile 0.187, mean −0.022; r = 0/10,000 | yes |
| Δ against null D2×2 | r = 0/10,000 | yes |
| A_cs above every rival | 0.890 against 0.311 (Hurrian), 0.263 (Egyptian), 0.110 (Luwian) | yes |
| A_cs at least the median A_cs of the H1 windows | 0.890 against 1.000 (26 of 44 H1 windows score 1.0) | no |

## The family among the controls

| Class | Windows | Mean Δ | Windows with Δ ≥ 0.579 | Max Δ |
|---|---|---|---|---|
| H1 Semitic prayer (Ugaritic, Hebrew) | 44 | +0.268 | 9 | +1.000 |
| H3 Semitic non-prayer (Ugaritic) | 23 | +0.356 | 6 | +1.000 |
| H2 Luwian | 19 | −0.501 | 0 | +0.200 |
| H2 Egyptian | 24 | −0.134 | 0 | +0.000 |
| NEG Linear B | 16 | −0.469 | 0 | +0.250 |
| H2 Hurrian | 0 (no edition lemmatization) | — | — | — |

In the family's length band (3.09–4.09 signs per word): H1, 14 windows, mean +0.229, one at or above the family; H3,
6 windows, mean +0.361, three at or above; Luwian (9), Egyptian (2) and Linear B (12), means −0.419, −0.611 and
−0.559, none at or above.

Red flags (PROTOCOL-B §11): A_cs(family) does not exceed every H1 window (1); D2's mean A_cs, 0.252, is below the
family's 0.890 (5); |AUC(Δ) − AUC(A_cs)| is 0.027 (6); flags 2–4 are unchanged since the inventories were built, and
the ablations behind flag 7 were not run under the stop.

What the run's review found: in 13 of the 24 Egyptian windows `cs` scores only through feminine *-t* (TE), where
A_cs equals A_egyptian; the Hurrian arm's vowel-only suffixes absorb Greek case vowels (A_hurrian 0.675 on Linear B),
so the family's 0.311 carries no Hurrian evidence; and H1 windows reach A_cs = 1.0 because they have few scorable
tokens (median 5, against the family's 57), which puts G3's H1-median criterion out of reach.

## Post-run review (2026-10-29)

| Cut | n | free | cs | best rival | Δ pooled |
|---|---|---|---|---|---|
| as run | 57 | 46 | 45 | Eg 17 | +0.491 |
| cs without `cs_c_e` (dual oblique -ē) | 57 | 46 | 23 | Eg 17 | +0.105 |
| drop tokens with any lacuna | 26 | 18 | 23 | Hu 6 | +0.654 |
| drop edge damage + without -ē, ya- | 34 | 26 | 15 | Eg 7 | +0.235 |
| *301 treated as opaque | 57 | 46 | 45 | Eg 17 | +0.491 |

- `cs_c_e` is absent from the pre-registration's §4.2 case list and the selftest checks the family's -RE-MA residue
  with it.
- 57 tokens are 27 distinct forms, held out within the 33 inscriptions the inventory was checked against.
- Several variants are breaks (U-NA-KA-NA TL Za 1, JA-SA-SA PK Za 14, I-PI PK Za 8, SI-RU PK Za 11, SE-KA-NA-SI
  SY Za 3) and two are artefacts (PK Za 12 joined across lacunae; IO Za 16 split at a line break).
- Against a stem-keeping null the structure result holds on all tokens (0/2000) but not on undamaged tokens
  (p ≈ 0.11).
- The "200 random inventories" figure has no script (reconstructed p ≈ 0.005–0.03).
- Frozen `data/snapshot/lexicon.json` changed after the freeze (withheld, drifted), so the blindness selftest cannot
  run against frozen bytes.
