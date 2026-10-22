---
name: docs/corpora/bronze-iron-semitic-corpora
title: Bronze- and Iron-Age Semitic corpus index
desc: The Bronze- and Iron-Age Semitic corpora the project has indexed, from CDLI and ORACC to the Ebla, Ugarit and Hebrew sets, with their rights and the acquisitions still outstanding.
tags: [corpora, docs]
created: 2026-10-22T18:14:10Z
updated: 2026-10-22T18:14:10Z
---

# Bronze- and Iron-Age Semitic corpus index

This index distinguishes text editions from catalogue metadata and unresolved
acquisition requests.
Searchable public access does not by itself authorize bulk acquisition.
Counts describe overlapping evidence layers, not a deduplicated total of ancient texts.

## Corpora indexed by the project

Status is the project's own inventory. This repository ships only the sets under `data/`; each folder's index lists
them.

| Corpus | Relevant layer | Local status | Rights / handling |
|---|---|---|---|
| CDLI | 426,703 catalogue records; 150,220 ATF edition blocks, including Ebla, Mari, Alalakh, Emar, Nuzi, Ugarit, Amarna, and Kanesh | Acquired and indexed | Text reuse with attribution; image rights separate |
| ORACC | 19,365 editions after adding DCCLT/Ebla, AEMW/Ugarit, and AEMW/Alalakh-Idrimi; 1,893,023 tokens | Acquired and indexed | Embedded machine data CC0; retain project attribution |
| DCCLT/Ebla | 109 valid structured school/lexical editions from 156 package members; invalid upstream members retained in the rejection ledger | Acquired and indexed | CC0 |
| EbDA | 3,094 published ARET/ARES/MEE roster records: 3,086 text editions, 150,857 transliteration rows, and 276,866 lexical word links; 22,791 editorial-note anchors are separately typed; 8 catalogue pages have no transliteration | Acquired and indexed; all 8 non-text pages preserved and ledgered; 79 source cross-edition links retained without automatic deduplication; no images | Research-use notice; not redistributable |
| Ebla VE | Vocabulary of Ebla knowledge base | Acquired and indexed; 142 pages, including 38 VE entries and 904 explicit links; SED II cites Eblaite lexical-list entries by VE number | No explicit open-data license; not redistributable |
| Ebla Personal Names (Pagan 1998) | 5,309 name forms, 7,589 element occurrences, 2,390 analyses | Acquired and indexed with source ASCII notation retained | Copyright stated; no open-data license located; not redistributable |
| Prosopography of Ebla | Public alphabetic installments B, G, and K | Three public PDFs; no structured export | Supported export or permission required for the complete database |
| ELISIR | OntoLex-Lemon Ebla lexical data | Acquired and indexed as a six-entry pilot layer; not represented as a comprehensive lexicon | CC BY 4.0 |
| Copenhagen Ugaritic Corpus | 279 sign-level/transliterated tablets, principally KTU 1–3 | Upstream checkout updated to v0.2.8/current main; the existing 279-tablet derived index still uses the separately published `auto_parsing/0.2.7` layer | CC BY-NC 4.0 |
| AEMW/Ugarit | 1,900 valid editions: 839 KTU 4 texts, 955 wholly alphabetic-Ugaritic documents, and extensive syllabic Akkadian material | Acquired and indexed | CC0 |
| Ugarit Texts Database | 4,582-record catalogue with KTU/RS/SAU identifiers and metadata; not full text | Acquired and indexed with 4,582 unique row IDs and 0 parse failures; 922 exact, set-equivalent, or individual repeated-reference groups are retained in a separate ledger | CC BY 4.0 |
| Open Scriptures Hebrew Bible | Full Hebrew Bible text and morphology | Acquired; 39 biblical books plus verse map | CC BY 4.0 |
| Ancient Hebrew Inscriptions (AHI2) | 752 pre-200 BCE inscription records; 9 deliberately empty text fields retained | Part 2 recovered from the archived official OTA bitstreams and indexed without parse loss; Part 1 item 1707 is identified but its full bitstream remains unavailable | OTA metadata states CC BY 3.0; its readme additionally prohibits using the file to prepare a printed corpus or concordance for publication/circulation |
| I.Sicily | 5,136 valid EpiDoc XML files; 73 records have Punic or Hebrew in `mainLang`/`otherLangs` (67 primarily Punic, 2 primarily Hebrew, and 4 multilingual records) | Acquired and indexed; 19 currently contain nonempty plain edition text, while all 73 retain their EpiDoc edition XML and metadata | CC BY 4.0 |
| IIP Hebrew/Phoenician layer | 496 language-partitioned records and 2,373 typed tokens | Acquired and indexed; 44 empty target-language records and 7 malformed upstream XML files remain explicit; overlaps are not collapsed | CC BY-NC 4.0 |
| Old Assyrian Text-Fabric | 4,775 Old Assyrian documents and 314,012 word rows | Acquired and indexed; matching CDLI P-numbers are duplicate controls, not independent witnesses | MIT |
| eBL transliterated fragments | Official snapshot: 23,289 records, 23,288 unique IDs, and 447,701 ATF lines; one duplicate ID is explicitly ledgered | Acquired, checksum-verified, and indexed | Snapshot CC BY 4.0; code MIT |
| Achemenet Babylonian | 2,830 Achaemenid-period Babylonian documents and 262,127 automatically lemmatized tokens in five CoNLL-U collections | Acquired, checksum-verified, and indexed; one malformed 18-field upstream row is retained in the failure ledger | CC BY 4.0; automatic analyses are not gold annotation |
| OCIANA | 37,955 Ancient North Arabian inscriptions with transliteration, translation, provenance, references, and notes | Acquired and indexed without parse loss; 29 illegal control bytes repaired only in memory and 6 duplicate-ID occurrences ledgered | ORA research download and terms; no images acquired |
| DASI/CSAI OAI | 18,910 OAI records: 9,127 South Arabian epigraph headers and 9,783 object headers | All 18,872 active headers are resolved and the derived query index reconciles to the complete roster | Record data CC BY 4.0; images excluded and not acquired |
| DAPCA | 782 guest-visible catalogue rows; all 742 released text records indexed as 17,243 lines and 58,804 token spans | Acquired with no failures; 44,526 token spans pass strict preservation typing; no images or restricted records | CC BY-NC-SA 4.0 |
| EUPT | Production collection currently lists KTU 1.14–1.16: 742 facsimile lines, 776 philology units, 2,510 analyzed tokens, and 6,863 annotations | Production API layers acquired and indexed separately; editions self-identify as Draft 3.2, 1.3, and 1.3, so they are not treated as final; repository code/samples remain pinned at exact commits | Edition manifests state CC BY-SA 4.0; TextAPI code is AGPL-3.0 |
| Ancient/classical Aramaic aggregation | 368,017 passages, including Biblical Aramaic, Judaean Desert material, Targums, Syriac, IIP, and separately labeled Bavli candidates | Acquired and indexed | Preserve per-source licenses and automatic-candidate labels |
| TLHdig 0.3 | 23,936 mixed-language Hittite-tablet XML records and 1,651,388 word rows, including 13,442 Hurrian-tagged lines | 23,783 canonical designations; repeated designations and recovery-parsed rows remain labeled; not an independent-artifact count | CC BY 4.0 |
| IG XV 1 | Mixed Greek syllabic, Eteocypriot, Phoenician, and alphabetic corpus | 311 of 410 records indexed; only explicitly labeled Greek syllabic parts are known-language CV controls | CC BY 4.0 |

## Future acquisition requests: permission or supported export required

| Priority | Corpus / missing layer | Why it matters | Constraint | Required action |
|---:|---|---|---|---|
| 1 | Corpus Inscriptionum Phoenicarum necnon Poenicarum (CIP/PhDB) | The intended comprehensive Phoenician/Punic corpus | Public description exists, but no verified bulk endpoint or reuse license | Request a research export and terms from CSIC/CIP |
| 2 | CAL Old and Official Aramaic layer | Tel Dan, Tell Fekheriye, Samʾal, Sefire, Bukan, and Imperial Aramaic with lexical parsing | CAL provides interactive access but no public bulk API; large-result harvesting is unsupported | Request a licensed Old/Official Aramaic tagged-text export from CAL |
| 3 | DiCoNab full corpus | Nabataean Aramaic and Developing Arabic inscriptions, with word attestations | Terms reserve reproduction/distribution and permit only partial reproduction; editor or administrator access may be granted by scholarly request | Request supported access or an export; meanwhile use `tools/ane/query_diconab.py` for one result page or exact record, never bulk harvesting |
| 4 | DEAPS | Current digital editions of Aramaic and Phoenician sources with translations and word-level apparatus | No public bulk export or explicit open-data license | Request a scholarly export from the OSU/DLATO team |
| 5 | Ras Shamra Tablet Inventory (RSTI) | Independent Ugarit editions, translations, glossaries, and archaeological metadata beyond the now-local AEMW KTU 4 layer | No documented bulk endpoint or reuse license | Request an OCHRE/RSTI export with text and rights metadata |
| 6 | Complete Mari / ARCHIBAB text corpus | Essential Old Babylonian and Amorite-era letters, administrative, legal, and prosopographic evidence; local CDLI is incomplete | ARCHIBAB forbids mass database acquisition without permission | Request a private-research export |
| 7 | Current complete Cypro-Minoan edition | Closest undeciphered Aegean script control | PASP metadata and Sign2Vec's filtered 213-witness sequence layer are indexed, but neither is a current complete edition | Request an edition-grade export with explicit reuse terms; do not scrape image viewers |
| 8 | Comprehensive Hurrian/ChS export | Independent Hurrian morphological and lexical control beyond the TLHdig subset | No supported comprehensive export verified | Request an official export; use TLHdig's tagged witnesses meanwhile |
| 9 | Complete Prosopography of Ebla export | Person dossiers, relationships, functions, places, goods, and line contexts beyond Pagan's name analysis | Only B/G/K PDFs are public; no structured export is exposed | Request a supported export |

KTU 4 text coverage comes from the CC0 `aemw-ugarit` package (839 valid KTU 4
editions). RSTI is a separate source of independent editorial and archaeological
data, not of basic KTU 4 coverage.

DiCoNab's rights boundary and citation rules are in the DiCoNab section of
`tools/ane/README.md`. The bounded DEAPS, Elephantine, and RSTI clients are listed
there too; these one-page/one-record clients do not change the bulk-export gaps
in the table above. CAL remains manual/request-only,
and no live public CIP/PhDB query database was verified.

## Other open or supported acquisitions to complete

| Corpus | Scope | Status / next step |
|---|---|---|
| Ancient Hebrew Inscriptions, Part 1 | Earlier 1991 corpus; AHI2 explicitly re-edits some records under the same numbers | The official item and filenames are identified, but the legacy bitstreams remain unavailable; acquire a supported copy, retain both parts, and ledger every overlap rather than merging silently |
| EUPT production normalization | Reconcile repository samples with the public TextAPI and index vocalization, translation, commentary, morphosyntax, and annotations | Completed for collection-listed KTU 1.14–1.16; retain EUPT's explicit Draft labels and re-fetch deliberately when versions change |
| DAPCA integration | Late Bronze cuneiform from Emar and the Middle Euphrates, with room for further collections as released | Completed for the current guest release: 742 editions, 17,243 lines, 58,804 token spans, 0 failures; three conflicting `has_txt`/`has_txt_file` rows are explicitly audited, with release governed by `ready_to_pub` plus the guest-facing `has_txt` flag |
| Ugarit Texts Database normalization | Crosswalk among KTU, RS/RIH, SAU, RSTI, museum, language, script, genre, object, and findspot metadata | Completed for all 4,582 source rows; source fields remain exact, derived search labels are navigation aids, and repeated references are not merged |
| OCIANA integration | 37,955 Ancient North Arabian inscriptions with transliteration and translation | Completed: source preserved byte-for-byte; derived parser indexes every record and ledgers duplicate IDs and in-memory control-character repair |
| DASI token/concordance layer | Add token-level occurrence and critical-state indexing beyond the completed record/name query layer | Build only as a derived layer over the retained EpiDoc; do not infer lemmas or roots that DASI does not supply |
| Elephantine | Imperial Aramaic documents and metadata | Individual TEI is public, but no supported bulk route is documented; request an export |

Three apparent expansions are not independent text corpora: Moore's Elephantine Figshare deposit is
a paleography-chart PDF only; the Palmyra Zenodo release is quantitative
inscription metadata rather than transcription; and `nabu-data` supplies
derived tables over upstream corpora rather than new witnesses.

## Methodological use

Use these corpora as external comparanda only after a Linear A segmentation is
established internally. Eblaite and Akkadian are archaic, syllabic-writing and
morphological controls; on their own they do not identify a language.

HALOT cites inscriptional Hebrew by label: Lachish (the Lachish letters; s.v.
יצא) and Ostr. Sam. (the Samaria ostraca; s.v. יַיִן). It also cites Old
Sinaitic (OSin.; s.v. יעץ), which no row here covers.
