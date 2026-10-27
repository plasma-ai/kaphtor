---
name: data/ane/gauthier-dng
title: Gauthier, Dictionnaire des noms géographiques
desc: 7,497 entries, cross-references and addenda of Gauthier's Dictionnaire des noms géographiques, t. 1–6 (1925–1929), read from the scans' OCR text layer as a page finder, public domain.
tags: [data, egyptian, toponyms]
license: Public domain
created: 2026-10-27T17:22:41Z
updated: 2026-10-27T17:22:41Z
---

# Gauthier, Dictionnaire des noms géographiques

[[data/ane/_index|..]]

[[data/ane/gauthier-dng/MANIFEST.json|MANIFEST.json]]: The work, rights, scans, the page, split and field rules, the page check of every half page, counts and checksums.

[[data/ane/gauthier-dng/entries.jsonl|entries.jsonl]]: 7,497 rows, 6,416 entries, 207 cross-references and 874 addenda, each under the volume and printed page it opens on.

***

The source is Henri Gauthier, *Dictionnaire des noms géographiques contenus dans les textes hiéroglyphiques*, t. 1–6
(Le Caire 1925–1929), from the archive.org scans and their OCR text layer. T. 7 (1931, the index) is not included.
HathiTrust records t. 1–6 as public domain in the US. Gauthier died in 1950, so they are also in the public domain where
the term is the author's life plus 70 years.

The file is a page finder, not a source of forms. The hieroglyphs are not in the text layer, so `hieroglyphs` is null
throughout. The transcription is Gauthier's French-style one (kh, ch, ou, â) as the OCR gives it: ḥ comes out as `l;l`,
`l)`, `J:i` or `Q`, and letters drop. Read the printed page before quoting a form, gloss or citation. 2,625 rows
carry `flags`: a head not found or irregular, no source citation, a margin row run on, an entry start near the indent,
a short entry. The MANIFEST counts each flag.

Ids are `gauthier:t<volume>:p<printed page>:<n>`, where n is the entry's place among those opening on that page. An
entry that runs on keeps its first page, and `page_end` gives its last. Each pdf page is a two-page spread: the printed
page of the left half is 2 × pdf page − 14 in t. 1 and 2 × pdf page − 8 in t. 2–6, and the right half is the next
page. `page_check` in the MANIFEST compares this with the OCR'd folio and the sheet signature. A modern name finds its
entry through `description_fr` (El-Achmounein, t. 2 p. 50).
