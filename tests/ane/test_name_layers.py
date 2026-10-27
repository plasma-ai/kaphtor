"""The four name layers match their manifests, carry no private catalogue ids, and are listed by their index.

Prosopographia Memphitica, Gauthier's DNG and the Kassite name concordances under data/ane/, the TLA v18 names under
data/share-alike/. Reads the shipped files only. No network.
"""
import hashlib
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.paths import ANE_DATA, SHARE_ALIKE

LAYERS = {
    "prosopographia-memphitica": ANE_DATA / "prosopographia-memphitica",
    "gauthier-dng": ANE_DATA / "gauthier-dng",
    "kassite-concordances": ANE_DATA / "kassite-concordances",
    "tla-v18-names": SHARE_ALIKE / "tla-v18-names",
}
PRIVATE = re.compile(r"src_\d+|sources_database|[a-z]+_(?:repo|root):|/Users/")


@pytest.mark.data
@pytest.mark.parametrize("layer", sorted(LAYERS))
def test_every_output_matches_its_manifest(layer):
    folder = LAYERS[layer]
    outputs = json.loads((folder / "MANIFEST.json").read_text(encoding="utf-8"))["outputs"]
    shipped = sorted(p.relative_to(folder).as_posix() for p in folder.rglob("*.jsonl"))
    assert shipped == sorted(outputs), layer
    for name, info in outputs.items():
        data = (folder / name).read_bytes()
        assert hashlib.sha256(data).hexdigest() == info["sha256"], (layer, name)
        assert data.count(b"\n") == info["rows"], (layer, name)


@pytest.mark.data
@pytest.mark.parametrize("layer", sorted(LAYERS))
def test_no_private_catalogue_id_or_path(layer):
    folder = LAYERS[layer]
    for path in sorted(folder.rglob("*")):
        if path.suffix in {".jsonl", ".json"}:
            text = path.read_text(encoding="utf-8")
            assert not PRIVATE.search(text), (layer, path.name, PRIVATE.search(text).group())
            if path.suffix == ".jsonl":
                assert '"source_id"' not in text, (layer, path.name)


@pytest.mark.data
@pytest.mark.parametrize("layer", sorted(LAYERS))
def test_the_index_lists_every_file(layer):
    folder = LAYERS[layer]
    for index in folder.rglob("_index.md"):
        listed = set(re.findall(r"\[\[[^|\]]+/([^/|\]]+)\|", index.read_text(encoding="utf-8")))
        here = {p.name for p in index.parent.iterdir() if p.name != "_index.md" and not p.name.startswith(".")}
        here = {name if (index.parent / name).is_file() else "_index" for name in here}
        assert here <= listed, (layer, index.parent.name, here - listed)
