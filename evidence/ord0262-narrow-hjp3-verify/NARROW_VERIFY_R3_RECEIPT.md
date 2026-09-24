### ✅ aad2d1f2 (SESSION=aad2d1f2) P3 · ORD-0262-NARROW verifier **第三段：N3 / N4 运行时读数到手（四问齐）** @2026-09-24T10:5x+08

**现场（一次性，跑完在脚本里真杀真删，见末尾）**
- 服务端 = 候选 `3093eea773c79fa00744fe72d1f2c43b4d0bd75e`（tree `5ae9f8959b059d04e5a41c53f0b6fa11470b19d0`）起在一次性端口 **`:8492`**；一次性库 `one_time_n34.s3db` 按你给的配方**只重放结构**（`sqlite_master` 里 table/index/trigger 的 CREATE，**92 条 / 55 张表 / 新库 journeys 0 行**），只 seed 我自己那 1 traveler（`4da2eb07…`）+ 1 journey（`b6aad6ba-8177-4eca-9514-8eecb22027c6`）。
- 前端 = **当前发布的那一枚包**：从用户链 `_qoder_preview_20260920/dist` 用 `cp -al` 只读复制成我自己的快照（没动用户链），`index.html` 引用 `/assets/index-ChOTTCvB.js`（sha256 前缀 `2d56a79632ef`），起在一次性 face **`:8493`**，`CITYNEXUS_BACKEND_PORT=8492`。**归属双向证明**：我的行程 `200`、外来 uuid `404`。⇒ 屏是用户会看到的那层，服务器是被测候选那一版。
- 冲突 = `BEGIN IMMEDIATE` + 一条 `UPDATE journeys` 不提交，另挂一个排队写手（让 SQLite 立刻回 BUSY 而不是等满 30 s）。

### N3 · `.plan-ai-reason` 必须等于服务器 `message`，屏上不得出现客户端自造的 `HTTP 500` —— **成立（运行时）**

浏览器那一发（点「开始规划」）：`POST …/agent/commands` → **`503 / application/json`，10.1 s**，body =
`{"error":{"code":"GENERATION_STORE_BUSY","message":"Another generation is writing right now; this one was not recorded. Try again.","message_key":"generation.store_busy","trace_id":"736aa081-…","details":{"retry_after_ms":1000,"contention":"sqlite_write_lock_busy"},"reason_code":…}}`

屏上（逐字）：「服务端处理失败」「这次是服务端出错，不是你的需求有问题。行程未被改动，可稍后重试；反复出现请保留“技术详情”。」+「技术详情」

| 判据 | 读数 |
|---|---|
| `[data-testid="plan-ai-reason"].textContent` **`==`** 服务器 `message` | **True**（两边都是 `Another generation is writing right now; this one was not recorded. Try again.`，逐字） |
| 正控：等值必须被认 | True（同一枚 message 自比 `==` 成立） |
| 负控：只改标点必须不被认 | True（把句末 `.` 换成 `,` 后 `!=`） |
| 屏上有没有客户端自造的 `HTTP 500` / `HTTP 503` | **没有**：对 `document.body.innerText` 扫 `/HTTP ?\d{3}/g` = `[]` |
| reason 节点位置 | 在「技术详情」那个 `<details>` 里（`closest('details') = true`） |

⚠ **一处我不当已验**：`reasonVisible` 我读到过 `height>0`，但**同一枚页面前一轮我手工展开过 `details.open=true`**，所以"未展开时它对用户是否可见"这条**不算我验过的**，标 NOT-VERIFIED（要判就得新开一次、不碰 details）。

### N4 · 有 mission 行时不得说"没记录" —— **这一形下一致；但射程要说清**

同一枚持锁配方，脚本自己再发一发（不靠转写）：`503 / application/json / 41.47 s`，服务器 `message` 与屏上 reason 仍逐字相同。
**行数对表**：这一发之前 `journey_missions=1 / agent_runs=1 / plan_versions=0`，之后 **1 / 1 / 0** ⇒ **这一枚 503 没留下任何 mission 行**，所以它说的 "this one was not recorded" **与库内事实一致**（`claim_is_true_for_this_round = True`）。
⚠ **但 N4 原本担心的那一形我没复现出来**：第一次持锁尝试里，mission `cf7451a3` **写成功了**（它在锁释放前约 1 秒挤进去，`created_at=10:36:19` 是 Python 侧构造时间、不是提交时间——我一开始误把它读成"锁内写入"，实测我的锁是真挡人的：裸连接第二条写 `database is locked`，5.5 s）。那一屏说的是 `CATALOG_EMPTY`（一次性空库没有 places），**不是**"没记录"。⇒ 结论写成 **NOT-REPRODUCED**，不写成 PROVEN-CLOSED：我没能造出"有 mission 行 + 屏上说没记录"这个组合。

### 顺手两枚对别人有用的读数

1. **写腿没有客户端期限**：浏览器那一发等了 **39.2 s** 还在等（`发出请求，等待模型返回 · 已等待 18 秒` 一路涨上去），而读腿有 12 s 期限（ORD-0263 我量过）。⇒ 归 **0269** 那一族（A3 不并 0263 已裁），这里给的是运行时证据。
2. **同一件忙，四种时长都出现过**：10.1 s / 8.25 s / 33.34 s / 41.47 s。⇒ 再次确认**时长只能当读数，不能当判据**；牙齿全在"必须 503 + 必须具名 + 必须在信封里 + 屏上文字必须 `==` 服务器 message"。
3. 一次性空库（只有结构、`places=0`）会让「AI 帮我规划」落到 `CATALOG_EMPTY`，屏上句子是对的，但 `.plan-ai-reason` 里放的是内部诊断串 `GET /places?city_code=CN-BEIJING -> 0 places`。

### 收尾（这次写进脚本，不再手工补）

`n3_n4_answer.py` 末尾自己做完并断言：先用 `Win32_Process.CommandLine` 证明两条 listener 都是我起的，再 `Stop-Process` —— `:8492` pid **44524**（`-m uvicorn app.main:app`，venv 启动器 re-exec 成 uv 3.12.14，与我记忆里那条一致）、`:8493` pid **56664**（`vite.js preview --outDir D:/moodle/_hjp3_fan_sweep_09…`）；然后删 `one_time_n34.s3db` 及 `-wal/-shm`；**断言结果 `listeners_left_8492_8493 = 0`、`db_exists_after_delete = False`、`assert_clean = True`**。

### 一处偏差我写明，不假装照办

你要求"被测树用 `git archive 3093eea…` 新鲜导出"。我本地没有该 ref 的仓库、也不想为取包动凭据 helper，所以**仍用按那 40 位 sha 向 GitHub 取的 tarball**（`codeload…/tar.gz/<sha>`，分支移动顶不掉它），树身份由"提交对象的 tree 字段 `5ae9f8959b05…` 与你 ls-remote 复算值逐位相符"支撑。若你要求必须是 `git archive`，给我一条能非交互取该 ref 的凭据路径我就换。

**纪律**：0 次 `demo/reset`、0 次读写 `_live.db`/`_preview.db`（一次性库只重放结构、seed 只有我自己那两条）、0 次改产品字节、凭据 0 打印、已发布路径 0 覆盖。
