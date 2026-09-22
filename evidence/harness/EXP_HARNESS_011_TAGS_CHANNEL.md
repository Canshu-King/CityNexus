# EXP-HARNESS-011 · 仲裁第 (c) 项：`tags_json` 迁移清单（只读，非阻塞）

提问（仲裁原话口径）：**有多少"无障碍样"的信息只存在于 `tags_json`、旁边没有任何规范化 evidence？**
报法要求：`具名关键 | 数量 | 是否已有规范化 evidence | 所在表/列/行数`；**>0 ⇒ 只开 producer-normalization 票**；
**=0 ⇒ 明写"真实路径下该通道为空"并附扫过的键名清单与分母**。裁决 `RAW_TAGS_ARE_NOT_HARD_EVIDENCE` 不变，
**本件不把 evaluator 改成吃 `tags_json`**（这一条我照令执行，见 §4）。

## 0 · 坐标（先说清"在哪台机器上的哪一份树量的"）

| 项 | 值 |
| --- | --- |
| 判据 | `RAW_TAGS_ARE_NOT_HARD_EVIDENCE`（已生效）⇒ 只数"单通道关键" |
| 产品 SHA | `4d9ceaee785e78fd25482f91d80e3f832aa3f684`（= `4d9ceae`，B 的 ORD-0219 尖） |
| 我的导出树 | `D:/moodle/_qoder_harness_revival_20260921/lab/snap_4d9ceae/backend`（`git archive` 单向导出，权威树未动） |
| 解释器 | `D:\moodle\CityNexus\.venv\Scripts\python.exe`（3.12.14，全仓唯一能跑本项目的口） |
| 量具 | `lab/tools/harness_tags_channel_inventory.py`（本轮 RC=0） |
| 收据 | `lab/evidence/tags_channel_inventory_0334.json` + 控制台 `lab/evidence/tags_console.txt` |
| 扫的两个存储 | ① 活库 `D:/moodle/_qoder_cmdr_gate_20260921/backend/_live.db`（`mode=ro`）<br>② 物化路径：本进程 `seed_demo` 灌进**本次新建**的 `lab/evidence/_db/tagscan_23364.db`（跑前 `existed_before_this_run=False`，扫完即删）**—— 从未 `POST demo/reset`** |

## 1 · 结论：**0**（真实路径下该通道为空），因此**不开票**

两个存储上，**没有任何一个无障碍关键只活在 `tags_json` 里**：

```
places.tags_json                  rows_scanned=16  非空 tags=16  形状全部 = list
  tags-ONLY accessibility : none          present in tags (access): none
  substring (accessibility 族 15 项) : none
real_place_candidates.tags_json   rows_scanned=0（该表两个存储都是 0 行）
```

**分母（照令必须给）**：扫过 **55 张表**，具名发现 `*tags*` 列 **2 个**（`places.tags_json`、
`real_place_candidates.tags_json`）；`places` 16 行 / `real_place_candidates` 0 行；
扫过的**精确关键 14 个**：`wheelchair, steps, ramp, elevator, lift, braille, tactile_paving, blind, deaf,
hearing, sensory, wheelchair_accessible, step_free, stroller_accessible`；
另用**宽松子串 15 项**兜第二遍（防嵌套写法）：`wheelchair, step, stroller, luggage, ramp, elevator, lift,
accessib, braille, sensory, toilet, rollator, mobility, disab, handicap` ⇒ **两遍都是 0**。

`tags_json` 里**真有内容**，但全是氛围形容词，不是无障碍事实（活库 16/16 行）：

```
culture 7 | outdoor 7 | indoor 7 | local_food 5 | history 4 | waterfront 4 |
art 1 | scenic 1 | view 1 | relaxed 1 | quiet 1 | street 1 | shopping 1 |
signature_dish 1 | night_view 1 | bars 1        样例 rowid=1 `["culture","history","outdoor"]`
```

> 我第一版把 `outdoor/indoor/quiet` 当成了命中，直接印出"需要开票"。那是**我自己的关键表过宽**：
> 演示种子把它们当氛围词用。已把两类**分开计数**，并且只有 accessibility 类能驱动结论。

## 2 · 反向发现（比"为空"更有用）：生产者已经在落规范化证据

同一把尺量物化路径时，`places.metadata_json` 里**已出现规范化证据的行 = 3/16**（活库 0/16，
因为活库是那笔生产者落地之前灌的）。具名到表/列/行：

| rowid | `places.id` | 命中列 | 命中标记 |
| --- | --- | --- | --- |
| 4 | `place-tech-art` | `places.metadata_json` | `accessibility_evidence`, `stroller_accessible`, `luggage_accessible`, `accessible` |
| 7 | `place-city-park` | `places.metadata_json` | 同上 |
| 8 | `place-design-library` | `places.metadata_json` | 同上 |

⇒ 第 (c) 项担心的"选了干净契约把真数据锁在门外"在 `4d9ceae` 上**没有发生**：生产者走的正是规范化列。
⇒ 这也把我 `EXP-HARNESS-009` 的模拟注入变成可实测：**这次是真生产者**，我的常驻门必须自己咬到
`stroller_infant` / `large_luggage` 两族（009 当时这两族逐字节不动，因为根本没有证据可读）。读数见 §5。

## 3 · 这个 0 不是"尺坏了"：控制臂先跑，跑不过就拒绝出结论

`--db`/`--seed-demo` 之前强制过一遍内存控制表（5 行，全部由本次进程拥有），
**任一断言不成立 ⇒ RC=5，产品结论根本不生成**。本轮 `passed: true`（7/7，逐条从实测行推导，无字面量 PASS）：

| 控制断言 | 为什么必须有 |
| --- | --- |
| dict 与 array 两种形状都计数 | 列声明默认是 `"[]"`；只读 dict 会把 `["wheelchair=yes"]` 读成"没有关键"——这就是那条**假 0** |
| 走 join 的证据要把 r4 排除在 tags-only 之外 | "旁边没有列" ≠ "没有规范化证据"；`place_id` 子表这一门必须算进"可达" |
| 同行列证据要把 r3 排除、但仍算 present | `tags` 里出现 ≠ 只存在于 `tags` |
| 氛围行不得进入 accessibility 判定 | 防 §1 那个我自己踩过的过度计数 |
| 子串第二遍在同一份数据上必须**非 0** | 证明第二遍是活的量具，不是一条永假的分母 |
| 特征子表 join 必须被"发现" | 证明第 3 列那一门是被扫过、而不是被跳过 |
| 两种形状的 tags-only 计数等于 3 | 总数咬合，防漏计/重计 |

## 4 · 只读声明是量出来的，不是写的

活库这一侧：`mode=ro` URI + 显式 `PRAGMA query_only=1` 并**从同一连接读回 = 1**；
再拿 3 条**即使守卫失效也改不动任何行**的写语句去撞（`UPDATE ... WHERE 1=0`、`DELETE ... WHERE 1=0`、
`INSERT ... SELECT ... WHERE 0`），三条全部被拒为 `attempt to write a readonly database`。
`_live.db` 与 `-wal`/`-shm` 三个文件的 size+mtime 扫前扫后**逐字节相同**（`stats_unchanged: true`）。
⇒ 收据里 `write_connection_opened: false` 是**从探针结果算出来的**。

> 一处诚实的自我修正：我第一版把探针写成 `DROP TABLE IF EXISTS <不存在的表>`，它**不报错**——因为 SQLite
> 对不存在的表根本不去取写锁。那是**我的探针设计错**（把"没有异常"读成"能写"），不是产品的洞。
> 已换成真取写锁、但零行的 `INSERT ... SELECT ... WHERE 0`，并把这个理由写进脚本注释。

## 5 · 已回填：同一把常驻门在真生产者上的差分（详见 `EXP_HARNESS_012_PRODUCER_BITE.md`）

`EXP-HARNESS-009` 当时只能**模拟注入**；`4d9ceae` 是真生产者落地，于是同一把 1152 格门重跑一次：
`cells_blocked` **320 → 354**（新挡 34 格、新放行 0 格），**34 格全部落在 `stroller_infant`(17) 与
`large_luggage`(17)**，两族的 `constraint_rows 0 → 1`、`severities STRONG → HARD`，其余 11 族逐格相同。
⇒ §2 那条"生产者已经在落规范化证据"不是我读代码的推测，**门这边真的咬到了**。
⇒ 差分是两份收据逐格重算出来的（`lab/tools/harness_gate_diff_012.py` →
`lab/evidence/EXP_012_GATE_DIFF_4d9ceae.json`），不是我抄的两个总数。

## 6 · 我要说的没说的

- 本件**只**回答"tags 里是否 stranded 无障碍事实"。它**不**证明演示库的证据覆盖率够（16 个地点里只有 3 个有证据 ≠
  3 个需要证据），也**不**碰 provider 真值路径（无 live 调用）。
- `capacity/noise/vibe/atmosphere` 这类词今天 0 命中；若以后 OSM 真给回同名 key，我的关键表已含它们，
  会被自动归到 atmosphere 类，**不会**冒充无障碍事实。

— HARNESS `d291c9dc`，2026-09-23（时间戳由 Python 生成为 +08）
