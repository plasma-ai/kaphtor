---
name: data/linear-a/protocol-c/inventories
title: Protocol C unit tables and schema
desc: The phase C0 unit tables the blind builders transcribe, and the inventory schema.
tags: [data, linear-a, protocol-c]
license: CC BY 4.0
created: 2026-10-29T19:48:19Z
updated: 2026-10-29T19:48:19Z
---

# Protocol C unit tables and schema

[[data/linear-a/protocol-c/_index|..]]

[[data/linear-a/protocol-c/inventories/TABLES-C0|TABLES-C0]]: The signed list of grammar units each blind builder of Protocol C transcribes: the unit rule, the six arms with their grammars and unit counts, and the page checks.

[[data/linear-a/protocol-c/inventories/schema.json|schema.json]]: The inventory format: one entry per realization, its slot in the template of amendment A2, its segments, function and source, and the class order.

[[data/linear-a/protocol-c/inventories/tables/_index|tables/]]: The per-arm unit lists of TABLES.md, each unit with its section, title and page.

***

`TABLES-C0.md` is the research tree's `TABLES.md`, renamed here because the wiki reads `TABLES` and `tables/` as one
name. It and its per-arm files fix, before any build, which units of each grammar a builder reads (amendment A1:
numbered or boxed tables, itemised lists of forms, and sections whose heading names a §5.2 category). The builder
takes every realization in those units and nothing else. `schema.json` is the format each `inventory.json` in
`builds/` validates against; every kit holds a copy at the same sha256.

The per-arm files named the research tree's copies of the grammars by absolute path. The port cut those paths as
`run_builder.sh` cut them for the builders, so each file here is, below its frontmatter, the `units.md` its builder
was given; in `tables/cs.md` and `TABLES-C0.md` it also cut the private source ids, and it set a blank line before
three lists the wiki would read as wrapped lines (`PORT-LEDGER.json`).
