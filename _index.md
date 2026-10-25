---
name: kaphtor
title: kaphtor
desc: Tools and data for Linear A research and comparative Semitics.
tags: [root]
created: 2026-10-22T18:14:10Z
updated: 2026-10-22T19:27:15Z
---

# kaphtor

[[assets/_index|assets/]]: Noto Sans fonts for the Aegean scripts, and the README banner.

[[codemeta.json|codemeta.json]]: The software's CodeMeta record, for research-software indexes.

[[data/_index|data/]]: The datasets, each with a datasheet or manifest naming its licence, grouped by licence and subject.

[[docs/_index|docs/]]: The repository's rules and methods, and the guides to its corpora.

[[llms.txt|llms.txt]]: A map of the repository for language-model readers.

[[wiki/_index|wiki/]]: The record, generated from the data: Linear A, the Semitic roots and the Aegean scripts.

***

Code lives in `tools/` and `tests/`, and the two Claude Code skills in `skills/`; each carries a
`README.md`. Code is Apache-2.0 (`LICENSE`); data and writing are CC BY 4.0 (`LICENSE-CC-BY-4.0`); third-party
material keeps its own terms, recorded in each datasheet and set out in `NOTICE`: the Linear A corpus builds on
SigLA's CC BY-NC-SA 4.0 data, and `data/share-alike/` is CC BY-SA 4.0. Cite as in `CITATION.cff`.
`.github/` holds the issue and pull-request templates and the gate workflow; `.gitignore` keeps caches, a user's own
downloads and the indexes built from restricted sources out of the tree.
