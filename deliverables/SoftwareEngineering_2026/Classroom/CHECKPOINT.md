# 中午前连续执行检查点 (CHECKPOINT)

任务书：`Evidence/CLASSROOM_QODER_CONTINUOUS_UNTIL_NOON_20261023.md`（远端 `db001c28ca`）。
本文件由 Qoder 本地会话每完成一阶段就重写一次；**Qoder 不会在后台自己运行**，如果会话中断，
下一个操作者按「下一阶段」继续即可，不要重做已标 PASS 的事。

## 基线

| 项 | 值 |
|---|---|
| 分支 | `review/se-coursework-deliverables-r1` |
| 本地已同步到的远端头 | `db001c28ca8f5c7623e6cf4f806d4eb18a2e6172` |
| R3 主体提交（保留，不重做） | `4bba9d2e54` → `fdbb4ff988` → `13f7d1842c` → `bf2a8d3a09` |
| 主计划 .mpp sha256/16 | `4cd35d0725c2c5d3`（本轮所有视图调整只动展示副本） |
| 现场时刻 | 2026-10-23 12:00 +08:00；11:00 起冻结 |

## 阶段状态

| 阶段 | 内容 | 状态 | 完成时刻 (+08) | 证据 |
|---|---|---|---|---|
| P0-A | 甘特图/里程碑「第一屏看得见任务条」展示副本 + 新截图 | **完成** | 06:40 | `Classroom/CityNexus_Plan_Classroom.mpp`、`CityNexus_Milestones_Classroom.mpp`、`previews/` 四张（窗口实拍 + Project 打印页） |
| P0-B | M11 中期汇报时间措辞 | **完成** | 06:05 | 计划源改为 `M11 Mid-term teacher review (scheduled 2026-10-23 noon)`、0% 完成；恢复计划把它记为 scheduledEvents 并写明 10.2 材料包 10-28 完成的风险 |
| P0-C | 双软件真机打开/编辑/副本保存/重开 | **完成**（改动后复跑） | 06:45 | `se_classroom_demo_result.json`：Visio PASS、Project PASS、连线跟随 True、原件摘要未变 |
| P1-D | `Classroom/课堂演示顺序.md` + 三套备用 | **完成** | 07:00 | 四段顺序+讲稿+离线文件清单（含大小与 sha256/12）+ 不要说的话 |
| P0-E | 中午包 + `CLASSROOM_FINAL_VERIFICATION.md` + 回执 + push | 进行中 | | 包在仓库外：`D:/moodle` 下的 `CityNexus_20261023_Noon_Ready.zip`（17 成员、解包逐文件字节一致、sha256 记在验收文件里） |
| 冻结 | 11:00～12:00 只读查验 | 未开始 | | |

## 硬约束（每阶段自查）

- 不改主计划/里程碑/恢复版 .mpp 的任务、工时、依赖、进度、成本与合同日期；视图调整只发生在
  `Classroom/` 下的展示副本。
- 12:00 之前不写「已举行 / held today / 已验收」。
- Part 1 提交状态保持「未核实」；20 h/周与 220.9 h 只称课程估算；14 行逾期与 2026-11-04
  恢复预测如实说明。
- 不使用 `--force`；不碰 `commander/control` 与 Codex Revolution 分支；不改主产品代码。
- 共享 git index 里有别的车道留下的 109 条该路径的「已删除」暂存记录，因此本会话一律用
  隔离索引（`GIT_INDEX_FILE` + `read-tree HEAD`）提交，禁止 `git add -A` / `git commit -a`。

## 下一阶段

1. 跑完 docs → index → package → commit → push，把最终 SHA 写回本文件。
2. 11:00 起冻结：只做只读抽检（重新打开四个 .vsdx 与三个 .mpp 的副本、看四页 PDF、核对 `Classroom/previews/` 四张图）。
3. 已知需要现场手动的一步：Project 甘特图右侧时间轴无法脚本滚到项目起点（13 个入口不存在、Timescale 赋值与 TimescaleEdit 全部失败，已留日志），现场按一次 Ctrl+Home 或用 `Gantt_Visible_print.png` 当替身图。
