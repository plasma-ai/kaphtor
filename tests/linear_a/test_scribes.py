"""`tools.core.scribes`: records grouped by the corpus `scribe` and `scribe_also` labels.

Unit tests only: every corpus is written inline.
"""
from tools.core import scribes

CORPUS = {
    'HT9a': {'scribe': 'HT Scribe 9', 'site': 'Haghia Triada', 'transliteratedWords': ['SA-RO', '𐄁', 'KU-RO', '31']},
    'HT9b': {'scribe': 'HT Scribe 9', 'site': 'Haghia Triada', 'transliteratedWords': ['KU-RO', '\n', 'PA-DE']},
    'HT2': {'scribe': 'HT Scribe 10', 'site': 'Haghia Triada', 'transliteratedWords': ['A-KA-RU']},
    'HTWa1021': {'scribe': 'HT Wa Scribe 100', 'scribe_doubt': True, 'site': 'Haghia Triada',
                 'transliteratedWords': ['KA']},
    'KHWc2009': {'scribe': 'KH Wc Scribe 54', 'site': 'Khania', 'transliteratedWords': []},
    'IOZa2': {'scribe': '', 'site': 'Iouktas', 'transliteratedWords': ['JA-DI-KI-TU']},
}


def test_index_groups_by_label_and_skips_the_unassigned():
    index = scribes.scribe_index(CORPUS)
    assert index['HT Scribe 9'] == ['HT9a', 'HT9b']
    assert set(index) == {'HT Scribe 9', 'HT Scribe 10', 'HT Wa Scribe 100', 'KH Wc Scribe 54'}


def test_labels_sort_by_number_not_by_string():
    assert scribes.scribe_sort_key('HT Scribe 9') < scribes.scribe_sort_key('HT Scribe 10')


def test_resolve_ignores_case_and_the_word_scribe():
    labels = list(scribes.scribe_index(CORPUS))
    assert scribes.resolve_scribe('ht scribe 9', labels) == ['HT Scribe 9']
    assert scribes.resolve_scribe('kh wc 54', labels) == ['KH Wc Scribe 54']


def test_resolve_matches_the_whole_number_and_the_class():
    labels = list(scribes.scribe_index(CORPUS))
    assert scribes.resolve_scribe('HT 1', labels) == []                     # not HT Scribe 10, not HT Wa Scribe 100
    assert scribes.resolve_scribe('HT 100', labels) == ['HT Wa Scribe 100']  # class may be left out
    assert scribes.resolve_scribe('HT', labels) == ['HT Scribe 9', 'HT Scribe 10', 'HT Wa Scribe 100']


def test_shared_words_are_those_on_two_or_more_documents():
    assert scribes.scribe_shared_words(CORPUS, ['HT9a', 'HT9b']) == [('KU-RO', ['HT9a', 'HT9b'])]


TWO_HANDS = {
    'HT6a': {'scribe': 'HT Scribe 17', 'site': 'Haghia Triada', 'transliteratedWords': ['KA-PA']},
    'HT6b': {'scribe': 'HT Scribe 17', 'scribe_part': 'lines 1–3', 'site': 'Haghia Triada',
             'scribe_also': [{'scribe': 'HT Scribe 18', 'part': 'lines 4–6'}], 'transliteratedWords': ['WA-DU-NI-MI']},
    'HT17': {'scribe': 'HT Scribe 18', 'site': 'Haghia Triada', 'transliteratedWords': ['RA-TI-SE']},
}


def test_a_record_with_a_second_scribe_is_listed_under_both():
    index = scribes.scribe_index(TWO_HANDS)
    assert index == {'HT Scribe 17': ['HT6a', 'HT6b'], 'HT Scribe 18': ['HT6b', 'HT17']}


def test_scribe_part_gives_the_part_each_scribe_wrote():
    assert scribes.scribe_part(TWO_HANDS['HT6b'], 'HT Scribe 17') == 'lines 1–3'
    assert scribes.scribe_part(TWO_HANDS['HT6b'], 'HT Scribe 18') == 'lines 4–6'
    assert scribes.scribe_part(TWO_HANDS['HT6a'], 'HT Scribe 17') == ''
