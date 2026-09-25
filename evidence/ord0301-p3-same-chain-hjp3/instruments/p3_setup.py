"""ORD-0301 pass 3, stage 1: build the generation the shared chain actually serves, and PROVE which one it is.

Why this exists: the commander's 21:5x note said the phone sits on `dc964086…` (swapped 15:19), while my own
20:0x note claimed the served asset equalled my `5aff3722` build. Both readings are wrong, and mine was worse
than wrong - it was manufactured: I fetched an asset path I had picked out of my own build list instead of the
one the served page references. So this stage does three things in order:

  1. read the served `index.html` and take the asset name FROM IT (regex on the reference, not a guess);
  2. read that asset and hash it;
  3. export the candidate commit with `git archive` (read-only; never `git apply`), build it into my own
     outDir, and compare byte-for-byte.

If (2) and (3) agree, everything measured downstream in this batch is on the deployed generation, by bytes.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import shutil
import subprocess
import time
import urllib.request

BASE = pathlib.Path('D:/moodle/_hjp3_0301p3_0925')
REPO = pathlib.Path('D:/moodle/CityNexus')
NM_SRC = REPO / 'frontend' / 'node_modules'
CANDIDATES = ['7856e03f6238da3000976eb6e690a448dfa39b9a', 'dc964086c9d412573ac19d70b24b30e6c3ee6168',
              '5aff3722d5c36c760a424f5fea5c3a771298f9ac']
SHEET = 'frontend/src/features/planning/PlanWithAiSheet.tsx'


def sh(args, cwd=None, timeout=1800):
    return subprocess.run([str(a) for a in args], cwd=str(cwd or BASE), capture_output=True,
                          text=True, encoding='utf-8', errors='replace', timeout=timeout)


def get(url, timeout=60):
    r = urllib.request.Request(url)
    r.add_header('User-Agent', 'hjp3-0301p3-read')
    with urllib.request.urlopen(r, timeout=timeout) as f:
        return f.status, f.read()


def sha(d):
    return hashlib.sha256(d).hexdigest()


def blob_of(p):
    d = pathlib.Path(p).read_bytes()
    return hashlib.sha1(b'blob %d\0' % len(d) + d).hexdigest(), len(d)


# 1 + 2: what the chain serves, read the honest way - the name comes out of the served document
st, idx = get('http://127.0.0.1:4781/')
html = idx.decode('utf-8', 'replace')
ref = re.search(r'''["'](/assets/index-[^"']+\.js)["']''', html)
served = {'index_http_status': st, 'index_bytes': len(idx), 'index_sha256_64_hex': sha(idx),
          'asset_referenced_by_the_served_page': ref.group(1) if ref else None}
if ref:
    s2, ab = get('http://127.0.0.1:4781' + ref.group(1))
    served.update({'asset_http_status': s2, 'asset_bytes': len(ab), 'asset_sha256_64_hex': sha(ab)})
out = {'ran_at_local': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'requests_made': 2,
       'methods': ['GET', 'GET'], 'writes': 0, 'credentials_sent': False,
       'how_the_asset_name_was_taken': 'regular expression over the served index.html, not a name from my '
                                       'own build list - the mistake this stage exists to avoid repeating',
       'served': served, 'builds': {}}

for tip in CANDIDATES:
    tag = tip[:8]
    snap = BASE / ('snap_%s' % tag)
    dist = BASE / ('dist_%s' % tag)
    if snap.exists():
        shutil.rmtree(snap)
    snap.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(['git', '-C', str(REPO), 'archive', '--format=tar', tip], capture_output=True)
    assert r.returncode == 0, 'git archive failed for ' + tip
    import tarfile
    import io
    with tarfile.open(fileobj=io.BytesIO(r.stdout)) as tf:
        tf.extractall(path=str(snap))
    sb, sb_len = blob_of(snap / SHEET)
    txt = (snap / SHEET).read_text(encoding='utf-8').splitlines()
    nm = snap / 'frontend' / 'node_modules'
    if not nm.exists():
        mk = sh(['cmd', '/c', 'mklink', '/J', str(nm), str(NM_SRC)])
        assert nm.exists(), 'junction not made: ' + (mk.stdout or '') + (mk.stderr or '')
    b = sh(['node', 'node_modules/vite/bin/vite.js', 'build', '--outDir', str(dist), '--emptyOutDir'],
           cwd=snap / 'frontend', timeout=1800)
    entry = {'tip': tip, 'git_archive_rc': r.returncode, 'sheet_blob_40_hex': sb, 'sheet_bytes': sb_len,
              'unguarded_detail_reads': sum(1 for x in txt if re.search(r'unknown \}\)\.detail', x)),
              'guarded_detail_reads': sum(1 for x in txt if re.search(r'\| null\)\?\.detail', x)),
              'device_note_lines': [i + 1 for i, x in enumerate(txt)
                                    if 'no readable answer reached this device' in x],
              'build_rc': b.returncode}
    if b.returncode == 0:
        h = (dist / 'index.html').read_text(encoding='utf-8', errors='replace')
        m = re.search(r'''["'](/assets/index-[^"']+\.js)["']''', h)
        entry['built_asset'] = m.group(1) if m else None
        raw = (dist / m.group(1).lstrip('/')).read_bytes()
        entry['built_bytes'] = len(raw)
        entry['built_sha256_64_hex'] = sha(raw)
        entry['equals_the_served_asset'] = (sha(raw) == served.get('asset_sha256_64_hex'))
    out['builds'][tag] = entry
    print('%s build_rc=%s asset=%s equals_served=%s' % (tag, b.returncode, entry.get('built_asset'),
                                                        entry.get('equals_the_served_asset')), flush=True)

match = [t for t, v in out['builds'].items() if v.get('equals_the_served_asset')]
out['verdict'] = {
    'served_asset_name_taken_from_the_served_page': bool(served.get('asset_referenced_by_the_served_page')),
    'exactly_one_candidate_build_equals_the_served_asset': len(match) == 1,
    'which_candidate_it_is': match[0] if match else None,
    'served_tip_full_40_hex': out['builds'][match[0]]['tip'] if len(match) == 1 else None,
    'commander_claim_that_the_phone_is_on_dc964086': bool(
        len(match) == 1 and match[0] == 'dc964086'),
    'my_own_20_0x_claim_that_it_was_5aff3722': bool(len(match) == 1 and match[0] == '5aff3722')}
(BASE / 'served_generation_bind_c2.json').write_text(json.dumps(out, ensure_ascii=False, indent=1),
                                                    encoding='utf-8', newline='\n')
print(json.dumps(out['verdict'], ensure_ascii=False, indent=1))
print('served asset:', served.get('asset_referenced_by_the_served_page'), served.get('asset_bytes'),
      served.get('asset_sha256_64_hex'))
