---
name: data/pre-greek/pregreek_lexicon
title: Pre-Greek lexicon
desc: Greek words that scholars class as Pre-Greek or as early Semitic loans, with the works that treat each word, the Semitic comparisons proposed for it, Beekes's Pre-Greek features and a sidecar of Wiktionary glosses; what each work gives and what is withheld.
tags: [data, pre-greek, greek, semitic-roots]
license: CC BY 4.0 AND CC BY-SA 4.0
created: 2026-11-06T18:00:00Z
updated: 2026-11-06T18:00:00Z
---

Four files hold the Pre-Greek lexicon. Every record is a Greek word; the Semitic roots stay in
`data/semitic-roots/semitic_roots.json`, and a word links to one only through `proto_semitic`, set by hand review.

| File | Licence | Holds |
| --- | --- | --- |
| `pregreek_lexicon.json` | CC BY 4.0 | 3,291 words, one per folded headword, with their sources and Semitic comparisons |
| `pregreek_features.json` | CC BY 4.0 | the 280 Pre-Greek features of Beekes 2014, chapters 2–3 |
| `pregreek_wiktionary_glosses.json` | CC BY-SA 4.0 | 1,156 short English glosses from Wiktionary, keyed by word id |
| `pregreek_lexicon.index.json` | CC BY 4.0 | each match key to the ids of the words it matches |

## The lexicon

`pregreek_lexicon.json` holds `schema_version` (1), `description`, `works` and `entries`. `works` maps each work key
to its `source_class` (`closed` for a published book, `web` for a page online), its verdict codes defined in our words
(`verdicts`), and its full reference (`reference`) unless [the bibliography](../../docs/bibliography.md) lists the key.

| Field | Content |
| --- | --- |
| `id` | `pg:` and the folded headword |
| `lemma` | the headword, accented |
| `key` | the headword folded: marks dropped, final sigma σ; vowel quality and gemination kept |
| `translit_key` | the headword in Latin letters |
| `lemma_basis` | `lsj` when the headword is LSJ's spelling, `first_lane` when it is the first work's |
| `variants` | the other Greek forms joined to the word |
| `variant_of` | the id of the word this one is a variant of, or null |
| `sources` | one per work and place that treats the word (below) |
| `semitic_comparisons` | the Semitic forms proposed for the word (below), where there are any |
| `proto_semitic` | `{id, form}` of a root in `semitic_roots.json`, set only by hand review; no entry carries one yet |
| `review_status` | `machine_compiled`: compiled from the works' indexes without hand review |

Each source gives `work` and, for a book, `loc` (the printed page or pages) and `verdict` (a code of that work's
`verdicts`). Beekes 2014 adds `section` and `features` (the feature ids its entry names) for a word in its lexicon,
and `example_of` (a feature id) and `toponym` for a word cited as an example of a feature. Furnée 1972 adds `section`
(its §). A web source gives only `work`, `url` and `source_class`.

Each Semitic comparison gives `lang`, `form`, `work`, `loc` and `verdict`, and where the source gives them `variety`,
`variants`, `cite` (each `{siglum, loc}`), `by` (the proposer's author–year citations, or Rosół 2013 for his own),
`cf` (true when the source gives the form only for comparison, Rosół's "vgl.") and `gloss_withheld` (true when the source glosses
the form). A rejected proposal keeps its form, proposer and the verdict `rejected`. `lang` uses the language keys of
`data/semitic-roots/branches.json`. Where the source's label names a dialect, period or variety, `variety` gives it in
English: Neo-Assyrian, Neo-Babylonian, Late Babylonian, syllabic Ugaritic, Old Canaanite, epigraphic Hebrew, Mishnaic
Hebrew, Modern Hebrew, Old Aramaic, Early Aramaic, Imperial Aramaic, Hatra, Deir Alla, Palmyrene, Christian
Palestinian, Samaritan, epigraphic Judaic Aramaic, colloquial Arabic and Tunisian Arabic (a label naming two gives
both, "Neo-Assyrian and Neo-Babylonian", in the source's order). Rosół's citations name dictionaries by his sigla:
HALAT is the German *Hebräisches und aramäisches Lexikon zum Alten Testament*, whose pages are not HALOT's.

## What each work gives

| Work | Class | Sources | Comparisons | What ships | Withheld |
| --- | --- | --- | --- | --- | --- |
| Beekes 2014, *Pre-Greek* | closed | 2,779 | 6 | section, page, feature ids; example pages | entry ids, glosses, headings, notes |
| Beekes 2010, *Etymological Dictionary of Greek* | closed | 2,072 | 154 | page, origin code (PG, PG?, LW Sem. and reason letters); the Semitic forms an etymology compares | glosses, etymologies, notes, forms as printed |
| Rosół 2013, *Frühe semitische Lehnwörter im Griechischen* | closed | 289 | 1,101 | page, verdict; each Semitic form with its language, variety, dictionary citations and proposer | glosses, his text and remarks, who rejected a proposal, the alternant forms |
| Furnée 1972, *Die wichtigsten konsonantischen Erscheinungen des Vorgriechischen* | closed | 3,152 | 0 | § and page; word-index pages | § headings, glosses, notes, alternant forms |
| Wiktionary | web | 1,272 | 0 | membership, URL | glosses (in the sidecar instead) |
| Wikipedia | web | 85 | 0 | membership, URL | glosses, notes |
| Hieber 2026; Hieber n.d. | web | 188; 17 | 0 | membership, URL | glosses, notes |
| Beekes 2000 | web | 23 | 0 | membership, URL | glosses, notes |
| Palaeolexicon 2016; Tardivo and Kitselis 2017 | web | 5; 7 | 0 | membership, URL | glosses, notes |
| Bengtson and Leschber 2021 | web | 4 | 0 | membership, URL | glosses, notes |

1,261 comparisons stand on 316 words; 378 of them are rejected proposals, 184 give a `variety`, and 1,058 have their
gloss withheld. The verdict codes are defined in each work's `verdicts`: Beekes 2010's origin codes combine (`PG?`,
`LW Sem.`, `PG(V)`), and its `comparandum`, like Beekes 2014's, marks a Semitic form the entry compares.

Words that only a web page lists, tied to no other work, are not included, and neither are any glosses of the web
pages other than Wiktionary's. No similarity score, distance or match verdict of any engine is in these files.

## The features

`pregreek_features.json` holds `schema_version` (1), `description` and `features`: one record per numbered section,
item and suffix of Beekes 2014, chapters 2–3, with `id` (the section number, `3.2.3.81`), `kind` (`phonology`,
`morphology` or `suffix`), `chapter`, `printed_page`, and, for 238 of them, `notation`: the affix or letters the
section treats (`-ινθ-(ο-)`, `βδ`, `π / σπ`). The English headings are withheld. Every feature id a lexicon entry
cites is here.

## The Wiktionary glosses

`pregreek_wiktionary_glosses.json` holds `schema_version`, `description`, `license`, `work` and `glosses`: for each
word id that Wiktionary lists in its category of Ancient Greek terms derived from a Pre-Greek substrate,
`{gloss, url}`, the first sense of Wiktionary's entry in twelve words or fewer. These glosses are Wiktionary's, under
CC BY-SA 4.0: attribute them to the Wiktionary contributors and share any adaptation alike. They are kept apart from
the lexicon so the lexicon stays under CC BY 4.0.

## The index

`pregreek_lexicon.index.json` maps each match key to the ids it matches: the folded headword, the transliteration,
each variant folded, and the headword's consonant skeleton in Latin letters (ἀξίνη: `k-s-n`). It is derived from the
lexicon and holds nothing else; `pregreek_index` in `tools/ane/ane_keys.py` rebuilds it, and
`tests/pre_greek/test_pregreek_lexicon.py` checks that it does.

## Terms

Beekes 2014 is © Koninklijke Brill NV (2014), Beekes 2010 © Koninklijke Brill NV (2009), Rosół 2013 © Peter Lang GmbH
(2013) and Furnée 1972 © Mouton & Co. N.V. (1972). Nothing of their text ships: no gloss, translation, etymology,
heading or note, and no meaning drawn from them. The files take from them only the headwords, the Semitic forms each
cites with its dictionary references and proposers, page and section numbers, and verdicts recast as our codes.
Hieber's pages, Palaeolexicon's, Tardivo and Kitselis's and Beekes's posting state no open licence, and the *Journal of
Language Relationship* PDF's licence is not stated on it: from each, only the word's membership and the URL ship.
Wikipedia's page is CC BY-SA 4.0; only membership and its URL ship. The selection, keys, codes, varieties, verdict
definitions and feature notation are ours (di Mino), under CC BY 4.0; the Wiktionary glosses are under CC BY-SA 4.0.
