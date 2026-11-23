---
name: data/share-alike/latin
title: LiLa LatInfLexi inflected Latin forms
desc: The 816,985 inflected Latin word forms of the LiLa LatInfLexi lexicon, CC BY-SA 4.0.
tags: [data, latin, indo-european]
license: CC BY-SA 4.0
created: 2026-11-23T15:42:00Z
updated: 2026-11-23T15:42:00Z
---

# LiLa LatInfLexi inflected Latin forms

[[data/share-alike/_index|..]]

[[data/share-alike/latin/latinf_forms.jsonl|latinf_forms.jsonl]]: One row per LatInfLexi form: lexeme identifier and orthographic form (816,985).

***

`latinf_forms.jsonl` holds 816,985 rows in source order, cut to the two fields read by `models/language-id-kernel/lid.py` (`4,386` lexemes, `765,540` clean forms) as an Indo-European non-Greek control.

**Source.** LiLa: Linking Latin (`LatInfLexi`), ERC Consolidator Grant 769994, CC BY-SA 4.0. Anything derived from this file carries the same terms.

**Build.** `models/language-id-kernel/build_shipped_inputs.py --latin` cuts the file from `LatInfLexi-forms.csv`; with `--check` it compares the two and writes nothing.
