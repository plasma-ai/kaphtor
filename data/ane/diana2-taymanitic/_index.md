---
name: data/ane/diana2-taymanitic
title: DIANA II, Taymanitic
desc: The 556 headwords of Al-Jallad's Dictionary of the Inscriptions of Ancient North Arabia II (Taymanitic), the dictionary, toponyms, group names and onomasticon, each with its gloss, compared forms, attestations and printed page, CC BY-NC 4.0.
tags: [data, taymanitic, ancient-north-arabian, dictionary]
license: CC BY-NC 4.0
created: 2026-11-16T17:30:00Z
updated: 2026-11-16T17:30:00Z
---

# DIANA II, Taymanitic

[[data/ane/_index|..]]

[[data/ane/diana2-taymanitic/MANIFEST.json|MANIFEST.json]]: The work and its DOI, the PDF's checksum, the pages read, the notation, the licence, counts by kind, section and language, and the output's checksum.

[[data/ane/diana2-taymanitic/records.jsonl|records.jsonl]]: 556 headwords: 103 of the dictionary (pp. 1–24), 7 toponyms, 10 group names and 436 personal names of the onomasticon (pp. 27–78), each with its gloss, part of speech, root, the forms it compares with their languages, the inscriptions that attest it, its commentary and its printed page.

***

Ahmad Al-Jallad, *Dictionary of the Inscriptions of Ancient North Arabia, Volume II: Taymanitic*, version 2026.1,
OCIANA, Columbus 2026, doi:10.5281/zenodo.24223110, © 2026 Ahmad Al-Jallad, CC BY-NC 4.0: the entries as printed,
with their pages, for non-commercial use. Read from the PDF's own text layer; the printed page is the PDF page less
26. The sibilants are printed s¹ s² s³ (type s1, s2, s3); a homograph is an integer. The Semitic roots cite this book
as Al-Jallad 2026b, by page.

```bash
uv run --no-sync python -m tools.ane.aneq diana nṣr --volume 2
uv run --no-sync python -m tools.ane.aneq diana ṣlm --volume 2 --section onomasticon
```
