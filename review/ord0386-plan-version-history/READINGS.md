# ORD-0386 · 版本可预期性第一步：只列历史版本 + 明说保留上限（不做还原）

车道：Q（ORD-0369 同一车道）· 分支：`review/Q-ord0386-plan-version-history`
起点：`090c048f220a3089506f565929ceda1511315a09`（权威线当时的尖，未移动）
本机所有读数都来自车道自己的导出副本 `D:/moodle/_qoder_q_ord0369_wk/q0386.db`；
`D:/moodle/_qoder_preview_20260920/_preview.db` 未被打开过，`demo/reset` 未被调用过，`:8000` 未被依赖。

## 1. 两件被转达的坐标，先回验再动代码

| 转达的说法 | 现场读数 | 结论 |
| --- | --- | --- |
| 「没有版本列表路由，要新建一条只读 GET」 | `backend/app/main.py:5111` 已有 `@app.get("/api/v1/journeys/{journey_id}/plans")`，docstring 自陈 "Every version this journey has ever had"，且刻意不按 status 过滤 | 路由**不需要新建**。本单真正缺的是投影里没有写入时间：改动前 `backend/app/services.py:609` 的 `PlanSchema(...)` 传了 18 个字段（计数：`re.findall(r'^\s{8}(\w+)=', <该调用体>, re.M)` 作用在 `git show HEAD:backend/app/services.py`），里面没有 `created_at` |
| 「studio 的版本徽标在 `V12TripStudioPanel.tsx:96`」 | `:96` 是 gate-reasons 的 memo 收尾大括号；徽标实际在 `frontend/src/features/studio/V12TripStudioPanel.tsx:195` | 坐标写错，按现场行号引用 |

因为路由本来就有，本单后端只动三处：`backend/app/schemas.py`（`PlanVersion` 加 `created_at: str | None`）、
`backend/app/services.py`（投影带上它）、`contracts/openapi.yaml`（契约声明同一枚字段）。
新增路由数：0，因此契约门的 route/method 分母不变（`tests/test_qoder_anywhere_contract_parity.py` 4 节点通过）。

## 2. 保留上限：量出来的，不是估的

`backend/tests/test_qoder_ord0386_plan_version_history.py` 的 `test_3` 在同一趟上新建行程、
连跑 4 轮 `plans/generate`（每轮 `candidate_count=2`），要求：行数 == 各轮返回候选数的累计、
`version_no` 连续无缝。通过。

同一台部署上另一趟（车道自己造的探针行程 `472c60ae-85e3-4604-88d8-7305d8437f67`，7 轮 × 3 枚候选）
在 sqlite 里的实际形状，`D:/moodle/_qoder_q_ord0369_wk/q0386.db`：

```
select count(*), min(rowid), max(rowid), min(version_no), max(version_no), count(distinct version_no)
  from plan_versions where journey_id='472c60ae-85e3-4604-88d8-7305d8437f67';
-> 21, rowid 10..30, version_no 1..21, distinct 21
select min(created_at), max(created_at) ... -> 2026-09-27T19:35:18.939504+00:00 .. 2026-09-27T19:35:35.421386+00:00
select source, count(*) ... -> INITIAL 21
全库 plan_versions 行数 = 30（另一趟封存演示 `9c6c3d73-8b8e-4f71-beaf-32bc87aba035` 占 rowid 1..9，
其中 8 行带 parent_plan_version_id，journeys.active_plan_version_id 指向 version_no 9）
```

代码侧的交叉验证（不是只靠一次跑数）：`grep -riE 'retention|prune|max_versions|keep_last' backend/app`
零命中；全仓对 `plan_versions` 的 DELETE 只有两处，且删的都是**硬闸门当场拒掉、从未返回给调用方的候选**
（`backend/app/main.py:9781`、`backend/app/operations/v9.py:733`），不是已入档的历史。
所以屏上那句「这台服务器没有设保留上限」是结构读数 + 实测行数，不是外推。

## 3. 屏（不另起外壳）

挂在 authoritative 那一段里，`frontend/src/app/V8Experience.tsx` 的两行改动：import 一行 +
`<PlanVersionHistoryPanel journeyId={journeyId} />` 一行（现尖 `:3374`）。
**位置是这单的一个产品结论**：面板原先挂在 `V12TripStudioPanel` 内，而那个面板只在 `plan` 读到之后才挂载——
于是"列表读失败"整块消失，旅客只剩 `LocaleContext` 的 `auth.noPlan`「你还没有选定方案。」，
把一次没答上的读说成了方案层的判断。现在面板自己持读（React Query 同一 key，不多发一次请求），
不再被 `plan &&` 挡。方向已用变异证明：把挂载移回 `plan &&` 之后，H5 报红（`mutant_kill_table.json` 的 M3）。

文案全部走本车道新建的 `frontend/src/features/studio/planVersionHistoryCopy.ts`，
**没有碰** `frontend/src/i18n/LocaleContext.tsx`（两车道在改它）。
词面只用「历史版本 / 还原」，本屏不出现「恢复」（H4 逐字判）。

一处诚实修正：`MANUAL` 最初被译成「来自一次住宿变更」。现场有两个写入点，
`backend/app/main.py:5715` 写的是行程工作台的活动重排（`product_path = V12_TRIP_STUDIO_ACCEPT`），
`backend/app/operations/v9.py:580` 写的才是住宿驱动的重写。而封存演示那 9 行**全是 MANUAL**，
所以那句错话会真的上屏。现在写成「来自一次人工改动（调整活动顺序或换住宿）」。

`created_at`/`is_current` 在面板里本地声明，没有重生成 `frontend/src/generated/api.ts`：
该文件与当前契约已差 497 行 / 13 个 hunk（量法与逐对象证据见 `api_ts_drift.txt`），
重生成会把别的单的漂移并进本单 diff。

## 4. 门禁与它咬不咬

后端：`tests/test_qoder_ord0386_plan_version_history.py` 6 节点 + 契约奇偶 4 节点 = 10 passed
（`CITYNEXUS_DATABASE_URL=sqlite:///D:/moodle/_qoder_q_ord0369_wk/q0386_gate.db`，全新库）。
整套 `--collect-only`：候选树 1341 条 / 20 个 collection error，
同一台机器上未动的 `090c048f` 归档快照 1335 条 / 同样 20 个 error（错误模块集合逐行 diff 相同，
见 `collect_candidate.txt` 与 `collect_control_head.txt`）；1341 − 1335 = 6，正是本单新增的 6 个节点。
前端：`tsc --noEmit` rc=0，`vite build` rc=0（FRONTSRC_BUILD_PREREQ 已满足）。
e2e：`gate-report-final.json` 7 节点全绿（stats.expected 7 / unexpected 0），
被判的字节是构建产物 `index-Bn2LR9Bv.js`（sha256 前缀 `d8a87094091f58720fff25d1`，
记在 `render_final.json` 的 `served_bundle`），由 `vite preview` 在 `127.0.0.1:4192` 提供，
后端是车道私有 `127.0.0.1:8713`（所有权证明：监听者必须答出只有本副本存在的探针行程，见 runner）。

7 个断点各自判什么、以及**每个断点被哪个变异杀掉**：`mutant_kill_table.json` ——
M1 空时间走格式化器 → H3 红；M2 份数写成字面量 9 → H2 红；M3 挂回 `plan &&` → H5 红；
M4 来源直接输出机器码 → H6 红；M5 只读屏长出一个按钮 → H4 红。5/5 全部被杀，
且每次还原后与还原前逐字节相同（`restored_byte_identical: true`）。
H1 判"真行程 9 行逐条对得上服务器实发"，H7 判 390×844 下每一行都能滚到不被悬浮球/底栏挡住的位置
（hit-test，不是 `scrolled>0`；逐行逐位置读数在 `reachability.json`）。

## 5. 顺手量到并改掉的一处排版

面板首屏有约 110px 的空白把副标题和第一句隔开：`.v8-muted` 自带 16px 上下 margin，
又叠在本段 16px 的 grid gap 上。作用域内清零后 header 从 95px 降到 63px（量法：
`document.querySelector('[data-testid="plan-version-history"]')` 子元素的
`getBoundingClientRect()` + `getComputedStyle().margin*`）。
同时删掉了原先给列表加的 `padding-bottom: calc(var(--cn-nav-h, 80px) + 64px)`：
把它去掉后 H7 仍然绿（单独一次重建 + 复跑，读数存 `mutant_M6_no_list_padding.json`：
stats.expected 1 / unexpected 0），说明那 144px 对"可达"并不承重，留着只是把最后一行和那句解释推远。

## 6. 没改善的部分

1. **不能还原**：这是本单的边界（步骤一不做还原），屏上明说了为什么。
   真正的还原需要"替换正在执行的方案"这条写路径，本单没有开。
2. **`:4781` 上还没有这一屏**：车道无权部署到共享预览链（`:4781/:4782/:8693` 由 E2E owner 操作），
   所以验收 B 是在车道自己的 `vite preview` + 构建产物上读的，不是在线上那一屏读的。
   线上下一步换代后才会带上它。
3. **REPLAN 这一枚来源没有真行**：这台部署上没有任何一趟留有 `source=REPLAN` 的版本
   （ORD-0369 已量过：重规划的接受腿被 422 非硬可用证据与 5/5 受保护锚点挡住）。
   H6 因此只能把真行的 source 改成契约声明的三枚码来判标签，不能算"走了一次真重规划"。
4. **行程工作台底栏仍把机器码写在旅客行上**：现尖 `frontend/src/features/studio/V12TripStudioPanel.tsx:195`
   渲染 `PlanVersion {version_no} · {source}`，实测屏上文字为「PlanVersion 9 · MANUAL」
   （读数存 `D:/moodle/_qoder_q_ord0369_wk/o0386_footer.json`）。它属于 Q64 那一类暴露面，
   但不在本单要件里，且改它要动别的车道刚落地的那段文字——留给号令者定单，本单没碰。
5. **`generated/api.ts` 的 497 行漂移仍在**：本单绕开它（本地声明两枚字段），没有替别的单收拾。
   谁重生成，都会把不属于自己的改动卷进 diff。
6. **列表只到"看得见"**：没有按状态筛、没有分页、没有导出。21 行一次全列，
   真跑上百版的行程会不会太长，本单没量（也没有那样的行程可量）。
