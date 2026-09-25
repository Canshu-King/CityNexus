"""Prove '0 覆盖 0 删除' the way git can be held to: compare blob ids across two branch tips.

Pass 1 ended at a tip its own coordinate line names. If any file that existed there is gone now, that is
a deletion; if any exists with a different blob id, that is an overwrite - which is exactly the rule I
broke once already (ORD-0300's receipt json), so this check exists rather than my assurance.
"""
from __future__ import annotations

import json
import pathlib
import re
import urllib.request

B = pathlib.Path('D:/moodle/_hjp3_0301_0925')
TOK = pathlib.Path('D:/moodle/_qoder_recovery_20260919/.api_tok_20260920').read_text(encoding='utf-8').strip()
API = 'https://api.github.com/repos/Canshu-King/CityNexus'
PREFIX = 'evidence/ord0301-screen-speaks-range-hjp3'


def api(path, tries=5):
    for attempt in range(tries):
        req = urllib.request.Request(API + path)
        req.add_header('Authorization', 'Bearer ' + TOK)
        req.add_header('Accept', 'application/vnd.github+json')
        req.add_header('User-Agent', 'citynexus-hjp3-immcheck')
        try:
            with urllib.request.urlopen(req, timeout=150) as f:
                return json.loads(f.read().decode())
        except Exception as e:  # noqa: BLE001
            if attempt == tries - 1:
                raise
            print('  retry %d: %s' % (attempt + 1, str(e)[:70]), flush=True)


def listing(tip):
    return {e['path'].split('/')[-1]: e['sha']
            for e in api('/git/trees/' + tip + '?recursive=1')['tree']
            if e['path'].startswith(PREFIX + '/')}


def tip_from(text):
    m = re.search(r'读回 commit 尖 `([0-9a-f]{40})`', text)
    return m.group(1) if m else None


pass1_line = (B / 'coords_line_final.txt').read_text(encoding='utf-8')
tip1 = tip_from(pass1_line)
now_tip = api('/git/ref/heads/commander/control')['object']['sha']
old = listing(tip1)
new = listing(now_tip)

overwritten = sorted(n for n in old if n in new and old[n] != new[n])
deleted = sorted(set(old) - set(new))
out = {
    'tip_after_pass_1': tip1,
    'tip_now': now_tip,
    'files_at_pass1_tip': len(old),
    'files_now': len(new),
    'added_since_pass1': len(set(new) - set(old)),
    'overwritten_paths': overwritten,
    'deleted_paths': deleted,
    'verdict': ('IMMUTABLE_0_OVERWRITE_0_DELETE' if not overwritten and not deleted
                else 'PUBLISHED_PATH_CHANGED'),
    'how_read': 'GET /git/trees/<tip>?recursive=1 at both tips, blob ids compared per file name; '
                'the pass-1 tip is the one pass 1 published and read back in its own coordinate line',
}
(B / 'immutability_check.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
print(json.dumps(out, ensure_ascii=False, indent=1))
raise SystemExit(0 if out['verdict'].startswith('IMMUTABLE') else 1)
