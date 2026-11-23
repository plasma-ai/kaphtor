---
name: data/share-alike/cuneiform
title: ORACC CC0 Akkadian and Sumerian documents and ePSD2 Sumerian lexicon
desc: The 1,420 CC0 ORACC Old/Standard Babylonian Akkadian documents, 1,855 CC0 ORACC Sumerian documents and 3,589 clean vocalized ePSD2 Sumerian glossed lemmas, CC0 1.0.
tags: [data, akkadian, sumerian, cuneiform, oracc]
license: CC0 1.0
created: 2026-11-23T16:35:00Z
updated: 2026-11-23T16:35:00Z
---

# ORACC CC0 Akkadian and Sumerian documents and ePSD2 Sumerian lexicon

[[data/share-alike/_index|..]]

[[data/share-alike/cuneiform/oracc_akkadian.jsonl|oracc_akkadian.jsonl]]: One row per CC0 ORACC Old/Standard Babylonian Akkadian document with undamaged normalized tokens (1,420 rows; 72,536 clean words).

[[data/share-alike/cuneiform/oracc_sumerian.jsonl|oracc_sumerian.jsonl]]: One row per CC0 ORACC Sumerian document with undamaged normalized tokens (1,855 rows; 7,313 clean words).

[[data/share-alike/cuneiform/sumerian_epsd2_lexicon.jsonl|sumerian_epsd2_lexicon.jsonl]]: Unique clean vocalized Sumerian ePSD2 lemmas with English glosses extracted from CC0 ORACC Sumerian documents (3,589 rows).

***

These three cuts keep only documents marked CC0 1.0 in their ORACC metadata, supplying the Akkadian and Sumerian running-text arms of `models/language-id-kernel/lid.py`, `liturgy_c.py` and `morphology_i.py` and the non-Semitic Bronze Age isolate dictionary of `auto_anchors_j.py` (Kernel J).

| File | Rows | Fields | Clean yield |
| --- | ---: | --- | --- |
| `oracc_akkadian.jsonl` | 1,420 | `canonical_id`, `tokens` (`lang`, `norm`) | 1,417 unique documents; 72,536 clean words (`akk-x-oldbab`, `akk-x-stdbab`) |
| `oracc_sumerian.jsonl` | 1,855 | `canonical_id`, `tokens` (`lang`, `norm`) | 1,851 unique documents; 7,313 clean words (`sux`) |
| `sumerian_epsd2_lexicon.jsonl` | 3,589 | `normalized`, `meaning` | 3,589 lowercase vocalized lemmas with English guide words (`gw`/`sense`) |

**Source.** Open Richly Annotated Cuneiform Corpus (ORACC, https://oracc.museum.upenn.edu/), including ePSD2 and ETCSRI CC0 1.0 open-data releases.

**Build.** `models/language-id-kernel/build_shipped_inputs.py --oracc-akk` and `--oracc-sux` cut these files from the full ORACC document archives; with `--check` they compare the two and write nothing.
