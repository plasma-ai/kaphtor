---
name: data/share-alike/anatolian
title: TLHdig Anatolian, Hurrian, Hattic and Boğazköy Akkadian documents
desc: The 19,725 preserved-word document records of TLHdig 0.3 covering Hittite, Luwian, Hurrian, Hattic and Boğazköy Akkadian, CC BY 4.0.
tags: [data, anatolian, hittite, luwian, hurrian, hattic, akkadian]
license: CC BY 4.0
created: 2026-11-23T16:35:00Z
updated: 2026-11-23T16:35:00Z
---

# TLHdig Anatolian, Hurrian, Hattic and Boğazköy Akkadian documents

[[data/share-alike/_index|..]]

[[data/share-alike/anatolian/tlhdig_docs.jsonl|tlhdig_docs.jsonl]]: One row per `(document_id, language)` in TLHdig 0.3 with preserved bound transcriptions (19,725 rows; 485,519 tokens across Hittite, Luwian, Hurrian, Hattic and Boğazköy Akkadian).

***

`tlhdig_docs.jsonl` holds 19,725 grouped rows in source order, cut to the fields read by `models/language-id-kernel/lid.py`, `liturgy_c.py`, `verbs_e.py`, `onomastics_h.py`, `morphology_i.py` and `render/c_texts.py`: Hittite (17,631 documents; 207,306 clean words), Luwian (140 documents; 1,054 clean words), Hurrian (723 documents; 9,868 clean words), Hattic (331 documents; 2,823 clean words) and Boğazköy Akkadian (900 documents; 15,776 clean words).

| Field | Content |
| --- | --- |
| `document_id` | TLHdig XML document identifier (`tlhdig:xml/...`) |
| `language` | TLHdig language code (`Hit`, `Luw`, `Hur`, `Hat`, `Hattian`, `Akk`) |
| `words` | Preserved bound transcriptions in token order |

**Source.** Thesaurus Linguarum Hethaeorum digitalis (TLHdig), release 0.3 (Zenodo, doi:10.5281/zenodo.20328284), CC BY 4.0.

**Build.** `models/language-id-kernel/build_shipped_inputs.py --tlhdig` cuts the file from the full TLHdig word list; with `--check` it compares the two and writes nothing.
