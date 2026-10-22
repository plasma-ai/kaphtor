#!/usr/bin/env python3
"""Affix-doublet miner — both-members-attested corpus pairs for nominal,
pronominal, and particle affixes.

Generalizes the hand method that validated suffix_ti from four corpus
doublets (JA-KU/JA-KU-TI, DU-RA/JA-DU-RA-TI, DA-KU-SE-NE/DA-KU-SE-NE-TI,
QA-KI/QA-KI-TI). A candidate affix only produces a pair when BOTH the bare
base and the affixed form are independently attested corpus words — the
false-discovery control that raw lens matching lacks.

Two mining modes, driven by the template's affix spec:

  prefix/suffix   Literal sign-sequence strip (with alternatives, e.g. the
                  mimation family -MA/-ME/-MI/-MO/-MU). Unlike the verb-lens
                  loader, single pure-vowel affixes are permitted: pair mining
                  is positional and both members must be independently
                  attested, so a bare-vowel affix cannot manufacture a
                  skeleton match the way a bare-vowel strip could.

  final_vowel     Case-vowel alternation on the FINAL sign (the CV syllabary
                  writes a postconsonantal case vowel inside the last sign,
                  so NOM/GEN/ACC -u/-i/-a surface as X…-CU / X…-CI / X…-CA
                  on a shared stem). A stem counts when its final-sign vowel
                  includes the template's vowel AND at least one other vowel
                  of the triple is attested on the same stem+consonant.

Report-only: never writes affiliations, lexicon entries, or promotions.
Null calibration lives in tools/linear_a/validation/null_model_audit.py --affix-lens.

Usage:
    uv run tools/linear_a/analysis/affix_doublet_miner.py --suffix TI
    uv run tools/linear_a/analysis/affix_doublet_miner.py --prefix U
    uv run tools/linear_a/analysis/affix_doublet_miner.py --suffix U-TI-NU
    uv run tools/linear_a/analysis/affix_doublet_miner.py --template-file data/linear-a/affix_templates.json
    uv run tools/linear_a/analysis/affix_doublet_miner.py --template-file data/linear-a/affix_templates.json \
        --template-id poss_su_3ms --json report.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    __package__ = "tools.linear_a.analysis"

from ...core.skeleton import _SUBSCRIPT_MAP, _lookup_sign
from ...paths import LINEAR_A_DATA, NotInCheckout, require

TEMPLATES_PATH = LINEAR_A_DATA / "affix_templates.json"
CORPUS_PATH = LINEAR_A_DATA / "corpus.json"
LEXICON_PATH = LINEAR_A_DATA / "lexicon.json"
ONOMASTICON_PATH = LINEAR_A_DATA / "onomasticon.json"

# Damaged readings: affix mining on restorations would pair conjecture with
# conjecture (same rationale as lib/verb_morphology.LACUNA_CHARS).
LACUNA_CHARS = ("[", "]", "?")
SEPARATOR = "\U00010101"  # 𐄁 Aegean word separator
PENALTY_TIERS = (0.10, 0.25, 0.40)


def _normalize_sign(sign: str) -> str:
    return sign.upper().translate(_SUBSCRIPT_MAP)


def normalize_word(word: str) -> str:
    return "-".join(_normalize_sign(s) for s in word.split("-"))


def is_word(token: str) -> bool:
    """Multi-sign transliteration, undamaged, not a numeral."""
    return (
        "-" in token
        and not token.replace("-", "").isdigit()
        and not any(ch in token for ch in LACUNA_CHARS)
    )


def is_numeral(token: str) -> bool:
    return token.replace("-", "").isdigit() or "⁄" in token  # ⁄ fraction slash


# ---------------------------------------------------------------------------
# Template loading
# ---------------------------------------------------------------------------

def load_affix_templates(path: Path | None = None) -> list[dict]:
    """Load and validate the affix-template inventory.

    Schema mirrors verb_templates.json where the fields overlap (id,
    description, penalty tiers, evidence, layer_scope, status) but the
    surface spec is an `affix` object, not a deparser pattern — these
    templates are mined for attested doublet pairs, never parsed for
    residual-root matching.
    """
    path = path or TEMPLATES_PATH
    data = json.loads(require(path, path.name).read_text(encoding="utf-8"))
    templates: list[dict] = []
    seen_ids: set[str] = set()
    for raw in data["templates"]:
        tid = raw["id"]
        if tid in seen_ids:
            raise ValueError(f"template {tid}: duplicate id")
        seen_ids.add(tid)
        affix = raw["affix"]
        position = affix["position"]
        if position not in ("prefix", "suffix", "final_vowel"):
            raise ValueError(f"template {tid}: unknown position {position!r}")
        if raw["penalty"] not in PENALTY_TIERS:
            raise ValueError(f"template {tid}: penalty {raw['penalty']} outside defined tiers")
        if raw["status"] not in ("active", "speculative"):
            raise ValueError(f"template {tid}: unknown status {raw['status']!r}")
        t = dict(raw)
        if position == "final_vowel":
            vowel = affix["vowel"].lower()
            triple = [v.lower() for v in affix["triple"]]
            if vowel not in triple:
                raise ValueError(f"template {tid}: vowel {vowel!r} missing from its triple")
            if len(triple) < 2:
                raise ValueError(f"template {tid}: final_vowel triple needs >= 2 vowels")
            t["affix"] = {"position": position, "vowel": vowel, "triple": triple}
        else:
            alternatives = [
                tuple(_normalize_sign(s) for s in alt) for alt in affix["alternatives"]
            ]
            if not alternatives or any(not alt for alt in alternatives):
                raise ValueError(f"template {tid}: empty affix alternative")
            if len(set(alternatives)) != len(alternatives):
                raise ValueError(f"template {tid}: duplicate affix alternative")
            co_strips = [
                tuple(_normalize_sign(s) for s in p)
                for p in affix.get("co_strip_prefixes", [])
            ]
            if co_strips and position != "suffix":
                raise ValueError(f"template {tid}: co_strip_prefixes require a suffix affix")
            t["affix"] = {"position": position, "alternatives": alternatives,
                          "co_strip_prefixes": co_strips}
        templates.append(t)
    return templates


# ---------------------------------------------------------------------------
# Corpus indexing
# ---------------------------------------------------------------------------

def build_word_index(corpus_path: Path | None = None) -> dict[str, dict]:
    """Normalized word -> attestation record with positional metadata.

    Positional counters per occurrence:
      heads_document   first word-token of its inscription
      line_initial     inscription-initial or immediately after a line break
      follows_numeral  previous non-separator token is a numeral/fraction
    """
    corpus = json.loads((corpus_path or CORPUS_PATH).read_text(encoding="utf-8"))
    index: dict[str, dict] = {}
    for iid, insc in sorted(corpus.items()):
        site = insc.get("site", "?")
        support = str(insc.get("support", ""))
        first_word_seen = False
        prev: str | None = None
        prev_non_sep: str | None = None
        for token in insc.get("transliteratedWords", []):
            if is_word(token):
                w = normalize_word(token)
                info = index.setdefault(w, {
                    "frequency": 0,
                    "inscriptions": set(),
                    "sites": set(),
                    "supports": set(),
                    "heads_document": 0,
                    "line_initial": 0,
                    "follows_numeral": 0,
                })
                info["frequency"] += 1
                info["inscriptions"].add(iid)
                info["sites"].add(site)
                info["supports"].add(support)
                if not first_word_seen:
                    info["heads_document"] += 1
                if prev is None or prev == "\n":
                    info["line_initial"] += 1
                if prev_non_sep is not None and is_numeral(prev_non_sep):
                    info["follows_numeral"] += 1
                first_word_seen = True
            if token != SEPARATOR:
                prev_non_sep = token
            prev = token
    return index


def load_corpus_vocab(corpus_path: Path | None = None) -> list[str]:
    """Sorted unique normalized word forms (the pair-mining population)."""
    return sorted(build_word_index(corpus_path))


def load_lexicon_map(path: Path | None = None) -> dict[str, dict]:
    lex = json.loads((path or LEXICON_PATH).read_text(encoding="utf-8"))
    entries = lex.get("entries", lex)
    out = {}
    for e in entries:
        word = normalize_word(str(e.get("word", "")))
        if word:
            out[word] = {
                "reading": e.get("reading"),
                "meaning": e.get("meaning"),
                "confidence": e.get("confidence"),
                "tier": e.get("tier"),
            }
    return out


def load_onomasticon_map(path: Path | None = None) -> dict[str, dict]:
    ono = json.loads((path or ONOMASTICON_PATH).read_text(encoding="utf-8"))
    out = {}
    for e in ono.get("entries", []):
        token = normalize_word(str(e.get("normalized") or e.get("token") or ""))
        if token:
            out[token] = {
                "reading": e.get("reading"),
                "type": e.get("type"),
                "affiliation": e.get("affiliation"),
                "affiliation_confidence": e.get("affiliation_confidence"),
            }
    return out


# ---------------------------------------------------------------------------
# Pair mining
# ---------------------------------------------------------------------------

def iter_affix_pairs(vocab, position: str, alternatives,
                     co_strip_prefixes=()) -> list[tuple[str, str, tuple[str, ...], tuple[str, ...] | None]]:
    """(base, affixed, alt, co_strip) for every vocab word whose strip leaves an attested base.

    Bases must themselves be multi-sign vocabulary words, so single-sign
    residues (KU-RO minus -RO) never pair — a stated coverage limit, not a bug.

    `co_strip_prefixes` handles doubly-affixed doublets: when a suffix strip
    leaves no attested base, each co-strip prefix is additionally removed
    before the base lookup (DU-RA / JA-DU-RA-TI pairs only after the JA-
    person prefix comes off with the -TI). Co-stripped pairs carry the
    stripped prefix in the fourth slot; direct pairs carry None.
    """
    vocab_set = set(vocab)
    pairs = []
    for w in sorted(vocab_set):
        signs = tuple(w.split("-"))
        for alt in alternatives:
            k = len(alt)
            if len(signs) <= k:
                continue
            if position == "suffix" and signs[-k:] == tuple(alt):
                residual = signs[:-k]
            elif position == "prefix" and signs[:k] == tuple(alt):
                residual = signs[k:]
            else:
                continue
            base = "-".join(residual)
            if base in vocab_set and base != w:
                pairs.append((base, w, tuple(alt), None))
                continue
            if position != "suffix":
                continue
            for co in co_strip_prefixes:
                co = tuple(co)
                j = len(co)
                if len(residual) > j and residual[:j] == co:
                    co_base = "-".join(residual[j:])
                    if co_base in vocab_set and co_base != w:
                        pairs.append((co_base, w, tuple(alt), co))
    return pairs


def iter_vowel_alternations(vocab, triple) -> list[tuple[str, str, dict[str, str]]]:
    """Final-sign case-vowel alternation groups.

    Returns (stem_display, final_consonant, {vowel: word}) for every stem
    whose final sign alternates across >= 2 vowels of the triple with the
    same final consonant. Pure-vowel and unknown final signs are skipped —
    a bare-vowel final sign carries no consonant to hold the stem constant.
    """
    triple = [v.lower() for v in triple]
    groups: dict[tuple[str, str], dict[str, str]] = {}
    for w in sorted(set(vocab)):
        signs = w.split("-")
        if len(signs) < 2:
            continue
        decomp = _lookup_sign(signs[-1])
        if not decomp or decomp[0] is None or decomp[1] is None:
            continue
        cons, vowel = decomp
        if vowel not in triple:
            continue
        key = ("-".join(signs[:-1]), cons)
        groups.setdefault(key, {})[vowel] = w
    return [
        (stem, cons, by_vowel)
        for (stem, cons), by_vowel in sorted(groups.items())
        if len(by_vowel) >= 2
    ]


def count_template_pairs(vocab, template: dict) -> int:
    """The null-calibration statistic for one template.

    prefix/suffix: distinct (base, affixed) pairs.
    final_vowel:   alternating stems whose vowel set includes this template's vowel.
    """
    affix = template["affix"]
    if affix["position"] == "final_vowel":
        return sum(
            1 for _, _, by_vowel in iter_vowel_alternations(vocab, affix["triple"])
            if affix["vowel"] in by_vowel
        )
    return len({
        (b, w) for b, w, _, _ in iter_affix_pairs(
            vocab, affix["position"], affix["alternatives"],
            co_strip_prefixes=affix.get("co_strip_prefixes", ()),
        )
    })


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def _summarize(info: dict) -> dict:
    return {
        "frequency": info["frequency"],
        "inscriptions": sorted(info["inscriptions"]),
        "sites": sorted(info["sites"]),
        "supports": sorted(s for s in info["supports"] if s),
        "heads_document": info["heads_document"],
        "line_initial": info["line_initial"],
        "follows_numeral": info["follows_numeral"],
    }


def _assignments(word: str, lexicon: dict, onomasticon: dict) -> dict:
    return {
        "lexicon": lexicon.get(word),
        "onomasticon": onomasticon.get(word),
    }


def mine_affix(index: dict[str, dict], position: str, alternatives,
               lexicon: dict | None = None, onomasticon: dict | None = None,
               co_strip_prefixes=()) -> list[dict]:
    lexicon = lexicon or {}
    onomasticon = onomasticon or {}
    records = []
    seen: set[tuple[str, str]] = set()
    for base, affixed, alt, co_strip in iter_affix_pairs(
            index, position, alternatives, co_strip_prefixes=co_strip_prefixes):
        if (base, affixed) in seen:
            continue
        seen.add((base, affixed))
        records.append({
            "base": base,
            "affixed": affixed,
            "affix": "-".join(alt),
            "co_stripped_prefix": "-".join(co_strip) if co_strip else None,
            "position": position,
            "base_attestation": _summarize(index[base]),
            "affixed_attestation": _summarize(index[affixed]),
            "base_assignments": _assignments(base, lexicon, onomasticon),
            "affixed_assignments": _assignments(affixed, lexicon, onomasticon),
        })
    records.sort(key=lambda r: -(r["base_attestation"]["frequency"]
                                 + r["affixed_attestation"]["frequency"]))
    return records


def mine_vowel_alternation(index: dict[str, dict], vowel: str, triple,
                           lexicon: dict | None = None,
                           onomasticon: dict | None = None) -> list[dict]:
    lexicon = lexicon or {}
    onomasticon = onomasticon or {}
    records = []
    for stem, cons, by_vowel in iter_vowel_alternations(index, triple):
        if vowel.lower() not in by_vowel:
            continue
        records.append({
            "stem": stem,
            "final_consonant": cons,
            "vowels_attested": sorted(by_vowel),
            "forms": {
                v: {
                    "word": w,
                    "attestation": _summarize(index[w]),
                    "assignments": _assignments(w, lexicon, onomasticon),
                }
                for v, w in sorted(by_vowel.items())
            },
        })
    records.sort(key=lambda r: -sum(
        f["attestation"]["frequency"] for f in r["forms"].values()))
    return records


def mine_template(index: dict[str, dict], template: dict,
                  lexicon: dict | None = None, onomasticon: dict | None = None) -> dict:
    affix = template["affix"]
    if affix["position"] == "final_vowel":
        results = mine_vowel_alternation(index, affix["vowel"], affix["triple"],
                                         lexicon, onomasticon)
    else:
        results = mine_affix(index, affix["position"], affix["alternatives"],
                             lexicon, onomasticon,
                             co_strip_prefixes=affix.get("co_strip_prefixes", ()))
    return {
        "template_id": template["id"],
        "family": template.get("family"),
        "description": template["description"],
        "status": template["status"],
        "penalty": template["penalty"],
        "confounds": template.get("confounds", []),
        "n_results": len(results),
        "results": results,
    }


def _print_pairs(report: dict) -> None:
    print(f"\n=== {report['template_id'] or 'ad-hoc'} — {report['description']} "
          f"({report['n_results']} pairs) ===")
    for c in report.get("confounds", []):
        print(f"  CONFOUND: {c}")
    if not report["results"]:
        print("  (no both-members-attested pairs)")
        return
    print(f"  {'base':<18}{'affixed':<22}{'n(b)/n(a)':>10}  sites(base) | lexicon base -> affixed")
    for r in report["results"]:
        if "stem" in r:
            forms = ", ".join(f"{v}:{f['word']}({f['attestation']['frequency']})"
                              for v, f in r["forms"].items())
            print(f"  {r['stem']+'-C'+r['final_consonant']:<40} {forms}")
            continue
        b, a = r["base_attestation"], r["affixed_attestation"]
        bl = (r["base_assignments"]["lexicon"] or {}).get("reading") or "—"
        al = (r["affixed_assignments"]["lexicon"] or {}).get("reading") or "—"
        co = f" [+{r['co_stripped_prefix']}-]" if r.get("co_stripped_prefix") else ""
        print(f"  {r['base']:<18}{r['affixed'] + co:<22}{b['frequency']:>4}/{a['frequency']:<5} "
              f"{','.join(b['sites'][:3]):<24} {bl} -> {al}")


def main() -> int:
    """Exit 2 with the file's name when a data file is not in the checkout."""
    try:
        _run()
    except NotInCheckout as e:
        print(f"stopped: {e}", file=sys.stderr)
        return 2
    return 0


def _run() -> None:
    parser = argparse.ArgumentParser(description="Affix doublet miner (report-only)")
    spec = parser.add_mutually_exclusive_group(required=True)
    spec.add_argument("--suffix", type=str, help="Suffix sign sequence, e.g. TI or U-TI-NU")
    spec.add_argument("--prefix", type=str, help="Prefix sign sequence, e.g. U or PA")
    spec.add_argument("--template-file", type=Path,
                      help="Mine every template in an affix-template JSON file")
    parser.add_argument("--template-id", action="append", default=None,
                        help="Restrict --template-file mining to these template ids")
    parser.add_argument("--also-strip-prefix", action="append", default=None,
                        help="Co-strip this prefix when a --suffix strip leaves no "
                             "attested base (e.g. JA for DU-RA/JA-DU-RA-TI)")
    parser.add_argument("--json", type=Path, default=None,
                        help="Write the full report JSON to this path")
    args = parser.parse_args()

    if args.template_id and not args.template_file:
        parser.error("--template-id requires --template-file")

    index = build_word_index()
    lexicon = load_lexicon_map()
    onomasticon = load_onomasticon_map()
    print(f"Corpus vocabulary: {len(index)} unique undamaged word forms", file=sys.stderr)

    reports = []
    if args.template_file:
        templates = load_affix_templates(args.template_file)
        wanted = set(args.template_id) if args.template_id else None
        if wanted:
            missing = wanted - {t["id"] for t in templates}
            if missing:
                parser.error(f"unknown template ids: {sorted(missing)}")
        for t in templates:
            if wanted and t["id"] not in wanted:
                continue
            reports.append(mine_template(index, t, lexicon, onomasticon))
    else:
        position = "suffix" if args.suffix else "prefix"
        if args.also_strip_prefix and position != "suffix":
            parser.error("--also-strip-prefix only applies to --suffix mining")
        signs = tuple(_normalize_sign(s) for s in (args.suffix or args.prefix).split("-"))
        co_strips = [
            tuple(_normalize_sign(s) for s in p.split("-"))
            for p in (args.also_strip_prefix or [])
        ]
        template = {
            "id": None, "family": "ad-hoc", "status": "ad-hoc", "penalty": 0.40,
            "description": f"ad-hoc {position} -{'-'.join(signs)}",
            "affix": {"position": position, "alternatives": [signs],
                      "co_strip_prefixes": co_strips},
        }
        reports.append(mine_template(index, template, lexicon, onomasticon))

    for report in reports:
        _print_pairs(report)

    if args.json:
        payload = {
            "generator": "tools/linear_a/analysis/affix_doublet_miner.py",
            "vocabulary_size": len(index),
            "reports": reports,
        }
        args.json.write_text(json.dumps(payload, indent=1, ensure_ascii=False),
                             encoding="utf-8")
        print(f"\nReport written to {args.json}", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
