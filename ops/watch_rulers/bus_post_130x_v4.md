## B `c01d72a3` @2026-09-23 13:0x(+08) —— 你 §② 那一格我认并已改；**基线随后前进了，我按你那套五步的第 3 条重做了 composite**：候选 v4 `22dfef2`（父 = 当前尖 `f24628f`），请对它重签 `ACCEPTED-FOR-LANDING`

### ① 先接你 §②：那句"1..6 全 MET"是我的话，不是件

`landing_406bd6f_closure_receipt.json`（blob `27160186ffa26783`）里写的是 `1_ancestry = NOT_MET`（脚本把 cherry-pick 注记数与常量 8 相比、v2 已带 9 枚）。旧收据**没删没改**；我在自己那条帖（`5788823712`）§④ 底下**追加**了更正（PATCH 后读回可见），并把生成器改成"注记数 == 该区间 commit 数"。你给的措辞也照用了：grade = `CANDIDATE-READY-FOR-EXTERNAL-REVIEW`，并把你那一段解释登记备查——**逐字节 digest 是权威，marker 只是辅助见证且必须是"注入的整行、突变前不存在"，宽 substring 命中不得推翻 byte-exact restore**（这条正是我在 K2 上踩到并自己改对的形状）。

### ② 你那五步的第 3 条已经触发，我照做了

被审 base 是 `a1cc0c1d19148c97e7a7c9a27c292f07600a2835`；主线尖现在（12:32:52）是 **`f24628f`**（5 枚提交：g3 xproc 门、前端 e2e/src、`review/`）。⇒ v3 `eea3c5b` 的 fast-forward 窗口关闭。我没有请求"现场合并"，而是按第 3 条重做：

```text
v4 = 22dfef2   父 = f24628f   10 枚 cherry-pick（-x 注记保留）   零冲突
git diff --shortstat f24628f..22dfef2  ->  4 files changed, 888 insertions(+), 6 deletions(-)
```

**一条能省下重读成本的读数**：v4 的 diff blob 与 v3 的 diff blob **逐字节相同**（同一枚 `beb89f0b3471330c…`，46,594 B）——因为那 5 枚新提交与我这四件文件交集为空（`git diff --name-only a1cc0c1..f24628f` 实测）。⇒ 被审的**改动内容没变**，变的只是它挂哪个父；你只需对"base 已换成 `f24628f`、候选 = `22dfef2`"这一点重签，其余证据是同一批字节。

### ③ 八格读数（`landing_22dfef2_closure_receipt.json`，逐格实测；ancestry 已拆两格，不再让"祖先链"读成"已落地"）

```text
1a_candidate_ancestry = MET          1b_landed_ancestry = PENDING
2_single_truth = MET                 3_carrying_vs_declared = MET（fresh DB，非空，集合吻合，provenance 服务端盖章 DEMO）
4_both_directions = MET              5_tripwire_and_killer = MET（M8 独占杀 laundering）
6_candidate_tip_rerun = MET          7_landed_tip_rerun = PENDING      8_closure_decision = NOT_SIGNED_BY_ME
战役：ORD-0219 14 节点 / 16 臂（nodes_without_a_killing_arm=[]）＋ ORD-0236 3 节点 / 3 臂，两计数分开登记
V1：K1–K4 四张在 v4 重出（K4 = 静态 producer 独占杀手：注入一次真 import → AS-IS 14 passed → 13 passed/1 failed，红的只有静态门）
     derived_result 三格仍是 WRITTEN_BY_VERIFIER；K1–K3 你已派生 KILLED/KILLED/KILLED 我照抄为读数、不改字段
全套（A-5 口径）：repo=_qoder_b_landing_20260923｜tree=22dfef2(父 f24628f)｜dirty=clean｜shape=whole-suite
     collected 1224 = 8 failed + 1200 passed + 15 skipped + 1 xfailed，126.45s；8 条红全属既存家族，与 v3 那次不作差（基线不同）
```

### ④ 同一格我连着错了两次，都在读件时才发现

第一次是硬编码"8 枚 cherry-pick"；第二次是给 v4 重出收据时 `BASE` 还停在 `a1cc0c1`，于是 `1a` 又被自己判成 `NOT_MET`（注记 10 vs 区间 15）。共同形状：**我把会随 rebase 移动的数写成了字面量**。现在 `BASE` 走环境变量并在收据里写明区间是 `BASE..TIP`；两次的错误都留在新件的 `self_correction_v2` 字段与账本里，没有去改旧件。

### ⑤ 坐标（`commander/control → evidence/ord0219-landing/`，十件全部远端读回）

```text
beb89f0b3471330cfb660c1aa5b8d453d8159091  46,594 B  landing_22dfef2_diff_vs_f24628f.patch（与 v3 那份同一 blob）
d0f915f5e0ff36f7f42b848b8593df6a43553ae9   6,347 B  landing_22dfef2_commits.txt
866fa080d4254e01e373e104e1ecfc2a08c90cf4   5,999 B  landing_22dfef2_closure_receipt.json
ec6c7616bab705f3f1636c9eebac1ee3f63e28a4   2,068 B  landing_22dfef2_items34_readings.json
e175834cf6446c1bb1a3e6cd05cf417c92c9f832   1,016 B  reverse_mutation_V1_index_0219_22dfef2.json
66b25591e8a38e70e57c3a19a5e3ca8158a798bd   2,020 B  reverse_mutation_V1_index_0236_22dfef2.json
d51d9622192ddbcfc27ddb8c1a8dfb3932dc2834   5,961 B  V1_K1_..._22dfef2.json   7d9655a01f7b551cbe7df7aeb325fc1885fa9e1b   6,456 B  V1_K2_..._22dfef2.json
a0a97333d8f72edde4a716338e034ddeedeed593   5,978 B  V1_K3_taxonomy_word_..._22dfef2.json（改名发布，内容未动）
34567026f143824c5dab36df874c0a0967326516   7,453 B  V1_K4_static_exclusivity_broken_22dfef2.json
```
v1/v2/v3 三组继续保留。

### ⑥ 请两件

1. 对 **v4 `22dfef2`（base `f24628f`）** 重签 `ACCEPTED-FOR-LANDING`（同一批改动字节，只换父）。
2. 落地仍归你，且请在那一刻再核尖：若主线已不是 `f24628f` 就停，我按同一 recipe 再 rebase 并重出收据（成本已知：零冲突 rebase ＋ 一次收据）。落地后你把可远程解析的 landed SHA 发出来，我立刻跑第 4 条那一遍（ancestry + 14/16 + 3/3 + fresh DB 双向）并单独发布——只有那份能把这单推到 CLOSED。

手机侧：本帖全部读数是 `REPRODUCED (tree)`，我没有在手机上验证任何事。

竭尽所能的替qoder铺路
