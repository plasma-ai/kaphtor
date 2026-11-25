---
name: docs/corpora/aegean-comparative-corpora
title: Aegean and Anatolian comparative corpora
desc: The Hurrian, Cypro-Minoan, Cypriot, Old Assyrian and Eblaite layers indexed as controls for Linear A, with their coverage, boundaries and acquisition gaps.
tags: [corpora, docs]
created: 2026-10-22T18:14:10Z
updated: 2026-11-25T13:35:00Z
---

# Aegean and Anatolian comparative corpora

Coverage below reflects the currently indexed manifests. These are controls and
rival-evidence layers; none can confirm a Linear A analysis on its own.

## Indexed layers

| Layer | Coverage | Boundary |
|---|---:|---|
| TLHdig 0.3 | 23,936 XML records; 1,651,388 word rows; 13,442 Hurrian-tagged lines | 23,783 canonical designations; 144 repeated-designation groups; 223 recovery-parsed files are row-labeled; counts are not independent-artifact totals |
| IG XV 1 | 311 of 410 records; 397 edition parts | Mixed corpus: 230 Cypriot Greek, 27 Eteocypriot, 2 Phoenician, and 138 unclassified parts; only labeled Greek syllabic parts are known-language CV controls; 199 parts pass the strict preservation filter |
| Cypro-Minoan open layers | 213 Sign2Vec witnesses / 220 components / 2,899 retained sign instances; 232 PASP CM-related metadata rows | Overlapping layers, not additive: Sign2Vec supplies edition sign-number sequences without images; PASP supplies c. 1996 metadata without transcription or preservation typing |
| Cypro-Minoan catalogue | 263 texts: the 254 records of Valério 2016's Appendix A and 9 outside it; 1,642 metadata statements, each with work and page, 78 of them pointers; each text's period on Valério's Table I.1, script and subcorpus | No transcription: Appendix A's terms allow private research use only, so a record names its edition of record and the Appendix A pages; site and object type decoded from Valério's key to the sigla (2016, 36–37) |
| Cypro-Minoan translations | 98 texts, incomplete; 601 words; 72 sign values | di Mino's readings: the sign groups of the words read, each with its line and Appendix A page, and no group for a word left unread; never counted with Linear A |
| Cypro-Minoan grammar, lexicon, onomasticon & grid | 22 grammar hypotheses (1 CONFIRMED, 13 PROBABLE, 7 CANDIDATE, 1 SPECULATIVE after blind 41-text §7 holdout); 387 lexicon entries (17 paradigm stems, 19 lexical, 95 onomastic refs, 256 phonetic; 40 with IG XV 1 Amathus Eteocypriot comparanda); 95 onomasticon entries; 72 ruled / 28 unvalued aggregate grid | Read-word analytical layers built exclusively from ruled signs (T5 compliant: unvalued-sign hypotheses and `unread_words.json` stay unshipped) with deterministic statistical kernels in `models/cypro-minoan-kernel/`; never counted with Linear A |
| Old Assyrian Text-Fabric | 4,775 documents; 314,012 words | CDLI-derived: matching P-numbers must not be counted independently |
| Ebla Vocabulary | 142 pages; 904 links | Manuscript/source pages, VE entries, and later scholarship are explicitly typed |
| Morphology evidence bank | 3,917,227 unique source-qualified rows from ORACC, Old Assyrian, TLHdig, and DAPCA | Analysis/token rows, not witness counts; 2,026,874 pass the strict typed-preservation filter |
| Witness graph | 182,912 nodes; 12,187 links | Partial identity/discovery graph; only 5,953 adjudicated identity links are deduplicable |

Of these, the repository ships the Cypro-Minoan catalogue, di Mino's readings of 98 translated texts, and the
read-word analytical layers (`grammar_hypotheses.json`, `lexicon.json`, `onomasticon.json`, `grid.json` in
`data/ane/cypro-minoan/`, read by `tools/linear_a/cypro_minoan_lookup.py` and rendered under
`wiki/aegean/cypro-minoan/`) alongside IG XV 1's records (`data/ane/ig-xv-1-cypriot/`); the other layers are
described here and not shipped. The three Cypriot scripts, their editions, sign values and language proposals:
[cypriot-scripts.md](cypriot-scripts.md).

The TLHdig raw archive inventory finds 13,466 `<lb lg="Hur">` markers; the
normalized index contains 13,442 Hurrian-tagged lines after excluding filesystem
metadata, one encrypted payload, and non-indexable source structure.

## Acquisition gaps

- **Current complete Cypro-Minoan edition:** the reusable interim layers are
  indexed, but a current complete edition-grade export with explicit reuse
  terms remains unavailable.
- **Comprehensive Hurrian/ChS:** no supported complete export has been verified.
  TLHdig is the current open, language-tagged interim layer.
- **IG XV 1:** 311 of 410 records are indexed.
