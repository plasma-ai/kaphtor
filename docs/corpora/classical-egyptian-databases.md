---
name: docs/corpora/classical-egyptian-databases
title: Classical & Egyptian Text Databases
desc: The open Greek, Latin and Egyptian text databases (TLA, Perseus, TLG and Digital Egypt for Universities), what each holds and how to reach it.
tags: [corpora, docs]
created: 2026-10-22T18:14:10Z
updated: 2026-10-22T18:14:10Z
---

# Classical & Egyptian Text Databases

Reference for open-access databases of Greek, Latin, and Egyptian texts relevant to ANE comparative research.

---

## TLA — Thesaurus Linguae Aegyptiae

**URL:** https://thesaurus-linguae-aegyptiae.de
**Institutions:** Berlin-Brandenburg Academy of Sciences (BBAW) & Saxon Academy of Sciences (SAW)
**Project period:** 2013–2034
**Access:** Open. Raw data downloadable from https://aaew.bbaw.de/daten-veroeffentlichungen

Digital corpus of Ancient Egyptian texts spanning 4,000+ years (ca. 3000 BCE – 1400 CE).

### Content

- Hieroglyphic, hieratic, demotic, and Coptic texts
- Complete lemma lists (Egyptian vocabulary)
- Morphological annotation
- Texts of all types and genres from all periods

### URL Patterns

```
# Home
https://thesaurus-linguae-aegyptiae.de/home?lang=en

# Text corpus info
https://thesaurus-linguae-aegyptiae.de/info/text-corpus?lang=en

# Lemma lists info
https://thesaurus-linguae-aegyptiae.de/info/lemma-lists?lang=en

# Search interface
https://thesaurus-linguae-aegyptiae.de/search

# Raw data downloads (Berlin server)
https://aaew.bbaw.de/daten-veroeffentlichungen
```

### Research Relevance

- **Tempest Stela (Ahmose I):** search by ruler "Ahmose" or by genre
- **Egyptian-Canaanite contact texts:** Amarna Letters context, Execration Texts, Sinuhe
- **Deity name parallels:** Egyptian forms of Semitic deity names (Astarte, Resheph, Ba'al)
- **Chronological data:** Egyptian king lists and annals for Bronze Age absolute dating

### Access Method

No API. Use web search interface or download raw data for local processing. For specific texts, use the web interface.

---

## Perseus Digital Library

**URL:** https://www.perseus.tufts.edu
**Institution:** Tufts University
**Access:** Open. Texts under Creative Commons.

Greek and Latin texts with morphological analysis, English translations, and lexicon integration.

### Structured Access

Perseus offers XML/JSON endpoints beyond the basic web interface:

```bash
# Text fetch (TEI XML)
curl -s "https://www.perseus.tufts.edu/hopper/xmlchunk?doc=Perseus:text:1999.01.0126:book=4:chapter=147"
# → Herodotus 4.147

# Morphological analysis
curl -s "https://www.perseus.tufts.edu/hopper/morph?l=θήρα&la=greek"
# → Parse Greek word

# Word study tool
https://www.perseus.tufts.edu/hopper/wordfreq?lang=greek
```

### Access Method

Prefer structured XML endpoints for known passages, and the web interface for browsing and discovery.

---

## TLG — Thesaurus Linguae Graecae

**URL:** https://stephanus.tlg.uci.edu
**Institution:** UC Irvine
**Access:** Subscription for full text; free word/author search

Comprehensive digital library of Greek literature from Homer (8th c. BCE) to 1453 CE. 110M+ words.

### Free Features

- **Word search:** Search for any Greek word across the entire corpus
- **Author index:** Browse by author, work, and genre
- **Canon of authors:** Complete bibliography of Greek authors and works

### Subscription Features

- Full text display
- Proximity search
- Morphological searching
- Citation export

### Research Relevance

Exhaustive Greek literary searching — broader than Perseus. Use for:

- Tracing all occurrences of Θήρα, Μίνως, Κνωσός across Greek literature
- Finding attestations of Semitic loanwords in Greek
- Identifying parallel mythological narratives

### Access Method

Free search identifies which texts contain a term; full text requires institutional subscription. For passages identified via TLG search, retrieve full text from Perseus where it is available there.

---

## Digital Egypt for Universities (UCL)

**URL:** https://www.ucl.ac.uk/museums-static/digitalegypt/
**Institution:** UCL Petrie Museum
**Access:** Open

Teaching resource for Egyptian history and material culture, organized by period, topic, and object type.

### Research Relevance

- New Kingdom material culture
- Egyptian-Aegean trade objects
- Chronological tables and king lists
