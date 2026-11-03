---
name: data/semitic-roots/semitic_roots
title: Semitic roots
desc: Proto-Semitic roots with their reflexes across the Semitic languages, each reflex cited to its source.
tags: [data, semitic-roots]
license: CC BY 4.0
created: 2026-10-22T18:14:10Z
updated: 2026-10-22T18:14:10Z
---

`semitic_roots.json` holds `schema_version` (2), `description` and `roots`: 5,157 records with 26,295 reflexes.
Most reconstructions and meanings come from the Semitic Etymological Dictionary; `sed` cites the SEDonline entry
(2,624 records) or the printed volume, SED I or SED II (23 records). The SA series are Epigraphic South Arabian headwords (Beeston 1982; Biella 1982), not comparative
reconstructions.

| Field | Content |
| --- | --- |
| `id` | the record's number: numeric, or a K, S or SA series id |
| `ps` | the reconstruction (for SA records, the headword) |
| `meaning` | English meaning of the reconstruction |
| `basis` | `{ps, meaning}`: where each comes from, `sed`, `sed_edited` (SED's, corrected) or `project` |
| `sed` | `{siglum, loc}` when the reconstruction or meaning is SED's: `{siglum: "SEDonline", loc: "semet N"}`, or `{siglum: "SED I", loc: "No. N"}` and the like for the printed volumes |
| `reflexes` | one per language (below) |
| `notes` | the project's notes on the record, where there are any |

Each reflex:

| Field | Content |
| --- | --- |
| `lang` | the language |
| `cite` | its sources, each `{siglum, loc}` (siglum and page or entry) |
| `basis` | `sed`, `sed_edited` or `project`, the values of the record's `basis` |
| `source_class` | the cited source's terms: `open` (public domain or an open licence), `open_nc`, `closed`, `mixed`, `unknown`, or `none` (no source cited) |
| `text` | the form or forms as filed, with their citations |
| `gloss_withheld` | true when the source's quoted gloss was taken out of `text` |
| `text_withheld` | true when the cell was the source's prose; only `lang` and `cite` are given |

A reflex keeps its quoted gloss only when its cited source is `open` (3,448 reflexes: Biberstein-Kazimirski,
Lane, Payne Smith, Brockelmann, Jastrow, Freytag, BDB, the Aramaic Root Atlas,
Anderson and Moser's *Protosemitic Root Derivations* and others). Other reflexes give the form and its citation, with
any quoted gloss taken out. In every reflex, a source's commentary after the forms (derivations, hedges, remarks on
what a dictionary lacks) is not included, and neither are the citations that only that commentary named. Notes are the project's own; notes
taken from SED are not included.

1,366 reflexes, 1,089 of them in the K series, cite Anderson and Moser 2024, *Protosemitic
Root Derivations* (Zenodo, doi:10.5281/zenodo.14160276, CC BY 4.0), as `{siglum: "Anderson–Moser 2024",
loc: "root …"}`.

The other cells cite the standard dictionaries by siglum, HALOT, LGz., Lane, CAD, BK, Payne Smith, DULAT and LA (Lisān
al-ʿArab) among them, and five more: Klein (*A Comprehensive Etymological Dictionary of the Hebrew Language*, 1987,
by headword), Ricks 1982 (*A Lexicon of Epigraphic Qatabanian*, by headword; not the 1989 book SED cites as Ricks),
Rubin 2018 (*Omani Mehri*, CC BY-NC-ND 4.0, by page), Al-Jallad 2026 (*Dictionary of the Inscriptions of Ancient
North Arabia I: Safaitic*, CC BY-NC-ND 4.0, by page) and Tāj or TA (*Tāj al-ʿArūs*, by volume:page).

| `source_class` | Reflexes |
| --- | --- |
| closed | 17,563 |
| open | 3,448 |
| none | 2,747 |
| mixed | 1,818 |
| unknown | 409 |
| open_nc | 310 |

`semitic_correspondences.json` is the consonant correspondence table (Huehnergard 2019, Table 3.2, p. 51): for
each Proto-Semitic consonant, its reflex in Akkadian, Ugaritic, Hebrew, Aramaic, Arabic, Sabaic, Gəʿəz and Mehri
(`forward`, and `reverse` from each branch), with `proxies` naming the column a related language is checked
against. The root matcher (`tools/core/root_match.py`) reads both files.

`branches.json` gives the Semitic branch of each language key the reflexes and SED's Analogues columns carry: East
Semitic, Northwest Semitic, Arabic, Epigraphic South Arabian, and Ethiopic with Modern South Arabian (`SOUTH`);
`IGNORE` marks non-Semitic and bookkeeping keys. The branch-distribution census
(`tools/linear_a/analysis/branch_distribution.py`) reads it.

`author_glosses.json` holds the author's gloss of each of the 349 roots the Linear A lexicon cites: `glosses`, keyed
by `id`, each with `gloss` (the root's senses in di Mino's words, beside the record's `meaning`) and `sources` (the
dictionaries the senses are read from, by siglum and page, as the reflexes cite them).
