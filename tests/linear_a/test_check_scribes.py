"""`check_scribes`: the corpus scribe fields against scribes.json, and what the check reports.

Unit tests only: every corpus and registry is written inline. The data test runs the check on the shipped files.
"""
import json

import pytest

from tools.linear_a.validation import check_scribes
from tools.paths import LINEAR_A_DATA

REGISTRY = {'HT Scribe 9': {'site': 'Haghia Triada', 'class': 'tablet', 'numbering': 'Militello 1989', 'source': 'x'},
            'KH Wc Scribe 54': {'site': 'Khania', 'class': 'Wc', 'numbering': 'GORILA V', 'source': 'x'}}


def corpus(**over):
    base = {'HT85a': {'scribe': 'HT Scribe 9', 'scribe_gorila': '9 HT'}, 'KHWc2009': {'scribe': 'KH Wc Scribe 54'},
            'IOZa2': {'scribe': ''}}
    base.update(over)
    return base


def test_clean_data_reports_nothing():
    assert check_scribes.problems(corpus(), REGISTRY) == []


def test_a_label_missing_from_the_registry_is_reported():
    out = check_scribes.problems(corpus(HT1={'scribe': 'HT Scribe 21'}), REGISTRY)
    assert out == ['HT1: scribe "HT Scribe 21" has no entry in scribes.json']


def test_a_registry_entry_with_no_record_is_reported():
    out = check_scribes.problems(corpus(KHWc2009={'scribe': ''}), REGISTRY)
    assert out == ['scribes.json: "KH Wc Scribe 54" is carried by no corpus record']


def test_doubt_written_into_the_label_is_reported():
    out = check_scribes.problems(corpus(HT85a={'scribe': 'HT Scribe 9 (?)'}), REGISTRY)
    assert 'HT85a: scribe "HT Scribe 9 (?)" carries its doubt in the label; use scribe_doubt' in out


def test_doubt_beside_no_scribe_is_reported():
    out = check_scribes.problems(corpus(IOZa2={'scribe': '', 'scribe_doubt': True}), REGISTRY)
    assert out == ['IOZa2: scribe_doubt stands beside no scribe']


def test_a_label_on_another_site_s_record_is_reported():
    out = check_scribes.problems(corpus(KHWc2009={'scribe': 'HT Scribe 9'}), {'HT Scribe 9': REGISTRY['HT Scribe 9']})
    assert out == ['KHWc2009: scribe "HT Scribe 9" does not open with the record\'s site code']


def test_scribe_gorila_outside_the_ht_tablets_is_reported():
    out = check_scribes.problems(corpus(KHWc2009={'scribe': 'KH Wc Scribe 54', 'scribe_gorila': '54 KH Wc'}), REGISTRY)
    assert out == ['KHWc2009: scribe_gorila belongs to Haghia Triada tablets only']


BOTH = {'scribe': 'HT Scribe 9', 'scribe_part': 'lines 1–3', 'scribe_also': [{'scribe': 'HT Scribe 18', 'part': 'lines 4–6'}]}
REGISTRY_18 = dict(REGISTRY, **{'HT Scribe 18': REGISTRY['HT Scribe 9']})


def test_a_second_scribe_counts_as_carried():
    assert check_scribes.problems(corpus(HT6b=BOTH), REGISTRY_18) == []


def test_a_second_scribe_missing_from_the_registry_is_reported():
    out = check_scribes.problems(corpus(HT6b=BOTH), REGISTRY)
    assert out == ['HT6b: scribe "HT Scribe 18" has no entry in scribes.json']


def test_a_second_scribe_beside_no_scribe_is_reported():
    out = check_scribes.problems(corpus(HT6b=dict(BOTH, scribe='', scribe_part='')), REGISTRY_18)
    assert out == ['HT6b: scribe_also stands beside no scribe']


def test_a_second_scribe_repeating_the_first_is_reported():
    rec = {'scribe': 'HT Scribe 9', 'scribe_also': [{'scribe': 'HT Scribe 9', 'part': 'lines 4–6'}]}
    assert check_scribes.problems(corpus(HT6b=rec), REGISTRY) == ['HT6b: scribe_also repeats the record\'s scribe']


def test_a_second_scribe_not_written_as_a_list_of_objects_is_reported():
    out = check_scribes.problems(corpus(HT6b={'scribe': 'HT Scribe 9', 'scribe_also': 'HT Scribe 18'}), REGISTRY_18)
    assert out == ['HT6b: scribe_also must be a list of {"scribe", "part"} objects',
                   'scribes.json: "HT Scribe 18" is carried by no corpus record']


def test_a_part_beside_no_scribe_is_reported():
    out = check_scribes.problems(corpus(IOZa2={'scribe': '', 'scribe_part': 'line 1'}), REGISTRY)
    assert out == ['IOZa2: scribe_part stands beside no scribe']


@pytest.mark.data
def test_the_shipped_corpus_agrees_with_the_shipped_registry():
    corpus = json.loads((LINEAR_A_DATA / "corpus.json").read_text(encoding="utf-8"))
    registry = json.loads((LINEAR_A_DATA / "scribes.json").read_text(encoding="utf-8"))["scribes"]
    assert check_scribes.problems(corpus, registry) == []
