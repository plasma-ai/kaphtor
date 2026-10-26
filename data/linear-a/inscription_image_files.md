---
name: data/linear-a/inscription_image_files
title: Linear A inscription image files
desc: Each corpus record's photograph and facsimile files, as paths inside a checkout of the image archive; names only, no images.
tags: [data, linear-a, images]
license: CC BY 4.0
created: 2026-10-24T14:45:00Z
updated: 2026-10-26T21:18:27Z
---

`inscription_image_files.json` holds `description` and `files`: one entry per corpus record that has an image,
keyed by its id in `corpus.json`, each `{inscription: [...], facsimile: [...]}`. A path is relative to a checkout of
the image archive (`images/HT13-Inscription.jpg`). A record's files
can carry a face letter or the edition's own number where the corpus merged or renamed it (CRZf1 →
`CR(?)Zf1-Inscription.jpg`). 1,708 records name 1,702 photograph files (on 1,671 records) and 1,691 facsimile files
(on 1,673). Two facsimiles named here, HTW231c's and KNsceau's, are not in the checkout. Where a record lacks a
photograph or a facsimile, its `visual_evidence` in `corpus.json` cites the published one, or is `[]`.

`tools/linear_a/inscription_image.py` reads this file with `corpus.json` and opens, copies or lists the images from
the checkout named by `LASHON_HA_KRETAN_DIR`. The images are their sources' and are not in this repository; this
file names them and nothing more.
