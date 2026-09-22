# ORD-0236 · `RAW_TAGS_ARE_NOT_HARD_EVIDENCE` 边界门交付（head `75bc8ca`）

## 0. 这一单钉的是契约，不是实现

仲裁冻结的契约原文：

```text
RAW_TAGS_ARE_NOT_HARD_EVIDENCE
Place.tags_json: display/discovery/taxonomy/raw-provider retention, NOT an evaluator truth source
accessibility evaluator: consumes normalized evidence only
```

所以本单 **0 处修改 `app/`**。工作区实测：`git status --porcelain` 空；
`backend/app/replanning/feasibility.py` 的 `git hash-object` = `git rev-parse HEAD:...` =
`a9736797ed0e99be0e9b5b8a280646767cfe41d1`（sha256 前缀 `87bbb2c5dfa0d0de`，与下面每臂收据里的
`before_sha256` 同值 ⇒ 三条杀手臂都逐字节还原了）。

## 1. 三条门（一个文件，3 个节点）

`backend/tests/test_qoder_ord0236_raw_tags_not_evidence.py`

| 门 | 节点 | 断言的东西 |
| --- | --- | --- |
| T1 | `test_t1_raw_tags_column_alone_never_causes_a_hard_verdict` | 只有 `tags_json` 带无障碍字样 ⇒ 求值方看不到任何证据（`_accessibility_metadata` 返回 `None`）、一条硬性判定都不生成；允许的只有 UNKNOWN 一族（`ACCESSIBILITY_UNVERIFIED` / `NEEDS_LIVE_EVIDENCE`）。同一批词改走规范化通道必须立刻长出 `STROLLER_ACCESS_UNAVAILABLE` / `LUGGAGE_ACCESS_UNAVAILABLE` / `ACCESSIBILITY_CONFLICT` ⇒ 这条"读不到"不是永真 |
| T2 | `test_t2_the_same_fact_through_the_normalized_producer_does_name_the_blocker` | 同一件事实在规范化产物里时，**逐码**得到具名判定（`accessibility_evidence` ⇒ 两码各自的名字；`osm_tags{highway=steps}` ⇒ `ACCESSIBILITY_CONFLICT`） |
| T3 | `test_t3_display_taxonomy_tags_never_become_accessibility_evidence` | 展示/分类裸词（culture / indoor / quiet / bars…）不是证据；并且拿真库比库存：求值方看得见的证据地点集合 **必须等于** 生产者声明的集合，同时库里必须存在"只带 tags、没有规范化产物"的地点（否则这条比较是空断言） |

### 实测读数（`lab` 侧探针 `q236_readings.py`，一次进程，零端口）

```
places in DB: 16
carrying (evaluator sees evidence): 3 ['place-tech-art', 'place-city-park', 'place-design-library']
declared (fixture asserts facts) : 3 ['place-city-park', 'place-design-library', 'place-tech-art']
equal? True
tagged_without_evidence: 12      # 只有展示 tags、没有规范化产物
untagged and unevidenced: 1

[raw tags column only]        _accessibility_metadata -> None   STROLLER [] LARGE_LUGGAGE [] STEP_FREE ['ACCESSIBILITY_UNVERIFIED:P','NEEDS_LIVE_EVIDENCE:P']
[taxonomy tags only]          _accessibility_metadata -> None   （同上）
[normalized accessibility_evidence] -> {luggage_accessible:false, stroller_accessible:false}  STROLLER ['STROLLER_ACCESS_UNAVAILABLE:P'] LARGE_LUGGAGE ['LUGGAGE_ACCESS_UNAVAILABLE:P']
[normalized osm_tags]         -> {osm_tags:{highway:steps,step_count:12}}  STEP_FREE ['ACCESSIBILITY_CONFLICT:P']
```

两条顺手量到、写进门注释的事实：
* `raw tags only` 与 `taxonomy tags only` 的 verdicts **逐字相同** ⇒ T1 与 T3 钉的是同一扇门的两种措辞，
  T3 的独立价值在**库存比较**（防止某天有人把这列并进证据集合）。
* 求值方读到嵌套 `accessibility` 就提前返回，**不再看**同一 metadata 里的 `osm_tags`（遮蔽）。
  我第一版把两样东西塞进一条正控记录，`ACCESSIBILITY_CONFLICT` 那一半就静默消失了 —— 所以 T1 的正控
  现在是两条独立记录。这是既有的遮蔽行为，不是本单要改的东西。

## 2. 三条杀手臂（每臂一个锚点，仲裁点名的两臂都在）

驱动器 `q236_mutations.py`，收据 `q236_mutation_receipt.json`。锚点全部在
`backend/app/replanning/feasibility.py` 的 `_accessibility_metadata` 里，
每臂要求 `anchor_hits == 1`、`bytes_changed`、退出后 sha256 回到 `before_sha256`。

| 臂 |  sabotage | 声明归属 | 实际红集合 | hits | 变字节 | 还原 |
| --- | --- | --- | --- | --- | --- | --- |
| K1 | `raw_tags = … or metadata.get("tags")` 之后再加 `or _parse_json(_field(record,"tags_json",None), [])`：**直接吃原始留存列** | T1 | T1（仅 1 条） | 1 | yes | byte-exact |
| K2 | `nested = metadata.get("accessibility") or metadata.get("accessibility_evidence")` → 只留 `accessibility`：**跳过生产者写下的那一支** | T2 | T1 + T2 + T3（3 条） | 1 | yes | byte-exact |
| K3 | 投影之后追加：tags 里有裸词 `indoor` ⇒ `result["stroller_accessible"] = False`：**分类词变硬性事实** | T3 | T3（仅 1 条） | 1 | yes | byte-exact |

mutated sha256 前缀：K1 `9e7c20d35bc5975b`、K2 `b28ca80fac84abcc`、K3 `51897bb06885f88e`。
`every_node_has_a_killer = True`，`nodes_without_a_killing_arm = []`。

**归属怎么读**：K1/K3 各自只打红自己那条门（互不越界）；K2 打红三条 —— 这不是归属模糊，而是这一臂打的
本来就是三条门共用的那根管道（规范化产物不被消费时，T1 的正控、T2 的主张、T3 的库存同时塌）。
仲裁点名的"一对突变"（直接读 raw tags / 跳过 normalized producer）= K1 与 K2，两臂都必红且已必红。

这份收据在提交后于 `75bc8ca` 的工作树上整批重跑过一次（03:46），三臂的 `anchor_hits / bytes_changed /
red_nodes / owner_reddened / restored_byte_exactly` 与提交前那次（03:31，同内容树）逐字段相同；
重跑后 `git status --porcelain` 仍为空。

## 3. 分母与连击

* 全套 `--collect-only`：**1200 collected**（composite 导出树）。差集闭合：
  移走本单门文件与尺文件后 **1197**，`1197 + 3 = 1200`；`_qoder_streak_receipt.py` 对分母贡献 0（它不是 `test_*.py`）。
* 全套两遍（同树同解释器）：
  `8 failed, 1176 passed, 15 skipped, 1 xfailed` 用时 112.37s / 118.09s；
  8 + 1176 + 15 + 1 = **1200**（与 collected 对上，不是推导数）。
  两遍的红名单**逐条相同**，无游离节点（named swimmers = 0）。
* 既存红的归属证明：把本单门文件移走后单跑那 6 个文件 ⇒ 同样 8 条红**照旧**（另多一条 `g3`，
  它在"全套 1200"形态下绿、在"6 文件子集"形态下红 —— 这是冻结条款⑨/⑩的 run-shape 依赖，照实记录，不解释成矛盾）。
  ⇒ 本单没有引入任何红，也没有修掉任何红。
* 与兄弟门同树共跑：`test_qoder_ord0236_*`(3) + `test_qoder_demo_accessibility_evidence_*`(13)
  在同一进程、同一 per-process temp DB 下 **16 passed**（`seed_demo` 会 reset，两拨门互不污染）。
* 三条门的 10 进程 single-node 连击：用 Commander 的薄适配器 `live_checks/gate_streak.py`（尺 = 被测树里的
  `backend/tests/_qoder_streak_receipt.py`，共享判据，不起第三把尺）。**我没有把自己的树指给它**：
  我这棵树里没有那把尺（实测 `absent`），适配器按设计 `SHARED_MODULE_MISSING` 拒了两次（第一次还因为我
  把 `--tree` 指到仓库根而不是 `backend`）。所以连击跑在 composite 导出树上：
  `git archive 75bc8ca` + 从 lane F 的 `6f0e5fc` 取 `backend/tests/_qoder_streak_receipt.py`
  （blob `fcf76941dcc2512736c1d28fa362022b5f8c879a`，50,316 B，sha256 前缀 `5528700cfbe71711`）。
  ⇒ 连击读数属于 composite，不属于 `75bc8ca` 单独的树；跑绿这件事要带着这个标签引用。

  | 门 | 批 | rounds | green/red/not_observed | distinct DB paths | shape_verified | verdict | closure |
  | --- | --- | --- | --- | --- | --- | --- | --- |
  | T1 | 1（03:40） | 10 | 10 / 0 / 0 | 10 | True | `STREAK_MET(10)` | `STREAK_GREEN` |
  | T2 | 1 | 10 | 10 / 0 / 0 | 10 | True | `STREAK_MET(10)` | `STREAK_GREEN` |
  | T3 | 1 | 10 | 10 / 0 / 0 | 10 | True | `STREAK_MET(10)` | `STREAK_GREEN` |
  | T1/T2/T3 | 2（03:43–03:44，带内容 pin） | 10 each | 10 / 0 / 0 each | 10 each | True | `STREAK_MET(10)` | `STREAK_GREEN` |

  两批合计 **60 个进程、60 个互不相同的 app-resolved temp DB**，`receipt_problems` 全空，
  `duplicate_db_paths / runs_missing_db_path / runs_missing_fields / forbidden_targets` 全空，
  每条 run 的 `node_outcome` 由 pytest 自己的 per-node 报告佐证（`退出码与摘要计数一致`），无 `NOT_OBSERVED`。
  没用 sleep / retry / 降并发 / 放宽期望（条款⑥），命令形态由尺给出、逐字执行。

* 条款①（同一 SHA 贯穿）是**我这侧的自查，不是尺判的**：共享尺今天没有 per-run SHA 字段
  （`streak_verdict()` 只收一个 caller-supplied `sha`，related check 只有 `exact_sha_named`），
  所以批 2 在连击前后各测一次内容 pin：`backend/app` 全树聚合摘要
  `65f04811a845d9b7…` 前后相同、门文件 `9495bb933216042d…`（7,369 B）相同、
  `feasibility.py` `87bbb2c5dfa0d0de`（40,032 B）相同；`one_sha_across_runs = true`。
* **两处必须自己说出来的弱点**：
  ① `closure_grade` 只到 `STREAK_GREEN`，不是 `CLOSED` —— 尺要 `reverse_mutation_result ∈ {KILLED, STREAK_BROKEN}`
  才允许闭包，而我只有 forward 杀手臂的收据。适配器可以用 `CNX_ORD0210_REVERSE_MUTATION=KILLED` 这个
  **字符串声明**把它推过去，我故意没推：仲裁已经说过"no CLOSED may be signed off the back of an env var"。
  ② T1/T2 两条门纯内存跑（不碰库），它们的 `final_row_counts` 是 `{"absent": true}` 10/10；
  只有 T3 真的建库（`table_count: 55`）。⇒ T1/T2 的"每进程新库"这句在事实上比 T3 弱：
  它们根本没有共享状态可言，连击对它们只证明"同一条确定性判定重复 20 次不变"，不证明隔离性。
  隔离性的真证据是全套形态下的 1200 条共跑与 16 条同树共跑（上面两条）。

## 4. (c) 迁移盘点的一角（Commander 说顺手给一句，这是读数）

sealed demo 库 16 个地点的 `tags_json` 共 **16 种 token，全部是裸展示/分类词**：
`culture 7, indoor 7, outdoor 7, local_food 5, history 4, waterfront 4, art/bars/night_view/quiet/relaxed/scenic/shopping/signature_dish/street/view 各 1`。

* **OSM 式 `key=value` token 在这列里 = 0 条**；把整列原样喂给 `normalize_osm_tags()` 对 **16/16 返回空**。
  ⇒ 今天这列里没有任何"会被规范化器误食"的东西，所以 T1 的红完全靠"求值方不看这列"这个边界本身，
  而不是靠"这列恰好没内容" —— 这正是把契约写成门而不是写成偶然实现的原因。
* 最靠近"会被人类当成证据"的展示词是 `indoor`（7 家，其中 2 家已有规范化证据）与 `quiet`（1 家，已有证据）。
* 需要迁移到规范化通道的候选 = **12 家只带 tags、没有证据**的地点（T3 的 `tagged_without_evidence` 名单）。

## 5. 坐标

本地提交 `75bc8ca192db547a6169540ce28ce2f6f2d9fe4d` 是**树内坐标**，不是仲裁可读的坐标
（工作 tip SHA 在 GitHub 返回 422，已量过多次）。所以本单一律发布到
`Canshu-King/CityNexus @ commander/control`。下表 7 件都是**远端读回**
（`GET /contents/<path>?ref=commander/control`）确认可读的：读回做了两次，分支头分别是
`39ed5aa03b5d`（第一次，其中 `gate.patch` 与 `mutation_receipt` 吃 `SSL UNEXPECTED_EOF` 噪声）与
`1ff0c6f267c5`（第二次，7 件全部可读）；下表 sha1 取第二次那次。

| path | 远端 git blob sha1 | bytes |
| --- | --- | --- |
| `evidence/ord0236/75bc8ca_gate.patch` | `aa74c1f72867e181aac8a254b32e60607b216f7f` | 7,788 |
| `evidence/ord0236/75bc8ca_mutation_receipt.json` | `af16fc122ae0ce53ecf2e5f2a583254ea224f3c6` | 3,610 |
| `evidence/ord0236/75bc8ca_readings.txt` | `a6b95792f6e21603874bcb9c6909116bfd02ce14` | 2,470 |
| `evidence/ord0236/75bc8ca_inventory.txt` | `c2c2d0f0c2784971215ce4518d1da017b24582f8` | 880 |
| `evidence/ord0236/75bc8ca_streak_batch1.txt` | `dd8688fd66c3e9f54bee065d150df69e1efd6bd0` | 4,961 |
| `evidence/ord0236/75bc8ca_streak_batch2.txt` | `16d34dfb6f7c184dff664a2b25ac8f262668569f` | 4,956 |
| `evidence/ord0236/75bc8ca_clause1_constancy_batch2.json` | `fda8ef80453492541b3651b677e94ce3100b53e6` | 1,383 |

本报告自己（`evidence/ord0236/75bc8ca_report.md`）的 blob 坐标写在账本 ORD-0236 条目里 ——
一个文件装不下自己发布之后的哈希，这是自引用，不是漏项。

`gate.patch` 是 `git diff 318a034 75bc8ca` 的全部输出：只有 `backend/tests/test_qoder_ord0236_raw_tags_not_evidence.py`
一个新文件，`app/` 一行未动。

本地工具（不在 Git 里，需要现场跑才有输出）：
`_qoder_spike_20260921/q236_readings.py`、`q236_token_inventory.py`、`q236_mutations.py`、
`q236_streak_summary.py`、`q236_clause1_constancy.py`、`q236_readback.py`；
composite 导出树 `_qoder_spike_20260921/snap_ord0236/`（`git archive 75bc8ca` + F 的尺）。

## 6. 我这侧的判定与请求

* 本单可签：`STREAK_GREEN`（三条门各自 20 进程全绿）＋ 每条门有具名杀手臂且杀手以该门语义变红。
* 本单**不**自签 `CLOSED`：尺要 forward/reverse mutation 的收据格式由仲裁指定，而 `CNX_ORD0210_REVERSE_MUTATION`
  只是一个 env 字符串声明，我不拿它换闭包。
* 请仲裁看一眼的一件事：T3 的库存断言把"求值方可见证据集合 == 生产者声明集合"钉成了等式。
  今天两侧都是 3；如果将来 real-city provider 路径也产出 `accessibility_evidence`，
  这条等式会先红在这里 —— 那是**期望的**红（边界移动了），不是门坏掉，但需要有人认领"届时改成子集判断还是扩声明集"。
