"""The kaphtor command.

    kaphtor gate [--list]        run the repository's checks in order; fail unless every one is built and passes
    kaphtor reproduce [--quick]  rerun the headline numbers (not built yet)

The gate runs every step even after one fails, then prints one line per step. A step that is not built yet fails the
gate by name, so a passing gate means every check ran.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

from ..paths import LINEAR_A_DATA

REPO = Path(__file__).resolve().parents[2]

# (name, command): run from the repository root. A step with no command is not built yet. Every step checks and none
# writes: the pre-commit step runs the manual stage, which holds the hooks' check-only forms (.pre-commit-config.yaml).
GATE: list[tuple[str, list[str] | None]] = [
    ("tests", [sys.executable, "-m", "pytest", "-q"]),
    ("pre-commit hooks", ["pre-commit", "run", "--all-files", "--hook-stage", "manual"]),
    ("generated pages", [sys.executable, "-m", "tools.views.build", "--data", str(LINEAR_A_DATA), "--out", "wiki"]),
    ("census blocks", [sys.executable, "-m", "tools.views.census_doc", "--data", str(LINEAR_A_DATA)]),
    ("wiki lint", ["wiki", "lint"]),
    ("no empty folders", [sys.executable, "-m", "tools.cli.main", "empty-folders"]),
    ("index coverage", [sys.executable, "-m", "tools.cli.main", "index-coverage"]),
    ("licence audit", [sys.executable, "-m", "tools.cli.main", "licence-audit"]),
]


def gate(steps: list[tuple[str, list[str] | None]]) -> int:
    """Run each step and print its result; 0 only when every step is built and passes."""
    results = []
    for name, command in steps:
        if command is None:
            results.append(("not built", name, ""))
            continue
        print(f"== {name}: {' '.join(command)}", flush=True)
        try:
            code = subprocess.run(command, cwd=REPO, check=False).returncode
        except FileNotFoundError:
            results.append(("MISSING", name, f"missing program {command[0]}"))
            continue
        results.append(("ok", name, "") if code == 0 else ("FAILED", name, f"exit {code}"))
    print()
    for status, name, detail in results:
        print(f"{status:<10} {name}" + (f" ({detail})" if detail else ""))
    return 0 if all(status == "ok" for status, _, _ in results) else 1


EMPTY = "Empty until a later wave"  # the line an index or README carries while its folder holds nothing yet
SKIP = {".git", ".venv", "__pycache__", ".pytest_cache"}


def empty_folders(root: Path = REPO) -> int:
    """List every index or README whose folder is still empty; 0 only when there is none."""
    found = sorted(p.relative_to(root).as_posix() for p in root.rglob("*.md")
                   if not SKIP & set(p.relative_to(root).parts) and EMPTY in p.read_text(encoding="utf-8"))
    for path in found:
        print(path)
    if found:
        print(f"{len(found)} empty folder(s): fill each or leave it out of the release")
    return 1 if found else 0


INDEXES = {"_index.md", "README.md"}


def tracked_files(root: Path = REPO) -> list[str]:
    """The files git tracks or would add (ignored files left out), as paths relative to root."""
    out = subprocess.run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], cwd=root,
                         capture_output=True, check=True).stdout.decode("utf-8")
    return sorted({p for p in out.split("\0") if p and (root / p).is_file()})


def index_coverage(root: Path = REPO, files: list[str] | None = None) -> int:
    """List every folder that holds two or more files and no `_index.md` or `README.md`; 0 only when there is none."""
    folders: dict[str, set[str]] = {}
    for path in tracked_files(root) if files is None else files:
        folder, _, name = path.rpartition("/")
        folders.setdefault(folder or ".", set()).add(name)
    found = sorted(folder for folder, names in folders.items() if len(names) >= 2 and not names & INDEXES)
    for folder in found:
        print(folder)
    if found:
        print(f"{len(found)} folder(s) of two or more files with no _index.md or README.md")
    return 1 if found else 0


def frontmatter(text: str) -> dict[str, str]:
    """The `key: value` lines of a page's frontmatter (the block between the opening `---` lines)."""
    if not text.startswith("---\n"):
        return {}
    head = text[4:].split("\n---", 1)[0]
    return {k.strip(): v.strip() for k, sep, v in (line.partition(":") for line in head.splitlines()) if sep}


def names_a_licence(value: object) -> bool:
    """Whether a manifest holds a non-empty `license` or `licence` key at any depth."""
    if isinstance(value, dict):
        return any(("licen" in key.lower() and isinstance(v, str) and v.strip()) or names_a_licence(v)
                   for key, v in value.items())
    return isinstance(value, list) and any(names_a_licence(v) for v in value)


def licence_audit(root: Path = REPO, files: list[str] | None = None) -> int:
    """List every data file under `data/` whose licence no datasheet, index or manifest names; 0 when there is none.

    A data file is covered by a datasheet beside it that has a `license` key and either is named for it (`lexicon.md`
    for `lexicon.json`, `eteocretan.md` for `eteocretan_words.json`) or names it in its text; or by an `_index.md`
    with a `license` key, or a `MANIFEST.json` naming a licence, in its folder or a parent folder under `data/`.
    """
    files = tracked_files(root) if files is None else files
    present = set(files)

    def text(path: str) -> str:
        return (root / path).read_text(encoding="utf-8")

    def covered(path: str) -> bool:
        folder, _, name = path.rpartition("/")
        for sheet in files:
            sheet_folder, _, sheet_name = sheet.rpartition("/")
            if sheet_folder != folder or not sheet_name.endswith(".md") or sheet_name in INDEXES:
                continue
            body = text(sheet)
            if frontmatter(body).get("license") and (name.startswith(sheet_name[:-3]) or f"`{name}`" in body):
                return True
        while folder.startswith("data"):
            index, manifest = f"{folder}/_index.md", f"{folder}/MANIFEST.json"
            if index in present and frontmatter(text(index)).get("license"):
                return True
            if manifest in present and names_a_licence(json.loads(text(manifest))):
                return True
            folder = folder.rpartition("/")[0]
        return False

    found = [path for path in files if path.startswith("data/") and not path.endswith(".md")
             and not path.endswith("/MANIFEST.json") and not covered(path)]
    for path in found:
        print(path)
    if found:
        print(f"{len(found)} data file(s) whose licence no datasheet, index or manifest names")
    return 1 if found else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="kaphtor", description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    gate_cmd = sub.add_parser("gate", help="run the repository's checks")
    gate_cmd.add_argument("--list", action="store_true", help="name each step and whether it is built; run none")
    reproduce = sub.add_parser("reproduce", help="rerun the headline numbers")
    reproduce.add_argument("--quick", action="store_true", help="the short run")
    sub.add_parser("empty-folders", help="list the folders that hold nothing yet")
    sub.add_parser("index-coverage", help="list the folders of two or more files with no index")
    sub.add_parser("licence-audit", help="list the data files whose licence nothing names")
    args = parser.parse_args(argv)
    if args.command == "empty-folders":
        return empty_folders()
    if args.command == "index-coverage":
        return index_coverage()
    if args.command == "licence-audit":
        return licence_audit()
    if args.command == "gate":
        if args.list:
            for name, command in GATE:
                print(f"{'built' if command else 'not built':<10} {name}")
            return 0
        return gate(GATE)
    print("stopped: kaphtor reproduce is not built yet; docs/reproduce.md says what it will rerun", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
