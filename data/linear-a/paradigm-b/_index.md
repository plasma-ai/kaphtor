---
name: data/linear-a/paradigm-b
title: Paradigm B data
desc: The frozen inputs and the five production runs of Paradigm B, the pre-registered held-out paradigm-prediction test, with the freeze's SHA256SUMS and the port ledger.
tags: [data, linear-a, paradigm-b]
license: CC BY 4.0, except snapshot/corpus.json (CC BY-NC-SA 4.0 AND CC BY 4.0) and controls_b.jsonl (row by row, below)
created: 2026-10-29T00:00:00Z
updated: 2026-10-29T16:13:43Z
---

# Paradigm B data

[[data/linear-a/_index|..]]

[[data/linear-a/paradigm-b/PORT-LEDGER.json|PORT-LEDGER.json]]: Every shipped file's frozen path and sha256, what pins it, and the port's substitutions; every withheld file with the reason.

[[data/linear-a/paradigm-b/SHA256SUMS|SHA256SUMS]]: The freeze's hashes of the research package, verbatim (sha256 f5d6733f…); it lists files the port withholds.

[[data/linear-a/paradigm-b/controls_b.jsonl|controls_b.jsonl]]: The 128 control windows of known language, rendered to Linear A signs.

[[data/linear-a/paradigm-b/formula_family.json|formula_family.json]]: The 33 inscriptions of the formula family, their tokens, damage flags and slots.

[[data/linear-a/paradigm-b/freeze-record|freeze-record]]: The record the option B freeze appended to the research package's PROTOCOL.md, copied verbatim; the run refuses to start without it.

[[data/linear-a/paradigm-b/paradigm/_index|paradigm/]]: The five frozen morphological inventories of Paradigm B, Central Semitic and its Northwest Semitic floor against Luwian, Hurrian and Egyptian, each morpheme cited to a grammar.

[[data/linear-a/paradigm-b/runs/_index|runs/]]: The five production runs Paradigm B made under its freeze, the observed family and controls, nulls D, D2 and D2×2 at 10,000 replicates and the gate, each with its manifest.

[[data/linear-a/paradigm-b/snapshot/_index|snapshot/]]: The Linear A corpus as Paradigm B froze it, read only to train the nulls' sign model.

***

These files are the inputs Paradigm B froze on 2026-10-09 and the runs it made under that freeze. The test, its
nulls and its gate are set out in [the pre-registration](../../../docs/paradigm-b-preregistration.md); the outcome
(G1 passed, G2 failed, no posterior) is in [the result](../../../docs/paradigm-b-result.md). The frozen code is in
`tools/core/frozen/paradigm_b/`.

`SHA256SUMS` lists paths in the research package (`data/paradigm/cs.json`, `controls/controls_b.jsonl`), and lists
the stage 1–3 files and `data/snapshot/lexicon.json` that are not shipped. `PORT-LEDGER.json` maps each shipped file
to its listed path. Where a file carried a private path or a credit other than "di Mino", the port replaced that
string; the ledger records the text each replacement wrote, and the maintainer's key, not shipped, the strings it
replaced. `tools/linear_a/validation/paradigm_b.py verify` checks every file's shipped sha256, and with `--key`
undoes the replacements and checks every file against its frozen sha256. The runs are flattened to
`runs/<run>.<file>`.

`snapshot/corpus.json` predates [corpus.json](../corpus.json) and differs from it; it is the corpus as frozen. It
is here only because the nulls are trained on it, and its readings are not this repository's.

## Licences

| File | Licence |
| --- | --- |
| `SHA256SUMS`, `freeze-record.md`, `PORT-LEDGER.json`, `runs/` | CC BY 4.0 |
| `formula_family.json` | CC BY 4.0 for the selection, slots and damage flags; the transliterations keep the corpus's terms ([corpus.md](../corpus.md)) |
| `paradigm/*.json` | CC BY 4.0: hand-encoded from the cited grammars, which are cited, not quoted |
| `snapshot/corpus.json` | CC BY-NC-SA 4.0 AND CC BY 4.0, as [corpus.md](../corpus.md) sets out |
| `controls_b.jsonl` | row by row, by its `source` field, below |

`controls_b.jsonl` holds one window per row after its `_meta` line. A window gives each token's surface form, its
lemma as the edition or dictionary assigns it and its rendering in Linear A signs, grouped by unit; no translation
or commentary is carried.

| Class | Rows | `source` | Terms |
| --- | --- | --- | --- |
| H1 Ugaritic prayer | 20 | `CUC KTU 1.x` | Copenhagen Ugaritic Corpus, `auto_parsing/0.2.7` (surface forms, DULAT lemma column): CC BY-NC 4.0 |
| H1 Hebrew Psalms | 24 | `OSHB Ps` | Open Scriptures Hebrew Bible, morphhb (words, Strong's lemmas): CC BY 4.0 |
| H3 Ugaritic prose | 24 | `CUC KTU 2.x`, `KTU 3.x` | Copenhagen Ugaritic Corpus: CC BY-NC 4.0 |
| H2 Egyptian | 24 | `ORAEC htp-dj-nswt` | ORAEC (Open Richly Annotated Egyptian Corpus) sentences and lemma ids: CC BY-SA 4.0 |
| H2 Luwian | 19 | `ACLT <text>` | Annotated Corpus of Luwian Texts (Ilya Yakubovich, web-corpora.net/LuwianCorpus), forms and lemmata as derived fields: ACLT states no licence, describes itself as a work in progress, and asks to be credited with its URL; the same terms as [rival-roots.md](../rival-roots.md) |
| NEG Linear B | 17 | `DAMOS/DMic` | DAMOS (Database of Mycenaean at Oslo, Federico Aurora, https://damos.hf.uio.no) tablets and forms, lemmatized by Aura Jorro's *Diccionario Micénico* I–II (Madrid 1985, 1993) headwords, as derived fields with that credit |

The share-alike Egyptian rows and the non-commercial Ugaritic rows keep their sources' terms; the windows' cut,
renderings and lemma grouping are ours, under CC BY 4.0.
