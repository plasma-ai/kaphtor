---
name: docs/corpora/cuneiform-databases
title: CDLI and ORACC Online
desc: How to reach one record at a time on the live CDLI and ORACC sites, and how ATF transliteration is written.
tags: [corpora, docs]
created: 2026-10-22T18:14:10Z
updated: 2026-10-22T18:14:10Z
---

# CDLI and ORACC Online

How to reach one record at a time on the live CDLI and ORACC sites. The local snapshot of both, with its counts,
licences, edition identity and bulk acquisition routes, is described in [cuneiform-corpora.md](cuneiform-corpora.md);
query that first.

## CDLI: Cuneiform Digital Library Initiative

**URL:** https://cdli.earth. **API documentation:** https://cdli.earth/docs/api.

The API works by content negotiation; for metadata a `.json` extension does the same as `Accept: application/json`.
An artifact's id is its P-number without the `P`:

```bash
curl -s "https://cdli.earth/artifacts/480701.json"
```

The response is a one-item list. Its `designation`, `period`, `genres`, `languages`, `publications` and `composites`
describe the artifact; `inscription.atf` holds the full ATF text and `inscription.transliteration` the bare lines.
`/artifacts/P480701.json`, with the `P`, returns 500.

The same pattern serves the other catalogue tables (`/periods/*`, `/proveniences/*`, `/genres/*`, `/publications/*`
and more; the documentation lists them all). Full-text search is the web page https://cdli.earth/search.

## ORACC: Open Richly Annotated Cuneiform Corpus

**URL:** https://oracc.museum.upenn.edu.

```
https://oracc.museum.upenn.edu/projectlist.json            # every project, with its pathname and blurb
https://oracc.museum.upenn.edu/json/{project}.zip          # one project's editions, glossaries and catalogue
https://oracc.museum.upenn.edu/amgg/listofdeities/marduk/  # one AMGG deity article
```

`projectlist.json` is not valid JSON: its `"projects"` array is opened twice. Read the `"pathname"` lines from it as
text rather than parsing it. Sub-projects have slash paths (`cams/gkab`, `ribo/babylon4`).

The per-text routes `/{project}/corpusjson/{P-number}.json` and `/{project}/glossary-{lang}.json` answer 200 with an
empty body; take editions and glossaries from the project ZIP. A project that does not exist also answers 200, with a
page that says so.

| Project | Contents |
|---|---|
| `amgg` | Ancient Mesopotamian Gods and Goddesses: one article per deity |
| `epsd2` | electronic Pennsylvania Sumerian Dictionary, 2nd edition |
| `dcclt` | Digital Corpus of Cuneiform Lexical Texts |
| `saao` | State Archives of Assyria Online |
| `rinap` | Royal Inscriptions of the Neo-Assyrian Period |
| `rimanum` | The House of Prisoners: the Old Babylonian Rimanum archive |
| `cams/*` | Corpus of Ancient Mesopotamian Scholarship, in sub-projects |

## ATF

ATF (ASCII Transliteration Format) is the line format of both sites. CDLI's `inscription.atf` keeps the ASCII
spellings: `sz` for š, `s,` for ṣ, `t,` for ṭ, plain `h` for ḫ (`hu-bur`), and sign indices as digits (`u2`).
ORACC's editions use Unicode (`šá`, `ṣ`, `ḫ`). The opening of P480701, as CDLI serves it:

```
&P480701 = CDLI Literary 002718 (enuma elish) composite
#atf: lang akk
@object composite text
@surface a
@tablet 1
1. e-nu-ma e-lisz la na-bu-u2 sza2-ma-mu
#tr.en: When on high the heaven had not been named,
>>Q002718.01 001
2. szap-lisz am-ma-tum szu-ma la zak-rat
#tr.en: Firm ground below had not been called by name,
>>Q002718.01 002
```

- `&P…` opens a text with its id and designation; `#atf: lang` gives its language.
- `@object`, `@surface`, `@tablet`, `@obverse`, `@reverse` mark the physical structure.
- A numbered line is transliteration; `#tr.en:` is its English translation.
- `>>Q…` links the line to its line in a composite text (here composite Q002718).
- Words between underscores (`_abzu_`) are logograms.
