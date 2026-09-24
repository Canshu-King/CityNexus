# ORD-0279-X · 唯一变量=树 · 在已落地那代 `dcae1bc9` 上重跑服务器侧三格 + 同代 W2

- 单：`ORD-0279-X`（号令 @02:5x+08 第 ⑤ 段第一小段）；仪器与 0279 同一套，**只换树**；旧收据不覆盖不删，新目录新文件名；产品字节 0 改动。
- run id `O0279X-2504` · 车道 `HJ-P3 / aad2d1f2` · 本机钟 2026-09-25T04:29:25+0800
- 代界（这一段是先量后写）：新尖 `dcae1bc964125c3a975916f6bf667794cc19622a`，其 commit tree `d96c2974924d19831495f2945117d4221a1b6d62`，父=c79e2b4f（`parent_is_the_previous_tip=True`）；导出 6,980 个文件，被引 `backend/app/main.py` blob `416ea4f210e967130710a900cdecd20e7a1b5eca`（与号令者 ② 段引的 `416ea4f2…` **逐字节相等** = True），`PlanWithAiSheet.tsx` blob `58c0580bbb603c939592ae8b911c4a291b4eb60a`（两代同一枚，相等 = True ⇒ 客户端那一半本来就代无关）。
- 包工头第 4 点那个坑我量过再写：导出树祖先路径上的 `.git` = 0 个，导出内部 `.git` = 0 个 ⇒ 我这把尺不从任何上层仓库取 HEAD，所有 sha 常量由 40 位写死 + 每文件重算 blob。
- 服务：一次性后端 `:8493` + 面 `:8494`（`ensure_schema()` 建新库，代理归属 200/404/200）；上一代那一对 `:8497`/`:8498` **留着当对照臂**（也照号令给 ORD-0276 用）。

## ① 代界对照：哪些读数能搬、哪些不能（号令 ② 段的分法，我按字节判）

| 格 | 上一代 `c79e2b4` 的读数 | 已落地 `dcae1bc9` 的读数 | 能搬吗 |
|---|---|---|---|
| 服务器对撞锁写腿的答案形状 | `NOT_200_BUT_UNNAMED`（21 B / text/plain） | `NOT_200_BUT_UNNAMED`（21 B / `text/plain; charset=utf-8`） | **能**（产生它的字节没变：ORD-0272 只碰 4 件，`agent/commands` 那条路一个字没动） |
| 「服务器给出的原因」下自造状态串 | `CLIENT_SUBSTITUTES_A_STATUS_STRING_FOR_THE_SERVER_REASON` | `CLIENT_SUBSTITUTES_A_STATUS_STRING_FOR_THE_SERVER_REASON` | **能** |
| 幂等凭条 | 「`idempotency_keys` 全库 0 行」 | 用户这一路仍然 **0 行**，但带上续跑身份就有 2 行（cont / header-key） | **不能照搬**：那句话在新代只对"这一条腿"成立，见 ② |
| 非 GET/HEAD 拿不到读超时 | `WRITE_LEG_RUNS_PAST_THE_READ_DEADLINE_WITH_NO_CLIENT_ABORT` | 未在本代重取运行时常量：发那一句的文件两代同一 blob（`58c0580b…`），发布 bundle 也没重建 ⇒ 记为代无关的支持，不当本代新证 | 支持搬，证据仍在上一代 |

顺带一格（不算裁决，但正好咬到）：`plans/generate` 拒绝那一支在新代给的是 **HTTP 422 + `reason_code=CATALOG_INSUFFICIENT`**，不是 busy 那一支 ⇒ "写锁窗口的 500 没名字"这一格不因 0272 而闭。

## ② 服务器三格（都是现场读数）

**S1 撞锁写腿的答案**：HTTP `500`、`content-type: text/plain; charset=utf-8`、正文 `Internal Server Error`（21 B），耗时 `32379 ms` 作读数；`not_200` = True、`server_named_a_code` = False ⇒ 派生 `NOT_200_BUT_UNNAMED`。

**S2 幂等凭条**：同一次真人点击其实发了两腿——
- `agent/commands` → HTTP 200 / 7083 B（body `{"command": …}`，头里没有 Idempotency-Key）；
- `plans/generate` → HTTP 422 / 1443 B，请求体逐字 `{"candidate_count":3}`，请求头只有 `{"Content-Type": "application/json"}` ⇒ **没带 mission_id、没带 Idempotency-Key**，所以它根本走不到新代那套回执机器。
- 库里回读（应用在跑、我用**第二条连接**在外面读）：用户这一路之后 `idempotency_keys` = 0 行；我按服务器的合同补一发带 `mission_id` + `Idempotency-Key` 的调用之后 = 2 行，键形 cont / header-key，全部 `filled=true`、`response_status=[422]` ⇒ 派生 `RECEIPT_MACHINERY_LIVE_BUT_NOT_ON_THE_SHEET_LEG`。两句合起来才是这句：**回执机器是活的，手机这一路没接上。**
- 上一代我写过"失败的写在服务端连一枚可对账的凭条都没留下"——这句**收窄**：在同一条撞锁 500 的路上成立（新库内 mission 行 +0、回执 +0），但 422 那条带身份的拒绝**是**留了凭条的 ⇒ `NO_DURABLE_TRACE_FOR_FAILED_WRITE_ON_THIS_PATH` / `NOT_TRANSFERABLE_AS_A_BLANKET_CLAIM`。

## ③ 同代 W2（客户端那一半，预期仍红——红了才叫代无关）

| 臂 | 服务器真正发出的字节 | 「服务器给出的原因」下渲染 | `==` |
|---|---|---|---|
| 真后端（写锁冲突） | `Internal Server Error`（21 B，`text/plain; charset=utf-8`） | `HTTP 500` | **False** |
| 仪器路由代答（标记信封，非产品产生） | `error.message = MARKER-X-0279-2504` | `MARKER-X-0279-2504` | **True** |

- `token_present_in_server_bytes` = **False** ⇒ 派生 `CLIENT_SUBSTITUTES_A_STATUS_STRING_FOR_THE_SERVER_REASON`，与上一代同 verdict（`transfers=true`）——**同代复现仍红**，所以它不是代际偶然。
- 可见性按上一轮那条教训重做：先 `scrollIntoViewIfNeeded()` 再命中测试——真后端的臂命中 `CODE`（rect 301x25，屏内），标记臂命中 `SECTION`（那次没重测命中点，读数照原样记）。两臂的值都在渲染 `innerText` 里，不是 data 属性。

## ④ 上一单我写着"未测"的那格：取消

在飞 7046 ms 时点掉真按钮「取消」（`getByRole` 命中 1 个）：客户端记录 `client_error = AbortError: signal is aborted without reason`（HTTP 状态为空，是**用户中止**不是超时）；卡片换成逐字：「已中止后续核对 / 请求本身已经发出去了，可能已经生成方案。请先刷新确认，不要重复提交。」。库内 0 行新增（mission/agent_runs 都没动）⇒ 派生 `CANCEL_IS_MANUAL_ABORT_ONLY`。
- 仪器缺口具名：access log 里那条腿**一行都没有**（基线 2 → 现在 2）——uvicorn 是在响应发出时写行，客户端先走就没有行。所以这一格只能问库，不能问日志：`uvicorn writes the access line when the response is sent, so an aborted request leaves no log line - the durable store, not the log, is what answers this`。
- 这一格补上后，"写腿没有自我终止的时刻"这句更准了：**手动取消有，自动截止没有**（同一页 `:491/:598` 两腿都带 `signal`，但 `vb()` 的写分支不装计时器）。

## ⑤ 两条自我更正（都发新件，不覆盖旧收据）

1. `REPLAY_IS_EQUAL_ONCE_TRACE_ID_IS_EXCLUDED`：我第一次用**整段正文**比"重发是否同一份"，得到 `raw_bodies_equal=False` 就差点写成"回执重发不稳定"；按字段重比之后只差 `trace_id`（`equal_after_dropping_trace_id=True`，code/message/message_key/details 键数 6/6 全等）⇒ 那句不等**没有判据基础**，撤回。
2. 上一代那格我先报 `visible:false`，是**没滚动就命中测试**造成的（同一条读数里元素 rect 301×25 明明在视口内）；本轮先滚再测，命中 `CODE`。旧收据不动，这里记差。

## ⑥ 未测 / 边界

- 未在本代重取"写分支无计时器"的**运行时**读数（只依据同一 blob 的代无关支持）；要钉死可再跑一窗口，说一声。
- 没测第二枚"后发腿秒级即拒"：上一代在 WAL + `busy_timeout=30000` 下就没复现，本轮没有再凑。
- K8 定向观测排在 0279-X 之后（号令：不抓现在的主线），本轮**未做**，不预支读数。
- 负向搜索声明：`mission_id`/`Idempotency-Key` 的"这一条腿没带"是在 `PlanWithAiSheet.tsx`（43,631 B）全文 + 发布 bundle 的字符串计数上判的（bundle：plans/generate 4 / mission_id 2 / Idempotency-Key 6 处），未遍历其余组件 ⇒ `coverage: NOT EXHAUSTIVE`。
- `demo/reset` 0 次；用户库 0 写；凭据 0 打印；一次性库跑完删。库里那行 `Demo之旅` 行程来自`seed_demo()`（目录要有行才能让 plans/generate 走到判断），不是我造的第二个库。

## ⑦ 已发布件（blob 从分支 tree 读回）

分支 `commander/control` 读回 commit 尖 `02c2c93c58ccec3a024f94834f6d9d80f8e78eb7` · 该 commit 的 tree `545f7e31c94f7b8acd45c75e6a5c77286022ec81` · 共 8 件 · 外部可读探针 `O0279X-2504_readings.json` 重算 sha1 与 tree 上 blob id 相等 = True：

| 文件 | 大小（读回） | blob（40 位，读回） |
|---|---|---|
| `O0279X-2504_readings.json` | 9,483 B | `24a6a384e357449c7cc8f4de4a0f1d9b2759da63` |
| `o0279x_dbfacts.py` | 2,639 B | `2fed690ffcd0c607c55cd641871d50f2468a01b1` |
| `o0279x_score.py` | 10,733 B | `500cf32258ccae9df5251173dfee5c0a369b4254` |
| `o0279x_serve.py` | 8,653 B | `d941680104615f3b6dfe6d408c4a49c2e6acc535` |
| `o0279x_setup.py` | 6,129 B | `387ec80bc6e6dbe17cf77e3d588f112cf739ddbe` |
| `shots_O0279X-landed-cancel-card.png` | 41,814 B | `327002cd6f6529000b4aa13ef86695cb37d1a0a8` |
| `shots_O0279X-landed-marker-open.png` | 44,536 B | `15aac1f99e90550d1d43a56059e2b315871da7c9` |
| `shots_O0279X-landed-w2-scrolled.png` | 44,247 B | `2daf1dfe4044a9de560b232d3803598d251c1131` |

本地另存、未发布的第 4 帧：`shots_O0279X-landed-w2-details-open.png`（那是"没滚动"那次，其教训已写进 ⑤-2，就不再占分支一件）。
复跑：`python o0279x_setup.py export` → `python o0279x_setup.py db` → `python o0279x_serve.py start|seed|own` →（`o0279x_serve.py lock 95` + 点「开始规划」/点「取消」）→ `python o0279x_dbfacts.py` → `python o0279x_score.py` → `python o0279x_publish.py` → `python o0279x_readback.py`。
