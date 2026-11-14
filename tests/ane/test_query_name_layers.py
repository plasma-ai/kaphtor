"""query_proper_names reaches the Prosopographia Memphitica, TLA v18, Gauthier DNG and Kassite concordance layers.

Runs the client as a user would (a subprocess from the repo root) on the shipped files. No network.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "tools" / "ane" / "query_proper_names.py"


def run(*args: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    env.pop("KAPHTOR_DATA", None)
    return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=ROOT, env=env,
                          capture_output=True, text=True, timeout=120)


def query(*args: str) -> list[dict]:
    done = run(*args, "--json")
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


def query_text(*args: str) -> list[str]:
    done = run(*args)
    assert done.returncode == 0, done.stderr
    return done.stdout.splitlines()


@pytest.mark.data
def test_prom_person_is_found_by_its_unicode_name():
    rows = query("Ḏḥw.tj-m-ḥꜣb", "--source", "prom", "--layer", "persons", "--exact")
    assert {"prom:person:829", "prom:person:830", "prom:person:831", "prom:person:2399",
            "prom:person:2652"} <= {r["id"] for r in rows}
    assert all(r["match_basis"] == 0 and r["entity_scope"] == "prosopography_entry" for r in rows)


@pytest.mark.data
def test_prom_reads_a_manuel_de_codage_query():
    rows = query("Ra.w-ms", "--source", "prom", "--layer", "persons", "--exact", "--limit", "200")
    assert any(r["id"] == "prom:person:553" and r["match_basis"] == 1 for r in rows)


@pytest.mark.data
def test_prom_title_and_english_rendering_are_searched():
    assert any(r["id"] == "prom:person:859"
               for r in query("ḥꜣ.tj-ꜥ n.j Mn-nfr", "--source", "prom", "--layer", "persons", "--limit", "200"))
    assert "prom\tHr.w-nfr\tperson\tprom:person:859, Hornefer" in query_text(
        "Hornefer", "--source", "prom", "--layer", "persons", "--exact")


@pytest.mark.data
def test_prom_name_row_on_the_name_form_layer():
    rows = query("Ḥr.w-nfr", "--source", "prom", "--layer", "name_forms", "--exact")
    assert any(r["id"] == "prom:name:1467" and r["entity_scope"] == "name_form" for r in rows)


@pytest.mark.data
def test_tla_lemma_is_a_whole_name_on_the_name_form_layer():
    rows = query("Wsꞽr", "--source", "tla", "--layer", "name_forms", "--exact")
    assert [r["id"] for r in rows] == ["tla:49460"]
    assert rows[0]["match_basis"] == 0 and rows[0]["entity_scope"] == "name_lexeme"


@pytest.mark.data
def test_tla_reads_a_j_or_mdc_i_as_its_yod():
    # TLA writes yod ꞽ; PNM and most scholars type j, the Manuel de Codage i. Ꞽmn-m-ḥꜣ.t is two lemmas, the
    # king's name and the private name.
    for typed in ("Jmn-m-ḥꜣ.t", "imn-m-HA.t"):
        rows = query(typed, "--source", "tla", "--layer", "name_forms", "--exact")
        assert sorted((r["id"], r["match_basis"]) for r in rows) == [("tla:400161", 1), ("tla:600435", 1)], typed


@pytest.mark.data
def test_tla_occurrences_are_found_by_their_hieroglyphs():
    rows = query("𓍹𓃹𓈖𓇋𓋴𓍺", "--source", "tla", "--exact", "--limit", "1000")
    assert len(rows) == 644 and {r["tla_lemma_id"] for r in rows} == {"800001"}
    assert all(r["entity_scope"] == "textual_attestation" for r in rows)


@pytest.mark.data
def test_tla_lemma_is_found_by_its_ranke_reference_and_prints_its_class():
    assert any(r["id"] == "tla:400565" for r in query("RPN I 37.19", "--source", "tla", "--layer", "name_forms"))
    lines = query_text("Wnꞽs", "--source", "tla", "--layer", "name_forms", "--exact")
    assert lines[0].startswith("tla\tWnꞽs\troyal name\ttla:800001, ")


@pytest.mark.data
def test_gauthier_entry_is_found_by_its_transcription_and_prints_its_page():
    rows = query("per aht", "--source", "gauthier", "--exact")
    assert [r["id"] for r in rows] == ["gauthier:t2:p50:4"]
    assert rows[0]["match_basis"] == 0 and rows[0]["entity_scope"] == "toponym_lead"
    assert query_text("per aht", "--source", "gauthier", "--exact") == [
        "gauthier\tper aht\tentry\tGauthier DNG t. 2, p. 50 (gauthier:t2:p50:4)"]


@pytest.mark.data
def test_gauthier_description_and_gloss_are_searched():
    # the modern name in the description, and the French gloss
    assert "gauthier:t2:p50:4" in {r["id"] for r in query("El-Achmounein", "--source", "gauthier", "--limit", "200")}
    assert "gauthier:t2:p50:4" in {r["id"] for r in query("de la vache", "--source", "gauthier", "--limit", "200")}


@pytest.mark.data
def test_a_name_only_gauthier_s_ocr_line_holds_is_found_last_and_said_to_be_there():
    # t. 5 p. 9, entry 2: the head runs over two OCR lines, no headword was parsed, and 'SaQ' stands in the OCR
    # line alone
    rows = query("SaQ", "--source", "gauthier", "--limit", "400")
    hit = next(r for r in rows if r["id"] == "gauthier:t5:p9:2")
    assert hit["match_basis"] == 5 and hit["matched_in"] == "raw_text"
    assert [r["match_basis"] for r in rows] == sorted(r["match_basis"] for r in rows)
    assert all("matched_in" not in r for r in rows if r["match_basis"] < 5)
    assert "gauthier:t5:p9:2" not in {r["id"] for r in query("SaQ", "--source", "gauthier", "--exact", "--limit", "400")}
    # a head the OCR glued to stray signs is parsed: t. 1 p. 4, entry 5
    assert query("apd", "--source", "gauthier", "--exact")[0]["id"] == "gauthier:t1:p4:5"


@pytest.mark.data
def test_a_typed_dotted_h_reaches_gauthier_s_marks_and_digits():
    # the OCR gives ḥ as a cluster of marks or a digit, m as 111 and i as 1; the typed letter finds them, in notation
    rows = query("atf-peḥou", "--source", "gauthier", "--exact")
    assert {"atf-pel)ou", "atf-pe~ou", "atf-pe}Jou"} <= {r["transcription"] for r in rows}
    assert all(r["match_basis"] == 1 for r in rows)
    assert any(r["transcription"].startswith("1:).at skhem") for r in query("ḥat skhem", "--source", "gauthier"))
    assert any("Ouza9or" in r["transcription"] for r in query("Ouzaḥor", "--source", "gauthier", "--limit", "50"))
    assert query("atf-pel)ou", "--source", "gauthier", "--exact")[0]["match_basis"] == 0


@pytest.mark.data
def test_gauthier_name_after_its_article_and_a_word_an_addendum_adds():
    assert "gauthier:t2:p29:5" in {r["id"] for r in query("(pa) bkhn", "--source", "gauthier", "--exact")}
    assert "gauthier:t1:p214:9" in {r["id"] for r in query("aat sent", "--source", "gauthier", "--exact")}


@pytest.mark.data
def test_gauthier_has_no_persons_layer():
    done = run("per", "--source", "gauthier", "--layer", "persons", "--json")
    assert done.returncode == 0 and json.loads(done.stdout) == []
    assert "gauthier has no persons layer" in done.stderr


@pytest.mark.data
def test_kassite_concordance_headword_and_page():
    rows = query("A-gi-ia", "--source", "kassite-concordances", "--exact")
    assert any(r["id"] == "clay1912-yos1-058-001" and r["entity_scope"] == "index_entry" for r in rows)
    # A spelling inside the entry (A-qi-ia, a variant Clay prints after the headword) is found as a substring.
    assert any(r["id"] == "clay1912-yos1-058-001" for r in query("A-qi-ia", "--source", "kassite-concordances"))
    assert "kassite-concordances\tA-gi-ia\tperson\tclay1912-yos1 p. 50 (clay1912-yos1-058-001)" in query_text(
        "A-gi-ia", "--source", "kassite-concordances", "--exact")
