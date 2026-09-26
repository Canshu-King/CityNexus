"""Bus note for the single re-run on `ab12c17a`: two baseline items re-measured, one of my own numbers voided.

Same discipline as the previous note, kept short because the ledger block carries the detail: readings only, no
verdict, grading left to E. Three things are worth a dispatcher's minute here - the confound I caught in my own
reading of the dead-id screen, the fact that the artefact cited for this generation pins no bytes so my own three
GETs do instead, and that the mirror ref has already moved past the generation I was told to measure with the
wizard's own source in the drift.

Posting is idempotent by a cached comment id, and the tail line is compared byte-for-byte against the bytes read
from CLOSING_LINE.txt rather than retyped. `--dry` prints without posting.
"""
from __future__ import annotations

import hashlib
import importlib.util as iu
import json
import pathlib
import sys
import time
import urllib.request

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

OUT = pathlib.Path('D:/moodle/_hjp3_0323walk_0926')
SRC = pathlib.Path('D:/moodle/HJ-P3_evidence')
W = 'evidence/hjp3-journey-recheck-ab12c17a'
spec = iu.spec_from_file_location('pub', str(SRC / 'p3_publish.py'))
pub = iu.module_from_spec(spec)
spec.loader.exec_module(pub)
SC = json.loads((OUT / 'r5_recheck_scored.json').read_text(encoding='utf-8'))
DR = json.loads((OUT / 'r5_tip_drift.json').read_text(encoding='utf-8'))
FR = json.loads((OUT / 'r5_deadid_fresh.json').read_text(encoding='utf-8'))
WL = json.loads((OUT / 'write_ledger_recheck.json').read_text(encoding='utf-8'))
PRF = json.loads((OUT / 'ledger_inbox_proof_recheck.json').read_text(encoding='utf-8'))
tip, tree, _r = pub.branch_rows()
BLOB = {x['path']: x['sha'] for x in pub.api('/git/trees/' + tip + '?recursive=1')['tree']}
BLK = lambda p: BLOB.get(p, 'NOT_ON_BRANCH')
CLOSING = pathlib.Path('D:/moodle/_qoder_cmdr_ref_20260921/live_checks/CLOSING_LINE.txt').read_bytes()
assert len(CLOSING) == 83
assert hashlib.sha1(b'blob 83' + bytes([0]) + CLOSING).hexdigest() == \
    'b82ca923501c312b6931ad894c607ab9e43e1137'
Q = chr(96)
J = SC['judgments']
B1 = SC['baseline_items']['B1_confirm_create']
B2 = SC['baseline_items']['B2_dead_journey_id']
leg = B1['leg_now']
post_id = OUT / 'r5_bus_recheck_id.txt'


def gh(path, payload=None):
    r = urllib.request.Request('https://api.github.com' + path,
                               data=json.dumps(payload).encode() if payload else None,
                               method='POST' if payload else 'GET')
    r.add_header('Authorization', 'Bearer ' + pub.TOK)
    r.add_header('Accept', 'application/vnd.github+json')
    r.add_header('User-Agent', 'hjp3-r5-bus-recheck')
    if payload:
        r.add_header('Content-Type', 'application/json')
    with urllib.request.urlopen(r, timeout=180) as f:
        return json.loads(f.read().decode())


L = []
L.append('## 新代次只重跑了一次：两件「用户做不到」的读数，一件我自己的污染数被我作废 · HJ-P3 aad2d1f2')
L.append('')
L.append(f'四元组：**scope** = 第 3 步按下 {Q}确认创建{Q} 与一个不存在的 journey id 那一屏；**generation** = '
         f'{Q}{DR["generation_named_by_the_commander"]}{Q}（链上此刻点名资产 {Q}{SC["faces_i_read_myself_over_get"]["assets_named_by_the_shell"]["js"]}{Q}，'
         f'我自己 GET 回来的字节与 sha256 在件里）；**artifact** = 末段那几条 40 位；**method** = 我自己的 Chromium '
         f'泳道（390×844@3、hasTouch、zh-CN）走部署链，行程只走一次，其余全是只读 GET 或不带点击的一次导航；'
         f'点按用 role 并把被点的节点写进件里；产品字节 0 改。')
L.append('')
L.append(f'**① 第 3 步仍然建不成行程**：按的是 {Q}{B1["node_pressed_by_role"][0]["text"]}{Q}（disabled = '
         f'{B1["node_pressed_by_role"][0]["disabled"]}，top {B1["node_pressed_by_role"][0]["top"]} px，class '
         f'{Q}{B1["node_pressed_by_role"][0]["cls"]}{Q}）；腿照发 = {leg.get("m")} {Q}{leg.get("url")}{Q}，请求体 '
         f'{leg.get("req_bytes")} B，浏览器侧状态 {leg.get("status")}、类型 {leg.get("ct")}；人留在向导 = '
         f'{B1["still_on_wizard_now"]}，localStorage 里没有 journey id（件里那一格写作 null）。屏上那两句话与'
         f'上一代逐字相同 = {J["B1_sentences_word_for_word_unchanged"]}，腿的形态与基线逐字段相同 = '
         f'{J["B1_leg_shape_unchanged_from_the_baseline"]}。新量到的一条：这张引用了状态码的失败屏上没有折叠块'
         f'（{Q}details_blocks_on_the_failure_screen{Q} = {B1["details_blocks_on_the_failure_screen"]}），而干净'
         f'上下文的同一个壳有；按下之后 DOM 里多出一枚 {Q}data-testid{Q} 锚点，其名字我在服务资产字节里按字面量'
         f'取到了偏移与次数凭据（弱于 DOM 读数，已在件里写明）。')
L.append('')
L.append(f'**② 坏 id 那一屏——我先把自己那枚数作废了**：我第一趟在同一上下文里先走完向导再导航，读到一大段文本，'
         f'几乎要说成「产品改了」。抓我的信号是那段文本里有我亲手填的 {Q}天津站{Q} 与 {Q}CNY 3000{Q}；而且那张截图与'
         f'上一代那张自然态复核屏挂在同一枚 blob 上（'
         f'{Q}evidence/hjp3-journey-walk-c740f45d/shots/W3_7_natural.png{Q} 与 '
         f'{Q}{W}/shots/RC_3_dead_id.png{Q} 同号 = {BLOB.get("evidence/hjp3-journey-walk-c740f45d/shots/W3_7_natural.png") == BLOB.get(W + "/shots/RC_3_dead_id.png")}，'
         f'{BLK(W + "/shots/RC_3_dead_id.png")}），所以那段文本是复核屏自己。我判这一格被我自己的上下文污染 = '
         f'{J["B2_my_walked_number_was_confounded_by_my_own_context"]}。于是用不点击、不键入的干净上下文重测：渲染的还是同一个壳，屏上说的是'
         f'{Q}{FR["after_opening_details"]["tail_lines"][1]}{Q}，而不是「这个 id 不存在」；异常字面进文本 = '
         f'{FR["after_opening_details"]["exception_in_text"]}、属性命中为空。与基线相比屏上真正变的只有一行 = '
         f'{J["B2_shell_text_differs_from_the_baseline_by_exactly_one_line"]}：{Q}'
         f'{B2["text_lines_that_actually_differ_from_the_baseline"][1][1:]}{Q} 取代了短的那句。')
L.append('')
L.append(f'**③ 你引的那枚件钉不住字节，我用自己的 GET 顶上（事实，不是指控）**：blob 2fcaaf3e49295a06f3fe9c03db3f54239bf6e610 '
         f'我取回并重算 = {J["his_cited_blob_resolves_to_the_bytes_i_read"]}，schema 是 '
         f'{SC["commander_artefact_as_I_READ_IT"]["schema"]}、overall {SC["commander_artefact_as_I_READ_IT"]["overall"]}，'
         f'但它里面没有资产行、也没有代次字段 = {J["his_artefact_carries_neither_asset_rows_nor_a_generation_field"]}；'
         f'所以本块的字节绑定是我自己三行 GET（JS / CSS / {Q}/v10-sw.js{Q} 的字节与 sha256 都在件里，'
         f'JS 那行与我走路那趟、与字面量扫描那趟各自独立取得的结果相同 = '
         f'{J["my_two_independent_gets_of_the_js_asset_agree_with_my_click_pass"]}）。')
L.append('')
L.append(f'**④ 代次已经漂了（这件要你定）**：现读 {Q}refs/heads/mirror/integration-frontend-apple-pass1{Q} = '
         f'{DR["mirror_tip_read_now"]}，比你点名的那一尖超前 {DR["commits_ahead"]} 笔，而且漂的那几笔里有向导本体那支源文件 = '
         f'{DR["touches_the_wizard_source"]}；单号看得到 ORD-0332、ORD-0344、ORD-0344-b、ORD-0346 —— 也就是 ORD-0349 '
         f'那一族正在改的东西还没上到手机链。我没有重建、没有换代、没有再走一遍（你说只重跑一次），所以本批读数全部锁在 '
         f'{DR["generation_named_by_the_commander"]}。要不要换代后再叫我走一次，等你号令。')
L.append('')
L.append(f'**⑤ 三面射程不变**：列表 / 收件箱 / 错误边界我仍然一次都没抵达，坏 id 落回同一个壳（ORD-0351 的射程与上回一致）。')
L.append(f'**⑥ 记账**：本前缀 {WL["files_under_prefix"]} 枚路径，每枚都只有一笔提交 = '
         f'{all(v == 1 for v in WL["commits_per_path"].values())}（三枚已知双发的反控各读到 '
         f'{WL["controls_known_to_hold_two_writes"][0]["commits"]} 笔 ⇒ 计数器不瞎）；中间有一次 PUT 被 409 乐观并发'
         f'拒掉，重投同一枚名字后计数器仍然一笔，说明那次拒绝没有落笔。')
L.append('')
L.append(f'坐标：走路读数 `{W}/r5_recheck_raw.json` {BLK(W + "/r5_recheck_raw.json")}；评分件 '
         f'`{W}/r5_recheck_scored.json` {BLK(W + "/r5_recheck_scored.json")}；三面字节 '
         f'`{W}/r5_faces_get.json` {BLK(W + "/r5_faces_get.json")}；字面量扫描 `{W}/r5_anchor_scan.json` '
         f'{BLK(W + "/r5_anchor_scan.json")}；干净上下文读数 `{W}/r5_deadid_fresh.json` '
         f'{BLK(W + "/r5_deadid_fresh.json")}；代次漂移 `{W}/r5_tip_drift.json` {BLK(W + "/r5_tip_drift.json")}；'
         f'写入计数 `{W}/write_ledger_recheck.json` {BLK(W + "/write_ledger_recheck.json")}；本块 Q43 r4d 回执 '
         f'`{W}/ledger_inbox_proof_recheck_0930_q43r4d.json` '
         f'{BLK(W + "/ledger_inbox_proof_recheck_0930_q43r4d.json")}（块 '
         f'{pathlib.Path(PRF["block_file"]).name}，{PRF["bytes"]} B，rc {PRF["q43_rc"]}）；上一块 '
         f'aad2d1f2_0902.md 缺的那份回执补发在 `{W}/ledger_inbox_proof_walk_0902_q43r4d.json` '
         f'{BLK(W + "/ledger_inbox_proof_walk_0902_q43r4d.json")}；干净上下文那张像素 '
         f'`{W}/shots/RC_4_dead_id_fresh.png` {BLK(W + "/shots/RC_4_dead_id_fresh.png")}。')
L.append('')
L.append(CLOSING.decode('utf-8'))
body = '\n'.join(L) + '\n'
(OUT / 'r5_bus_recheck.md').write_text(body, encoding='utf-8', newline='\n')
if '--dry' in sys.argv:
    print(body)
    raise SystemExit(0)
if post_id.exists():
    cid = int(post_id.read_text(encoding='utf-8').strip())
    print('already posted, id', cid)
else:
    cid = gh('/repos/Canshu-King/CityNexus-Workspace/issues/1/comments', {'body': body})['id']
    post_id.write_text(str(cid) + '\n', encoding='utf-8', newline='\n')
    print('posted id', cid)
time.sleep(2)
back = gh('/repos/Canshu-King/CityNexus-Workspace/issues/comments/%d' % cid)
tail = [x for x in back['body'].rstrip().splitlines() if x.strip()][-1]
rec = {'comment_id': cid, 'permalink': back['html_url'], 'created_at': back['created_at'],
       'body_bytes': len(back['body'].encode('utf-8')), 'remote_equals_local': back['body'] == body,
       'tail_bytes': len(tail.encode('utf-8')),
       'tail_equals_fetched_closing_line': tail.encode('utf-8') == CLOSING,
       'generation': DR['generation_named_by_the_commander'], 'branch_tip': tip,
       'read_at': time.strftime('%H:%M:%S')}
(OUT / 'r5_bus_recheck_readback.json').write_text(json.dumps(rec, ensure_ascii=False, indent=1),
                                                 encoding='utf-8', newline='\n')
print(json.dumps({k: rec[k] for k in ('comment_id', 'permalink', 'remote_equals_local',
                                      'tail_equals_fetched_closing_line')}, ensure_ascii=False))
