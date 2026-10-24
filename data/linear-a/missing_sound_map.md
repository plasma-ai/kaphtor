---
name: data/linear-a/missing_sound_map
title: Linear A missing-sound map
desc: The phonemic gaps of the Linear A syllabary against the Proto-Semitic consonants, the signs whose values fill them, and the positional behaviour of the frequent unknown signs.
tags: [data, linear-a, signs, phonology]
license: CC BY 4.0
created: 2026-10-24T15:42:46Z
updated: 2026-10-24T15:42:46Z
---

The standard Aegean CV grid writes 12 consonant series, 11 once D and T are taken as one voicing pair; Proto-Semitic
has 29 consonants. `missing_sound_map.json`
records where the difference falls: which gaps a sign value fills, which the script writes by neutralization, and
which stay open.

| Key | Content |
| --- | --- |
| `methodology` | how the gaps were found (the grid against Northwest Semitic, Luwian and Middle Egyptian), which unknown signs count as candidates, and `standing` |
| `proto_semitic_inventory` | the 29 consonants and the vowels (after Lipiński, *Outline*, §10.11), and the grid's coverage of them |
| `cuneiform_parallels` | how cuneiform wrote sibilants, velars and pharyngals (Lipiński §§13.2, 18.3, 19.9), beside Linear A |
| `standard_grid` | the grid's 11 consonant series (D/T as one) and what each neutralizes, and six signs outside it (RA₂, PA₃, PU₂, TA₂, ZO, NWA) |
| `filled_gaps` | six signs whose values fill a gap: *314 ḤA, *118 ṬA, PA₃ BA, *310 IN, *306 ʿA, *21F HA; each with the phonemes it covers, `key_evidence` words, and Lipiński's phonology where given |
| `open_gaps` | eleven gaps, each with its phonemes, `description`, `priority`, `likely_script_strategy`, `candidate_signs` and `status` |
| `syllabic_behavior_index` | fifteen frequent unknown signs counted by word position in `corpus.json`, each with an `assessment` |

**Standing.** A sign value carries the standing and confidence `sign_values.json` gives it: resolved (TA₂, AU),
proposed (the six filled-gap signs, ZU, *305, *34, *301, JU, *28B) or speculative (*86, *324, *325, *333).

**Evidence.** Each evidence word is spelled as `corpus.json` writes it and read as `lexicon.json` reads it, with the
lexicon's rival where it gives one; readings from *Ya Diktu* (DU-*314-RE, *307-PU₂-RE, A-TA-I-*301-WA-JA) cite it.
`other_values` names a second value the sign's record allows (*314 bu, *118 d or ṯ), and *118 and *21F note their
logograms (the talent, OVISf).

**Gap status.** `FILLED`: conventional signs write the gap (the vowel signs write aleph). `PROPOSED`: a proposed value
writes it (ʿ, h, the interdentals). `LIKELY_NEUTRALIZED`: the grid writes it with a neighbouring series (ṣ in S, g and
ġ in K). `POLYVALENT`: each guttural and emphatic sign serves every vowel. `SPECULATIVE`: further VC signs. `OPEN`: a
slot with a speculative candidate (/bu/ *325, /bi/ *333).

**Positions.** A word token is split at "-" into sign positions and at "+" into the signs of a ligature; a token of
one position stands alone. Brackets, quotation marks and the dot under a damaged sign are ignored.

`tools/linear_a/sign_proposer.py --polyvalent` draws consonant candidates from the `LIKELY_NEUTRALIZED` gaps.

**Sources.** E. Lipiński, *Semitic Languages: Outline of a Comparative Grammar* (OLA 80), for the inventory and the
cuneiform and phonological notes; di Mino, *Ya Diktu: Grammar of the Minoan Peak Sanctuary Libation Formula*, for the
formula readings; the gaps, candidates and values are di Mino's.
