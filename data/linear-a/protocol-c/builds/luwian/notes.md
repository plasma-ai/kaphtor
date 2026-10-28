---
name: data/linear-a/protocol-c/builds/luwian/notes
title: "Transcription notes"
desc: "The luwian builder's notes on the units, forms, segmentations and doubts, as written."
tags: [data, linear-a, protocol-c]
license: CC BY 4.0
created: 2026-10-29T19:48:19Z
updated: 2026-10-29T19:48:19Z
---

# Transcription notes

All five listed tables were read in full and checked against the PDF on printed pages 12, 13, 15, 16 and 19. The PDF and supplied text agree on their forms; the PDF supplies the merged-cell boundaries. No form was illegible. The title page spells the author's first name “Ilya”; the manuscript date comes from units.md.

## Scope and difficult cases

- Table 2's singular-neuter and plural-neuter cells each span nominative and accusative. Their functions include both cases. Genitive and ablative-instrumental cells span both numbers and genders; dative-locative cells span genders.
- Table 2 prints `-Ø(+sa/za)` as one expression. Two nonzero realizations retain that exact expression as `form`, with segments for `sa` and `za`. The slash separates alternatives and the plus marks attachment; neither is a segment. The zero-only option is excluded. Likewise `-n(+za)` yields `n` and `nza`, retaining the printed expression. These are ending expressions, not newly supplied spellings such as a hyphenated standalone extension absent from that table.
- Table 3 mostly supplies complete declined words, not separately written bound endings. The complete words were not entered, and no endings were inferred by subtracting presumed stems. Its explicit parenthesized, hyphen-delimited component `(-za)` in `parnan(-za)` is the sole entry from this unit; parentheses are retained. This is a difficult scope boundary: the entry transcribes the visibly delimited bound component rather than the entire free word. The absence of this optional component is not a zero-ending entry. The cell spans nominative and accusative singular neuter. Its extension shares a morpheme ID with the extension alternatives in Table 2.
- For audit, the complete Table 3 cells read: singular-common nominative `alis, massanis`; accusative `alin, arin`; singular-neuter nominative/accusative `tanimanza, parnan(-za)`; plural-common nominative `taniminzi, massaninzi`; accusative `alinza, arinzi`; plural-neuter nominative/accusative `ala, parna`; genitive `immarassa, massanassi`; singular dative-locative `ali, parni, ari`; plural dative-locative `tanimanza, parnanza, massananza`; ablative-instrumental `aladi, tanimadi, aradi`; singular-common vocative `alawaimi`; plural-common vocative `annarumminzi`. This list documents the reading, not additional inventory entries.
- Table 5's bound nominative and reflexive pronouns are included under `pronominal`, consistent with the brief's explicit inclusion of forms called clitic. Repeated identical forms are entered once with all their table functions. Thus `=ada` includes singular neuter and plural nominative/accusative, and `=du` includes second-singular accusative/dative and third-singular dative. Reflexive entries remain distinct from nonreflexive entries even where their segments coincide.
- Table 7 really prints `(s)sa` without a leading hyphen. No hyphen has been supplied. Commas that separate alternatives or end a table cell are punctuation, not part of a form. A cell containing `?` supplies no form. Finite endings remain in `s_case_person`, including the imperative and Middle endings.
- Each verbal paradigm cell's alternative endings share a morpheme ID. The separately printed `-ha` and the short realization of `-(h)ha` are both retained even though their segments coincide. Conversely, identical spellings in different grammatical cells need not identify one morpheme.
- Table 8 labels `=wa` and `=gwa` simply as particles; it does not state whether they are allomorphs. They have separate morpheme IDs rather than an inferred relationship. It names the three pronominal ranks without printing pronoun forms, so those ranks add no duplicate entries from Table 5. No forms from adjacent prose were imported.

## Segmentation and ordering limitations

- All parenthesized material in bound forms is expanded into present/absent realizations, keeping the same printed `form`. No absent realization with an empty segment list is entered.
- Capital `T` in Table 7 is retained as one segment. The table's accompanying explanation defines it as a cover symbol for fortis `t(t)` and lenis `d` where the distribution is not assured; it is not expanded into inferred alternatives.
- Doubled consonant spellings `tt`, `hh`, `ss`, `mm`, `nn` and `ll` are preserved as single consonant units in `segments`; no length mark or different consonant symbol has been invented. Their precise phonemic treatment is not fully established by the listed tables. In particular, expansion of `-(t)ti`, `-(h)ha` and `(s)sa` retains the contrast between single and doubled spelling without claiming that every orthographic doubling establishes phonemic length. This segmentation remains uncertain.
- In `=gwa`, `g` and `w` are provisionally separate segments. Table 8 does not establish whether `gw` is a consonant cluster or a single labialized consonant; no phonemic resolution is asserted. Other consonant letters, including `z`, are retained in the printed notation.
- Table 8 requires `s_enclitic_inner` before `s_pronoun` and `s_enclitic` after it. The cited order is recorded in `class_order.basis`; the rest of the template is unchanged. The schema cannot distinguish ranks 1 and 2 within `s_enclitic_inner`, or ranks 3, 4 and 5 within `s_pronoun`. The six ranks are therefore documented in the basis statement, with the conjunction/particle and locative ranks also noted on their entries.

## Zero endings, empty cells, and table differences

- Table 2 zero endings excluded: singular-neuter nominative/accusative `-Ø` within `-Ø(+sa/za)` when no extension is chosen; plural-neuter nominative/accusative `-Ø`; singular dative-locative `-Ø`; singular-common vocative `-Ø`.
- Table 2 singular-neuter and plural-neuter vocatives are `?`. The plural-common vocative cell is `= nom.`, a reference rather than a printed bound form; no new spelling is inferred from it.
- Table 7 zero ending excluded: active imperative second singular `-Ø`. The question marks in the other cells mark missing forms, not zero endings. Table 5's `n.a.` cells likewise supply no form.
- Table 3's plural-common accusative `alinza` is not a straightforward match to Table 2's printed accusative alternatives `-nz, -nzi`; no additional ending has been inferred from the unsegmented word. Table 3's singular-common vocative `alawaimi` also does not transparently display either of Table 2's `-Ø, -s` without a stem analysis. These are unresolved differences in presentation, not corrected readings.
- Table 5 prints the plural reflexives `=anza` and `=mmanza` without optional parentheses, whereas its nonreflexive oblique entries have `=anz(a)` and `=mmanz(a)`. The distinction is preserved; optional final vowels were not supplied for the reflexives.

Every listed unit contributes at least one entry under the explicitly delimited-component treatment of Table 3, so `units_without_entries` is empty.
