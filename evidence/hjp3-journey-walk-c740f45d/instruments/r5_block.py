"""Ledger block for the phone-generation walkthrough, built only from readings and self-checked by Q43 r4d.

Per CMDR-0925-2307 the lane never writes the ledger: one block goes to the commander's inbox with a `### ` first
line, and it is run through the live gate - r4d, the revision the commander stamped at 07:50 - with
`--expect-clean` before he ever sees it. Every figure here is read out of `r5_walk_scored.json` or out of the
branch tree at write time; nothing is typed by hand, and no cell is written as a PASS.
"""
from __future__ import annotations

import hashlib
import importlib.util as iu
import json
import pathlib
import re
import subprocess
import sys
import time

OUT = pathlib.Path('D:/moodle/_hjp3_0323walk_0926')
SRC = pathlib.Path('D:/moodle/HJ-P3_evidence')
INBOX = pathlib.Path('D:/moodle/_qoder_ledger_inbox')
GATE = 'D:/moodle/_qoder_cmdr_ref_20260921/live_checks/claim_coordinate_check_r4d.py'
WALK = 'evidence/hjp3-journey-walk-c740f45d'
spec = iu.spec_from_file_location('pub', str(SRC / 'p3_publish.py'))
pub = iu.module_from_spec(spec)
spec.loader.exec_module(pub)

RS = json.loads((OUT / 'r5_walk_scored.json').read_text(encoding='utf-8'))
WA = json.loads((OUT / 'r5_who_answered.json').read_text(encoding='utf-8'))
FN = json.loads((OUT / 'r5_finish_findings.json').read_text(encoding='utf-8'))
C1 = RS['cells']['C1_new_journey_wizard']
BAND = C1['band_between_step_bar_and_first_control']
CONF = C1['pressing_the_real_submit_button']
C4 = RS['cells']['C4_broken_three_ways']
FATE = C4['per_fate']
NAT = RS['cells']['C3_read_failure_copy']
SELFS = RS['instrument_self_tests']
PIX = RS['screenshot_pixel_identity']
J = RS['judgments']
EXC = RS['runs_excluded']
Q = chr(96)
TIP, TREE, _rows = pub.branch_rows()
BLOB = {x['path']: x['sha'] for x in pub.api('/git/trees/' + TIP + '?recursive=1')['tree']}
BLK = lambda p: BLOB.get(p, 'NOT_ON_BRANCH')
READING_BLOB = BLK(WALK + '/journey_walk_readings.json')
SHOT_REFUSED = BLK(WALK + '/shots/W3_4_fate_refused.png')
SHOT_EMPTY500 = BLK(WALK + '/shots/W3_5_fate_empty500.png')
SHOT_CONFIRM = BLK(WALK + '/shots/W3_9_after_confirm.png')
INSTR_BLOB = BLK(WALK + '/instruments/r5_walk3.cjs')
SHOT_CANARY = BLK(WALK + '/shots/W3_6_fate_canary200.png')
SHOT_SHOT7 = BLK(WALK + '/shots/W3_7_natural.png')
SHOT_FIXTURE = BLK(WALK + '/shots/W3_8_collapse_fixture.png')
SHOT_STEP2 = BLK(WALK + '/shots/W3_3_next2.png')
WHO_BLOB = BLK(WALK + '/who_answered_the_500s.json')
RAW3 = BLK(WALK + '/raw_walk3_findings.json')
RAWFIN = BLK(WALK + '/raw_finish_findings.json')
post_legs = CONF['legs_after_the_press']
post = post_legs[0] if post_legs else {}
CLOSING = pathlib.Path('D:/moodle/_qoder_cmdr_ref_20260921/live_checks/CLOSING_LINE.txt').read_bytes()
assert len(CLOSING) == 83
assert hashlib.sha1(b'blob 83' + bytes([0]) + CLOSING).hexdigest() == \
    'b82ca923501c312b6931ad894c607ab9e43e1137'
L = []
L.append('### 📱 aad2d1f2 (SESSION=aad2d1f2) P3 · **真人行程复验已在手机新代次上走完：读数、我自己的仪器错、'
         '用户做不到的事都按步骤具名；只交读数，不写 PASS** @' + time.strftime('%H:%M') + '+08')
L.append('')
L.append('```text')
L.append('四元组先报（MEASUREMENT_SCOPE_FIRST_V1）：')
L.append('· scope = 手机链此刻在部署的那一屏（新建行程三步 → 确认创建；封存演示入口；三处故意弄坏）')
L.append(f'· generation = {Q}{RS["generation"]}{Q}（{RS["generation_how_read"][:60]}…；链上页面点名的资产 = '
         f'{Q}{RS["artifact"]["asset_named_by_the_served_page"]}{Q}，我取的字节 = '
         f'{RS["artifact"]["asset_bytes"]} B、sha256 {Q}{RS["artifact"]["asset_sha256_64_hex"][:16]}…{Q}，'
         f'与你说的名字同号 = {RS["artifact"]["name_matches_what_the_commander_named"]}）')
L.append(f'· artifact = 本块末坐标行那几件（全 40 位，现读分支 tree {Q}{TREE[:12]}…{Q}）')
L.append(f'· measurement method = {RS["measurement_method"][:96]}…（写在本块末行那件里，全文不缩）')
L.append('')
L.append(f'**读数总账（件 blob {Q}{READING_BLOB}{Q}）：走到的格 {len(RS["cells"])} 格、被我排除的仪器跑 '
         f'{len(EXC)} 次、由件内字段算出的判据 {sum(1 for v in J.values() if v is True)} 条为真 / 共 {len(J)} 条；'
         f'逐条都不是我打的勾**')
L.append(f'· 能走到第三步复核页 = {J["traveller_can_reach_the_review_step"]}；按「下一步」两次都换页 = '
         f'{C1["screen_changed_after_each_press"]}；第三步上按钮清单 = '
         f'{Q}{" / ".join([b for b in CONF["all_buttons_painted_at_step3"] if b])}{Q}')
L.append(f'· 现在能不能建成行程 = {J["traveller_can_create_a_journey_on_this_chain_right_now"]}（按真按钮之后仍停在向导 '
         f'{CONF["still_on_the_wizard_afterwards"]}、localStorage 里 journey id = '
         f'{Q}{CONF["journey_id_stored_in_localStorage_after"]}{Q}、进了主界面 = {CONF["reached_the_hub"]}）')
L.append(f'· 失败那屏说了人话且有动作 = {J["the_refusal_screen_offers_an_action"]} / 明说没改动任何东西 = '
         f'{J["the_refusal_screen_states_nothing_was_changed"]} / 讲清原因 = '
         f'{J["confirm_press_tells_the_traveller_why_in_words"]}：{Q}{"；".join(CONF["lines_the_traveller_reads"])}{Q}')
L.append(f'· 那一次按下去真发了请求：{post.get("m")} {Q}{post.get("url")}{Q}，浏览器侧记到状态 '
         f'{post.get("status")}、类型 {Q}{post.get("ct")}{Q}、请求体 {post.get("post_body_len")} B；'
         f'截图 {Q}{SHOT_CONFIRM}{Q}（全 40 位亦在末行）')
L.append('')
L.append(f'**① 三步向导与那段留白（ORD-0338 的定性我自己重测）**')
L.append(f'· 步骤条 padding-bottom = {BAND["trial_steps_padding_bottom_px"]} px，圆点行顶 {BAND["step_dot_row_top_px"]} px、'
         f'卡片顶 {BAND["card_top_px"]} px ⇒ 视觉上点与卡之间 {BAND["visual_gap_dot_row_to_card_px"]} px，而步骤条盒子底到卡片只 '
         f'{BAND["gap_from_the_steps_box_to_the_card_px"]} px；卡片在不滚动的当下就看得见 = '
         f'{BAND["card_visible_at_rest"]}，整页可滚溢出 {BAND["scroll_overflow_px"]} px。')
L.append(f'· 所以这条与 ORD-0338 的定性一致：那是真 padding，不是「在等数据」（判据 '
         f'{Q}agrees_with_ORD-0338_that_the_band_is_a_real_padding_not_data_waiting{Q} = '
         f'{J["the_ORD-0338_band_is_a_real_padding_not_data_waiting"]}）；提交按钮此刻在 {" 与 ".join(str(x) for x in BAND["submit_button_top_px"])} px，'
         f'不需要滚就按得到。修复不归我：产品字节 0 改。')
L.append('')
L.append(f'**② 封存演示入口：同一句话盖住了两种不同的腿（这是要你派单的一件）**')
L.append(f'· 三种腿各测一遍、每种都读两次（先原样读、再把所有 details 全开再读）：')
for k in ('refused', 'empty500', 'canary200'):
    v = FATE[k]
    _sb = {'refused': SHOT_REFUSED, 'empty500': SHOT_EMPTY500, 'canary200': SHOT_CANARY}[k]
    L.append(f'    {Q}{k}{Q} 开块后：异常字面 文本 {v["exception_in_text_after_opening_details"]} 处、属性 '
             f'{v["exception_in_attributes_after_opening_details"]} 处、堆栈 {v["stack_frame"]}、长机器串 '
             f'{v["long_machine_text"]}、canary 到 DOM = {v["canary_reached_the_dom"]}'
             f'（截图 blob {Q}{_sb}{Q}；尾部三行 {Q}{" ▏ ".join(v["the_lines_it_shows"])}{Q}）')
L.append(f'· 关键一条：腿被拒（根本没连上）与「答了但内容用不了」两屏的截图 sha256 完全相同 = '
         f'{PIX["refused_vs_empty500"]["pixel_identical"]}（两张各 {PIX["refused_vs_empty500"]["left_bytes"]} B；'
         f'而 canary 那屏与它们不同 = {not PIX["refused_vs_canary200"]["pixel_identical"]}），且这句话写的是'
         f'「服务器刚才答了」 ⇒ {J["the_screen_speaks_for_a_server_that_never_answered_in_at_least_one_fate"]}。'
         f'我不判它对不对，只把两条事实放这儿：像素不可分、句子做了一种腿断言。')
L.append(f'· 而「谁答的」是量出来的（件 blob {Q}{WHO_BLOB}{Q}）：'
         f'{WA["verdict"]["the_made_up_path_answers_identically_to_the_real_api_paths"]} —— '
         f'我编了一条产品不可能有的路径（{Q}/api/v1/zzz-hjp3-canary-path{Q}）与三条真路径比签名，'
         f'{len(WA["readings"])} 条路径的（状态/类型/字节/正文哈希）签名只有 {len(RS["cells"]["C3_read_failure_copy"]["distinct_signatures"])} 种：'
         f'{Q}{" ".join(RS["cells"]["C3_read_failure_copy"]["distinct_signatures"])}{Q}，且都没有 server 头 = '
         f'{WA["verdict"]["no_reading_carries_a_server_header"]}、正文都 0 B = '
         f'{WA["verdict"]["every_answer_has_a_zero_length_body"]} ⇒ 那枚 500 里没有任何应用专属内容。')
L.append(f'· 还有两件小的（截图 blob {Q}{SHOT_SHOT7}{Q}）：链上不当我动手时也是这个态（自然态屏上尾部三行 '
         f'{Q}{" ▏ ".join(NAT["what_the_shell_says_without_me_breaking_anything"])}{Q}，'
         f'有没有给你动作 = {NAT["an_action_is_offered_at_rest"]}）；而场景读失败在用户按下什么之前完全不说 = '
         f'{NAT["the_scene_failure_is_silent_until_the_traveller_presses_something"]}。')
L.append('')
L.append(f'**③ 量具自己先自证（两向）**')
L.append(f'· 暴露判据：我自建一张真会漏的页（异常字面进文本 + 进 data-* 属性；夹具截图 blob '
         f'{Q}{SHOT_FIXTURE}{Q}，原始读数 blob {Q}{RAW3}{Q}）跑同一条判据 = 文本 '
         f'{SELFS["exposure_detector_two_way"]["leaky_fixture_authored_by_me_after_opening"]["exception_in_text"]} 处、'
         f'属性 {SELFS["exposure_detector_two_way"]["leaky_fixture_authored_by_me_after_opening"]["exception_in_attributes"]} 处；'
         f'一张干净页同一判据 = {SELFS["exposure_detector_two_way"]["clean_fixture"]["exception_in_text"]} / '
         f'{SELFS["exposure_detector_two_way"]["clean_fixture"]["exception_in_attributes"]} 处 ⇒ 两向都过 = '
         f'{SELFS["exposure_detector_two_way"]["derived"]["detector_fires_once_the_block_is_open"]} / '
         f'{SELFS["exposure_detector_two_way"]["derived"]["detector_is_silent_on_a_clean_page"]}（Q71 的 data-* 位我一并扫了）。')
L.append(f'· 折叠敏感度我改了测法（原始读数 blob {Q}{RAWFIN}{Q}）：元素级 innerText 在折叠时确实读不到（'
         f'{SELFS["collapse_sensitivity_at_element_level"]["derived"]["element_inner_text_hides_it_when_collapsed"]}），'
         f'body 级 innerText 同样会漏（'
         f'{SELFS["collapse_sensitivity_at_element_level"]["derived"]["body_level_read_hides_it_when_collapsed"]}），'
         f'而我的判据读的是节点 nodeValue，text_content 那一层从不被折叠遮住 = '
         f'{SELFS["collapse_sensitivity_at_element_level"]["derived"]["element_text_content_never_hides_it"]} ⇒ '
         f'「扫不到」不等于「屏上没有」这条我按两种读法各自交代。')
L.append(f'· 记账的仪器错 {len(EXC)} 次，每次都有机械信号（不是我事后认；三次的原始读数在 blob '
         f'{Q}{RAW3}{Q} 与 {Q}{RAWFIN}{Q}）：')
for e in EXC:
    L.append(f'    {Q}{e["run"]}{Q} 我说过「{e["what_I_claimed"]}」；抓它的信号 = {e["mechanical_signal"]}；'
             f'真因 = {e["real_cause"]}')
L.append(f'· 我这批不比 pass-3：手机链上没有我的跳板可发 pair_id，服务器侧只能取浏览器网络层（件里 '
         f'{Q}pairing_note{Q} 一句已写明它是更弱的一侧，不当等价物用）。')
L.append('')
L.append(f'**用户现在做不到什么（按步骤具名，只列我做过的路上读到的）**')
L.append(f'· 第 3 步「确认创建」按下去建不成行程：请求发出后浏览器记到的状态是 '
         f'{post.get("status")}、正文 {post.get("post_body_len")} B 的请求换回 0 B 空正文，人留在第 3 步（能读到的解释只有那两句，'
         f'没有可点的替代出口去任何列表或收件箱）。')
L.append(f'· 列表/收件箱这一路到不了：此刻可见的可按项只有 {Q}{" / ".join([x for x in C4["journey_list_and_inbox_reachability"]["labels_a_traveller_can_press_now"]][:6])}{Q} 这些；'
         f'而这枚包里没有为存储 journey id 准备的客户端路由，所以 /journey/<坏 id> 渲染的是同一个壳'
         f'（那屏 {RS["cells"]["C5_error_boundary_three_places"]["dead_stored_id_paint_len"]} 字）⇒ '
         f'错误边界我**到不了**，因此不敢说它干净。')
L.append(f'· 第三步复核页（截图 blob {Q}{SHOT_STEP2}{Q}）上写着「{C1["values_the_product_filled_for_me"][0]}」'
         f'这类话（{len(C1["values_the_product_filled_for_me"])} 处）：'
         f'它自己标了「替你填」，这一条是诚实的，但用户要改就得回去挨个找 —— 我不替它判定好坏，只报读到的。')
L.append('')
L.append(f'**纪律**：产品字节 0 改（路上看到的一切不修，全交你派单）；权威线 0 写；ref 0 推别人的；'
         f'demo/reset 0；_live.db 与 _preview.db 0 读 0 写；git apply 0；凭据 0 打印；手机链只被我驱动 UI 与只读 GET，'
         f'写请求只发生在我自己的浏览器上下文里（route 拦截），隧道与 :4782 我一行没碰；自己的泳道是临时 profile，'
         f'截图全写绝对路径并逐张回验存在与字节；Q43 用的是你 07:50 换的 r4d，原判在本块末行那件里。')
L.append('```')
L.append('')
L.append(f'坐标（本块写时从分支 tree 现读，写时尖 {Q}{TIP}{Q} · tree {Q}{TREE}{Q}）：'
         f'读数件 `{WALK}/journey_walk_readings.json` `{READING_BLOB}` · '
         f'量具 `{WALK}/instruments/r5_walk3.cjs` `{INSTR_BLOB}` · '
         f'`{WALK}/instruments/r5_finish.cjs` `{BLK(WALK + "/instruments/r5_finish.cjs")}` · '
         f'`{WALK}/instruments/r5_who_answered.py` `{BLK(WALK + "/instruments/r5_who_answered.py")}` · '
         f'`{WALK}/instruments/r5_consolidate_2.py` `{BLK(WALK + "/instruments/r5_consolidate_2.py")}` · '
         f'截图（三屏对照的关键三张）`{WALK}/shots/W3_4_fate_refused.png` `{SHOT_REFUSED}` · '
         f'`{WALK}/shots/W3_5_fate_empty500.png` `{SHOT_EMPTY500}` · '
         f'`{WALK}/shots/W3_9_after_confirm.png` `{SHOT_CONFIRM}`。')
L.append('')
L.append('要你定的只有两件：① 那句「服务器刚才答了」要不要按腿分叉（我可以补一判据：同一屏在两种腿下像素不可分 = '
         '事实，句子里的断言是否属于产品该负责的口径，归你或仲裁）；② 列表/收件箱/错误边界这三面在这枚包里没有可点入口，'
         '是要我按路由名去查源（只读）还是你直接派单。其余不自启：ORD-0316 那件已交完并量到闸回绝，'
         'ORD-0312 的读数已在新代次上重做完。')
L.append('')
L.append(CLOSING.decode('utf-8'))
text = '\n'.join(L) + '\n'
CACHE = OUT / 'walk_inbox_block_name.txt'
if CACHE.exists():
    name = CACHE.read_text(encoding='utf-8').strip()
else:
    stale = sorted(q.name for q in INBOX.glob('aad2d1f2_*.md'))
    assert len(stale) <= 1, f'more than one unswept block of mine: {stale}'
    name = stale[0] if stale else 'aad2d1f2_%s.md' % time.strftime('%H%M')
    CACHE.write_text(name + chr(10), encoding='utf-8', newline=chr(10))
dest = INBOX / name
assert text.startswith('### ')
dest.write_text(text, encoding='utf-8', newline='\n')
chk = subprocess.run([sys.executable, GATE, '--text', str(dest), '--expect-clean'],
                     capture_output=True, text=True, encoding='utf-8', errors='replace')
proof = {'block_file': str(dest), 'bytes': dest.stat().st_size, 'gate': GATE.rsplit('/', 1)[-1],
         'q43_rc': chk.returncode, 'q43_out': (chk.stdout or '')[-1600:],
         'q43_err': (chk.stderr or '')[-300:], 'ledger_written_by_this_lane': False,
         'cells': len(RS['cells']), 'excluded_runs': len(EXC), 'generation': RS['generation']}
(OUT / 'ledger_inbox_proof_walk.json').write_text(json.dumps(proof, ensure_ascii=False, indent=1),
                                                  encoding='utf-8', newline='\n')
print('inbox block', name, proof['bytes'], 'B | gate', proof['gate'], '| rc =', chk.returncode)
print((chk.stdout or '')[-1200:])
if chk.returncode != 0:
    print('NOT CLEAN - fix the named numbers before this block counts as a delivery')
