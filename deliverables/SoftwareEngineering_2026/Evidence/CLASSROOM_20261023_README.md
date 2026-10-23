# 课堂展示单 - 2026-10-23 12:00 +08:00

生成 2026-10-23 02:14。这份文件只回答一个问题：**中午怎么在真机上把 Visio 和 Project 演示完，以及哪些话不能说。**

## 0. 现场先说清楚的三件事

1. 计划里的工时是**课程估算**，不是已发生的真实人工时；每人每周 20 h 是假设，还没有三位成员各自确认。
2. Part 1（2026-10-02 截止）在课程平台的真实提交状态**未核实**，计划里按「已错过」记录，不宣称已交。
3. 状态日 2026-10-22 之上有 **14 行**任务已过计划完成日仍未完成（全表见 `Evidence/STATUS_AND_OVERDUE.md`）。

## 1. 演示顺序（约 2 分钟主线）

| 步 | 时长 | 打开什么 | 说什么 |
|---|---|---|---|
| 1 | 30 s | `D:\moodle\CityNexus\deliverables\SoftwareEngineering_2026\Visio\01_CityNexus_System_Architecture.vsdx` | 四层结构：体验层 / HTTP 面 / Agent 平面与域服务 / 供应商与持久化。每个方框都是被审代码树里真实存在的组件，图上带来源引用。
| 2 | 30 s | `D:\moodle\CityNexus\deliverables\SoftwareEngineering_2026\Visio\03_CityNexus_Agent_Workflow.vsdx` | Agent 不是想写就写：白名单、审计、幂等、授权四道门的顺序来自 `gateway.py`；未知工具在产生任何审计行之前就 404。 |
| 3 | 40 s | `D:\moodle\CityNexus\deliverables\SoftwareEngineering_2026\Microsoft_Project\CityNexus_Software_Engineering_Plan.mpp` | 切 WBS / 甘特图 / 网络图 / 跟踪甘特图：65 行、61 条依赖、引擎自己算的关键路径与成本 $4460.69。
| 4 | 20 s | `D:\moodle\CityNexus\deliverables\SoftwareEngineering_2026\Microsoft_Project\CityNexus_Milestone_View.mpp` 或 `D:\moodle\CityNexus\deliverables\SoftwareEngineering_2026\Microsoft_Project\CityNexus_Plan_Recovery.mpp` | 里程碑与分工：13 个里程碑分「预计就绪日」和「课程截止日」两种语义；重计划文件从状态日排到 2026-11-04，早于 2026-11-06 的合同截止日。
| 备 | 随时 | `D:\moodle\CityNexus\deliverables\SoftwareEngineering_2026\Presentation\CityNexus_SE2026_Briefing_Deck.vsdx` | 老师追问细节时翻对应页；四页 16:9，正文 13 pt 起。

## 2. 怎么启动

```
start "" "D:\moodle\CityNexus\deliverables\SoftwareEngineering_2026\Visio\01_CityNexus_System_Architecture.vsdx"
start "" "D:\moodle\CityNexus\deliverables\SoftwareEngineering_2026\Visio\03_CityNexus_Agent_Workflow.vsdx"
start "" "D:\moodle\CityNexus\deliverables\SoftwareEngineering_2026\Microsoft_Project\CityNexus_Software_Engineering_Plan.mpp"
```

本机实测版本：Visio `16.0 build ?`，Project `16.0`。

## 3. 真机驱动验证结果（不是导出成功，是真的开过、改过、存过、重开过）

验证方式：把交付文件**复制**到临时目录再操作，交付原件在验证前后按字节比对。

**01_CityNexus_System_Architecture.vsdx** - 整体 PASS；原件字节未变：True

| 步骤 | 结果 |
|---|---|
| open | PASS 01_CityNexus_System_Architecture.vsdx |
| pinX | PASS 1.73 |
| glued connectors | PASS 2 |
| move +0.75in | PASS 0.75 |
| pinX after | PASS 2.48 |
| edit text | PASS True |
| text reads back | PASS True |
| save the copy | PASS saved |
| close | PASS closed |
| reopen the copy | PASS 01_CityNexus_System_Architecture.vsdx |
| move persisted | PASS True |
| text persisted | PASS True |
| close again | PASS closed |

拖动的是 `圆角矩形`（ID 20，原文字 'CopilotDock + AgentComposer\n'）：形状向右移 0.75 in，移动后的矩形范围 x 1.24..3.72；粘在它上面的连线 2 条，端点从 [[[0.49, 10.19], [0.563, 9.237]], [[0.563, 8.643], [0.587, 7.953]]] 变成 [[[0.49, 10.19], [1.313, 9.237]], [[1.313, 8.643], [0.587, 7.953]]]，仍落在移动后的形状上：是。

**03_CityNexus_Agent_Workflow.vsdx** - 整体 PASS；原件字节未变：True

| 步骤 | 结果 |
|---|---|
| open | PASS 03_CityNexus_Agent_Workflow.vsdx |
| pinX | PASS 1.3085 |
| glued connectors | PASS 1 |
| move +0.75in | PASS 0.75 |
| pinX after | PASS 2.0585 |
| edit text | PASS True |
| text reads back | PASS True |
| save the copy | PASS saved |
| close | PASS closed |
| reopen the copy | PASS 03_CityNexus_Agent_Workflow.vsdx |
| move persisted | PASS True |
| text persisted | PASS True |
| close again | PASS closed |

拖动的是 `开始/结束`（ID 20，原文字 'A request arrives\nmain.py:14'）：形状向右移 0.75 in，移动后的矩形范围 x 1.275..2.842；粘在它上面的连线 1 条，端点从 [[[2.092, 9.85], [2.222, 9.85]]] 变成 [[[2.058, 10.26], [3.006, 10.26]]]，仍落在移动后的形状上：是。

**demo_plan.mpp**（`CityNexus_Software_Engineering_Plan.mpp` 的副本）- 整体 PASS；交付原件未变：计划 True、里程碑视图 True

| 步骤 | 结果 |
|---|---|
| open the copy | PASS True |
| rows | PASS 65 |
| links read back | PASS 122 |
| switch to WBS / 任务工作表 | PASS True |
| switch to Gantt | PASS True |
| switch to Network | PASS True |
| switch to Tracking Gantt | PASS True |
| switch to Resource Sheet | PASS True |
| switch to Calendar | PASS True |
| edit a note | PASS True |
| note reads back | PASS True |
| save the copy | PASS True |
| close | PASS True |
| reopen the copy | PASS True |
| note survived | PASS True |
| links survived | PASS 122 |
| milestone view file opens | PASS opened |
| milestone rows | PASS 13 |
| close milestone view | PASS True |
| close the copy | PASS True |

这条把外审留的最后一个问号关掉了一半：**拖动形状时连线确实跟着走**（上表「connector follows」两行），因为量的不是端点位移而是「拖动后连线端点是否仍落在形状自己的矩形内」，容差 0.2 in 小于 0.75 in 的位移，落在原位的线不可能通过。

## 4. 现场如果打不开 Office（备用预览）

| 备用 | 文件 |
|---|---|
| Presentation/previews/CityNexus_SE2026_Briefing_Deck.pdf | 存在，49423 字节，sha256 `4d9a3c4ae1d4e53a` |
| Microsoft_Project/previews/Gantt_Chart.png | 存在，225387 字节，sha256 `f01dc3684255936e` |
| Microsoft_Project/previews/Milestone_Timeline.png | 存在，203766 字节，sha256 `c8a809eb8140c521` |
| Microsoft_Project/previews/Network_Diagram.png | 存在，189475 字节，sha256 `961a3e9b9ac06179` |
| Microsoft_Project/previews/WBS_Task_Sheet.png | 存在，310899 字节，sha256 `be7025d452b83b9c` |
| Microsoft_Project/Plan_Briefing_Print.pdf | 存在，450530 字节，sha256 `095fc85c78749ad4` |
| Briefing/previews/CityNexus_Plan_Briefing_A3.pdf | 存在，45713 字节，sha256 `3d2a8b1155b5dfc7` |

截图是 Win32 `PrintWindow` 抓的目标窗口自身 DC（`se_project_snapshot_r2.py`），不是屏幕矩形，所以别的窗口压在上面也不会把 Chrome 当成 Project；抓图时以文件系统只读方式打开，摘要前后一致：`4cd35d0725c2c5d3`。

## 5. 数据一句话

* 学生工时 220.9 h，单人单周峰值 19.9 h（声明可用 20 h），超配人周 0；构建在出现任何超配时直接拒绝发布。
* 依赖 61 条声明、引擎回读 122 条记录（同一批链路两端各读一次）、日期顺序违例 0。
* 12 项构建检查通过 12 项；四页汇报图绘图门失败 0 项。

## 6. 不要说的话

* 不要说「1808 小时是团队真实投入」- 那是上一版未经容量校验的计划读数，已被本轮重算取代。
* 不要说「Part 1 已提交」- 没有课程平台证据。
* 不要说「所有测试通过」- 阻塞栏里的四件事（Valhalla 实时路由、原生 Hermes、支付/退款工具、手机影子试用）本机未做。

