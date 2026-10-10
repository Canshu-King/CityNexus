## 号令 @2026-09-25 06:5x+08 —— **放行 @B 开 ORD-0280 写窗口**；ORD-0274 收尾已收（候选 `ef277b2da5df`，我按你自证口径复核了能复算的那几格）；**Q35=② 已落地**；新单 **ORD-0290** 派 @HJ-P1

### ① 放行令（写给 @B `c01d72a3`）
```text
ORD-0280 写窗口现在开。范围与判据不变（账本 05:2x / 05:4x 两块）：
  只改 frontend/src/features/planning/PlanWithAiSheet.tsx 的 :515 / :573 / :629 三处"往归因标签底下塞客户端拼的话"，
  标签本体 :882「服务器给出的原因 / Reason the server gave」不动语义、不挪位置；
  统一修复模型用仓库里现成的 simulationAdapter.ts:145-155（said ? 引原话 : 明说不替它编造原因）——**不要自造新方言**；
  一处一笔 commit（0280-a/b/c 三笔可以，但**不许顺手改 0274/0278/0281 的文件**）；
  每处都要一枚反例：服务器无文案时屏上**不得**出现 `HTTP <code>` 顶在标签下（服务端字段与渲染文字两侧同判，
  这是 0262 那枚坑：漂亮 JSON ≠ 用户看见的那句）。
  0281 产码排在 0280 之后（判据已按 Q33=① 拆成 0281 有键那一支 + 0288 无键那一支，先做 0281）。
你 0274 的候选 ef277b2 我收到了，见 ②；那条链的 derived_result 我不自己签，已开 ORD-0290 派 HJ-P1。
```

### ② ORD-0274 收尾（B @06:25 + 勘误 @06:28）我这一拍核到的
```text
候选  ef277b2da5dfff22ae3f1deaf63b295f5cda678f  refs/heads/review/0274-b2c-c   （旧枝 853c549… 原样未动，B 未 force-push）
基线  权威尖 45b0a5e2（我先读，仍是它）；候选父链按 %p：ef277b2 ← 45a3d56 ← 69fd2f8 ← 45b0a5e
内容  4 files, +116 / -9：frontend/src/api/citynexus.ts, app/V8Experience.tsx, lib/inFlightWrites.ts, main.tsx
patch-id  新旧两代 `<base>..<tip> | git patch-id --stable` = ab2d9690eb4d… 两侧相等 ⇒ re-parent 没改内容（这条 B 自己算的，
         我认可方法：patch-id 正是"同一改动换父"的判据）
Q24  逐格 = **0 格撤回**，但引用行号平移（1717→1717 / 185→186 / 890→897），且 B 明确用"引用区间字节摘要"而不是整文件对等
勘误  B 自报上一块把 `git log A..B`（本就新在前）又反转了一次 ⇒ 单独发勘误件，`was` 是从账本那一行**取出来**的而不是回忆，
     端点 evidence/ord0274-reparent-laneB/ord0274_reparent_erratum_ancestry.json blob 19ce9e5d710ce679a275d64ad5ff2cfe39e2779a
```
⇒ 候选**形状成立**，等 ORD-0290 的 `derived_result` 才谈落地；我不提前动权威线。

### ③ Q35 = ②（窗口 06:50 实测单字符「②」；总线仍无章 ⇒ provisional）
已把路径通知 @F：**0287 继续走"只依赖权威线"的守卫回归测试**（测现成的具名 409 与"不覆盖别人回执"，不引 `_fill_plan_generation_receipts`），ORD-0289 排其后，不并行。若 ② 也需要动产品码，仍按第 0 条口径具名停手。
**HJ-P3 的硬链接修复我已独立量过**（06:35 同尺 `hits 35→0 rc=0`；nlink 2→1、新 inode、mtime 06:23:04/20；**我在服的 index.html inode 未变**）；它另外把自己上一轮"共享 outDir 被半同步"的错误归因改成硬链接，并把"起面前先跑 hardlink_audit"变成它自己的前置——**这是今天第三条被车道主动收回的错误结论**，形状都记在这里，别让它只留在聊天记录里。

### ④ ORD-0290 · B 的 0274 候选派生 · @HJ-P1（`1a986a24`，冷；这三臂的 derived_result 依 B 自己的口径归你）
```text
被验对象：你在收据里**自己先读到**的那一枚尖（不是 B 报的那一枚）；我 06:5x 读到 review/0274-b2c-c = ef277b2da5dfff22ae3f1deaf63b295f5cda678f
任务：对 B2 / B2b / B2c / B3 / A 五臂逐臂签 `derived_result`（B-1：只有 verifier 的 derived 能闭）：
 每臂给 (sha, nodeid, shape) 三元组 + 同键前件；一臂红三条 ≠ 三份证据；composite 与 mainline 分格写。
 树来源：GitHub tarball 或 `git archive <tip>`，先读尖；不许用 B 的工作树；一次性库带 run id、fresh-or-no-run。
 反控必须**双向**：还原那一处改动 ⇒ 该臂必须绿；不还原 ⇒ 红。做不到就说明射程，不写 KILLED。
 发布 evidence/ord0290-0274-derivation/；账本块 + 总线一条；权威线不动、已发布路径 0 覆盖。
```

### ⑤ 队列（现在这一秒）
B → **已放行，开 0280** ｜ 红队 → 0286（D 的 0278+0253）｜ F → 0287（②路线）→ 0289 ｜ HJ-P3 → 0288 定形（刚点名）｜ HJ-P1 → 0290（本次点名）｜ D 等 0286。
**权威线未动**（`45b0a5e2…`）；已发布路径 0 覆盖；用户库 0 读写；凭据 0 打印；手机链两面 200 + 无凭据 401（06:34 复测）。
