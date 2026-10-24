---
name: data/linear-a/morphemes
title: Linear A affixes and particles
desc: The prefixes, suffixes, case vowels and particles the morphological analysis strips or tests, each with its value, function, tier and evidence.
tags: [data, linear-a, morphology]
license: CC BY 4.0
created: 2026-10-24T15:23:03Z
updated: 2026-10-24T15:23:03Z
---

`morphemes.json` holds `schema_version`, `description`, `prefixes`, `suffixes`, `case_vowels` and `particles`.

| Field | Content |
| --- | --- |
| `prefixes` | 6 (JA-, A-, U-NA-, RU-, I-, TA-), each `{form, value, function, confidence, evidence, strips_to}`; U-NA- and RU- add a `note` |
| `suffixes` | 8 (-TE, -TI, -TU, -NA, -NU, -NE, -ME, -SI), with the same fields; -TI adds a `note` |
| `case_vowels` | a `description` and the final vowels U, A and I, each `{function, confidence, evidence}` |
| `particles` | JA "O!", U "and", DU "(that) of" and RE "to, for, as", each `{form, value, meaning, confidence, source}` |

`confidence` is the lexicon's tier word: CONFIRMED, PROBABLE, CANDIDATE or SPECULATIVE. An `evidence` string names a
corpus word, with the lexicon's reading where it has one (JA-RA = yara).

`tools/linear_a/ventris_propagate.py` strips each prefix and suffix by its `form`, alone and in pairs, before it
matches a word against the roots. `strips_to` is false on -TI alone, whose note says why; `ventris_propagate.py` does
not read the field and strips -TI too. `ventris_decode.py` runs propagation as one of its phases.

**Sources.** U, DU and RE after Gordon 1966, §163, and the vocative JA after di Mino, *Ya Diktu*; the cognates and grammars each `function` and `note` cites; the
affixes, values and tiers are di Mino's.
