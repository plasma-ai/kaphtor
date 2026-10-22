---
name: docs/corpora/cuneiform-corpora
title: Local Cuneiform Corpora
desc: What the local CDLI, ORACC, SEAL and ARCHIBAB snapshot covers, how each layer was acquired, and how the layers are kept apart.
tags: [corpora, docs]
created: 2026-10-22T18:14:10Z
updated: 2026-10-22T18:14:10Z
---

# Local Cuneiform Corpora

Coverage reflects the current local snapshot. Its exact acquisition timestamp
and checksums are in `data/ingest/cuneiform/derived/manifest.json`. Raw
acquisitions and generated indexes are not in this repository.

Human tables of contents: [`cuneiform-indices/_index.md`](cuneiform-indices/_index.md).

## Inventory

| Layer | Local coverage | Use | Limit |
|---|---:|---|---|
| CDLI catalogue | 426,703 artifacts | Period, genre, provenience, language, archive, publication, and object metadata | Metadata is much broader than transcription coverage |
| CDLI ATF | 150,220 blocks; 150,212 P-number IDs | Exact transliteration and ATF search | Only 24,553 blocks are Akkadian by ATF-or-catalogue evidence; translation and lemmatization are sparse |
| ORACC | 117 official ZIPs; 19,470 `corpusjson` members, of which 19,365 editions (19,031 P/Q IDs) parse and 105 are upstream empty/invalid placeholders | Edition-aware lines, tokens, lemmata, senses, projects, and metadata | Overlapping projects are alternate editions, not duplicates to discard |
| SEAL | 923/923 official records; 448 with text; 401 with translation; 42,371 annotated word spans | Early Akkadian literary texts and lemma/sense search | 475 catalogue-only; CC BY-NC-ND and noncommercial use only |

Project-specific layers acquired afterward remain separately versioned and
provenanced:

| Layer | Local coverage | Boundary |
|---|---:|---|
| EbDA | 3,086 text records; 150,857 transliteration rows; 276,866 lexical word links; 22,791 editorial-note anchors excluded | 8 additional roster records are verified catalogue-only pages; 79 source cross-edition links preserved; not redistributable; no images |
| DAPCA | 742 released Late Bronze editions; 17,243 lines; 58,804 token spans | Guest-visible release follows `ready_to_pub` + `has_txt`; three conflicting auxiliary file flags are audited; CC BY-NC-SA 4.0; no images |
| EUPT | KTU 1.14–1.16; 742 facsimile lines; 2,510 tokens; 6,863 annotations | Three source-labelled Draft editions; evidence layers kept separate; CC BY-SA 4.0 |
| Ugarit Texts Database | 4,582 metadata rows | Identifier/archaeological catalogue only, never textual attestation; CC BY 4.0 |
| Achemenet Babylonian | 2,830 documents; 262,127 token rows | Achaemenid-period corpus in five CoNLL-U collections; BabyLemmatizer analyses are automatic, not independent philological confirmation; CC BY 4.0 |

The Copenhagen Ugaritic source checkout is current through v0.2.8, whose new
Text-Fabric layer corrects word divisions. The existing 279-tablet project index
continues to cite `auto_parsing/0.2.7`; do not silently relabel that derived
index as v0.2.8 until it is rebuilt from the new Text-Fabric representation.

The ORACC total includes SAAo, ATAE, RINAP, RIBo, TCMA, BALT, BabCity, Borsippa,
HBTIN, Rīm-Anum, OBTA, OBMC, OBEL, AEMW/Amarna, AEMW/Ugarit,
AEMW/Alalakh-Idrimi, DCCLT/Ebla, NERE, and CAMS/GKAB.

## What “local coverage” means

- CDLI's live export delivered 426,703 catalogue rows and 150,220 ATF blocks. It is a
  complete retrieval of those public endpoints on the snapshot date, not a claim that
  every catalogued object has an edition.
- CDLI has 145,558 catalogue objects labeled Akkadian, but only 24,553 locally delivered
  text blocks qualify as Akkadian by ATF or joined metadata; 24,294 contain numbered text.
- The Akkadian text subset includes 10,415 Old Babylonian, 4,757 Old Assyrian, and 3,610
  Neo-Assyrian blocks. Its leading genres are 7,605 administrative, 4,020 letters, and
  2,986 legal. Labels can be multivalued.
- ORACC records are keyed by edition (`project + text ID + archive`). Repeated P/Q numbers
  are retained because project editions differ in annotation, metadata, or text.
- SEAL source HTML/JSON is kept byte-for-byte. The generated JSONL is a separate local
  search index; it is not a republished or modified SEAL edition.

## Named-corpus assessment

| Requested area | Assessment |
|---|---|
| Assyrian letters | Strong local coverage: SAAo contains 5,058 unique IDs across SAA 1–21 and SAAS 2; the broader ATAE/TCMA holdings are also present |
| Old Babylonian administrative/legal | Materially improved, not comprehensive: CDLI supplies 38,783 OB administrative and 8,678 OB legal catalogue records; local ATF availability is much smaller and uneven |
| Mari | Discovery coverage, not a comprehensive local text corpus: the CDLI filter returns 9,479 Mari + Early/Old Babylonian + Akkadian catalogue records; NERE contributes only the Epic of Zimri-Lim |
| Ugarit | AEMW/Ugarit supplies 1,900 valid editions: 839 KTU 4 texts, 955 wholly alphabetic-Ugaritic documents, and extensive syllabic Akkadian material; CUC remains the independent sign-level KTU 1–3 layer |
| Ebla | DCCLT/Ebla supplies 109 valid structured school/lexical editions; CDLI provides 1,395 Ebla ATF blocks; EbDA is the separate Royal Archive acquisition |
| ARCHIBAB | Not mirrored: its terms prohibit mass use to construct or enrich a database without permission; use record-by-record consultation until written permission is obtained |
| SEAL | Exact official 923-record roster represented locally; 448 records presently expose transcription |

Do not describe the local layer as “most Akkadian texts” or a “complete Mari archive.”

## Validation

Every generated JSONL row is validated, and `data/ingest/cuneiform/derived/manifest.json` records the result. Acceptance
counts for this snapshot are:

```text
oracc_documents.jsonl   19,365
oracc_invalid.jsonl        105
cdli_texts.jsonl        150,220
cdli_catalogue.jsonl    426,703
seal_records.jsonl          923
```

Also require unique generated `id` fields. Do not require unique P-numbers: CDLI has eight
IDs with two distinct ATF blocks, and ORACC intentionally preserves alternate project
editions.

## Acquisition and provenance

### CDLI

- Catalogue: `https://cdli.earth/artifacts?page=N&limit=1000`, requested as `text/csv`.
- Text: `https://cdli.earth/inscriptions?page=N&limit=100`, requested as `text/x-c-atf`.
- Local audit: `data/ingest/cuneiform/cdli/REPORT.md` and `audit/`.
- Rights: `LicenseRef-CDLI-Terms-of-Use`. CDLI permits copying, aggregation, and reuse of
  transliterations and translations under fair academic practice and requests attribution
  for considerable reuse. No images were acquired. Do not relabel the data CC0.

### ORACC

- Packages: `https://oracc.museum.upenn.edu/json/{project-slug}.zip`.
- Exact URLs and hashes: `data/ingest/cuneiform/oracc/SOURCE_URLS.tsv` and
  `CHECKSUMS.sha256`.
- Local audit: `data/ingest/cuneiform/oracc/REPORT.md`, `MANIFEST.jsonl`,
  `DUPLICATES.jsonl`, and `PROXY_COVERAGE.json`.
- Every acquired package embeds CC0 metadata. Preserve project attribution and edition
  provenance even where the data license does not require it.

### SEAL

- Official taxonomy: `https://seal.huji.ac.il/taxonomy/term/339`.
- The unfiltered CSV endpoint exhausts the upstream server's memory. The acquisition uses
  every public collection filter, deduplicates against the official taxonomy, and retrieves
  omitted records from canonical `/node/{id}?_format=json` endpoints.
- Local audit and exact hashes: `data/ingest/cuneiform/seal/REPORT.md` and
  `metadata/seal/`.
- Rights: CC BY-NC-ND, noncommercial use only. Preserve the fixed SEAL number and URL and
  attribute Michael P. Streck and Nathan Wasserman. Keep derived tokenization local and
  separate; do not publish altered editions.

### ARCHIBAB

No bulk data was acquired. The site's permission for private/scientific consultation
does not waive its separate prohibition on mass use to build or enrich an offline or
online database. Comprehensive Mari integration therefore requires prior written
permission from ARCHIBAB's publication director. Until then, use on-demand consultation,
record exact citations, and do not automate a mirror.

## Data separation

Keep these evidence layers distinct:

1. immutable raw package/page/record;
2. source edition or catalogue row;
3. locally derived text/token index;
4. any normalized lemma, root, or comparative inference.

Never infer a transcription from catalogue description, flatten alternate editions into one
P-number row, or treat a machine lemma as an independent confirmation of an etymology.
