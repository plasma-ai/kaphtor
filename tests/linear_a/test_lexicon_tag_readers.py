"""The tools that classify lexicon words read the `tags` array (the retired `category` field is gone)."""
from tools.linear_a import context_search, logogram_analyzer


def test_context_search_labels_a_word_by_its_first_matching_tag():
    label = context_search._semantic_category
    assert label(["administrative", "theonym"]) == "DIVINE"
    assert label(["hapax", "personal_name"]) == "PN"
    assert label(["noun", "ritual"]) == "RITUAL"
    assert label(["preposition"]) == "PARTICLE"
    assert label(["commodity", "logogram"]) == "LEX"
    assert label([]) == "LEX"
    assert label(None) == "LEX"


def test_logogram_analyzer_finds_function_words_by_tag_only():
    tag = logogram_analyzer._function_word_tag
    assert tag({"tags": ["particle", "ritual"]}) == "particle"
    assert tag({"tags": ["preposition"]}) == "preposition"
    assert tag({"tags": ["commodity", "logogram"]}) == ""
    assert tag({"semantic_field": "particle"}) == ""
    assert tag({}) == ""
