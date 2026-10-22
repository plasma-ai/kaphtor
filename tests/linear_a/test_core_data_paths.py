"""The tools/core loaders read from the repository's data/ folders, and name a dataset that is not in the checkout.

Some Linear A sets are not in every checkout, so these tests check where each loader looks, and that a missing file
fails with its name rather than a bare traceback. Nothing here writes.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.core import (
    contact_lexicon,
    corpus_utils,
    data_cache,
    run_saver,
    semitic_root_schema,
    site_profiles,
    skeleton,
    verb_morphology,
)
from tools.paths import CACHE, CONTACT_DATA, DATA, LINEAR_A_DATA, REPO, SEMITIC_ROOTS_DATA, NotInCheckout

READ_PATHS = {
    "corpus_utils.CORPUS_PATH": corpus_utils.CORPUS_PATH,
    "contact_lexicon._CONTACT_DIR": contact_lexicon._CONTACT_DIR,
    "semitic_root_schema._CORRESPONDENCES": semitic_root_schema._CORRESPONDENCES,
    "site_profiles.SITE_PROFILES_PATH": site_profiles.SITE_PROFILES_PATH,
    "skeleton.REGISTRY_PATH": getattr(skeleton, "REGISTRY_PATH", Path("unset")),
    "verb_morphology.TEMPLATES_PATH": verb_morphology.TEMPLATES_PATH,
}


@pytest.mark.parametrize("name", sorted(READ_PATHS))
def test_every_loader_reads_inside_data(name):
    assert READ_PATHS[name].is_relative_to(DATA), (name, READ_PATHS[name])


def test_runs_are_saved_in_the_cache_not_the_repository():
    for path in (run_saver.RUNS_DIR, run_saver.INDEX_PATH):
        assert path.is_relative_to(CACHE), path
        assert not path.is_relative_to(REPO), path


def test_each_dataset_has_its_folder():
    assert corpus_utils.CORPUS_PATH.parent == LINEAR_A_DATA
    assert contact_lexicon._CONTACT_DIR == CONTACT_DATA
    assert semitic_root_schema._CORRESPONDENCES.parent == SEMITIC_ROOTS_DATA
    assert data_cache.data_path("lexicon").parent == LINEAR_A_DATA
    assert data_cache.data_path("semitic_roots").parent == SEMITIC_ROOTS_DATA


def test_a_missing_dataset_is_named(monkeypatch, tmp_path):
    monkeypatch.setattr(data_cache, "LINEAR_A_DATA", tmp_path)
    data_cache.clear()
    with pytest.raises(NotInCheckout, match="lexicon.json is not in this checkout"):
        data_cache.lexicon()


def test_the_root_index_lists_no_closed_lexicon():
    from tools.core import root_index
    # CAD headwords, Gelb AS 21, Harding, the Anchor Bible commentaries' Phoenician
    closed = {"cad", "amorite_onomasticon", "arabian_onomasticon", "anchor_bible_phoenician"}
    assert not closed & {lx.name for lx in root_index.LEXICA}
    assert all(lx.path.parent == CONTACT_DATA for lx in root_index.LEXICA), [lx.path for lx in root_index.LEXICA]


def test_site_profiles_and_verb_templates_name_a_missing_file(monkeypatch, tmp_path):
    monkeypatch.setattr(site_profiles, "_cached_profiles", None)
    with pytest.raises(NotInCheckout, match="profiles.json is not in this checkout"):
        site_profiles.load_site_profiles(tmp_path / "profiles.json")
    with pytest.raises(NotInCheckout, match="templates.json is not in this checkout"):
        verb_morphology.load_templates(tmp_path / "templates.json")
