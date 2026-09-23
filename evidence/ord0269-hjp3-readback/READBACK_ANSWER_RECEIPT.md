### 🔎 aad2d1f2 (SESSION=aad2d1f2) P3 · 把 0269 §①(i) 那枚假设量了一遍：**"本来就能被读回"只对一半** @2026-09-24T01:4x+08

**问题（照包工头 01:1x §①(i) 原话）**：「那三件事本来就在库里、**本来就能被读回**（`agent-feed`/`missions` 那条路）」。这是机制主张，所以我没有讨论它，我把它量了：从服务自己的 `openapi.json` 取路由清单（不猜名字），逐条调用，再看载荷里到底有没有那三件事。

**读数（4 轮全对得上；库 = 我的 `_lane_aad2d1f2_livecopy.sqlite3`，后端 `:8424`）**

| 轮 | mission 库内状态 | run 库内状态 | 该轮写了几行 plan | feed 里有 `plans.generated` 吗 |
|---|---|---|---|---|
| A（旧代，离开） | `COMPLETED` | `COMPLETED` | **0** | 无 |
| B（不离开） | `COMPLETED` | `COMPLETED` | 3 | 有（同一秒） |
| C（不离开） | `COMPLETED` | `COMPLETED` | 3 | 有（同一秒） |
| 3（新代，离开） | **`DEGRADED`** | **`FAILED_EXTERNAL`** | **0** | 无 |

**结论：一半对。**
- **对的那半**：确实有 **4 条 GET 能点出那两枚"零方案"的 mission id** —— `~/agent-feed`、`~/history`、`~/observability/traces`、`~/reflect`；每轮都有 `agent.run.completed` 事件。所以"跑过一次"这件事今天读得到。
- **不对的那半，三处，逐条可核**：
  1. **`missions` 那条路不存在**：139 条路由里唯一含 `mission` 的是 `PUT /api/v1/journeys/{journey_id}/guardian/mission`（**写**，不是读）⇒ **没有任何 GET 能列出一趟行程的 missions**。
  2. **mission 的终态读不到**：`DEGRADED` 在 **39 条 journey 级 GET 里出现 0 次**；`FAILED_EXTERNAL` 只在 `history` 与 `reflect` 两条里各 1 次。⇒ 库里那句"这一轮是降级收场"，**面上一处都没有**。
  3. **plans 与 mission 之间没有键**：`plans.generated` 事件 4/4 轮都**不写 mission id**，`plan_versions` 表也没有 `mission_id` 列（我上一轮量过列名）。⇒ 今天想判"跑完了但没产出方案"，**只能拿时间戳对齐**（我验了：4 轮里"同一秒有 `plans.generated`"与"同一秒有 plan 行"**完全一致**，所以这个土办法现在能用）。但它在 **0262 那个重复提交/并发形状下不安全**——两轮落在同一秒就分不开，而这正是 0262 研究的形状。
- **附带一枚会咬人的**：`GET ~/agent-feed` **不带 limit 时只回 100 条事件、并且不含最新那枚 abort 轮**（`17aec167`）；带 `?limit=200` 才回 187 条并含它。现网客户端启动时确实带 `limit=200`（访问日志里能看到），所以**今天不咬人**，但任何新读路沿用默认分页就会漏。

**给 D 的一句（只报可行性，不设计）**：§①(ii) 选的"揭示 + 一次可续"**不需要新增后端原子操作**就有原料——原料是 `agent.run.completed` 那 4 条事件。真正缺的是**一个字段**：让 `plans.generated`（或 `plan_versions` 行）带上 `mission_id`；不补它，"揭示"就只能靠时间戳对齐，而那个对齐在并发下不成立。这比"新增原子"便宜，也不碰 0253/0262 的文件面。

**我自己撤回一条**：我第一版探针把 `agent-feed` 读成"0 events / 空"，那是**我的键名错**（载荷真实键是 `events`，我找了 `items/entries/feed`）。**撤回**：它不空，`?limit=200` 下是 187 条。两版读数我都留着，别拿后一版覆盖前一版的形状。

**纪律**：本轮全部是 GET（其中 `~/experience` 是产品里"读时会写"的那条老路，我照实说我又调了一次，调后我的库行数与我上一块收据里的一致：missions 71 / runs 70 / plans 139 未变）；**0 次 `demo/reset`、0 次写用户库、0 次改产品字节、凭据 0 打印**；端口只用了自己的 `:8424`；关页 0。
