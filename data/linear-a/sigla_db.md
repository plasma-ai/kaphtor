---
name: data/linear-a/sigla_db
title: SigLA database
desc: SigLA's corpus decoded from its own database file, one record per document, with its metadata and seals, every sign position with its reading, certainty, role and erasure flag, SigLA's word division, and the corpus.json record it belongs to.
tags: [data, linear-a, corpus, sigla]
license: CC BY-NC-SA 4.0 AND CC BY 4.0
created: 2026-11-03T22:07:01Z
updated: 2026-11-03T22:50:00Z
---

[SigLA](https://sigla.phis.me) (Ester Salgarella and Simon Castellan) is a palaeographic database of Linear A: every
GORILA tablet, the roundels of Haghia Triada and Khania, and documents published since, each sign with its reading
and role. The site ships its whole corpus as one file, [sigla/database.js](sigla/database.js), two OCaml Marshal
blobs, here unchanged. `tools/linear_a/build_sigla_db.py` decodes its `data` blob into `sigla_db.json`: a position
SigLA leaves unread stays unread, and its word groups stand as SigLA sets them. Two things are left out: the image
geometry of each position, and a reference field on each sign record (AB30 `ZA 8/6`).

`sigla_db.json` holds `description`, `source` (`file`, `sha256`, `site`), `stats` and `documents`, keyed by SigLA's
id (`"HT 25a"`, `"HT Wa 1019α"`, `"KN Wc <24a>"`). It holds 802 documents and 5,144 sign positions.

| Field | Content |
| --- | --- |
| `sigla_id`, `corpus_id` | SigLA's id, and the id with its spaces removed (`HT25a`), which is not always a corpus.json key |
| `corpus_key`, `corpus_match` | the corpus.json record the document belongs to, and how it was found (below) |
| `site`, `support`, `period` | as SigLA writes them (`Gournia` and `GOURNIA` both occur; `period` is empty on 24) |
| `dimensions_cm`, `edition_url` | the object's size, on 634; SigLA's link to the edition, on 783: the GORILA page on cefael.efa.gr for 755, editions.efa.gr for 24, and the string `missing` on 4, each without the site's session token |
| `seals` | the seal impressed on the document: `cms` (its CMS number), `motif`, `count` and `arachne_url` |
| `positions` | every sign position, in order (below) |
| `words` | SigLA's word division: each word's `positions` and its `text` |
| `outside_words` | the positions SigLA puts in no word |

## Positions

A position holds `position`, `read`, `signs`, `certain`, `role`, `role_certain`, `erased`, `hidden` and
`sigla_kind`. Of the 5,144, 4,756 are read and 388 unread. Positions are SigLA's own numbers: HT 130 has no
position 5, so its positions 6–10 are #5–#9 on SigLA's page.

**Read.** `signs` holds one sign, and `certain` is SigLA's flag: true on 4,712, false on the 44 readings SigLA marks
uncertain.

| Sign field | Content |
| --- | --- |
| `code` | SigLA's code (`AB76`, `A707`) |
| `phon` | its phonetic value, with SigLA's index as a subscript (`ra₂` on 43, `ta₂` on 14, `pu₂` on 7); null on the 1,498 where SigLA gives none (855 logograms, 331 fractions, 268 syllabograms such as AB79, 29 transaction signs, 15 unknown) |
| `name` | SigLA's name for the sign, a logogram's abbreviation or a fraction's letter (`FIC` on AB30, `GRA` on AB120, `J` on A707), on 748, whatever the position's role; null elsewhere |
| `variant` | SigLA's variant mark (`f` on AB21f, `a` on AB131a), on 177; null elsewhere |
| `sign_id` | the code with AB numbers in two digits and the variant joined (`AB08`, `AB21F`, `A709-2`), as [sigla-sign-map.json](sigla-sign-map.json) writes its `ab_number`: 4,709 of the 4,756 match one; most of the rest are vessel signs the map writes otherwise (`A402VAS`) |

**Unread.** `read` is false where SigLA records a sign but gives it no reading: `signs` is empty, `certain` null, and
`sigla_kind` keeps SigLA's raw tag (0 on 376, 1 on 12). 237 documents hold an unread position.

The values are SigLA's, not the corpus's: AB21 is `qi`, and HT 84 .1 opens with AB21 variant `f` (`AB21F`), which
corpus.json writes *21F. AB79 has no value. The file holds no numerals and no line division.

**Role.** `role` is SigLA's, the role its document pages print for each position:

| `role` | Positions | Where |
| --- | --- | --- |
| `syllabogram` | 3,448 | every sign inside a word, and only those (274 unread) |
| `logogram` | 1,196 | outside words (40 unread) |
| `fraction` | 331 | outside words |
| `transaction_sign` | 61 | outside words (HT 13 .6, AB04) |
| `unknown` | 108 | outside words (74 unread) |

A logogram keeps the phonetic value SigLA gives its sign (ARKH 1a .3, AB16, `phon` `qa`; 301 logograms carry one),
so read `role` before taking `phon` as a sound. `role_certain` is false on the 114 roles SigLA marks with "?": 14
logograms (5 unread), 26 transaction signs, and 74 unknown, all unread.

**Erased and hidden.** `erased` is true on the 104 positions SigLA marks as erasures, in 51 documents: 30 read
(KH 8 .10, AB30/FIC) and 74 unread. `hidden` is true on 7 positions SigLA leaves off its document page, all
`unknown` (HT 22 .3, A330, where the page shows positions 1–2).

## Words

1,401 words in 488 documents. A word's `text` writes each sign as its value upper-cased (`RA₂`), a sign with no
value by its code, `[?]` an unread position and `(?)` after an uncertain reading: HT 25a's seventh word is
`AB79-JU-PU₂`. 307 words are one sign long, 249 hold an unread position, 26 an uncertain reading, and 62 an indexed
value. No word holds an erased position. Each word also carries `sigla_word_flag`, a pair of values from 0 to 2 that
SigLA stores per word and does not label on its pages: `[0, 0]` on 836 words, another pair on 565. It is kept as
SigLA stores it.

`outside_words` holds 1,696 positions in 561 documents, every position whose role is not `syllabogram`: 1,196
logograms, 331 fractions, 61 transaction signs and 108 unknown. Of the 314 documents with no word, 299 hold signs and
15 hold none.

## Seals

305 documents carry a seal record, one each: 161 nodules, 132 roundels, 6 tablets and 6 sealings. 303 give the CMS
number, 301 the motif (`CMS II,6 no. 159`, `bull`) and 107 a link to Arachne.

## Matching a document to its record

`corpus_key` names the corpus.json record a document belongs to, and `corpus_match` says how it was found, by the
first rule that holds:

| `corpus_match` | Rule | Documents |
| --- | --- | --- |
| `sigla_id` | one corpus.json record's `sigla.id` names the document | 713 |
| `override` | [sigla/corpus_key_overrides.json](sigla/corpus_key_overrides.json) sets the key by hand: joins (`HT 123a` → `HT123+124a`, `KH 68` → `KH68+71`) and keys written with `(?)` (`PH 31a` → `PH(?)31a`) | 9 |
| `key` | the id with its spaces removed is a corpus.json key | 0 |
| `face` | the id less a face suffix (`a`, `b`, `α`, `β`, `γ`, `-latus`) is one corpus.json key: `HT Wa 1019α` → `HTWa1019` | 78 |
| null | no record: `KN Wc <24a>` and `KN Wc <24b>` | 2 |

The 800 matched documents fall in 757 corpus records; 41 records hold more than one SigLA document, a face each
(`KN Za 10a` and `KN Za 10b` under `KNZa10`).

## Building it

```sh
uv run tools/linear_a/build_sigla_db.py --dry-run   # decode and report; write nothing
uv run tools/linear_a/build_sigla_db.py             # write sigla_db.json, the old file backed up first
```

The build reads `sigla/database.js`, `corpus.json` and the overrides, and writes nothing else. It backs up the old
file outside the repository (`tools.paths.BACKUPS`, or `--backups`), and refuses to drop a document or shrink one's
positions or words without `--allow-drop`. `source.sha256` is the hash of the `database.js` it decoded;
`tests/linear_a/test_sigla_db.py` decodes the shipped `database.js` again and fails if the result differs from the
shipped `sigla_db.json`.

## Against corpus.json

`corpus.json` gives the GORILA text, checked against the primary editions and corrected; `sigla_db.json` gives
SigLA's reading as it stands. Where they part, the corpus record's `notes` say so:

- HT 84: GORILA's copie tabulaire sets ] before NU on .2 (GORILA I 128–29); SigLA reads NU-TI whole, both signs sure,
  a word of its own after one unread sign at the end of .1 (`QI-JA-DU · [?] · NU-TI`).
- HT 25a: SigLA divides .4–5 `DU-RU-WI · I-KI-RA` and reads I-KI-RA whole, with no sign lost before it.

The `sigla` blocks of corpus.json's 713 SigLA records carry each read sign's role but hold no word division, leave
out every unread position, and write codes with two digits (`AB08`). For word division, unread positions, erasures
and SigLA's certainty flag, read `sigla_db.json`.

## Sources and terms

Salgarella, E. and Castellan, S. (2021). "SigLA: The Signs of Linear A. A Palæographical Database." In Y. Haralambous
(ed.), *Grapholinguistics in the 21st Century 2020: Proceedings, Part 2*, pp. 945–962. Brest: Fluxus Editions.

SigLA's dataset is © 2020– Ester Salgarella and Simon Castellan, under CC BY-NC-SA 4.0, as its About page states.
`sigla/database.js` is that dataset as SigLA serves it, and `sigla_db.json` decodes it; both carry CC BY-NC-SA 4.0.
The `corpus_key` and `corpus_match` fields and `sigla/corpus_key_overrides.json` are CC BY 4.0. The SigLA drawings
are not in this repository.
