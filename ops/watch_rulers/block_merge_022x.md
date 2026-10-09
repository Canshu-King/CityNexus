### SESSION=494abfd7 · 两件事同时落地：**B 的 typed outcomes 合进权威树（`520cf29`）我复跑 49/49 无破损**；canary 提交是真的（我在其导出上跑 **53/53**），但它报的"**第一次真 HYDRATABLE**"运行时链**我复现不了——canary 已经停了** @02:2x

`STATUS: MERGE-VERIFIED + RUNTIME-CLAIM-HELD | 全部在 `git archive <SHA>` 导出树跑（权威树 0 写），3.12.14、AI off、凭据清空 | targeted only（P5）|`

#### ① 合并没有打断东西（这条最容易被跳过）
- tip 从 `306f153` → **`520cf29`**（`Merge branch 'agent/b-ord188-20260922'`）。
- 我在 `git archive 520cf29` 上复跑三套：`provider_identity` + `pending_destination_identity` + `provider_identity_leg` → **49 passed / 0 failed**。
⇒ 合的是**新增 typed provider 结果层**，产品消费面尚未接线（ORD-0197 未完），所以 **P7 不变**：`520cf29 ≠ P7=true`。

#### ② canary 的提交是真的，测试是真的，**运行时那一格不是**
- `git cat-file -t`：`53a21fc` / `e3f416f` / `08786c1` / `44e4ea7` **全是 commit** ⇒ 坐标真实存在、可 checkout（这正是我今夜反复要的东西）。
- 我在 `git archive 53a21fc` 上复跑四套（含 `capability_from_store`）→ **53 passed / 0 failed**，`g19a/g19b/g19c` 三绿 ⇒ **测试面 REPRODUCED**。
- 但车道报的那条**可见链**（`?query=贡山县` → `OSM:R:2729765` / `resolution=provider` / **HYDRATABLE** → 202 durable → 6 live 行 → planner 422 → 逐边收据 → `MOBILITY_EVIDENCE_NOT_HARD_ELIGIBLE`）：我 02:25 去连 canary `:8596` → **connection refused（进程已停）** ⇒ **运行时那一格我只能记 `SELF_REPORTED`**，写进晨报时与测试面**分两格**。
⇒ 已向车道要：canary 启动命令 + 当时那份 used-edge 收据路径；它一起来我就自己 GET 一遍，成立才升 REPRODUCED。

#### ③ 为什么这一格值得单独抠（不嫌麻烦）
"贡山第一次被真 provider 命名成 canonical 并给出 HYDRATABLE"如果成立，是**今夜第一个从 provider contract 走到产品语义的时刻**，也是仲裁 A 里程碑的最强证据；
正因为它最有新闻价值，**它最不能被"跑过 39 个测试"代替**——测试证的是代码形状，链证的是运行时真的问过、真的拿到、真的没造 SELECTABLE。
⇒ 所以：**代码/测试升档，运行时不升档**；唤醒条件继续锁死（P7=false，Harness 与 P1–P4 不叫）。

#### ④ P0 与隔离
- 车道自证：`:8596` loopback、`sqlite3.backup` 只读拷库、`_live.db` **零写连接**、主预览仍 `53fe8e8`；
- 我这一侧独立复核（只读）：主预览 `demo/reset → 403 PREVIEW_GUARDED`、匿名隧道 `401`、用户 `journeys=3 / plan_versions=19 / travelers=3` + places 北京8/演示8 **未变**；
- canary 已停 ⇒ 当前不存在"用户可达 canary"的风险面；重启时我会再量一次端口与库路径，**并确认它不挂用户的 preview URL/隧道/SW scope**。

status: 合并验证（49/49 无破损、P7 不变）；canary 提交与测试面验真（53/53，g19a/b/c 三绿）；**运行时"第一次真 HYDRATABLE"因 canary 停机仍未复现，保持 SELF_REPORTED**；P0 全部独立复核未变
