---
name: data/linear-a/protocol-c/builds/egyptian/notes
title: "Inventory notes"
desc: "The egyptian builder's notes on the units, forms, segmentations and doubts, as written."
tags: [data, linear-a, protocol-c]
license: CC BY 4.0
created: 2026-10-29T19:48:19Z
updated: 2026-10-29T19:48:19Z
---

# Inventory notes

Source: James P. Allen, *Middle Egyptian: An Introduction to the Language and Culture of Hieroglyphs*, third edition, 2014, supplied Markdown conversion. All 52 rows in `units.md` were read, including the HTML tables and both complete preposition sections. No other source was used.

## Scope and transcription decisions

- A row labelled **table** selects that table, including explanatory text inside its cells. Surrounding prose was read to identify its morphology and interpret its terminology; it did not independently supply extra realizations. The two listed **lists** and the listed **headed section** were read in full, including their examples. Affixes in those examples are eligible even when the surrounding word is not itself a clitic.
- The title/caption column, including its md line number, is used verbatim as the unit label. This distinguishes repeated tables in the same section. Page citations follow anchors at the actual forms, not automatically the earlier anchor recorded for the start of a table.
- This is an inventory of bound realizations, not whole inflected words. Where a table supplies whole words, the entry copies the identifiable affix substring, including its printed boundary dot or hyphen if present. No hyphen, dot, or reconstruction asterisk has been invented. Markdown emphasis and HTML markup are not part of a form. Underlined t and d are represented as ṯ and ḏ; these encode the source's typographic underlines rather than adopting readings from the unit descriptions. En dashes in the explicitly isolated endings –wj, –tj, –j and –y are retained.
- Repeated attestations of the same morpheme, printed form and segmentation share one entry. A primary source is attached to that entry; the coverage table below records the other eligible units. Distinct printed boundary notation is retained as a distinct realization sharing the same morpheme ID. Different grammatical morphemes that happen to have the same spelling remain distinct.
- Parenthesized segments have both nonempty realizations. If removal of the parenthesis would leave no segment, only the nonempty realization enters the JSON; the zero alternative is recorded below. Optional radicals in lexical roots are not converted into optional affixes.
- Segments use the source's transliteration symbols, without restoring unprinted vowels. For example, `.j` remains `["j"]`; the vowel `i`, explicitly identified in the 1s cell of §5.3, is a separate realization of that morpheme. This preserves the distinction between the printed transliteration and the explicitly stated pronunciation.
- Nominal gender and number endings shared by nouns, adjectives, relative forms and participles are not counted again for each construction. Participial stem endings enter `s_stem`; finite stative person endings enter `s_case_person`. Ordinary suffix pronouns enter `s_pronoun`, including their tabulated use as subjects and agreement markers, because the grammar explicitly identifies them as the regular suffix pronouns. No separate finite-person series is invented from them.
- The prefix `s` is extracted only from the rows explicitly labelled causative. A lexical initial s elsewhere is not treated as a causative prefix. The rare `j.` prefixes are separately attested in the finite-form and active-participle tables.

## Bound and free forms

§5.4 explicitly says that dependent pronouns “were separate words.” It does not call the series enclitic. Consequently the dependent columns of §§5.4 and 5.6 and the dependent subjects in §§7.3 and 7.14 do not license a general bound-pronoun series. This differs from the parenthetical description in `units.md`. The independent column of §5.6 and the independent pronouns in §7.14 are excluded. The gender endings in the first-person nominal predicates of §7.14 are included.

§7.8 is a local exception: the text introducing the listed table says that n(j) and a dependent pronoun were pronounced together and often written as one word. The readable pronoun pieces in wj, nw(j), nsw, ns(j), n(j)-w(j), n(j)-sw and n(j)-s(j) are included for this construction only. The nisbe n(j) itself is not classified as a bound preposition. The whole reconstructions *níwa, *nísu and *nísi do not print internal boundaries: additional vocalized pronoun allomorphs have not been guessed from them.

§10.5 calls its complete forms a new kind of independent pronoun. The complete tw-forms and standalone third-person forms are excluded. Its first- and second-person suffix components are included because the same introduction explicitly analyses these as tw plus suffix pronouns. The optional 2fs suffix is copied as `.(t)`.

§8.2 does not call its ordinary prepositions bound prefixes. Taking a suffix pronoun does not by itself turn the host preposition into a prefix. Accordingly no general preposition-prefix paradigm is inferred. The hyphenated prepositional compounds jmjtw-nj and r-jmjtw are also not automatically treated as an affix paradigm. The bound noun endings and suffix pronouns actually present in this complete list's examples are included. Free adverbial forms and optional mm(j) are not entered. §8.3 describes combinations of several words and supplies no independently identifiable eligible bound form.

§15.7 explicitly calls its items enclitic particles. The brief's explicit inclusion of forms the grammar calls enclitic is applied even though the examples write them separately from their preceding hosts. This is a scope tension with the protocol's “one word” wording. The complete r.f/jr.f/r.s/r.k expressions are included because the grammar itself identifies the prepositional phrase as the enclitic; the section also supplies the ordinary pronominal pieces. No unattested r + pronoun combinations are generated.

## Missing images and uncertain segmentations

The working directory contains the Markdown book but none of its referenced image files. Image-only hieroglyphic spellings therefore cannot be checked, and image-only transliteration characters cannot safely be restored. In particular, `images/00055.gif`, `images/00085.gif`, `images/00056.gif` and some less frequent files occur inside transliterations. The unit-list approximations do not replace these missing source glyphs.

- **§19.9, pp.295–296:** the third biliteral suffix is printed as `.k` followed by the missing `00055.gif`. The entire suffix is unreadable, so it is not entered as `.k`, as an invented capital cover symbol, or with a replacement character. The fully readable `.jn`, `.ḫr`, pronominal suffixes, and `.tw`/`.t(w)` examples remain usable.
- **§15.7 item 1, p.217:** the particle heading is an image and its occurrences use `00055.gif`. No readable form can be supplied. Items 7 and 8 also have additional image-only alternative spellings; the readable ms/msw and ḥm are transcribed, but no extra alternative is inferred from those images. The unreadable emphasis particle is also part of some combined particle expressions in item 1.
- **§13.3 second table, p.182:** the two reconstructed forms contain both `V` and missing transliteration images. They are stems, not printed suffix pronouns. The table yields no bound entry. `V` is the source's unspecified-vowel cover symbol; it would remain one segment if an eligible affix containing it were available. No eligible affix in this inventory contains a cover symbol. The unit description's approximated reconstructed strings do not reproduce this table reliably.
- **§16.2 reconstructed paradigm, p.229:** ku, ta, ti, nu, tunu and tina are extracted as suffix substrings by alignment with the immediately preceding stative-suffix table. The complete printed reconstructed forms, including their asterisks, are retained in the relevant entry notes. No stress change in the stem creates an extra suffix realization. The two 2mpl words have the same tunu suffix; the two 2fpl words have the same tina suffix. The final vowels in *ḥátpa and *ḥátpu could be analysed as a and u endings, but the table does not print their boundary from the stem. This vowel-only segmentation is left unresolved rather than entered as certain. The accompanying whole-form survival is not a bound affix entry.
- **§15.1 second table, p.209:** the source labels the four whole forms Coptic and renders them as amoy, amvi, amh and amhi. Final i in the two plural forms is included because the immediately following paragraph explicitly identifies it as the plural ending. The table does not give a separate masculine or feminine affix, and no phonemic analysis of oy, v or h is guessed. This entry is restricted to the stage and paradigm explicitly identified by the table; it is not extrapolated to the other imperative table.
- **§24.1 ending table, p.403:** the left-hand ending cells are images. The examples nevertheless provide readable j in ḏddj, y in jryt, and w in jtw/jrrw, with the stem and gender/number conditions in adjacent cells. Those readable substrings are included; the unavailable image cells have not been assigned invented transliterations.
- Internal gemination, root allomorphs, and final weak radicals are not automatically additional affixes. Thus final y explicitly identified as a radical or as the consonantal realization of a stem vowel in §§18.2 and 19.13 is not entered as an independent derived-stem suffix. Likewise the root-changing n discussed for the infinitive of “see” is not an added grammatical suffix.
- The optional j in sr(j) “official” (§15.7) is not identified there as a particular grammatical ending; it is not automatically assigned to the nisbe series. The final w in the active-participle example translated “who saw” (§23.5) is also ambiguous between stem spelling and number without a gender/number label. No extra singular-participle w morpheme is invented from it. The unequivocal plural-w examples are included.
- In §19.9 `.tw` is used in forms translated with the impersonal subject “one,” whereas `.t(w)` occurs in the forms translated as passive. These are filed by their stated function: finite impersonal subject under `s_case_person`, valence marking under `s_stem`. The schema has no construction-specific ordering mechanism for repeated stem slots.

## Zero and unwritten endings

No entry has empty segments, and no zero marker is entered.

- The bare masculine singular ROOT in §4.8, bare primary/secondary masculine singular adjectives in §6.2, and the corresponding bare masculine singular relative and participial forms have no ending to enter.
- The root/base forms without an ending in the infinitive, negatival-complement and imperative tables do not acquire an invented ending. A visibly omitted weak ending is not restored unless the table itself prints it parenthetically.
- `.(t)` in §10.5 has the realizations t and zero; only t is entered.
- `.(tj)` in the 2s and 3fs cells of §16.2 has the realizations tj and zero; only tj is entered. The explicitly rejected spelling `.kwj` in the 1s cell is not an attested realization and is excluded.
- `.(w)` in §§16.3 and 19.18 has the realizations w and zero; only w is entered. `.t(j)` and `.k(w)` have two nonzero realizations each, both entered.
- `.(j)` in §17.2 has j and zero; only j is entered. The examples without a written 1s pronoun elsewhere do not license a new zero entry.
- `.t(w)` in §19.9 and t(j)/wt(j) in §23.13 retain both nonzero expansions. Parenthesized weak radicals belonging to whole lexical roots, such as those in some nouns and verbs, are not affix variants.
- Unwritten third-person stative suffixes, and participial stem endings whose identity the grammar itself says cannot be determined, are not silently supplied.

## Source discrepancies and limits of the slot template

- §4.6 prints ḥftwt in one feminine plural example, while the surrounding noun paradigms use ḫft-. This root-level difference is preserved as an unresolved conversion/source discrepancy; the readable ending wt is unaffected.
- The feminine dual is presented as j added to the feminine singular in §§4.7 and 4.8, but the small spelling table in §4.7 labels the complete ending –tj. Both presentations are retained under one morpheme ID, with the different attachment bases stated. This is not permission to add an extra feminine t to an already feminine singular noun.
- The feminine plural participle and relative-form examples in §§22.12, 22.13, 23.2 and 24.1 have t on the verb/adjective and wt on the head noun. Some descriptions in `units.md` could suggest wt on the participle itself. The entries follow the actual tables; no distinct wt participle ending is invented.
- The §5.4 dependent table labels st as neutral in gender and number; §5.6 places st alongside the feminine singular and third-person plural forms. Both are excluded as separate dependent words, and their different tabular presentation is not used to invent extra bound forms.
- §16.2's 3pl head form is .wj, with .y also listed, but its example šn.w supplies .w. All three printed forms are retained. Older forms inside the table's explanatory cells are also retained, with their restrictions.
- The §13.20 table labels ḥnmnmyt as 5-lit., although its yt resembles the ending the preceding explanation associates with final-weak verbs. The table's yt is retained without changing its root-class label.
- The caus. 4ae-inf. row in §19.9 prints nḏr.ḫr.k without an initial s. No s is inserted into that example; the causative prefix is independently readable in other causative rows.
- Some printed pages differ from the table-start anchor recorded in `units.md`: §5.3 crosses pp.60–61; §5.4 crosses pp.61–62; the §5.7 examples are on p.64; the second §6.2 table is on p.76; the second §13.3 table is on p.182; §16.2 crosses pp.228–229; §16.3 crosses pp.229–230; §19.9 crosses pp.295–296; and the first §23.13 table's forms are on p.395. The entries cite the page of the actual primary attestation.
- The default slot template is retained, with an empty `basis`, because the source supplies no single alternative global order that can express all these constructions. There is a real limitation: the relative forms in §22.12 put gender/number on the stem before .n (mrt.n.f, mrw.n.f, p.359), whereas the participle tables put stem endings before gender/number (jrrjw/jrryw in §23.4, p.383; jryw/jryt in §24.1, p.403). These imply opposite orders for `s_stem` and `s_gender_number`, since A2 places .n and participial stem endings in the same slot. Swapping those two global slots would solve one construction and break the other. This unresolved representational conflict is recorded rather than concealed by an invented fused affix or a claim that the default reproduces every word.
- The ordinary suffix pronouns are placed after the relevant endings, as stated in §5.3 and illustrated in §§5.7, 17.2 and 23.13. The stative suffixes are the finite person class. No `s_enclitic_inner` slot is licensed by these units.

Forms found only in prose outside a listed table remain out even if the section heading is relevant in the broader protocol. Examples include the separate paragraph of dual suffix pronouns after §5.3, dual-noun .fj/.sj in §5.7 (these shapes are independently included from the listed §23.13 table), the –wt complementary-infinitive description not exemplified in its table, the plural imperative –y examples after the §15.1 tables, –tw after the §19.13 table, and the extra relative-form endings discussed after the §22.13 table. This follows the brief's explicit restriction to the listed units rather than expanding each selected table into its entire section.

## Unit coverage

Each row identifies the listed unit by its source line. Repeated attestations point to existing entries; they do not multiply a realization. The complete verbatim unit labels are in `units_read`.

| Section | Unit md line | Entry IDs or reason |
|---|---:|---|
| §4.4 | 1299 | egyptian_001, egyptian_002, egyptian_002b |
| §4.5 | 1321 | egyptian_001, egyptian_002, egyptian_002b, egyptian_003, egyptian_004 |
| §4.6 | 1339 | egyptian_001, egyptian_002, egyptian_002b, egyptian_003, egyptian_004 |
| §4.7 | 1359 | egyptian_001, egyptian_002, egyptian_002b, egyptian_005, egyptian_006 |
| §4.7 | 1373 | egyptian_005b, egyptian_006b |
| §4.7 | 1383 | egyptian_001, egyptian_002, egyptian_002b, egyptian_005, egyptian_006 |
| §4.8 | 1401 | egyptian_001, egyptian_002, egyptian_002b, egyptian_003, egyptian_004, egyptian_005, egyptian_006 |
| §6.2 | 2177 | egyptian_007 |
| §6.2 | 2187 | egyptian_007, egyptian_003 |
| §6.2 | 2197 | egyptian_001 |
| §6.2 | 2209 | egyptian_003, egyptian_001, egyptian_004 |
| §5.3 | 1767 | egyptian_008, egyptian_009, egyptian_010, egyptian_010b, egyptian_011, egyptian_012, egyptian_013, egyptian_014, egyptian_014b, egyptian_015, egyptian_008b, egyptian_015b |
| §5.4 | 1790 | The dependent pronouns are explicitly called separate words in §5.4; the table does not call them bound or enclitic. No suffix is extracted from these complete pronouns. |
| §5.6 | 1851 | egyptian_008, egyptian_009, egyptian_010, egyptian_010b, egyptian_011, egyptian_012, egyptian_013, egyptian_014, egyptian_014b, egyptian_015 |
| §5.7 | 1875 | egyptian_008, egyptian_009, egyptian_010, egyptian_010b, egyptian_011, egyptian_012, egyptian_013, egyptian_014, egyptian_014b, egyptian_015 |
| §7.3 | 2480 | Only the uninflected predicate nfr and separate dependent-pronoun subjects occur in this table. No bound realization is printed. |
| §7.8 | 2576 | egyptian_016, egyptian_016b, egyptian_016c, egyptian_016d, egyptian_016e, egyptian_017, egyptian_017b, egyptian_018, egyptian_018b, egyptian_018c, egyptian_018d, egyptian_018e |
| §7.14 | 2809 | egyptian_001, egyptian_003 |
| §8.4 | 3157 | egyptian_008, egyptian_009, egyptian_010, egyptian_011, egyptian_012, egyptian_013, egyptian_014, egyptian_015 |
| §10.4 | 3944 | egyptian_009, egyptian_010, egyptian_010b, egyptian_014, egyptian_014b |
| §10.5 | 3996 | egyptian_008, egyptian_009, egyptian_013, egyptian_014b, egyptian_010c |
| §13.3 | 5079 | egyptian_019, egyptian_020 |
| §13.3 | 5169 | Only reconstructed infinitive stems and unavailable spelling images are tabulated; the suffix pronoun itself is not printed. V is a vowel cover symbol in a stem, not a bound morpheme. |
| §13.17 | 5551 | egyptian_021, egyptian_020 |
| §13.20 | 5609 | egyptian_022, egyptian_022b |
| §15.1 | 6030 | egyptian_020 |
| §15.1 | 6051 | egyptian_023 |
| §16.2 | 6611 | egyptian_024, egyptian_024b, egyptian_025, egyptian_026, egyptian_026b, egyptian_027, egyptian_028, egyptian_028b, egyptian_029, egyptian_030, egyptian_030b, egyptian_030c, egyptian_031, egyptian_032, egyptian_033, egyptian_025b, egyptian_025c, egyptian_025d, egyptian_027b, egyptian_027c, egyptian_027d |
| §16.2 | 6635 | egyptian_024c, egyptian_025e, egyptian_025f, egyptian_027e, egyptian_028c, egyptian_029b, egyptian_029c |
| §16.3 | 6653 | egyptian_026c, egyptian_026, egyptian_026d, egyptian_030d, egyptian_024, egyptian_024d, egyptian_024e, egyptian_025, egyptian_025b, egyptian_025c, egyptian_027, egyptian_027b, egyptian_027c, egyptian_027e, egyptian_020 |
| §17.2 | 7093 | egyptian_034, egyptian_011, egyptian_012, egyptian_008, egyptian_009, egyptian_015, egyptian_013, egyptian_008c, egyptian_020 |
| §18.2 | 7754 | egyptian_035, egyptian_036, egyptian_008, egyptian_009, egyptian_012, egyptian_011, egyptian_015, egyptian_014, egyptian_020 |
| §19.2 | 8764 | egyptian_037, egyptian_037b, egyptian_011, egyptian_008, egyptian_020 |
| §19.4 | 8807 | egyptian_034, egyptian_012, egyptian_027 |
| §19.9 | 8941 | egyptian_038, egyptian_039, egyptian_040, egyptian_041, egyptian_041b, egyptian_011, egyptian_009, egyptian_015, egyptian_020 |
| §19.13 | 9088 | egyptian_042, egyptian_011, egyptian_008, egyptian_014, egyptian_009, egyptian_013, egyptian_020 |
| §19.18 | 9194 | egyptian_026c, egyptian_027b, egyptian_027c, egyptian_034, egyptian_015, egyptian_003 |
| §22.12 | 10834 | egyptian_003, egyptian_001, egyptian_004, egyptian_011, egyptian_034 |
| §22.13 | 10870 | egyptian_003, egyptian_001, egyptian_004, egyptian_011 |
| §23.2 | 11481 | egyptian_003, egyptian_001, egyptian_004 |
| §23.4 | 11514 | egyptian_043, egyptian_043b, egyptian_003, egyptian_020 |
| §23.4 | 11525 | egyptian_043c, egyptian_043d, egyptian_003, egyptian_001 |
| §23.5 | 11546 | egyptian_044, egyptian_043c, egyptian_043d, egyptian_003, egyptian_001, egyptian_020 |
| §23.13 | 11921 | egyptian_011, egyptian_011b, egyptian_012, egyptian_012b, egyptian_015 |
| §23.13 | 11935 | egyptian_045, egyptian_045b, egyptian_045c, egyptian_045d, egyptian_045e, egyptian_015, egyptian_012b, egyptian_011, egyptian_011b, egyptian_020 |
| §24.1 | 12173 | egyptian_003, egyptian_001, egyptian_004 |
| §24.1 | 12186 | egyptian_043c, egyptian_046, egyptian_046b, egyptian_001 |
| §24.1 | 12194 | egyptian_046b, egyptian_046, egyptian_003, egyptian_001 |
| §24.2 | 12211 | egyptian_046b, egyptian_046, egyptian_043c, egyptian_001, egyptian_020 |
| §8.2 | 3004 | egyptian_015, egyptian_011, egyptian_009, egyptian_008, egyptian_003, egyptian_001, egyptian_004, egyptian_005, egyptian_006, egyptian_007, egyptian_019 |
| §15.7 | 6274 | egyptian_047, egyptian_047b, egyptian_047c, egyptian_047d, egyptian_048, egyptian_049, egyptian_050, egyptian_050b, egyptian_051, egyptian_052, egyptian_052b, egyptian_053, egyptian_054, egyptian_055, egyptian_056, egyptian_056b, egyptian_011, egyptian_012, egyptian_009, egyptian_008, egyptian_013, egyptian_015, egyptian_034, egyptian_019, egyptian_003, egyptian_001 |
| §8.3 | 3133 | The section explicitly describes compound prepositions formed from several words. No bound preposition or other identifiable eligible affix is printed in its examples. |
