# 讲台上从这里开始（三个文件，2 分半讲完）

生成时间 2026-10-23 18:50。这三份是**原生可编辑文件**，不是图片：Visio 里能拖框、
Project 里能改工期。原版的取证文件（带源码行号、65 行计划、资源分配）都还在，
本目录只是给现场用的一套。

## 打开顺序与讲法

### ① `Teacher_01_System_Overview.vsdx` — 30 秒：这套系统是什么

双击打开（Visio 会显示 `[只读]` 没关系，要演示编辑就另存一份）。

> 「CityNexus 是一个城市出行助手。旅行者提需求，前端把需求交给后端，
> 后端把活交给 Agent；Agent 调用地点和路线工具生成方案，方案在地图上展示，
> **最后一步必须由用户确认才写库**。整条链路就是这一屏，八个框。」

指着右下角的**备注框**收尾：「图上一个源码行号都没有，出处在 Shape Data 里，
选中任意框按 `Ctrl+1` 就能看到它对应的文件与端点数。」

### ② `Teacher_02_Agent_User_Flow.vsdx` — 30 秒：Agent 不能自己改行程

> 「这是同一个系统的用户流程，重点是中间那个菱形。**『否』才会写入并留下审计；
> 『是』只产生新提案，回到调用工具那一格重跑，库里一行都不动。**
> 所以 Agent 只有提案权，改动行程的权力在用户手上——这是这门课要的权限边界。」

如果老师问「这个边界是写在文档里还是代码里」：答代码里，
`backend/app/agent/gateway.py:358` 是工具白名单闸门，`:41` 是 Idempotency-Key；
完整对照在 `Classroom/Teacher_Source_Map.md`。

### ③ `Teacher_03_Project_Overview.mpp` — 60 秒：做到哪了，还差什么

> 「11 个阶段折成 11 行，加 5 个带日期的里程碑。蓝条是计划工期，
> 条里的深色是完成度。**M10 那个 10 月 2 日的课程截止已经过了**（里程碑上写着 missed），
> 今天 10 月 23 日是中期汇报（M11），Part 2 的硬截止是 11 月 6 日（M12）。
> 每一行的日期、完成度、工时、成本都取自 65 行的那份计划基准，没有重排。」

**打开后必做的一步**（甘特图默认停在"今天"附近，九月的条在屏幕左边）：
把**图表区下方那根横向滚动条拖到最左**，11 条甘特条就从 2026-09-07 起全部进屏。
不想现场动手，就直接放这张已经排好的图：`previews/Teacher_03_Project_Overview_bars.png`
（那是 Project 自己打印出来的第 1 页，起点就是 9 月 7 日，不是手工画的）。

## 兜底

| 情况 | 怎么办 |
|---|---|
| 老师机器没装 Visio | 直接放 `Classroom/previews/Teacher_01_System_Overview.png` / `Classroom/previews/Teacher_02_Agent_User_Flow.png`（Visio 自己导出的整页），或同一目录下的 `.pdf` |
| 没装 Project | 放 `previews/Teacher_03_Project_Overview_bars.png`，或 `Teacher_03_Project_Overview_print.pdf`（12 页，第 1 页从 2026-09-07 开始） |
| 投影仪分辨率低 | 两张 Visio 图正文 18pt、标题 26pt，是按 1080p 整屏一页设计的，不需要缩放 |
| 老师要问细节 | 打开取证版：`Visio/01_CityNexus_System_Architecture.vsdx`、`Visio/03_CityNexus_Agent_Workflow.vsdx`、`Microsoft_Project/CityNexus_Software_Engineering_Plan.mpp` |

## 现场别做的事

- 不要在 Project 那份里读"关键路径"：这份折成 11 行的文件不画依赖箭头（原因写在
  `TEACHER_READABILITY_VERIFICATION.md`），关键路径在 65 行的计划基准里。
- 不要在这份里看工时/成本合计：这一版**故意没有资源分配**（分配是上次被点名"密密麻麻"
  的元凶），所以合计列是 0；每行的真实工时与成本写在该行的"备注"里，
  总计在计划基准文件里。
- 不要说这份甘特图"打开就能看全"：默认停在今天附近，需要拖一下滚动条（上面那一步）。
