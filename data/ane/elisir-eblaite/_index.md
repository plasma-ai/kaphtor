---
name: data/ane/elisir-eblaite
title: ELiSiR Eblaite lexicon
desc: The 37 published entries of Erica Scarpa's ELiSiR, a linked-data lexicon of Eblaite, each with its forms, senses and editorial note, CC BY 4.0.
tags: [data, eblaite, lexicon]
license: CC BY 4.0
created: 2026-11-13T19:10:00Z
updated: 2026-11-13T19:10:00Z
---

# ELiSiR Eblaite lexicon

[[data/ane/_index|..]]

[[data/ane/elisir-eblaite/MANIFEST.json|MANIFEST.json]]: The source repository and commit, the source files' checksums, the licence, counts and the output's checksum.

[[data/ane/elisir-eblaite/records.jsonl|records.jsonl]]: 37 lexical entries, each with its canonical form, other forms, senses, citations and the source's JSON-LD in `raw`.

***

Erica Scarpa, *ELISIR* (Zenodo, 2025, doi:10.5281/zenodo.17051643; gitlab.com/erica-scarpa/elisir), CC BY 4.0.
The lexicon is a pilot: 37 entries, 14 of them classed as Sumerograms and 2 as Akkadograms.

```bash
uv run --no-sync python -m tools.ane.aneq elisir father
```
