# EXP-HARNESS-012 · 真生产者落地后，**我自己的常驻门咬到了**（EXP-009 预登记的回填）

`EXP-HARNESS-009`（2026-09-22T23:22）我当时只能做**模拟注入**：把 `app/services.py` 的证据写入点改掉，
看我的门会不会动。结论是"门会咬"，但同一份注入下 `stroller_infant` / `large_luggage` 两族**逐字节不动**，
因为**根本没有证据可读**——那两族的"不动"证不了门，也证不了产品。

现在 B 的 ORD-0219 生产者落地在 `4d9ceae`。**同一个人、同一把门、同一份 1152 格矩阵**，重跑一次：

| 坐标 | 值 |
| --- | --- |
| 前 | head `dfdc5d5` → `lab/evidence/evidence_gate_dfdc5d5.json`（09-22 23:19，生产者落地之前） |
| 后 | head `4d9ceae` = `4d9ceaee785e78fd25482f91d80e3f832aa3f684` → `lab/evidence/evidence_gate_4d9ceae_post0219.json`（09-23 03:35） |
| 树 | 我的导出 `lab/snap_4d9ceae/backend`（`git archive` 单向导出；权威树未动） |
| 解释器 | `D:\moodle\CityNexus\.venv\Scripts\python.exe` 3.12.14 |
| 判据 | 我自己那把常驻门 `lab/tools/harness_evidence_gate.py`（13 族 × 6 shape × 16 地点 = 1152 格），本次 `--run-tag post0219` 独立库独立文件 |

## 1 · 总读数

```
cells_blocked  320 / 1152   (dfdc5d5, 生产者之前)
cells_blocked  354 / 1152   (4d9ceae, 生产者之后)      Δ = +34
新被挡 34 格；新被放行 0 格（不是"动了又回去"，是单向变严）
```

**34 格全部落在这两族**：`stroller_infant` 17 格、`large_luggage` 17 格
（按 shape：`curated_false` 各 16 格 + `seed_native` 各 1 格——即"证据说 false 的地点"从放行变挡，
和演示种子里真声明 `false` 的那 1 个地点从放行变挡）。

## 2 · 13 族逐族对照（这才是"只动了该动的"证明）

| family | 前 `dfdc5d5` | 后 `4d9ceae` | 动了吗 |
| --- | --- | --- | --- |
| `stroller_infant` | rows=0 `STRONG` why=`extracted_but_not_hard` | **rows=1 `HARD`** | **YES** |
| `large_luggage` | rows=0 `STRONG` why=`extracted_but_not_hard` | **rows=1 `HARD`** | **YES** |
| `step_free_wheelchair` | rows=2 `HARD` | rows=2 `HARD` | 否 |
| `infant_nap_window` | rows=1 `HARD` | rows=1 `HARD` | 否 |
| `max_walking_per_leg` | rows=1 `HARD` | rows=1 `HARD` | 否 |
| `midday_rest_window` | rows=1 `HARD` | rows=1 `HARD` | 否 |
| `rest_cadence` | rows=1 `HARD` | rows=1 `HARD` | 否 |
| `toilet_cadence` | rows=1 `HARD` | rows=1 `HARD` | 否 |
| `indoor_only` | rows=0 `SOFT` why=`extracted_but_not_hard` | 同 | 否 |
| `quiet_environment` | rows=0 `SOFT` why=`extracted_but_not_hard` | 同 | 否 |
| `avoid_stairs_route` | rows=0 why=`no_code_extracted` | 同 | 否 |
| `sensory_low_stimulation` | rows=0 why=`no_code_extracted` | 同 | 否 |
| `slow_pace` | rows=0 why=`no_code_extracted` | 同 | 否 |

⇒ **只有被点名的两族移动，其余 11 族逐格相同。** 这既证明门对生产者有牙，也证明它没有"到处乱挡"。
⇒ 剩下没动的 5 族（2 族 `extracted_but_not_hard` 的 `SOFT`、3 族 `no_code_extracted`）正是 B 自己声明
"等排期、连可行性层一起做"的那一批——**本次没有偷偷少报，也没有多修**。

## 3 · 为什么这一格比 009 那一格值钱

009 的读数只能签"机制"：门在生产者存在时会不会动。今天这份是**真产品**：
`_demo_accessibility_evidence()` 把 `data/mock/places.json` 里 3 个地点声明的两个白名单布尔投影进
`places.metadata_json.accessibility_evidence`（并在这里盖 `source_kind=DEMO`，不是从 JSON 读来的署名），
解析器把 `STROLLER`/`LARGE_LUGGAGE` 的 severity 传进约束行 ⇒ 可行性层第一次**有证据可依**。
两件事**分别**由两笔提交带来（生产者 + 解析器补 severity），所以这一格是"合起来才咬"，
单独任一笔都不该被算成修好——**如果只想确认这一点，看 §2 的两行 `rows=0 → rows=1` 就够**。

具名证据行（我的扫描逐行读出，不是数出来的期望值）：

| rowid | `places.id` | 声明 | 落点 |
| --- | --- | --- | --- |
| 4 | `place-tech-art` | stroller=False, luggage=True | `places.metadata_json.accessibility_evidence` |
| 7 | `place-city-park` | stroller=True, luggage=True | 同上 |
| 8 | `place-design-library` | stroller=True, luggage=False | 同上 |

（同一把尺在**活库** `_live.db` 上读到 0/16 —— 那份库是生产者落地之前灌的，两个存储的差别本身就是证据。）

## 4 · 我这把门现在能不能当 ORD-0219 的复验件？

- **能回答**：生产者是否落地、落地后可行性层是否真的开始挡、以及"是否只挡该挡的"（1152 格逐格差分）。
- **不能回答**：B 自己那 9 道门里的**语义**断言（如"具名阻塞""不得把单条 stroller 事实洗成 step_free_verified"）
  ——那是它的产品断言，我的矩阵不覆盖；我用 `gate_streak.py` 在它自己的 2 道门上量了 10 连绿（见
  `ORD_0219_INDEPENDENT_REPRO_HARNESS.md`），但**10 连绿不产生语义正确性**。
- 我**不**因为这次动了就把它当验收：按 `GATE_ACCEPTANCE_STREAK` ⑧，一次绿是观察；
  闭结仍需反向突变证据（那一格归 B/主链，我这边没有签的权限）。

## 5 · 本件没做的事

没跑真 provider、没调 AI、没写任何权威树或活库（`_live.db` 只做 `mode=ro` 扫描）；
`--run-tag post0219` 保证这次没踩到 09-22 那份同名基线文件；跑完删掉自己临时库并报字节（见复现报告 §3）。

— HARNESS `d291c9dc`，2026-09-23（时间戳由 Python 生成为 +08）
