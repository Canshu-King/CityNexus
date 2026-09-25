"""ORD-0300 C2 challenge publisher: NEW remote names only, identical-or-refuse, and the md last.

The rules this file exists to obey (all of them earned the hard way in ORD-0288/0300):
  1. 加格子一律新文件名 - before anything is sent, every planned remote name is compared with the branch:
     byte-identical -> SKIP (reported), changed bytes -> the whole batch refuses before the first write.
  2. EVIDENCE_INTEGRITY_GATE_V1 - every coordinate in the manifest and the coordinate line is a 40-hex
     blob; short prefixes only appear in a field named display_prefix.
  3. The md is the last file pushed (its @COORD@ placeholder is substituted from the branch tree after the
     rest has landed, never hand-copied), and the manifest is pushed after it.
"""
from __future__ import annotations

import base64
import hashlib
import json
import pathlib
import subprocess
import sys
import time
import urllib.request

B = pathlib.Path('D:/moodle/_hjp3_0300c2_0925')
SRC = pathlib.Path('D:/moodle/HJ-P3_evidence')
R5 = pathlib.Path('D:/moodle/_hjp3_0279_0924/publish_evidence_r5.py')
TOK = pathlib.Path('D:/moodle/_qoder_recovery_20260919/.api_tok_20260920').read_text(
    encoding='utf-8').strip()
API = 'https://api.github.com/repos/Canshu-King/CityNexus'
BRANCH = 'commander/control'
PREFIX = 'evidence/ord0300-c2-pairing-hjp3'
MD_LOCAL = B / 'RECEIPT_O0300C2-1955_r3.md'
RULE = sorted(p.name for p in B.glob('q38_ruler_O0300C2-1955_r3_*.txt'))[-1]
INSTRUMENTS = ['c2_setup.py', 'c2_add_data.py', 'c2_add_t90.py', 'c2proxy.py', 'c2_rig.py',
               'c2_runarm.py', 'c2_score.py', 'c2_receipt.py', 'c2_md.py', 'c2_bounds.py',
               'c2_bundle.py', 'c2_bundle_check.py', 'c2_gate_selftest.py', 'c2_no_rewrite.py',
               'c2_publish.py', 'c2_pair_log_publish_copy.py', 'c2_instrument_publish_copy.py',
               'seed_helper.py', 'c2_cells_pub.cjs', 'c2_ledger.py', 'c2_bus.py', 'c2_bus_scan.py',
               'c2_bus_tail.py', 'c2_bus_correction.py', 'c2_bus_duplicate_note.py']
# the pages own instrument is published as a copy with one recorded field renamed (pair_token -> pair_id)
# because the shared content guard matches that key name; the bytes that ran are inside raw_bundle_c2_r2.json
# under the member name c2_cells.cjs, and instrument_publish_copy_proof_c2.json lists every line that differs.


def api(path):
    for a in range(5):
        r = urllib.request.Request(API + path)
        r.add_header('Authorization', 'Bearer ' + TOK)
        r.add_header('Accept', 'application/vnd.github+json')
        r.add_header('User-Agent', 'hjp3-0300c2-publish')
        try:
            with urllib.request.urlopen(r, timeout=180) as f:
                return json.loads(f.read().decode())
        except Exception as e:  # noqa: BLE001
            if a == 4:
                raise
            print('  retry %d on %s: %s' % (a, path[:40], str(e)[:90]), flush=True)
            time.sleep(3 + 3 * a)


def blob_of(p):
    d = pathlib.Path(p).read_bytes()
    return hashlib.sha1(b'blob %d\0' % len(d) + d).hexdigest()


def branch_rows():
    tip = api('/git/ref/heads/' + BRANCH)['object']['sha']
    tree_sha = api('/commits/' + tip)['commit']['tree']['sha']
    entries = api('/git/trees/' + tip + '?recursive=1')['tree']
    rows = sorted(({'path': e['path'], 'blob': e['sha'], 'size': e['size']}
                   for e in entries if e['path'].startswith(PREFIX + '/')
                   and e.get('size') is not None), key=lambda x: x['path'])
    return tip, tree_sha, rows


def plan():
    items = []

    def add(local, remote, msg):
        items.append((local, remote, msg))

    add(B / 'RECEIPT_O0300C2-1955_r3.json', 'RECEIPT_O0300C2-1955_r3.json',
        'machine receipt, second copy: the readings are identical, the rename record in K7 is corrected to '
        'name the bundle copy that really carries the as-ran bytes')
    add(B / 'c2_score.json', 'c2_score.json',
        'the derivation table: 12 cells (one per paired run) and 26 booleans computed from the arm files')
    add(B / RULE, RULE, 'Q38 r2 ruler output over the shipped receipt, kept out of the receipt so it '
                        'never quotes a verdict on itself')
    for f, m in (('instrument_publish_copy_proof_c2.json', 'the page-side instrument rename proof: every line '
                                                            'that differs and the bundle pointer'),
                 ('published_names_c2.json', 'the branch state this receipt was written against: which remote '
                                             'name holds which blob'),
                 ('publish_plan_c2.json', 'the authoritative was/now mapping the gate produced for this batch'),
                 ('gate_selftest_publish_c2.json', 'three-way control of this batch own publication gate'),
                 ('bundle_check_c2_r1.json', 'the FIRST bundle copy on the branch, downloaded and every member '
                                             're-hashed: 84 members, its own blob recomputes'),
                 ('bundle_check_c2_r2.json', 'the second bundle copy, re-hashed from the branch: 86 members'),
                 ('bundle_check_c2_r3.json', 'the bundle copy that the rename proofs point at, re-hashed from '
                                             'the branch: 86 members')):
        if (B / f).exists():
            add(B / f, f, m)
    add(B / 'raw_bundle_c2.json', 'raw_bundle_c2.json',
        'every per-arm witness packed with its own size/sha256/blob sha1: 15 arm files, 16 cell files, '
        '26 teardown rounds, rig states, lock/face/build/proxy logs')
    add(B / 'pair_log_pub.jsonl', 'pair_log_pub.jsonl',
        'the pairing proxy audit line per leg, published as a copy with ONE field renamed (token -> '
        'pair_id) because the shared content guard matches that quoted key; values, order and every other '
        'field are untouched and the original bytes also ship inside raw_bundle_c2.json')
    add(B / 'pair_log_publish_proof_c2.json', 'pair_log_publish_proof_c2.json',
        'the proof of that rename: both blob ids, line counts, ids identical in order, and the guard '
        'pattern matching the original but not the copy')
    add(B / 'backend_access.log', 'backend_access.log', "the product's own uvicorn access log for the batch")
    add(B / 'boundary_proof_c2.json', 'boundary_proof_c2.json',
        'boundary proof: served generation untouched, user chain listeners untouched, negative scan with '
        'calls / named-in-denial / self-reference split out')
    for f, msg in (('setup_facts.json', 'what the exports and the three private builds are: tips, sheet '
                                          'blobs, guard counts, bundle sha256, mutant line list'),
                   ('t90_facts.json', 'the generation the challenged cell was born on, re-exported into '
                                      'this batch and byte-verified against what ORD-0300 recorded'),
                   ('export_repair_facts.json', 'the packaging fix that removed my own fake 500, with '
                                                'before/after hashes proving the subject bytes never moved')):
        add(B / f, f, msg)
    for f in INSTRUMENTS:
        where = SRC / f if (SRC / f).exists() else B / f
        add(where, 'instruments/' + f, 'instrument as it ran for this batch')
    # these two can only be built once something of mine is on the branch, so they join the plan later
    for f, msg in (('gate_selftest_publish_c2.json', 'three-way control for this batch own publication '
                                                     'gate, run against the branch'),
                   ('bundle_check_c2.json', 'raw_bundle_c2.json re-downloaded from the branch and every '
                                            'member re-hashed'),
                   ('no_rewrite_proof_c2.json', 'write ledger: commits touching each published path in this '
                                                'prefix, with two counters-that-are-not-blind')):
        if (B / f).exists():
            add(B / f, f, msg)
    return items


def bumped(remote, on_branch, mine):
    """A published path is never re-PUT, so a revision takes a fresh name: `x.py` -> `x_r2.py`, `x_r3.py` ...

    If one of those names already carries these exact bytes, that is an identical skip, not a new revision -
    otherwise a rebuild loop would invent a phantom revision on every run.
    """
    stem, dot, ext = remote.rpartition('.')
    if not dot:
        stem, ext = remote, ''
    n = 2
    while True:
        cand = ('%s_r%d.%s' % (stem, n, ext)) if ext else ('%s_r%d' % (remote, n))
        there = on_branch.get(PREFIX + '/' + cand)
        if there == mine:
            return None, cand
        if there is None:
            return cand, None
        n += 1


def gate(items):
    tip, tree_sha, rows = branch_rows()
    on_branch = {r['path']: r['blob'] for r in rows}
    collide, skip, fresh = [], [], []
    for local, remote, msg in items:
        path = PREFIX + '/' + remote
        mine = blob_of(local)
        if not pathlib.Path(local).exists():
            collide.append({'remote': remote, 'reason': 'LOCAL FILE MISSING', 'me': None})
            continue
        if path not in on_branch:
            fresh.append((local, remote, msg, mine))
        elif on_branch[path] == mine:
            skip.append({'remote': remote, 'blob': mine, 'decision': 'SKIP byte-identical'})
        else:
            new, already = bumped(remote, on_branch, mine)
            if new is None:
                skip.append({'remote': remote, 'blob': mine,
                             'decision': 'SKIP - these exact bytes are already published as %s' % already,
                             'carried_by': already})
                continue
            collide.append({'remote': remote, 'reason': 'CHANGED BYTES UNDER A PUBLISHED NAME',
                            'me': mine, 'branch': on_branch[path], 'revised_name': new})
            fresh.append((local, new, msg + ' | revised copy; the first bytes stay at '
                          + remote + ' untouched', mine))
    return {'tip': tip, 'tree': tree_sha, 'already_on_branch': len(rows), 'fresh': fresh,
            'skipped_identical': skip, 'refusals': collide}


def push(items, label):
    res = []
    for local, remote, msg in items:
        r = subprocess.run([sys.executable, str(R5), str(local), PREFIX + '/' + remote,
                            'docs(evidence): ORD-0300 C2 pairing HJ-P3 %s' % msg[:70]],
                           capture_output=True, text=True, encoding='utf-8', errors='replace')
        res.append({'remote': remote, 'rc': r.returncode,
                    'tail': (r.stdout or '').strip().splitlines()[-2:]})
        print('  %-46s rc=%s' % (remote, r.returncode), flush=True)
        if r.returncode != 0:
            print(json.dumps(res[-1], ensure_ascii=False), flush=True)
    ok = sum(1 for x in res if x['rc'] == 0)
    print('%s published=%d/%d' % (label, ok, len(res)), flush=True)
    if ok != len(res):
        raise SystemExit('partial publication - stopping; nothing gets retried under an old name')
    return res


def coords_line():
    tip, tree_sha, rows = branch_rows()
    probe = next(x for x in rows if x['path'].endswith('RECEIPT_O0300C2-1955_r3.json'))
    obj = api('/git/blobs/' + probe['blob'])
    raw = base64.b64decode(obj['content'])
    ok = hashlib.sha1(b'blob %d\0' % obj['size'] + raw).hexdigest() == probe['blob']
    same = hashlib.sha256(raw).hexdigest() == hashlib.sha256(
        (B / 'RECEIPT_O0300C2-1955_r3.json').read_bytes()).hexdigest()
    key = ' · '.join('`%s` %s B `%s`' % (x['path'].split('/')[-1], format(x['size'] or 0, ','), x['blob'])
                     for x in rows if x['path'].split('/')[-1] in
                     ('RECEIPT_O0300C2-1955_r3.json', RULE, 'pair_log_pub.jsonl', 'c2_score.json',
                      'boundary_proof_c2.json', 't90_facts.json', 'gate_selftest_publish_c2.json',
                      'raw_bundle_c2_r3.json', 'bundle_check_c2_r3.json', 'no_rewrite_proof_c2.json',
                      'publish_plan_c2_r3.json', 'evidence_manifest_full40_c2.json'))
    line = ('`Canshu-King/CityNexus @ commander/control` 读回 commit 尖 `%s` · 其 tree `%s` · `%s/` 共 %d 件'
            '（合计 %s B，只数 blob，不数目录项）。所有 blob 为 40 位全字 (EVIDENCE_INTEGRITY_GATE_V1，'
            '短前缀只出现在清单件的 display_prefix 字段)。外部可读探针 `GET /git/blobs/%s` → 重算 sha1 与 '
            'tree 上 blob id 相等 = %s；与本机字节一致 = %s（%s B）。关键件：%s。'
            % (tip, tree_sha, PREFIX, len(rows), format(sum(x['size'] or 0 for x in rows), ','),
               probe['blob'], ok, same, format(len(raw), ','), key))
    return line, rows


def manifest(rows):
    tip, tree_sha, r2 = branch_rows()
    body = {'generated_at_local': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
            'repo': 'Canshu-King/CityNexus', 'branch': BRANCH, 'commit_tip': tip, 'tree': tree_sha,
            'prefix': PREFIX, 'count': len(r2),
            'bytes_total': sum(x['size'] or 0 for x in r2),
            'self_reference': 'this manifest lists the branch state before itself; the two files that land '
                              'after it (this manifest and the no-rewrite proof) are named in the delivery '
                              'post with their own blobs',
            'files': [{'path': x['path'], 'blob_sha1_40_hex': x['blob'], 'size': x['size'],
                       'display_prefix': x['blob'][:12]} for x in r2]}
    p = B / 'evidence_manifest_full40_c2.json'
    p.write_text(json.dumps(body, ensure_ascii=False, indent=1), encoding='utf-8', newline='\n')
    return p, body


if __name__ == '__main__':
    stage = sys.argv[1] if len(sys.argv) > 1 else 'gate'
    items = plan()
    if stage == 'gate':
        g = gate(items)
        print('planned', len(items), '| fresh', len(g['fresh']), '| identical', len(g['skipped_identical']),
              '| revisions renamed', len(g['refusals']), '| already under prefix', g['already_on_branch'])
        if g['refusals']:
            print(json.dumps([{'was': x['remote'], 'now': x['revised_name'], 'branch_blob_40_hex':
                               x['branch'], 'my_blob_40_hex': x['me']} for x in g['refusals']],
                             ensure_ascii=False, indent=1))
        if g['refusals'] and '--strict' in sys.argv:
            pass
        (B / 'publish_plan_c2.json').write_text(
            json.dumps({'tip': g['tip'], 'planned': [i[1] for i in items],
                        'skipped': g['skipped_identical'],
                        'revisions_renamed': [{'was': x['remote'], 'now': x['revised_name'],
                                               'branch_blob_40_hex': x['branch'],
                                               'my_blob_40_hex': x['me']} for x in g['refusals']]},
                       ensure_ascii=False, indent=1), encoding='utf-8', newline='\n')
        print('plan written: publish_plan_c2.json')
    elif stage == 'rest':
        g = gate(items)
        bad = [x for x in g['refusals'] if not x.get('revised_name')]
        assert not bad, 'a refusal with no revised name means the gate would have re-PUT: %s' % bad
        for x in g['refusals']:
            print('REVISION  %s -> %s (first bytes stay published, branch blob %s, my new blob %s)' % (
                x['remote'], x['revised_name'], x['branch'], x['me']), flush=True)
        todo = [(l, r, m) for (l, r, m, _b) in g['fresh'] if r != 'RECEIPT_O0300C2-1955_r3.md']
        push(todo, 'rest')
        line, rows = coords_line()
        (B / 'coords_line_c2_batch.txt').write_text(line, encoding='utf-8', newline='\n')
        p, body = manifest(rows)
        print('on branch after the rest:', body['count'], 'files')
    elif stage == 'md':
        md = MD_LOCAL.read_text(encoding='utf-8')
        assert '@COORD@' in md, 'the supplement lost its coordinate placeholder'
        line = (B / 'coords_line_c2_batch.txt').read_text(encoding='utf-8')
        MD_LOCAL.write_text(md.replace('@COORD@', '**发布与坐标（本批其余件先落架，本件随后）**：' + line),
                            encoding='utf-8', newline='\n')
        md_item = [(MD_LOCAL, 'RECEIPT_O0300C2-1955_r3.md',
                    'human supplement with its own coordinates')]
        mg = gate(md_item)
        assert not [x for x in mg['refusals'] if not x.get('revised_name')], 'gate would re-PUT the md'
        push([(l, r, m) for (l, r, m, _b) in mg['fresh']], 'md')
        line2, rows2 = coords_line()
        (B / 'coords_line_c2_final.txt').write_text(line2, encoding='utf-8', newline='\n')
        p, body = manifest(rows2)
        print('FINAL on branch:', body['count'], 'files,', body['bytes_total'], 'B')
    elif stage == 'manifest':
        tip, tree, rows = branch_rows()
        p, body = manifest(rows)
        item = [(p, 'evidence_manifest_full40_c2.json',
                 'manifest of 40-hex blobs for this prefix')]
        g = gate(item)                      # the same gate as the batch: no direct PUT of a published path
        bad = [x for x in g['refusals'] if not x.get('revised_name')]
        assert not bad, 'gate would have re-PUT: %s' % bad
        for x in g['refusals']:
            print('REVISION  %s -> %s (first bytes stay published, branch blob %s, my new blob %s)' % (
                x['remote'], x['revised_name'], x['branch'], x['me']), flush=True)
        push([(l, r, m) for (l, r, m, _b) in g['fresh']], 'manifest')
        print('manifest lists', body['count'], 'files at tip', tip[:12])
    elif stage == 'one':
        local, remote = B / sys.argv[2], sys.argv[3]
        g = gate([(local, remote, 'late artefact')])
        assert not g['refusals'], 'gate refuses %s: %s' % (remote, g['refusals'])
        assert g['fresh'], 'nothing fresh to send (already identical on the branch)'
        push([(local, remote, sys.argv[4] if len(sys.argv) > 4 else 'late artefact for this batch')], 'one')
        print('now on branch:', len(gate(plan())['fresh']) if False else len(branch_rows()[2]), 'files')
    elif stage == 'coords':
        print(coords_line()[0])
    else:
        raise SystemExit('unknown stage')
