仲裁: SESSION=494abfd7（Commander）— **我把你刚接受的基线 16 又更正了一次：稳定核 = 14**（我第三次跑就掉了），并回报一条你的 policy 缺口

## ① 基线更正（这次是**我自己打自己**：第三次运行推翻了我"两次一致所以稳定"的断言）
同一 SHA `8ee64ae`、同一棵 `git archive` 导出树，全量三次：
```
run1 16 failed / 1069 / 15    run2 16 failed / 1070 / 15    run3 **14** failed / 1072 / 15
三次交集（稳定核）= 14        并集 = 16        轮换成员 = 2
```
⇒ 与 lane F 在同一 SHA 上独立算出的 **14 一致**（它是 17/14 两遍取交）。
⇒ 正式引用句（我已入账本，全线不再用任何单值）：
```
BASELINE@8ee64ae = 稳定核 14（三次 ∩；与 lane F 独立 ∩ 相同）· as-is 区间 14–17 · 并集 16
swimmers（具名，禁止被"红变少"叙事吸收）：
  catalog_hydration::a_job_stopped_before_its_worker_starts_still_closes_itself
  catalog_hydration::nothing_leaves_the_process_while_the_deterministic_plane_answers
  （同族第三个 abandon_reports_a_request_not_a_death 亦在轮换集内）
另有 g3 = 上下文依赖红：TARGETED:RED / FULLSUITE:GREEN，两边都不得外推
稳定核 14 的分布：discovery_truth 4 / capability_from_store 3 / provider_truth 2 / matrix_truth 2 / provider_independence 1 / lock_duration 1 / gates 1
```
⇒ **我的方法错在哪**：只跑两次就宣布"逐行一致 ⇒ 稳定"。**两次一致不构成稳定性证据。**
⇒ 请你收进 `test_execution_truth_policy.md`（和"没收集就没分母"同族，一句话就够）：
   **"A baseline is an intersection over ≥3 runs plus named residue; two identical runs are luck, not stability."**
   并要求任何"红集合变小"的宣称必须同时给**区间 + 轮换成员名**——否则顺序一漂，大家都以为产品在变好。

## ② lane F 这轮值得记一功（也是你 ③ 那类条款的又一次生效）
它没有把我的 16 当权威去对齐，而是写"**与你的 16/16 不一致，我如实并列**"，并把差异定位到**具体成员**；
同时把它自己新加的契约条目 `context-dependent-red-needs-both-lines` 提了出来（上下文依赖的红必须两行并排 + 两种上下文各一条断言）。
⇒ 这条我认为应该进你那份 policy，跟**交叉突变**并列：**"看起来独立"和"看起来稳定"都必须有可复放的证明，不能用一次观察代替。**
⇒ 另外它把我那个账本锚点守卫**包装调用**（`GUARD = …/live_checks/ledger_anchor_guard.py`，写前 `require_healthy()`、写后 `verify_after()`），没有另写一份——这是我希望的形状，避免两个实现各修一半。

## ③ 签收状态（都带我的独立核对，不是转述）
- **ORD-0170（F）= ACCEPTED**（新 tip 重测 + 双上下文 + 守卫接入）。
- **ORD-0173 / H0–H10 表 = ACCEPTED-PARTIAL**：一行表已交、H8b 与旧的 vacuous H7 都没沿用 PASS；**8 个证据文件我逐个 stat，字节数与自报完全一致**（135,012 / 11,225 / 84,238 / 2,791 / 1,932 / 7,353 / 595 B）。
  ⇒ **但它的 `EVIDENCE_MANIFEST.json` 过期**：`generated=2026-09-21T23:06:42`（早于本轮证据约 1.5 小时），180 条里查不到本轮引用文件，抽查在列文件的 sha256 也与磁盘不符 ⇒ 我记 **ORD-0190**：先定稿再出清单 + 把"清单覆盖率与哈希一致"做成可复放检查 + 历史原件继续不覆盖（它这点一直做对了）。
  ⇒ 这正是你对 R3 包说过的同一条规则的**第二次发生**，所以我把它写成单而不是口头提醒。

## ④ 现场
主线：ORD-0167 已按你的"乙"切开并派（ORD-0188 provider 半段 → B；产品半段留 C），B/C 都已收到，防撞条款我加了"上游停在接口，C 不得伸进 `integrations/discovery/**` 顺手修"。
预览：前端 `index-BkEHAbFb.js`、后端未动、`demo/reset → 403`、匿名 AI 调用 401；用户 journeys=3 / plan_versions=19 / travelers=3 未变；账本镜像 `07c751109f4a` 字节级相等（1,993,274 B / 149 条真条目）。

竭尽所能的替qoder铺路
