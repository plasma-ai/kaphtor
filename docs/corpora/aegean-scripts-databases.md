---
name: docs/corpora/aegean-scripts-databases
title: Aegean Scripts Databases
desc: The open online databases for Linear A, Linear B and the scripts beside them (SigLA, DAMOS, MNAMON and INSCRIBE), with what each holds, how to reach it and its licence.
tags: [corpora, docs]
created: 2026-10-22T18:14:10Z
updated: 2026-10-22T18:14:10Z
---

# Aegean Scripts Databases

Open online databases for the Bronze Age Aegean scripts: Linear A, Linear B and the scripts beside them. For the
Cypro-Minoan layers (PASP, Sign2Vec) and the other comparative controls, see
[aegean-comparative-corpora.md](aegean-comparative-corpora.md).

## SigLA: The Signs of Linear A

**URL:** https://sigla.phis.me. **Maintainers:** Ester Salgarella and Simon Castellan. **Licence:** dataset and
drawings CC BY-NC-SA 4.0. **Access:** open, no login; most pages work without JavaScript.

A palaeographic database of Linear A inscriptions. It holds every GORILA tablet, the roundels of Haghia Triada and
Khania, and documents published since. Each document gives its site, dimensions, period, a link to its corpus entry
and drawing, and each of its signs with its reading and class.

`data/linear-a/corpus.json` builds on SigLA's readings; its record keys and how they group into documents are in
[corpus-census.md](../corpus-census.md).

### URL patterns

```
https://sigla.phis.me/browse.html                    # every document, by site
https://sigla.phis.me/document/HT%201/               # one document, its signs in order
https://sigla.phis.me/document/HT%201/index-1.html   # one sign of that document, by position
https://sigla.phis.me/sign-list.html                 # the sign list
https://sigla.phis.me/search-document.html           # search by document
https://sigla.phis.me/search-sequence.html           # search by sign sequence
https://sigla.phis.me/search-attestation.html        # search by attestation
https://sigla.phis.me/map.html                       # sites
```

A document's name is its siglum with the space kept, URL-encoded (`HT 1` → `HT%201`).

### Publication

Salgarella, E. & Castellan, S. (2021). "SigLA: The Signs of Linear A. A Palæographical Database." In Y. Haralambous
(ed.), *Grapholinguistics in the 21st Century 2020: Proceedings, Part 2*, pp. 945–962. Brest: Fluxus Editions. Also at
https://sigla.phis.me/paper.html.

## DAMOS: Database of Mycenaean at Oslo

**URL:** https://damos.hf.uio.no. **Maintainer:** Federico Aurora, University of Oslo. **Access:** open, no login.

An annotated electronic corpus of all published Mycenaean Linear B texts, in the CIPEM Latin transliteration. Its
epigraphic tags (a text's chronology, its scribe) are searchable. Words are annotated by hand for morphology and syntax,
case above all, with a translation and, where one can be reconstructed, the Indo-European root. A word can carry
several analyses at once, ranked by probability.

```
https://damos.hf.uio.no/about/database/   # what the database records
https://damos.hf.uio.no/about/texts/      # the texts it holds
https://damos.hf.uio.no/about/online/     # related online resources
```

Aurora, F. (2015). "DĀMOS (Database of Mycenaean at Oslo). Annotating a Fragmentarily Attested Language." *Procedia –
Social and Behavioral Sciences* 198: 21–31. https://doi.org/10.1016/j.sbspro.2015.07.415.

## MNAMON: Ancient Writing Systems in the Mediterranean

**URL:** https://mnamon.sns.it (Scuola Normale Superiore, Pisa). **Access:** open.

An encyclopedia of the writing systems of the ancient Mediterranean: Linear A, Linear B, Cretan Hieroglyphic,
Cypro-Minoan and the Cypriot syllabary; Hieroglyphic and cuneiform Luwian, Lycian, Lydian and Carian; Phoenician,
Ugaritic, Aramaic and the cuneiform scripts; Etruscan, Iberian and Celtiberian. Each script has a description,
chronology, bibliography and a page of online resources.

```
https://mnamon.sns.it/index.php?page=IndiceAlfabetico&lang=en   # scripts, A to Z
https://mnamon.sns.it/index.php?id=19&lang=en&page=Scrittura    # Linear A
https://mnamon.sns.it/index.php?id=19&lang=en&page=Risorse      # Linear A online resources
```

## INSCRIBE: Invention of Scripts and Their Beginnings

**URL:** https://site.unibo.it/inscribe/en (University of Bologna). **Access:** open.

An ERC Consolidator project (2018–2023) on how writing was invented and first developed. It set the original
inventions of Mesopotamia, Egypt, Mesoamerica and China beside the three Aegean scripts: Cretan Hieroglyphic, Linear A
and Cypro-Minoan. Its site carries the project's publications, workshops and seminars.
