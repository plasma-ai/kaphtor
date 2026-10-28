---
name: data/linear-a/protocol-c/builds/C1-MANIFEST
title: "C1 manifest"
desc: "The C1 manifest of Protocol C: the six blind builds with their entry counts, probes, audits and inventory hashes, the blindness record, what is not part of C1, and the review points before rendering."
tags: [data, linear-a, protocol-c]
license: CC BY 4.0
authors: "di Mino"
date: 2026-10-29
status: "built and checked; not yet committed or tagged (commit waits for di Mino). No Linear A form has been rendered."
created: 2026-10-29T19:48:19Z
updated: 2026-10-29T19:48:19Z
---

# C1 manifest

Six inventories, one per arm, each written by a fresh Codex session (GPT-6-Astra, reasoning high, ChatGPT login) from
its own kit by `../scripts/run_builder.sh <arm> --codex`, and checked by `../scripts/check_inventory.py`.

## Builds

| Arm | Entries | Morphemes | Distinct (side, segments) | Probe | Audit | `inventory.filled.json` SHA-256 |
|---|---|---|---|---|---|---|
| `cs` | 183 | 91 | 125 | clean | 30 commands, 0 outside the kit | `73266e62f1457d7cfff26581310b7cfd4f1c2156abc267179428a37a820d7020` |
| `yd` | 52 | 35 | 36 | clean | 21 commands, 0 outside | `82fc1ef17a2ec04c14e042dd6113e7c8eff0f55c066d059ecd7e729aa034dc76` |
| `luwian` | 87 | 50 | 70 | clean | 12 commands, 0 outside | `df9ba92e89ab2d42f170a2186bb0529e7b23a59e0424e1a27b2b89ff3b3cc8e9` |
| `hurrian` | 303 | 120 | 152 | clean | 21 commands, 0 outside | `aee54dafd9f04533e57055bffec8ce4e4a1f0d9d30cd5ebb01f7de1825683b3b` |
| `egyptian` | 116 | 56 | 53 | clean | 24 commands, 0 outside | `a38b77152b38345d5a9e199596506acd98bf8955bd39c81f8a3a538d2c954521` |
| `greek` | 382 | 112 | 166 | clean | 35 commands, 0 outside (correction: 10, 0) | `557c3b43cb56ea280b67d7624cee47a15096cd77329469c65fd054161676753b` |

Each folder holds the kit as given (grammar copies excepted; `kit.sha256` hashes them), `probe.txt`, the full
`--json` transcript, `blindness_audit.txt`, the builder's `inventory.json` and `notes.md`, the checked
`inventory.filled.json`, and `SHA256SUMS`.

## Blindness

- **Context.** Codex ran with no user `config.toml`, no execpolicy rules, every skill disabled by path, plugins and
  apps off, and web search off. Before each build a probe asked the session to list its skills and plugins and to say
  whether its instructions mention Linear A, Minoan or Semitic, or contain an email address; all six answered
  NONE / no / no, and a build runs only on that answer. Codex's user-level AGENTS.md (git authentication only)
  loads.
- **Skill scan (disclosed).** Every `stderr.txt` logs Codex's startup skill scan reaching its traversal limit and
  failing to load one nested file, `linear-a-decipherment/references/linear-b/SKILL.md` (no frontmatter). The disable
  list covered top-level `SKILL.md` files only, so this nested file was scanned; it failed to load, and the probe
  answered NONE. From C2 on the disable list covers `SKILL.md` at any depth (`run_builder.sh`).
- **Builder model.** Codex's `--json` log names no model, so each build's `builder_model.txt` records what the runner
  launched (gpt-6-astra, Codex CLI 0.165.0, reasoning effort high); for these six it was written after the run, from
  `run_builder.sh`, and `inventory.filled.json` takes `builder.model` from it.
- **Scratch.** Builders' scratch scripts are kept where they survived (`hurrian/work/`). The cs and egyptian builders
  deleted theirs; luwian's `.review/` and greek's `.work/` were not copied (dot-folders) and are no longer in the
  kits. The transcripts record every command.
- **Files.** Writes were confined to the kit (writes to `/tmp` excluded). Codex's shell can read outside the kit, so
  reads are audited, not prevented: the audit flags every command path outside the kit that starts at a root folder,
  `~`, `$HOME` or `..`. All six: none.
- **What the builder is told.** The kit includes protocol §5.2, §5.3 and §16, as §5.3 item 1 requires; those
  sections name Linear A and *Ya Diktu*. Blindness here means no corpus, no lexicon, no sign list and no thesis, not
  ignorance of the test's purpose.
- **Refusal (§5.3 item 2).** `greek_274`'s function string quoted Bartoněk's syllabic spelling "-A-I", which is also a
  Linear A corpus word. The check refused it. A fresh correction session, sandboxed and probed the same way, restated
  that one function from p. 167; nothing else changed (`inventory.v1.json` is the builder's first version,
  `correction-transcript.jsonl` the session).

## Not part of C1

- `pilot-luwian-2026-10-29/`: Claude Code pilot that tested the format. Its tool list still held WebSearch, Skill and
  Task (unused). Its 70 distinct forms match the C1 `luwian` build in 69; the one difference is g-w-a vs gw-a,
  neutralised by the renderer's digraph rule (`../render/series.json`).
- `pilot-luwian-codex-2026-10-29-skills-visible/`: first Codex pilot. Codex's user skills folder links every Claude skill,
  `linear-a-decipherment` and `minoan` among them, and Codex listed them in its instructions. Not blind; kept as the
  record of the defect.

- `setaside-yd-2026-10-29-old-pdf-3204dd2/`: the first `yd` build (55 entries, 34 morphemes). The kit paired the
  current `tables/yd.md` with the PDF at commit `3204dd2`, a 42-page edition fourteen updates old in which final NU is
  an energic. Its mood-order conflict (energic after the object suffix, indicative before it) and its count gap came
  from that edition. Set aside under amendment A3; the current edition reads NU as the 1cp object suffix and states
  the order base, indicative -u, 2fs subject -tī, 1cp object -n(u) (§6.1, n. 23).

## Review points (before rendering)

1. **`yd` edition (resolved by A3).** See the set-aside build above. The rebuild (commit d9a3f93) cites §6.1,
   pp. 13–15 for the order base, indicative -u (`s_mood`), 2fs -tī (`s_case_person`), 1cp -n(u) (`s_pronoun`). Its 35
   morphemes against `TABLES.md`'s 36: the 36 counts two statements with no printable form ("case endings (general)",
   construct state), which the builder declined; its `notes.md` table gives the disposition of every unit row. The
   builder labelled Appendix B collectively (the appendix title names Linear A, which the brief forbids it to write)
   and accounted for rows 36–59 one by one in `notes.md`; the checker accepts that table and fails if a row is
   missing from it (tested).
2. **`hurrian` slot repetition.** Wegner's Tabelle 1–2 order (Suffixaufnahme) needs `s_pronoun` and
   `s_gender_number` twice; A2 allows each slot once. The builder kept the template order and said so. The template
   therefore under-generates Hurrian stacking; null L prices each arm against its own slots, so the effect is on
   Hurrian's power, not on its calibration.
3. **`greek` spellings.** 92 entries carry Bartoněk's syllabic spelling in `form` with the phonemic segments he pairs
   with it; they collapse into the same distinct shapes as their phonemic twins, so they add no realization.
4. **Coverage labels.** Builders labelled units by section, by printed title or (yd Appendix B) by row number; the
   checker accepts each and fails on a missing unit (tested by dropping two `cs` units).
