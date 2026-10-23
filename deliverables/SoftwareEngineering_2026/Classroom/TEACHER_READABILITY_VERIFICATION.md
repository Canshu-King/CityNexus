# 课堂可读性修复 · 实测记录（2026-10-23）

对应任务书：`Evidence/TEACHER_READABILITY_CORRECTION_20261023.md`（Commit
`f27926c68f120bc293381637efa99a4f80c7e6c4`）。
用户 14:5x 的原始判定：**「我已经亲自在 Visio 和 Microsoft Project 打开了你做的文件，
实际展示效果严重不合格。」** 本文件记录改了什么、用什么量出来的、以及**现在还不行的地方**。

## 一、交付的三个文件

| 文件 | 字节 | sha256/16 | 内容 |
|---|---|---|---|
| `Classroom/Teacher_01_System_Overview.vsdx` | 25,926 | `35fb97e137f8958b` | 8 框 7 线，一页 16:9，微软雅黑，正文 18pt／标题 26pt |
| `Classroom/Teacher_02_Agent_User_Flow.vsdx` | 29,574 | `3806e4efd8d81d72` | 9 框 8 线，一个判定菱形 + 是／否两条出口 |
| `Classroom/Teacher_03_Project_Overview.mpp` | 281,088 | `5a570e79f9b363f0` | 11 个**中文**阶段行 + 5 个带日期的里程碑，无资源分配，时间刻度存成 50% |

> Project 的 `.mpp` 容器**每次打开都会重写**（不保存也重写），所以不同时刻读到的
> 字节数与摘要会变；上表是本轮最后一次关闭后、提交前的那一刻。内容的判据不是摘要，
> 是下面第五节第 7 条那两件事：16 行日期逐行等于计划基准，以及重开后窗口仍是 74 天。

原版技术交付（4 张带源码坐标的取证图、65 行计划基准）**一个字节都没动**：
计划基准 `Microsoft_Project/CityNexus_Software_Engineering_Plan.mpp` 的摘要
`6398e58f9b4cd3b3…` 在建课堂版前后各读一次，相等（脚本会因摘要变化直接 REFUSE）。

## 二、五个量具，和它们各自的读数

| 脚本 | 量什么 | 本轮读数 |
|---|---|---|
| `live_checks/se_teacher_diagrams_r1.py` | 出片 + 版面闸（重叠、溢出、页界、标签可落位） | T01/T02 各 `0 failures`；目标文件被别的 Visio 实例占用时**拒绝出片**并说明原因 |
| `live_checks/se_visio_cross_check_r1.py` | 读回真文件，逐条连线量交叉／穿形／出界，并核对摘要未变 | T01 `connectors=7 crossings=0 throughShapes=0 offPage=0 unchanged=True`；T02 `connectors=8 crossings=0 … unchanged=True` |
| `live_checks/se_teacher_project_r1.py` | 建 .mpp 后重开，逐行对账日期 | `rows=16 datesAgree=true dateDrift=[] noResourceAssignments=true linkRecords=0 constraintTypes={"0":1,"4":15}`；任务名换成中文后按**中文名**逐行匹配，仍要求每名恰好一行 |
| `live_checks/se_teacher_eye_r1.py` | **真开软件**：只读打开→最大化→`PrintWindow(PW_RENDERFULLCONTENT)`→量墨量 | 三张 2578×1558 窗口照片；画面主体墨量 T01 0.4035、T02 0.3441、T03 0.0725（图表半 0.0413／表格半 0.1175，比上一版 0.0558 高，因为 16 行中文全在一屏）；三个文件摘要开前开后相等 |
| `live_checks/se_teacher_project_print_r1.py` | 让 Project 自己打印，取第 1 页 | 4 页（刻度变宽后从 12 页降到 4 页），第 1 页起点 2026-09-07，图表墨量 **0.0880**（上一版 0.0611，被拒基线 0.0244） |

窗口照片就是文件名 `_window.png`，在 `Classroom/previews/`。

## 三、这一轮真正修掉的三个缺陷（都是肉眼发现的，不是测量发现的）

| 缺陷 | 之前（从文件里读回） | 之后（同一读法） |
|---|---|---|
| T02「是」分支与入流线共用菱形**顶顶点**，读起来像一条直线穿过 | 连线 `begin=(11.725,4.450) end=(6.625,4.450)` —— 两个端点都落在两框的**上沿**，线从框顶上绕过去 | `begin=(10.425,3.900)`＝菱形**左顶点** → `end=(7.750,3.900)`＝调整框**右边缘**，水平一条线 |
| 连线标签浮在空处，不知道说哪条线 | T01「用户确认后」墨迹带 y 4.36–4.52，而它那条线在 y 5.225（高出去 0.78 英寸） | 标签落在自己那条线上；4 倍放大核对：笔画不穿字（任务书"箭头不得穿过文字"） |
| 备注框排版像右对齐 | 每行一个整宽文本框，段落对齐单元格在本机取不到 → Visio 默认居中 | 每行文本框宽度＝该行实测墨宽，左边缘同一起点 |

「是」这条的成因是**几何**，不是路由：两框中心差 0.09 英寸时 Visio 宁可绕顶。
把中心调平（`ROW_MID + (DH-AH)/2`）就正了——因为这台机器上
`RoutingStyle` 与连接点寻址全都不可用（见第五节），几何是唯一能动的地方。

## 四、任务书逐条对照

| 任务书要求 | 状态 | 依据 |
|---|---|---|
| 两张简洁中文原生 Visio 图 | 达成 | 两个 `.vsdx`，原生形状（Drawing/Flow 母版），Shape 数 24／27 |
| 一份首屏能看清甘特条的原生 Project 文件 | **达成（有一处已知瑕疵）** | 打开即见 16 行中文任务名、**6 条甘特条**（需求／后端／AI Agent／验证／交付物／最终验收）、**4 个里程碑**（10/6、10/16、10/23、10/23）；窗口 2026-10-06→12-19 已存进文件，重开仍是 74 天。九月的三段与 M10 仍需拖一格滚动条（第五节第 1 条）；两个日期列各差一个汉字宽（第五节第 7 条） |
| 每框 ≤18 个汉字 | 达成 | 最多 13 字（「保存行程与状态／写入并留审计」，去掉换行与标点计数） |
| 正文 ≥16pt、标题 ≥22pt | 达成 | 节点正文 18pt、标题 26pt；连线标签 14pt、脚注 12–12.5pt（不是正文） |
| 箭头不得穿过文字 | 达成 | 交叉实测 0；标签有白色底板（`FillPattern=1`、`FillForegndTrans=0.35`），放大核对过笔画 |
| 源码行号移出正文 | 达成 | 全部进 Shape Data 的 `SourceRef` + `Classroom/Teacher_Source_Map.md` |
| 中文授课现场可读 | 达成 | 见上面三张 `_window.png` |
| 不许只做自动化测试就宣布完成 | 达成 | 本轮结论全部由"打开软件＋看照片＋看放大图"给出，测量项只作为旁证 |

## 五、现在还不行的地方（不粉饰）

1. **Project 首屏的"从哪里开始"由状态日决定，改不了；能改的是"一屏装多少天"。**
   两条要分开说，上一版把这两条混成了一条，写错了原因：
   - **起点**：`TimescaleStart/TimescaleFinish` 可读不可写——字符串 `2026-09-01`、
     `2026/9/1`、整数 `46272`、以及更早试过的 datetime 与 `pywintypes.Time` 全部
     `类型不匹配`。`TimescaleEdit` 18 组参数全拒，`ViewWhole`/`SplitBestFit`/`GoTo`/
     `Window.Scroll`/`TaskScrollTo`/`SelectTaskRow` 不存在（本轮又逐一 `hasattr` 复核过），
     `TimescaleStart` 是唯一读得到的锚点：重开时它落在 2026-10-15，也就是状态日
     （2026-10-22）往回 7 天。九月的条因此永远在左边。
   - **宽度**：`ZoomIn()`/`ZoomOut()` **在 COM 里是有效的**（上一版写"只改档位、画面没动"
     是错的，那次没把窗口调到前台）。逐档读回：8 → 38 → 119 → 278 → 860 天。
     真正好用的是时间刻度对话框里的**大小（%）**：100%→60% 使窗口从 38 天变 63 天，
     50% 变 **74 天**；`Ctrl+S` 保存后重开仍是 74 天（38→74 的两次读数见第五节第 7 条）。
   - **处置**：把 50% 存进文件（已做），首屏因此从 5 条横条变成 6 条；九月三段与 M10
     仍需拖一格滚动条，作为现场一步写在 `TEACHER_DEMO_START_HERE.md`，并附 Project
     自己打印的第 1 页作为不依赖手动的证据。
   - **一个坑要记住**：时间刻度对话框是模态的。它开着的时候 `GetActiveObject` 返回的对象
     连 `ActiveProject` 都会抛 `AttributeError`，`Ctrl+S` 也进不去——我为此白丢过一次保存，
     最后是 `Esc` 关掉对话框再 `FileSave()` 才落盘。
2. **这份 .mpp 的工时／成本合计是 0。** 没有资源分配是刻意的（分配列正是上次被点名的
   "密密麻麻"），代价是 Project 算不出 Work/Cost。真实数字在每行的"备注"里和计划基准里。
3. **这份 .mpp 不画依赖箭头。** 实测：11 个阶段行在原计划里前驱全为空，
   折叠视图里任何人为的 FS 箭头都会把并行的阶段推离计划日期——日期比箭头重要。
   关键路径请回 65 行的计划基准读。
4. **日程表（Timeline）子窗格在部分照片里仍占着顶部一条。** `TimelineViewToggle()` 不报错，
   但画面变化只有 0.0272→0.0281，不能证明它真的收起了；不声称已收起。
5. **引擎里有 6 类单元格在本机不可写**，`gate.json` 的 `styleIssues` 原文：
   `PrintFitLayerPages`、`RoutingStyle`、`ConLineJumpSize`、`WrappingStyle`、
   `WrappingDirection`、`ShrinkAutoFit`；段落对齐单元格完全取不到
   （`notes` 里 `"paragraph alignment skipped"` ×8／×9）。
   上一版的"门禁 0 failures"把这些全吞了——现在它们被记进 `styleIssues`/`notes` 并在此点名。
6. **"门禁 0 failures"不等于合格。** 本轮三处缺陷在测量项（交叉／穿形／出界）已经是 0 的时候
   依然存在，是看屏幕看出来的。任何一次"绿了"都只说明那把尺没覆盖到。
7. **两个日期列各差一个汉字宽，单行行高下「日」会被切掉。**
   放大截图核对：`完成时间` 列显示 `2026年10月2`（实际是 21 日），换行行高够时「日」会
   落到第二行，单行的行（如第 1 行）就只剩前面几位。逐条试过的路：`ColumnBestFit()`
   单独调用与先 `SelectAll()` 再调用都不按值加宽（它按列头算）；本机没有
   `ColumnWidth`/`SetColumnWidth`，`ColumnEdit` 只弹交互对话框。
   **处置**：不加宽——加宽 34 px 会把第 6 条横条挤出首屏，而这条横条正是任务书要的
   「六条以上」；改为在讲稿里写明"上课前把那两列往右拖一格"，并说明数字本身没变
   （每行备注、计划基准、`Evidence/STATUS_AND_OVERDUE.md` 都是完整日期）。
   **同一档位的第二个代价**：50% 尺寸下每周列只有约 64 px，顶栏标签
   `2026年10月19日` 需要约 85 px，于是每一列都被截成 `2026年10月`——五个星期看起来
   是五个同样的月份标签。月份推进（10→11→12）仍读得出，精确到日的日期在任务表的
   开始/完成两列里；要让顶栏恢复成完整日期，就得把尺寸调回 100%，代价是首屏只剩
   5 条横条、窗口退回 38 天。这一轮选择"六条横条 + 月份级标签"，两个选项都量过。
8. **中文任务名是展示名，映射必须可查。** 11 个阶段 + 5 个里程碑的中文名与计划行一一对应，
   英文原名与 WBS 写进该行备注（`原计划 WBS 10.5，原名 'M10  Part 1 course deadline…'`），
   映射表在 `Teacher_Source_Map.md`；日期／完成度／工时／成本照抄
   `se_project_build_r2_result.json` 同一行的引擎计算值，重开后按中文名逐行匹配，
   要求每个名字恰好一行且日期相同（`datesAgree=true`、`dateDrift=[]`）。

## 六、复现

```
# 出图与版面闸（这个 venv 才有 pywin32 的 Office 绑定）
D:/moodle/CityNexus/.venv/Scripts/python.exe live_checks/se_teacher_diagrams_r1.py
D:/moodle/CityNexus/.venv/Scripts/python.exe live_checks/se_visio_cross_check_r1.py
D:/moodle/CityNexus/.venv/Scripts/python.exe live_checks/se_teacher_project_r1.py

# 拍照与打印页需要 PIL，用带 PIL 的那个系统 Python 3.10（本机以 `python` 调用）
python live_checks/se_teacher_eye_r1.py
python live_checks/se_teacher_project_print_r1.py
```

（两个解释器不是随意选的：课程 venv 有 pywin32 但没有 PIL，系统 3.10 两样都有；
用错的那个会在 `import PIL` 或 `DispatchEx` 上直接失败。）

跑之前先确认没有遗留的 Office 进程（`VISIO.EXE` / `WINPROJ.EXE` 计数应为 0）：
一个崩溃的探针会留下看不见的 `/Automation` 实例，把目标文件按只读占住，
表现为 `SaveAs` 报"DOS 无效句柄"——那不是 Visio 的 bug，是锁；
`se_teacher_diagrams_r1.py` 现在会在出片前检查目标可写并点名是谁占着。
