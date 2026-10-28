---
name: data/linear-a/sign-registry
title: Linear A sign registry
desc: One record per Linear A sign, with its readings and their status, its Unicode rendering, a SigLA image, its Cretan Hieroglyphic and Linear B lineage, and the Gordon 1966 words that use it.
tags: [data, linear-a, signs]
license: CC BY 4.0
created: 2026-10-24T14:27:54Z
updated: 2026-10-24T15:17:23Z
---

`sign-registry.json` holds `metadata` and `signs`: 365 records, one per sign, keyed by `ab_number` (AB numbers for
the signs Linear A shares with Linear B, A numbers for the rest, the fractions from A701). The registry
says how each sign is written and where it comes from. The values beyond Linear B, and the evidence for them, are in
`sign_values.json`; each reading here carries the status that file gives.

| Field | Content |
| --- | --- |
| `ab_number`, `name` | the sign's number, and its label: a Linear B value (`da`), a logogram (`VIN`), a number (`*86`) or, for A325, its value `bu`; empty on 254 signs |
| `unicode_codepoint`, `unicode_glyph` | the code point and character, on the 320 signs Unicode encodes |
| `readings` | the sign's values, each `{value, consonant, vowel, source, confidence, is_primary, implications, status}`; *86's na carries a `note` |
| `rendering` | `unicode`, `unicode_glyph`, `unicode_name`, `unicode_block`, `unicode_status`, `unicode_source_refs`, `tier`, the Noto `font`, and the SigLA image of one attestation (`sigla_image`, `sigla_url`; none for A400, A408VAS, A409VAS and A805). AB100 VIR and AB131 VIN add `unicode_alias_conflict`: the code point the sign does not take (`not_unicode`), and why |
| `gordon_entries` | the words of Gordon 1966 §163 (*Evidence for the Minoan Language*, index of Minoan words) that use the sign, in Gordon's transliteration and sign values (60 words, on 38 signs). Twelve are spelled otherwise in the corpus (his DA-WE-DA is DA-RI-DA, his KU-DO-NI is KU-ZU-NI) |
| `evolution` | for 20 signs: `id`; the Cretan Hieroglyphic ancestor (`sign_number`, `pictographic_ancestor`, `font_codepoint_hex`, and `source`, who proposed the lineage); the Linear B sign; `cypro_minoan` (null throughout); a Proto-Sinaitic letter compared on 8 signs (`letter`, `meaning`, `connection_type`); and `graphic_tendencies` |
| `semantic_context` | for the same 20 signs, the `pictograph` |
| `pictographic_note`, `classification`, `classification_note` | the description of one pictograph (AB04), and the commodity class of one logogram (A304) |

**Status.** `conventional` marks the 49 Linear B values, AB76's `ra` and AB79's `zu`: Linear B ra₂ is rya or
lya, and AB76 reads /la/ with /ra/ beside it; Linear B *79 is tentatively zu (Davis 2026, 174 n. 641; Melena
reads wo₂, *The Untransliterated Syllabograms*, §15). A value beyond Linear B takes the standing `sign_values.json`
gives its sign: `proposed` marks ZU's ṯu, ḏu and ṯ̣u (the interdental range, which ZU writes before every vowel;
ṯ̣ keyed ẓ), and `speculative` a value held in its sign record only: QA's za, SE's se2, *86's na (a mostly
standalone sign whose syllabic value is undetermined), and *325's bu and at. Each reading keeps its own `confidence`: HIGH,
MEDIUM or LOW, or for *86 and *325 the lexicon's tier word (SPECULATIVE; CANDIDATE on *325's bu). The readings are the Linear B values and
these five signs' values; AU, TA₂ and the other values beyond Linear B are in `sign_values.json` alone.
`tools/core/skeleton.py` and `root_match.py` read the non-primary readings as alternate consonants.

**Rendering.** 320 signs have a standard Unicode code point (`unicode_status` STANDARD_UNICODE, tier
`unicode_native`). 45 have none and are known from their SigLA image (IMAGE_ONLY, tier `image_only`). The fraction
signs are named by letter (A701 A, A704 E, A713 O, …); the letters are labels, not vowels, and the fractions have no
reading here. Their values are under `fractions` in `sign_values.json`.

**Lineage.** Each `source` names who proposed the Cretan Hieroglyphic ancestor. Ferrara, Montecchi & Valério 2022 give
their own derivations in Appendix 2 and §1.1, and earlier scholars' comparisons (Evans 1921, DOCS², Davis 1964,
Soldani 2013, Younger 2000–2020 and others) in Appendix 1. Where a record follows an earlier scholar, its `source`
names Ferrara, Montecchi & Valério's own derivation beside it: they derive LA 01 from CH 009, LA 09 from CH 026, LA 54
from CH 041 and LA 61 from CH 013, and give LA 41 no Cretan Hieroglyphic counterpart. The pictographs follow CHIC
1996, 17 where CHIC describes the sign. A Proto-Sinaitic `connection_type` is `shared_phonetic_space` (the letter
shares the sign's sound) except on AB59, whose taw "mark" and CH 034 cross share a form.

**Sources.** Linear B values after Ventris 1952; the lineage as above; the word index after Gordon 1966, §163, whose
*pà*, *tá* and *rá* are PA₃, TA₂ and RA₂; the Unicode names list (Unicode 15.1). The SigLA images (sigla.phis.me,
CC BY-NC-SA 4.0) are not in this repository: `sigla_image` and `sigla_url` name the image of one attestation per sign.
Values beyond Linear B and the Proto-Sinaitic comparisons are di Mino's.
