#!/usr/bin/env python3
"""Phase 0 harness for the Shoresh root-match engine.

Captures the pre-change state of cognate_search.py so the new engine and the
Phase 3 shim can be measured against it. Each subcommand writes one NEW
fixture (exclusive, atomic create; an existing fixture is never overwritten):

  gold         tests/fixtures/root_match_gold.json
               Gold positives (tier >= 3 Semitic lexicon entries with a parseable
               root), negatives (REJECTED, non-Semitic layers), and seeded
               controls (sign shuffles + corpus-frequency fabrications).
  golden       tests/fixtures/cognate_search_golden.json
               search_cognates() output for 200 corpus words, two flag configs,
               the byte-identity target for the Phase 3 shim.
  baseline     tests/fixtures/root_match_baseline.json
               Root recovery (hit@k, MRR) and discrimination AUC of the current
               Proto-Semitic layer on the gold set, plus CLI latency/peak RSS.
  gold-v2      tests/fixtures/root_match_gold.v2.json (ref §6, amendment A1)
               The gold set rebuilt under the §6 rules: skeletons fail loud on
               an unmapped sign, positives carry `informative` (>= 3 consonants)
               and `lb_values_only`, shuffles never repeat their source's
               skeleton, fabrications are position-matched and skeleton-length
               matched, and the Linear B controls are added (Greek vocabulary
               negatives, Semitic-loan positives, and their shuffles).
  baseline-v2  tests/fixtures/root_match_baseline.v2.json
               The baseline on gold v2: tie-aware expected ranks, bootstrap
               AUC intervals, and the Linear A vs Linear B real-minus-shuffled
               margins.
  gold-v3      tests/fixtures/root_match_gold.v3.json
               Gold v2 with lexicon spellings of project sign values rewritten in
               corpus signs (PI-QI-TE → PI-*34-TE), so *34 words are no longer
               excluded as unmapped.
  baseline-v3  tests/fixtures/root_match_baseline.v3.json
               The baseline-v2 measurements on gold v3.
  gold-v4      tests/fixtures/root_match_gold.v4.json (ref §6 A22)
               Positives in two strata (primary: Linear B values, root record
               in v3's roots file, plus strong tier 1-2 words of 4-5 signs;
               secondary: the rest), one sign group per root record, no
               two-sign word; skeletons one consonant per sign (A16). Also
               hashes v3's roots file, gold v3, the archive, the exposure
               ledger root_match_exposure.v4.json and the semantic gate.
  baseline-v4  tests/fixtures/root_match_baseline.v4.json (ref §6 A22)
               Recovery by target Number in the top 5 (D5) and A2's contrast
               with a distance-matched Linear B margin per stratum (D3).

Every fixture carries sha256 provenance of its inputs (a missing input is
recorded as missing), hashed before and after the run; if any input changed
mid-run the fixture is not written. A baseline refuses a gold set built from
other inputs. Long runs read a frozen snapshot (ref §7.7).

Usage:
  uv run tools/linear_a/validation/root_match_phase0.py gold
  uv run tools/linear_a/validation/root_match_phase0.py golden
  uv run tools/linear_a/validation/root_match_phase0.py baseline [--latency-words 20]
  uv run tools/linear_a/validation/root_match_phase0.py gold-v2
  uv run tools/linear_a/validation/root_match_phase0.py baseline-v2
  uv run tools/linear_a/validation/root_match_phase0.py gold-v3
  uv run tools/linear_a/validation/root_match_phase0.py baseline-v3
  uv run tools/linear_a/validation/root_match_phase0.py gold-v4
  uv run tools/linear_a/validation/root_match_phase0.py baseline-v4
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import statistics
import subprocess
import sys
import time
from collections import Counter
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from itertools import pairwise
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    __package__ = "tools.linear_a.validation"

from ...core.data_cache import sign_value_entries as campaign_entries
from ...core.phonetics import GUTTURAL_PHONEMES, _tokenize_phonemes
from ...core.semitic_root_schema import roots_records
from ...core.skeleton import _SUBSCRIPT_MAP, _lookup_sign, extract_skeleton
from ...paths import ANE_DATA, CONTACT_DATA, LINEAR_A_DATA, REPO, SEMITIC_ROOTS_DATA
from ..cognate_search import (
    _extract_root_consonant_variants,
    search_cognates,
)
from .null_model_audit import load_corpus_words

DATA_DIR = LINEAR_A_DATA
FIXTURE_DIR = REPO / "tests" / "fixtures"
GOLD_PATH = FIXTURE_DIR / "root_match_gold.json"
GOLDEN_PATH = FIXTURE_DIR / "cognate_search_golden.json"
BASELINE_PATH = FIXTURE_DIR / "root_match_baseline.json"
GOLD_V2_PATH = FIXTURE_DIR / "root_match_gold.v2.json"
BASELINE_V2_PATH = FIXTURE_DIR / "root_match_baseline.v2.json"
GOLD_V3_PATH = FIXTURE_DIR / "root_match_gold.v3.json"
BASELINE_V3_PATH = FIXTURE_DIR / "root_match_baseline.v3.json"
GOLD_V4_PATH = FIXTURE_DIR / "root_match_gold.v4.json"
BASELINE_V4_PATH = FIXTURE_DIR / "root_match_baseline.v4.json"
ROOTS_V3_PATH = SEMITIC_ROOTS_DATA / "semitic_roots.json.bak-2026-10-16-pre-cases"   # gold v3's roots file (sha 42167a4e)
EXPOSURE_V4_PATH = FIXTURE_DIR / "root_match_exposure.v4.json"                     # A22's engine-exposure ledger (E1, E2)
ANE_DATA_DIR = ANE_DATA

SEED = 20261016
GOLDEN_SIZE = 200
SEMITIC_LAYER_PREFIXES = ("NWS", "Akkad", "East Semitic")
NON_SEMITIC_LAYERS = ("Middle Egyptian", "Hurrian", "Anatolian", "Anatolian candidate")
# Words the plan's spot checks and evals name: always in the golden record.
PINNED_WORDS = ("KU-NI-SU", "KU-RO", "TI-TI-KU", "JA-DI-KI-TU", "DE-JU-KU")

# Flag configs for the golden record: every searcher, with and without the
# two lenses (the lenses route through the same per-language searchers).
ALL_LANGUAGES = {
    "include_luwian": True, "include_egyptian": True, "include_ugaritic": True,
    "include_amorite": True, "include_greek": True, "include_hebrew": True,
    "include_aramaic": True, "include_geez": True, "include_south_arabian": True,
    "include_arabian": True,
}
GOLDEN_CONFIGS = {
    "all_languages": ALL_LANGUAGES,
    "all_languages_lenses": {**ALL_LANGUAGES, "verb_lens": True, "historical_lens": True},
}
CLI_FLAGS = ["--luwian", "--egyptian", "--ugaritic", "--amorite", "--greek",
             "--hebrew", "--aramaic", "--geez", "--south-arabian", "--arabian"]

# §6 A1: an informative skeleton has at least this many consonants.
INFORMATIVE_MIN = 3
# §6 A2: the Linear B controls. Negatives: Ventris & Chadwick 1956 Appendix I
# vocabulary concurring with DMic, no loan or foreign word, informative
# skeleton, at most LB_NEGATIVE_CAP (seeded sample). Positives: the four
# Mycenaean Semitic loans V&C and Masson agree on.
LB_SEMITIC_LOANS = {"ku-ru-so": "ḫurāṣu / ḥrṣ 'gold'", "ki-to": "kitû, ktn 'linen, tunic'",
                    "ku-mi-no": "kamūnu 'cumin'", "sa-sa-ma": "šamaššammū 'sesame'"}
LB_NEGATIVE_CAP = 200
_LOAN_WORDING = re.compile(r"loan|foreign|pre-?greek|semitic|hebrew|egypt|akkad|phoenic|anatolian|hittite|"
                           r"luwian|non-?greek|borrow", re.IGNORECASE)
# Gold v3: the lexicon writes the project's value where the corpus writes the sign number. *34 is the only
# such sign (resolution_summary "*34=QI"; the corpus has PI-*34-TE, the lexicon PI-QI-TE). Linear B's QI is
# AB21 and is not aliased.
LEXICON_SIGN_ALIASES = {"QI": "*34"}


def tracked_inputs() -> list[Path]:
    """Inputs whose change would invalidate a fixture: every data file and module search_cognates, the gold
    rules and the corpus loader read (the contact lexica globbed at call time, the ANE onomasticon included)."""
    return [
        SEMITIC_ROOTS_DATA / "semitic_roots.json",
        DATA_DIR / "lexicon.json",
        DATA_DIR / "corpus.json",
        DATA_DIR / "gordon.json",
        DATA_DIR / "luwian_roots.json",
        DATA_DIR / "egyptian_roots.json",
        DATA_DIR / "compound_morphemes.json",
        DATA_DIR / "verb_templates.json",
        DATA_DIR / "sign-registry.json",
        DATA_DIR / "sign_values.json",
        DATA_DIR / "linear_b_vc1956_glosses.json",
        REPO / "tools" / "linear_a" / "cognate_search.py",
        REPO / "tools" / "linear_a" / "validation" / "null_model_audit.py",
        *(REPO / "tools" / "core" / f"{m}.py" for m in ("phonetics", "skeleton", "verb_morphology",
                                                         "semitic_morphology", "normalization", "greek_spelling",
                                                         "types", "root_index", "semitic_root_schema",
                                                         "semitic_notation")),
        SEMITIC_ROOTS_DATA / "semitic_correspondences.json",
        *sorted(CONTACT_DATA.glob("*.jsonl")),
        ANE_DATA_DIR / "arabian_onomasticon.jsonl",
    ]


# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------

def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _rel(p: Path) -> str:
    try:
        return str(p.relative_to(REPO))
    except ValueError:
        return str(p)


def input_hashes(extra: Sequence[Path] = ()) -> dict[str, str | None]:
    """sha256 per tracked input, and per `extra` input a fixture also reads; None for one that does not exist (its
    arrival is a change too)."""
    return {_rel(p): _sha256(p) if p.exists() else None for p in (*tracked_inputs(), *extra)}


def changed_inputs(before: dict[str, str | None], after: dict[str, str | None]) -> list[str]:
    return sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))


def _git_head() -> str | None:
    try:
        return subprocess.run(
            ["git", "-C", str(REPO), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def write_fixture(path: Path, payload: dict[str, Any], hashes_before: dict[str, str | None],
                  extra: Sequence[Path] = ()) -> None:
    """Write a fixture only if no tracked input (nor `extra` input) changed during the run. The JSON goes to a temp
    file first and is linked into place (fails if the target exists), so a crash never leaves a half-written fixture."""
    changed = changed_inputs(hashes_before, input_hashes(extra))
    if changed:
        sys.exit(f"inputs changed during the run, fixture NOT written: {changed}")
    payload["provenance"] = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "generator": "tools/linear_a/validation/root_match_phase0.py",
        "git_head": _git_head(),
        "seed": SEED,
        "input_sha256": hashes_before,
    }
    text = json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=False, allow_nan=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp-{os.getpid()}")
    try:
        with open(tmp, "x", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.link(tmp, path)                       # exclusive: never overwrite
    finally:
        tmp.unlink(missing_ok=True)
    print(f"wrote {_rel(path)}")


def _refuse_existing(path: Path) -> None:
    if path.exists():
        sys.exit(f"{_rel(path)} exists; move it aside to regenerate (never overwritten)")


def _read_gold(path: Path, before: dict[str, str | None]) -> dict[str, Any]:
    """The gold fixture, refused unless it was built from exactly the current inputs (one snapshot, §7.7)."""
    if not path.exists():
        sys.exit(f"{_rel(path)} not built; run its gold command first")
    gold = json.loads(path.read_text(encoding="utf-8"))
    built = gold.get("provenance", {}).get("input_sha256", {})
    differ = sorted(k for k in built if built[k] != before.get(k))
    if differ:
        sys.exit(f"{_rel(path)} was built from other inputs ({differ[:5]}); rebuild both on one snapshot")
    return gold


def sign_group_key(word: str) -> tuple[str, ...]:
    """A sign group as the gold guard compares it: signs upper-cased, subscripts as digits (A-PA₃ = a-pa3)."""
    return tuple(s.upper().translate(_SUBSCRIPT_MAP) for s in word.strip().split("-") if s)


GOLD_SECTIONS = ("positives", "negatives", "controls", "lb_negatives", "lb_loans", "lb_shuffles", "excluded")


def gold_sign_groups(path: Path = GOLD_V3_PATH) -> set[tuple[str, ...]]:
    """Every sign group the gold set holds, in any section (rows, controls, exclusions), as corpus or lexicon
    spelling. No engine number is taken on these before the gold run (ref §6 A14). A file without every gold
    section as a non-empty list raises ValueError: an empty set would let every word through."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or any(not isinstance(data.get(s), list) or not data[s] for s in GOLD_SECTIONS):
        raise ValueError(f"{path.name} lacks a gold section ({', '.join(GOLD_SECTIONS)} must be non-empty lists)")
    return {sign_group_key(row[f]) for rows in data.values() if isinstance(rows, list)
            for row in rows if isinstance(row, dict) for f in ("word", "lexicon_word") if row.get(f)}


def reading_key(word: str, conventional: bool = False) -> tuple | None:
    """A sign group as the engine reads it: each sign's readings (lib.root_match.sign_options); None with an unmapped
    sign, which the engine refuses anyway. KU2-RO, KU-RO9 and KU-*310-SU read as KU-RO and KU-NI-SU do."""
    from ...core import root_match as rm
    try:
        return tuple(tuple(rm.sign_options(s, conventional=conventional)) for s in rm.word_signs(word))
    except rm.UnmappedSign:
        return None


def gold_guard(path: Path = GOLD_V3_PATH, conventional: bool = False) -> Callable[[str], bool]:
    """word → whether it is a gold-set sign group, by name (sign_group_key) or by reading (reading_key): a spelling
    the engine reads as a gold word gives that word's numbers, so it is held back with it (A14). A conventional run
    also holds back a spelling that reads as one by Linear B values (X-PA-Y as X-PA₃-Y)."""
    names = gold_sign_groups(path)
    modes = (False, True) if conventional else (False,)
    readings = {(m, k) for m in modes for g in names if (k := reading_key("-".join(g), m)) is not None}

    def is_gold(word: str) -> bool:
        if sign_group_key(word) in names:
            return True
        return any((m, k) in readings for m in modes if (k := reading_key(word, m)) is not None)
    return is_gold


# ---------------------------------------------------------------------------
# Root keys
# ---------------------------------------------------------------------------

def parse_lexicon_root(root: str | None, unparsed: list[str] | None = None) -> list[tuple[str, ...]]:
    """'k-n-s' → [('k','n','s')]; 'q-y-n / q-n-y' → two keys; prose → []. Alternatives that do not parse are
    appended to `unparsed` (so a dropped gold root is visible, never silent)."""
    if not root:
        return []
    keys = []
    for alt in root.split("/"):
        parts = [p.strip() for p in alt.strip().lstrip("√").rstrip("?").split("-")]
        if len(parts) < 2 or not all(p and _ROOT_TOKEN.match(p) for p in parts):
            if unparsed is not None:
                unparsed.append(alt.strip())
            continue
        toks = tuple(t for p in parts for t in _tokenize_phonemes(p))
        if len(toks) == len(parts):  # one phoneme per radical, else prose
            keys.append(toks)
        elif unparsed is not None:
            unparsed.append(alt.strip())
    return keys


_ROOT_TOKEN = re.compile(r"^[^\s\d()]+$")


def fold_gutturals(key: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(t for t in key if t not in GUTTURAL_PHONEMES)


def ps_match_keys(ps_root: str) -> list[tuple[str, ...]]:
    return [tuple(_tokenize_phonemes(v)) for v in _extract_root_consonant_variants(ps_root)]


def recovery_rank(gold_keys: list[tuple[str, ...]], ps_matches: list[dict]) -> tuple[int | None, int | None]:
    """1-based rank of the first PS match whose radicals equal a gold root —
    exact canonical tokens, and with gutturals folded on both sides."""
    exact = folded = None
    gold_exact = set(gold_keys)
    gold_folded = {fold_gutturals(k) for k in gold_keys}
    for rank, m in enumerate(ps_matches, start=1):
        keys = ps_match_keys(m.get("root", ""))
        if exact is None and any(k in gold_exact for k in keys):
            exact = rank
        if folded is None and any(fold_gutturals(k) in gold_folded for k in keys):
            folded = rank
    return exact, folded


def expected_rank(gold_keys: list[tuple[str, ...]], ps_matches: list[dict], folded: bool = False
                  ) -> tuple[float | None, bool]:
    """(expected 1-based rank of the first gold match under random tie-breaking, tie group truncated?).

    With B matches strictly closer than the best gold match and a tie group of T matches at its distance, G of
    them gold, the expected position of the first gold one is B + (T + 1) / (G + 1). The group is truncated
    when the list ends at that distance (the search's top_n cut it)."""
    f = fold_gutturals if folded else (lambda k: k)
    gold = {f(k) for k in gold_keys}
    return _expected_rank_of([any(f(k) in gold for k in ps_match_keys(m.get("root", ""))) for m in ps_matches],
                             ps_matches)


def _expected_rank_of(is_gold: list[bool], ps_matches: list[dict]) -> tuple[float | None, bool]:
    """expected_rank's formula on given flags: which of ps_matches count as the target."""
    if not any(is_gold):
        return None, False
    d = min(m["distance"] for m, g in zip(ps_matches, is_gold) if g)
    better = sum(1 for m in ps_matches if m["distance"] < d)
    ties = [g for m, g in zip(ps_matches, is_gold) if m["distance"] == d]
    return better + (len(ties) + 1) / (sum(ties) + 1), ps_matches[-1]["distance"] == d


# ---------------------------------------------------------------------------
# skeletons, decoys
# ---------------------------------------------------------------------------

def _syllabic(word: str) -> bool:
    return "-" in word and "+" not in word and not word.replace("-", "").isdigit()


def loud_skeleton(word: str) -> tuple[str, list[str]]:
    """(skeleton, signs with no decomposition). Never shortens a word silently: a caller excludes any word
    whose second element is non-empty (§6 A1)."""
    consonants, unmapped = _sign_consonants(word)
    return "".join(consonants), unmapped


def _sign_consonants(word: str) -> tuple[list[str], list[str]]:
    """(consonants, unmapped signs): one consonant per sign that has one, as loud_skeleton reads them (A16)."""
    consonants, unmapped = [], []
    for sign in word.split("-"):
        decomp = _lookup_sign(sign)
        if decomp is None:
            unmapped.append(sign)
        elif decomp[0]:
            consonants.append(decomp[0])
    return consonants, unmapped


def _skel_len(word: str) -> int:
    return len(_tokenize_phonemes(extract_skeleton(word)))


def _ocp_ok(word: str) -> bool:
    """No two identical consonants adjacent in the skeleton (the Semitic OCP on C1/C2)."""
    toks = _tokenize_phonemes(extract_skeleton(word))
    return all(a != b for a, b in pairwise(toks))


def position_tables(words: list[str]) -> dict[str, tuple[tuple[str, ...], tuple[int, ...]]]:
    """Sign frequencies by position (initial, medial, final) over the mapped corpus words."""
    tables: dict[str, Counter] = {"initial": Counter(), "medial": Counter(), "final": Counter()}
    for w in words:
        signs = w.split("-")
        if len(signs) < 2 or loud_skeleton(w)[1]:
            continue
        tables["initial"][signs[0]] += 1
        tables["final"][signs[-1]] += 1
        tables["medial"].update(signs[1:-1])
    return {k: tuple(zip(*sorted(c.items()))) for k, c in tables.items()}  # type: ignore[misc]


def fabricate(rng: random.Random, n_signs: int, skel_len: int, tables: dict, real: set[str],
              tries: int = 500, tokens: Callable[[str], Sequence[str]] | None = None, ocp: bool = True) -> str | None:
    """A position-matched pseudo-word (§6 A3, decoy family B): initial, medial and final signs drawn from their
    own corpus distributions, the source's sign count and skeleton length, OCP kept, not a real word. tokens(w)
    gives the skeleton's tokens; by default _skel_len and _ocp_ok's, as the gold set was built (Shoresh passes its
    own, one per letter). ocp=False (A17, the tokens path only) lets two identical consonants stand side by side,
    for a source word that has them."""
    for _ in range(tries):
        signs = [rng.choices(*tables["initial"])[0]]
        signs += rng.choices(*tables["medial"], k=max(0, n_signs - 2)) if n_signs > 2 else []
        if n_signs > 1:
            signs.append(rng.choices(*tables["final"])[0])
        w = "-".join(signs)
        if w in real:
            continue
        if tokens is None:
            if _skel_len(w) == skel_len and _ocp_ok(w):
                return w
            continue
        toks = tokens(w)
        if len(toks) == skel_len and (not ocp or all(a != b for a, b in pairwise(toks))):
            return w
    return None


def shuffle_new_skeleton(rng: random.Random, word: str, tries: int = 200) -> str | None:
    """A sign shuffle whose skeleton differs from the source's (A-KA-NU → KA-A-NU repeats k-n: not a control)."""
    parts, skel = word.split("-"), extract_skeleton(word)
    for _ in range(tries):
        s = parts[:]
        rng.shuffle(s)
        if s != parts and extract_skeleton("-".join(s)) != skel:
            return "-".join(s)
    return None


def _resolution_pairs() -> set[str]:
    """The sign_values resolution_summary phonemic entries, resolved and proposed, as written ("*34=QI")."""
    rs = json.loads((DATA_DIR / "sign_values.json").read_text(encoding="utf-8"))["resolution_summary"]
    return set(campaign_entries(rs, "phonemic"))


def campaign_signs() -> set[str]:
    """Signs whose value is the project's (sign_values resolution_summary, phonemic, resolved or proposed): no
    Linear B value."""
    out = set()
    for item in _resolution_pairs():
        sign = item.split("=")[0].strip()
        out.add(sign)
        out.add(sign.translate(str.maketrans("₂₃₄₅", "2345")))
    out |= {"QI"} if "*34" in out else set()
    return out


def lexicon_sign_aliases() -> dict[str, str]:
    """LEXICON_SIGN_ALIASES, each checked against its resolution_summary entry: a stale alias stops the build."""
    pairs = _resolution_pairs()
    stale = [f"{sign}={value}" for value, sign in LEXICON_SIGN_ALIASES.items() if f"{sign}={value}" not in pairs]
    if stale:
        raise SystemExit(f"sign_values resolution_summary no longer lists {stale}: LEXICON_SIGN_ALIASES is stale")
    return dict(LEXICON_SIGN_ALIASES)


def corpus_spelling(word: str) -> str:
    """A lexicon word in corpus signs: PI-QI-TE → PI-*34-TE."""
    return "-".join(LEXICON_SIGN_ALIASES.get(s, s) for s in word.split("-"))


# ---------------------------------------------------------------------------
# gold
# ---------------------------------------------------------------------------

def build_gold() -> None:
    _refuse_existing(GOLD_PATH)
    before = input_hashes()
    rng = random.Random(SEED)
    entries = json.loads((DATA_DIR / "lexicon.json").read_text(encoding="utf-8"))["entries"]

    positives, negatives, excluded = [], [], []
    for e in entries:
        word, layer, tier = e.get("word", ""), str(e.get("language_layer") or ""), e.get("tier", 0)
        candidate = (e.get("confidence") == "REJECTED" or (layer in NON_SEMITIC_LAYERS and tier >= 2)
                     or (tier >= 3 and layer.startswith(SEMITIC_LAYER_PREFIXES)))
        row = {"word": word, "root": e.get("root"), "meaning": e.get("meaning", ""),
               "tier": tier, "language_layer": e.get("language_layer"),
               "skeleton": extract_skeleton(word) if _syllabic(word) else ""}
        if not _syllabic(word):
            if tier >= 3 and layer.startswith(SEMITIC_LAYER_PREFIXES):
                excluded.append({"word": word, "reason": "not a syllabic sign group"})
            continue
        row["skeleton_len"] = len(_tokenize_phonemes(row["skeleton"]))
        if not row["skeleton"]:
            # Egyptian group-writing (Keftiu spells) and logogram+sign groups
            # have no Linear A skeleton; the skeleton matcher cannot score them.
            if candidate:
                excluded.append({"word": word, "reason": "no Linear A skeleton"})
            continue
        if e.get("confidence") == "REJECTED":
            negatives.append({**row, "kind": "rejected"})
        elif layer in NON_SEMITIC_LAYERS and tier >= 2:
            negatives.append({**row, "kind": "non_semitic_layer"})
        elif tier >= 3 and layer.startswith(SEMITIC_LAYER_PREFIXES):
            keys = parse_lexicon_root(e.get("root"))
            if not keys:
                excluded.append({"word": word, "reason": f"root not parseable: {e.get('root')!r}"})
                continue
            positives.append({**row, "root_keys": ["-".join(k) for k in keys]})

    # Controls: one seeded sign shuffle per positive (differing from the
    # original), and one corpus-frequency fabrication of matched length.
    corpus_words = load_corpus_words()
    sign_counts = Counter(s for w in corpus_words for s in w.split("-"))
    signs, weights = zip(*sorted(sign_counts.items()))
    real = set(corpus_words)
    controls = []
    for p in positives:
        parts = p["word"].split("-")
        if len(set(parts)) > 1:
            for _ in range(50):
                shuffled = parts[:]
                rng.shuffle(shuffled)
                if shuffled != parts:
                    controls.append({"word": "-".join(shuffled), "kind": "sign_shuffle", "source": p["word"]})
                    break
        for _ in range(50):
            fab = "-".join(rng.choices(signs, weights=weights, k=len(parts)))
            if fab not in real:
                controls.append({"word": fab, "kind": "fabricated", "source": p["word"]})
                break
    for c in controls:
        c["skeleton"] = extract_skeleton(c["word"])
        c["skeleton_len"] = len(_tokenize_phonemes(c["skeleton"]))

    payload = {
        "description": ("Shoresh gold set. Positives were found by the pre-Shoresh matcher, "
                        "so they measure recall only; false-positive rates come from "
                        "negatives and controls."),
        "counts": {"positives": len(positives), "negatives": len(negatives),
                   "controls": len(controls), "excluded": len(excluded)},
        "positives": positives, "negatives": negatives,
        "controls": controls, "excluded": excluded,
    }
    write_fixture(GOLD_PATH, payload, before)
    print(json.dumps(payload["counts"]))


def _lb_words(one_letter: bool = False) -> tuple[list[dict], list[dict], list[dict]]:
    """(negatives, loans, excluded) from the V&C 1956 glossary, by the §6 A2 rule. one_letter counts a skeleton
    one consonant per sign (gold v4, A16) rather than by phoneme tokens."""
    entries = json.loads((DATA_DIR / "linear_b_vc1956_glosses.json").read_text(encoding="utf-8"))["entries"]
    negatives, loans, excluded = [], [], []

    def length(word: str, skel: str) -> int:
        return len(_sign_consonants(word)[0]) if one_letter else len(_tokenize_phonemes(skel))

    for lemma, e in sorted(entries.items()):
        if lemma in LB_SEMITIC_LOANS:
            word = lemma.upper()
            skel, unmapped = loud_skeleton(word)
            if unmapped:
                excluded.append({"word": word, "reason": f"unmapped {unmapped}"})
            else:
                loans.append({"word": word, "lb_lemma": lemma, "source": LB_SEMITIC_LOANS[lemma], "skeleton": skel,
                              "skeleton_len": length(word, skel), "kind": "lb_semitic_loan"})
            continue
        section = e.get("section") or ""
        if (e.get("agreement_status") != "concurs_dmic" or not section.startswith("Appendix I")
                or section.startswith("Appendix II") or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)+", lemma)):
            continue
        text = " ".join(str(e.get(k) or "") for k in ("vc1956_interpretation", "verbatim_quote"))
        if _LOAN_WORDING.search(text):
            excluded.append({"word": lemma.upper(), "reason": "loan or foreign wording in V&C"})
            continue
        word = lemma.upper()
        skel, unmapped = loud_skeleton(word)
        if unmapped:
            excluded.append({"word": word, "reason": f"unmapped {unmapped}"})
            continue
        n = length(word, skel)
        if n < INFORMATIVE_MIN:
            continue
        negatives.append({"word": word, "lb_lemma": lemma, "skeleton": skel, "skeleton_len": n,
                          "kind": "lb_greek"})
    rng = random.Random(SEED)
    if len(negatives) > LB_NEGATIVE_CAP:
        negatives = sorted(rng.sample(negatives, LB_NEGATIVE_CAP), key=lambda r: r["word"])
    return negatives, loans, excluded


def _primary_index_exclusions() -> dict[str, str]:
    """Numbers left out of the primary statistic (§6 A4): no Semitic-branch reflex (only non-Semitic comparanda
    or none), or numbered 2964–2998 (restored and added records)."""
    from ...core.root_index import record_keys
    out = {}
    for rec in roots_records(json.loads((SEMITIC_ROOTS_DATA / "semitic_roots.json").read_text(encoding="utf-8"))):
        n = str(rec["Number"])
        if n.isdigit() and 2964 <= int(n) <= 2998:
            out[n] = "campaign_addition"
        elif not any(k.kind == "reflex" and k.branch not in (None, "non_semitic") for k in record_keys(rec)):
            out[n] = "no_semitic_reflex"
    return out


def frozen_index_exclusions(path: Path = GOLD_V3_PATH) -> dict[str, str]:
    """A4's primary key set as A4 names it: the gold set's primary_index_exclusions (gold v3, equal to v2's, A13),
    read and never recomputed (A17). A file without a non-empty list raises ValueError."""
    data = json.loads(path.read_text(encoding="utf-8"))
    out = data.get("primary_index_exclusions") if isinstance(data, dict) else None
    if not isinstance(out, dict) or not out:
        raise ValueError(f"{path.name} has no primary_index_exclusions (A4's frozen list)")
    return {str(k): str(v) for k, v in out.items()}


def build_gold_v2(version: int = 2) -> None:
    """Gold v2, or v3: v2 with lexicon spellings rewritten in corpus signs (LEXICON_SIGN_ALIASES)."""
    path = {2: GOLD_V2_PATH, 3: GOLD_V3_PATH}[version]
    _refuse_existing(path)
    before = input_hashes()
    rng = random.Random(SEED)
    entries = json.loads((DATA_DIR / "lexicon.json").read_text(encoding="utf-8"))["entries"]
    resolved = campaign_signs()
    aliases = lexicon_sign_aliases() if version >= 3 else {}

    positives, negatives, excluded = [], [], []
    for e in entries:
        word, layer, tier = e.get("word", ""), str(e.get("language_layer") or ""), e.get("tier", 0)
        is_rejected = e.get("confidence") == "REJECTED"
        is_non_semitic = layer in NON_SEMITIC_LAYERS and tier >= 2
        is_positive = tier >= 3 and layer.startswith(SEMITIC_LAYER_PREFIXES)
        if not (is_rejected or is_non_semitic or is_positive):
            continue
        if not _syllabic(word):
            excluded.append({"word": word, "reason": "not a syllabic sign group"})
            continue
        lexicon_word, word = word, corpus_spelling(word) if aliases else word
        skel, unmapped = loud_skeleton(word)
        if unmapped:
            excluded.append({"word": word, "reason": f"unmapped sign {unmapped}"})
            continue
        if not skel:
            excluded.append({"word": word, "reason": "no Linear A skeleton"})
            continue
        n = len(_tokenize_phonemes(skel))
        row = {"word": word, "root": e.get("root"), "meaning": e.get("meaning", ""), "tier": tier,
               "language_layer": e.get("language_layer"), "skeleton": skel, "skeleton_len": n,
               "informative": n >= INFORMATIVE_MIN,
               "lb_values_only": not any(s in resolved for s in word.split("-"))}
        if lexicon_word != word:
            row["lexicon_word"] = lexicon_word
        if is_rejected:
            negatives.append({**row, "kind": "rejected"})
        elif is_non_semitic:
            negatives.append({**row, "kind": "non_semitic_layer"})
        else:
            unparsed: list[str] = []
            keys = parse_lexicon_root(e.get("root"), unparsed)
            if not keys:
                excluded.append({"word": word, "reason": f"root not parseable: {e.get('root')!r}"})
                continue
            positives.append({**row, "root_keys": ["-".join(k) for k in keys], "unparsed_alternatives": unparsed})

    corpus_words = load_corpus_words()
    tables = position_tables(corpus_words)
    real = set(corpus_words)
    controls, control_gaps = [], []
    seen_skeletons = {p["skeleton"] for p in positives}
    for p in positives:
        shuffled = shuffle_new_skeleton(rng, p["word"])
        if shuffled and extract_skeleton(shuffled) not in seen_skeletons:
            controls.append({"word": shuffled, "kind": "sign_shuffle", "source": p["word"]})
            seen_skeletons.add(extract_skeleton(shuffled))
        else:
            control_gaps.append({"source": p["word"], "kind": "sign_shuffle", "reason": "no new-skeleton order"})
        fab = fabricate(rng, len(p["word"].split("-")), p["skeleton_len"], tables, real)
        if fab and extract_skeleton(fab) not in seen_skeletons:
            controls.append({"word": fab, "kind": "fabricated", "source": p["word"]})
            seen_skeletons.add(extract_skeleton(fab))
        else:
            control_gaps.append({"source": p["word"], "kind": "fabricated", "reason": "no distinct match in 500 draws"})
    for c in controls:
        c["skeleton"] = extract_skeleton(c["word"])
        c["skeleton_len"] = len(_tokenize_phonemes(c["skeleton"]))
        c["informative"] = c["skeleton_len"] >= INFORMATIVE_MIN

    lb_negatives, lb_loans, lb_excluded = _lb_words()
    lb_shuffles = []
    for r in lb_negatives + lb_loans:
        s = shuffle_new_skeleton(rng, r["word"])
        if s:
            lb_shuffles.append({"word": s, "kind": "lb_shuffle", "source": r["word"], "skeleton": extract_skeleton(s),
                                "skeleton_len": _skel_len(s)})

    payload = {
        "description": (f"Shoresh gold set v{version} (ref §6 amendments A1-A4). Positives were found by the "
                        "pre-Shoresh matcher, so they measure recall only; false-positive rates come from the "
                        "controls and the Linear B negatives. Criteria 2-5 use informative rows only (>= 3 consonants)."
                        + (" Lexicon spellings of campaign values are rewritten in corpus signs (QI → *34); "
                           "`lexicon_word` keeps the lexicon's spelling." if aliases else "")),
        "counts": {"positives": len(positives), "positives_informative": sum(p["informative"] for p in positives),
                   "positives_lb_values_only": sum(p["lb_values_only"] for p in positives),
                   "negatives": len(negatives), "controls": len(controls), "control_gaps": len(control_gaps),
                   "lb_negatives": len(lb_negatives), "lb_loans": len(lb_loans), "lb_shuffles": len(lb_shuffles),
                   "excluded": len(excluded) + len(lb_excluded)},
        "rules": {"informative_min_consonants": INFORMATIVE_MIN, "campaign_resolved_signs": sorted(resolved),
                  "lb_negative_cap": LB_NEGATIVE_CAP, "lb_semitic_loans": LB_SEMITIC_LOANS}
                 | ({"lexicon_sign_aliases": aliases} if aliases else {}),
        "positives": positives, "negatives": negatives, "controls": controls, "control_gaps": control_gaps,
        "lb_negatives": lb_negatives, "lb_loans": lb_loans, "lb_shuffles": lb_shuffles,
        "excluded": excluded + lb_excluded,
        "primary_index_exclusions": _primary_index_exclusions(),
    }
    write_fixture(path, payload, before)
    print(json.dumps(payload["counts"]))


# ---------------------------------------------------------------------------
# gold v4 (§6 A22)
# ---------------------------------------------------------------------------

# Inputs gold v4 reads beyond tracked_inputs(): v3's roots file (B6), gold v3 (A4, G1), the archive (R1), the
# exposure ledger (B7), the semantic gate with its frozen tagger (contexts, anchors), the campaign-value reader
# (lb_values_only, so the strata) and this builder.
V4_INPUTS = (ROOTS_V3_PATH, GOLD_V3_PATH, DATA_DIR / "lexicon_archive.json", EXPOSURE_V4_PATH,
             REPO / "tools" / "core" / "semantic_gate.py", REPO / "tools" / "core" / "frozen" / "tag_semantic_fields.py",
             REPO / "tools" / "core" / "data_cache.py", Path(__file__).resolve())
# The two inputs A22 names by content: gold v3's roots file and the exposure ledger (exposure-v4b.json).
V4_PINNED_SHA256 = {ROOTS_V3_PATH: "42167a4ee41e63985a8b530e78d4f18e3739429170ddbeec70082976bc06fc6e",
                    EXPOSURE_V4_PATH: "27e4c2fe6b4d0a5201df48e89187f3fec771af6ffbfa1e7d033cd427a0008794"}
V4_NON_SEMITIC_FAMILIES = frozenset({"Hurro-Urartian", "Egyptian", "Indo-European"})
V4_CONVENTIONAL_KEEP = frozenset({"AU", "PA3", "JU", "ZU"})     # A20: read by Linear B values
V4_REMOVED = {"SE-TO-I-JA": "removed", "KU-MI-NA": "removed",
              "TU-*21F-RI-NA": "removed from both strata (rests on *21F, 'proposed (fails)')"}
V4_LB_LOAN_WORDS = {"KU-MI-NA": "ku-mi-no, kamūnu 'cumin'", "SA-SA-ME": "sa-sa-ma, šamaššammū 'sesame'"}
V4_VESSEL_PREFIX = re.compile(r"^\]?\*4\d\d[A-Z]?-VS-(.+)$")    # HT 31's vessel ideograms written before the word
# S2: a note that names an unresolved sign-value doubt, matched case-insensitively.
V4_DOUBT = re.compile(
    r"sign[- ]values?\b|value of (the )?(sign|\*\d)|\bsign\b[^.;]{0,40}\b(uncertain|unclear|disputed|doubtful|"
    r"ambiguous|unread|unresolved)|\b(uncertain|unclear|disputed|doubtful|ambiguous|unresolved)\b[^.;]{0,25}"
    r"\b(sign|reading of)\b|\bif\s+\*?[A-Z][A-Z0-9₂₃*]*\s+(is|reads|=)|\*\d{2,3}\b[^.;]{0,30}\b(or|reads?|=)\b"
    r"|written over|\berased\b|damage (crosses|runs through|to the)|\bdoubtful\b"
    r"|(?-i:\breads? [A-Z*][A-Z0-9₂₃*]* for [A-Z*])|(?-i:GORILA reads)",
    re.IGNORECASE)
V4_ONE_READING_FAIL = re.compile(r"\bOR\b|[Dd]ual reading|two competing|TWO COMPETING")     # S4
V4_COMPOUND = re.compile(r"\bcompound\b|sentence name", re.IGNORECASE)                      # S5
V4_CONTEXT_PAREN = re.compile(r"\([^)]*\b(heading|header|entry|list|roster|before|after|under)\b[^)]*\)",
                              re.IGNORECASE)
V4_STRENGTH = {
    "S1": "the root record has reflexes in >= 3 Semitic branches (root_index.record_keys)",
    "S2": "the lexicon note matches no sign-value or sign-reading doubt pattern (V4_DOUBT)",
    "S3": "at least one anchor A1-A4 (domains from the gloss alone; A3 by outside_scholar or Gordon named first in "
          "source), or >= 2 intact standalone attestations",
    "S4": "the gloss offers one reading: no upper-case OR, 'Dual reading' or 'two competing' in the meaning",
    "S5": "the gloss names one root: the meaning does not call the word a compound or a sentence name",
    "strong": "S1 and S2 and S3 and S4 and S5",
    "rank": "strong, then anchored, then intact attestations, then branches, then the word",
}


def _norm_sign(sign: str) -> str:
    return sign.upper().translate(_SUBSCRIPT_MAP)


def _v4_gloss(meaning: str | None) -> str:
    """The reading's own gloss, as A22 reads anchors: the meaning up to its first ';', without the parentheses that
    describe the word's place on the document ('heading of a grain list')."""
    return V4_CONTEXT_PAREN.sub("", (meaning or "").split(";")[0])


def _v4_ps_ids(entry: dict) -> list[str]:
    ps = entry.get("proto_semitic")
    ps = [ps] if isinstance(ps, dict) else ps
    return [str(p.get("id")) for p in (ps or []) if isinstance(p, dict) and p.get("id")]


def _v4_contexts(corpus: dict) -> tuple[dict, dict]:
    """(sign-group key → attestations, sign-group key → [(doc, vessel ideogram)]), read as the semantic gate reads
    a word's contexts: a fused logogram, else the next token after layout, else the document's support (A18, A19)."""
    from ...core import semantic_gate as sg
    att: dict[tuple, dict] = {}
    vessels: dict[tuple, list] = {}
    for doc_id, doc in corpus.items():
        support = sg.SUPPORT_DOMAINS.get(doc.get("support", "") or "")
        site = doc.get("site") or (re.match(r"[A-Z]+", doc_id) or [doc_id])[0]
        toks = [t for t in doc.get("transliteratedWords", []) if isinstance(t, str)]
        for i, t in enumerate(toks):
            m = V4_VESSEL_PREFIX.match(t)
            if m and ("-" in m.group(1) or _lookup_sign(m.group(1))):
                vessels.setdefault(sg._key(m.group(1)), []).append((doc_id, t.split("-VS-")[0].lstrip("]")))
            if "-" not in t:
                continue
            word, logo = sg._fused(t)
            logo_name = t.rpartition("-")[2] if logo is not None else None
            if logo is None:
                j = i + 1
                while j < len(toks) and toks[j] in sg.LAYOUT:
                    j += 1
                nxt = toks[j] if j < len(toks) else None
                logo = sg.logogram_domains(nxt, toks[j + 1] if j + 1 < len(toks) else None)
                logo_name = sg._base(nxt) if logo is not None else None
            if "-" not in word:
                continue
            rec = att.setdefault(sg._key(word), {"docs": [], "sites": set(), "logograms": Counter(),
                                                 "logogram_domains": set(), "support_domains": set()})
            rec["docs"].append(doc_id)
            rec["sites"].add(site)
            if logo is not None:
                rec["logograms"][logo_name] += 1
                rec["logogram_domains"] |= set(logo)
            elif support is not None:
                rec["support_domains"] |= set(support)
    return att, vessels


def _v4_census(entries: list[dict]) -> dict[str, Any]:
    """Per lexicon entry and archive row, the facts A22's rules read: skeleton, attestations, contexts, root
    records (live and in v3's roots file), exposure and v3 section. Reads no engine number."""
    from ...core import semantic_gate as sg
    from ...core.root_index import record_keys
    from ...core.skeleton import SIGN_STATUS

    def ps_keys(rec: dict) -> set[tuple]:
        return {k.radicals for k in record_keys(rec) if k.kind == "ps"}

    def branches(rec: dict) -> set[str]:
        return {k.branch for k in record_keys(rec) if k.kind == "reflex" and k.branch not in (None, "non_semitic")}

    roots = {str(r["Number"]): r for r in
             roots_records(json.loads((SEMITIC_ROOTS_DATA / "semitic_roots.json").read_text(encoding="utf-8")))}
    roots_v3 = {str(r["Number"]): r for r in roots_records(json.loads(ROOTS_V3_PATH.read_text(encoding="utf-8")))}
    gold3 = json.loads(GOLD_V3_PATH.read_text(encoding="utf-8"))
    a4 = set(frozen_index_exclusions(GOLD_V3_PATH))
    ledger = json.loads(EXPOSURE_V4_PATH.read_text(encoding="utf-8"))["words"]
    grades: dict[tuple, set] = {}
    for w, v in ledger.items():
        grades.setdefault(sg._key(w), set()).add(v["grade"])
    classify = sg.tagger().classify
    camp = {_norm_sign(s) for s in campaign_signs()}
    aliases = lexicon_sign_aliases()
    att, vessels = _v4_contexts(json.loads((DATA_DIR / "corpus.json").read_text(encoding="utf-8")))
    v3_ps: dict[tuple, set] = {}
    for n, r in roots_v3.items():
        for k in ps_keys(r):
            v3_ps.setdefault(k, set()).add(n)
    v3_where: dict[tuple, str] = {}
    for sec, rows in gold3.items():
        for r in rows if isinstance(rows, list) else ():
            for f in ("word", "lexicon_word") if isinstance(r, dict) else ():
                if r.get(f):
                    v3_where.setdefault(sg._key(r[f]), sec)

    def exposure(*spellings: str) -> str | None:
        """The ledger's grade for a word under any of its spellings (corpus and lexicon)."""
        g = set().union(*(grades.get(sg._key(w), set()) for w in spellings))
        return "E1" if "E1" in g else ("E2" if g else None)

    spell = corpus_spelling

    def facts(word: str) -> dict:
        cons, unmapped = _sign_consonants(word)
        signs = [_norm_sign(s) for s in word.split("-")]
        a = att.get(sg._key(word))
        return {"skeleton": "".join(cons), "consonants": len(cons), "unmapped": unmapped,
                "lb_values_only": not any(s in camp for s in signs),
                "conventional_unmapped": sorted({s for s in signs if s in SIGN_STATUS and s not in V4_CONVENTIONAL_KEEP}),
                "corpus_attestations": len(a["docs"]) if a else 0, "sites": sorted(a["sites"]) if a else [],
                "logograms": dict(a["logograms"]) if a else {},
                "logogram_domains": sorted(a["logogram_domains"]) if a else [],
                "support_domains": sorted(a["support_domains"]) if a else [],
                "vessel_prefixed": vessels.get(sg._key(word), [])}

    rows = []
    for e in entries:
        cw = spell(e["word"])
        row = {"word": cw, "tier": e.get("tier"), "confidence": e.get("confidence"),
               "language_family": e.get("language_family"), "language_layer": e.get("language_layer"),
               "meaning": e.get("meaning", ""), "root": e.get("root"), "proto_semitic_ids": _v4_ps_ids(e),
               "outside_scholar": e.get("outside_scholar"), "source": e.get("source"), "note": e.get("note") or "",
               "syllabic": _syllabic(cw)}
        if cw != e["word"]:
            row["lexicon_word"] = e["word"]
        if row["syllabic"]:
            row.update(facts(cw))
        row["meaning_domains"] = sorted(classify(row["meaning"] or ""))
        row["root_records"] = [{
            "number": n, "live": n in roots, "headword": roots[n].get("Proto-Semitic") if n in roots else None,
            "in_v3_file": n in roots_v3, "a4_excluded": n in a4,
            "ps_keys": sorted("-".join(k) for k in ps_keys(roots[n])) if n in roots else [],
            "v3_records_with_same_ps_key": sorted({m for k in (ps_keys(roots[n]) if n in roots else ())
                                                   for m in v3_ps.get(k, ())}),
            "semitic_branches": sorted(branches(roots[n])) if n in roots else []} for n in row["proto_semitic_ids"]]
        row["exposure"] = exposure(cw, e["word"])
        row["v3_section"] = v3_where.get(sg._key(cw)) or (v3_where.get(sg._key(e["word"])) if row["syllabic"] else None)
        rows.append(row)

    archive = json.loads((DATA_DIR / "lexicon_archive.json").read_text(encoding="utf-8"))
    arch_rows = []
    for e in archive["entries"] if isinstance(archive, dict) else archive:
        w = spell(e.get("word", ""))
        r = {"word": w, "confidence": e.get("confidence"), "tier": e.get("tier"), "meaning": e.get("meaning", ""),
             "language_layer": e.get("language_layer"), "syllabic": _syllabic(w)}
        if r["syllabic"]:
            r.update(facts(w), exposure=exposure(w, e.get("word", "")), v3_section=v3_where.get(sg._key(w)))
        arch_rows.append(r)
    live_ps: dict[str, set[str]] = {}
    for n, rec in roots.items():
        for k in ps_keys(rec):
            live_ps.setdefault("-".join(k), set()).add(n)
    return {"lexicon": rows, "archive": arch_rows, "live_ps": live_ps, "gold3": gold3,
            "campaign_signs": sorted(camp), "aliases": aliases}


def _spellings(row: dict) -> dict[str, str]:
    """A row's word and, when the lexicon spells it otherwise, its lexicon_word: both stay under the guard (A14)."""
    return {k: row[k] for k in ("word", "lexicon_word") if row.get(k)}


def _v4_anchors(r: dict, md: set[str]) -> list[str]:
    """Independence strata, never admission (D6): md is the gloss's domains (_v4_gloss, never the whole meaning);
    A3 needs `outside_scholar` or a source that names Gordon first (the reading's originator, not a rival)."""
    out = []
    if r.get("vessel_prefixed") and "pottery_vessel" in md:
        out.append("A1_vessel_ideogram")
    if set(r.get("logogram_domains") or []) & md:
        out.append("A1_logogram")
    if r["word"] in V4_LB_LOAN_WORDS:
        out.append("A2_linear_b_loan")
    if r.get("outside_scholar") or str(r.get("source") or "").startswith("Gordon"):
        out.append("A3_outside_scholar")
    if set(r.get("support_domains") or []) & md:
        out.append("A4_document_type")
    return out or ["A0_reading_only"]


def _v4_strength(r: dict, rec: dict, anchors: list[str]) -> dict:
    attested = r["corpus_attestations"] + len(r.get("vessel_prefixed") or [])
    anc = [a for a in anchors if a != "A0_reading_only"]
    m = V4_DOUBT.search(r["note"])
    s = {"branches": len(rec["semitic_branches"]), "intact_attestations": attested, "anchors": anc,
         "note_sign_value_doubt": m.group(0) if m else None,
         "S1_branches_ge3": len(rec["semitic_branches"]) >= 3, "S2_note_clean": m is None,
         "S3_anchor_or_att_ge2": bool(anc) or attested >= 2,
         "S4_one_reading": not V4_ONE_READING_FAIL.search(r["meaning"] or ""),
         "S5_one_root": not V4_COMPOUND.search(r["meaning"] or "")}
    s["strong"] = all(s[k] for k in ("S1_branches_ge3", "S2_note_clean", "S3_anchor_or_att_ge2", "S4_one_reading",
                                     "S5_one_root"))
    s["score"] = [int(s["strong"]), int(bool(anc)), attested, s["branches"]]
    return s


def _v4_select(entries: list[dict]) -> dict[str, Any]:
    """A22's selection on a lexicon: the primary and secondary positives, the negatives (N1, N2, R1) and every
    exclusion with its rule. No controls and no engine call; build_gold_v4 adds the controls."""
    from ...core import semantic_gate as sg
    c = _v4_census(entries)
    excluded, negatives, prim_pool, sec_pool, t12_pool = [], [], [], [], []

    def common_gate(r: dict) -> str | None:
        """B3, B4, B5, B7 as the negatives share them: the first failure, or None."""
        if not r["syllabic"]:
            return "B3 not a syllabic sign group"
        if r["unmapped"]:
            return f"B3 unmapped sign {r['unmapped']}"
        if r["corpus_attestations"] == 0 and not r["vessel_prefixed"]:
            return "B4 no intact standalone attestation in corpus.json"
        if r["consonants"] < INFORMATIVE_MIN:
            return f"B5 {r['consonants']} consonant(s)"
        if r["exposure"] == "E1":
            return "B7 an engine p or verdict is on record (exposure E1)"
        return None

    for r in c["lexicon"]:
        tier, fam = r["tier"] or 0, r.get("language_family")
        base = {"word": r["word"], **({"lexicon_word": r["lexicon_word"]} if r.get("lexicon_word") else {}),
                "tier": tier, "meaning": r["meaning"], "root": r["root"], "v3_section": r.get("v3_section"),
                "exposure": r.get("exposure")}
        if fam in V4_NON_SEMITIC_FAMILIES and tier >= 2:            # N1, N2
            base = {**base, "language_family": fam, "language_layer": r["language_layer"]}
            why = common_gate(r) or ("N2 the entry names a Semitic root record" if r["proto_semitic_ids"] else None)
            if why:
                excluded.append({**base, "section": "negatives", "reason": why})
            else:
                negatives.append({**base, "kind": "non_semitic_layer", "skeleton": r["skeleton"],
                                  "skeleton_len": r["consonants"], "informative": True,
                                  "lb_values_only": r["lb_values_only"],
                                  "conventional_unmapped": r["conventional_unmapped"],
                                  "corpus_attestations": r["corpus_attestations"], "sites": r["sites"],
                                  "rule": "N1 (tier >= 2, non-Semitic family) + B3-B5, B7; N2"})
            continue
        if fam != "Semitic" or tier < 1:
            continue
        nsigns = len(r["word"].split("-")) if r["syllabic"] else 0
        hi = tier >= 3
        base = {**base, "signs": nsigns, **({} if hi else {"pool": "tier1-2"})}
        if r["word"] in V4_REMOVED:                             # held under the guard whatever its tier now
            excluded.append({**base, "section": "positives", "reason": V4_REMOVED[r["word"]] + "; kept under the guard"})
            continue
        if not hi and not 4 <= nsigns <= 5:
            continue                                            # B1b admits tier 1-2 only at 4-5 signs
        rec = r["root_records"][0] if len(r["proto_semitic_ids"]) == 1 else None
        # The first failure, in PROPOSAL §2.1's order (B1b and R3 once the signs are known to map)
        if not r["syllabic"]:
            why = "B3 not a syllabic sign group"
        elif r["unmapped"]:
            why = f"B3 unmapped sign {r['unmapped']}"
        elif nsigns <= 2:
            why = "R3 two-sign word"
        elif not hi and (not r["lb_values_only"] or r["conventional_unmapped"]):
            why = "B1b a sign read beyond Linear B"
        elif r["corpus_attestations"] == 0 and not r["vessel_prefixed"]:
            why = "B4 no intact standalone attestation in corpus.json"
        elif r["consonants"] < INFORMATIVE_MIN:
            why = f"B5 {r['consonants']} consonant(s)"
        elif rec is None:
            why = ("B6 no single root record named" if not r["proto_semitic_ids"]
                   else f"B6 compound root: {len(r['proto_semitic_ids'])} records named")
        elif not rec["live"]:
            why = f"B6 record {rec['number']} not in the live semitic_roots.json"
        elif rec["a4_excluded"]:
            why = f"B6 record {rec['number']} is in A4's frozen primary_index_exclusions"
        elif len(rec["semitic_branches"]) < 2:
            why = f"B6 record {rec['number']} has reflexes in {len(rec['semitic_branches'])} Semitic branch(es)"
        elif not hi and not (rec["in_v3_file"] or rec["v3_records_with_same_ps_key"]):
            why = f"B6 record {rec['number']} postdates gold v3's roots file and no record there shares its PS key"
        elif r["exposure"] == "E1":
            why = "B7 an engine p or verdict is on record (exposure E1)"
        else:
            why = None
        if why:
            excluded.append({**base, "section": "positives", "reason": why})
            continue
        new_root = not (rec["in_v3_file"] or rec["v3_records_with_same_ps_key"])
        gloss_domains = set(sg.tagger().classify(_v4_gloss(r["meaning"])))
        anchors = _v4_anchors(r, gloss_domains)
        row = {**{k: v for k, v in base.items() if k != "pool"}, "root_number": rec["number"],
               "root_headword": rec["headword"], "root_keys": rec["ps_keys"],
               "target_numbers": sorted({m for k in rec["ps_keys"] for m in c["live_ps"].get(k, ())} | {rec["number"]}),
               "language_layer": r["language_layer"], "skeleton": r["skeleton"], "skeleton_len": r["consonants"],
               "informative": True, "lb_values_only": r["lb_values_only"],
               "conventional_unmapped": r["conventional_unmapped"],
               "intact_attestations": r["corpus_attestations"] + len(r["vessel_prefixed"]),
               "vessel_prefixed": r["vessel_prefixed"], "sites": r["sites"], "context_logograms": r["logograms"],
               "context_support_domains": r["support_domains"], "meaning_domains": r["meaning_domains"],
               "semitic_branches": rec["semitic_branches"],
               "gloss_domains": sorted(gloss_domains), "anchors": anchors}
        if hi and r["lb_values_only"] and not new_root:
            prim_pool.append({**row, "rule": "B1, B3-B7 (Linear B values; root at v3)"})
        elif hi:
            sec_pool.append({**row, "rule": "B1, B3-B7; secondary: " + ", ".join(
                x for x in ("values beyond Linear B" if not r["lb_values_only"] else None,
                            "root record postdates v3's roots file" if new_root else None) if x)})
        else:
            t12_pool.append({**row, "strength": _v4_strength(r, rec, anchors),
                             "rule": "B1b (tier 1-2, 4-5 signs, Linear B values), B3-B7"})

    def b8(rows: list[dict], stratum: str) -> list[dict]:
        """One sign group per root record within a stratum: tier >= 3 first, then the most intact attestations,
        then the most consonants, then the word."""
        by: dict[str, list[dict]] = {}
        for x in rows:
            by.setdefault(x["root_number"], []).append(x)
        kept = []
        for n, g in sorted(by.items()):
            g.sort(key=lambda x: (x["tier"] < 3, -x["intact_attestations"], -x["skeleton_len"], x["word"]))
            kept.append(g[0])
            excluded.extend({**_spellings(x), "tier": x["tier"], "signs": x["signs"], "root": x["root"],
                             "section": "positives",
                             "reason": f"B8 {stratum}: same root record {n} as {g[0]['word']}"} for x in g[1:])
        return kept

    primary, secondary = b8(prim_pool, "primary"), b8(sec_pool, "secondary")
    hi_targets: dict[str, str] = {}             # B8 binds within a stratum: a B1b word competes with the primary only
    for x in primary:
        for n in x["target_numbers"]:
            hi_targets.setdefault(n, x["word"])
    t12_pool.sort(key=lambda x: tuple(-v for v in x["strength"]["score"]) + (x["word"],))
    first_of_root: dict[str, str] = {}
    for x in t12_pool:
        collides = sorted({hi_targets[n] for n in x["target_numbers"] if n in hi_targets})
        loser = first_of_root.setdefault(x["root_number"], x["word"]) != x["word"]
        if x["strength"]["strong"] and not collides and not loser:
            primary.append({**x, "rule": "B1b + strong (S1-S5), B3-B8"})
            continue
        failed = [k.split("_")[0] for k in ("S1_branches_ge3", "S2_note_clean", "S3_anchor_or_att_ge2",
                                            "S4_one_reading", "S5_one_root") if not x["strength"][k]]
        reason = (f"B1b not strong: fails {', '.join(failed)}" if failed
                  else f"B1b collides with tier >= 3 positive {', '.join(collides)}" if collides
                  else f"B8 tier 1-2 pool: same root record {x['root_number']} as {first_of_root[x['root_number']]}")
        excluded.append({**_spellings(x), "tier": x["tier"], "signs": x["signs"], "root": x["root"],
                         "section": "positives", "pool": "tier1-2", "strength": x["strength"],
                         **({"collides_with": collides} if collides else {}), "reason": reason})
    for stratum, rows in (("primary", primary), ("secondary", secondary)):
        for x in rows:
            x["stratum"] = stratum
    primary.sort(key=lambda x: x["word"])
    secondary.sort(key=lambda x: x["word"])

    for a in c["archive"]:                                  # R1: REJECTED rows, descriptive only (A5)
        if a.get("confidence") != "REJECTED" or not a["syllabic"]:
            continue
        base = {"word": a["word"], "meaning": a["meaning"], "tier": a.get("tier"),
                "language_layer": a.get("language_layer"), "v3_section": a.get("v3_section"),
                "exposure": a.get("exposure")}
        why = (f"B3 unmapped sign {a['unmapped']}" if a["unmapped"]
               else "R1 not an intact corpus word (ghost or segment)" if a["corpus_attestations"] == 0
               else f"B5 {a['consonants']} consonant(s)" if a["consonants"] < INFORMATIVE_MIN
               else "B7 engine p or verdict on record" if a.get("exposure") == "E1" else None)
        if why:
            excluded.append({**base, "section": "negatives", "reason": why})
        else:
            negatives.append({**base, "kind": "rejected", "skeleton": a["skeleton"], "skeleton_len": a["consonants"],
                              "informative": True, "corpus_attestations": a["corpus_attestations"],
                              "rule": "R1 (archive REJECTED, intact corpus word) + B3, B5, B7; descriptive only (A5)"})
    return {"primary": primary, "secondary": secondary, "negatives": negatives, "excluded": excluded,
            "gold3": c["gold3"], "campaign_signs": c["campaign_signs"], "aliases": c["aliases"]}


def build_gold_v4() -> None:
    """Gold v4 under A22: primary and secondary positives in `positives` (each row's `stratum`), seeded controls
    by the registered generators on one-letter tokens (A16), the A2 Linear B rows, A4's frozen exclusions from
    gold v3, and every v3 row v4 does not hold kept under the guard (G1)."""
    _refuse_existing(GOLD_V4_PATH)
    missing = [_rel(p) for p in V4_INPUTS if not p.exists()]
    if missing:
        sys.exit(f"gold v4 inputs missing: {missing}")
    before = input_hashes(V4_INPUTS)
    wrong = [_rel(p) for p, sha in V4_PINNED_SHA256.items() if before[_rel(p)] != sha]
    if wrong:
        sys.exit(f"not the file A22 names: {wrong}")
    rng = random.Random(SEED)
    sel = _v4_select(json.loads((DATA_DIR / "lexicon.json").read_text(encoding="utf-8"))["entries"])
    positives = sel["primary"] + sel["secondary"]
    excluded = sel["excluded"]

    def letters(word: str) -> list[str]:
        return _sign_consonants(word)[0]

    lb_negatives, lb_loans, lb_excluded = _lb_words(one_letter=True)
    corpus_words = load_corpus_words()
    tables, real = position_tables(corpus_words), set(corpus_words)
    # A5, C1: no control repeats a skeleton anywhere in the set, and none is a corpus word
    seen = {r["skeleton"] for r in positives + sel["negatives"] + lb_negatives + lb_loans}
    controls, control_gaps = [], []
    for p in positives:
        s = shuffle_new_skeleton(rng, p["word"])
        sk = "".join(letters(s)) if s else None
        if s and sk not in seen and s not in real:
            controls.append({"word": s, "kind": "sign_shuffle", "source": p["word"], "skeleton": sk,
                             "skeleton_len": len(letters(s)), "informative": len(letters(s)) >= INFORMATIVE_MIN})
            seen.add(sk)
        else:
            control_gaps.append({"source": p["word"], "kind": "sign_shuffle", "reason": "no new-skeleton order"})
        pc = letters(p["word"])
        f = fabricate(rng, len(p["word"].split("-")), len(pc), tables, real, tokens=letters,
                      ocp=all(a != b for a, b in pairwise(pc)))
        fk = "".join(letters(f)) if f else None
        if f and fk not in seen:
            controls.append({"word": f, "kind": "fabricated", "source": p["word"], "skeleton": fk,
                             "skeleton_len": len(letters(f)), "informative": True})
            seen.add(fk)
        else:
            control_gaps.append({"source": p["word"], "kind": "fabricated", "reason": "no distinct match in 500 draws"})

    lb_shuffles = []
    for r in lb_negatives + lb_loans:
        s = shuffle_new_skeleton(rng, r["word"])
        if s:
            lb_shuffles.append({"word": s, "kind": "lb_shuffle", "source": r["word"], "skeleton": "".join(letters(s)),
                                "skeleton_len": len(letters(s))})
    excluded += [{**x, "section": "lb"} for x in lb_excluded]

    # G1: every sign group of gold v3, in every section and either spelling, that v4 does not hold
    held = {sign_group_key(w) for sec in (positives, sel["negatives"], controls, lb_negatives, lb_loans, lb_shuffles,
                                          excluded) for r in sec for w in _spellings(r).values()}
    for sec in GOLD_SECTIONS:
        for r in sel["gold3"][sec]:
            if any(sign_group_key(w) not in held for w in _spellings(r).values()):
                excluded.append({**_spellings(r), "section": "guard_only", "v3_section": sec,
                                 "reason": "G1 gold v3 row that v4 does not hold: kept under the guard until the gold run"})
                held |= {sign_group_key(w) for w in _spellings(r).values()}

    from ...core import semantic_gate as sg
    sizes = Counter(p["signs"] for p in sel["primary"])
    payload = {
        "description": ("Shoresh gold set v4 (ref §6 A22). `positives` holds both strata, each row's `stratum`: "
                        "primary = tier >= 3 readings on Linear B values whose root record is in v3's roots file, "
                        "plus strong tier 1-2 words of 4-5 signs (B1b); secondary = values beyond Linear B or a root "
                        "record after v3, reported without a pass mark. One sign group per root record within a "
                        "stratum (B8); no two-sign word. REJECTED rows are descriptive only (R1). Every v3 row v4 "
                        "does not hold stays under the guard (G1)."),
        "counts": {"positives": len(positives), "primary": len(sel["primary"]),
                   "primary_by_signs": {str(k): v for k, v in sorted(sizes.items())},
                   "primary_tier1_2_added": sum(1 for p in sel["primary"] if p["tier"] < 3),
                   "secondary": len(sel["secondary"]), "negatives": len(sel["negatives"]),
                   "negatives_by_kind": dict(Counter(n["kind"] for n in sel["negatives"])),
                   "controls": len(controls), "control_gaps": len(control_gaps), "lb_negatives": len(lb_negatives),
                   "lb_loans": len(lb_loans), "lb_shuffles": len(lb_shuffles), "excluded": len(excluded)},
        "rules": {"amendment": "A22", "informative_min_consonants": INFORMATIVE_MIN,
                  "tokens": "one consonant per sign (A16)", "campaign_resolved_signs": sel["campaign_signs"],
                  "conventional_keep": sorted(V4_CONVENTIONAL_KEEP), "removed": V4_REMOVED,
                  "lb_negative_cap": LB_NEGATIVE_CAP, "lb_semitic_loans": LB_SEMITIC_LOANS,
                  "lexicon_sign_aliases": sel["aliases"], "strength_definition": V4_STRENGTH,
                  "doubt_pattern": V4_DOUBT.pattern, "tagger_sha256": sg.TAGGER_SHA256},
        "positives": positives, "negatives": sel["negatives"], "controls": controls, "control_gaps": control_gaps,
        "lb_negatives": lb_negatives, "lb_loans": lb_loans, "lb_shuffles": lb_shuffles, "excluded": excluded,
        "primary_index_exclusions": frozen_index_exclusions(GOLD_V3_PATH),
    }
    write_fixture(GOLD_V4_PATH, payload, before, V4_INPUTS)
    print(json.dumps(payload["counts"], ensure_ascii=False))


# ---------------------------------------------------------------------------
# golden
# ---------------------------------------------------------------------------

def golden_words() -> list[str]:
    words = [w for w in load_corpus_words() if extract_skeleton(w)]
    rng = random.Random(SEED)
    pinned = [w for w in PINNED_WORDS if w in words]
    missing = sorted(set(PINNED_WORDS) - set(pinned))
    if missing:
        print(f"warning: pinned words not in the corpus: {missing}", file=sys.stderr)
    pool = [w for w in words if w not in pinned]
    if len(pool) < GOLDEN_SIZE - len(pinned):
        raise ValueError(f"corpus has {len(pool)} unpinned words with a skeleton; {GOLDEN_SIZE - len(pinned)} needed")
    return sorted(pinned + rng.sample(pool, GOLDEN_SIZE - len(pinned)))


def build_golden() -> None:
    _refuse_existing(GOLDEN_PATH)
    before = input_hashes()
    words = golden_words()
    records: dict[str, dict[str, Any]] = {name: {} for name in GOLDEN_CONFIGS}
    t0 = time.perf_counter()
    for i, word in enumerate(words, start=1):
        for name, flags in GOLDEN_CONFIGS.items():
            records[name][word] = search_cognates(word, top_n=5, use_cache=False, **flags)
        if i % 10 == 0:
            print(f"  {i}/{len(words)} words, {time.perf_counter() - t0:.0f}s", flush=True)
    payload = {
        "description": ("search_cognates(top_n=5, use_cache=False) output before the Shoresh "
                        "shim. Phase 3 acceptance: identical output for every word and config."),
        "configs": {k: sorted(v) for k, v in GOLDEN_CONFIGS.items()},
        "words": words,
        "results": records,
    }
    write_fixture(GOLDEN_PATH, payload, before)


# ---------------------------------------------------------------------------
# baseline
# ---------------------------------------------------------------------------

def _auc(pos: list[float], neg: list[float]) -> float:
    """P(score_pos < score_neg), ties count half (lower distance = stronger)."""
    if not pos or not neg:
        raise ValueError(f"AUC needs both classes (positives {len(pos)}, negatives {len(neg)})")
    wins = sum((p < n) + 0.5 * (p == n) for p in pos for n in neg)
    return wins / (len(pos) * len(neg))


def _bootstrap(stat: Callable[[list, list], float], a: list, b: list, n: int = 2000, seed: int = SEED
               ) -> dict[str, float]:
    """Point estimate and percentile 95% interval, resampling each class with replacement (seeded)."""
    rng = random.Random(seed)
    draws = sorted(stat(rng.choices(a, k=len(a)), rng.choices(b, k=len(b))) for _ in range(n))
    return {"estimate": round(stat(a, b), 3), "ci95": [round(draws[int(0.025 * n)], 3),
                                                       round(draws[int(0.975 * n) - 1], 3)]}


def _best_ps_distance(word: str) -> float:
    res = search_cognates(word, top_n=1, use_cache=False)
    ds = [m["distance"] for m in res["matches"] if m["method"] == "proto_semitic"]
    return min(ds) if ds else float("inf")


def _cli_latency(words: list[str]) -> dict[str, Any]:
    """Wall time and peak RSS of the real CLI path (cold process per call). A failed call, or a platform whose
    /usr/bin/time prints no RSS, stops the run: a crash must never be timed as a fast query."""
    walls, rss = [], []
    for w in words:
        cmd = ["/usr/bin/time", "-l", "uv", "run", "tools/linear_a/cognate_search.py", w,
               "--no-cache", "--top", "5", *CLI_FLAGS]
        t0 = time.perf_counter()
        out = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, check=False)
        walls.append(time.perf_counter() - t0)
        if out.returncode != 0:
            sys.exit(f"cognate_search.py {w} exited {out.returncode}: {out.stderr[-500:]}")
        m = re.search(r"(\d+)\s+maximum resident set size", out.stderr)
        if not m:
            sys.exit("no peak RSS in /usr/bin/time -l output (macOS BSD time required)")
        rss.append(int(m.group(1)))
    walls.sort()
    return {
        "words": words,
        "wall_s_p50": round(statistics.median(walls), 3),
        "wall_s_p95": round(walls[max(0, int(0.95 * len(walls)) - 1)], 3),
        "wall_s_max": round(walls[-1], 3),
        "peak_rss_mb_max": round(max(rss) / 2**20, 1),
        "flags": ["--no-cache", "--top", "5", *CLI_FLAGS],
    }


def build_baseline(latency_words: int) -> None:
    _refuse_existing(BASELINE_PATH)
    before = input_hashes()
    gold = _read_gold(GOLD_PATH, before)

    # Root recovery on positives (PS layer, deep list for ranks).
    per_word, ranks_exact, ranks_folded = [], [], []
    for p in gold["positives"]:
        res = search_cognates(p["word"], top_n=20, use_cache=False)
        ps = [m for m in res["matches"] if m["method"] == "proto_semitic"]
        keys = [tuple(k.split("-")) for k in p["root_keys"]]
        exact, folded = recovery_rank(keys, ps)
        ranks_exact.append(exact)
        ranks_folded.append(folded)
        per_word.append({"word": p["word"], "root_keys": p["root_keys"],
                         "skeleton_len": p["skeleton_len"],
                         "rank_exact": exact, "rank_folded": folded,
                         "best_distance": ps[0]["distance"] if ps else None,
                         "n_ps_matches": len(ps)})

    def recovery(ranks: list[int | None]) -> dict[str, float]:
        n = len(ranks)
        return {f"hit@{k}": round(sum(1 for r in ranks if r and r <= k) / n, 3) for k in (1, 5, 20)} | {
            "mrr": round(sum(1 / r for r in ranks if r) / n, 3)}

    # Discrimination: best PS distance, positives vs each comparison class.
    pos_d = [_best_ps_distance(p["word"]) for p in gold["positives"]]
    classes: dict[str, list[float]] = {}
    for row in gold["negatives"] + gold["controls"]:
        classes.setdefault(row["kind"], []).append(_best_ps_distance(row["word"]))
    discrimination = {}
    for kind, ds in sorted(classes.items()):
        finite = [d for d in ds if d != float("inf")]
        discrimination[kind] = {
            "n": len(ds),
            "auc_vs_positives": round(_auc(pos_d, ds), 3),
            "share_with_match_d_lt_0.3": round(sum(1 for d in finite if d < 0.3) / len(ds), 3),
        }
    pos_finite = [d for d in pos_d if d != float("inf")]
    discrimination["positives"] = {
        "n": len(pos_d),
        "share_with_match_d_lt_0.3": round(sum(1 for d in pos_finite if d < 0.3) / len(pos_d), 3),
    }

    # By skeleton length: saturation lives in the short skeletons.
    by_len: dict[str, Any] = {}
    for bucket, test in (("2", lambda n: n <= 2), ("3", lambda n: n == 3), ("4+", lambda n: n >= 4)):
        rows = [w for w in per_word if test(w["skeleton_len"])]
        if rows:
            by_len[bucket] = {"n": len(rows), **recovery([w["rank_exact"] for w in rows])}

    rng = random.Random(SEED)
    lat_words = rng.sample(golden_words(), min(latency_words, GOLDEN_SIZE))
    payload = {
        "description": "Pre-Shoresh baseline of cognate_search's Proto-Semitic layer on the gold set.",
        "recovery_exact": recovery(ranks_exact),
        "recovery_guttural_folded": recovery(ranks_folded),
        "recovery_exact_by_skeleton_len": by_len,
        "discrimination_best_ps_distance": discrimination,
        "cli_latency_all_languages": _cli_latency(lat_words),
        "per_word": per_word,
    }
    write_fixture(BASELINE_PATH, payload, before)
    print(json.dumps({k: payload[k] for k in payload if k not in ("per_word",)}, ensure_ascii=False, indent=1))


DEEP = 5000     # top_n for baseline-v2: the whole PS match list, so tie groups are complete


def _ps_matches(word: str) -> list[dict]:
    res = search_cognates(word, top_n=DEEP, use_cache=False)
    return [m for m in res["matches"] if m["method"] == "proto_semitic"]


def _share_lt(ds: list[float], cut: float = 0.3) -> float:
    return sum(1 for d in ds if d < cut) / len(ds) if ds else float("nan")


def build_baseline_v2(version: int = 2) -> None:
    """The baseline on gold v2, or on gold v3."""
    gold_path, path = {2: (GOLD_V2_PATH, BASELINE_V2_PATH), 3: (GOLD_V3_PATH, BASELINE_V3_PATH)}[version]
    _refuse_existing(path)
    before = input_hashes()
    gold = _read_gold(gold_path, before)
    best: dict[str, float] = {}

    def best_d(word: str, ps: list[dict] | None = None) -> float:
        if word not in best:
            ps = _ps_matches(word) if ps is None else ps
            best[word] = min((m["distance"] for m in ps), default=float("inf"))
        return best[word]

    per_word = []
    for p in gold["positives"]:
        ps = _ps_matches(p["word"])
        keys = [tuple(k.split("-")) for k in p["root_keys"]]
        er, trunc = expected_rank(keys, ps)
        erf, truncf = expected_rank(keys, ps, folded=True)
        d = best_d(p["word"], ps)
        per_word.append({"word": p["word"], "skeleton_len": p["skeleton_len"], "informative": p["informative"],
                         "lb_values_only": p["lb_values_only"], "expected_rank": er, "expected_rank_folded": erf,
                         "tie_group_truncated": trunc or truncf, "n_ps_matches": len(ps),
                         "best_distance": None if d == float("inf") else d})     # null: no PS match at all

    def recovery(rows: list[dict], key: str) -> dict[str, Any]:
        n = len(rows)
        if not n:
            return {"n": 0}
        r = [w[key] for w in rows]
        return {"n": n, **{f"hit@{k}": round(sum(1 for x in r if x is not None and x <= k) / n, 3) for k in (1, 5, 20)},
                "mrr": round(sum(1 / x for x in r if x) / n, 3),
                "truncated_tie_groups": sum(w["tie_group_truncated"] for w in rows)}

    info = [w for w in per_word if w["informative"]]
    strata = {"all": per_word, "informative": info,
              "informative_lb_values_only": [w for w in info if w["lb_values_only"]]}
    recovery_out = {name: {"exact": recovery(rows, "expected_rank"), "folded": recovery(rows, "expected_rank_folded")}
                    for name, rows in strata.items()}

    pos_info = [best_d(w["word"]) for w in info]
    classes: dict[str, list[float]] = {}
    for row in gold["negatives"] + gold["controls"]:
        if row.get("informative", row.get("skeleton_len", 0) >= INFORMATIVE_MIN):
            classes.setdefault(row["kind"], []).append(best_d(row["word"]))
    for kind in ("lb_negatives", "lb_loans", "lb_shuffles"):
        classes[kind] = [best_d(r["word"]) for r in gold[kind]]
    discrimination = {}
    for kind, ds in sorted(classes.items()):
        if not ds:
            continue
        discrimination[kind] = {"n": len(ds), "share_with_match_d_lt_0.3": round(_share_lt(ds), 3),
                                "auc_vs_informative_positives": _bootstrap(_auc, pos_info, ds)}
    discrimination["positives_informative"] = {"n": len(pos_info), "share_with_match_d_lt_0.3":
                                               round(_share_lt(pos_info), 3)}

    # Real-minus-shuffled, Linear A vs Linear B (§6 A2): share with a match d < 0.3, the real words minus their
    # own shuffles; Linear A must beat Linear B with the interval of the difference above zero.
    la_real = pos_info
    la_shuf = [best_d(c["word"]) for c in gold["controls"] if c["kind"] == "sign_shuffle" and c["informative"]]
    lb_real = classes["lb_negatives"]
    lb_shuf = [best_d(r["word"]) for r in gold["lb_shuffles"] if r["source"] in {x["word"] for x in gold["lb_negatives"]}]
    rng = random.Random(SEED)

    def margin(real: list[float], shuf: list[float]) -> float:
        return _share_lt(real) - _share_lt(shuf)

    diffs = sorted(margin(rng.choices(la_real, k=len(la_real)), rng.choices(la_shuf, k=len(la_shuf)))
                   - margin(rng.choices(lb_real, k=len(lb_real)), rng.choices(lb_shuf, k=len(lb_shuf)))
                   for _ in range(2000))
    margins = {
        "linear_a": {"n_real": len(la_real), "n_shuffled": len(la_shuf), "margin": round(margin(la_real, la_shuf), 3)},
        "linear_b": {"n_real": len(lb_real), "n_shuffled": len(lb_shuf), "margin": round(margin(lb_real, lb_shuf), 3)},
        "difference_a_minus_b": {"estimate": round(margin(la_real, la_shuf) - margin(lb_real, lb_shuf), 3),
                                 "ci95": [round(diffs[50], 3), round(diffs[1949], 3)]},
    }
    payload = {
        "description": (f"Pre-Shoresh baseline of cognate_search's Proto-Semitic layer on gold v{version} "
                        "(ref §6): expected ranks under random tie-breaking over the full PS list, bootstrap 95% intervals "
                        "(2,000 seeded resamples), and the Linear A vs Linear B real-minus-shuffled margins."),
        "recovery": recovery_out,
        "discrimination_best_ps_distance": discrimination,
        "real_minus_shuffled": margins,
        "per_word": per_word,
    }
    write_fixture(path, payload, before)
    print(json.dumps({k: payload[k] for k in payload if k != "per_word"}, ensure_ascii=False, indent=1))


def _distance_band(d: float) -> str:
    """D3's distance bands on a best PS distance: 0, ≤ 0.15, ≤ 0.3, ≤ 0.5, > 0.5, and none for no match."""
    if d == float("inf"):
        return "none"
    if d == 0:
        return "0"
    return next((f"<={hi}" for hi in (0.15, 0.3, 0.5) if d <= hi), ">0.5")


def _d3_weights(la_bins: list[tuple], lb_bins: list[tuple]) -> tuple[list[float], float]:
    """D3: each Linear B row's weight, its bin's Linear A share over its Linear B share (0 for a bin Linear A lacks),
    and the Linear A share that falls in bins with no Linear B row (reported, never reweighted)."""
    la, lb = Counter(la_bins), Counter(lb_bins)
    weights = [(la[b] / len(la_bins)) / (lb[b] / len(lb_bins)) if la[b] else 0.0 for b in lb_bins]
    return weights, sum(n for b, n in la.items() if b not in lb) / len(la_bins)


def _wshare(ds: list[float], ws: list[float], cut: float = 0.3) -> float:
    total = sum(ws)
    return sum(w for d, w in zip(ds, ws) if d < cut) / total if total else float("nan")


def build_baseline_v4() -> None:
    """The baseline on gold v4 (A22): recovery by target Number in the top 5 (D5), and A2's contrast with the Linear
    B margin distance-matched to each stratum's positives (D3). A Linear B shuffle carries its source word's weight,
    so the matched contrast compares how far shuffling moves Linear A and Greek words that start at the same
    distance. The per-row distances are the bins the gold run reuses."""
    _refuse_existing(BASELINE_V4_PATH)
    before = input_hashes(V4_INPUTS)
    gold = _read_gold(GOLD_V4_PATH, before)
    numbers_by_ps: dict[str, set[str]] = {}
    for rec in roots_records(json.loads((SEMITIC_ROOTS_DATA / "semitic_roots.json").read_text(encoding="utf-8"))):
        numbers_by_ps.setdefault(rec.get("Proto-Semitic", ""), set()).add(str(rec["Number"]))
    best: dict[str, float] = {}

    def best_d(word: str, ps: list[dict] | None = None) -> float:
        if word not in best:
            ps = _ps_matches(word) if ps is None else ps
            best[word] = min((m["distance"] for m in ps), default=float("inf"))
        return best[word]

    per_word = []
    for p in gold["positives"]:
        ps = _ps_matches(p["word"])
        targets = set(p["target_numbers"])
        er, trunc = _expected_rank_of([bool(numbers_by_ps.get(m["root"], set()) & targets) for m in ps], ps)
        d = best_d(p["word"], ps)
        per_word.append({"word": p["word"], "stratum": p["stratum"], "skeleton_len": p["skeleton_len"],
                         "expected_rank_number": er, "tie_group_truncated": trunc, "n_ps_matches": len(ps),
                         "best_distance": None if d == float("inf") else d, "band": _distance_band(d)})
    recovery = {}
    for stratum in ("primary", "secondary"):
        rows = [w for w in per_word if w["stratum"] == stratum]
        r = [w["expected_rank_number"] for w in rows]
        recovery[stratum] = {"n": len(rows), **({"hit@5": round(sum(1 for x in r if x is not None and x <= 5)
                                                                 / len(rows), 3),
                                                  "mrr": round(sum(1 / x for x in r if x) / len(rows), 3),
                                                  "truncated_tie_groups": sum(w["tie_group_truncated"] for w in rows)}
                                               if rows else {})}

    lb_real = [r for r in gold["lb_negatives"] if r["skeleton_len"] >= INFORMATIVE_MIN]
    lb_words = {r["word"] for r in lb_real}
    lb_shuf = [r for r in gold["lb_shuffles"] if r["source"] in lb_words]
    lb_bins = [(r["skeleton_len"], _distance_band(best_d(r["word"]))) for r in lb_real]
    rng = random.Random(SEED)

    def contrast(stratum: str) -> dict[str, Any]:
        real = [p for p in gold["positives"] if p["stratum"] == stratum and p["informative"]]
        sources = {p["word"] for p in real}
        shuf = [c for c in gold["controls"] if c["kind"] == "sign_shuffle" and c["informative"]
                and c["source"] in sources]
        la_real, la_shuf = [best_d(p["word"]) for p in real], [best_d(c["word"]) for c in shuf]
        weights, unmatched = _d3_weights([(p["skeleton_len"], _distance_band(d)) for p, d in zip(real, la_real)],
                                         lb_bins)
        by_word = dict(zip((r["word"] for r in lb_real), weights))
        lr = list(zip([best_d(r["word"]) for r in lb_real], weights))
        ls = [(best_d(r["word"]), by_word[r["source"]]) for r in lb_shuf]

        def margins(a: list[float], s: list[float], b: list[tuple], t: list[tuple]) -> tuple[float, float]:
            la_m = _share_lt(a) - _share_lt(s)
            return la_m, la_m - (_wshare(*zip(*b)) - _wshare(*zip(*t)))

        la_m, diff = margins(la_real, la_shuf, lr, ls)
        boot = sorted(margins(rng.choices(la_real, k=len(la_real)), rng.choices(la_shuf, k=len(la_shuf)),
                              rng.choices(lr, k=len(lr)), rng.choices(ls, k=len(ls)))[1] for _ in range(2000))
        out = {"n_real": len(la_real), "n_shuffled": len(la_shuf), "linear_a_margin": round(la_m, 3),
               "weighted_linear_b_margin": round(la_m - diff, 3),
               "difference_a_minus_weighted_b": {"estimate": round(diff, 3),
                                                 "ci95": [round(boot[50], 3), round(boot[1949], 3)]},
               "linear_a_share_in_bins_without_linear_b": round(unmatched, 3),
               "bins": dict(sorted(Counter(f"{n}:{b}" for n, b in zip((p["skeleton_len"] for p in real),
                                                                      map(_distance_band, la_real))).items()))}
        if stratum == "primary":
            out["lower_bound_above_0"] = boot[50] > 0
        return out

    payload = {
        "description": ("Pre-Shoresh baseline of cognate_search's Proto-Semitic layer on gold v4 (ref §6 A22): "
                        "recovery as an expected rank, under random tie-breaking, of the first match whose "
                        "Proto-Semitic headword belongs to a target Number (D5: a hit is rank <= 5); A2's "
                        "contrast per stratum with the Linear B Greek rows reweighted to the stratum's bins of "
                        "skeleton length and distance band (D3), each Linear B shuffle at its source's weight; "
                        "2,000 seeded bootstrap resamples of rows. The secondary stratum carries no pass mark."),
        "recovery_by_number": recovery,
        "a2_distance_matched": {s: contrast(s) for s in ("primary", "secondary")},
        "best_ps_distance": {w: (None if d == float("inf") else d) for w, d in sorted(best.items())},
        "per_word": per_word,
    }
    write_fixture(BASELINE_V4_PATH, payload, before, V4_INPUTS)
    print(json.dumps({k: payload[k] for k in ("recovery_by_number", "a2_distance_matched")}, ensure_ascii=False,
                     indent=1))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("gold", help="write tests/fixtures/root_match_gold.json")
    sub.add_parser("golden", help="write tests/fixtures/cognate_search_golden.json")
    b = sub.add_parser("baseline", help="write tests/fixtures/root_match_baseline.json")
    b.add_argument("--latency-words", type=int, default=20)
    sub.add_parser("gold-v2", help="write tests/fixtures/root_match_gold.v2.json")
    sub.add_parser("baseline-v2", help="write tests/fixtures/root_match_baseline.v2.json")
    sub.add_parser("gold-v3", help="write tests/fixtures/root_match_gold.v3.json")
    sub.add_parser("baseline-v3", help="write tests/fixtures/root_match_baseline.v3.json")
    sub.add_parser("gold-v4", help="write tests/fixtures/root_match_gold.v4.json (A22)")
    sub.add_parser("baseline-v4", help="write tests/fixtures/root_match_baseline.v4.json (A22: D3, D5)")
    args = parser.parse_args()
    if args.cmd == "gold":
        build_gold()
    elif args.cmd == "golden":
        build_golden()
    elif args.cmd == "baseline":
        build_baseline(args.latency_words)
    elif args.cmd in ("gold-v2", "gold-v3"):
        build_gold_v2(int(args.cmd[-1]))
    elif args.cmd == "gold-v4":
        build_gold_v4()
    elif args.cmd == "baseline-v4":
        build_baseline_v4()
    else:
        build_baseline_v2(int(args.cmd[-1]))


if __name__ == "__main__":
    main()
