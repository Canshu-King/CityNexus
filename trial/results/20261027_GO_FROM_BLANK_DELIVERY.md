# 交付件：QODER_GO_FROM_BLANK_AND_AGENT_VISIBILITY 三刀（2026-10-27 01:08 本地 / 17:08Z 起算的同一夜）

权威枝 `rescue/v3-final-departure-20261022`，本件最后核对的尖 **57ac24254a7429a4afe5145724485e8b909d506d**
（`git ls-remote` 现读 `57ac24254a7429a4afe5145724485e8b909d506d`，逐字相同）。自表头上一版 pin 的 `3ad2f482ff` 之后又走 14 笔，
其中产品字节只有三枚：`e5fdc2734e`（§64，已保存过的草案卡仍允许「按以上时间重新准备方案」，重存时换新幂等键）、
`2b12752108`（§68／§72／§75，一次真成功的保存不再教旅客原地重试）、
`840534ec11`（§72／§73／§76，探索屏「自己先挑地点」那层默认展开；§73 已把它的支持读数更正过一次）。

**#339（同代性保留）已闭**：另有一棵零 dirty 的干净树 `E:/_cmdr_clean_1028`，现读 tip `840534ec11…`、
`git status --porcelain=v1` 行数 **0**，它与现尖之间的产品差异现读为空
（`git diff --stat 840534ec11..HEAD -- backend frontend contracts` → 空输出）。
在这棵树上真机走到「行程执行中」，地图 6 处＝计划点标签 6 枚＝地图列表 6 条＝库里 `activities` 6 条（§74）。
§47–§53 的早期屏证仍带 §67 记下的代差，未被这棵树追认；#337 的「430 且零 dirty」这一格还空着（§77：卡在网关超时）。

明细全部在 `trial/results/20261026_GO_FROM_BLANK_REPORT.md` §47–§77。

## 1. PRODUCT_SHA（本夜落线的产品字节，逐笔可取回）

| 提交 | 改的文件 | 那一格 |
| --- | --- | --- |
| `ab2ca5913a` | `backend/app/planning/travel_brief.py` + 新测试 | 已接受方案的站要能上图（第二臂 + 署名/CRS 分家） |
| `f2f65020b9` | `frontend/src/trial/mobile/MissionCockpit.tsx` | 日程与计划点跨两套 place-id 命名空间对齐 |
| `0188ebd5f4` | `frontend/src/trial/mobile/MobilePlanWorkbench.tsx:70` `:376` | 选用门拒绝那一屏，原因句下面给可按的一枚 |
| `c160a9cea3` | `frontend/src/trial/mobile/DraftDepartureCard.tsx:141` | `PLACE_NOT_IN_GOAL_TASK_SCOPE` 不再谎称「可以重试」 |
| `89dbbe22c1` | （撤回）| 我自己基于 500 字截断造的冗余分支，已撤 |
| `12609ae5e3` | `frontend/src/trial/mobile/DraftDepartureCard.tsx:343` 前 | 只有拒绝句、没有可挪行时那一块里一颗键都不剩 → 补「重新核实这几段」 |

同代回归：`npx tsc -p tsconfig.check.json --noEmit` RC=0；`e2e/revolution-draft-preparation.spec.ts`
3 passed (13.9s)；后端聚焦 **86 passed**（47+39），宽面 129 条里 15 枚红经父代对照臂证明早于本刀（§58）。

## 2. USER_CLICK_PATH（真实 Chrome，无假 DOM、无 API 代按、无 localStorage 预置）

冷首屏 → 输入那句两天两人步行 1 公里的话 → 「继续规划」→「对话」→ ⚙ 勾两项许可 → 发送 →
研究 → 「跳过/回答」→ 草案卡 → 「保存为正式候选方案」→「票价没有来源，我接受先不计入预算」→
「核实并冻结今天的转场」→「刷新方案」→「选用这份方案」→ **「确认方案，开始行程」**
（`HIT start-fallback-… true`，走的是中心命中测试）→ 出发。

## 3. 同号收据（journey / task / candidate / plan / ACTIVE 同一趟）

| 形状 | journey_id | task_id | plan_version_id | 出发读数 |
| --- | --- | --- | --- | --- |
| 390×844 | `5180b857-e1d2-47fb-b31c-f5b86023247a` | `214f5e61-8f82-4c4d-bd8d-ef503d125ee6` | `10cf2ebb-8837-456e-8e42-e3acf259a426` | `departure/commit 200` → `start 200`，屏上「行程执行中」 |
| 430×932 | `a87c821b-8eec-418b-8ccf-0888d5581cdd` | `8ac475d1-d48f-4fa0-958d-ce7d952ec4b0` | （同屏 `5 项/8 项` 见收据） | `start 200` 同上 |
| 漂移腿 390 | `0ff63e58-53d5-41a7-812c-5920c16d031a` | `f495676e-c976-4b85-a7ef-a1bf91f2e587` | `ccd05664-e21a-483d-b4f7-226094e9424f` | 出发门被我自己那一改挡住（见第 6 项） |

收据文件：`trial/results/20261026_gozero/go-active-390-r57.txt`、`go-active-430-r57.txt`、
`drift-check-390-r62.txt`、`plan-open-hand-390-r53.txt`、`go-active-390-r55.txt`、`drift-check-390-r61.txt`。
令牌一律不落文件（bearer 只在浏览器 sessionStorage，屏证里没有 Authorization 串）。

## 4. 截图（本件提交时一并入库）

390：`390-g7-started-fallback.png`、`390-g8-map-preview.png`、`390-g8-map-loaded.png`、`390-g8-map-reloaded.png`
430：`430-g7-started-fallback.png`、`430-g8-map-preview.png`、`430-g8-map-loaded.png`、`430-g8-map-reloaded.png`、`430-r54-plan-blocked.png`
另 `390-r53-no-workbench.png`（身份丢失那一屏）已在库。

## 5. 真实工具调用状态与供应商来源

`/map-places` 现读响应（收据 `RELOAD_MAP_READS`）：`candidates:5`（390）/`candidates:8`（430），
每枚 `origin:"PLAN_ACTIVITY"`、`coordinate_system:"WGS84"`、`region_status:"MATCHED"`、
`selection_state:"READY_FOR_NATIVE_PLAN"`；`GCJ02` 在两枚收据里命中 0 次 ⇒ 没有原始高德坐标被画上 OSM。
署名分家：高德来源的点写 `© 高德地图（AMAP）` 且给「在高德地图打开 ↗」，OSM 来源给「查看地点来源 ↗」；
两档 `MAP_AMAP_LINKS` 与活动数一致（5/8）。

## 6. 失败与刷新路径（实测，不是设计意图）

- 刷新：两档都在 reload 后读到同样的 `N 处 / N 计划标 / N 列表项`（`RELOAD_*`）。
- 出发门拒绝：`departure/commit 422 … INSUFFICIENT_TRAVEL_GAP:real-place-00d9e27c…|real-place-62c2e606…`
  —— 成因是我把晚餐结束时间 20:00→20:30；屏上句点名该挪哪一边（`departureGaps.ts:346-348`），
  而我的臂没照做，改成把拒绝句发回 Agent，所以这一格只证到"门说得清"，未证到"旅客能自救回来"。
- 身份：关浏览器后 `TRIPS 行程` 给「这台设备上还留着「北京」这趟行程，这次打开没有登录到它，所以读不到进度」，
  旁边只有「课堂演示：进入示例行程开始探索 →」，没有"回到这趟行程"的门（#332，待裁）。
- 模型方差型阻塞：`prepare-plan 422 PLACE_NOT_IN_GOAL_TASK_SCOPE`（O 臂 13 拍）与 `409 prepare-plan`（H 臂）
  都真实出现过，新句已落线但**该屏未再见** ⇒ 标 NOT-STARTED。

## 7. KNOWN_BLOCKERS（照原样挂着，不粉饰）

1. `rev-plan-open-place-explore`（`0188ebd5f4`）与范围拒绝新句（`c160a9cea3`）的屏证 —— 要等各自阻塞形状
   在真机再现；不能预置。
2. 430 与 390 的 ACTIVE 读数取自「尖 + 三枚他人未提交的 `frontend/src/app/*`」工作树，同代性带此保留
   （§59），闭法见 #339。
3. 平板 `USER_VERIFIED=PENDING`：要主人真机走一遍，我不代按。
4. 课堂随机城市池仍 0/3；冻结公交事实 `route_geometry=[]` 那格未变。
5. ~~「和 Agent 补齐出发资料」之后，被拒的方案没有"应用这一版"的可达键（#336 的分辨仍未跑成）。~~
   **10-29 已结（两代各走一趟真机）**：出发门报出缺口之后，「根据路线重新安排」与「按这一版安排」都挂着、
   看得见、点得中，按下去服务端真的一次 `prepare-plan 201` 并换出一份新候选（生效那份未变，卡上就这么说）。
   收据 `trial/results/20261026_gozero/bf110-replan-apply-full-chain-430-r4.txt:75-81`（代次 `ea51658c9a`＋我把
   两枚前端文件带进那一代，已复原）与 `bj115-named-sentence-tip-generation-430.txt:74-99`（代次＝现尖
   `dea0328e0b`，用 `E:/_cmdr_tip_113` 零 dirty 工作树新起的一栈 :60364/:14464）。账见报告 §12.1、§12.2。
   中途另有一拒改了口径：真机上先撞到的是 `409 PLACE_NOT_IN_JOURNEY_CITY`（那一趟六槽里有一处地点登记在别的
   城市池），这条的处置见第 5a 条与 §11。
5a. 那一拒的说法已经修到能点名（门挂 `reason_code` + 哪一项 + 哪一处 + 两个城市码，卡片按 `reason_code` 先分流），
   后端侧有 `pytest` 三条臂钉住、并把门退回旧版就 2 红为判别证明；**但它的话术本身还没有屏上证词**：
   后面两趟链都没再撞见这一拒，不可预置，也不该预置。见 §11.3、§11.4、§12.4。
6. 15 枚后端红（`test_sol_concurrency_and_remap` 9／`test_qoder_live_replans_endpoint` 5／
   `test_dsh_list_replans_bound` 1）经同代对照臂证明早于本刀存在（§58），归属待裁。
7. 新句子「第 N 项…记在另一座城市的清单上…改时间没有用」只有代码级与 details 级证据，**还没有屏上证词**。
   原先卡在"要重启 :60362 会丢掉环境里的高德键"这一点上已经解开：不必重启那台，
   现尖可用 `trial/human_walk/_boot_rescue_stack_r113.py` 另起一栈（键只从进程环境继承，脚本只印 True/False）。
   剩下缺的是那一拒自己再现（§12.4）。
8. `frontend/tsconfig.check.json:16` 的 `include` 只有 5 枚具名文件，不含 `trial/mobile/DraftDepartureCard.tsx`
   与 `departureGaps.ts`，CI 的 `Typecheck current V3 product` 步骤同样看不见这两枚文件的引用错误
   （`e351f5089c` 那半条改动就是这样被"clean"放过去的，修复见 `5182018dab`）。宽配置
   `tsconfig.typecheck.json`（`src/**/*.ts(x)`）在修好的树上退出码 `0`。要不要把窄配置扩到这两枚文件，
   是别人正在写的表面，要点名后由主人或该文件写者决定。
9. 第 2 刀 2a 三件，各交各的账（报告 §13.1–§13.3、§13.6）：
   事件时间线已上屏 —— 折叠、可按开、八十行服务端记录，屏上没有私有文本
   （`trial/results/20261026_gozero/bk116-agent-tool-timeline-430.txt:47-51`）；
   步骤行的来源披露也已上屏，并与库侧一对一（`bl117-tool-step-source-430.txt:15-21` 对
   `bl118-step-provider-census.txt:4-8`：库里七行带 provider，屏上七行来源；六行有核实状态，屏上六行
   「已核实」；两步全无 provider 的不挂来源行）。
   **仍欠两格**：接受键旁的差异在码里有「费用：未知」分支
   （`frontend/src/trial/mobile/ClassroomPresenterPanel.tsx:307-308`、
   `frontend/src/trial/mobile/DraftDepartureCard.tsx:376-377`），但屏上证到的那次读的是「费用：不变」，
   未知那一格没有证词（要一条真算不出总价的候选，不可预置）；r117 只走 430×932 一档，390×844 同格未量。
10. 现尖验证栈 `E:/_cmdr_tip_113` 仍携带一枚外来文件 —— `WorkspaceActions.tsx` 是 `599ed95b76` 的那枚
   blob（`82a158d91bf0…`），其余仍是 `dea0328e0b`；这是屏证的前提，也是要还原的偏差，还原一行：
   `git -C E:/_cmdr_tip_113 checkout HEAD -- frontend/src/trial/mobile/WorkspaceActions.tsx`。
   另自报：本班两次 `git commit` 漏带 pathspec，把同一写者的二十二条前端暂存条目卷进我的提交信息底下，
   两次都 `git reset --soft` 退回并按路径重打（他人 index 每笔之后仍为二十二条），并把这条装进门
   `trial/human_walk/_cmdr_pathspec_commit_gate_r119.py --selftest`（三格真跑：对照组确实吞、门确实不吞、
   ROOT 深度、点名不存在的文件即拒）。见报告 §13.5。
11. 第 9、10 两条各销掉一格，另有一格新张（不动旧正文，只在此补账）：
   一、第 10 条那枚临时携带**已复原并现读回验**：`E:/_cmdr_tip_113` 的 `git status --porcelain=v1` 为 0 行，
   `WorkspaceActions.tsx` 的 blob 从 `82a158d91bf0…` 回到 `74019c5573ab…`（`dea0328e0b` 同代），vite 仍回 200。
   二、第 9 条「390×844 同格未量」**已闭**：臂 bn122 在同一栈另一空库上按开了步骤时间线，屏上六行来源
   （`trial/results/20261026_gozero/bn122-tool-step-source-390.txt:20-22`），只读探针数到该旅程存表八条、
   其中六条带 provider 与核实状态（`bn123-step-provider-census-390.txt:4-7`）—— 六对六。
   三、新张的一格来自第一次 390 尝试（臂 r121）：那一轮十五步、来源行落在 y=1204（844 高视口之外），
   且按 summary 之后读回仍 `open=false`；查明是尺把 click 的拒绝吞了（修在 `9a559d6c78`），
   因此**不给产品定性**，但也据此记下：还没在「步数多到 summary 自己落到视口外」的形状下按成过一次。
   「费用：未知」那一格仍无证词。账见报告 §13.7 与 #344。

## 8. 纯净树上的账（截至 2026-10-28 晚 · 报告 §74–§82）

核对时代码尖为 `bbfb03f6dd037138c087d945d18352b87a952162`；屏证全部来自零 dirty 的第二棵树 `E:/_cmdr_clean_1028`
（`git status --porcelain=v1` 现读 0 行，与现尖之间 `backend/frontend/contracts` 差异为空）。

| 单 | 结论 | 凭据（现读） |
| --- | --- | --- |
| #339 同代性 | **闭** | 390 走到「行程执行中」：地图 6 处＝计划点标签 6 枚＝地图列表 6 条＝库 `activities` 6 条；journey 状态 `ACTIVE`（§74） |
| #340 重存链 | **屏证到位** | AM/AN/AO 三臂同拍 `*_RESIVE_KEY 1 enabled=true`，按下去服务端真重生成候选，并把「赶路时间不够」从 2 段报成 1 段（§80–§82） |
| #337 430 尾格 | **闭**（§83，`27675e27d3`） | AP 臂在零 dirty 树上走到「行程执行中」：库现读 journey `4c6ff80b…` 状态 `ACTIVE`、`active_plan_version_id=d8f29fe8…`、`activities` 6 条＝屏上「地图地点 6 处」＝计划点标签 6 枚＝地图列表 6 条。同一趟 `AP_REFUSAL_SEEN false`，故本节不抵消 AO 那 1 段（下表裁语事实仍挂着） |
| #283／#330 裁语 | 事实已交 | 选用门查营业时间缺口（`services.py:776-782` → `UNRESOLVED_ACTIVITY_FACTS`）而出发门不查；430 这一趟另有可行性拒绝（赶路 1 段）。两方向（放宽选用门／出发门补校验）不代裁（§75、§82） |
| 十五枚后端红 | 具名清单已交 | 现尖重跑宽面 129 条：`test_sol_concurrency_and_remap.py` 9、`test_qoder_live_replans_endpoint.py` 5、`test_dsh_list_replans_bound.py` 1，与 §58 同名同数 ⇒ 本夜刀零新增红（§76） |
| 平板 | 仍 `USER_VERIFIED=PENDING` | 需主人亲自走一遍真机，未做任何模拟替代 |
## 9. 代次续记（10-29 凌晨）：#340/#341 结案、2a 归别人在飞、409 一格改为"有依据的取不到"

**权威线**：`rescue/v3-final-departure-20261022` 现尖 `3ae3fd1878`（远端 `git ls-remote` 回读同枚）。本段之内的提交依次为 `3a11fb144d`、`97577718cd`、`f7bba7a6d0`、`11a07d8f2c`、`0e8b7364ea`、`e598eade8a`、`641da56b8d`、`3ae3fd1878`，另有尺与门禁两笔 `dd7d4abd48`、`2af5efac60` 与臂脚本 `3d888949e2`、`79c2f87606`、`96c966780e`、`87e983348e`、`4cdb80d984`。**产品字节改动：0**（本段只动 `trial/`、`.github/workflows/` 与报告）。

**干净代次现场**：`E:/_cmdr_clean_1028` 已从 `840534ec11` 切到 `ea51658c9a`，`git status --porcelain=v1` 计数 0；后端 `:60362`、前端 `:14462` 全程 LISTENING 未断；canary 库 `E:/_cmdr_clean_1028_data/citynexus_v3_clean_1028.db` 与一次性 profile 逐跑独立。

**这一轮结掉的单**

- **#340（「重新准备方案」那一按的真链屏证）→ 已闭**。bd106 在 430×932 真 Chrome 上：勾「按以上时间准备方案」（`was=false → true`）→ `key_disabled` 由 true 翻 false（`fieldset_disabled` 恒 false）→ 两次按下都成功，服务端 `prepare-plan 201`、`prepare-plan 201`，**4xx 计数 0**；屏上「已保存 6 项正式安排」，按钮改名「按以上时间重新准备方案」。泄漏三档 `api_in_body / api_in_band / uuid_in_band` 两轮全 false，`FINAL_CLEAN true`。收据 `trial/results/20261026_gozero/bd-confirm-then-press-430-r106.txt`，截图 `430-bd-after-press-1.png` / `-2.png`，报告 §105。
- **#341（量「保存为正式候选方案」的挂载条件）→ 已结**。条件不是层、不是轮次、不是标签，而是**一枚必须先勾的确认框**；同一枚键有三种标签（`DraftDepartureCard.tsx:324`：`busy` → 「正在保存安排…」、有 `result` → 「按以上时间重新准备方案」、否则 → 「保存为正式候选方案」），我早前的探针只搜第一种，因此连错九跑。报告 §101-§105。
- **裸错误上屏这一族**：源码侧 7 支口全走 `travelerErrorMessage`；尺带**实物历史对照**（`840534ec11` 旧文件体命中 7 处、现尖 0 处）并已挂进 `v3-rescue-release-gate.yml` 的 `assistant-screen-text`，外读证据是 run 40685781818 的两步 **success 而非 skipped**（浅历史会 rc 7，故 `fetch-depth: 0` 是承重件）。报告 §93/§94/§97。
- **#332 补硬事实**：冷开时行程屏 7 扇门、我的屏 5 扇门、3 枚 `<summary>` 同名「AI 已配置 · 未验证」，**没有登录/认领/再认证任何一扇**；行程屏自己说「这台设备上还留着「北京」这趟行程，这次打开没有登录到它，所以读不到进度」。这是逐门量过的负结论，不再是"找不到"。报告 §93。

**没结的、以及为什么**

- **「旅客在真 409 上看到哪一句」→ 从"未证"改为"有依据的取不到"**：这条路径两次按下都是 201，不再产生 `GOAL_TASK_REQUIRES_DRAFT_JOURNEY`；剩下的 409 入口（轮次 WORKING 时 `resume`）被 `WorkspaceActions.tsx:512` 与 `<fieldset disabled>` 双重挡住。所以 `travelerError.ts:7` 的 `GOAL_TASK_ALREADY_RUNNING` 句子是**状态滞后兜底**，正常点击路径按不到。我不拿"没触发"冒充"看到过"。
- **#342（2a 可展开工具时间线）→ 归别人**：HEAD 上 `AgentRunRail.tsx` 仍是 27 行扁平 `<ol>`（0 个 `details`），但工作树里有 19 增/11 删的未提交实现正把它变成 `<details data-testid="agent-run-timeline">`。我不在别人的在飞文件上叠改动。
- 其余照旧：#283/#330 两道门的裁语、平板 `USER_VERIFIED`、课堂随机城市池 0/3、六枚后端红的归属、#331 账本镜像 401、#333 裸路由仍回 200 的观察项。

**本轮新增的量具纪律（都付过学费）**：派生脚本时收据名、截图前缀、profile 目录三样必须一起换（`ba103`/`bb104` 因沿用 `az102` 的 profile 造成一页两跑与撞锁，§104 已披露）；判"功能不存在"要同时看 HEAD 与工作树并指名代次（§106）；`node --check` 不解析未定义标识符、`grep -c` 的 0 是计数不是退出码、`tail -2` 会截掉崩溃栈——三处都改成显式读数后才拿到真因。

## 9. 本班完成审计（2026-10-29 凌晨 · 代次 `d45c5f3250`）

三刀逐件，每件只写看到的与没看到的：

| 件 | 状态 | 凭据（本班现读） |
| --- | --- | --- |
| 刀一 · 两档真实 Chrome 从空白走到 ACTIVE | 已交（前班） | 390 走到「行程执行中」且地图 6＝库 6（§339 闭，`#339` 行在本件第 8 节）；430 同代另有一趟（报告 §12.1） |
| 刀二 2a · 可展开的 Agent 工具时间线 | 已交 | 事件线八十行可按开、无私有文本（`trial/results/20261026_gozero/bk116-agent-tool-timeline-430.txt:47-51`）；步骤行来源披露在两档各证一次并与只读探针一对一（`bl117…:15-21` 对 `bl118…:4-8`；`bn122…:20-22` 对 `bn123…:4-7`）；长页面形状滚后可按（`bo128…:20-23`）；代次负对照 `bo128-generation-ticket.txt:1-3` 与 `bo128…:16` |
| 刀二 · 新旧差异摆在接受键旁 | 码在两处，屏上一格未证 | 出发卡 `DraftDepartureCard.tsx:376` 紧贴 `:377`；课堂面板 `ClassroomPresenterPanel.tsx:307-308` 两枝都写「未知」；本档证到的是「费用：不变」那一枝，**「费用：未知」仍无证词**（#344） |
| 刀二 · 接受后主动刷新 | 已交（前班） | 整链 confirm→promote→freeze→replan→按这一版→`prepare-plan 201` 在两代各走通（`bf110…-r4.txt:75-81`、`bj115….txt:74-99`）；地图 6＝计划点 6（#335） |
| 刀三 · 课堂手册过期断言与 QUICK_CARD | 已交（前班） | 本档未再动课堂线，未新增读数 |

门禁与门的原话（都是本班内取的，不是沿用的）：

一、宽面类型检查 `frontend/tsconfig.typecheck.json` 覆盖 `src/**/*.ts(x)`，退出码 `0`（回执`trial/results/20261026_gozero/r133-typecheck-broad-receipt.txt:1-4`，其中带测量时的尖 d45c5f3250 与被检文件的 blob 82a158d91bf0）；窄配置只含五枚具名文件的盲区已写在第 8 条，未擅自动。
二、走查臂互不污染尺 `trial/human_walk/_arm_collision_ruler_r108.py`：`SELFTEST_OK`、`ARMS files=315 … COLLISIONS 0`。
三、提交门 `trial/human_walk/_cmdr_pathspec_commit_gate_r119.py` 三格自测在 GitHub runner 上印出`ROOT_ARM True` / `COMMIT_PATHS 1` / `FOREIGN_STAGED before=1 after=1` / `SELFTEST_OK …`（`trial/results/20261026_gozero/r130-ci-gate-step-proof.txt:10-13`，run `40756205676` 步号 7）。
四、发布门两代 `4d5895d89e`、`4d1eee472a` 的 backend / frontend-build / screen-text 三个 job 全 success；`dc7b5e6d5d` 那一代被并发取消（`cancel-in-progress` 的形状），所以那步的原话只认上面那一条。

    "本班的写动作全部可取回：十笔提交 `599ed95b76`、`bebdf21b72`、`95997901dd`、`fb63b625f2`、`9a559d6c78`、

    "那十枚不是墙上的说法：逐枚 `git cat-file -t` 现读都是 commit；拆笔重打后的 `bebdf21b72` 经 `git merge-base --is-ancestor` 判在 HEAD 祖先链上，"且 `git branch -r --contains` 显示 `origin/rescue/v3-final-departure-20261022` 已含它；它带五个文件，就是 r116 那笔。原本要在这里写一条「坐标取不回」的勘误，'
    "是测量把它推翻的 —— 它根本没丢。这段留下来当凭：报告 §13.5 的那个 sha 是有效坐标，不需要勘误。",
没做的事，直说：

一、整套后端测试本档没有重跑 —— 本班没改后端，代次级后端读数来自 CI 的 backend job；第 6 条那十五枚红的归属仍待裁，没有把它算成已修。
二、平板 `USER_VERIFIED` 仍是 PENDING，主人真机走过之前我不代按。
三、课堂随机城市池仍 0/3；冻结公交事实 `route_geometry=[]` 那一格未变。
四、`#283`、`#312`、`#330`、`#333` 等裁语未落，`#331` 镜像腿的 401 未修，`#332` 重启身份恢复仍未做（本班两次靠「另起一栈」绕过它，那是绕行不是修）。
五、e2e 套件未跑：权威口径要 `npm run dev`，dev 数字不算交付证据，跑它只会多一张不可比的表。

