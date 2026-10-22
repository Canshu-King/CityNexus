# CityNexus 软件工程 2026 - 第三轮交付结果 (R3_RESULT)

生成 2026-10-23 02:14。计划文件 `Microsoft_Project/CityNexus_Software_Engineering_Plan.mpp` sha256 `4cd35d0725c2c5d3ab26cff11925015a4fa78fd52610abcb8ca0ce4918277e41`；重计划文件 `CityNexus_Plan_Recovery.mpp` sha256 `ec3e1a5c7b2b25b8063b17120a3c07f6c3b0c95a2abf70cdf392af79a6d6ada7`。

本轮只动课程交付的生成器、证据文件与展示资产：没有改 CityNexus 主产品代码，没有碰 Codex Revolution 分支，没有跑无关的历史全量回归。R2 已被独立验收的 Visio 自定义属性、Agent 核心流程与 Project 全量依赖三项修复按原样保留，并重新通过各自的门。

## 1. 三件产品级问题

### 1.1 人力容量：从「数学上正确、执行上不可能」到零超配

| 指标 | R2 被审时的值 | 现在实测 |
|---|---|---|
| 学生人工工时 | 1808 h（外审报告 §B-P0 读数） | **220.9 h** |
| 单人单周峰值 | 大量任务同日满负荷并行 | **19.9 h / 人 / 周**，声明可用 20 h |
| 超配人周 | 未做验收 | **0**，构建在出现任何一超配周时直接拒绝发布 |
| Agent 算力 | 与学生工时混在一起 | 两条 lane 设为 material 资源，只计价 7 次分派，**0 学生工时**；没有任何一行只靠 lane 却还带人工小时 |

做法：工时不再由「工期 × 8 小时 × 单位」倒推，而是每行显式写 `eff`（谁、几小时），单位由 `hours / (工期天 × 8)` 截断导出，构建用 Project 自己的 assignment Start/Finish/Work 复算每人每 ISO 周，并与声明可用工时比较。可用工时 20 h/周是**假设**，需要三位成员各自确认，`Evidence/STATUS_AND_OVERDUE.md` 与汇报第 4 页都这样写。

### 1.2 逾期与截止日语义：四把时钟分开，逾期清单全量给出

逾期未完任务 **14 行**（其中 6 行 0%、8 行部分完成），每行给出原定工期、实际进度、重预测日期，全部列在 `Evidence/STATUS_AND_OVERDUE.md`。外审按我上一版给出的读数点了 10 行；那 10 行全部仍在这 14 行里，多出来的是下面 §2 那个日期读取缺陷造成的低估。

| 时钟 | 含义 | 例 |
|---|---|---|
| planned finish | 引擎算出的计划完成日 | 9.3 -> 2026-09-30 |
| actual finish | 已经发生的事实完成日 | 24 行在状态日或之前 |
| forecast finish | 状态日之后按剩余工作日重排 | 9.3 -> 2026-10-27 |
| course deadline | 课程合同截止日，与计划里程碑分开 | Part 1 2026-10-02（已错过，事实记录）· Part 2 2026-11-06 |

M9/M10/M11/M12/M13 已改名为「预计就绪日」与「课程截止日」两种语义；**Part 1 是否真的提交仍未证实**，只能以课程平台记录为准，本轮没有任何一处宣称它已提交。

前瞻重计划：`CityNexus_Plan_Recovery.mpp` 只含 16 行未完工作与 3 个带日期里程碑，从 2026-10-23 起排，引擎算得完成日 **2026-11-04**，成本 $1099.552，0 超配、0 截止日违约、14 条依赖 0 违例——比 2026-11-06 的合同截止日早 2 天。

### 1.3 平板汇报版：新增，且原来的截图问题按机制修掉

新增 `Presentation/CityNexus_SE2026_Briefing_Deck.vsdx`：四页 16:9（13.333 x 7.5 英寸），56 个形状、4 条连接线，绘图门 **0 条失败**。正文最小字号 13 pt，并且门里新加了一条规则：任何带文字、尺寸小于该页字号下限的形状直接判失败，所以这张图不可能再退化成5.8 pt 的墨墙。四页分别是：系统概览、Agent 受约束的核心流程、进度与阻塞、分工与成本。

Project 视图 PNG 的根因是上一版抓的是「屏幕矩形」，Chrome 压在上面就照下来了。新版（`se_project_snapshot_r2.py`）改用 Win32 `PrintWindow(PW_RENDERFULLCONTENT)` 抓目标窗口自身的 DC，与 z-order 无关；并且以只读方式打开（文件系统层 chmod 只读），抓完比对摘要：`4cd35d0725c2c5d3` -> `4cd35d0725c2c5d3`，未改动。每帧还做非空白检查（颜色数 1098~2295，非白像素比例最低 0.160）。7 个视图全部由我肉眼看过，画面是 Project 自己的表格与甘特条，没有别的窗口。

命名与页数也按实测交代：`Briefing_One_Page.pdf` 已删除（它实际 12 页），同一份打印以 `Plan_Briefing_Print.pdf` 交付，实测 **12 页**；汇报 deck PDF 实测 **4 页**；A3 总览 `Briefing/previews/CityNexus_Plan_Briefing_A3.pdf` 确实是 **1 页**，但它不是汇报版，汇报版是上面那四页。`Task_Usage.pdf` 不再被引用：这台安装的 Project 里「任务使用情况」视图不存在（`ViewApply` 报「视图已经不存在」），所以那个文件不可能由本机产生，引用已删而不是补一个假文件。

## 2. 本轮自己发现并修掉的缺陷（不是外审点的）

**日期读取器把每个「工作日结束」的时刻推到第二天。** pywin32 返回 Project 的 `2026-09-09 17:00` 时挂的时区名不是本机时区，旧 `dstr()` 于是做一次 `astimezone()`，八小时把日期推到 09-10。屏幕上的表格写 9月9日，我所有从 JSON 生成的文档写 09-10。发现方式：把纯 Python CPM 与引擎逐行对拍时，两侧工期天数完全相同而日期系统性差一天。

影响与处置：读取器改为按 Project 返回的日历日直读，并写了自检；构建现在第一件事就是跑这个自检，不通过就不开工。修好后逾期行数从 10 变成 14（被掩盖的 4 行露出来），并且暴露出 yang 在 2026-W37 真实超配 21.2 h > 20 h——上一版的「0 超配」是这个偏移造成的假绿。该周靠重估两行九月的工时（2.2 10->9 h、2.3 7->6 h）解决，重排后依赖与关键路径全部重算，12 项检查仍全绿。同类偏移在里程碑视图与简报生成器里各有一处（把日期写成 00:00 会被 Project挪回上一个工作分钟），也一并改成工作时段内写入，并由各自的对拍验证。

## 3. 证据一致性（外审 §B-P1 与 §B-P2）

新增 `se_evidence_index_r1.py`，产出 `Evidence/EVIDENCE_INDEX.md` 与 `.json`：

* 逐个证据 JSON 记录字节数、sha256、生成时间、生成脚本，以及**它自称来自哪一版计划**；凡自称的来源摘要与磁盘上的现文件不一致就判 STALE 并拒绝。当前 3 个带来源摘要的文件全部 current。
* 跨文件比对同名事实：依赖数、日期违例数、M13 计划日、逾期行数、学生工时、超配人周——6 组事实，0 组不一致。
* 文档引用完整性：扫描交付树里 markdown 引用的相对路径，逐条解析；不可解析 **0** 条。两类文件按名字排除在扫描之外并写在索引里：外审原件（引文，不许改）与本轮的两份新报告 `R3_RESULT.md`、`EVIDENCE_INDEX.md`——它们的存在由本轮构建本身证明，不能自证。上一版被点名的三处悬空引用（`se_review_package_r2_result.json`、`logs/se_brief_r2.log`、`Task_Usage.pdf`）现在都不再被引用。
* `se_plan_cpm_r2.json` 已从当前计划重算（links 61、状态日、容量表都在里面），不再是上一轮的中间残留；它与引擎的日期差异不再被抹平，而是在 `Evidence/PLAN_RECONCILIATION.md` 里逐行摊开：静态 2026-10-30、引擎 2026-10-23、重计划 2026-11-04，17 行关键链上两侧跨度都等于声明工期，差在哪一步、差几天，全部列成表。

## 4. 仍然没有证明的事（本轮不做假动作）

1. **Part 1 是否提交**：要课程平台记录，本机拿不到；计划里 10.1 与 M10 按「已错过」记，不宣称提交。
2. **成员可用工时与分工**：20 h/周与三人分工是课程计划提案，git 只有一个提交身份，需要本人确认。
3. **Visio 形状拖动时连线是否跟随**：结构面已证（Shape Data 579/579 属性、connector glue 148/148、重开/编辑/恢复 PASS），实际拖动的观感仍需在平板上人工看一次。
4. **PrintWindow 与屏幕像素的对照**：本机 SetForegroundWindow 被前台锁拒绝，抓屏时确有 7 个窗口压在上面，所以「与屏幕一致」这一条没做成决定性验证；能给的证据是窗口自身 DC 的渲染、非空白统计与肉眼检查。
5. **真机用户流程**：Valhalla 实时路由未配置、原生 Hermes 缺失、支付/退款无真实工具、手机与 PWA 影子试用未做——这四条写在汇报第 3 页的阻塞栏里，没有粉饰。

## 5. 复现清单

按顺序执行即可重建本轮全部产物（都在 `live_checks/`，随包交付）：

```
python se_plan_cpm_r1.py            # 静态前置门 + 容量普查
python se_project_build_r2.py       # 建 .mpp，12 项检查，零超配才发布
python se_project_recovery_r1.py    # 前瞻重计划 .mpp
python se_plan_status_r1.py         # STATUS_AND_OVERDUE.md
python se_milestone_view_r2.py      # Milestone_Timeline.pdf（只读打开，摘要不变）
python se_project_brief_r1.py       # Plan_Briefing_Print.pdf
python se_visio_build_r1.py && python se_visio_proof_r2.py   # 四张工程图与读回证明
python se_deck_r1.py                # 16:9 汇报四页
python se_project_snapshot_r2.py    # PrintWindow 截图，只读，摘要自证未变
python se_evidence_reconcile_r1.py  # PLAN_RECONCILIATION.md
python se_evidence_docs_r1.py       # README / SOURCE_MAPPING / AUTOMATION_VERIFICATION
python se_evidence_index_r1.py      # EVIDENCE_INDEX.*（STALE 或悬空引用即拒绝）
python se_review_package_r2.py      # MANIFEST.sha256 + 复审包，zip 往返校验
```

压缩包自身的 sha256 不写在包内文件里（zip 不能自证），随提交信息给出。

