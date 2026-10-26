---
name: data/contact/syriac_lexicon
title: Syriac lexicon
desc: The Classical Syriac words of English Wiktionary that name their root, with the root in Latin letters and the Wiktionary glosses.
tags: [data, contact, aramaic, syriac]
license: CC BY-SA 4.0
created: 2026-10-25T23:50:00Z
updated: 2026-10-26T03:10:00Z
---

`syriac_lexicon.jsonl` holds 1,391 entries: the 1,369 Classical Syriac entries of English Wiktionary that name a
root, one row per root (22 name two). The other 2,535 Wiktionary entries name none and are not here. The root index
keys each row on its `root` alone.

| Field | Content |
| --- | --- |
| `id` | `syr:wikt:`, the word, its part of speech and, where Wiktionary numbers them, the etymology; `:1`, `:2` for a word with two roots, and `#2` for a second Wiktionary entry of the same spelling and part of speech (ܬܩܠܐ "weight, mass, bulk" and "weighing, weight") |
| `form_original` | the word as Wiktionary writes it, in Syriac script |
| `root_original`, `root` | the root as Wiktionary gives it (its `syc-root` template or its "belonging to the root" category), and the same in Latin letters, hyphenated, letter for letter as `tools/core/sedra.py` reads Syriac: alaph `ʔ`, ʿe `ʕ`, ḥeth `ḥ`, ṭeth `ṭ`, ṣadhe `ṣ`, shin `š` |
| `normalized` | Wiktionary's romanization, on 531 entries; empty on the rest |
| `meaning` | the Wiktionary glosses, the most specific line of each sense; on 8 entries whose only senses point to another word ("female equivalent of ܙܡܪܐ (zammārā)") that pointer |
| `pos` | Wiktionary's part of speech: `noun` (1,232), `adj` (64), `verb` (54), `proper_noun` (31; Wiktionary's `name`, which the root index flags as a name), `adv` (6), one each of `conj`, `prep`, `intj` and `pron` |
| `semantic_domain`, `dialect_labels` | `general`, `Syriac` |
| `match_keys` | the root hyphenated and run together, and the romanization where there is one |
| `source_refs` | English Wiktionary, with the URL of the word's page |
| `review_status` | `machine_imported`: read from Wiktionary without hand review |

**Source.** English Wiktionary's Classical Syriac entries, from kaikki.org's Wiktextract JSON Lines (extracted
2026-07-16 from the 2026-07-06 dump; 3,904 records). Wiktionary's text is under CC BY-SA 4.0 (and the GFDL); credit
goes to the Wiktionary contributors, and this file and anything derived from it carry the same terms. The roots and
glosses are Wiktionary's, written by its contributors, not a dictionary's.

**Checked against SEDRA.** 795 rows name a word that SEDRA III also holds under the same spelling. For 544 the root
is SEDRA's. For 123 it is SEDRA's root as SEDRA writes hollow, geminate and weak roots (k-n for k-w-n, ḥ-b for
ḥ-b-b). For 86 SEDRA files the word as its own root and Wiktionary names the root it derives from (ܡܥܪܬܐ "cave":
ʕ-w-r). 22 are homographs: SEDRA's word of that spelling is another word (ܡܛܪܐ "guarding" here, "rain" in SEDRA).
20 (2.5%) analyse the same word differently, among them ܡܐܢܐ "implement" (here ʔ-n-ʔ, SEDRA m-ʔ-n) and ܢܘܟܪܝܐ
"foreign" (here n-k-r-y, SEDRA n-k-r). The other 596 rows have no SEDRA word of the same spelling to check against.

**Not included.** The private build fills this slot with SEDRA III (Kiraz 1996, Beth Mardutho's terms), which is not
redistributed. No SEDRA row or field is here, and this file's lexemes are not SEDRA's, so a run on it is not the
private configuration (see the note to [the pre-registration](../../docs/shoresh-preregistration.md)).
`tools/linear_a/fetch_sedra.py` builds a Syriac lexicon for this slot on the user's own machine from Sedra's weekly
data release (Sedra V, CC BY-NC 4.0), with a data overlay to build an index on, and leaves this file as it is. Its
rows carry the etymologies Sedra records; of the 85 lexemes in the 2026-10-25 build that have one, 57 are ruled loans
in `tools/linear_a/sedra_loans.json` and have the domain `loan`, and 28 record a Greek translation or a Hebrew cognate
instead of a source. The root index does not read the domain, and loans stay in the build.
