### SESSION=494abfd7 · **我更正自己：共享基线不是 16，是"稳定核 14 + 具名轮换成员"**（我第三次跑就掉到 14；与 lane F 独立算出的 14 对上了）+ ORD-0170 签收 + ORD-0173 签收但**清单已过期** @00:5x

`STATUS: MY-BASELINE-CLAIM-CORRECTED-BY-A-THIRD-RUN | 同一 SHA `8ee64ae` 我共三次全量 + F 四次 | 树均为 `git archive 8ee64ae` 干净导出 | 解释器 3.12.14、AI off、凭据清空 |`

#### ① 我的 "16（两次逐行一致）" 是**运气**，第三次就变了
```
run1 16 failed / 1069 / 15    run2 16 failed / 1070 / 15    run3 14 failed / 1072 / 15
三次交集（稳定核）= 14        并集 = 16        轮换成员（swimmers）= 2
```
⇒ 与 lane F 在同一 SHA 上的 17/14（as-is）与 15/16（带边界）**并列后一致**：**它算出的稳定核也是 14。**
⇒ **共享基线正式改为**（请全线引用这一句，别再引用任何单值）：
```
BASELINE@8ee64ae = 稳定核 14（我三次 ∩ 与 lane F 独立 ∩ 相同）
  as-is 观测区间 14–17；并集 16
  swimmers（具名，随运行顺序/并发轮换，不得被"变小"叙事吸收）：
    catalog_hydration::test_a_job_stopped_before_its_worker_starts_still_closes_itself
    catalog_hydration::test_nothing_leaves_the_process_while_the_deterministic_plane_answers
    （同族第三个 abandon_reports_a_request_not_a_death 亦在轮换集内）
  另有 g3 = 上下文依赖红（TARGETED:RED / FULLSUITE:GREEN），两边都不得外推
```
⇒ 稳定核 14 的分布：`discovery_truth 4 / capability_from_store 3 / provider_truth 2 / matrix_truth 2 / provider_independence 1 / lock_duration 1 / gates 1`。
⇒ **我自己这条错是怎么来的**：只跑两次就宣布"逐行一致、故稳定"。⇒ 已改口径：**"两次一致"不构成稳定性证据；核必须是 ≥3 次交集**，且报数必须同时给区间与轮换成员。

#### ② ORD-0170（F 在新 tip 重测）= **ACCEPTED**
除了上面的 14，我还认它两点做法：
- **它没有把我的数字当权威去对齐**，而是写"与你的 16/16 不一致，我如实并列"，并把差异**定位到具体成员**；
- 契约新增 `context-dependent-red-needs-both-lines`：上下文依赖的红必须两行并排 + **两种上下文各一条断言**。
⇒ 这条我提给仲裁入 policy（与它已收的"交叉突变"同族：都是"看起来独立/看起来稳定"要有可复放的证明）。
⇒ F 另接入我的账本锚点守卫（`_qoder_f_run/_qoder_ledger_guard.py`）：**它是包装调用我的脚本**（`GUARD = …/live_checks/ledger_anchor_guard.py`，写前 `require_healthy()` 非 0 即停写、写后 `verify_after()`），**没有另写一份**——这是我要的形状。

#### ③ ORD-0173 / H0–H10 表 = **签收（一处硬缺陷另立单）**
回执一行：`H0–H7 PASS | H8a PASS | H8b NOT_RUN | H9 PASS | H10a PASS | H10b 读单数 proposal 可推进 + 剩 solver_mode(ORD-0176)`，
且**没有沿用被降级前的 PASS**（H7 旧的 vacuous PASS 自己改记 NOT_RUN）。我逐条对了磁盘：**8 个证据文件全部存在且字节数与自报完全一致**
（`H4_readonly_truth.json 135,012 B`、`…_run1.json 11,225 B`、`H6e_H7_accept_and_idempotency.json 84,238 B`、`H6e_H7_rerun_fresh_db.json 2,791 B`、`H5_rescore.py 1,932 B`、`h6e_h7_accept_rerun.py 7,353 B`、`H8_boundary_probe.json 595 B`）。
⇒ **但它的清单过期了**：`EVIDENCE_MANIFEST.json` 的 `generated = 2026-09-21T23:06:42+0800`（比这批新证据早约 1.5 小时），
   180 条里**根本没有** `H4_readonly_truth.json` 等本轮文件；随机抽查一个在列文件的 sha256 也与磁盘不符。
⇒ 所以"sha256 前 12 位见 manifest"这句**现在不成立**——文件是真的，索引是旧的。
⇒ 已记 **ORD-0190**：**先定稿证据、后生成 manifest**（与仲裁今晚对 R3 包说的那条同规则），并要求它把"manifest 覆盖率"做成一次可复放检查（每个引用文件必须能在 manifest 里查到且 hash 与磁盘一致）。

status: 基线更正为稳定核 14（三次交集）+ 区间 + 具名 swimmers；ORD-0170 签收；ORD-0173 签收但 manifest 过期另立 ORD-0190
evidence: `live_checks/red_8ee_r1|r2|r3.txt`、`red_8ee_stable.txt`（14）、三次 `fullsuite_8ee64ae_r*.txt` 尾行；8 个证据文件的 stat 结果；manifest `generated` 与缺失条目实测
