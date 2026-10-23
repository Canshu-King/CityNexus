# CityNexus 软件工程 2026 · 修订二交付包（复审简报）

生成 2026-10-23 · 仓库 `CityNexus` · 分支 `review/se-coursework-deliverables-r1` · 打包时分支头 `f27926c68f120bc293381637efa99a4f80c7e6c4`。
包内 **233** 个文件（不含 `MANIFEST.sha256` 自身——清单不能给自己的摘要签名）。
逐文件 sha256 见 `MANIFEST.sha256`；压缩包 sha256 `zip 不能自证：压缩包自身的 sha256 记在包外的 `Evidence/R3_RESULT.md` 与提交信息里，包内只放逐文件清单`。

## 0. 这一版是冲着谁的

上一版被独立审查否掉三处：Project 排程语义、Visio 逐形状元数据、Agent 流程图与真实代码不符。
`Evidence/REVISION_2.md` 逐条回答，并且**每个"改后"数字都是打包时从工件重算的**，
不是从终端记录里抄的。本简报告诉你怎么自己复算。

**如果哪一项你复算不出来，请当成它没有发生。**

## 1. 交付物（实测）

| 项 | 值 | 怎么复算 |
|---|---|---|
| Visio 原生图 | 4 张 .vsdx，共 5 页 | Visio 直接打开 |
| 形状 / 连线 / 分层带 | 128 / 148 / 24 | 对 `Visio/specs/*.json` 的 sheets 求和 |
| 连线两端真粘连 | 148 / 148 | `Evidence/se_visio_proof_result.json` → glue.proven |
| 逐形状自定义属性读回 | 579 / 579 | 同上 → shapeData.propsOk / expected |
| 打开-改字-存-关-重开-读回 全通过 | 4 / 4 | 同上 → checks |
| 版面闸门失败项（重叠/越界/文字出框/图例被压） | 0 | `Visio/previews/*.gate.json` → failures |
| Project 原生计划 | `Microsoft_Project/CityNexus_Software_Engineering_Plan.mpp`，sha256 `6398e58f9b4cd3b3` | Project 直接打开 |
| 行数 | 65（摘要 11 / 明细 54，含里程碑 13） | 看 WBS 列 |
| 声明依赖 / 引擎读回 | 61 / 122 条依赖记录 | `Task.TaskDependencies`，脚本已逐条比对 |
| 违反日期顺序的依赖 | 0 | 同上 |
| 被钉住日期的行（约束≠ASAP） | 0 | 约束列应为空 |
| 关键路径 | 4 行（引擎算出） | 勾 Critical 列 |
| 人力工时 / 总成本 | 221 h / $4461 | 工时=工期×投入×8h，成本由 Project 自己乘费率 |
| 工时或成本与估算不符的行 | 0 | 逐行对 duration×units×rate |
| 截止日 | 6 满足 / 0 违反（课程硬日期） / 0 内部目标未达 | Deadline 列 |
| 关闭后由新进程重开，逐字段比对 | 0 处差异 | 行/日期/百分比/工时/成本/约束/实际/关键/WBS |
| 发布回读 | 65 行、122 条依赖、0 处违反 | 打包脚本对**已发布文件**再开一次 |
| 汇报版一页图 | `Briefing/CityNexus_Plan_Briefing_A3.vsdx` + PDF/PNG | 日期全部来自 .mpp 计算结果 |

## 2. 这一轮新加的、可以攻击的硬断言

1. **静态前置检查**（`se_plan_cpm_r1.py`，纯 Python，不开 Project）：环、未知行、自环、
   SF 链接、以及每条声明依赖能否被自己的正向排程满足。当前 0 违反 / 0 结构问题。
2. **依赖必须从引擎读回**：不再相信脚本"我写了"，而是打开文件遍历
   `Task.TaskDependencies`，用本机实测的类型映射（FF=0, FS=1, SF=2, SS=3）逐条判日期不等式。
3. **链接类型必须真的驱动日期**：把一条未完成任务加 10 个工作日，看哪些后继、哪个字段动了；
   FS/SS 必须拖动开始日，FF 必须拖动完成日；然后改回去，要求每个日期完全复原。
   （本机实测：`TaskDependency.Lag` 写入被吞、`TaskMoveToStatusDate` 返回真但什么都不动，
   所以不能用 lag 证明，见 `Evidence/logs/se_proj_probe_r10.log`。）
4. **形状属性写一次读一次**：`AddNamedRow` + `Prop.<name>.Value`，写完立刻在同一调用里读回，
   读不回原值就是错误，不是提示。验收脚本再从**磁盘上的文件**逐形状、按 (页, ShapeID) 复核。
5. **版面闸门覆盖非节点元素**：图例、说明块、页脚、连线标签必须在页内、不压形状、不互相压；
   带标题的分层带不能被形状压住；每条引用文字必须放得下它自己的形状。
   这条规则第一次运行就抓出三类真实缺陷：图例被说明块压住、连线标签被丢到页角（旧代码在粘连瞬间取端点，那时还是 0,0）、引用文字越出形状边界。
6. **包必须过自己的往返**：压缩 → 解压到新目录 → 逐文件重算 sha256 与清单比对。

## 3. 我没有做成、也没有假装做成的事

| 项 | 状态 | 依据 |
|---|---|---|
| Part 1（2026-10-02 截止） | **本仓库无法证实也无法证伪**；行仍为 0%，等课程记录 | 仓库内无该 .pptx；但这不等于没交 |
| 迟开的工作 | 6 行相对状态日已迟，**保持迟到**，没有挪日期 | Project 的 Move-to-Status-Date 在本机 COM 无效 |
| 三人分工 | 成员已实名，但 git 只有一个提交身份，分工是**计划提案** | `git log --format=%an` |
| 费率 | 课程规划估算，非工资；两条算力车道是材料资源（只花钱不计工时） | 资源备注 |
| 基准计划 | **故意没存**：没有可信原始计划 | 未调用 `BaselineSave` |
| 拖动母版形状看连线跟随 | **未证明**：内置模具位置保护 | moveProof 缺席即未证 |
| Project 分页设置 | **无法脚本化**：`FilePageSetupPage` 各形参均报参数无效 | `Evidence/logs/se_project_brief.log` |
| 真实支付 / Hermes 原生 / live Valhalla / 真机影子测试 | 未实现或未验证，图上黄/灰虚线 | `BLOCKERS.md:9-16` 等 |

## 4. 请专门挑这六处

1. **里程碑日期不单调**（M8 早于 M4）：这是并行流的真实形状，还是我链接画错了？
2. **百分比是否可辩护**：凡 100% 都有测试或提交证据吗？重点看 `9.1 后端回归 85%`、
   `4.5 商务与守护 40%`、`8.2 前端回移 50%`。
3. **工时是否可信**：221 工时摊到三人七周，是否偏高或偏低？
4. **Agent 图的三族处理器**：读→无策略、replan 对→策略先于幂等、typed→各自守卫，
   与 `gateway.py` 现在的行号是否仍然一致？
5. **一页汇报图**：把计划压到 11 条相位条 + 13 个里程碑，是否已经丢失了老师判断所需的信息？
6. **三态配色**：黄=已写未验证、灰虚线=计划中，有没有该黄却画成蓝的形状？

## 5. 包内结构

```
README.md                      用途与展示顺序
SOURCE_MAPPING.md              每个数字怎么量的 + 全部代码坐标 + 文件指纹
AUTOMATION_VERIFICATION.md     跑了什么、哪一步失败过、怎么修的
REVISION_2.md                  对上一轮审查的逐条回答（改前/改后都是重算的）
REVIEW_BRIEF.md                本文件
se_*.json                      机器可读结果（gate / proof / build / brief / revision）
Visio/                         4 个 .vsdx + previews(PNG/PDF/gate.json) + specs(JSON)
Microsoft_Project/             .mpp + 汇报版 .mpp + 视图 PDF + previews(PNG)
Briefing/                      一页 A3 横版汇报图（.vsdx + PDF + PNG + gate.json）
Evidence/scripts/              生成器与验收脚本（可重跑）
Evidence/logs/                 探针与构建原始日志
MANIFEST.sha256                包内每个文件的 sha256
```

## 6. 复现

```
cd D:\moodle\live_checks
python se_plan_cpm_r1.py                # 只做静态依赖检查
python se_project_build_r2.py           # 建计划、全量审计、发布 .mpp
python se_visio_build_r1.py             # 四张图 + 预览 + gate
python se_visio_proof_r2.py             # 重开、粘连、逐形状属性
python se_visio_plan_brief_r1.py        # 一页汇报图
python se_evidence_docs_r1.py           # 三份说明文档
python se_evidence_revision_r1.py       # REVISION_2.md
python se_review_package_r2.py          # 本文件 + MANIFEST + 压缩包 + 往返校验
```
每个脚本在断言不过时都返回非零，而不是"看起来成功"。

---

竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度
