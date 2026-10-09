- id: ORD-0140
  to: HERMES-REVIVAL-001（专属会话，见 `## ACTIVE_WORKERS` 19:2x 登记的 sessionId）
  priority: P0-critical
  if_head: 53fe8e8
  order: |
    **USER HARD ORDER（总线 5758456196 @17:41 + 兼容研究 5758471438 @17:42）：HERMES 是第三条持久产线，立刻立项。**
    用户更正：他最早指的是 **Hermes**，不是 Harness。**三条线从此不许再混**：
    `HARNESS_REVIVAL` = 外部自主工程/产品实验室；`HUMAN_JOURNEY_LAB` = 真人式黑盒测试；
    **`HERMES_REVIVAL` = CityNexus 产品内部的 Agent 编排 / 运行时集成**。
    本线最小执行契约 = 总线仓 `Canshu-King/CityNexus-Workspace` 分支 **`arbiter/hermes-revival`**
    （tip **`5e6e50c37949`** @17:42，我 REST 实读过：
    `docs/HERMES_REVIVAL_PLAYBOOK.md` 10,818 B / sha a0edf2cd02、
    `docs/HERMES_SMOKE_MATRIX.md` 2,212 B / sha 11f9d437e5、
    `docs/HERMES_CURRENT_PROFILE.example.yaml` 1,073 B、
    `docs/HERMES_UPSTREAM_COMPATIBILITY_NOTES.md` 4,958 B；分支上另有 `6d3c3b93`/`1611359b`/`15283976`）。
    **读它只能用 REST contents，不许对 github.com 用 git fetch/clone/push。**

    **① 本地历史锚点（我已实勘，照这张表开工，别再"搜不到就说不存在"）**
    - `D:\moodle\CityNexus-V17-DeepSeek-Semantic-Core-Hermes-20260914.zip` **4,152,651 B**（09-14 17:09）
    - `D:\moodle\CityNexus-V18.1-Native-Hermes-Connected-20260915.zip` **77,337,167 B**（09-15 01:25）
    - `D:\moodle\CityNexus-V18.2-Native-Hermes-Agent-Experience-20260915.zip` **14,932,372 B**（09-15 03:15）
    - `D:\moodle\CityNexus-V18.3-Hermes-Experience-Convergence-20260915.zip` **15,181,061 B**（09-15 09:48）
    - `D:\moodle\_hermes_v7_runtime\` = 只有 `bin/{uv,uvw,uvx}.exe` 与一个**空目录** `hermes-agent\`
    - `D:\moodle\_v18_hermes_citynexus_profile\config.yaml`（**历史 profile，唯一档案，不许原地升级**）
    - `D:\moodle\citynexus_v18_1_hermes_roadprep\`：`ACCEPTANCE_MATRIX.md`、`DEEPSEEK_HERMES_RUNTIME_MAP.md`、
      `HERMES_ACTIVATION_CONTRACT.md`、`VERIFIED_GAPS.md`、`evidence\` 等 11 项
    - 产品侧：`CityNexus\HERMES_INTEGRATION_STATUS.md`、`AGENT_RUNTIME_ARCHITECTURE.md`、`AGENT_TOOL_CATALOG.md`、
      `DELEGATION_POLICY.md`、`contracts\HERMES_MCP_BOUNDARY.md`、
      `agent-mcp\{citynexus_mcp/server.py,client.py,schemas.py, pyproject.toml, tests, citynexus-hermes-config.example.yaml}`

    **② 禁止写"Hermes 从来没接通过"** —— 历史上是假的：0.19.0 时代 `hermes mcp test citynexus` 曾 **PASS**、
    六个 CityNexus 安全 MCP 工具曾被发现；**缺的证据是"模型驱动的 Hermes"**，其历史状态是 `NOT_RUN_EXTERNAL`。

    **③ 隔离优先**：建 `D:\moodle\CityNexus-Hermes-Revival\{historical-019, current-0213, home-019, home-0213, evidence}`，
    `HERMES_HOME` 用**进程级**环境变量，保住用户/全局既有 profile。
    上游当前稳定 **v0.21.3 / tag v2026.9.14**，历史证明是 **0.19.0** ⇒ 这是**兼容性迁移**，
    **不要在唯一的旧档案上跑 `hermes update`**（v0.21.x 的 state/session/MCP 大改）。

    **④ MCP 面固定六工具**：`inspect_journey`、`inspect_twin`、`list_replans`、`search_city_services`、
    `request_replan`、`accept_replan`。inspect/list/search 只读；`request_replan` **只出提案**；
    `accept_replan` 必须走服务端 Delegation Policy + accept 时的确定性门。
    **Hermes 不得拿到 SQL、SQLAlchemy Session、直接写库或任何领域权限近路**；
    用当前版 MCP 的 **`tools.include` 精确锁六个**，**别靠 prompt 讲道理**。

    **⑤ 今天的 truth contracts 覆盖 V18 老行为**（不许因为"Hermes 当年在那棵树上跑过"就拿老 V18 产品树盖现树）：
    JourneyTwin 只是投影、单 ACTIVE PlanVersion、当前计划真值归服务端、AI 与直接规划共用同一确定性可行性核、
    DestinationCapability/CatalogHydration 为权威、可选/生效计划要求每条 used edge 有合规 mobility 证据、
    provider 失败不得静默变 mock/live 成功、BLOCKED/NO_ACTION 必须可见、Simulation provenance 与 LIVE 分开、
    C4/锁定承诺受保护。

    **⑥ 梯子不许跳**：H0 可执行/版本 → H1 doctor → H2 `mcp test citynexus` → H3 精确工具面 →
    H4 只读真值对齐 → H5 只提案重规划 → H6 受守卫 accept 的正例 + 负例 → H7 幂等 → H8 提示注入边界 →
    H9 Hermes 宕机/回退 → H10 直连 vs Hermes 确定性排程对齐；**H0–H10 全部立住之后才准试 H11 模型驱动**。
    旗舰任务原句：**"Tech Art Center 关闭了。不要影响已付款 River Cruise，预算最多额外增加 30 元。在我的授权范围内处理。"**
    期望链路：Hermes → inspect → request_replan → inspect/list 提案 → **仅当 CityNexus 返回 `ALLOW_AUTO` 才 accept** → 权威回执。
    **没有回执就不许声称改过 Journey。**
    模型侧：当前稳定版内置 DeepSeek provider（吃 `DEEPSEEK_API_KEY`），只能在 H0–H10 立住之后作为首条模型驱动路线；
    密钥留在隔离 `HERMES_HOME` / 进程环境，**任何报告里不得出现 key 或其前缀**。

    **⑦ 我已经量到的现状（写单即引用，别重复劳动）**
    - `GET /api/v1/agent/hermes/capabilities` → **200 / 1.31 s**：`configured:false`、`reachable:false`、
      `runs/events/approval/stop` 全 false、`ready:false`、`profile:"citynexus"`、`provider:null`、`model:null`
    - `GET /api/v1/agent/runtime-status` → `runtime_identity=NATIVE_DEEPSEEK_TOOL_LOOP`、
      `hermes_compat_configured:false`、`native_binary_detected:false`
    - 代码侧：`app/integrations/hermes/native_client.py` **213 行**；`main.py` 里 **6 条 hermes 只读路由**
      （capabilities / `runs/{id}` / events / journey 作用域的 runs+timeline+events）；
      `app/core/config.py` 有 **10 个 `CITYNEXUS_HERMES_*`** 变量且**没有 `enabled` 旗标**
      ⇒ **"填了 env 就算启用"这件事必须单独防，别让它变成 R6 的静默回退**；
      `agent-mcp` 目录自 09-19 12:54 基线冻结提交以来**零改动**；测试只有
      `tests/test_v18_hermes_native_client.py`（**60 行**）
    - **H0 实测结论（我打的）**：`where hermes` 无命中、`D:\moodle` 深 3 层内没有任何 `hermes*.exe`、
      `_hermes_v7_runtime\hermes-agent\` 是空目录 ⇒ **H0 = runtime unavailable**（矩阵判据正是这一档）；
      **H1 / H2 = 未跑**，卡点具名：**没有可执行**，需要把 v0.21.3 装进 `current-0213` 隔离根 + 进程级 `HERMES_HOME` 才能出 H1。

    **⑧ 纪律**：本线**只读 / 隔离起步**，不拥有生产文件，不抢 C/D/E 写域；端口自开自登记，
    不得触碰 `:4781/:4782/:8693` 与 `_qoder_cmdr_gate_20260921\backend\_live.db`（用户此刻在用的预览实例）；
    不得在活库上触发 `demo/reset`（ORD-0125 修好前全线禁止）；不动 `_qoder_integration_20260919` 与 `CityNexus\**`；
    禁止 junction/symlink 指向共享资产（**D-7**）；解释器 `D:/moodle/CityNexus/.venv/Scripts/python.exe`（3.12.14）。
    每完成一层梯子就在账本 `## DELIVERIES` 追加一块，并回报 **H0–H11 状态表**；
    总线要求的回执格式固定为 **`sessionId | runtimeState | H0 | H1 | H2`**。
    **不排队等 ORD-0131/0125/0132/0134**：那些是用户此刻的 P0，本单并行跑。
  status: DISPATCHED@2026-09-21T19:2x+08 by 494abfd7（编号说明：仲裁令里写的"立 ORD-0135"已被 19:0x 的向导缺陷单占用，本单取下一个空号 **0140**，内容一字未减）
