---
name: data/share-alike/linear-b
title: Linear B tokens of Pylos and Knossos
desc: The syllabic tokens of the Pylos and Knossos Linear B tablets, each with its tablet, line, place and its status against DAMOS, CC BY-NC-SA 4.0.
tags: [data, linear-b]
license: CC BY-NC-SA 4.0
created: 2026-11-23T15:30:00Z
updated: 2026-11-23T15:30:00Z
---

# Linear B tokens of Pylos and Knossos

[[data/share-alike/_index|..]]

[[data/share-alike/linear-b/linear_b_tokens.jsonl|linear_b_tokens.jsonl]]: One row per syllabic token of a Pylos or Knossos tablet, in tablet, line and token order (13,254).

***

`linear_b_tokens.jsonl` holds 13,254 rows from 3,677 tablets: 7,107 from Pylos and 6,147 from Knossos. The language
identification suite in `models/language-id-kernel/` reads it as its Linear B control: real tablets, whose language
is known, set under the same instruments as Linear A.

| Field | Content |
| --- | --- |
| `document_id` | the tablet's siglum (`PY An 657`, `KN Fp(1) 1`) |
| `line_id`, `token_index` | the line and the token's place in it |
| `token_type` | `syllabic` on every row; logograms, numerals and dividers are not in this file |
| `editorial_status` | `clean` (8,711), `damaged` (4,508), `normalized` (20), `restored` (14) or `uncertain` (1) |
| `source_status` | how the tablet's text stands against DAMOS or another check (below) |
| `token_normalized` | the token in transliteration (`ko-wa`); empty on the 1,302 rows whose tablet is not marked verified against DAMOS |

**Status.** The mark is given by tablet, not by token. `DAMOS_VERIFIED_EXACT` (10,160 rows): the tablet is found in
DAMOS under its number and at least 90% of its tokens match DAMOS's. `DAMOS_VERIFIED_VARIANTS` (1,792): at least
60% match, the rest editorial variants. The other marks are `PTT3_VERIFIED_PRINT` (895), `DAMOS_CONTENT_MISMATCH`
(160), `DAMOS_ONLY_IMPORT` (127), `ARIADNE_VERIFIED_AUTOPSY` (57), `DAMOS_NO_COUNTERPART` (49) and
`ARIADNE_VERIFIED_RTI` (14); those rows keep their place and their marks, and their text is left out. The suite uses
the 7,883 rows that are both `clean` and verified against DAMOS, and counts the rest as left out.

**Sources.** DAMOS, the Database of Mycenaean at Oslo (Federico Aurora, University of Oslo;
https://damos.hf.uio.no), CC BY-NC-SA 4.0: cite Aurora, F. (2015), "DAMOS (Database of Mycenaean at Oslo).
Annotating a fragmentarily attested language", *Procedia - Social and Behavioral Sciences* 198, 21–31. The
transliterations were first taken from LiBER, Linear B Electronic Resources (Maurizio Del Freo and Francesco Di
Filippo, CNR; https://liber.cnr.it), which states no licence, and then checked tablet by tablet against DAMOS. For
non-commercial use; anything derived from this file carries the same terms.

**Build.** `models/language-id-kernel/build_shipped_inputs.py --linear-b` cuts the file from the full token list;
with `--check` it compares the two and writes nothing.
