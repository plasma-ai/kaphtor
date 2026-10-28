#!/usr/bin/env python3
"""Paradigm B, the pre-registered held-out paradigm-prediction test: check the shipped files against the freeze,
rerun the frozen runs, run the frozen selftest.

  uv run tools/linear_a/validation/paradigm_b.py verify [--key KEY]
  uv run tools/linear_a/validation/paradigm_b.py reproduce --quick | --full [--workers N] [--key KEY]
  uv run tools/linear_a/validation/paradigm_b.py selftest [--key KEY]

The frozen code is in tools/core/frozen/paradigm_b/, its data and the five production runs in
data/linear-a/paradigm-b/. PORT-LEDGER.json there gives each shipped file's path and sha256 in the package it was
frozen in, what pins that hash (SHA256SUMS, the PROTOCOL-B freeze record, the run manifest) and the text each of the
port's substitutions wrote, with its count. The strings they replaced (the research credit and private paths) are
not shipped: they are in the maintainer's key, which reviewers may ask for.

verify checks every shipped file's sha256 and the frozen sha256 of every file the port left unchanged; with --key it
undoes each file's substitutions and checks every file against its frozen sha256. It checks SHA256SUMS against the
freeze record (f5d6733f…), the PROTOCOL-B pins against docs/paradigm-b-preregistration.md and each run's manifest
against SHA256SUMS, checks that the ledger names no private path or credit, and lists the frozen files the port
withholds without failing on them.

reproduce rebuilds the frozen package in a temporary folder and runs it there: with --key byte for byte; without it
from the files as shipped, the package's SHA256SUMS giving the shipped sha256 of each file the port changed (the
frozen code checks every data file against it on load). --quick reruns the
observed family and the 128 control windows (the result must equal the shipped results.json except wall_s),
recomputes the gate from the shipped null vectors (equal to the shipped gate), and reruns replicates 0–199 of nulls
D and D2 on one worker (equal to rows 0–199 of the production arrays). --full reruns the three 10,000-replicate
nulls in full. Floats must agree within 1e-12; the report says whether each result is also bitwise identical.

selftest runs the frozen selftest_b.py --fast on the rebuilt package (the same with or without --key). Its blindness check reads the lexicon
snapshot, which changed after the freeze and is withheld, so here it runs with the formula family's forms alone.

Nothing is written under data/: the rebuilt package lives in a temporary folder deleted on exit. reproduce and
selftest need numpy and scipy (the `paradigm` extra).

Exit status: 0; 1 if a check fails; 2 if a shipped file is missing or the ledger is unreadable; 3 without numpy or
scipy.

Attribution: di Mino
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib
import json
import math
import os
import re
import sys
import tempfile
import time
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    __package__ = "tools.linear_a.validation"

from ...paths import DATA, LINEAR_A_DATA, REPO

PARADIGM_DATA = LINEAR_A_DATA / "paradigm-b"
LEDGER = PARADIGM_DATA / "PORT-LEDGER.json"
FREEZE_RECORD = PARADIGM_DATA / "freeze-record.md"
PREREG = REPO / "docs" / "paradigm-b-preregistration.md"
SHA256SUMS_SHA256 = "f5d6733fbf922c951b5e690725cdedf6fda4bf52747c59e284807efc351cd7ca"
TOLERANCE = 1e-12
QUICK_REPLICATES = 200
RUNS = {"observed": "20261009T194551Z-paradigm-observed-strict-base",
        "D": "20261009T194512Z-paradigm-null-D-strict-base-B10000-s20260913",
        "D2": "20261009T194527Z-paradigm-null-D2-strict-base-B10000-s20260914",
        "D2x2": "20261009T194546Z-paradigm-null-D2x2-strict-base-B10000-s20260915",
        "gate": "20261009T194557Z-paradigm-gate-strict-base"}
# top-level module names the frozen package imports; dropped before each load so a rebuilt package is read afresh
FROZEN_MODULES = ("common", "run_paradigm", "render_la", "skeleton", "phonetics", "build_paradigm", "selftest_b")
# a home folder, the maintainer's user name, a model credit; written in pieces so this file does not hold them
LEAK = re.compile("|".join(["/Users" + "/", "tom" + "dimino", r"&\s*" + "Claude", r"Claude,\s*" + "Opus"]))


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


def load_key(path: Path | None) -> dict[str, list[str]] | None:
    """The maintainer's key: for each shipped path, the strings its substitutions replaced, in the ledger's order."""
    if path is None:
        return None
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))["originals"]
    except (OSError, ValueError, KeyError) as error:
        raise LedgerError(f"cannot read the key {path}: {error}") from error


def frozen_bytes(row: dict, key: dict[str, list[str]] | None = None) -> tuple[bytes, list[str], bool]:
    """The file as it was frozen: its shipped bytes with the ledger's substitutions undone from the key. Returns the
    bytes, the problems found (a shipped sha256 that differs from the ledger's, a substitution not found its count
    times) and whether they are the frozen bytes: a file with substitutions and no key comes back as shipped."""
    path = shipped_path(row["path"])
    if not path.is_file():
        raise LedgerError(f"{row['path']} is not in this checkout")
    data = path.read_bytes()
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
        return data, problems, False
    for i in reversed(range(len(subs))):
        new = subs[i]["new"].encode()
        if data.count(new) != subs[i]["count"]:
            problems.append(f"{row['path']}: {subs[i]['new']!r} occurs {data.count(new)} times, not {subs[i]['count']}")
        data = data.replace(new, olds[i].encode())
    return data, problems, True


def freeze_block() -> str:
    """The freeze record copied into freeze-record.md, between its markers."""
    text = FREEZE_RECORD.read_text(encoding="utf-8")
    m = re.search(r"<!-- freeze-record:begin -->\n(.*?)<!-- freeze-record:end -->", text, re.DOTALL)
    if not m:
        raise LedgerError(f"{FREEZE_RECORD} has no freeze-record block")
    return m.group(1)


def protocol_b_pins() -> dict[str, str]:
    """The PROTOCOL-B freeze record's script hashes, read from the pre-registration as shipped."""
    text = PREREG.read_text(encoding="utf-8")
    section = text.split("## Freeze record (option B)", 1)
    if len(section) < 2:
        raise LedgerError(f"{PREREG} has no 'Freeze record (option B)' section")
    return dict(re.findall(r"^- (scripts/\S+\.py): ([0-9a-f]{64})$", section[1], re.MULTILINE))


def read_sums(data: bytes) -> dict[str, str]:
    out = {}
    for line in data.decode("utf-8").splitlines():
        if line.strip() and not line.startswith("#"):
            digest, rel = line.split(None, 1)
            out[rel.strip()] = digest
    return out


# ---------------------------------------------------------------------------
# verify
# ---------------------------------------------------------------------------

def verify(ledger: dict, key: dict | None = None) -> tuple[list[str], int]:
    """Every check of the shipped files against the freeze; returns the failures (empty when all pass) and how many
    files were checked as shipped (those with substitutions, when there is no key)."""
    fails: list[str] = []
    restored: dict[str, bytes] = {}
    as_shipped = 0
    for row in ledger["files"]:
        data, problems, exact = frozen_bytes(row, key)
        fails += problems
        if not exact:
            as_shipped += 1
        elif sha256(data) != row["frozen_sha256"]:
            fails.append(f"{row['path']}: restored sha256 {sha256(data)[:12]}… is not the frozen "
                         f"{row['frozen_sha256'][:12]}…")
        restored[row["frozen_path"]] = data
    if hits := sorted({m.group(0) for m in LEAK.finditer(LEDGER.read_text(encoding="utf-8"))}):
        fails.append(f"PORT-LEDGER.json names {', '.join(hits)}")

    sums_bytes = restored.get("SHA256SUMS", b"")
    block = freeze_block()
    recorded = re.search(r"sha256sums_sha256: ([0-9a-f]{64})", block)
    if sha256(sums_bytes) != SHA256SUMS_SHA256:
        fails.append(f"SHA256SUMS hashes to {sha256(sums_bytes)[:12]}…, not {SHA256SUMS_SHA256[:12]}…")
    if not recorded or recorded.group(1) != SHA256SUMS_SHA256:
        fails.append("freeze-record.md does not record SHA256SUMS as f5d6733f…")
    if "refreeze_reason: option B freeze" not in block:
        fails.append("freeze-record.md carries no 'option B freeze' reason")

    sums = read_sums(sums_bytes)
    pins = protocol_b_pins()
    for row in ledger["files"]:
        rel, digest = row["frozen_path"], row["frozen_sha256"]
        if "SHA256SUMS" in row["pinned_by"] and sums.get(rel) != digest:
            fails.append(f"{rel}: SHA256SUMS has {str(sums.get(rel))[:12]}…, the ledger {digest[:12]}…")
        if "PROTOCOL-B freeze record" in row["pinned_by"] and pins.get(rel) != digest:
            fails.append(f"{rel}: the pre-registration's freeze record has {str(pins.get(rel))[:12]}…")
        if rel.endswith("/results.json"):
            run = rel.split("/")[1]
            if ledger["runs_results_sha256"].get(run) != digest:
                fails.append(f"{rel}: the run manifest's results_sha256 differs")
        if rel.endswith("/manifest.json") and json.loads(restored[rel]).get("sha256sums") != SHA256SUMS_SHA256:
            fails.append(f"{rel}: the run was not made under SHA256SUMS f5d6733f…")
    for rel, digest in sums.items():
        listed = any(r["frozen_path"] == rel for r in ledger["files"]) or \
            any(w["frozen_path"] == rel for w in ledger["withheld"])
        if not listed:
            fails.append(f"{rel}: in SHA256SUMS but neither shipped nor withheld in the ledger")
    return fails, as_shipped


def cmd_verify(key_path: Path | None) -> int:
    ledger = load_ledger()
    key = load_key(key_path)
    fails, as_shipped = verify(ledger, key)
    n_files = len(ledger["files"])
    if key is None:
        print(f"shipped files: {n_files}; {n_files - as_shipped} at their frozen sha256, {as_shipped} with the port's "
              f"substitutions checked as shipped (--key restores them)")
    else:
        n_subs = sum(len(r["substitutions"]) for r in ledger["files"])
        print(f"shipped files: {n_files} ({n_subs} substitutions undone from the key)")
    print(f"SHA256SUMS: {SHA256SUMS_SHA256} (freeze 2026-10-09T19:44:46Z, option B)")
    print(f"withheld ({len(ledger['withheld'])}, not checked):")
    for w in ledger["withheld"]:
        print(f"  {w['frozen_path']}: {w['reason']}")
    for f in fails:
        print(f"FAIL {f}")
    print("verify: " + ("PASS" if not fails else f"{len(fails)} failure(s)"))
    return 1 if fails else 0


# ---------------------------------------------------------------------------
# the rebuilt package
# ---------------------------------------------------------------------------

def rebuild(ledger: dict, dest: Path, key: dict | None = None) -> int:
    """Write the frozen package into ``dest`` in its frozen layout, with the freeze record as PROTOCOL.md. With the
    key every file is at its frozen sha256; without it the files the port changed are as shipped, and the package's
    SHA256SUMS gives their shipped sha256. Stops on the first file that does not match the ledger. Returns the number
    of files written as shipped."""
    shipped: dict[str, str] = {}
    for row in ledger["files"]:
        data, problems, exact = frozen_bytes(row, key)
        if problems or (exact and sha256(data) != row["frozen_sha256"]):
            raise LedgerError(f"{row['path']} does not match the ledger; run verify")
        if not exact:
            shipped[row["frozen_path"]] = row["shipped_sha256"]
        out = dest / row["frozen_path"]
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
    if shipped:
        sums = dest / "SHA256SUMS"
        lines = []
        for line in sums.read_text(encoding="utf-8").splitlines(keepends=True):
            parts = line.split(None, 1)
            if len(parts) == 2 and not line.startswith("#") and parts[1].strip() in shipped:
                line = f"{shipped[parts[1].strip()]}{line[len(parts[0]):]}"
            lines.append(line)
        sums.write_text("".join(lines), encoding="utf-8")
    (dest / "PROTOCOL.md").write_text(freeze_block(), encoding="utf-8")
    return len(shipped)


def load_frozen(dest: Path, module: str):
    """Import a frozen script from the package rebuilt at ``dest``, never from an earlier one."""
    for name in list(sys.modules):
        if name.split(".")[0] in FROZEN_MODULES:
            del sys.modules[name]
    sys.path[:] = [p for p in sys.path if not p.startswith(str(dest.parent))]
    sys.path.insert(0, str(dest / "scripts"))
    return importlib.import_module(module)


@contextlib.contextmanager
def rebuilt_package(key_path: Path | None = None):
    ledger = load_ledger()
    with tempfile.TemporaryDirectory(prefix="paradigm-b-") as tmp:
        dest = Path(tmp) / "package"
        n = rebuild(ledger, dest, load_key(key_path))
        print("rebuilt the frozen package byte for byte from the key" if not n else
              f"rebuilt the frozen package from the files as shipped ({n} carry the port's substitutions; its "
              f"SHA256SUMS gives their shipped sha256; --key rebuilds it byte for byte)")
        yield dest


def require_numpy() -> bool:
    try:
        import numpy  # noqa: F401
        import scipy  # noqa: F401
    except ImportError:
        print("reproduce and selftest need numpy and scipy: uv sync --extra paradigm", file=sys.stderr)
        return False
    return True


# ---------------------------------------------------------------------------
# reproduce
# ---------------------------------------------------------------------------

def compare(got, want, path: str = "") -> tuple[list[str], float]:
    """Differences between two JSON values (floats within TOLERANCE, NaN equal to NaN) and the largest float gap."""
    if isinstance(want, dict) and isinstance(got, dict):
        out, gap = [], 0.0
        for k in sorted(set(want) | set(got)):
            if k not in got or k not in want:
                out.append(f"{path}/{k}: present on one side only")
                continue
            d, g = compare(got[k], want[k], f"{path}/{k}")
            out, gap = out + d, max(gap, g)
        return out, gap
    if isinstance(want, list) and isinstance(got, list):
        if len(want) != len(got):
            return [f"{path}: length {len(got)} against {len(want)}"], 0.0
        out, gap = [], 0.0
        for i, (a, b) in enumerate(zip(got, want)):
            d, g = compare(a, b, f"{path}[{i}]")
            out, gap = out + d, max(gap, g)
        return out, gap
    if isinstance(got, bool) or isinstance(want, bool):
        same = type(got) is type(want) and got == want
        return ([] if same else [f"{path}: {got!r} against {want!r}"]), 0.0
    if isinstance(want, float) or isinstance(got, float):
        if got is None or want is None or isinstance(got, str) or isinstance(want, str):
            return ([] if got == want else [f"{path}: {got!r} against {want!r}"]), 0.0
        a, b = float(got), float(want)
        if math.isnan(a) and math.isnan(b):
            return [], 0.0
        gap = abs(a - b)
        return ([] if gap <= TOLERANCE else [f"{path}: {a!r} against {b!r}"]), gap
    return ([] if got == want else [f"{path}: {got!r} against {want!r}"]), 0.0


def as_written(result: dict) -> str:
    """A result dict serialized exactly as run_paradigm.write_run writes results.json."""
    return json.dumps(result, indent=1, ensure_ascii=False, default=str)


def report(name: str, got: dict, shipped_text: str) -> bool:
    want = json.loads(shipped_text)
    if "wall_s" in want:
        got = {**got, "wall_s": want["wall_s"]}
    identical = as_written(got) == shipped_text
    diffs, gap = compare(json.loads(as_written(got)), want)
    ok = not diffs
    state = "bitwise identical" if identical else (f"equal within {TOLERANCE:g} (max gap {gap:.3g})" if ok else "DIFFERS")
    print(f"  {name}: {state}")
    for d in diffs[:10]:
        print(f"    {d}")
    return ok


def compare_arrays(name: str, got, want) -> bool:
    import numpy as np
    if got.shape != want.shape:
        print(f"  {name}: shape {got.shape} against {want.shape}: DIFFERS")
        return False
    if np.array_equal(got, want, equal_nan=True):
        print(f"  {name}: bitwise identical ({got.shape[0]} replicates)")
        return True
    both = ~(np.isnan(got) & np.isnan(want))
    gap = float(np.nanmax(np.abs(got[both] - want[both]))) if both.any() else 0.0
    ok = gap <= TOLERANCE and bool((np.isnan(got) == np.isnan(want)).all())
    print(f"  {name}: {'equal within ' + format(TOLERANCE, 'g') if ok else 'DIFFERS'} (max gap {gap:.3g})")
    return ok


def run_file(run: str, suffix: str) -> Path:
    return PARADIGM_DATA / "runs" / f"{run}.{suffix}"


def gate_config(rp) -> dict:
    """The gate configuration (strict, base, leave-one-site-out), through the runner's own parser of its flags."""
    return rp.config_from_args(argparse.Namespace(cons=False, ext=False, with_sabaic=False, folds="lso",
                                                  drop_slot=None, drop_damaged=False))


def null_result(rp, cfg: dict, null: str, arr, B: int, seed: int) -> dict:
    """The results.json run_paradigm.py main writes for a production null run (wall_s supplied by the caller)."""
    import numpy as np
    summ = {s: {"mean": float(np.nanmean(arr[:, j])), "sd": float(np.nanstd(arr[:, j], ddof=1)),
                "p95": float(np.nanpercentile(arr[:, j], 95)), "nan": int(np.isnan(arr[:, j]).sum())}
            for j, s in enumerate(rp.STATS)}
    return {"null": null, "B": B, "seed": seed, "config": cfg, "d2_params": rp._G["d2"],
            "variation_rate": rp._G["rate"], "summary": summ, "wall_s": 0.0, "debug": False}


def cmd_reproduce(full: bool, workers: int, key_path: Path | None = None) -> int:
    if not require_numpy():
        return 3
    import numpy as np
    ok = True
    with rebuilt_package(key_path) as dest:
        rp = load_frozen(dest, "run_paradigm")
        cfg = gate_config(rp)
        print(f"in a temporary folder; Python {sys.version.split()[0]}, numpy {np.__version__}")

        t0 = time.time()
        obs = rp.run_observed(cfg)
        obs.update({"config": cfg, "wall_s": time.time() - t0})
        print(f"observed family and controls ({time.time() - t0:.1f} s)")
        ok &= report(RUNS["observed"] + ".results.json", obs, run_file(RUNS["observed"], "results.json")
                     .read_text(encoding="utf-8"))
        fam = obs["family"]
        print(f"    A_free {fam['A_free']:.3f}  A_cs {fam['A_cs']:.3f}  A_nws_floor {fam['A_nws_floor']:.3f}  "
              f"A_luwian {fam['A_luwian']:.3f}  A_hurrian {fam['A_hurrian']:.3f}  A_egyptian {fam['A_egyptian']:.3f}"
              f"  delta {fam['delta']:.3f}  scorable {fam['scorable']}")

        shipped = {n: np.load(run_file(RUNS[n], "null_vectors.npy")) for n in ("D", "D2", "D2x2")}
        gate_manifest = json.loads(run_file(RUNS["gate"], "manifest.json").read_text(encoding="utf-8"))
        argv = gate_manifest["argv"]
        observed_run = argv[argv.index("--observed-run") + 1]
        null_runs = argv[argv.index("--null-runs") + 1:]
        shipped_obs = json.loads(run_file(RUNS["observed"], "results.json").read_text(encoding="utf-8"))
        g = rp.gate(shipped_obs, shipped)
        g.update({"observed_run": observed_run, "null_runs": null_runs})
        print("gate from the shipped observed run and null vectors")
        ok &= report(RUNS["gate"] + ".results.json", g, run_file(RUNS["gate"], "results.json")
                     .read_text(encoding="utf-8"))
        g1, g2, g3 = g["G1"], g["G2"], g["G3"]
        print(f"    G1 {'pass' if g1['pass'] else 'fail'}: D mean {g1['D_mean']:.3f}, p95 {g1['D_p95']:.3f}, "
              f"r {g1['r']}/10000")
        print(f"    G2 {'pass' if g2['pass'] else 'fail'}: AUC(delta) {g2['auc_lm_delta']['auc']:.3f} "
              f"[{g2['auc_lm_delta']['ci95'][0]:.3f}, {g2['auc_lm_delta']['ci95'][1]:.3f}] "
              f"{g2['auc_lm_delta']['pairs']} pairs; AUC(A_cs) {g2['auc_lm_A_cs']['auc']:.3f} "
              f"[{g2['auc_lm_A_cs']['ci95'][0]:.3f}, {g2['auc_lm_A_cs']['ci95'][1]:.3f}]; "
              f"Linear B above the H1 band median: {[w['id'] for w in g2['linear_b_above_h1_band_median']]}")
        print(f"    G3 (descriptive): D2 delta p95 {g3['D2_delta_p95']:.3f}, r {g3['r']}/10000; "
              f"D2x2 r {g3['D2x2']['r']}/10000")

        nulls = ("D", "D2", "D2x2") if full else ("D", "D2")
        for null in nulls:
            B = 10_000 if full else QUICK_REPLICATES
            w = workers if full else 1
            t0 = time.time()
            arr = rp.run_null(cfg, null, B, rp.NULL_SEED[null], w)
            print(f"null {null}: {B} replicates on {w} worker(s) ({time.time() - t0:.1f} s)")
            ok &= compare_arrays(f"{RUNS[null]}.null_vectors.npy rows 0–{B - 1}", arr, shipped[null][:B])
            if full:
                ok &= report(RUNS[null] + ".results.json", null_result(rp, cfg, null, arr, B, rp.NULL_SEED[null]),
                             run_file(RUNS[null], "results.json").read_text(encoding="utf-8"))
    print("reproduce: " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


# ---------------------------------------------------------------------------
# selftest
# ---------------------------------------------------------------------------

def cmd_selftest(key_path: Path | None = None) -> int:
    if not require_numpy():
        return 3
    with rebuilt_package(key_path) as dest:
        st = load_frozen(dest, "selftest_b")
        paths = sys.modules["common.paths"]
        frozen_load = paths.load_snapshot

        def load_snapshot(name: str, *, strict: bool = True):
            # the lexicon snapshot is withheld (changed after the freeze): the blindness check gets no headwords
            if name == "lexicon.json":
                return {"entries": []}
            return frozen_load(name, strict=strict)

        paths.load_snapshot = load_snapshot
        print("frozen selftest_b.py --fast; check 3 reads the formula family's forms only (lexicon snapshot withheld)")
        argv, sys.argv = sys.argv, ["selftest_b.py", "--fast"]
        try:
            rc = st.main()
        finally:
            sys.argv = argv
    print("selftest: " + ("PASS" if rc == 0 else "FAIL"))
    return rc


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="paradigm_b.py", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    key_help = "the maintainer's key (the strings the port replaced), to work on the frozen bytes"
    ver = sub.add_parser("verify", help="check every shipped file against the freeze")
    ver.add_argument("--key", type=Path, help=key_help)
    rep = sub.add_parser("reproduce", help="rerun the frozen runs in a rebuilt package")
    mode = rep.add_mutually_exclusive_group(required=True)
    mode.add_argument("--quick", action="store_true", help="observed run, gate, 200 replicates of D and D2")
    mode.add_argument("--full", action="store_true", help="the quick checks and the three 10,000-replicate nulls")
    rep.add_argument("--workers", type=int, default=os.cpu_count() or 1, help="processes for --full")
    rep.add_argument("--key", type=Path, help=key_help)
    st = sub.add_parser("selftest", help="the frozen selftest_b.py --fast")
    st.add_argument("--key", type=Path, help=key_help)
    args = ap.parse_args(argv)
    try:
        if args.cmd == "verify":
            return cmd_verify(args.key)
        if args.cmd == "reproduce":
            return cmd_reproduce(args.full, max(1, args.workers), args.key)
        return cmd_selftest(args.key)
    except LedgerError as error:
        print(f"stopped: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
