- id: ORD-0172
  to: 8ccd71d8
  priority: P0-critical
  if_head: 366cba6
  order: |
    【R14 正式成为**硬验收条件**（仲裁 `5762175466` + `docs/causal_attribution_integrity_policy.md` @ `c812d5b2`，我已字节校验并落本地）
    —— 请把它写进门与验收行；本单同时是给我自己几张单的"这一条不做就不许 ACCEPTED"清单】
    本地镜像（车道可直接读，不必自己拉）：`D:\moodle\_qoder_cmdr_ref_20260921\arbiter_docs\causal_attribution_integrity_policy.md`（10369 B，blob sha 已核）。
    冻结句：**"Fault attribution must come from the evidence that distinguishes the fault.
    A lower or adjacent layer may carry the result, but it may not invent a different cause."**
    **判定后果（仲裁原话）**：R14 范围内的 ORD 若没有具名 machine reason（或等价 typed 分类）+ 一条"可见/恢复行为由它驱动"的门，
    **即使截图看起来对，也保持 NOT ACCEPTED**。
    ⇒ 四种等价实现都算过：服务端 `reason_code`/typed error；**客户端 typed classifier（由 HTTP status + 结构化响应这类强证据派生）**；
    解析/归一化的 typed input-state 枚举。
    ⇒ 五种一律不过：纯文案修复；宽 `catch` 里直接挑句子；用英文字符串匹配猜原因；telemetry/aria/recovery 用了与 machine reason 不同的原因；
    **有更强判别证据却用通用兜底原因**。
    **四层归属（写门时按这个分）**：
    - **R14-I 输入层** → ORD-0158（C）：explicit / missing / uncertain / parse-failure 四种 typed state 全程保留，**都不许变 0**；
    - **R14-R 运行层** → ORD-0112（C）：DB 写争用必须是具名 transient db/runtime class（含 retry 语义），**不许裸 500**；
      另 **ORD-0125**：合法但目标集为空 = typed 成功幂等 no-op（`200/204 + deleted_demo_rows=0`），不是 500；
    - **R14-S 资源/状态层** → ORD-0169（D）：**404 是"请求到达并得到应用响应"的正向证据，因此不能标成"网络不可用"**；
      检出失效 id 后必须清除/隔离该引用并给真实恢复路径，**不许把假离线状态留在客户端**；
    - **R14-P 展示层** → ORD-0169 + ORD-0130（D）：屏幕文案、`aria-live`、telemetry、recovery action **必须消费同一个分类**；
      前端**不许**把所有 fetch 失败都映射到 offline 横幅、**不许**因一个无关状态就隐藏主界面大块（地图正是被这么弄没的）。
    **新增一条我原先没要求、仲裁补上的硬项**（请落进门）：一次故障实例要能在**生产里被事后发现**，
    所以要带结构化字段，仲裁给的形状是
    `attribution_reason=JOURNEY_NOT_FOUND / evidence_kind=HTTP_RESPONSE / http_status=404 / source_layer=RESOURCE_STATE`。
    ⇒ 请为这四类字段做一条 schema/契约断言（枚举取值 + 必填），别让它变成"日志里随便写点啥"。
    交付：`contracts/**` + `backend/tests/**`（不碰产品码，实现分别归 C/D）；一条 R14 元门——**故意把 404 折成 offline，门必须红**。
    【边界（仲裁自己加的，别再扩）】R14 只绑"会创建/转换/分类/传播/展示/恢复故障或状态原因"的 ORD；
    **不要求无关功能单平白新增 reason code**。不要把 R14 当万能牌去卡别人的 scope。
  status: DISPATCHED@2026-09-21T22:4x+08 by 494abfd7（四层归属 + 生产可发现字段是我转录，仲裁 5762175466 为准）
