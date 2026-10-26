"""Shoresh's semantic gate (§3.1, A10, A18, A19; see SHORESH.md): a word's context domains and
a cluster's domains. The engine computes d*_sem over the clusters that fit and gates every decoy by the real word's
context (root_match).

Frozen with A18 and A19, changed only by an amendment: the logogram map, its spelling variants, the layout tokens,
the document-type table and the tagger, frozen/tag_semantic_fields.py, whose bytes are checked against
TAGGER_SHA256 before they run.

Attribution: di Mino
"""
from __future__ import annotations

import hashlib
import re
import sys
from collections.abc import Iterable
from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace

try:
    from .shoresh_nulls import sign_group_key
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from tools.core.shoresh_nulls import sign_group_key

TAGGER = Path(__file__).resolve().parent / "frozen" / "tag_semantic_fields.py"
TAGGER_SHA256 = "7f7c5225b110c27eed033979934260d24e9f471f0f5d8d3dc8ac125ac422e1ee"

# The adjacent logogram, by its conventional identification only (Linear B ideograms, GORILA); ligatures pool with
# their base sign. The project's own readings of a logogram never count (A18).
LOGOGRAM_DOMAINS: dict[str, frozenset[str]] = {
    "GRA": frozenset({"agriculture", "food_drink"}),                  # grain, LB *120
    "CYP": frozenset({"flora", "food_drink"}),                        # cyperus, LB *125
    "OLE": frozenset({"food_drink", "agriculture"}),                  # oil, LB *130
    "VIR": frozenset({"administrative", "kinship"}),                  # men, LB *100
    "VIN": frozenset({"food_drink", "agriculture"}),                  # wine, LB *131
    "OLIV": frozenset({"flora", "food_drink", "agriculture"}),        # olives, LB *122
    "*21M": frozenset({"fauna"}), "*21F": frozenset({"fauna"}),       # ram, ewe (A19)
    "*22F": frozenset({"fauna"}), "*22M": frozenset({"fauna"}),       # she-goat, he-goat
    "*23M": frozenset({"fauna"}),                                     # bull
    "HIDE": frozenset({"fauna", "textile"}),
    "*131B": frozenset({"food_drink"}), "*131C": frozenset({"food_drink"}),   # GORILA's wine class
    "*118": frozenset({"metrology", "metallurgy"}),                   # LB *118 TALENT
    "NI": frozenset({"flora", "food_drink"}),                         # LB *30 FIC
}
NUMBER_REQUIRED = frozenset({"*118", "NI"})     # a logogram only where a number follows; otherwise a syllable
SPELLINGS = {"*OLIV": "OLIV", "VINb": "*131B", "VINc": "*131C"}    # a mapped sign's spelling variants (A19)
LAYOUT = frozenset({"\n", "𐄁"})                # skipped between a word and the next token (A19)

_RITUAL = frozenset({"ritual_cultic", "deity"})
_POTTERY = frozenset({"pottery_vessel", "food_drink"})
# corpus.json `support`, every string the corpus holds (A18): formula objects, vessels, and the rest unknown (None).
SUPPORT_DOMAINS: dict[str, frozenset[str] | None] = {
    "Stone vessel": _RITUAL, "Stone-vessel fragment": _RITUAL, "Stone object": _RITUAL, "Metal object": _RITUAL,
    "ivory object": _RITUAL, "Bronze bowl": _RITUAL, "Silver pin": _RITUAL, "Triton": _RITUAL,
    "Stone ladle (HM 1545)": _RITUAL, "Fragment of a locally made limestone bowl or krater": _RITUAL,
    "Serpentine cylindrical jar; HM 2479 + HM 2480": _RITUAL,
    "Square red-orange serpentine libation table (HM 5317)": _RITUAL,
    "Square serpentine libation-table fragment": _RITUAL, "Stone libation table fragment": _RITUAL,
    "Fragmentary circular serpentine libation table": _RITUAL,
    "Clay vessel": _POTTERY, "clay vessel": _POTTERY, "Painted clay vessel": _POTTERY, "Pithoid jar": _POTTERY,
    "Inked inscription": _POTTERY, "Clay chalice rim (two nonjoining fragments); painted inscription": _POTTERY,
    "Tablet": None, "Lames (short thin tablet)": None, "3-sided bar": None, "4-sided bar": None, "Roundel": None,
    "Nodule": None, "Sealing": None, "Architecture": None, "Graffito": None, "Grave stele fragment": None,
    "Clay reel": None, "Clay larnax fragment": None, "Loom weight": None, "Label": None,
    "Amygdaloid stone seal": None, "Unspecified object": None, "": None,
}

_NUMBER = re.compile(r"\d|⁄")


class TaggerChanged(RuntimeError):
    """The tagger's bytes differ from those A18 froze."""


@lru_cache(maxsize=1)
def tagger() -> SimpleNamespace:
    """The frozen tagger module (classify, DOMAIN_KEYWORDS), run from the very bytes that were hashed."""
    data = TAGGER.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != TAGGER_SHA256:
        raise TaggerChanged(f"{TAGGER.name} sha256 {digest[:8]} is not the {TAGGER_SHA256[:8]} frozen with A18: "
                            "the tagger changes only by an amendment")
    ns: dict = {"__name__": "tag_semantic_fields", "__file__": str(TAGGER)}
    exec(compile(data, str(TAGGER), "exec"), ns)  # noqa: S102 (the bytes just checked against TAGGER_SHA256)
    return SimpleNamespace(classify=ns["classify"], DOMAIN_KEYWORDS=ns["DOMAIN_KEYWORDS"])


def _key(word: str) -> tuple[str, ...]:
    return sign_group_key(word)                         # the gold guard's canonical spelling


def _base(token: str) -> str:
    """A logogram token's mapped sign: ligatures by their base, spelling variants as their sign (A18, A19)."""
    base = token.split("+")[0]
    return SPELLINGS.get(base, base)


def logogram_domains(after: str | None, next_after: str | None) -> frozenset[str] | None:
    """The domains of the token after a word, if it is a mapped logogram (ligatures by their base)."""
    if not after:
        return None
    base = _base(after)
    domains = LOGOGRAM_DOMAINS.get(base)
    if domains is not None and base in NUMBER_REQUIRED and not (next_after and _NUMBER.search(next_after)):
        return None
    return domains


def _fused(token: str) -> tuple[str, frozenset[str] | None]:
    """(word, domains): a hyphenated token ending in a mapped logogram other than *118 and NI is the word before it
    followed by that logogram (A19); any other token is itself, with no logogram."""
    head, _, last = token.rpartition("-")
    base = _base(last)
    if head and base in LOGOGRAM_DOMAINS and base not in NUMBER_REQUIRED:
        return head, LOGOGRAM_DOMAINS[base]
    return token, None


class Contexts:
    """Each word's attested contexts in a corpus (corpus.json's shape): per attestation, the adjacent logogram's
    domains, else the document type's, else unknown. The adjacent logogram is the next token past any layout, or
    one fused onto the word. A word's context is the union over its attestations (A18, A19)."""

    def __init__(self, corpus: dict[str, dict]):
        self._of: dict[tuple[str, ...], list[frozenset[str] | None]] = {}
        for doc in corpus.values():
            support = SUPPORT_DOMAINS.get(doc.get("support", "") or "")
            toks = [t for t in doc.get("transliteratedWords", []) if isinstance(t, str)]
            for i, t in enumerate(toks):
                if "-" not in t:
                    continue
                word, logo = _fused(t)
                if logo is None:
                    j = i + 1
                    while j < len(toks) and toks[j] in LAYOUT:
                        j += 1
                    logo = logogram_domains(toks[j] if j < len(toks) else None,
                                            toks[j + 1] if j + 1 < len(toks) else None)
                if "-" not in word:
                    continue                                 # a one-sign remainder is no word
                self._of.setdefault(_key(word), []).append(logo if logo is not None else support)

    def attestations(self, word: str) -> tuple[int, int]:
        """(attestations, those with a known context)."""
        rows = self._of.get(_key(word), [])
        return len(rows), sum(r is not None for r in rows)

    def context(self, word: str) -> frozenset[str] | None:
        """The union of the known contexts, or None: no semantic evidence (§3.1)."""
        known = [r for r in self._of.get(_key(word), []) if r is not None]
        return frozenset().union(*known) if known else None


def cluster_domains(meanings: dict[str, str | None], joined_glosses: dict[str, Iterable[str]]) -> dict[str, frozenset[str]]:
    """Number → the tagger's domains over the record's Meaning and the glosses of its joined contact lexemes (the
    caller leaves onomastica out). An empty set never fits."""
    classify = tagger().classify
    out: dict[str, frozenset[str]] = {}
    for n in meanings.keys() | joined_glosses.keys():
        texts = [meanings.get(n) or "", *joined_glosses.get(n, ())]
        out[n] = frozenset(d for t in texts for d in classify(t or ""))
    return out


def fits(cluster: frozenset[str], context: frozenset[str] | None) -> bool:
    return bool(context) and bool(cluster & context)
