# ORD-0219（amended 第②③④⑤步）交付 · 封存演示的无障碍证据生产者 · `c01d72a3` @2026-09-22T23:5x+08

仲裁 `5778570154` 的五步里，①（parser severity）已在 `5730004` 交过；本笔交 **②demo 证据生产者 + ③正常消费链 + ④sealed-demo E2E 两向 + ⑤突变**。

## 0. 坐标（六要素）

| 要素 | 读数 |
|---|---|
| 树 / 分支 | `D:/moodle/_qoder_b_ord188_20260922` · `agent/canary-ord198-20260922` |
| 提交 | `git log -1`：**`21309b9 Tue Sep 22 23:35:29 2026 +0800 feat(demo): the sealed demo produces accessibility evidence the stroller and luggage gates can read`**（40 位 `21309b996ecb474d9122f88b81fba2216a006833`，parent `5730004`）**未 push** |
| 改动文件 | `data/mock/places.json`(+3 条无障碍事实)、`backend/app/services.py`(+生产者 `_demo_accessibility_evidence` 并接进 `seed_demo`)、`backend/tests/test_qoder_demo_accessibility_evidence.py`(新，8 节点) |
| 解释器 | `D:/moodle/CityNexus/.venv/Scripts/python.exe` 3.12.14 |
| 观察面 | 我自己的一次性库 `sqlite:///D:/moodle/_qoder_spike_20260921/q219b_demo.db`（进程内 TestClient，0 端口）；pytest 侧由 `tests/conftest.py` ORD-0211 每进程一只 `cnx_pytest_*` 临时库，头部打印 resolved 路径 |
| 命令 | 见 §6 复跑配方 |

**现场合规**：0 provider 出网（`DEEPSEEK_API_KEY`/`CITYNEXUS_AI_API_KEY`/`OPENAI_API_KEY` 导入前清空、`AI_ENABLED=false`）；**未发 `demo/reset`**（种子走 `app.services.seed_demo`）；未碰 `_live.db` / `_preview.db`、未碰 `:4781/:4782/:8693`；突变全部走 `mutation_anchor_guard.temporary_guarded_replace`，六臂跑完 `git status --porcelain` 为空。

## 1. 改动前的实测（先复现 HARNESS 的 0/16，再动代码）

在本树自己的临时库里 `seed_demo` 之后逐行读 `SELECT id, metadata_json FROM places`：
**CNX-DEMO 8 个地点、CN-BEIJING 8 个地点，带无障碍证据的 = 0/16**；metadata 顶层只有 `duration_min` / `cost_minor`。
并且解析器补完 severity 之后（`5730004`），实测“既不挡也不放”：

```text
S1（无能力断言）  plans/generate 201 -> 3 候选
（改动前）带 HARD STROLLER 的 select 三候选全 200 —— 门读到 None，没有任何一挡
```

## 2. 生产者（第②步）落在哪里、边界怎么守住

`backend/app/services.py`（`seed_demo` 上方）：

```python
_DEMO_ACCESSIBILITY_FACTS = ("stroller_accessible", "luggage_accessible")

def _demo_accessibility_evidence(item):
    """Project the demo fixture's accessibility facts onto a sealed demo place.
    Only the whitelisted booleans cross over, and the provenance is stamped here
    rather than read from the fixture: editing JSON must not be able to label a
    demo place as provider truth."""
```
`seed_demo` 的地点循环把它写进 `metadata_json["accessibility_evidence"]`——**这正是 `replanning/feasibility.py:_accessibility_metadata` 已经认的那个形状**，所以 feasibility 里没有 demo 特例（仲裁第③步）。

fixture 侧只声明三个事实（`data/mock/places.json`，全在 `CNX-DEMO`）：

| 地点 | stroller_accessible | luggage_accessible | 为什么是它 |
|---|---|---|---|
| `place-tech-art` | **false** | true | 只有模板 1 经过它 ⇒ 负例可演示且不必把整趟拒死 |
| `place-design-library` | true | **false** | 只有模板 3 经过它 ⇒ 行李码的负例 |
| `place-city-park` | true | true | 只有模板 2 经过它 ⇒ 正证据不误伤的控制 |
| 其余 5 个 CNX-DEMO 地点 + 全部 CN-BEIJING | — 不写 — | | 保留 UNKNOWN 这一格，并作为“不得泄进非封存城市”的负例面 |

入库后实际读数（`q219b_demo_chain_receipt.json` S9）：

```text
place-city-park        {'stroller_accessible': True,  'luggage_accessible': True,  'source_kind': 'DEMO', 'source': 'data/mock/places.json#place-city-park'}
place-design-library   {'stroller_accessible': True,  'luggage_accessible': False, 'source_kind': 'DEMO', 'source': 'data/mock/places.json#place-design-library'}
place-tech-art         {'stroller_accessible': False, 'luggage_accessible': True,  'source_kind': 'DEMO', 'source': 'data/mock/places.json#place-tech-art'}
```

## 3. 两向 E2E（第④步，真实封存 journey `22222222-…` / `One Day in Nexus City`）

需求由产品自己的耳朵进来：`extract_capabilities_from_text("我们带婴儿车，这是必须的。")` ⇒ `STROLLER/HARD`（无硬标记的同文 ⇒ STRONG，正证据不误伤），再 `POST /travelers/{id}/capabilities/confirm` ⇒ 回读 `severity=HARD confirmed=True`。

| 形制 | 读数 |
|---|---|
| 先出方案、**后**声明 HARD STROLLER | `POST .../plans/<含 tech-art>/select` ⇒ **422 `PlanVersion … is infeasible: STROLLER_ACCESS_UNAVAILABLE:place-tech-art`**；含 city-park / design-library 的两个方案 ⇒ **200**（不误伤） |
| 先出方案、**后**声明 HARD LARGE_LUGGAGE | 含 design-library 的方案 ⇒ **422 `LUGGAGE_ACCESS_UNAVAILABLE:place-design-library`**；含 tech-art / city-park 的 ⇒ **200** |
| **先**声明 HARD STROLLER 再生成 | 201 ⇒ 2 候选，含 tech-art 的模板不入库；HARD LARGE_LUGGAGE ⇒ 2 候选（去 design-library）；两条都 HARD ⇒ 1 候选（city-park 模板） |
| 无断言 | 3 候选不受影响（证据本身不挡任何人的路） |
| UNKNOWN | 未被 fixture 声明的地点在库里读不到这两个键（断言 `key not in evidence`，不是 `!= True`） |
| 不泄漏 | 非 `CNX-DEMO` 的 8 个地点带 `accessibility_evidence` 的 = **0** |

**一条如实报的缺口（不修，等裁）**：约束**先**落地时，权威门在落库前 `continue` 掉冲突候选，于是用户看到的是“方案少了两个”，**看不到为什么**——具名码只在“方案已存在→事后声明→select 复验”这条面上出现（422 那句 `STROLLER_ACCESS_UNAVAILABLE:place-tech-art`）。这是生成阶段的解释面问题，属 §11「AI no-op 必须说清是哪种」同族，不在本单四格边界里。

## 4. 连击（GATE_ACCEPTANCE_STREAK，commander 那把尺 `gate_streak.py` v2-2，不养第二把尺）

靶树＝`git archive 21309b9 backend data contracts tools` 的导出（`_qoder_spike_20260921/snap_21309b9`），
尺＝F 的共享模块 `backend/tests/_qoder_streak_receipt.py`（47,572 B，sha256 前缀 `ef608a34f9a3e4f2`，
从 `_qoder_f_o210b_20260922` 原样取出并逐字节比对相等）——**它是尺，不是我这一尖的产物，所以收据里单列**。

| 节点 | 形制 | 绿/轮 | verdict | closure | 每轮新库 | 不同库数 | 第6条命令面 | 反向突变 |
|---|---|---|---|---|---|---|---|---|
| `..._lands_every_claimed_fact_with_demo_provenance` | single-node | 10/10 | STREAK_MET(10) | STREAK_GREEN | ✓ | 10 | clean, hits=0 | KILLED |
| `..._reaches_exactly_the_places_the_fixture_claims` | single-node | 10/10 | STREAK_MET(10) | STREAK_GREEN | ✓ | 10 | clean, hits=0 | KILLED |
| `..._stays_out_of_non_sealed_cities` | single-node | 10/10 | STREAK_MET(10) | STREAK_GREEN | ✓ | 10 | clean, hits=0 | KILLED |
| `..._is_unknown_and_never_implicit_access` | single-node | 10/10 | STREAK_MET(10) | STREAK_GREEN | ✓ | 10 | clean, hits=0 | KILLED |
| `..._refuses_non_boolean_and_provenance_keys_from_the_fixture` | single-node | 10/10 | STREAK_MET(10) | STREAK_GREEN | ✓ | 10 | clean, hits=0 | KILLED |
| `test_hard_stroller_names_the_blocker_and_does_not_misfire` | single-node | 10/10 | STREAK_MET(10) | STREAK_GREEN | ✓ | 10 | clean, hits=0 | KILLED |
| `test_hard_luggage_names_the_blocker_and_does_not_misfire` | single-node | 10/10 | STREAK_MET(10) | STREAK_GREEN | ✓ | 10 | clean, hits=0 | KILLED |
| `test_generation_never_persists_a_candidate_that_conflicts_with_a_hard_capability` | single-node | 10/10 | STREAK_MET(10) | STREAK_GREEN | ✓ | 10 | clean, hits=0 | KILLED |

聚合（`streak_21309b9/streak_readback.json`，全部从逐 run 读数算出，无一条写死）：
**80 个独立子进程 / 80 个不同一次性库 / 逐 run 节点 verdict 集合只有 `{GREEN}` / `duplicate_db_paths=[]` /
`runs_missing_db_path=[]` / `runs_missing_fields=[]` / `forbidden_targets=[]` / `run_shape_verified=True`（8/8）**。

**第 6 条怎么达成的（自己声明，尺不判）**：80 次调用全是同一条命令形态
`python -m pytest <单个 nodeid> -q --no-header`（由尺的 `shape_command(SINGLE_NODE, …)` 生成，逐 run 存 argv），
**没有** sleep / 重试 / 退避 / 降并发 / 放宽断言 / deselect / skip；尺自己扫命令面 8/8 clean、hits=0。
`closure_grade` 停在 `STREAK_GREEN` 而不是 `CLOSED`，正是尺对"结案要交付方写明手段"的那一半保留——本段就是那句声明。

**收尾**：连击跑完我把**自己这 80 次跑产生的一次性库目录**按收据里的绝对路径逐个删除并复验（`80 个目录 / 释放 65.3 MB / 仍存在 0 个`）。
顺带一条现场事实给 commander：`tests/conftest.py`（ORD-0211）每进程 `tempfile.mkdtemp(prefix="cnx_pytest_")` **从不回收**，
我删完自己那 80 个之后再数一次 `%TEMP%`，**仍剩 913 个** `cnx_pytest_*` 目录（各车道历史跑的，我一个没碰）。

## 5. 突变（第⑤步）：六臂全 KILLED，且每条节点都有归属断言

尺：`mutation_anchor_guard.temporary_guarded_replace`（`anchor_hits==1`、字节必变、还原 SHA-256 逐臂相等），靶：`tests/test_qoder_demo_accessibility_evidence.py` 8 节点，逐节点 verdict。

| 臂 | 改哪里 | 变红的节点（归属） | 还原 |
|---|---|---|---|
| M1 | fixture：tech-art stroller false→true | `test_hard_stroller_names_the_blocker_and_does_not_misfire`、`test_generation_never_persists_a_candidate_that_conflicts_with_a_hard_capability` | sha256 ✓ |
| M2 | fixture：删掉 tech-art 的 accessibility | 同 M1 两节点 | sha256 ✓ |
| M3 | 生产者：出处改写成 `LIVE_PROVIDER_CAPTURE` | `test_demo_producer_lands_every_claimed_fact_with_demo_provenance`、`test_demo_producer_refuses_non_boolean_and_provenance_keys_from_the_fixture` | sha256 ✓ |
| M4 | 生产者：漏给所有地点（含非封存城） | `test_demo_evidence_stays_out_of_non_sealed_cities`、`test_demo_producer_reaches_exactly_the_places_the_fixture_claims`、`test_missing_demo_evidence_is_unknown_and_never_implicit_access` | sha256 ✓ |
| M5 | 生产者：白名单失效（fixture 有什么搬什么） | `test_demo_producer_refuses_non_boolean_and_provenance_keys_from_the_fixture` | sha256 ✓ |
| M6 | fixture：design-library luggage false→true | `test_hard_luggage_names_the_blocker_and_does_not_misfire` | sha256 ✓ |

`nodes_without_a_killing_arm = []`（收据 `q219b_mutation_receipt.json`）。
过程中我自己踩到一处**空断言**并当场补牙：M2 之后生成那条节点仍绿（它比的是“无冲突模板数”，冲突被删光就恒等）——已加“无冲突模板数 > 0 且 有冲突模板数 > 0”的存在性守卫，补牙后 M1/M2 都能咬红它。

## 6. 复跑配方

```bash
cd D:/moodle/_qoder_b_ord188_20260922/backend
# 八条门（1.2s）
D:/moodle/CityNexus/.venv/Scripts/python.exe -m pytest tests/test_qoder_demo_accessibility_evidence.py -v --tb=short
# 两向 E2E 读数（进程内，0 端口，一次性库）
D:/moodle/CityNexus/.venv/Scripts/python.exe D:/moodle/_qoder_spike_20260921/q219b_demo_chain.py
# 六臂突变（跑完 git status 必须为空）
D:/moodle/CityNexus/.venv/Scripts/python.exe D:/moodle/_qoder_spike_20260921/q219b_mutations.py
# 连击（先 git archive 21309b9 到 snap_21309b9，再把 F 的共享尺放进去）
D:/moodle/CityNexus/.venv/Scripts/python.exe D:/moodle/_qoder_spike_20260921/q219b_streak.py
```

## 7. 全量分母（回归）

`pytest tests/ -q --tb=no`：**1192 collected → 1166 passed / 10 failed / 15 skipped / 1 xfailed（108.12s）**。

那 10 条我逐条对同尖干净导出（`git archive 5730004 backend data contracts tools`）复放过，**不是我引入的回归**：

```text
既有红（导出里同样红，9 条）：aiv3_02、g5、g9a、g9b、g14a、g14c、g8a、g10、city_failure_reasons
g3（本轮多出的 1 条）＝已知 FLIP 节点（同一节点换 run 形制会翻面）
```

**顺带抓到自己一个环境假红**：我第一次跑全量是 **15 failed**，多出的 6 条（`test_contract.py` 三条 + `test_qoder_anywhere_contract_parity.py` 两条 + `g6a`）**全是 `FileNotFoundError: contracts/openapi*.yaml`** —— 我的稀疏检出只含 `backend data frontend tools`，**没含 `contracts/`**。补 `git sparse-checkout add contracts` 后这 6 条复跑 **6 passed**。记进常驻教训：**稀疏工作区缺目录会造出与产品无关的红**（同 09-21 那次缺 `data/` 造出 53 条假红）。

## 8. 明确没做的（按令与边界）

- **四个 `SOFT_PREFERENCE` 码**：一行没动（`SLOW_PACE`/`QUIET_ENVIRONMENT`/`INDOOR_PREFERRED`/`SENSORY_LOW_STIMULATION`）。仲裁原话照记：“severity 与 feasibility evaluator 必须同批落”，且**不跟本次 demo 生产者一起扩范围**。
- **写入端两层校验**（`5778314066` 的四格：`UNKNOWN_RULE_CODE` / `HARD_RULE_NOT_EXECUTABLE` / SOFT 按 soft 契约 / hard-executable 落库后由 feasibility 按证据求值，并要求“可执行集来自一份共享 registry”）：**没动**——仲裁与 commander 都写明“与四个 SOFT 码、与本单 demo 生产者不混成一笔”。这一笔我领，但请给排期与“共享 registry 放哪一层”的一句话（schema、capabilities parser、feasibility 三处现在各养各的词表）。
- `feasibility.py` / `_CAPABILITY_GATE_CODES` / `main.py` / 契约：0 改动。真实 provider 路径（`integrations/discovery/**`）0 改动 ⇒ “不泄进 normal-city/provider 路径”是靠“生产者只存在于 `seed_demo`+`CNX-DEMO` fixture”达成的，并有 S8 负例读数撑着，不是靠注释。
- 演示库以外的地点仍然没有无障碍证据（这是产品事实，不是缺陷已修）；`MOBILITY_EVIDENCE_NOT_HARD_ELIGIBLE` 那一格不受本笔影响。
