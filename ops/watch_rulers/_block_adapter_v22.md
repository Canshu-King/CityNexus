## commander 适配器 v2-2 @2026-09-22T22:49+08 —— 按 F 的 v2-2 处方补了那一行（corroborate_node_outcome），并用它自己的共享模块验证了正反两向；仲裁两笔产品决定落账

### ① F 的"skip ⇒ exit 0 ⇒ GREEN"假绿通道（我那一侧的补法）

F 20:03 的话：**"你的 `gate_streak.py` 现在只调 `node_outcome_from_exit`，不调佐证层 ⇒ 你那侧仍会把『整条 skip』报成 GREEN"**，并给了确切的一行。我照抄并用**它修正后的共享模块**（`801e90b` 导出树）自测：

```text
run1: raw GREEN -> final GREEN | corroboration=退出码与摘要计数一致 | counts={passed:1}
run2: raw GREEN -> final GREEN | 同上
⇒ 正向对照成立（F 特意钉的：真通过不能误拒）
⇒ skip 的反例由 F 的 test_9b 用真 skip 子进程钉住（skipped 批次只会得 HARNESS_INVALID_target_verdict_not_scoped，永不 STREAK_MET）
收据新增：raw_node_outcome / node_outcome / outcome_corroboration / pytest_counts 四格
```
**适配器 v2-2 已发布**：`live_checks/gate_streak.py` **10,233 B**，blob **`4931d6526eb0a3ea`**（BYTE-LEVEL MATCH）。

### ② 仲裁两笔产品决定落账（`5778314066`）

**写入端校验：要，分两层**——所有写入先要求 `rule_code ∈ canonical vocabulary`；若 `kind=HARD` 还必须 `∈ HARD_EXECUTABLE_SET`，否则**写入前 422 fail-closed、不落库**；SOFT 不因"不属于 hard-executable"被拒。四格边界照录进 ORD-0219 的 amend（`UNKNOWN_RULE_CODE` / `HARD_RULE_NOT_EXECUTABLE` 必须分开、SOFT 按 soft 契约、hard-executable 落库后由 feasibility 按证据求值）。
⇒ **C 的第一步（STROLLER/LARGE_LUGGAGE 的 severity）不受影响**；写入端校验与四个 SOFT 码的可行性层工作**不要混成一笔**。

**HARNESS 22:31 的发现我记进账本并升级了范围问题**：`seed_demo` 16 个地点**无障碍证据 0/16** ⇒ 就算门补上也没证据可读。"演示库要不要补无障碍证据生产者"等产品拍板。

### ③ 工作尖推进

D 在 20:55/20:56 交了 **`fbbc21d`**（ORD-0222 ② follow-up：创建成功后继续跟随那条播报）与 **`bce7269`**（把后续绑定到 served bundle generation）。我还没验收（运行层归车道/GPT），只确认 tip 前进。

### ④ 现场

working tip `bce7269`（20:56）；链三条端口在听；镜像 `2ad4ac8a233a7bc2`（SSL 又抖一次，重试后字节级证明通过——与 19:1x 那次 401 同族，**网络瞬断不当作凭据问题**）；`P7=false`；reference tip `c0d7e3d`；P0 未动（用户库 3/3/19/1/1）；那把 key 仍未轮换。
