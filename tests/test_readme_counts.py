"""The count badges at the top of the README match the counts computed from the data.

Each badge is a shields.io static badge, `img.shields.io/badge/<label>-<count>%20<unit>-<colour>` or
`<label>-<count>-<colour>`, so its number is fixed text. These tests recompute every count the way the record's
`counts` page does and fail when a badge has drifted. Nothing here writes.
"""
import json
import re

import pytest

from tools.paths import LINEAR_A_DATA, REPO, SEMITIC_ROOTS_DATA

pytestmark = pytest.mark.data

BADGE = re.compile(r"img\.shields\.io/badge/([^-?]+)-([0-9][0-9,]*)(?:%20[^-?]+)?-")
LIVE_FILES = ("corpus.json", "lexicon.json", "translations.json", "onomasticon.json", "unread_words.json",
              "sign_values.json", "census_classes.json")


def badges(readme: str) -> dict[str, int]:
    """Badge label (with %20 read as a space) -> its count."""
    return {label.replace("%20", " "): int(count.replace(",", "")) for label, count in BADGE.findall(readme)}


def computed() -> dict[str, int]:
    from tools.views import counts, model

    m = model.load(LINEAR_A_DATA)
    complete, _ = counts.translation_counts({k: t["raw"] for k, t in m.translations.items()})
    summary = m.sign_values["resolution_summary"]
    roots = json.loads((SEMITIC_ROOTS_DATA / "semitic_roots.json").read_text(encoding="utf-8"))["roots"]
    return {
        "corpus": len(m.corpus),
        "translations": complete,
        "lexicon": len(m.lexicon),
        "names": len(m.onomasticon),
        "Semitic roots": len(roots),
        "sign values": (summary["total"] + summary["proposed"]["phonemic_count"]
                        + summary["proposed"]["logogram_count"]),
    }


@pytest.mark.skipif(not all((LINEAR_A_DATA / name).exists() for name in LIVE_FILES)
                    or not (SEMITIC_ROOTS_DATA / "semitic_roots.json").exists(),
                    reason="the Linear A data or the root database is not in this checkout")
def test_each_count_badge_matches_the_data():
    shown = badges((REPO / "README.md").read_text(encoding="utf-8"))
    assert shown == computed()
