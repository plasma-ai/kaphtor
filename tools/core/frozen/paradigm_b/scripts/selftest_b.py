#!/usr/bin/env python3
"""Option B selftest (PROTOCOL-B §8). Exit 1 on any failure.

B1 covers checks 1 (own-language parse ≥ 90%), 2 (leakage matrix), 3
(blindness rejection), 4 (pair alignment) and 6 (parity). B3 adds the rest of
check 4 (hand-computed pairs, slot 7, empty residues, identity exclusion),
check 5 (D2) and check 7 (timing; skipped with --fast).

Run: IOZA2_PREFREEZE=1 uv run python scripts/selftest_b.py
Attribution: di Mino.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import paths  # noqa: E402
from common import paradigm  # noqa: E402
import render_la  # noqa: E402

FAILS: list[str] = []
OWN_THRESHOLD = 0.90
LEAK_FLAG = 0.70


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  [{'OK' if ok else 'FAIL'}] {name}{('  ' + detail) if detail else ''}")
    if not ok:
        FAILS.append(name)


def morph_segments(inv: paradigm.Inventory, ids: list[str]) -> list[paradigm.Segment]:
    out: list[paradigm.Segment] = []
    for mid in ids:
        out.extend(inv.morpheme(mid).phonemic)
    return out


def stem_segments(stem: str, arm: str) -> list[paradigm.Segment]:
    return paradigm.segs(stem, arm)


def score_forms(inv: paradigm.Inventory, src: paradigm.Inventory, forms: list[dict], *, strict: bool = True):
    """Explain each attested form of ``src``'s language with ``inv``.
    Returns (explained, total, failures). The form's segmentation comes from
    ``src`` (the inventory the form was written against); rendering uses
    ``src``'s arm rules, so the residues are the language's own spelling."""
    n = ok = 0
    failures = []
    for f in forms:
        pre = morph_segments(src, f["prefixes"])
        stem = stem_segments(f["stem"], src.arm)
        suf = morph_segments(src, f["suffixes"])
        side, signs = paradigm.form_sides(pre, stem, suf, src.arm)
        exp = paradigm.explain_side(side, inv, strict=strict)
        n += 1
        if exp is not None and exp.cost == 0:
            ok += 1
        else:
            failures.append((f["id"], "-".join(signs), side.prefix, side.boundary, side.suffix,
                             None if exp is None else exp.cost))
    return ok, n, failures


def main() -> int:
    print("1. own-language parse (base inventory, strict vowels)")
    invs = {arm: paradigm.load_inventory(arm, "base") for arm in paradigm.ARMS}
    raws = {arm: paths.load_data(f"paradigm/{arm}.json") for arm in paradigm.ARMS}
    forms_by_lang: dict[str, tuple[str, list[dict]]] = {}
    for arm in ("cs", "luwian", "hurrian", "egyptian"):
        for f in raws[arm]["attested_forms"]:
            forms_by_lang.setdefault(f["language"], (arm, []))[1].append(f)
    own_rates = {}
    for arm in paradigm.ARMS:
        langs = raws[arm]["languages"]
        forms = [f for lang in langs for f in forms_by_lang.get(lang, (arm, []))[1]]
        src = invs["cs"] if arm in ("cs", "nws_floor") else invs[arm]
        ok, n, failures = score_forms(invs[arm], src, forms)
        rate = ok / n if n else float("nan")
        own_rates[arm] = rate
        check(f"{arm}: {ok}/{n} attested forms explained at cost 0", rate >= OWN_THRESHOLD, f"{rate:.1%}")
        for fid, signs, pre, b, suf, cost in failures:
            print(f"        miss {fid}: {signs}  prefix={list(pre)} boundary={b} suffix={list(suf)} cost={cost}")
    # with-Sabaic variant on the Sabaic forms (reported)
    inv_sab = paradigm.load_inventory("cs", "base", with_sabaic=True)
    sab_forms = forms_by_lang.get("sabaic", ("cs", []))[1]
    ok, n, failures = score_forms(inv_sab, inv_sab, sab_forms)
    print(f"  [INFO] cs with Sabaic: {ok}/{n} Sabaic forms explained")
    for fid, signs, pre, b, suf, cost in failures:
        print(f"        miss {fid}: {signs}  prefix={list(pre)} boundary={b} suffix={list(suf)} cost={cost}")

    print("2. cross-language leakage matrix (rows: inventory; columns: forms of language)")
    langs = [l for l in ("ugaritic", "hebrew", "arabic", "safaitic", "luwian", "hurrian", "egyptian") if l in forms_by_lang]
    header = "  {:<10}".format("inv\\forms") + "".join(f"{l[:8]:>10}" for l in langs)
    print(header)
    leak: dict[str, dict[str, float]] = {}
    for arm in paradigm.ARMS:
        row = {}
        for lang in langs:
            src_arm, forms = forms_by_lang[lang]
            src = invs[src_arm]
            ok, n, _ = score_forms(invs[arm], src, forms)
            row[lang] = ok / n if n else float("nan")
        leak[arm] = row
        print("  {:<10}".format(arm) + "".join(f"{row[l]:>10.2f}" for l in langs))
    flags = []
    semitic = {"ugaritic", "hebrew", "arabic", "safaitic", "sabaic"}
    for arm, row in leak.items():
        own = semitic if arm in ("cs", "nws_floor") else set(raws[arm]["languages"])
        for lang, rate in row.items():
            n = len(forms_by_lang[lang][1])
            if lang not in own and n >= 10 and rate >= LEAK_FLAG:
                flags.append(f"{arm} explains {rate:.0%} of {lang} forms (n={n})")
    print("  [INFO] red-flag 2 (≥ 70% of a foreign language's forms): " + ("; ".join(flags) if flags else "none"))

    print("3. blindness rule")
    import build_paradigm as bp  # noqa: E402
    needles = bp.family_needles()
    bad = [dict(id="x_bad", function="mirrors the Linear A word A-TA-I-*301-WA-JA", citations=["none"], note=None)]
    try:
        bp.check_blind("cs", bad, [], needles)
        check("target-citing entry rejected", False)
    except SystemExit:
        check("target-citing entry rejected", True)
    bad2 = [dict(id="x_bad2", function="an ordinary morpheme", citations=["Ya Diktu §6.1"], note=None)]
    try:
        bp.check_blind("cs", bad2, [], needles)
        check("paper-citing entry rejected", False)
    except SystemExit:
        check("paper-citing entry rejected", True)
    for arm in paradigm.ARMS:
        cites = " ".join(" ".join(m["citations"]) + " " + m["function"] for m in raws[arm]["morphemes"]).lower()
        check(f"{arm} inventory carries no forbidden string", not any(x in cites for x in bp.FORBIDDEN))

    print("4. pair alignment (synthetic forms)")
    al = paradigm.align_pair("KA-RA-MU-TE", "KA-RA-MU-TA")
    check("boundary vowel alternation detected", al is not None and al.run_len == 3 and al.boundary_consonant == "t"
          and al.f.boundary == "e" and al.g.boundary == "a" and al.f.suffix == () and al.g.suffix == ())
    al = paradigm.align_pair("KI-PA", "KI-PA-NA-MA")
    check("suffix residue after an identical run", al is not None and al.run_len == 2
          and al.g.suffix == (("n", "a"), ("m", "a")) and al.f.suffix == () and al.f.word_final_after_run)
    al = paradigm.align_pair("A-TA-I-*301-WA-JA", "TA-NA-I-*301-U-TI-NU")
    check("prefix and suffix residues both sides", al is not None and al.run_len == 2
          and al.f.prefix == ((None, "a"), ("t", "a")) and al.g.prefix == (("t", "a"), ("n", "a"))
          and al.f.suffix == (("w", "a"), ("y", "a")) and al.g.suffix == ((None, "u"), ("t", "i"), ("n", "u")))
    check("homographic signs compare equal (*301 = NA)", paradigm.align_pair("KI-*301", "KI-NA") is not None
          and paradigm.align_pair("KI-*301", "KI-NA").run_len == 2)
    check("no common run ⇒ unscorable", paradigm.align_pair("O-SU-QA-RE", "TU-RU-SA") is None)
    check("one-sign run ⇒ unscorable", paradigm.align_pair("KA-RA", "KA-TI") is None)
    check("empty residues are explained by every inventory",
          all(paradigm.explain_side(paradigm.Side((), None, (), "a", "a", True), inv) is not None for inv in invs.values()))

    print("5. explanation mechanics (synthetic residues)")
    cs = invs["cs"]
    s = paradigm.Side(((None, "a"), ("t", "a")), None, (), "i", "a", True)
    e = paradigm.explain_side(s, cs)
    check("A-TA prefix generated at cost 0 under cs (ʾa-/ha- + ta-)", e is not None and e.cost == 0
          and "ta" in "".join(e.prefix_chain), str(e))
    check("A-TA prefix not generated by luwian/hurrian/egyptian",
          all(paradigm.explain_side(s, invs[a]) is None for a in ("luwian", "hurrian", "egyptian")))
    s = paradigm.Side((), None, ((None, "u"), ("t", "i"), ("n", "u")), "a", "e", False)
    e = paradigm.explain_side(s, cs)
    check("U-TI-NU generated at cost 0 by cs base (attested chain, e.g. -ūt + -i + nunation)",
          e is not None and e.cost == 0, str(e))
    ext = paradigm.load_inventory("cs", "ext")
    e2 = paradigm.explain_side(s, ext)
    check("ext never costs more than base on the same residue", e2 is not None and e2.cost <= e.cost)
    s = paradigm.Side((), "u", (("t", "i"), ("n", "u")), "a", "a", False)
    e = paradigm.explain_side(s, cs)
    print(f"        [INFO] boundary u + TI-NU under cs base: {e}")
    print("        [INFO] the priced morphemes (archaic *-t- object, energic after object) are surface-identical "
          "to attested 2fs -ti / 2ms -ta and enclitic -n: the ext ablation cannot differ from base on A (recorded)")
    s = paradigm.Side((), "a", (("m", "a"),), "a", "a", False)
    e = paradigm.explain_side(s, cs)
    check("-RA-MA (boundary a + MA): accusative + mimation or enclitic under cs", e is not None and e.cost == 0, str(e))
    s = paradigm.Side((), "e", (("m", "a"),), "a", "a", False)
    e = paradigm.explain_side(s, cs)
    check("-RE-MA (boundary e + MA) under cs: dual oblique -ē + mimation", e is not None, str(e))
    s = paradigm.Side((), "u", (), "a", "a", True)
    check("word-final boundary u explained (nominative or dead vowel)", paradigm.explain_side(s, cs) is not None)
    s = paradigm.Side((), "o", (), "a", "a", True)
    check("word-final boundary o not explained under cs (no o-morpheme, not a dead vowel)", paradigm.explain_side(s, cs) is None)
    check("… but explained under hurrian (valence -o)", paradigm.explain_side(s, invs["hurrian"]) is not None)
    check("cons mode ignores the vowel", paradigm.explain_side(s, cs, strict=False) is not None)

    print("6. parity (PROTOCOL-B §4.2)")
    cs_c = raws["cs"]["counts"]
    for arm in ("luwian", "hurrian", "egyptian"):
        c = raws[arm]["counts"]
        r1 = max(cs_c["distinct_headline"], c["distinct_headline"]) / min(cs_c["distinct_headline"], c["distinct_headline"])
        r2 = max(cs_c["one_sign_headline"], c["one_sign_headline"]) / min(cs_c["one_sign_headline"], c["one_sign_headline"])
        check(f"{arm} distinct realizations within 1.5× of cs", r1 <= 1.5, f"{c['distinct_headline']} vs {cs_c['distinct_headline']} ({r1:.2f})")
        check(f"{arm} one-sign realizations within the 2.0 cap", r2 <= 2.0, f"{c['one_sign_headline']} vs {cs_c['one_sign_headline']} ({r2:.2f})")
    check("nws_floor ⊂ cs", set(m["id"] for m in raws["nws_floor"]["morphemes"]) <= set(m["id"] for m in raws["cs"]["morphemes"]))
    check("priced morphemes absent from base, present in ext",
          not any(m.cost > 0 for m in cs.prefixes + cs.suffixes) and any(m.cost > 0 for m in ext.prefixes + ext.suffixes))

    print("4b. pairs and the statistic (PROTOCOL-B §8 check 4, B3)")
    def res(f, g):
        return paradigm.align_pair(f, g)
    al = res("SA-SA-RA-ME", "JA-SA-SA-RA-ME")
    check("SA-SA-RA-ME / JA-SA-SA-RA-ME: run 4, prefix JA on g only", al is not None and al.run_len == 4
          and al.f.prefix == () and al.g.prefix == (("y", "a"),) and al.f.suffix == al.g.suffix == ())
    al = res("I-PI", "I-PI-NA-MA")
    check("I-PI / I-PI-NA-MA: run 2, suffix NA-MA", al is not None and al.run_len == 2
          and al.f.suffix == () and al.g.suffix == (("n", "a"), ("m", "a")))
    al = res("U-NA-KA-NA-SI", "U-NA-RU-KA-NA-TI")
    check("U-NA-KA-NA-SI / U-NA-RU-KA-NA-TI: leftmost of two 2-runs (U-NA), no boundary",
          al is not None and al.run_len == 2 and al.boundary_consonant is None
          and al.f.suffix == (("k", "a"), ("n", "a"), ("s", "i"))
          and al.g.suffix == (("r", "u"), ("k", "a"), ("n", "a"), ("t", "i")))
    al = res("SI-RU-TE", "SI-RU")
    check("SI-RU-TE / SI-RU: run 2, suffix TE", al is not None and al.f.suffix == (("t", "e"),) and al.g.suffix == ())
    al = res("JA-SA-SA-RA-ME", "JA-SA-SA-RA-MA")
    check("JA-SA-SA-RA-ME / -MA: run 4, boundary m e/a", al is not None and al.run_len == 4
          and al.boundary_consonant == "m" and (al.f.boundary, al.g.boundary) == ("e", "a"))
    fam = __import__("common.nulls", fromlist=["x"]).observed_family()
    idx = paradigm.family_slot_index()
    ftoks = paradigm.family_tokens(fam, idx)
    check("family slot tokens: 61 (KO Za 1 slot 2 carries three)", len(ftoks) == 61, str(len(ftoks)))
    s7 = paradigm.score([t for t in ftoks if t.slot == "7"], {})
    check("slot 7 unscorable in every fold", s7["scorable"] == 0)
    T = paradigm.Token
    toks = [T("u1", "u1", "s", ("TA", "KI", "PA")), T("u2", "u2", "s", ("SA", "KI", "PA", "NA")),
            T("u3", "u3", "s", ("KI", "PA", "NA"))]
    r = paradigm.score(toks, {}, [frozenset({"u3"})])
    check("empty prefix residue counts as in the training inventory", r["scorable"] == 1 and r["A"]["free"] == 1.0, str(r))
    ps = paradigm.prediction_set(("KI", "NA", "TA"), [("KI", "*301", "TA"), ("KI", "NA", "TA", "RE"), ("PA", "TA")])
    check("identical form (CV level, *301 = NA) leaves the prediction set; the aligned other form stays",
          len(ps) == 1 and ps[0].g.suffix == (("r", "e"),), str(ps))
    r = paradigm.score([T("u1", "u1", "s", ("KI", "PA")), T("u2", "u2", "s", ("KI", "PA"))], {})
    check("a token whose only match is identical is unscorable", r["scorable"] == 0, str(r))
    toks = [T("a", "A", "s", ("KA", "RA", "MU", "TE")), T("b", "B", "s", ("KA", "RA", "MU", "TA")),
            T("c", "C", "s", ("KA", "RA", "MU", "TI")), T("d", "D", "s", ("KA", "RA", "MU"))]
    r = paradigm.score(toks, {"cs": cs, "luwian": invs["luwian"], "hurrian": invs["hurrian"],
                              "egyptian": invs["egyptian"]}, detail=True)
    check("leave-one-group-out: one fold per group, every token scorable", r["folds_scored"] == 4 and r["scorable"] == 4, str(r["folds"]))
    check("Δ = A_cs − max(rivals)", abs(r["delta"] - (r["A"]["cs"] - max(r["A"][a] for a in ("luwian", "hurrian", "egyptian")))) < 1e-12)

    print("5'. null D2 (PROTOCOL-B §8 check 5)")
    import numpy as np  # noqa: E402
    from common import nulls  # noqa: E402
    model = nulls.SignModel(nulls.corpus_syllabic_words({i.id for i in fam}))
    d2p = paradigm.d2_params(ftoks)
    def draw(seed, scale=1):
        rng = np.random.default_rng(seed)
        P, S = nulls.draw_affix_inventory(model, rng, scale * d2p["k_prefix"], scale * d2p["k_suffix"],
                                          d2p["prefix_lengths"], d2p["suffix_lengths"])
        return P, S, nulls.null_d2(model, rng, fam, P, S, d2p["mode_p"])
    P, S, rep = draw(11)
    check("inventory sizes k, k' as observed", len(P) == d2p["k_prefix"] and len(S) == d2p["k_suffix"]
          and len(set(P)) == len(P) and len(set(S)) == len(S), f"{len(P)}, {len(S)}")
    P2, S2, _ = draw(11, 2)
    check("D2×2 doubles both sizes", len(P2) == 2 * d2p["k_prefix"] and len(S2) == 2 * d2p["k_suffix"])
    check("slot matrix preserved", nulls.family_slot_matrix(rep) == nulls.family_slot_matrix(fam)
          and len(paradigm.family_tokens(rep, idx)) == len(ftoks))
    occ = __import__("collections").Counter(w for i in fam for w in i.words)
    bad = []
    for o, n in zip(fam, rep):
        for w, x in zip(o.words, n.words):
            if occ[w] == 1 and len(x) != len(w):
                bad.append((w, x))
            if len(x) != len(w) and not any(x[:len(p)] == p and x[len(x) - len(s):] == s and len(x) - len(p) - len(s) == len(w)
                                             for p in [()] + P for s in [()] + S):
                bad.append((w, x))
    check("every varied form is type form + inventory affixes; singletons unvaried", not bad, str(bad[:3]))
    check("varied forms occur", any(len(x) != len(w) for o, n in zip(fam, rep) for w, x in zip(o.words, n.words)))
    check("deterministic by seed", draw(11)[2] == rep and draw(12)[2] != rep)

    if "--fast" not in sys.argv:
        print("7. timing (PROTOCOL-B §8 check 7)")
        import time  # noqa: E402
        import run_paradigm as rp  # noqa: E402
        cfg = {"strict": True, "variant": "base", "with_sabaic": False, "folds": "lso", "drop_slots": (), "drop_damaged": False}
        t0 = time.time()
        arr = rp.run_null(cfg, "D2", 1000, rp.NULL_SEED["D2"] * 7 + 1, 12)
        wall = time.time() - t0
        check("1,000 D2 replicates, leave-one-site-out, 12 workers, under 60 s", wall < 60 and arr.shape == (1000, len(rp.STATS)),
              f"{wall:.1f} s")
        check("no replicate left without scorable tokens", not np.isnan(arr[:, 0]).any(), f"{int(np.isnan(arr[:, 0]).sum())} nan")

    out = {"own_rates": own_rates, "leakage": leak, "flags": flags}
    (paths.RUNS / "_cache").mkdir(parents=True, exist_ok=True)
    (paths.RUNS / "_cache" / "selftest_b_last.json").write_text(json.dumps(out, indent=1))
    print(f"\n{'ALL PASS' if not FAILS else 'FAILURES: ' + ', '.join(FAILS)}")
    return 0 if not FAILS else 1


if __name__ == "__main__":
    sys.exit(main())
