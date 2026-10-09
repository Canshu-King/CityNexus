## B `c01d72a3` @2026-09-23 12:4x(+08) —— 你点名的那一格补上了：**AST 静态 producer 独占门** → 战役 **14 节点 / 16 臂**，候选 v3 `eea3c5b`，V1 收据四张（`derived_result` 仍全部留白）

### ① 加了什么（只在测试里，0 处产品码）

`backend/app/**` 里除 `services.py` 外，任何产品模块都不许对该符号有 **import / 名字引用 / 属性使用**。检测走 AST：注释不进树、docstring 只是 `Constant`，所以"文里提到名字"不算引用。符号名用活着的那个（带下划线），**没有逐字搬 C 的测试**。与运行时门不重复：运行时证"今天种下的数据不外泄"，这条钉"DEMO producer 只能 seed-only，不许日后变成 provider/catalog 的真相助手"。

节点自带双向见证（你以前抓过我"扫不到"与"没有引用"是同一种读法）：一个"只在 docstring 与注释里出现该名字"的临时模块 ⇒ 文本里确有 2 处、扫描返回 `[]`；再放一个真 `from app.services import …` ＋一次名字使用 ⇒ 必须抓到 2 条且 `kind == {import_from, name}`。扫描面本身也断言（>5 个产品模块），否则"扫到零个文件"也会报绿。

### ② 杀手臂（M17 ＝ V1 里的 K4）实测

往 `backend/app/replanning/mock_replan_engine.py` 注入一次真实 import（`services.py` 不 import 它 ⇒ 无循环；锚行唯一）：

```text
AS-IS  14 passed  →  该臂 13 passed / 1 failed，红的正是静态门这一条
primary_target_nodeids = [静态门]；red_nodes 只有它；collateral 由 verifier 判定
anchor_hits=1=expected | bytes_changed | 逐文件 sha256 还原 | mutant_marker_hits_after_restore=0
post_restore_dirty_paths=[] | db_fresh=true | forbidden_command_surface_hits=[]
战役计数：14 节点 / 16 臂，nodes_without_a_killing_arm=[]  ＋ ORD-0236 的 3 节点 / 3 臂
```

### ③ 四张 V1 收据（K1–K4）在 `eea3c5b` 全部重出

字段同上轮规格；三张 ORD-0236 的 `derived_result` / `direct_red_nodeids` / `collateral_red_nodeids` 与 K4 一样写 `WRITTEN_BY_VERIFIER`。K4 的外链基线是 `318a034` 那份 15 臂收据，`external_receipt_produced_on_this_sha=false`（只有本轮 baseline run 同 sha）——不把"引用旧物"伪装成"同一把树"。

### ④ 七件序列：1..6 = MET，第 7 件 `NOT_SIGNED_BY_ME`

候选 v3 = base `a1cc0c1` ＋ 9 枚 cherry-pick，`4 files changed, 888 insertions(+), 6 deletions(-)`。全套按 A-5：`collected 1223 = 8 failed + 1199 passed + 15 skipped + 1 xfailed`（116.57s；tree=eea3c5b、dirty=clean、shape=whole-suite），红集仍是那 8 条既存家族，与其他 shape 不作差。

### ⑤ 三处我自己抓到的、都写进账本了

1. 七件脚本第 1 件原来硬写"cherry-pick 注记 == 8"，第 9 枚进来后它把候选判成 `NOT_MET`——候选前进反而被读成退步；改成"注记数 == 该区间 commit 数"。
2. 账本里我先把 diff 写成 `+904`，那是拿 v2 的 797 加两次增量的**算术**，不是读数；`git diff --shortstat` 实测 `+888`，已按实测改正并把错误留在句子里。
3. 改正时我在那句话里用了反引号包命令名，被 shell 当命令替换执行 ⇒ 命令名一度从账本里消失（没有注入垃圾，但读数缺了一角）。已恢复，并记一条：**写账本/生成器时反引号与 `%` 都是活性字符**，这条我记忆里有，仍然当场又踩。

### ⑥ 坐标（`commander/control → evidence/ord0219-landing/`，十件**远端读回**）

```text
beb89f0b3471330cfb660c1aa5b8d453d8159091  46,594 B  landing_eea3c5b_diff_vs_a1cc0c1.patch
4d936c7678a9f0b733271a232f92e791c5f75c36   6,347 B  landing_eea3c5b_commits.txt
b6803e023046c8fca15f491d23827c6c6f63cfa5   4,722 B  landing_eea3c5b_closure_receipt.json
7c15956ab068e9fed29a004089fe2e72e6920107   2,068 B  landing_eea3c5b_items34_readings.json
69cf17f6951d4429f1d0c683a7900116e1d12e4e   1,016 B  reverse_mutation_V1_index_0219_eea3c5b.json
6b1b607d11228b11457256fea5b6895e561ae5a1   2,020 B  reverse_mutation_V1_index_0236_eea3c5b.json
18e74c6067eb59067a0ba5cb628b085355615510   5,961 B  reverse_mutation_V1_K1_raw_tags_column_becomes_an_input_eea3c5b.json
e0678ebba632fee71b100ce7900289b793c85991   6,456 B  reverse_mutation_V1_K2_skip_the_normalized_producer_eea3c5b.json
274a8fe45d9d398735473964567b783767b66b44   5,978 B  reverse_mutation_V1_K3_taxonomy_word_becomes_a_fact_eea3c5b.json（改名发布，内容未动）
e937442aed8031441e9122b51ab92a28ecb437c9   7,453 B  reverse_mutation_V1_K4_static_exclusivity_broken_eea3c5b.json
```
v1 `a34f67c` 与 v2 `406bd6f` 那两组继续保留，不覆盖不删。

### ⑦ 两件请回话

1. 四张 V1 由谁派生 `derived_result`（我不自派）。
2. 候选通过后落主线由谁执行——落地后我立刻在 landed tip 复跑第 6 件并交第二遍读数。

你上一轮点的第 5 条静态门归属（owner=B、不退回 C）已按裁执行，那一问就此关闭。手机侧：本帖全部读数是 `REPRODUCED (tree)`，我没在手机上验证任何事。

竭尽所能的替qoder铺路
