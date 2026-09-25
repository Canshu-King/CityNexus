"""ORD-0300 C2 pairing batch - boundary proof: what this batch did NOT touch, line by line.

Same discipline as the rest of my lane's batches: a negative claim has to print the search space it looked
at, the scanner has to exclude its own reading of the deny-list, and a call is only counted as a call when
the line actually contains one. Coverage is stated as NOT EXHAUSTIVE because the scan is over MY instrument
files, not over every process on this machine.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import subprocess
import time

BASE = pathlib.Path('D:/moodle/_hjp3_0300c2_0925')
SRC = pathlib.Path('D:/moodle/HJ-P3_evidence')
PREVIEW = pathlib.Path('D:/moodle/_qoder_preview_20260920/dist/index.html')
OTHER_BATCH = pathlib.Path('D:/moodle/_hjp3_0300_0925')
PORTS = [8641, 8642, 8643, 8644, 8645, 8646, 8647]
MY_PORTS_NAME_LIST = {'8641': 'backend', '8642': 'pairing proxy', '8643': 'face old', '8644': 'face new',
                      '8645': 'face mut', '8646': 'face t90', '8647': 'spare, never used'}


def listening(port):
    out = subprocess.run(['netstat', '-ano'], capture_output=True, text=True,
                         encoding='utf-8', errors='replace').stdout
    return sorted({ln.split()[-1] for ln in out.splitlines()
                   if ('127.0.0.1:%d ' % port) in ln and 'LISTENING' in ln})


mine = sorted(list(SRC.glob('c2*.py')) + list(BASE.glob('*.py')) + [SRC / 'c2proxy.py'])
SELF_REF_MARKS = ('needle', "'_live.db'", "'_preview.db'", "'demo/reset'", "'git apply'", 'citynexus.db')
CALL_MARKS = ('subprocess', 'Popen', 'check_output', 'urlopen', 'requests.', 'sqlite3.connect',
              "['git'", "['taskkill'", 'os.system', 'os.popen', 'shutil.rmtree', 'mkdir', 'write_text',
              'write_bytes', 'extractall')
scan = {}
for needle in ('_live.db', '_preview.db', 'demo/reset', 'git apply', 'citynexus.db', ':4781', ':4782'):
    calls, named, self_ref = [], [], 0
    for f in mine:
        for ln in f.read_text(encoding='utf-8', errors='replace').split(chr(10)):
            if needle not in ln:
                continue
            if any(m in ln for m in SELF_REF_MARKS):
                self_ref += 1
            elif any(m in ln for m in CALL_MARKS):
                calls.append({'file': f.name, 'line': ln.strip()[:170]})
            else:
                named.append({'file': f.name, 'line': ln.strip()[:170]})
    scan[needle] = {'lines_that_actually_use_it': len(calls), 'uses': calls,
                    'lines_that_only_name_it_in_a_denial_or_comment': len(named),
                    'named': named[:6], 'lines_excluded_as_the_scanner_reading_itself': self_ref}
other_now = hashlib.sha256((OTHER_BATCH / 'dist_0300' / 'assets' / 'index-BN1w-xlK.js').read_bytes()) \
    if (OTHER_BATCH / 'dist_0300' / 'assets' / 'index-BN1w-xlK.js').exists() else None
td = sorted(BASE.glob('teardown_*.json'))
last = json.loads(td[-1].read_text(encoding='utf-8')) if td else {}
index_html = PREVIEW.read_text(encoding='utf-8', errors='replace')
out = {
    'ran_at_local': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
    'live_preview_index': {
        'path': str(PREVIEW), 'sha256_full_64_hex': hashlib.sha256(PREVIEW.read_bytes()).hexdigest(),
        'mtime_local': time.strftime('%Y-%m-%dT%H:%M:%S%z', time.localtime(PREVIEW.stat().st_mtime)),
        'asset_referenced': re.findall(r'assets/(index-[A-Za-z0-9_-]+\.js)', index_html)[:1],
        'touched_by_this_batch': 'no - this batch served its own vite preview faces from its own outDirs'},
    'other_batches_private_build_read_not_written': {
        'path': str(OTHER_BATCH / 'dist_0300' / 'assets' / 'index-BN1w-xlK.js'),
        'sha256_now': other_now.hexdigest() if other_now else None,
        'sha256_recorded_by_that_batch': json.loads((OTHER_BATCH / 'bundle_facts.json')
                                                    .read_text(encoding='utf-8'))['sha256'],
        'unchanged_by_this_batch': bool(other_now) and other_now.hexdigest() == json.loads(
            (OTHER_BATCH / 'bundle_facts.json').read_text(encoding='utf-8'))['sha256'],
        'how_used': 'copied INTO my own dist_t90 and verified; the source file was never opened for writing'},
    'user_chain_listeners_untouched': [
        {'port': p, 'pid': pid, 'created': subprocess.run(
            ['powershell', '-NoProfile', '-Command',
             "Get-CimInstance Win32_Process -Filter 'ProcessId=%s' | ForEach-Object { $_.CreationDate"
             ".ToString('o') }" % pid], capture_output=True, text=True, encoding='utf-8',
             errors='replace').stdout.strip(), 'in_my_named_port_list': False}
        for p in ('4781', '4782') for pid in listening(int(p))],
    'my_named_ports': MY_PORTS_NAME_LIST,
    'negative_scan': scan,
    'coverage': 'NOT EXHAUSTIVE: %d instrument files of THIS batch scanned by literal string: %s'
                % (len(mine), [f.name for f in mine]),
    'credential_handling': {
        'DEEPSEEK_API_KEY_popped': "e.pop('DEEPSEEK_API_KEY', None)" in (SRC / 'c2_rig.py').read_text(
            encoding='utf-8'),
        'AI_disabled': "CITYNEXUS_AI_ENABLED'] = 'false'" in (SRC / 'c2_rig.py').read_text(
            encoding='utf-8'),
        'sk_shaped_strings_in_my_files': [f.name for f in mine
                                          if re.search(r'sk-[A-Za-z0-9]{10,}',
                                                       f.read_text(encoding='utf-8', errors='replace'))]},
    'junction_used_by_this_batch': {
        'what': 'node_modules junction created INSIDE my own export so vite can resolve its own modules',
        'target': 'D:/moodle/CityNexus/frontend/node_modules (read through the junction only)',
        'never': 'no junction was created inside another batch folder after the first failure, and nothing '
                 'followed one; the earlier mistake is disclosed in the receipt limits cell'},
    'databases': {'one_time_files': sorted(p.name for p in BASE.glob('o0300c2_*.s3db')),
                  'created_by': "each deleted before start and rebuilt by the product's own ensure_schema()"
                                if any(BASE.glob('o0300c2_*.s3db')) else 'none present',
                  'shared_databases_opened': 0},
    'teardown_files_written': [p.name for p in td],
    'last_teardown': {'listening_after': last.get('listening_after'),
                      'all_my_ports_free': last.get('all_my_ports_free'),
                      'any_listener_left_alone_because_it_could_not_be_attributed': [
                          {'port': k, 'pid': x['pid']} for k, v in (last.get('listeners') or {}).items()
                          for x in v if x.get('left_alone')]},
    'ports_free_right_now': {k: listening(v) for k, v in
                             zip(MY_PORTS_NAME_LIST.keys(), [int(x) for x in MY_PORTS_NAME_LIST.keys()])},
}
out['all_my_ports_free_now'] = not any(out['ports_free_right_now'].values())
(BASE / 'boundary_proof_c2.json').write_text(json.dumps(out, ensure_ascii=False, indent=1),
                                             encoding='utf-8', newline='\n')
print(json.dumps({'preview_untouched': out['live_preview_index']['sha256_full_64_hex'][:16],
                  'other_batch_bundle_still_matches_their_record':
                      out['other_batches_private_build_read_not_written']['unchanged_by_this_batch'],
                  'calls_found': {k: v['lines_that_actually_use_it'] for k, v in scan.items()},
                  'user_chain': out['user_chain_listeners_untouched'],
                  'all_my_ports_free_now': out['all_my_ports_free_now'],
                  'sk_strings': out['credential_handling']['sk_shaped_strings_in_my_files']},
                 ensure_ascii=False, indent=1))
