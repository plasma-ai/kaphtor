---
name: docs/corpora/egyptian-corpora
title: Egyptian Text Corpora
desc: Acquisition routes, file formats and gaps for the Egyptian texts layer, built on the open ORAEC/TLA corpus, with the texts that name Keftiu or the Levant.
tags: [corpora, docs]
created: 2026-10-22T18:14:10Z
updated: 2026-10-22T18:14:10Z
---

# Egyptian Text Corpora

Acquisition routes, file formats, and gap analysis for the Egyptian texts layer:
the full ORAEC/TLA corpus (every open-access Egyptian text, Old Kingdom through
Greco-Roman).

## Local corpora

This repository ships only the sets under `data/`; each folder's index lists them.

| File | Rows | Source |
|---|---|---|
| `data/egyptian_documents.jsonl` | 13,026 documents | ORAEC corpus_raw_data |
| `data/egyptian_sentences.jsonl` | 101,796 sentences | same |
| `data/proper_names/pnm-v6/` | 60,488 name attestations plus linked people, spellings, titles, dossiers, inscriptions, and sources | PNM v6, Zenodo DOI 10.5281/zenodo.15806808 |

## ORAEC (backbone)

**github.com/oraec/corpus_raw_data** (main branch)—the Open Richly Annotated
Egyptian Corpus, an open GitHub republication of the Thesaurus Linguae
Aegyptiae corpus data via AED/AES (Simon D. Schweitzer).

- 13,026 document JSONs (`oraec1.json` … `oraec13026.json`), ~92 MB
- **License: CC BY-SA 4.0** for corpus files (authors: TLA contributors, see
  repo README); CC0 for `mapping_oraec_trismegistos.csv`,
  `mapping_oraec_wikidata.tsv`, `collocation/`, `statistics/`
- Per-document: `oraecid`, `title`, `date[]` (named reigns/periods),
  `origplace[]`, `objecttype[]`, `bibliography`, `sentences[]`
- Per-sentence: `translation` (**German**—search with German keywords:
  Kreta not Crete, Seevölker not Sea Peoples) + `token[]` with `written_form`,
  `lemma_form`, `lemmaID`, `pos`, morphological features, some `hiero`
- Sibling repo `oraec/corpus` (gh-pages) serves stable per-text HTML at
  `https://oraec.github.io/corpus/<oraecid>.html` — cite those URLs, don't parse them
- Companion: HuggingFace `thesaurus-linguae-aegyptiae/tla-*` datasets carry the
  same data with numeric `dateNotBefore`/`dateNotAfter`

## Schema notes

Both files carry the common fields (id, language, source_corpus,
form_original, normalized, match_keys, meaning, pos, semantic_domain,
source_refs, review_status). Extensions:

- **Documents** (`egytext:doc:oraec1234`): title, period, dynasty, reign,
  date_not_before/after (coarse period ranges, negative = BCE), genre,
  objecttype (raw German), provenance, bibliography, trismegistos_id,
  sentence_count
- **Sentences** (`egytext:sent:oraec1234-s7`): document_id, oraecid,
  sentence_index, transliteration (joined written_forms), lemma_ids, pos_seq,
  translation_language (`de`/`none`), match_keys = normalized lemma forms
  (dots/brackets/digits stripped, lowercased: `Kft.w` → `kftw`)
- Sentence index file maps oraecid → sentence ids (document retrieval);
  lemma lookups go through DuckDB match_keys

Transliteration conventions: TLA Unicode Egyptological (ꜣ ꜥ ꞽ ḥ ḫ š ṯ ḏ).
Folding ꜣ→ʔ, ꜥ→ʕ, ꞽ→y, j→y lets Semitic roots scan Egyptian lemmata.

## ORAEC texts naming Keftiu or the Levant

| oraecid | Text |
|---|---|
| oraec7 | London Medical Papyrus (BM EA 10059): Keftiu Spells #32 (s163-166), #33 (s167-169) |
| oraec21 | Admonitions of Ipuwer: s99, Keftiu |
| oraec32 | Ebers portion: s107 "Keftiu beans" |
| oraec82 | Stele of Montuhotep (CG 20539): "priest of Horus-of-Keftiu" |
| oraec84 | pChester Beatty IV: Hatti/Keftiu goods list |
| oraec47 | Wenamun: Tjeker at Dor |
| oraec408 | Astarte Papyrus: Canaanite Baal-Yam myth in Egyptian |
| oraec20/710 | Annals of Amenemhat II (Mit Rahina) |
| oraec448 | Taking of Joppa |

## Gap table (not in ORAEC's open set)

| Text | In ORAEC | Edition |
|---|---|---|
| Tempest Stele of Ahmose | absent | Ritner & Moeller, JNES 73 (2014), DOI 10.1086/675069 (paywalled) |
| Annals of Thutmose III (Karnak) | absent (only pTurin Syrienfeldzug, which is not the annals) | Breasted, ARE II §§391-540 |
| Theban tomb captions (TT100 Rekhmire, TT86, TT131), Keftiu tribute scenes | absent | Davies, *Tomb of Rekh-mi-Rē* vols I-II (MetPublications) |
| Kom el-Hetan statue-base lists | absent | Cline & Stannish 2011 (open access) for the PWN V Aegean list; Edel & Görg 2005 for all five bases |
| BM EA 5647 Keftiu names | absent | Dautais & Gabolde 2025, tables 1-2; proposed Greek matches remain proposals |
| Medinet Habu Ramesses III war inscriptions | absent | Epigraphic Survey, OIP 8 + OIP 9 (ISAC official PDFs) |
| Merneptah Great Karnak Inscription + Israel Stele | absent (only literary eulogies) | Breasted, ARE III; KRI IV for the full edition |
| Papyrus Harris I (BM 9999) | absent (pHarris 500 is not pHarris I) | Breasted, ARE IV; Grandet 1994 |
| Onomasticon of Amenope | absent | Gardiner, AEO II; Herbin 1987 for the BM EA 10474 witness |
| Execration Texts (Berlin/Brussels) | absent | Sethe 1926 (Berlin); Posener 1940 (Brussels) |
| Amarna Letters | **Akkadian, not Egyptian** | the Akkadian layer (`cuneiform-corpora.md`); Moran's translation |

## Lichtheim

Lichtheim, *Ancient Egyptian Literature* vols 1–3, is the standard English
translation of many ORAEC texts, whose own translations are German. ORAEC titles
use German name forms (Thutmose→Thutmosis, Rekhmire→Rechmire).
