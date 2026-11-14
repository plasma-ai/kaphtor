---
name: data/ane/isicily-semitic
title: I.Sicily, Semitic inscriptions
desc: The 73 inscriptions of I.Sicily whose language is Punic, Phoenician or Hebrew, with findspot, object, date and the edition where the source gives one, CC BY 4.0.
tags: [data, punic, sicily, epigraphy]
license: CC BY 4.0
created: 2026-11-13T19:10:00Z
updated: 2026-11-13T19:10:00Z
---

# I.Sicily, Semitic inscriptions

[[data/ane/_index|..]]

[[data/ane/isicily-semitic/MANIFEST.json|MANIFEST.json]]: The source repository and commit, the selection rule, the licence, counts and the output's checksum.

[[data/ane/isicily-semitic/records.jsonl|records.jsonl]]: 73 inscriptions (67 Punic), each with its settlement, object type, material, date and I.Sicily URI; 19 carry a text.

***

I.Sicily (sicily.classics.ox.ac.uk; github.com/ISicily/ISicily, doi:10.5281/zenodo.4384232), ed. Jonathan Prag
and others, CC BY 4.0. A record is selected when its main or other language is Punic, Phoenician or Hebrew. Most
records are catalogue entries without a transcription.

```bash
uv run --no-sync python -m tools.ane.aneq isicily Erice
```
