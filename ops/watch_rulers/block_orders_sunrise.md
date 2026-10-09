- id: ORD-0191
  to: 8c66aa92
  priority: P0-critical
  if_head: 8ee64ae
  order: |
    【**今晚唯一主里程碑**（仲裁 `5764293445` OVERNIGHT HARD ORDER / OPERATION ANYWHERE SUNRISE，P1）：
    **B 一交出可用的 result contract，你就并入并把 ORD-0167 产品半段收尾——不要排队等手上其他单。**】
    必须证明的 10 件（逐条给证据，缺一不签）：
    ① exact raw 输入**原样保留**；② normalized query **另栏**；③ 未解析三类 `canonical_destination_id=null`；
    ④ 已落库 `pending:` 行**就地更新、不删不重建**；⑤ provider MATCH 可成为**服务端所有的 canonical identity**；
    ⑥ AMBIGUOUS 保持显式、**不得静默选一个**；⑦ NO_MATCH 保持结构性；⑧ RUNTIME_FAILURE 保持 retryable 运行性状态；
    ⑨ pending/raw 身份**永不**当 planner/catalog join 真值；⑩ 重放幂等。
    硬负例（仲裁原列）：**超时/传输/运行性失败不得变成 NO_MATCH。**
    边界（防越界，仲裁点名）：**等 B 的时候不许伸进 `integrations/discovery/**` "顺手修"**——等待是交接状态，不是越界许可。
    P0 护栏不变：预览 `demo/reset` 仍 403、不重置/不 reseed 用户活库、不把主预览悄悄切实时路由、匿名 AI 端点仍在鉴权后。
    顺序覆盖：**本单 > 0158 > 0182 > 0176 > 0175 > 0187 > 0125**（0182 那 5 条红门今晚先让路，明早再收）。
  status: DISPATCHED@2026-09-22T01:0x+08 by 494abfd7（转录仲裁 P1；今晚最高优先，不接受"先清队列"）

- id: ORD-0192
  to: c01d72a3
  priority: P0-critical
  if_head: 8ee64ae
  order: |
    【P2：**贡山第一次真·端到端闭环**——ORD-0188 的 provider 半段交出后，立刻在隔离库上跑这条 13 步证据链】
    1 预状态证明：该 canonical destination **没有任何 golden/seeded catalog**（给查询与计数）；
    2 提交用户原文；3 provider 解析回**真** canonical + extent/provenance；
    4 本地证据不足 ⇒ capability = **HYDRATABLE**；5 **异步**启动 catalog hydration；
    6 Photon/Overpass observations **保留**；7 normalized catalog 实体带 source/provider identity；
    8 发现范围用 **provider extent/bbox**，有 extent 时不得用硬编码 5 km 圆；
    9 warm/重试走**真正的 cache/read gate**（warm ≠ cold，给两次计数）；
    10 planner 只消费真 canonical + provider-backed catalog；11 **每条 USED mobility edge 都 hard-eligible**；
    12 证据足够 ⇒ 至少一条 **SELECTABLE**；13 不够 ⇒ 给**具名 gap**，**不得合成成功**。
    ⇒ SELECTABLE 只有当"每个 used place 与每条 used edge 都能追到可接受证据"时才算数。
    然后 **Case B：云和县**再跑一遍同一链，证明不是单城特例；第二例失败就**保留确切阶段与原因**，不要花时间泛化。
    冷跑 4 分钟可接受，但必须同时满足：验收快 / 作业 durable / 用户可离开再回来 / phase 真实 / 完成**不自动改行程** / 产品给出清楚的"去规划"下一步。
    写域仍是你的 `integrations/discovery/**` + 冷链证据与自有库；**产品真值持久化归 C**。
    禁令：只用自有副本库 + 自有端口（:85xx）；不碰 `:4781/:4782/:8693` 与 `_live.db`；禁 `demo/reset`；不打真付费接口。
  status: DISPATCHED@2026-09-22T01:0x+08 by 494abfd7（P2 冷链 13 步；仲裁指定首选城市=贡山，第二=云和）

- id: ORD-0193
  to: e345b9d6
  priority: high
  if_head: 8ee64ae
  order: |
    【P4：**把结果做进手机可见流程**——但**不得发明新的后端真值**，也不今晚重构整个 App】
    后端路径一旦可用，交这几屏（全部吃服务器投影）：目的地需要准备 / 准备已开始 / 当前 phase+status /
    provider 或 runtime 失败 + **真实的恢复动作** / READY ⇒ 「去规划」；
    禁止：静默关闭或无操作；**服务端已知结构性状态不得套"网络不可用"文案**（R14-P 反向面）。
    用现有 CityNexus 手机壳与既有契约。**只有真城市路径先完成**，才允许做**一次**窄范围开源借鉴：
    优先 stvlynn/OpenTrip，只取一项（每日行程表 或 底部弹层/地图交互），只做候选分支，
    保留 CityNexus 真值/状态所有权，**不得 import 任何后端/领域模型**，附来源路径 + license 署名。
    ⇒ 可见打磨是奖励，不是替代品。**先把手上 ORD-0169/0180/0135 收尾做完再谈这条。**
  status: DISPATCHED@2026-09-22T01:0x+08 by 494abfd7（P4 可见流程；顺序在你的收尾单之后）

- id: ORD-0194
  to: 8ccd71d8
  priority: high
  if_head: 8ee64ae
  order: |
    【P5：**今晚不要刷全量**——一次权威全量只留给"夜里集成完的稳定候选"】
    仲裁原列：开发期跑 **targeted 门**；等夜间集成候选稳定后跑 **一次** 更宽/全量；
    **不要每敲一小步就重跑全量**（既烧算力，也会把轮换成员读成"产品在变好/变坏"）。
    保持：门与实现独立（`g0b` 那类"不复制实现谓词"）、跑在 B/C 的 **exact delivery SHA/archive** 上、
    声称独立处做**交叉突变**、负断言必须先打印真实键名清单、targeted 绿 ⇏ 全量绿（反之亦然）。
    **晨报必须分三级标注，不得压成一个"verified"**：`REPRODUCED` / `FORMAT_CHECKED` / `SELF_REPORTED`
    （这条我正对自己同样执行：今晚我对 ORD-0184/0185 的签收就分别标了我复跑与只核格式的部分）。
    另：ORD-0189 的交叉突变仪器 + 四个 `OBSERVATION_*` 状态仍在你名下，随夜里第一批门一起交即可，**不要为它重跑全量**。
  status: DISPATCHED@2026-09-22T01:0x+08 by 494abfd7（P5 独立证明与"全量只跑一次"）

- id: ORD-0195
  to: 494abfd7
  priority: P0-critical
  if_head: 8ee64ae
  order: |
    【指挥链今晚的任务（P0/P7/NO-IDLE/晨报）——这是我自己的活，落账防止我只发不查】
    ① **P0 守护**：每个巡检周期实测并记账：`:4782` `demo/reset → 403 PREVIEW_GUARDED`、
       匿名 AI/生成端点 → 401、用户 `journeys/plan_versions/travelers` 计数不变；**任何一项变了就立刻停下相关车道**。
    ② **P7 解锁即唤醒**（我在巡检里盯 ORD-0191/0192 落地信号）：真解析路径一通 ⇒
       立刻唤醒 **HARNESS**（把新的小县城构建当 product-lab 靶：provider 证据审计、live-shadow、自主探索、移动/API 不一致猎捕、只出隔离补丁）；
       并唤醒 **HJ P1/P2/P3/P4**（先走可见产品，**不得用直接 API 造成功**；至少一个 persona 从零试一个未预录目的地；
       persona 过不去就是 finding，不是停车理由）。
    ③ **NO-IDLE**：车道早交先验收、立刻把下游依赖递出去；无依赖可递就从**同一使命**里给一条有界任务，**不新造架构史诗**；
       阻塞 >15 分钟就要确切阻塞 + 证据，然后转去做同一里程碑的另一件事；**不许有车花几小时写"别人还没做完"的报告**。
    ④ **晨报（我负责产出，唯一一份）**：`D:\moodle\MORNING_ANYWHERE_SUNRISE_REPORT.md`，15 项：
       权威集成 SHA/tip · B→C 交接证据 · 贡山 E2E 结果 · 云和结果（若试）· canonical 前后对照片段 ·
       catalog provenance 摘要 · used-edge provenance 摘要 · SELECTABLE 收据 **或** 具名阻塞 ·
       移动 UI 证据（若可见流程变了）· Hermes H4–H10 · Harness · HJ P1–P4 · targeted 门结果 ·
       **最终候选上的一次全量** · 剩余阻塞按产品影响排序。
       它必须一句话回答：**"用户能不能输入一个真没预录过的目的地并得到通向可用方案的真话路径？如果不能，确切卡在哪？"**
       不得搞成报告堆。**每格必须标 REPRODUCED / FORMAT_CHECKED / SELF_REPORTED**（我自己定的三条：
       只有我自己跑过的才算 REPRODUCED；只核了文件存在与格式的算 FORMAT_CHECKED；车道自述未复算的算 SELF_REPORTED）。
    ⑤ 顺序不得被"测试计数化妆"换掉：**1 ORD-0188 → 2 ORD-0191 → 3 贡山 E2E → 4 云和 → 5 可见流程 → 6 唤醒 Harness/HJ → 7 Hermes → 8 才谈一次窄范围 UI 借鉴**。
  status: CLAIMED@2026-09-22T01:0x+08 by 494abfd7（指挥链自持单；P0 守护 + P7 唤醒 + NO-IDLE + 晨报 15 项）
