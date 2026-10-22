# Plugin manifest

The Claude Code manifests for the two skills in `skills/`.

- `marketplace.json`: the `plasma` marketplace, which lists one plugin, `kaphtor`, at the repository root
- `plugin.json`: the `kaphtor` plugin; its skills are the folders in `skills/`, and its version is the project's
- `icon.png`: the plugin's listing icon (1024 px square): the Iouktas libation table under horns of consecration

`tests/test_plugin.py` checks both against `pyproject.toml`, the README's install lines and each skill's frontmatter.
