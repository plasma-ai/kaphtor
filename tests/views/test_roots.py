"""The root pages: one per record of semitic_roots.json, filed by first radical."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.views import roots

DOC = {"schema_version": 2, "description": "x", "roots": [
    {"id": "1", "ps": "*bayt-", "meaning": "house", "basis": {"ps": "sed", "meaning": "sed"},
     "sed": {"siglum": "SEDonline", "loc": "semet 113"},
     "reflexes": [{"lang": "Hebrew", "cite": [{"siglum": "BDB (Open Scriptures)", "loc": "108"}], "basis": "sed",
                   "source_class": "open", "text": "bayit 'house' | bāttīm"},
                  {"lang": "Akkadian", "cite": [{"siglum": "CAD", "loc": "b 282"}], "basis": "sed",
                   "source_class": "closed", "text": "bītu [CAD b 282]", "gloss_withheld": True},
                  {"lang": "Ugaritic", "cite": [{"siglum": "DULAT", "loc": "250"}], "basis": "sed",
                   "source_class": "closed", "text_withheld": True}],
     "notes": "A note."},
    {"id": "S2", "ps": "*ʿzr", "meaning": "to help, aid", "basis": {"ps": "project", "meaning": "project"},
     "reflexes": []},
]}


def folder(tmp_path, doc=DOC):
    (tmp_path / "semitic_roots.json").write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    return tmp_path


def test_one_page_per_root_filed_by_first_radical(tmp_path):
    assert list(roots.pages(folder(tmp_path))) == ["wiki/semitic-roots/b/1_house", "wiki/semitic-roots/ʿ/S2_to_help_aid"]


def test_no_file_no_pages(tmp_path):
    assert roots.pages(tmp_path) == {}
    assert roots.descs(tmp_path) == {}


def test_the_page_shows_the_root_its_reflexes_and_the_note(tmp_path):
    text = roots.pages(folder(tmp_path))["wiki/semitic-roots/b/1_house"]
    assert "| Reconstruction | \\*bayt- |" in text
    assert "| SED | SEDonline semet 113 |" in text
    assert "| Hebrew | bayit 'house' \\| bāttīm | BDB (Open Scriptures) 108 |  |" in text
    assert "| Akkadian | bītu \\[CAD b 282\\] | CAD b 282 | gloss withheld |" in text
    assert "| Ugaritic |  | DULAT 250 | source's text withheld |" in text
    assert "## Notes" in text and "A note." in text


def test_a_project_root_names_no_sed_entry(tmp_path):
    text = roots.pages(folder(tmp_path))["wiki/semitic-roots/ʿ/S2_to_help_aid"]
    assert "SEDonline" not in text and "| Basis | project |" in text


def test_each_radical_folder_has_a_desc(tmp_path):
    assert roots.descs(folder(tmp_path)) == {
        "wiki/semitic-roots/b": "Semitic roots whose first radical is b.",
        "wiki/semitic-roots/ʿ": "Semitic roots whose first radical is ʿ."}
