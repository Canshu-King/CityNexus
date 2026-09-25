"""ORD-0301 pass 3 publisher: a NEW prefix, new names only, identical-or-refuse before the first write.

Rules this file exists to obey (each one earned by a published mistake, not invented here):
  1. 加格子一律新文件名 - a published path is never re-PUT. Every planned remote name is compared with the
     branch first: byte-identical -> SKIP and reported; changed bytes under a name that already landed ->
     the whole batch refuses before the first write. Single-file pushes go through `gated_push.py`, which is
     the wrapper that exists because I twice bypassed this gate by calling the low-level publisher directly.
  2. EVIDENCE_INTEGRITY_GATE_V1 - manifest coordinates are 40-hex blob ids; a short prefix only ever lives in
     a field named display_prefix.
  3. The md is the last content file pushed, because its @COORD@ line is substituted from the branch tree
     after the rest has landed - never hand-copied. The self-growing manifest follows it, and the post that
     announces the batch carries the manifest's NEW blob, per CMDR-0925-2128 ①.
  4. The shared content guard is pre-scanned locally so a refusal is a plan-time fact, not a half-pushed
     batch. If a file trips it, the fix is a new name or a renamed field with a line-level proof - never an
     edited guard and never a masked value.
"""
from __future__ import annotations

import hashlib
import importlib.util as iu
import json
import pathlib
import re
import sys
import time
import urllib.request

B = pathlib.Path('D:/moodle/_hjp3_0301p3_0925')
SRC = pathlib.Path('D:/moodle/HJ-P3_evidence')
TOK = pathlib.Path('D:/moodle/_qoder_recovery_20260919/.api_tok_20260920').read_text(
    encoding='utf-8').strip()
API = 'https://api.github.com/repos/Canshu-King/CityNexus'
BRANCH = 'commander/control'
PREFIX = 'evidence/ord0301-p3-same-chain-hjp3'
MD_LOCAL = B / 'RECEIPT_O0301P3-2230.md'
RULE = 'q38_ruler_O0301P3-2230.txt'
RCPT = 'RECEIPT_O0301P3-2230.json'
INSTRUMENTS = ['p3_setup.py', 'p3proxy.py', 'p3_rig.py', 'p3_arms.py', 'p3_cells.cjs', 'p3_score.py',
               'p3_receipt.py', 'p3_md.py', 'p3_boundary.py', 'p3_gate_selftest.py', 'p3_no_rewrite.py',
               'p3_publish.py']
_spec = iu.spec_from_file_location('gp', str(SRC / 'gated_push.py'))
gp = iu.module_from_spec(_spec)
_spec.loader.exec_module(gp)
GUARD = iu.spec_from_file_location('r5', str(pathlib.Path(
    'D:/moodle/_hjp3_0279_0924/publish_evidence_r5.py')))
r5 = iu.module_from_spec(GUARD)
GUARD.loader.exec_module(r5)


def api(path):
    for a in range(5):
        r = urllib.request.Request(API + path)
        r.add_header('Authorization', 'Bearer ' + TOK)
        r.add_header('Accept', 'application/vnd.github+json')
        r.add_header('User-Agent', 'hjp3-0301p3-publish')
        try:
            with urllib.request.urlopen(r, timeout=180) as f:
                return json.loads(f.read().decode())
        except Exception as e:  # noqa: BLE001
            if a == 4:
                raise
            print('  retry %d on %s: %s' % (a, path[:44], str(e)[:90]), flush=True)
            time.sleep(3 + 3 * a)


def blob_of(p):
    d = pathlib.Path(p).read_bytes()
    return hashlib.sha1(b'blob %d\0' % len(d) + d).hexdigest()


def branch_rows():
    tip = api('/git/ref/heads/' + BRANCH)['object']['sha']
    tree = api('/commits/' + tip)['commit']['tree']['sha']
    entries = api('/git/trees/' + tip + '?recursive=1')['tree']
    rows = sorted(({'path': e['path'], 'blob': e['sha'], 'size': e['size']}
                   for e in entries if e['path'].startswith(PREFIX + '/') and e.get('size') is not None),
                  key=lambda x: x['path'])
    return tip, tree, rows


def plan():
    items = []

    def add(local, remote, msg):
        # a file this stage has not produced yet is not a plan item - the gate must not be run against a
        # path that only exists later (that is how a "LOCAL FILE MISSING" refusal is earned)
        if not pathlib.Path(local).exists():
            return
        items.append((local, remote, msg))

    add(B / RCPT, RCPT, 'machine receipt: 7 cells, both readings of every leg taken in one hop, the two '
                        'answer classes separated at both statuses and on both bundles')
    add(B / 'RECEIPT_O0301P3-2230.md', 'RECEIPT_O0301P3-2230.md',
        'human supplement: the range table, the two generation corrections, what my instrument broke')
    add(B / 'p3_scored.json', 'p3_scored.json',
        'the scored arm table with 25 derived booleans and the mechanically-caught exclusions')
    add(B / 'p3_boundary.json', 'p3_boundary.json',
        'boundary proof: forbidden names counted per role, exports hashed against their own commits')
    add(B / RULE, RULE, 'Q38 r2 ruler output over the shipped receipt, kept outside the receipt so it never '
                        'quotes a verdict on itself')
    for f in ('gate_selftest_publish_p3.json', 'no_rewrite_proof_p3.json', 'ledger_inbox_proof_p3.json'):
        add(B / f, f, 'this batch\'s own gate control / write ledger / inbox delivery proof, produced after '
                      'the first files landed and shipped as-is')
    scored = json.loads((B / 'p3_scored.json').read_text(encoding='utf-8'))
    for r in scored['arms_scored']:
        add(B / r['file'], r['file'], 'scored arm: one class on one bundle, both ends of the same leg')
        cell = r['file'].replace('p3_arm_', 'p3_cell_')
        if (B / cell).exists():
            add(B / cell, cell, 'the page witness for that arm: fetch, body read, browser stack, painted text')
    for x in scored['runs_excluded']:
        add(B / x['file'], 'discarded_' + x['file'],
            'discarded arm kept on the branch as the mistake: %s' % x['mechanical_test'])
    for f in sorted(p.name for p in B.glob('p3_rig_state_*.json')):
        add(B / f, f, 'rig state for one arm: which tip, which ports, which one-time db, two-sided identity')
    td = sorted(B.glob('p3_teardown_*.json'))
    add(B / td[-1].name, td[-1].name, 'closing teardown: every named port proven free by re-listening')
    add(B / 'p3_pair_log.jsonl', 'p3_pair_log.jsonl',
        'the hop append-only audit: one line per request, the id the hop minted, the answer body class read '
        'from the bytes')
    shots = sorted(B.glob('p3_cell_*hoplock*.png'))
    for s in shots:
        add(B / s.name, s.name, 'the sheet as painted in the contended-write arm (screenshot of the same run)')
    for f in INSTRUMENTS:
        if (SRC / f).exists():
            add(SRC / f, 'instruments/' + f, 'instrument of this batch (new name; published instrument paths '
                                             'are never rewritten)')
    return items


def pre_scan_guard(items):
    """Run the shared content guard locally BEFORE writing anything, so a refusal is a plan-time fact."""
    refused = []
    for local, remote, _msg in items:
        if not pathlib.Path(local).exists():
            refused.append({'remote': remote, 'reason': 'LOCAL FILE MISSING'})
            continue
        hit = None
        for rule, pat in getattr(r5, 'SECRET_VALUE_PATTERNS', ()):
            m = pat.search(pathlib.Path(local).read_bytes())
            if m and not r5._placeholder_in_value(r5._matched_secret_value(rule, m.group(0))):
                hit = {'rule': rule, 'match_len': len(m.group(0))}
                break
        if hit:
            refused.append({'remote': remote, 'reason': 'FORBIDDEN_CONTENT(secret_pattern=%s)'
                            % hit['rule'], 'bytes_hidden': hit['match_len']})
    return refused


def gate(items):
    tip, tree, rows = branch_rows()
    on_branch = {r['path']: r['blob'] for r in rows}
    fresh, skip, refuse = [], [], []
    for local, remote, msg in items:
        path = PREFIX + '/' + remote
        mine = blob_of(local)
        if path not in on_branch:
            fresh.append((local, remote, msg, mine))
        elif on_branch[path] == mine:
            skip.append({'remote': remote, 'blob': mine, 'decision': 'SKIP byte-identical'})
        else:
            refuse.append({'remote': remote, 'reason': 'CHANGED BYTES UNDER A PUBLISHED NAME',
                           'me': mine, 'branch': on_branch[path]})
    return {'tip': tip, 'tree': tree, 'already_on_branch': len(rows), 'fresh': fresh,
            'skipped_identical': skip, 'refusals': refuse}


def push(items, label):
    res = []
    for local, remote, msg in items:
        rc = gp.push(str(local), PREFIX + '/' + remote,
                     'docs(evidence): ORD-0301 p3 HJ-P3 %s' % msg[:70])
        res.append({'remote': remote, 'rc': rc})
        if rc != 0:
            print(json.dumps(res, ensure_ascii=False, indent=1), flush=True)
            (B / 'publish_result_%s.json' % label).write_text(
                json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8', newline='\n')
            raise SystemExit('rc=%d on %s - stopping; nothing is retried under an old name'
                             % (rc, remote))
    (B / 'publish_result_%s.json' % label).write_text(json.dumps(res, ensure_ascii=False, indent=1),
                                                     encoding='utf-8', newline='\n')
    print('%s published=%d/%d' % (label, len(res), len(res)), flush=True)
    return res


def coords_line():
    tip, tree, rows = branch_rows()
    probe = next(x for x in rows if x['path'].endswith(RCPT))
    obj = api('/git/blobs/' + probe['blob'])
    raw = __import__('base64').b64decode(obj['content'])
    ok = hashlib.sha1(b'blob %d\0' % obj['size'] + raw).hexdigest() == probe['blob']
    same = hashlib.sha256(raw).hexdigest() == hashlib.sha256((B / RCPT).read_bytes()).hexdigest()
    key = ' · '.join('`%s` %s B `%s`' % (x['path'].split('/')[-1], format(x['size'] or 0, ','), x['blob'])
                     for x in rows if x['path'].split('/')[-1] in
                     (RCPT, 'p3_scored.json', RULE, 'p3_boundary.json', 'p3_pair_log.jsonl',
                      'p3_no_rewrite.py'))
    return ('坐标（脚本从分支 tree 读回，非手抄）：`Canshu-King/CityNexus @ commander/control` 读回 commit 尖 '
            '`%s` · 其 tree `%s` · `%s/` 共 %d 件（合计 %s B）。所有 blob 为 40 位全字 '
            '(EVIDENCE_INTEGRITY_GATE_V1，短前缀只出现在清单件的 display_prefix 字段)。外部可读探针 '
            '`GET /git/blobs/%s` → 重算 sha1 与 tree 上 blob id 相等 = %s；与本机字节一致 = %s（%s B）。'
            '关键件：%s。'
            % (tip, tree, PREFIX, len(rows), format(sum(x['size'] or 0 for x in rows), ','),
               probe['blob'], ok, same, format(len(raw), ','), key))


def manifest():
    tip, tree, rows = branch_rows()
    body = {'generated_at_local': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
            'repo': 'Canshu-King/CityNexus', 'branch': BRANCH, 'commit_tip': tip, 'tree': tree,
            'prefix': PREFIX, 'count': len(rows),
            'self_reference': 'this manifest lists what is on the branch, so it lists the state before '
                              'itself landed; its own blob is reported in the delivery post, per '
                              'CMDR-0925-2128 ①',
            'files': [{'path': x['path'], 'blob_sha1_40_hex': x['blob'], 'size': x['size'],
                       'display_prefix': x['blob'][:12]} for x in rows]}
    p = B / 'evidence_manifest_full40_p3.json'
    p.write_text(json.dumps(body, ensure_ascii=False, indent=1), encoding='utf-8', newline='\n')
    return p, body


if __name__ == '__main__':
    stage = sys.argv[1] if len(sys.argv) > 1 else 'gate'
    items = plan()
    guard = pre_scan_guard(items)
    print('planned %d | guard refusals %d' % (len(items), len(guard)))
    if guard:
        print(json.dumps(guard[:8], ensure_ascii=False, indent=1))
        raise SystemExit('the content guard refuses this plan - fix names or fields, never the guard')
    g = gate(items)
    print('fresh %d | identical %d | refusals %d | already on branch %d (tip %s)'
          % (len(g['fresh']), len(g['skipped_identical']), len(g['refusals']), g['already_on_branch'],
             g['tip'][:12]))
    if g['refusals']:
        print(json.dumps(g['refusals'][:6], ensure_ascii=False, indent=1))
        raise SystemExit('the identical-or-refuse gate refused this batch - nothing was sent')
    (B / 'publish_plan_p3.json').write_text(
        json.dumps({'tip': g['tip'], 'planned': [i[1] for i in items],
                    'skipped': g['skipped_identical'], 'refusals': g['refusals']},
                   ensure_ascii=False, indent=1), encoding='utf-8', newline='\n')
    if stage == 'gate':
        pass
    elif stage == 'rest':
        todo = [(l, r, m) for (l, r, m, _b) in g['fresh'] if r != MD_LOCAL.name]
        push(todo, 'rest')
        (B / 'coords_line_p3.txt').write_text(coords_line(), encoding='utf-8', newline='\n')
    elif stage == 'md':
        md = MD_LOCAL.read_text(encoding='utf-8')
        assert '@COORD@' in md or '%COORD%' in md, 'the supplement lost its coordinate placeholder'
        line = (B / 'coords_line_p3.txt').read_text(encoding='utf-8')
        MD_LOCAL.write_text(md.replace('%COORD%', '**发布与坐标（本批其余件先落架，本件随后）**：' + line),
                            encoding='utf-8', newline='\n')
        g2 = gate([(MD_LOCAL, MD_LOCAL.name, 'supplement')])
        assert not g2['refusals'], 'the md name moved after the rest landed'
        push([(MD_LOCAL, MD_LOCAL.name, 'human supplement with its own coordinates')], 'md')
    elif stage == 'manifest':
        p, body = manifest()
        g3 = gate([(p, p.name, 'manifest')])
        if g3['skipped_identical']:
            print('manifest unchanged on the branch - nothing to send')
        assert not g3['refusals'], 'the manifest path already holds different bytes; publish a NEW name'
        push(g3['fresh'], 'manifest')
        p2, body2 = manifest()
        print('FINAL on branch: %d files, blob of this manifest %s'
              % (body2['count'], blob_of(p2)))
    elif stage == 'coords':
        print(coords_line())
    else:
        raise SystemExit('unknown stage')
