# CityNexus 课堂演示紧急纠偏：真正可读的 Visio + Microsoft Project 原生文件

## 用户反馈（最高优先级）
用户已经在 Windows Project Professional 与 Visio **真实打开**了前一轮推荐的文件，并给了两张实际截图。结论是：**目前的工程版完全不适合给软件工程老师看**：
- `Visio/03_CityNexus_Agent_Workflow.vsdx` 文字与 5 层多路连线挤满屏幕，每个框含 `main.py:14169,1367`、`runtime.py:238`、`gateway.py:359` 等源码行号，中文授课现场几乎不可读。来源行号不是流程内容，应保存在 Shape Data 的 SourceRef/附录，不要显示在方框正文。
- `Microsoft_Project/CityNexus_Software_Engineering_Plan.mpp` 实机截图的 65 行任务全展开、任务名称列过窄、行高几乎上百像素，资源名称包含名字/学号/角色全文/资源分配百分比（如 `[38%]`），资源文字越过表格列压到右侧甘特区，任务进度条在视口外。此截图不是可用的演示页。
- R3 的 `Presentation/CityNexus_SE2026_Briefing_Deck.vsdx` 虽然有 4 页，但主要是英文大段文字与开发计量字段，不是解决“老师一眼看懂”的免疫证明。

**上次 GPT 推荐直接打开 `03_Agent_Workflow.vsdx` 是错误选择。不能再把“VSDX / MPP 能打开、工具测试绿”当成课堂展示通过。**

## 紧急交付（最小范围，禁止重做源计划）

### A. 另造两张真正适合讲解的 Visio 原生图
保留已生成 4 张详细工程图，**另新增**：
- `deliverables/SoftwareEngineering_2026/Classroom/Teacher_01_System_Overview.vsdx`
- `deliverables/SoftwareEngineering_2026/Classroom/Teacher_02_Agent_User_Flow.vsdx`

必须由真实 Windows Visio COM/MCP 建立，并确保中文字体（微软雅黑/等线）、一页横向、16:9 或 A3、形状为可编辑原生对象。

Teacher_01：6～8 个简短节点，展示 `用户→前端地图/对话→后端API→Agent与工具→路线/地点数据→行程结果与状态存储` 以及必要的方向关系。每个框**不超过 2 行中文**；内部细节（框架版本、API 数、工具数、文件与行号）移入 Shape Data 或附页。

Teacher_02：不超过 9 个节点、完整可闭合的一个核心用户场景：`用户输入需求→Agent理解→调用地点/路线工具（可选外部服务请明确标记）→生成方案→展示→是否修改?→继续调整/确认→保存结果`。条件分支标注“是/否”。如实际代码需要用户批准才执行修改，必须画出确认门，不能画成 Agent 自行执行；未验证的实时供应商不能涂成已实现。每框 ≤18 个汉字、正文不小于 16pt、标题 ≥22pt，箭头不得穿过文字，不得把无数详细 handler 当作主图。

可接受技术溯源必须**藏在形状数据**或 `Teacher_Source_Map.md`，不要出现在可见标签；图上最多一句“根据 CityNexus 当前已验证架构整理”。

### B. 另造一个课堂版 Project（真 .mpp，首屏真实看见任务条）
- 输出 `deliverables/SoftwareEngineering_2026/Classroom/Teacher_03_Project_Overview.mpp`
- 必须从已核对的 `Microsoft_Project/CityNexus_Software_Engineering_Plan.mpp` **复制**，不删除真实细节任务/依赖、不改任务日期、人力、真实状态、课程截止日。只改展示副本的视图状态：
  1. `视图→甘特图`；`视图→数据→大纲→大纲级别 1`（如顶层太少可 2），只显示 8～12 个大的工作阶段；
  2. 右侧时间轴**缩放到整个项目** 2026-09-07～2026-11-06，任务摘要条和里程碑菱形必须在一个 1920×1080 屏幕内真实可见；
  3. 隐藏 `资源名称` 列、`任务模式` 等无关列，任务名称列适当加宽、避免每行几十厘米高；显示 `任务名称/开始/完成/%完成` 即可；
  4. 对甘特条使用 `甘特图格式→条形图样式→文本` 清除 `资源名称`（尤其右侧栏），**不可删除真实资源或 assignments**；如仍需职责可另建三行清晰的资源分工展示。
  5. 清理顶部冗余时间线视图，但保留可讲的状态日期与进度条。
- 不要再用 `PrintWindow` 非空像素统计替代视觉验收。实际在 Windows Project 的 1366×768 或 1920×1080 屏幕中打开文件，截**整屏**；老师能在三秒内认出至少六条有意义的任务横条、能读清任务名和几处里程碑，且没有大段英文越界，才能 PASS。
- 如果 Project 本机 API 不能保存滚动/大纲级别，则保留可信的真实 `.mpp`、录制 **三步操作**（单独用户可重现）而不是继续用不存在的 COM 属性自证。绝不以静态仿制甘特图冒充原生 Project。

### C. 用真实课堂成果验收，不准再拿原来的“结构全绿”说事
- 附 `Classroom/Teacher_01_System_Overview.png`、`Teacher_02_Agent_User_Flow.png`、`Teacher_03_Project_Overview.png`；
- `Classroom/TEACHER_DEMO_START_HERE.md` 只写打开这三个文件的顺序、30/30/60秒说辞，以及兜底步骤；
- 截图必须实际检查：无源码行号外露、无数值串压住正文、无“资源学号职责[38%]”压满图、不小于目标文字大小、没有交叉密集连线，Visio 原生框可编辑、Project 摘要条可见；
- 输出 `Classroom/TEACHER_READABILITY_VERIFICATION.md` 说明每个文件的大小、页数、已核实真机编辑结果、对照截图、失败项，包含新旧前后对比；
- 保留完整技术工程图与原始 .mpp 作附录；不去动主产品或 Revolution 分支。

**停止条件**：当三个原生教学文件真实可打开并肉眼看懂就停止；不要扩到新报表或重复源码全量测试。此事首要指标是用户现在打开就能给老师讲，而不是自动化跑绿。

### 快速手工兜底（Qoder 如遇 COM 视图障碍直接按）
Project 里在原计划窗口先“另存为”一份教学副本，`视图→大纲→级别1`、`视图→缩放→整个项目`、隐藏资源名称列，`甘特图格式→条形图样式→文本` 去掉资源名称标签。确认右侧真有横条才截图；源 `.mpp` 勿改。

**本任务替代早前推荐教师直接开详细的 `03_CityNexus_Agent_Workflow.vsdx`。**
