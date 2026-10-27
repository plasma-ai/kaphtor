---
name: data/ane/kassite-concordances
title: Kassite name concordances
desc: 9,621 entries of the name indexes in seven volumes of Kassite-period and kudurru texts (Clay, Hinke, Radau, King, 1906–1912), as OCR leads to the printed page, public domain.
tags: [data, cuneiform, kassite, onomastics]
license: Public domain
created: 2026-10-27T17:22:41Z
updated: 2026-10-27T17:22:41Z
---

# Kassite name concordances

[[data/ane/_index|..]]

[[data/ane/kassite-concordances/MANIFEST.json|MANIFEST.json]]: The seven works, the sections read and left out, the transcription, identity, kind and OCR-status rules, the OCR slips seen, counts and checksums.

[[data/ane/kassite-concordances/entries.jsonl|entries.jsonl]]: 9,621 printed index entries, one row each, with headword, references, kind, gender and printed page.

***

| Work | Rows |
| --- | ---: |
| Clay, *Personal Names from Cuneiform Inscriptions of the Cassite Period* (YOS 1, 1912) | 3,703 |
| Clay, *Documents from the Temple Archives of Nippur*, incomplete dates (BE A 15, 1906) | 1,888 |
| Clay, *Documents from the Temple Archives of Nippur* (PBS 2/2, 1912) | 1,239 |
| Clay, *Documents from the Temple Archives of Nippur*, complete dates (BE A 14, 1906) | 1,183 |
| Hinke, *A New Boundary Stone of Nebuchadrezzar I from Nippur* (BE D 4, 1907) | 632 |
| King, *Babylonian Boundary-Stones and Memorial-Tablets in the British Museum* (1912) | 518 |
| Radau, *Letters to Cassite Kings from the Temple Archives of Nippur* (BE A 17/1, 1908) | 458 |

The volumes are in the public domain, and the OCR text and this file add no rights.

A row is an OCR lead to the printed page, not a reading: it says that the volume prints an entry of this form on this
page. Read the form off the page image before citing it, and cite the volume and printed page. `ocr_status` says what
each row was compared with:

- `image_checked` (814): against the page scan.
- `acrobat_rendering_checked` (575): BE A 14 and BE A 15, whose PDFs are Acrobat Paper Capture output with no page
  scan. The row agrees with both Acrobat's OCR and the OCR it was read from, and can keep a slip they share.
- `ocr_unchecked` (8,232): the rest. They keep the OCR's slips, which the MANIFEST lists under `ocr_slips_seen`: h or
  ḥ for ḫ, ¹ or l for the feminine determinative, 4 for ᵈ, d- or 6- for Ú-, macrons for circumflexes.

`entry_ocr` is the record, and `headword`, `refs_ocr` and `normalized_key` are derived from it. `kind` (8,201 persons,
504 places, 386 deities, 68 rivers and canals, 26 gates, 22 temples) and `gender` come from the book's section
headings. King's index has no headings: 104 of his rows take their kind from his own words, quoted in `kind_basis`,
and the other 414 are `unstated`. `column: "span"` means the OCR gave both columns of the page as one block. Ids are
`<work key>-<pdf page>-<row>` (`clay1906-be15-034-037`).
