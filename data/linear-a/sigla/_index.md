---
name: data/linear-a/sigla
title: SigLA source
desc: SigLA's own database file, unchanged, and the hand-set corpus.json keys the SigLA database build reads beside it.
tags: [data, linear-a, sigla]
license: CC BY-NC-SA 4.0 AND CC BY 4.0
created: 2026-11-03T22:07:01Z
updated: 2026-11-03T22:07:01Z
---

# SigLA source

[[data/linear-a/_index|..]]

[[data/linear-a/sigla/corpus_key_overrides.json|corpus_key_overrides.json]]: The corpus.json keys for the SigLA documents no other rule matches: joins, and keys written with (?); CC BY 4.0.

[[data/linear-a/sigla/database.js|database.js]]: SigLA's corpus as the site serves it, two OCaml Marshal blobs; CC BY-NC-SA 4.0.

***

`tools/linear_a/build_sigla_db.py` decodes `database.js` into `../sigla_db.json`; the datasheet is
[sigla_db.md](../sigla_db.md). SigLA's dataset is © 2020– Ester Salgarella and Simon Castellan, under CC BY-NC-SA
4.0.
