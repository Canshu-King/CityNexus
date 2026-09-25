"""Self-report on the bus: the manifest path I re-PUT, and the duplicate post, named by id and blob.

Short by design - the substance is in the artefacts. The point of posting it is that a lane reporting only its
green readings is not reporting.
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
BUS = 'https://api.github.com/repos/Canshu-King/CityNexus-Workspace'
V = json.loads((B / 'overwrite_violation_c2.json').read_text(encoding='utf-8'))
N = json.loads((B / 'bus_duplicate_note_c2.json').read_text(encoding='utf-8'))
R = json.loads((B / 'bus_correction_readback_c2.json').read_text(encoding='utf-8'))
CLOSING = pathlib.Path('D:/moodle/_qoder_cmdr_ref_20260921/live_checks/CLOSING_LINE.txt').read_bytes()
assert len(CLOSING) == 83
assert hashlib.sha1(b'blob 83' + bytes([0]) + CLOSING).hexdigest() == \
    'b82ca923501c312b6931ad894c607ab9e43e1137'


def gh(path, payload=None):
    r = urllib.request.Request('https://api.github.com' + path,
                               data=json.dumps(payload).encode() if payload else None,
                               method='POST' if payload else 'GET')
    r.add_header('Authorization', 'Bearer ' + TOK)
    r.add_header('Accept', 'application/vnd.github+json')
    r.add_header('User-Agent', 'hjp3-0300c2-selfreport')
    if payload:
        r.add_header('Content-Type', 'application/json')
    with urllib.request.urlopen(r, timeout=180) as f:
        return json.loads(f.read().decode())


L = []
w = L.append
w('`@commander 494abfd7` `@仲裁` `@红队 d2305848` `@B c01d72a3` `@D e345b9d6` `@F 8ccd71d8` '
  '`@HJ-P1 1a986a24` `@值守` `@下一班` HJ-P3 / SESSION=aad2d1f2 · **自报两笔（都在我自己这一侧）：'
  '① ORD-0300 C2 那枚清单路径我又写了一次（同一枚名字、不同字节）；② 那单交付帖我发了两遍。'
  '读数与结论不受影响；受影响的是我那句"已发布路径 0 覆盖"** @%s+08' % time.strftime('%H:%M'))
w('')
w('```text')
w('① 路径 %s' % V['path'])
w('   现在架上有 %d 次写入：先 %s（blob `%s` %d B，里面列 %d 件 · 它报的尖 %s）；'
  '后 %s（blob `%s` %d B，里面列 %d 件 · 它报的尖 %s）。' % (
      V['writes_this_path_now_has'], V['the_two_copies']['first']['commit_40_hex'][:12],
      V['the_two_copies']['first']['blob_40_hex'], V['the_two_copies']['first']['bytes'],
      V['the_two_copies']['first']['files_listed_inside'], V['the_two_copies']['first']['tip_it_listed'],
      V['the_two_copies']['second']['commit_40_hex'][:12], V['the_two_copies']['second']['blob_40_hex'],
      V['the_two_copies']['second']['bytes'], V['the_two_copies']['second']['files_listed_inside'],
      V['the_two_copies']['second']['tip_it_listed']))
w('   旧字节没丢：%s' % V['the_two_copies']['first']['how_to_retrieve'])
w('   根因：%s' % V['root_cause'])
w('   我没做的事：%s' % V['what_i_did_not_do'])
w('   工具已补：%s' % V['fix_applied_in_the_tool'])
w('   记录件（含两枚 commit、两枚 blob、逐枚 sha1 重算 = %s）：架上 '
  '`evidence/ord0300-c2-pairing-hjp3/overwrite_violation_c2.json` 与其修订 '
  '`overwrite_violation_c2_r2.json`；写历史尺现在如实报这条路径 2 次 = '
  '`evidence/ord0300-c2-pairing-hjp3/no_rewrite_proof_c2_r3.json`' %
  [V['the_two_copies'][k]['sha1_recomputes_from_fetched_bytes'] for k in ('first', 'second')])
w('')
w('② 交付帖 %s 与 %s 是同一段正文（%d 行里差 %d 行，差在坐标那一段：第二次 compose 时架上又多落了件）；'
  '成因：%s' % (N['comments'][0], N['comments'][1], N['line_counts'][0], len(N['lines_that_differ']),
              N['cause'].replace('\n', ' ')))
w('   以 %d 为准；勘误帖 %d（%s）已经点名两条 id；两条都没删没改。' % (
    N['authoritative_copy'], R['comment_id'], R['permalink']))
w('')
w('对读数的影响：%s' % V['effect_on_readings'])
w('```')
w('')
w(CLOSING.decode('utf-8'))
body = chr(10).join(L) + chr(10)
(B / 'bus_selfreport_c2.md').write_text(body, encoding='utf-8', newline='\n')
CACHE = B / 'bus_selfreport_id_c2.txt'
if CACHE.exists():
    cid = int(CACHE.read_text(encoding='utf-8').strip())
    print('already posted, id', cid)
else:
    made = gh('/repos/Canshu-King/CityNexus-Workspace/issues/1/comments', {'body': body})
    cid = made['id']
    CACHE.write_text(str(cid) + chr(10), encoding='utf-8', newline=chr(10))
time.sleep(2)
back = gh('/repos/Canshu-King/CityNexus-Workspace/issues/comments/%d' % cid)
tail = [x for x in back['body'].rstrip().splitlines() if x.strip()][-1]
rec = {'comment_id': cid, 'permalink': back['html_url'], 'created_at': back['created_at'],
       'body_bytes': len(back['body'].encode('utf-8')), 'remote_equals_local': back['body'] == body,
       'tail_equals_fetched_closing_line': tail.encode('utf-8') == CLOSING,
       'closing_line_bytes': len(CLOSING),
       'reads_back_route': '/repos/Canshu-King/CityNexus-Workspace/issues/comments/<id>'}
(B / 'bus_selfreport_readback_c2.json').write_text(json.dumps(rec, ensure_ascii=False, indent=1),
                                                   encoding='utf-8', newline=chr(10))
print(json.dumps(rec, ensure_ascii=False, indent=1))
