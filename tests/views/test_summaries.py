"""The summaries at the top of the section indexes: the block the builder owns under an index's `***`, and the
templates whose numbers come from the data."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.paths import LINEAR_A_DATA, SEMITIC_ROOTS_DATA
from tools.views import markdown, model, summaries

LIVE_FILES = ("corpus.json", "lexicon.json", "translations.json", "onomasticon.json", "unread_words.json",
              "sign_values.json", "census_classes.json")
LIVE = pytest.mark.skipif(not all((LINEAR_A_DATA / n).exists() for n in LIVE_FILES)
                          or not (SEMITIC_ROOTS_DATA / "semitic_roots.json").exists(),
                          reason="the Linear A data or the root database is not in this checkout")

INDEX = ("---\nname: wiki/x\ndesc: X.\n---\n\n# X\n\n[[wiki/_index|..]]\n\n"
         "[[wiki/x/a|a]]: A.\n\n***\n\nWritten by hand.\n")


def test_the_summary_goes_under_the_rule_and_every_other_line_stays():
    text = markdown.set_summary(INDEX, "First.\n\nSecond.")
    assert text.split("\n")[:13] == INDEX.split("\n")[:13]
    after = text.split("***\n", 1)[1]
    assert after == f"\n{markdown.SUMMARY_BEGIN}\nFirst.\n\nSecond.\n{markdown.SUMMARY_END}\n\nWritten by hand.\n"


def test_a_new_summary_replaces_the_old_and_a_rewrite_changes_nothing():
    once = markdown.set_summary(INDEX, "Old.")
    twice = markdown.set_summary(once, "New.")
    assert "Old." not in twice and twice == markdown.set_summary(INDEX, "New.")
    assert markdown.set_summary(twice, "New.") == twice


def test_an_index_without_the_rule_gets_one():
    bare = INDEX.split("***")[0].rstrip("\n") + "\n"
    text = markdown.set_summary(bare, "S.")
    assert text.endswith(f"[[wiki/x/a|a]]: A.\n\n***\n\n{markdown.SUMMARY_BEGIN}\nS.\n{markdown.SUMMARY_END}\n")


def test_a_summary_block_with_no_end_is_refused():
    with pytest.raises(ValueError):
        markdown.set_summary(INDEX.replace("Written", f"{markdown.SUMMARY_BEGIN}\nWritten"), "S.")


def test_a_slot_no_field_fills_is_an_error():
    with pytest.raises(KeyError, match="nowhere"):
        summaries.fill("{lexicon} words in {nowhere}", {"lexicon": "1"})


@pytest.mark.data
@LIVE
def test_every_slot_of_every_template_is_filled_from_the_data():
    loaded = model.load(LINEAR_A_DATA)
    bodies = summaries.bodies(loaded, SEMITIC_ROOTS_DATA)
    assert set(bodies) == set(summaries.FOLDERS.values())
    for body in bodies.values():
        assert "{" not in body and "}" not in body
    assert f"{len(loaded.lexicon):,} words" in bodies["wiki/linear-a"]


@pytest.mark.data
@LIVE
def test_the_intact_unread_words_are_those_no_witness_shows_damaged():
    loaded = model.load(LINEAR_A_DATA)
    fields = summaries.fields_linear_a(loaded)
    intact = [w for w, u in loaded.unread.items() if not u.get("surface_damage")]
    assert fields["unread_intact"] == f"{len(intact):,}"
    assert 0 < len(intact) < len(loaded.unread)
    assert "TA-I" in intact                        # undamaged on HT 39, HT 9a and HT 9b
    assert "QE-KA" not in intact                   # whole on HT 85b, but damaged at the start on HT 111a
