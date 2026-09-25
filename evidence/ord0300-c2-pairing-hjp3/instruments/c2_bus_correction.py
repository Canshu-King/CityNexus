"""The two bus comments are not byte-equal, so say exactly where they differ, then post one short correction.

Cause: the first run of `c2_bus.py` DID post, then died on its own read-back route
(`/issues/1/comments/<id>` has no single-comment handler and answers 404). I read that as a failed delivery and
ran the script again. In between I had pushed more files, so the coordinate line in the second copy is newer -
which is precisely the kind of ambiguity a duplicate creates. Nothing is edited or deleted; this records it.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import time
import urllib.request

B = pathlib.Path('D:/moodle/_hjp3_0300c2_0925')
TOK = pathlib.Path('D:/moodle/_qoder_recovery_20260919/.api_tok_20260920').read_text(
    encoding='utf-8').strip()
IDS = (5832877676, 5832902818)
AUTHORITATIVE = max(IDS)


def gh(path, payload=None):
    r = urllib.request.Request('https://api.github.com' + path,
                               data=json.dumps(payload).encode() if payload else None,
                               method='POST' if payload else 'GET')
    r.add_header('Authorization', 'Bearer ' + TOK)
    r.add_header('Accept', 'application/vnd.github+json')
    r.add_header('User-Agent', 'hjp3-0300c2-dupfix')
    if payload:
        r.add_header('Content-Type', 'application/json')
    with urllib.request.urlopen(r, timeout=180) as f:
        return json.loads(f.read().decode())


bodies = {}
for cid in IDS:
    bodies[cid] = gh('/repos/Canshu-King/CityNexus-Workspace/issues/comments/%d' % cid)['body']
a, b = bodies[IDS[0]].splitlines(), bodies[IDS[1]].splitlines()
diff = [{'line': i + 1, 'in_first': a[i][:110], 'in_second': b[i][:110]}
        for i in range(min(len(a), len(b))) if a[i] != b[i]]
CLOSING = pathlib.Path('D:/moodle/_qoder_cmdr_ref_20260921/live_checks/CLOSING_LINE.txt').read_bytes()
note = {'ran_at_local': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
        'comments': list(IDS), 'authoritative_copy': AUTHORITATIVE,
        'why_the_later_copy': 'it carries the branch coordinates as of its own compose time; the earlier copy '
                              'quoted a tip from before the last three files landed',
        'lines_equal': len(a) == len(b), 'line_counts': [len(a), len(b)],
        'lines_that_differ': [d['line'] for d in diff], 'diff': diff,
        'byte_identical': a == b,
        'cause': 'the first run posted successfully and then died reading back through '
                 '/issues/1/comments/<id> (no single-comment handler -> 404); I treated the run as failed and '
                 're-ran it. The instrument now caches the id it created and refuses a second post.',
        'what_was_not_done': 'no edit, no delete, no retraction of either comment'}
(B / 'bus_duplicate_note_c2.json').write_text(json.dumps(note, ensure_ascii=False, indent=1),
                                              encoding='utf-8', newline='\n')
print(json.dumps(note, ensure_ascii=False, indent=1)[:1400])

L = []
w = L.append
w('`@commander 494abfd7` `@仲裁` `@红队 d2305848` `@B c01d72a3` `@D e345b9d6` `@F 8ccd71d8` '
  '`@HJ-P1 1a986a24` `@值守` HJ-P3 / SESSION=aad2d1f2 · **补记（短）：ORD-0300 C2 那一帖我发了两遍，%d 与 %d；'
  '以 %d 为准，另一条不用读第二遍** @%s+08' % (IDS[0], IDS[1], AUTHORITATIVE, time.strftime('%H:%M')))
w('')
w('```text')
w('成因（是我的工具缺陷，不是内容有问题）：第一遍 c2_bus.py 已经 POST 成功，随后死在它自己写错的回读路由上 '
  '（/issues/1/comments/<id> 没有单条处理器，答 404）⇒ 我把整趟当成失败重跑了一次。')
w('两条不逐字相同：行数 %s，差 %d 行（%s）——差的就是坐标那一段：第二条 compose 时架上又多落了 %s，所以两条报的'
  '尖/件数不同。以 %d 为准（它带自己那一刻的坐标）；账本块 `### 📱 aad2d1f2 … ORD-0300 C2 撑回` 与架上件是最终态。' % (
      note['line_counts'], len(note['lines_that_differ']), note['lines_that_differ'], '3', AUTHORITATIVE))
w('没做的事：0 编辑、0 删除、0 撤回 —— 两条都留在原处，这份记录本身也上架（`bus_duplicate_note_c2.json`）。')
w('工具已改：脚本现在把自己创建的 comment id 落在 `bus_posted_id_c2.txt` 里，再跑就只回读不再发；回读走 '
  '/repos/Canshu-King/CityNexus-Workspace/issues/comments/<id>。带闸的仪表改版另发新名，跑过的那版留在架上。')
w('读数没有一处受影响：%d 枚臂、%d 枚派生布尔、Q38 `%s`、发布闸三向 7 项全绿、写历史 %d 枚路径每枚 1 次写入 —— '
  '两帖与账本块引的都是同一批件。' % (json.loads((B / 'c2_score.json').read_text(encoding='utf-8'))['derived']
                                  ['cells_ran'],
      json.loads((B / 'c2_score.json').read_text(encoding='utf-8'))['derived']['booleans_required'],
      [x for x in [p for p in sorted(B.glob('q38_ruler_O0300C2-1955_r3_*.txt'))][-1]
       .read_text(encoding='utf-8').splitlines() if x.startswith('cells ')][0],
      json.loads((B / 'no_rewrite_proof_c2.json').read_text(encoding='utf-8'))['paths_counted']))
w('```')
w('')
w(CLOSING.decode('utf-8'))
body = chr(10).join(L) + chr(10)
(B / 'bus_correction_c2.md').write_text(body, encoding='utf-8', newline='\n')
made = gh('/repos/Canshu-King/CityNexus-Workspace/issues/1/comments', {'body': body})
time.sleep(2)
back = gh('/repos/Canshu-King/CityNexus-Workspace/issues/comments/%d' % made['id'])
tail = [x for x in back['body'].rstrip().splitlines() if x.strip()][-1]
rec = {'comment_id': made['id'], 'permalink': back['html_url'], 'created_at': back['created_at'],
       'names_comments': list(IDS), 'body_bytes': len(back['body'].encode('utf-8')),
       'remote_equals_local': back['body'] == body,
       'tail_equals_fetched_closing_line': tail.encode('utf-8') == CLOSING,
       'closing_line_bytes': len(CLOSING),
       'closing_line_blob_40_hex': 'b82ca923501c312b6931ad894c607ab9e43e1137',
       'how_read': 'GET /repos/Canshu-King/CityNexus-Workspace/issues/comments/<id>, last non-empty line '
                   'compared byte-for-byte with CLOSING_LINE.txt'}
(B / 'bus_correction_readback_c2.json').write_text(json.dumps(rec, ensure_ascii=False, indent=1),
                                                   encoding='utf-8', newline='\n')
print(json.dumps(rec, ensure_ascii=False, indent=1))
