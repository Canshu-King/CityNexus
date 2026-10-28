# R5 双语课堂套件说明（2026-10-29 夜班，Qoder/zcode 接续会话）

本轮两件事，都只动课堂层，取证层与 Project 中文版一字未动。

## 一、中英双语四个 Visio + 英文甘特

| 文件 | 语言 | 内容 |
|---|---|---|
| `Teacher_01_System_Overview.vsdx` | 中文 | 系统总览（主图 + 附注页） |
| `Teacher_01_System_Overview_EN.vsdx` | 英文 | 同几何英文版（System Overview + Appendix） |
| `Teacher_02_Agent_User_Flow.vsdx` | 中文 | 用户流程（主图 + 附注页） |
| `Teacher_02_Agent_User_Flow_EN.vsdx` | 英文 | 同几何英文版（User Flow + Appendix） |
| `Teacher_03_Project_Overview_R4.mpp` | 中文 | **冻结不动**（R4.1 验收版，sha256/16 `30af900a34a46f0d`） |
| `Teacher_03_Project_Overview_R4_EN.mpp` | 英文 | R4 的英文展示副本（sha256/16 `deeb1500b4cd257d`） |

英文版不是机翻摆设：11 个摘要行恢复为**计划自己的英文原名**（R4 建中文版时把
原名写进了每行备注，本轮原样取回，零编造），M9–M13 里程碑用中文展示名的英文
对应句式，65 任务/61 依赖/61 资源分配一条不少，逐 Task.ID × 十字段对事实源
**0 差异**（`Evidence/logs/se_r43_fidelity_en.json`）。

## 二、左下小字出画面（GPT 10-28 复验留下的唯一非阻断缺点）

两张中文主图左下角的多行技术说明整块移到每个文件的第 2 页「附注（不投屏）」，
内容逐字保留、字号反而更大（13.5pt）。主图版面**一个坐标都没动**——坐标逐项
照抄 R4.2 通过版（`Evidence/scripts/se_teacher_diagrams_r2.py`），包括那条
R4.2 补的回环箭头。投影只放第 1 页；备查时翻第 2 页或看形状数据（Ctrl+1）。

## 三、门禁与实机验证（全部真跑，不是自我声明）

- Builder 自带门禁（溢出/交叉/压盖/页界）：4 份全 0 failures；
- 连线交叉检查 `se_visio_cross_check_r2.py`（r1 的多页感知版；r1 保留给历史证据）：
  4 份 `crossings=0 throughShapes=0 offPage=0`；
- 回环证明 `se_r42_loop_proof_r1.py`：中英两份 Teacher_02 的回环线都同时粘在
  `['t2n3','t2n7']`，尾 (6.625,4.360) 头 (6.625,5.130)，EndArrow=4；
- 可编辑往返 `se_r43_roundtrip_{zh,en}_r1.py`：改一处非关键文字（标题块的说明行，
  注记挪走后页 1 上最"非关键"的字）→ 另存副本 → 冷重开 → 拖框线跟随 → 复位；
  两份原件摘要前后一致；
- **真开窗终验** `se_r43_eye_r2.py`：6 个文件（4 vsdx + 2 mpp）全部真实打开、
  最大化、PrintWindow 截图（`previews/*_window.png`），两张 mpp 打开前后摘要一致；
- 修复了一个真 bug：多页保存会把"活动页"留在第 2 页，老师双击会先看到附注页。
  实测 `Page.Activate` 在本机 COM 绑定上不存在，`ActiveWindow.Page` 赋值在
  **新建**文档上不落盘；最终用"打开→指回第 1 页→另存→重开验证"的后处理
  （已烘进生成器 `se_teacher_diagrams_r2.py`），4 份全部重开即第 1 页。

## 四、没有做与不做

- Project 中文版、取证版 Visio、65 行事实计划：一律未动（冻结是 GPT 与操作者的
  共同决定；英文 mpp 是副本，见上表摘要）。
- `se_evidence_index_r1.py` 的 STALE 旧缺口维持 10-26 的处置：等主人点头再动。
- 英文 mpp 的任务名列比中文窄一档（英文名更长换行到三行，首屏 8 行、滚动可见
  其余），布局沿用冻结版视图没再做列宽手术——要不要加宽留给主人定。

生成器与全部证据：`Evidence/scripts/se_teacher_diagrams_r2.py`、
`se_r43_project_en_r1.py`、`se_r43_{loop_proof_*,roundtrip_*,eye_r2,fidelity_en}` 等，
日志与 JSON 在 `Evidence/logs/`、`Evidence/scripts/*_result*.json`。
