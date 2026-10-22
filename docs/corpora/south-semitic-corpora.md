---
name: docs/corpora/south-semitic-corpora
title: Geʿez and South Arabian corpora
desc: The Geʿez, Ancient South Arabian and Modern South Arabian layers, kept as separate comparative evidence, with their scope and how to search them.
tags: [corpora, docs]
created: 2026-10-22T18:14:10Z
updated: 2026-10-22T18:14:10Z
---

# Geʿez and South Arabian corpora

Keep Ethiopic, Ancient South Arabian, and Modern South Arabian as separate
comparative layers. Their labels describe linguistic branches, not one corpus.

## Holdings indexed by the project

This repository ships only the sets under `data/`; each folder's index lists them.

| Layer | Current local scope | Evidential use |
|---|---:|---|
| Geʿez contact lexicon | 17,588 records; 16,353 unique original forms; 3,497 root entries | Root, form, gloss, and cognate discovery; not running text |
| TraCES Geʿez | 23 TEI documents; 122,423 annotated word units; 181,911 analyses | Contextual lexical and morphological comparison |
| Ancient South Arabian contact lexicon | 19,217 records: 10,778 Sabaic, 3,074 Qatabanic, 2,836 Minaic, 1,516 Hadramitic, 1,013 generic ASA; 1,632 records have meanings | Lexical discovery; the rows are not inscriptions |
| Sabaic dictionaries | 4,623 merged Beeston/Biella entries | Glossed lexical control; not in this repository (rights) |
| DASI/CSAI | 18,910-record roster: 9,127 epigraph headers and 9,783 object headers | All active headers resolved; raw payloads and a roster-complete query index are local |
| Modern South Arabian | Supplemental root comparisons only | Secondary control, not a comprehensive local text corpus |

Counts describe overlapping evidence layers, not independent witnesses. Consult each source manifest for current
state.

## Geʿez running-text search

The official 2019 TraCES deposit is a limited but representative,
morphologically annotated corpus. Its TEI, GeTa, and ANNIS copies are alternate
encodings, not separate witnesses. The local index uses TEI only, preserves all
source analyses, records two XML-recovered documents, and marks the Kebra Nagast
chapters 55–60 extract as overlapping the full edition.

Source: TraCES, DOI `10.25592/uhhfdm.707`, CC BY-NC-ND 4.0. Raw and derived
text data are not in this repository; use them for noncommercial research only,
and do not redistribute modified corpus data.

## Ancient South Arabian

The contact lexicon supports lexical screening. Citation or grammatical argument
must return to the DASI EpiDoc record or the named dictionary entry (Beeston 1982,
Biella 1982). The DASI section of [arabic-corpora.md](arabic-corpora.md)
describes the harvest route.

## Modern South Arabian boundary

The local comparative roots contain Mehri, Jibbali, Soqotri, and Harsusi data,
but no extensive searchable running-text corpus. Heidelberg's Semitic Sound
Archive exposes recordings under creator-controlled rights. The CC BY 4.0
Figshare deposit for the *Corpus of Soqotri Oral Literature* supplies audio and
artwork, not the published transcriptions; open Jibbali text publications remain
document sources rather than a normalized corpus. Do not silently substitute
Modern South Arabian for Ancient South Arabian evidence or treat modern
reflexes as Bronze Age attestations.

Discovery records for future ingestion:

- Soqotri audio/artwork deposit: DOI `10.6084/m9.figshare.1379832.v1`.
- Jibbali proverbs: *An Annotated Corpus of Jibbali/Śḥərɛ̄́t Proverbs*, DOI
  `10.11647/OBP.0422`.
- Mehri and Jibbali documentation: ELAR deposits 0307 and 0308; access and
  participant-rights conditions must be checked before acquisition.

Beta maṣāḥəft is a future Geʿez expansion route. It provides broad TEI metadata
and selected encoded texts, but record totals must not be reported as full-text
corpus totals.
