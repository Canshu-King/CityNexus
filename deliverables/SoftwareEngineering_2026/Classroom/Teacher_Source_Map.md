# 课堂演示图的出处对照表（Teacher_01 / Teacher_02）

课堂版两张 Visio 图上**一个文件名、一个行号都没有**——这是任务书的要求
（`Evidence/TEACHER_READABILITY_CORRECTION_20261023.md` 第 5 行：来源行号不是流程内容，
应保存在 Shape Data 的 SourceRef／附录，不要显示在方框正文）。

出处没有丢，分两处放着：

1. **图上**：选中任意方框 → `Ctrl+1`（或 数据 → 形状数据）→ `SourceRef` 一行写着它对应的代码位置；
   `NodeId`、`State`、`FlowEdge` 同在这个窗口里。
2. **本表**：17 个形状 + 15 条连线的完整对照，以及每个数字是怎么量出来的。

本表所有行号都是 **2026-10-23 当天从当前工作树现读的**，不是抄自上一版。

## 一、Teacher_01_System_Overview.vsdx（8 框 7 线）

| 图上文字 | Shape Data 的 SourceRef | 代码位置（现读） |
|---|---|---|
| 旅行者／提出出行需求 | 前端对话入口与向导；journey 会话 | `frontend/src/routes/v8Routes.ts:1`（desktopRoutes）、`backend/app/main.py:3136`（`POST /api/v1/journeys`） |
| 前端／地图与对话 | 15 个路由面板、MapLibre 地图、Copilot 面板 | `frontend/src/routes/v8Routes.ts:1` 桌面路由 15 条、`:60` 移动路由 5 条；`frontend/src/components/JourneyMap.tsx:65` |
| 后端／统一接口 | FastAPI `/api/v1`，175 个端点 | `backend/app/main.py:554`（`app = FastAPI(...)`），端点计数见下表 |
| Agent／规划与调用工具 | gateway 与 mission 循环，11 个白名单工具 | `backend/app/agent/gateway.py:358`（`RUNTIME_MCP_ALLOWLIST_V2` 闸门）、`backend/app/agent/runtime.py:342` + `:405`（mission 循环，`max_steps=12`） |
| 地点与路线数据／外部服务 | integrations/discovery、Photon／Nominatim／Open-Meteo；默认 mock | `backend/app/integrations/discovery/photon.py`、`backend/app/integrations/discovery/provider_identity.py`、`backend/app/integrations/discovery/real_city.py` |
| 生成行程方案／可对比多套 | plan 生成与 replan 提案，proposal 表 | `backend/app/db/models.py:782`（`__tablename__ = "replan_proposals"`） |
| 展示方案／等待用户确认 | 前端方案对比与 Trip Studio；确认前不写库 | `frontend/src/routes/v8Routes.ts:1`（`studio` 键）、`backend/app/agent/gateway.py:41`（`IdempotencyKey`） |
| 保存行程与状态／写入并留审计 | SQLite 60 张表：journey、proposal、audit、idempotency | `backend/app/db/models.py:175`（journeys）、`:782`（replan_proposals）、`:562`（audit_logs）、`:677`（idempotency_keys） |

## 二、Teacher_02_Agent_User_Flow.vsdx（9 框 8 线）

| 图上文字 | Shape Data 的 SourceRef | 代码位置（现读） |
|---|---|---|
| 用户提出需求 | 前端对话入口与向导；journey 会话 | `backend/app/main.py:3136` |
| Agent 理解需求 | mission 循环，最多 12 步 | `backend/app/agent/runtime.py:342`、`:405` |
| 调用地点与路线工具 | 白名单 11 个工具；未知工具在写审计之前 404 | `backend/app/agent/tool_catalog.py`（`ToolDescriptor(` 共 11 处）、`backend/app/agent/gateway.py:358` |
| 生成行程方案 | plan 生成；供应商默认 mock，真实供应商要显式开启 | `backend/app/integrations/provider_config.py:32`、`backend/app/integrations/discovery/photon.py` |
| 地图展示方案 | MapLibre 地图与方案对比面板 | `frontend/src/components/JourneyMap.tsx:65` |
| 需要修改吗？ | replan 判定：是否改动行程 | `backend/app/db/models.py:782`（replan_proposals 就是这一步的产物） |
| 继续调整方案（回到第 3 步） | replan 提案，等待下一次确认；提案不写库 | `backend/app/agent/gateway.py:41`、`backend/app/db/models.py:677`（idempotency_keys） |
| 用户确认方案 | 确认门：Idempotency-Key + 授权；未确认只留提案 | `backend/app/agent/gateway.py:41`、`:358` |
| 保存并留下审计 | 域服务写入 + audit + receipt；SQLite 60 张表 | `backend/app/db/models.py:562`（audit_logs） |

## 三、Teacher_03 的中文任务名对照（16 行）

老师看到的任务名是中文，计划基准里是英文。**同一行的展示名**，不是新任务：
日期、工期、完成度、工时、成本全部照抄原行，英文原名与 WBS 写进该行备注，
重开后按中文名逐行匹配核对（每名恰好一行、日期相同）。

| # | 图上中文名 | 计划基准原行名 | WBS |
|---|---|---|---|
| 1 | 选题与开题 | 1  Coursework initiation and project selection | 1 |
| 2 | 需求工程 | 2  Requirements engineering | 2 |
| 3 | 系统设计与架构 | 3  System design and architecture | 3 |
| 4 | 后端平台与数据层 | 4  Backend platform and data layer | 4 |
| 5 | 地图与地点数据接入 | 5  Map and place data integration | 5 |
| 6 | AI Agent 与 Hermes 能力 | 6  AI agent and Hermes capability | 6 |
| 7 | 前端界面与交互 | 7  Frontend UI and interaction | 7 |
| 8 | 集成与联调 | 8  Integration and consolidation | 8 |
| 9 | 验证与缺陷管理 | 9  Verification and defect management | 9 |
| 10 | 课程交付物与汇报 | 10  Coursework deliverables and reporting | 10 |
| 11 | 最终验收、文档与交付 | 11  Final acceptance, documentation and delivery | 11 |
| 12 | M10 Part 1 截止 10-02（已错过） | M10  Part 1 course deadline (contract 2026-10-02, missed) | 10.5 |
| 13 | M9 系统测试就绪（计划目标） | M9  System test ready (plan target) | 9.7 |
| 14 | M11 中期师生检查 10-23 中午 | M11  Mid-term teacher review (scheduled 2026-10-23 noon) | 10.6 |
| 15 | M12 Part 2 截止 11-06 | M12  Part 2 course deadline (contract 2026-11-06) | 10.7 |
| 16 | M13 课程交付完成（计划） | M13  Coursework delivery (plan) | 11.3 |

里程碑的**截止日**（Deadline 字段）与计划日不同，这是刻意的：M10 行日期 9-29、
合同截止 10-02、状态"已错过"；M12 行日期 10-23、合同截止 11-06。两者都显示在任务表里，
语义分层写在 `Evidence/STATUS_AND_OVERDUE.md`。

## 四、图上出现过的每个数字是怎么来的

| 数字 | 命令（在工作树根目录执行） | 2026-10-23 实测 |
|---|---|---|
| 175 个 HTTP 端点 | `grep -acE '^@app\.(get\|post\|patch\|put\|delete)' backend/app/main.py` | 175 |
| 60 张数据库表 | `grep -ac '__tablename__ = ' backend/app/db/models.py` | 60 |
| 11 个 Agent 工具 | `grep -ac 'ToolDescriptor(' backend/app/agent/tool_catalog.py` | 11 |
| mission 最多 12 步 | `grep -anm1 'max_steps: int = 12' backend/app/agent/runtime.py` | `:342` |
| 桌面路由 15 条 | 全表：`grep -acE '^\s*\{ *key:' frontend/src/routes/v8Routes.ts` → 20；桌面：`sed -n '1,42p' frontend/src/routes/v8Routes.ts \| grep -acE '^\s*\{ *key:'` → 15；移动：`sed -n '60,$p' ... \| grep -acE '^\s*\{ *key:'` → 5 | 桌面 15、移动 5（合计 20 条键；图上写的是桌面的 15） |
| main.py 规模 | `wc -l < backend/app/main.py` | 14,569 行 |

同一批数字在 `Evidence/SOURCE_MAPPING.md` 里有一份覆盖全部四张取证图的总表；
本表只覆盖课堂版这两张。

## 五、要看"带行号的取证版"去哪里

| 课堂版 | 取证版（每个框正文里带 `文件:行号`） |
|---|---|
| `Classroom/Teacher_01_System_Overview.vsdx` | `Visio/01_CityNexus_System_Architecture.vsdx` |
| `Classroom/Teacher_02_Agent_User_Flow.vsdx` | `Visio/03_CityNexus_Agent_Workflow.vsdx` |
| `Classroom/Teacher_03_Project_Overview.mpp`（11 阶段 + 5 里程碑） | `Microsoft_Project/CityNexus_Software_Engineering_Plan.mpp`（65 行、依赖、资源分配、关键路径） |

取证版没有被课堂版取代，两份都在交付包里；课堂版也没有为了好看改任何事实——
被拿掉的只有源码坐标和泳道细节，它们原样留在 Shape Data 和上面这两张表里。
