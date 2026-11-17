"""classify_pictograph matches whole words: a word inside a longer one ('ram' in 'frame', 'hand' in 'handle') is no
hit, and an animal's head is an animal, not personnel."""
from tools.linear_a.logogram_analyzer import classify_pictograph


def test_word_inside_a_longer_word_is_no_hit():
    assert classify_pictograph("frame with diagonal")[0] != "animal"            # 'ram' in 'frame'
    assert classify_pictograph("a rhyton with a handle at its rim")[0] != "personnel"  # 'hand' in 'handle'
    assert classify_pictograph("toothed bar over a box")[0] != "animal"         # 'ox' in 'box'


def test_an_animal_head_is_an_animal():
    assert classify_pictograph("a front-facing feline head") == ("animal", "SUPPORTS")
    assert classify_pictograph("animal head in profile") == ("animal", "SUPPORTS")


def test_whole_words_and_plurals_still_classify():
    assert classify_pictograph("bent arm") == ("personnel", "WEAKENS")
    assert classify_pictograph("fig leaf or plant") == ("botanical", "SUPPORTS")
    assert classify_pictograph("stemmed cup") == ("vessel/measure", "SUPPORTS")
    assert classify_pictograph("bulbs of garlic") == ("botanical", "SUPPORTS")
    assert classify_pictograph("ox head") == ("animal", "SUPPORTS")
    assert classify_pictograph(None) == ("none", "NEUTRAL")
