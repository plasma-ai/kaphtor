---
name: data/ane/hatra-marcato
title: Hatra personal names (Marcato 2018)
desc: The 407 entries of Enrico Marcato's catalogue of personal names in the Aramaic inscriptions of Hatra (376 names, 31 incomplete), each with his translation, other readings, analysis, inscription numbers and printed page, CC BY 4.0.
tags: [data, hatra, aramaic, onomastics]
license: CC BY 4.0
created: 2026-11-14T22:18:40Z
updated: 2026-11-14T22:18:40Z
---

# Hatra personal names (Marcato 2018)

[[data/ane/_index|..]]

[[data/ane/hatra-marcato/MANIFEST.json|MANIFEST.json]]: The book and its DOI, the PDF's checksum, what each row holds and leaves out, the text, id and page rules, counts and the output's checksum.

[[data/ane/hatra-marcato/names.jsonl|names.jsonl]]: 407 catalogue entries, one row each: the name as printed, Marcato's translation or cross-reference, his other readings, his analysis, the references to Palmyrene names he gives, the attestation line with its H numbers, and the printed page.

***

Enrico Marcato, *Personal Names in the Aramaic Inscriptions of Hatra* (Antichistica 17, Studi orientali 7;
Venezia: Edizioni Ca' Foscari 2018, doi:10.30687/978-88-6969-231-4), CC BY 4.0.

The rows come from chapter 2 of the publisher's PDF: section 2.1, the 376 names, and section 2.2, the 31
incomplete names. `analysis` and `other_readings` are Marcato's text, quoted under his licence; a footnote mark is
dropped and a raised determinative is written as a superscript letter (ᵐad-da-a). `palmyrene_refs` lists the
references he gives to Stark 1971 and to PAT numbers, as printed: they are his citations, and neither work is
shipped here. Chapters 3 to 5 (the linguistic analysis and concordances) are in the book.

```bash
uv run --no-sync python -m tools.ane.query_proper_names ʿqb --source hatra-marcato --exact
uv run --no-sync python -m tools.ane.query_proper_names ʾdʾ --source hatra-marcato --exact --json
```
