# ORD-0272 · nodeid 坐标更正（包工头 00:0x 那条坐标缺陷）

lane F `8ccd71d8` · 2026-09-25T01:45:48+08:00

## 你说的那 4 条，我认

`evidence/ord0272-reverify/*` 与 `evidence/ord0272-q22-corrected/*` 里，八臂载体表共 21 条 nodeid，
其中 **4 条的根是 `backend/`，而同一件里 `run_shape` 记录的 cwd 是 `<导出树>/backend`** ⇒ 按 nodeid
复收会拿到 **0 条**，且**不报错**（`no tests collected`）。这不是格式洁癖：verifier 复收时空集会被
当成"这一臂没人替它说话"。

| 臂 | 从（错） | 到（对） |
|---|---|---|
| `K2_two_identities_merged_into_one` | `backend/tests/test_qoder_ord0272_continuation.py::test_G3_second_device_with_no_client_header_still_gets_the_same_answer` | `tests/test_qoder_ord0272_continuation.py::test_G3_second_device_with_no_client_header_still_gets_the_same_answer` |
| `K3_mission_ownership_door_removed` | `backend/tests/test_qoder_ord0272_continuation.py::test_G8_a_mission_that_is_not_this_journeys_is_not_an_identity` | `tests/test_qoder_ord0272_continuation.py::test_G8_a_mission_that_is_not_this_journeys_is_not_an_identity` |
| `K4_link_event_stops_naming_the_plans` | `backend/tests/test_qoder_ord0272_continuation.py::test_G7_the_feed_projection_names_the_mission_and_the_plans_it_produced` | `tests/test_qoder_ord0272_continuation.py::test_G7_the_feed_projection_names_the_mission_and_the_plans_it_produced` |
| `K6_unowned_path_laundered_into_a_bare_500` | `backend/tests/test_qoder_ord0272_continuation.py::test_G6_no_second_failure_vocabulary_is_introduced` | `tests/test_qoder_ord0272_continuation.py::test_G6_no_second_failure_vocabulary_is_introduced` |

## 不止那 4 条：我用同一把尺全量扫

`nodeid_scan.json`：受影响的是 **4 件已发布件、共 29 条** —— 三份 reverify 读数各 4 条，
加上 `day1_receipt.json` 的 **17 条**（八格 `cells[*].nodeid` + `judgments[*].carriers` + 那枚回归载体）。
后 17 条你没点，但同一口径下就是同一个错。

## 缺陷的两层根因（第二层才是真问题）

1. **写错**：`o272_reverify.py` 的 `ARM_CARRIERS` 里四条用了仓库根相对常量（`GATE_FILE`），
   其余用了 backend 相对常量（`GATE_TARGET`）—— 同一张表两套根。
2. **判松**：可收集判定原本是 `tail in pool_tails`（只比 `::` 后面的格名），所以那 4 条错根被读成
   `collect=True`。**宽松的判定等于没有判定**：它恰恰放过了唯一会伤到 verifier 的那类错。

## 改法（r2 仪器 + 新文件名，旧件一律不覆盖不删）

* 四条根改对；`day1` 生成器也改成与自身 `run_shape` 一致的 `tests/…`，并**另存一个**
  `nodeid_from_repo_root` 字段 + 标明它只在 cwd=仓库根时可用（实测见下）。
* 收集判定改成**整条 nodeid 相等**，并给 `mismatch_kind`：`ROOT-MISMATCH(cell 在树里存在，路径根不对)`
  / `CELL-ABSENT`。
* 自测加了一枚**反向探针**：故意写一条 `backend/…::x`，严格的整条判定必须判它不匹配 —— 现在自测输出
  里多一行 `[selftest] 错根探针（backend/…::x 必被判不匹配）-> BITES`，`SELFTEST_PASS` 依赖它。

## 两种形式的实测（同一棵 corrected 导出树，逐条命令可复跑）

```text
B) cwd=<树>/backend  python -m pytest --collect-only -q tests/…::test_G1…      -> collected=1
C) cwd=<树>/backend  python -m pytest --collect-only -q backend/tests/…::test_G1… -> no tests collected
A) cwd=<树>（仓库根） python -m pytest --collect-only -q backend/tests/…::test_G1… -> collected=1
```

⇒ `backend/tests/…` 这种写法**本身不是错的**，错的是它与我所记录形状（cwd=backend）不一致。
所以 r2 的每份读数都写"nodeid + 它自己的 cwd/cmd"，让按号复收的人拿到 1 条而不是静默 0 条。

## 21 条逐条读数（原文行在 collect_proof_21_carriers.txt）

```text
collected=1 的条数：21/21
strict whole-nodeid 匹配（r2 判定）：21/21
verdict：GATE-GREEN（八格 8/8、警报 无）
```

## 本组新文件（未覆盖任何已发布件）

```text
evidence/ord0272-nodeid-correction/NODEID_CORRECTION.md                     ← 本件
evidence/ord0272-nodeid-correction/o272_reverify_r2.py                      ← 修好的仪器（根改对 + 判定改严 + 反向探针）
evidence/ord0272-nodeid-correction/gate_reading_corrected_tree_r2.json      ← 21/21 整条严格可收集的那份读数
evidence/ord0272-nodeid-correction/collect_proof_21_carriers.txt            ← 21 条逐条收集原文 + 两种形式双向证明
evidence/ord0272-nodeid-correction/nodeid_scan.json                         ← 全量扫描：旧 29 条 → r2 0 条
evidence/ord0272-nodeid-correction/day1_receipt_r2.json                     ← 门收据 r2（17 条根改对 + 双形式字段）
```
