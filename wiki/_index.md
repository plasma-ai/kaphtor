---
name: wiki
title: Wiki
desc: The record, generated from the data: Linear A, the Semitic roots, the Pre-Greek lexicon and the Aegean scripts.
created: 2026-10-22T18:14:10Z
updated: 2026-11-06T23:18:29Z
---

# Wiki

[[_index|..]]

[[wiki/aegean/_index|aegean/]]: The Eteocretan inscriptions.

[[wiki/linear-a/_index|linear-a/]]: Inscriptions, words and signs, with the generated ledgers.

[[wiki/pre-greek/_index|pre-greek/]]: Greek words classed as Pre-Greek or as early Semitic loans: one generated page per word, filed by initial, with the feature and Semitic comparison ledgers.

[[wiki/semitic-roots/_index|semitic-roots/]]: One generated page per root, filed by first radical.

***

Every page is generated from `data/` by `tools/views/` (`python -m tools.views.build --write`): change the data or
the builder, and rebuild. The folder indexes belong to `wiki update`.
