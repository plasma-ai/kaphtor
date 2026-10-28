---
name: docs/corpora/hathitrust-search-only-volumes
title: Searching HathiTrust search-only volumes
desc: Find the pages of an in-copyright HathiTrust book that hold a word, through the HTRC Extracted Features file of its scan.
tags: [corpora, docs]
created: 2026-10-28T13:25:50Z
updated: 2026-10-28T13:25:50Z
---

# Searching HathiTrust search-only volumes

Many in-copyright books are digitized in HathiTrust but marked search-only (`rightsCode: ic`). Their pages cannot be read or downloaded. HathiTrust's own search-inside runs on `babel.hathitrust.org`, which sits behind a Cloudflare managed challenge (even `robots.txt`, checked 2026-10-28). The client never tries to pass it.

The HathiTrust Research Center (HTRC) Extracted Features (EF) dataset gives the same answer without the viewer. It lists every token on every page of the scan, with its count and part of speech. It covers 17.1 million volumes, in-copyright ones included. The dataset is open:

> Jett, Capitanu, Kudeki, Cole, Hu, Organisciak, Underwood, Dickson Koehl, Dubnicek, Downie (2020). *The HathiTrust Research Center Extracted Features Dataset (2.0)*. HathiTrust Research Center. https://doi.org/10.13012/R2TE-C227. CC BY 4.0.

A hit tells you which printed page to read. It gives no wording and no context, so it is not a source for content: cite the book only after reading the page itself.

## Command

`tools/ane/query_hathitrust.py`; tests in `tests/ane/test_query_hathitrust.py`.

```bash
python3 tools/ane/query_hathitrust.py oclc:2422204                          # list the book's volumes and rights
python3 tools/ane/query_hathitrust.py mdp.39015008689583 'w?ldn' --offset 14  # pages holding a token (regex, any case)
python3 tools/ane/query_hathitrust.py mdp.39015008689583 a-ra-ad-ni --exact --offset 14 --json
python3 tools/ane/query_hathitrust.py mdp.39015008689583 awldn --ef-file FILE.json.bz2   # a file on disk; no request
```

- **Limits:** one catalog call per `oclc:` lookup and one features-file fetch per volume. The file is cached under `$XDG_CACHE_HOME/kaphtor/hathitrust-ef/` (else `~/.cache/kaphtor/hathitrust-ef/`), and `--refresh` fetches it again.
- **Refusals:** the client will not search a volume without a pattern, run with `--delay` under 1 second, or take a volume id it cannot parse or an `oclc:` that is not a number.
- **Output:** `--json` records the file's path, sha256 and origin, the volume's rights, and the CC BY citation.

## How it works

1. **Volume id (htid) and rights.** The catalog API is not behind the challenge:
   `https://catalog.hathitrust.org/api/volumes/brief/oclc/<OCLC>.json`. Its `items` give each `htid` with `rightsCode` and `usRightsString`.
2. **The EF file.** Split the htid at its first dot into library and volume (`mdp`, `39015008689583`). Put the volume in pairtree clean form, `:` → `+`, `/` → `=`, `.` → `,`. The folder is every third character of the clean volume id:
   `https://data.analytics.hathitrust.org/features-2020.03/<lib>/<clean[::3]>/<lib>.<clean>.json.bz2`.
   For example, `mdp.39015008689583` → `mdp/31088/…`, `nc01.ark:/13960/t2v41mn4r` → `nc01/a+30214/nc01.ark+=13960=t2v41mn4r.json.bz2`, and `miun.adx6300.0001.001` → `miun/a600,1/miun.adx6300,0001,001.json.bz2`.
3. **Pages.** `features.pages[]` holds one object per scan page:
   - `seq` is the scan page, not the printed page.
   - `body.tokenPosCount` maps each token to `{POS: count}`.
   - `header` and `footer` are `null` on many scans.
   - `body` itself can be `null` on blank pages.
   The client sums the counts across the parts of speech and across header, body and footer.
4. **Printed pages.** Printed page = `seq` − offset. Calibrate the offset with a page cited elsewhere. Check it against two or more citations, since the offset can change across plates or unnumbered pages.

## Reading the tokens

- **The OCR drops diacritics and special letters.** Ugaritic *ảwldn* is the token `awldn`, and *bʕldn* is `bldn` or `b'ldn`. Search on the plain consonants, as a regex.
- **Hyphenated syllabic spellings stay whole** (`a-ra-ad-ni`). Line-end hyphenation can split a word into two tokens.
- **Tokens are counted, not ordered.** EF cannot show a phrase, only that its words share a page.
- **Back matter answers too.** A name discussed in the body also shows up in the book's lists and addenda. Read the page's other tokens to tell the two apart.

## Example: Gröndahl, *Die Personennamen der Texte aus Ugarit*

Studia Pohl 1, Rome 1967, v + 435 pp.: htid `mdp.39015008689583` (Michigan; `ic`, search-only; 456 scan pages). Offset 14, calibrated against DULAT's citations of the book:

| Token | Scan pages | Printed pages | Cited as |
|---|---|---|---|
| `awldn` | 112, 137 | 98, 123 | DULAT 128: *ảwldn* "Gröndahl PTU 98, 123" |
| `bldn`, `b'ldn` | 34, 130, 137 | 20, 116, 123 | DULAT 207: *bʕldn* "Gröndahl PTU 20, 116, 123" |
| `a-ra-ad-ni` | 318, 336 | 304, 322 | Berger, WO 5 (1969–1970) 279: a-ra-ad-ni among the unexplained names, "S. 304 ff." |

The hits on scan pages 375–437 fall in the back matter: lists of names by text and the addenda.

For this book, Google Books has metadata only, and the Internet Archive has neither a scan nor a copy to borrow. The pages can be read only in a library copy.
