"""The `kaphtor` command: the gate passes only when every step is built and passes, and names each one.

The gate's own steps include this suite, so these tests hand it stand-in steps. Nothing here writes outside tmp_path.
"""
import importlib
import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
import yaml

from tools.cli import main as cli

REPO = Path(__file__).resolve().parents[1]
CONFIG = REPO / ".pre-commit-config.yaml"
PASS = [sys.executable, "-c", "pass"]
FAIL = [sys.executable, "-c", "raise SystemExit(3)"]
# The pre-commit-hooks and ruff hooks that rewrite the files they are given.
FIXERS = {"trailing-whitespace", "end-of-file-fixer", "mixed-line-ending", "fix-byte-order-marker",
          "requirements-txt-fixer", "sort-simple-yaml", "file-contents-sorter", "double-quote-string-fixer",
          "ruff-format"}


def line(status: str, name: str) -> re.Pattern:
    return re.compile(rf"^{status}\s+{name}\b", re.MULTILINE)


def test_the_gate_passes_when_every_step_passes(capsys):
    assert cli.gate([("one", PASS), ("two", PASS)]) == 0
    out = capsys.readouterr().out
    assert line("ok", "one").search(out) and line("ok", "two").search(out)


def test_a_failing_step_fails_the_gate_and_the_rest_still_run(capsys):
    assert cli.gate([("one", FAIL), ("two", PASS)]) == 1
    out = capsys.readouterr().out
    assert line("FAILED", "one").search(out) and line("ok", "two").search(out)
    assert "(exit 3)" in out


def test_a_step_not_yet_built_fails_the_gate_by_name(capsys):
    assert cli.gate([("one", PASS), ("licence audit", None)]) == 1
    assert line("not built", "licence audit").search(capsys.readouterr().out)


def test_a_missing_program_fails_its_step_with_no_traceback(capsys):
    assert cli.gate([("lint", ["kaphtor-no-such-program", "lint"])]) == 1
    assert "missing program kaphtor-no-such-program" in capsys.readouterr().out


def test_gate_list_names_every_step_and_runs_none(capsys):
    assert cli.main(["gate", "--list"]) == 0
    out = capsys.readouterr().out
    for name, _ in cli.GATE:
        assert name in out


def test_empty_folders_lists_each_one_and_fails(tmp_path, capsys):
    (tmp_path / "library" / "greek").mkdir(parents=True)
    (tmp_path / "library" / "greek" / "_index.md").write_text("---\ntitle: Greek\n---\n\nEmpty until a later wave.\n")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "anatomy.md").write_text("# Anatomy\n\nFilled.\n")
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "README.md").write_text("Empty until a later wave.\n")
    assert cli.empty_folders(tmp_path) == 1
    out = capsys.readouterr().out
    assert "library/greek/_index.md" in out
    assert "anatomy" not in out and ".venv" not in out


def test_empty_folders_passes_when_every_folder_is_filled(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "anatomy.md").write_text("# Anatomy\n\nFilled.\n")
    assert cli.empty_folders(tmp_path) == 0


def test_the_gate_checks_for_empty_folders():
    assert any(command and command[-1] == "empty-folders" for _, command in cli.GATE)


def put(root: Path, files: dict[str, str]) -> list[str]:
    """Write each file under root and return the paths, as the tracked-file list the checks are given."""
    for path, text in files.items():
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_text(text, encoding="utf-8")
    return sorted(files)


def test_every_gate_step_is_built():
    assert [name for name, command in cli.GATE if command is None] == []
    assert {"index coverage", "licence audit"} <= {name for name, _ in cli.GATE}


def test_index_coverage_names_each_folder_of_two_files_without_an_index(tmp_path, capsys):
    files = put(tmp_path, {"_index.md": "x\n", "a/one.py": "", "a/two.py": "", "b/README.md": "x\n", "b/one.py": "",
                           "c/only.py": "", "d/_index.md": "x\n", "d/e/one.json": "", "d/e/two.json": ""})
    assert cli.index_coverage(tmp_path, files) == 1
    out = capsys.readouterr().out
    assert "a\n" in out and "d/e\n" in out
    assert "b\n" not in out and "c\n" not in out


def test_index_coverage_passes_when_every_folder_has_an_index(tmp_path):
    files = put(tmp_path, {"_index.md": "x\n", "README.md": "x\n", "a/README.md": "x\n", "a/one.py": ""})
    assert cli.index_coverage(tmp_path, files) == 0


SHEET = "---\nname: x\nlicense: CC BY 4.0\n---\n\n"


def test_licence_audit_accepts_each_way_a_data_file_names_its_licence(tmp_path):
    files = put(tmp_path, {
        "data/la/lexicon.json": "{}", "data/la/lexicon.md": SHEET,                       # its own datasheet
        "data/la/eteo_words.json": "{}", "data/la/eteo.md": SHEET,                       # a datasheet named for the set
        "data/sr/table.json": "{}", "data/sr/roots.md": SHEET + "`table.json` is …\n",   # a datasheet that names it
        "data/sr/roots.json": "{}",
        "data/ane/pnm/tables/t.jsonl": "", "data/ane/pnm/_index.md": SHEET,               # a parent index
        "data/ane/places/p.jsonl": "", "data/ane/places/MANIFEST.json": '{"a": {"b": {"license": "CC BY 3.0"}}}',
        "data/_index.md": "---\nname: data\n---\n",
    })
    assert cli.licence_audit(tmp_path, files) == 0


def test_licence_audit_names_each_data_file_with_no_licence(tmp_path, capsys):
    files = put(tmp_path, {
        "data/ane/glossary.jsonl": "", "data/ane/glossary.index.json": "{}",
        "data/ane/_index.md": "---\nname: data/ane\n---\n",
        "data/la/x.json": "{}", "data/la/x.md": "---\nname: x\n---\n\n`x.json`\n",      # a datasheet with no licence
        "data/la/y.json": "{}", "data/la/y.md": SHEET,
        "data/ane/MANIFEST.json": '{"title": "no licence here"}',
        "docs/z.json": "{}",                                                             # outside data/: not audited
    })
    assert cli.licence_audit(tmp_path, files) == 1
    out = capsys.readouterr().out
    for path in ("data/ane/glossary.jsonl", "data/ane/glossary.index.json", "data/la/x.json"):
        assert path in out
    assert "data/la/y.json" not in out and "docs/z.json" not in out and "MANIFEST" not in out


def gate_hooks() -> tuple[str, list[tuple[str, dict]]]:
    """The stage the gate runs pre-commit at, and each (repo, hook) of the config that runs at that stage."""
    (command,) = [command for _, command in cli.GATE if command and command[0] == "pre-commit"]
    stage = command[command.index("--hook-stage") + 1] if "--hook-stage" in command else "pre-commit"
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    default = config.get("default_stages", [stage])
    return stage, [(repo["repo"], hook) for repo in config["repos"] for hook in repo["hooks"]
                   if stage in hook.get("stages", default)]


def test_the_gate_runs_no_fixer():
    assert [name for name, command in cli.GATE if command and "--fix" in command] == []
    _, hooks = gate_hooks()
    assert [hook["id"] for _, hook in hooks if hook["id"] in FIXERS or "--fix" in hook.get("args", [])] == []
    assert "ruff-check" in {hook["id"] for _, hook in hooks}


def test_the_gates_local_hooks_flag_whitespace_and_rewrite_nothing(tmp_path):
    # the gate's local hooks in a scratch repository, with a cache of its own: nothing is fetched
    stage, hooks = gate_hooks()
    config = tmp_path / "config.yaml"
    config.write_text(yaml.safe_dump({"repos": [{"repo": "local", "hooks": [h for r, h in hooks if r == "local"]}]}))
    files = {
        "tools/trailing_space.py": b"x = 1 \n",
        "tools/trailing_tab_crlf.txt": b"a\t\r\nb\r\n",
        "tools/trailing_cr.txt": b"a\r\r\n",
        "tools/no_final_newline.txt": b"a\nb",
        "tools/two_final_newlines.md": b"# A\n\n",
        "tools/only_newlines.txt": b"\n\n",
        "tools/clean.txt": b"a\n\nb\n",
        "tools/clean_crlf.txt": b"a\r\nb\r\n",
        "tools/clean_empty.txt": b"",
    }
    work = tmp_path / "work"
    for path, data in files.items():
        (work / path).parent.mkdir(parents=True, exist_ok=True)
        (work / path).write_bytes(data)
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env["PRE_COMMIT_HOME"] = str(tmp_path / "pc")
    subprocess.run(["git", "init", "-q"], cwd=work, env=env, check=True)
    subprocess.run(["git", "add", "."], cwd=work, env=env, check=True)
    run = subprocess.run([sys.executable, "-m", "pre_commit", "run", "--all-files", "--hook-stage", stage,
                          "--config", str(config)], cwd=work, env=env, capture_output=True, text=True)
    assert run.returncode == 1, run.stdout + run.stderr
    for path, data in files.items():
        assert (work / path).read_bytes() == data, f"{path} was rewritten"
        assert (path in run.stdout) == ("clean" not in path), f"{path}\n{run.stdout}"


def test_reproduce_stops_and_names_its_guide(capsys):
    assert cli.main(["reproduce", "--quick"]) == 2
    assert "docs/reproduce.md" in capsys.readouterr().err


def test_no_subcommand_is_a_usage_error():
    with pytest.raises(SystemExit) as e:
        cli.main([])
    assert e.value.code == 2


def test_the_kaphtor_script_points_at_this_main():
    scripts = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))["project"]["scripts"]
    module, _, name = scripts["kaphtor"].partition(":")
    assert getattr(importlib.import_module(module), name) is cli.main
