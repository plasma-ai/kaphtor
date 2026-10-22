---
name: docs/corpora/aegean-comparative-corpora
title: Aegean and Anatolian comparative corpora
desc: The Hurrian, Cypro-Minoan, Cypriot, Old Assyrian and Eblaite layers indexed as controls for Linear A, with their coverage, boundaries and acquisition gaps.
tags: [corpora, docs]
created: 2026-10-22T18:14:10Z
updated: 2026-10-22T18:14:10Z
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
| Old Assyrian Text-Fabric | 4,775 documents; 314,012 words | CDLI-derived: matching P-numbers must not be counted independently |
| Ebla Vocabulary | 142 pages; 904 links | Manuscript/source pages, VE entries, and later scholarship are explicitly typed |
| Morphology evidence bank | 3,917,227 unique source-qualified rows from ORACC, Old Assyrian, TLHdig, and DAPCA | Analysis/token rows, not witness counts; 2,026,874 pass the strict typed-preservation filter |
| Witness graph | 182,912 nodes; 12,187 links | Partial identity/discovery graph; only 5,953 adjudicated identity links are deduplicable |

This repository ships none of these layers.

The TLHdig raw archive inventory finds 13,466 `<lb lg="Hur">` markers; the
normalized index contains 13,442 Hurrian-tagged lines after excluding filesystem
metadata, one encrypted payload, and non-indexable source structure. Preserve both
counts with their definitions.

## Acquisition gaps

- **Current complete Cypro-Minoan edition:** the reusable interim layers are
  indexed, but a current complete edition-grade export with explicit reuse
  terms remains unavailable.
- **Comprehensive Hurrian/ChS:** no supported complete export has been verified.
  TLHdig is the current open, language-tagged interim layer.
- **IG XV 1:** retain the 99 failed record IDs in the acquisition manifest and
  retry only through the documented official API; never claim completeness from
  the 311 locally indexed records.
