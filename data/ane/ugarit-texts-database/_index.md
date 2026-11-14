---
name: data/ane/ugarit-texts-database
title: Ugarit Texts Database
desc: Catalogue metadata for 4,582 inscribed objects from Ras Shamra and Ras Ibn Hani (find number, KTU number, language, script, genre, findspot), from František Válek's Ugarit Texts Database, CC BY 4.0.
tags: [data, ugarit, catalogue]
license: CC BY 4.0
created: 2026-11-13T19:10:00Z
updated: 2026-11-13T19:10:00Z
---

# Ugarit Texts Database

[[data/ane/_index|..]]

[[data/ane/ugarit-texts-database/MANIFEST.json|MANIFEST.json]]: The Zenodo record, its licence and date, the source file's checksum, counts and the output's checksum.

[[data/ane/ugarit-texts-database/records.jsonl|records.jsonl]]: 4,582 catalogue records, one per object, with the source's own columns kept in `raw_fields`.

***

František Válek, *Ugarit Texts Database* (Zenodo, 2024, doi:10.5281/zenodo.12820382), CC BY 4.0. The database
combines the Ras Shamra Tablet Inventory (RSTI), Bordreuil and Pardee's concordance (TEO), SAU, KTU and other
sources; those works keep their own terms, and this file holds catalogue metadata only, no transcription.

```bash
uv run --no-sync python -m tools.ane.aneq ugaritdb 16.156
```

A record locates a tablet; it is no attestation of a word. For the Akkadian texts' editions and translations see
`data/share-alike/oracc-levant/`.
