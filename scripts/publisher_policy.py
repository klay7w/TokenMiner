"""Validate generated Git blobs without importing or checking out candidate code."""
import json
import math
import re
import subprocess
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from unicodedata import category
from unittest.mock import patch

import yaml

from tokenminer.diffing import Change, diff_data
from tokenminer.generators import generate_changelog, generate_provider_page, generate_readme
from tokenminer.models import Model, Offer, Provider
from tokenminer.scoring import score_provider
from tokenminer.store import load_snapshot


def require(ok, message):
    if not ok:
        raise ValueError(message)


def git(*args):
    return subprocess.check_output(['git', *args])


def blob(rev, path):
    obj = f'{rev}:{path}'  # empty rev reads index
    require(int(git('cat-file', '-s', obj)) <= 8_000_000, 'oversize blob')
    return git('cat-file', 'blob', obj).decode('utf-8')


def day(value):
    require(isinstance(value, str) and date.fromisoformat(value).isoformat() == value, 'invalid ISO day')
    return value


def load_json(text):
    value = json.loads(text)
    require(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n' == text,
            'noncanonical JSON (duplicate key, nonfinite number or bad encoding)')
    return value


def registry(text):
    require(len(text) < 200_000 and not any(isinstance(t, (yaml.AliasToken, yaml.AnchorToken, yaml.TagToken))
                                           for t in yaml.scan(text)), 'unexpected YAML structure')
    rows = yaml.safe_load(text)
    require(isinstance(rows, list) and rows and yaml.safe_dump(rows, sort_keys=False, allow_unicode=True) == text,
            'noncanonical provider registry')
    return rows


def fixed_fields(row, mutable):
    return {k: v for k, v in row.items() if k not in mutable}


def changes(base, head, allowed, history):
    args = [base, head] if head else ['--cached', base]
    raw = git('diff', '--raw', '-z', '--no-renames', *args, '--').split(b'\0')[:-1]
    paths = []
    for meta, filename in zip(raw[::2], raw[1::2], strict=True):
        old, new, _, _, status = meta[1:].split()
        path = filename.decode('ascii')
        require(path in allowed or path == history, 'unexpected generated path')
        require(new == b'100644' and ((old, status) == (b'100644', b'M') or
                (path == history and (old, status) == (b'000000', b'A'))), 'unsafe file operation/mode')
        paths.append(path)
    require(paths, 'empty generated change')
    return paths


def plain(value):
    require(isinstance(value, str) and len(value) <= 1024 and not re.search(r'[<>\[\]`|\\@&]|://|\$\{\{|\bwww\.', value, re.I)
            and all(category(c) not in ('Cc', 'Cf') for c in value), 'unexpected markup in collected text')


def documents(base, head, stamp, providers, offers, models, notes, paths):
    """Compare bytes with the base revision's offline generators, not a Markdown blocklist."""
    on = date.fromisoformat(stamp)
    ps, os_, ms = [Provider(**r) for r in providers], [Offer(**r) for r in offers], [Model(**r) for r in models]
    with patch('tokenminer.utils.time.today', return_value=on), patch('tokenminer.diffing.today', return_value=on):
        if not notes or 'CHANGELOG.md' in paths or 'data/history/' + stamp + '.json' in paths:
            with TemporaryDirectory() as temp:
                directory = Path(temp)
                names = git('ls-tree', '--name-only', '-r', base, 'data/history').decode().splitlines()
                snapshot = 'data/history/' + stamp + '.json'
                for path in sorted(set(names) | ({snapshot} if snapshot in paths else set())):
                    (directory / Path(path).name).write_text(blob(head if path == snapshot else base, path), encoding='utf8')
                require(blob(head, 'CHANGELOG.md') == generate_changelog(directory), 'changelog differs from generated data')
                if not notes:
                    snaps = sorted(directory.glob('*.json'))
                    old = load_snapshot(snaps[-2]) if len(snaps) > 1 else ([], [], [])
                    notes = diff_data(*old, *load_snapshot(snaps[-1])) if snaps else []
        scores = {p.id: score_provider(p, [o for o in os_ if o.provider_id == p.id], [m for m in ms if m.provider_id == p.id]) for p in ps}
        require(blob(head, 'README.md') == generate_readme(ps, os_, ms, scores, notes, on), 'README does not match trusted generator')
        for p in ps:
            require(blob(head, f'docs/providers/{p.id}.md') == generate_provider_page(p, os_, ms, scores[p.id]), 'provider page does not match data')


def validate(base, head=''):
    old = registry(blob(base, 'data/providers.yaml'))
    providers = registry(blob(head, 'data/providers.yaml'))
    require(len(old) == len(providers), 'provider registry membership changed')
    for prev, row in zip(old, providers):
        Provider.model_validate(row, strict=True)
        require(fixed_fields(row, ('last_verified', 'last_checked')) == fixed_fields(prev, ('last_verified', 'last_checked')),
                'only provider verification dates may change')
        for field in ('last_verified', 'last_checked'):
            require(day(row[field]) >= prev[field], 'provider date regressed')
    pages = {f'docs/providers/{p["id"]}.md' for p in old} | {'README.md', 'CHANGELOG.md'}
    allowed = pages | {'data/' + n for n in ('providers.yaml', 'arena.json', 'generic_state.json', 'offers.json', 'models.json', 'update_summary.txt')}
    summary = blob(head, 'data/update_summary.txt').splitlines()
    stamp = day(summary[0].removeprefix('date: '))
    require(blob(base, 'data/update_summary.txt').splitlines()[0] <= 'date: ' + stamp <= 'date: ' + date.today().isoformat(), 'invalid snapshot chronology')
    history = 'data/history/' + stamp + '.json'
    paths = changes(base, head, allowed, history)
    for p in providers:
        require(p['last_verified'] <= p['last_checked'] <= stamp, 'inconsistent provider dates')
    def data(name, rev=head):
        return load_json(blob(rev, 'data/' + name + '.json'))
    offers, models = data('offers'), data('models')
    previous_offers = data('offers', base)
    require(len(offers) == len(previous_offers) and offers, 'offer membership changed')
    for prev, row in zip(previous_offers, offers):
        Offer.model_validate(row, strict=True)
        mutable = {'last_checked', 'last_verified', 'status', 'stale'}
        if prev['id'] in ('openrouter-free-models', 'tokenrouter-free-models'):
            mutable.update(('title', 'description'))
            plain(row['title'])
            plain(row['description'].replace('https://openrouter.ai/docs/api-reference/limits', 'limits'))
        require(fixed_fields(prev, mutable) == fixed_fields(row, mutable), 'offer seed or URL changed')
        for k in ('last_checked', 'last_verified'):
            if row[k] is not None:
                require(day(row[k]) <= stamp, 'invalid offer date')
    ids = set()
    sources = {'openrouter': 'https://openrouter.ai/api/v1/models', 'tokenrouter': 'https://tokenrouter.com/models'}
    for row in models:
        Model.model_validate(row, strict=True)
        pid, mid = row['provider_id'], row['model_id']
        require(pid in sources and row['source_url'] == sources[pid] and re.fullmatch(r'[\w.~/:-]+', mid, re.ASCII), 'invalid model identity')
        require((pid, mid) not in ids, 'duplicate model')
        ids.add((pid, mid))
        host = sources[pid].split('/')[2]
        require(re.fullmatch('https://' + re.escape(host) + r'/[a-zA-Z0-9._~%/:-]+', row['model_url']), 'unexpected model URL')
        for value in (row['name'], row['developer'], *row['model_type'], row['free_variant'] or '', row['rate_limit'] or ''):
            plain(value)
        for k in ('last_checked', 'last_verified'):
            require(day(row[k]) <= stamp, 'invalid model date')
        for k in ('context_length', 'max_output_tokens', 'arena_rank', 'usage_rank'):
            require(row[k] is None or row[k] > 0, 'invalid model count/rank')
        for k in ('input_price', 'output_price'):
            require(row[k] is None or math.isfinite(row[k]) and (row[k] >= 0 or row[k] == -1), 'invalid price')
    require({pid for pid, _ in ids} == sources.keys(), 'missing model catalog')
    counts = [len(providers), len(offers), len(models), sum(r['free'] for r in models)]
    fields = [f'date: {stamp}', f'providers: {counts[0]}', f'offers: {counts[1]}',
              *(f'offers_by_{k}: {dict(sorted(Counter(r[k] for r in offers).items()))}' for k in ('status', 'confidence')),
              f'models: {counts[2]}', f'free_models: {counts[3]}']
    require(summary[:7] == fields and re.fullmatch(r'changes: [0-9]+', summary[7]), 'invalid summary')
    notes = diff_data([Provider(**r) for r in old], [Provider(**r) for r in providers],
                      [Offer(**r) for r in previous_offers], [Offer(**r) for r in offers],
                      [Model(**r) for r in data('models', base)], [Model(**r) for r in models])
    state, previous_state = data('generic_state'), data('generic_state', base)
    for p in old:
        for url in p['watch_urls']:
            now = state.get(p['id'], {}).get(url)
            prev = previous_state.get(p['id'], {}).get(url)
            if now and (not prev or now['hash'] != prev['hash']):
                kind = 'watch page changed' if prev else 'now watching'
                notes.append(Change(stamp, '', f"{p['name']}: {kind}: {url}"))
    require(summary[7:] == [f'changes: {len(notes)}', *('change: ' + n.text for n in notes[:20])], 'summary differs from data')
    for note in notes:
        note.date = stamp
    if notes or history in paths:
        require(data('history/' + stamp) == {'date': stamp, 'providers': providers, 'offers': offers,
                'free_models': [m for m in models if m['free']]}, 'snapshot not equal to current data')
    if 'data/arena.json' in paths:
        arena = data('arena')
        require(set(arena) == {'source', 'fetched', 'models'} and arena['source'] == data('arena', base)['source']
                and day(arena['fetched']) <= stamp and isinstance(arena['models'], list) and arena['models'], 'invalid arena')
        for row in arena['models']:
            require(set(row) == {'rank', 'name', 'organization'} and type(row['rank']) is int and row['rank'] > 0, 'invalid arena row')
            plain(row['name'])
            if row['organization'] is not None:
                plain(row['organization'])
    if 'data/generic_state.json' in paths:
        watches = {p['id']: p['watch_urls'] for p in old if p['collector'] == 'generic'}
        require(state.keys() == watches.keys(), 'unknown or missing generic provider')
        for pid, entries in state.items():
            for url, row in entries.items():
                require(url in watches[pid] and set(row) == {'hash', 'keywords', 'status', 'checked'} and
                        re.fullmatch('[0-9a-f]{64}', row['hash']) and type(row['status']) is int and 200 <= row['status'] < 400 and
                        day(row['checked']) <= stamp and isinstance(row['keywords'], list), 'invalid watch result')
                for keyword in row['keywords']:
                    require(keyword in ('free tier', 'free', 'credit', 'trial', 'promotion', 'promo', 'student', 'developer',
                                        'signup', 'sign up', 'sign-up', '$5', '$10', '$20', 'token'), 'unknown watch keyword')
    documents(base, head, stamp, providers, offers, models, notes, paths)


if __name__ == '__main__':
    validate(*sys.argv[1:])
