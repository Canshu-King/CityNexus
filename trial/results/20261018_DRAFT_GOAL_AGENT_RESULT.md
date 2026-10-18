# DRAFT Goal Agent：建宁县两日任务实测

用户可以在 DRAFT 行程启动真实 AI 研究，地点零结果后仍得到可编辑两日草案，并保存、刷新恢复。此次没有查到正向 POI；草案中的具名地点调查项与费用建议仍需核实。

## 产品与实际过程

- 初次研究代码：`e0dd2eb8f01b0f38674846233599a99395ca6ed5`。
- 续作/编辑/刷新代码：`81b5d1801eb0368196002711fcc2f4cab7a4959b`。
- 同版本试玩入口：`http://127.0.0.1:14332/revolution`；使用原隔离库和原签名身份，无新建 ACTIVE、无样例地点注入。
- Chrome-use 390×844 浏览器视口；操作流程为普通签名创建建宁 DRAFT、打开 AI 助手、确认模型/公开查询预算、开始任务。
- 场景采用独立公开测试目标：两日、古村落/博物馆/小吃街、午后出门、少走路、1000 元预算。未上传用户截图中的私人要求。

初次 4 轮模型没有完成草案交付，任务保留为可继续。修复后，给**原任务**增加 2 轮预算，读取同一行程并保存草案，没有重新创建任务或重发地点查询。当前合计 6 轮模型、6 次工具、2 条 AgentRun、6 条持久 AgentRunStep。

| 实际工具 | 结果 | 耗时 |
| --- | --- | --- |
| inspect_journey | 读取签名 DRAFT | 14ms |
| discover_places：建宁县 古村落 | Photon HTTP 200，0 地点 | 1871ms |
| discover_places：建宁 博物馆 | Photon HTTP 200，0 地点 | 1627ms |
| discover_places：建宁县 濉溪 | Photon HTTP 200，0 地点 | 1565ms |
| inspect_journey（续作） | 读取原任务行程 | 12ms |
| save_draft_itinerary | 保存两日五项草案，revision 1 | 2ms |

三条查询由实际模型选择。第一条为零后，模型自主两次改变关键词；没有预设这三个词的固定执行脚本。系统保留最后一轮用于草案交付，研究阶段仍由模型选择工具。模型请求为 `auto:cheapest`；响应未报告实际路由模型，未猜测模型名称。

草案包含午后抵达休息、小吃街调查、博物馆资料核实、古村落交通调查、返程前晚餐。随后在浏览器将第一项改为“午后抵达县城，先休息再就近出门”，正常 PUT 保存，revision 2。刷新页面、重新打开 AI 助手后，同一 task 的五项和修改内容均恢复。地图面板可打开；此次没有新地点标记或地图瓦片验收。

## Qoder 六工具接口整合

交接来源为 PR #35 `e6455c2398780f5cea069386f271ed5db0f97b20`。按接口适配，未整枝合并。

| 工具 | Revolution GoalTask 接法 | 本轮证据 |
| --- | --- | --- |
| discover_places | 现有 Photon 公开查询适配，保留任务范围的来源线索 | 上述三次真实 200/0 |
| research_place_sources | 复用当前 Gateway，要求任务内 canonical Place；依赖单独配置的来源服务 | 源码接线，未真实请求 |
| acquire_place_facts | 复用当前 Gateway；Place/来源观察均绑定当前任务 | 聚焦 dispatcher fixture，未真实请求 |
| estimate_place_facts | 复用当前 Gateway，ESTIMATED_AGENT 保持估算 | 聚焦 dispatcher fixture，未真实请求 |
| generate_plans | 复用当前 Gateway，生成 CANDIDATE，选用/启动另行操作 | 聚焦 dispatcher fixture，未生成真实正式方案 |
| compare_routes | 适配 Qoder 已存 MobilityFact 只读投影，返回采集时间/过期时间 | 隔离 fixture，有/无路线及 UNKNOWN 费用 |

Photon 来源线索不冒充 canonical Place；后四种操作不能通过猜测 ID 越过已有数据合同。路线比较不发起路线采集。候选方案投影省略其他成员的集体偏好资料。手机轨迹显示对应中文工具名和结果。

## 验证与剩余项

- 新接口整合：GoalTask 服务/签名路由/草案与工具适配聚焦测试 14/14，内存 SQLite，无外部请求。
- 前端 TypeScript 全量语义检查、Vite build 通过。
- 真实续作产品 `81b5d1801e` GitHub CI `39125664283` PASS。后续接口增量的 CI 另随当前 PR HEAD，不将旧 CI 外推。
- Chrome-use 实际完成：签名 DRAFT、模型工具研究、零结果自主改词、同任务续作、两日草案、编辑保存、刷新恢复。
- 截图命令两次出现 `Page.captureScreenshot` relay timeout（含重新选择原 tab 后一次），没有生成截图文件。未用 fixture 截图替代。
- 仍需正向真实地点/来源事实、完整正式 PlanVersion→选用→ACTIVE 的后续闭环；此次 DRAFT AgentRun 不当作 ACTIVE Execution Agent 验收。

脱敏机器收据：`20261018_DRAFT_GOAL_AGENT_LIVE.json`。不含 Key、签名 token、身份资料或模型私有推理。
