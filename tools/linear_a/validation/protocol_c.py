#!/usr/bin/env python3
"""Protocol C, the pre-registered blind-inventory test: check the shipped C0 and C1 record against its hashes and
rerun the C1 checks.

  uv run tools/linear_a/validation/protocol_c.py verify [--key KEY]
  uv run --extra protocol-c tools/linear_a/validation/protocol_c.py reproduce [--arm ARM] [--key KEY]
      [--transcripts DIR]

The record is in data/linear-a/protocol-c/, the C1 scripts in tools/core/frozen/protocol_c/, the protocol in
docs/protocol-c-preregistration.md. PORT-LEDGER.json gives each shipped file's path and sha256 in the research tree,
what pins that hash (a build's SHA256SUMS or kit.sha256, the C1 manifest, SIGNATURE.txt, or the port) and the text
each of the port's substitutions wrote, with its count; each redacted builder log with the sha256 of the full log it
was derived from; and each hashed file the port withholds (the grammar copies, the Ya Diktu PDF). The strings the
substitutions replaced (private paths, private source ids, the maintainer's first name) are not shipped: they are in
the maintainer's key, which reviewers may ask for.

verify checks every shipped file's sha256 and each substitution's count, and the research-tree sha256 of every file
the port left unchanged; with --key it undoes each file's substitutions and checks every file against its
research-tree sha256, the signed text against SIGNATURE.txt (5a7b442c…) and the protocol against the ledger. It
accounts for every line of every build's SHA256SUMS and kit.sha256 as shipped, derived or withheld; checks each
inventory.filled.json against the C1 manifest; checks each kit against C0 (units.md is its table, BRIEF.md and
schema.json are the C0 files, protocol.md is the protocol's extract at the arm's amendment level, the probe answered
NONE/no/no); and checks that no redacted log keeps a command output and that no shipped file names a private path, a
private source id, the maintainer's first name or an email address.

reproduce imports check_inventory.py, points it at data/linear-a/corpus.json (which must yield the recorded 1,070
hyphenated words), and reruns it on each build in a temporary folder: every inventory.filled.json must come out byte
for byte, and the greek builder's first inventory must be refused as it was. It then reruns the blindness audit cut
from run_builder.sh on each redacted log, which must give the shipped audit byte for byte; where the port's
substitutions shorten a command the audit truncates, the audit's verdict (its counts and every OUTSIDE line) must
match, and --key restores the bytes. Without --key it runs on the files as shipped, with --key on the research bytes.
--transcripts DIR (a maintainer's folder holding <arm>/transcript.jsonl and greek/correction-transcript.jsonl, with
--key) also checks each full log against its recorded sha256 and its redaction against the shipped log.

Nothing is written under data/. reproduce needs jsonschema (the `protocol-c` extra).

Exit status: 0; 1 if a check fails; 2 if a shipped file is missing or the ledger is unreadable; 3 without jsonschema.

Attribution: di Mino
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib.util
import io
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    __package__ = "tools.linear_a.validation"

from ...paths import DATA, LINEAR_A_DATA, REPO

PROTOCOL_DATA = LINEAR_A_DATA / "protocol-c"
LEDGER = PROTOCOL_DATA / "PORT-LEDGER.json"
FROZEN = REPO / "tools" / "core" / "frozen" / "protocol_c"
PREREG = REPO / "docs" / "protocol-c-preregistration.md"
SIGNED_SHA256 = "5a7b442c02336f31058a7fc51da7ecc382ff86eb6cdef7783883de108ed41ea0"
ARMS = ("cs", "yd", "luwian", "hurrian", "egyptian", "greek")
KIT_FILES = {"BRIEF.md", "protocol.md", "schema.json", "units.md", "grammar_files.txt"}
PROBE = "probe: NONE/no/no/\n"
# the files check_inventory.py reads from a build folder
CHECK_INPUTS = ("inventory.json", "schema.json", "units.md", "notes.md", "kit.sha256", "grammar_files.txt",
                "session_started_utc.txt", "builder_model.txt")
# a home folder, the macOS temporary folder, the maintainer's user name or first name, a private source id, a kept
# command output, a model credit; written in pieces so this file does not hold the strings it looks for
PRIVATE_TMP = "/private" + "/tmp"
LEAK = re.compile("|".join(["/Users" + "/", PRIVATE_TMP, "tom" + "dimino", r"\bTo" + r"m\b", r"\bsrc_\d{3}\b",
                            "aggregated_output", r"&\s*" + "Claude"]))
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


class LedgerError(RuntimeError):
    """A shipped file is missing, or the ledger cannot be read."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def shipped_path(rel: str) -> Path:
    """A ledger path (repository-relative) on disk; data/ follows KAPHTOR_DATA."""
    return DATA / rel[len("data/"):] if rel.startswith("data/") else REPO / rel


def load_ledger() -> dict:
    try:
        return json.loads(LEDGER.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise LedgerError(f"cannot read {LEDGER}: {error}") from error


def read_shipped(rel: str) -> bytes:
    path = shipped_path(rel)
    if not path.is_file():
        raise LedgerError(f"{rel} is not in this checkout")
    return path.read_bytes()


def load_key(path: Path | None) -> dict[str, list[str]] | None:
    """The maintainer's key: for each shipped path, the strings its substitutions replaced, in the ledger's order."""
    if path is None:
        return None
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))["originals"]
    except (OSError, ValueError, KeyError) as error:
        raise LedgerError(f"cannot read the key {path}: {error}") from error


def frozen_bytes(row: dict, key: dict[str, list[str]] | None = None) -> tuple[bytes, list[str], bool]:
    """The file as the research tree holds it: its shipped bytes with the ledger's substitutions undone from the
    key. Returns the bytes, the problems found (a shipped sha256 that differs from the ledger's, a substitution not
    found its count times) and whether they are the research bytes: a file with substitutions and no key comes back
    as shipped."""
    data = read_shipped(row["path"])
    problems = []
    if sha256(data) != row["shipped_sha256"]:
        problems.append(f"{row['path']}: shipped sha256 {sha256(data)[:12]}… is not the ledger's "
                        f"{row['shipped_sha256'][:12]}…")
    subs = row["substitutions"]
    if not subs:
        return data, problems, True
    olds = key.get(row["path"], []) if key is not None else None
    if olds is not None and len(olds) != len(subs):
        problems.append(f"{row['path']}: the key holds {len(olds)} strings for {len(subs)} substitutions")
        olds = None
    if olds is None:
        # a later substitution may rewrite an earlier one's text, so counts hold only as the key undoes them; the
        # shipped sha256 already fixes the bytes
        return data, problems, False
    for i in reversed(range(len(subs))):
        new = subs[i]["new"].encode()
        if data.count(new) != subs[i]["count"]:
            problems.append(f"{row['path']}: {subs[i]['new'][:60]!r} occurs {data.count(new)} times, "
                            f"not {subs[i]['count']}")
        data = data.replace(new, olds[i].encode())
    return data, problems, True


def redact(line: str, kit: str) -> str:
    """One event of a builder's Codex --json log as shipped: every item.aggregated_output replaced by its sha256
    (output_sha256) and UTF-8 byte length (output_bytes), dumped compact, the kit folder written $KIT."""
    ev = json.loads(line)
    item = ev.get("item")
    if isinstance(item, dict) and "aggregated_output" in item:
        out = item.pop("aggregated_output")
        raw = (out if isinstance(out, str) else json.dumps(out, ensure_ascii=False)).encode("utf-8")
        item["output_sha256"] = sha256(raw)
        item["output_bytes"] = len(raw)
    return json.dumps(ev, ensure_ascii=False, separators=(",", ":")).replace(kit, "$KIT") + "\n"


def redact_log(data: bytes, kit: str) -> bytes:
    text = data.decode("utf-8")
    if "$KIT" in text:
        raise ValueError("the log already holds $KIT, so its redaction could not be undone")
    return "".join(redact(line, kit) for line in text.splitlines() if line.strip()).encode("utf-8")


def body(data: bytes) -> bytes:
    """A Markdown file below its frontmatter (and the blank line after it)."""
    if not data.startswith(b"---\n"):
        return data
    end = data.index(b"\n---\n", 4) + len(b"\n---\n")
    return data[end + 1:] if data[end:end + 1] == b"\n" else data[end:]


def extract(protocol: str, level: int) -> str:
    """The protocol extract run_builder.sh writes into a kit (§5.2–5.3 and §16), cut at amendment A<level>."""
    def cut(start: str, end: str) -> str:
        i = protocol.index(start)
        return protocol[i:protocol.index(end, i)].rstrip() + "\n"
    amendments = cut("## 16. Amendments", "## Scratch files")
    later = f"**A{level + 1} ("
    if later in amendments:
        amendments = amendments[:amendments.index(later)].rstrip() + "\n"
    return ("# Protocol C: the rules this inventory is built under (extract)\n\n"
            + cut("### 5.2 Categories", "### 5.4 Parity") + "\n" + amendments)


def read_sums(data: bytes) -> dict[str, str]:
    out = {}
    for line in data.decode("utf-8").splitlines():
        if line.strip():
            digest, rel = line.split(None, 1)
            out[rel.strip().removeprefix("./")] = digest
    return out


def needles_sha256(needles: set[str]) -> str:
    return sha256("\n".join(sorted(needles)).encode("utf-8"))


def build_dir(arm: str) -> str:
    return f"protocol-c/builds/{arm}"


# ---------------------------------------------------------------------------
# verify
# ---------------------------------------------------------------------------

def restore_all(ledger: dict, key: dict | None = None) -> tuple[dict[str, bytes], set[str], list[str]]:
    """Every shipped file keyed by its research-tree path, restored where it can be (no substitutions, or the key);
    the research-tree paths left as shipped; and the failures met."""
    fails: list[str] = []
    restored: dict[str, bytes] = {}
    as_shipped: set[str] = set()
    for row in ledger["files"]:
        data, problems, exact = frozen_bytes(row, key)
        fails += problems
        if not exact:
            as_shipped.add(row["frozen_path"])
        elif sha256(data) != row["frozen_sha256"]:
            fails.append(f"{row['path']}: restored sha256 {sha256(data)[:12]}… is not the research tree's "
                         f"{row['frozen_sha256'][:12]}…")
        restored[row["frozen_path"]] = data
    return restored, as_shipped, fails


def derived_bytes(row: dict, key: dict | None = None) -> tuple[bytes, list[str]]:
    """A redacted log as redact() wrote it: the shipped log with the row's substitutions undone (with the key)."""
    data, problems, exact = frozen_bytes(row, key)
    if exact and sha256(data) != row["redacted_sha256"]:
        problems.append(f"{row['path']}: undone to {sha256(data)[:12]}…, not the redaction's "
                        f"{row['redacted_sha256'][:12]}…")
    return data, problems


def check_derived(ledger: dict, key: dict | None = None) -> list[str]:
    fails = []
    for row in ledger["derived"]:
        data = read_shipped(row["path"])
        fails += derived_bytes(row, key)[1]
        for n, line in enumerate(data.decode("utf-8").splitlines(), 1):
            try:
                item = json.loads(line).get("item") or {}
            except ValueError:
                fails.append(f"{row['path']}: line {n} is not JSON")
                continue
            if "aggregated_output" in item:
                fails.append(f"{row['path']}: line {n} keeps a command output")
            elif item.get("type") == "command_execution" and "output_sha256" not in item:
                fails.append(f"{row['path']}: line {n} has a command with no output_sha256")
    return fails


def check_protocol(ledger: dict, restored: dict[str, bytes], as_shipped: set[str]) -> list[str]:
    """The signed text and the protocol against their sha256 (when restored), the amendments in the protocol."""
    fails = []
    proto = ledger["protocol"]
    signed_path = "protocol-c/PROTOCOL-C-SIGNED-2026-10-29.md"
    signed = restored.get(signed_path, b"")
    if proto["signed_sha256"] != SIGNED_SHA256:
        fails.append(f"the ledger records the signed text as {proto['signed_sha256'][:12]}…, not {SIGNED_SHA256[:12]}…")
    if signed_path not in as_shipped and sha256(signed) != SIGNED_SHA256:
        fails.append(f"the signed text restores to {sha256(signed)[:12]}…, not {SIGNED_SHA256[:12]}…")
    if f"sha256 at signature: {SIGNED_SHA256}".encode() not in restored.get("protocol-c/SIGNATURE.txt", b""):
        fails.append("SIGNATURE.txt does not record 5a7b442c…")
    current = restored.get("PROTOCOL-C-DRAFT.md", b"")
    if "PROTOCOL-C-DRAFT.md" not in as_shipped and sha256(current) != proto["current_sha256"]:
        fails.append(f"the protocol restores to {sha256(current)[:12]}…, not the ledger's "
                     f"{proto['current_sha256'][:12]}…")
    for amendment in proto["amendments"]:
        if f"**{amendment} (".encode() not in current:
            fails.append(f"the protocol carries no amendment {amendment}")
    return fails


def check_builds(ledger: dict, restored: dict[str, bytes]) -> list[str]:
    fails = []
    files = {r["frozen_path"]: r for r in ledger["files"]}
    derived = {r["frozen_path"]: r for r in ledger["derived"]}
    withheld = {r["frozen_path"]: r for r in ledger["withheld"]}
    manifest = restored.get("protocol-c/builds/C1-MANIFEST.md", b"").decode("utf-8")
    recorded = dict(re.findall(r"^\| `(\w+)` \|.*\| `([0-9a-f]{64})` \|$", manifest, re.MULTILINE))
    draft = restored.get("PROTOCOL-C-DRAFT.md", b"").decode("utf-8")
    for arm in ARMS:
        bdir = build_dir(arm)
        sums = read_sums(restored.get(f"{bdir}/SHA256SUMS", b""))
        if not sums:
            fails.append(f"{bdir}/SHA256SUMS is not shipped")
        for name, digest in sums.items():
            key = f"{bdir}/{name}"
            row = files.get(key) or derived.get(key)
            if row is None:
                fails.append(f"{key}: in SHA256SUMS but neither shipped nor derived in the ledger")
            elif row["frozen_sha256"] != digest:
                fails.append(f"{key}: SHA256SUMS has {digest[:12]}…, the ledger {row['frozen_sha256'][:12]}…")
        for key in [*files, *derived]:
            if key.startswith(bdir + "/") and key != f"{bdir}/SHA256SUMS" and key[len(bdir) + 1:] not in sums:
                fails.append(f"{key}: shipped but not in the build's SHA256SUMS")
        kit = read_sums(restored.get(f"{bdir}/kit.sha256", b""))
        grammar = set(restored.get(f"{bdir}/grammar_files.txt", b"").decode("utf-8").split())
        for name, digest in kit.items():
            key = f"{bdir}/{name}"
            if name in KIT_FILES:
                if key not in files or files[key]["frozen_sha256"] != digest:
                    fails.append(f"{key}: kit.sha256 has {digest[:12]}…, not the shipped file's")
            elif key not in withheld or withheld[key]["frozen_sha256"] != digest:
                fails.append(f"{key}: in kit.sha256 but neither shipped nor withheld at that sha256")
            elif name not in grammar:
                fails.append(f"{key}: withheld from the kit but not a grammar file")
        if grammar != set(kit) - KIT_FILES:
            fails.append(f"{bdir}/grammar_files.txt does not list the kit's grammar files")
        # the research-tree sha256, which restore_all has checked wherever the file could be restored
        filled = files.get(f"{bdir}/inventory.filled.json", {}).get("frozen_sha256", "")
        if recorded.get(arm) != filled:
            fails.append(f"{bdir}/inventory.filled.json: the C1 manifest has {str(recorded.get(arm))[:12]}…, the file "
                         f"{filled[:12]}…")
        # the kit against C0
        units = read_shipped(f"data/linear-a/protocol-c/builds/{arm}/units.md")
        table = read_shipped(f"data/linear-a/protocol-c/inventories/tables/{arm}.md")
        if body(units) != body(table):
            fails.append(f"{bdir}/units.md is not inventories/tables/{arm}.md")
        # compared below their frontmatter, which only the shipped copies carry
        if body(restored.get(f"{bdir}/BRIEF.md", b"")) != body(restored.get("protocol-c/builds/BRIEF.md", b"")):
            fails.append(f"{bdir}/BRIEF.md is not builds/BRIEF.md")
        if restored.get(f"{bdir}/schema.json") != restored.get("protocol-c/inventories/schema.json"):
            fails.append(f"{bdir}/schema.json is not inventories/schema.json")
        level = int(ledger["kit_amendments"][arm].rsplit("A", 1)[1])
        if body(restored.get(f"{bdir}/protocol.md", b"")).decode("utf-8") != extract(draft, level):
            fails.append(f"{bdir}/protocol.md is not the protocol's extract through A{level}")
        if restored.get(f"{bdir}/probe.txt", b"").decode("utf-8") != PROBE:
            fails.append(f"{bdir}/probe.txt is not {PROBE.strip()!r}")
    return fails


def ledger_paths(ledger: dict) -> set[str]:
    return ({r["path"] for r in ledger["files"]} | {r["path"] for r in ledger["derived"]}
            | set(ledger["port_files"]))


def check_tree(ledger: dict) -> list[str]:
    """No stray file in the record's folders, and no private trace in any shipped file, the ledger included."""
    fails = []
    known = ledger_paths(ledger)
    roots = [(PROTOCOL_DATA, "data/linear-a/protocol-c"), (FROZEN, "tools/core/frozen/protocol_c")]
    on_disk = {f"{prefix}/{p.relative_to(root).as_posix()}" for root, prefix in roots if root.is_dir()
               for p in root.rglob("*") if p.is_file() and p.name != ".DS_Store" and "__pycache__" not in p.parts}
    on_disk.add("docs/protocol-c-preregistration.md")
    for rel in sorted(on_disk - known):
        fails.append(f"{rel}: in the record's folders but not in the ledger")
    for rel in sorted(known):
        if not shipped_path(rel).is_file():
            continue
        text = shipped_path(rel).read_text(encoding="utf-8", errors="replace")
        hits = {m.group(0) for m in LEAK.finditer(text)}
        if rel.endswith(("/run_builder.sh", "/PORT-LEDGER.json")):
            hits.discard(PRIVATE_TMP)  # the builder's kit folder, documented in the frozen README
        if hits:
            fails.append(f"{rel}: names {', '.join(sorted(hits))}")
        if m := EMAIL.search(text):
            fails.append(f"{rel}: holds an email address ({m.group(0)})")
    return fails


def verify(ledger: dict, key: dict | None = None) -> tuple[list[str], set[str]]:
    """Every check of the shipped record against its hashes; returns the failures (empty when all pass) and the
    research-tree paths checked as shipped (those with substitutions, when there is no key)."""
    restored, as_shipped, fails = restore_all(ledger, key)
    fails += check_derived(ledger, key)
    fails += check_protocol(ledger, restored, as_shipped)
    fails += check_builds(ledger, restored)
    fails += check_tree(ledger)
    return fails, as_shipped


def cmd_verify(key_path: Path | None) -> int:
    ledger = load_ledger()
    key = load_key(key_path)
    fails, as_shipped = verify(ledger, key)
    n_files = len(ledger["files"])
    if key is None:
        print(f"shipped files: {n_files}; {n_files - len(as_shipped)} at their research-tree sha256, {len(as_shipped)} "
              f"with the port's substitutions checked as shipped (--key restores them)")
    else:
        n_subs = sum(len(r["substitutions"]) for r in ledger["files"])
        print(f"shipped files: {n_files} ({n_subs} substitutions undone from the key)")
    print(f"redacted logs: {len(ledger['derived'])} (full logs withheld; their sha256 in each build's SHA256SUMS)")
    signed = "restored and checked" if key is not None else "checked with --key"
    print(f"signed text: {SIGNED_SHA256} (SIGNATURE.txt; {signed}); protocol with A1–A4: "
          f"{ledger['protocol']['current_sha256']}")
    print(f"withheld ({len(ledger['withheld'])}, not checked):")
    for w in ledger["withheld"]:
        print(f"  {w['frozen_path']}: {w['reason']}")
    for f in fails:
        print(f"FAIL {f}")
    print("verify: " + ("PASS" if not fails else f"{len(fails)} failure(s)"))
    return 1 if fails else 0


# ---------------------------------------------------------------------------
# reproduce
# ---------------------------------------------------------------------------

def redacted_log(row: dict, key: dict | None = None) -> bytes:
    """The redacted log as reproduce rereads it: as shipped, or with its substitutions undone from the key. Its
    hashes are verify's to check, so that the rerun audit judges whatever the log holds."""
    return frozen_bytes(row, key)[0]


def restored_file(ledger: dict, frozen_path: str, key: dict | None = None) -> bytes:
    """A shipped file, at its research bytes where it can be restored and as shipped otherwise; it stops on a file
    whose shipped or restored sha256 is not the ledger's."""
    row = next((r for r in ledger["files"] if r["frozen_path"] == frozen_path), None)
    if row is None:
        raise LedgerError(f"{frozen_path} is not in the ledger")
    data, problems, exact = frozen_bytes(row, key)
    if problems or (exact and sha256(data) != row["frozen_sha256"]):
        raise LedgerError(f"{row['path']} does not match the ledger; run verify")
    return data


def has_substitutions(ledger: dict, frozen_path: str) -> bool:
    return any(r["frozen_path"] == frozen_path and r["substitutions"] for r in ledger["files"])


def audit_verdict(text: bytes) -> list[str]:
    """An audit's verdict: its two count lines and every line naming a path outside the kit."""
    lines = text.decode("utf-8").splitlines()
    return lines[:2] + [line for line in lines[2:] if "OUTSIDE" in line]


def load_checker(ledger: dict, tmp: Path, key: dict | None = None):
    """check_inventory.py, imported from a temporary copy, reading this repository's corpus.json."""
    source = tmp / "check_inventory.py"
    source.write_bytes(restored_file(ledger, "protocol-c/scripts/check_inventory.py", key))
    spec = importlib.util.spec_from_file_location("protocol_c_check_inventory", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.CORPUS = LINEAR_A_DATA / "corpus.json"
    return module


def run_checker(checker, folder: Path) -> tuple[int, str]:
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        try:
            rc = checker.main(folder)
        except SystemExit as stop:
            rc = stop.code if isinstance(stop.code, int) else 2
            print(stop.code)
    return rc, out.getvalue()


def audit_source(runner: str) -> str:
    """The blindness audit, the Python program run_builder.sh feeds a session's log to."""
    m = re.search(r"> \"\$SB/blindness_audit\.txt\" <<'PY'\n(.*?)\nPY\n", runner, re.DOTALL)
    if not m:
        raise LedgerError("run_builder.sh has no blindness audit")
    return m.group(1) + "\n"


def audit_program(ledger: dict, key: dict | None = None) -> str:
    return audit_source(restored_file(ledger, "protocol-c/scripts/run_builder.sh", key).decode("utf-8"))


def rerun_audit(program: str, log: bytes, kit: str, tmp: Path) -> bytes:
    """The audit run_builder.sh runs on a session's log, run on the redacted log with $KIT put back."""
    path = tmp / "log.jsonl"
    path.write_bytes(log.replace(b"$KIT", kit.encode()))
    result = subprocess.run([sys.executable, "-I", "-", kit, str(path)], input=program.encode(), capture_output=True,
                            check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode("utf-8", "replace"))
    return result.stdout


def cmd_reproduce(arms: list[str], transcripts: Path | None, key_path: Path | None = None) -> int:
    try:
        import jsonschema  # noqa: F401
    except ImportError:
        print("reproduce needs jsonschema: uv sync --extra protocol-c", file=sys.stderr)
        return 3
    ledger = load_ledger()
    key = load_key(key_path)
    if transcripts is not None and key is None:
        raise LedgerError("--transcripts compares the full logs with the restored redactions: it needs --key")
    print("on the research bytes, restored from the key" if key is not None else "on the files as shipped")
    ok = True
    with tempfile.TemporaryDirectory(prefix="protocol-c-") as name:
        tmp = Path(name)
        checker = load_checker(ledger, tmp, key)
        needles = checker.corpus_needles()
        corpus = ledger["c1_corpus"]
        same = len(needles) == corpus["needles"] and needles_sha256(needles) == corpus["needles_sha256"]
        ok &= same
        print(f"corpus.json: {len(needles)} hyphenated words, sha256 {needles_sha256(needles)[:12]}… "
              f"({'as recorded' if same else 'DIFFERS from ' + corpus['needles_sha256'][:12] + '…'})")
        program = audit_program(ledger, key)
        derived = {r["frozen_path"]: r for r in ledger["derived"]}
        for arm in arms:
            bdir = build_dir(arm)
            folder = tmp / arm
            folder.mkdir()
            for name in CHECK_INPUTS:
                if any(r["frozen_path"] == f"{bdir}/{name}" for r in ledger["files"]):
                    (folder / name).write_bytes(restored_file(ledger, f"{bdir}/{name}", key))
            log = derived[f"{bdir}/transcript.jsonl"]
            (folder / "transcript.jsonl").write_bytes(redacted_log(log, key))
            rc, out = run_checker(checker, folder)
            want = restored_file(ledger, f"{bdir}/inventory.filled.json", key)
            got = (folder / "inventory.filled.json").read_bytes() if (folder / "inventory.filled.json").exists() \
                else b""
            same = rc == 0 and got == want
            ok &= same
            summary = next((line for line in out.splitlines() if line.startswith(f"arm {arm}:")), "")
            print(f"{arm}: check_inventory {'PASS' if rc == 0 else 'FAIL'}; inventory.filled.json "
                  f"{'byte for byte' if got == want else 'DIFFERS'} ({sha256(got)[:12]}…); {summary}")
            if not same:
                print("    " + out.replace("\n", "\n    ").rstrip())
            if arm == "greek":
                first = tmp / "greek-v1"
                first.mkdir()
                for name in CHECK_INPUTS:
                    if (folder / name).exists():
                        (first / name).write_bytes((folder / name).read_bytes())
                (first / "inventory.json").write_bytes(restored_file(ledger, f"{bdir}/inventory.v1.json", key))
                (first / "transcript.jsonl").write_bytes(redacted_log(log, key))
                rc1, out1 = run_checker(checker, first)
                refused = rc1 == 1 and "[blindness] greek_274: corpus word 'a-i'" in out1 \
                    and not (first / "inventory.filled.json").exists()
                ok &= refused
                print(f"greek inventory.v1.json: {'refused, as recorded' if refused else 'NOT refused'} "
                      f"(greek_274: corpus word 'a-i')")
            audits = [("transcript.jsonl", "blindness_audit.txt")]
            if arm == "greek":
                audits.append(("correction-transcript.jsonl", "correction_blindness_audit.txt"))
            for log_name, audit_name in audits:
                row = derived[f"{bdir}/{log_name}"]
                got = rerun_audit(program, redacted_log(row, key), row["kit"], tmp)
                want = restored_file(ledger, f"{bdir}/{audit_name}", key)
                head = " ".join(want.decode("utf-8").splitlines()[:2])
                if got == want:
                    print(f"{arm}: {audit_name} byte for byte from the redacted log ({head})")
                elif key is None and has_substitutions(ledger, f"{bdir}/{audit_name}") \
                        and audit_verdict(got) == audit_verdict(want):
                    print(f"{arm}: {audit_name} verdict as recorded from the redacted log ({head}); the port's "
                          f"substitutions shorten a truncated command, and --key restores the bytes")
                else:
                    ok = False
                    print(f"{arm}: {audit_name} DIFFERS from the redacted log ({head})")
                if transcripts is not None:
                    full_path = transcripts / arm / log_name
                    if not full_path.is_file():
                        print(f"{arm}: {log_name} not in {transcripts}")
                        ok = False
                        continue
                    full = full_path.read_bytes()
                    match = sha256(full) == row["frozen_sha256"]
                    redacts = redact_log(full, row["kit"]) == redacted_log(row, key)
                    ok &= match and redacts
                    print(f"{arm}: full {log_name} {'at its recorded sha256' if match else 'at another sha256'}; "
                          f"its redaction {'is' if redacts else 'is NOT'} the shipped log")
    print("reproduce: " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="protocol_c.py", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    key_help = "the maintainer's key (the strings the port replaced), to check the research bytes"
    ver = sub.add_parser("verify", help="check every shipped file against its hashes")
    ver.add_argument("--key", type=Path, help=key_help)
    rep = sub.add_parser("reproduce", help="rerun the C1 checker and the blindness audits")
    rep.add_argument("--arm", choices=ARMS, action="append", help="one arm (repeatable); all six by default")
    rep.add_argument("--key", type=Path, help=key_help)
    rep.add_argument("--transcripts", type=Path, help="a folder of the full logs, <arm>/transcript.jsonl (with --key)")
    args = ap.parse_args(argv)
    try:
        if args.cmd == "verify":
            return cmd_verify(args.key)
        return cmd_reproduce(args.arm or list(ARMS), args.transcripts, args.key)
    except LedgerError as error:
        print(f"stopped: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
