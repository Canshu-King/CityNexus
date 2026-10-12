# Revolution Lab 全量吸收五年计划（2026Q4 - 2031Q4）

主人 2026-10-12 令：把 revolution lab 全量吸收，一根不少，融会贯通。这份计划是那道令的执行件。

## 一、事实基线（现读，权威尖 70da925d8861）

| 事项 | 现读数 |
|---|---|
| 远端 revolution 枝 | 41 枚，全部不在权威线上 |
| 叉口 | 3 个：族A 4ee14229f806、族B 7d22cd0eb784、族C a6e2cdbff94e |
| 是本族代表的祖先（整根携带，不必再落一次） | 6 枚（merge-base --is-ancestor 实测） |
| 需独立处置 | 35 枚 |
| 族A 代表 gpt/revolution-r33-open-world-journey-adaptation 对现尖的独有新增 | 554 枚文件：产品码 65、测试 151、文档证据 224、其他 93、产物 21 |
| 真并行撞面（枝相对自己基线确实动过、且与现尖内容不同） | 族A 88 枚、族B 173 枚、族C 93 枚 |
| 族内各枝相对本族代表的独有增量 | 族A 93 枚、族B 23 枚、族C 0 枚 |

三条测绘结论，直接决定这份计划的形状：

1. **族B 不是功能，是快照。** 8 枚 r6~r74-prep 的根提交是主线早期那枚 import（整树一次进仓），
   之后每枚只往 `evidence/gpt-assist/` 放评审产物。它们对现尖的独有产品码为 0。
   表面那 173 枚"内容差"全部来自基线太老，属"不得回退"面，不占吸收工期。
2. **族C 是族A 同一批能力的第二次移植尝试，且离尖更近。** 它相对族A 代表的独有增量是 0 枚；落后仅 283 代。所以吸收顺序取族C 的接尖红利，内容以族A 代表为准，不重复落两遍。
3. **族A 的 31 枚轮次枝不是 31 份活，是同一条累积线上的快照点。**
   41 枚里 6 枚整根落在本族代表之下（是其祖先），其余各枝相对本族代表的独有增量合计 93 枚（族A）+ 23 枚（族B），且绝大多数是轮次文档与 CI 脚本，产品码只零星几枚。

所以"一根不少"的可执行定义是：**41 枚枝逐枚有归属结论与 40 位坐标，每枚枝的独有资产都能被一把尺复算出来**。不是 41 次 merge。

## 二、吸收的到底是哪些能力（取自族A 代表对现尖的产品码独有清单）

Revolution Lab 自己的宪章（`gpt/revolution-r33-open-world-journey-adaptation` 上的 `REVOLUTION_LAB_PRODUCT_DIRECTION_CHARTER.md`）
把它的任务选择写成一句话：**用户现在能做到什么以前做不到的事**，并列出七个方向。
这七个方向就是吸收清单——主线恰好是最不擅长快速做出这类能力的地方，这也正是主人要全量吸收的理由。

| 能力族 | 落点（族A 代表对现尖独有的码） | 用户面 |
|---|---|---|
| 行程执行续跑 | `backend/app/execution/`（continuous_journey、departure_activation、in_transit_reroute、launch_setup、launch_origin、group_presence 等） | 出发前设置、途中改道、断了能接上 |
| 集体协同 | `backend/app/collective_authority.py`、`collective_mediation.py`、`collective_operator.py` 与 `execution/member_*` | 多人约走、成员侧 quest、集合点握手 |
| 主动观察 | `backend/app/agent/watch_policy.py`、`journey_ahead.py`、`recovery_discovery.py`、`live_moment_scout` | 现实变了先看见，不用用户盯 |
| 中断恢复 | `backend/app/agent/continuation.py`、`standby.py`、`overnight_steward.py` | 夜里断的早上接上 |
| 决策代理 | `backend/app/agent/operator_brain.py`、`journey_intent.py`、`transactional_operator.py` | 要授权时来问人，问完继续办 |
| 前端承接 | `frontend/src/features/`（agent/JourneyClarificationPanel、discovery/BootstrapDiscoveryPanel、PublicCityAreaPicker、execution/MemberPlaceInvitationPanel、MomentScoutCard、travelerSession.ts 等） | 上面五族在屏上真的按得动 |
| 验证承接 | 测试 151 枚（backend/tests 与 frontend/e2e） | 每族能力有自己的绿 |

## 三、五年路线（每年四季度，每季一句"用户能做什么"）

### 2026Q4 第0季：把地基钉死
- 本计划与对账表、吸收尺进权威线（同一批、同一道门）。
- 族C 归零确认：codex 的移植枝相对族A 代表独有 0 枚，把它当成"接尖顺序的参照"，不再单独落一遍内容。
- 族B 的 `evidence/gpt-assist/` 评审产物并入 `docs/revolution-archive/gpt-assist/`（纯搬运，零产品码）。
- 退出判据：尺报"对账表 41 枚枝每枚有归属"，且尺能自跑非零退出码可读。

### 2027（第1年）：接上现尖的契约，让能力先跑得起来
按域串行落，一个域绿了才开下一个，禁止同时动两域的热文件。
- Q1 `execution/` 域：把 `backend/app/execution/` 的新模块接到现尖的 schemas 与 services 上；真并行撞面里 `backend/app/main.py`、`backend/app/schemas.py` 先只开这两枚。
  用户能做什么：**一条行程出发后中途断了，回来还能接着走**（这是主线至今没有的）。
- Q2 `collective_*` 域 + `contracts/openapi.yaml`：群组权限与调解进契约。
  用户能做什么：**两个人约同一趟，其中一人改主意时，另一人看得见影响**。
- Q3 `agent/` 域（watch_policy、journey_ahead、continuation、overnight_steward）。
  用户能做什么：**不用刷新页面，系统在现实变化时先动**。
- Q4 前端 `features/` 六枚组件接入口 + 该域测试转绿。
  用户能做什么：**上面三件事在手机屏上按得到，不是只有 API**。
- 每季门禁同一条：`merge-tree` 无冲突 + `codes_on_screen_gate_r4` + 字典同侧键闸 + `--frontend-build`，全绿才走 `preflight_and_land_r7.py --land`。

### 2028（第2年）：真数据面
revolution 的码是围着真供应商写的（`integrations/discovery/real_city.py` 在 88 枚撞面里）。这一年把实验室里"能跑"换成"有真事实"。
- Q1 供应商证据通道（B 类）与产品真值判定（C 类）分离落地，沿用 R1-R13 裁定的词表，不另造枚举。
- Q2 校园实测：labmai/aiask 两平台的真地点与真时段进演示面。
- Q3 e2e 场景层（族A 代表对现尖独有的 `frontend/e2e` 共 53 枚）换成真机场景（手机直连 :4781 那条 LAN 路线）。
- Q4 演示板从"夹具驱动"换成"真库驱动"，把 `seed_demo` 那条破坏性出口彻底移出验收路径。

### 2029（第3年）：多人
- 全年一条主线：**collective 那三枚模块从"后端能算"变成"多个人真在一起用"**。
- Q1 成员侧邀请与握手；Q2 成员侧 quest 与集合点；Q3 分歧调解（`collective_mediation`）落到真实冲突；Q4 授权链（要人点头的那件事，点头之后系统继续办）。

### 2030（第4年）：主动与预测
- Q1 `journey_ahead` + `watch_policy` 组成真正的"前瞻"；Q2 中断预测（disruption）；Q3 自愈预算（失败了怎么诚实说 BLOCKED，宪章里那半句要留在产品里）；Q4 夜间值班产品化。

### 2031（第5年）：消解 lab
- 目标是**让 revolution 这个词在主线里失去意义**：`REVOLUTION_R*.md` 224 枚轮次文档归档进 `docs/revolution-archive/`，能力名进主线语汇，字典按域拆片后的键全部并回，吸收尺退出日常（改为季度复检）。
- 年末判据：尺报 0 枚未吸收，且 `ls-remote` 上 `*revolution*` 只剩归档枝。

### 2028-2031 共用的可靠性预算
- 自主值守（`overnight_steward`、`standby`）每年只许占用固定份额的运行成本，且必须能一按就停；
- 每年 Q4 出一份"这年用户多做了什么"的对账单，句子必须是用户视角，不许写成"我们证明了什么"。

## 四、编制与节拍

- 国际服并行车道 **不超过 8 扇**（主人的常设令），CN 侧不占该名额、走零扣费通道，两翼同时开工。
- 每季度开工式：先跑吸收尺取未吸收面，再按域切片进账本 `## ORDERS`，交块走 `review/*` 车道枝，权威尖只由号令者经落地门移动。
- 每季度收工式：对账表补 `absorbed_on` 列（写吸收代的 40 位），尺重跑一次，绿了才许写"本季完成"。
- 撞同一枚热文件的枝（现尖面上最挤的是 `backend/app/main.py`、`backend/app/schemas.py`、`contracts/openapi.yaml`、`frontend/src/api/citynexus.ts`、`backend/app/agent/runtime.py`）一律排队，不许同时发。

## 五、这份计划自己怎么被推翻

如果某季度实测发现：未吸收面在涨、或已声明吸收的文件被后续落地删掉，
`live_checks/revolution_absorption_check_r1.py` 会以退出码 9 报退化，当季里程碑不算完成，
计划必须改写这一节而不是把尺调松。

