"""The clients offer no source this repository does not ship, and the notation of the views that stay is unchanged.

The Sabaic dictionaries, Harding, the Kitāb al-Aṣnām, the Zohar and Pagan's Ebla names are not redistributable here,
so neither ane_keys nor query_proper_names names them. The Egyptian foreign-name index is held too: its rows carry
commentary from the editions they cite. So are Sanmartín's Glossary of Old Syrian, Pentiuc's West Semitic vocabulary
at Emar, Streck's Amorite loanwords and Heimpel's Mari letters. No network.
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ANE = ROOT / "tools" / "ane"
sys.path.insert(0, str(ANE))

from ane_keys import VIEW_NOTATION, expand, parse_query

WITHHELD_VIEWS = ("sabaic", "harding", "asnam", "zohar", "ebla", "glos")


def run(*args: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    env.pop("KAPHTOR_DATA", None)
    return subprocess.run([sys.executable, str(ANE / "query_proper_names.py"), *args], cwd=ROOT, env=env,
                          capture_output=True, text=True, timeout=120)


def test_no_withheld_view_has_a_notation():
    assert [view for view in WITHHELD_VIEWS if view in VIEW_NOTATION] == []


def test_ebla_is_not_a_source():
    done = run("ʿamm", "--source", "ebla")
    assert done.returncode == 2 and "invalid choice" in done.stderr


def test_the_ebla_elements_layer_is_gone():
    done = run("ʿamm", "--layer", "elements")
    assert done.returncode == 2 and "invalid choice" in done.stderr


def test_all_sources_do_not_mention_ebla():
    done = run("dd-tw", "--layer", "name_forms", "--json")
    assert done.returncode == 0, done.stderr
    assert "ebla" not in done.stderr.lower()


def test_egyptian_is_not_a_source():
    done = run("Knossos", "--source", "egyptian")
    assert done.returncode == 2 and "invalid choice" in done.stderr


def test_all_sources_do_not_mention_the_egyptian_index():
    # The attestation layer is the one the Egyptian index fed.
    done = run("Knossos", "--layer", "attestations", "--json")
    assert done.returncode == 0, done.stderr
    assert "egyptian" not in done.stderr.lower()


def test_the_views_that_stay_spell_queries_as_before():
    # Recorded from ane_keys before the withheld views were removed.
    expected = {
        ("ʾ-n-s¹", "dasi"): {"ʾ-n-s¹", "ʾns¹"},
        ("sbk-Htp", "pnm"): {"sbk-htp", "sbk-ḥtp"},
        ("m-n-y", "quran"): {"m-n-y", "mny"},
        ("kns", "ahi"): {"kns"},
        ("ʾ-ṯ-r", "epi"): {"ʾṯr"},
        ("shms", "epi"): {"shms", "šms"},
        ("כנש", "aramaic"): {"knś", "knš"},
    }
    for (query, view), keys in expected.items():
        assert expand(parse_query(query), view) == keys, (query, view)
