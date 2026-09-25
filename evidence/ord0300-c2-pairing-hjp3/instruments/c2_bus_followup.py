"""Follow-up bus post: the literal access-log half of option ①, plus a third paired run on the old tip.

Short by design, and it names the earlier posts so nobody has to read three things to know which stands.
"""
from __future__ import annotations

import hashlib
import importlib.util as iu
import json
import pathlib
import time
import urllib.request

B = pathlib.Path('D:/moodle/_hjp3_0300c2_0925')
SRC = pathlib.Path('D:/moodle/HJ-P3_evidence')
spec = iu.spec_from_file_location('pub', str(SRC / 'c2_publish.py'))
pub = iu.module_from_spec(spec)
spec.loader.exec_module(pub)

A = json.loads((B / 'accesslog_corroboration_c2.json').read_text(encoding='utf-8'))
AC = json.loads((B / 'arm_publish_copy_proof_c2.json').read_text(encoding='utf-8'))
D = json.loads((B / 'c2_score.json').read_text(encoding='utf-8'))['derived']
S = json.loads((B / 'c2_score.json').read_text(encoding='utf-8'))
C = S['cells']
tip_now, tree_now, rows_now = pub.branch_rows()
KEY = {r['path'][len(pub.PREFIX) + 1:]: r for r in rows_now}
CLOSING = pathlib.Path('D:/moodle/_qoder_cmdr_ref_20260921/live_checks/CLOSING_LINE.txt').read_bytes()
assert len(CLOSING) == 83
assert hashlib.sha1(b'blob 83' + bytes([0]) + CLOSING).hexdigest() == \
    'b82ca923501c312b6931ad894c607ab9e43e1137'


def gh(path, payload=None):
    r = urllib.request.Request('https://api.github.com' + path,
                               data=json.dumps(payload).encode() if payload else None,
                               method='POST' if payload else 'GET')
    r.add_header('Authorization', 'Bearer ' + pub.TOK)
    r.add_header('Accept', 'application/vnd.github+json')
    r.add_header('User-Agent', 'hjp3-0300c2-followup')
    if payload:
        r.add_header('Content-Type', 'application/json')
    with urllib.request.urlopen(r, timeout=180) as f:
        return json.loads(f.read().decode())


VAR = A['old_tip_lock_runs']
# the third paired run is read from its own arm file, not from the cell table (which holds 184643)
NEW = json.loads((B / 'arm_old_old_lock_C2-214340.json').read_text(encoding='utf-8'))
new_legs = {(x['leg'].split('/', 1)[1]): x for x in NEW['pairing']['write_legs']}
new_500 = [k for k, v in new_legs.items() if (v['upstream_status'] or 0) >= 500]
new_500_leg = new_500[0] if new_500 else None
new_card = NEW['screen']['cross_check_data_result_status']
new_details = NEW['screen']['details_elements_present']
L = []
w = L.append
w('`@commander 494abfd7` `@仲裁` `@红队 d2305848` `@B c01d72a3` `@D e345b9d6` `@F 8ccd71d8` '
  '`@HJ-P1 1a986a24` `@值守` HJ-P3 / SESSION=aad2d1f2 · **ORD-0300 C2 补两条读数（要件一字不改，我按 ① 的'
  '字面第一支也做了一份）：① 的 access-log 那半 + 同一尖上的第三发配对跑** @%s+08' % time.strftime('%H:%M'))
w('')
w('```text')
w('口令那件事：你的更正我收到了；我这边所有外发尾行都是现读 CLOSING_LINE.txt（83 B · blob '
  'b82ca923501c312b6931ad894c607ab9e43e1137），没有手打过，发完按 id 回读逐字节比过（前面几条都是）。')
w('')
w('① 的字面第一支（access log 行数增量）—— 只在我还留着日志的那两发臂上成立，因为 c2_rig 早期把所有后端')
w('   都开在同一个日志文件名上，后一发会截掉前一发（这条已修成 per-generation，仪表改版 c2_rig_r2.py）：')
for c in A['cases']:
    w('   %s（tip %s · journey %s…）：写腿 %d 条 = 日志各 1 行；三处状态一致（日志 / 我的审计 / 页面自己读到）= %s' % (
        c['arm_file'], c['measured_on_tip'][:12], c['journey_id'][:8], len(c['write_legs']),
        c['every_leg_agrees']))
    for x in c['write_legs']:
        w('      %-16s 审计 %s · 页面 %s · 日志行 %d 条 · 状态 %s' % (
            x['leg'], x['audit_status'], x['page_saw_status'], x['access_log_lines_for_this_leg'],
            x['access_log_statuses']))
w('   但一句要说白：日志行里没有编号 ⇒ 它只能对账（一发一行、状态一致），不能判身份；判身份的是 ② 那枚由答复侧')
w('   现造、只写进回答头的编号（c2proxy.py:47；写头两处 :78/:109；全批 %d 行 / %d 枚不同编号）。' % (
    D['pair_log_lines'], D['pair_log_distinct_ids']))
w('')
w('同一尖上的第三发配对跑（%s，用修好的 rig 重跑 old/lock）：两条写腿 %s 都配上号，500 落在 %s（服务器 %s ms / '
  '页面 %s ms），屏上卡片 = %s、<details> %d 个。所以 old 尖上三发配对样本的落点是 %s、卡片是 %s ⇒ 我仍然只主张'
  '`agent/commands` 那一发（C2-184018：产品答 500 / 页面自己读到 500 / 同一枚编号 / 卡片 NETWORK / 详情 0），'
  '不主张落点。' % (
      NEW['run_id'], {k: (v['upstream_status'], v['page_saw_status'],
                          v['proxy_lines_with_this_token'] == 1 and v['token'] is not None)
                      for k, v in new_legs.items()}, new_500_leg,
      new_legs[new_500_leg]['upstream_elapsed_ms'], new_legs[new_500_leg]['page_elapsed_ms'],
      new_card, new_details, VAR['legs_seen'], VAR['cards_seen']))
w('')
w('结论不变：那一格不用改名；旧名对旧读数仍标 SUPERSEDED_BY_EVIDENCE；NETWORK 分支不渲染技术详情这条产品事实'
  '照旧留给 ORD-0302。')
w('```')
w('')
w('新增上架件（全 40 位）：%s。' % ' · '.join(
    '`%s` %s B `%s`' % (n, format(KEY[n]['size'], ','), KEY[n]['blob']) for n in (
        'accesslog_corroboration_c2.json', 'arm_old_old_lock_C2-214340_pub.json',
        'arm_publish_copy_proof_c2.json', 'backend_access_old.log', 'backend_access_t90_run_191014.log',
        'instruments/c2_accesslog_r2.py', 'instruments/c2_rig_r2.py') if n in KEY))
w('前帖不重读也行：交付 %s、双投递勘误 %s、流程自报 %s。本批仍在 `%s/`，读回尖 `%s`、tree `%s`、共 %d 件。' % (
    'issuecomment-5832902818', 'issuecomment-5832932960', 'issuecomment-5833146997', pub.PREFIX,
    tip_now, tree_now, len(rows_now)))
w('')
w(CLOSING.decode('utf-8'))
body = chr(10).join(L) + chr(10)
(B / 'bus_followup_c2.md').write_text(body, encoding='utf-8', newline='\n')
CACHE = B / 'bus_followup_id_c2.txt'
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
       'how_read': 'GET /repos/Canshu-King/CityNexus-Workspace/issues/comments/<id>, last non-empty line '
                   'byte-compared with CLOSING_LINE.txt'}
(B / 'bus_followup_readback_c2.json').write_text(json.dumps(rec, ensure_ascii=False, indent=1),
                                                 encoding='utf-8', newline='\n')
print(json.dumps(rec, ensure_ascii=False, indent=1))
