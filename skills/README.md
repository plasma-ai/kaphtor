# Skills

Two agent skills, for Claude Code (through the plugin in `.claude-plugin/`) and Codex (linked into
`~/.agents/skills/`):

- [linear-a-decipherment](linear-a-decipherment/SKILL.md): reads and checks the Linear A record, its inscriptions,
  words, signs and readings with their tiers
- [ancient-near-east-research](ancient-near-east-research/SKILL.md): queries the ancient Near East corpora and
  the place and name authorities through `tools/ane/`

Each skill's `SKILL.md` names the pages, data and commands it works from, and its `README.md` describes the skill:
[linear-a-decipherment](linear-a-decipherment/README.md),
[ancient-near-east-research](ancient-near-east-research/README.md). `tests/test_plugin.py` checks that every folder
here is a skill named for its folder.
