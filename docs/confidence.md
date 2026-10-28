---
name: docs/confidence
title: Confidence
desc: The confidence tiers, the tests a reading passes to rise a tier, and what counts as a resolved sign value.
tags: [docs, linear-a]
authors: "di Mino"
created: 2026-10-22T18:14:10Z
updated: 2026-10-29T12:00:00Z
---

# Confidence

## Tiers

- **4, CONFIRMED:** passes all four corpus tests and is staked by the project's author, recorded on the reading's
  page as its reviewer.
- **3, PROBABLE:** passes the crossword and inscription tests, or shows complementary distribution between a full
  spelling and its abbreviation.
- **2, CANDIDATE:** attested in two or more independent contexts.
- **1, SPECULATIVE:** a proposal on record that has not yet met the CANDIDATE test.

No reading skips a tier. A rejected reading leaves the record for the archive, with the reason it was rejected. The
tiers describe support under this project's evaluation criteria; they do not imply scholarly consensus.

## Sign values

A sign value counts as resolved only on support that does not depend on a Semitic match: a Linear B value, a scribe's
arithmetic, or a spelling variant of the same word. Every other value is listed as proposed, with its evidence where
given, or as speculative when it is held only in its sign record.

## The tests

Four tests decide a reading's tier. They are judgments recorded on the reading's page, not significance tests.

1. **Crossword:** the value, substituted wherever the sign occurs, gives words with Semitic matches in more than one
   context.
2. **Inscription:** the reading leaves every inscription it touches more readable. One inscription made less readable
   blocks promotion.
3. **Complementary distribution:** a sign value fills a gap in the sign grid without colliding with another sign's
   value. For a word, a full spelling and its abbreviation never stand in the same document (GRA+KU: the full
   spelling as a section heading, the ligature in the list).
4. **Structural fit:** the value fits the CV grid and the Proto-Semitic consonant inventory.

Tests 1 and 4 assume a Semitic language: they rank readings within that hypothesis and do not test it. The tests of
the hypothesis itself are pre-registered: `paradigm-b-preregistration.md` (run, with its result in
`paradigm-b-result.md`), `shoresh-preregistration.md` and `meaning-shuffle-preregistration.md`.

*Not yet written:* the rescoring of every Semitic match against Luwian, Egyptian and Hurrian roots.

## Prohibited readings

*Not yet written:* the readings the record refuses, and why.
