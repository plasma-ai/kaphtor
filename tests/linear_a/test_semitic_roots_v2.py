"""The shipped semitic_roots.json (schema 2) reads into the record shape the root matcher keys on.

Nothing here writes outside tmp_path.
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.core import data_cache, root_index
from tools.core.semitic_root_schema import roots_records

DOC = {"schema_version": 2, "description": "x", "roots": [
    {"id": "1", "ps": "*bayt-", "meaning": "house", "basis": {"ps": "sed", "meaning": "sed"},
     "reflexes": [{"lang": "Hebrew", "cite": [], "basis": "sed", "source_class": "open", "text": "bayit 'house'"},
                  {"lang": "Akkadian", "cite": [], "basis": "sed", "source_class": "closed", "text": "bītu",
                   "gloss_withheld": True},
                  {"lang": "Ugaritic", "cite": [], "basis": "sed", "source_class": "closed", "text_withheld": True}],
     "notes": "A note."},
    {"id": "S2", "ps": "*ʿzr", "meaning": "help", "basis": {"ps": "project", "meaning": "project"}, "reflexes": []},
]}


def test_schema_2_reads_as_records():
    recs = roots_records(DOC)
    assert recs[0] == {"Number": "1", "Proto-Semitic": "*bayt-", "Meaning": "house",
                       "Analogues": {"Hebrew": "bayit 'house'", "Akkadian": "bītu"}, "Notes": "A note."}
    assert recs[1] == {"Number": "S2", "Proto-Semitic": "*ʿzr", "Meaning": "help", "Analogues": {}}


def test_the_private_list_format_passes_through():
    live = [{"Number": "1", "Proto-Semitic": "*bayt-", "Meaning": "house", "Analogues": {}}]
    assert roots_records(live) is live


def test_another_schema_version_is_refused():
    with pytest.raises(ValueError, match="schema_version 3"):
        roots_records({**DOC, "schema_version": 3})


def test_root_index_loads_schema_2(tmp_path):
    path = tmp_path / "semitic_roots.json"
    path.write_text(json.dumps(DOC), encoding="utf-8")
    assert [r["Number"] for r in root_index.load_records(path)] == ["1", "S2"]
    path.write_text(json.dumps({**DOC, "roots": DOC["roots"] + DOC["roots"][:1]}), encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate Numbers"):
        root_index.load_records(path)


def test_data_cache_reads_schema_2(monkeypatch, tmp_path):
    (tmp_path / "semitic_roots.json").write_text(json.dumps(DOC), encoding="utf-8")
    monkeypatch.setattr(data_cache, "SEMITIC_ROOTS_DATA", tmp_path)
    data_cache.clear()
    try:
        assert [r["Number"] for r in data_cache.semitic_roots()] == ["1", "S2"]
    finally:
        data_cache.clear()


@pytest.mark.data
def test_the_shipped_roots_read_as_records():
    data_cache.clear()
    recs = data_cache.semitic_roots()
    assert len(recs) == 4177
    assert all({"Number", "Proto-Semitic", "Meaning", "Analogues"} <= set(r) for r in recs)
