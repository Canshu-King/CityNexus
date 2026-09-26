"""Did the mirror move again while I was walking, and does the bundle on the phone chain predate the move?

The commander named `b6a8ea5c…` for this pass at 17:20. This instrument reads the ref again and asks GitHub how
many commits separate it from the named tip, which files they touch, and whether the frontend or the wizard's own
source is among them. It does NOT rebuild anything and does NOT re-walk: cutting a generation is the commander's
action, and my readings are worth more if I say plainly which bundle they were taken against rather than chasing a
newer one.

Read-only: git ls-remote plus GET /compare over the API; 0 requests to the phone chain; 0 refs written.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import subprocess
import time
import urllib.request

OUT = pathlib.Path('D:/moodle/_hjp3_b6a8_0926')
REF = 'refs/heads/mirror/integration-frontend-apple-pass1'
NAMED = 'b6a8ea5c625d7e3e82f7348fad57d595a8a403c0'
WIZARD = 'frontend/src/features/setup/JourneyTrialSetup.tsx'
DIRECT = urllib.request.build_opener(urllib.request.ProxyHandler({}))
TOK = pathlib.Path('D:/moodle/_qoder_recovery_20260919/.api_tok_20260920').read_text(encoding='utf-8').strip()


def api(path):
    r = urllib.request.Request('https://api.github.com/repos/Canshu-King/CityNexus' + path)
    r.add_header('Authorization', 'Bearer ' + TOK)
    r.add_header('Accept', 'application/vnd.github+json')
    r.add_header('User-Agent', 'hjp3-r6-drift')
    for i in range(3):
        try:
            with DIRECT.open(r, timeout=60) as f:
                return json.loads(f.read().decode())
        except Exception as e:  # noqa: BLE001
            if i == 2:
                raise
            time.sleep(2)


lr = subprocess.run(['git', '-C', 'D:/moodle/CityNexus', 'ls-remote', 'origin', REF],
                    capture_output=True, text=True, encoding='utf-8', errors='replace')
now = ([l.split()[0] for l in (lr.stdout or '').splitlines() if l.strip()] + [None])[0]
cmp_ = api('/compare/%s...%s' % (NAMED, now)) if now and now != NAMED else {'ahead_by': 0, 'files': [], 'commits': []}
files = [f.get('filename') for f in (cmp_.get('files') or [])]
rc = json.loads((OUT / 'r6_gen_check.json').read_text(encoding='utf-8'))
served = {e['base']: e['asset_named_by_the_shell'] for e in rc['entry_points']}
out = {'ran_at_local': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'ref': REF,
       'named_by_the_commander': NAMED, 'tip_read_now': now,
       'method': 'git ls-remote plus GET /compare/<named>...<now>; 0 builds, 0 requests to the phone chain, '
                 '0 refs written',
       'commits_ahead': cmp_.get('ahead_by'),
       'subjects': [(c['sha'][:10], (c['commit']['message'] or '').split('\n')[0])
                    for c in (cmp_.get('commits') or [])],
       'files_changed': files,
       'frontend_files_changed': [f for f in files if f.startswith('frontend/')],
       'touches_the_wizard_source': WIZARD in files,
       'asset_the_chain_served_during_my_walk': served,
       'what_i_did_not_do': 'no rebuild, no re-cut, no second walk; the readings stay bound to the bundle the '
                            'chain served while I took them'}
(OUT / 'r6_drift.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8', newline='\n')
print(json.dumps({'now': now, 'ahead': out['commits_ahead'], 'wizard_touched': out['touches_the_wizard_source'],
                  'frontend_files': out['frontend_files_changed'], 'subjects': out['subjects']},
                 ensure_ascii=False, indent=1))
