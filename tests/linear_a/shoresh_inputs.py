"""The shipped files the Shoresh tests read, and the mark that runs them as `data` tests and skips them when one is not
in the checkout. Every index a test builds keys its records through the correspondence table, every word is read
through the sign registry, family B draws its decoys from the corpus, and the end-to-end runs read the roots, the
lexicon, the sign values and the three rival-language files.
"""
import pytest

from tools.paths import LINEAR_A_DATA, SEMITIC_ROOTS_DATA

INPUTS = (
    SEMITIC_ROOTS_DATA / "semitic_correspondences.json",
    SEMITIC_ROOTS_DATA / "semitic_roots.json",
    LINEAR_A_DATA / "sign-registry.json",
    LINEAR_A_DATA / "sign_values.json",
    LINEAR_A_DATA / "corpus.json",
    LINEAR_A_DATA / "lexicon.json",
    LINEAR_A_DATA / "luwian_roots.json",
    LINEAR_A_DATA / "egyptian_roots.json",
    LINEAR_A_DATA / "hurrian_roots.json",
)
MISSING = [p.name for p in INPUTS if not p.exists()]
SHORESH = [pytest.mark.data,
           pytest.mark.skipif(bool(MISSING), reason=f"{', '.join(MISSING)} not in this checkout")]
