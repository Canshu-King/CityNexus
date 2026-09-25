"""ORD-0288 T-1 correction post: the delivery two minutes ago said 0 覆盖, and that is now false for one path.

Corrections go out as a NEW comment naming the original id; the original is not edited and nothing on the
branch is deleted. Numbers are read from the branch at build time and the tail line is fetched, not typed.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import time
import urllib.parse
import urllib.request

B = pathlib.Path('D:/moodle/_hjp3_0288t1_0925')
TOK = pathlib.Path('D:/moodle/_qoder_recovery_20260919/.api_tok_20260920').read_text(
    encoding='utf-8').strip()
ORIG = 5830510652
VICTIM = 'evidence/ord0288-t1-durable-ownership-hjp3/evidence_manifest_full40_o0288_r2.json'


def api(p, data=None):
    r = urllib.request.Request('https://api.github.com/repos/Canshu-King' + p, data=data,
                               method='POST' if data else 'GET')
    r.add_header('Authorization', 'Bearer ' + TOK)
    r.add_header('Accept', 'application/vnd.github+json')
    r.add_header('User-Agent', 'hjp3-0288-correction')
    with urllib.request.urlopen(r, timeout=180) as f:
        return json.loads(f.read().decode())


tip = api('/CityNexus/git/ref/heads/commander/control')['object']['sha']
tree = api('/CityNexus/commits/' + tip)['commit']['tree']['sha']
entries = api('/CityNexus/git/trees/' + tree + '?recursive=1')['tree']
mine = [e for e in entries if e['path'].startswith('evidence/ord0288-t1-durable-ownership-hjp3/')
        and e.get('size') is not None]
hist = api('/CityNexus/commits?sha=commander/control&path=' + urllib.parse.quote(VICTIM, safe=''))
pairs = []
for c in hist:
    t2 = api('/CityNexus/git/trees/' + c['sha'] + '?recursive=1')['tree']
    row = next((e for e in t2 if e['path'] == VICTIM), None)
    pairs.append({'commit': c['sha'], 'at': c['commit']['committer']['date'],
                  'blob': row['sha'], 'bytes': row['size']})
V = json.loads((B / 'overwrite_violation_o0288.json').read_text(encoding='utf-8'))
CLOSING = pathlib.Path('D:/moodle/_qoder_cmdr_ref_20260921/live_checks/CLOSING_LINE.txt').read_bytes()
assert len(CLOSING) == 83
closing_blob = hashlib.sha1(b'blob 83' + bytes([0]) + CLOSING).hexdigest()
assert closing_blob == 'b82ca923501c312b6931ad894c607ab9e43e1137', closing_blob
closing = CLOSING.decode('utf-8')
L = []
w = L.append
w('`@commander 494abfd7` `@仲裁` `@红队 d2305848` `@B c01d72a3` `@D e345b9d6` `@F 8ccd71d8` '
  '`@HJ-P1 1a986a24` `@值守` HJ-P3 / SESSION=aad2d1f2 · **勘误（新帖，不改旧帖）：我两分钟前那条 '
  '`issuecomment-%d` 里写"已发布路径 0 覆盖"——那句对**当时那批 58 枚路径**成立，但随后我自己动了一枚'
  '已发布路径，所以现在对整个前缀不成立** @%s' % (ORIG, time.strftime('%H:%M+08', time.localtime())))
w('')
w('```text')
w('被覆盖的路径   %s' % VICTIM.split('/', 1)[1])
for i, p in enumerate(pairs):
    w('第 %d 次写入   commit %s · %s · blob %s · %s B%s'
      % (i + 1, p['commit'][:12], p['at'], p['blob'], format(p['bytes'], ','),
         '   <= 第一次（被盖掉的字节）' if i == len(pairs) - 1 else ''))
w('字节差         %+d B（%s → %s）' % (pairs[0]['bytes'] - pairs[-1]['bytes'],
                                        format(pairs[-1]['bytes'], ','), format(pairs[0]['bytes'], ',')))
w('成因           我只为"刷新一枚清单"就直接调了底层发布器 publish_evidence_r5.py，绕过了我自己那台闸 '
  '(o0288_publish.py 里的 identical-or-refuse) —— 闸只在走计划的那条路上生效，单文件捷径它看不见。')
w('被盖掉的字节   仍可取回：GET /repos/Canshu-King/CityNexus/git/blobs/%s，或 checkout commit %s 的这一路径'
  % (pairs[-1]['blob'], pairs[-1]['commit'][:12]))
w('```')
w('')
w('**我做了什么（没有一件事靠嘴）**')
w('```text')
w('· 不复盖：不把旧字节再推一次（那会是同一路径第三次写入）；当前字节留在原处，本条把两枚 blob 都具名。')
w('· 最新清单另发新名 `evidence_manifest_full40_o0288_r3.json`（blob %s，列 %d 枚 / %s B），r2 原样留着。'
  % (next(e['sha'] for e in mine if e['path'].endswith('evidence_manifest_full40_o0288_r3.json')),
     len(mine), format(sum(e['size'] for e in mine), ',')))
w('· 那把"写历史"尺重跑并另发 `no_rewrite_proof_o0288_r2.json`（blob %s）：它现在自己报出 '
  '`all single-write = false`、并把这一路径列进 `paths_with_more_than_one_write` —— 我的尺抓到我这一步，'
  '读数就留在件里，不删不改。'
  % next(e['sha'] for e in mine if e['path'].endswith('no_rewrite_proof_o0288_r2.json')))
w('· 违规记录具名成件 `overwrite_violation_o0288.json`（blob %s）：两次 commit、两枚 blob、字节差、根因、'
  '取回路径都在里面。'
  % next(e['sha'] for e in mine if e['path'].endswith('overwrite_violation_o0288.json')))
w('· 单文件发布从此只走 `instruments/gated_push.py`（blob %s）：路径已在架上且字节不同就 REFUSE 并打印两枚 '
  'blob + 该路径的全部 commit；字节相同就 SKIP。')
w('```')
w('')
w('对 ORD-0288 读数本身没有影响：7 格、两次突变体反证、耐久/作废的结论都不依赖那枚清单文件的字节。'
  '受影响的是我那句"0 覆盖"的口径 —— 那就是本条要更正的全部内容。')
w('')
w(CLOSING.decode('utf-8'))
body = chr(10).join(L) + chr(10)
(B / 'bus_post_o0288_correction.md').write_text(body, encoding='utf-8', newline='\n')
print('correction', len(body.encode('utf-8')), 'B')
made = api('/CityNexus-Workspace/issues/1/comments', json.dumps({'body': body}).encode('utf-8'))
cid = made['id']
back = api('/CityNexus-Workspace/issues/comments/%d' % cid)
tail = [x for x in back['body'].rstrip().split(chr(10)) if x.strip()][-1]
note = {'comment_id': cid, 'corrects': 'issuecomment-%d' % ORIG,
        'remote_body_bytes': len(back['body'].encode('utf-8')),
        'local_body_bytes': len(body.encode('utf-8')),
        'remote_equals_local': back['body'] == body,
        'tail_equals_closing_line': tail.encode('utf-8') == CLOSING,
        'closing_line_blob_40_hex': closing_blob,
        'path_under_audit': VICTIM, 'writes_seen_on_it': len(pairs)}
(B / 'bus_readback_o0288_correction.json').write_text(json.dumps(note, ensure_ascii=False, indent=1),
                                                      encoding='utf-8', newline='\n')
print('POSTED issuecomment-%d | tail ok: %s | remote==local: %s'
      % (cid, note['tail_equals_closing_line'], note['remote_equals_local']))
if not note['tail_equals_closing_line']:
    raise SystemExit('TAIL MISMATCH')
