---
name: docs/pre-greek-lexicon
title: "The Pre-Greek Lexicon"
desc: How the Pre-Greek lexicon is compiled: its sources, the folding of headwords, the identity rule, each work's verdict codes, and what ships and what is withheld.
tags: [docs, pre-greek, semitic-roots]
authors: "di Mino"
created: 2026-11-06T23:22:00Z
updated: 2026-11-06T23:22:00Z
---

# The Pre-Greek Lexicon

[[docs/_index|..]]

`pregreek_lexicon.json` ([[data/pre-greek/pregreek_lexicon|pregreek_lexicon]]) holds one record per Greek word that a scholarly work classes as Pre-Greek, as a substrate word or as an early Semitic loan. It is compiled from the works' indexes and lexica: each work is a lane with its own verdict, joined to the others by the word's folded headword, and no field sums the lanes into one verdict. Every record carries `review_status: machine_compiled` until a person reviews it. The record wiki gives each word a page in [[wiki/pre-greek/_index|wiki/pre-greek/]], built by `tools/views/pregreek.py`.

## Sources

| Work | Class | What it gives the lexicon |
| --- | --- | --- |
| Beekes 2014, *Pre-Greek: Phonology, Morphology, Lexicon* | closed | the core: the words of its lexicon, each with its section, page and the Pre-Greek features its entry names, and the words chapters 2–3 cite as examples of a feature |
| Beekes 2010, *Etymological Dictionary of Greek* | closed | the origin each entry marks (Pre-Greek, Indo-European, a loan and its donor), with the page, and the Semitic forms an etymology compares |
| Rosół 2013, *Frühe semitische Lehnwörter im Griechischen* | closed | the Greek words proposed as early Semitic loans, his verdict on each, and every Semitic form he cites with its language, dictionary references and proposer, including the proposals he rejects |
| Furnée 1972, *Die wichtigsten konsonantischen Erscheinungen des Vorgriechischen* | closed | the words listed as material in each §, and the pages of its word index |
| Wiktionary, Wikipedia, Hieber 2026, Hieber n.d., Beekes 2000, Palaeolexicon 2016, Tardivo and Kitselis 2017, Bengtson and Leschber 2021 | web | membership of a list of Pre-Greek words, with the page's URL |

A web list adds a source to a word that a closed work already holds; a word that only a web page lists is left out. Each work's full reference is in the lexicon's `works` block, or in [[docs/bibliography|bibliography]] where that lists the key.

## Folding the headwords

Each work prints its headwords its own way: accented or not, with or without the breathing, with a final ς or a σ. The lexicon meets them on a folded key:

- **`key`**: the headword in Greek letters, lowercased, with every combining mark dropped (accents, breathings, diaeresis, iota subscript, macron, breve) and a final ς written σ. Vowel quality and gemination are kept: η and ε, ω and ο, λλ and λ stay apart. ἀξίνη folds to αξινη.
- **`translit_key`**: the headword in Latin letters: θ th, φ ph, χ kh, ψ ps, ξ x, ζ z, υ u, η e, ω o, ϝ w, the rough breathing dropped (ἁμαξίς: amaxis).
- **The consonant skeleton**: the Latin consonants of the headword, for a root query: aspirates as their plain stops, ξ k-s, ψ p-s, γ before a velar n, a doubled consonant once, the vowels and the nominative's final ς dropped (ἀξίνη: k-s-n). It is a key of the index `pregreek_lexicon.index.json`, never a field of a record.

The headword shown (`lemma`) is LSJ's spelling where LSJ has the word (`lemma_basis: lsj`), and otherwise the spelling of the first work that lists it (`first_lane`). `greek_fold` and `greek_skeleton` in `tools/ane/ane_keys.py` compute the folded key and the skeleton, and `pregreek_index` rebuilds the index from them.

## The identity rule

Two works treat the same word when their headwords fold to the same `key`, and the word's id is `pg:` and that key. A form a work prints beside a headword joins the headword's `variants`; a variant that a work also treats under a headword of its own keeps its own record, which names its headword in `variant_of`. Two entries of Beekes 2014's lexicon that fold to one key stay two words when their senses share nothing, the second numbered (`pg:κιλλιξ#2`).

A Semitic comparison is a proposal on record, never an identity. A word links to a root of [[data/semitic-roots/semitic_roots|semitic_roots]] only through `proto_semitic`, set by hand review; a comparison's form that matches a root's key is a lead for that review, never a link. A root that the root database lacks enters it through the rules of [[docs/semitic-roots-scan|semitic-roots-scan]], never as a Pre-Greek root.

## Verdict codes

Each source's `verdict` is a code of its work, and each comparison takes the verdict of the work that lists it. The codes are defined in our words under each work's `verdicts`:

| Work | Code | Meaning |
| --- | --- | --- |
| Beekes 2014 | `PG` | in the lexicon of Pre-Greek words |
| Beekes 2014 | `example` | cited as an example of the feature in `example_of` |
| Beekes 2010 | `PG` | a Pre-Greek substrate word |
| Beekes 2010 | `IE` | inherited from Indo-European |
| Beekes 2010 | `GR` | formed within Greek |
| Beekes 2010 | `EUR` | a loanword from a European substrate |
| Beekes 2010 | `ONOM` | onomatopoeic |
| Beekes 2010 | `LW` | a loanword; the donor follows when named (`LW Sem.`, `LW Eg.`, `LW Anat.`) |
| Beekes 2010 | `?` | origin unknown |
| Beekes 2010 | `<origin>?` | the origin is doubted (`PG?`, `LW Sem.?`) |
| Beekes 2010 | `(V)` | Pre-Greek on the evidence of variant forms |
| Beekes 2010 | `(S)` | Pre-Greek on the evidence of a suffix |
| Beekes 2010 | `(O)` | a reason letter outside the dictionary's key, kept as read |
| Beekes 2010 | `unmarked` | no origin is marked |
| Beekes 2010, Beekes 2014 | `comparandum` | a Semitic form the entry compares |
| Rosół 2013 | `loan` | a Semitic loanword |
| Rosół 2013 | `probable_loan` | probably a Semitic loanword |
| Rosół 2013 | `possible_loan` | possibly a Semitic loanword |
| Rosół 2013 | `semitic_letter_name` | a letter name taken over from the Semitic alphabet |
| Rosół 2013 | `greek_letter_name` | a letter name formed within Greek |
| Rosół 2013 | `letter_name_unknown` | a letter name whose origin is left open |
| Rosół 2013 | `egyptian_via_semitic` | an Egyptian word that reached Greek through a Semitic language |
| Rosół 2013 | `iranian_via_semitic` | an Iranian word that reached Greek through a Semitic language |
| Rosół 2013 | `oriental_doubtful` | an eastern word whose Semitic origin is doubted |
| Rosół 2013 | `isogloss` | a word Greek shares with Semitic, with no direction of borrowing set |
| Rosół 2013 | `rejected` | a Semitic etymology proposed by an earlier scholar and rejected |
| Furnée 1972 | `listed` | listed as material in the § given |
| Furnée 1972 | `indexed` | in the word index, at the pages given |

Beekes 2010's codes combine as its entries do: a reason letter follows its origin (`PG(V)`, `PG?(S,V)`), and an entry that names two origins gives both, in its order (`IE?, PG?`). A web source carries no verdict: its membership is the claim.

## How a comparison cites its sources

A comparison from Rosół 2013 gives the Semitic form with the dictionary references he prints for it (`cite`, each a siglum and a page) and the scholars who proposed the comparison (`by`). Both are second-hand: the sigla are Rosół's, resolved by his list of abbreviations, and HALAT is the German *Hebräisches und aramäisches Lexikon zum Alten Testament*, whose pages are not HALOT's; `by` gives the author–year citations as he prints them (`Lewy 1895: 111`), or `Rosół 2013` where the comparison is his own. The [[docs/bibliography|bibliography]] gives each proposer key under "Cited through Rosół 2013" and each siglum under "Sigla of the Pre-Greek lexicon", as Rosół's bibliography gives them. That table, not the main one, names the work a siglum means here: LS and EDG name other works in the main table. A comparison from Beekes 2010 or Beekes 2014 gives the form and the page, with no citation or proposer.

## What ships and what is withheld

| Ships | Withheld |
| --- | --- |
| headwords, their keys and their variants | every gloss, translation, etymology, heading and note of Beekes, Rosół and Furnée, and any meaning drawn from them |
| each source's work, page, section, verdict code, feature ids, `example_of` and toponym flag | Beekes's entry ids and every private source id |
| each comparison's form, language, variety, variants, dictionary citations, proposer, work, page, verdict, `cf` and `gloss_withheld` | Rosół's text and remarks, who rejected a proposal, and the alternant forms |
| the features' ids, kind, chapter, page and Greek notation | the features' English headings |
| a web source's membership and URL | the web pages' glosses, apart from Wiktionary's, and the words only a web page lists |
| Wiktionary's short glosses, in `pregreek_wiktionary_glosses.json` under CC BY-SA 4.0 | the score, distance or verdict of any match engine |

A word page in `wiki/pre-greek/` shows what ships and nothing more. The one gloss it can show is Wiktionary's, and every page that shows one names Wiktionary as its source and CC BY-SA 4.0 as its licence beside it; the ledger pages show none. The datasheet [[data/pre-greek/pregreek_lexicon|pregreek_lexicon]] gives the terms of each work.
