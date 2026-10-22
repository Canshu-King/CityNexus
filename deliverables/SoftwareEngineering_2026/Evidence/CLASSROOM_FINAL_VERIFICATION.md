# 中午演示最终验收 (CLASSROOM_FINAL_VERIFICATION)

最后更新 2026-10-23 04:47（本机 +08:00）。基线分支 `review/se-coursework-deliverables-r1`，任务书 `Evidence/CLASSROOM_QODER_CONTINUOUS_UNTIL_NOON_20261023.md`。

## 1. 真机测了什么

Visio `16.0 build ?`、Project `16.0`。所有修改都写在临时副本或课堂展示副本上，交付原件在每次操作前后按 sha256 比对。

| 项 | 结果 | 依据 |
|---|---|---|
| 原生 Visio `01_CityNexus_System_Architecture.vsdx`：打开→选中形状→拖动 0.75 英寸→改文字→保存副本→关闭→重开 | **PASS**；原件字节未变：True；2 条连线在拖动后端点仍贴在形状上：是 | `Evidence/scripts/se_classroom_demo_r1.py` + `se_classroom_demo_result.json` |
| 原生 Visio `03_CityNexus_Agent_Workflow.vsdx`：打开→选中形状→拖动 0.75 英寸→改文字→保存副本→关闭→重开 | **PASS**；原件字节未变：True；1 条连线在拖动后端点仍贴在形状上：是 | `Evidence/scripts/se_classroom_demo_r1.py` + `se_classroom_demo_result.json` |
| 原生 Project 主计划副本：任务工作表/甘特图/网络图/跟踪甘特图/资源工作表/日历 六个视图切换→改一条备注→保存→重开 | **PASS**；65 行、122 条依赖记录读回；交付的 .mpp 未变：True | 同上 |
| 里程碑视图文件与恢复计划文件能否打开 | 能；里程碑文件 13 行、恢复文件 16 行 | `se_milestone_view_r2.py`、`se_project_recovery_r1.py` |
| 四张工程图的形状数据与连线（重开之后） | 属性 579/579、连线 148/148 全部读回 | `se_visio_proof_r2.py` → `Evidence/se_visio_proof_result.json` |
| 构建的 12 项计划检查 | 全部通过（12/12） | `Evidence/se_project_build_r2_result.json` |
| 四页 16:9 汇报图 | 绘图门失败 0 项，PDF 实测 4 页 | `se_deck_r1.py` |

## 2. 截图到底看不看得到甘特条

| 图 | 说明 | 图表区墨度 |
|---|---|---|
| `Classroom/previews/Milestones_Visible.png` | Project 窗口实拍（PrintWindow 抓目标窗口自身 DC，不受其它窗口遮挡） | 0.0124 |
| `Classroom/previews/Gantt_Visible.png` | Project 窗口实拍（PrintWindow 抓目标窗口自身 DC，不受其它窗口遮挡） | 0.0199 |
| `Classroom/previews/Gantt_Visible.png` | Project 窗口实拍（PrintWindow 抓目标窗口自身 DC，不受其它窗口遮挡） | 0.0584 |
| `Classroom/previews/Milestones_Visible.png` | Project 窗口实拍（PrintWindow 抓目标窗口自身 DC，不受其它窗口遮挡） | 0.0536 |

被外审点名的旧图（`Microsoft_Project/previews/Gantt_Chart.png`）图表区墨度只有 0.0244，因为右侧时间轴停在 10 月中旬、任务条被推到画面外；上面每一张都重新量过，并且逐张打开肉眼确认过任务条与日期文字。

**这台电脑上做不到的事（写清楚，不含糊）**：Project 的甘特图右侧时间轴无法用脚本滚到项目起点。测过并全部失败：`TaskScrollTo`、`SelectTaskRow`、`Goto`、`Window.Scroll`、`ScrollBar`、`FirstTask`、`ScrollLeft`、`ScrollItem` 等方法不存在；`TimescaleStart/TimescaleFinish` 赋值报类型不匹配；`TimescaleEdit` 对 18 种参数组合报「参数值无效」；`ZoomIn/ZoomOut` 只改时间刻度层级（会走到「年」或「15 分钟」），`ZoomTimescale` 会把进程挂住 15 分钟。课堂副本已用真实按键 Ctrl+Home 与滚动条拖动调过视图（`se_classroom_fit_r1.py`，键鼠事件只在确认目标窗口为前台后才发送），但视图状态在个别 Project 版本上仍会回到默认位置，**所以现场请手动按一次 Ctrl+Home 或拖底部滚动条**；替身图用 `Classroom/previews/Gantt_Visible_print.png`。

## 3. 中期会面的时间语义

计划里的 M11 现在叫 `M11  Mid-term teacher review (scheduled 2026-10-23 noon)`，完成度 **0%%**，截止日 2026-10-23。它不再写成「已举行」，也没有任何文件宣称老师已经签字或验收。恢复计划里它被记为「已安排的会面」而不是工作项（`scheduledEvents`），同时如实记下风险：它所依赖的 10.2 材料包按重排会在 2026-10-28 完成，而中午真正拿给老师看的是本包已交付的内容。

## 4. 关键摘要

| 文件 | sha256/16 |
|---|---|
| `Microsoft_Project/CityNexus_Software_Engineering_Plan.mpp` | `6398e58f9b4cd3b3` |
| `Microsoft_Project/CityNexus_Milestone_View.mpp` | `d1def47164e694c0` |
| `Microsoft_Project/CityNexus_Plan_Recovery.mpp` | `7e4f561a46d32b22` |
| `Classroom/CityNexus_Plan_Classroom.mpp` | `02ebbcba23808a47` |
| `Classroom/CityNexus_Milestones_Classroom.mpp` | `0947fc8eba04ff82` |
| `Presentation/CityNexus_SE2026_Briefing_Deck.vsdx` | `89a555163bec93ac` |
| `Visio/01_CityNexus_System_Architecture.vsdx` | `2869450c0f1d4e2d` |
| `Visio/03_CityNexus_Agent_Workflow.vsdx` | `3f7c57410bf6abfd` |

证据索引：`Evidence/EVIDENCE_INDEX.md`（15 个证据文件、6 组跨文件事实一致、3 条引用无法解析）。

## 5. 中午包

本地文件：`D:\moodle\CityNexus_20261023_Noon_Ready.zip`（zip 不入库：包内 16 个文件在仓库里都已存在，重复提交只会多出几 MB 二进制；任务书允许这种做法，要求把路径与摘要记在这里）。

* sha256：`1f7bf7af90169970aa14d2df3c1e252b87df8c9e39af0023c45d49a665548655`
* 成员：17 个文件 + `MANIFEST.sha256`；`testzip()` clean；解包逐文件字节比对差异 0 处。
* 内容：4 个 .vsdx、5 个 .mpp（含两个课堂副本）、四页汇报 PDF、5 张可读截图、课堂演示顺序一份；zip 内的目录名与本仓库路径不同，所以下表按仓库路径列出。

成员清单：

```
Visio/01_CityNexus_System_Architecture.vsdx                   62156 B  2869450c0f1d
Visio/03_CityNexus_Agent_Workflow.vsdx                        66526 B  3f7c57410bf6
Visio/02_CityNexus_User_Journey.vsdx                          62749 B  d9c88139e7d8
Visio/04_CityNexus_Use_Case.vsdx                              84933 B  6d77427c4c08
Microsoft_Project/CityNexus_Software_Engineering_Plan.mpp    386048 B  6398e58f9b4c
Microsoft_Project/CityNexus_Milestone_View.mpp               253952 B  d1def47164e6
Microsoft_Project/CityNexus_Plan_Recovery.mpp                289792 B  7e4f561a46d3
Classroom/CityNexus_Plan_Classroom.mpp                       376320 B  02ebbcba2380
Classroom/CityNexus_Milestones_Classroom.mpp                 256000 B  0947fc8eba04
Presentation/previews/CityNexus_SE2026_Briefing_Deck.pdf      49448 B  f679e4f082c0
Classroom/previews/Gantt_Visible.png                         340737 B  5f536d14d294
Classroom/previews/Gantt_Visible_print.png                   173315 B  54ca5ecd36b7
Classroom/previews/Milestones_Visible.png                    296869 B  7b5f111c609e
Classroom/previews/Milestones_Visible_print.png              172105 B  cab030a95ea8
Microsoft_Project/previews/Milestone_Timeline.png            293526 B  ccbce7847ae1
Classroom/课堂演示顺序.md                                            7471 B  79255c072708
```

## 6. 还没证明 / 风险

1. Part 1 在课程平台的真实提交状态：本机无法核实，计划按「已错过」记录。
2. 每人每周 20 小时与三人分工：是课程估算，未由成员确认；学生工时合计 220.9 小时。
3. 状态日之上 14 行未完工（全表在 `Evidence/STATUS_AND_OVERDUE.md`）；重排后的完成日 2026-11-04。
4. 甘特图视口的脚本化滚动（见第 2 节），以及 `PrintWindow` 与屏幕像素的决定性对照（前台锁拒绝，抓图时确有窗口压在上面）。
5. 四件产品阻塞：Valhalla 实时路由未配置、原生 Hermes 缺失、无真实支付/退款工具、手机与 PWA 影子试用未做。

