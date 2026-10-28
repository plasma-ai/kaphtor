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


def input_hashes() -> dict[str, str | None]:
    """sha256 per tracked input; None for one that does not exist (its arrival is a change too)."""
    return {_rel(p): _sha256(p) if p.exists() else None for p in tracked_inputs()}


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


def write_fixture(path: Path, payload: dict[str, Any], hashes_before: dict[str, str | None]) -> None:
    """Write a fixture only if no tracked input changed during the run. The JSON goes to a temp file first and
    is linked into place (fails if the target exists), so a crash never leaves a half-written fixture."""
    changed = changed_inputs(hashes_before, input_hashes())
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
    is_gold = [any(f(k) in gold for k in ps_match_keys(m.get("root", ""))) for m in ps_matches]
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
    consonants, unmapped = [], []
    for sign in word.split("-"):
        decomp = _lookup_sign(sign)
        if decomp is None:
            unmapped.append(sign)
        elif decomp[0]:
            consonants.append(decomp[0])
    return "".join(consonants), unmapped


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


def _lb_words() -> tuple[list[dict], list[dict], list[dict]]:
    """(negatives, loans, excluded) from the V&C 1956 glossary, by the §6 A2 rule."""
    entries = json.loads((DATA_DIR / "linear_b_vc1956_glosses.json").read_text(encoding="utf-8"))["entries"]
    negatives, loans, excluded = [], [], []
    for lemma, e in sorted(entries.items()):
        if lemma in LB_SEMITIC_LOANS:
            word = lemma.upper()
            skel, unmapped = loud_skeleton(word)
            if unmapped:
                excluded.append({"word": word, "reason": f"unmapped {unmapped}"})
            else:
                loans.append({"word": word, "lb_lemma": lemma, "source": LB_SEMITIC_LOANS[lemma], "skeleton": skel,
                              "skeleton_len": len(_tokenize_phonemes(skel)), "kind": "lb_semitic_loan"})
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
        n = len(_tokenize_phonemes(skel))
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
    args = parser.parse_args()
    if args.cmd == "gold":
        build_gold()
    elif args.cmd == "golden":
        build_golden()
    elif args.cmd == "baseline":
        build_baseline(args.latency_words)
    elif args.cmd in ("gold-v2", "gold-v3"):
        build_gold_v2(int(args.cmd[-1]))
    else:
        build_baseline_v2(int(args.cmd[-1]))


if __name__ == "__main__":
    main()
