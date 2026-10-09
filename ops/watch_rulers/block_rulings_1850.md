### commander 转录 @2026-09-21 18:5x —— 仲裁 5759213125 已到：**R10 与 R11 双双冻结**，本条是车道可执行版（原文在总线，我按能开工的粒度重排）

**R11 = 选 A，并吸收 B 的正确部分：可规划性 ≠ 覆盖完整度**
- 契约新增两个独立真值：`planning_readiness: READY | NEEDS_HYDRATION | BLOCKED`、
  `coverage_completeness: COMPLETE | PARTIAL`；
- `capability` 不再由"六轴全 READY"机械决定，改问一件事：**当前本地目录/证据能否让共享 planner
  产出至少一条 evidence-complete 的 selectable plan**：能 ⇒ READY；不能但有受支持 provider 可补 ⇒ HYDRATABLE；
  无可追溯来源或无法合法解析 ⇒ UNAVAILABLE；
- **北京此刻应有的形状就是 `capability=READY + planning_readiness=READY + coverage_completeness=PARTIAL
  （nightlife PARTIAL / lodging MISSING）`**——它今天已经能出 3 个 selectable 候选，却被判 HYDRATABLE，这是评估器的错；
- 六条硬规则（逐条可测）：
  1. coverage PARTIAL **不得**把 READY 降成 HYDRATABLE；
  2. bare capability 是"基础可规划性"，不是"所有偏好都满足"；
  3. 单次请求可因自己的硬要求被拒（例如用户把 lodging 设成硬要求而 `lodging=MISSING` ⇒ 对**该请求**给
     `CATALOG_INSUFFICIENT`），但**不得**反过来说整座北京不能规划；
  4. **capability evaluator 与 shared planner 必须做 parity gate**：同一 snapshot 上，
     只要 shared planner 已能产出 selectable candidate，capability 就**不许**回答 HYDRATABLE/NEEDS_HYDRATION；
  5. coverage 仍要展示，UI 文案改成"可规划，夜生活/住宿数据仍不完整"，**不许**再显示"这城市还要灌数据"；
  6. 后台 enrichment 可以继续，但**不得阻塞**一个已经 READY 的城市。
→ 已落成 **ORD-0133**（车道 C，排在 ORD-0131 之后）。

**R10 = 禁止把 `unresolved:<hash>` 当规范身份；原始输入与规范身份必须分离**
冻结句：**raw destination text 是用户输入，不是身份；hash 是相关键，不是身份；canonical identity 必须来自可追溯 resolver 事实。**
1. `canonical_destination_id` **只有 resolver 确认规范地理实体后才可有值**；unresolved 时必须是 `null`，不许塞 hash；
2. `unresolved:<hash>` 只允许当：request correlation key / hydration fingerprint 的临时输入摘要 / diagnostic token。
   **不得**当：canonical destination identity、Journey 的 durable city identity、provider entity identity、UI 回显的城市身份；
3. Journey 语义必须分开：`destination_input`（用户原文）、`destination_resolution_status: RESOLVED|UNRESOLVED|AMBIGUOUS`、
   `canonical_destination_id: null|真 id`、`canonical_display_name`；字段名可适配，**语义不许再混**；
4. **新 Journey 写入不得再把任意字符串升级成 canonical city_code**（今天 `CN-云和县` 就是活证据）；
   允许先存 DRAFT，但它是"带原始 destination_input 的未解析 Journey"，不是"已经拥有一个伪造的 CN-xxx 城市"；
5. resolver 成功后：**原 Journey id 不变**，只补 canonical identity / display name / resolver provenance，
   hydration 与 planning 从该规范身份继续；
6. resolver 不可达 ⇒ 按 **R1** 走 runtime failure / retryable：**不写 hash、不判结构性 UNAVAILABLE**；
7. resolver 返回多个合理候选 ⇒ `AMBIGUOUS`，把候选交给人选：**不许模型或后端悄悄猜一个**；
8. resolver 成功且明确 0 候选 ⇒ 才允许 `NO_CANONICAL_IDENTITY` + `canonical_destination_id=null`，
   可给 UNAVAILABLE，但文案必须是"无法解析此目的地"，不是"伪造一个 hash 城市继续跑"；
9. **legacy Journey 里已有的任意字符串 city_code 禁止删除/重建**：兼容读取 + 按需 backfill，
   解析成功就附 canonical identity，失败就保留用户原文并标 legacy/unresolved——
   **"不要拿 schema 清洁度换用户数据。"**
→ ORD-0127 的硬门按仲裁指定钉 7 条：unresolved 不产生 durable hash canonical id / 新 Journey 不把 raw text 当 canonical /
Photon 单候选 ⇒ 同一 Journey 原地 RESOLVED / 多候选 ⇒ AMBIGUOUS 不猜 / resolver outage ⇒ retryable 不写 hash /
legacy raw city_code 不丢不重建 / capability·hydration·planning 只在 canonical 成立后才进入真正的城市数据流程。

**另一条是冲我自己下的**：仲裁令——在 ORD-0125 变成"只删 demo seed 派生数据 + `preserved_user_rows` 可证"之前，
**任何人（包括我）不得再在活的 `_live.db` 上跑会触发 reset 的 M1-M4 全链**。我照办：
要重走 M1→M4 就在 `live_snapshots/` 的一致快照副本上走，手机台上只做只读观察。
