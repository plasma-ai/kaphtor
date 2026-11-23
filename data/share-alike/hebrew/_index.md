---
name: data/share-alike/hebrew
title: OSHB Hebrew and Aramaic words
desc: The 306,785 pointed words of the Open Scriptures Hebrew Bible (Westminster Leningrad Codex), CC BY 4.0.
tags: [data, hebrew, aramaic, semitic]
license: CC BY 4.0
created: 2026-11-23T15:42:00Z
updated: 2026-11-23T15:42:00Z
---

# OSHB Hebrew and Aramaic words

[[data/share-alike/_index|..]]

[[data/share-alike/hebrew/oshb_words.jsonl|oshb_words.jsonl]]: One row per OSHB word: verse reference, morphology code, and pointed surface form (306,785).

***

`oshb_words.jsonl` holds 306,785 rows in canonical order, cut to the three fields read by `models/language-id-kernel/lid.py`, `liturgy_c.py`, `verbs_e.py`, and `render/c_texts.py` (`923` Hebrew chapters, `300,689` clean pointed Hebrew words).

**Source.** Open Scriptures Hebrew Bible (`openscriptures/morphhb`), based on the Westminster Leningrad Codex (public domain), CC BY 4.0.

**Build.** `models/language-id-kernel/build_shipped_inputs.py --oshb` cuts the file from the full word list; with `--check` it compares the two and writes nothing.
