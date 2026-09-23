### 🔬 aad2d1f2 (SESSION=aad2d1f2) P3 · **ORD-0262 `DUPLICATE_RAPID_SUBMIT_RETURNS_500` 定形（只测不修）** @2026-09-23T16:1x–17:1x+08

**一句话结论**：500 的自变量不是"重复"，也不是"间隔"，而是**同一时刻有几个写事务叠在一起**；两发跨 journey 的普通提交（各点一次，POST 相隔 49 ms）就能打死一发，而同 journey 的同刻双击（相隔 65 ms）两次都 200。标题里的 "duplicate rapid submit" 只是最容易凑出并发的一种手法。

**现场（可复放，逐条是实测不是推断）**
- 后端：`D:\moodle\_qoder_cmdr_gate_20260921` @ **`53fe8e86920aed0ddb5fb325f070b4ed8210b686`**，`git status --porcelain` **0 行（干净）**，跑在我的 `:8424`，库 = `D:/moodle/_lane_aad2d1f2_livecopy.sqlite3`（我自己的副本，未碰 `_live.db`）。⇒ 与手机线钉的是同一枚后端 sha，`REPRODUCED(tree)` 成立。
- 前端：`:8476` = 控制代 **`index-CrAwWm5f.js`**（15:53 换代后它就是"上一代"，见文末坐标更正）（1,234,802 B，sha256 `9fd89456daf12bca…1536`，`git archive f5a6b9a` 导出构建，与已发布 canary 包逐字节相同）。
- 仪器：R0a–R0d = 真触摸点击（390×844 / hasTouch）；R1–R7 = 页内 `element.click()`（同 tick 双击只能用这个，两次真触摸做不到同一 tick）。

**1) 几次重复、间隔多少**

| 轮 | 形状 | POST 实测间隔 | 结果 |
|---|---|---|---|
| R0a | 同 journey 真触摸双击 | 6 ms | 200, 200（2 行 mission） |
| R0b | 另一个 journey 的同刻双击，与 R0a 同时在飞 | 30 ms | **500, 500**（0 行 mission） |
| R0c | 两 journey 顺序提交 | 4,412 ms | 200, **500** |
| R0d | 两 journey 相隔 70 s | 70,427 ms | 200, 200，中间另有一发 **500** |
| R1 | 两 journey，点按差 1,031 ms | **109 ms** | 200, 200 |
| R2 | 两 journey，第二发正好落在第一发的 run 窗口内 | 21,023 ms | 200, 200 |
| R3 | **单发**（其余页 idle + 15 s 余量） | — | 200 |
| R4 | 同 journey 同 tick 双击（点按差 1 ms） | 65 ms | 200, 200 |
| R5 | 两 journey 各点一次 | 49 ms | **500**, 200 |
| R6 | 同上（第二下都撞到 `disabled=true`） | 90 ms | 200, 200 |
| R7 | **3 journey × 同 tick 双击 = 6 发挤在 287 ms** | 6 发 | **500 × 3**，每一对恰好输掉后发那一腿（3/3） |

⇒ 没有"间隔超过 X 就安全"的门槛：49 ms 死过、65 ms 活过、21 s 活过、70 s 也死过。**并发写事务的个数**才是：1 发 → 0/1 红；2 发并发 → 0–1 红；6 发并发 → 3/6 红。
⇒ 整条车道日志的分母（我这一个后端进程，10:27→17:0x，收据发布时现算）：`POST /agent/commands` **45 × 200 + 14 × 500 = 59 发，23.7% 红**（R 系列读数当时是 39 发 / 10 红 = 25.6%，我把两个时刻都留下，不覆盖）；旧端点 `POST /plans/generate` 另有 2 × 500（同一根因的另一条路）。

**2) 500 的响应体有没有可读理由：没有**
- 状态 500，`content-type: text/plain; charset=utf-8`，正文恰好 **`Internal Server Error`**（19 字节）。**无 JSON、无 `detail`、无机器可读码、无 trace/request id。**
- 前端 `PlanWithAiSheet` 依次找 `body.detail` → `body.error.message`，都拿不到，于是落到自己造的 `` `HTTP ${response.status}` `` 字符串——屏上「技术详情」里那行 `<code data-testid="plan-ai-reason">HTTP 500</code>` **是客户端自造的，不是服务器给的**（控制代还没有归属标签；新代那行上面挂着「服务器给出的原因」这个标签，会把这句客户端自造的话冒充成服务器口径 —— 这条与 09-23 手机线那条同源，读数在此固定下来）。
- 卡片原文（截图 `ord0262_A_0810_http500_card.png`，sha256 `b59afe26…2a69`，67,902 B）：
  `data-result-status="HTTP_500" data-result-tone="warn" data-plan-count="-1" data-new-plan-ids=""` → 「**服务端处理失败** / 这次是服务端出错，不是你的需求有问题。行程未被改动，可稍后重试；反复出现请保留“技术详情”。 / 技术详情 → `HTTP 500`」

**3) 是否总落在同一 journey：不是**
`ae79fbf1`、`e168580c`、`94669bae`、`cc5e67c4` —— 4 个 journey 都既红又绿，R7 里同一个 journey 一腿 200 一腿 500。输的是**抢不到写锁的那一腿**，与身份无关。**最终整段分母按 journey 拆**（`receipt.log_tally.agent_commands_per_journey`）：ae79fbf1 24/7、e168580c 8/3、94669bae 2/3、cc5e67c4 3/1 **红过**；51929591 6/0、c10df843 1/0、1e525047 1/0 **没红过**（后两枚各只 1 发，不算反证）。

**4) 失败点在哪（从 traceback 帧读，不是猜）**
硬失败（收据发布时 **20 次**，R 系列快照时 16 次）= **17 × `INSERT INTO journey_missions`**（`app/main.py:1121 run_agent_command` → `app/agent/mission.py:537 create_mission` 的 `session.flush()`，异常未捕获 ⇒ 冒成 500）+ **2 × `INSERT INTO plan_versions`**（`app/services.py:1631 generate_plans`，**发生在返回 200 的请求里**）+ **1 × `INSERT INTO agent_runs`**（`app/main.py:1227` → `app/agent/runtime.py:342`）。
**同一根 contention 的另一面**：`UPDATE journey_twins` 撞锁被 `app/main.py:5911` 捕获、只 warning 一句「cache write skipped during transient SQLite contention」——本车道 **390 次软跳过 vs 20 次硬失败**。同一个库、同一种锁，一处降级一处抛穿，这就是不对称所在。
**不平滑的一处对不上**：17 次 mission INSERT 抛穿 vs HTTP 层 14（agent/commands）+2（plans/generate）= 16 个 500 ⇒ **多出的 1 次没有对应的 500 访问行**（可能是后台线程里抛穿、或访问日志与 traceback 的先后差）。我按原样报，不改数凑齐。

**5) 比 500 更贵的两件事（都在 200 里）**
- **落不回去的备选**：`INSERT INTO plan_versions` 在 run 内抛穿，而请求仍是 200。两次硬失败逐枚回读库（不是数总数猜的）：
  - `ae79fbf1 v10`（参数里的 id `42325086…`）抛了，但**同一枚 id 后来在库里**（`created_at=07:55:21.931`）⇒ 这一条被后续写入救回，我不算它丢。
  - `e168580c v22`（id `2ad35721…`）**库里没有**，且该 journey 的 `version_no` 序列是连续的 1..21、max=21 ⇒ **版本号被消费掉而行没落**，这一枚是静默丢失。
  ⇒ 所以别用"200 就等于全落"这句口径；一条 200 后面可以少一行，也可以被补回来，两者都在同一枚锁上发生。
- **孤儿 mission**：`agent_runs` 插入失败（`app/main.py:1227` → `app/agent/runtime.py:342`）⇒ journey_missions 里留下 `5a2726ff`（`status=CREATED`，`created_at=08:06:10.068`，**关联 run 数 0**，全库唯一一枚 `CREATED`，44 mission / 43 run 的差额就是它），而那一腿的 HTTP 结果是 500、屏上写的是「**行程未被改动**」。**这句话在这条路径上不成立**：它已经写了一行 mission。
- 顺带的用户体感读数（同一次 R7）：成功腿阻塞 **43.2 / 58.9 / 78.9 秒**才返回，失败腿 **14.2 / 42.8 / 43.6 秒**才告诉用户"稍后重试"。`app/db/session.py:55` `timeout=30` + `:65` `PRAGMA busy_timeout=30000` 解释了为什么 500 慢而不是快。
- 卡片归属：R7 三个页面**最后落地的卡覆盖了 500 的卡**（终态分别是 PLANS_WITHOUT_AI / PLANS_WITHOUT_AI / NO_PLANS_PRODUCED）—— 一个 sheet 只有一个结果槽，两发并发时"谁说完话"取决于谁后返回。

**6) 最小复现（我跑的这台）**
1. 后端 `53fe8e8`（干净树）+ 自己的 sqlite 库，`CITYNEXUS_AI_ENABLED=true`（让每发 POST 在写库前先停 ~10–20 s，把窗口拉长）。
2. 开 3 个 journey 的规划 sheet（同一个后端即可）。
3. 每个 sheet 内一次 task 里 `b.click(); b.click();`（同 tick），三个 journey 连着做，6 发会挤进 ~300 ms。
4. 期望：约一半返回 `500 / text/plain / "Internal Server Error"`，耗时 14–44 s；每对的**后发那一腿**输；库里可能出现 `CREATED` 孤儿 mission；200 那一腿也可能少落 plan 行。
   单 journey 版（09-23 上午已复现）：另一 journey 的同刻双击在飞时提交 → 两腿全 500、0 行。

**7) 归属建议（读数给方向，判级归你）**：后端。触发面是「POST 前的最后一次 flush 没有重试/翻译」，与 `main.py:5911` 已有的软处理是同一把锁；和仲裁预留的 **ORD-0253（幂等键）**是否同根我只说可能性：幂等键能挡住"用户自己重复提交"这一类流量，挡不住 R5/R6 那种**两个 journey 各点一次**——那条路幂等键不在场。

**8) 顺带纠正我 ORD-0257 的一处口径（自翻）**：我当时写"控制代同刻双击能出 2 发 POST"，容易被读成"随便快点两下就会重复提交"。R6 实测：**同一个 task 内连点两下 → 2 发；隔 7 ms 的第二下看到的是 `disabled=true` → 只有 1 发**（`{click_1_disabled:false, click_2_disabled_7ms_later:true}`）。也就是说控制代的漏口只有一 tick 宽，**ORD-0246 的反例臂必须打在"同 tick"上，否则控制组自己就不会红**。（这一 tick 在新代是否真被堵住 —— 见下面第 10 节 P0–P3：**4/4 轮 2 下只出 1 发**，已闭。）

**9) ②a：同条件重复 6 轮，报完整分布（不报平均）** —— 面 = **上一代** `index-CrAwWm5f.js`（`:8476`），单 journey `ae79fbf1`，同 tick 双击，轮间用 sheet 自己的 busy 标志分闸
| 轮 | 两下点按 | POST | 结果 | 后发腿耗时 |
|---|---|---|---|---|
| Q1 | 同一 ms | 2 | 1×200 + **1×500** | 61.8 s |
| Q2 | 同一 ms | 2 | 2×200 | 106.6 s |
| Q3 | 同一 ms | 2 | **1×500** + 1×200 | 12.0 s(500) |
| Q4 | 同一 ms | 2 | **1×500** + 1×200 | 12.6 s(500) |
| Q5 | 同一 ms | 2 | **1×500** + 1×200 | 21.9 s(500) |
| Q6 | 同一 ms | 2 | 2×200 | — |

分布（6 轮 / 12 次点按）：**点按被吞 0 次；12 次点按 → 12 发 POST**；每轮结局 `{2×200: 2, 1×200+1×500: 4, 2×500: 0, 0 POST: 0}`；POST 层 **8×200 / 4×500**；`agent_runs` 增量 **8**、`plan_versions` 增量 **9**。**输的 4 次全是后发那一腿**（与 R7 的 3/3 同形）。
对账（不是我算平均，是三处独立读数互相咬合）：后端访问日志 `200 34→45`、`500 10→14`（Q+P 合计 15 发 = 11×200 + 4×500），traceback 硬失败 `16→20`（**+4，与 4 个 500 一一对应**），库里 mission/run 各 +11（Q 8 + P 3）。
**顺带一枚新读数（不是我要找的）**：sheet 的 busy 标志**没做引用计数**——两腿同时在飞时，先返回的那条把按钮放开成「开始规划」，此时另一条仍在跑（Q2 是在 Q1 第一腿 08:55:59 返回之前的 08:55:33 发出的）。⇒ 我这 6 轮的"轮间分闸"不可靠，**Q2–Q6 不是实验室隔离条件**，只有 Q1 可证明隔离（距上一次活动结束 78 s）。我按实测条件报，不把它说成隔离条件。

**10) ②b：发布代上重跑 ORD-0257 那两格 ⇒ 从"树里验过"升级成"现网验过"**
面 = 我自己的 `:8474`，serve 的就是你 15:53 换上去的两件（`index-DJEINrOl.js` 1,236,190 B / `index-COUUKhbU.css` 183,342 B；与你换代收据 `swap_027d65e_0923_1553.json` 的 `new_index_refs` + `assets_union.already_identical` 同名同字节，那侧 arm `J_name_content_binding` = GREEN）。
- **格 1 双击不再重复生成**（三列判据）：P0 同 tick 两下（08:41:17.086 / .088，两下都看到 `disabled=false`）→ **1 发 POST**；P1（09:01:54.575/.577）、P2（09:02:30.004/.004）、P3（09:03:09.552/.552）同样 **2 下 → 1 发 POST**，`dur` 30.1 / 34.0 s，状态 **200**。⇒ **4/4 轮：POST 数 = 1、`agent_runs` 增量 = 1（不是 2）、非 2xx = 0**。库里 P1–P3 各落 1 mission + 1 run（`9750770e`/`3799b570`/`6e72a007`）。**与上一代 12/12 点按全漏同框对照：这一格是真的换代之差，不是环境之差。**
- **格 2 summary 44px**：`/v8/bookings` 的 `[data-testid="bookings-advanced"] > summary`（「高级：结构化数据」）实测 **311.3 × 44 px**（`line-height:44px`、`min-height:44px`、`innerWidth=390`、dpr≈3），中心点 (195.2, 636) 的 `elementFromPoint` **命中的就是 SUMMARY 本身**（栈：SUMMARY → DETAILS.v8-advanced → ASIDE.v9-inbox），真触摸 tap 把它 `open` false→**true**。截图 `ORD0257B-PUB-1641_published_bookings_advanced_summary.png`。上一代同坐标是 311 × 14（ORD-0257）。

**坐标更正（覆盖我 ORD-0257 里的说法）**：那一场我写的"新代 `index-DJEINrOl.js` / 旧代（canary）`index-CrAwWm5f.js`" —— 15:53 之后应读作 **发布代 = DJEINrOl（= 我当时的"新代"）**，而 **CrAwWm5f 已降为上一代**（锚 `dist_bak_154923_1790149763821685500`）。以后我做反例一律拿 CrAwWm5f 当"旧形"，不再把它当现网。

**caveats（不藏）**
- 背景写压力：R 系列（重启前）我这一个 Chrome 里同时挂着 **7 个 hub 页**在轮 `/twin`；Q/P 系列（软件重启后）我重建的是 **2–3 个页面**（`:8476` + `:8474` 各一，另有一只在 `:4411` 是别人的车道，我没驱动它）。两段的**背景写压力不同**，所以 25.6%（R 段整体）与 4/12（Q 段）不要互换外推，更不要当手机上的发生率；形状（哪条语句失败、响应体长什么样、后发腿输）两段一致。
- R3"单发不红"只有 **1 次**试验，不足以下"单发安全"的结论，只能说我没复现出。
- 这些 run 大多以 `FAILED_EXTERNAL / DeepSeek Agent completion failed` 收口（那把待撤销 key 的老问题），run 时长与写窗口因此偏长；AI 正常时形状未测。
- 未修任何产品码、未 `demo/reset`、未碰 `_live.db`/`_preview.db`/`:4781`/`:4782`/`:8693`；写只发生在我自己的库和 `commander/control:evidence/ord0262/`。

**外读坐标**：`Canshu-King/CityNexus @ commander/control` → `evidence/ord0262/`，逐件 GET 回读 40 位 git blob sha1 ＋字节数（见同目录 `MANIFEST.txt`）。文件：`ORD0262_RECEIPT.md`（本块）、`receipt_ord0262.json`（**所有计数由 `measure_ord0262.py` 从日志/库里现算**，含 20 次硬失败逐枚的语句/参数/帧）、`measure_ord0262.py`（那把尺本身，可复放）、`rounds_capture_ord0262.json`（R 系列浏览器原始逐发记录）、`qp_capture_ord0262.json`（Q/P 系列逐发记录＋发布代身份论证）、`backend_contention_extract_ord0262.txt`（硬失败的 SQL/参数/帧原文）、`ord0262_A_0810_http500_card.png`（500 卡）、`ORD0257B-PUB-1641_published_bookings_advanced_summary.png`（发布代 44px 那一格）。
**保留树不清**（按令）：`_hjp3_ord0257_0923/` 与本轮 `_hjp3_ord0262_0923/` 都留着当控制组现场，其中含指向 `frontend/node_modules` 的硬链接。
