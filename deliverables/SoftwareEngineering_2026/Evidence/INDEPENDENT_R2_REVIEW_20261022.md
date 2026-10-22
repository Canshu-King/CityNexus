# CityNexus 软件工程课程交付 R2 独立外审（2026-10-22）

## 范围与取证

审查对象：上传的 `CityNexus_SE2026_review_r2_20261022.zip`，内含 136 个文件；打包说明对应课程交付分支 `review/se-coursework-deliverables-r1` 的 `21aa16e68ad1951588739993d338f11dac9a1bab`。审查时 GitHub 分支已经前进一个提交到 `a493ac0c50d1840db1a30dbf5a63b4b6fd9338ac`，新提交自称重新导出 PDF/PNG。以下有关截图的判断严格针对**上传 ZIP**；GitHub 较新二进制图须重新视觉检查，不能用旧版的图替最新成果定论。

独立校验：ZIP CRC 通过，135 条 `MANIFEST.sha256` 对 135 个其他文件全部匹配；ZIP SHA-256=`02f693327f5b04dbb32ccb4c642a16e37ca6c6d84f74a97995e61ddec426ad33`。本审查环境不能启动 Windows Project/Visio COM，所以应用内保存/重开/关键路径和依赖传播仍以 Qoder 的构建日志为证，不虚称本审查已亲自用桌面 Office 复现。

## A. 上轮三项主要缺陷

1. **Visio Shape Data 已独立确认修复。** 直接解压 4 个 .vsdx 的 page XML，计数为：01=93，02=118，03=157，04=211，共 579 个非空 `Prop.*.Value`；连接端点记录分别为 48、68、86、94，共 296，对应 148 条双端连线。第 04 图确实已经拆为两页。Qoder 记录的 Windows 重开、编辑、恢复以及 148/148 glue 均为 PASS。判定：结构修复验收通过；形状实际拖动时是否跟线仍未在独立环境复现。
2. **Project 前置关系修复证据充分，但非直接 COM 复现。** `Evidence/se_project_build_r2_result.json` 显示 61 条独立链接，`Task.TaskDependencies` 双端回读 122 条记录，missing/mismatched/violations 均为空、非 ASAP 强制约束为 0，FF/FS/SS 扰动复原成功；发版后回读 65 行和 122 条记录，0 日期违例。判定：接受“生成器/回读一致”，不等于已审定整体计划可执行性。
3. **Agent 图关键语义已纠正。** 当前 GitHub `backend/app/agent/gateway.py` 的 `dispatch` 在未知工具时先 404，`record_audit` 在白名单检查之后；新 `03_CityNexus_Agent_Workflow` 图已经更正，并单独画出 read/replan/typed 三族路径。判定：上次指出的错误解决；逐 handler 的最新动态代码仍需版本化核查。

## B. 新发现：优先修复

### P0 资源容量（不是 arithmetic 校验可以替代的）
`se_project_build_r2_result.json` 的静态前置检查及资源汇总为人力 **1,808 h**，其中 Yang=756h, WangJR=448h, WangXY=604h。2026-09-07 至 2026-10-24 共约 35 个工作日，按 8h/日、三人每人 100% 的标准总容量上限只有 **840 h**。整体约 215%，三人单独分别约 270%、160%、216%。这不是“人工真实已花工时”；大量满负荷任务在同一日并行，`se_project_build_r2.py` 未做资源超配验收/leveling。数学成本 `1808h × $20 + compute charges = $36202` 可以成立，但**资源计划不现实**。

**要求：** 先征询组内实际可投入时间，基于可解释的每周上限重估人工 effort，Agent 算力另计并明确不等于学生工时；对资源超额分配建立机器 gate（每日/每周 max units 或 Project Overallocation census）。调整 effort、units、计划并真实重算依赖/关键路径，不能只修改费率、隐藏资源超配或把人工挪成 Agent。“历史实际完成”的工时与“课程估算”分列，避免虚构历史。

### P0 逾期进度和截止日语义
`rows` 中 **10 个**非摘要/非里程碑任务满足 `pct<100 AND finish<2026-10-22`：5.2、5.3、6.5、8.2、9.3、9.4、9.6、10.1、10.2、11.2。其中 **4 个 0%**（5.3/9.4/9.6/10.1），另 **6 个部分完成**；文档只强调 4 个会让人误以为仅有 4 个逾期。M9 “System test complete” 于 10-07 但 0%；M10 “Part 1 deadline (recorded as missed)” 于 09-30、0%，真实截止日却为 10-02；M12 “Part 2 submission deadline” 预测 10-24 而合同截止 11-06。报告的“6 met / 0 breached”**仅是计划日期早于 Deadline 字段，不是证据证明作业已经提交**。

**要求：** 明确区别 `planned_finish` / `forecast_finish` / `actual_submission` / `course_deadline`；Part 1 状态标为“课程平台提交未核实，风险/待人工核查”，绝不凭计划日期宣称已完成。全面列出 10 个逾期未完任务，重新作一版状态日之后的前瞻计划，保留原始事实快照。里程碑名区分“预计就绪日”与“实际截止日”。

### P1 独立证据快照过期
包内 `Evidence/se_plan_cpm_r2.json` 是旧的中间结果：`links_total=57`，`project_finish=2026-10-21`；同期 `Evidence/se_project_build_r2_result.json.static_preflight` 是 61 条、静态 `project_finish=2026-10-30`，发布 .mpp 的 `shippedFinish=2026-10-24`。三者不能在文档中被混作一个真相。请重算/删除有歧义的旧文件，精确解释为什么纯 Python CPM 和 Project 日历不同时，不要只把最终数字改成一样。打包验收加跨 JSON 的 schema / version / source SHA / 生成时间校验。

### P1 汇报图和截图可读性
上传包 `Microsoft_Project/previews/*.png` 的实际画面前景是 **Chrome CityNexus 窗口，遮挡 Project 表格和甘特图大量内容**（`Gantt_Chart.png`、`Network_Diagram.png`、`WBS_Task_Sheet.png` 等均受影响）。`Briefing_One_Page.pdf` 实际 **12 页**，`Gantt_Chart.pdf` 24 页、`Network_Diagram.pdf` 41 页、`Milestone_Timeline.pdf` 9 页；不要以文件名宣称一页。`Briefing/previews/CityNexus_Plan_Briefing_A3.pdf` 确实是 1 页，但抽样文字字体中位数仅 **5.8pt**；Agent 图中位数约 6.8pt，平板横屏不放大无法讲解。Visio gate 的“0 重叠”并未检测到上述“看不清”的用户问题。

GitHub 最新 `a493ac0` 已声称重新导出截图和视图 PDF，请首先复验最新版，不要不必要地重做已完成修复。凡截图必须确保 Project 窗口真正前台且无遮挡；再检查导出 PDF 的真实页数。保留工程全图，但新增 16:9 汇报版：1 张可读架构概览、1 张极简 Agent 工作核心流程、1 张进度/阻塞概览和 1 张资源分工页（正文建议 12pt+；页脚可较小），而非坚持把所有细节挤进一张 A3。详细原生工程保留。

### P2 文档指向包内缺失文件
`REVIEW_BRIEF.md` 让读者去找 `Evidence/se_review_package_r2_result.json`，但文件不在上传包。 `REVISION_2.md` 提到 `Evidence/logs/se_brief_r2.log`，未包含；文档提到 `Microsoft_Project/Task_Usage.pdf`，压缩包中也没有。打包时检查每个被引用的相对路径是否真实存在，或改为直接记录可核查的 SHA 和理由。

## C. 源码范围与教学语义

课程图基于该 review 分支的一份代码快照；`commander/control` 与 Codex 的 `gpt/revolution-r33-open-world-journey-adaptation` 是独立推进的开发线，不应将尚未整合的能力统一涂蓝叫作现有主产品。“存在代码/单元测试”与“真机用户已经成功操作”需要区分证据等级。M8 “Integration line stable” 比 M4 “Core backend running end to end” 早，可能是真实并行，请在图注注明 M8 是**当时集成线的阶段状态**，而不是整个 CityNexus 已经最终整合稳定。

学生具体分工和投入时间未经各成员确认，仅可作为课程计划提案。Part 1 实际提交情况只能以课程平台记录为准。

## D. 给 Qoder 的闭环验收

1. 本轮 **只修课程交付生成器、证据文件及展示资产**，不要顺带重构主产品，也不动 Codex Revolution 分支；修复不推翻已验证的 Visio/Project 技术能力。
2. 校准人力工作量，提供每名成员按周的 `available_hours / assigned_hours / overallocated_hours`，超配应为零或显式解释、获得确认；成本只做规划估计。
3. 全量依赖 61/61、双端 122/122、0 日期冲突、0 强制约束，扰动/回滚/重开仍通过；把状态日/完成记录/截止日三者区别开，列出所有未完且逾期工作。
4. 继续保持 Shape Data 579/579 和 connector glue 148/148，不要为了做大字删除关键信息；分层大图保留，另产演示图。
5. 重新输出无遮挡截图和真正可读的单页/少页汇报 PDF，用本机 PDF 渲染后的 PNG 人眼审查，不要以导出函数成功代替可读性。
6. 清理失效证据/悬空文档引用，提供新的 manifest 与最新 HEAD SHA。完成后交付一份包含实际修复、仍然未证明的地方的 `R3_RESULT.md`，无需重跑整个产品系统历史回归。

结论：R2 的工程文件技术交付明显进步，上一轮三个 blockers 的核心修复可接受；**项目排程现在是技术正确但容量不可信，展示层也未达到平板汇报质量**。下一棒应是“可执行计划 + 人能看懂的展示”，不是新一轮无限自证。