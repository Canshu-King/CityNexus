# ORD-0272 · K8 升格 + Q24 合流

lane F `8ccd71d8` · 2026-09-25T04:25:27+08:00

候选 `7c806fab5`（父 = 已落地的 `dcae1bc96`，`parent_is_landed_generation=True`），ref `review/ord0272-k8-f`。

## 1. K8 从「没有载体」变成有 carriers_removed 的一臂

红队把 K8 判成 `UNPROVEN_AS_KILL / OBSERVED_AS_BEHAVIOUR`，理由是单进程 HTTP 面走不到「覆盖那一幕」
（Phase A 的唯一索引让第二个抢键者停在 409）。我接受，所以这一轮不硬凑击杀数，而是：

* 把 Phase B 的回填抽成可直调的缝 `_fill_plan_generation_receipts(...)`（同一条带守卫的 UPDATE、
  同一个状态/正文推导、少填一把照样抛现成那句 409 ⇒ 行为不变）；
* 给这条不变量一格载体 **G9**：负例 = 别人已填的回执逐字不动 + fill 返回 0；
  正控 = 我占的 NULL 必须填成 1 并持有我的答案 ⇒ 这一格不会靠「永远失败」蒙绿。

```text
删的那一行 :                    IdempotencyKey.response_json.is_(None))
carriers_removed : ["test_G9_a_filled_receipt_is_never_rewritten_by_a_later_answer"]
逐格红轮数 : {"test_G9_a_filled_receipt_is_never_rewritten_by": 3}
期望绿仍绿 : True   意外红 : 无
claimed_result : KILLED_CANDIDATE_ALL_ROUNDS_RED（derived_result 仍为 null，不自签）
```

八臂总览（campaign v2，34 格/轮 × 3 轮，控制轮 34 passed, 2 warnings in 5.87s）：

```text
K1_claim_stops_committing_before_generation    KILLED_CANDIDATE_ALL_ROUNDS_RED  carriers=6
K2_two_identities_merged_into_one              KILLED_CANDIDATE_ALL_ROUNDS_RED  carriers=1
K3_mission_ownership_door_removed              KILLED_CANDIDATE_ALL_ROUNDS_RED  carriers=1
K4_link_event_stops_naming_the_plans           KILLED_CANDIDATE_ALL_ROUNDS_RED  carriers=1
K5_both_replay_doors_removed                   KILLED_CANDIDATE_ALL_ROUNDS_RED  carriers=5
K6_unowned_path_laundered_into_a_bare_500      KILLED_CANDIDATE_ALL_ROUNDS_RED  carriers=5
K7_refusal_stops_persisting_the_durable_fact   KILLED_CANDIDATE_ALL_ROUNDS_RED  carriers=2
K8_receipt_overwrite_guard_removed             KILLED_CANDIDATE_ALL_ROUNDS_RED  carriers=1
survivors 合计 0、意外红合计 0、每轮字节级还原 True
```

## 2. A/B（候选 vs 已落地那一代，3×3，全新临时库）

```text
分母 {"candidate_7c806fa": 1233, "base_dcae1bc9": 1232}（差 1 = 新增的 G9）
每轮红数 候选=[8, 10, 8] 基线=[10, 9, 7]
only_in_candidate=[]  only_in_baseline=[]
两树三轮恒红 8 条（= 已知基线红）
判级：MET：候选独有红 0 条、基线独有红 0 条；分母 1233 vs 1232（差 1 = 本代新增 1 格 G9）
（第一版把期望分母差写死成上一代的 8 ⇒ 误报 NOT MET；底层逐轮读数一字未动，只重算判级，改前值留在 ab_3x3_r3.json 的 recompute_note 里）
```

## 3. Q24 合流：逐格两代 blob，缺任一侧就不是「可转移」

```text
backend/app/main.py                                  416ea4f210 vs ad13f4395e  -> NOT_TRANSFERABLE_GENERATION
backend/app/schemas.py                               2e6e26ce17 vs 2e6e26ce17  -> TRANSFERABLE_BY_CITED_BLOB_EQUALITY
backend/tests/test_qoder_ord0272_continuation.py     efa783397e vs 799fbd2fe9  -> NOT_TRANSFERABLE_GENERATION
contracts/openapi.yaml                               484c64cdaa vs 484c64cdaa  -> TRANSFERABLE_BY_CITED_BLOB_EQUALITY

九格逐格判定：可转移 0/9（阻塞文件：backend/app/main.py, backend/tests/test_qoder_ord0272_continuation.py）
⇒ main.py 与本门文件在两代之间都变了，所以本收据里九格全部是**在候选代实测**的，没有一格沿用旧代；旧代那几份（day1/坐标件）继续按它们自己的代成立，不折算过来。
```

## 4. 我这把尺自己被抓到的两处松（已修，双向自测钉住）

```text
· 格子清单写死成 8 个名字 ⇒ 新增的 G9 会被静默漏掉，而且照样报 GATE-GREEN；
· 八臂载体表是仪器内嵌副本 ⇒ campaign 升格后 K8 在仪器里还是 0/0。
现在：清单与臂表只从 campaign 收据读，读不到判 ARM_TABLE_UNTRUSTED（拒判，不给绿）；
可收集判定=整条 nodeid 相等；外层仓库的 HEAD 一律不拿来盖章。

五向自测（一条命令）：
[selftest] 有门的树 -> GATE-GREEN（收据点名 9 格，9/9 绿）
[selftest] 没有那扇门的树 -> NOT-PRESENT
[selftest] 错根探针（backend/…::x 必被判不匹配）-> BITES
[selftest] 嵌在别的仓库里的导出树 -> SHA_SOURCE_MISMATCH（被拒：不给别人的 HEAD 盖章）
SELFTEST_PASS
```

## 5. 坐标

```text
evidence/ord0272-k8-q24-lane-f/K8_Q24_RECEIPT.md
evidence/ord0272-k8-q24-lane-f/k8_q24_receipt.json
evidence/ord0272-k8-q24-lane-f/mutation_receipt_v2.json
evidence/ord0272-k8-q24-lane-f/ab_3x3_r3.json
evidence/ord0272-k8-q24-lane-f/gate_reading_k8_with_q24.json
evidence/ord0272-k8-q24-lane-f/q24_two_generation_blobs.json
evidence/ord0272-k8-q24-lane-f/cnx_generation_transfer_check.py
evidence/ord0272-k8-q24-lane-f/o272_reverify_r4.py
evidence/ord0272-k8-q24-lane-f/r4_selftest.txt
evidence/ord0272-k8-q24-lane-f/k8_ref_lsremote.txt

候选 ref 回读行：7c806fab58e872060cb5811ff96c770b40dad165  refs/heads/review/ord0272-k8-f
git blob（本代）：{
  "backend/app/main.py": "ad13f4395e3405ce722ae8660836f3c2aaa29df2",
  "backend/app/schemas.py": "2e6e26ce17a9e25a40dd8d686f64def5ef1bff0e",
  "backend/tests/test_qoder_ord0272_continuation.py": "799fbd2fe9d28433405408ddec1d7405b2d1c9d9",
  "contracts/openapi.yaml": "484c64cdaaa41e72d252563b84cef915cb4e80eb"
}

## 6. 仍未测（不越界）

* K8 的**跨进程**那一腿归 HJ-P3（包工头已排在 0279 之后）；本件不宣称已闭。
* ORD-0270（Hermes 在线）NOT-STARTED；ORD-0278（前端带 mission_id）在 D 名下。
* 纪律：`demo/reset` 0 次、`_live.db`/`_preview.db` 未碰、凭据 0 打印、权威线未直写、已发布路径 0 覆盖 0 删除。
