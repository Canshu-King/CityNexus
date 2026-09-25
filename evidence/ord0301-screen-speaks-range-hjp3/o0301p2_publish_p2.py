"""ORD-0301 pass 2 publisher: NEW remote names only - nothing already on the branch is rewritten.

Two rules this file exists to obey:
  1. the commander's 15:1x word - 加格子一律新文件名. A published path is never re-PUT, so every remote
     name in the plan below is checked against what pass 1 actually published, and the batch refuses to
     run if any of them collides;
  2. the instruments changed between the passes (ports now come from the live rig, the abort arm, one
     extra key). The pass-1 receipt was produced by the pass-1 bytes, so the pass-1 instrument files are
     left exactly as they were published and the pass-2 revisions go out under `o0301p2_*` names.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import sys

B = pathlib.Path('D:/moodle/_hjp3_0301_0925')
SRC = pathlib.Path('D:/moodle/HJ-P3_evidence')
R5 = pathlib.Path('D:/moodle/_hjp3_0279_0924/publish_evidence_r5.py')
PREFIX = 'evidence/ord0301-screen-speaks-range-hjp3'
sys.path.insert(0, str(SRC))
import importlib.util as iu

spec = iu.spec_from_file_location('pub1', str(SRC / 'o0301_publish.py'))
m = iu.module_from_spec(spec)
spec.loader.exec_module(m)

T = json.loads((B / 'table_O0301.json').read_text(encoding='utf-8'))
P2_RUNS = {r['arm']: r['run_id'] for r in T['rows']
           if int(''.join(ch for ch in r['row'].split('_')[0] if ch.isdigit())) >= 18}

NEW = [
    (B / 'RECEIPT_O0301P2-1540.json', 'RECEIPT_O0301P2-1540.json',
     'machine receipt pass 2: five cells for the classes written in the dispatch'),
    (B / 'RECEIPT_O0301P2-1540.md', 'RECEIPT_O0301P2-1540.md',
     'human supplement pass 2: what I had missed and the seven new rows'),
    (B / 'table_O0301.json', 'table_O0301_p2_24rows.json',
     'the range table grown to 24 rows (the published 17-row file stays untouched)'),
    (B / 'q38_ruler_p2.txt', 'q38_ruler_p2.txt', 'the Q38 ruler over the pass-2 receipt'),
    (B / 'boundary_proof_o0301p2.json', 'boundary_proof_o0301p2.json',
     'pass-2 boundary proof, including the served generation that changed mid-batch'),
    (B / 'teardown_O0301P2_r1.txt', 'teardown_O0301P2_r1.txt', 'pass-2 teardown written to a file this time'),
    (B / 'o0301p2_state.json', 'o0301p2_state.json', 'pass-2 rig: new ports, fresh one-time db, bundle bytes'),
    (B / 'o0301p2_pids.json', 'o0301p2_pids.json', 'pass-2 pids'),
    (B / 'mission_bad_status.json', 'mission_bad_status.json',
     'the fixture behind the 200-with-an-unusable-status arm'),
]

INSTRUMENTS_P2 = [
    ('o0301_rig.py', 'instrument p2: ports and state file come from the live rig, not hardcoded'),
    ('o0301_runarm.py', 'instrument p2: the seven new arms and the route-abort switch'),
    ('o0301_score.py', 'instrument p2: 24 rows, class coverage, the other surface keeps elapsed_ms'),
    ('o0301_cells.cjs', 'instrument p2: route.abort on the tapped leg only'),
    ('o0301_bounds.py', 'instrument p2: proof reads whichever rig is live'),
    ('o0301_receipt_p2.py', 'instrument r2: the five pass-2 cells, with the discarded-run slice fixed'),
    ('o0301_md_p2.py', 'instrument: this supplement rendered from the same artefacts'),
]
# the receipt builder changed after the first flight (the discarded-run slice fix), so its revision
# goes out as _r2 rather than over the name the first flight already used
REMOTE_OVERRIDE = {'o0301_receipt_p2.py': 'o0301p2_o0301_receipt_p2_r2.py'}
for name, why in INSTRUMENTS_P2:
    NEW.append(((SRC / name) if name.endswith('.py') else (B / name),
                REMOTE_OVERRIDE.get(name, 'o0301p2_' + name), why))

for arm, run in sorted(P2_RUNS.items()):
    for pat, why in (('cell_%s_%s.json', 'pass-2 arm: both sides read'),
                     ('probe_%s_%s.json', 'who answered this leg, probed outside the browser'),
                     ('originlog_%s_%s.jsonl', "the origin's own record for this run")):
        pp = B / (pat % (arm, run))
        if pp.exists():
            NEW.append((pp, pp.name, why))
    sp = B / ('spec_%s.json' % arm)
    if sp.exists():
        NEW.append((sp, 'spec_%s.json' % arm, 'the outcome declared before the arm ran'))
    for shot in sorted(B.glob('shots_%s-%s-end.png' % (run, arm))):
        NEW.append((shot, shot.name, 'what the traveller was left with in this row'))

# the seven disclosed dead executions: probe + origin record exist, no cell
FAILED = sorted([p for p in B.glob('probe_a*') if not (B / ('cell_' + p.name[len('probe_'):])).exists()])
for p in FAILED:
    NEW.append((p, p.name, 'DISCLOSED: one of seven executions that fired at a face I had already stopped'))
    q = B / ('originlog_' + p.name[len('probe_'):-len('.json')] + '.jsonl')
    if q.exists():
        NEW.append((q, q.name, 'the origin record of that same discarded execution'))

def published_on_branch():
    """What is actually on the branch, read from the tree - not what a local listing happens to contain
    now (my first pass derived the comparison from the live table, which by pass 2 already lists these
    very files, so every pass-2 name looked like a collision)."""
    def with_retry(fn, what):
        import time
        last = None
        for attempt in range(5):
            try:
                return fn()
            except Exception as e:  # noqa: BLE001
                last = e
                print('  retry %d on %s: %s' % (attempt + 1, what, str(e)[:60]), flush=True)
                time.sleep(2 + 2 * attempt)
        raise SystemExit('branch listing unavailable (%s): %s' % (what, last))
    tip = with_retry(lambda: m.api('/git/ref/heads/' + m.BRANCH)['object']['sha'], 'ref')
    tree = with_retry(lambda: m.api('/git/trees/' + tip + '?recursive=1')['tree'], 'tree')
    return {e['path'].split('/')[-1]: e['sha'] for e in tree if e['path'].startswith(PREFIX + '/')}


def blob_of(path):
    data = path.read_bytes()
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + bytes([0]) + data).hexdigest()


PUBLISHED_PASS1 = published_on_branch()


def classify():
    """EVIDENCE_INTEGRITY_GATE_V1, applied to my own pushes: a name that is already on the branch is
    only allowed if the bytes are byte-identical (then it is skipped, not re-pushed). A different blob
    under an existing name is an overwrite and the batch refuses."""
    keep, identical, refuse = [], [], []
    for path, remote, msg in NEW:
        if remote in PUBLISHED_PASS1:
            if PUBLISHED_PASS1[remote] == blob_of(path):
                identical.append(remote)
                continue
            refuse.append(remote)
            keep.append((path, remote, msg))
        else:
            keep.append((path, remote, msg))
    return keep, identical, refuse


KEEP, IDENTICAL, COLLIDE = classify()
plan = {'files': [r for _, r, _ in KEEP], 'bytes': sum(pt.stat().st_size for pt, _, _ in KEEP),
        'skipped_already_published_byte_identical': IDENTICAL,
        'overwrites_refused': COLLIDE,
        'gate': 'a name already on the branch may only be re-planned with byte-identical content; the '
                'push is then skipped, never re-PUT (EVIDENCE_INTEGRITY_GATE_V1 applied to my own pushes)',
        'names_already_on_the_branch_when_planning': len(PUBLISHED_PASS1),
        'discarded_executions': [p.name for p in FAILED]}
(B / 'publish_plan_p2.json').write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding='utf-8')
print('planned %d files / %d bytes | skipped identical %d | overwrites refused %s'
      % (len(plan['files']), plan['bytes'], len(IDENTICAL), COLLIDE))
if COLLIDE:
    raise SystemExit('refusing to publish over a name pass 1 already used')
if len(set(plan['files'])) != len(plan['files']):
    raise SystemExit('duplicate remote name inside this batch')

def push(items):
    res = []
    for p, remote, msg in items:
        r = subprocess.run([sys.executable, str(R5), str(p), PREFIX + '/' + remote,
                            'docs(evidence): ORD-0301 pass 2 HJ-P3 %s' % msg[:70]],
                           capture_output=True, text=True, encoding='utf-8', errors='replace')
        res.append({'remote': remote, 'rc': r.returncode,
                    'tail': (r.stdout or '').strip().splitlines()[-2:]})
        if r.returncode != 0:
            print(json.dumps(res[-1], ensure_ascii=False), flush=True)
    ok = sum(1 for x in res if x['rc'] == 0)
    print('published=%d/%d' % (ok, len(res)))
    if ok != len(res):
        raise SystemExit('partial publication - stopping, nothing will be retried under an old name')
    return res


MD = next((i for i in KEEP if i[1] == 'RECEIPT_O0301P2-1540.md'), None)
REST = [i for i in KEEP if i is not MD]

if __name__ == '__main__':
    stage = sys.argv[1] if len(sys.argv) > 1 else 'rest'
    if stage == 'rest':
        push(REST)
        line, rows = m.coords_line()
        (B / 'coords_line_p2_batch.txt').write_text(line, encoding='utf-8', newline='\n')
        print('on branch after the rest:', len(rows), 'bytes', sum(x['size'] or 0 for x in rows))
    elif stage == 'md':
        if MD is None:
            print('the supplement is already on the branch, byte-identical - nothing to push')
            raise SystemExit(0)
        md = MD[0].read_text(encoding='utf-8')
        assert '%COORD%' in md, 'the supplement lost its coordinate placeholder'
        line = (B / 'coords_line_p2_batch.txt').read_text(encoding='utf-8')
        MD[0].write_text(md.replace('%COORD%', '**发布与坐标（本批其余 57 件先落架，本件随后）**：' + line),
                         encoding='utf-8', newline='\n')
        push([MD])
        line2, rows2 = m.coords_line()
        (B / 'coords_line_p2_final.txt').write_text(line2, encoding='utf-8', newline='\n')
        print('FINAL on branch:', len(rows2), 'bytes', sum(x['size'] or 0 for x in rows2))
    else:
        raise SystemExit('unknown stage')
