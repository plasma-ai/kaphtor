# tools/linear_a/review

The human-review pages: each puts one question about a Linear A word in front of a person, with every witness
needed to answer it, and records the ruling on the page. What each page shows and its worked example:
`docs/human-review/`.

| File | Purpose |
|---|---|
| `review_core.py` | The shared parts: SigLA's sign boxes decoded from `data/linear-a/sigla/database.js`, the word found on SigLA's faces, the zoomed and whole drawing, the sign strip with measured gaps, SigLA's reading and full record, the edition images, ruling badges and the progress panel |
| `break_check.py` | The break-check page: each attestation's edges against SigLA's drawing and division; tabs from a spec, or from the archived words with unread records (`archive_unread`, needs `lexicon_archive.json`) |
| `word_in_context.py` | The word-in-context page: a word in every inscription that carries it, the corpus lines as glyphs over transliteration, the word lit, each card tagged |
| `word_in_context.html` | The word-in-context page's shell and styles |

Both read a JSON spec and the data read-only (`corpus.json`, `lexicon.json`, `unread_words.json`, `sigla_db.json`,
`sigla-sign-map.json`, `sigla/database.js`), and write the page and its images to `CACHE/review/{spec name}/` or
`--out`, never into the repository. `--fetch` fetches SigLA's drawings at one request a second; `--sigla-images`,
`--crops` and `--edition-images` name folders already holding drawings, sign crops and edition photographs.
