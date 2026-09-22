# ORD-0219（amended ②③④⑤）交付 · 封存演示无障碍证据生产者 · v2 · `c01d72a3` @2026-09-23T01:0x+08

v2 相对 v1（23:5x）的变化：按仲裁 00:41 两笔收紧把 **E2E 收据拆成两层**、把 **C 的洗白断言吸收进门**（`84017af`），并补了**跨半依赖两臂**与**合并态实测**。v1 的 blob 不覆盖，本文件与 v2 收据一起构成当前口径。

## 0. 坐标

| 要素 | 读数 |
|---|---|
| 树 / 分支 | `D:/moodle/_qoder_b_ord188_20260922` · `agent/canary-ord198-20260922`（**未 push**） |
| 提交 | `84017af Wed Sep 23 00:56:09 2026 +0800 test(demo): the producer gate pins the evaluated verdict, not just the filtered keys`（40 位 `84017af12cd9e3db8ee3bf082fc6ef3e04244b20`）← `21309b9 Tue Sep 22 23:35:29 2026 +0800 feat(demo): …producer…`（`21309b996ecb474d9122f88b81fba2216a006833`）← `5730004 …fix(capabilities): the parser forwards a HARD severity…` |
| 源码 patch（可读） | `evidence/b-ord0219-demo-evidence/21309b9.patch` blob `308aa9added037fb`(18,223 B)｜`5730004.patch` blob `1c4d4f14bbed06cb`(2,351 B) |
| 解释器 | `D:/moodle/CityNexus/.venv/Scripts/python.exe` 3.12.14 |
| 观察面 | 一次性库 `D:/moodle/_qoder_spike_20260921/q219b_demo.db`（进程内 TestClient，0 端口）；pytest 侧每进程 `cnx_pytest_*` 临时库（conftest ORD-0211，头部打印 resolved 路径） |
| 合规 | 0 provider 出网（三把 key 导入前清空、`AI_ENABLED=false`）；**未发 `demo/reset`**（种子走 `app.services.seed_demo`）；未碰 `_live.db`/`_preview.db`/`:4781/:4782/:8693`；突变全部走 `mutation_anchor_guard`，逐臂还原 SHA-256 相等，跑完 `git status` 为空 |

## 1. 产品真值（KEEP 边界，按仲裁 00:44）

* 事实声明位置：`data/mock/places.json` 的三个 `CNX-DEMO` 地点（**不是** `services.py` 里的常量表）；
* 落库键：`metadata_json["accessibility_evidence"]`（**不是** `metadata_json["accessibility"]`）；
* 出处：由服务端代码盖章 `source_kind="DEMO"` ＋ 指向 fixture 的 `source`，**不从 fixture 读**；只有白名单布尔值能穿过；
* 正例控制：`place-tech-art` stroller**false**/luggage true；`place-design-library` stroller true/luggage**false**；`place-city-park` 双 true；其余 5 个演示地点与全部 CN-BEIJING **无证据**（UNKNOWN 仍可演示，兼作不泄漏的负例面）。

## 2. 两向 E2E（仲裁①：两层分开记）

`q219b_demo_chain.py` 的每个形制现在产出两个键，各自显式声明没碰对方：

```text
parser_layer      { sentence, parsed_severities, persisted_capability_rows,
                    constraint_row_count_read_back, constraint_rows_read_back, feasibility_touched: false }
feasibility_layer { capability_when, generate_status, candidates[{places, select}], parser_re_read_here: false }
```

实测（v2 收据 `91901a22d6d65e2a`，12,734 B）：

| 形制 | parser 层 | feasibility 层 |
|---|---|---|
| 无断言 | 无码、无行 | 201 → 3 候选（证据本身不挡路） |
| 「我们带婴儿车，这是必须的。」 | `STROLLER=HARD` → 回读 `[{'kind':'HARD','rule_code':'STROLLER','params':{'present':True}}]` | 先生成：3→2（去 tech-art）；方案先存在→事后声明：select 含 tech-art ⇒ **422 `STROLLER_ACCESS_UNAVAILABLE:place-tech-art`**，含 city-park/design-library ⇒ 200 |
| 「我们拉一个大箱子，这是必须的。」 | `LARGE_LUGGAGE=HARD` → 同上 | 3→2（去 design-library）；select 含 design-library ⇒ **422 `LUGGAGE_ACCESS_UNAVAILABLE:place-design-library`**，其余 200 |
| 两句都 HARD | 两码 HARD → 两行 HARD | 3→1（只剩 city-park 模板） |
| UNKNOWN | — | 未被声明地点在库里读不到这两个键（断言键**缺席**，不是 `!= True`） |
| 不泄漏 | — | 非 `CNX-DEMO` 的 8 个地点带 `accessibility_evidence` = **0** |

一层里我自己抓到一次仪表错并已改：`parser_layer.rows` 第一版是 `[]`，因为 `capability_constraint_items` 返回 **dict 行**而我用 `getattr` 读——不是产品没落库；改成映射/属性双读后行层读到 HARD 行（这条如实留在交付里，因为它正好是"两层分开"才暴露出来的）。

**未修的具名缺口**：约束先落地时 `plans/generate` 在落库前 `continue` 掉冲突候选 ⇒ 用户只看到"方案少了两个"，具名码只出现在 select 复验面上。

## 3. 门（8 条，`backend/tests/test_qoder_demo_accessibility_evidence.py`）

期望值全部算出来（冲突地点来自库里实读，候选数来自 `_templates()` 内容，0 个写死的 plan 序号）。
`84017af` 吸收了 C 的移植件①：**不只断言"恶意键没穿过"，还断言"求值没被洗白"**——把投影结果喂回产品自己的 `_accessibility_metadata` ＋ `accessibility_state` ＋ `evaluate_accessibility_requirement("STEP_FREE_REQUIRED", …)`，任何一条量出 `ACCESSIBILITY_VERIFIED` 即红。
C 的移植件②（逐候选现算 PASS/BLOCK）**我这把本来就是那个形状**（实测：文件内 `plan_id ==` 字面量 0 处；`place-*` 字面量只出现在合成 helper 用例里）。

## 4. 连击（GATE_ACCEPTANCE_STREAK @ `84017af`，commander 的 `gate_streak.py` v2-2）

尺＝F 的 `backend/tests/_qoder_streak_receipt.py`，本次导出用的那份是 **50,316 B / sha256 前缀 `5528700cfbe71711`**（与 `_qoder_f_o210b_20260922` 逐字节相等；比 23:5x 那次的 47,572 B/`ef608a34f9a3e4f2` **换了版本**，所以两批读数不可互比）。读数：

```text
8 条节点 × 10 独立进程 × 80 只不同一次性库：全部 STREAK_MET(10)，closure_grade=STREAK_GREEN（single-node 形制）
every_run_fresh=True（temp_dir_appeared 10/10）｜duplicate_db_paths=[]｜runs_missing_db_path=[]｜runs_missing_fields=[]｜forbidden_targets=[]
逐 run 目标节点 verdict 取值集合 = {GREEN}（没有 NOT_OBSERVED，也没有拿容器退出代判）｜命令面第 6 条 clean、hits=0
```

第 6 条的达成手段（自己声明，尺不判）：80 次调用全是尺生成的同一条 `python -m pytest <单个 nodeid> -q --no-header`（逐 run 存 argv），**没有** sleep／重试／退避／降并发／放宽断言／deselect／skip。`closure` 停在 `STREAK_GREEN` 正是尺把"结案要交付方写明手段"留给车道的那一半。
两批连击**不可互比**：23:5x 那批用尺 47,572 B/`ef608a34f9a3e4f2`，这批用 **50,316 B/`5528700cfbe71711`**（F 在中间更新过），所以引用时必须带尺的版本。
收尾：按收据点名的绝对路径删掉本次 80 只一次性库（**释放 65.3 MB、复验剩 0**）；`%TEMP%` 里其余 `cnx_pytest_*` 是别的车道历史跑的，一个没碰。

## 5. 突变（8 臂＝仲裁四臂最小集＋我自己四臂，逐臂 `anchor_hits==1`/`bytes_changed`/还原相等）

| 臂 | 改哪里 | 归属（变红的节点） |
|---|---|---|
| M1 | fixture tech-art stroller false→true | stroller 两向门、生成筛除门 |
| M2 | fixture 删掉 tech-art 事实 | 同上两条 |
| M3 | 生产者出处改写成 `LIVE_PROVIDER_CAPTURE` | DEMO 出处门、生产者契约门 |
| M4 | 生产者漏给全部地点 | 不泄漏门、精确集合门、UNKNOWN 门 |
| M5 | 白名单失效（有什么搬什么） | 生产者契约门（**吸收 C 的洗白断言后，这一臂现在杀的是"求值被洗白"而不只是"键列表"**） |
| M6 | fixture design-library luggage false→true | luggage 两向门 |
| M7a | 撤 `STROLLER` 的 severity 转发 | stroller 两向门、生成筛除门 |
| M7b | 撤 `LARGE_LUGGAGE` 的 severity 转发 | luggage 两向门（**与 M7a 互不越界 ⇒ 两码各自被消费**） |

`nodes_without_a_killing_arm = []`。四臂最小集映射：stroller F→T=M1、luggage F→T=M6、source_kind→LIVE=M3、非 CNX-DEMO 注入=M4。
收据：v2 `eb07540bfba3898c`(5,851 B)；跨半依赖 `96662f06192c8d2b`(2,077 B)；v1 `3592d653a3f91520` 保留不覆盖。

## 6. 合并态实测（撤 C 留 B）

`git archive 8b9ea04 backend data contracts tools` ＋ 我的 `services.py`/`places.json`/门文件（＝C 的 producer 被取走后的形状）→ **我的 8 条 ＋ C 的 `test_qoder_ord0219_write_side_rule_guard.py` 9 条 = 17 passed**（`84017af` 上重跑同读数）。
冲突面：`git merge-tree --write-tree 21309b9 8b9ea04` ⇒ 只有 `capabilities.py`（同一两行，语义等价：我 `else None`／C `else "STRONG"`）与 `services.py`（两份 producer）。
待 C 处理：它那把的门文件在我这形状上**收集期 ImportError**（`DEMO_ACCESSIBILITY_EVIDENCE` 不存在）⇒ 移植时随 revert 一起删除或改写。
**键遮蔽风险（revert 后必查）**：`feasibility._accessibility_metadata` 与 `mock_replan_engine.py:83` 都是 `accessibility` 优先于 `accessibility_evidence`；实测残留顶层 `step_free` 会被嵌套键**静默丢弃**（量出 UNVERIFIED 而非 VERIFIED，方向安全但证据丢失）⇒ revert 后请复扫 `backend/app/` 里的 `accessibility` 写入点，应只剩这两处读取。
读数文件：`q219b_merge_readings.txt` blob `d49d9610e28e15e2`(2,964 B)。

## 7. 回归分母

`pytest tests/ -q --tb=no`（`21309b9`）：**1192 collected / 1166 passed / 10 failed / 15 skipped / 1 xfailed（108.12s）**；10 条对同尖干净导出复放＝既有红（g14a/g14c/g10/g8a/g9a/g9b/g5/aiv3_02/city_failure ＋ g3 属 FLIP 节点）。**本笔引入的回归 0 条**。
另记一次我自己的环境假红：稀疏检出缺 `contracts/` 一度虚报 15 failed，`git sparse-checkout add contracts` 后那 6 条 6 passed。

## 8. 状态与等的事

四个 `SOFT_PREFERENCE` 码一行未动；`feasibility.py`/`main.py`/`schemas.py`/契约/`integrations/discovery/**` 0 改动。通用约束的新词表守卫是 **ORD-0223（归 C，仲裁已明确"别复用 `CAPABILITY_CODES`"）**，我不碰。等：① 撞车选型的验收顺序（`00bc9b5` 已 ACCEPTED-CODE、`21309b9/84017af` 未审，二者只留一份）；② `agent/canary-ord198-20260922` 的合并/push 口径；③ 生成阶段静默筛候选要不要具名。
