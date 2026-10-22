"""The skeleton table labels every value that is not plain Linear B with its standing in sign_values.json.

SIGN_STATUS uses the wiki's three words: resolved (in `resolution_summary`'s resolved lists), proposed (in its proposed
lists) and speculative (held in a sign record only). The live tests read `data/linear-a/sign_values.json` and are
skipped when it is not in the checkout.
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.core.skeleton import SIGN_DECOMPOSITION, SIGN_STATUS
from tools.paths import LINEAR_A_DATA

SIGN_VALUES = LINEAR_A_DATA / "sign_values.json"
ABSENT = pytest.mark.skipif(not SIGN_VALUES.exists(), reason="sign_values.json is not in this checkout")


def LIVE(test):
    """Skipped without sign_values.json, and a `maintainer` test until it ships (`data` after)."""
    return pytest.mark.maintainer(ABSENT(test))
SUBSCRIPTS = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")


def _sign(entry: str) -> str:
    return entry.split("=", 1)[0].strip().translate(SUBSCRIPTS)


def _expected() -> dict[str, str]:
    summary = json.loads(SIGN_VALUES.read_text(encoding="utf-8"))["resolution_summary"]
    status = {_sign(e): "resolved" for e in summary["phonemic"]}
    for p in summary.get("proposed", {}).get("phonemic", []):
        status.setdefault(_sign(p["entry"]), "proposed")
    return status


def test_every_label_is_one_of_the_three_statuses():
    assert set(SIGN_STATUS.values()) <= {"resolved", "proposed", "speculative"}, set(SIGN_STATUS.values())


def test_every_label_names_a_table_sign():
    assert set(SIGN_STATUS) <= set(SIGN_DECOMPOSITION)


@LIVE
def test_labels_match_the_resolution_summary():
    expected = _expected()
    for sign, label in SIGN_STATUS.items():
        assert label == expected.get(sign, "speculative"), sign


@LIVE
def test_every_summary_sign_in_the_table_is_labelled():
    unlabelled = sorted(s for s in _expected() if s in SIGN_DECOMPOSITION and s not in SIGN_STATUS)
    assert not unlabelled, unlabelled
