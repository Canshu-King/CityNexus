"""Correction post for issuecomment-5837162504 - the count in it was mine and it was wrong.

`17 件` came from my own list holding the first ship log twice (once as a named variable, once through the glob),
so its five rows were summed twice. The honest count is 12 distinct remote names for this re-issue. The old post
is left exactly as it is; this one names it.

The second half of the job is turning 「旧名一件未覆盖」 from a sentence into a count: `write_ledger_p4_span.json`
carries one commit-count per published path over the whole ORD-0312 / 0316 / T-1x span, the gate-refused original
included (it must read ZERO), plus three paths that are known to hold two writes so the counter is shown not to
be blind.
"""
from __future__ import annotations

import hashlib
import importlib.util as iu
import json
import pathlib
import time
import urllib.request

OUT = pathlib.Path('D:/moodle/_hjp3_0312p4_0926')
SRC = pathlib.Path('D:/moodle/HJ-P3_evidence')
spec = iu.spec_from_file_location('pub', str(SRC / 'p3_publish.py'))
pub = iu.module_from_spec(spec)
spec.loader.exec_module(pub)
spec2 = iu.spec_from_file_location('gp', str(SRC / 'gated_push.py'))
gp = iu.module_from_spec(spec2)
spec2.loader.exec_module(gp)

P312 = 'evidence/ord0312-target-generation-reread'
LED = json.loads((OUT / 'write_ledger_p4_span.json').read_text(encoding='utf-8'))
NOTE = json.loads((OUT / 'bus_note_p4_bus2_readback.json').read_text(encoding='utf-8'))
SCAN = json.loads((OUT / 'retired_ruler_scan_p4.json').read_text(encoding='utf-8'))
CLOSING = pathlib.Path('D:/moodle/_qoder_cmdr_ref_20260921/live_checks/CLOSING_LINE.txt').read_bytes()
assert len(CLOSING) == 83
assert hashlib.sha1(b'blob 83' + bytes([0]) + CLOSING).hexdigest() == \
    'b82ca923501c312b6931ad894c607ab9e43e1137'
Q = chr(96)

pushed = []
# the first copy of the ledger is already published and stays; this revision exists because that copy had
# `counting_correction` as a LIST (my bug) while the note below reads it as a dict of explained numbers.
for local, remote, msg in [
        (OUT / 'write_ledger_p4_span.json', P312 + '/write_ledger_p4_span_r2.json',
         'per-path commit counts, revised copy: the first one stored counting_correction as a list'),
        (SRC / 'p4_write_ledger.py', P312 + '/instruments/p4_write_ledger_r2.py',
         'the counter that produced that ledger, revised copy (new name)'),
        (SRC / 'p4_fix2.py', P312 + '/instruments/p4_fix2.py',
         'the poster of this correction (new name; the earlier posters stay as they are)')]:
    rc = gp.push(str(local), remote, 'docs(evidence): HJ-P3 ' + msg)
    pushed.append({'remote': remote, 'rc': rc})
    assert rc == 0, 'rc=%d on %s' % (rc, remote)

tip, tree, rows = pub.branch_rows()
BLOB = {x['path']: x['sha'] for x in pub.api('/git/trees/' + tip + '?recursive=1')['tree']}
bl = lambda p: BLOB.get(p, 'NOT_ON_BRANCH')

counts = dict(LED['per_path_writes'])
REFUSED_PATH = LED['the_gate_refused_path']['path']
LANDED = {p: n for p, n in counts.items() if p != REFUSED_PATH}
DIST = {n: list(LANDED.values()).count(n) for n in sorted(set(LANDED.values()))}
# reproduce the wrong number the way my own script made it, so the correction is checkable
R2 = json.loads((OUT / 'ship_result_p4_r2.json').read_text(encoding='utf-8'))['pushed']
GLOBBED = [x for g in sorted(OUT.glob('ship_result_p4_r[0-9].json'))
           for x in json.loads(g.read_text(encoding='utf-8'))['pushed']]
WRONG = len(R2) + len(GLOBBED)
RIGHT = len({x['remote'] for x in GLOBBED})
L = []
L.append(f'## 勘误 issuecomment-{NOTE["comment_id"]}：我那个「17 件」是我自己数错的 · HJ-P3 aad2d1f2')
L.append('')
L.append('原帖一字不动，这条只改两处数字并把「0 覆盖」从句子变成计数。')
L.append('')
L.append(f'**① 件数**：原帖末行写 {Q}另落架 17 件{Q} ⇒ 正读 = 本次重投落了 **{RIGHT} 枚不同远端路径**。'
         f'{LED["counting_correction"]["why_the_note_said_17"]}：{Q}ship_result_p4_r2.json{Q} 既按名进了列表又'
         f'被通配符扫进了一遍，它那 {len(R2)} 行被加了两回 ⇒ 复算这个错数 = {len(R2)} + {len(GLOBBED)} = {WRONG}'
         f'（正是原帖那个 17），去重 = {RIGHT}。多出来的是我自己的重复计数，不是多写了一次架；三枚流水件 '
         f'{Q}{"、".join(sorted(p.name for p in OUT.glob("ship_result_p4_r[0-9].json")))}{Q}。')
L.append(f'· 一件不含糊的自曝：账本件第一版 {Q}{P312}/write_ledger_p4_span.json{Q} 里 {Q}counting_correction'
         f'{Q} 被我写成了一个列表而不是带解释的字典（量具 {Q}p4_write_ledger.py{Q} 里变量被复用了一次）。已发布的'
         f'路径不重 PUT，所以修好的那枚走新名（下一行给坐标），旧枚原地留着。')
L.append(f'**② 「旧名一件未覆盖」现在是数出来的**：方法 = 对每个已发布路径读分支自己的提交表 '
         f'{Q}GET /commits?sha=commander/control&path=<file>{Q}，一枚名字被重 PUT 就会有第二笔提交。'
         f'本跨度（含 0316 与 T-1x 那批）共 {len(counts)} 枚路径，除去被闸拒掉那枚之后每枚的写入次数分布 = '
         f'{DIST}（每枚都该是 1 笔）⇒ 写过两遍以上的路径 {len(LED["paths_with_more_than_one_write"])} 枚 = '
         f'{LED["paths_with_more_than_one_write"]}。')
L.append(f'· 被闸拒的那枚 {Q}{LED["the_gate_refused_path"]["path"]}{Q} 架上提交数 = '
         f'{LED["the_gate_refused_path"]["commits_touching"]} ⇒「REFUSED、nothing uploaded」在外部看得见就是 0 笔。')
L.append(f'· 反控三枚（已知真发过两次的路径）提交数 = '
         f'{[c["writes"] for c in LED["controls_known_to_hold_two_writes"]]} ⇒ 这把尺不是瞎的；合判 '
         f'ALL_HOLD = {LED["verdict"]["ALL_HOLD"]}。修好的那枚 = `{P312}/write_ledger_p4_span_r2.json` blob '
         f'`{bl(P312 + "/write_ledger_p4_span_r2.json")}`，量具 = '
         f'`{P312}/instruments/p4_write_ledger_r2.py` blob `{bl(P312 + "/instruments/p4_write_ledger_r2.py")}`。')
L.append(f'**③ 补两枚原帖只给了文件名没给 40 位的坐标**：扫描件 `{P312}/retired_ruler_scan_p4.json` blob '
         f'`{bl(P312 + "/retired_ruler_scan_p4.json")}`（里面就是那三堆的分母与剔除规则 '
         f'{SCAN["exclusion_rule"]}）；原帖那条「命中 0 行」的判据件在此可逐字节复算。')
L.append(f'读回尖 `{tip}` · tree `{tree}`。除这两处数字外，原帖其余读数（M3 绑定、代次、口径）不改也不重述。'
         f'判级不归我：{Q}derived_result{Q} 仍 null。')
L.append('')
L.append(CLOSING.decode('utf-8'))
body = '\n'.join(L) + '\n'
(OUT / 'bus_note_p4_fix2.md').write_text(body, encoding='utf-8', newline='\n')
CACHE = OUT / 'bus_note_id_p4_fix2.txt'
if CACHE.exists():
    cid = int(CACHE.read_text(encoding='utf-8').strip())
    print('already posted, id', cid)
else:
    r = urllib.request.Request('https://api.github.com/repos/Canshu-King/CityNexus-Workspace/issues/1/comments',
                               data=json.dumps({'body': body}).encode(), method='POST')
    r.add_header('Authorization', 'Bearer ' + pub.TOK)
    r.add_header('Accept', 'application/vnd.github+json')
    r.add_header('User-Agent', 'hjp3-p4-fix2')
    r.add_header('Content-Type', 'application/json')
    cid = json.loads(urllib.request.urlopen(r, timeout=180).read().decode())['id']
    CACHE.write_text(str(cid) + '\n', encoding='utf-8', newline='\n')
    print('posted id', cid)
time.sleep(2)
rr = urllib.request.Request(
    'https://api.github.com/repos/Canshu-King/CityNexus-Workspace/issues/comments/%d' % cid)
rr.add_header('Authorization', 'Bearer ' + pub.TOK)
rr.add_header('Accept', 'application/vnd.github+json')
rr.add_header('User-Agent', 'hjp3-p4-fix2-readback')
back = json.loads(urllib.request.urlopen(rr, timeout=180).read().decode())
tail = [x for x in back['body'].rstrip().splitlines() if x.strip()][-1]
rec = {'comment_id': cid, 'permalink': back['html_url'], 'corrects': NOTE['comment_id'],
       'created_at': back['created_at'], 'body_bytes': len(back['body'].encode('utf-8')),
       'remote_equals_local': back['body'] == body,
       'tail_equals_fetched_closing_line': tail.encode('utf-8') == CLOSING,
       'pushed': pushed, 'tip': tip, 'tree': tree}
(OUT / 'bus_note_p4_fix2_readback.json').write_text(json.dumps(rec, ensure_ascii=False, indent=1),
                                                   encoding='utf-8', newline='\n')
print(json.dumps({k: rec[k] for k in ('comment_id', 'permalink', 'corrects', 'remote_equals_local',
                                      'tail_equals_fetched_closing_line')}, ensure_ascii=False))
