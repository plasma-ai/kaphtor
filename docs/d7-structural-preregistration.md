---
name: docs/d7-structural-preregistration
title: "D7: Schrijver's Structural Claims"
desc: "The pre-registered structural test of Schrijver 2019's claims for a Minoan–Hattic relation: S1 edge alternation, S2 the libation verb's slots, S3 -RE beside -TE, the rival-language controls, the gate and the rulings."
tags: [docs]
authors: "di Mino"
status: "SIGNED 2026-11-02"
created: 2026-11-03T00:00:00Z
updated: 2026-11-03T00:00:00Z
---

# D7: Schrijver's Structural Claims

**Status.** **Signed by di Mino, 2026-11-02, as written below, before any statistic below exists on a Linear A word.**
T1–T5 are ruled (below). The controls ran on 2026-11-02: S1 failed its gate and will not run on Linear A. S3 ran on
Linear A as registered the same day; its result is in `docs/d7-structural-result.md`.

**Scope.** Three of Schrijver's claims for a Minoan–Hattic relation:

- Claim 1: the libation verb is a prefix-suffix chain around a fixed core (Schrijver 2019: 342–343).
- Claim 5: *-te* is a 3rd-person feminine possessive (pp. 367–368).
- Claim 6: a predicted *le* is written RE (pp. 368–369).

His lexical claims fall to the Hattic arm of Shoresh's competitor null (A23 in `docs/shoresh-preregistration.md`).
His other claims either have no Hattic term or are Hatto-Sumerian and lie outside Linear A.

**Terms.** Every language gets the same test, there is no hurdle, and each result is reported with its own number.
Nothing runs on Linear A before this pre-registration is signed. The scripts are report-only and write only their
`--out`.

## S1. Edge alternation (claim 1, the prefixing core)

- **Statistic.** Over the distinct words (types) of a text set, count the pairs in which one word is the other with
  one or two signs added at one edge, the shorter word having at least two signs:
  - a *left* pair is w₂ = p + w₁;
  - a *right* pair is w₂ = w₁ + s.

  L = left / (left + right). A mainly prefixing language raises L; a suffixing one lowers it.

- **Controls, one per language.** Each language's own running text, spelled into Linear A by A9's competitor
  speller:
  - The spelling uses the open pattern on the word's consonant key, as A9 spells a competitor plant (A15), with
    gutturals by the script's rule. A word-initial vowel the source writes stays as its vowel sign.
  - Every language passes through the same filter, whether its script writes vowels (cuneiform) or not (Ugaritic,
    Egyptian). A vowel-only prefix such as Hattic *a=* or *e=*, and Ugaritic's ʾa, ʾi, ʾu, survive it.

  - S1 compares the series each word is written in, not its signs. The speller's vowels are drawn at random, so one
    morpheme spelled twice can differ in its signs, and edge pairs would vanish. A consonant becomes the series its
    arm's table picks (A9's `series_consonant`). A guttural, ḫ included, or a written initial vowel becomes one
    bare-vowel token V. Linear A's words, after signature, reduce the same way: each sign by its Linear B consonant,
    a pure vowel sign as V, a polyphonic sign by its primary value.
  - A cuneiform geminate written across a sign boundary (*at-ti*) is one consonant, since the alphabetic scripts
    write no gemination. A capitalised Egyptian word is a name and drops out, as a determinative takes a name out of
    the cuneiform texts.

  | Language | Running text held (types) | Note |
  |---|---|---|
  | Ugaritic | AEMW/Ugarit, its wholly alphabetic documents (KTU 4 and the rest) | |
  | Hattic | TLHdig `Hat` and `Hattian`: 19,136 word rows, 6,279 + 84 types | Forms only, no glosses |
  | Hurrian | TLHdig `Hur`: 46,564 word rows, 16,401 types | |
  | Luwian | TLHdig `Luw`: 12,430 word rows, 3,946 types | Cuneiform Luwian |
  | Egyptian | ORAEC/TLA consonantal transliteration | |

  A cuneiform form's consonant key is its signs joined, with the vowels out. TLHdig rows marked damaged are left
  out (their `preserved` field).

  Each control draws 1,000 samples at 500, 1,000, 1,500 and 2,000 types. The gate applies at the size nearest
  Linear A's type count, which is read after signature.

  The script is `tools/linear_a/validation/d7_structural_controls.py`. It is report-only, has no Linear A mode, and
  is tested in `tests/linear_a/test_d7_structural_controls.py`. None of its three text layers ships in this
  repository; it reads them at `tools/ane/aneq.py`'s paths and exits 3 without them.

- **Gate before Linear A (T4).** At Linear A's size, the central 95% interval of Hattic's L must be disjoint from
  Ugaritic's and from Hurrian's.
  - If it is clear of Hurrian's but not of Ugaritic's, S1 answers nothing between Hattic and Semitic: it is reported
    as uninformative and not run on Linear A.
  - The gate is fixed here, before any control is run, so it cannot be tuned to a result.
- **Readout.** Linear A's L, with its percentile in each language's distribution and the languages whose 95%
  interval holds it. All are reported; none is ranked.
- **Text sets (T2).** The whole corpus is primary, since the claim of a prefixing language is about the language,
  and the formula holds too few words to give L a usable interval. The libation formula is reported apart.

## S2. The libation verb's slots (claim 1 as stated)

The verb's attested variants number about a dozen. Schrijver's slot analysis (p. 342) and the Semitic reading were
both built on those same forms, so neither can be tested on them. S2 is declared non-diagnostic: both analyses are
printed side by side, with no statistic.

## S3. -RE beside -TE (claims 5 and 6)

- **Statistic, narrow (primary).** Count the stems X (one or more signs) for which both X-TE and X-RE are attested
  words.
- **Statistic, broad.** The same count with TE~TI and RE~RI, since Hattic spelling treats *ti* and *te* as one
  morpheme (Kassian 2015: 21) and Schrijver's support pairs TE with TI (2019: 367–368; T3).
- **Second count.** The stems for which both X and X-TE are attested.
- **Null.** Final signs are permuted among words of the same sign count, which keeps each final sign's frequency.
  The test uses 10,000 permutations and reports observed, expected and p for every count.
- **What separates the analyses:**
  - Schrijver's analysis (le/te, male/female) predicts an excess of X-TE/X-RE pairs.
  - The Semitic analysis (feminine *-t* against a bare masculine) predicts an excess of X/X-TE pairs and none of
    X-TE/X-RE pairs.
  - A feminine -TE alone does not separate them, since both predict it. Claim 5 is answered only through its -RE
    counterpart.
- **The controls calibrate the null only.** The speller drops codas, so Hattic's reduced *=l* and *=t* (*šai=l*,
  *še=t*) go unwritten in a spelled Hattic control. A control cannot show Schrijver's pattern. It shows how often
  the permutation null throws such pairs up in real text.

## The controls (2026-11-02; no Linear A word read)

`d7_structural_controls.py --perm 10000` (seed 20261102, 1,000 draws a size), on inputs with sha256
`words.jsonl` (TLHdig 0.3) `00153fea…`, `oracc_documents.jsonl` `8c2d95f2…` and `egyptian_sentences.jsonl`
`9f4a189f…`.

| Language | Keys | Series types | L, all types | L at 1,000 types (95%) |
|---|---|---|---|---|
| Ugaritic | 2,793 | 2,213 | 0.462 | 0.417–0.507 |
| Hattic | 1,258 | 1,181 | 0.480 | 0.462–0.498 |
| Hurrian | 3,247 | 2,770 | 0.408 | 0.365–0.454 |
| Luwian | 793 | 752 | 0.381 | — (752 types; 0.329–0.431 at 500) |
| Egyptian | 19,429 | 14,877 | 0.492 | 0.391–0.582 |

- **S1 fails its gate at every size.** Hattic's interval overlaps Ugaritic's at 500 and 1,000 types (0.421–0.533
  against 0.376–0.552 at 500), and Hattic cannot fill 1,500 or 2,000. It clears Hurrian's only at 1,000. By T4, S1
  is reported as uninformative and is not run on Linear A.
- **What the controls show without Linear A.** After the script's filter, the edge statistic separates the
  languages that add material at the left edge (Hattic 0.48, Egyptian 0.49, Ugaritic 0.46) from the suffixing ones
  (Hurrian 0.41, Luwian 0.38). It does not separate Hattic from Semitic: Ugaritic, a language with a prefix
  conjugation, gives Hattic's profile once spelled. Claim 1's "prefixes and suffixes around a core" describes a
  Semitic verb as well, so the claim is not diagnostic between the two.
- **Hattic's text is small once damage is out.** TLHdig's preserved Hattic rows give 1,258 keys; 15,840 of its rows
  are damaged.
- **S3 on the controls:**
  - **Narrow (TE, RE):** degenerate. A9's open pattern draws its vowels from *a*, *i* and *u* (`ENDING_VOWELS`), so
    no spelled control ends in TE or RE: observed and expected are 0 in all five languages. The narrow count stands
    on Linear A as registered; its permutation null comes from Linear A's own final signs, and no control
    calibrates it.
  - **Broad (TE/TI, RE/RI):** the null raises no alarm on real text. The X-TE/X-RE count is near its permutation
    expectation in every language: Ugaritic 3 against 3.2 (p 0.66), Hattic 1 against 0.85 (0.60), Hurrian 2 against
    2.9 (0.81), Luwian 0 against 0.7 (1.0), Egyptian 9 against 9.2 (0.58). The X/X-TE count gives p 0.10–1.0, none
    below 0.05.
- **Amendment (T5).** S1 and S3 are unchanged after the controls. S1 stands as run and failed, and is not retuned.
  S3 runs on Linear A after signature as registered, with the narrow count primary (T3) and the controls'
  degeneracy stated beside it.

## Rulings (2026-11-02, di Mino: "Use your judgement on T1–T5")

- **T1, Luwian.** Held: TLHdig's cuneiform Luwian. All five languages run.
- **T2, text sets.** The whole corpus is primary, and the libation formula is reported apart (S1).
- **T3, S3's primary.** Narrow (TE, RE), the forms Schrijver names (AU-RE-TE, the -RE words); broad is secondary.
  The primary reads his claim as he states it.
- **T4, S1's gate.** The disjoint-interval gate, as stated in S1. A power target would need an alternative to plant,
  and Schrijver gives none for a whole language's affix profile.
- **T5, run order.**
  - The statistics, nulls and gate are fixed by this pre-registration.
  - The controls touch no Linear A word, so they may run before signature, as the meaning-shuffle calibration did,
    and their numbers enter this pre-registration.
  - Any change to S1 or S3 after the controls are seen is an amendment, with its reason, before signature.
  - No statistic is computed on Linear A words before signature.
