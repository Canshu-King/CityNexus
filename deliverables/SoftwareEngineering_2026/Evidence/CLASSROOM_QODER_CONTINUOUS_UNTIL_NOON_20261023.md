# Qoder：10月23日中午前连续执行令（CityNexus 软件工程 Visio + Microsoft Project）

**发布时刻：2026-10-23 约 04:02（北京时间 UTC+08:00）**
**现场截止：2026-10-23 12:00（北京时间 UTC+08:00）**
**硬冻结建议：11:00 开始，只允许补救阻断现场打开的故障。**

## 一、你要执行的事情，不要重新规划

本令是用户要求：**让 Qoder 将课程 Visio 与 Microsoft Project 工作持续推进到 10 月 23 日中午**。不是让你通宵证明系统 green，也不是改 CityNexus 主产品。已完成的成果应该坚决保留。

仓库：`Canshu-King/CityNexus`；仅在 `review/se-coursework-deliverables-r1` 执行课程交付修正。先 `git fetch` 并核对当前 HEAD；切忌使用过时本地文件覆盖 GitHub 最新版。自本任务书读取起以远端 HEAD 为基线，检查不影响课程交付的并行改动。

先读取两份已经存在的真实外审：
- `deliverables/SoftwareEngineering_2026/Evidence/INDEPENDENT_R2_REVIEW_20261022.md`
- `deliverables/SoftwareEngineering_2026/Evidence/CLASSROOM_R3_LAST_MILE_20261023.md`

和证据：
- `deliverables/SoftwareEngineering_2026/Evidence/R3_RESULT.md`
- `deliverables/SoftwareEngineering_2026/Evidence/CLASSROOM_20261023_README.md`

R3 已有 4 张 Visio 工程图（.vsdx）、4 页横屏演示（.vsdx + PDF）、主计划/里程碑/恢复版等 .mpp、Project 自动化修改/保存/重开记录。**禁止推倒重来**。

## 二、持续执行机制

1. 按下面优先级直接干，能决定的低风险细节自主决定，不要每一步等用户回复。
2. 每完成一个阶段，保存可用版本；记录 `CHECKPOINT.md` 中的时间（+08:00）、检查项、变更文件、实际证据、Git SHA、下一阶段。这里的“持续”是连续推进**有用的**任务，不准通过无意义死循环、空等、重复绿色测试装作正在工作。
3. 当前 Qoder 会话如果受上下文、配额、进程退出、IDE 睡眠或工具断联影响，必须留下状态接力文件；不能声称离线仍在运行，也不能假装 GitHub Commit 会自动重启 Qoder。
4. 现场验收以能用 Windows **真正打开 Visio/Project 原生文件**、平板能看清图为首要成功条件。不得只用文件大小或 PNG 作为成功。
5. 不修改 `commander/control` 或 Codex 的 `gpt/revolution-r33-open-world-journey-adaptation`；不要改用户实际产品、真实提交历史、课程合同截止日、任务实际完成证据。不要使用 `--force` push。
6. 若发现 09:30 前所有必要修正均已完成，转为冷备演示：反复从干净目录**只读**抽检可打开性、文件存在、分辨率与离线展示，并准备应急资料；不要因“还没到 12 点”发明不必要的开发任务。

## 三、时间盒任务安排（全部北京时间）

### P0-A：04:05～06:00 Project 第一屏必须看到甘特图任务条
- 原生 `Microsoft_Project/CityNexus_Software_Engineering_Plan.mpp` 作为证据基线，不改其任务、进度、工时、前置关系、成本、预测完成时间。
- 在**临时展示副本**里设置甘特图视图：项目整体缩放至 2026-09-07 ～ 2026-11-06（或 Zoom to Entire Project），WBS 折叠或只显示关键摘要；表格列控制为任务名称、开始、完成日期、%完成；取消冗长资源名称的自动折行占宽。
- 另对 `CityNexus_Milestone_View.mpp` 做相同视图调整，至少能同时看到早期和未来里程碑；不用把 13 个里程碑挤到看不清。
- 用实际 Project 目标窗口抓两张无外部应用覆盖且**右侧有任务条**的截图，放在课程交付下 `Classroom/previews/Gantt_Visible.png`、`Classroom/previews/Milestones_Visible.png`；人工打开图片检查文字和条形可读，不能只测非白色像素。
- 两张缩略预览+真实 Office 应用截图须内容一致；无法做出可靠截图时改用实机 Project 的清晰 PDF 演示视图，并准确写原因，不能用手工图冒充软件截图。

### P0-B：06:00～07:00 中期汇报日期措辞修正
- 老师会面为 `2026-10-23 12:00 +08:00`，在此之前**绝不能写「已举行 / held today / 已验收」**。
- 对课堂文件使用 `Mid-term teacher review | Scheduled: 2026-10-23 noon`，用一行说明“这是计划会面，不等于老师已经签字或评价”；如正式 .mpp 的旧 M11 名称受历史约束，仅修改展示副本或解说文字，不冒险重写已经验过的计划事实。
- `Part 1` 的课程平台提交状态保持“未核实”；成员 20 h/周和 220.9 总工时仅称课程估算；14 个逾期未完任务和 2026-11-04 恢复预测不能隐瞒。不要把计划完成日期说成实际完成。

### P0-C：07:00～08:30 双软件真实教学演示验收
- Windows Visio：打开 `Visio/01_CityNexus_System_Architecture.vsdx`、`Visio/03_CityNexus_Agent_Workflow.vsdx`，实际可见、对象编辑，另将编辑保存至**副本**、重新打开；确认原件摘要未变。
- Windows Project：打开主计划 .mpp 与展示副本 .mpp，现场可见甘特图，切换 WBS/里程碑/任务网络图，复制副本做一处备注修改→保存→关闭→重开；确认任务 65 行、61 链接/122 端点未丢失，原件未更改。
- 记录真实验证日志；没有启动桌面程序就不得报已验证。不要用截图冒充 `.mpp` 文件，也不要把用户电脑不具备 Visio/Project 许可的问题掩盖。

### P1-D：08:30～10:00 演示材料和中文稿
- 维持已有 `Presentation/previews/CityNexus_SE2026_Briefing_Deck.pdf` 的**四页 16:9**，核实 PDF 真实页数为 4，文字清楚。
- 新增 `Classroom/课堂演示顺序.md`：Visio 架构图 30s → Visio Agent 工作流 30s → Project 甘特图 40s → Project 里程碑/剩余工作 20s；每段附 **实际打开路径**和 1～3 句浅显中文讲稿。
- 提供三套备用：`原生 Office`、`离线 PDF/PNG`、`小组同学接替讲稿`；使平板不用连网也能演示。
- 内容短而真，不做新产品功能、不扩展新流程图数量。

### P0-E：10:00～11:00 全封包验证 + 上传
- 整理 `Classroom/CityNexus_20261023_Noon_Ready.zip`（或如果仓库二进制包过大，只在本地生成 zip，把当前原生文件链接和 SHA 记入 README）：
  1. 关键两张 Visio .vsdx + 另两张备用 .vsdx；
  2. 主计划 .mpp + 里程碑 .mpp + 恢复计划 .mpp；
  3. 四页 PDF + Project 两张可读截图/导出视图；
  4. `课堂演示顺序.md` + `CLASSROOM_FINAL_VERIFICATION.md`。
- 用 manifest 复算完整性；检查所有相对路径、独立预览与实际原生文件相匹配；重新打开两个软件检查副本保存功能；确认文件可脱网使用。
- 在 `Evidence/CLASSROOM_FINAL_VERIFICATION.md` 中说明: 真实测试了什么、哪些未测试、关键工程 SHA、Git Commit SHA、最后更新时间、会遇到什么风险。Push 到课程分支；不要误发到其它两条产品分支。

### 11:00～12:00 冻结与就绪
- 11:00 起禁止改需求、升级依赖、调整图的语义或大幅改 Project 原计划。除非发现原生文件无法打开或重要预览完全不可见。
- 持续检查“可打开 / 可投屏 / PDF 平板离线 / 小组讲解稿完整”的 readiness checklist。最终交付状态分为 `READY`、`READY_WITH_LIMITATIONS` 或 `BLOCKED`，如实标注。
- 最晚于 11:15 发布最终可用 Git SHA、README、可下载交付位置。11:15～12:00 只做演示前的只读查验和必要补救，不要继续修改 GitHub 中已经冻结的版本。停止时刻不晚于 12:00 +08:00。

## 四、失败时的决策

- 没有足够时间：优先保留两款**原生文件能打开**，其次 4 页 PDF 和真实甘特图截图，最后才是美化或补充证据。
- 导致复现失败的脚本或 Office COM 异常：在专项日志写原因，尝试一次窄修；不能因为非关键小测试失败而阻断课堂展示。
- 截图可能被 Chrome 覆盖/右侧空白：不得重用旧错误截图，也不许贴假条形图。转用 Project 自身导出并标明来源。
- 不要求不必要的对外真实供应商调用、Agent 实时旅行演示、线上密钥配置，课程 Office 演示不需要这些。
- 会面时间以用户口头说的**10月23日中午**为准，不把该时刻写作已完成的事实。

## 五、回执

一旦两个 P0 完成，就在本任务书旁添加 `CLASSROOM_CONTINUOUS_EXECUTION_RESULT.md`，用最少的中文汇报：原生 Visio PASS/FAIL、原生 Project PASS/FAIL、截图是否能看到真正甘特条、里程碑时间措辞、4页 PDF、文件路径、SHA、尚存障碍。

此指令**不会自行唤醒或维持 Qoder 的本地会话**：要由操作者在已经打开的 Qoder 里读取并运行。只有在本地 Qoder 确实运行、工具和网络可用的情况下，才谈得上“持续推进到中午”。
