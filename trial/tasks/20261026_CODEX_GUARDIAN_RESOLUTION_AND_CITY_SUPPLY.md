# 2026-10-26 Revolution V3 执行令 | Codex | P0 守护终态 + 真实城市供给

**立刻执行，交付产品代码。** Owner：Codex。只在 `codex/sandbox-execution-security-20261025`（PR #55，Issue #47 / #49）工作，不直接写 rescue 主产品、Qoder 手机 UI、启动器。派工基线 `2bf2a5994b32049d527c71fc0f1484ddc659fccc`，工作前 fetch 更新。PR #54 已通过 `cedeaf2800` 合入，不重做匿名 ACL/签名测试/当前事件绑定的已修内容。PR #55 已有 GitHub 两个 focused-backend SUCCESS（156 pass）、真模型 10 步、当前事件提案 ACCEPTED 的独立回执，别把 PARTIAL 改写为全成功。

## 第 1 刀：修真正错误的已接受终态和模型回收

1. 在 `backend/app/simulation/progress.py` 的 `guardian_outcome` 判定，当前只接受 `proposal.status==PRESENTED`；用户已经本人签名接受、当前 Event 已 `RESOLVED` 后，PARTIAL Agent 反而落成 `AGENT_UNRESOLVED`，Qoder 4分48秒实跑已证实。**加严绑定**：同 Journey、同 simulation run pending_event、同 Guardian 对应的原生 `ReplanProposal=ACCEPTED` 与 `Event=RESOLVED`，应展示“本次建议已接受/事件已解决”，不能被旧事件、其他用户、其它 run 的方案洗白。可以引入 `PROPOSAL_ACCEPTED` 或兼容的成功终态枚举，与 Qoder 在 Issue #49 公开协商，不能无提示破坏旧客户端。测试要包含正例/错误事件/旧 proposal/PARTIAL Agent/真实失败五条。
2. `GUARDIAN_RUNNING` 已多次在 Agent 明确 `EXTERNAL_FAILED / MODEL_REQUEST_FAILED` 后仍滞留 379+ 秒，时钟与恢复按钮全灰。定位异步提交/轮询最终归并哪一步没及时更新 run，给明确**有限、幂等、可恢复**的收束机制：真实失败记录后最终进入 `PAUSED_MODEL_UNAVAILABLE` 或可恢复的准确状态，保留 retry 门；避免自动重复收费模型请求，不能靠 UI 静默变成成功。给一条失败 503/超时→服务器终态→用户可重试的 HTTP 回执。
3. 校对 `progress` 中真实 `AgentRunStep` 的安全展示字段，必要时做向后兼容的只读增量（工具名/阶段/状态/毫秒/失败分类/关联 event、run、agent），**不返回**私密 prompt、工具参数或 key。给 Qoder 一个短 TS 字段示例与消息样本，别再送 20 页文档。

## 第 2 刀：从“北京识别成功但 0 路线”到真正可发布的城市资料

当前根因已由 `20261026_CITY_POOL_ROUTE_SHAPE_GAP.md` 定位：演示北京 `provider_adcode=110000` 已绑定，`freeze-routes` 真实测到两条 TRANSIT（77分/6006m，64分/7509m），但 `route_geometry=[]`、`geometry_provider=null`；`preflight.py` 正确要求有可证的几何，故 routes=0。不是“再补一条路线即可”，也不是随机改城市名字。

1. 先从真实高德公交/步行提供者结果检查能否提取有 provenance 的线路/步行分段 polyline，并贯通到 `goal_route_freeze`、移动事实、城市公共目录与预检计数。**不准用起终点直线冒充真实路径**；若供应商这条接口确实不提供线路几何，就输出原始字段证据及标注的 `BLOCKED_GEOMETRY_UNAVAILABLE`，再提出明确的数据域/产品门槛方案，但不要无批准把没有几何的估算称为“已捕获路线”。
2. 北京最小演示需要 **≥3 条真实可计的来源路线 + ≥5 个真实来源 POI**，同一六位 adcode，快照可重放、去重、各字段可追溯。以后扩到三座不同城市 + 两个 seed；此轮先拿北京真正从 `BLOCKED` 变为可证 `ELIGIBLE`，然后做三城资料供给，不允许把原北京事实复制三份充数。
3. 针对“课堂两日各≥两站”的最小业务供应：提供至少四处具名真实 `Place` 和当天活动/路线映射，保留用户预约与活动时间，`activity_coverage` 区分本 run 新完成与历史完成；不能用天安门此前完成一次加进本 run，也不能拿无 Place 的 FREE_TIME 填第四站。必要时补测试数据构造，但不越过可行性 writer 或真实数据要求。

## 第 3 刀：把 PR #55 正确交给 Qoder 集成

- 已交 PR #55：恢复事件工具绑定、晚起/预约冲突和只改晚餐的模型 schema；本轮只做上述新增修复、provider 真相与最小联调。PR #55 的真实 Chrome 证据是隔离库 + 带未提交改动的前端，不是正式 rescue；不声称已经上线。
- 若碰到 Qoder 正在修改的 `main.py` 或 shared hot file，先在 Issue #49 写明确的 API/职责契约，Codex 仍不得写 `ClassroomPresenterPanel.tsx` 等 Qoder 文件。
- 成功则 push PR #55 或后续窄 PR，说明基线、改动文件、GitHub Actions 链接、同一事件/方案/Agent 工具回执；让 Qoder在最新 rescue 上负责合并与完整 Chrome 试用。

## 明确验收与停止机制

**首笔应是可审的 P0 真修复**：已接受 proposal 不再报 `AGENT_UNRESOLVED`，聚焦回归与 HTTP 同 run 收据；第二笔是几何捕获及实际 0→≥1 合格路线（不是简单放宽预检或写报告）。真实 provider/model 不可用时保留 BLOCKED 和错误码，继续推进其他不依赖该供给的能力。不得重置真实 DB、越过鉴权、使用未授权付费调用、force-push 或伪造模型/路线成功。

最终回报：`PRODUCT_SHA / FOCUSED_CI / RUN_EVENT_PROPOSAL_BINDING / REAL_ROUTE_GEOMETRY_PROVENANCE / ELIGIBLE_COUNT / FOUR_STOPS / UNRESOLVED_BLOCKERS`。独立贡献尽量让 Qoder一键集成，**不用让老师去研究 ORM、后台接口或 Docker 配置**。Developer Companion #51 暂保持 P1，不抢这轮 CityNexus 用户路径。
