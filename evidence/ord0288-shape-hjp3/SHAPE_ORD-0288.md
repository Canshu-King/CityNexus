# ORD-0288 · 无键写腿补一枚可命名凭条 · 定形（判据 + 反例 + 射程）· HJ-P3 aad2d1f2

> 只交形状：不产码（产码归 @D，排在 ORD-0286 结论之后）、不签 `derived_result`（归 @红队）。依据全是本轮现场读数
> （`keyless_leg_facts.json`：一次性后端 `:8493` + 一次性库 + 本轮新建行程 `f14f7521-f38b-417b-82d2-07d194db490e`），行数一律用**第二条 sqlite
> 连接**判、不读文案。Q25：本轮没有任何时长/竞态断言，也不从别代继承此类读数。

## 0. 今天的事实基线（@D 产码后要对表的就是这张）

| 我发了什么 | `journey_missions` | `agent_runs` | `idempotency_keys` | 响应里的 mission id |
|---|---|---|---|---|
| 起点（本轮新行程） | 0 | 0 | 2 | — |
| 同一条指令、不带键 ×3 | 3 | 3 | 2 | 三个全不同 |
| **同一把 `Idempotency-Key`** ×3 | 6 | 6 | 2 | 又三个，全不同 |
| 同一把键再发一发 | 7 | 7 | 2 | 又一个 |

- 同键三发 ⇒ 三行新 mission、**零行新回执**（回执表是全局的，基线 2 → 现在 2，没动）；响应也**没回显**这把键（`echoed_idempotency_key_header` 全 None、HTTP 全 200）。⇒ 这一支今天对幂等键的态度是**接受并静默忽略**，不是拒绝。
- 对照：同一把库上按 `plans/generate` 的合同发一发带键请求，回执表立刻多一行（现共 3 行，`operation` 就是 `plans.generate`）⇒ **机器是现成的，缺的是这一支没接上**。
- 路由侧证据：`Header(alias="Idempotency-Key")` 在落地树里只出现在 `app/main.py:4606 / :7740 / :9907 / :11364` 四个路由，本单的 `run_agent_command`（`:1057`）**不在其中**；校验函数现成：`app/commerce/validators.py:109 validate_idempotency_key`。

## 1. 三格判据（每格：判据 / 可跑反例 / 红态名）

### T-1 发出去时必须带一枚**客户端可命名、服务端可回读**的凭条
判据（四件同时成立；字段名全部取自真 schema，不自造）：
- (a) 客户端带 `Idempotency-Key` 头，并过既有 `validate_idempotency_key` 的规则（不是新发明的字段）；
- (b) 服务端在**既有表** `idempotency_keys`（列：`key`, `operation`, `request_hash`, `response_status`, `response_json`, `created_at`, `expires_at`）落**一行**，`operation` 值必须把这一支**具名**（与 `plans.generate` 同族，建议 `agent.commands`；最终串由 @D 定，但要可回读、可断言、不许空）；
- (c) 同键 + **同一份请求体** ⇒ `request_hash` 相等 ⇒ 第二发读回同一份答案，**不产生第二行副作用**；
- (d) 同键 + **不同请求体** ⇒ 走现成那句 409（`same idempotency key used for a different request`），**不许**把旧答案静默端给新请求。

可跑反例（我这侧全部可复现：私有冻结 dist + 新端口 + 一次性库）：
- R1 只加头不落行 ⇒ 今天状态重演：missions 0→3 而回执 2→2 不动 ⇒ 红 `KEY_IGNORED_NO_RECEIPT`；
- R2 每次点击自己换新键 ⇒ 同一意图仍堆第二行 ⇒ 红 `FRESH_KEY_PER_CLICK`（0253 的老教训：键由 UI 现造 = 等于没键）；
- R3 只把键写进响应体/日志、库里没有行 ⇒ 红 `NO_READABLE_RECEIPT_ROW`；
- R4 同键不同体却返回旧答案 ⇒ 红 `KEY_REUSED_ACROSS_DIFFERENT_BODIES`（判据要的是 409，不是省事）；
- 等值口径：判"是不是同一份答案"用**逐字段 `==` 且先去掉 `trace_id`**（我在 0279-X 钉过：整段正文比必假不等）。

### T-2 重发同一凭条 ⇒ 不得产生第二行副作用（拆两半，依赖写明白）
- **T-2a（今天就能验，不依赖 0281）**：同键两发 ⇒ 第二发 `journey_missions`/`agent_runs` 行数**不增**，且与被答过那一发逐字段一致（去 `trace_id`）。今天必红：本轮 3→6 三发同键堆了 6−3 行。
- **T-2b（依赖 0281 给写腿装上期限，才会有"中止"这一步）**：期限到或手动取消之后重发同一凭条 ⇒ 仍不增行，屏上也不许把这一发写成"新的一轮"。本单**先钉判据**，执行期标 `BLOCKED_BY-0281-T-b`，**不许拿 T-2a 的绿冒充 T-2b**。
- 反例：中止后客户端自动补发 ⇒ SQL 行数 +1 ⇒ 红 `DUPLICATE_SIDE_EFFECT_AFTER_ABORT`（与 0281 T-d 同一枚反例、**不同修复点**：0281 管"要不要自动补发"，本单管"补发了服务端挡不挡得住"）。

### T-3 拿不到凭条支持时，屏上只许说"结果未知，先核对"
- 判据：三种"不知道"——(i) 键校验失败、(ii) 回读取不到/未填、(iii) 传输被中止——只许出现**结果未知**那一类文案；现成范本就是今天这一句：「已中止后续核对 / 请求本身已经发出去了，可能已经生成方案。请先刷新确认，不要重复提交。」。同时**不许**出现标签「服务器给出的原因」顶着客户端拼的串。
- 反例 1：中止态下标签出现、值是 `AbortError` 或 `HTTP 500` ⇒ 红 `CLIENT_SENTENCE_UNDER_SERVER_LABEL`（与 0280 共享判据、**修复点不同文件**：0280 改 `PlanWithAiSheet.tsx:504/:508/:622` 的归因，本单改这条腿的凭据分支与文案选择）。
- 反例 2（正控，防我把判据写成永远红）：服务器真给了 `error.message` 时标签必须出现且与服务器 `==` 相等——两代我都用标记串验过这条通道能原样搬话。
- 反例 3：库里**有**回执、屏上却报"没发生" ⇒ 红 `RECEIPT_EXISTS_BUT_UI_DENIES`（这格必须**同时**读库和读屏，单侧不许判）。

## 2. 射程（逐腿点名；不在射程的具名列出，不沉默 —— 0281 T-c 的教训照做）

- **在射程（1 条）**：`PlanWithAiSheet.tsx:491` → `POST /agent/commands`（今天有 `signal`、无期限、无凭条）。
- **不在射程（具名 12 条）**：`PlanWithAiSheet.tsx:598`（`plans/generate`：已有 0272 回执机器，归 0281 有键那一支）、`LiveRecovery.tsx:225`、`PushCapabilityCard.tsx:56`、`PlanComparison.tsx:88`、`V14RecoveryTruthPanel.tsx:69`、`simulationAdapter.ts:229/:296/:335/:376`、`HotelsPanel.tsx:63/:64/:87`。这 12 处同为裸 `fetch` 写点（计时器 0 处），**要不要凭条属另一张单**，本单不吞。
- **不在射程的机理**：服务端锁语义与 `busy_timeout`（0262 线）、写腿期限（0281）、归因标签真实性（0280）。
- 搜索空间与局限：清单来自 `frontend/src` 全量 `fetch(` 扫描（33 处、其中写 13 处）+ 落地树 `app/main.py` 的 `Header(alias=...)` 出现位置；未遍历第三方库与运行时动态拼接 URL ⇒ `coverage: NOT EXHAUSTIVE`。

## 3. 交付与签级口径

- 产码（@D）：各自 commit、各自门节点；产品字节改动清单逐件带 40 位 blob；**不许顺手改 0280/0281 的文件**。
- 验收前置：服务器侧那几格必须**跨进程**再跑一次（我这套 rig 现成：两 uvicorn 共一把一次性库）。理由是 K8 那一腿我已实测的机理——Phase A 唯一索引把第二发挡在 409/重放之外，**单进程里"同键撞车再改写"根本走不到**。
- `derived_result` 归 @红队；我只交判据、反例与现场基线，不签级、不自宣击杀。

## 4. 我这侧的读数边界（不遮）

- §0 是**直接 POST 真路由**得到的（不经 UI），所以"T-1 的客户端半件"还没在真机路径上验过——那要等 @D 产码后由我复跑，届时 `signal`/期限等读数以当代为准。
- T-2b 今天跑不了（还没有可命名的期限），已标依赖，不预支读数。
