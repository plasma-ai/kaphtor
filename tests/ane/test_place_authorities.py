"""query_place_authorities: the folded tier joins whenever nothing matches as a whole label, as in query_proper_names,
and the client offers no crosswalk view, since the crosswalks do not ship.

Runs the client on a two-row Pleiades fixture under KAPHTOR_DATA. No network.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLIENT = ROOT / "tools" / "ane" / "query_place_authorities.py"

PLACES = [
    {"authority_id": "1", "title": "Tell el-Amarna"},        # the whole name, once - is folded
    {"authority_id": "2", "title": "Tell el Amarna North"},  # the query as typed, inside a longer name
]


def run(data: Path, *args: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "KAPHTOR_DATA": str(data)}
    return subprocess.run([sys.executable, str(CLIENT), *args], cwd=ROOT, env=env, capture_output=True, text=True,
                          timeout=60)


def fixture(tmp_path: Path) -> Path:
    folder = tmp_path / "ane" / "place-authorities"
    folder.mkdir(parents=True)
    (folder / "pleiades_places.jsonl").write_text("".join(json.dumps(row) + "\n" for row in PLACES), encoding="utf-8")
    return tmp_path


def test_a_substring_hit_does_not_keep_out_a_folded_whole_name(tmp_path):
    done = run(fixture(tmp_path), "Tell el Amarna", "--authority", "pleiades", "--json")
    assert done.returncode == 0, done.stderr
    rows = json.loads(done.stdout)
    assert [(row["authority_id"], row["match_basis"]) for row in rows] == [("1", 2), ("2", 4)]


def test_a_whole_label_match_keeps_the_fold_out(tmp_path):
    done = run(fixture(tmp_path), "Tell el-Amarna", "--authority", "pleiades", "--json")
    assert done.returncode == 0, done.stderr
    assert [row["authority_id"] for row in json.loads(done.stdout)] == ["1"]


def test_there_is_no_crosswalk_view(tmp_path):
    done = run(fixture(tmp_path), "Knossos", "--crosswalk")
    assert done.returncode == 2 and "unrecognized arguments: --crosswalk" in done.stderr
