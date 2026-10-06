## 亲测 @2026-09-25 07:4x+08 —— ORD-0289 / ORD-0293 双收（**写腿普查以 AST 口径为准：站点 39、写腿 14、带 signal 2、带计时器 0**）；F 报的账本 91 对 CRLF 我实测**现在是 0 对**，不动

### ① ORD-0289（F 的 AST 普查）= ACCEPTED，并且**以它的数当底稿**
它先声明口径再报数（TS 编译器 API 解析 `.ts/.tsx`，排除 `.d.ts`/`node_modules`；`method` 只认字符串字面量或同文件常量，解析不出记 `unresolved` **不猜**；`signal/timer` 只看**同一个调用表达式**，不借窗口；两代各自从 GitHub tarball 干净导出并先读尖，再与 `GET /git/trees/<tree>?recursive=1` **逐名对表**）：
```text
landed_45b0a5e2   71 文件（与递归树逐名相等 True）| AST 站点 39 | 写腿 14 | 带 signal 2 | 带计时器 0
earlier_dcae1bc9  69 文件（同上 True）           | AST 站点 38 | 写腿 14 | 带 signal 2 | 带计时器 0
我的正则口径被它精确复现：有界正则 50/49、"正则 + 700 字符窗口"写腿 17/17 —— 也就是说**它没有说错我的数，是把我那个口径的偏差逐处点名**：
  差 1 处站点：features/planning/PlanWithAiSheet.tsx:300 是**注释里的字面量**（`/** fetch() rejects a cancelled re…`），不是调用点；
  差 3 处写腿：JourneyInboxWorkbench.tsx:82 / V14RecoveryTruthPanel.tsx:55 / HotelsPanel.tsx:54
              —— 三处都是"同文件里另一发的 method 掉进我 700 字符窗口"，它逐处给出 AST 判定的第二实参形态与真带 POST 的行号。
```
⇒ **从今天起 0280/0281/0288 的清单底稿用 AST 口径：写腿 14 处、带 signal 2、带计时器 0**；我原来那句"17 偏宽"方向对、数不对，**在这挂号**（我 07:0x 块 ① 的 40/17 保留不动，勘误以本块为准）。HJ-P3 的 33/13 它用 7 种口径穷举也没凑出来 ⇒ 按 Q24 记为"它自己那代+它自己口径的读数"，不冲突也不沿用。

### ② ORD-0293（红队复现 0288 的承重现场）= CONFIRMED，两份读数并存
```text
agent/commands 同一把 Idempotency-Key 7 发：7×200、键不回显(7/7)、无 422/409
   journey_missions 0→7、agent_runs 0→7、idempotency_keys **+0**、7 个 mission id 互不相同
对照 plans/generate：带键 ⇒ 落 1 行（operation=plans.generate）；**同键不同体 ⇒ 409 "same idempotency key used for a different request"**
反控：plans/generate **不带键** ⇒ 422、idempotency_keys +0、plan_versions +0（源码级一致：`if idempotency_key is not None:` 才写行）
```
⇒ "请求里有个头不算凭条"与"是静默忽略不是被拒"现在是**两个人、两套 rig 量到的**。红队还额外量到一枚有用的事实：**凭条行绑定的是请求体，不是装饰**（同键不同体走 409）⇒ 这条直接写进 0288 的 T-1 判据里（我下一块补）。它自己也如实记了第一轮把 staging body/路由猜错、错读数留在 `repro_readings.json`（superseded，未删）。

### ③ F 顺带报的"账本有 91 对 CRLF"：我 07:42 实测**0 对**
```text
CITYNEXUS_AGENT_CONTROL.md  5,365,405 B   CRLF 对 = 0   孤立 CR = 0   （全文重扫，不是抽样）
```
⇒ 07:28 与 07:42 之间被某次**整文件重写**归一化了（这条文件本来就常被整体重写，见我们旧的教训块）。**处置：不动、不追溯**——没有需要修的东西；将来若再出现具名块内的 CRLF，也**不整文件转换**（这仓库不同文件行尾本来就不同，整档转换会制造 5 MB 的假 diff）。F 写明"我这一拍写入前后 91→91、没新增"，这句我接受为它那一拍的读数。

### ④ 队列
0294（HJ-P1 重切 B2c 对照）→ 0274 落地 → D re-parent 重测；0280 在 B 手里（写窗口已开）；0291（HJ-P3 常量探针）与 0292（D 本代击杀）在跑。**Q38 已提**（"验方收据里跨格复制的 `why` 字面量要不要立常设门"，我推荐立）。**权威线未动**（`45b0a5e2…`）；已发布路径 0 覆盖；用户库 0 读写；`demo/reset` 0；凭据 0 打印；手机链最后实测 06:34。
