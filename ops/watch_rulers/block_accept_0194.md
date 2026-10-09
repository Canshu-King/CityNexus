### SESSION=494abfd7 · ORD-0194 = **REPRODUCED**（今晚第一个由我复跑升档的项）；基线集合与 lane F **正式合并成一份**：交集 14、区间 14–17 @01:0x

`STATUS: ACCEPTED-REPRODUCED-BY-COMMANDER | 我量的树 `git archive 2176774` → `v_2176774`（权威树 0 写）| 3.12.14、AI off、凭据清空 | 全部 targeted（按 P5，不跑全量）|`

#### ① 我复跑的结果（车道自报 → 我复核升档）
```
--collect-only -q                       → 1163 tests collected in 4.56 s（车道报 1163 / 1.83 s，同数）
tests/test_qoder_anywhere_collection_gate.py → 9 passed in 2.39 s（车道报 9 passed）
其中新立的两条：
  test_7（负断言必须先在真键清单上算"缺什么"）  → passed
  test_8（守卫必须单实现：包装里出现 HEADING/board_start/lines.insert ⇒ 当场红）→ passed
```
⇒ **ORD-0194 = ACCEPTED，并在我这边标 `REPRODUCED`。**
⇒ 车道这一轮**主动只标 SELF_REPORTED 并写着"我不替任何一项写 REPRODUCED，那是你的标记"**——这是晨报三档标注能被执行的样子，不是姿态。我已把它的 P5/基线集合化/守卫单实现三项从 `SELF_REPORTED` 升为 `REPRODUCED`；**交叉突变仪器（`14a5b64`）仍未复跑，保持 SELF_REPORTED**，明早我按同样方法升或不升。

#### ② 基线正式合并为"一份集合"（我的三次 + 它的四次，同一 SHA `8ee64ae`）
| 谁 | as-is（无边界）读数 | 两遍交集 |
|---|---|---|
| 我（3 次全量） | 16 / 16 / **14** | **14** |
| lane F（2 次全量） | 17 / **14** | **14** |
⇒ **两个独立来源的交集相同 = 14**，合并区间 **14 – 17**。⇒ 你我之前"16 vs 17"的冲突就此定性：**不是谁错，是单值这个说法本身错**（车道那句话我原样引用："真值是这个集合"）。
⇒ 全线引用这一句：
```
BASELINE@8ee64ae = 交集 14（Commander 3 次 ∩ 与 lane F 2 次 ∩ 相同）· 区间 14–17
具名轮换成员（只 3 个，全在 catalog_hydration 一族）：
  test_a_job_stopped_before_its_worker_starts_still_closes_itself
  test_abandon_reports_a_request_not_a_death
  test_nothing_leaves_the_process_while_the_deterministic_plane_answers
上下文依赖：g3 = TARGETED:RED / FULLSUITE:GREEN（两边都不得外推）
带边界稳定核 15（车道两遍；我这边一次未做，明早一次跑在最终候选上）
```
⇒ 契约侧已由车道把 `baseline-is-a-set-not-a-number`（含 worked example）、`p5-targeted-only-until-the-stable-candidate`、`ledger-guard-single-implementation`、`morning-report-labelling` 四条落进 `0.94-annex.17`（我核了纯增补回验的说法与门文件行为一致）。

#### ③ 顺带：`ledger-guard-single-implementation` 这条门正是我今晚担心的东西
我上一轮怕的是"两份实现各修一半"（我修脚本、它包装），现在**这件事由门守着**：包装里若出现锚点判定逻辑就红。⇒ 我这边的动作：`ledger_anchor_guard.py` 保持**唯一实现**，我的巡检脚本只调用不复制。

status: ORD-0194 ACCEPTED 且升档 REPRODUCED（1163 collected、9 passed、test_7/test_8 双绿，全部 targeted）；基线与 lane F 合并为交集 14 / 区间 14–17；交叉突变仪器仍 SELF_REPORTED 待我复跑
