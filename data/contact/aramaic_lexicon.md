---
name: data/contact/aramaic_lexicon
title: Aramaic lexicon
desc: Syriac roots from the Aramaic Root Atlas, with their glosses and the Hebrew and Arabic cognates it lists.
tags: [data, contact, aramaic, syriac]
license: Apache-2.0
created: 2026-10-25T22:00:00Z
updated: 2026-10-25T22:45:00Z
---

`aramaic_lexicon.jsonl` holds 1,647 entries from the Aramaic Root Atlas, built from its `cognates.json` and
`known_roots.json`.

| Field | Content |
| --- | --- |
| `id` | `aram:atlas:` and a running number |
| `form_original` | the Syriac root as the Atlas writes it |
| `normalized`, `root`, `match_keys` | a transliteration of that Syriac, the same hyphenated, and the keys the root index matches on. In 147 entries this differs from the Atlas's own root key, and some are a derived form rather than the root: 0086 ܡܣܩ `m-s-q` for s-l-q "ascend", 0099 `tḥz` for ḥ-z-y, 0090 `wṭr` for n-ṭ-r |
| `meaning` | the Atlas gloss |
| `pos` | read from the gloss by keyword: `verb` (190), `noun` (14), otherwise `unknown` (1,443) |
| `semantic_domain` | from `pos` alone: `nominal_root` for a noun, `verbal_root` for anything else; it is not a semantic field |
| `dialect_labels` | `Syriac` |
| `cognates`, `attested_forms` | the Hebrew and Arabic cognates the Atlas lists, and, on 163 entries, its attested Syriac forms |
| `source_refs`, `review_status` | the source of the row; every row is `machine_imported` |

**Source.** The Aramaic Root Atlas; its `data/roots/cognates.json` and `known_roots.json` are under Apache-2.0. Its
licence notes describe `cognates.json` as an "Initial set extracted from scholarly sources; the rest generated via the
Anthropic Claude API and partially curated (493 in Phase 1, 84 for Targum Jonathan in v3.1, 38 for the v3.3 corpora).
Not yet systematically validated against authoritative lexicons (HALOT, BDB, Sokoloff, Brockelmann, Lane, Wehr)."
Treat a gloss or cognate here as a lead.

**Not included.** The private build also joins the Atlas rows to the BHSA lexicon (CC BY-NC 4.0) and to the SEDRA
Syriac lexicon (Beth Mardutho's terms), adds 403 Biblical Aramaic rows from the BHSA, and takes semantic fields, and
59 more rows, from the Atlas's `semantic_fields.json`, which has no stated licence. None of that is in this file: the
BHSA and SEDRA fields and the `Biblical Aramaic` label they give are out, the part of speech is read from the Atlas
gloss, and `semantic_domain` is the generic one the builder gives before the semantic fields are applied.
