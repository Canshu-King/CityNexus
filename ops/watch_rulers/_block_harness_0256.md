## commander 验收 @2026-09-23T02:56+08 —— HARNESS `d291c9dc` 三件全交：**它给 `_live.db` 造了第二把尺（`max(rowid)` 等于行数 ⇒ 无"删了再补"）**；并已解阻它的排队项、另派仲裁的 `tags_json` 迁移盘点

### ① 准备物（可读坐标）

```text
探针        evidence/harness-hard-cap-probe/harness_hard_cap_before_generate_probe.py   blob 1f71d0ba4ac77f97 (11,341 B)
dry-run 收据  hard_cap_probe_dryrun_0056.json                                        blob 1db06c3ecb4b63f0 (668 B)
```
**它自己废掉了旧坐标**：先登记过 `ff77ee6271759547`，之后为兑现"把这条写进探针文档"改了该文件 ⇒ blob 随之变更，**旧号当场标为作废**。⇒ 这正是该有的做法：**改了文件就废旧坐标**，否则两个人各拿一个 sha1 去比对。

### ② `_live.db` 独立见证（第二把尺，只读）——**比我自己的读数强**

```text
tables=55
journeys        行数 3   max(rowid) 3    created_at 2026-10-01T00:00:00+00:00
travelers       行数 3   max(rowid) 3    created_at 2026-10-01T00:00:00+00:00
plan_versions   行数 19  max(rowid) 19   created_at 2026-09-21T12:49:37.045597+00:00
places          行数 16  max(rowid) 16   updated_at 2026-10-01T00:00:00+00:00   ← 该表无 created_at，用实存列并记名
四表 max(rowid) 逐个等于行数 ⇒ 游程内【没有"删了再补"】（这正是行数掩盖不了的那一格）
两遍（隔 3s）读数完全相同；_live.db 3,710,976 / -wal 4,243,632 / -shm 32,768 B 跑前跑后【零漂移】
未开任何写连接：mode=ro URI ＋ 每连接显式 PRAGMA query_only=1 读回=1；journal_mode 只观测；脚本内无 INSERT/UPDATE/DELETE、无 backup()、无文件拷贝
仪器 blob 82ec8f16db52040a ｜ 收据 blob 4f4590cc932dbcdd
```
**它自己先抓住两个错**：① 第一版断言"`mode=ro` ⇒ `PRAGMA query_only=1`"，实测 **0**（那是连接局部标志）⇒ **守卫当场中止，没带着错假设继续**；② 它给"未 seed"补了测量支撑——`import app.main` 会建空 schema，那只遗留库实测 **55 表 / 总行数 0 / 非空表 0**，随后删掉。
⇒ **我今后写"P0 未动"时会引用它这份读数作为独立见证**，不再只用自己的仪器。

### ③ 它报的发布器两笔现象 + 我的处置口径

- **文件名含 `_live` 被拦**：它没"绕"，是**正确适配**（改名即过）。↔ 那道名字守卫是**故意**的第二道带（第一道是内容里的 SQLite 魔数）。**处置**：守卫保留，但把拒绝文案改成**可行动**的——直说"改仪器文件名，不要改内容；改名这一动作本身会出现在收据里"。**不许**为此开"只读仪器放行口"（那会让车道学会的是绕名字）。
- **PUT 409 ＝ 基线在 GET→PUT 之间被别的车道推进**：对，就是"**分支动了、不是文件被改了**"；重试正确。**处置**：把"调用方自带重试"写进工具说明。

### ④ 已解阻它的排队项 + 新派一件

- **排队项解阻**：B 的 ORD-0219 patch 坐标已给它 —— 累积 patch `bce7269→4d9ceae` **`0d97dfc6b0393ded`**(19,924 B)；逐笔 `5730004.patch 1c4d4f14bbed06cb` / `21309b9.patch 308aa9added037fb` / `84017af.patch f0a562b015c5e0c1` / `4d9ceae.patch 1ce909c1ee9a1351`；尺 `_qoder_streak_receipt.py` 50,316 B / sha256 前缀 `5528700cfbe71711`。规格不变：3 轮全套报**交集＋范围**（不重复 B 自认的"两轮当基线"）、连击**具名挑 2 门 × 10 进程**、跑完删自己临时库报释放字节、**B 的数只当对照**。
- **新派（仲裁第 (c) 项，只读，可并行）**：现有**真实 provider / materialization 路径**里，有多少"可访问性样式信息只存在 `tags_json`、没有规范化 evidence"？报法：`只存在 tags 的关键（wheelchair/steps/*_accessible 等具名子串）| 数量 | 是否已有规范化 evidence | 所在表/列/行数`；>0 ⇒ 只开 producer-normalization 票（**不得因此把 evaluator 改成吃 `tags_json`**）；=0 ⇒ 明写"真实路径下该通道为空"并附**扫过的键名清单与分母**（0 命中必须配分母）。

### ⑤ 现场

链三条端口在听（`:4781` 56212 / `:4782` 20364 / `:8693` 55960）；三代包同挂；清理闸门仍关（0 删除，等用户真机刷新）；`P7=false`；reference tip `c0d7e3d`；P0 未动（HARNESS 第二把尺：3/3/19/16 且 max(rowid)=行数、三文件零漂移）；那把 key 仍未轮换。
**D 盘**：HARNESS 读到可用 **13,084 MB**（我 02:26 读的是 12,112 MB ⇒ 仍在被别人吃）；后台 `du -sm /d/moodle/*` 盘点仍在跑。
