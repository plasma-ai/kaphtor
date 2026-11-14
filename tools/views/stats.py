"""The headline counts of the Linear A record as one JSON file, `data/linear-a/stats.json`, for sites that print them.

    python -m tools.views.stats --data DIR [--check | --write | --print] [--backups DIR]

The wiki computes every count it prints; this file is the one stored copy, for pages outside the repository. Its keys,
the invariants it keeps and the contract with the sites that read it are in its datasheet, `data/linear-a/stats.md`.
The Semitic roots are counted in the `semitic-roots/` folder beside the data folder. `--check`, the default, writes
nothing and exits 1 naming each count that differs from the data, and the command that rewrites the file. `--write`
copies the file into `--backups` (by default `tools.paths.BACKUPS`, outside the repository) and replaces it whole.
`--print` prints the counts and touches no file. Data that cannot be counted (a file missing or not JSON, a key
missing, an invariant broken) stops with exit 2, naming the file or the cause.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = "tools.views"

from ..core.safe_write import backup_file, write_atomic
from ..paths import BACKUPS, REPO, NotInCheckout, require
from . import counts, model

NAME = "stats.json"
SCHEMA_VERSION = 1
DESCRIPTION = "Headline counts of the Linear A record, computed from the data files."
# resolution_summary's lists of sign values and the counters that must equal their lengths, fractions apart.
SIGN_LISTS = (("phonemic", "phonemic_count"), ("logograms", "logogram_count"))


def roots_file(data: Path) -> Path:
    """The root database beside the data folder `data` (resolved)."""
    return data.parent / "semitic-roots" / "semitic_roots.json"


def compute(data: Path) -> dict[str, Any]:
    """The counts of the data folder `data`. ValueError, naming the file, when a lexicon entry's confidence is none of
    the four tiers, a phonemic or logogram counter of `resolution_summary` (resolved or proposed) is not the length of
    its list, or the resolved total is not the resolved phonemic values and logograms together."""
    data = Path(data).resolve()
    loaded = model.load(data)
    tiers = counts.lexicon_tiers(loaded.lexicon.values())
    unknown = sorted(str(t) for t in set(tiers) - set(counts.TIERS))
    if unknown:
        raise ValueError(f"lexicon.json: confidence outside the four tiers: {', '.join(unknown)}")
    summary = loaded.sign_values["resolution_summary"]
    for block, values in (("resolution_summary", summary), ("resolution_summary.proposed", summary["proposed"])):
        for kind, counter in SIGN_LISTS:
            if values[counter] != len(values[kind]):
                raise ValueError(f"sign_values.json: {block}: {counter} is {values[counter]}, but its list "
                                 f"`{kind}` holds {len(values[kind])}")
    if summary["total"] != summary["phonemic_count"] + summary["logogram_count"]:
        raise ValueError(f"sign_values.json: {summary['total']} resolved sign values, but "
                         f"{summary['phonemic_count']} phonemic and {summary['logogram_count']} logograms")
    complete, incomplete = counts.translation_counts({k: t["raw"] for k, t in loaded.translations.items()})
    roots = json.loads(require(roots_file(data), "semitic_roots.json").read_text(encoding="utf-8"))["roots"]
    return {
        "schema_version": SCHEMA_VERSION,
        "description": DESCRIPTION,
        "corpus": {"records": len(loaded.corpus), "documents": len(counts.documents(loaded.corpus))},
        "lexicon": {"entries": len(loaded.lexicon), "tiers": {tier: tiers[tier] for tier in counts.TIERS}},
        "translations": {"complete": complete, "incomplete": incomplete},
        "sign_values": counts.sign_value_counts(summary),
        "names": len(loaded.onomasticon),
        "semitic_roots": len(roots),
    }


def json_text(stats: dict[str, Any]) -> str:
    """The text of stats.json: the counts as JSON, two-space indent, non-ASCII kept, one final newline."""
    return json.dumps(stats, ensure_ascii=False, indent=2) + "\n"


def flatten(value: Any, prefix: str = "") -> dict[str, Any]:
    """A nested dict as dotted keys: {"lexicon": {"entries": 692}} -> {"lexicon.entries": 692}."""
    if not isinstance(value, dict):
        return {prefix: value}
    return {k: v for key, item in value.items()
            for k, v in flatten(item, f"{prefix}.{key}" if prefix else key).items()}


def stale(old: str, fresh: dict[str, Any]) -> list[str]:
    """The dotted keys whose value in the file `old` differs from `fresh`, or the whole file when it is not JSON."""
    try:
        before = flatten(json.loads(old))
    except json.JSONDecodeError:
        return ["the whole file (not JSON)"]
    after = flatten(fresh)
    return sorted(k for k in before.keys() | after.keys() if before.get(k) != after.get(k))


def fix_command(data: Path) -> str:
    """The command that rewrites stats.json in the data folder `data` (resolved), named from the repository root."""
    folder = data.relative_to(REPO) if data.is_relative_to(REPO) else data
    return f"python -m tools.views.stats --data {folder} --write"


def unparsed(error: json.JSONDecodeError, data: Path) -> str:
    """The data file whose text `error` failed to parse, found by that text, since json keeps the text and not the
    file; "a data file" when none matches."""
    for path in (*sorted(data.glob("*.json")), roots_file(data)):
        if path.is_file() and path.read_text(encoding="utf-8", errors="replace") == error.doc:
            return str(path)
    return "a data file"


def main(argv: list[str] | None = None) -> int:
    """Exit 0 when stats.json is current or rewritten, 1 when it is stale, and 2, printing `stopped: <file or cause>:
    <message>`, when the data cannot be counted."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--data", type=Path, required=True, help="the folder holding the Linear A data files")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="report only; the default")
    mode.add_argument("--write", action="store_true", help="rewrite stats.json")
    mode.add_argument("--print", action="store_true", help="print the counts and touch no file")
    parser.add_argument("--backups", type=Path, default=BACKUPS, help="where --write copies the file first")
    args = parser.parse_args(argv)

    data = args.data.resolve()
    try:
        fresh = compute(data)
    except NotInCheckout as e:
        return _stopped(str(e))
    except json.JSONDecodeError as e:  # a ValueError, so caught first
        return _stopped(f"{unparsed(e, data)}: {e}")
    except KeyError as e:
        return _stopped(f"a key the counts read is missing: {e}")
    except ValueError as e:
        return _stopped(str(e))
    if args.print:
        sys.stdout.write(json_text(fresh))
        return 0
    target = data / NAME
    old = target.read_text(encoding="utf-8") if target.exists() else None
    if old == json_text(fresh):
        print(f"{NAME}: current")
        return 0
    changed = (stale(old, fresh) or ["formatting only"]) if old is not None else ["the whole file (missing)"]
    if not args.write:
        print(f"{NAME}: stale: {', '.join(changed)}; rewrite it with {fix_command(data)}")
        return 1
    saved = backup_file(target, args.backups) if old is not None else None
    write_atomic(target, json_text(fresh))
    print(f"{NAME}: rewrote {', '.join(changed)}" + (f"; the old file is {saved}" if saved else ""))
    return 0


def _stopped(message: str) -> int:
    print(f"stopped: {message}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
