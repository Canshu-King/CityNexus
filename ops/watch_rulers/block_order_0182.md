- id: ORD-0182
  to: 8c66aa92
  priority: high
  if_head: 82f136f
  order: |
    【**本单取代 ORD-0181 的 (A)/(B) 提问** —— 仲裁 5763138225 已拍：**一张 C 单、两张表同修，服务端过滤**；前端过滤只许当过渡桥。
    合同原文我已 REST 拉回并**字节校验**：`D:\moodle\_qoder_cmdr_ref_20260921\arbiter_docs\list_status_filtering_policy.md`
    （`docs/list_status_filtering_policy.md` @ `63ac93eb`，+146 行，5622 B）。
    冻结句：**"Filter collection state at the server boundary; let clients choose the view, not redefine the truth."**】
    查询合同（照做，别再自己发明形状）：
    - replans：`?status=PRESENTED`、重复传 `?status=PRESENTED&status=GENERATED`；合法枚举沿现有 API：
      `GENERATED / PRESENTED / ACCEPTED / REJECTED / EXPIRED / INVALIDATED`
    - plans：`?status=CANDIDATE`、`?status=ACTIVE&status=SELECTED`；枚举 `CANDIDATE / SELECTED / ACTIVE / SUPERSEDED / REJECTED`
    - 规则八条：不传 ⇒ **当前全量行为逐字段不变**；单值 ⇒ 只返该状态；重复值 ⇒ 同实体内 **OR**；
      合法但无命中 ⇒ `200 []`；**非法 status ⇒ typed 422/validation，不得静默忽略、不得回全量**；
      **过滤必须进 SQL/ORM query，禁止"全查出来再在 Python 里滤"**；Journey scope 与 status 做 **AND**；
      排序不变（replans 按 `created_at`，plans 按 `version_no`）。
    15 条验收门（仲裁原列，逐条交）：
    1-3 replans 不传不变 / 单值精确 / 多值并集；4-6 plans 同三条；7 合法无命中 `200 []`；8 非法 typed validation；
    9 **别的 Journey 同状态绝不泄漏**；10 过滤后排序不变；
    11 accept/reject 之后下一次 `status=PRESENTED` 不再返回该 proposal；
    12 plan 状态迁移后过滤读到持久化的新状态；
    13-15 三条突变必红：**删掉 replans 谓词仍 200** / **删掉 plans 谓词仍 200** / **非法 status 被静默丢弃后返回全量**。
    边界（仲裁原话，别越）：**不要为"一张单"造通用查询框架** —— 一张 ORD、两条 endpoint、两套各自合法枚举、同一种过滤合同。
    并且**列表过滤只是 view/query 语义**：`accept`/`reject`/`select` 这些 mutation 仍必须重查当前状态、C4、单 ACTIVE、幂等 ⇒
    **`status=PRESENTED` 绝不是授权 token**。
    顺序：ORD-0167 > 0158 > **0182** > 0176 > 0175 > 0125（NOT-STARTED）。报数口径照 `test_execution_truth_policy`。
  status: DISPATCHED@2026-09-21T23:4x+08 by 494abfd7（**取代 ORD-0181 的提问形式**；合同与 15 门逐条来自仲裁 5763138225，我只做了转录与本地字节校验）
