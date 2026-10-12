# Revolution 轮次 → 能力 → 落点 地图（ORD-0589）

本枚由车道「地图工」产出。目的只有一个：第五年要把 `revolution` 这个词消解进主线语汇，靠的是这张图。
它不裁定该不该吸收，只回答**某一轮到底想让用户做到什么、这件事在现尖上该接在哪**。

- 现取权威尖：`refs/heads/mirror/integration-frontend-apple-pass1` = `d7776c6a7730e05ba32e7cb1e2e733f5099a7433`
  （命令原样 `git -C D:/moodle/CityNexus ls-remote origin refs/heads/mirror/integration-frontend-apple-pass1`；本文件所有「现尖坐标」都在这一枚上现读）
  上一代 `b63b364dce4bc1adef9cd02e121df372117b980a` 到这一代只多两枚路径（`backend/app/execution/route_session_contract.py` 与它的测试；命令原样 `git diff --name-only` 现读）：本文件引的 155 枚路径零命中那两枚，且尖侧那 50 枚路径跨这两代 blob 逐枚相同，所以坐标逐枚仍然成立。
- 代表枝（族A 累积线）：`refs/heads/gpt/revolution-r33-open-world-journey-adaptation` = `a5a2f1096e0fbd806acd8be134fe8fb6095ad1a9`
  （对账行 `docs/REVOLUTION_ABSORPTION_MANIFEST.tsv:29`；本文件所有「轮次文档坐标」都在这一枚的 blob 上现读，行号是 `git cat-file blob` 出来的原文行号）
- 零产品字节：本文件之外一个字节没动，权威枝一笔没推。

## 零、先说清楚轮次文档有两处之家

1. **代表枝上那一大面**：`REVOLUTION_R*.md` 与 `REVOLUTION_REALTRIP_R*.md` 共 190 枚 blob（`git ls-tree -r` 实测），形态是 TASKBOOK（任务书）与 RESULT（结果纸）成对或单独存在。这是本表逐行取锚的那一面。
2. **每轮自己的枝上还有一代更早的任务书**：形如 `revolution/R14_FACT_DRIVEN_PLANNER_MISSION.md`、`CODEX_START_HERE_R14.md`。代表枝上**没有**这两枚（`git ls-tree -r a5a2f1096e0fbd806acd8be134fe8fb6095ad1a9` 里 `MISSION` 零命中）；它们在 `refs/heads/gpt/revolution-r14-fact-driven-planner-20261001` 上，本车道 fetch 后实测到（枝尖 `21ee4be0d62ae85f2e68d4e45cc39524ee56fdd5`）。37 枚 `refs/heads/gpt/revolution*` 枝的名单与归属结论在 `docs/REVOLUTION_ABSORPTION_MANIFEST.tsv`，本车道未逐枚枚举那 37 枚上的 MISSION 文件——要逐枚清点请另开单。

这条区分很重要：**CN 侧那份摘要草稿（CMDR-DELIVER-0598-CNDRAFT）的「文档」列引的是第 2 家的路径，不是第 1 家**。它的「土话」列本车道当作措辞对照用过，但每一行的判据来自第 1 家文档的原文行。

## 一、八个能力族与主线叫法（对齐五年计划那张能力表 `docs/REVOLUTION_ABSORPTION_FIVE_YEAR_PLAN.md:34`）

| 主线叫法 | 覆盖轮次 | 现尖上这一族的代表坐标 |
|---|---|---|
| 真地点与来源真值 | REALTRIP R5–R11、REALTRIP 恢复轮、R15、R88 | `backend/app/integrations/discovery/provider_identity.py:89` |
| 决策代理 | R14、R20、R21、R25、R26、R43、R44、R46、R47、R51 | `backend/app/agent/runtime.py:63` |
| 主动观察 | R16、R17、R18、R19、R34、R35、R36、R48、R49、R50、R55 | `backend/app/agent/autorun.py:171` |
| 中断恢复 | R28、R29、R30、R31、R32、R33、R59、R60、R61、R62 | `backend/app/db/models.py:789` |
| 集体协同 | R27、R45、R57、R58、R63、R64、R69、R70、R71、R72、R73、R74、R75、R76、R78、R79 | `backend/app/db/models.py:1277` |
| 行程执行续跑 | R9、R10、R11、R37、R38、R39、R40、R41、R42、R52、R53、R54、R56、R65–R68 | `backend/app/execution/clock.py:14` |
| 私享外出（零目录起步） | R83–R109（除已归他族者） | `backend/app/integrations/discovery/real_city.py:1444` |
| 验证承接 | 每族自带：代表枝对现尖独有的测试面（归 ORD-0591，本表不判） | `live_checks/revolution_absorption_check_r1.py:56` |

## 二、逐轮地图

读法：每行一个轮次。「能力」是这轮想让用户做到的那一句土话；「落点域」是现尖上该接的域；后两列是坐标，枝内锚指代表枝上那份文档的原文行，现尖锚指现尖上该域的代表文件行。

### A. 真实一趟行（REALTRIP 代，R5–R11 与恢复轮）

| 轮次 | 这轮让用户做到什么 | 落点域 | 轮次文档坐标（代表枝内） | 现尖坐标 |
|---|---|---|---|---|
| REALTRIP-R5 | 行程里的地点是真能点选、真来自供应商的，不是列表里摆着好看 | 契约+数据层 | `REVOLUTION_REALTRIP_R5_RESULT.md:5` | `backend/app/db/models.py:467` |
| REALTRIP-R6 | 同一处地点的「身份」和「事实」分得开：谁说的、什么时候说的、能不能采信 | 契约（`/facts/acquire` 现尖无对应路径） | `REVOLUTION_REALTRIP_R6_RESULT.md:1` | `backend/app/db/models.py:335` |
| REALTRIP-R7 | 重跑一次供应商就把那处地点的正典事实刷新，旧值不再冒充新值 | 后端 integrations/discovery | `REVOLUTION_REALTRIP_R7_CANONICAL_PROJECTION_RESULT.md:5` | `backend/app/integrations/discovery/provider_identity.py:89` |
| REALTRIP-R8 | 换季只改窗口就能走同一条真产品路径，authority 不被旧记录顶着 | 后端 integrations/discovery | `REVOLUTION_REALTRIP_R8_WINTER_AUTHORITY_RESULT.md:5` | `backend/app/integrations/discovery/real_city.py:86` |
| REALTRIP-R9 | 两站真挨着时那段「零分钟」是诚实结论，不是算错 | 后端 integrations/mobility | `REVOLUTION_REALTRIP_R9_COLOCATED_EDGE_RESULT.md:5` | `backend/app/integrations/mobility/snapshot_capture.py:57` |
| REALTRIP-R10 | 这段共位事实能在屏上看出来，走的是真执行状态机不是演示态 | 前端 features/execution | `REVOLUTION_REALTRIP_R10_COLOCATED_UI_RESULT.md:5` | `frontend/src/features/execution/V10LiveExecutionPanel.tsx:47` |
| REALTRIP-R11 | 一整趟真行程五站走完，最后一站也是真走完的 | 后端 execution + 数据层 | `REVOLUTION_REALTRIP_R11_COMPLETED_JOURNEY_RESULT.md:5` | `backend/app/db/models.py:542` |
| REALTRIP-恢复轮（R77-R4 权威闸检查点） | 事实还是 UNKNOWN 的旧候选不许被选中，历史证据只算历史 | 契约+数据层 | `REVOLUTION_REALTRIP_RECOVERY_RESULT.md:5` | `backend/app/db/models.py:425` |

### B. 自主控制面（R14–R33）

| 轮次 | 这轮让用户做到什么 | 落点域 | 轮次文档坐标（代表枝内） | 现尖坐标 |
|---|---|---|---|---|
| R14 | 说一句偏好，系统自己判断缺哪门证据、补齐后排真行程、遇事重排 | 后端 agent + planning | `REVOLUTION_R14_AUTONOMOUS_STRATEGY_RESULT.md:133` | `backend/app/agent/gateway.py:173` |
| R15 | 不再拿估算蒙混：系统自己去查官方来源，用户拿到的是真凭据 | 后端 integrations/discovery | `REVOLUTION_R15_TRUTH_SEEKING_OPERATOR_RESULT.md:5` | `backend/app/integrations/discovery/photon.py:24` |
| R16 | 天气、封路这类状况一落地，系统自己醒来改行程 | 后端 agent（值守） | `REVOLUTION_R16_EVENT_DRIVEN_GUARDIAN_RESULT.md:5` | `backend/app/agent/guardian.py:62` |
| R17 | 从天气预报看出未来要出事，提前一步把行程换掉 | 后端 agent/predictive | `REVOLUTION_R17_PREDICTIVE_SELF_HEALING_RESULT.md:5` | `backend/app/agent/predictive.py:54` |
| R18 | 行程还正常时就备好带真凭据的备用方案，风险超线立刻切 | 后端 agent/predictive | `REVOLUTION_R18_ANTICIPATORY_RESILIENCE_RESULT.md:5` | `backend/app/db/models.py:381` |
| R19 | 系统养着几套真材实料的备选行程，自动刷新淘汰，到点才启用 | 后端 planning + 数据层 | `REVOLUTION_R19_LIVING_PLAN_PORTFOLIO_RESULT.md:5` | `backend/app/db/models.py:518` |
| R20 | 事件来了系统自己拍板：启用备用、重排、还是不动，用户不用救场 | 后端 agent + replanning | `REVOLUTION_R20_AUTONOMOUS_BRANCH_ARBITRATION_RESULT.md:5` | `backend/app/replanning/opportunity_window_family.py:47` |
| R21 | 备用不够用时当场现排新行程并走完 | 后端 agent/mission_plan | `REVOLUTION_R21_AUTONOMOUS_FUTURE_SYNTHESIS_RESULT.md:5` | `backend/app/agent/mission_plan.py:1` |
| R22 | 行程空出闲暇，系统自己找靠谱真景点加进去，不硬塞 | 后端 replanning | `output/revolution-r22-delivery-20261003/REVOLUTION_R22_AUTONOMOUS_OPPORTUNITY_RESULT.md:5` | `backend/app/replanning/opportunity_window_family.py:15` |
| R23 | 从你真实游玩的反馈里记住偏好，推荐更对味，随时能抹掉 | 后端 execution/traveler_twin | `output/revolution-r23-delivery-20261003/REVOLUTION_R23_ADAPTIVE_TRAVELER_TWIN_RESULT.md:5` | `backend/app/execution/traveler_twin.py:42` |
| R24 | 那份偏好记忆会随时间变淡，你明说不要就真避开 | 后端 execution/traveler_twin（注意：结果纸文件名写作 R23，交付目录才叫 r24） | `output/revolution-r24-memory-delivery-20261003/REVOLUTION_R23_TWIN_MEMORY_RESULT.md:1` | `backend/app/execution/traveler_twin.py:42` |
| R25 | 通盘比较整段剩余行程，该放掉的空窗先放掉 | 后端 planning | `REVOLUTION_R25_STRATEGIC_HORIZON_STEWARD_RESULT.md:5` | `backend/app/planning/solver_contract.py:57` |
| R26 | 「现在玩还是稍后玩」拿不准时只问你一句，答案不影响就不问 | 后端 agent + 契约 | `REVOLUTION_R26_DECISION_CRITICAL_CLARIFICATION_RESULT.md:5` | `backend/app/agent/runtime.py:63` |
| R27 | 群里两个人对同一个改法有分歧时，系统把两边摆出来主持 | 后端集体面（现尖无 `collective_mediation.py`） | `REVOLUTION_R27_COLLECTIVE_JOURNEY_MEDIATOR_RESULT.md:283` | `backend/app/agent/approval.py:30` |
| R28 | 大家一起点过头的那件事，点头之后系统自己接着办完 | 后端集体面 + 数据层 | `taskbooks/revolution/REVOLUTION_R28_AUTHENTICATED_COLLECTIVE_CONTINUITY_TASKBOOK.md:5` | `backend/app/db/models.py:697` |
| R29 | 当场吵起来时有一台真的调解回合，不靠人肉转达 | 后端集体面 | `REVOLUTION_R29_LIVE_DISAGREEMENT_MEDIATION_RESULT.md:5` | `backend/app/db/models.py:1277` |
| R30 | 共识刚定完世界就变了（consent epoch 被冲击）时，旧授权不会冒充新授权 | 后端集体面 + 数据层 | `REVOLUTION_R30_CONSENT_EPOCH_SHOCK_RECOVERY_RESULT.md:5` | `backend/app/db/models.py:209` |
| R31 | 一处点过头，别处不能拿同一段哈希冒充；权威回执不串味 | 数据层（epoch/provenance；该轮文档不在 `REVOLUTION_` 命名里） | `taskbooks/revolution/R31_EPOCH_INTEGRITY_AUTHORITY_PROVENANCE.md:5` | `backend/app/db/models.py:681` |
| R32 | 同时来两记冲击时恢复不塌成一张孤立的补 | 后端 agent + 恢复面 | `REVOLUTION_R32_AUTONOMOUS_RECOVERY_MESH_RESULT.md:9` | `backend/app/db/models.py:300` |
| R33 | 世界真变了才改行程：外部事实→Agent 选择→行程结果，一条因果链 | 契约 + 前端 execution | `REVOLUTION_R33_OPEN_WORLD_JOURNEY_ADAPTATION_TASKBOOK.md:18` | `backend/app/main.py:13090` |

### C. 行中守夜与出发（R34–R56）

| 轮次 | 这轮让用户做到什么 | 落点域 | 轮次文档坐标（代表枝内） | 现尖坐标 |
|---|---|---|---|---|
| R34 | 出发前那一眼是真的：新鲜外部事实要么说「没变糟」，要么说清变在哪 | 后端 integrations（web/discovery） | `REVOLUTION_R34_LIVE_CONTEXT_WATCH_TASKBOOK.md:21` | `backend/app/integrations/web/searxng.py:29` |
| R35 | 给系统一次「站住使命＋授权信封」，之后它自己盯，不用反复点头 | 后端 agent（mission/guardian） | `REVOLUTION_R35_OPEN_WORLD_GUARDIAN_FUSION_TASKBOOK.md:52` | `backend/app/agent/guardian.py:50` |
| R36 | 守望按行程节奏自适应，不再死板固定频率poll | 后端 agent/autorun | `REVOLUTION_R36_ADAPTIVE_JOURNEY_WATCH_TASKBOOK.md:24` | `backend/app/agent/autorun.py:222` |
| R37 | 我主动交一次位置，系统回答「我在哪、下一步该怎么走」 | 数据层 + 契约 | `REVOLUTION_R37_GROUNDED_PRESENCE_NEXT_MOVE_TASKBOOK.md:51` | `backend/app/db/models.py:1068` |
| R38 | 出发前告我_ready_不_ready_，把不确定的那几条说清楚 | 后端 execution | `REVOLUTION_R38_DEPARTURE_READINESS_TASKBOOK.md:24` | `backend/app/execution/journey_twin.py:9` |
| R39 | 第一段路从哪儿起不再是猜：能用真锚点就用 | 后端 integrations/mobility | `REVOLUTION_R39_GROUNDED_JOURNEY_LAUNCH_TASKBOOK.md:22` | `backend/app/integrations/mobility/runtime.py:77` |
| R40 | 出发地不再是被动推断，用户能显式设定 | 后端 execution + 契约 | `REVOLUTION_R40_LAUNCH_SETUP_TASKBOOK.md:25` | `contracts/openapi.yaml:2760` |
| R41 | 一段路有一份可留存的路线会话，不被反复重算换值 | 后端 execution（该载体已在 d7776c6a 落线，ORD-0593） | `REVOLUTION_R41_ROUTE_SESSION_TASKBOOK.md:44` | `backend/app/execution/route_session_contract.py:28` |
| R42 | 「我出发了」这一句话把执行状态机真的点着 | 后端 execution + 前端 | `REVOLUTION_R42_DEPARTURE_ACTIVATION_TASKBOOK.md:55` | `backend/app/execution/clock.py:14` |
| R43 | 行程里那台操作者自己能动手，不只是记录该动 | 后端 agent | `REVOLUTION_R43_AUTONOMOUS_JOURNEY_OPERATOR_TASKBOOK.md:28` | `backend/app/agent/tool_catalog.py:70` |
| R44 | 外部那颗「大脑」连不上时，事故还活着、回来后接着办 | 后端 agent（可用性） | `REVOLUTION_R44_RESILIENT_OPERATOR_BRAIN_RESULT.md:5` | `backend/app/agent/ai_availability.py:49` |
| R45 | 一台行程级操作者，按你是谁给出不同的集体视图 | 后端集体面 + 前端 execution | `REVOLUTION_R45_COLLECTIVE_JOURNEY_OPERATOR_RESULT.md:5` | `backend/app/schemas.py:1094` |
| R46 | 眼下恢复选项太窄时，Agent 自己去外头找补 | 后端 agent + integrations | `REVOLUTION_R46_OPEN_WORLD_RECOVERY_DISCOVERY_RESULT.md:5` | `backend/app/integrations/discovery/orchestration.py:124` |
| R47 | 改签、退款这类真交易走服务器持有的 saga，不假装办完了 | 后端 commerce | `REVOLUTION_R47_TRANSACTIONAL_JOURNEY_OPERATOR_TASKBOOK.md:23` | `backend/app/db/models.py:645` |
| R48 | 一整天连续的行程执行有单一前台视图，不必拼 | 后端 execution + 前端 | `REVOLUTION_R48_CONTINUOUS_JOURNEY_DAY_OPERATOR_TASKBOOK.md:28` | `backend/app/db/models.py:937` |
| R49 | 往前的几小时提前预警，不等出事了才说 | 后端 agent（predictive） | `REVOLUTION_R49_JOURNEY_AHEAD_PREVENTIVE_OPERATOR_TASKBOOK.md:31` | `frontend/src/features/recovery/V14PreventivePanel.tsx:88` |
| R50 | 夜里断掉的行程，早上有一份交代清楚的收口 | 后端 agent + 数据层 | `REVOLUTION_R50_OVERNIGHT_STEWARD_TASKBOOK.md:27` | `backend/app/db/models.py:1056` |
| R51 | 路上用大白话说一句想改，系统听懂并把它落成真意图 | 后端 agent + 契约 | `REVOLUTION_R51_LIVE_JOURNEY_INTENT_STEERING_RESULT.md:7` | `backend/app/integrations/ai/copilot_contract.py:119` |
| R52 | 只有真需要你点头的事才来找你，其余安静 | 前端 features/agent + 契约 | `REVOLUTION_R52_QUIET_OPERATOR_DECISION_INBOX_RESULT.md:7` | `frontend/src/features/agent/AgentComposer.tsx:46` |
| R53 | 把订单截图、改期短信直接丢进行程，它自己变成真事实 | 后端 integrations/inbox + 前端 | `REVOLUTION_R53_JOURNEY_INBOX_LIVE_CHANGE_INTAKE_TASKBOOK.md:9` | `backend/app/integrations/inbox/vision.py:57` |
| R54 | 两个来源互相打架时不再「后写的赢」，走真核对 | 后端 integrations/inbox + 数据层 | `REVOLUTION_R54_REALITY_RECONCILIATION_TASKBOOK.md:9` | `backend/app/integrations/inbox/semantic_intake.py:50` |
| R55 | 真行程和计划表飘开了，系统从实际打卡/抵达里看出来 | 后端 execution + 数据层 | `REVOLUTION_R55_LIVE_PROGRESS_DRIFT_OPERATOR_TASKBOOK.md:9` | `backend/app/db/models.py:1311` |
| R56 | 已经在路上时位置偏了，能给一条诚实的在途改道建议 | 后端 integrations/mobility | `REVOLUTION_R56_IN_TRANSIT_REROUTE_OPERATOR_TASKBOOK.md:9` | `backend/app/main.py:10535` |

### D. 多人一块儿出门（R57–R82）

| 轮次 | 这轮让用户做到什么 | 落点域 | 轮次文档坐标（代表枝内） | 现尖坐标 |
|---|---|---|---|---|
| R57 | 共享行程里分得清「这是谁的位置」、谁还没到集合点 | 数据层 + 后端 execution | `REVOLUTION_R57_MEMBER_PRESENCE_RENDEZVOUS_OPERATOR_TASKBOOK.md:74` | `backend/app/db/models.py:1068` |
| R58 | 有人赶不上共同那一站时，系统来谈怎么合 | 后端集体面 | `REVOLUTION_R58_SPLIT_GROUP_RECOVERY_NEGOTIATOR_TASKBOOK.md:70` | `backend/app/db/models.py:718` |
| R59 | 「一起调一下」真连到成员应答与授权机器，不断在半路 | 后端集体面 + 恢复面 | `REVOLUTION_R59_COLLECTIVE_GROUP_RECOVERY_CLOSURE_TASKBOOK.md:70` | `backend/app/main.py:13110` |
| R60 | 群体选定的那一次恢复，只能被花掉一次 | 后端集体面（authority 单次消费） | `REVOLUTION_R60_COLLECTIVE_RECOVERY_COMMIT_RECONSENT_RESULT.md:5` | `backend/app/agent/approval.py:55` |
| R61 | 商定过的方案执行不了时，旧决定留档、立刻给新的可选面 | 后端恢复面 | `REVOLUTION_R61_REGROUNDED_COLLECTIVE_RECOVERY_TASKBOOK.md:130` | `backend/app/replanning/feasibility.py:64` |
| R62 | 一次治理过的合流之后，各自能报到、系统认得出真聚上了 | 后端 execution + 前端 execution | `REVOLUTION_R62_GROUP_RECOVERY_FOLLOW_THROUGH_TASKBOOK.md:63` | `frontend/src/features/execution/LiveRecovery.tsx:98` |
| R63 | 明说「我要暂时走开一下」被系统认成成员级意图，不是掉线 | 后端 execution + 数据层 | `REVOLUTION_R63_PLANNED_PARALLEL_GROUP_JOURNEY_RESULT.md:5` | `backend/app/db/models.py:1297` |
| R64 | 分开那段时间里，成员能用自己的账号真跑自己的小任务 | 后端 execution + 前端 | `REVOLUTION_R64_MEMBER_SIDE_QUEST_EXECUTION_TASKBOOK.md:300` | `backend/app/schemas.py:1130` |
| R65 | 限时私探后能重新归队，路上那段只有我自己看得见 | 后端 execution + 契约 | `REVOLUTION_R65_TIMEBOXED_PRIVATE_DETOUR_REJOIN_NAVIGATOR_TASKBOOK.md:20` | `contracts/openapi.yaml:1883` |
| R66 | 还没决定去哪时，系统给出一处有根据、值得顺路去的附近点 | 后端 integrations/discovery | `REVOLUTION_R66_MOMENT_SCOUT_MICRO_ADVENTURES_TASKBOOK.md:120` | `backend/app/integrations/discovery/pipeline.py:10` |
| R67 | 本地目录很薄时，我可以明确要真附近的地点数据，来源如实标 | 契约 + 后端 integrations | `REVOLUTION_R67_OPEN_WORLD_LIVE_MOMENT_SCOUT_TASKBOOK.md:123` | `contracts/openapi.yaml:2257` |
| R68 | 接受完一处私人地点，交接给真能用的导航而不是小示意图 | 后端 integrations/mobility + 前端 | `REVOLUTION_R68_REAL_WORLD_NAVIGATION_HANDOFF_TASKBOOK.md:5` | `backend/app/integrations/mobility/valhalla_http.py:32` |
| R69 | 私探完报告到了集合点，同伴那边收到确认，归队成一条链 | 后端 execution + 数据层 | `REVOLUTION_R69_RENDEZVOUS_HANDSHAKE_TASKBOOK.md:176` | `backend/app/db/models.py:978` |
| R70 | 自己发现的真实地点，能明确邀同伴、对方独立决定去不去 | 后端集体面 + 契约 | `REVOLUTION_R70_BRING_EVERYONE_HERE_INVITATION_TASKBOOK.md:139` | `contracts/openapi.yaml:906` |
| R71 | 被邀的人先知道：临时绕这一步会不会砸掉集合点 | 后端 execution（可行性） | `REVOLUTION_R71_CAN_WE_MAKE_IT_TASKBOOK.md:6` | `backend/app/replanning/protected_commitments.py:19` |
| R72 | 发现→邀请→各自决定→真去→回来，一整条社交可见的新链路走通 | 后端集体面 + 前端 | `REVOLUTION_R72_DISCOVERY_MICRO_GROUP_TASKBOOK.md:53` | `backend/app/db/models.py:1244` |
| R73 | 私下发现的那点东西，能升格成全组共同的下一站 | 后端 integrations/mobility + 集体面 | `REVOLUTION_R73_PROMOTE_DISCOVERY_TO_SHARED_JOURNEY_RESULT.md:37` | `backend/app/integrations/mobility/runtime.py:169` |
| R74 | 主理人可以把某一站的共规划权，限时只授给一个同伴 | 契约 + 数据层 | `REVOLUTION_R74_SCOPED_REAL_GROUP_CO_PLANNING_RESULT.md:12` | `contracts/openapi.yaml:1139` |
| R75 | 普通人发现的东西也能发起改全组行程，但谁能知道由发现者说了算 | 后端集体面 | `REVOLUTION_R75_ANYONE_CAN_SPARK_GROUP_DISCOVERY_RESULT.md:9` | `backend/app/schemas.py:1108` |
| R76 | 后到的同伴不必吃完整历史，只看该看的就能追上来 | 后端集体面 + 前端 | `REVOLUTION_R76_REAL_COMPANION_JOIN_CATCHUP_TASKBOOK.md:50` | `contracts/openapi.yaml:1062` |
| R77 | 追队那张卡能明确要一次定位，并给出到当前集合点的路线 | 后端 integrations/mobility + 契约 | `REVOLUTION_R77_COMPANION_CATCHUP_NAVIGATOR_RESULT.md:11` | `contracts/openapi.yaml:2760` |
| R78 | 成员能广播「我在去的路上」或「需要协调」，绑定当下计划那一版 | 数据层 + 契约 | `REVOLUTION_R78_MEMBER_RENDEZVOUS_COORDINATION_RESULT.md:11` | `backend/app/db/models.py:1277` |
| R79 | 同伴能接住求救交接：一方报位置、一方来寻 | 后端 execution | `REVOLUTION_R79_BUDDY_RESCUE_HANDOFF_RESULT.md:47` | `backend/app/execution/traveler_twin.py:42` |
| R80 | 私下把「我在这」只给来帮我的那个人，两次同意各是各的 | 后端 execution + 契约 | `REVOLUTION_R80_PRIVATE_BUDDY_NAVIGATION_RESULT.md:14` | `contracts/openapi.yaml:2760` |
| R81 | 私享路线有不可篡改的库绑定，且含安全返回那一段 | 数据层 + 后端 integrations | `REVOLUTION_R81_REAL_BUDDY_ROUTE_AND_SAFE_RETURN_RESULT.md:11` | `backend/app/db/models.py:669` |
| R82 | 帮人的那一程真执行，执行完双方归队并各自回执 | 后端 execution + 数据层 | `REVOLUTION_R82_BUDDY_ASSIST_EXECUTION_AND_GROUP_REJOIN_RESULT.md:11` | `backend/app/db/models.py:1311` |

### E. 零目录城市与口袋步行（R83–R109）

| 轮次 | 这轮让用户做到什么 | 落点域 | 轮次文档坐标（代表枝内） | 现尖坐标 |
|---|---|---|---|---|
| R83 | 在真实城市里一点就出发去一处真地点（不靠预置目录） | 后端 execution + integrations | `REVOLUTION_R83_ONE_TAP_LIVE_CITY_ADVENTURE_RESULT.md:5` | `backend/app/integrations/discovery/real_city.py:1444` |
| R84 | 浏览器不给定位时仍有一条诚实的出路（公开地图动作） | 前端 components | `REVOLUTION_R84_REAL_CITY_EMPTY_CATALOG_RESULT.md:13` | `frontend/src/components/JourneyMap.tsx:66` |
| R85 | 目录是零的新城市，可以先给个中心把它 bootstrap 起来 | 契约（bootstrap 门现尖无路径） | `REVOLUTION_R85_ZERO_CATALOG_BOOTSTRAP_RESULT.md:5` | `contracts/openapi.yaml:2247` |
| R86 | 第一次在零地点城市也能起一趟真能出发的行程 | 后端 services + 前端 discovery | `REVOLUTION_R86_FIRST_STARTABLE_REAL_CITY_JOURNEY_RESULT.md:5` | `backend/app/services.py:112` |
| R87 | 真供应商数据进来时，零目录那条路仍然不撒谎 | 后端 integrations/discovery | `REVOLUTION_R87_FIRST_LIVE_CITY_DISCOVERY_RESULT.md:5` | `backend/app/integrations/discovery/real_city.py:86` |
| R88 | 营业时间未知的真地点照样有下一步可做，但不放进权威计划 | 前端 components | `REVOLUTION_R88_REAL_POI_EXPLORATION_WITHOUT_OPENING_PROOF_TASKBOOK.md:7` | `frontend/src/components/PoiCandidateCard.tsx:26` |
| R89 | 普通手机浏览器上，POI 地图能可靠弹出，官方证据看得懂 | 前端 components | `REVOLUTION_R89_MOBILE_REAL_POI_NEXT_ACTION_TASKBOOK.md:11` | `frontend/src/components/RawFactsPanel.tsx:20` |
| R90 | 在零目录城市里私藏三处感兴趣的真实地点 | 后端 execution + 数据层 | `REVOLUTION_R90_PRIVATE_REAL_CITY_EXPLORATION_BOARD_RESULT.md:11` | `backend/app/db/models.py:1378` |
| R91 | 收藏那处一点就能真去看，未知的几项如实挂着 | 前端 components | `REVOLUTION_R91_SHORTLIST_GO_EXPLORE_RESULT.md:11` | `frontend/src/components/CnxMeasuredFacts.tsx:15` |
| R92 | 开了导航、离开再回来，接上的还是我自己那一趟 | 前端 app + 后端 execution | `REVOLUTION_R92_PRIVATE_OUTING_RESUME_TASKBOOK.md:7` | `frontend/src/features/execution/V12AuthoritativeJourneyPanel.tsx:66` |
| R93 | 搜的是我自己选的那座城，私人会话之间不串味 | 后端 anywhere/契约 | `REVOLUTION_R93_EXPLICIT_CITY_CENTER_AND_PRIVATE_SESSION_RESULT.md:11` | `backend/app/anywhere_capability.py:248` |
| R94 | 首次来访者能在公开地图上选一块城市区域就出发 | 前端 features/discovery | `REVOLUTION_R94_PICK_PUBLIC_CITY_AREA_AND_GO_TASKBOOK.md:9` | `frontend/src/features/discovery/RealCityDiscoveryPanel.tsx:168` |
| R95 | 「找到我的城」只是一条提示，中心必须我自己落定 | 前端 features/setup | `REVOLUTION_R95_CITY_JUMP_AND_HONEST_REAL_POI_RESULT.md:5` | `frontend/src/features/setup/JourneyTrialSetup.tsx:234` |
| R96 | 第一次外出能表达口味（想走想坐想安静）拿到有根据的候选 | 后端 integrations/discovery | `REVOLUTION_R96_ONE_TAP_FIRST_OUTING_RESULT.md:5` | `backend/app/integrations/discovery/orchestration.py:124` |
| R97 | 一次给自己排出两站的市内漫步，不再只能跳一个点 | 后端 execution | `REVOLUTION_R97_TWO_STOP_FIRST_CITY_WALK_TASKBOOK.md:13` | `backend/app/execution/journey_twin.py:9` |
| R98 | 两站之间到底走不走得动，有真路线证据而不是直线 | 后端 integrations/provider | `REVOLUTION_R98_REAL_WALKABILITY_TWO_STOP_OUTING_RESULT.md:61` | `backend/app/integrations/provider_config.py:1` |
| R99 | 正在走的时候它会跟着现实调整这一段短步 | 后端 execution | `REVOLUTION_R99_ADAPTIVE_SHORT_WALK_TASKBOOK.md:12` | `backend/app/execution/clock.py:14` |
| R100 | 我私人的两站小行程存得住，能在地图、App、朋友之间带 | 数据层 + 前端 components | `REVOLUTION_R100_POCKET_TWO_STOP_CITY_WALK_RESULT.md:9` | `backend/app/db/models.py:1354` |
| R101 | 朋友公开的散步文本粘过来，变成我自己的私人冒险 | 后端 integrations/discovery | `REVOLUTION_R101_SHARED_WALK_TO_MY_PRIVATE_ADVENTURE_RESULT.md:9` | `backend/app/integrations/discovery/provider_identity.py:76` |
| R102 | 同一条公开身份大家共认，但各自的观测各归各 | 数据层 | `REVOLUTION_R102_FIRST_REAL_SHARED_CITY_OUTING_RESULT.md:9` | `backend/app/db/models.py:425` |
| R103 | 在真城市里搜两处来源可链的候选，做出可分享的外出 | 契约 | `REVOLUTION_R103_REAL_TWO_PLACE_SHAREABLE_CITY_DISCOVERY_RESULT.md:9` | `contracts/openapi.yaml:2257` |
| R104 | 直接点名一座真城市并拿到两站短途外出 | 前端 features/discovery | `REVOLUTION_R104_FIRST_GENUINE_TWO_PLACE_CITY_OUTING_TASKBOOK.md:14` | `frontend/src/features/discovery/DestinationPreparationPanel.tsx:48` |
| R105 | 打公共供应商之前，先看清可不可用、为什么不可用 | 前端 components | `REVOLUTION_R105_REAL_PROVIDER_READINESS_CITY_DISCOVERY_RESULT.md:9` | `frontend/src/components/CnxMeasuredFacts.tsx:15` |
| R106 | 公开发现是「一次、由我同意」的动作，配置就绪不等于查过 | 后端 integrations | `REVOLUTION_R106_FIRST_HUMAN_CONSENTED_PUBLIC_DISCOVERY_RESULT.md:10` | `backend/app/integrations/discovery/real_city.py:48` |
| R107 | 刚搜到的候选直接进我自己的口袋散步 | 数据层 + 后端 integrations | `REVOLUTION_R107_DISCOVERY_TO_MY_POCKET_WALK_RESULT.md:10` | `backend/app/db/models.py:1378` |
| R108 | 存好的两站有 GO MODE，改一站不会把另一站抹掉 | 后端 execution + 数据层 | `REVOLUTION_R108_POCKET_WALK_GO_MODE_RESULT.md:9` | `backend/app/db/models.py:1354` |
| R109 | 走一半发现第二站不行，能人-controlled 就地换掉 | 后端 execution | `REVOLUTION_R109_GO_MODE_STREET_PIVOT_TASKBOOK.md:15` | `backend/app/execution/journey_twin.py:9` |

## 三、缺口：本车道读到的与读不到的

| 事项 | 实测结论 | 判据 |
|---|---|---|
| 代表枝上没有 R1–R4、R12、R13 的轮次文档 | `REVOLUTION_R1/R2/R3/R4_*.md`、`R12`、`R13` 在 `a5a2f1096e0fbd806acd8be134fe8fb6095ad1a9` 的树里零命中；R14 之前那一段的文档之家在每轮自己的枝上 | 命令原样 `git ls-tree -r --name-only a5a2f1096e0fbd806acd8be134fe8fb6095ad1a9` |
| R24 没有以自己轮次号命名的文档 | 交付目录叫 `output/revolution-r24-memory-delivery-20261003/`，里面那份结果纸文件名写作 `REVOLUTION_R23_TWIN_MEMORY_RESULT.md`；按文件名数轮次会把 R24 漏掉 | `output/revolution-r24-memory-delivery-20261003/REVOLUTION_R23_TWIN_MEMORY_RESULT.md:1` |
| R31 的文档不带 `REVOLUTION_` 前缀 | 在 `taskbooks/revolution/R31_EPOCH_INTEGRITY_AUTHORITY_PROVENANCE.md`；只按 `REVOLUTION_R*.md` 收面会漏掉这一轮 | `taskbooks/revolution/R31_EPOCH_INTEGRITY_AUTHORITY_PROVENANCE.md:5` |
| R56、R57、R65、R66、R67、R68、R69、R109 只有任务书、没有结果纸 | 上面 D/E 节各行给的枝内锚就是任务书行；这几轮「能力写清了、 closure 未交」，吸收时不能当已验能力 | 例 `REVOLUTION_R65_TIMEBOXED_PRIVATE_DETOUR_REJOIN_NAVIGATOR_TASKBOOK.md:20`（该轮 RESULT 在同树零命中） |
| 多轮自报 LIVE 面未通（BLOCKED / PARTIAL / NOT_PROVEN） | R33、R84、R97、R104、R105、R106、R107、R32 的结果纸各自写明只到受控/回放下界；这是能力边界，不是文档缺陷 | 例 `REVOLUTION_R33_OPEN_WORLD_JOURNEY_ADAPTATION_RESULT.md:5` |
| `/facts/acquire` 在现尖契约上没有对应路径 | `contracts/openapi.yaml` 全文 grep `facts` 命中的是 capability facts 的描述行，不是路径行；REALTRIP-R6 那一族的落点得改挂 `:2247`/`:2257` | `contracts/openapi.yaml:2247` |
| `backend/app/fact_acquisition.py` 现尖上不存在 | 它在代表枝上有、在现尖上没有；CN 草稿把它当现成路径列了两次，号令者复算已点名，本车道独立复算同判 | `docs/REVOLUTION_ABSORPTION_MANIFEST.tsv:29` |
| 现尖的集体面只有「成员/角色/审批」那一半 | `backend/app/collective_authority.py`、`collective_mediation.py`、`collective_operator.py` 在现尖零命中；D 节 26 轮的共同落点是这三枚模块的家 | `backend/app/db/models.py:1277` |
| 现尖的 execution 只有四枚模块 | `backend/app/execution/` 在现尖上是 `__init__.py`、`clock.py`、`journey_twin.py`、`traveler_twin.py`；B/C/D/E 节大量轮次要往这里新增，逐枚判定归 ORD-0590 | `backend/app/execution/clock.py:14` |

## 四、证据面在哪（不在本表逐轮展开，给归档入口）

| 面 | 枝内位置 | 备注 |
|---|---|---|
| 轮次结果与任务书 | 仓库根 `REVOLUTION_R*.md`、`taskbooks/revolution/`、`output/revolution-r*/` | 本表取锚的那一面 |
| 每轮自己的任务书 | `refs/heads/gpt/revolution-r<NN>-*-2026MMDD` 上的 `revolution/R<NN>_*_MISSION.md`、`CODEX_START_HERE_R<NN>.md` | 实测枚：`refs/heads/gpt/revolution-r14-fact-driven-planner-20261001` |
| 真趟证据 | `evidence/revolution-realtrip/` | 14 枚（`git ls-tree -r --name-only` 计数） |
| 机器回执与 strike 产物 | `output/revolution-r2[2-9]-*/`、`output/revolution-r3[0-2]-*/`、`backend/output/r3*-*-v1.js` | 属五年计划里「不计入吸收面的产物」那一档 |
| 族B 评审产物 | 现尖 `docs/revolution-archive/gpt-assist/`（ORD-0588 已落） | 与本表无重叠 |

## 五、第五年消解时用得到的术语对照

| lab 里的词 | 主线语汇 |
|---|---|
| Revolution / REVOLUTION_C / REVOLUTION_B | 能力名本身（真地点、主动观察、集体协同……见第一节那一列），不再带轮次等级 |
| strike / closure / live strike | 一次真跑通的用户路径验收 |
| taskbook / result 文档对 | 需求卡与验收记录 |
| RecoveryEpoch、consent epoch | 授权批次（一次点头只覆盖那一批事实） |
| Operator / operator_projection | 行程操作者视图 |
| Pocket Walk | 私人两站漫步 |
| Moment Scout | 顺路发现 |
| TEST_PROVIDER / LIVE_PROVIDER / UNVERIFIED | 来源等级（现尖已有这套词表，别再造） |
| GPT remote review / addendum | 外部评审与补记 |

## 六、本枚的边界（自报）

- 本表一百零四行按轮次一行一轮，全部落点在现尖 `d7776c6a7730e05ba32e7cb1e2e733f5099a7433` 上现读；轮次文档的行号是从代表枝 blob 里数出来的原文行号，不是目录行号。
- 「能力」一句是文档正文的转述，不是逐字引用。逐字判据请读那行原文。
- 落点候选只到**域 + 一枚代表文件行**，不是文件级归并方案；execution 域的逐枚三态判定归 ORD-0590，测试面归 ORD-0591。
- 未跑构建、未起端口、未跑后端测试：本枚零产品字节，没有可跑之物。
- 权威枝一笔没推，`docs/REVOLUTION_ABSORPTION_MANIFEST.tsv` 一字节未改；`absorbed_on` 那一列不由本车道点。
