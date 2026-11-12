# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Check the hand-edited unread_signs.json against the corpus. Read-only: writes nothing.

A sign token is an undamaged token of corpus.json `transliteratedWords` that is neither a numeral nor a
separator and yields no syllabic run of 2+ signs (those are words, and unread_words.json holds them): one
sign, a ligature (+), a vessel sign (-VS), a logogram, or a logogram joined to a sign. It counts as read,
and stays out of the file, when a live lexicon entry matches it (the lookup check_unread_words uses).
Everything else belongs in the file. The check reports:
  unlisted       a corpus sign token with no lexicon entry that the file neither lists nor excludes
  now_read       a listed sign the lexicon now reads (remove it by hand)
  not_in_corpus  a listed sign that no undamaged corpus token yields
  field          a counted field (frequency, attestations, sites, cross_site) that differs from the corpus
  stats          a `stats` value that differs from a recount
Curated fields (kind, status, components, read_components, on_file, note) are never checked.
Exit status 1 when anything is reported, 2 when a file it reads is not in the checkout.

`--rank` prints instead, for each listed sign, the records with no translation on which it is the only
token left unread: every other token there is a numeral, a separator, a damage mark, a lexicon entry or an
onomasticon name with a reading.

    uv run tools/linear_a/validation/check_unread_signs.py [--json] [--rank]
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

from ...paths import NotInCheckout
from . import check_unread_words as words

NAME = 'unread_signs.json'
# Numeral and fraction glyphs of the Aegean numbers and Linear A blocks, written out in some records
GLYPHS = re.compile(r'[\U00010100-\U0001013F\U00010740-\U0001077F,]+')


def is_counted(token) -> bool:
    """A numeral, fraction, separator or bare damage mark: nothing to read."""
    if words.is_separator(token) or words.is_numeral(token):
        return True
    token = token.strip()
    return bool(words.NUMERIC.fullmatch(token) or GLYPHS.fullmatch(token))


def sign_tokens(record: dict):
    """The undamaged sign tokens of one corpus record, in order."""
    for token in record.get('transliteratedWords') or []:
        if is_counted(token):
            continue
        token = token.strip()
        if words.syllabic_runs(token) or words.damaged(token):
            continue
        yield token


def occurrences(corpus: dict, lex_hit, excluded=()) -> dict[str, list[tuple[str, str]]]:
    """Sign token -> [(document, site)] for every sign token the lexicon does not read."""
    out = defaultdict(list)
    for key, record in corpus.items():
        for token in sign_tokens(record):
            if token not in excluded and not lex_hit(token):
                out[token].append((key, record.get('site')))
    return dict(out)


def check(doc: dict, occ: dict, lex_hit) -> list[tuple[str, str, str]]:
    """Compare the hand file with the corpus. Returns a list of (kind, sign, detail)."""
    issues = []
    listed = {e['sign']: e for e in doc['entries']}
    excluded = doc.get('excluded', {})
    for sign, hits in occ.items():
        if sign not in listed and sign not in excluded:
            issues.append(('unlisted', sign, f"{len(hits)}x {', '.join(sorted({d for d, _ in hits}))}"))
    for sign, entry in listed.items():
        if (hit := lex_hit(sign)):
            issues.append(('now_read', sign, f"lexicon: {hit['word']} {hit.get('reading')!r}"))
            continue
        hits = occ.get(sign)
        if not hits:
            issues.append(('not_in_corpus', sign, 'no undamaged corpus token yields this sign'))
            continue
        sites = sorted({s for _, s in hits if s})
        found = {'frequency': len(hits), 'attestations': sorted({d for d, _ in hits}), 'sites': sites,
                 'cross_site': len(sites) > 1}
        for field, value in found.items():
            have = sorted(entry.get(field) or []) if field in ('attestations', 'sites') else entry.get(field)
            if have != value:
                issues.append(('field', sign, f'{field}: file {entry.get(field)!r}, corpus {value!r}'))
    entries = doc['entries']
    recount = {'listed': len(entries), 'by_status': dict(Counter(e['status'] for e in entries)),
               'by_kind': dict(Counter(e['kind'] for e in entries)),
               'occurrences': sum(e['frequency'] for e in entries),
               'hapax': sum(e['frequency'] == 1 for e in entries),
               'cross_site': sum(bool(e['cross_site']) for e in entries)}
    stats = doc.get('stats', {})
    for key, value in recount.items():
        if stats.get(key) != value:
            issues.append(('stats', key, f'file {stats.get(key)!r}, recount {value!r}'))
    return issues


def sole_blockers(corpus: dict, translated, listed, lex_hit, named) -> dict[str, list[str]]:
    """Listed sign -> the untranslated records on which it is the only token left unread.
    `translated` holds the record ids with a translation, `named` the onomasticon tokens with a reading."""
    out = defaultdict(list)
    for key, record in corpus.items():
        if key in translated:
            continue
        unread = set()
        for token in record.get('transliteratedWords') or []:
            if is_counted(token):
                continue
            token = token.strip()
            if not (lex_hit(token) or token in named):
                unread.add(token)
        if len(unread) == 1 and (sign := next(iter(unread))) in listed:
            out[sign].append(key)
    return dict(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--json', action='store_true', help='print the report as JSON')
    ap.add_argument('--rank', action='store_true',
                    help='list the signs by the untranslated records each one alone leaves unread')
    args = ap.parse_args()

    try:
        words.load_sign_classes()
        doc, corpus = words.load(NAME), words.load('corpus.json')
        lex_hit = words.make_lex_hit(words.live_lexicon(words.load('lexicon.json')))
        if args.rank:
            named = {o['token'] for o in words.load('onomasticon.json')['entries'] if o.get('reading')}
            listed = {e['sign']: e for e in doc['entries']}
            blocked = sole_blockers(corpus, words.load('translations.json')['translations'], listed, lex_hit, named)
            rows = sorted(blocked.items(), key=lambda kv: (-len(kv[1]), kv[0]))
            if args.json:
                print(json.dumps([{'sign': s, 'status': listed[s]['status'], 'records': r} for s, r in rows],
                                 ensure_ascii=False, indent=2))
            else:
                for sign, records in rows:
                    print(f"{len(records):4}  {sign:16} {listed[sign]['status']:15} {', '.join(records[:6])}"
                          + (' …' if len(records) > 6 else ''))
                print(f'{sum(len(r) for _, r in rows)} record(s) wait on one sign each')
            return 0
        issues = check(doc, occurrences(corpus, lex_hit, doc.get('excluded', {})), lex_hit)
    except NotInCheckout as e:
        print(f'stopped: {e}', file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps([{'kind': k, 'sign': s, 'detail': d} for k, s, d in issues], ensure_ascii=False, indent=2))
    else:
        for k, s, d in issues:
            print(f'{k:14} {s}  {d}')
        print(f'{len(issues)} issue(s)' if issues else f'{NAME} agrees with the corpus')
    return 1 if issues else 0


if __name__ == '__main__':
    sys.exit(main())
