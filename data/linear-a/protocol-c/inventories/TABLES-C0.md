---
name: data/linear-a/protocol-c/inventories/TABLES-C0
title: "TABLES.md"
desc: "The signed list of grammar units each blind builder of Protocol C transcribes: the unit rule, the six arms with their grammars and unit counts, and the page checks."
tags: [data, linear-a, protocol-c]
license: CC BY 4.0
authors: "di Mino"
status: "SIGNED 2026-10-29 (given in session, recorded by instruction); hashed at C1 before any build"
protocol: "../../PROTOCOL-C-DRAFT.md §5.1–5.3, §16 A1"
created: 2026-10-29T19:48:19Z
updated: 2026-10-29T19:48:19Z
---

# TABLES.md

Each arm's builder transcribes every realization in the units listed in its file under `tables/`, and nothing else.
The per-arm files are part of this document and are hashed with it.

## Unit rule (§16 A1)

A unit is (a) a numbered or boxed table, (b) an itemised list of forms, or (c) a section whose own heading names a
§5.2 category, in the arm's named grammar. Forms named only in running prose under a heading that names no category
stay out. Free pronouns (independent, demonstrative, interrogative) stay out; a form the grammar itself calls bound
enters. Exercises and answer keys are never units. Units were chosen by category alone, from each grammar's table
of contents and tables, before any Linear A form was rendered and with no comparison against Linear A.

## Arms

| Arm | Grammar (held copy) | File | Units | Notes |
|---|---|---|---|---|
| `cs` | Huehnergard, "Proto-Semitic," *The Semitic Languages*, 2nd ed. (2019), ch. 3; innovations: Huehnergard and Rubin, "Phyla and Waves" (2011), and Huehnergard, "Features of Central Semitic" (2005) | `tables/cs.md` | 24 | Tables 3.5–3.9, §§3.1.1 (bound forms), 3.3.2.1–3.3.2.4, 3.5.3–3.5.5, 3.6, 3.7, 3.10; innovations: H&R §§3, 4, 8.1, 8.2 and Huehnergard 2005 (Mistral OCR) §§II.1, II.10, which restate *yaqtulu* and Barth-Ginsberg and add no form. Its other confident innovations are free words; its hedged features stay out |
| `yd` | di Mino, *Ya Diktu* (commit d9a3f93, per amendment A3) | `tables/yd.md` | 65 rows, 36 morphemes | every bound morpheme the grammar states, §§4–11 and Appendix B; no affix written with a contested value (contested values sit in host words) |
| `luwian` | Yakubovich, *The Luwian Language* (2015 ms.) | `tables/luwian.md` | 5 | Tables 2, 3, 5, 7, 8. The participle and infinitive are prose under "6.5 Verb" and stay out |
| `hurrian` | Wegner, *Einführung in die hurritische Sprache* (2000) (Mistral OCR) | `tables/hurrian.md` | 32 | Tabelle 3–13, lists, 10 headed sections (§§11–15 moods, 16 Wunschformen, 17 Der Infinitiv, Postpositionen und Partikeln, the particle sections); exercises F.1–F.4 out |
| `egyptian` | Allen, *Middle Egyptian*, 3rd ed. (2014) | `tables/egyptian.md` | 52 | uncaptioned tables cited by section and page anchor; §8.2, §15.7 lists; ky, ntj, jwtj and numerals out (free words) |
| `greek` | Bartoněk, *Handbuch des mykenischen Griechisch* (2003) (Mistral OCR) | `tables/greek.md` | 25 + spelling rules | declension sections and tables, VII.E.4.b Personalendungen (p. 337), VII.E.4.c (p. 338); verb attestation lists out; -qe, -de the only enclitics |

Linear B spelling rules for §5.5: Bartoněk §V.A.D, pp. 106–111 (Abb. 38, p. 112), in `tables/greek.md`.

## Checks made on the page numbers

Read off the held copy for a sample in each arm: Huehnergard Table 3.7 (p. 60, pdf 17), §3.5.4 (p. 63, pdf 20),
§3.5.5 (p. 64, pdf 21); *Ya Diktu* §4.1 p. 4, §4.2 p. 6, §4.3 p. 8 (mimation), §5.2 p. 11 (enclitic -ma); Allen §5.3
table at `html_page_60`; Bartoněk "b) Personalendungen" on p. 337 (p. 338 follows). Yakubovich's eight numbered
tables were each confirmed in the text layer.

## Open before C1

1. Done: Huehnergard 2005 OCR (25 pages, Mistral batch 293b08ce, collected 2026-10-29); rows added to `tables/cs.md`.
2. The per-arm files carry absolute local paths; they are cut (ledgered) when the protocol is frozen into kaphtor.
3. Inventory format: `schema.json` (one entry per realization; slot and class order per amendment A2,
   adopted 2026-10-29 under di Mino's delegation). A Luwian pilot build (`../builds/pilot-luwian-2026-10-29/`) tested the format; it is not
   the C1 build.

Signed: di Mino    Date: 2026-10-29 (given in session, recorded by instruction)
