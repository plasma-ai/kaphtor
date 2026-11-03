---
name: docs/d7-structural-result
title: "D7: Result"
desc: "S3 of the D7 pre-registration run on Linear A: the word set, the four counts against their permutation null, and how the pre-registration reads them."
tags: [docs]
authors: "di Mino"
status: "RUN 2026-11-02 under the signed docs/d7-structural-preregistration.md"
created: 2026-11-03T00:00:00Z
updated: 2026-11-03T00:00:00Z
---

# D7: Result

S3 of `docs/d7-structural-preregistration.md`, run after its signature, with `tools/linear_a/validation/d7_s3_linear_a.py`
(10,000 permutations, seed 20261102). The counts and the null are the controls' own functions. S1 failed its gate on
the controls and was not run on Linear A.

    uv run python tools/linear_a/validation/d7_s3_linear_a.py --out d7-s3.json

## Words

639 distinct multi-sign words in the recorded run's `corpus.json` (sha256 `e256ff11…`), which does not ship, each with
one witness that has no lost sign and no damage mark; the shipped corpus marks more broken edges, so its word set
differs. Set aside: 322 witnesses with a lost sign and 186 with a damage mark. Nine witnesses come from documents with no aligned Unicode layer and are kept, since the mark cannot be read there.

## Counts

| Count | Observed | Expected | p | Stems |
|---|---|---|---|---|
| Narrow X-TE / X-RE (primary) | 1 | 0.42 | 0.35 | SI-DA |
| Broad X-TE~TI / X-RE~RI | 1 | 1.59 | 0.83 | SI-DA |
| Narrow X / X-TE | 2 | 1.43 | 0.42 | I-JA, SI-RU |
| Broad X / X-TE~TI | 4 | 2.07 | 0.15 | I-JA, SI-RU, DA-KU-SE-NE, JA-KU |

## Reading, by the pre-registration's terms

- Schrijver's analysis predicts an excess of X-TE/X-RE pairs. Linear A holds one pair, SI-DA-TE beside SI-DA-RE,
  against 0.42 expected under the null (p 0.35).
- The Semitic analysis predicts an excess of X/X-TE pairs: two observed against 1.43 (p 0.42), four against 2.07 in
  the broad count (p 0.15).
- Neither excess is there, so S3 favours neither analysis. With S1 failed at its gate, D7's structural test gives no
  evidence for Hattic over Semitic.
- **Power.** The corpus is small: the null expects about two pairs or fewer in each count, so only a strong pattern
  could have reached p < 0.05. The narrow count is uncalibrated on the controls, whose speller writes only *a*, *i*
  and *u*.
