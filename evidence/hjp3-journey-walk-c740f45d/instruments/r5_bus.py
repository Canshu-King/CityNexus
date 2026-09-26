"""Bus note for the walkthrough: what a traveller can and cannot do on the new phone generation.

Kept short because the block carries the detail. The two findings worth a dispatcher's attention are stated as
readings, never as verdicts: the sealed-demo sentence claims the server answered in a fate where nothing was ever
reached, and the two fates are pixel-identical; and confirming a journey on this chain cannot succeed because no
backend answers at all, which the screen says honestly but leaves the traveller with no way onward.
"""
from __future__ import annotations

import hashlib
import importlib.util as iu
import json
import pathlib
import sys
import time
import urllib.request

OUT = pathlib.Path('D:/moodle/_hjp3_0323walk_0926')
SRC = pathlib.Path('D:/moodle/HJ-P3_evidence')
W = 'evidence/hjp3-journey-walk-c740f45d'
spec = iu.spec_from_file_location('pub', str(SRC / 'p3_publish.py'))
pub = iu.module_from_spec(spec)
spec.loader.exec_module(pub)
RS = json.loads((OUT / 'r5_walk_scored.json').read_text(encoding='utf-8'))
WA = json.loads((OUT / 'r5_who_answered.json').read_text(encoding='utf-8'))
PRF = json.loads((OUT / 'ledger_inbox_proof_walk.json').read_text(encoding='utf-8'))
tip, tree, _r = pub.branch_rows()
BLOB = {x['path']: x['sha'] for x in pub.api('/git/trees/' + tip + '?recursive=1')['tree']}
BLK = lambda p: BLOB.get(p, 'NOT_ON_BRANCH')
CLOSING = pathlib.Path('D:/moodle/_qoder_cmdr_ref_20260921/live_checks/CLOSING_LINE.txt').read_bytes()
assert len(CLOSING) == 83
assert hashlib.sha1(b'blob 83' + bytes([0]) + CLOSING).hexdigest() == \
    'b82ca923501c312b6931ad894c607ab9e43e1137'
Q = chr(96)
J = RS['judgments']
PIX = RS['screenshot_pixel_identity']
C1 = RS['cells']['C1_new_journey_wizard']
BAND = C1['band_between_step_bar_and_first_control']
CONF = C1['pressing_the_real_submit_button']
post = (CONF['legs_after_the_press'] or [{}])[0]


def gh(path, payload=None):
    r = urllib.request.Request('https://api.github.com' + path,
                               data=json.dumps(payload).encode() if payload else None,
                               method='POST' if payload else 'GET')
    r.add_header('Authorization', 'Bearer ' + pub.TOK)
    r.add_header('Accept', 'application/vnd.github+json')
    r.add_header('User-Agent', 'hjp3-r5-bus')
    if payload:
        r.add_header('Content-Type', 'application/json')
    with urllib.request.urlopen(r, timeout=180) as f:
        return json.loads(f.read().decode())


L = []
L.append('## 真人行程复验已在手机新代次走完（ORD-0323 / ORD-0339 那一代）：能走到第 3 步，建不成行程；'
         '一处文案在替一条从没到达的腿说话 · HJ-P3 aad2d1f2')
L.append('')
L.append(f'四元组：**scope** = 新建行程三步 → 确认创建、封存演示入口、三处故意弄坏的屏；**generation** = '
         f'{Q}{RS["generation"]}{Q}（链上页面点名的资产 {Q}{RS["artifact"]["asset_named_by_the_served_page"]}{Q} = '
         f'{RS["artifact"]["asset_bytes"]} B，与你说的名字同号 = {RS["artifact"]["name_matches_what_the_commander_named"]}）；'
         f'**artifact** = 末段那几条 40 位；**method** = 我自己的 Chromium 泳道走部署链，点按用 role 与真标签，'
         f'每屏读两次（原样 + 把所有 details 打开），腿的状态取浏览器网络层，截图逐张回验字节；'
         f'产品字节 0 改、路上看到的不修。')
L.append('')
L.append(f'**能做的**：走到第 3 步复核页 = {J["traveller_can_reach_the_review_step"]}（按「下一步」两次都换页）；'
         f'提交按钮不滚就按得到（在 {BAND["submit_button_top_px"][0]} px）。')
L.append(f'**做不到的**：现在建不成行程 = {J["traveller_can_create_a_journey_on_this_chain_right_now"]}（这条判据为真是'
         f'「建不成」的意思）—— 真按 '
         f'{Q}确认创建{Q} 之后发出 {post.get("m")} {Q}{post.get("url")}{Q}（请求体 {post.get("post_body_len")} B），'
         f'浏览器记到状态 {post.get("status")}，人留在第 3 步，localStorage 里没有 journey id。屏上那两句是人话且带动作：'
         f'{Q}{"；".join(CONF["lines_the_traveller_reads"])}{Q}（判据 '
         f'{J["the_refusal_screen_offers_an_action"]} / {J["the_refusal_screen_states_nothing_was_changed"]} / '
         f'{J["confirm_press_tells_the_traveller_why_in_words"]}）。')
L.append('')
L.append(f'**要你派单的一件（同一句话盖住两种腿）**：腿被拒（根本没连上任何东西）与「答了但内容用不了」这两种，'
         f'屏上是同一句 {Q}没读到封存演示的信息：服务器刚才答了，但答的内容我们用不了。{Q}，而且两屏截图的 sha256 '
         f'完全相同 = {PIX["refused_vs_empty500"]["pixel_identical"]}（各 {PIX["refused_vs_empty500"]["left_bytes"]} B）。'
         f'「到底有没有服务器答过」我是量出来的：把一条产品不可能有的路径与三条真 API 路径比签名，'
         f'{len(WA["readings"])} 条只剩一种签名（{RS["cells"]["C3_read_failure_copy"]["distinct_signatures"][0]}，'
         f'无 server 头 = {WA["verdict"]["no_reading_carries_a_server_header"]}）⇒ 那句话对其中一种腿做了它没依据的断言。'
         f'我只放事实，不判它该改成什么口径。')
L.append('')
L.append(f'**留白那格我自己重测了（不抄 ORD-0338）**：步骤条 padding-bottom = {BAND["trial_steps_padding_bottom_px"]} px，'
         f'圆点行顶 {BAND["step_dot_row_top_px"]} px、卡片顶 {BAND["card_top_px"]} px ⇒ 视觉间隙 '
         f'{BAND["visual_gap_dot_row_to_card_px"]} px，而盒子底到卡片只 {BAND["gap_from_the_steps_box_to_the_card_px"]} px；'
         f'卡片不滚动就看得见 = {BAND["card_visible_at_rest"]}、整页溢出 {BAND["scroll_overflow_px"]} px。'
         f'与「那是真 padding、不是在等数据」一致 = {J["the_ORD-0338_band_is_a_real_padding_not_data_waiting"]}。')
L.append(f'**量具两向自检**：我自建一张真会漏的页（异常字面进文本也进 data-*）跑同一条判据 ⇒ 文本 1 处 / 属性 1 处；'
         f'一张干净页同一判据 ⇒ 0 / 0（两向都过；Q71 的属性位一并扫）。折叠这一坑我改了测法：元素级与 body 级 '
         f'innerText 在折叠时都读不到（True / True），而我的判据读节点 nodeValue，text_content 那层不被折叠遮住 '
         f'⇒ 三处「扫到 0」都按两种读法各自交代，不当「屏上没有」用。')
L.append(f'**我自己的仪器错记 {len(RS["runs_excluded"])} 笔**（每笔都有机械信号，不是我事后认）：① 没填表就点'
         f'「下一步」却报「向导不动」；② 按没读过的标签名探「封存演示」入口；③ 用 getByText 命中步骤条上同名的'
         f'圆点标签，误报「按下确认什么都没发」。都写在块里并附截图，不覆盖成没有发生。')
L.append('')
L.append(f'**到不了因而不敢说干净的**：这枚包里没有为存储 journey id 准备的客户端路由，所以 /journey/<坏 id> 渲染同一个壳；'
         f'列表 / 收件箱 / 错误边界三面在当前状态下没有可点入口 ⇒ 那三面我标 NOT-REACHED，不标 clean。')
L.append(f'坐标：读数件 `{W}/journey_walk_readings.json` blob `{BLK(W + "/journey_walk_readings.json")}`；'
         f'签名件 `{W}/who_answered_the_500s.json` blob `{BLK(W + "/who_answered_the_500s.json")}`；'
         f'原始逐格 `{W}/raw_walk3_findings.json` blob `{BLK(W + "/raw_walk3_findings.json")}` / '
         f'`{W}/raw_finish_findings.json` blob `{BLK(W + "/raw_finish_findings.json")}`；'
         f'Q43 r4d 原判 `{W}/ledger_inbox_proof_walk_q43r4d.json` blob '
         f'`{BLK(W + "/ledger_inbox_proof_walk_q43r4d.json")}`（块 '
         f'{pathlib.Path(PRF["block_file"]).name}，{PRF["bytes"]} B，rc {PRF["q43_rc"]}）；'
         f'两张关键截图 blob `{BLK(W + "/shots/W3_4_fate_refused.png")}`（拒腿）与 '
         f'`{BLK(W + "/shots/W3_9_after_confirm.png")}`（按下确认之后）。')
L.append('')
L.append(CLOSING.decode('utf-8'))
body = '\n'.join(L) + '\n'
(OUT / 'r5_bus_note.md').write_text(body, encoding='utf-8', newline='\n')
if '--dry' in sys.argv:
    print(body)
    raise SystemExit(0)
CACHE = OUT / 'r5_bus_note_id.txt'
if CACHE.exists():
    cid = int(CACHE.read_text(encoding='utf-8').strip())
    print('already posted, id', cid)
else:
    cid = gh('/repos/Canshu-King/CityNexus-Workspace/issues/1/comments', {'body': body})['id']
    CACHE.write_text(str(cid) + '\n', encoding='utf-8', newline='\n')
    print('posted id', cid)
time.sleep(2)
back = gh('/repos/Canshu-King/CityNexus-Workspace/issues/comments/%d' % cid)
tail = [x for x in back['body'].rstrip().splitlines() if x.strip()][-1]
rec = {'comment_id': cid, 'permalink': back['html_url'], 'created_at': back['created_at'],
       'body_bytes': len(back['body'].encode('utf-8')), 'remote_equals_local': back['body'] == body,
       'tail_bytes': len(tail.encode('utf-8')),
       'tail_equals_fetched_closing_line': tail.encode('utf-8') == CLOSING,
       'generation': RS['generation'], 'branch_tip': tip, 'read_at': time.strftime('%H:%M:%S')}
(OUT / 'r5_bus_note_readback.json').write_text(json.dumps(rec, ensure_ascii=False, indent=1),
                                               encoding='utf-8', newline='\n')
print(json.dumps({k: rec[k] for k in ('comment_id', 'permalink', 'remote_equals_local',
                                      'tail_equals_fetched_closing_line')}, ensure_ascii=False))
