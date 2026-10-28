"""Package paths and hash-verified snapshot loading.

``load_snapshot(name)`` refuses to return a file whose SHA-256 differs from the
value recorded in ``SHA256SUMS`` at freeze time. A modified input fails loudly;
that is the isolation guarantee the protocol relies on.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parents[2]
DATA = PKG / "data"
SNAPSHOT = DATA / "snapshot"
CONTROLS = PKG / "controls"
RUNS = PKG / "runs"
LINEUP = PKG / "lineup"
VENDOR = PKG / "vendor"
SHA_FILE = PKG / "SHA256SUMS"
PROTOCOL = PKG / "PROTOCOL.md"
MANIFEST = PKG / "run_manifest.json"

# Make vendored modules importable as top-level names (skeleton, phonetics, ...)
if str(VENDOR) not in sys.path:
    sys.path.insert(0, str(VENDOR))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_sums() -> dict[str, str]:
    """Return {relative path: sha256} from SHA256SUMS (empty before freeze)."""
    if not SHA_FILE.exists():
        return {}
    out: dict[str, str] = {}
    for line in SHA_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        digest, rel = line.split(None, 1)
        out[rel.strip()] = digest
    return out


class SnapshotIntegrityError(RuntimeError):
    pass


def verified_path(rel: str, *, strict: bool = True) -> Path:
    """Path under the package root whose hash matches SHA256SUMS."""
    path = PKG / rel
    if not path.exists():
        raise FileNotFoundError(path)
    sums = read_sums()
    recorded = sums.get(rel)
    if recorded is None:
        # Pre-freeze development only: IOZA2_PREFREEZE=1 lets a not-yet-frozen
        # component load. A file that IS listed is still hash-checked. Production
        # scripts refuse to run unless PROTOCOL.md carries a freeze record.
        if strict and not os.environ.get("IOZA2_PREFREEZE"):
            raise SnapshotIntegrityError(f"{rel} is not listed in SHA256SUMS; run freeze_protocol.py")
        return path
    actual = sha256(path)
    if actual != recorded:
        raise SnapshotIntegrityError(
            f"{rel}: hash mismatch (recorded {recorded[:12]}…, actual {actual[:12]}…)")
    return path


def load_snapshot(name: str, *, strict: bool = True):
    """Load ``data/snapshot/<name>`` (JSON or JSONL) after hash verification."""
    path = verified_path(f"data/snapshot/{name}", strict=strict)
    if path.suffix == ".jsonl":
        with open(path, encoding="utf-8") as fh:
            return [json.loads(line) for line in fh if line.strip()]
    return json.loads(path.read_text(encoding="utf-8"))


def load_data(name: str, *, strict: bool = True):
    """Load ``data/<name>`` (frozen model component) after hash verification."""
    path = verified_path(f"data/{name}", strict=strict)
    if path.suffix == ".jsonl":
        with open(path, encoding="utf-8") as fh:
            return [json.loads(line) for line in fh if line.strip()]
    return json.loads(path.read_text(encoding="utf-8"))
