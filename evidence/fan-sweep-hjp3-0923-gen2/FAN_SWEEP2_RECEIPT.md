### 🔬 aad2d1f2 (SESSION=aad2d1f2) P3 · **扇扫第二轮：对象换成 20:08 后的发布代 `d2665e2` / `index-D76m_cky.js`** @2026-09-23T20:3x–20:5x+08

**身份先钉**：部署包 = `index-D76m_cky.js` 1,238,834 B sha256 `270377c83471a5a1…` + `index-I45CQek8.css` 183,897 B `1b3632785212847b…`；换代收据 `evidence/deploy/swap_d2665e2_0923_2008.json` 独立回读 blob **`0aa298042d78d317828e2d33a6a55eeabefe7bff`** 与你给的前缀相等，`overall=GREEN`、arms A/B/G/H/I/J/F 全 GREEN、`temporal_obligations=DISCHARGED`、`new_index_refs` = 上面两件。`:4781` 我只读了 index 文本 ⇒ refs 正是那两件。**我的面 = `:8479`**（同一枚构建：`d2665e2`、`e3b0b47`、`6daceb1` 的 `frontend/src` **tree hash 三者相同** `389c1bd6b4fe25e13a179484ae2207ab32522e5b`，我 build 出的 js/css sha256 与部署值逐字节相同）；**对照面 = `:8474`**（上一代 `DJEINrOl`，仍在盘上）。后端我的 `:8424`（`53fe8e8`，porcelain 0）+ 我的副本库。第 10 格用我自己的两张面：`:8483`→哑 `:8599`（永不回答）、`:8484`→哑 `:8598`（一律 500）。**未碰** `:4781`(除 index 文本)/`:4782`/隧道/两个用户库；0 次 `demo/reset`；0 处产品码。

**A) 你要我特别看的那格：向导 step-1 底部让位（发布后验收）= PASS，没有新陷阱**
| 读数 | 发布代 `D76m_cky` | 上一代 `DJEINrOl`（对照） |
|---|---|---|
| `.trial-steps` `padding-bottom` | **212px**（76 + `--cn-sim-float-clearance` 解析 `calc(136px + 0px)`） | **0px** |
| 「高级设置」静止位置 | y=**929**（视口 844 之外，h=44 w=349） | y=**1142** |
| 可滚范围 max | **623** | **373** |
| 真触摸滑动到达 | **1 次**到 max：入口 y=306、中心 **328** ⇒ 在 sticky 带 628–708 **之上**、`elementFromPoint` 命中自身 | 1 次到底：中心 **810** ⇒ 落在 sticky 带之下、离底边仅 34 px 的贴底缝里才点得着 |
| 真点按 | `.trial-advanced` `open` false→**true**（`.trial-supported` 保持 false） | 同样能开（贴底缝里） |
| 到底后遮挡扫描 | 17 个控件中心逐个 hit-test ⇒ **occluded 0**；最低控件下缘 812、尾隙 **32px** | 同样 0 / 812 / 32px ⇒ **让位没多要吃屏** |
| 可逆 | 反向一滑 scrollTop → **0** | → 0 |
⇒ 新代把入口从"贴底缝"提到"视口内舒适位"，且**没有**引入新的滚动/导航陷阱；两代的尾隙与遮挡计数相同。**草稿态那一维**（我 18:4x 量的）：旧代只要填一个目的地，入口中心就被顶到 **1102 = 视口外、`elementFromPoint` 返回 null**；新代同操作后 1 次滑动即达（中心 396，条带之外）。⇒ ORD-0264 的可达性契约在新代两态都成立。

**B) ORD-0263 那一族 —— 按你的指令标 `NOT-YET-DEPLOYED`，不当回归**
- **永不回答面**（`:8483` + 哑后端 `:8599`）：4 s / 13 s / 22 s 三次读数**一字不变**「CN 正在准备城市周末行程… 锚点 · 住宿 · 出行事实 · 可行性」，`<button>` 数 **0**，无超时、无错误 ⇒ 屏上把"没有答案"讲成"还在准备"。**NOT-YET-DEPLOYED**（B 的候选未落地，与你的预告一致）。
- **答 500 面**（`:8484` + 哑后端 `:8598`）：屏上**不是**「网络不可用」，而是「服务器这次没能把行程读出来 / 服务器自己报错了（HTTP 500）。这是它那边的问题，不是你填错了什么。可以重试；如果一直这样，稍后再来。」+ 归因详情 `attribution_reason=SERVER_ERROR evidence_kind=HTTP_RESPONSE http_status=500 source_layer=RUNTIME retryable=true recovery_action=retry` ⇒ **这条启动路径已经诚实**。你提到的「网络不可用」那一句我这轮**没触发到**（它在别的 surface，纯 500 面下根本进不到 AI sheet）⇒ 我标 **NOT-MEASURED**，不假称看到，也不替它背书"已修"。

**C) 上一轮那 5 枚，在新代重测的结果**
- **N-1 标签标点化：仍在。** 48 张卡实测 **22 张标签不是 `方案 A–Z`**：`方案 [`、`方案 \`、`方案 ]`、`方案 ^`、`方案 _`、`方案 \``、`方案 a…f`。机制未变（`PlanComparison.tsx:178` `String.fromCharCode(65 + index)`；该文件**不在** `027d65e..d2665e2` 的改动清单里）。「生成了 48 个」与 48 行**一致**，问题在标签与区分度，不在计数。
- **N-2 成功后 Today 不刷新：仍在。** 我按一次「开始规划」：卡「AI 没有参与这次规划（生成了 3 个备选）」+ 3 枚 new-plan id；库里该 journey `plan_versions` **9→12**；**同一屏不重载仍写「生成了 9 个可选方案」（cards=9）**。机制未变：`PlanWithAiSheet.tsx:668 if (status === "COMPLETED") onPlanned?.();`。
  - 顺带一枚新事实（给 ORD-0253/0262 用）：**用户一次按下 = 两发 POST** —— `POST …/agent/commands 200 (30.1 s)` + `POST …/plans/generate 201 (72 ms)`，后者才是那 3 行的来源。任何"一次激活一次请求"的判据必须知道这条回退链。
- **N-3 Simulation 面板一条 404 静默：仍在。** `GET /api/v1/city-services/service-food-preorder/booking-slots?start_… → 404`（同一次共 16 条，姊妹 `service-river-cruise-booking/booking-slots → 200`），面板正文对这条失败**零表述**（`has404note=false`）。
- **N-4「没有到期时间 · 没有到期时间」：仍在**（面板正文正则计数 **2**）。
- **N-5 进行中/失败任务无 UI 出口：新代未重测**（我没有把这格再走一遍；两枚落地 commit 未触碰任务列表类文件，但我不拿"源码没改"代替读数）⇒ 记 **NOT-RE-MEASURED-ON-NEW-GEN**，上一代的读数仍在第一轮收据里（mission `216cbd7f` / run `7ff8c262` FAILED_EXTERNAL / 屏上 0 处提及）。
- **由坏变好的一格：空文本按下（ORD-0250 已落地）。** 旧代：按钮硬 `disabled`、**0 提示 0 POST**。新代：`disabled=false` + `aria-disabled="true"`，按下后**屏上出现**「还差你自己的一句话：上面灰色的例子只是提示，不算你说的需求，所以我们没有东西可以拿去排。」（`data-request-length="0"`），**POST 计数不变（0 新增）** ⇒ 从"点了没反应"变成"会告诉你缺什么"。
- 地图 / 钱包：仍**一致**。地图「底图未加载，显示的是路线示意。」与 `.maplibregl-tile=0` 相符；「7 段路程」「未知费用保持未知。」「下一段路程 等待方案」与 8 活动 − 1 / `active_plan_version_id=NULL` 相符；钱包「0 个受保护事实」= 该 journey `commitments` **0 行**（屏上 0、库里真 0）。

**仪器纪律（本轮自查）**：上一轮我撞过"`goto` 抹掉 fetch 补丁 ⇒ 假 0 请求"，这轮**每次导航后重装**；只有钱包那格我 reload 前装了、reload 把它抹掉，于是那一格我**不报请求数**（只报文案与行数）。地图那格第一次我用 `[role=status]` 抓提示抓到空数组，复查后确认提示在（`.maplibregl-*` 之外，`hasNotice=true`）—— 是选择子没覆盖，不是产品丢了表述。

**判定**：A = **PASS（发布后验收）**；B = **NOT-YET-DEPLOYED**（silent）/ **已诚实**（500 启动页）/ **NOT-MEASURED**（「网络不可用」那句）；C = **N-1/N-2/N-3/N-4 仍在**、**N-5 新代未重测**、**ORD-0250 已落地并屏上验证**。
