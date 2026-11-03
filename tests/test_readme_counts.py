"""The count badges at the top of the README match the counts computed from the data.

Each badge is a shields.io static badge, `img.shields.io/badge/<label>-<count>%20<unit>-<colour>` or
`<label>-<count>-<colour>`, so its number is fixed text. These tests recompute every count the way the record's
`counts` page does and fail when a badge has drifted. Nothing here writes.
"""
import json
import re

import pytest

from tools.paths import LINEAR_A_DATA, PRE_GREEK_DATA, REPO, SEMITIC_ROOTS_DATA

# A label's own hyphen is written `--` (shields.io's escape): `Pre--Greek%20words`.
BADGE = re.compile(r"img\.shields\.io/badge/((?:[^-?]|--)+)-([0-9][0-9,]*)(?:%20[^-?]+)?-")
LIVE_FILES = ("corpus.json", "lexicon.json", "translations.json", "onomasticon.json", "unread_words.json",
              "sign_values.json", "census_classes.json")
PRE_GREEK = PRE_GREEK_DATA / "pregreek_lexicon.json"


def badges(readme: str) -> dict[str, int]:
    """Badge label (with %20 read as a space and -- as a hyphen) -> its count."""
    return {label.replace("--", "-").replace("%20", " "): int(count.replace(",", ""))
            for label, count in BADGE.findall(readme)}


def computed() -> dict[str, int]:
    from tools.views import counts, model

    m = model.load(LINEAR_A_DATA)
    complete, _ = counts.translation_counts({k: t["raw"] for k, t in m.translations.items()})
    summary = m.sign_values["resolution_summary"]
    roots = json.loads((SEMITIC_ROOTS_DATA / "semitic_roots.json").read_text(encoding="utf-8"))["roots"]
    pre_greek = json.loads(PRE_GREEK.read_text(encoding="utf-8"))["entries"]
    return {
        "corpus": len(m.corpus),
        "translations": complete,
        "lexicon": len(m.lexicon),
        "names": len(m.onomasticon),
        "Semitic roots": len(roots),
        "Pre-Greek words": len(pre_greek),
        "sign values": (summary["total"] + summary["proposed"]["phonemic_count"]
                        + summary["proposed"]["logogram_count"]),
    }


def test_a_hyphen_in_a_label_reads_as_one():
    readme = ('<img src="https://img.shields.io/badge/Pre--Greek%20words-3,291-e8d9bd?style=flat-square">'
              '<img src="https://img.shields.io/badge/code-Apache--2.0-3a3229?style=flat-square">')
    assert badges(readme) == {"Pre-Greek words": 3291}


@pytest.mark.data
@pytest.mark.skipif(not all((LINEAR_A_DATA / name).exists() for name in LIVE_FILES)
                    or not (SEMITIC_ROOTS_DATA / "semitic_roots.json").exists() or not PRE_GREEK.exists(),
                    reason="the Linear A data, the root database or the Pre-Greek lexicon is not in this checkout")
def test_each_count_badge_matches_the_data():
    shown = badges((REPO / "README.md").read_text(encoding="utf-8"))
    assert shown == computed()
