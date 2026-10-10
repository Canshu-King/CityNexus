## 亲测 @2026-09-25 08:2x+08 —— B 的 ORD-0280 候选 `48827a9d` 我做的是**静态核对**（逐行读，没跑）：**结构过关，但"绿"一个字都没说**——这条规格至今没有任何一次运行记录

### ① 我实际读了什么（文件与行号都来自那次 `git show`，不是我复述）
```text
frontend/src/features/planning/PlanWithAiSheet.tsx（候选版全文 12 处 failureReason，逐处点名）
  362 类型改成 FailureNote = {text, from:"server"|"device"}
  536 / 597 / 622 / 708 四处赋值：agent-commands、GET /places 不可读、<2-places 计数、mission.failure_reason
  721 / 725 两处显式 null；913 / 918 两处渲染条件；929 取 from、931 按 from 选标签文案、939 渲染 text
  ⇒ 计数（`grep -n failureReason` 实际输出）：候选版 **12 处**（上面 11 个行号 + 362 的类型声明行）；父版 **10 处**
  ⇒ **没有一处再把对象当字符串渲染**
```
```text
新规格 frontend/e2e/qoder-ord0280-attribution-label-speaks-for-itself.spec.ts
  127-129：label 与 reason 都取 `innerText()`（屏幕上真正那行字），origin 取 `data-reason-origin` 作第二见证
  154-157：server 臂 ⇒ label === "服务器给出的原因" 且 origin=="server"；device 臂 ⇒ label 不等于中英文两种标签 且 origin=="device"
  162：server 臂还要求 reason 与服务端句子 **`===` 逐字节相等**（不是 `in`，正是我要的那一条）
  167：device 臂还要求"那行读数仍然可见"（reason.length>0）⇒ 这不是"把数字抹掉"的假修
  臂集合：A1(device) / **A2(server 正控：服务器给了句子就必须逐字挂到标签下)** / B1 / C1 / D
```

### ② 结论（写清楚是哪一档，别越界）
```text
STATIC_REVIEW = PASS   —— 形状、覆盖面、比较符、两侧同判（渲染文字 + 服务端字段）都成立
GATE_EXECUTION  = 0 次 —— 这条规格**没有跑过**，所以我不签任何绿；它还需要真起 face（e2e 跑在 npm dev 上，
                          按既有纪律那类读数不能当发布级证据，只能当"规格自己会红/会绿"的证据）
```
⇒ 交给 @B（或谁接）做一次**带收据的运行**：干净导出上跑这 5 条臂，`claimed_result` 自写、`derived_result` 留 null；
并加一枚**反件**：把 `from` 恒置为 `"server"`（模拟"标签不看来源"的旧行为）⇒ A1/B1/C1/D 必须全红；
只有正控红、反件也红的收据我才会机械地签 derived。收据走 `evidence/ord0280-attribution-run/**` 新路径。
**候选 `48827a9d` 不许重推**（父位就在现尖上，等 0274 落地后按 Q40=① 由我处理——但它是 2 个文件，超出 Q40"单文件"那条，所以**这一笔仍归车道 re-parent**，我把这句话也挂号，免得我偷用 Q40）。

### ③ 队列
等 ORD-0294（HJ-P1，08:18 重敲）→ 跑 r2 尺 → 落 0274 → 我自 re-cut 落 0287（单文件，符合 Q40=①）→ 才做换代；
ORD-0295（红队，08:18 重敲，含"对我这把尺做红队"）、ORD-0296（F，08:24 下发）在跑；D 的 0278/0253 仍拦停等 derived。
**权威线未动** `45b0a5e2…`；本节 0 次 PUT；用户库 0 读写；`demo/reset` 0；凭据 0 打印；手机链 07:49 HEALTHY / 08:19 READY_TO_SWITCH。
