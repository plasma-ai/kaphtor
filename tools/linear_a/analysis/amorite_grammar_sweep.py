#!/usr/bin/env python3
"""Grammar-driven Amorite sweep of the Linear A onomasticon.

Where amorite_template_match.py finds edit-distance lookalikes, this script
applies the *rules* of Huffmon's Amorite Personal Names in the Mari Texts
(APNM) as falsifiable corpus queries — each subcommand is one rule:

  r1  ya-classes    JA-initial tokens sorted into Yaqtal/Yaqtul/Yaqtil by
                    theme vowel; second-element lookup           (APNM ch. III)
  r2  frozen-u      -U finals whose last element is a dual-role appellative
                    (the -Cu-u frozen nominative class)          (APNM 104-15)
  r3  weak-e        -E finals vs the III-weak element class      (APNM 116)
  r4  hypocoristic  -JA/-NA/-NE/-TU/-TA-NA finals on attested stems
                                                                 (APNM ch. VII)
  r5  interrogative A-JA/I-JA/A-I openers vs *ayya "where?"      (APNM 103)
  r6  genitive      KA/KI "like" + DN; ZU "the one of"           (APNM 102,121)
  r7  position      positional-grammar audit of semitic/amorite-affiliated
                    tokens (initial-only vs final-only elements) (APNM ch. IV)

Report-only: never writes affiliations. Every rule reports its base rate
(tokens with the trigger shape) so hits are read against chance.

Usage:
  uv run tools/linear_a/analysis/amorite_grammar_sweep.py all [--json]
  uv run tools/linear_a/analysis/amorite_grammar_sweep.py r2 [--json]
  uv run tools/linear_a/analysis/amorite_grammar_sweep.py --selftest
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    __package__ = "tools.linear_a.analysis"

from ...core.skeleton import extract_full
from ...paths import CONTACT_DATA, LINEAR_A_DATA, NotInCheckout, require

# --- element sets from APNM (guttural-dropped LA forms) ---

# APNM p. 101: appellatives that also serve as theophorous elements and take
# the frozen nominative -Cu-u when final. Keys are Linear A equivalence
# forms (gutturals dropped), values the Amorite element for the report.
DUAL_ROLE_FINALS = {
    "ab": "ʾab- 'father'", "abu": "ʾab-", "a": "ʾaḫ- 'brother'",
    "am": "ʿamm- 'paternal uncle'", "amu": "ʿamm-",
    "sum": "šum- 'name/posterity'", "sumu": "šum-", "samu": "šam-",
    "al": "ḫāl- 'maternal uncle'", "alu": "ḫāl-",
    "dad": "dād- 'beloved/uncle'", "dadu": "dād-",
    "atn": "ḫatn- 'son-in-law'", "asd": "ʾasd- 'warrior(?)'",
    "sitr": "sitr- 'protection'", "sur": "ṣūr- 'rock'",
    "tal": "tal-", "yad": "yaḫad 'unique'", "da": "dāʿ 'knowing' (√ydʿ)",
}

# APNM p. 116 (+ n. 98 Bauer): III-weak elements spelled -Ci/e-e when final.
WEAK_E_FINALS = {
    "sari": "śarī- (√śry 'contend/prince?')", "sare": "śarī-",
    "rami": "rāmī- (√rwm/rmy 'high')", "rame": "rāmī-",
    "rai": "rāḫī-/raḫī- (I-la-ra-ḫi-e)", "rae": "rāḫī-",
    "dari": "-da-ri-e (Bauer I-ṣi/zi-da-ri-e)", "dare": "-da-ri-e",
    "da": "dāʿē? (III-guttural via drop — flag, don't assume)",
}

# APNM ch. VII hypocoristic suffixes → Linear A final syllables.
HYPO_SUFFIXES = {
    "JA": ("-iya", "masculine at Mari (A-bi-ya, Si-it-ri-ya)"),
    "NA": ("-ān", "masculine (Ba-aḫ-la-an)"),
    "NE": ("-ān(i)", "masculine, oblique?"),
    "TU": ("-atum", "feminine (Ba-aḫ-la-tum); caritative on masc."),
}

# APNM ch. IV/V positional sets (LA equivalence forms).
INITIAL_ONLY = {"abd", "mut", "bin", "bun", "zu", "samsi", "zikr", "zimr",
                "sidq", "niqm", "azr", "aqb", "naps", "ikbs", "milk", "nium"}
FINAL_ONLY = {"malik", "salim", "sari", "rame", "epu", "esu", "samas",
              "bal", "rapi", "nasi", "tanu", "samu", "saduq"}

THEOPHORIC_LA = {"adu", "asara", "dagan", "ilu", "il", "ada", "era", "ra"}

VOWELS = "aeiou"


def load_entries():
    path = require(LINEAR_A_DATA / "onomasticon.json", "onomasticon.json")
    return json.loads(path.read_text(encoding="utf-8"))["entries"]


def load_amorite_index():
    path = require(CONTACT_DATA / "amorite_onomasticon.index.json", "amorite_onomasticon.index.json")
    return json.loads(path.read_text(encoding="utf-8"))["index"]


def syls(token: str) -> list[str]:
    return token.split("-")


def cv(token: str) -> list[tuple[str, str]]:
    """(consonant, vowel) per syllable; '' consonant for pure vowels."""
    out = []
    for d in extract_full(token):
        c, v = d[0], d[1]
        out.append((c or "", v or ""))
    return out


def flat(token: str) -> str:
    return "".join(c + v for c, v in cv(token))


def name_tokens(entries):
    return [e for e in entries
            if e.get("type") in ("personal_name", "theonym", "toponym",
                                 "toponym_gentilic", "unknown", None)
            or e.get("type_confidence") in ("SPECULATIVE",)]


def fmt(rows, headers):
    if not rows:
        return "  (no hits)"
    w = [max(len(str(r[i])) for r in rows + [headers]) for i in range(len(headers))]
    lines = ["  " + "  ".join(str(h).ljust(w[i]) for i, h in enumerate(headers))]
    for r in rows:
        lines.append("  " + "  ".join(str(c).ljust(w[i]) for i, c in enumerate(r)))
    return "\n".join(lines)


# --- rules ---

def r1_ya_classes(entries, index):
    """JA-initial tokens → imperfect theme-vowel classes."""
    classes = {"a": "yaqtal", "u": "yaqtul", "i": "yaqtil", "e": "yaqtil(i/e)",
               "o": "yaqtul(u/o)"}
    hits, base = [], 0
    for e in entries:
        s = syls(e["token"])
        if not s or s[0] != "JA" or len(s) < 2:
            continue
        base += 1
        parts = cv(e["token"])
        if len(parts) < 2 or not parts[1][1]:
            continue
        theme = parts[1][1]
        remainder = "".join(c + v for c, v in parts[1:])
        # is the post-verbal remainder tail a known element?
        tail_hits = [k for k in list(DUAL_ROLE_FINALS) + list(THEOPHORIC_LA)
                     if len(k) >= 2 and remainder.endswith(k)]
        hits.append((e["token"], classes.get(theme, "?"), theme,
                     ",".join(tail_hits) or "-", e.get("affiliation", "?"),
                     e.get("frequency", "")))
    return {"rule": "R1 ya-classes (APNM ch. III; no Barth-Ginsberg at Mari)",
            "base": base, "hits": hits,
            "headers": ("token", "class", "theme", "element-tail",
                        "curr-affil", "freq")}


def r2_frozen_u(entries, index):
    """-U finals whose final element is a dual-role appellative."""
    hits, base = [], 0
    for e in entries:
        f = flat(e["token"])
        if not f or not f.endswith("u"):
            continue
        base += 1
        body = f[:-1] if f[-1] == "u" and len(f) > 1 else f
        matched = []
        for k, gloss in DUAL_ROLE_FINALS.items():
            if body.endswith(k) and len(k) >= 2:
                matched.append((k, gloss))
        if matched:
            k, gloss = max(matched, key=lambda m: len(m[0]))
            opener = body[: len(body) - len(k)]
            hits.append((e["token"], opener or "-", k, gloss,
                         e.get("affiliation", "?"), e.get("frequency", "")))
    return {"rule": "R2 frozen nominative -Ū on final elements (APNM 104-15)",
            "base": base, "hits": hits,
            "headers": ("token", "opener", "final-el", "element",
                        "curr-affil", "freq")}


def r3_weak_e(entries, index):
    """-E finals vs the III-weak element class."""
    hits, base = [], 0
    for e in entries:
        f = flat(e["token"])
        if not f or not f.endswith("e"):
            continue
        base += 1
        body = f[:-1]
        for k, gloss in sorted(WEAK_E_FINALS.items(), key=lambda x: -len(x[0])):
            if body.endswith(k):
                opener = body[: len(body) - len(k)]
                hits.append((e["token"], opener or "-", k, gloss,
                             e.get("affiliation", "?"), e.get("frequency", "")))
                break
    return {"rule": "R3 III-weak -Ci/e-e finals (APNM 116)",
            "base": base, "hits": hits,
            "headers": ("token", "opener", "final-el", "element",
                        "curr-affil", "freq")}


def r4_hypocoristics(entries, index):
    """Hypocoristic suffix finals on stems attested elsewhere."""
    stems = {flat(e["token"]): e["token"] for e in entries}
    hits, base = [], 0
    for e in entries:
        s = syls(e["token"])
        if len(s) < 2 or s[-1] not in HYPO_SUFFIXES:
            continue
        base += 1
        suffix, note = HYPO_SUFFIXES[s[-1]]
        stem_tok = "-".join(s[:-1])
        stem_flat = flat(stem_tok)
        attested = stems.get(stem_flat) if stem_flat in stems else None
        skel = "".join(c for c in stem_flat if c not in VOWELS)
        in_amorite = (stem_flat in index
                      or stem_flat.rstrip("aeiou") in index
                      or (len(skel) >= 2 and skel in index))
        if attested or in_amorite:
            hits.append((e["token"], suffix, stem_tok,
                         attested or "-", "yes" if in_amorite else "-",
                         note.split("(")[0].strip(),
                         e.get("affiliation", "?")))
    return {"rule": "R4 hypocoristic suffixes on attested stems (APNM ch. VII)",
            "base": base, "hits": hits,
            "headers": ("token", "suffix", "stem", "stem-token", "amorite-el",
                        "gender-prior", "curr-affil")}


def r5_interrogatives(entries, index):
    """*ayya 'where is—?' and *manna 'who?' openers."""
    hits, base = [], 0
    for e in entries:
        s = syls(e["token"])
        head2 = "-".join(s[:2])
        f = flat(e["token"])
        trig = None
        if head2 in ("A-JA", "I-JA", "A-I") and len(s) >= 3:
            trig = "*ayya 'where?'"
        elif f.startswith("mana") and len(s) >= 3:
            trig = "*manna 'who?'"
        if not trig:
            continue
        base += 1
        rest = f[len("".join(x for p in cv("-".join(s[:2])) for x in p)):] \
            if trig.startswith("*ayya") else f[4:]
        tail = [k for k in list(DUAL_ROLE_FINALS) + list(THEOPHORIC_LA)
                if len(k) >= 2 and rest.endswith(k)]
        hits.append((e["token"], trig, rest or "-", ",".join(tail) or "-",
                     e.get("affiliation", "?"), e.get("frequency", "")))
    return {"rule": "R5 interrogative sentence names (APNM 102-03)",
            "base": base, "hits": hits,
            "headers": ("token", "interrogative", "subject", "element-tail",
                        "curr-affil", "freq")}


def r6_genitive(entries, index):
    """ka/ki 'like'+DN comparisons; zū 'the one of' compounds."""
    hits, base = [], 0
    dn_flats = {flat(e["token"]): e["token"] for e in entries
                if e.get("type") == "theonym"}
    for e in entries:
        s = syls(e["token"])
        if len(s) < 2 or s[0] not in ("KA", "KI", "ZU"):
            continue
        base += 1
        rest_tok = "-".join(s[1:])
        rest = flat(rest_tok)
        kind = ("zū 'the one of' (APNM 121)" if s[0] == "ZU"
                else "ka/ki 'like' (APNM 102)")
        dn = dn_flats.get(rest)
        in_amorite = rest in index or rest.rstrip("aeiou") in index
        if dn or in_amorite:
            hits.append((e["token"], kind, rest_tok, dn or "-",
                         "yes" if in_amorite else "-",
                         e.get("affiliation", "?")))
    return {"rule": "R6 preposition/demonstrative compounds (APNM 102, 121)",
            "base": base, "hits": hits,
            "headers": ("token", "type", "rectum", "corpus-DN", "amorite-el",
                        "curr-affil")}


def r7_position_audit(entries, index):
    """Positional-grammar audit of semitic/amorite-affiliated tokens."""
    hits, base = [], 0
    for e in entries:
        if e.get("affiliation") not in ("semitic", "amorite"):
            continue
        f = flat(e["token"])
        if not f:
            continue
        base += 1
        problems = []
        for el in INITIAL_ONLY:
            if len(el) >= 3 and f.endswith(el):
                problems.append(f"initial-only '{el}' in final position")
        for el in FINAL_ONLY:
            if len(el) >= 3 and f.startswith(el) and len(f) > len(el) + 1:
                problems.append(f"final-only '{el}' in initial position")
        if problems:
            hits.append((e["token"], "; ".join(problems),
                         e.get("affiliation_confidence", "?"),
                         (e.get("reading") or "")[:24]))
    return {"rule": "R7 positional-grammar audit (violations = negative evidence)",
            "base": base, "hits": hits,
            "headers": ("token", "violation", "affil-conf", "reading")}


RULES = {"r1": r1_ya_classes, "r2": r2_frozen_u, "r3": r3_weak_e,
         "r4": r4_hypocoristics, "r5": r5_interrogatives,
         "r6": r6_genitive, "r7": r7_position_audit}


def selftest(results) -> int:
    """Positive controls: known readings the rules must rediscover."""
    checks = [
        ("r2", "A-MI-DA-U", "R2 must rediscover A-MI-DA-U"),
        ("r3", "SA-MI-DA-E", "R3 must rediscover SA-MI-DA-E"),
        ("r4", "DA-NA-TU", "R4 must surface DA-NA-TU (-atum feminine)"),
    ]
    failures = []
    for rule, token, msg in checks:
        toks = {h[0] for h in results[rule]["hits"]}
        if token not in toks:
            failures.append(msg)
    for f in failures:
        print("SELFTEST FAIL:", f)
    if not failures:
        print("selftest: 3/3 positive controls pass")
    return 1 if failures else 0


def main() -> int:
    try:
        return _run()
    except NotInCheckout as e:
        print(f"stopped: {e}", file=sys.stderr)
        return 2


def _run() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("rule", nargs="?", default="all",
                    choices=list(RULES) + ["all"])
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    entries = name_tokens(load_entries())
    index = load_amorite_index()
    todo = list(RULES) if args.rule == "all" or args.selftest else [args.rule]
    results = {r: RULES[r](entries, index) for r in todo}

    if args.selftest:
        return selftest(results)
    if args.json:
        print(json.dumps({r: {k: v for k, v in res.items() if k != "headers"}
                          for r, res in results.items()},
                         ensure_ascii=False, indent=1, default=list))
        return 0
    total = len(entries)
    for res in results.values():
        print(f"\n== {res['rule']}")
        print(f"   trigger-shape base rate: {res['base']}/{total} tokens; "
              f"hits: {len(res['hits'])}")
        print(fmt(res["hits"], res["headers"]))
    print("\n⚠ Report only — readings follow the Gordon-di Mino decipherment; "
          "hits are candidates for adjudication, not writes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
