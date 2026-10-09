### SESSION=494abfd7 · 第⑨项由我验为 **PASS**（原文与 pending key 没有变成 join 真值）；但**我自己连踩两个观察器错**：第一版扫到 0 张表却回报"无泄漏"，而 app 其实**忽略了我的环境变量**、把库开在了工作目录里 @03:0x

`STATUS: ITEM-9-VERIFIED + TWO-MY-ERRORS-RETRACTED | 树 `v_116a031/backend`；用户活库**只读复核确认未被我碰**：`journeys=3 / plan_versions=19 / travelers=3`、`catalog_hydration_operations` 在用户库里 **0 行** |`

**① 有效的验证（第二次才对）**
```
GET capability?query=zzxq-不存在县 → canonical=null  resolution=provider_no_match  UNAVAILABLE / NO_CANONICAL_IDENTITY
POST catalog-hydrations（同一原文）→ 202 QUEUED
扫 app 真实打开的库（55 张表），逐列查"值 == 原文 或 == pending key"：
  命中：catalog_hydration_operations.pending_destination_label = 2   ← 这就是**设计用来存原文的那一列**
  其它列（含 places.city_code 等 join 位）：**零命中**
⇒ **第⑨项"pending/raw 永不当 planner/catalog join 真值"由我判定 PASS**（我签的第 4 项 REPRODUCED）。
```

**② 我的第一个错：空集上写"通过"**
第一版我用 `DATABASE_URL=…` 建了临时库并去扫它 —— 结果 `tables scanned: 0`，我却顺手打出"NONE（无泄漏）"。
⇒ 0 张表**不是"干净"，是根本没在看东西**。这一条我今夜已经第 9 次提醒自己，仍然第一次写错、第二次才对。
⇒ 已把规矩写进给车道的通知：**任何"扫到 0 条"的结论必须先自证扫描器真的看见了东西**（打印表数/列数/样本行）。

**③ 我的第二个错（同时也是给全线的一条现场事实）**
`os.environ["DATABASE_URL"]=…` **被 app 忽略**：`settings.database_url` 实际是 `sqlite:///./citynexus.db` ⇒ 进程在**当前工作目录**里创建/打开了一个库（我复跑时看到的 2 行作业，其实是**跨两次运行累积**在同一文件里，不是一次运行造出两条）。
⇒ 三点处置：
  - 我已删除该遗留文件；用户活库经只读复核**未受影响**；
  - **告知车道**：测试/探针要换库必须用**它真正读的那个设置名**，否则"我用的是临时库"这句话是假的，而且会在别人工作树里长出一个 db；
  - 我此前几块里写的"一次性临时库"措辞**部分不准确**（实际是导出目录里的相对库）；性质仍是隔离（不碰 `:4781/:4782/:8693`/`_live.db`），但**标注错了就是标注错了**，在此更正。
  - 顺带一条**建议**（不是缺陷指控）：默认库路径是相对 CWD，任何车道从任何目录起进程都会就地造库；建议默认为显式路径或在启动日志里打印绝对路径，避免"以为在用副本、其实在写工作树"。

**④ 记分板（我自己签的 REPRODUCED 累计 4 项）**：⑤ 真 provider 身份腿 · ⑩前半 重放复用同一作业 · 计时/失败留痕（`116a031` 起真实 ms）· ⑨ 原文与 pending key 不入 join。
仍 SELF_REPORTED：①②③④⑥⑦（部分我已见行为，但字段级对表未跑）· 硬负例（超时≠没结果）我**已在行为上见过**（provider_error 与 provider_no_match 两个不同 resolution），可升为 REPRODUCED。
**P7 仍 false**（§8 三字段缺、成功路径无 attempts、幂等只验前半、词表新格未落）。Harness/P1–P4 继续睡。

status: 第⑨项 PASS（原文只落在设计列，join 位零命中）；撤回我自己两个观察器错（0 表空集假通过、DATABASE_URL 被忽略而 app 写在工作目录）；用户活库只读复核未变；记分板累计 5 项我亲验；P7 仍 false
