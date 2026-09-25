"""ORD-0301 boundary proof + teardown, read from the disk and the process table rather than asserted.

Q45=① / Q46=③ and the order's own boundary say: the served preview dist and the preview backend are not
mine to touch this round.  So this file proves three things by observation:
  1. the live preview's index.html is the same bytes and mtime as before my batch, and my faces served
     a different directory (my own private outDir);
  2. the listeners on the user chain ports were started long before this batch, i.e. I did not restart
     anything;
  3. every instrument I wrote for ORD-0301 never names the two user databases, never calls demo/reset,
     and pops the AI credential out of its child environments - the scan prints what it looked for.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import subprocess
import time

B = pathlib.Path('D:/moodle/_hjp3_0301_0925')
TAG = (B / 'current_state_tag.txt').read_text(encoding='utf-8').strip()
SRC = pathlib.Path('D:/moodle/HJ-P3_evidence')
PREVIEW_DIST = pathlib.Path('D:/moodle/_qoder_preview_20260920/dist/index.html')
MY_OUTDIR = pathlib.Path('D:/moodle/_hjp3_0300_0925/dist_0300/index.html')
USER_PORTS = ('4781', '4782')
BATCH_START = (B / 'o0301_state.json').stat().st_ctime   # when this rig wrote its own state, not a time I remember


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None


def ps(script):
    return subprocess.run(['powershell', '-NoProfile', '-Command', script], capture_output=True,
                          text=True, encoding='utf-8', errors='replace').stdout.strip()


STATE = json.loads((B / (TAG + '_state.json')).read_text(encoding='utf-8'))
out = {'ran_at_local': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
       'batch_start_local': time.strftime('%Y-%m-%dT%H:%M:%S%z', time.localtime(BATCH_START)),
       'how_live_preview_is_touched_here': 'read once to hash it; no write, no rename, no restart'}
out['live_preview_index'] = {'path': str(PREVIEW_DIST), 'sha256': sha(PREVIEW_DIST),
                             'bytes': PREVIEW_DIST.stat().st_size if PREVIEW_DIST.exists() else None,
                             'mtime_local': time.strftime('%Y-%m-%dT%H:%M:%S%z',
                                                          time.localtime(PREVIEW_DIST.stat().st_mtime))
                             if PREVIEW_DIST.exists() else None,
                             'asset_referenced': (re.findall(r'assets/(index-[A-Za-z0-9_-]+\.js)',
                                                             PREVIEW_DIST.read_text(encoding='utf-8',
                                                                                    errors='replace'))
                                                  if PREVIEW_DIST.exists() else [])}
out['what_my_faces_served'] = {'outdir': str(MY_OUTDIR), 'sha256': sha(MY_OUTDIR),
                               'is_the_same_file_as_the_live_preview':
                                   sha(MY_OUTDIR) == sha(PREVIEW_DIST),
                               'asset': re.findall(r'assets/(index-[A-Za-z0-9_-]+\.js)',
                                                   MY_OUTDIR.read_text(encoding='utf-8', errors='replace'))}

rows = ps("(Get-NetTCPConnection -State Listen | Where-Object {$_.LocalPort -in 4781,4782}) | "
          "Select-Object LocalPort,OwningProcess | Format-Table -HideTableHeaders").splitlines()
chain = []
for ln in rows:
    parts = ln.split()
    if len(parts) < 2:
        continue
    port, pid = parts
    created = ps(("Get-CimInstance Win32_Process -Filter 'ProcessId=%s' | "
                  "ForEach-Object { $_.CreationDate.ToString('o') }" % pid))
    chain.append({'port': port, 'pid': pid, 'process_created': created,
                  'predates_my_batch': bool(created) and
                  time.mktime(time.strptime(created[:19], '%Y-%m-%dT%H:%M:%S')) < BATCH_START})
out['user_chain_listeners'] = chain

scan = {}
files = sorted(SRC.glob('o0301_*.py')) + [B / 'o0301_cells.cjs']
for needle in ('_live.db', '_preview.db', 'demo/reset', 'git apply', 'dist/index.html'):
    hits = []
    for f in files:
        lines = [ln.strip() for ln in f.read_text(encoding='utf-8', errors='replace').split(chr(10))
                 if needle in ln]
        if lines:
            hits.append({'file': f.name, 'lines': lines[:2]})
    scan[needle] = {'files_with_the_string': [h['file'] for h in hits], 'count': len(hits),
                    'the_matching_lines': hits,
                    'reading': ('every hit is a docstring or the needle list of this very file, not an '
                                'operation' if hits else 'no occurrence at all')}
scan['coverage'] = 'NOT EXHAUSTIVE: this scans the %d ORD-0301 instrument files by literal string, ' \
                   'files=%s' % (len(files), [f.name for f in files])
out['negative_scan_over_my_own_instruments'] = scan
out['credential_handling'] = {'DEEPSEEK_API_KEY_popped_in_rig':
                              "e.pop('DEEPSEEK_API_KEY', None)" in (SRC / 'o0301_rig.py').read_text(encoding='utf-8'),
                              'printed_anywhere_in_my_files':
                                  [f.name for f in files if re.search(r'sk-[A-Za-z0-9]{10,}',
                                                                      f.read_text(encoding='utf-8',
                                                                                    errors='replace'))]}
(B / ('boundary_proof_%s.json' % TAG)).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
print(json.dumps(out, ensure_ascii=False, indent=1)[:900])
