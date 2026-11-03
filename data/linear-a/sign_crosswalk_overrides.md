---
name: data/linear-a/sign_crosswalk_overrides
title: Sign crosswalk overrides
desc: Hand-curated resolutions of sign labels to sign-registry.json codes, which win over every automatic route of the sign crosswalk.
tags: [data, linear-a, signs]
license: CC BY 4.0
created: 2026-11-03T23:49:05Z
updated: 2026-11-03T23:49:05Z
---

`sign_crosswalk_overrides.json` holds `_doc` and `overrides`. `tools/core/sign_crosswalk.py` resolves every sign label
the project meets (corpus transliterations, SigLA codes, SigLA crop names, lineara sign boxes) to the `ab_number` codes
of `sign-registry.json`; an override is a label whose resolution a person has settled by hand, so no automatic route
and no rebuild changes it.

| Field | Content |
| --- | --- |
| key | the label exactly as its source writes it; a label differing only by an underdot (an uncertain reading) matches too |
| `kind` | one of `sign`, `ligature`, `fraction`, `divider`, `numeral`, `lacuna`, `unresolved` |
| `codes` | registry `ab_number` codes in order, a ligature's components one by one; `?` for a component no one can name |
| `note` | why the label resolves so |

The crosswalk refuses to load an override whose `kind` is not in that list or whose codes are absent from the
registry. The file holds no overrides: every label resolves by glyph, code, registry name or a lineara label, or is
reported `unresolved`.
