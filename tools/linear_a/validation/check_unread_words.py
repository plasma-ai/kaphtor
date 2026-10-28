# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Check the hand-edited unread_words.json against the corpus. Read-only: writes nothing.

A word is any undamaged syllabic run of 2+ signs in corpus.json `transliteratedWords`
(logogram parts split off). It counts as read, and stays out of this file, when it:
  - matches a live lexicon entry (exact / logogram prefix stripped / J-Y swap / corpus_forms);
    subscripts mark different signs and never fold (PU₂-RA₂ is not PU-RA₂);
  - splits wholly into lexicon words of 2+ signs;
  - is read in translations.json (a gloss that is a reading, not a role label, or a `reading`
    that is not a placeholder, tentative ?...? or partial ... form, nor the signs spelled out);
  - carries a reading in onomasticon.json.
Everything else belongs in the file. The check reports:
  unlisted       a corpus word with no reading that the file neither lists nor excludes
  now_read       a listed word that is now read (remove it by hand)
  not_in_corpus  a listed word that no undamaged corpus token yields
  lexicon_reads  a listed word the lexicon reads that stands whole in no intact token on the
                 documents its lexicon entry cites (a broken word the lexicon reads keeps its
                 reading and has no entry here)
  field         a counted field (signs, frequency, attestations, sites, cross_site,
                 surface_damage) that differs from the corpus
  stats          a `stats` value that differs from a recount
Curated fields (status, role, translation_label, edge_overlap, note) are never checked.
Exit status 1 when anything is reported, 2 when a file it reads is not in the checkout.

    uv run tools/linear_a/validation/check_unread_words.py [--json]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    __package__ = "tools.linear_a.validation"

from ...core.normalization import _jy_variants
from ...paths import LINEAR_A_DATA, NotInCheckout, require

DATA = LINEAR_A_DATA
NAME = 'unread_words.json'

SEPARATORS = {"", "\n", "\U00010101", "—", "–", "-"}
FRACTION_CHARS = frozenset("¼½¾⅐⅑⅒⅓⅔⅕⅖⅗⅘⅙⅚⅛⅜⅝⅞⁄")


def is_separator(word) -> bool:
    return not isinstance(word, str) or word.strip() in SEPARATORS


def is_numeral(word: str) -> bool:
    compact = word.strip()
    if not compact:
        return False
    if compact.isdigit():
        return True
    return all(c in FRACTION_CHARS or c.isdigit() or c in "/.," for c in compact)


# Logogram codes that can sit inside a hyphenated token (NI, TE etc. left out: also syllables)
LOGO = {'GRA', 'OLE', 'VIN', 'VINA', 'TELA', 'LANA', 'OLIV', 'FIC', 'CYP', 'BOS', 'OVIS', 'SUS', 'CAP',
        'EQU', 'VIR', 'AES', 'AUR', 'HORD', 'COR', 'ARE', 'TRI', 'AROM', 'GAL', 'VAS', 'L'}
# Starred syllabograms: every *NNN sign sign_values.json gives a syllabic record in `signs`, resolved, proposed
# or speculative (*21F = /ha/, *28B = JI), so a new value joins automatically. Every other letter-suffixed
# sign (*22F, *309B …) stays a logogram. load_sign_classes() fills these before the census reads a token.
LETTERED: list[str] = []
SYL: re.Pattern | None = None
PHON_STAR: set[str] = set()


def load_sign_classes(data_dir=None):
    global LETTERED, SYL, PHON_STAR
    PHON_STAR = {k for k in load('sign_values.json', data_dir)['signs'] if k.startswith('*')}
    LETTERED = sorted(s for s in PHON_STAR if re.fullmatch(r'\*\d+[A-Z]', s))
    SYL = re.compile(r'(?:[BCDGHJKLMNPQRSTWZ]{0,2}[AEIOU][₂₃23]?|AU|'
                     + ''.join(re.escape(s) + '|' for s in LETTERED) + r'\*\d+|A\d{3}|AB\d{2,3})')


PREFIX = re.compile(r'^\*\d+(-VS)?-')  # logogram or vessel-sign prefix
MARK = '\U0001076B'
DAMAGE = re.compile(r'[\[\]\?\U0001076B\U000FD1EB]')
NUMERIC = re.compile(r'[\d\s¹²³⁴⁵⁶⁷⁸⁹⁰⁄₀₁₂₃₄₅₆₇₈₉≈.,/]+')
UNGLOSSED = re.compile(r'^\s*(\?+|unknown|unclear|untranslated|uncertain|—|-|n/?a)?\s*$', re.IGNORECASE)
LABEL_ONLY = re.compile(r'unread|opaque|unresolved|^unknown|^roster entry|^recipient|^heading|^PN \(|'
                        r'^personal name( \(unread|\s*$)|^tentative|segmentation contested|possibly a personal name|'
                        r'^\[unresolved|^personal name or institution|^personal or institutional (label|name)|'
                        r'^administrative label|^untranslated|^unidentified|^transaction sign|'
                        r'^personal name\s*\(\?\)\s*$|^broken word\b|(No reading|Not readable|Not a word)\.\s*$', re.IGNORECASE)
# A translation `reading` that is a placeholder, tentative (?...?) or partial (...) proposes nothing
NO_READING = re.compile(r'^\s*(\?|\[?unknown\]?|unread|—|-|)\s*$|^\?|\?$|…|\.\.\.', re.IGNORECASE)
READ_BINS = ('lexicon', 'composite', 'translation', 'onomasticon')
UNREAD_BINS = ('unread', 'name_class', 'partial')


def _spelled(s):
    """Letters only, lower-cased: 'Sidu(?)' and 'SI-DU' both give 'sidu'."""
    return re.sub(r'[^a-z]', '', s.lower())


def proposes(reading, word):
    """True when a translation `reading` proposes something: not a placeholder, tentative or partial
    form (NO_READING), and not the word's own signs spelled out (Didizake for DI-DI-ZA-KE)."""
    return isinstance(reading, str) and not NO_READING.search(reading) and _spelled(reading) != _spelled(word)


def load(name, data_dir=None):
    return json.loads(require((data_dir or DATA) / name, name).read_text(encoding='utf-8'))


def syllabic_runs(tok):
    """Split a token on logogram / vessel-sign parts; return the syllabic runs of 2+ signs."""
    tok = PREFIX.sub('', tok) if re.match(r'^\*\d+-VS-', tok) else tok
    runs, cur = [], []
    for p in tok.split('-'):
        if p in LOGO or not SYL.fullmatch(p):
            runs.append(cur)
            cur = []
        else:
            cur.append(p)
    runs.append(cur)
    return ['-'.join(r) for r in runs if len(r) >= 2]


def surface_damage(uni):
    """Where a Unicode word carries the damage marker 𐝫: start / interior / end.
    The marker records damaged surface, not necessarily lost signs."""
    if not isinstance(uni, str) or MARK not in uni:
        return []
    s = uni.strip()
    out = []
    if s.startswith(MARK):
        out.append('start')
    if s.endswith(MARK):
        out.append('end')
    if MARK in s.strip(MARK):
        out.append('interior')
    return out


def strict_lookup(entries, w):
    """Exact, then with a logogram prefix stripped, then J/Y swapped. Subscripts are kept:
    PA₃ (AB56) is not PA (AB03), so PU₂-RA₂ never finds PU-RA₂."""
    for q in dict.fromkeys([w, PREFIX.sub('', w)]):
        if q in entries:
            return entries[q]
        for v in _jy_variants(q):
            if v in entries:
                return entries[v]
    return None


def make_lex_hit(live):
    """Lexicon lookup for a corpus word: exact / logogram prefix stripped / J-Y swap.

    A bare word never matches a star-prefixed entry (MI-NA is not *118-MI-NA). A query loses a
    leading *NNN- only when that sign is not a syllabogram: *815-QA-PA₃ finds QA-PA₃,
    but *306-TU (ʿA-TU) never finds TU.
    """
    def lex_hit(w):
        m = re.match(r'(\*\d+[A-Z]?)-', w)
        if m and m.group(1) in PHON_STAR:
            return live.get(w)
        return strict_lookup(live, w)
    return lex_hit


def live_lexicon(lex):
    """Live (not REJECTED) lexicon entries by word, plus the alias spellings recorded on them."""
    live = {e['word']: e for e in lex['entries'] if e.get('confidence') != 'REJECTED'}
    for e in lex['entries']:
        if e.get('confidence') == 'REJECTED':
            continue
        forms = (e.get('corpus_forms') or []) + ([e['linear_a_form']] if isinstance(e.get('linear_a_form'), str) else [])
        for f in forms:
            if isinstance(f, str) and f not in live:
                live[f] = e
    return live


def census(data_dir=None):
    """Classify every unique corpus word. Returns (rows, excluded-token counts)."""
    load_sign_classes(data_dir)
    corpus, lex, ono = load('corpus.json', data_dir), load('lexicon.json', data_dir), load('onomasticon.json', data_dir)
    trans = load('translations.json', data_dir)['translations']

    live = live_lexicon(lex)
    rej = {e['word']: e for e in lex['entries'] if e.get('confidence') == 'REJECTED'}
    lex_hit = make_lex_hit(live)

    gloss, proposed = {}, {}
    for t in trans.values():
        for w in t.get('words') or []:
            if not isinstance(w, dict):
                continue
            g = w.get('gloss') or w.get('meaning') or ''
            if w.get('linear_a') and isinstance(g, str) and not UNGLOSSED.match(g):
                gloss.setdefault(w['linear_a'], (g, w.get('confidence')))
            rd = w.get('reading')
            if w.get('linear_a') and proposes(rd, w['linear_a']):
                proposed.setdefault(w['linear_a'], rd)
    ono_by = {e['token']: e for e in ono['entries']}

    occ, docs, sites = Counter(), defaultdict(set), defaultdict(set)
    damage = defaultdict(dict)  # word -> {doc: [start|interior|end]} from 𐝫 in the Unicode `words`
    other = Counter()
    for did, d in corpus.items():
        tw = d.get('transliteratedWords') or []
        uw = d.get('words') if len(d.get('words') or []) == len(tw) else [None] * len(tw)
        for raw, uni in zip(tw, uw):
            if is_separator(raw):
                continue
            tok = raw.strip()
            if not tok or tok == 'None' or is_numeral(tok) or NUMERIC.fullmatch(tok):
                other['numeral/punct'] += 1
            elif DAMAGE.search(tok):
                other['damaged'] += 1
            elif '+' in tok:
                other['ligature/logogram'] += 1
            elif not (runs := syllabic_runs(tok)):
                other['single-sign' if SYL.fullmatch(tok) and tok not in LOGO else 'logogram'] += 1
            else:
                marks = surface_damage(uni)
                for i, w in enumerate(runs):
                    occ[w] += 1
                    docs[w].add(did)
                    sites[w].add(d.get('site') or '?')
                    # token-edge damage belongs to the first / last run only
                    m = [x for x in marks if x == 'interior' or (x == 'start' and i == 0)
                         or (x == 'end' and i == len(runs) - 1)]
                    if m:
                        damage[w][did] = [x for x in ('start', 'interior', 'end') if x in set(damage[w].get(did, [])) | set(m)]

    def segment(parts):
        """Split a sign list wholly into lexicon words of 2+ signs; None if impossible."""
        if not parts:
            return []
        for n in range(len(parts), 1, -1):
            if lex_hit('-'.join(parts[:n])):
                rest = segment(parts[n:])
                if rest is not None:
                    return ['-'.join(parts[:n])] + rest
        return None

    def edge(w):
        parts = w.split('-')
        for n in range(len(parts) - 1, 1, -1):
            for seg in ('-'.join(parts[:n]), '-'.join(parts[-n:])):
                if (e := lex_hit(seg)):
                    return seg, e
        return None

    rows = []
    for w in occ:
        rec = {'word': w, 'occ': occ[w], 'docs': sorted(docs[w]), 'sites': sorted(sites[w]),
               'signs': len(w.split('-'))}
        if damage.get(w):
            rec['damage'] = dict(sorted(damage[w].items()))
        e, o = lex_hit(w), ono_by.get(w)
        if e:
            rec.update(bin='lexicon', tier=e['confidence'], lex_word=e['word'], reading=e.get('reading'))
        elif strict_lookup(rej, w):
            rec.update(bin='rejected')
        elif (s := segment(w.split('-'))):
            rec.update(bin='composite', parts=s)
        elif w in gloss and not LABEL_ONLY.search(gloss[w][0]):
            rec.update(bin='translation', gloss=gloss[w][0], tier=gloss[w][1])
        elif w in proposed:
            rec.update(bin='translation', reading=proposed[w], gloss=gloss.get(w, (None,))[0],
                       tier=gloss.get(w, (None, None))[1])
        elif o and o.get('reading'):
            rec.update(bin='onomasticon', reading=o['reading'], type=o.get('type'))
        elif (p := edge(w)):
            rec.update(bin='partial', contains=p[0], contains_tier=p[1]['confidence'])
        elif o and o.get('type') not in (None, 'unknown') or w in gloss:
            rec.update(bin='name_class', type=(o or {}).get('type') or 'label in translations',
                       type_conf=(o or {}).get('type_confidence'), gloss=gloss.get(w, (None,))[0])
        else:
            rec.update(bin='unread')
        if o:
            rec['ono_type'] = o.get('type')
        if w in gloss:
            rec['label'] = gloss[w][0]
        rows.append(rec)
    rows.sort(key=lambda r: (-r['occ'], -len(r['docs']), r['word']))
    return rows, other


LOST = '[?]'


def trim(ps):
    """Drop lost signs at either edge."""
    while ps and ps[0] == LOST:
        ps = ps[1:]
    while ps and ps[-1] == LOST:
        ps = ps[:-1]
    return ps


def parts_of(tok):
    """A token's signs with damage brackets stripped; an internal lost sign stays as [?]."""
    t = tok.replace(LOST, '\0').replace('[…]', '').replace('…', '')
    t = re.sub(r'[\[\]\U000FD1EB]', '', t)
    out = []
    for p in t.split('-'):
        p = p.replace('\0', LOST)
        p = p if p == LOST else p.rstrip('?')
        if p:
            out.append(p)
    return trim(out)


def is_sign(p):
    return p == LOST or (p not in LOGO and bool(SYL.fullmatch(p)))


def keys_of(ps):
    """The lookup keys one token yields: each syllabic run, the pieces either side of an internal
    lost sign, and the whole token, so a listed ligature group (KI-MA+RU) finds itself."""
    keys, runs, cur = set(), [], []
    for p in ps + [None]:
        if p is not None and is_sign(p):
            cur.append(p)
            continue
        runs.append(trim(cur))
        cur = []
    for run in runs:
        pieces, piece = [], []
        for p in run + [LOST]:
            if p == LOST:
                pieces.append(piece)
                piece = []
            else:
                piece.append(p)
        for x in [run] + pieces:
            if len(x) >= 2:
                keys.add('-'.join(x))
    if len(ps) >= 2:
        keys.add('-'.join(ps))
    return keys


def occurrences(data_dir=None):
    """Every corpus token, damaged ones included. Returns (key -> [(doc, site)], raw token -> [(doc, site)])."""
    load_sign_classes(data_dir)
    idx, raw_idx = defaultdict(list), defaultdict(list)
    for did, d in load('corpus.json', data_dir).items():
        site = d.get('site') or '?'
        for raw in d.get('transliteratedWords') or []:
            if not isinstance(raw, str) or is_separator(raw):
                continue
            raw_idx[raw.strip()].append((did, site))
            for k in keys_of(parts_of(raw.strip())):
                idx[k].append((did, site))
    return idx, raw_idx


def intact_tokens(data_dir=None):
    """Per document, the signs of each token with no damage bracket and no damaged surface (𐝫), hyphen-joined."""
    out = defaultdict(set)
    for did, d in load('corpus.json', data_dir).items():
        tw = d.get('transliteratedWords') or []
        uw = d.get('words') if len(d.get('words') or []) == len(tw) else [None] * len(tw)
        for raw, uni in zip(tw, uw):
            if isinstance(raw, str) and not is_separator(raw) and not DAMAGE.search(raw) and not surface_damage(uni):
                out[did].add('-'.join(parts_of(raw.strip())))
    return dict(out)


def bracket_key(tok):
    """A broken token with any hyphen beside a bracket dropped: A-RA-[ and A-RA[ are one form."""
    return re.sub(r'-?\[', '[', re.sub(r'\]-?', ']', tok))


def check(doc, rows, occ, other, lex_hit=None, intact=None):
    """Compare the hand file with the corpus. Returns a list of (kind, word, detail).
    A listed word written with brackets names one broken token and matches it as written, a hyphen
    beside a bracket aside. With `lex_hit` (a lexicon lookup) and `intact` (intact_tokens), a listed
    word the lexicon reads must stand whole in an intact token on a document the lexicon entry cites."""
    intact = intact or {}
    idx, raw_idx = occ
    by_bracket = defaultdict(list)
    for tok, hits in raw_idx.items():
        by_bracket[bracket_key(tok)].extend(hits)
    issues = []
    by_word = {r['word']: r for r in rows}
    listed = {e['word']: e for e in doc['entries']}
    excluded = doc.get('excluded', {})
    for r in rows:
        if r['bin'] in UNREAD_BINS and r['word'] not in listed and r['word'] not in excluded:
            issues.append(('unlisted', r['word'], f"{r['occ']}x {', '.join(r['docs'])}"))
    for w, e in listed.items():
        r = by_word.get(w)
        if r and r['bin'] in READ_BINS:
            issues.append(('now_read', w, f"{r['bin']}: {r.get('reading') or r.get('gloss') or r.get('parts')}"))
        elif lex_hit and LOST not in (key := '-'.join(parts_of(w))) and (le := lex_hit(key)):
            cited = le.get('attestations') or list(intact)
            if not any(f'-{x}-' in f'-{t}-' for x in {key, le['word']} for d in cited for t in intact.get(d, ())):
                issues.append(('lexicon_reads', w, (f"{le['word']} {le.get('reading')!r}: whole in no intact token "
                                                    f"of {', '.join(cited)}")))
        hits = (re.search(r'[\[\]]', w) and by_bracket.get(bracket_key(w))) or idx.get('-'.join(parts_of(w)), [])
        if not hits:
            issues.append(('not_in_corpus', w, 'no corpus token yields this word'))
            continue
        docs = sorted({d for d, _ in hits})
        sites = sorted({s for _, s in hits})
        found = {'frequency': len(hits), 'attestations': docs, 'sites': sites, 'cross_site': len(sites) > 1}
        for k, v in found.items():
            have = sorted(e.get(k) or []) if k in ('attestations', 'sites') else e.get(k)
            if have != v:
                issues.append(('field', w, f'{k}: file {e.get(k)!r}, corpus {v!r}'))

    ents = doc['entries']
    recount = {'corpus_words': len(rows), 'read': sum(r['bin'] in READ_BINS for r in rows),
               'excluded_tokens': dict(other), 'unread_listed': len(ents), 'by_status': dict(Counter(e['status'] for e in ents)),
               'hapax': sum(e['frequency'] == 1 for e in ents),
               'repeated': sum(e['frequency'] >= 2 for e in ents),
               'cross_site': sum(bool(e['cross_site']) for e in ents),
               'surface_damaged': sum('surface_damage' in e for e in ents)}
    stats = doc.get('stats', {})
    for k, v in recount.items():
        have = dict(stats[k]) if isinstance(stats.get(k), dict) else stats.get(k)
        if have != v:
            issues.append(('stats', k, f'file {stats.get(k)!r}, recount {v!r}'))
    return issues


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--json', action='store_true', help='print the report as JSON')
    args = ap.parse_args()

    try:
        rows, other = census()
        issues = check(load(NAME), rows, occurrences(), other,
                       lex_hit=make_lex_hit(live_lexicon(load('lexicon.json'))), intact=intact_tokens())
    except NotInCheckout as e:
        print(f'stopped: {e}', file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps([{'kind': k, 'word': w, 'detail': d} for k, w, d in issues], ensure_ascii=False, indent=2))
    else:
        for k, w, d in issues:
            print(f'{k:14} {w}  {d}')
        print(f'{len(issues)} issue(s)' if issues else f'{NAME} agrees with the corpus')
    return 1 if issues else 0


if __name__ == '__main__':
    sys.exit(main())
