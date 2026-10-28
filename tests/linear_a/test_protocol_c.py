"""Protocol C's port (tools/linear_a/validation/protocol_c.py): the redaction and the blindness audit on inline logs,
the shipped record verifying against its hashes, a ledger that ships no replaced string, a changed byte, a missing
file, a kept command output or a private path in the ledger failing verification, and the C1 checker and audits
rerunning on the files as shipped. Maintainer tests, given the key (KAPHTOR_PROTOCOL_C_KEY) and the full logs
(KAPHTOR_PROTOCOL_C_TRANSCRIPTS), restore the research bytes. The commands run in subprocesses; a test that changes a
file does it in a copy under tmp_path, pointed at by KAPHTOR_DATA.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tools.linear_a.validation import protocol_c as pc
from tools.paths import LINEAR_A_DATA

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "tools" / "linear_a" / "validation" / "protocol_c.py"
RUNNER = REPO / "tools" / "core" / "frozen" / "protocol_c" / "scripts" / "run_builder.sh"
HAS_JSONSCHEMA = importlib.util.find_spec("jsonschema") is not None
NEEDS_JSONSCHEMA = pytest.mark.skipif(not HAS_JSONSCHEMA, reason="needs jsonschema (the protocol-c extra)")
# a maintainer's folder of the builders' full logs, <arm>/transcript.jsonl, and the key of the strings the port
# replaced; neither is shipped
TRANSCRIPTS = os.environ.get("KAPHTOR_PROTOCOL_C_TRANSCRIPTS")
KEY = os.environ.get("KAPHTOR_PROTOCOL_C_KEY")
NEEDS_KEY = pytest.mark.skipif(not (KEY and Path(KEY).is_file()),
                               reason="the maintainer's key is not in this checkout (KAPHTOR_PROTOCOL_C_KEY)")
KIT = "/Volumes/kit/zz"


def run(*args: str, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, cwd=REPO,
                          env={**os.environ, **(env or {})}, timeout=600)


def command_event(command: str, output: str = "") -> str:
    return json.dumps({"type": "item.completed", "item": {"id": "item_1", "type": "command_execution",
                                                          "command": command, "aggregated_output": output,
                                                          "exit_code": 0, "status": "completed"}})


def copy_record(tmp_path: Path, corpus: bool = False) -> Path:
    data = tmp_path / "data"
    shutil.copytree(LINEAR_A_DATA / "protocol-c", data / "linear-a" / "protocol-c")
    if corpus:
        shutil.copy2(LINEAR_A_DATA / "corpus.json", data / "linear-a" / "corpus.json")
    return data


def test_redact_replaces_each_output_by_its_hash_and_length_and_writes_the_kit_as_a_variable():
    out = json.loads(pc.redact(command_event(f"cat {KIT}/units.md", "Tabelle 1\n"), KIT))
    item = out["item"]
    assert "aggregated_output" not in item
    assert item["output_sha256"] == hashlib.sha256(b"Tabelle 1\n").hexdigest() and item["output_bytes"] == 10
    assert item["command"] == "cat $KIT/units.md"
    with pytest.raises(ValueError):
        pc.redact_log(command_event("echo $KIT").encode(), KIT)


def test_the_audit_flags_a_path_outside_the_kit_and_passes_one_inside(tmp_path):
    program = pc.audit_source(RUNNER.read_text(encoding="utf-8"))
    log = "\n".join([command_event(f"cat {KIT}/units.md"), command_event("cat /Volumes/other/corpus.json"),
                     command_event("sed -n 1,5p ../lexicon.json")]) + "\n"
    out = pc.rerun_audit(program, log.encode(), KIT, tmp_path).decode("utf-8")
    assert "commands: 3" in out
    assert "paths outside the kit: 2" in out
    assert "OUTSIDE '/Volumes/other/corpus.json'" in out
    assert "OUTSIDE '../lexicon.json'" in out


@pytest.mark.data
def test_verify_passes_on_the_shipped_record():
    result = run("verify")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "verify: PASS" in result.stdout
    assert "signed text: 5a7b442c02336f31058a7fc51da7ecc382ff86eb6cdef7783883de108ed41ea0" in result.stdout


@pytest.mark.data
def test_the_ledger_ships_no_replaced_string():
    ledger = pc.load_ledger()
    for row in ledger["files"] + ledger["derived"]:
        for sub in row["substitutions"]:
            assert set(sub) == {"new", "count"}, row["path"]


@pytest.mark.data
def test_verify_names_a_private_path_in_the_ledger(tmp_path):
    data = copy_record(tmp_path)
    ledger = data / "linear-a" / "protocol-c" / "PORT-LEDGER.json"
    raw = json.loads(ledger.read_text(encoding="utf-8"))
    raw["_meta"]["what"] += " /Users" + "/someone/research"
    ledger.write_text(json.dumps(raw, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    result = run("verify", env={"KAPHTOR_DATA": str(data)})
    assert result.returncode == 1, result.stdout + result.stderr
    assert "FAIL data/linear-a/protocol-c/PORT-LEDGER.json: names /Users/" in result.stdout


@pytest.mark.data
def test_verify_names_a_changed_byte(tmp_path):
    data = copy_record(tmp_path)
    target = data / "linear-a" / "protocol-c" / "builds" / "cs" / "inventory.json"
    target.write_bytes(target.read_bytes().replace(b'"cs"', b'"CS"', 1))
    result = run("verify", env={"KAPHTOR_DATA": str(data)})
    assert result.returncode == 1, result.stdout + result.stderr
    assert "FAIL data/linear-a/protocol-c/builds/cs/inventory.json" in result.stdout


@pytest.mark.data
def test_verify_stops_when_a_shipped_file_is_missing(tmp_path):
    data = copy_record(tmp_path)
    (data / "linear-a" / "protocol-c" / "builds" / "yd" / "notes.md").unlink()
    result = run("verify", env={"KAPHTOR_DATA": str(data)})
    assert result.returncode == 2
    assert "builds/yd/notes.md is not in this checkout" in result.stderr


@pytest.mark.data
def test_verify_refuses_a_redacted_log_that_keeps_a_command_output(tmp_path):
    data = copy_record(tmp_path)
    log = data / "linear-a" / "protocol-c" / "builds" / "luwian" / "transcript.redacted.jsonl"
    lines = log.read_text(encoding="utf-8").splitlines(True)
    n = next(i for i, line in enumerate(lines) if '"command_execution"' in line)
    event = json.loads(lines[n])
    event["item"]["aggregated_output"] = "a grammar's page"
    lines[n] = json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n"
    log.write_text("".join(lines), encoding="utf-8")
    result = run("verify", env={"KAPHTOR_DATA": str(data)})
    assert result.returncode == 1, result.stdout + result.stderr
    assert f"transcript.redacted.jsonl: line {n + 1} keeps a command output" in result.stdout


@pytest.mark.data
@NEEDS_JSONSCHEMA
def test_reproduce_reruns_the_checker_and_the_audits_byte_for_byte():
    result = run("reproduce")
    out = result.stdout
    assert result.returncode == 0, out + result.stderr
    assert "corpus.json: 1070 hyphenated words, sha256 e60a13f086fc… (as recorded)" in out
    assert "on the files as shipped" in out
    assert out.count("inventory.filled.json byte for byte") == 6
    assert out.count("blindness_audit.txt byte for byte from the redacted log") == 6
    # the cut name shortens one command the yd audit truncates; its counts and OUTSIDE lines still match
    assert "yd: blindness_audit.txt verdict as recorded from the redacted log (commands: 21 paths outside the kit: 0)" \
        in out
    assert "greek inventory.v1.json: refused, as recorded (greek_274: corpus word 'a-i')" in out
    assert "reproduce: PASS" in out


@pytest.mark.data
@NEEDS_JSONSCHEMA
def test_the_checker_fails_an_inventory_that_drops_units(tmp_path):
    ledger = pc.load_ledger()
    checker = pc.load_checker(ledger, tmp_path)
    folder = tmp_path / "cs"
    folder.mkdir()
    for name in pc.CHECK_INPUTS:
        (folder / name).write_bytes(pc.restored_file(ledger, f"protocol-c/builds/cs/{name}"))
    inv = json.loads((folder / "inventory.json").read_text(encoding="utf-8"))
    dropped = set(inv["units_read"][-2:])
    inv["units_read"] = inv["units_read"][:-2]
    (folder / "inventory.json").write_text(json.dumps(inv, ensure_ascii=False), encoding="utf-8")
    (folder / "transcript.jsonl").write_bytes((LINEAR_A_DATA / "protocol-c/builds/cs/transcript.redacted.jsonl")
                                              .read_bytes())
    rc, out = pc.run_checker(checker, folder)
    assert rc == 1 and "FAIL" in out
    assert "[coverage]" in out and any(unit in out for unit in dropped)
    assert not (folder / "inventory.filled.json").exists()


@pytest.mark.data
@NEEDS_JSONSCHEMA
def test_reproduce_catches_a_read_outside_the_kit_added_to_a_log(tmp_path):
    data = copy_record(tmp_path, corpus=True)
    log = data / "linear-a" / "protocol-c" / "builds" / "cs" / "transcript.redacted.jsonl"
    with log.open("a", encoding="utf-8") as f:
        f.write(pc.redact(command_event("cat ~/corpus.json"), KIT))
    result = run("reproduce", "--arm", "cs", env={"KAPHTOR_DATA": str(data)})
    assert result.returncode == 1, result.stdout + result.stderr
    assert "cs: blindness_audit.txt DIFFERS from the redacted log" in result.stdout


@pytest.mark.maintainer
@NEEDS_KEY
def test_the_key_restores_every_file_and_the_signed_text():
    result = run("verify", "--key", KEY)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "substitutions undone from the key" in result.stdout
    assert "(SIGNATURE.txt; restored and checked)" in result.stdout


@pytest.mark.maintainer
@NEEDS_KEY
def test_a_wrong_key_fails_verify(tmp_path):
    key = json.loads(Path(KEY).read_text(encoding="utf-8"))
    path = "data/linear-a/protocol-c/PROTOCOL-C-SIGNED-2026-10-29.md"
    key["originals"][path][0] += " "
    wrong = tmp_path / "key.json"
    wrong.write_text(json.dumps(key, ensure_ascii=False), encoding="utf-8")
    result = run("verify", "--key", str(wrong))
    assert result.returncode == 1, result.stdout + result.stderr
    assert f"FAIL {path}: restored sha256" in result.stdout
    assert "FAIL the signed text restores to" in result.stdout


@pytest.mark.maintainer
@pytest.mark.skipif(not (TRANSCRIPTS and Path(TRANSCRIPTS).is_dir()),
                    reason="the builders' full logs are not in this checkout (KAPHTOR_PROTOCOL_C_TRANSCRIPTS)")
@NEEDS_KEY
@NEEDS_JSONSCHEMA
def test_the_full_logs_hash_as_recorded_and_redact_to_the_shipped_logs():
    result = run("reproduce", "--key", KEY, "--transcripts", TRANSCRIPTS)
    out = result.stdout
    assert result.returncode == 0, out + result.stderr
    assert out.count("blindness_audit.txt byte for byte from the redacted log") == 7
    assert out.count("at its recorded sha256; its redaction is the shipped log") == 7


@NEEDS_JSONSCHEMA
def test_transcripts_need_the_key():
    result = run("reproduce", "--transcripts", "/nonexistent")
    assert result.returncode == 2, result.stdout + result.stderr
    assert "--transcripts compares the full logs with the restored redactions: it needs --key" in result.stderr
