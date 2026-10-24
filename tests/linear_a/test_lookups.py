"""The Linear A lookups in tools/linear_a/ read data/linear-a/, and name a dataset that is not in the checkout.

Each command runs as a user would run it (a subprocess from the repo root). The unit tests point KAPHTOR_DATA at a
folder written inline; the data tests read the shipped files. Nothing here writes to data/.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools" / "linear_a"

INSCRIPTIONS = {"inscriptions": [
    {"id": "ETEOCRETAN_DREROS_1", "common_name": "Dreros bilingual", "site": "Dreros", "date": "c. 650 BCE",
     "script": "Greek alphabet", "direction": "boustrophedon", "status": "VALID",
     "relationship_to_linear_a": "descendant", "notes": "Read with the Greek text beside it.",
     "gordon_word_readings": [{"form": "TUPRMIRIIA", "meaning": "a cultic term", "constraint": "bilingual"}]},
    {"id": "ETEOCRETAN_PSYCHRO_1", "common_name": "Psychro stone", "site": "Psychro", "status": "PROVEN_FAKE",
     "forgery_evidence": {"debunker": "Duhoux", "publication": "1982", "impact": "Not an ancient text."}},
]}
WORDS = {"words": [
    {"inscription_id": "ETEOCRETAN_DREROS_1", "site": "Dreros", "form": "TUPRMIRIIA", "gordon_meaning": "a cultic term",
     "root": "t-p-r", "constraint_type": "bilingual", "status": "VALID"},
    {"inscription_id": "ETEOCRETAN_PSYCHRO_1", "site": "Psychro", "form": "SANDAI", "gordon_meaning": "lord",
     "root": "s-n-d", "constraint_type": "comparative", "status": "CONTAMINATED_FORGERY",
     "forgery_note": "From the Psychro stone, a modern fake."},
]}
LEXICON = {"entries": [
    {"linear_a": "TU-PA-RA", "meaning": "a cultic term", "confidence": "CANDIDATE", "root": "t-p-r"},
]}
ONOMASTICON = {
    "stats": {"total": 2, "by_affiliation": {"semitic": 1, "unknown": 1}, "by_type": {"theonym": 1, "toponym": 1},
              "by_provenance": {"manual": 2}},
    "entries": [
        {"token": "A-DU", "reading": "ʾAddu", "type": "theonym", "affiliation": "semitic", "frequency": 10,
         "provenance": "manual", "affiliation_evidence": "lexicon_reading", "lexicon_ref": "A-DU", "contact_ref": None},
        {"token": "SU-KI-RI-TA", "reading": "", "type": "toponym", "affiliation": "unknown", "frequency": 3,
         "provenance": "manual", "affiliation_evidence": "none", "lexicon_ref": None, "contact_ref": None},
    ],
}


DATING = {
    "HT13": {"inscription_id": "HT13", "site": "Haghia Triada", "support": "Tablet", "best_period_code": "LMIB",
             "best_date_certainty": "high", "dating_status": "DATED", "dating_basis": "context",
             "best_findspot": "Villa | room 9", "structured_context_code": "LMIB"},
    "ZAZb3": {"inscription_id": "ZAZb3", "site": "Zakros", "support": "Pithos", "best_period_code": "LMIA",
              "best_date_certainty": "low", "dating_status": "DATED", "dating_basis": "style",
              "best_findspot": "", "structured_context_code": ""},
}
CORPUS = {"HT13": {"transliteratedWords": ["KA-U-DE-TA", "KU-RO"]}, "ZAZb3": {"transliteratedWords": ["A-MA-JA"]}}
LB = "Ventris 1952 (projected via Linear B)"
REGISTRY = {"metadata": {"total_signs": 3}, "signs": [
    {"ab_number": "AB01", "name": "da", "rendering": {"unicode": "U+10600"}, "gordon_entries": ["DA-KU-NA"],
     "readings": [{"value": "da", "consonant": "d", "vowel": "a", "source": LB, "confidence": "HIGH",
                   "is_primary": True, "implications": [], "status": "conventional"}]},
    {"ab_number": "AB86", "name": "*86", "rendering": {"unicode": "U+10645"}, "gordon_entries": [],
     "readings": [{"value": "na", "consonant": "n", "vowel": "a", "source": "di Mino", "confidence": "SPECULATIVE",
                   "is_primary": True, "implications": [], "status": "speculative"}]},
    {"ab_number": "AB16", "name": "qa", "rendering": {"unicode": "U+1060F"}, "gordon_entries": [],
     "readings": [{"value": "qa", "consonant": "q", "vowel": "a", "source": LB, "confidence": "HIGH",
                   "is_primary": True, "implications": [], "status": "conventional"},
                  {"value": "za", "consonant": "z", "vowel": "a", "source": "di Mino", "confidence": "LOW",
                   "is_primary": False, "implications": ["Emphatic/sibilant overlap"], "status": "speculative"}]},
]}


def run(script: str, *args: str, data: Path | None = None, cache: Path | None = None) -> subprocess.CompletedProcess:
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    env.pop("KAPHTOR_DATA", None)
    if data is not None:
        env["KAPHTOR_DATA"] = str(data)
    if cache is not None:
        env["XDG_CACHE_HOME"] = str(cache)
    return subprocess.run([sys.executable, str(TOOLS / script), *args], cwd=ROOT, env=env,
                          capture_output=True, text=True, timeout=120)


@pytest.fixture
def data(tmp_path):
    folder = tmp_path / "linear-a"
    folder.mkdir()
    for name, content in [("eteocretan_inscriptions", INSCRIPTIONS), ("eteocretan_word_analysis", WORDS),
                          ("lexicon", LEXICON), ("onomasticon", ONOMASTICON),
                          ("inscription_dating_metadata", DATING), ("corpus", CORPUS), ("sign-registry", REGISTRY)]:
        (folder / f"{name}.json").write_text(json.dumps(content, ensure_ascii=False), encoding="utf-8")
    return tmp_path


def test_eteocretan_counts_leave_the_fake_out(data):
    done = run("eteocretan_lookup.py", "--stats", "--json", data=data)
    assert done.returncode == 0, done.stderr
    stats = json.loads(done.stdout)
    assert (stats["valid_inscriptions"], stats["proven_fakes"]) == (1, 1)
    assert (stats["valid_words"], stats["quarantined_words"], stats["la_root_matches_valid"]) == (1, 1, 1)


def test_eteocretan_shows_notes_and_lexicon_matches(data):
    inscription = run("eteocretan_lookup.py", "--inscription", "DREROS", data=data)
    assert inscription.returncode == 0, inscription.stderr
    assert "Notes: Read with the Greek text beside it." in inscription.stdout
    word = run("eteocretan_lookup.py", "--word", "tuprm", data=data)
    assert "LA match: TU-PA-RA = a cultic term (CANDIDATE)" in word.stdout
    fake = run("eteocretan_lookup.py", "--word", "sandai", data=data)
    assert "QUARANTINED" in fake.stdout and "FORGERY: From the Psychro stone" in fake.stdout


def test_eteocretan_stats_carry_no_process_wording(data):
    done = run("eteocretan_lookup.py", "--stats", data=data)
    assert done.returncode == 0, done.stderr
    assert "reconcil" not in done.stdout.lower() and "campaign" not in done.stdout.lower()
    assert "Lexicon entries with a root: 1" in done.stdout


def test_onomasticon_lookup_reads_the_token_and_filters(data):
    token = run("onomasticon_lookup.py", "--token", "A-DU", "--json", data=data)
    assert token.returncode == 0, token.stderr
    assert json.loads(token.stdout)["reading"] == "ʾAddu"
    unknown = run("onomasticon_lookup.py", "--unknown", data=data)
    assert "SU-KI-RI-TA" in unknown.stdout and "A-DU" not in unknown.stdout
    stats = run("onomasticon_lookup.py", "--stats", data=data)
    assert stats.returncode == 0, stats.stderr
    assert "Corpus Onomasticon — 2 entries" in stats.stdout and "generated" not in stats.stdout


def test_dating_filters_by_period_and_by_a_corpus_form(data):
    period = run("inscription_dating_lookup.py", "--period", "LMIB", "--json", data=data)
    assert period.returncode == 0, period.stderr
    assert [row["inscription_id"] for row in json.loads(period.stdout)] == ["HT13"]
    form = run("inscription_dating_lookup.py", "--chronology-form", "a-ma-ja", "--json", data=data)
    assert [row["inscription_id"] for row in json.loads(form.stdout)] == ["ZAZb3"]
    table = run("inscription_dating_lookup.py", "--inscription", "HT13", data=data)
    assert "| HT13 | Haghia Triada | Tablet | LMIB | high | DATED | context | Villa / room 9 |" in table.stdout


def test_sign_lookup_shows_each_reading_with_its_status(data):
    proposed = run("sign_lookup.py", "AB86", data=data)
    assert proposed.returncode == 0, proposed.stderr
    assert "/na/ [na] — speculative, SPECULATIVE (primary)" in proposed.stdout
    conventional = run("sign_lookup.py", "AB01", data=data)
    assert "/da/ [da] — conventional, HIGH (primary)" in conventional.stdout
    detail = run("sign_lookup.py", "AB16", "--reading", "za", data=data)
    assert "Status: speculative" in detail.stdout and "Confidence: LOW" in detail.stdout


def test_sign_lookup_polyphonic_names_the_status_of_each_value(data):
    done = run("sign_lookup.py", "--polyphonic", data=data)
    assert done.returncode == 0, done.stderr
    assert "/qa/ (conventional) / /za/ (speculative)" in done.stdout
    assert "Semitic decipherment" not in done.stdout


def test_inscription_image_finds_a_record_through_the_file_index(tmp_path):
    data = tmp_path / "data"
    (data / "linear-a").mkdir(parents=True)
    (data / "linear-a" / "corpus.json").write_text(json.dumps({"CRZf1": {"site": "Crete"}}), encoding="utf-8")
    index = {"files": {"CRZf1": {"inscription": ["images/CR(?)Zf1-Inscription.jpg"], "facsimile": []}}}
    (data / "linear-a" / "inscription_image_files.json").write_text(json.dumps(index), encoding="utf-8")
    lashon = tmp_path / "lashon"
    (lashon / "images").mkdir(parents=True)
    (lashon / "images" / "CR(?)Zf1-Inscription.jpg").write_bytes(b"not a real jpeg")
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "KAPHTOR_DATA": str(data),
           "XDG_CACHE_HOME": str(tmp_path / "cache"), "LASHON_HA_KRETAN_DIR": str(lashon)}
    done = subprocess.run([sys.executable, str(TOOLS / "inscription_image.py"), "CRZf1", "--json", "--rebuild"],
                          cwd=ROOT, env=env, capture_output=True, text=True, timeout=120)
    assert done.returncode == 0, done.stderr
    image = json.loads(done.stdout)["records"][0]["images"][0]
    assert (image["relative_path"], image["exists"]) == ("images/CR(?)Zf1-Inscription.jpg", True)
    (data / "linear-a" / "inscription_image_files.json").unlink()
    gone = subprocess.run([sys.executable, str(TOOLS / "inscription_image.py"), "CRZf1", "--rebuild"],
                          cwd=ROOT, env=env, capture_output=True, text=True, timeout=120)
    assert gone.returncode == 2 and "inscription_image_files.json is not in this checkout" in gone.stderr


def test_inscription_image_rebuilds_a_manifest_built_from_other_sources(tmp_path):
    data = tmp_path / "data"
    (data / "linear-a").mkdir(parents=True)
    corpus = data / "linear-a" / "corpus.json"
    corpus.write_text(json.dumps({"CRZf1": {"site": "Crete"}}), encoding="utf-8")
    index = {"files": {"CRZf1": {"inscription": ["images/CRZf1-Inscription.jpg"], "facsimile": []}}}
    (data / "linear-a" / "inscription_image_files.json").write_text(json.dumps(index), encoding="utf-8")
    lashon = tmp_path / "lashon"
    (lashon / "images").mkdir(parents=True)
    (lashon / "images" / "CRZf1-Inscription.jpg").write_bytes(b"not a real jpeg")
    old = tmp_path / "cache" / "kaphtor" / "linear-a" / "inscription_images.json"   # read from the corpus alone
    old.parent.mkdir(parents=True)
    old.write_text(json.dumps({"generated_from": [str(corpus)], "lashon_ha_kretan_dir": str(lashon), "summary": {},
                               "records": {"CRZf1": {"id": "CRZf1", "images": [], "facsimiles": []}}}),
                   encoding="utf-8")
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "KAPHTOR_DATA": str(data),
           "XDG_CACHE_HOME": str(tmp_path / "cache"), "LASHON_HA_KRETAN_DIR": str(lashon)}
    done = subprocess.run([sys.executable, str(TOOLS / "inscription_image.py"), "CRZf1", "--json"],
                          cwd=ROOT, env=env, capture_output=True, text=True, timeout=120)
    assert done.returncode == 0, done.stderr
    assert [i["relative_path"] for i in json.loads(done.stdout)["records"][0]["images"]] == \
        ["images/CRZf1-Inscription.jpg"]


def save_run(cache: Path, run_id: str, words: list[str]) -> None:
    runs = cache / "kaphtor" / "linear-a" / "runs"
    (runs / run_id).mkdir(parents=True)
    provenance = {"run_id": run_id, "run_type": "propagation", "timestamp": f"2026-01-0{len(words)}T00:00:00",
                  "label": None, "parameters": {"min_score": 0.5}, "corpus_hash": "c", "lexicon_hash": "l",
                  "git": {"commit": "abc1234", "dirty": False}, "counts": {"new_candidates": len(words)}}
    results = [{"word": w, "skeleton": "k-r", "best_root": "k-r-y", "best_meaning": "to call", "score": 0.6,
                "status": "new"} for w in words]
    (runs / run_id / "provenance.json").write_text(json.dumps(provenance), encoding="utf-8")
    (runs / run_id / "output.json").write_text(json.dumps({"results": results}), encoding="utf-8")
    index_path = runs / "INDEX.json"
    index = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else {"runs": []}
    index["runs"].append({k: provenance[k] for k in ("run_id", "run_type", "timestamp", "label", "counts")})
    index_path.write_text(json.dumps(index), encoding="utf-8")


def test_saved_runs_list_show_diff_and_export(tmp_path):
    save_run(tmp_path, "run-a", ["KU-RO"])
    save_run(tmp_path, "run-b", ["KU-RO", "KI-RO"])
    listed = run("ventris_runs.py", "list", "--json", cache=tmp_path)
    assert listed.returncode == 0, listed.stderr
    assert [r["run_id"] for r in json.loads(listed.stdout)] == ["run-b", "run-a"]
    shown = run("ventris_runs.py", "show", "run-b", cache=tmp_path)
    assert "Git: abc1234 (clean)" in shown.stdout and "KI-RO" in shown.stdout
    diff = json.loads(run("ventris_runs.py", "diff", "run-a", "run-b", "--json", cache=tmp_path).stdout)
    assert (diff["only_in_a"], diff["only_in_b"]) == ([], ["KI-RO"])
    out = tmp_path / "export.json"
    exported = run("ventris_runs.py", "export", "run-a", "--out", str(out), cache=tmp_path)
    assert exported.returncode == 0, exported.stderr
    assert json.loads(out.read_text(encoding="utf-8"))["results"][0]["word"] == "KU-RO"


def test_a_missing_run_is_named(tmp_path):
    done = run("ventris_runs.py", "show", "nowhere", cache=tmp_path)
    assert done.returncode == 1
    assert "Run 'nowhere' not found in" in done.stderr and str(tmp_path) in done.stderr


@pytest.mark.parametrize(("script", "args", "dataset"), [
    ("eteocretan_lookup.py", ["--stats"], "eteocretan_inscriptions.json"),
    ("onomasticon_lookup.py", ["--stats"], "onomasticon.json"),
    ("inscription_dating_lookup.py", ["--period", "LMIB"], "inscription_dating_metadata.json"),
    ("sign_lookup.py", ["AB01"], "sign-registry.json"),
])
def test_a_missing_dataset_is_named(tmp_path, script, args, dataset):
    done = run(script, *args, data=tmp_path)
    assert done.returncode == 2, (done.stdout, done.stderr)
    assert f"{dataset} is not in this checkout" in done.stderr


@pytest.mark.data
def test_eteocretan_lookup_reads_the_shipped_files():
    done = run("eteocretan_lookup.py", "--stats", "--json")
    assert done.returncode == 0, done.stderr
    stats = json.loads(done.stdout)
    assert (stats["inscription_count"], stats["proven_fakes"], stats["word_count"]) == (10, 1, 27)


@pytest.mark.data
def test_the_sign_registry_labels_its_readings_as_sign_values_does():
    from tools.core.skeleton import SIGN_STATUS
    signs = json.loads((ROOT / "data" / "linear-a" / "sign-registry.json").read_text(encoding="utf-8"))["signs"]
    by_ab = {s["ab_number"]: s for s in signs}
    readings = [(s["ab_number"], r) for s in signs for r in s["readings"]]
    assert {r["status"] for _, r in readings} <= {"conventional", "proposed", "speculative"}
    assert all(r["status"] == "conventional" for _, r in readings if r["source"].startswith("Ventris 1952"))
    assert {r["status"] for r in by_ab["AB86"]["readings"]} == {SIGN_STATUS["*86"]}
    assert {r["status"] for r in by_ab["A325"]["readings"]} == {SIGN_STATUS["*325"]}
    assert [by_ab[ab]["readings"] for ab in ("A701", "A704", "A713")] == [[], [], []]  # fraction signs A, E, O
    assert not [ab for ab, r in readings if r["source"].startswith("Gordon") and r["value"] == "ku"]
    gordon = {w for s in signs for w in s["gordon_entries"]}
    assert "KU-RO" in gordon and "KI-RO" not in gordon and "KU-PA₃-NU" in by_ab["AB56"]["gordon_entries"]


@pytest.mark.data
def test_sign_lookup_reads_the_shipped_registry():
    done = run("sign_lookup.py", "AB86")
    assert done.returncode == 0, done.stderr
    assert "/na/ [na] — speculative" in done.stdout


@pytest.mark.data
def test_onomasticon_lookup_reads_the_shipped_file():
    first = json.loads((ROOT / "data" / "linear-a" / "onomasticon.json").read_text(encoding="utf-8"))["entries"][0]
    done = run("onomasticon_lookup.py", "--token", first["token"], "--json")
    assert done.returncode == 0, done.stderr
    assert json.loads(done.stdout)["token"] == first["token"]
