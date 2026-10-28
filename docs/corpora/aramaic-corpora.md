---
name: docs/corpora/aramaic-corpora
title: Ancient and classical Aramaic corpus
desc: The passage-level Aramaic index (Biblical Aramaic, the Targums, Qumran, Syriac, inscriptions and the Babylonian Talmud), its fields, validation, sources and gaps.
tags: [corpora, docs]
created: 2026-10-22T18:14:10Z
updated: 2026-10-22T18:14:10Z
---

# Ancient and classical Aramaic corpus

## Scope

`data/aramaic_texts.jsonl` is a passage-level research index built from local source caches; it is not in this repository, and this page describes a user's own build. The current manifest records **368,017 passages**, **3,983,946 source nodes/tokens**, and **1,036,685 structured token rows**. It is broad, not exhaustive, and does not turn texts of different dates and dialects into one synchronic corpus.

| Layer | Passages | Tokens | Source and status |
|---|---:|---:|---|
| Biblical Aramaic, Peshitta, Onkelos, Jonathan, Writings Targums, Ephrem | 55,710 | 859,016 | Aramaic Root Atlas CSVs; mixed PD, CC BY, CC BY-SA, and CC BY-NC |
| ETCBC Targum witnesses | 13,751 | 332,026 | 58 base-view XML witnesses: Pseudo-Jonathan, Fragment Targums P/V/N, Cairo Genizah fragments, and full Pentateuchal Neofiti base text; conservatively CC BY-NC 4.0 |
| Qumran/Judaean Desert Aramaic | 6,380 line-keyed extracts | 49,404 TF word/morpheme nodes; 37,862 orthographic words; 135,712 sign slots | ETCBC/DSS 2.0.1, filtered by word-level `lang=a`; critical-state and full-line context retained; CC BY-NC 4.0 |
| Digital Syriac Corpus | 133,120 lines/paragraphs | 2,087,504 | 632 TEI works; CC BY 4.0; composition, redaction, and manuscript dates vary |
| ETCBC Syriac, extra-biblical works | 5,778 verses | 120,330 | Annotated Syriac; canonical Peshitta books excluded here to prevent duplicate counting; CC BY-NC 4.0 |
| Inscriptions of Israel/Palestine | 1,770 inscriptions | 10,503 | Aramaic-classified EpiDoc records; CC BY-NC 4.0; seven malformed upstream XML files are reported in the manifest |
| ORACC Aramaic-tagged passages | 529 lines | 1,725 | Extracted from 199 P/Q/X edition records; identifiers overlap, so 199 is not an independent-inscription count; CC0 in each selected source record |
| Babylonian Talmud candidate JBA | 150,979 spans | 523,438 | Gemara-only automatic candidates from Dicta's complete vocalized Bavli. Mishnah remains in the audit layer; no uncertain-token promotion; both spellings, model scores, source context, and risk flags retained. Automatic classification, not a language edition |

The ETCBC Targum repository also preserves Neofiti's fuller short-variant view. It stays in the source cache but is excluded from frequency counts so base text and variants are not double-counted. Longer Neofiti marginalia remain incomplete. Sefaria-derived Pseudo-Jonathan, Jerusalem fragments, and the eight-segment Neofiti excerpt are retained in the source cache as acquisition controls but are not duplicated in the default index.

This repository ships no Aramaic text.

## Fields

`aramaic` exposes passage fields including `corpus_id`, `reference`, `dialect`, `period`, `form_original`, Unicode display form where available, normalized transliteration, TF-node and orthographic counts, source file, license, redistribution status, and review status. `aramaic_tokens` exposes the critical surface, consonantal form, token transliteration, lexeme, original and normalized root, gloss, morphology, model score where applicable, and DSS preservation state. A DSS token counts as preserved only if it has none of: reconstruction, uncertainty, correction, removal, alternatives, vacats, or missing/empty signs.

The normalized-root layer keeps the sibilants apart: ETCBC/CAL `C` (šin) normalizes to `š` (`CLM` → `šlm`), `F` (śin) to `ś`, and `S` (samekh) stays `s`. `J` (yod) normalizes to `y`.

The ETCBC Targum `root` attribute is cut off at ṭet: no rooted token carries `V`, while 2,852 tokens (968 lexemes) keep it in `lexeme` (`MVWL` has root `M`, `JTQVL` has `Q`, `LJV` has `LW`). A ṭ-root cannot be found by root in this layer; search the ETCBC lexeme (`NVL`) or the consonantal form (`נטל`), either of which matches as a substring.

## Validation

The index validates required CSV fields, unique record IDs, DSS word-to-line containment, and the Bavli segmentation checksum/schema/counts. Its manifest, `data/aramaic_texts.manifest.json`, carries builder/input/output hashes, source commits, per-corpus counts, DSS structural counts, and an explicit diagnostics ledger. The index retains sign-level critical state and does not manufacture roots for unannotated corpora. The current diagnostics list seven malformed upstream IIP XML files; they are not silently counted.

## Primary sources

- Aramaic Root Atlas: eight established corpora plus public-domain Sefaria acquisitions staged for comparison.
- ETCBC Targum Corpus at commit `5b2108b9eed2f7eaffd5f63abafa244d173b4087`.
- ETCBC Dead Sea Scrolls at commit `ac91a978d630f426e327f88eb0eeb85d6e67210a`; data version 2.0.1 is indexed.
- Open corpora: IIP inscriptions, the Digital Syriac Corpus, ETCBC Syriac, a reproducible ORACC Aramaic extraction, Sefaria and Dicta Bavli witnesses, ETCBC extrabiblical controls, and Palmyrene metadata.

The ETCBC Targum checkout has conflicting license metadata (MIT in README/config and Zenodo, CC BY-NC in the current `LICENSE.md`). Apply the stricter CC BY-NC terms until the publisher resolves this. The Vatican Neofiti facsimile has separate image rights and is not copied locally.

## Limits and priority gaps

Do not describe this as “all ancient Aramaic.” Strong areas are Biblical Aramaic, major Targums, most published Judaean Desert texts, the Peshitta, and a substantial Syriac layer. Major gaps remain:

1. Old and Imperial Aramaic, especially Sefire, Tell Fekheriye, Zakkur, Samʾal, Elephantine, Hermopolis, Ahiqar, Arsames, Saqqara, Wadi Daliyeh, Idumaean, and Bactrian documentary texts, and Aramaic written in Demotic script (SED's `Dem.`, e.g. `Dem. tkmh` 'back' [HJ 1266]).
2. Full linguistic corpora for Nabataean, Palmyrene, and Hatran.
3. Old Syriac inscriptions and Gospel witnesses; Christian Palestinian and Samaritan Aramaic.
4. Mandaic literature and epigraphy.
5. A manually or independently verified Bavli language edition, plus acquisition and segmentation of the Yerushalmi; both mix Hebrew and Aramaic.
6. Targum Sheni, longer Neofiti marginalia, and fragment witnesses beyond the ETCBC/Klein corpus.

Elephantine exposes object-level TEI under CC BY-NC-SA, but no documented bulk export has yet been verified; obtain permission or a supported dump before harvesting. BBAW Digital Ginza requires confirmation that both halves are fully exportable before it can be called a Mandaic corpus. CAL covers many gaps. It publishes no terms or export, and its robots.txt sets Crawl-delay: 60, so bulk harvest is out; request targeted exports from the editor. DEAPS and critical Yerushalmi resources likewise require rights/export checks before bulk acquisition. DASI record data instead has a verified CC BY 4.0 OAI route; see the DASI section of [arabic-corpora.md](arabic-corpora.md) and keep any DiCoNab language layer explicitly labeled.

For case-by-case research, bounded adapters query one DEAPS result page or one exact record and one Elephantine catalogue result page, object, or text. They do not paginate automatically, fetch images, follow TEI links, or convert public search access into bulk acquisition:

```bash
python3 tools/ane/query_deaps.py 'TAD D.17.1' --field name
python3 tools/ane/query_elephantine.py 309606
python3 tools/ane/query_elephantine.py --text 309606
```

CAL remains manual/export-only. The clients and their caching are listed in `tools/ane/README.md`.

## Method cautions

- Treat composition, redaction, manuscript, and edition dates separately.
- Qumran/DSS and rabbinic corpora are multilingual; filter by language rather than script.
- Palmyrene metadata is not counted as transcription.
- Samaritan Pentateuch data is Samaritan Hebrew, not automatically Samaritan Aramaic.
- Aramaic-script Iranian texts and Aramaic heterograms are not automatically Aramaic language.
- Use manuscript or critical-edition control for consequential readings. ETCBC Targum is alpha. DSS morphology here is Abegg's annotation decomposed into ETCBC features, while the separately named `_etcbc` model fields are not ingested; neither substitutes for edition control.
