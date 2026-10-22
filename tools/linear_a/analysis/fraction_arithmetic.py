#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Fraction-sign arithmetic.

Solves the A700 klasmatogram series as a constraint-satisfaction problem over
tablet sum-checks, working from RAW sign identities in the corpus `words`
layer (Linear A Unicode, U+10740-U+10755) rather than the value-rendered
`transliteratedWords` layer (whose vulgar-fraction glyphs embed Bennett-
convention assumptions -- treated here as hypothesis H_Bennett, not data).

Subcommands:
  inventory   Corpus-wide census of raw fraction-sign identities, renderings,
              rendering inconsistencies, damage adjacency.
  extract     Parse anchor tablets into line-structured candidate equations.
  solve       Exhaustive/DFS search over value assignments for atomic signs;
              composites (JE=J+E, DD=2D...) expand structurally.
  check       Corpus-wide sum-check under a given value assignment.

Every subcommand reads and writes its JSON in --out (default: the user cache,
`CACHE/linear-a/fraction-arithmetic/`); hand-curated equations for the complex
tablets go in EQUATION_CURATION.json there.

    uv run tools/linear_a/analysis/fraction_arithmetic.py [--out DIR] inventory

Fraction-char constants follow tools/linear_a/logogram_analyzer.py (FRACTION_CHARS,
FRACTION_VALUES); duplicated here (cf. context_search.py) because logogram_analyzer
is a command, not a library module.
"""

from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from collections import Counter, defaultdict
from fractions import Fraction
from itertools import product
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    __package__ = "tools.linear_a.analysis"

from ...paths import CACHE, LINEAR_A_DATA, NotInCheckout, require

DATA_DIR = LINEAR_A_DATA
DEFAULT_OUT = CACHE / "linear-a" / "fraction-arithmetic"

# Raw klasmatogram codepoints (Linear A block, Unicode names "LINEAR A SIGN A7xx L")
FRAC_CP_RANGE = range(0x10740, 0x10756)
DAMAGE_CP = 0x1076B  # lacuna/truncation mark, renders as 𐝫; unnamed in unicodedata 15.1
SEPARATOR_CHARS = {"\U00010101", "—", "–", "-", ""}
VULGAR_FRACTION_CHARS = frozenset("¼½¾⅐⅑⅒⅓⅔⅕⅖⅗⅘⅙⅚⅛⅜⅝⅞⁄₀₁₂₃₄₅₆₇₈₉⁰¹²³⁴⁵⁶⁷⁸⁹≈ ./")

# Composite klasmatograms decompose into atomic letters (from Unicode letter
# names: JE, DD, BB, ABB, EYYY are letter concatenations). A709-n "L2/L3/L4/L6"
# are palaeographic variants of L, NOT sums -- kept atomic and flagged.
COMPOSITES = {
    "JE": ["J", "E"],
    "DD": ["D", "D"],
    "BB": ["B", "B"],
    "ABB": ["A", "B", "B"],
    "EYYY": ["E", "Y", "Y", "Y"],
}
VARIANT_ATOMS = {"L2": "L2", "L3": "L3", "L4": "L4", "L6": "L6"}

TOTAL_LABELS = ("KU-RO",)
GRAND_TOTAL_LABELS = ("PO-TO-KU-RO",)
DEFICIT_LABELS = ("KI-RO",)

ANCHOR_TABLETS = [
    "HT9a", "HT13", "HT27a", "HT46a", "HT89", "HT94a", "HT100", "HT104",
    "HT123+124a", "HT123+124b", "PH(?)31a",
]


def _sign_letter(cp: int) -> str | None:
    """Map a codepoint to its klasmatogram letter via the Unicode name."""
    if cp not in FRAC_CP_RANGE:
        return None
    try:
        name = unicodedata.name(chr(cp))
    except ValueError:
        return None
    # "LINEAR A SIGN A707 J" -> ("A707", "J"); "LINEAR A SIGN A709-2 L2"
    parts = name.replace("LINEAR A SIGN ", "").split(" ", 1)
    return parts[1] if len(parts) == 2 else parts[0]


def _sign_a_number(cp: int) -> str | None:
    if cp not in FRAC_CP_RANGE:
        return None
    try:
        name = unicodedata.name(chr(cp))
    except ValueError:
        return None
    return name.replace("LINEAR A SIGN ", "").split(" ", 1)[0]


SIGN_BY_CP = {cp: _sign_letter(cp) for cp in FRAC_CP_RANGE if _sign_letter(cp)}
A_NUMBER_BY_LETTER = {
    _sign_letter(cp): _sign_a_number(cp) for cp in FRAC_CP_RANGE if _sign_letter(cp)
}


def load_corpus() -> dict:
    with require(DATA_DIR / "corpus.json", "corpus.json").open(encoding="utf-8") as fh:
        return json.load(fh)


def fraction_signs_in(glyph_token: str) -> list[str]:
    return [SIGN_BY_CP[ord(ch)] for ch in glyph_token if ord(ch) in SIGN_BY_CP]


def has_damage(glyph_token: str) -> bool:
    return any(ord(ch) == DAMAGE_CP for ch in glyph_token)


def is_integer_token(text: str) -> bool:
    return bool(text) and all(ch.isdigit() for ch in text)


def atoms_of(letter: str) -> list[str]:
    return COMPOSITES.get(letter, [letter])


# ---------------------------------------------------------------- inventory


def cmd_inventory(args: argparse.Namespace) -> None:
    corpus = load_corpus()
    census: dict[str, dict] = defaultdict(lambda: {
        "occurrences": 0, "inscriptions": set(), "sites": set(),
        "renderings": Counter(), "damage_adjacent": 0, "composite": False,
    })
    misaligned, unrecoverable = [], []

    for name, entry in corpus.items():
        tw = entry.get("transliteratedWords") or []
        words = entry.get("words") or []
        site = entry.get("site") or ""
        aligned = len(tw) == len(words)
        if not aligned:
            misaligned.append(name)
        stream = zip(tw, words) if aligned else ((None, w) for w in words)
        for rendered, glyph in stream:
            if not isinstance(glyph, str):
                continue
            letters = fraction_signs_in(glyph)
            if not letters:
                if rendered and any(ch in rendered for ch in "¼½¾⅓⅕⅙⅛⁄") \
                        and not is_integer_token(rendered):
                    unrecoverable.append({"inscription": name, "token": rendered})
                continue
            damaged = has_damage(glyph)
            for letter in letters:
                rec = census[letter]
                rec["occurrences"] += 1
                rec["inscriptions"].add(name)
                if site:
                    rec["sites"].add(site)
                if rendered is not None:
                    rec["renderings"][rendered] += 1
                if damaged:
                    rec["damage_adjacent"] += 1
                if letter in COMPOSITES:
                    rec["composite"] = True

    inconsistent = {
        letter: dict(rec["renderings"])
        for letter, rec in census.items()
        if len(rec["renderings"]) > 1
    }
    out = {
        "generated": "fraction_arithmetic.py inventory",
        "note": ("Raw identities from corpus `words` layer (Linear A Unicode); "
                 "`transliteratedWords` renderings are GORILA/Bennett-convention "
                 "hypotheses, not data. Damage marker U+1076B tracked separately."),
        "signs": {
            letter: {
                "a_number": A_NUMBER_BY_LETTER.get(letter),
                "occurrences": rec["occurrences"],
                "inscription_count": len(rec["inscriptions"]),
                "site_count": len(rec["sites"]),
                "sites": sorted(rec["sites"]),
                "renderings": dict(rec["renderings"].most_common()),
                "damage_adjacent": rec["damage_adjacent"],
                "composite": rec["composite"],
                "decomposition": COMPOSITES.get(letter),
            }
            for letter, rec in sorted(census.items(),
                                      key=lambda kv: -kv[1]["occurrences"])
        },
        "rendering_inconsistencies": inconsistent,
        "misaligned_inscriptions": sorted(misaligned),
        "unrecoverable_tokens": unrecoverable,
        "totals": {
            "distinct_signs": len(census),
            "total_occurrences": sum(r["occurrences"] for r in census.values()),
        },
    }
    args.out.mkdir(parents=True, exist_ok=True)
    path = args.out / "FRACTION_SIGN_INVENTORY.json"
    path.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {path}")
    print(f"{out['totals']['distinct_signs']} signs, "
          f"{out['totals']['total_occurrences']} occurrences; "
          f"{len(misaligned)} misaligned inscriptions; "
          f"{len(inconsistent)} signs with inconsistent renderings")


# ------------------------------------------------------------------ extract


def parse_lines(entry: dict) -> list[dict]:
    """Split an inscription's parallel token streams into structured lines."""
    tw = entry.get("transliteratedWords") or []
    words = entry.get("words") or []
    aligned = len(tw) == len(words)
    lines: list[dict] = []
    cur = {"labels": [], "int": None, "fracs": [], "damaged": False}

    def flush() -> None:
        nonlocal cur
        if cur["labels"] or cur["int"] is not None or cur["fracs"]:
            lines.append(cur)
        cur = {"labels": [], "int": None, "fracs": [], "damaged": False}

    for i, tok in enumerate(tw):
        glyph = words[i] if aligned and i < len(words) else ""
        if tok == "\n":
            flush()
            continue
        if tok in SEPARATOR_CHARS or tok == "\U00010101":
            continue
        if isinstance(glyph, str) and has_damage(glyph):
            cur["damaged"] = True
        letters = fraction_signs_in(glyph) if isinstance(glyph, str) else []
        if letters:
            cur["fracs"].extend(letters)
        elif is_integer_token(tok):
            cur["int"] = (cur["int"] or 0) + int(tok)
        elif tok == "𐝫":
            cur["damaged"] = True
        else:
            cur["labels"].append(tok)
    flush()

    for line in lines:
        label = " ".join(line["labels"])
        if any(g in label for g in GRAND_TOTAL_LABELS):
            line["kind"] = "GRAND_TOTAL"
        elif any(t in label for t in TOTAL_LABELS):
            line["kind"] = "TOTAL"
        elif any(d in label for d in DEFICIT_LABELS):
            line["kind"] = "DEFICIT"
        else:
            line["kind"] = "ENTRY"
    return lines


def auto_equations(lines: list[dict]) -> tuple[list[dict], bool]:
    """Build entries->TOTAL equations for simple tablets.

    Returns (equations, is_simple). A tablet is simple when it is one run of
    ENTRY lines followed by exactly one TOTAL line, with nothing after it.
    """
    total_idx = [i for i, l in enumerate(lines) if l["kind"] == "TOTAL"]
    if len(total_idx) != 1 or total_idx[0] != len(lines) - 1:
        return [], False
    entries = lines[: total_idx[0]]
    if any(l["kind"] != "ENTRY" for l in entries):
        return [], False
    eq = {
        "entries": [
            {"label": " ".join(l["labels"]), "int": l["int"] or 0,
             "fracs": l["fracs"], "damaged": l["damaged"]}
            for l in entries
        ],
        "total": {"label": " ".join(lines[-1]["labels"]),
                  "int": lines[-1]["int"] or 0,
                  "fracs": lines[-1]["fracs"],
                  "damaged": lines[-1]["damaged"]},
        "auto": True,
    }
    return [eq], True


def cmd_extract(args: argparse.Namespace) -> None:
    corpus = load_corpus()
    out = {"tablets": {}, "note": "Auto-built equations for simple tablets; "
           "complex tablets carry structured lines with needs_curation=true. "
           "Curated equations belong in EQUATION_CURATION.json."}
    for name in args.tablets or ANCHOR_TABLETS:
        entry = corpus.get(name)
        if not entry:
            print(f"!! {name} not in corpus", file=sys.stderr)
            continue
        lines = parse_lines(entry)
        equations, simple = auto_equations(lines)
        out["tablets"][name] = {
            "site": entry.get("site"),
            "lines": [
                {"kind": l["kind"], "label": " ".join(l["labels"]),
                 "int": l["int"], "fracs": l["fracs"], "damaged": l["damaged"]}
                for l in lines
            ],
            "equations": equations,
            "needs_curation": not simple,
        }
    args.out.mkdir(parents=True, exist_ok=True)
    path = args.out / "ANCHOR_TABLET_EQUATIONS.json"
    path.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    simple_n = sum(1 for t in out["tablets"].values() if not t["needs_curation"])
    print(f"Wrote {path}: {len(out['tablets'])} tablets, "
          f"{simple_n} auto-equated, {len(out['tablets']) - simple_n} need curation")


# -------------------------------------------------------------------- solve


def candidate_values() -> list[Fraction]:
    vals: set[Fraction] = set()
    for d in (2, 3, 4, 5, 6, 8, 10, 12, 16, 20, 24, 30, 32, 60):
        for n in range(1, d):
            f = Fraction(n, d)
            if f < 1 and (f.denominator <= 16 or f.numerator == 1):
                vals.add(f)
    return sorted(vals)


def equation_residual(eq: dict, assign: dict[str, Fraction]) -> Fraction | None:
    """Sum(entries) - total under an assignment; None if a var is unassigned."""
    total = Fraction(0)
    for side, sign in ((eq["entries"], 1), ([eq["total"]], -1)):
        for line in side:
            total += sign * Fraction(line["int"] or 0)
            for letter in line["fracs"]:
                for atom in atoms_of(letter):
                    if atom not in assign:
                        return None
                    total += sign * assign[atom]
    return total


def cmd_solve(args: argparse.Namespace) -> None:
    name = args.equations or "ANCHOR_TABLET_EQUATIONS.json"
    eq_path = require(args.out / name, f"{name} (write it with the extract subcommand)")
    data = json.loads(eq_path.read_text(encoding="utf-8"))
    curation_path = args.out / "EQUATION_CURATION.json"
    curated = {}
    if curation_path.exists():
        curated = json.loads(curation_path.read_text(encoding="utf-8")).get("tablets", {})

    equations: list[tuple[str, dict]] = []
    for name, tab in data["tablets"].items():
        eqs = curated.get(name, {}).get("equations") or tab["equations"]
        for eq in eqs:
            if eq.get("exclude"):
                continue
            if args.include_damaged or not (
                eq["total"].get("damaged")
                or any(l.get("damaged") for l in eq["entries"])
            ):
                equations.append((name, eq))

    variables = sorted({
        atom
        for _, eq in equations
        for line in eq["entries"] + [eq["total"]]
        for letter in line["fracs"]
        for atom in atoms_of(letter)
    })
    cands = candidate_values()
    print(f"{len(equations)} equations, variables: {variables}, "
          f"{len(cands)} candidate values each")

    var_count = Counter(
        atom for _, eq in equations
        for line in eq["entries"] + [eq["total"]]
        for letter in line["fracs"] for atom in atoms_of(letter)
    )
    tol = Fraction(args.tolerance).limit_denominator(120) if args.tolerance else Fraction(0)

    def eq_vars(eq: dict) -> set[str]:
        return {
            atom for line in eq["entries"] + [eq["total"]]
            for letter in line["fracs"] for atom in atoms_of(letter)
        }

    # Structured analytic enumeration instead of full DFS. Core variables
    # (appearing in >1 equation) are enumerated over the candidate grid;
    # satellite variables (appearing in exactly 1 equation) are solved
    # algebraically per equation. Each equation is precompiled to a linear
    # form: residual = base + sum(coeff[v] * value[v]).
    core = sorted([v for v in variables if var_count[v] > 1],
                  key=lambda v: -var_count[v])
    satellites = [v for v in variables if var_count[v] == 1]
    if len(core) > 3:
        sys.exit(f"solver assumes <=3 core variables, got {core}")

    def compile_eq(eq: dict) -> tuple[int, dict[str, int]]:
        base, coeffs = 0, Counter()
        for line in eq["entries"]:
            base += line["int"] or 0
            for letter in line["fracs"]:
                for atom in atoms_of(letter):
                    coeffs[atom] += 1
        base -= eq["total"]["int"] or 0
        for letter in eq["total"]["fracs"]:
            for atom in atoms_of(letter):
                coeffs[atom] -= 1
        return base, dict(coeffs)

    def eq_is_clean(eq: dict) -> bool:
        if eq["total"].get("damaged") or any(l.get("damaged") for l in eq["entries"]):
            return False
        return "assumes" not in (eq.get("note") or "")

    compiled = [(name, eq, *compile_eq(eq)) for name, eq in equations]
    cand_set = set(cands)

    # Hard structural constraint: every composite sign attested in the corpus
    # (JE, DD, BB...) writes a FRACTIONAL quantity -- if its atom-sum reached 1
    # the scribe would have written an integer. So sum(atoms) < 1 whenever all
    # atoms are assigned. This is arithmetic structure, not a value assumption.
    attested_composites = [
        (letter, atoms) for letter, atoms in COMPOSITES.items()
        if any(letter in line["fracs"]
               for _, eq in equations
               for line in eq["entries"] + [eq["total"]])
    ]

    def violates_composite_bound(assign: dict[str, Fraction]) -> bool:
        for _, atoms in attested_composites:
            if all(a in assign for a in atoms) and sum(assign[a] for a in atoms) >= 1:
                return True
        return False

    results: list[dict] = []
    for combo in product(cands, repeat=len(core)):
        assign = dict(zip(core, combo))
        if violates_composite_bound(assign):
            continue
        sat, vio, sat_clean, detail = 0, 0, 0, {}
        for name, eq, base, coeffs in compiled:
            key = f"{name}:{eq.get('id', '')}"
            free = sorted(v for v in coeffs if v not in assign and coeffs[v] != 0)
            known = base + sum(c * assign[v] for v, c in coeffs.items()
                               if v in assign)
            clean = eq_is_clean(eq)
            if not free:
                ok = abs(known) <= tol
                sat, vio = sat + ok, vio + (not ok)
                sat_clean += ok and clean
                detail[key] = {"status": "SAT" if ok else "VIOLATED",
                               "residual": str(known), "clean": clean}
                continue
            if len(free) == 1:
                v = free[0]
                exact = Fraction(-known, coeffs[v])
                feasible = [{v: str(exact)}] if exact in cand_set else []
            elif len(free) == 2:
                v1, v2 = free
                feasible = []
                for x in cands:
                    y = Fraction(-known - coeffs[v1] * x, coeffs[v2])
                    if y in cand_set:
                        feasible.append({v1: str(x), v2: str(y)})
            else:
                feasible = [{"note": f">{len(free)} free vars; not solved"}]
            ok = bool(feasible)
            sat, vio = sat + ok, vio + (not ok)
            sat_clean += ok and clean
            detail[key] = {
                "status": "FEASIBLE" if ok else "INFEASIBLE",
                "clean": clean,
                "free_vars": free,
                "solution_count": len(feasible),
                "sample_solutions": feasible[:8],
            }
        results.append({
            "core_assignment": {v: str(f) for v, f in assign.items()},
            "satisfied_clean": sat_clean,
            "satisfied": sat, "of": len(equations), "detail": detail,
        })

    # Lexicographic ranking: clean (undamaged, structurally certain) equations
    # first, damaged/assumption-dependent equations as tie-breakers only.
    results.sort(key=lambda r: (-r["satisfied_clean"], -r["satisfied"]))
    best_key = (results[0]["satisfied_clean"], results[0]["satisfied"]) if results else (-1, -1)
    best = [r for r in results
            if (r["satisfied_clean"], r["satisfied"]) == best_key]
    best_score = best_key

    # Which core values are pinned (unique across best)?
    pinned = {}
    for v in core:
        vals = {r["core_assignment"][v] for r in best}
        if len(vals) == 1:
            pinned[v] = next(iter(vals))

    out = {
        "protocol": "blind solve: no published value table is read",
        "method": ("analytic enumeration: core variables (in >1 equation) on the "
                   "candidate grid; satellite variables reported as per-equation "
                   "feasibility sets/relations, not enumerated assignments"),
        "equations_used": len(equations),
        "variables": variables,
        "core_variables": core,
        "satellite_variables": satellites,
        "variable_equation_counts": dict(var_count),
        "candidate_value_count": len(cands),
        "tolerance": str(tol),
        "scoring": "lexicographic (clean equations, then all equations)",
        "best_score": {"clean": best_score[0], "all": best_score[1]},
        "pinned_core_values": pinned,
        "co_optimal_core_assignments": len(best),
        "solutions": best[: args.max_solutions],
    }
    args.out.mkdir(parents=True, exist_ok=True)
    path = args.out / "BLIND_SOLVE_SOLUTION.json"
    path.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {path}: best clean={best_score[0]} all={best_score[1]} "
          f"of {len(equations)}; {len(best)} co-optimal; pinned={pinned}")


# -------------------------------------------------------------------- check


def segmented_equations(lines: list[dict]) -> list[dict]:
    """One equation per TOTAL line: the ENTRY lines since the last boundary.

    Boundaries are TOTAL / GRAND_TOTAL / DEFICIT lines. Header lines with no
    numeral and no fractions contribute 0 and are kept as labels. Trailing
    sections with no total are ignored (no equation to check).
    """
    equations, seg = [], []
    for line in lines:
        if line["kind"] == "ENTRY":
            seg.append(line)
        elif line["kind"] == "TOTAL":
            if seg:
                equations.append({
                    "entries": [
                        {"label": " ".join(l["labels"]), "int": l["int"] or 0,
                         "fracs": l["fracs"], "damaged": l["damaged"]}
                        for l in seg
                    ],
                    "total": {"label": " ".join(line["labels"]),
                              "int": line["int"] or 0,
                              "fracs": line["fracs"],
                              "damaged": line["damaged"]},
                })
            seg = []
        else:  # GRAND_TOTAL / DEFICIT reset the segment without an equation
            seg = []
    return equations


def cmd_check(args: argparse.Namespace) -> None:
    values = {
        k: Fraction(v) for k, v in
        json.loads(Path(args.values).read_text(encoding="utf-8")).items()
    }
    corpus = load_corpus()
    report = {"values": {k: str(v) for k, v in values.items()},
              "tablets": {}, "summary": Counter(), "failure_residuals": Counter()}
    for name, entry in corpus.items():
        lines = parse_lines(entry)
        equations = segmented_equations(lines)
        if not equations:
            continue
        has_fracs = any(
            l["fracs"] for eq in equations
            for l in eq["entries"] + [eq["total"]]
        )
        results = []
        for i, eq in enumerate(equations):
            damaged = eq["total"]["damaged"] or any(
                l["damaged"] for l in eq["entries"])
            missing = sorted({
                a for line in eq["entries"] + [eq["total"]]
                for letter in line["fracs"] for a in atoms_of(letter)
                if a not in values
            })
            if missing:
                results.append({"eq": i, "status": "UNASSIGNED_SIGN",
                                "missing": missing})
                continue
            # An entry line that lost its numeral to damage cannot be summed
            lost = [l["label"] for l in eq["entries"]
                    if l["int"] == 0 and not l["fracs"] and l["damaged"]]
            r = equation_residual(eq, values)
            status = "PASS" if r == 0 else "FAIL"
            if damaged or lost:
                status += "_DAMAGED"
            results.append({"eq": i, "status": status, "residual": str(r),
                            "total_label": eq["total"]["label"],
                            "entry_count": len(eq["entries"]),
                            "has_fractions": bool(has_fracs)})
            if status == "FAIL":
                report["failure_residuals"][str(r)] += 1
        statuses = [r["status"] for r in results]
        tablet_status = ("PASS" if all(s.startswith("PASS") for s in statuses)
                         else "MIXED" if any(s.startswith("PASS") for s in statuses)
                         else "FAIL")
        report["tablets"][name] = {
            "status": tablet_status, "fraction_bearing": has_fracs,
            "equations": results,
        }
        report["summary"][tablet_status] += 1
        for s in statuses:
            report["summary"][f"eq_{s.lower()}"] += 1
    report["summary"] = dict(report["summary"])
    report["failure_residuals"] = dict(report["failure_residuals"].most_common())
    args.out.mkdir(parents=True, exist_ok=True)
    path = args.out / "CORPUS_CONSISTENCY_REPORT.json"
    path.write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {path}: {report['summary']}")


# --------------------------------------------------------------------- main


def main() -> int:
    try:
        _run()
    except NotInCheckout as e:
        print(f"stopped: {e}", file=sys.stderr)
        return 2
    return 0


def _run() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT,
                    help="folder the subcommands read and write their JSON in")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("inventory")
    p_ex = sub.add_parser("extract")
    p_ex.add_argument("--tablets", nargs="*")
    p_so = sub.add_parser("solve")
    p_so.add_argument("--equations")
    p_so.add_argument("--tolerance", default=0, type=str)
    p_so.add_argument("--include-damaged", action="store_true")
    p_so.add_argument("--max-solutions", type=int, default=20)
    p_ch = sub.add_parser("check")
    p_ch.add_argument("--values", required=True)
    args = ap.parse_args()
    {"inventory": cmd_inventory, "extract": cmd_extract,
     "solve": cmd_solve, "check": cmd_check}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
