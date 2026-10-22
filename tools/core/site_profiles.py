"""Loader and validator for per-site language prior profiles."""
from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    from ..paths import LINEAR_A_DATA, require
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from tools.paths import LINEAR_A_DATA, require

DATA_DIR = LINEAR_A_DATA
SITE_PROFILES_PATH = DATA_DIR / "site_language_profiles.json"

_cached_profiles: dict | None = None


def load_site_profiles(path: Path = SITE_PROFILES_PATH) -> dict:
    global _cached_profiles
    if _cached_profiles is not None:
        return _cached_profiles
    raw = json.loads(require(path, path.name).read_text(encoding="utf-8"))
    if raw.get("schema_version") != 1:
        raise ValueError(f"Unsupported schema_version: {raw.get('schema_version')}")
    _cached_profiles = raw
    return raw


def validate_site_profiles(profiles: dict, corpus_sites: set[str]) -> list[str]:
    """Return a list of validation errors (empty = valid)."""
    errors: list[str] = []
    categories = set(profiles.get("categories", []))
    if not categories:
        errors.append("Missing or empty 'categories' field")
        return errors

    def _check_distribution(name: str, entry: dict) -> None:
        langs = entry.get("languages", {})
        if set(langs.keys()) != categories:
            errors.append(f"{name}: language keys {set(langs.keys())} != categories {categories}")
        total = sum(langs.values())
        if abs(total - 1.0) > 0.02:
            errors.append(f"{name}: language priors sum to {total:.3f}, expected ~1.0")
        if "site_weight" not in entry:
            errors.append(f"{name}: missing site_weight")

    _check_distribution("default", profiles.get("default", {}))

    sites_in_json = set(profiles.get("sites", {}).keys())
    for site_name, entry in profiles.get("sites", {}).items():
        _check_distribution(f"site[{site_name!r}]", entry)

    missing = corpus_sites - sites_in_json
    if missing:
        errors.append(f"Corpus sites missing from profiles: {sorted(missing)}")

    return errors


def get_site_prior(site: str, lang_category: str, profiles: dict) -> float:
    """Return the language prior for (site, category), falling back to default."""
    site_entry = profiles.get("sites", {}).get(site)
    if site_entry is None:
        site_entry = profiles.get("default", {})
    return site_entry.get("languages", {}).get(lang_category, 0.10)


def get_site_weight(site: str, profiles: dict) -> float:
    """Return the site_weight for composing priors."""
    site_entry = profiles.get("sites", {}).get(site)
    if site_entry is None:
        site_entry = profiles.get("default", {})
    return site_entry.get("site_weight", 0.35)
