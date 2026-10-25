"""The discovery metadata at the root agree with pyproject.toml.

`codemeta.json` is read by Software Heritage and the research-software indexes, so its version and description must
follow the package's. Nothing here writes.
"""
import json
import tomllib

from tools.paths import REPO


def test_codemeta_names_the_package_version():
    project = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    codemeta = json.loads((REPO / "codemeta.json").read_text(encoding="utf-8"))
    assert codemeta["name"] == project["name"]
    assert codemeta["version"] == project["version"]
