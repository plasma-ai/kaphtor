---
name: data/linear-a/sign_attestations
title: Sign attestations on SigLA
desc: For each Linear A sign SigLA traces, up to eight of its tracings by SigLA document and sign position, with the site, the use, the distance from the sign's standard form and the rule that orders them.
tags: [data, linear-a, signs, sigla]
license: CC BY-NC-SA 4.0 AND CC BY 4.0
created: 2026-11-17T03:58:10Z
updated: 2026-11-17T03:58:10Z
---

`sign_attestations.json` points from a sign to places where [SigLA](https://sigla.phis.me) draws it. It holds
`schema_version`, `description`, `compiled_by`, `source`, `rule`, `per_sign` and `signs`, an object keyed by the
sign's code as [sign-registry.json](sign-registry.json) gives it in `ab_number` (`AB81`, `A301`). A code SigLA
has and the registry lacks (`A411b`, `AB43`) keeps SigLA's spelling. The file holds no image: a document
and a position name a tracing on SigLA's page for that document.

| Field | Content |
| --- | --- |
| `tracings` | how many tracings of the sign SigLA reads with certainty, erased signs left out |
| `site` | the home site: where the sign is most often traced unworn as a syllable, or in any use where it is never a syllable |
| `attestations` | up to eight tracings, in the order of the rule below |

Each attestation:

| Field | Content |
| --- | --- |
| `document` | SigLA's name for the document (`HT 13`, `HT Wa 1029α`), the key of [sigla_db.json](sigla_db.json) |
| `position` | the sign's position in that document, as SigLA numbers it |
| `site` | the document's site, as SigLA names it |
| `use` | SigLA's role for the sign where it is not a syllable (`logogram`, `fraction`, `transaction sign`), with SigLA's question mark where it has one |
| `distance` | the distance of the tracing from the sign's standard form; absent where none was measured: the sign has no character in Unicode, or SigLA's code for it is not the registry's |
| `dots` | the number of damage dots SigLA draws on the tracing; absent where it draws none |

## The rule

Of the tracings SigLA reads with certainty, erased signs left out, the unworn ones of the home site come first, those
used as a syllable before other uses, by rising distance, or by document where no distance was measured. Unworn tracings of other sites follow in the same order,
then worn ones. A tracing is worn where SigLA draws damage dots on it. The first eight are kept.

Distance is a chamfer distance between two one-pixel skeletons scaled into the same 64-pixel box with their aspect
kept: the tracing without its damage dots, and the sign as the font Noto Sans Linear A draws it. It orders the
tracings of one sign and compares nothing across signs. One site's tracings come first because hands differ by
site, and a cursive hand can stand nearer the font's form than a careful one does.

The distances and the dot counts are measured on SigLA's images, which this repository does not hold. The file is
generated from them and from `sigla_db.json`; it is not edited by hand.
