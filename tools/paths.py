"""Where kaphtor's data and caches live: one place, so no tool builds its own path.

DATA is the repository's `data/`, or the folder named by the KAPHTOR_DATA environment variable. Query clients
cache what they fetch under CACHE (`$XDG_CACHE_HOME/kaphtor`, else `~/.cache/kaphtor`), never inside the repo. The
generators copy a file before they rewrite it into BACKUPS (`$XDG_STATE_HOME/kaphtor/backups`, else
`~/.local/state/kaphtor/backups`), outside the repository and so outside the wiki.
"""
from __future__ import annotations

import os
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get("KAPHTOR_DATA") or REPO / "data")
ANE_DATA = DATA / "ane"
SHARE_ALIKE = DATA / "share-alike"
LINEAR_A_DATA = DATA / "linear-a"
CONTACT_DATA = DATA / "contact"
SEMITIC_ROOTS_DATA = DATA / "semitic-roots"
CACHE = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "kaphtor"
BACKUPS = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state") / "kaphtor" / "backups"


class NotInCheckout(FileNotFoundError):
    """A dataset this tool reads is not in the repository: it is held back, or fetched separately."""


def require(path: Path, dataset: str) -> Path:
    """`path` if it exists; otherwise NotInCheckout naming the dataset and where it was looked for."""
    if not path.exists():
        raise NotInCheckout(f"{dataset} is not in this checkout (looked for {path})")
    return path
