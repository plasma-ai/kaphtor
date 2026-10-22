---
name: data/linear-a/corpus
title: Linear A corpus
desc: One record per Linear A inscription or face, with its object, findspot, edition, Unicode text and transliteration.
tags: [data, linear-a, corpus]
license: CC BY-NC-SA 4.0 AND CC BY 4.0
created: 2026-10-22T18:14:10Z
updated: 2026-10-22T18:14:10Z
---

`corpus.json` is an object keyed by record id (`HT88`, `IOZa2`, `HT123+124a`). A record is one inscription, or one
face of an inscribed object; the census in [docs/corpus-census.md](../../docs/corpus-census.md) groups records into
documents. [census_classes.json](census_classes.json) holds the hand-curated sets the census counts by: the GORILA V
supplements, the RILA-S1 accepted, doubtful and uncounted texts, texts outside the area or published after 2023,
records under other editions, GORILA records without a label, unresolved and merged records.

| Field | Content |
| --- | --- |
| `name`, `names` | the record id, and every id the record is known by |
| `site`, `findspot`, `support`, `scribe` | where the object was found, what it is, and the scribe where one is assigned |
| `context`, `period`, `date` | the archaeological date (`LMIB`, `MM III–LM I`); the pages print `context` as the period |
| `gorila_volume`, `source_provenance` | the GORILA volume, and the edition the record comes from (`GORILA`, `RILA-S1`, `SigLA`…) |
| `rila_s1`, `rila`, `rila_note` | the record's status in RILA-S1 and readings checked against it |
| `transcription`, `parsedInscription`, `words` | the text in Linear A Unicode: as written, by line and by word |
| `transliteratedWords` | the words in transliteration, aligned with `words`; `"\n"` marks a line break |
| `editorialTransliteration`, `epigraphic_transliteration`, `sigla_transliteration` | other transliterations, where recorded |
| `notes`, `condition_note`, `designation_note`, `support_note`, `epigraphic_annotation` | epigraphic notes: damage, line breaks, sigla, joins |
| `sigla`, `sigla_only`, `sigla_sides`, `sigla_vs_gorila`, `reconciliation_note` | the SigLA record, its per-face records, and where SigLA and GORILA differ |
| `merged_records` | second records of the same object, folded into this one, each kept as a snapshot |
| `source`, `status` | the edition of a text published after GORILA, and `incomplete` where the text is partial |
| `imageRights` | the holder of the photographs, which are not reproduced here |

Readings and translations are in [lexicon.json](lexicon.json) and [translations.json](translations.json), keyed by
the same ids. A record's `notes` may discuss how a word is read, as epigraphic commentary.

## Sources and terms

The corpus builds on GORILA (Godart and Olivier) and RILA-S1, on [SigLA](https://sigla.phis.me) (Salgarella and
Castellan) and on [lineara.xyz](https://github.com/mwenge/lineara.xyz) (Hogan). Its readings were checked against
GORILA, Younger's *Linear A Texts* and the other primary editions, and many were corrected. SigLA's data is under
CC BY-NC-SA 4.0, and lineara.xyz states no licence. Our corrections and added layers are CC BY 4.0. The underlying
texts keep their sources' terms.
