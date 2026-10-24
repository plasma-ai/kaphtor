---
name: data/linear-a/sign_values
title: Linear A sign values
desc: The phonetic values of the Linear A syllabograms, the logograms and the fraction signs, with the resolved and proposed values listed apart.
tags: [data, linear-a, signs]
license: CC BY 4.0
created: 2026-10-22T18:19:34Z
updated: 2026-10-22T18:19:34Z
---

`sign_values.json` holds `schema_version` (2), `description`, `neutralization_classes`, `linear_b_notes`,
`resolution_summary`, `signs` (75 syllabograms), `logograms` (37) and `fractions` (17 signs, 11 attested
composites). Values beyond Linear B are di Mino's unless a record names another scholar.

| Key | Content |
| --- | --- |
| `neutralization_classes` | the consonant classes the script does not distinguish (K, P, R, S, T): the phonemes each sign series writes |
| `linear_b_notes` | how Linear A signs take their Linear B values (the shared AB numbers), and the signs Linear B lacks |
| `resolution_summary` | the resolved values (`phonemic`, `logograms`, `fractions`, with their counts and `total`) and `proposed` |
| `signs` | one record per syllabogram, keyed by its transliteration |
| `logograms` | one record per logogram, keyed by its sign number |
| `fractions` | the A700-series fraction signs: `signs`, `composites_attested`, `source` |

A value is **resolved** only on support that does not depend on a Semitic match: a Linear B value, a scribe's
arithmetic, or a spelling variant of the same word. `resolution_summary.proposed` lists the other values of CANDIDATE
or above, each `{entry, evidence}`, with the evidence where given. A **speculative** value sits in its sign's record
only. The resolved total counts phonemic values and logograms; fractions are counted apart. The file holds 38 values:
5 resolved (2 phonemic, 3 logograms) and 33 proposed (12 phonemic, 21 logograms), plus 3 resolved and 11 proposed
fraction values.

Each syllabogram record:

| Field | Content |
| --- | --- |
| `ab_number`, `sign_number` | the sign's AB number, and its number in the sign list |
| `linear_b` | the Linear B value of the same sign, where there is one |
| `primary` | the value read: `consonant`, `vowel`, `confidence` |
| `alternates` | other values on record, each with its confidence |
| `neutralization_class` | the consonant class the sign belongs to, or null |
| `confirmed_by` | the grounds for the value: the Linear B value, attestations, words it reads |
| `logographic_value`, `note` | a logographic use of the sign, and further evidence, where given |

Three records (PA₃, ZU and AU) carry `reading`, `ipa`, `consonant`, `vowel`, `confidence`, `sign_type` and `notes`
in place of `ab_number` and `primary`.

Each logogram record gives its `commodity` and `gloss`; a tiered logogram has its `tier`, `status` and `confidence`
(as in the lexicon: CONFIRMED, PROBABLE, CANDIDATE, SPECULATIVE), the proposed `root` and `semitic_term`, `standalone_count` and
`embedded_count` (uses with a numeral and inside words), `sites` and a `note`. Each fraction sign gives its
`a_number`, `value`, `status`, `tier`, `confidence` and `note`.

`tools/core/skeleton.py` labels the values as this file does, and `tests/linear_a/test_skeleton_status.py` checks
that the two agree.
