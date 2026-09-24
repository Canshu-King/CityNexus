### ✅ aad2d1f2 (SESSION=aad2d1f2) P3 · ORD-0262-NARROW verifier **第一段**：N1 / N2 我证到了源码级；**N3 / N4 没跑**，阻塞具名 @2026-09-24T09:0x+08

**我量的是哪一枚**：候选 `3093eea773c79fa00744fe72d1f2c43b4d0bd75e`（tree `5ae9f8959b059d04e5a41c53f0b6fa11470b19d0`，父 `30092dcb664c`，subject `test(ord0262): the busy-door assertion stops pinning the number it was meant to follow`）。
取树方式：**按那 40 位 sha** 向 GitHub 要 tarball（`codeload…/tar.gz/<sha>`，不取分支名，所以分支移动不能顶包），落到 `_hjp3_narrow_0924/snap_3093eea/`。**我没碰 F 的 worktree，也没碰权威线 `c79e2b4`。**
诚实交代一处没证成：我顺手 `git write-tree` 复算得 `31ebf0fe…` **不等于** `5ae9f895…`——原因是我把整包 `git add -A` 重算，`.gitignore`/mode 差异会改树形，**这不能说明包不对**；包的身份由"按 40 位 sha 请求 tarball + 提交对象里 tree 字段逐位相符"这两条支撑（与包工头逐件 blob 复算 10/10 一致）。

### N1 · 具名码是否真走 `error()` 信封 —— **成立（源码级，逐处可核）**

| 站点 | 位置 | 走的是什么 |
|---|---|---|
| 共用出口 | `backend/app/main.py:666-673` `_contention_response()` | `error("GENERATION_STORE_BUSY", …, status=503, details={"retry_after_ms": …, "contention": reason}, message_key="generation.store_busy", reason_code=reason)` |
| generation 站点 | `main.py:2997-3004`（`except GenerationStoreBusy`） | 同一个 `error(...)`，`message_key="generation.store_busy"` |
| hydration 站点 | `main.py:2939-2944`（`except HydrationStoreBusy`） | `error("HYDRATION_STORE_BUSY", …, status=503, details={"retry_after_ms": _hydration_busy_retry_after_ms()}, message_key="hydration.store_busy")` |
| 信封本体 | `main.py:452-466` `def error(...)` | 全产品唯一信封（docstring 自述 ORD-0055：`message_key` 由 `code` 派生，**永不**由 `message` 派生） |
| 同步那扇门 | `main.py:3097-3104`（另一处 `except GenerationStoreBusy`，`submit_operation` + `wait_for_operation` 那一路） | 与异步门**同一具名、同一措辞**：`error("GENERATION_STORE_BUSY", …, status=503, details={"retry_after_ms": _contention_retry_after_ms()}, message_key="generation.store_busy")`；注释自述"one condition, one wording, no endpoint-specific invention" |

⇒ **没有一处手拼 JSON**；四处都经由 `error()`。`grep -n "STORE_BUSY" backend/app --include=*.py` 的命中就是这 4 行（`667` 共用出口 / `2940` hydration / `3000` generation 异步 / `3099` generation 同步），我把命中行原样打出来了，不是"我找过没有"。
**顺带核到 F 那格收口的形状**：`main.py:643-662` 的 `_busy_retry_after_ms(ladder)` 用 `ladder(SimpleNamespace(status=QUEUED, queued_at=now))` **向操作自己的阶梯要数**，generation 走 `stay_generation_operations.retry_after_ms`、hydration 走 `catalog_hydration_operations.retry_after_ms`（`main.py:397/417` 两处 import 别名）⇒ 三处硬编码 `500` 已经不在代码里（`grep -rn "retry_after_ms" backend/app` 的 14 处命中里没有一处赋常数 500）。

### N2 · 三处 `create_mission(` + 两处 flush，**按分布判** —— **成立（源码级），但有一处我没能排除**

- 三处 `create_mission(` 实测在 `main.py:1211`、`main.py:1365`、`main.py:10992`（`copilot_message` 那一路，正是包工头点过"容易漏看的第三处"）。**三处都不在 `try/except OperationalError` 里**（`main.py` 里 `except OperationalError` 只有 **1** 处：`:6026`，是 twin 那条软跳过）。
- 那三处逃出来的 `OperationalError` 由**全局**处理器接：`main.py:684-690` `@app.exception_handler(OperationalError) busy_write_lock`：
  `reason = _contention_of(exc)`；**`if reason is None: raise exc`** ⇒ 名单外一律原样再抛、仍落框架那一面；命中才 `_contention_response(reason)`。
- 判据用的名单在 `main.py:625-627`：`CONTENTION_UNIQUE_ROWS = {"traveler_agent_policies.traveler_id"}`、`CONTENTION_LOCK_MARKERS = ("database is locked", "database is busy")`，注释自述"名单外保持 500，否则契约变成洗白机器"（与 `TEMPORAL_REJECTIONS` 同一条不洗白规则）。
⇒ **分布结论**：三处 mission 创建点 + 两处 flush 的锁冲突，今天都会从同一个出口出去，且**只有可具名的那两种**会被收进 503 信封；逃手的那一支（名单外）确实仍落框架面，**这是设计意图而不是漏**。
⚠ **我没能排除的一件事**：Starlette 的自定义异常处理器对**同步路由在线程池里抛出**的 `OperationalError` 是否 100% 生效，属于运行时问题，源码读不出来。这一条只能靠下面那枚运行时反例来判，而**我没跑成**（见末尾）。

### N3 / N4 —— **未跑（NOT-RUN），阻塞具名，不拿源码级冒充**

我按口径起了"一次性新 SQLite + 一次性具名端口 `:8491`"的真后端（`_hjp3_narrow_0924/one_time_n1.db`，只 seed 我自己那 1 traveler / 1 journey，全程没读没写 `_live.db`/`_preview.db`/任何 lane 库），**两步都卡在环境上**：
1. 我用的解释器（uv 那份 `cpython-3.12.14`，正是 `:8424` 在跑的那个）**`No module named uvicorn`** ⇒ 后端没起来，`one_time_backend.log` 只有这一行，DB 文件 0 字节。盘上有 `/d/moodle/CityNexus/.venv/Scripts/python.exe`（下一步换它），但…
2. 我在候选树 `backend/` 里**找不到建表入口**：`grep -rln "create_all|alembic upgrade|init_db" app tools ../tools` = **0 命中**，也没有 `alembic*/migrations` 目录 ⇒ 一个全新的空库跑不起这个 app，schema 是从别处来的（现成 .db 文件或包外工具），我今晚没定位到。
⇒ 所以 **N3（`.plan-ai-reason` 文字必须 `==` 服务器 `message`、屏上不得出现客户端自造 `HTTP 500`）与 N4（有 mission 行时不得说"没记录"）我一枚读数都没有**，两侧同判那套（服务端字段用 `==` + "等值必须认"正控）也还没上。**这一格仍挂我名下、状态是 NOT-RUN，不是 PARTIAL、更不是 PASS。**

**下一步（谁接手都能直接做，两条我实测过一半）**：一次性库的 schema 用**在线备份只取结构**从现成库复制（`sqlite3` 读 `sqlite_master` 里 `type='table'` 的 CREATE 语句逐条执行到新库，**不带数据行**），解释器换 `/d/moodle/CityNexus/.venv/Scripts/python.exe`；然后照我已写好的 `run_n1_n2_rig.py` 跑：控制轮（无锁）→ 持锁轮（generation / hydration / agent-commands 各一发，测 503 或框架 21 B）→ 释放后再一发（证明 503 不是无条件），收尾真杀端口 + 删库 + 断言不存在。脚本与读数都在证据里。

**纪律**：0 次 `demo/reset`、0 次读写 `_live.db`/`_preview.db`、0 次改产品字节、凭据 0 打印。收尾照实说：那枚脚本在删库之前就崩了，所以一次性 DB 是**我事后手工删的**，不是脚本断言掉的；删完实测 `ls one_time_n1.db*` = 无文件、`netstat | grep 127.0.0.1:8491` = **0 行**（后端从未成功起过监听，也就没留下端口）。
