# 连续执行回执（两个 P0 完成后）

时刻 2026-10-23 04:47 · 分支 `review/se-coursework-deliverables-r1`

| 项 | 判定 |
|---|---|
| 原生 Visio（01 与 03 打开、拖动形状、改字、存副本、重开） | **PASS** |
| 拖动时连线是否跟着走 | **PASS**（两张图各自 2 / 1 条连线端点仍贴在移动后的形状上） |
| 原生 Project（六个视图切换、改备注、存副本、重开、65 行与依赖读回） | **PASS** |
| 截图能否看到真正的甘特条 | **能**：`Classroom/previews/Gantt_Visible.png`（窗口实拍）与 `Gantt_Visible_print.png`（Project 打印第 1 页，从 2026-09-07 起）；里程碑两张同理。旧图被点名的原因是时间轴停在 10 月中旬，已换掉。
| 中期汇报措辞 | M11 改为 `Mid-term teacher review (scheduled 2026-10-23 noon)`、0%% 完成；没有任何文件写「已举行/已验收」 |
| 四页 PDF | `Presentation/previews/CityNexus_SE2026_Briefing_Deck.pdf` 实测 4 页，绘图门失败 0 项 |

关键路径：`Classroom/课堂演示顺序.md`、`Evidence/CLASSROOM_FINAL_VERIFICATION.md`、`Microsoft_Project/CityNexus_Software_Engineering_Plan.mpp`（sha256 `6398e58f9b4cd3b3f1a24255d50c9bb2b10569abdd747271f15d3e50eab84aee…`）。

中午包：`D:\moodle\CityNexus_20261023_Noon_Ready.zip`，sha256 `1f7bf7af90169970aa14d2df3c1e252b87df8c9e39af0023c45d49a665548655…`，17 个成员，解包逐文件字节一致。

尚存障碍：Project 视口无法脚本滚动（现场按一次 Ctrl+Home）；Part 1 平台提交状态未核实；20 小时/周与分工未经成员确认；14 行逾期未完。

判定：**READY_WITH_LIMITATIONS**（理由见 `Evidence/CLASSROOM_FINAL_VERIFICATION.md` 第 2、6 节）。
