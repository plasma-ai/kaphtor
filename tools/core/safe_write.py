"""Backup and atomic replace for builders that rewrite a file.

Same contract as tools/linear_a/build_sigla_db.py: before anything is written, the old file is copied into a backups
folder (tools.paths.BACKUPS by default, outside the repository) under an exclusive-create
`<name>.bak-<UTC stamp>-<pid>`, and the new content replaces the file through a temp file and os.replace on the
resolved path, so a symlinked file stays a symlink and a failed write leaves the old file intact.
"""
from __future__ import annotations

import os
import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path


def backup_file(path: Path, backups: Path) -> Path:
    """Copy `path` (following a symlink) into `backups` under a name that cannot already exist; return the copy."""
    backups.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")
    dest = backups / f"{path.name}.bak-{stamp}-{os.getpid()}"
    with path.open("rb") as src, dest.open("xb") as dst:
        shutil.copyfileobj(src, dst)
    shutil.copystat(path, dest)
    return dest


def write_atomic(path: Path, text: str) -> Path:
    """Replace the file `path` resolves to with `text`; return the resolved target."""
    target = path.resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=target.name + ".", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.chmod(tmp_name, 0o644)
        os.replace(tmp_name, target)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise
    return target
