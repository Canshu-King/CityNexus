### SESSION=494abfd7 · **`P7_RESOLVER_INTEGRATED` 我逐条量了：现在是 `false`** ⇒ **不唤醒 Harness 与 P1–P4**（唤醒条件正是我 01:4x 才钉死的七条）@01:5x

`STATUS: P7-GATE-EVALUATED-BY-ME | 树 权威 tip `bfdeb1f`（`git grep`，只读）| 每条给"我搜了什么/读到什么"，负结论一律附清单 |`

| # | 仲裁钉的条件 | 我的实测 | 判定 |
|---|---|---|---|
| 1 | 未预录原文走**正常 application path** | 生产码里没有任何 provider 调用点（见 #2）| **FAIL** |
| 2 | **C 确实消费 B 的 typed result** | `git grep "provider_identity\|PhotonIdentityProvider\|ProviderResolution" HEAD -- backend/app \| grep -v app/integrations/discovery` ⇒ **0 命中** | **FAIL（关键缺口）** |
| 3 | exact raw 与 normalized query **分栏** | `db/models.py:1180 pending_destination_label` 独立列存在；`:1188` 另有"是原文还是 legacy 幸存"标记 | **PASS** |
| 4 | MATCH 写入**服务端所有的真 canonical** | 依赖 #2；当前无 MATCH 通路 ⇒ 无法发生 | **NOT-YET-REACHABLE** |
| 5 | 未解析三类 `canonical=null` | 我 01:2x 在 `f2708dd` 上 targeted 复跑 **19/19**（含 `g19a/g19b/g19c` 三条退出） | **PASS** |
| 6 | 作业可持久化 / 重放幂等 | 本轮未测（等 #2 通了才有重放对象） | **NOT-MEASURED** |
| 7 | `pending/raw` key 不冒充产品身份 | 同 #5 那批门（`g19b` 正是这条），退出即通过 | **PASS** |

⇒ **结论：条件 2 是唯一的硬缺口，且它是那条"跑了就解锁"的前提。所以：**
- `P7_RESOLVER_INTEGRATED = false`，**我不叫 Harness、不叫 HJ-P1/P2/P3/P4**（这正是仲裁 01:08 ② 要防的：把机械触发器装在错误层——B 一拿到 MATCH 就叫醒真人组，而 C 还没接上，等于让四个人对着没接线的产品做走查）；
- C 的 ORD-0167 目前交付的是**身份/持久化半段**（列 + 回填标记 + 三类 null），**不含 provider 接线**；`ORD-0191` 仍 OPEN，第一件要做的事就是把 #2 变成 0 命中之外的现实。
- 我也因此**不采信**"端到端 11 项收据"作为链通的证据（那只能是 fixture 重放层，见下条待核）。

**待我下一轮核的一件事**：C 交付块写"单元 15 门 + 5/5 突变 + 端到端 11 项收据"。#2 既然为 0 命中，那 11 项**必然**不是真 provider 闭环 ⇒ 我会去读它那份 receipt 的 `evidence`/`stage` 字段，按"是 replay 还是 live"如实标注；**在核清之前我不会在晨报里把它写成 E2E 已过**。

status: P7 七条逐条实测（1/2 FAIL、4/6 尚不可达或未测、3/5/7 PASS）；确认不唤醒 Harness 与真人组；ORD-0191 保持 OPEN 并把"消费 B 的 typed result"钉为唯一硬缺口；C 的 11 项 E2E 收据待我核其性质
