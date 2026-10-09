## 号令 @2026-09-25 07:2x+08 —— **ORD-0293 派 @红队**：独立复现 0288 那条"键被静默忽略"的现场读数（我自己只能核静态部分，那三发是真 POST）

### ORD-0293 · 第二观察者复现 · @红队（`d2305848`，0286 已交、现 ready）
```text
要复现的主张（来自 HJ-P3 的 ORD-0288 定形，总线 5823596418）：
  在同一趟新行程上，同一把 Idempotency-Key 连发三发 POST /api/v1/agent/commands
    ⇒ journey_missions 0→3、agent_runs 0→3，而 idempotency_keys **一行都不多**；
      7 次请求得到 7 个互不相同的 mission id（零重放），响应不回显这把键；
      对照：POST /plans/generate 带同一形状 ⇒ +1 行 idempotency_keys（operation=plans.generate）。
  判论："请求里有个头不算凭条"，而且是**静默忽略**（不是 422/409）。

为什么值得你再跑一遍：这条读数是 0281 / 0288 排产的承重墙，而我只核了静态那一半
  （alias 行号 [4606,7740,9907,11364] 一致；def run_agent_command 在 1058；
   `WRITE_DEADLINE` 全 frontend/src 0 命中；validate_idempotency_key 在 validators.py:109）。
  动态那一半必须是第二个人的，不然它就是"一个人的读数"。

判据：
 1) 树：先读权威尖（应为 45b0a5e2…）并从 GitHub tarball/`git archive` 干净导出；不许用任何车道工作树。
 2) 一次性后端 + 一次性库（`_*.db` 带 run id、`ensure_schema()`，fresh-or-no-run）；
    **0 demo/reset、0 用户库读写**；行数以**第二条 sqlite 连接**读，不用 HTTP 响应推断。
 3) 三格：R-1 同键三发的三张表行数；R-2 对照支（plans/generate）确实落 `idempotency_keys`；
    R-3 键是否回显/是否被 422/409 拒绝（今天预期是 **200 且无回执** = 静默忽略）。
 4) 双向防空转：再对 plans/generate 那一支做一次"把键拿掉"的反控 ⇒ 它应当**不再落回执行**；
    否则说明我的表读法本身在骗我。
 5) 若与 HJ-P3 的数不一致：**两份读数并贴**，具名你的端口/库/run id/树 sha，不许覆盖它的收据。
 6) 发布 evidence/ord0293-keyless-leg-repro/；账本块 + 总线一条；权威线不动、已发布路径 0 覆盖。
成本 20~30 分钟（一台一次性后端 + 几次 POST）。
```

### 现场与坐标（07:2x）
- 尺 r7 已发布：`live_checks/audit_closure_coordinates_r7.py` `7fd9b43dcb60d1f4419000cfba9f50db473d65bd`（17,650 B）⇒ **claims=107 failing=0 rc=0**，其中**可核对的申报 89 枚**、**存在性枚举 18 枚**（后者 cited_by 带 `ENUMERATED(existence only…)` 前缀，我自己把这类混进来就是永真格）。收据 `evidence/commander-coordinate-audit/audit_r7_receipt_r1.json`（43,843 B，`ref_tip_read=1b605858b4ed…`）。
- **Q36 已提**（写期限常量的默认值该不该 > busy_timeout）；HJ-P3 那两条我复现不出来的读数已退回它对表，**我不拿未复现的机理排产**。
- 车道：B running（0280）｜ F running（0287②→0289，队列 3）｜ HJ-P1 running（0290）｜ D running（0292 + 冻结 ref）｜ HJ-P3 running（0291）｜ 红队 → 0293。
- 权威线未动（`45b0a5e2…`）；手机链最后实测 06:34 两面全 200 + 无凭据 401；`demo/reset` 0 次；凭据 0 打印。
