**值守 02:17 · 两件事要摆在明面上：单号被重复派了 6 组，而且账本里出现了第二个号令者实例。**

一、单号重复（`ORD-04xx →` 形式的派单行，全账本本轮扫，行号=文件行号、会随重写漂移）：
- `ORD-0406` 出现 `2` 次：`CITYNEXUS_AGENT_CONTROL.md:18776`→车道 `e4f3490f`（组件硬兜底 i18n 化那条，正在跑，你那单的产品码; `CITYNEXUS_AGENT_CONTROL.md:21276`→车道 Q（`a68b0631`，本单的几何已经在你手上）：`今天` 屏那条安全提（**收件人不同 ⇒ 同一单派给了两条车道**）
- `ORD-0407` 出现 `2` 次：`CITYNEXUS_AGENT_CONTROL.md:19044`→车道 N3：`review/N3-ord0407-empty-state-act; `CITYNEXUS_AGENT_CONTROL.md:21182`→车道 N3（`49fe0d7b`；若你在忙 ORD-0388 那条字典线，任意空（同一收件人 ⇒ 是同一句话被写了两遍）
- `ORD-0410` 出现 `2` 次：`CITYNEXUS_AGENT_CONTROL.md:18775`→车道 `49fe0d7b`（复制链接那条，正在跑）：地图上「回到行程视野」按下去; `CITYNEXUS_AGENT_CONTROL.md:19949`→车道 3b65af59（地图线，控件是你新加的那枚）：「回到行程视野」这枚按钮按（**收件人不同 ⇒ 同一单派给了两条车道**）
- `ORD-0422` 出现 `2` 次：`CITYNEXUS_AGENT_CONTROL.md:17291`→车道 `904a042d-51c9-4291-89ca-5d420afe419e; `CITYNEXUS_AGENT_CONTROL.md:17413`→车道 `904a042d-51c9-4291-89ca-5d420afe419e（同一收件人 ⇒ 是同一句话被写了两遍）
- `ORD-0423` 出现 `2` 次：`CITYNEXUS_AGENT_CONTROL.md:17292`→车道 `a68b0631-cf5a-435d-93d7-b8dc438d9656; `CITYNEXUS_AGENT_CONTROL.md:17417`→车道 `a68b0631-cf5a-435d-93d7-b8dc438d9656（同一收件人 ⇒ 是同一句话被写了两遍）
- `ORD-0424` 出现 `2` 次：`CITYNEXUS_AGENT_CONTROL.md:17293`→车道 `1d64acf5-3f5f-48e8-a7b4-9d7a37996edb; `CITYNEXUS_AGENT_CONTROL.md:17423`→车道 `1d64acf5-3f5f-48e8-a7b4-9d7a37996edb（同一收件人 ⇒ 是同一句话被写了两遍）
- 合计：`25` 个单号有派单行，其中 `6` 个不止一次。号令者在 00:5x 那块块头里已经具名写过「我自己撞了号」，这条只是把范围量出来：不止那一组。

二、第二个号令者实例：`### CMDR` 块头共 `189` 枚，其中署名「号令者（实例 A，会话 `6efab655`）」的 `1` 枚：
    - `CITYNEXUS_AGENT_CONTROL.md:17024` 「### CMDR 2026-09-29 01:32 · 号令者（实例 A，会话 `6efab655`）· ORD-0421 与 ORD-0419 已落地并我亲测过：抽屉 14 行从实心靛蓝块变回导航列表、当前行有浅色胶囊；但这次放宽选择器把 head 行带坏了」
    （另有 `12` 枚块头是车道署名但以 `### CMDR` 开头的交付块——那一类我一贯不当派单读。）
  我这侧的不安全感来源很具体：`AUTHORITATIVE_BRANCH_SINGLE_WRITER_V1` 与 `LEDGER_SINGLE_WRITER_V1` 讲的是**一个笔**；现在两个实例都能落地、都能派号，撞号就是这套规则的必然代价。要不要收成一个实例、或给两边发一个号段前缀，这是您/仲裁的决定，我不擅自动。

三、盘（每轮都量，因为 23:17 那块里号令者写过「D 盘从写满清到还有余量」）：现读 
    ``C:` free `12.5` GB  `D:` free `15.1` GB  `E:` free `126.7` GB`。我已把这条提醒随敲门发给要开导出口的车道（它们的 `cp -al` node_modules 导出树是主要写入者）：新出口优先考虑还有余量的盘，别再造一次写满。

现场：现尖 `f662905ec4cafe05687d33a05dcbc7ca8031de43`；车道此刻在场读数见 `patrol/round_watch.log`（每 10 分钟一轮：磁盘、弹窗停摆、census、收件分类、现尖是否移动）。

边界：只读账本、收件目录、磁盘与 GitHub ref；0 次写账本、0 次插块、0 次删除、0 次动权威线、0 次点别人的窗口；所有行号/计数由 `patrol/_bus_dispatch_collisions.py` 本轮算出。
竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度
