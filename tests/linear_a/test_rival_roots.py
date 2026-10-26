"""The rival-language root files hold keys and citations only, and give the competitor null (A15) the key spaces the
exported data was checked against: every entry keyed, key for key and entry number for entry number, and no field
beyond the form, the key and its citations. Each file's content is pinned whole, so any change to a form, a Sources
string or a Category fails here and must be made, with its reason, together with the new digest. Nothing here writes.
"""
import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.core import competitors

# key-space sizes and key -> entry-number digests of the export, equal to the private files' under names=False
KEYS = {"luwian": 1441, "egyptian": 3011, "hurrian": 95}
DIGEST = {"luwian": "78731e68e654ed1e", "egyptian": "97a284651f89ab08", "hurrian": "beeacb24336a0d3f"}
# sha256 of each file as exported (first 16 hex digits)
FILE_SHA = {"luwian": "dfcd439570329a58", "egyptian": "ac231e1a4b6e939a", "hurrian": "46d40ece77f57b86"}
FIELDS = {
    "luwian": {"Number", "Proto-Luwian", "Consonantal_Root", "Analogue_Labels"},
    "egyptian": {"Number", "Middle_Egyptian", "Consonantal_Root", "Sources"},
    "hurrian": {"Number", "Hurrian", "Consonantal_Root", "Category", "Sources"},
}
SPECS = {s.name: s for s in competitors.COMPETITORS}
MISSING = [s.file for s in competitors.COMPETITORS if not (competitors.DATA_DIR / s.file).exists()]
pytestmark = [pytest.mark.data,
              pytest.mark.skipif(bool(MISSING), reason=f"{', '.join(MISSING)} not in this checkout")]


def rows(spec):
    return json.loads((competitors.DATA_DIR / spec.file).read_text(encoding="utf-8"))


def digest(space):
    pairs = sorted(["-".join(k), sorted(v)] for k, v in space.keys.items())
    return hashlib.sha256(json.dumps(pairs, ensure_ascii=False).encode()).hexdigest()[:16]


@pytest.mark.parametrize("name", sorted(KEYS))
def test_the_key_space_is_the_exported_one(name):
    space = competitors.load(SPECS[name], data_dir=competitors.DATA_DIR)
    assert len(space.keys) == KEYS[name]
    assert digest(space) == DIGEST[name]
    assert not space.dropped, space.dropped          # every entry gives a key


@pytest.mark.parametrize("name", sorted(KEYS))
def test_the_file_is_the_exported_one(name):
    data = (competitors.DATA_DIR / SPECS[name].file).read_bytes()
    assert hashlib.sha256(data).hexdigest()[:16] == FILE_SHA[name]


@pytest.mark.parametrize("name", sorted(KEYS))
def test_every_entry_has_exactly_the_shipped_fields(name):
    for e in rows(SPECS[name]):
        assert set(e) == FIELDS[name], (e["Number"], set(e) ^ FIELDS[name])


@pytest.mark.parametrize("name", sorted(KEYS))
def test_every_entry_says_where_it_is_cited(name):
    field = "Analogue_Labels" if name == "luwian" else "Sources"
    for e in rows(SPECS[name]):
        assert e[field], e["Number"]
