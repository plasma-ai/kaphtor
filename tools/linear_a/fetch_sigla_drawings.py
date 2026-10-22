#!/usr/bin/env python3
"""Download SigLA inscription drawings for the Linear A corpus.

corpus.json carries a `sigla` block (and occasionally per-side
`sigla_sides` blocks) with a `drawing_url` pointing at the published
tracing on sigla.phis.me. This fetcher mirrors those drawings locally,
one PNG per document side, politely and resumably:

  - 1.0 s rate limit between requests
  - atomic downloads (.part file, rename on success)
  - manifest reconciliation on startup (file on disk + nonzero → done)
  - 404 → permanent missing_404, never retried
  - other errors → exponential backoff 5 s → 300 s, doubling
  - manifest saved atomically every 50 events and on KeyboardInterrupt

Images land at {OUT_DIR}/{NormalizedID}-SigLA.png where NormalizedID is
the corpus key with spaces replaced by underscores (side-block downloads
append _{side}); the manifest sits beside them, in the user cache
(CACHE/sigla/), never in the repository. The drawings are SigLA's, not ours
to redistribute.

Usage:
    uv run --extra fetch tools/linear_a/fetch_sigla_drawings.py --dry-run       # plan only
    uv run --extra fetch tools/linear_a/fetch_sigla_drawings.py --test 3        # first 3 pending
    uv run --extra fetch tools/linear_a/fetch_sigla_drawings.py                 # full run
    uv run --extra fetch tools/linear_a/fetch_sigla_drawings.py --summary-only  # status table
    uv run --extra fetch tools/linear_a/fetch_sigla_drawings.py --force         # re-download all
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

try:
    import httpx
except ImportError:
    print("httpx is not installed: install the fetch extra (uv sync --extra fetch)", file=sys.stderr)
    sys.exit(1)

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = "tools.linear_a"

from ..paths import CACHE, LINEAR_A_DATA, NotInCheckout, require

CORPUS_PATH = LINEAR_A_DATA / "corpus.json"
OUT_DIR = CACHE / "sigla" / "drawings"
MANIFEST_PATH = CACHE / "sigla" / "sigla_drawings.json"

UA = {"User-Agent": "kaphtor/1.0 (scholarly corpus mirror)"}
RATE_LIMIT_S = 1.0
BACKOFF_START_S = 5.0
BACKOFF_MAX_S = 300.0
MAX_ATTEMPTS = 7  # 5+10+20+40+80+160 s of backoff before giving up this run
SAVE_EVERY = 50
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


@dataclass
class Job:
    corpus_id: str
    sigla_id: str
    side: str | None
    url: str
    filename: str

    @property
    def path(self) -> Path:
        return OUT_DIR / self.filename


def _sanitize(s: str) -> str:
    import re
    return re.sub(r'[<>?*:/\\"|]', '', s).replace(" ", "_")


def normalize_id(corpus_id: str, side: str | None) -> str:
    stem = _sanitize(corpus_id)
    if side:
        stem += "_" + _sanitize(side)
    return stem + "-SigLA.png"


def collect_jobs(corpus: dict) -> list[Job]:
    jobs: list[Job] = []
    for corpus_id, entry in corpus.items():
        if not isinstance(entry, dict):
            continue
        sigla = entry.get("sigla")
        if isinstance(sigla, dict) and sigla.get("drawing_url"):
            jobs.append(Job(corpus_id, sigla.get("id", corpus_id), None,
                            sigla["drawing_url"], normalize_id(corpus_id, None)))
        sides = entry.get("sigla_sides")
        if isinstance(sides, dict):
            for side, block in sides.items():
                if isinstance(block, dict) and block.get("drawing_url"):
                    jobs.append(Job(corpus_id, block.get("id", corpus_id), side,
                                    block["drawing_url"], normalize_id(corpus_id, side)))
    return jobs


def _today() -> str:
    return datetime.now(UTC).date().isoformat()


def load_manifest() -> dict:
    if MANIFEST_PATH.exists():
        with open(MANIFEST_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {"created": _today(), "updated": None, "items": {}}


def save_manifest(manifest: dict) -> None:
    manifest["updated"] = _today()
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = MANIFEST_PATH.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    tmp.replace(MANIFEST_PATH)


def reconcile(manifest: dict, jobs: list[Job]) -> None:
    """Disk is ground truth: any nonzero file already present is done."""
    items = manifest["items"]
    for job in jobs:
        rec = items.setdefault(job.filename, {
            "corpus_id": job.corpus_id, "sigla_id": job.sigla_id,
            "url": job.url, "status": "pending", "size": 0, "attempts": 0,
        })
        rec["url"] = job.url  # corpus is ground truth for the URL
        if job.path.exists() and job.path.stat().st_size > 0:
            rec["status"] = "done"
            rec["size"] = job.path.stat().st_size
        elif rec["status"] == "done":
            rec["status"] = "pending"  # manifest said done but file is gone


def download(client: httpx.Client, job: Job, rec: dict) -> str:
    """One download with backoff. Returns final status for this run."""
    backoff = BACKOFF_START_S
    for attempt in range(1, MAX_ATTEMPTS + 1):
        rec["attempts"] = rec.get("attempts", 0) + 1
        try:
            resp = client.get(job.url)
            if resp.status_code == 404:
                rec["status"] = "missing_404"
                rec["error"] = "HTTP 404"
                return "missing_404"
            resp.raise_for_status()
            if not resp.content.startswith(PNG_MAGIC):
                raise ValueError(f"not a PNG (content-type {resp.headers.get('content-type')!r})")
            part = job.path.with_suffix(".png.part")
            part.write_bytes(resp.content)
            part.replace(job.path)
            rec["status"] = "done"
            rec["size"] = len(resp.content)
            rec["fetched"] = _today()
            rec.pop("error", None)
            return "done"
        except (httpx.HTTPError, ValueError, OSError) as exc:
            rec["status"] = "error"
            rec["error"] = f"{type(exc).__name__}: {exc}"
            if attempt < MAX_ATTEMPTS:
                print(f"    retry in {backoff:.0f}s — {rec['error']}", flush=True)
                time.sleep(backoff)
                backoff = min(backoff * 2, BACKOFF_MAX_S)
    part = job.path.with_suffix(".png.part")
    if part.exists():
        part.unlink()
    return "error"


def print_summary(manifest: dict, n_jobs: int) -> None:
    counts: dict[str, int] = {}
    total_bytes = 0
    for rec in manifest["items"].values():
        counts[rec["status"]] = counts.get(rec["status"], 0) + 1
        if rec["status"] == "done":
            total_bytes += rec.get("size", 0)
    print(f"\n{'status':<14}{'count':>7}")
    print("-" * 21)
    for status in ("done", "pending", "missing_404", "error"):
        if counts.get(status):
            print(f"{status:<14}{counts[status]:>7}")
    print("-" * 21)
    print(f"{'total':<14}{sum(counts.values()):>7}   ({n_jobs} drawing URLs in corpus, "
          f"{total_bytes / 1e6:.1f} MB on disk)")


def main() -> int:
    ap = argparse.ArgumentParser(description="Mirror SigLA inscription drawings locally.")
    ap.add_argument("--dry-run", action="store_true", help="plan only, no network")
    ap.add_argument("--test", type=int, metavar="N", help="download only the first N pending")
    ap.add_argument("--force", action="store_true", help="re-download even if done/missing_404")
    ap.add_argument("--summary-only", action="store_true", help="print status table and exit")
    args = ap.parse_args()

    try:
        corpus = json.loads(require(CORPUS_PATH, CORPUS_PATH.name).read_text(encoding="utf-8"))
    except NotInCheckout as e:
        print(f"stopped: {e}", file=sys.stderr)
        return 2
    jobs = collect_jobs(corpus)
    manifest = load_manifest()
    reconcile(manifest, jobs)

    if args.summary_only:
        print_summary(manifest, len(jobs))
        return 0

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    skip = () if args.force else ("done", "missing_404")
    queue = [j for j in jobs if manifest["items"][j.filename]["status"] not in skip]
    if args.test is not None:
        queue = queue[: args.test]

    print(f"{len(jobs)} drawing URLs in corpus, {len(queue)} to fetch"
          f"{' (dry run)' if args.dry_run else ''}")
    if args.dry_run:
        for job in queue[:20]:
            print(f"  {job.filename:<28} ← {job.url}")
        if len(queue) > 20:
            print(f"  … and {len(queue) - 20} more")
        return 0

    events = 0
    try:
        with httpx.Client(headers=UA, timeout=30.0, follow_redirects=True) as client:
            for i, job in enumerate(queue, 1):
                rec = manifest["items"][job.filename]
                print(f"[{i}/{len(queue)}] {job.filename}", flush=True)
                status = download(client, job, rec)
                if status == "done":
                    print(f"    ok — {rec['size']:,} bytes")
                else:
                    print(f"    {status} — {rec.get('error', '')}")
                events += 1
                if events % SAVE_EVERY == 0:
                    save_manifest(manifest)
                if i < len(queue):
                    time.sleep(RATE_LIMIT_S)
    except KeyboardInterrupt:
        print("\ninterrupted — saving manifest")
        save_manifest(manifest)
        print_summary(manifest, len(jobs))
        return 130

    save_manifest(manifest)
    print_summary(manifest, len(jobs))
    return 0


if __name__ == "__main__":
    sys.exit(main())
