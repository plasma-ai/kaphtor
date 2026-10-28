---
name: data/linear-a/paradigm-b/paradigm
title: Paradigm B inventories
desc: The five frozen morphological inventories of Paradigm B, Central Semitic and its Northwest Semitic floor against Luwian, Hurrian and Egyptian, each morpheme cited to a grammar.
tags: [data, linear-a, paradigm-b]
sources: []
license: CC BY 4.0
created: 2026-10-29T15:12:45Z
updated: 2026-10-29T15:12:45Z
---

# Paradigm B inventories

[[data/linear-a/paradigm-b/_index|..]]

[[data/linear-a/paradigm-b/paradigm/cs.json|cs.json]]: Central Semitic, the headline arm: 93 morphemes (85 at cost 0, 69 distinct realizations), 67 attested forms.

[[data/linear-a/paradigm-b/paradigm/egyptian.json|egyptian.json]]: Middle Egyptian: 65 morphemes (62 distinct realizations), 42 attested forms.

[[data/linear-a/paradigm-b/paradigm/hurrian.json|hurrian.json]]: Hurrian: 74 morphemes (62 distinct realizations), 41 attested forms.

[[data/linear-a/paradigm-b/paradigm/luwian.json|luwian.json]]: Luwian: 68 morphemes (59 distinct realizations), 42 attested forms.

[[data/linear-a/paradigm-b/paradigm/nws_floor.json|nws_floor.json]]: The `cs` morphemes attested in Northwest Semitic, the conservative floor: 79 morphemes, 45 attested forms.

***

`build_paradigm.py` (in `tools/core/frozen/paradigm_b/scripts/`) wrote these files from its hand-encoded tables; each
morpheme carries its side (`kind`), order class (`position`), phonemic shape, function, the languages it is cited
from (`attested_in`), its citations and its cost (0 for an attested morpheme; 0.40 for the two priced innovations,
which enter only the `ext` ablation). `attested_forms` are the inflected forms the selftest parses. The build refused
any entry that names a Linear A form, "Linear A", "Minoan" or "Ya Diktu" (PROTOCOL-B §4.1). The citations' section
numbers marked "(topic)" were not checked against the grammars before the freeze, as each file's `_meta` says. The
port changed one string per file, the `_meta` attribution (`PORT-LEDGER.json`).
