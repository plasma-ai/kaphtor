#!/usr/bin/env python3
"""Ingest ORACC aemw/amarna corpus → amarna_canaanite.jsonl + enrichment data.

Downloads the bulk ZIP from ORACC, extracts glossary JSONs, and produces:
  - data/contact/amarna_canaanite.jsonl          (Canaanite lexicon entries)
  - CACHE/oracc/egyptian_candidates.jsonl        (Egyptian loanword candidates)
  - CACHE/oracc/affix_validation_triples.json    (affix-rule validation triples)

The ZIP and the extracted glossaries are kept in the user cache (`CACHE/oracc`), never in the
repository. An existing output is copied into `tools.paths.BACKUPS` before it is rewritten.

Usage:
  python3 tools/linear_a/ingest/ingest_oracc_amarna.py
  python3 tools/linear_a/ingest/ingest_oracc_amarna.py --use-cache
  python3 tools/linear_a/ingest/ingest_oracc_amarna.py --dry-run

Attribution: di Mino
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    __package__ = "tools.linear_a.ingest"

from ...core.contact_lexicon import normalize_canaanite
from ...paths import BACKUPS, CACHE, CONTACT_DATA

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

DATA_CONTACT = CONTACT_DATA
DATA_INGEST_ORACC = CACHE / "oracc"

ZIP_URL = "https://oracc.museum.upenn.edu/json/aemw-amarna.zip"
ZIP_PATH = DATA_INGEST_ORACC / "aemw-amarna.zip"
USER_AGENT = "kaphtor/1.0 (lexicon ingest)"

# Glossary paths inside the ZIP. ORACC uses flat gloss-{lang}.json files, not a
# glossary/ subdirectory. Proper nouns (divine, place, personal) are all in
# gloss-qpn.json, distinguished by POS (DN, GN, PN, EN).
GLOSSARY_PATHS = {
    "qca": "aemw/amarna/gloss-qca.json",
    "qpn": "aemw/amarna/gloss-qpn.json",
    "egy": "aemw/amarna/gloss-egy.json",
    "catalogue": "aemw/amarna/catalogue.json",
}

OUTPUT_CANAANITE = DATA_CONTACT / "amarna_canaanite.jsonl"
OUTPUT_EGYPTIAN = DATA_INGEST_ORACC / "egyptian_candidates.jsonl"
OUTPUT_AFFIX = DATA_INGEST_ORACC / "affix_validation_triples.json"


# ---------------------------------------------------------------------------
# Download and extract
# ---------------------------------------------------------------------------

def download_zip(use_cache: bool = False) -> Path:
    """Download the ORACC bulk ZIP; skip if cached and --use-cache."""
    DATA_INGEST_ORACC.mkdir(parents=True, exist_ok=True)

    if use_cache and ZIP_PATH.exists():
        print(f"  Using cached ZIP: {ZIP_PATH} ({ZIP_PATH.stat().st_size:,} bytes)")
        return ZIP_PATH

    if ZIP_PATH.exists() and not use_cache:
        print(f"  ZIP already exists ({ZIP_PATH.stat().st_size:,} bytes), re-downloading...")

    print(f"  Downloading {ZIP_URL} ...")
    # Use curl to avoid pyenv/homebrew Python SSL certificate issues
    result = subprocess.run(
        ["curl", "-fSL", "-A", USER_AGENT, "-o", str(ZIP_PATH), ZIP_URL],
        capture_output=True, text=True, timeout=120, check=False,
    )
    if result.returncode != 0:
        print(f"  ERROR: curl failed: {result.stderr}")
        raise RuntimeError(f"Download failed: {result.stderr}")
    print(f"  Downloaded: {ZIP_PATH.stat().st_size:,} bytes")
    return ZIP_PATH


def extract_glossaries(zip_path: Path) -> dict[str, Any]:
    """Extract the target JSON files from the ZIP. Returns {key: parsed_json}."""
    extracted: dict[str, Any] = {}

    with zipfile.ZipFile(zip_path, "r") as zf:
        namelist = zf.namelist()
        for key, target_path in GLOSSARY_PATHS.items():
            # Try exact path first, then partial match fallback
            matched = None
            if target_path in namelist:
                matched = target_path
            else:
                # Search for the filename component at end of path
                basename = target_path.rsplit("/", 1)[-1]
                for name in namelist:
                    if name.endswith("/" + basename) or name == basename:
                        matched = name
                        break

            if matched:
                data = json.loads(zf.read(matched))
                extracted[key] = data

                # Write to disk for inspection
                out_path = DATA_INGEST_ORACC / f"{key}.json"
                with open(out_path, "w") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                print(f"  Extracted {key}: {matched}")
            else:
                print(f"  WARNING: {key} not found in ZIP (expected {target_path})")

    return extracted


# ---------------------------------------------------------------------------
# Glossary parsing helpers
# ---------------------------------------------------------------------------

def _safe_int(val: Any) -> int:
    """Convert a value to int, handling strings like '1'."""
    if isinstance(val, int):
        return val
    if isinstance(val, str):
        try:
            return int(val)
        except ValueError:
            return 0
    return 0


def _extract_forms(entry: dict) -> list[dict]:
    """Extract form variants from an ORACC glossary entry.

    ORACC entries have `forms` (list of surface-form dicts with `n` key)
    and `norms` (list of normalized-form dicts). We collect both.
    """
    forms = []

    # Surface forms
    forms_raw = entry.get("forms", [])
    if isinstance(forms_raw, list):
        for fdata in forms_raw:
            if isinstance(fdata, dict):
                forms.append(fdata)
    elif isinstance(forms_raw, dict):
        for fdata in forms_raw.values():
            if isinstance(fdata, dict):
                forms.append(fdata)

    # Normalized forms (norms.n carries the vowel-resolved spelling)
    norms_raw = entry.get("norms", [])
    if isinstance(norms_raw, list):
        for ndata in norms_raw:
            if isinstance(ndata, dict) and ndata.get("n"):
                forms.append({"n": ndata["n"], "type": "norm"})

    return forms


def _make_match_keys(cf: str, forms: list[dict], normalized: str) -> list[str]:
    """Build deduplicated match_keys from citation form, forms, and normalized."""
    keys: list[str] = []
    seen: set[str] = set()

    def _add(candidate: str) -> None:
        norm = normalize_canaanite(candidate)
        if norm and norm not in seen:
            keys.append(norm)
            seen.add(norm)

    _add(normalized)
    _add(cf.lower())
    _add(cf)

    # Strip macrons, circumflexes, glottal stops for ASCII fallback matching
    ascii_stripped = re.sub(r"[āēīōūâêîôûʾʿ]", lambda m: {
        "ā": "a", "ē": "e", "ī": "i", "ō": "o", "ū": "u",
        "â": "a", "ê": "e", "î": "i", "ô": "o", "û": "u",
        "ʾ": "", "ʿ": "",
    }.get(m.group(), m.group()), normalized)
    _add(ascii_stripped)

    # Form variants
    for form in forms:
        n = form.get("n", "")
        if n:
            _add(n)

    return keys


def _pos_to_semantic_domain(pos: str) -> list[str]:
    """Map ORACC POS to semantic domains (must be in VALID_SEMANTIC_DOMAINS)."""
    pos_upper = pos.upper() if pos else ""
    if pos_upper == "DN":
        return ["divine_name"]
    elif pos_upper in ("GN", "SN", "WN", "FN", "TN"):
        return ["toponym"]
    elif pos_upper == "EN":
        return ["ethnonym"]
    elif pos_upper in ("RN", "PN"):
        return ["title"]
    else:
        return ["canaanite_loan"]


# ---------------------------------------------------------------------------
# Canaanite (qca) glossary → lexicon entries
# ---------------------------------------------------------------------------

def parse_qca_glossary(data: dict) -> list[dict[str, Any]]:
    """Parse the Canaanite (qca) glossary into lexicon entries.

    ORACC structure:
      data["entries"] = list of entry dicts, each with:
        cf (str), gw (str), pos (str), forms (list), norms (list),
        senses (list), icount (str), headword (str)
    """
    entries_out: list[dict[str, Any]] = []

    raw_entries = data.get("entries", [])
    if isinstance(raw_entries, dict):
        raw_entries = list(raw_entries.values())

    counter = 0
    for entry in raw_entries:
        if not isinstance(entry, dict):
            continue

        cf = entry.get("cf", "")
        gw = entry.get("gw", "")
        pos = entry.get("pos", "")

        if not cf and not gw:
            continue

        counter += 1
        forms = _extract_forms(entry)

        # Normalized form from citation form
        normalized = normalize_canaanite(cf) if cf else ""

        # Display form: prefer first surface form's 'n', else cf
        display_form = cf
        for f in forms:
            if f.get("n") and f.get("type") != "norm":
                display_form = f["n"]
                break

        # Semantic domain from POS
        domain = _pos_to_semantic_domain(pos)

        # Instance count
        icount = _safe_int(entry.get("icount", 0))

        match_keys = _make_match_keys(cf, forms, normalized)

        record = {
            "id": f"amarna:qca:{normalized or cf.lower()}:{counter:03d}",
            "language": "Canaanite",
            "source_corpus": "ORACC aemw/amarna",
            "form": display_form,
            "cf": cf,
            "normalized": normalized,
            "match_keys": match_keys if match_keys else [normalized or cf.lower()],
            "meaning": gw,
            "pos": pos,
            "semantic_domain": domain,
            "source_refs": [{"work": "ORACC aemw/amarna", "ref": "qca glossary"}],
            "review_status": "machine_imported",
        }
        if icount:
            record["instance_count"] = icount

        entries_out.append(record)

    return entries_out


# ---------------------------------------------------------------------------
# Proper noun (qpn) glossary → divine names + place names
# ---------------------------------------------------------------------------

def parse_qpn_by_pos(
    data: dict,
    target_pos: set[str],
    noun_type: str,
    semantic_domain: str,
) -> list[dict[str, Any]]:
    """Filter qpn glossary entries by POS → lexicon entries.

    target_pos: set of POS codes to include (e.g. {"DN"} or {"GN"})
    noun_type:  label for id prefix (e.g. "divine" or "places")
    semantic_domain: domain tag (e.g. "divine_name" or "toponym")
    """
    entries_out: list[dict[str, Any]] = []

    raw_entries = data.get("entries", [])
    if isinstance(raw_entries, dict):
        raw_entries = list(raw_entries.values())

    counter = 0
    for entry in raw_entries:
        if not isinstance(entry, dict):
            continue

        pos = entry.get("pos", "")
        if pos not in target_pos:
            continue

        cf = entry.get("cf", "")
        gw = entry.get("gw", "")

        if not cf:
            continue

        counter += 1
        normalized = normalize_canaanite(cf)
        forms = _extract_forms(entry)
        match_keys = _make_match_keys(cf, forms, normalized)

        # For proper nouns, gw is often just "1" (a numeric index).
        # Use the citation form as the meaning in that case.
        meaning = gw if gw and not gw.isdigit() else cf

        icount = _safe_int(entry.get("icount", 0))

        record = {
            "id": f"amarna:{noun_type}:{normalized or cf.lower()}:{counter:03d}",
            "language": "Canaanite",
            "source_corpus": "ORACC aemw/amarna",
            "form": cf,
            "cf": cf,
            "normalized": normalized,
            "match_keys": match_keys if match_keys else [normalized or cf.lower()],
            "meaning": meaning,
            "pos": pos,
            "semantic_domain": [semantic_domain],
            "source_refs": [
                {
                    "work": "ORACC aemw/amarna",
                    "ref": f"qpn glossary (POS={pos})",
                }
            ],
            "review_status": "machine_imported",
        }
        if icount:
            record["instance_count"] = icount

        entries_out.append(record)

    return entries_out


# ---------------------------------------------------------------------------
# Egyptian glossary → loanword candidates
# ---------------------------------------------------------------------------

def parse_egyptian_glossary(data: dict) -> list[dict[str, Any]]:
    """Parse Egyptian glossary → Egyptian loanword candidates."""
    entries_out: list[dict[str, Any]] = []

    raw_entries = data.get("entries", [])
    if isinstance(raw_entries, dict):
        raw_entries = list(raw_entries.values())

    counter = 0
    for entry in raw_entries:
        if not isinstance(entry, dict):
            continue

        cf = entry.get("cf", "")
        gw = entry.get("gw", "")
        pos = entry.get("pos", "")

        if not cf:
            continue

        counter += 1
        normalized = cf.lower().strip()

        record = {
            "id": f"amarna:egy:{normalized}:{counter:03d}",
            "language": "Egyptian",
            "source_corpus": "ORACC aemw/amarna",
            "form": cf,
            "cf": cf,
            "normalized": normalized,
            "meaning": gw if gw else "",
            "pos": pos,
            "source_refs": [{"work": "ORACC aemw/amarna", "ref": "egy glossary"}],
            "review_status": "machine_imported",
        }
        entries_out.append(record)

    return entries_out


# ---------------------------------------------------------------------------
# Affix validation triples
# ---------------------------------------------------------------------------

# Pattern: detect Canaanite morphological affixes in qca citation forms.
# Each rule matches an inflected form and extracts the stem/root candidate.
AFFIX_RULES = [
    {
        "name": "feminine_-at",
        "pattern": re.compile(r"^(.+?)[aā]t[iu]?$", re.IGNORECASE),
        "root_extractor": lambda m: m.group(1),
        "description": "Feminine -t/-at suffix",
    },
    {
        "name": "feminine_-t",
        "pattern": re.compile(r"^(.{2,}[^a])t$", re.IGNORECASE),
        "root_extractor": lambda m: m.group(1),
        "description": "Feminine -t suffix (non -at)",
    },
    {
        "name": "ma-_nominal_prefix",
        "pattern": re.compile(r"^ma(.{2,})$", re.IGNORECASE),
        "root_extractor": lambda m: m.group(1),
        "description": "ma- nominal prefix (maqtal pattern)",
    },
    {
        "name": "ya-_imperfect_prefix",
        "pattern": re.compile(r"^ya(.{2,})$", re.IGNORECASE),
        "root_extractor": lambda m: m.group(1),
        "description": "ya- imperfect prefix",
    },
    {
        "name": "ta-_prefix",
        "pattern": re.compile(r"^ta(.{2,})$", re.IGNORECASE),
        "root_extractor": lambda m: m.group(1),
        "description": "ta- prefix",
    },
]


def extract_affix_triples(entries: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Extract (inflected_form, expected_root, affix_rule) triples from qca entries.

    Only processes entries with POS in (N, V, AJ) — nominal, verbal, adjectival.
    Checks both the normalized citation form and all normalized surface/norm forms.
    """
    triples: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    for entry in entries:
        pos = entry.get("pos", "").upper()
        if pos not in ("N", "V", "AJ"):
            continue

        cf = entry.get("cf", "")
        normalized = entry.get("normalized", "")

        # Collect all form strings to check
        forms_to_check: list[str] = []
        if normalized and len(normalized) >= 3:
            forms_to_check.append(normalized)

        # Also check match_keys for norm-derived forms
        for mk in entry.get("match_keys", []):
            if mk and len(mk) >= 3 and mk not in forms_to_check:
                forms_to_check.append(mk)

        for form_str in forms_to_check:
            for rule in AFFIX_RULES:
                m = rule["pattern"].match(form_str)
                if m:
                    root_candidate = rule["root_extractor"](m)
                    key = (form_str, rule["name"])
                    if key not in seen:
                        seen.add(key)
                        triples.append({
                            "inflected_form": form_str,
                            "expected_root": root_candidate,
                            "affix_rule": rule["name"],
                            "description": rule["description"],
                            "cf": cf,
                            "pos": pos,
                        })

    return triples


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def backup_existing(path: Path, backups: Path = BACKUPS) -> None:
    """Copy `path` into `backups` under a timestamped name, if it exists."""
    if not path.exists():
        return
    stamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
    backups.mkdir(parents=True, exist_ok=True)
    dest = backups / f"{path.stem}-{stamp}{path.suffix}"
    shutil.copy2(path, dest)
    print(f"  backup {dest}")


def write_jsonl(entries: list[dict[str, Any]], path: Path) -> int:
    """Write entries to JSONL. Returns count."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        f.writelines(json.dumps(entry, ensure_ascii=False) + "\n" for entry in entries)
    return len(entries)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ingest ORACC aemw/amarna corpus → amarna_canaanite.jsonl"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be extracted without writing output files",
    )
    parser.add_argument(
        "--use-cache",
        action="store_true",
        help="Skip download, use cached ZIP",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("ORACC aemw/amarna Ingestion")
    print("=" * 60)

    # 1. Download
    print("\n[1] Download ZIP")
    zip_path = download_zip(use_cache=args.use_cache)

    # 2. Extract glossaries
    print("\n[2] Extract glossaries")
    glossaries = extract_glossaries(zip_path)

    if not glossaries:
        print("ERROR: No glossaries extracted. Aborting.")
        return 1

    # 2a. Check catalogue
    catalogue = glossaries.get("catalogue", {})
    cat_members = catalogue.get("members", {})
    if not cat_members:
        # ORACC catalogue: top-level keys that are entry dicts
        cat_members = {
            k: v for k, v in catalogue.items()
            if isinstance(v, dict) and (
                "id_text" in v or "designation" in v
                or "period" in v or "project" in v
            )
        }
    print(f"\n  Catalogue: {len(cat_members)} texts")
    if len(cat_members) < 200:
        print(f"  WARNING: Expected >=200 texts, got {len(cat_members)}")

    # 3. Parse qca glossary
    print("\n[3] Parse Canaanite (qca) glossary")
    qca_data = glossaries.get("qca")
    canaanite_entries: list[dict[str, Any]] = []
    if qca_data:
        canaanite_entries = parse_qca_glossary(qca_data)
        print(f"  Parsed {len(canaanite_entries)} qca entries")
    else:
        print("  WARNING: qca glossary not found in ZIP")

    # 4. Parse divine names from qpn (filtered by POS=DN)
    print("\n[4] Parse divine names (qpn, POS=DN)")
    qpn_data = glossaries.get("qpn")
    divine_entries: list[dict[str, Any]] = []
    if qpn_data:
        divine_entries = parse_qpn_by_pos(qpn_data, {"DN"}, "divine", "divine_name")
        print(f"  Parsed {len(divine_entries)} divine name entries")
    else:
        print("  WARNING: qpn glossary not found")

    # 5. Parse place names from qpn (filtered by POS=GN)
    print("\n[5] Parse place names (qpn, POS=GN)")
    place_entries: list[dict[str, Any]] = []
    if qpn_data:
        place_entries = parse_qpn_by_pos(qpn_data, {"GN"}, "places", "toponym")
        print(f"  Parsed {len(place_entries)} place name entries")
    else:
        print("  WARNING: qpn glossary not found")

    # Merge all into canaanite JSONL
    all_canaanite = canaanite_entries + divine_entries + place_entries

    # 6. Parse Egyptian candidates
    print("\n[6] Parse Egyptian candidates (egy)")
    egy_data = glossaries.get("egy")
    egyptian_entries: list[dict[str, Any]] = []
    if egy_data:
        egyptian_entries = parse_egyptian_glossary(egy_data)
        print(f"  Parsed {len(egyptian_entries)} Egyptian candidate entries")
    else:
        print("  WARNING: Egyptian glossary not found")

    # 7. Extract affix validation triples
    print("\n[7] Extract affix validation triples")
    affix_triples = extract_affix_triples(canaanite_entries)
    print(f"  Extracted {len(affix_triples)} affix triples")

    # 8. Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Catalogue texts:       {len(cat_members)}")
    print(f"  Canaanite (qca):       {len(canaanite_entries)}")
    print(f"  Divine names:          {len(divine_entries)}")
    print(f"  Place names:           {len(place_entries)}")
    print(f"  Total Canaanite JSONL: {len(all_canaanite)}")
    print(f"  Egyptian candidates:   {len(egyptian_entries)}")
    print(f"  Affix triples:         {len(affix_triples)}")

    if args.dry_run:
        print("\n  [DRY RUN] No files written.")
        # Show sample entries
        if all_canaanite:
            print("\n  Sample Canaanite entry:")
            print(f"    {json.dumps(all_canaanite[0], ensure_ascii=False, indent=4)}")
        if divine_entries:
            print("\n  Sample divine name entry:")
            print(f"    {json.dumps(divine_entries[0], ensure_ascii=False, indent=4)}")
        if affix_triples:
            print("\n  Sample affix triple:")
            print(f"    {json.dumps(affix_triples[0], ensure_ascii=False, indent=4)}")
        return 0

    # 9. Write outputs
    print("\n[8] Write output files")

    for out in (OUTPUT_CANAANITE, OUTPUT_EGYPTIAN, OUTPUT_AFFIX):
        backup_existing(out)

    n = write_jsonl(all_canaanite, OUTPUT_CANAANITE)
    print(f"  Wrote {n} entries → {OUTPUT_CANAANITE}")

    n = write_jsonl(egyptian_entries, OUTPUT_EGYPTIAN)
    print(f"  Wrote {n} entries → {OUTPUT_EGYPTIAN}")

    with open(OUTPUT_AFFIX, "w") as f:
        json.dump(affix_triples, f, indent=2, ensure_ascii=False)
    print(f"  Wrote {len(affix_triples)} triples → {OUTPUT_AFFIX}")

    # 10. Acceptance checks
    print("\n" + "=" * 60)
    print("ACCEPTANCE CHECKS")
    print("=" * 60)

    checks = [
        ("Catalogue >=200 texts", len(cat_members) >= 200),
        ("qca glossary parsed", len(canaanite_entries) > 0),
        ("All qca entries have cf+gw+pos",
         all(e.get("cf") and e.get("meaning") and e.get("pos")
             for e in canaanite_entries)),
        (">=30 entries in amarna_canaanite.jsonl", len(all_canaanite) >= 30),
        ("Divine names cross-listed", len(divine_entries) > 0),
        ("Place names cross-listed", len(place_entries) > 0),
        (">=10 affix triples", len(affix_triples) >= 10),
    ]

    all_pass = True
    for label, passed in checks:
        status = "PASS" if passed else "FAIL"
        if not passed:
            all_pass = False
        print(f"  [{status}] {label}")

    if all_pass:
        print("\n  All checks passed.")
        return 0
    print("\n  Some checks FAILED — review output above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
