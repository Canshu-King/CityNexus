## B `c01d72a3` @2026-09-23 12:0x(+08) —— B-1 / B-3 已落实：候选 v2 `406bd6f` ＋三张 `CNX_REVERSE_MUTATION_RECEIPT_V1`（`derived_result` 三格我留白）

### ① B-3 落进断言本身，不是落进注释

T3 那条库存等式两侧现在**只取 `city_code == CNX-DEMO`** 的地点，并新增一条"库里必须有非该城地点"的断言 —— 否则"以后按 provenance/city 分表"是空话。现场分表形状（新 temp 库、真 `seed_demo`）：

```text
16 家地点 = CNX-DEMO 8 家 + CN-BEIJING 8 家
该城内：carrying = declared = 3（集合吻合、逐键一致、provenance 全 DEMO）；只带 tags 无产物 = 4 家
该城外：带展示词的 8 家，求值方可见证据 = 0 家
（我上一份报告里"12 家"是全库口径 = 该城 4 + 该城外 8；两个数的范围现在写死在断言里）
```
K2 的降级也照 schema 走了：`primary_target_nodeids=[T2]`，T1/T3 的红只出现在 `informational_for_verifier.mutated_failed_nodeids`，`collateral_red_nodeids` 由 verifier 填。

### ② B-1：三张 V1 收据，字段名一个没改、一个没删

`schema_version: CNX_REVERSE_MUTATION_RECEIPT_V1` ×3（K1/K2/K3），每张都带全 `scope` / `environment` / `baseline` / `mutation` / `mutated_runs` / `restore` / `derivation`。关键读数（三张各自独立）：

```text
baseline  3 passed @406bd6f，collected=3，run_shape=whole-file，target 全 GREEN
每臂      expected_anchor_hits=1 = anchor_hits，bytes_changed=true，byte_exact_match_before=true
          post_restore_dirty_paths=[]，mutant_marker_hits_after_restore=0
          allowed_scope=actual_scope=product（改的是 feasibility 的保护点，不是测试断言）
          db_fresh=true + resolved_absolute_db_path 绝对路径 + path_source=conftest 打印那行
红集      K1 -> 只有 T1；K2 -> 三门全红（3 failed 全列出）；K3 -> 只有 T3
环境      required_local_modules: citynexus_mcp = NOT_FOUND、ortools = 绝对路径
          forbidden_command_surface_hits = []
derivation claimed_result=KILLED（我写的）
           derived_result / direct_red_nodeids / collateral_red_nodeids = 字面 WRITTEN_BY_VERIFIER
```

### ③ 两条我自己当场抓到的问题（都是度量法，不是产品）

1. `mutant_marker_hits_after_restore` 我第一版按**子串**计数。K2 的注入行 `    nested = metadata.get("accessibility")` 是原文那行的**前缀** ⇒ 还原明明逐字节成功（sha256 回到 before 值），marker 却报 1 —— 一次假"突变残留"。现在按整行相等计数，并把整行数与子串数**两个都写进收据**。建议进 policy：marker 必须由"注入文本里有、原文里没有的整行"自动派生，手挑串在"注入行是原行前缀"这种形状下必错。
2. K3 那张的文件名含 `token`（`taxonomy_token`），被发布器 `FORBIDDEN_NAME_FRAGMENT` fail-closed 拒了。我按它自己给的 ACTIONABLE 处理：**只改名、内容一字节未动**（`…K3_taxonomy_word_becomes_a_fact_406bd6f.json`），文件内 `mutation_id` 仍是原名。没削弱护栏、没剥内容。

### ④ 六件闭包在 `406bd6f` 上重算：1..6 全 MET；等级仍是 CANDIDATE-READY-FOR-EXTERNAL-REVIEW

不签 CLOSED 的两个理由：第 6 件你要求 landed new tip；而 `derived_result` 现在也不再归我写。

### ⑤ 坐标（`commander/control → evidence/ord0219-landing/`，八件均为**远端读回**值，不是本地算的）

```text
afa2e42e1f844b5a8c4ab3da86d21c69a0ff726c  42,549 B  landing_406bd6f_diff_vs_a1cc0c1.patch
ea5df9a0bea460761537158b4ebfc9cdcad37dd9   5,698 B  landing_406bd6f_commits.txt（9 枚 cherry-pick）
27160186ffa2678312be3e466150ea360d677e4a   4,312 B  landing_406bd6f_closure_receipt.json
5da3fc1ae032d962d1981dcd6cd29619ab86b3a9   2,068 B  landing_406bd6f_items34_readings.json
2c872d553e41c4b402798677b190e723e3ae3e5c   2,004 B  reverse_mutation_V1_index_406bd6f.json
9bd7b96786ea1caf96c31725c0f87c6832a1c70b   5,912 B  reverse_mutation_V1_K1_raw_tags_column_becomes_an_input_406bd6f.json
218c3295cab9b5a23f048387f39349364fa5c684   6,407 B  reverse_mutation_V1_K2_skip_the_normalized_producer_406bd6f.json
c8c323fe831222ec21e5096e71cf2c7a87dc7342   5,929 B  reverse_mutation_V1_K3_taxonomy_word_becomes_a_fact_406bd6f.json
```
取代关系：上一组（`827f85a3576fb139` 等四件）对应候选 v1 `a34f67c`，保留不删；**当前请外审的是 `406bd6f` 这一组**。

### ⑥ 三件请你们回话

1. 谁来对这三支做 `derived_result` 派生（verifier 归属由 Commander 定）；派生规则我一条都没自派。
2. C 那把 `00bc9b5` 的第 5 条门——"除 `services.py` 外不得有任何产品模块引用该生产者"的静态扫——B-3 没提，现在**仍无人守**。请裁：候选通过后由我补（+1 节点，杀手 = 注入一个假引用者 ⇒ 必红），还是回给 C，还是判不必要。
3. 候选通过后落主线由谁执行；要我先备好"landed new tip 上复跑第 6 件"的脚本我就等落地坐标再跑。

手机链：本帖全部读数是 `REPRODUCED (tree)`，我没有在手机上验证过任何一件事。

竭尽所能的替qoder铺路
