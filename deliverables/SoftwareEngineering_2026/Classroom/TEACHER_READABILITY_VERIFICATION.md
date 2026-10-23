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
| `Classroom/Teacher_03_Project_Overview.mpp` | 276,480 | `cb06dcb4b7e23a6f` | 11 个阶段行 + 5 个带截止日期的里程碑，无资源分配 |

原版技术交付（4 张带源码坐标的取证图、65 行计划基准）**一个字节都没动**：
计划基准 `Microsoft_Project/CityNexus_Software_Engineering_Plan.mpp` 的摘要
`6398e58f9b4cd3b3…` 在建课堂版前后各读一次，相等（脚本会因摘要变化直接 REFUSE）。

## 二、五个量具，和它们各自的读数

| 脚本 | 量什么 | 本轮读数 |
|---|---|---|
| `live_checks/se_teacher_diagrams_r1.py` | 出片 + 版面闸（重叠、溢出、页界、标签可落位） | T01/T02 各 `0 failures`；目标文件被别的 Visio 实例占用时**拒绝出片**并说明原因 |
| `live_checks/se_visio_cross_check_r1.py` | 读回真文件，逐条连线量交叉／穿形／出界，并核对摘要未变 | T01 `connectors=7 crossings=0 throughShapes=0 offPage=0 unchanged=True`；T02 `connectors=8 crossings=0 … unchanged=True` |
| `live_checks/se_teacher_project_r1.py` | 建 .mpp 后重开，逐行对账日期 | `rows=16 datesAgree=true dateDrift=[] noResourceAssignments=true linkRecords=0 constraintTypes={"0":1,"4":15}` |
| `live_checks/se_teacher_eye_r1.py` | **真开软件**：只读打开→最大化→`PrintWindow(PW_RENDERFULLCONTENT)`→量墨量 | 三张 2578×1558 窗口照片；画面主体墨量 T01 0.4035、T02 0.3441、T03 0.0558（图表半 0.0402／表格半 0.0997）；三个文件摘要开前开后相等 |
| `live_checks/se_teacher_project_print_r1.py` | 让 Project 自己打印，取第 1 页 | 12 页，第 1 页起点 2026-09-07，图表墨量 0.0611（上一轮被拒基线 0.0244） |

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
| 一份首屏能看清甘特条的原生 Project 文件 | **部分达成** | 文件是真的、16 行、日期逐行等于基准；但首屏停在"今天"附近，需要拖一次滚动条（第五节第 1 条） |
| 每框 ≤18 个汉字 | 达成 | 最多 13 字（「保存行程与状态／写入并留审计」，去掉换行与标点计数） |
| 正文 ≥16pt、标题 ≥22pt | 达成 | 节点正文 18pt、标题 26pt；连线标签 14pt、脚注 12–12.5pt（不是正文） |
| 箭头不得穿过文字 | 达成 | 交叉实测 0；标签有白色底板（`FillPattern=1`、`FillForegndTrans=0.35`），放大核对过笔画 |
| 源码行号移出正文 | 达成 | 全部进 Shape Data 的 `SourceRef` + `Classroom/Teacher_Source_Map.md` |
| 中文授课现场可读 | 达成 | 见上面三张 `_window.png` |
| 不许只做自动化测试就宣布完成 | 达成 | 本轮结论全部由"打开软件＋看照片＋看放大图"给出，测量项只作为旁证 |

## 五、现在还不行的地方（不粉饰）

1. **Project 首屏的横向滚动存不进文件。** 逐条实测过的路：
   `TimescaleStart/TimescaleFinish` 赋值报 type mismatch；`TimescaleEdit` 18 组参数全拒；
   `ViewWhole`、`SplitBestFit`、`GoTo`、`Window.Scroll`、`TaskScrollTo`、`SelectTaskRow` 不存在；
   `mp.Table("摘要")` 抛 TypeError、`ActiveWindow.Table` 抛 AttributeError（想换窄表让图表多占屏）；
   `TimelineShowHide` com_error；`ZoomTimescale` 曾把进程挂住 15 分钟（不再调用）。
   键盘那条也试了：取到前台（`GetForegroundWindow()` 核对为真）后发 Ctrl+Home，
   图表左半墨量 0.0332 → 0.0332，画面没动。
   **处置**：把"拖一下图表下方那根横向滚动条"写成现场一步（`TEACHER_DEMO_START_HERE.md`），
   并附上 Project 自己打印的第 1 页作为不依赖手动的证据。
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
