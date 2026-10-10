- id: ORD-0223
  to: 8c66aa92
  priority: normal
  if_head: 8b9ea04
  order: |
    **通用约束写入的新词表守卫（仲裁 `5780322197` 新开单，与 ORD-0219 分开）。**
    裁决原文：**"要设防，但不要复用 `CAPABILITY_CODES`；通用 `/journeys/{id}/constraints` 的合法词表归一个中立的
    `ConstraintRuleRegistry`（约束域单一真值源），`ConstraintInput` 只按该 registry 校验 `rule_code + kind`，
    capability 只是其中一个子集，feasibility/scoring 只消费 registry 的执行元数据。"**
    它独立核过：`ConstraintInput.rule_code` 仍是自由 `str`；通用 feasibility 明确认得 `BUDGET_MAX` / `JOURNEY_END_BY` /
    `LOCKED_COMMITMENT` 等**非 capability** 规则 ⇒ 把 `CAPABILITY_CODES` 直接套过去会误杀合法写入。
    最小落法（照录）：
    ```text
    ConstraintRuleRegistry (neutral domain module, no schemas/main/feasibility imports back into it)
      code
      allowed_kinds: {HARD, SOFT}
      execution_layer: FEASIBILITY | SCORING | CAPABILITY | ...
      hard_executable: bool

    ConstraintInput:
      unknown code                    -> 422 UNKNOWN_RULE_CODE, 0 row
      known code + disallowed kind    -> 422 RULE_KIND_NOT_ALLOWED, 0 row
      HARD + hard_executable=false    -> 422 HARD_RULE_NOT_EXECUTABLE, 0 row
      otherwise                       -> handler may persist
    ```
    `UNSUPPORTED_HARD_CONSTRAINT` **继续留在 feasibility**（兜历史脏数据/旧版本/防御性读取），**不再充当新写入的正常校验器**。
    验收：三条 422 各一条正例/反例（合法 SOFT 写入仍 2xx、非法 kind 拒、HARD 不可执行拒）＋ 0 行落库读回 ＋
    一条突变（把 registry 的 `hard_executable` 翻真，门必须红）；反例走 `mutation_anchor_guard.py`。
    **排程**：这是并行单，**不阻塞 ORD-0219**；你名下 ORD-0213（产品并发根因）仍是最终 CLOSED 的闸门，优先级高于本单。
  status: DISPATCHED@2026-09-23T00:44+08 by 494abfd7（来源＝仲裁 `5780322197` 第七十五次敲门回执）

## commander 转达 @2026-09-23T00:44+08 —— 仲裁接受我的更正与裁定，并把三件事钉死：**constraints 新单**、**撞车移植边界**、**HARD_EXECUTABLE 派生等式**

### ① constraints 路由：**新开 ORD-0223**（不复用 `CAPABILITY_CODES`）

裁决照录进 `- id: ORD-0223`：中立域模块 `ConstraintRuleRegistry`（**不许反向 import schemas/main/feasibility**），
`ConstraintInput` 按它校验 `rule_code + kind`；三格 422（`UNKNOWN_RULE_CODE` / `RULE_KIND_NOT_ALLOWED` / `HARD_RULE_NOT_EXECUTABLE`）各 0 行落库；
`UNSUPPORTED_HARD_CONSTRAINT` 留在 feasibility 兜历史脏数据，**不当新写入的正常校验器**。**与 ORD-0219 分开，不阻塞它。**

### ② 撞车移植边界（它把我的裁定细化了，照录）

```text
KEEP product truth（B）:
  B fixture facts in data/mock/places.json
  B producer -> metadata.accessibility_evidence
  B server-stamped DEMO provenance

PORT from C（只搬独有断言）:
  1) stroller/luggage 单点事实不得把整条记录洗成 STEP_FREE verified
  2) PASS/BLOCK 期望集合按候选现算，不按 plan 序号写死
  3) 对应的 tripwire 突变

DO NOT PORT:
  C 的 DEMO_ACCESSIBILITY_EVIDENCE 常量
  C 的 metadata['accessibility'] 生产者路径
```
它原话：**"否则嘴上说『只留一把尺』，代码里还是两套数据源，只是其中一套穿了测试文件的马甲。"**
**移植后的最小验收**：让 **B 的一份门**吸收 C 的这两条独有断言 → 重跑 B 的 8 门/6 臂 → **新增那条 laundering tripwire 的 killer** → **重复门删掉**（不是两套测试文件永久并存）。

### ③ `HARD_EXECUTABLE_CAPABILITY_CODES`：按 C 量到的等式实现，不写第四份名单

```text
HARD_EXECUTABLE_CAPABILITY_CODES = frozenset(CAPABILITY_CODES) - SOFT_CODES
feasibility 侧 _CAPABILITY_GATE_CODES 最终直接复用/派生同一来源，并留 parity test 防漂移
```

### ④ 现场

working tip `8b9ea04`；链三条端口在听；`P7=false`；reference tip `c0d7e3d`；P0 未动（用户库 3/3/19/1/1）；那把 key 仍未轮换。
