---
name: docs/corpora/query-notation
title: "Query notation: what each view stores, and how a query reaches it"
desc: How a typed root or form is read and spelled in each view's own transliteration, and how a matched row reports the basis of its match.
tags: [corpora, docs]
created: 2026-10-22T18:14:10Z
updated: 2026-10-22T18:14:10Z
---

# Query notation: what each view stores, and how a query reaches it

Each corpus keeps its own transliteration. `tools/ane/ane_keys.py` reads a query once and spells it in every
notation a view stores (`VIEW_NOTATION`); the data is never rewritten to suit a query. Type a root or form the
way you would write it — `ʾ-m-r`, `ʔmr`, `√ʾmr`, `'MR`, `s¹`, `s1`, `š`, Hebrew or Arabic letters — and
`query_proper_names.py` and `query_place_authorities.py` find the stored spelling.

## Reading a query

- Composed (NFC); `√` and `*` dropped; case folded (Hebrew and Arabic have none).
- A hyphen, a dot between single letters, or `√` makes it a **root**; otherwise it is a **form**.
- One unit per letter: a mark stays on its letter, `s¹`/`s₁`/`s1` is one letter.
- The aleph signs `ʾ ʔ ʼ` and the ayin signs `ʿ ʕ ‘ ᶜ` are each one letter; a bare `'` is either.
- ASCII digraphs are read both ways in views without a Manuel de Codage reading: `sh kh th dh gh` ↔ `š ḫ ṯ ḏ ġ`.

## What each view stores

| View | Aleph / ayin | Key shape | Notes |
|---|---|---|---|
| quran | ʔ / ʿ | bare, hyphenated | jīm stored ǧ (a typed j means ǧ) |
| epi | ʾ / ʿ | bare | |
| hebrew | — | as typed | unpointed consonants; pointing and final forms folded; `--root` takes BDB's root (Open Scriptures lexical index, `oshb_lemma_roots.jsonl`) in Hebrew letters or transliteration, ש as š or ś; 38% of lemmas (names, particles), 26% of word tokens, have none; a word matches whole or as one of its parts (ב/ראשית holds ראשית), inside it as a substring |
| egytext | ʾ / ꜥ ʿ | as typed | Manuel de Codage read too (A a H x X S T D i); ẖ composed |
| aramaic | ʾ / ʿ | bare | ETCBC roots; yod stored y (a typed j means yod); ś for ETCBC F; the root is cut off at ṭet (search the lexeme) |
| dasi | ʾ / ʿ | bare, as typed | s¹ s² s³; running text, matched word by word |
| ahi | ʾ / ʿ | bare, as typed | Hebrew letters romanised; a word is keyed whole across restorations and concordance marks (`D(W)'[L]` → dʿwʾl), a lacuna still separates; the folded key writes ʾ and ʿ as `'` |
| term | ʔ / ʕ | hyphenated | the pointed Hebrew term also matched unpointed |
| pnm (names) | ꜣ / ꜥ | as typed | Manuel de Codage read; = is ⸗ |

## How a row matched: `match_basis`

Every `--json` row names its basis, and rows sort by it:

| Basis | Meaning |
|---|---|
| 0 exact | the query as typed |
| 1 notation | the query spelled in the view's notation |
| 2 folded | marks, the aleph/ayin distinction, sibilant indexes and separators folded |
| 4 substring | the query inside a longer form, or an element of a name |
| 5 gloss | the query as a whole word of a gloss (an English plural allowed; German glosses by word start) |

Bases 3 and 6 belong to views that are not in this repository; the numbers are kept so the others keep their meaning.
A root query (hyphen, √, dotted letters) never matches a gloss.

## The folded tier and `--loose`

The folded tier joins when nothing matches strictly as a whole form (as typed, in notation, or in a spelling the
view stores folded: basis 0–2), as `query_proper_names.py` has it, or with `--loose`: a substring or gloss
match alone lets it in, and a folded name then ranks above them. It folds one way: a bare letter in
the query reaches any marked form of it (`hhtʾ` finds `hḫṭʾ`), but a mark the query carries is kept (`mwṯ`
does not find `mwt`). The ʾ/ʿ signs, sibilant indexes, separators and case fold
both ways. In running text (dasi) the fold never joins two words.

## Provenance

Every `--json` row carries `provenance`: the files read, each with its size, mtime and sha256 (files over 25 MB:
size and mtime only), and the query as typed, as read, and its mode.

## Known gaps

- ETCBC Targum roots are cut off at ṭet: search a ṭ-root by its ETCBC lexeme (`NVL`) or its
  consonants (`נטל`).
