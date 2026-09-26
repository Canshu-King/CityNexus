"""Did the mirror ref move out from under the generation I was told to re-measure? Read-only, no build, no walk.

The commander named `ab12c17a…` for my single re-run. This instrument reads the ref twice over the hour and asks
GitHub how many commits separate the named tip from the current one and which files they touch. It deliberately
does NOT rebuild the newer tip and does NOT walk the chain again: 换代归号令者, and he asked for one pass. The
product of this file is a dated fact - if the newer commits touch the wizard's own source, then any reading taken
on `ab12c17a` is already behind the line, and he should know that before grading my numbers.
"""
from __future__ import annotations

import importlib.util as iu
import json
import pathlib
import subprocess
import time

OUT = pathlib.Path('D:/moodle/_hjp3_0323walk_0926')
SRC = pathlib.Path('D:/moodle/HJ-P3_evidence')
spec = iu.spec_from_file_location('pub', str(SRC / 'p3_publish.py'))
pub = iu.module_from_spec(spec)
spec.loader.exec_module(pub)

REF = 'refs/heads/mirror/integration-frontend-apple-pass1'
NAMED = 'ab12c17a65450c2c3062c9232e27a26c4ae1b485'
WIZARD = 'frontend/src/features/setup/JourneyTrialSetup.tsx'
lr = subprocess.run(['git', '-C', 'D:/moodle/CityNexus', 'ls-remote', 'origin', REF],
                    capture_output=True, text=True, encoding='utf-8', errors='replace')
now = ([l.split()[0] for l in (lr.stdout or '').splitlines() if l.strip()] + [None])[0]
cmp_ = pub.api('/compare/%s...%s' % (NAMED, now)) if now else {}
files = [f.get('filename') for f in (cmp_.get('files') or [])]
fe = [f for f in files if f.startswith('frontend/')]
out = {'ran_at_local': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
       'method': 'git ls-remote of ' + REF + ' plus GET /compare/<named>...<now> over the GitHub API; '
                 '0 builds run, 0 requests to the phone chain, 0 refs written',
       'generation_named_by_the_commander': NAMED,
       'mirror_tip_read_now': now,
       'tip_equals_the_named_generation': now == NAMED,
       'commits_ahead': cmp_.get('ahead_by'),
       'compare_status': cmp_.get('status'),
       'commits': [{'sha': c['sha'], 'subject': (c['commit']['message'] or '').split('\n')[0]}
                   for c in (cmp_.get('commits') or [])],
       'files_changed': files,
       'frontend_files_changed': fe,
       'touches_the_wizard_source': WIZARD in files,
       'what_i_did_not_do': 'I did not re-cut, rebuild or re-walk. Deploying a generation is the commander\'s '
                            'action, and my one allowed pass on the named generation is already recorded'}
(OUT / 'r5_tip_drift.json').write_text(json.dumps(out, ensure_ascii=False, indent=1),
                                       encoding='utf-8', newline='\n')
print(json.dumps({'now': now, 'ahead_by': out['commits_ahead'], 'status': out['compare_status'],
                  'frontend_files': fe, 'touches_wizard': out['touches_the_wizard_source']},
                 ensure_ascii=False, indent=1))
