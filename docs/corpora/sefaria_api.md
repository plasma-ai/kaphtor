---
name: docs/corpora/sefaria_api
title: Sefaria API
desc: How to query Sefaria's public API for Hebrew Bible passages, Targums, commentaries, links and search, one passage at a time.
tags: [corpora, docs]
created: 2026-10-22T18:14:10Z
updated: 2026-10-22T18:14:10Z
---

# Sefaria API

Sefaria's public API serves the Hebrew Bible, its Targums and its commentaries, with no key. This repository ships no
Sefaria text; query it one passage at a time, and space requests out.

Base URL: `https://www.sefaria.org/api/`

## Texts (v3)

```
GET /api/v3/texts/{ref}
```

A ref joins book, chapter and verse with dots, and spaces in a title with underscores: `Genesis.1.1`, a range
`Genesis.1.1-3`, a chapter `Genesis.1`, across chapters `Genesis.1.1-2.4`.

With no `version`, the response holds the primary Hebrew text alone. `version` picks others and may be repeated:
`source`, `translation`, a language (`english`, `hebrew`), or one edition as `language|versionTitle`.

```bash
curl -s "https://www.sefaria.org/api/v3/texts/Genesis.1.1?version=source&version=translation"
```

The response names the passage (`ref`, `heRef`, `sectionRef`, `indexTitle`) and lists `versions`; each version
carries `versionTitle`, `language`, `text` and `license`. Licences differ by edition (the Masoretic text here is
CC-BY-SA, the JPS translation CC-BY-NC): check `license` before reusing a text.

## Commentaries and Targums

A commentary or Targum is a text of its own, fetched by its title:

| Text | Ref |
|---|---|
| Rashi | `Rashi_on_Genesis.1.2` |
| Ibn Ezra | `Ibn_Ezra_on_Genesis.1.2` |
| Ramban | `Ramban_on_Genesis.1.1` (only verses he comments on) |
| Targum Onkelos | `Onkelos_Genesis.1.2` |
| Targum Neofiti | `Targum_Neofiti,_Genesis.1.2` |

## Links

```
GET /api/links/{ref}
```

Every text that links to the passage, commentaries among them; each row gives the linked `ref`, its `category`,
`collectiveTitle` and `text`, and its `license`.

```bash
curl -s "https://www.sefaria.org/api/links/Genesis.1.1"
```

## Search

Search takes a POST with a JSON body; a GET is refused.

```bash
curl -s -X POST "https://www.sefaria.org/api/search-wrapper" \
  -H "Content-Type: application/json" \
  -d '{"query": "שלום", "type": "text", "filters": ["Tanakh"], "size": 20}'
```

`hits.total` counts the matches; each of `hits.hits` gives the ref and edition in `_id` (`Jeremiah 6:14 (Tanach
with Nikkud [he])`) and the matched words in `highlight`.

## Book index

```
GET /api/v2/index/{book}
```

The book's structure, categories and composition data.

## Errors

A failure returns JSON with an `error` key, and not always with an error status: an unknown title or a passage with
no text is a 404, but a GET to the search endpoint comes back 200 with `"error": "Unsupported HTTP method."`. Check
for `error` before reading a response.
