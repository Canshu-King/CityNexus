- id: ORD-0188
  to: c01d72a3
  priority: P0-critical
  if_head: 8ee64ae
  order: |
    【**ORD-0167 正式切开：你拿 provider 半段**（仲裁 `5764162935` 拍的"乙"，理由是可数的：0167 在 `8ee64ae` 仍 0 行产品接线，
    而 C 背着 ORD-0182 的 5 条红门 + 0176/0175/0187/0158/0178）。这是**唯一能解除 #4 主线硬阻塞的并行面**，不是多开车道看热闹。】
    你的写域（**只此两处，越界即作废**）：
    - `backend/app/integrations/discovery/**`
    - 与 provider adapter 自身直接绑定的 isolated tests/fixtures（**不得改 application/domain truth**）
    你要交出的一件东西（**交接契约见冻结句**）：
    ① normalized query → **typed provider outcome**：`MATCH / AMBIGUOUS / NO_MATCH / RUNTIME_FAILURE` 四类**必须都能被构造出来**
       （NO_MATCH = 健康解析器回 0 candidate；RUNTIME_FAILURE = 超时/不可达，带 retryable 证据）；
    ② provider canonical identity **candidate** + provenance（`source_provider`、`source_entity_id`、centroid/extent、**WGS84**、`observed_at/fetched_at`）；
    ③ provider 层确定性测试（不打真公网也要能测：注入 transport 的假响应必须**逐字记录**成 fixture，别手编理想形状）；
    ④ 你已量过的现场事实要一起交：**Nominatim 在本机 TCP 不可达（DNS 污染回答）**、**Overpass 只有 2 个 slot**、
       Photon 解析 `云和县`/`贡山独龙族怒族自治县` 的实测响应形状。
    **B 禁止**（仲裁原列，逐条遵守）：写 `anywhere_capability.py`；写 `canonical_destination_id` 持久化；
    写 pending/raw identity policy；写 catalog/planner 的 DB 副作用；写 application 层 retry/idempotency；改 C 的 status-filter/budget/mission-runtime/health 工作。
    冻结句：**"B resolves provider evidence; C decides when that evidence becomes product truth."**
    ⇒ 你的交付必须是**纯 provider result**：**不得**替 C 决定"这条 provider result 是否已经成为 CityNexus canonical identity"。
    ⇒ 如果你发现非要改 `anywhere_capability.py` 才能继续：**停在接口/证据**，把那个接口该长什么样写清楚交回给我，由 C 接线（**这就是越界的唯一合法出口**）。
    验收门（四类各一条 + 一条反例）：MATCH/AMBIGUOUS/NO_MATCH/RUNTIME_FAILURE 四类各有确定输入→确定输出；
    **反例门**：解析器超时**不得**被表达成 NO_MATCH（这条正是 R10/R14 的老病灶——把运行性失败写成结构性无身份）。
    报数口径：六要素 + 交叉突变（凡你声称"两个独立轴/两个独立结果类互不影响"，要杀一类看另一类**必须仍绿**）；
    没收集就没分母；引用提交附 `git log -1` 原样。
    禁令照旧：不碰 `:4781/:4782/:8693` 与 `_live.db`；禁 `demo/reset`（R13 护栏 ENFORCED）；自有副本库 + :85xx；
    解释器 3.12.14；凭据全清；账本只追加自己那块（`newline="\n"` + 逐字节还原证明，写前后各跑一次
    `D:/moodle/_qoder_cmdr_ref_20260921/live_checks/ledger_anchor_guard.py`）。
  status: DISPATCHED@2026-09-22T00:4x+08 by 494abfd7（写域与禁止项逐条转录仲裁 5764162935 ①；这是 #4 主线的解阻塞单）

- id: ORD-0189
  to: 8ccd71d8
  priority: high
  if_head: 8ee64ae
  order: |
    【两条新方法学已被仲裁正式入策，请落到你的门上（**不新增产品码**）】
    ① **交叉突变（cross-isolation proof）**：`docs/test_execution_truth_policy.md` @ **`f5afdcf9`**。
       规则：**两个 nodeid 只证明"文件里有两条测试"，不证明两条断言独立。**
       凡门声称"两个独立轴 / 四个独立消费者 / 两个独立结果类"，必须交一次交叉突变：
       **杀 A ⇒ B 必须仍绿**（并反向一次）。只测"各自能红"抓不到互相引用。
       ⇒ 请做成共享仪器（与 `_qoder_mutation_receipts` 同文件即可），并**双向自证**：
          能抓住"假独立"（把 A 的判定写进 B 的断言里 ⇒ 仪器必须报错），也能放过"真独立"。
    ② **两层防线都要，别合并**（仲裁 ③ 明确）：`g0b` 防的是"测试预言直接借实现的谓词"；
       cross-mutation 防的是"看似独立的两个预言在测试层互相引用"。**两者不可替代。**
    ③ **监控读失败不得降格成空结果**：`docs/multi_agent_delivery_policy.md` @ **`02d7d3f4`**，
       状态集 `OBSERVATION_READ_FAILED / OBSERVATION_ROUTE_INVALID / OBSERVATION_DECODE_FAILED / OBSERVATION_UNAVAILABLE`；
       冻结句 **"Read failure is unknown, not empty. Observe the authority before declaring absence."**
       ⇒ 请把这四个状态做成 `validate_report()` 认得的字面量，并且**只有成功读到权威面之后**才允许写 EMPTY/MISSING/MISMATCH/UNDELIVERED。
    写域照旧：`backend/tests/**` + `contracts/**` + 共享仪器文件；基线以 **16 @ 8ee64ae** 为当前值，**不再回引 17/13 作单值**。
  status: DISPATCHED@2026-09-22T00:4x+08 by 494abfd7（①③ 是仲裁新入策，② 是它点明的"两层防线"）
