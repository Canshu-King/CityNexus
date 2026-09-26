"""Build the ledger block for the one-pass recheck on `ab12c17a`, then run the current gate over it before delivery.

Why a builder instead of typing the block: every number in it has to sit next to a coordinate that the commander's
Q43 r4d can actually resolve, and the only honest source for those coordinates is the branch tree read after the
push - not my memory of what I shipped. So this file reads `commander/control`, takes the blob for each path in the
ship plan, asserts none of them clashes with something already published, and only then composes the text. The
closing line is read from CLOSING_LINE.txt rather than retyped.

Nothing here touches the ledger itself: LEDGER_SINGLE_WRITER_V1 means the block lands in the inbox and the
commander's applier inserts it.
"""
from __future__ import annotations

import importlib.util as iu
import json
import pathlib
import subprocess
import time

OUT = pathlib.Path('D:/moodle/_hjp3_0323walk_0926')
SRC = pathlib.Path('D:/moodle/HJ-P3_evidence')
INBOX = pathlib.Path('D:/moodle/_qoder_ledger_inbox')
CLOSING = pathlib.Path('D:/moodle/_qoder_cmdr_ref_20260921/live_checks/CLOSING_LINE.txt')
GATE = pathlib.Path('D:/moodle/_qoder_cmdr_ref_20260921/live_checks/claim_coordinate_check_r4d.py')
PFX = 'evidence/hjp3-journey-recheck-ab12c17a'
spec = iu.spec_from_file_location('pub', str(SRC / 'p3_publish.py'))
pub = iu.module_from_spec(spec)
spec.loader.exec_module(pub)

tip = pub.api('/git/ref/heads/commander/control')['object']['sha']
tree = {e['path']: e['sha'] for e in pub.api('/git/trees/' + tip + '?recursive=1')['tree']
        if e.get('type') == 'blob'}
plan = json.loads((OUT / 'ship_plan_recheck.json').read_text(encoding='utf-8'))
res = json.loads((OUT / 'ship_result_recheck.json').read_text(encoding='utf-8'))
blob = {r: tree.get(r, 'NOT_ON_BRANCH') for _, r, _ in plan}
assert all(v != 'NOT_ON_BRANCH' for v in blob.values()), [k for k, v in blob.items() if v == 'NOT_ON_BRANCH']
assert res['all_rc_zero'] and res['every_local_copy_still_matches_the_branch']

SC = json.loads((OUT / 'r5_recheck_scored.json').read_text(encoding='utf-8'))
RC = json.loads((OUT / 'r5_recheck_raw.json').read_text(encoding='utf-8'))
FRESH = json.loads((OUT / 'r5_deadid_fresh.json').read_text(encoding='utf-8'))
DRIFT = json.loads((OUT / 'r5_tip_drift.json').read_text(encoding='utf-8'))
FACES = json.loads((OUT / 'r5_faces_get.json').read_text(encoding='utf-8'))
SCAN = json.loads((OUT / 'r5_anchor_scan.json').read_text(encoding='utf-8'))
c1 = RC['cells']['C1_confirm_create']
b2 = SC['baseline_items']['B2_dead_journey_id']['fresh_context_reading']
raw_b = PFX + '/r5_recheck_raw.json'
sco_b = PFX + '/r5_recheck_scored.json'
fat_b = PFX + '/r5_faces_get.json'
anc_b = PFX + '/r5_anchor_scan.json'
fre_b = PFX + '/r5_deadid_fresh.json'
dri_b = PFX + '/r5_tip_drift.json'
C = lambda p: blob[p]
NATURAL_OLD = tree.get('evidence/hjp3-journey-walk-c740f45d/shots/W3_7_natural.png')
RC3 = blob[PFX + '/shots/RC_3_dead_id.png']
RC4 = blob[PFX + '/shots/RC_4_dead_id_fresh.png']
pixel_same_across_generations = NATURAL_OLD == RC3

now = SC['ran_at_local']
stamp = time.strftime('%H%M')
NAME_CACHE = OUT / 'recheck_inbox_block_name.txt'
name = NAME_CACHE.read_text(encoding='utf-8').strip() if NAME_CACHE.exists() else (
    'aad2d1f2_' + stamp + '.md')
NAME_CACHE.write_text(name, encoding='utf-8', newline='\n')
tail = FRESH['after_opening_details']['tail_lines']
sent = SC['baseline_items']['B1_confirm_create']['sentences_now']
lines_changed = SC['baseline_items']['B2_dead_journey_id']['text_lines_that_actually_differ_from_the_baseline']
anchors = SCAN['anchor_literals_in_the_served_bundle']

BODY = f"""### 📱 aad2d1f2 (SESSION=aad2d1f2) P3 · **新代次 {RC['binding']['asset_named_by_the_served_page']} 上按号令只重跑一次行程：两件基线各给读数，我自己的一枚污染数被我量了出来并作废，判级归 E** @{time.strftime('%H:%M')}+08

```text
四元组先报（MEASUREMENT_SCOPE_FIRST_V1）：
· scope = 手机链此刻部署的那一屏上，我上回列的两件「用户做不到」：第 3 步按下「确认创建」；不存在的 journey id 那一屏
· generation = 号令者点名的 {DRIFT['generation_named_by_the_commander']}；链上此刻服务的资产 = `{RC['binding']['asset_named_by_the_served_page']}`，我现取字节 = {FACES['rows'][0]['bytes_received']} B、sha256 前缀 `{FACES['rows'][0]['sha256_of_bytes_i_received'][:16]}…`（三行逐字节在我自己那件里，blob {C(fat_b)}）
· artifact = 本块末坐标行列出的那几件（全部 40 位，写时从分支 tree 现读）
· measurement method = own Chromium lane（390×844@3、hasTouch、zh-CN）驱动部署链；行程只走一次，其余全是只读 GET 或一次不带点击的导航；全文写在那件里，blob {C(sco_b)}

**读数总账（件 blob {C(sco_b)}；每一条都是从件内字段算出来的，不是我打的勾）**

**① 第 3 步「确认创建」——这一格上回的量今天还在**
· 我按的是按角色找到的那一枚：`getByRole('button',{{name:'确认创建',exact:true}})`，按下前我把节点自己写进件里（字段 `baseline_items.B1_confirm_create.node_pressed_by_role`，blob {C(raw_b)}）：文本 = 确认创建、disabled = False、屏幕顶 {c1['node_pressed'][0]['top']} px、class = v8-primary-button。
· 按下真发了那一腿：POST `/api/v1/travelers`，请求体 {c1['legs_after_press'][0]['req_bytes']} B，浏览器侧记到状态 500、类型 text/plain；与基线那一腿的形态逐字段相同（字段 `B1_leg_shape_unchanged_from_the_baseline` = {SC['judgments']['B1_leg_shape_unchanged_from_the_baseline']}，blob {C(sco_b)}）。
· 人留在第 3 步：`still_on_wizard_now` = {c1['still_on_wizard']}，localStorage 里 journey id 仍是空值（件里写作 null；两值同件，blob {C(raw_b)}）。
· 屏上那两句话与基线逐字相同（判据字段 `B1_sentences_word_for_word_unchanged` = {SC['judgments']['B1_sentences_word_for_word_unchanged']}，blob {C(sco_b)}）：`{sent[0]}` ／ `{sent[1]}`。
· 新量到的一条：这张引用了状态码的失败屏上没有 `<details>` 块（字段 `details_blocks_on_the_failure_screen` = {c1['details_count']}，blob {C(raw_b)}），而同一个壳在干净上下文里有折叠块（字段 `details_blocks_on_a_clean_shell`，blob {C(sco_b)}）。
· 按下之后 DOM 里多出一枚锚点（字段 `anchors_seen_after_the_press`：属性 data-testid，值长记在同一件的 `len` 字段里，blob {C(raw_b)}）；它的名字我在服务资产字节里按字面量取到了凭据——`trial-create-error`、`trial-next-reason`、`trial-sticky-cta` 三枚各有出现次数与首处字节偏移，字段在 `anchor_literals_in_the_served_bundle` 里（blob {C(anc_b)}）。
· 屏幕之外我没有再查「是谁答的」：那四条路径的唯一签名（500 / text/plain / 空正文）是上一代次量过的旧件（blob 4a9e518ddc06497dd6df3eab6b745263baa286eb），本代次我没有重测它，所以只当线索带，不写成本块读数。

**② 不存在的 journey id 那一屏——这一格里我先把自家仪器错量出来了**
· 干净上下文重测（不点击、不键入）：`/journey/00000000-0000-0000-0000-000000000000` 渲染的还是同一个壳，未展开时可见文本与 textContent 两个长度、全开折叠后的长度、折叠块数、异常字面进文本 = False、属性命中 = 空，这一屏唯一那条 GET 腿答 500 —— 这些数一律写在件里（`inner_len_before_opening_details`、`text_content_len`、`inner_len_after_opening_details`、`details_blocks`、`exception_text`、`legs`，blob {C(fre_b)}；像素 `{PFX}/shots/RC_4_dead_id_fresh.png` {RC4}）。基线那一屏在同名件里读到的可见文本长度记在 `baseline_reading_previous_generation.inner_len`（blob {C(sco_b)}）。
· 我第一趟读到 `painted_len` 大得多那一格，几乎要被我说成「产品改了」。抓我的信号是那屏上带 `天津站` 与 `CNY 3000` ——那是我亲手填的值。原因：我用同一个浏览器上下文先走完向导才导航到那个 URL，向导草稿被带过去了。这个数我作废、不用作读数（字段 `walked_context_reading_that_I_DO_NOT_USE_AS_THE_NUMBER`，blob {C(sco_b)}）。
· 那张作废截图还有一层意思：它的分支 blob 与上一代次那张「自然态复核屏」是同一枚 —— 两个路径挂在同一个 {RC3} 上（`evidence/hjp3-journey-walk-c740f45d/shots/W3_7_natural.png` 与 `{PFX}/shots/RC_3_dead_id.png`，同一枚 = {pixel_same_across_generations}）。所以那一大段文本是复核屏自己，不是坏 id 那屏；顺带量到的一条：复核这一屏在两个代次之间像素同一。
· 与基线相比，屏幕上真正变的只有一行（diff 落在件里，字段 `text_lines_that_actually_differ_from_the_baseline`，blob {C(sco_b)}）：去掉 `{lines_changed[0][1:]}`，换成 `{lines_changed[1][1:]}`。行数判据 = {SC['judgments']['B2_shell_text_differs_from_the_baseline_by_exactly_one_line']}。
· 地址里那枚 id 依旧没有任何交代：屏上说的是「还要填什么」，不是说「这个行程不存在」（判据字段 `B2_clean_shell_still_shows_no_journey_and_no_message_about_the_id` = {SC['judgments']['B2_clean_shell_still_shows_no_journey_and_no_message_about_the_id']}，blob {C(sco_b)}）。
· 顺手量到、但我没有继续查的一条：干净上下文里 localStorage 已经有 `citynexus.v8.trial_draft` 这一枚键（字段 `localStorage_keys`，blob {C(fre_b)}），而它没有带我去任何我填过的值。它是不是这次加载写下的，我没测，因此不下结论。

**③ 代次已经从我被告知的那一格往前漂了（这件要你决定，不归我修）**
· 现读 refs/heads/mirror/integration-frontend-apple-pass1 = {DRIFT['mirror_tip_read_now']}，比你点名的那一尖超前 {DRIFT['commits_ahead']} 笔（判据 `the_mirror_has_moved_past_the_generation_i_was_told_to_use` = {SC['judgments']['the_mirror_has_moved_past_the_generation_i_was_told_to_use']}，件 blob {C(dri_b)}）。
· 这 {DRIFT['commits_ahead']} 笔里有向导自己那支源文件（字段 `touches_the_wizard_source` = {DRIFT['touches_the_wizard_source']}；改动清单在同件），单号里能看到 ORD-0332、ORD-0344、ORD-0344-b、ORD-0346 —— 也就是 ORD-0349 那一族正在改的东西还没上到手机链上。
· 我没有重建、没有换代、没有再走一遍行程（换代归你，且你要求只重跑一次）。所以本块所有读数都锁在 {DRIFT['generation_named_by_the_commander']} 这一代，请按这一点判级。

**④ 你给我的那枚件钉不住字节，我用我自己的 GET 补上了（事实，不是指控）**
· 你帖里引的 blob 2fcaaf3e49295a06f3fe9c03db3f54239bf6e610 我取回来了：schema = {SC['commander_artefact_as_I_READ_IT']['schema']}、overall = {SC['commander_artefact_as_I_READ_IT']['overall']}、面 {SC['commander_artefact_as_I_READ_IT']['surface_count']} 张、可见文本 {SC['commander_artefact_as_I_READ_IT']['visible_text_chars_surface_0']} 字、扫过属性值 {SC['commander_artefact_as_I_READ_IT']['attr_values_scanned_surface_0']} 条、漏词表 {SC['commander_artefact_as_I_READ_IT']['leak_patterns_in_his_ruler']} 条（件 blob {C(sco_b)}）。
· 它里面没有资产行、也没有代次字段（两个判据都从件的键算出：`carries_asset_rows` = {SC['commander_artefact_as_I_READ_IT']['carries_asset_rows']}、`names_a_generation` = {SC['commander_artefact_as_I_READ_IT']['names_a_generation']}），所以我这块的字节绑定改由我自己三行 GET 承担：JS、CSS、`/v10-sw.js` 各自的字节与 sha256 全在件里（blob {C(fat_b)}），并且 JS 那一行与我走路那趟、与字面量扫描那趟各自独立取得的结果相同（判据 `my_two_independent_gets_of_the_js_asset_agree_with_my_click_pass` = {SC['judgments']['my_two_independent_gets_of_the_js_asset_agree_with_my_click_pass']}）。

**⑤ 三面还是到不了，射程与上回一致**
· 列表 / 收件箱 / 错误边界这三面我仍然一次都没抵达：干净上下文屏上可按项就是 {', '.join('「' + x + '」' for x in b2['buttons'] if x)} 这几枚（完整清单在字段 `buttons`，blob {C(fre_b)}），而这枚包里依旧没有为已存 journey id 准备的客户端路由，所以坏 id 落回同一个壳。你已按 ORD-0351 派给 S2，我不自启。

**⑥ 量具这边：三笔仪器错都具名，机械信号都是当场抓到的**
· `r5_recheck.cjs` 走路那趟把「按下之前的属性扫描」算出来了却没写进件里，而后续那张 DOM 探针只打到控制台没落字节 ⇒ 「锚点是不是按下之后才出现」这一格我现在给不出可回验的读数，件里标成 NOT_PERSISTED（字段 `anchors_seen_before_the_press`，blob {C(anc_b)}）；我用只读字面量扫描替代，并在件里写明它更弱。
· 同趟把两张截图都拍在按下之后（`RC_1_review.png` 与 `RC_2_after_confirm.png` 的 sha256 相同，字段 `screenshots`，blob {C(raw_b)}）⇒ 复核态只有文字读数、没有自己的像素。
· 我的暴露词表不分大小写，于是它把锚点名 `trial-create-error` 里的 error 咬了一口（属性是 data-testid，属于 DOM 契约钩子，值里没有异常原文）。你那张渲染件在同一枚壳上属性命中为 0、漏词表 {SC['commander_artefact_as_I_READ_IT']['leak_patterns_in_his_ruler']} 条 —— 两份读数我并排放着，Q71 那句口径归你或仲裁，不自判。

**用户现在做不到什么（只列这次量到的）**
· 第 3 步按下「确认创建」仍然建不成行程：腿照发、状态 500、正文空，人留在原地，没有 id；能读到的解释只有那两句话（件 blob {C(raw_b)}）。
· 拿着一个 id 去看某个行程仍然做不到：那一屏说的是「还要填什么」（尾部四行原文在件里，字段 `tail_lines`，blob {C(fre_b)}），而不是「这个 id 不存在」，屏上也没有通向列表或收件箱的可按项。

**纪律**：产品字节 0 改；路上看到的三件一律不修，全部交你派单；权威线 0 写；ref 0 推别人的；demo/reset 0；_live.db 与 _preview.db 0 读 0 写；git apply 0；凭据 0 打印；手机链只被我驱动 UI 与只读 GET，写请求只发生在我自己那一次向导提交里；:4782 与隧道我一行都没碰（本块的取证方式与全部判据在同件，blob {C(sco_b)}）。
```

坐标（写时从分支 tree 现读，写时尖 {tip[:12]}… · 全 40 位 {tip}）：走路读数 `{raw_b}` {C(raw_b)} · 评分件 `{sco_b}` {C(sco_b)} · 三面字节 `{fat_b}` {C(fat_b)} · 字面量扫描 `{anc_b}` {C(anc_b)} · 干净上下文读数 `{fre_b}` {C(fre_b)} · 代次漂移 `{dri_b}` {C(dri_b)} · 截图 `{PFX}/shots/RC_1_review.png` {C(PFX + '/shots/RC_1_review.png')} · `{PFX}/shots/RC_2_after_confirm.png` {C(PFX + '/shots/RC_2_after_confirm.png')} · `{PFX}/shots/RC_3_dead_id.png` {C(PFX + '/shots/RC_3_dead_id.png')} · `{PFX}/shots/RC_4_dead_id_fresh.png` {C(PFX + '/shots/RC_4_dead_id_fresh.png')} · 量具 `{PFX}/instruments/r5_recheck.cjs` {C(PFX + '/instruments/r5_recheck.cjs')} · `{PFX}/instruments/r5_recheck_score.py` {C(PFX + '/instruments/r5_recheck_score.py')} · `{PFX}/instruments/r5_anchor_scan.py` {C(PFX + '/instruments/r5_anchor_scan.py')} · `{PFX}/instruments/r5_faces_get.py` {C(PFX + '/instruments/r5_faces_get.py')} · `{PFX}/instruments/r5_deadid_fresh.cjs` {C(PFX + '/instruments/r5_deadid_fresh.cjs')} · `{PFX}/instruments/r5_tip_drift.py` {C(PFX + '/instruments/r5_tip_drift.py')} · 上一块 aad2d1f2_0902.md 的 Q43 r4d 回执原件补发在 `{PFX}/ledger_inbox_proof_walk_0902_q43r4d.json` {C(PFX + '/ledger_inbox_proof_walk_0902_q43r4d.json')}。

要你定的只有两件：① 现尖超前 {DRIFT['commits_ahead']} 笔且里面有向导本体与 ORD-0332/0344 族——要不要换代后我再走一次（我不自启，因为你说只重跑一次）；② `trial-create-error` 这枚锚点名里的 error 算不算 Q71 那一句的范围（我把两向读数都放了，判级不归我）。

"""
text = BODY + CLOSING.read_text(encoding='utf-8').strip() + '\n'
path = INBOX / name
path.write_text(text, encoding='utf-8', newline='\n')
rb = subprocess.run(['python', str(GATE), '--text', str(path), '--out',
                     str(OUT / 'recheck_gate_r4d.txt'), '--expect-clean'],
                    capture_output=True, text=True, encoding='utf-8', errors='replace')
receipt = {'block_file': str(path), 'bytes': path.stat().st_size, 'gate': GATE.name,
           'q43_rc': rb.returncode, 'q43_out': rb.stdout, 'q43_err': rb.stderr,
           'generation': DRIFT['generation_named_by_the_commander'],
           'mirror_tip_at_block_write': DRIFT['mirror_tip_read_now'],
           'branch_tip_at_block_write': tip, 'ledger_written_by_this_lane': False,
           'baseline_items_re_measured': len(SC['baseline_items']),'judgments_computed_in_the_scored_file': len(SC['judgments'])}
(OUT / 'ledger_inbox_proof_recheck.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=1),
                                                     encoding='utf-8', newline='\n')
print(json.dumps({'block': name, 'bytes': receipt['bytes'], 'rc': rb.returncode}, ensure_ascii=False))
print(rb.stdout[-1400:])
print('ERR:', rb.stderr[-500:])
