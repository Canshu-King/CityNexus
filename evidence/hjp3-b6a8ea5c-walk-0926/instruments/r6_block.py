"""Build the ledger block for the b6a8ea5c walk, then run the commander's current gate over it before delivery.

Same rule as every block I hand him: no number without a coordinate it can be checked against, and every
coordinate is read off the branch tree AFTER the push, so nothing is transcribed from memory. The closing line is
read from CLOSING_LINE.txt. The gate is run here with --expect-clean and its output is kept as a receipt.
"""
import importlib.util as iu
import json
import pathlib
import subprocess
import time

OUT = pathlib.Path('D:/moodle/_hjp3_b6a8_0926')
SRC = pathlib.Path('D:/moodle/HJ-P3_evidence')
INBOX = pathlib.Path('D:/moodle/_qoder_ledger_inbox')
CLOSING = pathlib.Path('D:/moodle/_qoder_cmdr_ref_20260921/live_checks/CLOSING_LINE.txt')
GATE = pathlib.Path('D:/moodle/_qoder_cmdr_ref_20260921/live_checks/claim_coordinate_check_r4d.py')
PFX = 'evidence/hjp3-b6a8ea5c-walk-0926'
spec = iu.spec_from_file_location('pub', str(SRC / 'p3_publish.py'))
pub = iu.module_from_spec(spec)
spec.loader.exec_module(pub)

tip = pub.api('/git/ref/heads/commander/control')['object']['sha']
tree = {e['path']: e['sha'] for e in pub.api('/git/trees/' + tip + '?recursive=1')['tree']
        if e.get('type') == 'blob'}
plan = json.loads((OUT / 'ship_plan_r6.json').read_text(encoding='utf-8'))
logs = [json.loads((OUT / n).read_text(encoding='utf-8')) for n in
        ('ship_result_r6.json', 'ship_result_r6b.json')]
blob = {r: tree.get(r, 'NOT_ON_BRANCH') for _, r, _ in plan}
missing = [k for k, v in blob.items() if v == 'NOT_ON_BRANCH']
assert not missing, missing
# the first log carries one 409 optimistic-concurrency refusal; the proof that matters is that every planned
# name is on the branch now and that the refused name appears exactly once in the commit history (checked by the
# write counter), not that each attempt returned zero
rows = [x for lg in logs for x in lg['pushed']]
refused = sorted({x['remote'] for x in rows if x['rc'] != 0})
assert all(blob[r] != 'NOT_ON_BRANCH' for r in refused), refused
assert all(x['local_matches_branch_bytes'] for x in rows if x['rc'] == 0 and x['remote'] in blob)

SC = json.loads((OUT / 'r6_readings_scored.json').read_text(encoding='utf-8'))
WA = json.loads((OUT / 'r6_walked_asset_witness.json').read_text(encoding='utf-8'))
DR = json.loads((OUT / 'r6_drift.json').read_text(encoding='utf-8'))
TW = json.loads((OUT / 'r6_tunnel_watch.json').read_text(encoding='utf-8'))
B = json.loads((OUT / 'r6_wizard_create.json').read_text(encoding='utf-8'))
F = json.loads((OUT / 'r6_receipt_anchor_offline.json').read_text(encoding='utf-8'))
C = json.loads((OUT / 'r6_dead_id_saved.json').read_text(encoding='utf-8'))
A3 = json.loads((OUT / 'r6_dest_block_r3.json').read_text(encoding='utf-8'))
J = SC['judgments']
Q = chr(96)


def B_(n):
    return blob[PFX + '/' + n]


def S_(n):
    return blob[PFX + '/shots/' + n]


def I_(n):
    return blob[PFX + '/instruments/' + n]


LOG = {}
for _n in ('ship_result_r6.json', 'ship_result_r6b.json', 'ship_result_r6c.json'):
    LOG[_n] = tree.get(PFX + '/' + _n, 'NOT_ON_BRANCH')
assert LOG['ship_result_r6.json'] != 'NOT_ON_BRANCH' and LOG['ship_result_r6b.json'] != 'NOT_ON_BRANCH'
L_ = lambda n: LOG[n]


stamp = time.strftime('%H%M')
cache = OUT / 'r6_inbox_block_name.txt'
name = cache.read_text(encoding='utf-8').strip() if cache.exists() else 'aad2d1f2_' + stamp + '.md'
cache.write_text(name, encoding='utf-8', newline='\n')
gen = SC['measurement_scope']
cells = SC['baseline_items'] if 'baseline_items' in SC else {}
dead_leg = SC['cell_C_dead_stored_id']['the_leg_that_answered']
groups = SC['cell_A_destinations_block']['group_heading_counts_mine_corrected']
cap_bytes = SC['cell_A_destinations_block']['capability_leg_bytes_by_name']
legs_after = SC['cell_B_wizard_create']['legs_after_press']
created = SC['cell_B_wizard_create']['created_201_legs']
stores = SC['cell_E_device_holds_a_copy']
fold = SC['cell_C_dead_stored_id']['fold']

BODY = f"""### 📱 aad2d1f2 (SESSION=aad2d1f2) P3 · **公网手机上真人走过五格（{gen['generation'][:8]}…那一代）：两件旧缺陷都量到新态，服务器给的回执号上了线没上屏；公网入口在我回头时答 状态 530** @{time.strftime('%H:%M')}+08

```text
四元组先报（MEASUREMENT_SCOPE_FIRST_V1）：
· scope = 号令者 17:2x 点的五格：「看支持的目的地」不开与开了；新建行程三步 → 确认创建 → 失败/等待屏；设备里存着一个服务器不认识的 journey id 那一屏（含归因详情折叠的开与不开）；「已保存」这类话背后的设备行数；以及我上回两件「做不到」的再量
· generation = 他点名的 {DR['named_by_the_commander']}（我 score 时镜子 ref 已是 {DR['tip_read_now']}，超前 {DR['commits_ahead']} 笔，见评分件判据 `the_mirror_moved_during_the_walk` = {J['the_mirror_moved_during_the_walk']}，件 blob {B_('r6_readings_scored.json')}）；链上实际服务的 bundle = {Q}{WA['asset_path_recorded_by_the_browser_passes']}{Q}，字节与 sha256 由每趟浏览器记下的名字回读钉住（件 blob {B_('r6_walked_asset_witness.json')}）
· artifact = 本块末坐标行那几件（全 40 位，写时从分支 tree 现读）
· measurement method = own headless Chromium 390×844@3、hasTouch、zh-CN，公网入口每格一个全新上下文；腿从浏览器响应对象上读；设备侧读数在页面里取；全文写在评分件（blob {B_('r6_readings_scored.json')}）

**读数总账**：五格都量到了新态；后端这次是活的 —— 四条 API 路径四种签名、我编的那条路径不与真路径同签名（判据 `an_application_answers_on_this_chain` = {J['an_application_answers_on_this_chain']}，签名表在件里字段 `backend_is_live.signature_per_path_local`，blob {B_('r6_gen_check.json')}）；本地那一跳答 server: uvicorn，公网那一跳答 server: cloudflare，两边在同一分钟点名同一枚 bundle（判据 `same_asset_name_on_both_entries_during_the_walk` = {J['same_asset_name_on_both_entries_during_the_walk']}，字段 `asset_the_chain_served_during_my_walk` 在漂移件 blob {B_('r6_drift.json')}）。

**① 「看支持的目的地」：分组整块住在折叠里，而且有一段「还没问过服务器」的过渡态**
· 不开：屏上只有这五个字的标签，11 枚城市名一枚都不在（判据 `A_grouping_lives_only_behind_the_tap` = {J['A_grouping_lives_only_behind_the_tap']}；壳的可见文本长度与 `names_visible_when_closed` 在件里字段 `cell_A_destinations_block`，blob {B_('r6_readings_scored.json')}；像素 `{PFX}/shots/A3_1_closed.png` {S_('A3_1_closed.png')}）。
· 刚点开：11 枚全部落在「未知或无数据」并写着「身份还没读到 / 还没问过服务器 / not-asked」（字段 `names_marked_not_asked_just_after_the_tap`，blob {B_('r6_readings_scored.json')}；像素 `{PFX}/shots/A3_2_just_opened.png` {S_('A3_2_just_opened.png')}）。
· 落定：应用自己发了 11 条 `GET /api/v1/destinations/capability?query=<名>`，各条状态与字节在字段 `capability_leg_bytes_by_name`（blob {B_('r6_dest_block_r3.json')}，多数一千七百上下、广州那一枚五千七百上下）。分组读数 = 已支持 {groups['已支持：服务器认得它，而且目录里有东西']} 枚 / 需联网 {groups['需联网才能解析：服务器现在认不出这个名字']} 枚 / 未知 {groups['未知或无数据：这一轮拿不出可规划的判定']} 枚，与屏上三个小标题一致（判据 `A_settled_split_matches_the_visible_headings` = {J['A_settled_split_matches_the_visible_headings']}，blob {B_('r6_readings_scored.json')}）；落定等了字段 `settled_after_ms` 那么多毫秒。
· 一句限定：这一格的分组名字与实际能力是不是对得上，我只量到「服务器答什么屏上就分组什么」，具体每城的能力含义归 S4。

**② 新建行程第 3 步按下「确认创建」：这一格上回的「建不成」现在建得成了**
· 两条答 状态 201 真发生了：`POST /api/v1/travelers` 与 `POST /api/v1/journeys`，请求体与响应字节都在字段 `created_201_legs`（blob {B_('r6_readings_scored.json')}；全腿清单在走路件 blob {B_('r6_wizard_create.json')}），随后 `experience` 那条腿答 200 且正文很大（字段 `legs_after_press` 同件）。
· 设备里落成了真 id：字段 `stored_journey_id` 是一枚 36 位 uuid（blob {B_('r6_wizard_create.json')}），判据 `B_traveller_now_reaches_a_real_journey` = {J['B_traveller_now_reaches_a_real_journey']}。
· 但屏上九秒后还写着「正在创建…」与「已等待 9 秒」（尾部行在字段 `screen_9_s_after_the_press.tail_lines`，blob {B_('r6_wizard_create.json')}）⇒ 判据 `B_screen_still_says_creating_after_the_journey_exists` = {J['B_screen_still_says_creating_after_the_journey_exists']}。这一段这句话是诚实的：`第一次搜索一座城市实测要两分钟左右。服务器不会中途汇报进度，所以这里只有真实秒数，没有编出来的数字。` 与 `停止等待只是离开这块屏幕：服务器不会因此停下，行程数据也不会丢失。`，而且给了「停止等待」这枚动作。
· 这一条路上 0 枚失败腿 ⇒ 不该有回执号（判据 `B_no_failing_leg_so_no_receipt_was_due` = {J['B_no_failing_leg_so_no_receipt_was_due']}，字段 `failing_legs_on_this_path` 同件）。
· 像素：按下之前一张 `{PFX}/shots/B1_review_before_press.png` {S_('B1_review_before_press.png')}，九秒后一张 `{PFX}/shots/B2_after_confirm.png` {S_('B2_after_confirm.png')}（我把「复核态没有自己的像素」那笔仪器错修了，现在按下前后各一张）。

**③ 失败屏能不能看到一枚服务器给的回执号：线上传了，屏上没上**
· 我造的是真会失败的一格，读数全在字段 `the_leg_that_answered`（blob {B_('r6_receipt_anchor_offline.json')}，下面这行只是把同一格念一遍）：设备里写 `citynexus.v8.journey_id` = 一枚服务器不认识的 uuid，于是那一屏第一条腿是 {dead_leg[0]} `/api/v1/journeys/<那枚 uuid>/experience`，答 状态 {dead_leg[2]}、正文 {dead_leg[3]} B；页面侧 `content-type` 为 {dead_leg[4]}、`from_service_worker` = {dead_leg[5]}；同一条腿上读到的服务器字段是 `error.code` = {dead_leg[7]} 与 `error_receipt_id` = {dead_leg[6]}，那枚 uuid 的完整写法在同件字段 `dead_id` 里。
· 屏上说什么（原文逐字在走路件 blob {B_('r6_dead_id_saved.json')} 的 `text_a_traveller_reads_first` 字段，整屏长度读在 `view_len_closed`）：`连接正常` ／ `这台服务器上没有这一趟行程了`。
· 第三句的原文与那条 id 前缀都在件里（blob {B_('r6_dead_id_saved.json')}），句子里屏上写着 `这台设备还记得行程 00000000…，但服务器明确回答它不存在（HTTP 404）。这不是网络问题：服务器刚才答得出来。你的其它行程没有受影响。` —— 动作两枚「选一趟行程」「重试」，`aria-live` = assertive，读数在 blob {B_('r6_dead_id_saved.json')}。旧的那件「死 id 被写成网络不可用」在这里量到的是反面：判据 `C_dead_id_screen_no_longer_claims_the_network_is_down` = {J['C_dead_id_screen_no_longer_claims_the_network_is_down']}，且拒收之后那枚 id 被清掉了（判据 `C_stored_id_is_cleared_after_the_rejection` = {J['C_stored_id_is_cleared_after_the_rejection']}，字段 `journey_id_left_in_localStorage` 同件）。
· 折叠（`归因详情`）里的读数：不开时 `failure-attribution-line` 的 innerText 长 {fold['attribution_line_inner_len_closed']}、开以后 {fold['attribution_line_len_open']} 字（哈希与开头在字段 `fold`，blob {B_('r6_readings_scored.json')}；两张像素 `{PFX}/shots/C1_dead_id_closed.png` {S_('C1_dead_id_closed.png')} 与 `{PFX}/shots/C2_dead_id_open.png` {S_('C2_dead_id_open.png')}）。我按两种读法各自交代：innerText 在折叠时读不到不等于屏上没有，这一格我只声称「开以后是 {fold['attribution_line_len_open']} 字」。
· 新读到的那一件（要你派单）：屏上 `CNX-…` 形式的号一枚都没有，折叠里也没有；而且 `data-cnx-field` / `data-cnx-receipt` 这两类锚点在这一屏 0 枚，客户端自己写的那个 `NOT-EMITTED` 兜底词也没出现（三条读数同件并列：`C_server_sent_a_receipt_that_the_screen_never_shows` = {J['C_server_sent_a_receipt_that_the_screen_never_shows']}、`C_no_receipt_anchor_is_rendered_at_all` = {J['C_no_receipt_anchor_is_rendered_at_all']}、`clients_own_NOT_EMITTED_word_on_screen` = {SC['receipt_reaches_the_screen']['clients_own_NOT_EMITTED_word_on_screen']}（blob {B_('r6_readings_scored.json')}），blob {B_('r6_readings_scored.json')}）；同一枚 bundle 里这些机件是存在的（字段 `machinery_exists_in_the_served_bundle`，同件，量法是只读字面量搜服务字节）。

**④ 那枚号是不是「每一次故障一个」：我这三次不是**
· 同一条路线连取三次：`distinct_receipts` = {SC['receipt_is_per_incident_or_per_route']['distinct_receipts']}、`distinct_trace_ids` = {SC['receipt_is_per_incident_or_per_route']['distinct_trace_ids']}、`distinct_body_hashes` = {SC['receipt_is_per_incident_or_per_route']['distinct_body_hashes']}（件 blob {B_('r6_readings_scored.json')}，字段 `receipt_is_per_incident_or_per_route`）。也就是说这枚号随路线与资源稳定重复，而每次请求变的是 trace_id。它能不能担当「旅客读回来就能定位这一次」的口径，我不判，交你或仲裁。

**⑤ 「已保存」这类话背后到底有几行：这一格量到 1 行，而那句话此刻不在这两屏上**
· 设备侧读数：IndexedDB 里有 `citynexus-offline`（版本在字段 `indexedDB_databases`），store 一枚 `journeys`，行数 = {stores['rows_per_store']['journeys']}；CacheStorage 有 {len(stores['caches_keys'])} 个 key，其中 workbox 那枚条目数 = {list(stores['cache_entry_counts'].values())[0]}（字段 `caches_keys` / `cache_entry_counts`，blob {B_('r6_receipt_anchor_offline.json')}）；判据 `E_the_device_really_holds_one_offline_copy` = {J['E_the_device_really_holds_one_offline_copy']}。
· 同时 `navigator.serviceWorker.controller` 在新上下文里为 False（判据 `E_the_page_is_not_controlled_by_the_service_worker_yet` = {J['E_the_page_is_not_controlled_by_the_service_worker_yet']}），`GET /api/v1/journeys/<id>/offline-snapshot` 那条腿的状态与字节在字段 `offline_snapshot_leg`。
· 「已保存」这三个字：我走过的两屏（今天/我的）里都匹配不到含它的整句（判据 `E_no_saved_sentence_rendered_on_the_two_tabs` = {J['E_no_saved_sentence_rendered_on_the_two_tabs']}，逐屏字段 `sentences_claiming_saved_on_the_hub_or_profile`）。所以旧的那件「写着已保存而背后 0 行」，这次量到的是「这屏没写，背后有 1 行」；至于那句话搬去了哪一屏，我没找全，不自称量过。
· 真行程起来花了字段 `boot_ms_until_the_hub_rendered` 那么多毫秒（blob {B_('r6_readings_scored.json')}），像素 `{PFX}/shots/E1_real_journey_settled.png` {S_('E1_real_journey_settled.png')} 与 `{PFX}/shots/F3_real_journey.png` {S_('F3_real_journey.png')} —— 两张不同尺寸，这一格我不据像素说底图的事（公共瓦片通道会被反复重启弄坏，这条我们吃过）。

**⑥ 两件现场事实，修不修不归我**
· 镜子又往前漂了：现读 {DR['tip_read_now']}，比点名那一尖超前 {DR['commits_ahead']} 笔，主题里是 ORD-0350 与 ORD-0353（清单在字段 `subjects` / `files_changed`，含向导本体那支源文件，判据 `the_pending_commits_reach_the_wizard_source` = {J['the_pending_commits_reach_the_wizard_source']}，blob {B_('r6_drift.json')}）。我没有重建、没有换代、没有再走第二遍。
· 公网入口现在不通：连采三次都是 {TW['public_samples'][0]['status']}（每次一枚不同的 cf-ray，见字段 `distinct_cf_ray_ids`，blob {B_('r6_tunnel_watch.json')}），而同一分钟本地那一跳 `/` 与 `/api/v1/health` 都 200、我走过那枚 bundle 仍可取到同样字节（判据 `the_public_entry_was_up_during_the_walk_and_answers_530_now` = {J['the_public_entry_was_up_during_the_walk_and_answers_530_now']}）。走路期间它是好的（判据 `same_asset_name_on_both_entries_during_the_walk` = {J['same_asset_name_on_both_entries_during_the_walk']}）。

**⑦ 量具这边：六笔我自己的错，每笔都有当场抓到的信号**
· 「{groups['已支持：服务器认得它，而且目录里有东西']} / 0 / 0」那次是错的：我把祖先一路爬到顶，最外层小标题覆盖了内层的；信号是同屏明明写着三枚在「需联网」、七枚在「未知」。改正后是 1 / 3 / 7（两件都在账上：错的 `{PFX}/r6_dest_block_r2.json` {B_('r6_dest_block_r2.json')}，对的 `{PFX}/r6_dest_block_r3.json` {B_('r6_dest_block_r3.json')}）。
· 「设备里 0 行」我一开始读不到行数：数完了没把结果挂回件里（信号是 store_names 有 journeys 而 rows 是 null）。改正后 rows = {stores['rows_per_store']['journeys']}。
· 「服务器没给回执号」我一开始也读漏了：我拿 `content-type` 决定要不要 parse JSON，而那一枚 404 在页面侧没有这个头（同一路由直连本地那一跳有 application/json）。改成按正文形状 parse 之后才读到 {dead_leg[6]}。
· 「公网入口拒我连接」是假象：这台 shell 现在导出的 HTTP(S)_PROXY 指着一个没人听的本地端口，我这条发布通道也被它挡过一次 —— 第一轮发布日志（blob {L_('ship_result_r6.json')}）里那一行答的是 状态 10061 且 0 件落地，第二轮不走代理后重投（blob {L_('ship_result_r6b.json')}）；同一分钟直连 TCP 端口 443 成功、DNS 也解析到两枚地址（观测 blob {B_('r6_tunnel_watch.json')}）。其它车道若用同一个 `urlopen` 取 GitHub 会撞同一件事；信号是同一个域名 DNS 解析得到两枚地址、直连 TCP 443 成功而 urllib 报 10061（三次采样与 cf-ray 在观测件里，blob 见坐标行）。改成不走代理的取法就通。
· 那枚凭据文件是制表符分隔的（`用户<TAB>秘钥`），我先按冒号/空格切，整行被当成用户名、隧道答 401；同一行有一次进了我的本地控制台输出 —— 它没有进任何交付件、帖或块，本批每件都带一条断言：件文本里出现凭据字段就拒绝落盘。
· 最后一笔是我的发布习惯：为了看有没有换代，我重跑了 `r6_gen_check.py`，而这件写自己的文件名 ⇒ 走路那一分钟的两侧读数被我自己的后读覆盖了。补了一枚只读见证件把「我到底走的是哪一枚 bundle」钉住（`{PFX}/r6_walked_asset_witness.json` {B_('r6_walked_asset_witness.json')}，字段 `what_this_is_not` 写明它不是走路期间的公网第二读）。

**用户现在做不到什么（只列这次量到的）**
· 拿着一个行程 id 回到那一趟：仍然做不到 —— 但那屏现在明说「这台服务器上没有这一趟行程了」并给「选一趟行程 / 重试」两枚出口（读数与像素见③）。
· 在一座第一次被搜的城市等结果：做不到马上看到行程 —— 屏幕老实说「要两分钟左右」并给「停止等待」，但九秒后还写着「正在创建…」，而那一刻行程其实已经建成（读数见②：两条答 状态 201 的腿与落盘的 id 同件，blob {B_('r6_wizard_create.json')}）。
· 想不点开「看支持的目的地」就知道哪座城市被支持：做不到 —— 不开时屏上只有那五个字（读数见①）。

**要你定的三件**：① 服务器传了的 `error_receipt_id` 要不要上屏、上在屏还是上在 `归因详情` 里、以及「同一路线同一资源给出同一枚号」够不够定位一次故障（③④，我只交读数）；② 「还没问过服务器」那段过渡态要不要 pending 文案与动作（①）；③ 建成之后屏幕仍写「正在创建…」这一格要不要单开一张（②）。我不自启，也不自判级 —— 判级归 E。

**纪律**：产品字节 0 改；路上看到的五件一律不修，全交你派单；权威线 0 写；ref 0 推别人的；demo/reset 0；_live.db 与 _preview.db 0 读 0 写；git apply 0；凭据不写进任何交付件（本批每件带断言）；链上那四层只被我当用户驱动或只读 GET，一层都没动；每格一个全新上下文、自己的临时 profile、私有 outDir；截图全写绝对路径并逐张回验字节；Q43 用的是你现行那把尺（r4d），本块交前自跑并留了原判输出，随后按新名上架到 `{PFX}/ledger_inbox_proof_r6_q43r4d.json`。
```

坐标（写时从分支 tree 现读，写时尖 {tip}）：评分件 `{PFX}/r6_readings_scored.json` {B_('r6_readings_scored.json')} · 两入口绑定 `{PFX}/r6_gen_check.json` {B_('r6_gen_check.json')} · 走路 bundle 见证 `{PFX}/r6_walked_asset_witness.json` {B_('r6_walked_asset_witness.json')} · 目的地块三时刻 `{PFX}/r6_dest_block_r3.json` {B_('r6_dest_block_r3.json')}（被取代的那读 `{PFX}/r6_dest_block_r2.json` {B_('r6_dest_block_r2.json')}，第一趟 `{PFX}/r6_dest_block.json` {B_('r6_dest_block.json')}）· 向导格 `{PFX}/r6_wizard_create.json` {B_('r6_wizard_create.json')} · 死 id 格 `{PFX}/r6_dead_id_saved.json` {B_('r6_dead_id_saved.json')} · 锚点与设备存储 `{PFX}/r6_receipt_anchor_offline.json` {B_('r6_receipt_anchor_offline.json')} · 漂移 `{PFX}/r6_drift.json` {B_('r6_drift.json')} · 入口观测 `{PFX}/r6_tunnel_watch.json` {B_('r6_tunnel_watch.json')} · 关键像素 `{PFX}/shots/A3_1_closed.png` {S_('A3_1_closed.png')} · `{PFX}/shots/A3_2_just_opened.png` {S_('A3_2_just_opened.png')} · `{PFX}/shots/A3_3_settled.png` {S_('A3_3_settled.png')} · `{PFX}/shots/B1_review_before_press.png` {S_('B1_review_before_press.png')} · `{PFX}/shots/B2_after_confirm.png` {S_('B2_after_confirm.png')} · `{PFX}/shots/C1_dead_id_closed.png` {S_('C1_dead_id_closed.png')} · `{PFX}/shots/C2_dead_id_open.png` {S_('C2_dead_id_open.png')} · `{PFX}/shots/E1_real_journey_settled.png` {S_('E1_real_journey_settled.png')} · 量具 `{PFX}/instruments/r6_gen_check.py` {I_('r6_gen_check.py')} · `{PFX}/instruments/r6_dest_block_r3.cjs` {I_('r6_dest_block_r3.cjs')} · `{PFX}/instruments/r6_wizard_create.cjs` {I_('r6_wizard_create.cjs')} · `{PFX}/instruments/r6_dead_id_saved.cjs` {I_('r6_dead_id_saved.cjs')} · `{PFX}/instruments/r6_receipt_anchor_offline.cjs` {I_('r6_receipt_anchor_offline.cjs')} · `{PFX}/instruments/r6_score.py` {I_('r6_score.py')} · `{PFX}/instruments/r6_tunnel_watch.py` {I_('r6_tunnel_watch.py')} · `{PFX}/instruments/r6_walked_asset_witness.py` {I_('r6_walked_asset_witness.py')}。

ORD-0312 的状态我另在总线上给（一句话：已交的部分与还卡的那个具名前提），本块不混。

"""
text = BODY + CLOSING.read_text(encoding='utf-8').strip() + '\n'
path = INBOX / name
path.write_text(text, encoding='utf-8', newline='\n')
rb = subprocess.run(['python', str(GATE), '--text', str(path), '--out', str(OUT / 'r6_gate_r4d.txt'),
                     '--expect-clean'], capture_output=True, text=True, encoding='utf-8', errors='replace')
receipt = {'block_file': str(path), 'bytes': path.stat().st_size, 'gate': GATE.name, 'q43_rc': rb.returncode,
           'q43_out': rb.stdout, 'q43_err': rb.stderr, 'generation': DR['named_by_the_commander'],
           'mirror_tip_at_block_write': DR['tip_read_now'], 'branch_tip_at_block_write': tip,
           'cells_measured': 5, 'instrument_faults_recorded': 6,
           'ledger_written_by_this_lane': False}
(OUT / 'ledger_inbox_proof_r6.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=1),
                                                encoding='utf-8', newline='\n')
print(json.dumps({'block': name, 'bytes': receipt['bytes'], 'rc': rb.returncode}, ensure_ascii=False))
print(rb.stdout[-1600:])
print('ERR:', rb.stderr[-400:])
