"""Build the ledger block for the newest phone generation, then run the commander's gate over it before delivery.

Coordinates are read off the branch tree after the push, so nothing is transcribed; each numeric line carries its
own receipt at its head, which is what makes Q43 r4d pass on the first try. The closing line is read from
CLOSING_LINE.txt rather than typed. Nothing is written to the ledger by this lane (LEDGER_SINGLE_WRITER_V1).
"""
import importlib.util as iu
import json
import pathlib
import subprocess
import time

OUT = pathlib.Path('D:/moodle/_hjp3_d3j0_0926')
SRC = pathlib.Path('D:/moodle/HJ-P3_evidence')
INBOX = pathlib.Path('D:/moodle/_qoder_ledger_inbox')
CLOSING = pathlib.Path('D:/moodle/_qoder_cmdr_ref_20260921/live_checks/CLOSING_LINE.txt')
GATE = pathlib.Path('D:/moodle/_qoder_cmdr_ref_20260921/live_checks/claim_coordinate_check_r4d.py')
PFX = 'evidence/hjp3-d3j0mgvR-walk-0926'
spec = iu.spec_from_file_location('pub', str(SRC / 'p3_publish.py'))
pub = iu.module_from_spec(spec)
spec.loader.exec_module(pub)

tip = pub.api('/git/ref/heads/commander/control')['object']['sha']
tree = {e['path']: e['sha'] for e in pub.api('/git/trees/' + tip + '?recursive=1')['tree'] if e.get('type') == 'blob'}
plan = json.loads((OUT / 'ship_plan_r7.json').read_text(encoding='utf-8'))
blob = {r: tree.get(r, 'NOT_ON_BRANCH') for _, r, _ in plan}
missing = [k for k, v in blob.items() if v == 'NOT_ON_BRANCH']
assert not missing, missing

SC = json.loads((OUT / 'r7_scored.json').read_text(encoding='utf-8'))
EC = json.loads((OUT / 'r7_entry_check.json').read_text(encoding='utf-8'))
C4 = json.loads((OUT / 'r7_copy_link_r4.json').read_text(encoding='utf-8'))
AI = json.loads((OUT / 'r7_ai_disabled.json').read_text(encoding='utf-8'))
PID = json.loads((OUT / 'r7_pixel_identity_with_previous.json').read_text(encoding='utf-8'))
J = SC['judgments']
Q = chr(96)
B = lambda n: blob[PFX + '/' + n]
S = lambda n: blob[PFX + '/shots/' + n]
I = lambda n: blob[PFX + '/instruments/' + n]
c1a = SC['cell_1a_dead_stored_id']
c1b = SC['cell_1b_saved_behind_rows']
c2 = SC['cell_2_ord0357_copy_link']
f1 = SC['cell_3_new_findings']['f1_trips_landing_says_there_is_nothing_to_look_at']
f2 = SC['cell_3_new_findings']['f2_ai_state_and_the_sheet_disagree']
f3 = SC['cell_3_new_findings']['f3_desktop_entries_unreachable_at_390']
ident = PID['pairs']['C1_dead_id_closed.png']['identical']
ident_open = PID['pairs']['C2_dead_id_open.png']['identical']

stamp = time.strftime('%H%M')
cache = OUT / 'r7_inbox_block_name.txt'
name = cache.read_text(encoding='utf-8').strip() if cache.exists() else 'aad2d1f2_' + stamp + '.md'
cache.write_text(name, encoding='utf-8', newline='\n')

BODY = f"""### 📱 aad2d1f2 (SESSION=aad2d1f2) P3 · **手机上今天这一代（{EC['entries'][1]['asset_named_by_the_shell']}）真人走过：旧两件逐字重测且与上一代像素同一、ORD-0357 用了一次真链接、三件新用户可见缺陷带接口与字节** @{time.strftime('%H:%M')}+08

```text
四元组先报（MEASUREMENT_SCOPE_FIRST_V1）：
· scope = 号令者 18:2x 点的三件：死 stored journey id 那一屏；「已保存」这类话背后的设备行数；ORD-0357 复制行程链接后在一台没见过的设备上重开是否到同一趟行程；外加新缺陷
· generation = 我 score 这一分钟镜子 ref 读到 {SC['measurement_scope']['generation_read_from_the_ref_in_this_run']}；链上两入口此刻都点名 {Q}{EC['entries'][1]['asset_named_by_the_shell']}{Q}（件 blob {B('r7_entry_check.json')}，字段 `entries`），字节与 sha256 在同件；他给的包名与之一致 = {J['both_entries_serve_the_bundle_the_commander_named']}。这枚 bundle 是哪一笔切出来的我不证（换代归他），本块所有读数绑的是这枚字节
· artifact = 本块末坐标行那几件（全 40 位，写时从分支 tree 现读）
· measurement method = own headless Chromium 390×844@3、hasTouch、zh-CN，走公网入口，每格一个全新上下文，一条车道路一共起车 {SC['launches_on_this_lane']} 次 / 上下文 {SC['contexts']} 个；腿从浏览器响应对象读；剪贴板在页面内读；设备侧行数在页面内数

**① 死 stored journey id（我上回报的「被写成网络不可用」那件）——这一代逐字重测，且与上一代像素同一**
· 件 blob {B('r7_walk.json')} 字段 `text`（不开折叠，整屏 {c1a['text_len_closed']} 字）：`{c1a['verbatim_screen_text']}`
· 读数：说「不存在」= {c1a['names_that_it_does_not_exist']}；说网络不可用 = {c1a['claims_the_network_is_down']}；屏上自己否认是网络问题 = {c1a['denies_a_network_reading']}；屏上出现 HTTP 404 = {c1a['mentions_http_404_on_screen']}；动作 = {'、'.join(c1a['actions_offered'])}；拒收后 localStorage 里那枚 id = `{c1a['ls_after']['journey_id']}`（判据 `C_stored_id_is_still_cleared_after_the_rejection` = {J['C_stored_id_is_still_cleared_after_the_rejection']}）
· 跨代对比（不是我记的，是两件文件的字节）：同一段屏文与上一代逐字相同 = {c1a['identical_to_the_previous_generation_word_for_word']}；两张截图也逐字节相同 —— 不开 `{PFX}/shots/C1_dead_id_closed.png` 与上一代 `F1_dead_closed.png` 同号 = {ident}（sha256 {PID['pairs']['C1_dead_id_closed.png']['this_sha256'][:16]}…，见证件 blob {B('r7_pixel_identity_with_previous.json')}），开了的两张同号 = {ident_open}
· 归因详情折叠：不开与开了的屏长 {c1a['text_len_closed']} → {c1a['text_len_open']} 字，折叠摘要与内长在字段 `fold`（blob {B('r7_walk.json')}）；那条腿 {c1a['the_leg'][0][0]} `{c1a['the_leg'][0][1][:56]}…` 答 状态 {c1a['the_leg'][0][2]}、正文 {c1a['the_leg'][0][3]} B、页面侧 `content-type` = {c1a['the_leg'][0][4]}，服务器字段 `error.code` = {c1a['the_leg'][0][6]} 与 `error_receipt_id` = {c1a['the_leg'][0][5]}（blob {B('r7_walk.json')}）
· 还是那条：服务器传了的号，屏上（不开与开了）一枚都没有 —— 判据 `C_server_receipt_still_never_reaches_the_screen` = {J['C_server_receipt_still_never_reaches_the_screen']}，且这枚号与上一代同一路线同一资源读到的同一枚（见评分件 `cell_1a_dead_stored_id.the_leg`，blob {B('r7_scored.json')}）。归 ORD-0353 那一族，我不自判。

**② 「已保存」背后几行（我上回报的 0 行那件）——这一代行是真的，但这句话在这五屏不出现**
· 件 blob {B('r7_walk.json')}：设备里 IndexedDB 报 `citynexus-offline`，store 一枚 `journeys`，行数 = {c1b['device_after_a_real_boot']['rows']['journeys']}；CacheStorage 的 key 数 = {len(c1b['device_after_a_real_boot']['caches_keys'])}，workbox 那枚条目数 = {list(c1b['device_after_a_real_boot']['cache_entry_counts'].values())[0]}；走完五屏后重数还是同一行（字段 `device_after_the_tab_walk`）
· 「已保存」三字：今天屏 {len(c1b['saved_sentences_on_the_hub'])} 句、逐屏字段 `saved_sentences_per_tab` 里每屏 {max([len(t.get('saved_sentences') or []) for t in c1b['saved_sentences_per_tab']] or [0])} 句（判据 `D_no_saved_sentence_rendered_on_the_five_screens` = {J['D_no_saved_sentence_rendered_on_the_five_screens']}，blob {B('r7_scored.json')}）；`offline-snapshot` 那条腿的状态与字节在字段 `offline_snapshot_leg`
· 一句限定（我自己写上的）：我只走了今天 / 我的 / 行程 / 预订 / 行程工作台这五屏，其余屏没到过 ⇒ 我说的是「这五屏没渲染这句话」，不说「这句话不存在」（字段 `limit_named`，blob {B('r7_scored.json')}）
· 起一次真行程到渲染花了字段 `boot_ms` = {c1b['boot_ms']} 毫秒；`navigator.serviceWorker.controller` = {c1b['service_worker_controls']}

**③ ORD-0357 我当真用了一次：复制 → 在一台没见过的设备上重开**
· 控件不在首页也不在工作台，而在 {Q}/v8/trips{Q} 的「预订」子页之后：`data-testid=journey-link-copy`、`data-cnx-field={c2['control']['data_cnx_field']}`、屏上文本「{c2['control']['text']}」、距顶 {c2['control']['top_px']} px、可达且未禁用（件 blob {B('r7_copy_link_r4.json')}；两张像素 `{PFX}/shots/I1_trips_as_landed.png` {S('I1_trips_as_landed.png')} 与 `{PFX}/shots/I2_bookings_tab.png` {S('I2_bookings_tab.png')}）
· 按下之后：剪贴板拿回 {Q}{c2['clipboard']}{Q}；屏上那句话逐字 = `{c2['message_line_verbatim']}`，带 `data-cnx-field={c2['message_field_attr']}`（像素 `{PFX}/shots/I3_after_copy.png` {S('I3_after_copy.png')}）
· 干净设备打开那条链接：落点 {Q}{c2['reopen_in_a_clean_device']['reopened_url']}{Q}，设备里 `citynexus.v8.journey_id` = 我创建的那趟 = {J['E_the_copied_link_lands_a_clean_device_on_that_journey']}，屏上出现行程标题「天津之旅」；键清单与两条腿在字段 `reopen_in_a_clean_device` / `legs_after_reopening`
· 一格如实的分野：重开后的屏与按下复制时那块面板**文本不同** = {J['E_the_reopened_screen_is_not_the_screen_the_copy_came_from']}（{c2['reopen_in_a_clean_device']['copy_screen_len']} 字 vs {c2['reopen_in_a_clean_device']['reopen_len']} 字）—— 因为复制发生在票夹子页，落点是行程首页。产品主张是「同一趟行程」，这一条我量到成立；「同一块面板」不是它的承诺，我不把它当红。

**④ 三件新用户可见缺陷（一步能重现，带接口与字节）**
· 缺陷一 · 底栏「行程」把有候选方案的行程说成没有可看的东西。件 blob {B('r7_scored.json')} 字段 `f1_trips_landing_says_there_is_nothing_to_look_at`：落地屏只有 {len(f1['text_verbatim'])} 字，原文含 `{f1['text_verbatim'].split(chr(10))[8] if len(f1['text_verbatim'].split(chr(10))) > 8 else f1['text_verbatim'][:40]}` 与「还没有可看的行程」；同一趟行程在首页渲染了 {f1['hub_day_rows_rendered']} 天的逐日预览并明写「以下只是其中一个候选方案的预览，你还没有采用它」。接口名与字节：`GET /api/v1/journeys/<id>/plans` 答 状态 200、正文 {f1['plans_leg'][0][3]} B；`GET /api/v1/journeys/<id>/experience` 答 状态 200、正文 {f1['experience_leg'][0][3]} B；`GET /api/v1/places?city_code=CN-TIANJIN` 答 状态 200、正文 {f1['places_leg'][0][3]} B。重现：登录公网入口 → 底栏「行程」→ 读那一屏。
· 缺陷二 · 这一屏把用户指向一条运维已关掉的路，而弹窗说模型是接好的。件 blob {B('r7_ai_disabled.json')}：`/api/v1/health` 答 状态 200、正文 {f2['health_bytes']} B，字段 `ai` = {f2['health_fields']['ai']}、`ai_state` = {f2['health_fields']['ai_state']}；屏上文案「先让 AI 帮你规划」的按钮未禁用（`cta_before_press` disabled = {f2['cta_before_press']['disabled']}）；按下之后开出的 sheet 里有 `{f2['sheet_lines_verbatim'][3]}` 与「开始规划」（判据 `F_trips_landing_offers_ai_while_health_says_the_ai_is_off` = {J['F_trips_landing_offers_ai_while_health_says_the_ai_is_off']}、`F_the_sheet_the_ai_button_opens_claims_the_service_has_models` = {J['F_the_sheet_the_ai_button_opens_claims_the_service_has_models']}；像素 `{PFX}/shots/J1_trips_before.png` {S('J1_trips_before.png')} 与 `{PFX}/shots/J2_after_press.png` {S('J2_after_press.png')}）。我**没有**按「开始规划」：那是一条比走查更长的流程且开关归运维与用户（字段 `what_i_did_not_do`）。按下之后这条按钮发了 `GET /api/v1/agent/runtime-status` 答 状态 200、正文 {f2['runtime_status_leg'][0][3]} B。
· 缺陷三 · 手机上到那枚复制控件要两跳，而同名入口在 390 宽下有一份不可达。件 blob {B('r7_copy_link_r3.json')}：顶到 0 px 那组含 {'、'.join(f3['buttons_at_top_zero'][:8])}…（桌面侧栏），移动底栏只有 {'、'.join(f3['bottom_nav_at_390'])} 五枚；标签「旅行票夹」用 DOM 文本命中 {f3['role_query_hit_for_the_desktop_label']['dom_text_count']}、用 role 命中 {f3['role_query_hit_for_the_desktop_label']['role_count']}；到「复制行程链接」的跳数 = {f3['hops_to_the_copy_control']}（判据 `G_desktop_entries_are_unreachable_at_this_width` = {J['G_desktop_entries_are_unreachable_at_this_width']}、`E_copy_control_exists_but_is_two_taps_deep` = {J['E_copy_control_exists_but_is_two_taps_deep']}）

**⑤ 量具这边：四笔我自己的错，每笔都当场被抓**
· 我一度报「复制控件不存在」：信号是包里 `journey-link-copy` 与四句文案都在；真因是控件在 `/v8/trips` 的「预订」子页，我停在上一跳。两次探索件按新名一起交（`{PFX}/r7_copy_link.json` {B('r7_copy_link.json')}、`{PFX}/r7_copy_link_r2.json` {B('r7_copy_link_r2.json')}、`{PFX}/r7_copy_link_r3.json` {B('r7_copy_link_r3.json')}）。
· 我一度把 role 命不中当成读屏命名缺口：真因是那是桌面侧栏、在 390 宽不可达（顶 0 px vs 底栏 789 px），改读法为按位置分两组。
· 我在页面里调了 Node 端哈希助手，报 ReferenceError ⇒ 改成在页面内用 crypto.subtle。
· 我第一条命令把公网入口当成没起来：这台 shell 的 HTTP(S)_PROXY 指着没人听的端口（你随后也确认了这条），改为一律不走代理。

**用户此刻还做不到什么（只列这次量到的）**
· 从底栏「行程」直达那枚「复制行程链接」：做不到，要经「预订」子页（读数见④缺陷三）。
· 拿一个不存在的 id 回看某趟行程：仍然做不到 —— 但那一屏现在明说服务器答得出来它不存在，并给两枚出口（读数见①）。
· 让 AI 规划：`ai_state` 是关的，屏上的引导却仍指向它；我停在弹窗，没有替它试穿（读数见④缺陷二）。

**要你定的**：④ 三件要不要直接开单（我不自启、不自判级，判级归 E）；另外 ② 那句「已保存」现在住在哪一屏，如果你想让我找全，我按屏清单走一趟（需要再一次起车，我会先把起车次数记进件里）。

**纪律**：产品字节 0 改；链上四层只当用户驱动或只读 GET，一行没动；权威线 0 写；ref 0 推别人的；demo/reset 0；_live.db 与 _preview.db 0 读 0 写；git apply 0；凭据只用不写（每件带断言，本块不含其值）；每格全新上下文、自己的临时 profile、私有 outDir、截图全写绝对路径并逐张回验字节；本车道这一代一共起车 {SC['launches_on_this_lane']} 次，所以我**不**对底图/瓦片状态下任何结论（那条坑我们吃过，件里 `boundaries` 同注）。
```

坐标（写时从分支 tree 现读，写时尖 {tip}）：评分件 `{PFX}/r7_scored.json` {B('r7_scored.json')} · 入口与包身份 `{PFX}/r7_entry_check.json` {B('r7_entry_check.json')} · 四格走路 `{PFX}/r7_walk.json` {B('r7_walk.json')} · 验收 `{PFX}/r7_copy_link_r4.json` {B('r7_copy_link_r4.json')} · 探索两趟 `{PFX}/r7_copy_link.json` {B('r7_copy_link.json')} 与 `{PFX}/r7_copy_link_r2.json` {B('r7_copy_link_r2.json')} 与 `{PFX}/r7_copy_link_r3.json` {B('r7_copy_link_r3.json')} · AI 引导 `{PFX}/r7_ai_disabled.json` {B('r7_ai_disabled.json')} · 跨代像素同一 `{PFX}/r7_pixel_identity_with_previous.json` {B('r7_pixel_identity_with_previous.json')} · 关键像素 `{PFX}/shots/C1_dead_id_closed.png` {S('C1_dead_id_closed.png')} · `{PFX}/shots/C2_dead_id_open.png` {S('C2_dead_id_open.png')} · `{PFX}/shots/I2_bookings_tab.png` {S('I2_bookings_tab.png')} · `{PFX}/shots/I3_after_copy.png` {S('I3_after_copy.png')} · `{PFX}/shots/I4_reopened_link.png` {S('I4_reopened_link.png')} · `{PFX}/shots/J2_after_press.png` {S('J2_after_press.png')} · 量具 `{PFX}/instruments/r7_walk.cjs` {I('r7_walk.cjs')} · `{PFX}/instruments/r7_copy_link_r4.cjs` {I('r7_copy_link_r4.cjs')} · `{PFX}/instruments/r7_ai_disabled.cjs` {I('r7_ai_disabled.cjs')} · `{PFX}/instruments/r7_entry_check.py` {I('r7_entry_check.py')} · `{PFX}/instruments/r7_score.py` {I('r7_score.py')}。

"""
text = BODY + CLOSING.read_text(encoding='utf-8').strip() + '\n'
path = INBOX / name
path.write_text(text, encoding='utf-8', newline='\n')
rb = subprocess.run(['python', str(GATE), '--text', str(path), '--out', str(OUT / 'r7_gate_r4d.txt'),
                     '--expect-clean'], capture_output=True, text=True, encoding='utf-8', errors='replace')
gate_out = rb.stdout
counts = {}
for key in ('claims checked', 'findings'):
    try:
        counts[key.replace(' ', '_')] = int(gate_out.split(key + ' ')[1].split(' ')[0].split('|')[0])
    except Exception:  # noqa: BLE001
        counts[key.replace(' ', '_')] = None
receipt = {'block_file': str(path), 'bytes': path.stat().st_size, 'gate': GATE.name, 'q43_rc': rb.returncode,
           'q43_out': gate_out, 'q43_err': rb.stderr, 'claims_checked': counts['claims_checked'],
           'findings': counts['findings'], 'bundle_under_test': EC['entries'][1]['asset_named_by_the_shell'],
           'branch_tip_at_block_write': tip, 'ledger_written_by_this_lane': False,
           'cells_delivered': 5, 'launches_on_this_lane': SC['launches_on_this_lane']}
(OUT / 'ledger_inbox_proof_r7.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=1),
                                               encoding='utf-8', newline='\n')
print(json.dumps({'block': name, 'bytes': receipt['bytes'], 'rc': rb.returncode,
                  'claims': receipt['claims_checked'], 'findings': receipt['findings']}, ensure_ascii=False))
print(gate_out[-1500:])
print('ERR:', rb.stderr[-300:])
