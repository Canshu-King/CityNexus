"""ORD-0261/0264 v2 identity readback: every claim in the v2 receipt is computed here
(ancestor test, changed paths, source tree hashes, rebuilt artifact hashes, gate-v2 blob ids),
never transcribed.  Writes artifact_identity_v2.json.
"""
from __future__ import annotations

import base64
import hashlib
import json
import pathlib
import subprocess
import urllib.request

D = pathlib.Path('D:/moodle')
CAND = D / '_hjp3_ord0261_0923'
TREE6 = CAND / 'snap_6daceb1/frontend/dist/assets'
TREE7 = CAND / 'snap_e3b0b47/frontend/dist/assets'
DLANE = D / '_qoder_d_lane_20260923'
TOK = (D / '_qoder_recovery_20260919/.api_tok_20260920').read_text(encoding='utf-8').strip()


def git(*a):
    return subprocess.run(['git', '-C', str(DLANE)] + list(a), capture_output=True, text=True)


def api(path):
    last = None
    for _ in range(5):
        try:
            req = urllib.request.Request('https://api.github.com' + path)
            req.add_header('Authorization', 'Bearer ' + TOK)
            req.add_header('Accept', 'application/vnd.github+json')
            req.add_header('User-Agent', 'hjp3-readback')
            return json.loads(urllib.request.urlopen(req, timeout=120).read().decode())
        except Exception as e:  # TLS resets are common on this link; a fresh request may succeed
            last = e
    raise last


out = {}
r = git('merge-base', '--is-ancestor', '6daceb1', 'e3b0b47')
out['ancestor_6daceb1_of_e3b0b47'] = (r.returncode == 0)
out['commits_between'] = git('log', '--format=%h %s', '6daceb1..e3b0b47').stdout.splitlines()
out['changed_paths'] = git('diff', '--name-status', '6daceb1', 'e3b0b47').stdout.splitlines()
BUNDLED = ('frontend/src', 'frontend/index.html', 'frontend/public', 'frontend/package.json',
           'frontend/vite.config.ts', 'frontend/tsconfig.json')
ps = [p.split('\t')[-1] for p in out['changed_paths']]
out['bundled_input_changes'] = [p for p in ps if any(p.startswith(b) for b in BUNDLED)]
out['frontend_src_tree_hash'] = {t: git('rev-parse', t + ':frontend/src').stdout.strip()
                                 for t in ('6daceb1', 'e3b0b47')}
out['frontend_src_tree_equal'] = len(set(out['frontend_src_tree_hash'].values())) == 1
names = sorted(p.name for p in TREE7.iterdir())
out['built_assets'] = {}
for n in names:
    a, b = (TREE6 / n).read_bytes(), (TREE7 / n).read_bytes()
    out['built_assets'][n] = {'bytes': len(b), 'sha256_e3b0b47': hashlib.sha256(b).hexdigest(),
                              'sha256_6daceb1': hashlib.sha256(a).hexdigest(), 'equal': a == b}
out['all_assets_equal'] = all(v['equal'] for v in out['built_assets'].values())
out['gate_v2_dir'] = []
try:
    listing = api('/repos/Canshu-King/CityNexus/contents/evidence/ord0261-0264-gate-v2?ref=commander/control')
except Exception as e:
    listing = []
    out['gate_v2_transport'] = 'LINK_DOWN ' + str(e)[:80]
for i in listing:
    if i['type'] == 'file':
        row = {'name': i['name'], 'bytes': i['size'], 'blob': i['sha']}
        try:
            raw = base64.b64decode(api(i['url'])['content'])
            row['recomputed_local_blob_equal'] = hashlib.sha1(b'blob %d\0' % len(raw) + raw).hexdigest() == i['sha']
        except Exception as e:
            row['recomputed_local_blob_equal'] = 'LINK_DOWN ' + str(e)[:40]
        out['gate_v2_dir'].append(row)
out['my_published_v2_inputs_untouched'] = sorted(p.name for p in (D / '_hjp3_ord0261_0923').iterdir()
                                                 if p.is_dir() or p.suffix in ('.json', '.patch', '.txt'))
(CAND / 'artifact_identity_v2.json').write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding='utf-8')
print(json.dumps({k: out[k] for k in ('ancestor_6daceb1_of_e3b0b47', 'bundled_input_changes',
                                      'frontend_src_tree_equal', 'all_assets_equal')}, ensure_ascii=False))
print('assets:', {k: (v['bytes'], v['sha256_e3b0b47'][:12], v['equal']) for k, v in out['built_assets'].items()})
print('gate v2:', [(d['name'], d['blob'][:12], d['recomputed_local_blob_equal']) for d in out['gate_v2_dir']])
