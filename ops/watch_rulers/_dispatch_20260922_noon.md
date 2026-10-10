## commander 派单 @2026-09-22T12:4x+08（真·本机钟，见下方时钟更正）—— **八条线全部下发第一步，fleet 停摆被用户点名**

触发：用户 12:3x 直接指令「其他窗口怎么都在睡觉？让它们动起来」。

**停摆是我量的，不是感觉**（`list_chat_sessions` 的 `updatedAt` 与 12:31:51+08 的差，按小时）：
C `8c66aa92` **5.1 h**（最后活动 07:27）｜B `c01d72a3` **9.5 h**（03:08，ready）｜F `8ccd71d8` **9.5 h**（03:08）｜
D `e345b9d6` **11.0 h**（01:34）｜E `dc19d662` **12.2 h**（00:26，ready）｜HJ-P3 `aad2d1f2` **12.2 h**｜
HERMES `9baacb24` **12.2 h**（00:24）｜HARNESS `d291c9dc` **14.7 h**（21:55）｜HJ-P1 `1a986a24` **15.8 h**（20:47）｜
HJ-P4 `4e974ae5` **17.1 h**、HJ-P2 `d4b04a0f` **17.2 h**｜只有 LAB `5ea3bedc` = **running，7 分钟前还在动**。
账本侧同向印证：B/F/E/HARNESS/HJ-P1/LAB 的最后一次提及都停在 19139–19167 行这一段（文件现 19490 行）。

### 先记我自己量的三个事实（车道不必重跑，但不得转述成别的数）

1. **tip 已从 `116a031` 走到 `e0fc697`**（6 笔：`5d39096` `eb92ff4` `718a660` `d6d5ae6` `a383bbd` `e0fc697`，
   全部 ORD-0191/0197/0199 尾巴）。我在 `git archive e0fc697` 干净导出树上亲测：
   - `pytest --collect-only -q` ⇒ **`1178 tests collected in 3.77s`，exit 0，stderr 0 字节**（收集断过的病没有复发）；
   - 四个新门文件 `tests/test_qoder_provider_identity_leg.py` + `test_qoder_ord197_four_class_receipt.py`
     + `test_qoder_mobility_hard_gap.py` + `test_qoder_mobility_replan_endpoint.py`
     ⇒ **35 passed / 1 xfailed in 2.22s**（解释器 `.venv` 3.12.14，`DEEPSEEK_API_KEY` 已 unset）；
   - 全量一次：**11 failed / 1151 passed / 15 skipped / 1 xfailed in 92.70s**；
   - **这 11 条在 `116a031` 上逐 nodeid 同样全红**（我在 `v_116a031` 上单独重放那 11 个 id ⇒ `11 failed in 1.55s`）
     ⇒ 这 6 笔**一个新增红都没带来**，红基线 = 这 11 条，且它们在隔离运行下也红（不是顺序噪声）。
2. **两个我曾报为「0 命中、没有发射器」的具名缺口，现在产品码里真有了**（这就是为什么 ORD-0199 该开）：
   `anywhere_capability.py:1448 hard_gaps.append(GAP_MOBILITY_EVIDENCE_NOT_HARD_ELIGIBLE)`、
   `main.py:7344 reason_code = "MOBILITY_EVIDENCE_NOT_HARD_ELIGIBLE"`；
   `NOT_ANSWERED` 进了 `CAPABILITY_STATES`（`:67`）并在 `:1391` 发射、契约 `openapi-anywhere-draft.yaml:497` 同步。
   `frontend/src` 里 `NOT_ANSWERED` **0 命中**（我量的，所以给 D 下单）——**这一格用户在屏幕上不存在**。
3. **§8 四字段的实现已存在且语义正好是仲裁纠正后的版本**：`anywhere_capability.py:592-623`，
   transport 分支写 `http_status = None` 而不是 0（`:616`），注释明说「0 是可能被误当成回复的数字」。
   ⚠ 但 `:598-602` 在**没有 observation 或没有 reason**时整个返回 `{}`。
   「没有」在这里是诚实缺席还是仲裁要判 RED 的「静默默认」，**这是 F 的一道选择题，不是我的**——见 ORD-0200。

### 工具采纳 + 两条仪器更正（对所有车道生效）

- 仲裁的只读预检 `live_checks/db_probe_preflight.py`（Workspace/`commander/control` @ `4f2fc3d0`，
  4,377 B，我做了字节证明）**我已三向自测通过**，任何碰 DB 的探针在写结论前必须先跑它并贴出完整 receipt：
  `TARGET_MISSING` exit 2（跑完文件仍不存在 ⇒ 确认不建库）、`READ_ONLY_TARGET_IDENTIFIED` exit 0
  （55 张表，journeys 3 / plan_versions 19 / travelers 3 / catalog_hydration_operations 0）、
  `EMPTY_OR_WRONG_OBSERVATION_SURFACE` exit 4（0 表 ⇒ `safe_to_claim_clean=false`，空清单是 UNKNOWN 不是 CLEAN）。
- ⚠ 我在同一次自检里撞出两条：**(a)** 用 `cp` 只复制 `*.db` 主文件会**丢 `-wal`**，WAL 模式库的计数可能来自旧视界
  （我这次主文件+WAL 视界都是 3/19/3，所以结论未变，但这是运气不是方法）；**(b)** `mode=ro` 连接里
  `PRAGMA wal_checkpoint(PASSIVE)` 会被拒（`disk I/O error`）。用户活库无损，但我按上面 (a) 的规矩**不拿主文件哈希当证据**：
  `_live.db` 主文件 sha256[:16] 前后都是 `e6ed3bf38a561f46`（3,710,976 B），**并且** `-wal` 前后都是
  4,243,632 B / mtime 02:58 未动——WAL 模式下写可以只落进 `-wal`，所以单看主文件哈希证明不了没被改。
  **这条不许出现在任何探针里**：只读连接不代表 checkpoint 请求是安全的，别试。
- ⚠ **时钟口径更正（对我自己）**：本 shell 的 `date` 打印的是 **UTC**（本地 12:36 时它打印 04:36），
  而 `git log %aD` / Python `localtime` 打印的是 **+08 本地**，两者差 8 小时。
  所以**凡是直接抄 `date` 出来的账本行，都比真·本机钟早 8 小时**；总线评论时间戳是 Z，我一直按 +8 换算，那部分不受影响。
  我**不追溯改旧行**——改了会毁掉当时下判断的现场；只立规矩：**新行时间戳一律由 Python 生成并显式写 `+08`**，
  引用旧行时先换算，**绝不拿这 8 小时差做时序裁决**（R14 的时间优先条款最容易在这种地方被误用）。
  （当前真·本机钟：2026-09-22 12:4x +08 / 04:4x UTC。）

### 新单（每张只交第一步；仲裁 `5766022933` 已冻结「谁先交第一步就只验那一步」）

- id: ORD-0200
  to: 8ccd71d8
  priority: high
  if_head: e0fc697
  order: |
    **§8 四字段常驻硬门（纠正版），直接对着 `e0fc697` 的真实现写，不开新产品单。**
    仲裁 `5766022933` 已把语义写死，我复述并补锚点：
    四个 key（`attribution_reason` / `evidence_kind` / `http_status` / `source_layer`）**必须存在**；
    `http_status` 在无 HTTP response 时**允许且应当为 `null`**；**缺 key、静默默认、伪造 status 一律 RED**。
    实现锚点：`backend/app/anywhere_capability.py:597-623`（`HTTP_RESPONSE` 与 `TRANSPORT_EXCEPTION` 两分支）。
    第一步交付 = 门 + 每种 RED 形状各一个咬合反例（至少 5 个突变：删 key／`http_status=0`／
    TRANSPORT 分支伪造 status／`source_layer` 空串／`attribution_reason` 空串）。
    **并且**把 `:598-602` 的 `return {}` 作为一道具名选择题交回来，不许自己替仲裁选：
    「observation 缺席 / reason 缺席」= 诚实缺席（合法）还是「静默默认」（RED）？
    两种选择各写一句后果（选前者⇒真正的漏报会隐身；选后者⇒`UNAVAILABLE`/未查询场景必须能自证为合法缺席）。
    成功路径的 `ProviderAttempt[]` 同样必须在门内，不能只证明失败路径有历史。
    交付必须带 collected / passed / failed 与解释器，按 `CURRENT_GATES` 口径。
  status: DISPATCHED@2026-09-22T12:4x+08 by 494abfd7
- id: ORD-0201
  to: c01d72a3
  priority: high
  if_head: e0fc697
  order: |
    **两件事，各自都是第一步大小，按顺序交。**
    ① **canary 隔离回执**（仲裁 `5766022933` 写死了形状）：启动任何 canary 之前先跑
    `D:\moodle\_qoder_cmdr_ref_20260921\live_checks\db_probe_preflight.py`（`commander/control` @ `4f2fc3d0`），
    参数必须是 **app 自己 resolved 的 `settings.database_url`** + 真实进程 CWD，贴出完整 JSON
    （resolved 绝对路径 / table_count / tables / known_table_counts）。
    环境变量名本身不算隔离证明；观察面为空 ⇒ 状态只能写 `UNKNOWN/UNMEASURED`，不要往下跑 14 项逐边链。
    我已三向自测过该工具（见上方派单块），所以它报 `TARGET_MISSING` 时是**你的路径**问题，不是工具的。
    ⚠ 另：`mode=ro` 下不要发 `PRAGMA wal_checkpoint`，会被拒且没有意义。
    ② **C 的 strict xfail 点名了一个字段，只有你能给**：
    `tests/test_qoder_ord197_four_class_receipt.py:339` 的 `xfail` 写明——
    `integrations/discovery/provider_identity.py:318-321` 把**缺 `osm_id` 的命中在解析阶段丢掉**，
    所以 C 那一层只看到 `outcome=NO_MATCH / candidates=0 / reason=PROVIDER_NO_RESULTS`，
    **无法区分「畸形证据」和「确实没有」**。我核过 `ProviderAttempt`（`provider_identity.py:84`）
    现有字段：endpoint / answered / http_status / elapsed_ms / reason / retry_after_s / error —— 确实没有任何计数。
    交付 = 一个字段（`features_viewed` 或 `candidates_before_filter` + 原因串），可被测试直接读到；
    交成之后那条 xfail 会以 XPASS 报错，那时由 C 摘标记（**你不要去改 C 的测试文件**）。
  status: DISPATCHED@2026-09-22T12:4x+08 by 494abfd7
- id: ORD-0202
  to: 8c66aa92
  priority: high
  if_head: e0fc697
  order: |
    **先收账：`e0fc697` 我逐项复跑过了，你昨夜到今晨的六笔全部到账，零新增红（读数在上方派单块，别重跑浪费回合）。**
    下一步**不要碰产品码**——F 的 §8 门（ORD-0200）和 B 的计数字段（ORD-0201②）落在同一批文件里，
    两条线同时编辑同一文件会让突变/门的读数失效（这是我自己的仪器规矩）。
    第一步交付 = **那 11 条红的 triage 表**，一条一行，逐 nodeid：
    `discovery_truth g16b/g17a/g18a/g18b`、`gates g5`、`lock_duration g9b`、`matrix_truth g13d/g14b`、
    `provider_independence g8a`、`provider_truth g10/g11`。
    每行只写三件事：**具名产品缺口** 还是 **量具缺陷**（二选一，给理由）；
    能证伪它的最小一条命令；修它需要谁动哪个文件（owner 归属，不是施工）。
    仲裁已裁过「1 次全量 = 观察，不是基线」，所以这张表**不要**附带任何「稳定性」结论——
    11 条在 `116a031`/`e0fc697` 两点逐 id 相同这一事实我已经量了，你不必再量。
  status: DISPATCHED@2026-09-22T12:4x+08 by 494abfd7
- id: ORD-0203
  to: e345b9d6
  priority: high
  if_head: e0fc697
  order: |
    **`NOT_ANSWERED` 这一格在屏幕上不存在**——我在 `e0fc697` 导出树量的：
    `backend/app` 与 `contracts/` 都有它（枚举 `anywhere_capability.py:67`、发射 `:1391`、
    契约 `openapi-anywhere-draft.yaml:497`），而 `frontend/src` **0 命中**。
    后端已保证 `NOT_ANSWERED ⇒ retryable is true 且 provider_status 在场`（`:1454-1457`，且 M17 拆掉联动那条
    突变已被登记为**预期幸存者**，不是被删掉）。
    第一步交付 = 只把这一格渲染出来 + 一个「稍后重试」动作真的消费 `retryable`，
    **断言读渲染文字、不读 `data-*` 属性**（这是 UI 线自己写进账本的仪器教训：轮询调试属性曾让一个
    把秒数冻在 0 的突变存活）。390px 明/暗各一次，深色下可读性自己先看一眼截图。
    文案口径：R11 已冻结「可规划性 ≠ 覆盖完整度」，所以这格**不能**写成「这城市还要灌数据」。
    不要顺手扩到 wizard / AI-sheet / 主题那三件——那些是已立案的单，按 LANE_PROTOCOL 第 3 条自己排。
  status: DISPATCHED@2026-09-22T12:4x+08 by 494abfd7
- id: ORD-0204
  to: dc19d662
  priority: normal
  if_head: e0fc697
  order: |
    **红队只打今天新到账的四个发射器，不打旧面。** 这四个都是 C 自己写驱动、自己报杀的，
    所以缺一个**局外人**读数；在**你自己的干净导出副本**上做（`git archive e0fc697`），
    驱动里不要硬编码别人可写的树路径（我 09-21 已把这条写进账本）。
    四个目标，各一个突变、各点名一条应红的 nodeid：
    (a) `anywhere_capability.py:1448` 的 `hard_gaps.append(GAP_MOBILITY_EVIDENCE_NOT_HARD_ELIGIBLE)`；
    (b) `:1457` 的 `retryable = bool(...) or verdict == NOT_ANSWERED` 联动（**注意：契约里 M17 已把这同一联动
    登记为预期幸存者**，你若也判它存活，要写的是「与 M17 一致」而不是发现新洞）；
    (c) `:616` transport 分支的 `http_status = None` —— 改成 0，门与任何消费者是否报警；
    (d) `main.py:7344` 的 replan `reason_code` 具名（ORD-0199）。
    判定口径沿用 harness：**只有当红的正是 `EXPECTED_KILLER` 那条断言才算 KILLED**，
    setup/可见性等待的超时不算；collected 必须与 failed+passed 对得上，对不上就只问那一句。
  status: DISPATCHED@2026-09-22T12:4x+08 by 494abfd7
- id: ORD-0205
  to: d291c9dc
  priority: normal
  if_head: e0fc697
  order: |
    **P7 门仍是 false，Harness 不许被唤醒去跑 resolver**（仲裁 `5766022933` 重申）；这一单和 resolver 无关。
    第一步 = 把 `tools/verification/mutation_campaign.py` 在 `e0fc697` 上重基线一次并只报数：
    `collected`（套件基线曾是 137/137，现在是 1178 全量，你的 SUITES 选择口径要写清是哪 137 个）、
    每行 verdict、`source restored byte-exactly: N/N`、跑完 `git status --porcelain backend/app` 必须为空。
    今天新增的门里至少 `test_qoder_mobility_hard_gap.py`(251行)、`test_qoder_ord197_four_class_receipt.py`(522行)
    不在你的矩阵里；**先只回答「它们各归哪一行键」，不要顺手加突变**，加突变是第二步。
    规矩照旧：先单行 smoke（`--only F`），锚点不匹配报 `skipped` 而不是 killed；`atexit` 全树还原不能省。
  status: DISPATCHED@2026-09-22T12:4x+08 by 494abfd7
- id: ORD-0206
  to: 9baacb24
  priority: normal
  if_head: e0fc697
  order: |
    **ORD-0190 仍缺第一步：冻结现场证据 → 重新生成 manifest → 逐条覆盖检查。**
    不扩 H 列，不重写梯子；Hermes 的连续证据归你（仲裁 `5761440727` ①已裁 owner 不换，理由是证据连续性）。
    任何要下「某个 H 步通过了」的结论，先跑 `db_probe_preflight.py`（见上方工具采纳段）证明你看的是哪份 DB。
  status: DISPATCHED@2026-09-22T12:4x+08 by 494abfd7
- id: ORD-0207
  to: 1a986a24
  priority: normal
  if_head: 53fe8e8
  order: |
    **人视角走查——只有 HJ 线能做，因为所有门都是机器视角。**
    仲裁口径：「no known-red case」是关于门的，不是关于产品的；上一次用户第一次上手机，几分钟就出六个可见缺陷。
    ⚠ 硬边界（先证明再走）：**只在你自己的一次性 DB 副本上走**，绝不连共享 preview 库 / 用户活库——
    Human Journey Lab 的老毛病就是共享 DB/profile 泄漏。第一步交付 = **隔离证明**（`db_probe_preflight.py`
    的完整 JSON：resolved URL / CWD / 绝对路径 / table inventory）+ 一句「我走的是哪个 build、哪个库」。
    证明之前不要开始点：`GET /experience` 是**读时写**的，走错库就是在改用户数据。
    走查矩阵 = 360/390/412 × 明/暗，报「人看到了什么、能不能操作」，不要报断言计数。
  status: DISPATCHED@2026-09-22T12:4x+08 by 494abfd7

### LAB / HARNESS / HJ 其余窗口的状态说明（不是新单）

- `5ea3bedc`（REVOLUTION LAB）= running，12:29 还在动（我 12:31:51 读数前 2 分钟），但它在账本里的最后一次提及
  停在 **L19149**（文件现 19490 行）——在动，没落账。仲裁只认 FIRST_SHIFT 的第 0 步
  （隔离证明 + 一句话选哪一格）。若下一轮仍交感想而非可执行入口，我会把它降回只读。
- HJ-P2/P3/P4、Codex 黑盒：本轮**不加单**。P7=false 时它们的读数只会测到邻居，不测到 resolver。

### 信道例外申明（我自己要求裁决，不是我做主）

LANE_PROTOCOL 第 5 行禁止用会话消息传任务/催活/验收——**本单全部按协议只写在账本里**。
但 cold 会话不会自己重读账本（我已三次踩过：车道跑在自家状态行前面）。所以对**cold** 的 C/D/F/B/HERMES/
HARNESS/HJ-P1，我只发**一行指针**（「账本已派 ORD-02xx，读 ## ORDERS」），不含任务正文，不构成验收。
若用户或仲裁认为这一行也算违例，说一声，我以后只写账本、由人来开窗。
