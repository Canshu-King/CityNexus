"""ORD-0300 C2 pairing batch - stage 1: three private trees, three private bundles, nothing shared touched.

Why this exists: the commander's challenge is that my C2 paired "server answered 500" with "the screen said
unreachable" by OUTCOME, not by request identity. Reading the two real generations gave me a discriminator I
did not have when I wrote that cell: on `dc964086…` the sheet's `serverReasonSentence` reads `body.detail`
with no null guard, so a plain-text 500 (body -> null) raises INSIDE the `HTTP_500` branch and the big catch
rewrites the card to `NETWORK`; on the newer tip that guard exists, so the very same answer must paint
`HTTP_500` with a technical-detail block. A transport death cannot produce that flip - only a response
object actually in the page's hands can.

Three trees, all read-only pulls by `git archive` (never `git apply`, never the working tree):
  old  = dc964086c9d412573ac19d70b24b30e6c3ee6168   the generation the challenge names
  new  = 5aff3722d5c36c760a424f5fea5c3a771298f9ac   the current authority
  mut  = a PRIVATE COPY of `new` with exactly the two guards put back to how `old` had them - the single
         variable that decides which card the traveller sees
Every bundle is built into my own outDir; the product tree, the release dist, the phone chain and the
authoritative line are never written.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import time

BASE = pathlib.Path('D:/moodle/_hjp3_0300c2_0925')
REPO = pathlib.Path('D:/moodle/CityNexus')
NM_SRC = REPO / 'frontend' / 'node_modules'
TIPS = {'old': 'dc964086c9d412573ac19d70b24b30e6c3ee6168',
        'new': '5aff3722d5c36c760a424f5fea5c3a771298f9ac'}
SHEET = 'frontend/src/features/planning/PlanWithAiSheet.tsx'
BLOBS = {'old': 'fd5f6e5ba2771a8d12669b9bec1ba91590970701',
         'new': 'f61d5312e8b33807d3e5304d1fa9fb7f77a518aa'}
UNGUARDED = '  const detail = (body as { detail?: unknown }).detail;'
GUARDED = '  const detail = (body as { detail?: unknown } | null)?.detail;'
DETACHED = 0x00000008 | 0x00000200


def sh(args, cwd=None, timeout=900):
    return subprocess.run(args, cwd=str(cwd) if cwd else None, capture_output=True, text=True,
                          encoding='utf-8', errors='replace', timeout=timeout)


def blob_of(path):
    d = pathlib.Path(path).read_bytes()
    return hashlib.sha1(b'blob %d' % len(d) + bytes([0]) + d).hexdigest()


def export(which, tip):
    snap = BASE / ('snap_' + which)
    if snap.exists():
        shutil.rmtree(snap)
    snap.mkdir(parents=True)
    r = subprocess.run(['git', 'archive', '--format=tar', tip, 'backend', 'frontend'], cwd=str(REPO),
                       capture_output=True, timeout=600)
    assert r.returncode == 0, 'git archive failed: ' + (r.stderr or '')[-300:]
    t = subprocess.run(['tar', '-xf', '-'], cwd=str(snap), input=r.stdout, timeout=600)
    assert t.returncode == 0, 'tar failed'
    gits = [str(p) for p in snap.rglob('.git')]
    assert not gits, 'a .git appeared inside my export: %s' % gits[:3]
    sheet = snap / SHEET
    assert sheet.exists(), 'no sheet in the export'
    return {'which': which, 'tip': tip, 'snap': str(snap), 'sheet_blob_recomputed_40_hex': blob_of(sheet),
            'sheet_blob_expected': BLOBS[which],
            'sheet_blob_matches_the_generation': blob_of(sheet) == BLOBS[which],
            'sheet_bytes': sheet.stat().st_size,
            'unguarded_detail_reads': sheet.read_text(encoding='utf-8').count(UNGUARDED),
            'guarded_detail_reads': sheet.read_text(encoding='utf-8').count(GUARDED)}


def make_mutant():
    """A private copy of `new` with ONLY the two guards reverted - one variable, not a generation swap."""
    src = BASE / 'snap_new'
    dst = BASE / 'snap_mut'
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(str(src), str(dst))
    f = dst / SHEET
    before = f.read_text(encoding='utf-8')
    n = before.count(GUARDED)
    assert n == 2, 'expected exactly 2 guarded reads, found %d - refusing to patch blind' % n
    after = before.replace(GUARDED, UNGUARDED)
    assert after.count(UNGUARDED) == 2 and after.count(GUARDED) == 0
    lines_before, lines_after = before.split(chr(10)), after.split(chr(10))
    changed = [i + 1 for i, (a, b) in enumerate(zip(lines_before, lines_after)) if a != b]
    f.write_text(after, encoding='utf-8', newline='\n')
    return {'dir': str(dst), 'lines_that_differ': changed, 'edits': n,
            'only_file_changed_vs_snap_new': [str(p.relative_to(dst)) for p in dst.rglob('*')
                                              if p.is_file() and p.suffix in ('.tsx', '.ts')
                                              and p.read_bytes() != (src / p.relative_to(dst)).read_bytes()],
            'sheet_sha256_new': hashlib.sha256((src / SHEET).read_bytes()).hexdigest(),
            'sheet_sha256_mut': hashlib.sha256(f.read_bytes()).hexdigest(),
            'sheet_blob_mut': blob_of(f), 'hardlink_free_note': 'copytree, no junctions inside src'}


def junction(frontend_dir):
    nm = frontend_dir / 'node_modules'
    if nm.exists() or nm.is_symlink():
        return str(nm) + ' already present'
    r = sh(['cmd', '/c', 'mklink', '/J', str(nm), str(NM_SRC)])
    assert nm.exists(), 'junction not made: ' + (r.stdout or '') + (r.stderr or '')
    return 'junction created'


def build(which, frontend_dir, outdir):
    if outdir.exists():
        shutil.rmtree(outdir)
    log = sh(['node', 'node_modules/vite/bin/vite.js', 'build', '--outDir', str(outdir),
              '--emptyOutDir'], cwd=frontend_dir, timeout=1200)
    (BASE / ('build_%s.log' % which)).write_text((log.stdout or '') + chr(10) + 'STDERR:'
                                                 + (log.stderr or '')[-3000:], encoding='utf-8',
                                                 newline='\n')
    assert log.returncode == 0, 'build failed for %s, rc=%d (see build_%s.log)' % (which, log.returncode, which)
    html = (outdir / 'index.html').read_text(encoding='utf-8', errors='replace')
    asset = re.findall(r'assets/(index-[A-Za-z0-9_-]+\.js)', html)[0]
    raw = (outdir / 'assets' / asset).read_bytes()
    text = raw.decode('utf-8', 'replace')
    return {'which': which, 'outdir': str(outdir), 'asset': asset, 'bytes': len(raw),
            'sha256_64_hex': hashlib.sha256(raw).hexdigest(),
            'markers': {'network_card_wording': '连不上服务端' in text,
                        'device_note_for_network_branch': 'no readable answer reached this device' in text,
                        'http_branch_wording': 'agent/commands -> HTTP ' in text,
                        'technical_detail_wording': '技术详情' in text},
            'build_rc': log.returncode}


if __name__ == '__main__':
    BASE.mkdir(exist_ok=True)
    out = {'ran_at_local': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'repo': str(REPO),
           'repo_head_read_only': sh(['git', 'rev-parse', 'HEAD'], cwd=REPO).stdout.strip(),
           'tips_used': TIPS, 'exports': {}, 'mutant': None, 'bundles': {}}
    for which, tip in TIPS.items():
        out['exports'][which] = export(which, tip)
        print('exported', which, out['exports'][which]['sheet_blob_matches_the_generation'],
              'unguarded:', out['exports'][which]['unguarded_detail_reads'],
              'guarded:', out['exports'][which]['guarded_detail_reads'], flush=True)
        assert out['exports'][which]['sheet_blob_matches_the_generation'], 'wrong generation exported'
    out['mutant'] = make_mutant()
    print('mutant:', json.dumps(out['mutant'], ensure_ascii=False)[:300], flush=True)
    for which in ('old', 'new', 'mut'):
        fd = BASE / ('snap_%s' % which) / 'frontend'
        print('junction', which, junction(fd), flush=True)
        b = build(which, fd, BASE / ('dist_%s' % which))
        out['bundles'][which] = b
        print('built', which, b['asset'], b['bytes'], b['sha256_64_hex'][:16],
              json.dumps(b['markers'], ensure_ascii=False), flush=True)
    out['bundle_discriminators'] = {
        'new_has_the_device_note_and_old_does_not':
            out['bundles']['new']['markers']['device_note_for_network_branch']
            and not out['bundles']['old']['markers']['device_note_for_network_branch'],
        'mut_bundle_differs_from_new_bundle': out['bundles']['mut']['sha256_64_hex']
        != out['bundles']['new']['sha256_64_hex'],
        'old_new_mut_all_three_are_different_bytes':
            len({out['bundles'][k]['sha256_64_hex'] for k in ('old', 'new', 'mut')}) == 3}
    (BASE / 'setup_facts.json').write_text(json.dumps(out, ensure_ascii=False, indent=1),
                                           encoding='utf-8', newline='\n')
    print(json.dumps(out['bundle_discriminators'], ensure_ascii=False))
    print('SHA256 of the three bundles:')
    for k, v in out['bundles'].items():
        print('  ', k, v['asset'], v['bytes'], v['sha256_64_hex'])
