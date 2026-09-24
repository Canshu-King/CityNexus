### 🔀 aad2d1f2 P3 · ORD-0272 **跨进程面**读数交 @红队 派生（claimed_result 归我，closure 只认你的 derived_result） @2026-09-24T23:4x+08

**我量的那一面**：F 的 `test_qoder_ord0272_continuation.py` 文件头自己写明**八格全是单进程**，而「真正的跨进程复现归 verifier（HJ-P3）与跨进程门」。这就是那一面：**两枚独立 uvicorn PID（`:8495` / `:8496`）服务同一枚全新临时库**，每一条判据都落在**行**与**投影字段**上（门外第二条 sqlite 直连），不落在状态码上。

**坐标（先说清，避免 nodeid 根踩坑）**
- `sha` = **`aa29612c855c10f1584a333cc19526066813b072`**（tree `d96c2974924d19831495f2945117d4221a1b6d62`，父 `44b428da83e40abd6d2b770006cb88dc022cf2fd`）；我按 40 位 sha 取包、**6,980/6,980 blob 逐文件字节全等**。
- **我的 run cwd = `<snap>/CityNexus-aa29612…/backend`**。⇒ 我这边写 nodeid **一律以 `tests/…` 起头**（`--collect-only` 实测 8 条：`tests/test_qoder_ord0272_continuation.py::test_G1… ::test_G8…`，`8 tests collected`）。**不要把 `backend/tests/…` 当成我的根**——你抓到的那个"收不到载体"就是根不一致，不是产品红。
- **被测树里没有一行是我的**：我用的是只读导出 + 两枚一次性进程，产品字节 0 改动；`status=COMPLETED` 这类我读不到的字段一律没写。

**四条腿（跨进程，逐条带 shape）**

| # | 形状（我发的） | 读数（两个进程各自的回答 + 门外 durable） | 覆盖它的单进程格（nodeid） |
|---|---|---|---|
| **Q1 身份跨进程** | P1 `POST /plans/generate {candidate_count:3, mission_id:m}`；随后 **P2 发同一枚 `mission_id`** | P1 `201` / 3 枚 plan id；P2 `201` / **逐位相同的 3 枚 id**；`plan_versions` 行数 **3 → 3**（`ids_identical=True`、`no_second_batch=True`） | `tests/test_qoder_ord0272_continuation.py::test_G1_one_mission_generates_once_and_a_plain_resend_replays_the_same_plans` |
| **Q2a 客户端键跨进程（同请求）** | P1 与 P2 各发一次**同一枚 header `Idempotency-Key` + 同 body** | 两发都 `201`，**plan id 逐位相同**（`replay_same_ids=True`） | `…::test_G3_second_device_with_no_client_header_still_gets_the_same_answer`（同族、不同形） |
| **Q2b 客户端键跨进程（换语义）** | P2 用**同一枚键**、把 `candidate_count` 3→2 | `409`，`error.message` **逐字 `==`** `same idempotency key used for a different request`（与门内那枚字面副本等值）；不留新候选 | `…::test_G4_two_identities_stay_two_doors_and_both_use_the_canonical_409` |
| **Q2c Phase A 占位跨进程可见（这条是我这单的核心）** | 门外第二条连接把 mission 绑定回执行 `plans.generate:cont:<m>`（原为 `response_status=201 / response_json=json`）**真落盘改成 `response_json = NULL`**（`UPDATE … rowcount=1`），再让 **P2** 发同一枚 `mission_id` | **P2 答 `409` + `error.message` 逐字 `==` `agent idempotency record is incomplete`** ⇒ **P1 提交的占位行对另一进程可见**，另一进程**没有重跑生成**、也没有另造词 | `…::test_G2_the_two_states_of_one_claim_answer_differently_and_neither_reruns_generation` |
| **Q3 mission 绑定的 owner 能否被另一进程读回** | **P2**（不是写它的那枚进程）读 `GET /journeys/{jid}/agent-feed?limit=200` | `200`、5 条事件，命中 `facts.continuation_id == cont:<m>`，且 `facts.mission_id` 与 **`plan_version_ids` 正是 Q1 那 3 枚**、`summary="this mission's continuation produced these plans"` ⇒ **owner 跨进程可读回** | `…::test_G7_the_feed_projection_names_the_mission_and_the_plans_it_produced` |

**两条我要你按判据用的关键坐标**（源码，不是我的推断）
- 身份与键的构造在 `backend/app/main.py::_plan_continuation_identity`：`continuation_id = f"cont:{request.mission_id}"`；回执键追加 `f"plans.generate:{continuation_id}"` ⇒ **mission 绑定的回执行是 `plans.generate:cont:<mission_id>`，不含客户端 header 值**（我第一版就是拿 header 值去查，查出 0 行——那是我的仪器错，不是产品空）。
- 回执三态在 `idempotency_keys(key, operation, request_hash, response_status, response_json, created_at, expires_at)`：`response_json IS NULL` = 占了没跑完；两句话面量分别是 `same idempotency key used for a different request` 与 `agent idempotency record is incomplete`（我按 `==` 判，不按 `in`）。

**与 K8 的关系（我不替你涂）**：F 自报的 8 臂里那枚具名存活 **K8（回缝守卫）**，我**还没有她的载体清单**，所以这一轮我**没有对它做定向观测** ⇒ 我名下的状态写 **K8 = NOT-YET-TARGETED（等载体清单）**；一旦拿到载体，我在**上面这套跨进程面**上补观测，**观测不到就写 `UNOBSERVED_CROSS_PROCESS`，不算绿**。
**B-1 口径**：本块的每一条都是 **claimed_result（我的）**；**closure 只认你按载体派生的 derived_result**。你要哪条腿的原始 body / 行数 / 键名，我按 sha+shape 复现给你。

**纪律与收尾（脚本内断言）**：一次性库由 `ensure_schema()` 建（**不再重放旧 DDL**）；**0 次 `demo/reset`**（舞台按 F 的合法配方走 in-process `seed_demo`，且只在缺东西时触发）；`_live.db`/`_preview.db` 0 读写；凭据 0 打印；已发布路径 0 覆盖；`netstat` 收尾 `:8495`/`:8496` = **0 listeners**、临时库含 `-wal/-shm` 已删、`assert_clean = True`。
