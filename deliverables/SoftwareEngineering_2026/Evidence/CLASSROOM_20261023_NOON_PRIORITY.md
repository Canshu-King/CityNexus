# 2026-10-23 12:00（北京时间）课堂展示：Visio + Microsoft Project 最终封包任务

**截止时间：2026-10-23 12:00 +08:00。项目进入展示冻结优先级，禁止无关重构。**

## 事实基线

- 当前课程交付主线：`review/se-coursework-deliverables-r1`。
- R2 原生 Visio 四图与 Project 完整 `.mpp` 均已交付；Visio Shape Data、连线和 Project 61/61 依赖结构已获独立验收证据。
- GPT 2026-10-22 外审：`deliverables/SoftwareEngineering_2026/Evidence/INDEPENDENT_R2_REVIEW_20261022.md`。
- 当前阻碍**不是没有文件**：原始 Project 整屏 PNG 被 Chrome 挡住；计划人工工时 1808h 超过三人常规容量 840h；历史计划日期/课程截止日/实际提交需区分。
- 用户只要求明天（即 2026-10-23）中午**两种软件都能向老师现场展示**；真实可用优先于把 R3 全部潜在问题做完。

## 展示冻结 P0（马上执行）

1. 在安装的 **Microsoft Visio 桌面版**中打开真实 `Visio/01_CityNexus_System_Architecture.vsdx` 和 `Visio/03_CityNexus_Agent_Workflow.vsdx`。实际选中形状，展示可以移动、编辑文字、重新保存副本；保持原文件不被误改。 `02_User_Journey` 备用； `04_Use_Case` 老师追问时用。
2. 在安装的 **Microsoft Project 桌面版**中打开 `Microsoft_Project/CityNexus_Software_Engineering_Plan.mpp`。实际切换 WBS / 甘特图 / 里程碑 / 网络图，证明任务、工期、前置依赖是真实可编辑 Project 数据。另准备 `CityNexus_Milestone_View.mpp` 以便快速展示关键日期。
3. 这两款原生文件都要进行“打开 → 改一处不重要的内容 → 保存到临时副本 → 关闭 → 重新打开”的现场验证，记录工具版本、时间与实际成功/失败。如软件未安装或许可证过期，请第一时间具体告知用户，不要用 PDF 假装通过原生测试。
4. 关闭 Chrome 和其它遮挡窗口后**重新截图**；确保截图主体是真正的 Project 甘特图和表格，不可把被浏览器挡住的旧 PNG 当成果。截图放大后肉眼看得到任务名和日期。Project 内至少一个无遮挡甘特图截图、一个里程碑截图；Visio 至少两张清晰预览。
5. 保留原生文件的同时，输出一个**极简的汇报导航文档**：先 Visio 系统架构（30秒）→ Agent 工作流（30秒）→ Project 甘特图（40秒）→ 里程碑/分工（20秒）。附清楚的文件路径、两个程序的启动说明和现场失败备用预览。
6. 项目工时 1808h 为未经成员确认的估算，不得在汇报中称为真实人工已完成工时。若没来得及完成资源容量 R3 重排，就**在计划与口头讲解中明确标注“预估工时待复核”**，不要删除原始异常证据，更不能虚报资源无超配。Part 1 课程平台真实提交状态未核实，不得宣称已交。

## 时间分配原则

先用已有成果交出老师能看的 Visio 和 Project（P0），再修资源超配/日期语义（P1）。如果 P1 修补会破坏当天已验证的原生文件，停止冒险，保存当前可演示的版本作为课堂冻结版。不要升级到无关的主产品任务，更不要重跑 Codex Revolution 历史验证。

## 最小交付合同

`deliverables/SoftwareEngineering_2026/` 内必须能清晰找到：
- `Visio/01_CityNexus_System_Architecture.vsdx` 和 `Visio/03_CityNexus_Agent_Workflow.vsdx`；
- `Microsoft_Project/CityNexus_Software_Engineering_Plan.mpp`；
- 至少两张无遮挡、可读的 Office 真实屏幕截图（可附单页预览 PDF）；
- `Evidence/CLASSROOM_20261023_README.md`，注明实际软件打开/编辑/重开结果、已知进度风险、展示顺序。

推送到同一课程分支，写明最终 SHA。禁止仅靠 `zipfile.testzip()` 或自称绿色证明 Windows Office 可用。

**不要误解为要从零生成 Visio / Project。现在最需要的是今日中午真实人类展示闭环。**
