# 跨进程证据方案：两个 uvicorn worker 下的"败者回读"（ORD-0224 处置一 / ORD-0210 FINAL CLOSED 的阻塞格）

状态：**方案，不是门**。指挥官 03:0x 明确：今晚不要求做，等仲裁回"跨进程是否必要"这句；在那之前我不为它写门、也不动强修。
写这份方案的原因：`ORD-0210 FINAL CLOSED = BLOCKED_ON_CROSS_PROCESS_EVIDENCE`，而阻塞物必须写清楚"最少需要什么"，否则这句 BLOCKED 只是一个借口。

交付 sha 参照：`f92f9e9`（本轮所有已签字的读数）与 `b2c6153`（处置二的注释提交）。

---

## 1. 待证的命题（一句话，可反证）

> 两个**各自独立**的 uvicorn 进程持有同一个 app-resolved 库时，同一 hydration 指纹的并发请求仍然：库里 **1 行 OPEN**、五个 caller 拿到 **同一个 operation_id**、且**上报这个 id 的是 `except IntegrityError` 里的败者回读**（不是我今晚测过的那两次读）。

今晚测到的所有门都在**单进程多线程**里（TestClient + `threading.Barrier` + 闩）。单进程里 SQLAlchemy 的 session、`expire_on_commit=False` 的对象、`_dispatched` 集合都是共享的，所以"跨进程"这一格我**没有读数**——我不签 FINAL CLOSED 就是这个原因。

## 2. 最少需要什么（七件，缺一不可）

1. **两个真实后台进程**：门自己 `subprocess.Popen` 起两个 `uvicorn app.main:app`，端口用**自动分配**（`--port 0` 不支持就绑 127.0.0.1:0 再回读），两个进程共享同一个 `CITYNEXUS_DATABASE_URL` = 本次 run 的临时库（门 spawn，所以这个库是我的，不违反 ORD-0211 的"门不许自带库"）。绝不碰 `:4781/:4782/:8693`，绝不指向 `_live.db`/`_preview.db`。
2. **端口身份 ≠ 就绪**：一个 200 可能是别的 lane 的后台（本链已量过的教训）。就绪判据必须三件齐全：① 我 spawn 的 pid 仍活着；② `netstat` 上该端口的持有 pid == 我的 pid；③ 该进程读到**我库里那一枚 marker 行**（例如启动前写入一条带 uuid 的 `journeys`/审计行，`/health` 或任一读接口把它回显出来）。三者缺一即 `NOT_READY_OWNERSHIP_UNPROVEN`，门直接红，不许退化成"200 就算好"。
3. **跨进程版的"闩"**（这是最难的一格，pytest 的 barrier 穿不过进程边界）。两条路：
   - **(a) 推荐：用真实产品路径把 worker 停在 RUNNING**。`CITYNEXUS_ANYWHERE_RESOLVER=photon`，并把 `CITYNEXUS_PHOTON_BASE_URL` 指到门自己起的**本地假 provider**（127.0.0.1，接受连接但**故意不回响应**，直到门放行）。两个进程里的 `_run_operation` 都会卡在 provider 调用上 ⇒ 行停在 `RUNNING`（仍算 OPEN）⇒ "同一 OPEN 窗口"由**可观测状态**成立，而不是靠 sleep。放行后再等它落终态。注意：这条链上还有一条已量过的坑——默认 `httpx` UA 会被 photon 真服务拒（403），但我们打的是自己的假服务，无关；**并且这一档全程 0 次外部解析**，仍用记录型 `getaddrinfo` 阻塞器量出来。
   - **(b) 不推荐：在产品里加一个 hold seam**（`CITYNEXUS_HYDRATION_HOLD` 之类）。那是为了测试改产品真值，且会把"能停住 worker"变成产品契约。除非 (a) 被证伪，否则不走。
4. **判词只读行，不读状态码**：断言从**共享库**里读 `catalog_hydration_operations WHERE fingerprint = ?` 的行数、id 集合、status/`queued_at`/`started_at`/`finished_at`；五个 caller 拿到的 id 从两进程的 HTTP 响应里收集。竞态判 row 不判 code（本链已有规矩）。
5. **败者回读真的发生了没有**（否则门可能是被今晚那条预查满足的）。跨进程没法 monkeypatch，所以只能用**外部代理指标**并明标来源：① 两进程 stdout/stderr 里 sqlite `UNIQUE constraint failed: catalog_hydration_operations.fingerprint` 的出现次数（= 撞索引次数）；② 若次数为 0 ⇒ 这一批不算跨进程反例，判 `INSTRUMENT_INSUFFICIENT`（红），**不许**用"结果对就行"糊过去。若需要更硬的证据，正确做法是给产品的 loser 分支加一条结构化审计行（那是产品可观测性改动，另开单，不混在这里）。
6. **反例（步 6 的形状，跨进程版）**：至少两把突变各跑一次，且必须在**跨进程门**上报红：① 破坏败者回读（今晚的 `Y3`，两进程下的等价改动）；② 破坏 durable 唯一性（`Y2`——跨进程下它应当**必然**红，因为单进程里预查替它兜底这层遮蔽在跨进程里不该复现）。若 ② 在跨进程下仍然绿，说明我 03:0x 的"A 与 B/C 互为冗余"结论只成立于单进程形状，必须当场改口。
7. **收据形状 + 自清**：run shape 仍要逐 run 记 target nodeid / 命令 / 每 run 一个**新**临时库；每 run 还要额外记 `spawned_pids`、`ports`、`index_conflict_lines`、`marker_row_visible_in_both_processes`。收尾删：两个子进程、假 provider、临时库（生产者自清，就是指挥官刚确认的那条规矩）。

## 3. 成本与预算（决定它今晚该不该做）

| 项 | 估计 | 依据 |
|---|---|---|
| 单次 run 时长 | 30–60 s | 起 2 个 uvicorn + 一次假 provider 往返 + 放行落终态；现有 `gate_streak.py` 每次子进程预算 1800 s（`gate_streak.py:72-73`），放得下 |
| 10 连 | ≈ 6–10 min | 尺的形状不变（一条 nodeid、一次子进程） |
| 尺能不能跑这个形状 | **能** | `RUN_SHAPES=(single-node, node-with-preceding-doors, whole-file)`；`FORBIDDEN_COMMAND_FLAGS` 是 `--maxfail/-x/--reruns/--timeout/--deselect/-k/-n/--collect-only`——我的方案一个都不需要（两进程由门自己 spawn，不用 xdist/timeout 插件）。但尺**只**判"每次 run 新临时库 + 逐 run 目标节点判定"，**跨进程所有权不在它的判据里** ⇒ 第 2 条的 marker 行必须由门自己做，尺不会替我证明"这两个端口是我的后台" |
| 盘 | 每 run 一枚临时库 + 两份 uvicorn 日志 | 现在 D: 97% 满（我今早自清释放 894 MB），所以这条要先量后跑 |

## 4. 我会先做的"一步探针"（不是门）

写门之前先花一次时间证伪一个更便宜的可能：**SQLite 的单写锁下，两个进程真能同时进入"各自的未提交视图"吗？** 如果实际序列永远是 `A commit → B 读到 A 的行`，那"跨进程"这一格的产品增量可能只是"多一次 read 命中"，仲裁那句"是否必要"的答案就会不一样。探针：两个进程并发 `INSERT` 同指纹（一个进程 commit 前另一进程读）+ 记 `busy_timeout` 行为，读数贴出来，**不写成门、不进套件**。

## 5. 需要谁定什么

- **仲裁**：跨进程是否属于 `G3_CONCURRENT_OPEN_GENERATION` 的**必要条件**（本方案按"必要"来写；若判定不必要，`f92f9e9` 那三张 `STREAK_MET(10)` 就是完整证据，`ORD-0210 FINAL CLOSED` 可以只等反向突变声明那格）。
- **指挥官**：若必要，请把它开成独立单（含 §2 第 5 条那个"要不要给 loser 分支加审计行"的产品可观测性决定——那是另一个人的作业面，不该塞进本单）。
