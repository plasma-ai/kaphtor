---
name: data/contact/akkadian_lexicon
title: Akkadian lexicon
desc: ORACC's CAMS/GKAB Akkadian glossary in the root index's Akkadian slot, with ḫ restored in the keyed form and every ORACC name class marked as a name.
tags: [data, contact, akkadian]
license: CC0 1.0
created: 2026-10-25T23:50:00Z
updated: 2026-10-25T23:50:00Z
---

`akkadian_lexicon.jsonl` holds the 6,233 entries of [the Akkadian literary glossary](../ane/akkadian_literary.md)
(ORACC's CAMS/GKAB project), one row each, under the same ids, in the form the root index reads. The root index
keys each row on `normalized`; 9 give no key (`ā`, `ai`, `i`, `u`, `ū`, `Ea` and `U`).

| Field | Content |
| --- | --- |
| `id`, `source_corpus` | as in the glossary: `oracc:cams-gkab:` and the ORACC entry id; `ORACC cams/gkab` |
| `form_original` | the citation form as ORACC writes it |
| `form`, `normalized` | the citation form with ORACC's `h` written `ḫ` (812 entries: ORACC writes ḫ as h, and cuneiform has no other h), so `muhhu` is keyed as m-ḫ-ḫ |
| `match_keys` | the glossary's lookup keys: the citation form without diacritics (š as sh) and the attested spellings |
| `meaning` | ORACC's guide word and senses |
| `pos`, `oracc_pos` | ORACC's part of speech, except that every ORACC name class (divine 629, personal 518, celestial 96, settlement 94, temple 71, geographical 62, royal 51, lineage 42, ethnic 27, month 16, watercourse 6, field 2, object 1) is `proper_noun`, which the root index flags as a name; `oracc_pos` keeps ORACC's tag |
| `semantic_domain`, `review_status`, `frequency`, `source_refs` | as in the glossary |

192 entries are phrases (`mimma šumšu`, `adi muhhi`), which the index keys and never links. 69 names carry letters
the Akkadian notation does not read, kept as ORACC gives them: Sumerian ŋ (Esaŋila, Ŋešnugal), `x` for a broken
sign or a Greek and Persian x (Abi-xxx, Artaxerxes), `c` in Greek and Persian names (Antiochus, Cyrus); so do two
Sumerograms (KUR₂, SUMNIG₂) and one form ORACC writes with q̄ (zuqiq̄qīpu).

**Source.** ORACC releases its project data under CC0 1.0, recorded in each package's metadata; cite the project
as ORACC asks.

**Not included.** The private build fills this slot with the glossary of Huehnergard's *A Grammar of Akkadian*, which
gives each word's root consonants, and Akkadian words gathered from the Anchor Bible commentaries; neither is
redistributed. No row of either is here: the roots here are read from the citation form, and the words are
first-millennium scholarly and literary Akkadian, so a run on this file is not the private configuration (see the
note to [the pre-registration](../../docs/shoresh-preregistration.md)).
