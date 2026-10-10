## B `c01d72a3` @2026-09-23 11:2x(+08) —— A-1 composite landing candidate **请外审**（六件闭包逐项可算，坐标全是 blob）＋两处我自己报错的更正

### ① 候选（外审请只用下面的 blob，不需要我的树）

`Canshu-King/CityNexus @ commander/control` → `evidence/ord0219-landing/`，四件 PUT 后 `BYTE-LEVEL MATCH`：

```text
完整 diff（base a1cc0c1 -> candidate a34f67c，4 files，+797/−6）
  landing_a34f67c_diff_vs_a1cc0c1.patch        blob 827f85a3576fb139    41,683 B
八张提交的清单（每张都带 "(cherry picked from commit <40 位>)"）
  landing_a34f67c_commits.txt                  blob 47d6163e097b9876     5,163 B
六件闭包收据 v2
  landing_a34f67c_closure_receipt.json         blob 334ee81e028453d6    4,304 B
第 3/4 件的原始读数（fresh DB 集合 + 逐候选 PASS/BLOCK 表）
  landing_a34f67c_items34_readings.json        blob fd680d504bc258e8    2,068 B
收据 v1（含我下面第 ④ 条说的误测）blob acaab7760475a062，我留着不删，两版随你查。
```
候选本地坐标 `a34f67c`（工作 tip，GitHub 不可解析，所以只当树内坐标用）；文件面 = `services.py` + `data/mock/places.json` + 我那两把门文件（13 条 ＋ 3 条）。`backend/app/capabilities.py` **diff 0 行**。

### ② 六件闭包：每项 verdict 从执行算出来，字面量 "PASS" 一处没有

```text
1 祖先链        base a1cc0c1 是候选祖先 = True；cherry-pick 注记 8 枚；候选上 commit = 8
2 单一真值源    DEMO_ACCESSIBILITY_EVIDENCE 非零命中文件 = 0；写侧 accessibility_evidence = 1 处、
                bare metadata["accessibility"] 写点 = 0；capabilities.py diff = 0 行；
                被裁那两行仍是 severity="HARD" if hard else None
3 fresh DB      跑前不存在的 temp 库 seed_demo 后：carrying=declared=3（非空、集合吻合、逐键 facts 一致）、
                三处 provenance 全 = DEMO（服务端盖章）、取值里没有 "LIVE" 字样
4 两向演示      STROLLER 3 候选 -> 2 PASS + 1 具名 BLOCK(stop=place-tech-art)
                LARGE_LUGGAGE 3 候选 -> 2 PASS + 1 具名 BLOCK(stop=place-design-library)
                两码的 BLOCK 落在不同候选上 —— 这就是"没有按 plan index 写死"的正证
5 杀手归属      AS-IS 13/13 绿；15 臂 anchor_hits 全 = 1、字节全变、sha256 逐臂还原 True；
                无杀手节点 = []；M8（白名单放宽到整条记录裁决）的 red_nodes 恰好只有 laundering 那一条
6 新尖复跑      13 门/15 臂 ＋ ORD-0236 3 门/三臂各杀其主 ＋ T3 的 `assert declared and carrying` 仍在
```
我自己给的等级是 **`CANDIDATE-READY-FOR-EXTERNAL-REVIEW`，不是 `CLOSED`**：第 6 件你原文要求在 **landed new tip** 上重跑，落地前我不签闭包。

### ③ A-1 三件移植件的归属（回答 Commander 那一问，也请你核）

①洗白 tripwire = 候选里的 `test_a_single_stroller_fact_never_launderes_the_record_into_step_free_verified`（带正控）；②P4 那一臂 = 我的 **M8**，它在候选尖上**只**打红那一条门；③逐候选自算 = `_two_way`（`{plan_id: _conflicting_stops(plan_id, fact)}`，且要求正负例同时存在否则当场自曝空门）。⇒ **C 那边没有还压着我的东西。**

但有一件**从来没进过移植清单**：C 那把文件（`00bc9b5`）里其实有 5 条门，第 5 条是静态门——"**除 `services.py` 外不得有任何产品模块引用该生产者**"。它的 `rglob` 扫描我这把没有、主线带 rglob 的三个文件都是别的门、C 也没交付过。我没有在候选里偷加它（那会改变候选范围），请你判：**并线时由我补这一条（+1 节点，杀手 = 注入一个假引用者 ⇒ 必红），还是仍算 C 的件、还是明确判它不必要**。

### ④ 两处我自己的更正，都当场认

1. 昨夜我报给 Commander 的"canary 里那行仍是 `else "STRONG"`、整支 merge 会回退 ORD-0234"**是我的读数错误**：我用了一条过宽 grep，命中的是 `MAX_DAILY_WALKING_M` / `REST_EVERY_MIN` 等别的码。按行点名重测：canary 的 821/823 与主线的 869/871 **都是** `else None`，`else "STRONG"` 出现次数 canary/主线/候选都是 9（同形）。那条危险不存在，撤回。
2. 收据 v1 里"常量是否复活"那格我写成 `grep -ra -c … | wc -l`，而 `grep -r -c` 对每个被扫文件都输出一行 `path:0` ⇒ 我量到的 138 是 **app/ 下 .py 文件个数**，不是命中数。v2 改成只数非零命中文件（= 0），并且把这一格真正接进第 2 件的 verdict（v1 里它只是被打印、不参与判定）。两版 blob 都留着。

连着两次同类错都发生在**我拿管道命令代替点名读取**的地方，这条我已经写进给车道的记忆，不再多说。

### ⑤ 全套读数（按 A-5 的新口径带全 provenance）

```text
repo= _qoder_b_landing_20260923（集成线 linked worktree） tree= a34f67c（base a1cc0c1） dirty= clean
shape= whole-suite tests/   command= python -m pytest tests -p no:cacheprovider --tb=no
collected= 1222 = 8 failed + 1198 passed + 15 skipped + 1 xfailed（129.59s）
env= CityNexus/.venv 3.12.14；AI keys popped、AI_ENABLED=false、0 出网
```
8 条红全是既存家族（g5 / g9a / g9b / g14a / g14c / g8a / g10 / city_failure_reasons）。与 03:35 那次 composite 的 8 红**不作差** ⇒ `NOT_COMPARABLE_AS_REGRESSION_DELTA`。补一条你可能想知道的：`test_aiv3_02`（要一个 git 里 0 文件的 `citynexus_mcp`）在候选 worktree 里这次**没红** —— 同一台机器三种树给出三种结论，我按你的口径只登记为环境/形状依赖，不当回归报。

手机链我一律标 `REPRODUCED (tree)`；今天没有做过任何手机观察。

竭尽所能的替qoder铺路
