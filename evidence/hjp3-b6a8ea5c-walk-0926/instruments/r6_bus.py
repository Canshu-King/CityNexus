"""Bus note for the b6a8ea5c walk: three dispatchable readings, two infrastructure facts, and the ORD-0312 status.

Kept short because the ledger block carries the detail. Every figure quotes a field in a shipped artefact, and the
tail line is read from CLOSING_LINE.txt rather than typed. Posting is idempotent through a cached comment id, and
the note is read back by id and compared byte for byte afterwards. `--dry` prints without posting.
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
OUT = pathlib.Path('D:/moodle/_hjp3_b6a8_0926')
SRC = pathlib.Path('D:/moodle/HJ-P3_evidence')
PFX = 'evidence/hjp3-b6a8ea5c-walk-0926'
spec = iu.spec_from_file_location('pub', str(SRC / 'p3_publish.py'))
pub = iu.module_from_spec(spec)
spec.loader.exec_module(pub)
SC = json.loads((OUT / 'r6_readings_scored.json').read_text(encoding='utf-8'))
WA = json.loads((OUT / 'r6_walked_asset_witness.json').read_text(encoding='utf-8'))
DR = json.loads((OUT / 'r6_drift.json').read_text(encoding='utf-8'))
TW = json.loads((OUT / 'r6_tunnel_watch.json').read_text(encoding='utf-8'))
F = json.loads((OUT / 'r6_receipt_anchor_offline.json').read_text(encoding='utf-8'))
NAME_CACHE = OUT / 'r6_bus_note_id.txt'
CLOSING = pathlib.Path('D:/moodle/_qoder_cmdr_ref_20260921/live_checks/CLOSING_LINE.txt').read_bytes()
assert len(CLOSING) == 83
assert hashlib.sha1(b'blob 83' + bytes([0]) + CLOSING).hexdigest() == \
    'b82ca923501c312b6931ad894c607ab9e43e1137'
Q = chr(96)
tip, _rows, _x = pub.branch_rows()
BLOB = {e['path']: e['sha'] for e in pub.api('/git/trees/' + tip + '?recursive=1')['tree'] if e.get('type') == 'blob'}
BLK = lambda p: BLOB.get(p, 'NOT_ON_BRANCH')
J = SC['judgments']
dead_leg = SC['cell_C_dead_stored_id']['the_leg_that_answered']
fold = SC['cell_C_dead_stored_id']['fold']
groups = SC['cell_A_destinations_block']['group_heading_counts_mine_corrected']
stores = SC['cell_E_device_holds_a_copy']
rp = SC['receipt_is_per_incident_or_per_route']


def gh(path, payload=None):
    r = urllib.request.Request('https://api.github.com' + path,
                               data=json.dumps(payload).encode() if payload else None,
                               method='POST' if payload else 'GET')
    r.add_header('Authorization', 'Bearer ' + pub.TOK)
    r.add_header('Accept', 'application/vnd.github+json')
    r.add_header('User-Agent', 'hjp3-r6-bus')
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
L.append('## 公网手机上真人走过五格（号令者 17:2x 那一代）：后端活了、两件旧缺陷量到新态、服务器给的回执号上了线没上屏 · HJ-P3 aad2d1f2')
L.append('')
L.append(f'四元组：**scope** = {Q}看支持的目的地{Q} 不开/开了、新建行程三步到确认创建之后、设备里存着一枚服务器不认识的 '
         f'journey id 那一屏（归因详情开与不开）、「已保存」这类话背后的设备行数；**generation** = '
         f'{Q}{DR["named_by_the_commander"]}{Q}（链上服务的是 {Q}{WA["asset_path_recorded_by_the_browser_passes"]}{Q}，'
         f'{WA["re_read_over_the_local_hop"]["bytes"]} B、sha256 前缀 `{WA["re_read_over_the_local_hop"]["sha256"][:16]}…`，'
         f'见见证件）；**artifact** = 末段那几条 40 位；**method** = own headless Chromium 390×844@3 touch zh-CN，'
         f'公网入口，每格一个全新上下文，腿从浏览器响应对象读，设备侧读数在页面里取。')
L.append('')
L.append(f'**链路形状（和上一代不同，值得先知道）**：四条 API 路径四种签名、我编的那条路径不与真路径同签名 = '
         f'{J["an_application_answers_on_this_chain"]}；本地那跳 server: uvicorn、公网那跳 server: cloudflare，'
         f'走路那一分钟两边点名同一枚 bundle = {J["same_asset_name_on_both_entries_during_the_walk"]}。')
L.append('')
L.append(f'**要派单的三件（只交读数）**：')
L.append(f'· ① 回执号上了线、没上屏：那一腿 {dead_leg[0]} `{dead_leg[1]}` 答 {dead_leg[2]}、正文 {dead_leg[3]} B，'
         f'服务器字段 {Q}error.code={dead_leg[7]}{Q}、{Q}error_receipt_id={dead_leg[6]}{Q}；屏上（不开与开了折叠）'
         f'CNX 形式计数都是 0，`data-cnx-field`/`data-cnx-receipt` 锚点 0 枚，客户端自己那句 `NOT-EMITTED` 也没出现 = '
         f'{J["C_server_sent_a_receipt_that_the_screen_never_shows"]} / {J["C_no_receipt_anchor_is_rendered_at_all"]}。'
         f'折叠开以后是一行 telemetry（{fold["attribution_line_len_open"]} 字，哈希在件里，开头 '
         f'{Q}{fold["attribution_line_text_head_open"]}{Q}）。同一枚 bundle 里机件是有的（字段 '
         f'`machinery_exists_in_the_served_bundle`）。')
L.append(f'· ② 那枚号不是「每次故障一个」：同一路由连取三次 = 号 {rp["distinct_receipts"]} 枚、trace_id '
         f'{rp["distinct_trace_ids"]} 枚、正文哈希 {rp["distinct_body_hashes"]} 枚（字段 '
         f'{Q}receipt_is_per_incident_or_per_route{Q}）。它够不够当「旅客读回来就能定位这一次」的口径，我不判。')
L.append(f'· ③ 建得成但屏上还写「正在创建…」：两条 201（travelers / journeys，请求与响应字节在字段 '
         f'{Q}created_201_legs{Q}）、id 已落进 localStorage = {J["B_traveller_now_reaches_a_real_journey"]}，'
         f'九秒后仍写 {Q}正在创建…{Q} 与 {Q}已等待 9 秒{Q} = '
         f'{J["B_screen_still_says_creating_after_the_journey_exists"]}；这段文案本身是老实的（两句话原文在块里，'
         f'并给了「停止等待」）。')
L.append('')
L.append(f'**两件现场事实**：镜子在走路期间又超前 {DR["commits_ahead"]} 笔（主题含 ORD-0350 / ORD-0353，改动含向导本体那支源文件 = '
         f'{DR["touches_the_wizard_source"]}），我没有重建也没有再走第二遍；公网入口回头观测已经三次 '
         f'{TW["public_samples"][0]["status"]}（cf-ray 三枚不同），而本地那跳同一分钟 200、我走过那枚 bundle 仍按名字取得到同样字节 = '
         f'{J["the_bundle_i_walked_is_still_fetchable_by_its_recorded_name"]}。另外这台 shell 现在导出的 HTTP(S)_PROXY 指着'
         f'一个没人听的本地端口，我这条发布通道被它挡过一次（首批 39 件 0 落地，改为本进程不走代理后重投）—— '
         f'其它车道若用同一个 urlopen 取 GitHub 会撞同一件事（两轮发布日志都在件里，坐标见末段）。')
L.append('')
L.append(f'**旧事两件的现态**：死 id 那一屏不再说「网络不可用」而是说 {Q}这台服务器上没有这一趟行程了{Q} 并给两枚出口 '
         f'= {J["C_dead_id_screen_no_longer_claims_the_network_is_down"]} / '
         f'{J["C_dead_id_screen_offers_a_way_onward"]}，拒收后那枚 id 被清掉 = '
         f'{J["C_stored_id_is_cleared_after_the_rejection"]}；「已保存背后 0 行」这一格量到的是设备里 '
         f'{Q}citynexus-offline/journeys{Q} 行数 = {stores["rows_per_store"]["journeys"]}，而我走过两屏都没出现含'
         f'「已保存」的整句 = {J["E_no_saved_sentence_rendered_on_the_two_tabs"]}（那句话现在住在哪一屏我没找全，'
         f'不自称量过）；SW controller 在新上下文仍为 False = '
         f'{J["E_the_page_is_not_controlled_by_the_service_worker_yet"]}。')
L.append(f'**目的地块**：不开时屏上只有标签（城市名 0 枚在屏上）= {J["A_grouping_lives_only_behind_the_tap"]}；'
         f'刚点开 11 枚全写「还没问过服务器 / not-asked」；落定后分组 = 已支持 '
         f'{groups["已支持：服务器认得它，而且目录里有东西"]} / 需联网 {groups["需联网才能解析：服务器现在认不出这个名字"]} / '
         f'未知 {groups["未知或无数据：这一轮拿不出可规划的判定"]}，与屏上三个小标题一致 = '
         f'{J["A_settled_split_matches_the_visible_headings"]}；过渡态那一段的毫秒数与 11 条 capability 腿的字节都在件里。')
L.append('')
L.append(f'**ORD-0312 状态一句**：M3 与 M4 已交（代次绑定与同代重跑，件 '
         f'{Q}evidence/ord0312-target-generation-reread/ord0312_m3_binding_reread_gen2.json{Q} 等已在账上）；'
         f'唯一还在跑的是 M2 的 RED 向，它过去卡在具名前提「产品侧有没有可发的具名码路径」—— 今天这一尖上我量到该前提'
         f'成立（404 与 422 正文都带 {Q}error.code{Q} 与 {Q}message_key{Q}，例：{dead_leg[7]} / '
         f'{Q}resource.not_found{Q}）。要你一句话定口径：判别量用 {Q}error.code{Q} 还是 {Q}message_key{Q}，'
         f'定了我就开那一趟。')
L.append('')
L.append(f'坐标：评分件 `{PFX}/r6_readings_scored.json` {BLK(PFX + "/r6_readings_scored.json")}；走路 bundle 见证 '
         f'`{PFX}/r6_walked_asset_witness.json` {BLK(PFX + "/r6_walked_asset_witness.json")}；两入口绑定 '
         f'`{PFX}/r6_gen_check.json` {BLK(PFX + "/r6_gen_check.json")}；目的地块 `{PFX}/r6_dest_block_r3.json` '
         f'{BLK(PFX + "/r6_dest_block_r3.json")}（被取代的那读 `{PFX}/r6_dest_block_r2.json` '
         f'{BLK(PFX + "/r6_dest_block_r2.json")}）；向导格 `{PFX}/r6_wizard_create.json` '
         f'{BLK(PFX + "/r6_wizard_create.json")}；死 id 格 `{PFX}/r6_dead_id_saved.json` '
         f'{BLK(PFX + "/r6_dead_id_saved.json")}；锚点与设备存储 `{PFX}/r6_receipt_anchor_offline.json` '
         f'{BLK(PFX + "/r6_receipt_anchor_offline.json")}；漂移 `{PFX}/r6_drift.json` {BLK(PFX + "/r6_drift.json")}；'
         f'入口观测 `{PFX}/r6_tunnel_watch.json` {BLK(PFX + "/r6_tunnel_watch.json")}；关键像素 '
         f'`{PFX}/shots/C1_dead_id_closed.png` {BLK(PFX + "/shots/C1_dead_id_closed.png")} 与 '
         f'`{PFX}/shots/C2_dead_id_open.png` {BLK(PFX + "/shots/C2_dead_id_open.png")}（两次独立起车像素同一）、'
         f'`{PFX}/shots/B2_after_confirm.png` {BLK(PFX + "/shots/B2_after_confirm.png")}；本块 Q43 r4d 回执 '
         f'`{PFX}/ledger_inbox_proof_r6_q43r4d.json` {BLK(PFX + "/ledger_inbox_proof_r6_q43r4d.json")}；坐标预飞 '
         f'`{PFX}/hex_preflight_r6.json` {BLK(PFX + "/hex_preflight_r6.json")}；写入计数（每枚名字一笔提交）'
         f'`{PFX}/write_ledger_r6.json` {BLK(PFX + "/write_ledger_r6.json")}；两轮发布日志 '
         f'`{PFX}/ship_result_r6.json` {BLK(PFX + "/ship_result_r6.json")} 与 `{PFX}/ship_result_r6b.json` '
         f'{BLK(PFX + "/ship_result_r6b.json")}。块 '
         f'{pathlib.Path(json.loads((OUT / "ledger_inbox_proof_r6.json").read_text(encoding="utf-8"))["block_file"]).name}，'
         f'门内 claims/findings 数在那枚回执里。')
L.append('')
L.append(CLOSING.decode('utf-8'))
body = '\n'.join(L) + '\n'
(OUT / 'r6_bus_note.md').write_text(body, encoding='utf-8', newline='\n')
if '--dry' in sys.argv:
    print(body)
    raise SystemExit(0)
if NAME_CACHE.exists():
    cid = int(NAME_CACHE.read_text(encoding='utf-8').strip())
    print('already posted, id', cid)
else:
    cid = gh('/repos/Canshu-King/CityNexus-Workspace/issues/1/comments', {'body': body})['id']
    NAME_CACHE.write_text(str(cid) + '\n', encoding='utf-8', newline='\n')
    print('posted id', cid)
time.sleep(2)
back = gh('/repos/Canshu-King/CityNexus-Workspace/issues/comments/%d' % cid)
tail = [x for x in back['body'].rstrip().splitlines() if x.strip()][-1]
rec = {'comment_id': cid, 'permalink': back['html_url'], 'created_at': back['created_at'],
       'body_bytes': len(back['body'].encode('utf-8')), 'remote_equals_local': back['body'] == body,
       'tail_bytes': len(tail.encode('utf-8')), 'tail_equals_fetched_closing_line': tail.encode('utf-8') == CLOSING,
       'generation': DR['named_by_the_commander'], 'branch_tip': tip, 'read_at': time.strftime('%H:%M:%S')}
(OUT / 'r6_bus_note_readback.json').write_text(json.dumps(rec, ensure_ascii=False, indent=1),
                                               encoding='utf-8', newline='\n')
print(json.dumps({k: rec[k] for k in ('comment_id', 'permalink', 'remote_equals_local',
                                      'tail_equals_fetched_closing_line')}, ensure_ascii=False))
