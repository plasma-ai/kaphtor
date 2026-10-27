---
name: data/ane/prosopographia-memphitica
title: Prosopographia Memphitica
desc: New Kingdom Memphite persons and names from Prosopographia Memphitica (ProM, release 2024-11-15), with titles, dating, objects and Unicode transliterations, CC BY 4.0 and ODC-By 1.0.
tags: [data, egyptian, onomastics]
license: CC BY 4.0 AND ODC-By 1.0
created: 2026-10-27T17:22:41Z
updated: 2026-10-27T17:22:41Z
---

# Prosopographia Memphitica

[[data/ane/_index|..]]

[[data/ane/prosopographia-memphitica/MANIFEST.json|MANIFEST.json]]: The source record, licence statements, the transliteration and join rules, counts and checksums.

[[data/ane/prosopographia-memphitica/names.jsonl|names.jsonl]]: 1,574 name rows, with their persons, Ranke references and the PNM v6 names they join.

[[data/ane/prosopographia-memphitica/persons.jsonl|persons.jsonl]]: 2,409 persons, one per ProM person, with names, titles, dating, objects and person-to-person relations.

[[data/ane/prosopographia-memphitica/tables/_index|tables/]]: ProM's eleven tables as released, one JSONL file per table, with ProM's column names and ids.

***

The source is Anne Herzberg-Beiersdorf's *Prosopographia Memphitica* (Humboldt-Universität zu Berlin; Zenodo concept
DOI 10.5281/zenodo.3856410), released 2024-11-15 with its files dated 2024-11-13. ProM states its licence as CC BY 4.0
and ODC-By 1.0, and the MANIFEST quotes each statement and where it stands. Ids are ProM's own primary keys:
`prom:person:<ID>`, `prom:name:<ID>`.

ProM types its transliteration in the Umschrift_TTn font (v3.0, 8/2007, F. Junge). `name`, `other_names` and `title`
keep the font strings. `name_unicode`, `other_names_unicode` and `title_unicode` convert them by that font's sign list:
`#` ꜣ, `o` ꜥ, `'` ʾ, `H` ḥ, `"` and `O` Ḥ, `!` plain H, `X` ḫ, `%` Ḫ, `x` ẖ, `$` H̱, `S` š, `C` Š, `c` S, `T` ṯ, `V` Ṯ,
`v` T, `D` ḏ, `E` Ḏ, `e` D, `Q` ḳ, `Ö` Ḳ, `=` ⸗, and code 127 `|`. The x and X values are the reverse of the Manuel de
Codage.

`pnm_name_ids` joins a name to PNM v6 (`data/ane/pnm-v6/`) only where its normalized Ranke reference (`I, 231.4`)
matches exactly one PNM name: 647 references join, 146 match none, and 5 match several and are left unjoined, with
their candidates listed. `pnm_ids` holds the PNM records ProM itself names. ProM's faults are kept as given, and the
MANIFEST lists them under `data_notes`. Its 204 person-to-name relations pair no person with a name of the same
spelling, so no link is drawn from them.
