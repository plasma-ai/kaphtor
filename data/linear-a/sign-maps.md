---
name: data/linear-a/sign-maps
title: Linear A and Linear B sign maps
desc: The SigLA sign list of Linear A (362 signs) and the 268 characters of Unicode's Linear B and Aegean Numbers blocks, each with its code point, name and status.
tags: [data, linear-a, linear-b, signs]
license: CC BY-NC-SA 4.0 AND CC BY 4.0
created: 2026-10-24T15:00:00Z
updated: 2026-10-24T15:09:40Z
---

Two sign lists. `tools/linear_a/aegean_unicode_lookup.py` reads both; `analysis/sign_analysis.py` reads the SigLA list.

`sigla-sign-map.json` holds `signs`, `total` and `source` (the SigLA sign list, sigla.phis.me/sign-list.html). Each
of the 362 signs gives its `ab_number` and `name`, the SigLA image of one attestation (`tablet`, `image_file`,
`image_url`; A400 has no image), and its Unicode `unicode`, `unicode_glyph`, `unicode_name` and `unicode_status`. Two
signs carry `unicode_alias_conflict`: the code point the sign does not take (`not_unicode`), and why (AB100 VIR, AB131
VIN). The SigLA images (CC BY-NC-SA 4.0) are not in this repository; the file names and links them.

`linear-b-sign-map.json` holds `metadata` and `signs`: the 268 characters of Unicode's Linear B Syllabary, Linear B
Ideograms and Aegean Numbers blocks (74 syllabograms, 117 ideograms, 45 numbers, 9 metrological signs, 3 editorial
marks, and as `sign_type` "unknown" 14 syllabic signs of unknown value and 6 monograms), each with its `sign_number`
(empty on 63), `standard_value` (empty on 20), `token_values`, `sign_type` and Unicode fields, all read from the
Unicode names list.

Every `unicode_name` in both files matches the Unicode 15.1 names list for its code point.

**Licence.** `sigla-sign-map.json` carries SigLA's dataset (Ester Salgarella and Simon Castellan, sigla.phis.me), which
is under CC BY-NC-SA 4.0, and so is this file; its Unicode fields are CC BY 4.0. `linear-b-sign-map.json` is CC BY 4.0.
