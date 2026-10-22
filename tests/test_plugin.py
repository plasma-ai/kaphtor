"""The plugin manifests install what the README's install lines name, and every skill folder is a loadable skill.

`/plugin marketplace add plasma-ai/kaphtor` reads `.claude-plugin/marketplace.json`, and
`/plugin install kaphtor@plasma` installs the plugin at the repository root, whose skills are the folders in
`skills/`. Nothing here writes.
"""
import json
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SKILLS = ("ancient-near-east-research", "linear-a-decipherment")


def manifest(name: str) -> dict:
    return json.loads((REPO / ".claude-plugin" / name).read_text(encoding="utf-8"))


def frontmatter(path: Path) -> dict[str, str]:
    """The `key: value` lines between the opening `---` and the next one."""
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"{path.name}: no frontmatter"
    head = text[4:text.index("\n---\n", 4)]
    return {k.strip(): v.strip() for k, _, v in (line.partition(":") for line in head.splitlines()) if v.strip()}


def test_the_marketplace_lists_the_kaphtor_plugin_at_the_root():
    market = manifest("marketplace.json")
    assert market["name"] == "plasma"
    assert [(p["name"], p["source"]) for p in market["plugins"]] == [("kaphtor", "./")]


def test_the_plugin_version_is_the_project_version():
    plugin = manifest("plugin.json")
    project = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert plugin["name"] == "kaphtor"
    assert plugin["version"] == project["version"]
    assert plugin["author"]["name"] == "Tom di Mino"


def test_the_readme_install_lines_name_the_marketplace_and_the_plugin():
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    plugin, market = manifest("plugin.json")["name"], manifest("marketplace.json")["name"]
    assert f"/plugin install {plugin}@{market}" in readme
    for skill in SKILLS:
        assert f"/{plugin}:{skill}" in readme or f"$PWD/skills/{skill}" in readme, skill


def test_each_skill_folder_holds_a_skill_named_for_it():
    folders = sorted(p.name for p in (REPO / "skills").iterdir() if p.is_dir())
    assert folders == list(SKILLS)
    for name in SKILLS:
        meta = frontmatter(REPO / "skills" / name / "SKILL.md")
        assert meta.get("name") == name
        assert meta.get("description"), f"{name}: no description"
