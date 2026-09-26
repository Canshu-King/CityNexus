"""Bus note for the newest phone generation: the two re-measured items, the ORD-0357 acceptance, three findings.

Short by design - the ledger block carries the detail. Readings only, grading to E, every figure next to the
artefact field it came from, the tail line read from CLOSING_LINE.txt, and posting made idempotent by a cached
comment id. `--dry` prints without posting.
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
OUT = pathlib.Path('D:/moodle/_hjp3_d3j0_0926')
SRC = pathlib.Path('D:/moodle/HJ-P3_evidence')
PFX = 'evidence/hjp3-d3j0mgvR-walk-0926'
spec = iu.spec_from_file_location('pub', str(SRC / 'p3_publish.py'))
pub = iu.module_from_spec(spec)
spec.loader.exec_module(pub)
SC = json.loads((OUT / 'r7_scored.json').read_text(encoding='utf-8'))
EC = json.loads((OUT / 'r7_entry_check.json').read_text(encoding='utf-8'))
C4 = json.loads((OUT / 'r7_copy_link_r4.json').read_text(encoding='utf-8'))
PID = json.loads((OUT / 'r7_pixel_identity_with_previous.json').read_text(encoding='utf-8'))
PRF = json.loads((OUT / 'ledger_inbox_proof_r7.json').read_text(encoding='utf-8'))
IDCACHE = OUT / 'r7_bus_note_id.txt'
CLOSING = pathlib.Path('D:/moodle/_qoder_cmdr_ref_20260921/live_checks/CLOSING_LINE.txt').read_bytes()
assert len(CLOSING) == 83
assert hashlib.sha1(b'blob 83' + bytes([0]) + CLOSING).hexdigest() == \
    'b82ca923501c312b6931ad894c607ab9e43e1137'
tip, _r, _x = pub.branch_rows()
BLOB = {e['path']: e['sha'] for e in pub.api('/git/trees/' + tip + '?recursive=1')['tree'] if e.get('type') == 'blob'}
BLK = lambda p: BLOB.get(p, 'NOT_ON_BRANCH')
Q = chr(96)
J = SC['judgments']
c1a = SC['cell_1a_dead_stored_id']
c1b = SC['cell_1b_saved_behind_rows']
c2 = SC['cell_2_ord0357_copy_link']
f1 = SC['cell_3_new_findings']['f1_trips_landing_says_there_is_nothing_to_look_at']
f2 = SC['cell_3_new_findings']['f2_ai_state_and_the_sheet_disagree']
f3 = SC['cell_3_new_findings']['f3_desktop_entries_unreachable_at_390']


def gh(path, payload=None):
    r = urllib.request.Request('https://api.github.com' + path,
                               data=json.dumps(payload).encode() if payload else None,
                               method='POST' if payload else 'GET')
    r.add_header('Authorization', 'Bearer ' + pub.TOK)
    r.add_header('Accept', 'application/vnd.github+json')
    r.add_header('User-Agent', 'hjp3-r7-bus')
    if payload:
        r.add_header('Content-Type', 'application/json')
    for i in range(3):
        try:
            with urllib.request.urlopen(r, timeout=180) as f:
                return json.loads(f.read().decode())
        except Exception:  # noqa: BLE001
            if i == 2:
                raise
            time.sleep(3)


L = []
L.append('## 今天这一代手机上真人走过：旧两件逐字重测（与上一代像素同一）、ORD-0357 用了一次真链接、三件新缺陷带接口与字节 · HJ-P3 aad2d1f2')
L.append('')
L.append(f'四元组：**scope** = 死 stored journey id 那一屏、「已保存」这类话背后的设备行、ORD-0357 复制行程链接后在干净设备重开、'
         f'以及新缺陷；**generation** = 链上两入口此刻都点名 {Q}{EC["entries"][1]["asset_named_by_the_shell"]}{Q}'
         f'（{EC["entries"][1]["asset_row"]["bytes"]} B，sha256 前缀 `{EC["entries"][1]["asset_row"]["sha256"][:16]}…`，'
         f'与你给的包名一致 = {J["both_entries_serve_the_bundle_the_commander_named"]}；镜子 ref 此刻 = '
         f'{SC["measurement_scope"]["generation_read_from_the_ref_in_this_run"]}；这枚包由哪一笔切出我不证，换代归你）；'
         f'**artifact** = 末段那几条 40 位；**method** = own Chromium 390×844@3 touch zh-CN 走公网入口，每格一个全新上下文，'
         f'本车道这一代一共起车 {SC["launches_on_this_lane"]} 次 ⇒ 我**不**对底图/瓦片下结论。')
L.append('')
L.append(f'**旧事两件，逐字重测**：')
L.append(f'· 死 id 那一屏仍然具名说「不存在」= {J["C_dead_id_screen_still_does_not_claim_the_network"]}，屏上文本与上一代'
         f'逐字相同 = {c1a["identical_to_the_previous_generation_word_for_word"]}，两张截图（不开与开了折叠）也与上一代'
         f'同一枚 sha256 = {PID["pairs"]["C1_dead_id_closed.png"]["identical"]} / '
         f'{PID["pairs"]["C2_dead_id_open.png"]["identical"]}（见证件）；拒收后 id 被清 = '
         f'{J["C_stored_id_is_still_cleared_after_the_rejection"]}。屏上那句话原文我抄进了块里。')
L.append(f'· 服务器那条腿 {c1a["the_leg"][0][0]} `…/experience` 答 状态 {c1a["the_leg"][0][2]}、正文 {c1a["the_leg"][0][3]} B，'
         f'字段 `error.code={c1a["the_leg"][0][6]}`、`error_receipt_id={c1a["the_leg"][0][5]}`；屏上（不开与开了）'
         f'CNX 号仍然 0 枚 = {J["C_server_receipt_still_never_reaches_the_screen"]}，而且这枚号与上一代同一路线读到的是同一枚。')
L.append(f'· 「已保存」那一件：设备里 `citynexus-offline/journeys` 行数 = '
         f'{c1b["device_after_a_real_boot"]["rows"]["journeys"]}、workbox 条目 '
         f'{list(c1b["device_after_a_real_boot"]["cache_entry_counts"].values())[0]} 条 = '
         f'{J["D_the_device_holds_one_offline_copy"]}；我走的五屏（今天/我的/行程/预订/行程工作台）没有一句含「已保存」= '
         f'{J["D_no_saved_sentence_rendered_on_the_five_screens"]} —— 这是「这五屏没渲染」，不是「这句话不存在」，'
         f'其余屏我没到过。')
L.append('')
L.append(f'**ORD-0357 我当真用了一次（这是验收，不是审查）**：控件在 {Q}/v8/trips{Q} 的「预订」子页之后，'
         f'`data-testid=journey-link-copy`、`data-cnx-field={c2["control"]["data_cnx_field"]}`、文本「{c2["control"]["text"]}」、'
         f'距顶 {c2["control"]["top_px"]} px、未禁用且在视口内；按下 → 剪贴板拿到 {Q}{c2["clipboard"]}{Q}，屏上那句逐字 = '
         f'`{c2["message_line_verbatim"]}`；一台没见过的设备打开这条链接 → 落点行程首页、`citynexus.v8.journey_id` 就是我'
         f'创建那趟 = {J["E_the_copied_link_lands_a_clean_device_on_that_journey"]}，屏上出现行程标题「天津之旅」。'
         f'一格如实分野：重开后的屏与按下复制那块面板文本不同 = '
         f'{J["E_the_reopened_screen_is_not_the_screen_the_copy_came_from"]}（{c2["reopen_in_a_clean_device"]["copy_screen_len"]} vs '
         f'{c2["reopen_in_a_clean_device"]["reopen_len"]} 字）—— 产品主张是「同一趟行程」，这条成立；「同一块面板」不是它的承诺。')
L.append('')
L.append(f'**三件新的（一步可重现，带接口与字节，你可直接开单）**：')
L.append(f'· 缺陷一 · 底栏「行程」把有候选方案的行程说成没得看：落地屏 {len(f1["text_verbatim"])} 字，写着「还没有可看的行程」'
         f'与「这个行程还没有选定的方案」；同一趟行程在首页渲染了 {f1["hub_day_rows_rendered"]} 天逐日预览并明写「以下只是其中一个'
         f'候选方案的预览，你还没有采用它」。接口：`GET /api/v1/journeys/<id>/plans` 200 / {f1["plans_leg"][0][3]} B、'
         f'`GET /api/v1/journeys/<id>/experience` 200 / {f1["experience_leg"][0][3]} B、'
         f'`GET /api/v1/places?city_code=CN-TIANJIN` 200 / {f1["places_leg"][0][3]} B。')
L.append(f'· 缺陷二 · 屏上把用户指向运维已关掉的路：`/api/v1/health` 200 / {f2["health_bytes"]} B 里 '
         f'{Q}ai={f2["health_fields"]["ai"]}{Q}、{Q}ai_state={f2["health_fields"]["ai_state"]}{Q}，而「AI 帮我规划」未禁用、'
         f'按下开出的 sheet 里写 `{f2["sheet_lines_verbatim"][3]}` 并给「开始规划」；我**没有**按它（更长流程与开关不归我试穿）。'
         f'该按钮发了 `GET /api/v1/agent/runtime-status` 200 / {f2["runtime_status_leg"][0][3]} B。')
L.append(f'· 缺陷三 · 手机上到那枚复制控件要 {f3["hops_to_the_copy_control"]} 跳：顶 0 px 那组（桌面侧栏）含'
         f'{"、".join(f3["buttons_at_top_zero"][:6])}…，移动底栏只有 {"、".join(f3["bottom_nav_at_390"])} 五枚；'
         f'标签「旅行票夹」用 DOM 文本命中 {f3["role_query_hit_for_the_desktop_label"]["dom_text_count"]}、用 role 命中 '
         f'{f3["role_query_hit_for_the_desktop_label"]["role_count"]}（即那份入口在 390 宽不可达）。')
L.append('')
L.append(f'**我自己这一代记 {len(SC["instrument_faults_of_mine"])} 笔仪器错**（含两趟未命中的探索，件都按新名交了）：'
         f'把「控件不存在」报错过一次（真因是子页没点到）、把 role 命不中当成读屏命名缺口一次（真因是桌面侧栏不可达）、'
         f'页面里调 Node 助手一次、把代理挡路当成入口没起来一次。')
L.append('')
L.append(f'坐标：评分件 `{PFX}/r7_scored.json` {BLK(PFX + "/r7_scored.json")}；入口与包身份 `{PFX}/r7_entry_check.json` '
         f'{BLK(PFX + "/r7_entry_check.json")}；四格走路 `{PFX}/r7_walk.json` {BLK(PFX + "/r7_walk.json")}；验收 '
         f'`{PFX}/r7_copy_link_r4.json` {BLK(PFX + "/r7_copy_link_r4.json")}；AI 引导 `{PFX}/r7_ai_disabled.json` '
         f'{BLK(PFX + "/r7_ai_disabled.json")}；跨代像素同一 `{PFX}/r7_pixel_identity_with_previous.json` '
         f'{BLK(PFX + "/r7_pixel_identity_with_previous.json")}；块 '
         f'{pathlib.Path(PRF["block_file"]).name}（{PRF["bytes"]} B，门 claims {PRF["claims_checked"]} / findings '
         f'{PRF["findings"]}，rc {PRF["q43_rc"]}），回执随后按新名上架。')
L.append('')
L.append(CLOSING.decode('utf-8'))
body = '\n'.join(L) + '\n'
(OUT / 'r7_bus_note.md').write_text(body, encoding='utf-8', newline='\n')
if '--dry' in sys.argv:
    print(body)
    raise SystemExit(0)
if IDCACHE.exists():
    cid = int(IDCACHE.read_text(encoding='utf-8').strip())
    print('already posted, id', cid)
else:
    cid = gh('/repos/Canshu-King/CityNexus-Workspace/issues/1/comments', {'body': body})['id']
    IDCACHE.write_text(str(cid) + '\n', encoding='utf-8', newline='\n')
    print('posted id', cid)
time.sleep(2)
back = gh('/repos/Canshu-King/CityNexus-Workspace/issues/comments/%d' % cid)
tail = [x for x in back['body'].rstrip().splitlines() if x.strip()][-1]
rec = {'comment_id': cid, 'permalink': back['html_url'], 'created_at': back['created_at'],
       'body_bytes': len(back['body'].encode('utf-8')), 'remote_equals_local': back['body'] == body,
       'tail_bytes': len(tail.encode('utf-8')), 'tail_equals_fetched_closing_line': tail.encode('utf-8') == CLOSING,
       'bundle': EC['entries'][1]['asset_named_by_the_shell'], 'branch_tip': tip,
       'read_at': time.strftime('%H:%M:%S')}
(OUT / 'r7_bus_note_readback.json').write_text(json.dumps(rec, ensure_ascii=False, indent=1),
                                               encoding='utf-8', newline='\n')
print(json.dumps({k: rec[k] for k in ('comment_id', 'permalink', 'remote_equals_local',
                                      'tail_equals_fetched_closing_line')}, ensure_ascii=False))
