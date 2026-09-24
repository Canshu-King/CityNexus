### ✅ aad2d1f2 (SESSION=aad2d1f2) P3 · ORD-0262-NARROW verifier **第二段：N1/N2 运行时读数到手**（一次性库 + 一次性端口，真杀真删）@2026-09-24T09:2x+08

接着第一段（那段只到源码级）。**运行时这一半现在跑出来了**，所以第一段里我留的那句"唯一没能排除的（同步路由在线程池里抛出的 `OperationalError` 是否真被全局处理器接住）"**就地关闭**。

**现场（全部一次性，可复现）**
- 被测树 = `3093eea773c79fa00744fe72d1f2c43b4d0bd75e`（tree `5ae9f8959b059d04e5a41c53f0b6fa11470b19d0`，父 `30092dcb664c`），按 40 位 sha 从 GitHub 取的 tarball，落在 `_hjp3_narrow_0924/snap_3093eea/…`。**没碰 F 的 worktree，没碰权威线 `c79e2b4`，产品字节 0 改动。**
- 一次性后端 = `:8491`（解释器 `D:/moodle/CityNexus/.venv/Scripts/python.exe`，`uvicorn 0.52.4`；第一段卡住的"那个 uv 3.12.14 解释器没有 uvicorn"已换掉解决）。
- 一次性库 = `D:/moodle/_hjp3_narrow_0924/one_time_n1.db`：候选树里 `grep -rln "create_all|alembic upgrade|init_db" backend/app backend/tools ../tools` = **0 命中**（第一段那条阻塞），所以我**只复制结构、不带任何数据行**：从我自己 lane 库的 `sqlite_master` 取 `type IN ('table','index','trigger')` 的 CREATE 语句逐条重放 ⇒ 实测 **92 条语句 / 55 张表 / 新库 `journeys` 行数 = 0**。
- 只 seed 我自己那 1 traveler + 1 journey（`POST /travelers` 201、`POST /journeys` 201）。**全程 0 次读写 `_live.db`/`_preview.db`/任何 lane 数据行；0 次 `demo/reset`；凭据 0 打印。**
- 制造冲突 = 第二个 sqlite3 连接 `BEGIN IMMEDIATE` + 一条 `UPDATE journeys SET title=title`，**不提交**，持锁跑完 R3–R5，然后 `ROLLBACK`。

**六轮读数（每轮都带 http / content-type / 字节 / 墙钟秒）**

| 轮 | 结果 | 屏外事实 |
|---|---|---|
| R2 控制轮（**无人持锁**） | `200 / application/json / 5,163 B / 0.34 s` | 真出方案（`optimizer=ORTOOLS_MODE_AWARE_CP_SAT`、`top_k[].status=CANDIDATE`）⇒ 下面那几枚 503 **不是无条件** |
| R3 generation 站点（持锁） | **`503 / application/json / 255 B / 33.34 s`** | `{"error":{"code":"GENERATION_STORE_BUSY","message":"Another generation is writing right now; this one was not recorded. Try again.","message_key":"generation.store_busy","trace_id":"d33bc2e5-…","details":{"retry_after_ms":1000}}}` |
| R4 hydration 站点（持锁） | **`503 / application/json / 252 B / 0.29 s`** | 同信封，`code=HYDRATION_STORE_BUSY`、`message_key=hydration.store_busy`、`retry_after_ms=1000` |
| **R5 建 mission 那一路（持锁）** | **`503 / application/json / 332 B / 8.25 s`** | `code=GENERATION_STORE_BUSY` + **`reason_code":"sqlite_write_lock_busy"`** + `details.contention="sqlite_write_lock_busy"` ⇒ **从 `create_mission(` 逃出来的 `OperationalError` 确实被 `main.py:684` 的全局处理器接住并具名了，没有落框架那一面** |
| R6 释放锁之后 | `200 / application/json / 5,163 B / 0.14 s` | 与 R2 同字节数 ⇒ 冲突消失后同一发恢复正常 |

**N1 判定（运行时）= 成立**：三枚具名 503 全部是 `application/json`、全部走产品自己的 `error()` 信封（`code/message/message_key/trace_id/details`，R5 另带 `reason_code`），**没有一处手拼 JSON**。
**N2 判定（运行时分布）= 成立**：generation 异步门、hydration 门、以及 `agent/commands` 里 `create_mission(` 那一路，**三族都从同一个具名出口出去**；本轮**没有一枚**落回框架的 `text/plain` 21 B 面（旧行为正是那一面）。名单外仍会原样再抛（`main.py:684-690` 的 `if reason is None: raise exc`），这条第一段已核，属设计意图。
**F 那一格（`retry_after_ms` 收口）= 运行时确认**：三枚 503 的 `retry_after_ms` 全是 **1000**，即阶梯下限，**不是**旧的硬编码 500。

**两条我不藏的限制**
1. **同一件忙，两种时长都是真的**：R3 等了 33.34 s（走完 `busy_timeout=30000` 才判忙）、R4 只 0.29 s、R5 8.25 s（锁已被前一轮的写占着，SQLite 立刻回 BUSY）。所以**我不把等待时长当判据**，只当读数——牙齿放在"必须 503 + 必须具名 + 必须在信封里"。
2. R3/R4/R5 的 503 是**同一条持锁事务**造成的，我没有为每个站点单独制造一次"只有它自己忙"的干净冲突；站点归属由"哪一发请求打哪条路"决定，不是由锁的种类决定。要按站点分级的话，需要三把独立的锁，我这一轮没做。

**N3 / N4 仍然 NOT-RUN**（不拿运行时 N1/N2 冒充）：那两问要的是**浏览器里那一屏**——`.plan-ai-reason` 的文字必须 `==` 服务器 `message`、屏上不许出现客户端自造的 `HTTP 500` 顶掉「服务器给出的原因」标签、有 mission 行时不得说"没记录"。配方我已经铺好（同一个一次性后端 + 一枚指向它的 face + 持锁窗口内点「开始规划」），但用户 10:00 要开工、机器今晨蓝屏过，我不在窗口里开一枚跑不完的大改。**这一格状态：N1/N2 = 运行时已证；N3/N4 = NOT-RUN，挂我名下。**

**收尾（真做实测，不是脚本自称）**：`port_still_listening=False`（`:8491` 上 netstat 0 行）、`db_exists_after_delete=False`（`one_time_n1.db*` 全部不存在）、uvicorn 进程已终止。脚本 `run_n1_n2_rig.py` 与逐轮原始读数 `n1_n2_runtime.json` 一起发布，谁都能在同一枚 sha 上重放。
