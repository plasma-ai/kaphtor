---
name: docs/human-review
title: Human review
desc: The kinds of artifact that serve a person making the final call on a Linear A reading, what question each settles, and the two review pages with their templates, worked examples and screenshots.
tags: [docs, linear-a, review]
authors: "di Mino"
created: 2026-11-04T02:00:41Z
updated: 2026-11-04T02:00:41Z
---

# Human review

[[docs/_index|..]]

[[docs/human-review/break-check|break-check]]: The break-check page: SigLA's drawing with the word boxed, the measured space at each edge and SigLA's division there, the full SigLA record, and the rulings recorded on the page; how to build it and a worked example.

[[docs/human-review/break-check-21f-ja-du-ht84.png|break-check-21f-ja-du-ht84.png]]: Screenshot of the break-check card for *21F-JA-DU on HT 84; CC BY-NC-SA 4.0 (SigLA).

[[docs/human-review/break-check-a-ru-ra-ht11a.png|break-check-a-ru-ra-ht11a.png]]: Screenshot of the break-check card for A-RU-RA on HT 11a; CC BY-NC-SA 4.0 (SigLA).

[[docs/human-review/break-check-progress.png|break-check-progress.png]]: Screenshot of the break-check example's progress panel and hold-list index; CC BY-NC-SA 4.0 (SigLA).

[[docs/human-review/break-check.spec.json|break-check.spec.json]]: The break-check example's spec: the hold list's words and corpus keys, one stretch SigLA reads otherwise, and the rulings.

[[docs/human-review/word-in-context|word-in-context]]: The word-in-context page: a word in every inscription that carries it, the corpus lines as glyphs over transliteration, SigLA's reading and drawing, and each card's tag; how to build it and a worked example.

[[docs/human-review/word-in-context-ru-di-ht141.png|word-in-context-ru-di-ht141.png]]: Screenshot of the word-in-context card for RU-DI on HT 141, SigLA's reading, drawing and crops; CC BY-NC-SA 4.0 (SigLA).

[[docs/human-review/word-in-context-su-du-ht42-59.png|word-in-context-su-du-ht42-59.png]]: Screenshot of the word-in-context card for SU-DU on HT 42+59, the corpus lines with the word lit.

[[docs/human-review/word-in-context.spec.json|word-in-context.spec.json]]: The word-in-context example's spec: nine words and the tags set on six cards.

***

A machine can match signs and count gaps; whether a mark at a broken corner is a sign, or a word runs on into a
lost line, is a person's call on the evidence. The artifacts below are the ones that made that call quick and
recorded it where the next reviewer sees it.

| Artifact | Question it settles | How |
| --- | --- | --- |
| Break-check page | Does the word end where the record says? Is a sign lost before or after it? | `tools/linear_a/review/break_check.py` |
| Word-in-context page | How does the word stand in every inscription that carries it: whole, broken, inside a longer word? | `tools/linear_a/review/word_in_context.py` |
| Card-per-entry walkthrough | One decision per lexicon or onomasticon entry, with its evidence and the proposed call on the card | a page built for the review at hand |
| Edition crops at 400 dpi | What the editor printed: the transcription, the copie tabulaire, the apparatus note and its dotted candidates | the edition page rendered at 400 dpi and cropped |
| Blind second reader | Does an independent reader see the same strokes? | a second model or person reads the same crops before seeing the first reading, then agrees or disagrees point by point |
| Rulings ledger and checker | What was decided, and does the data still agree after the change? | `rulings` in the page's spec; `tools/linear_a/validation/check_unread_words.py` after every edit |

What made the pages work:

- **SigLA's geometry, not a picture of it.** The sign boxes come from `data/linear-a/sigla/database.js`, so the
  space at each edge of a word is measured in that document's sign widths, beside SigLA's own word division.
- **Every witness on one card.** Drawing, crops, Unicode line, corpus text, the full SigLA record and, where held,
  the edition photograph.
- **The record against SigLA.** A card says where SigLA reads a stretch otherwise, where a face holds only part of
  a word, and where SigLA does not hold the document.
- **Rulings on the page.** Badges on the cards and a progress panel linking each ruling to its cards.
- **The page writes no data.** Each ruling is applied to the data by hand, and the checker runs after it.

The screenshots show SigLA's drawings and sign crops (https://sigla.phis.me), © 2020– Ester Salgarella and Simon
Castellan, CC BY-NC-SA 4.0; the pages' own text and layout are CC BY 4.0.
