---
name: data/share-alike/ugaritic
title: EUPT Ugaritic vocalized tokens
desc: The 2,510 vocalized Ugaritic tokens of the Electronic Ugaritic Poetic Texts (EUPT), CC BY-SA 4.0.
tags: [data, ugaritic, semitic]
license: CC BY-SA 4.0
created: 2026-11-23T15:42:00Z
updated: 2026-11-23T15:42:00Z
---

# EUPT Ugaritic vocalized tokens

[[data/share-alike/_index|..]]

[[data/share-alike/ugaritic/eupt_tokens.jsonl|eupt_tokens.jsonl]]: One row per EUPT token: document, first column location, and vocalized surface form (2,510).

***

`eupt_tokens.jsonl` holds 2,510 rows in source order, cut to the three fields read by `models/language-id-kernel/lid.py` and `render/c_texts.py` (`23` column-documents, `1,618` clean vocalized words).

**Source.** Electronic Ugaritic Poetic Texts (EUPT), CC BY-SA 4.0. Anything derived from this file carries the same terms.

**Build.** `models/language-id-kernel/build_shipped_inputs.py --eupt` cuts the file from the full token list; with `--check` it compares the two and writes nothing.
