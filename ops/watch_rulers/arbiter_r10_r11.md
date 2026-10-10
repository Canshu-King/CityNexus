仲裁: SESSION=EXTERNAL

已读 **5759171969**。R11 / R10 现在冻结。

## R11 — 选 A，但把语义钉死：**可规划性 ≠ 覆盖完整度**

北京这组实证已经证明当前 evaluator 把两个不同问题揉成了一个：
- “现在能不能生成至少一条 evidence-complete selectable plan？”
- “六个能力轴是不是都完整？”

这两件事必须拆开。

### 契约
保留六轴 coverage，但新增/明确两个独立真值：

```
planning_readiness:
  READY | NEEDS_HYDRATION | BLOCKED

coverage_completeness:
  COMPLETE | PARTIAL
```

原来的 destination `capability: READY|HYDRATABLE|UNAVAILABLE` 不再由“六轴是否全部 READY”机械决定。对 UI/业务而言：

- **READY**：当前本地 catalog/evidence 已足以让共享 planner 产出至少一条正常 selectable plan；
- **HYDRATABLE**：当前还不足以产出正常 selectable plan，但有受支持的真实 provider 可以补足；
- **UNAVAILABLE**：没有可追溯、受支持的数据来源或目的地无法被合法解析。

`coverage_completeness` 独立回答“这个城市的数据是否完整”。因此允许：

```
capability = READY
planning_readiness = READY
coverage_completeness = PARTIAL
nightlife = PARTIAL
lodging = MISSING
```

这正是当前北京应有的形状，而不是 HYDRATABLE。

### 硬规则
1. **coverage PARTIAL 不得自动把 READY 降成 HYDRATABLE。**
2. bare destination capability 是“基础可规划性”，不是承诺所有偏好都满足。
3. Journey/request 带明确需求时，planner 再根据该次请求所需 axis/evidence 判断；例如用户把 lodging 变成硬要求而 lodging=MISSING，可对该请求给 `CATALOG_INSUFFICIENT`，但不能反过来说整座北京都不能规划。
4. capability evaluator 与 shared planner 必须做 parity gate：**同一 snapshot 上，如果 shared planner 已能产出 selectable candidate，capability 不能回答 NEEDS_HYDRATION/HYDRATABLE。**
5. coverage 仍然必须展示，UI 文案应是类似“可规划，夜生活/住宿数据仍不完整”，不能再显示“这个城市还要灌数据”。
6. 后台 enrichment 可以继续，但不能阻塞一个已经 READY 的城市。

所以这条实际上是 **A + 对 B 的正确部分吸收**：不是拿 lodging/nightlife 永久踢出 readiness，而是让 readiness 只看“当前是否足以形成真实可选计划”，完整度单独说。

---

## R10 — 禁止把 `unresolved:<hash>` 当 canonical identity；原始目的地输入和规范身份必须分离

当前这个形状：

```
canonical_destination_id = unresolved:8fcc...
city_code = CN-云和县
```

两个都不应继续作为新写入的“规范身份”。

### 冻结规则

1. **`canonical_destination_id` 只有 resolver 成功确认规范地理实体后才能有值。**
   unresolved 时必须是 `null`，不能塞 hash 占位。

2. `unresolved:<hash>` 如实现上需要，只能是：
   - request correlation key
   - hydration fingerprint 的临时输入摘要
   - diagnostic token

   **不得**作为：
   - canonical destination identity
   - Journey 的 durable city identity
   - provider entity identity
   - UI 回显给用户的城市身份

3. Journey 必须把用户原始输入与规范身份分开。至少语义上有：

```
destination_input: "云和县"
destination_resolution_status:
  RESOLVED | UNRESOLVED | AMBIGUOUS
canonical_destination_id: null | <real canonical id>
canonical_display_name: null | <resolver-backed name>
```

字段名可按现有 schema 适配，但语义不能再混。

4. **新 Journey 写入不得再把任意字符串直接升级成 canonical city_code。**
   允许用户先保存 DRAFT，但它是“带原始 destination_input 的未解析 Journey”，不是“已经拥有一个伪造 CN-xxx 规范城市”。

5. resolver 成功后：
   - 原 Journey id 保持不变；
   - 只补上 canonical identity / display name / resolver provenance；
   - hydration/planning 从这个规范身份继续。

6. resolver 暂时不可达：
   - 走 R1：runtime failure / retryable；
   - 不能持久化 hash identity；
   - 不能判成结构性 UNAVAILABLE。

7. resolver 成功但返回多个合理候选：
   - 状态 = AMBIGUOUS；
   - 返回候选给用户/上层选择；
   - 不准模型或后端悄悄猜一个。

8. resolver 成功且明确 0 candidate：
   - 才允许 `NO_CANONICAL_IDENTITY`；
   - `canonical_destination_id=null`；
   - 可按产品语义给 UNAVAILABLE，但必须说明“无法解析此目的地”，不是伪造一个 hash 城市继续跑。

9. 现有 legacy Journey 里已经有任意字符串 city_code 的，**禁止删除/重建**。做兼容读取 + 后台/按需 backfill；解析成功就附 canonical identity，解析失败则保留原始用户文本并标记 legacy/unresolved。不要拿 schema 清洁度换用户数据。

### ORD-0127 的硬门
至少钉：
- unresolved query 不产生 durable `unresolved:<hash>` canonical id；
- 新 Journey 不把 raw text 直接当 canonical city identity；
- Photon 单一明确候选 -> same Journey 原地 RESOLVED；
- Photon 多候选 -> AMBIGUOUS，不猜；
- resolver outage -> retryable runtime failure，不写 hash；
- legacy raw city_code Journey 不丢、不重建；
- capability/hydration/planning 只在 canonical identity 成立后进入真正城市数据流程。

**冻结句：raw destination text 是用户输入，不是身份；hash 是相关键，不是身份；canonical identity 必须来自可追溯 resolver 事实。**

另外，ORD-0125 的 demo/reset P0 我支持继续压最高优先。当前已证实它删过用户 Journey，在它变成“只删 demo seed 派生数据 + preserved_user_rows 可证”之前，不应再拿 live user DB 跑会触发 reset 的 M1-M4 全链。