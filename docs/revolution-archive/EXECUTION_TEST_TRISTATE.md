# execution 域测试面三态判定（ORD-0591）

号令者单原文在账本 CMDR-ORDER-0588-0592 段：代表枝独有的测试那一大面里，先只做 execution 域相关那批，逐枚判「现尖可跑 / 需改夹具 / 该作废」，不许改断言换绿，判作废要给原因并说清现尖为什么跑不了它（缺路由、缺字段、还是缺种子）。本件是那一格的回答。

## 一、分母与方法（现读，可复算）

| 事项 | 读数 | 怎么复算 |
|---|---|---|
| 权威尖（本件判定所依据的那一代） | `6b4ae6f34cd62f491d145d6f6744c2fc8f87e58c` | `git -C D:/moodle/CityNexus ls-remote origin refs/heads/mirror/integration-frontend-apple-pass1` |
| 代表枝 | `a5a2f1096e0fbd806acd8be134fe8fb6095ad1a9` | 账本 docs/REVOLUTION_ABSORPTION_FIVE_YEAR_PLAN.md:5 那节点名的族A 代表 |
| 代表枝独有的测试件（尖→枝 diff 状态 A） | 全集 145 枚 | `git diff --name-status 6b4ae6f34cd62f491d145d6f6744c2fc8f87e58c a5a2f1096e0fbd806acd8be134fe8fb6095ad1a9 -- backend/tests frontend/e2e` |
| 其中带 execution 域词的（本件子集） | 64 枚（后端 43、前端 21） | 子串命中 `app.execution.`、`continuous_journey`、`departure_activation`、`in_transit_reroute`、`launch_setup`、`launch_origin`、`route_session`、`shared_walk`、`readiness`、`presence_projection`、`execution_truth`、`execution_clock`、`/execution`、`watch_policy` |

两件事先说清，免得读数被读歪：

1. 本件**不跑测试**。执行面的真跑读数号令者已经跑过，在 `refs/remotes/origin/commander/control` 的 `evidence/cmdr-rep-test-sweep-0620/rep_only_sweep_r1.tsv`（94 行，形制 `COLLECT_ERROR` / `RED_ON_TIP` / `GREEN_ON_TIP`），本件把它作为对拍列逐枚带上，两边不一致的行点名列出，不抹平。
2. 本件是**静态可判性**：从尖与枝的 blob 里解析 import、路由字面量、模型字段、种子出口、前端 test id，逐枚问「尖上有没有」。它回答的是「尖今天能不能跑到它」，不是「它绿不绿」。

解析器的自检臂（红就不出表）：模块级单例 `settings` 必须在尖索引里；未落线的 `backend/app/execution/continuous_journey.py` 必须报缺；尖上确有的 `/api/v1/health` 必须判「有」（正对照）；枝上独有的 `/journeys/{id}/group-presence/route` 必须判「无」（负对照）；`from app.execution import readiness` 这种**子模块形**必须判缺（r3 当年把它当符号、两边都查不到就当没事，造出五枚假绿）；单下划线符号 `_skip_current_activity` 必须判缺；test id 正负对照各一枚。尖在跑批中途移动就整表作废重跑。

## 二、结论（先看这四行）

| 判定 | 枚数 |
|---|---|
| 现尖可跑 | 3 枚 |
| 需改夹具 | 0 枚 |
| 该作废 | 0 枚 |
| 等落线（本件新增第四形，理由见第五节） | 61 枚 |

成因分布（一枚可带多形，27 枚带两形以上）：缺后端模块 32 枚、缺路由 21 枚、缺前端件 21 枚、缺模型类 17 枚、缺种子 7 枚、缺后端符号 4 枚、缺字段 1 枚。

**三句话**：

1. 没有一枚该作废。判作废我只设了一条硬证据线：某个 import 目标在尖上和枝上**都**取不到（死引用）；按这条线跑完全集，命中 0 枚。枝上的测试都还围着枝自己的活代码，废不掉。
2. 没有一枚**只**靠改夹具能救活。带「缺种子」这一形的有 7 枚，但它们同时缺产品侧的东西；把 0 枚「需改夹具」派给车道会白花一轮。
3. 这批的红绝大多数在**产品面未落线**，不在测试面。所以 ORD-0591 的实际产物是下面那张「要先落什么」的阶梯，它能和 ORD-0590 的模块清单直接接上。

## 三、逐枚判定表

枝内坐标按代表枝取回：`git -C D:/moodle/CityNexus show a5a2f1096e0fbd806acd8be134fe8fb6095ad1a9:<路径>`；尖侧坐标一律现读自 `6b4ae6f34cd6`。

| 测试件（枝内 : 行） | 语 | 形制 | 判定 | 成因 | 首要缺项 | 号令者分拣 | 对拍 |
|---|---|---|---|---|---|---|---|
| `backend/tests/r73_replay_server.py:1` | py | 非测试件(夹具/驱动器) | 现尖可跑 | - | - | 不在分拣里 | - |
| `backend/tests/test_r24_adaptive_memory.py:1` | py | - | 现尖可跑 | - | - | RED_ON_TIP | 一致 |
| `backend/tests/test_r86_first_startable_real_city_journey.py:1` | py | - | 现尖可跑 | - | - | RED_ON_TIP | 一致 |
| `backend/tests/test_adaptive_watch_policy.py:6` | py | - | 等落线 | 缺后端模块 | `app.agent.watch_policy` | COLLECT_ERROR／缺 `agent` | 一致 |
| `backend/tests/test_continuous_journey.py:3` | py | - | 等落线 | 缺后端模块 | `app.execution.continuous_journey` | COLLECT_ERROR／缺 `execution.continuous_journey` | 一致 |
| `backend/tests/test_departure_readiness.py:6` | py | - | 等落线 | 缺后端模块 | `app.execution.readiness` | COLLECT_ERROR／缺 `execution` | 一致 |
| `backend/tests/test_grounded_launch_origin.py:6` | py | - | 等落线 | 缺模型类、缺后端模块 | `JourneyLaunchContext` | COLLECT_ERROR／缺 `execution.launch_origin` | 一致 |
| `backend/tests/test_grounded_presence.py:7` | py | - | 等落线 | 缺后端模块 | `app.execution.presence` | COLLECT_ERROR／缺 `execution.presence` | 一致 |
| `backend/tests/test_guardian_phase_policy.py:6` | py | - | 等落线 | 缺后端模块 | `app.agent.watch_policy` | COLLECT_ERROR／缺 `agent.watch_policy` | 一致 |
| `backend/tests/test_in_transit_reroute.py:9` | py | - | 等落线 | 缺模型类、缺后端模块、缺路由 | `RouteAcquisitionOperation` | COLLECT_ERROR／缺 `execution.in_transit_reroute;integrations.mobility` | 一致 |
| `backend/tests/test_launch_setup_projection.py:6` | py | - | 等落线 | 缺模型类、缺后端模块 | `JourneyLaunchContext` | COLLECT_ERROR／缺 `execution.launch_setup` | 一致 |
| `backend/tests/test_overnight_steward.py:3` | py | - | 等落线 | 缺后端模块 | `app.agent.overnight_steward` | COLLECT_ERROR／缺 `agent.overnight_steward` | 一致 |
| `backend/tests/test_progress_drift.py:4` | py | - | 等落线 | 缺后端模块 | `app.execution.progress_drift` | COLLECT_ERROR／缺 `execution.progress_drift` | 一致 |
| `backend/tests/test_r101_shared_walk.py:7` | py | - | 等落线 | 缺后端模块 | `app.execution.shared_walk` | COLLECT_ERROR／缺 `execution.shared_walk` | 一致 |
| `backend/tests/test_r102_shared_city_outing.py:11` | py | - | 等落线 | 缺后端模块 | `app.execution.bootstrap_discovery` | COLLECT_ERROR／缺 `execution.bootstrap_discovery;execution.shared_walk` | 一致 |
| `backend/tests/test_r105_provider_readiness.py:4` | py | - | 等落线 | 缺后端模块 | `app.execution.bootstrap_discovery` | COLLECT_ERROR／缺 `execution.bootstrap_discovery` | 一致 |
| `backend/tests/test_r106_human_consented_public_discovery.py:9` | py | - | 等落线 | 缺后端模块 | `app.execution.bootstrap_discovery` | COLLECT_ERROR／缺 `execution` | 一致 |
| `backend/tests/test_r23_adaptive_traveler_twin.py:11` | py | - | 等落线 | 缺后端符号 | `app.agent.runtime._server_completion_contract` | COLLECT_ERROR | 一致 |
| `backend/tests/test_r27_skip_hygiene.py:22` | py | - | 等落线 | 缺后端符号 | `app.main._skip_current_activity` | COLLECT_ERROR | 一致 |
| `backend/tests/test_r28_execution_truth.py:15` | py | - | 等落线 | 缺后端符号、缺后端模块 | `app.services.SYNTHETIC_LIVE_SELECTION_BLOCKED` | COLLECT_ERROR／缺 `execution.presence;traveler_principal` | 一致 |
| `backend/tests/test_r42_departure_activation_integration.py:6` | py | - | 等落线 | 缺后端模块 | `app.execution.readiness` | COLLECT_ERROR／缺 `execution.readiness` | 一致 |
| `backend/tests/test_r55_live_progress_drift_product.py:13` | py | - | 等落线 | 缺后端模块、缺路由 | `app.traveler_principal` | COLLECT_ERROR／缺 `traveler_principal` | 一致 |
| `backend/tests/test_r57_group_presence_operator.py:11` | py | - | 等落线 | 缺模型类、缺后端模块、缺路由 | `RouteAcquisitionOperation` | COLLECT_ERROR／缺 `agent;execution.group_presence;operator_projection;traveler_principal` | 一致 |
| `backend/tests/test_r60_collective_recovery_apply.py:15` | py | - | 等落线 | 缺模型类、缺后端符号、缺后端模块 | `CollectiveAuthorityReceipt` | COLLECT_ERROR／缺 `collective_authority;collective_operator;recovery_epoch;traveler_principal` | 一致 |
| `backend/tests/test_r62_group_recovery_followthrough.py:24` | py | - | 等落线 | 缺后端模块 | `app.execution.group_recovery_followthrough` | COLLECT_ERROR／缺 `execution.group_recovery_followthrough;traveler_principal` | 一致 |
| `backend/tests/test_r63_planned_separation.py:12` | py | - | 等落线 | 缺模型类、缺后端模块、缺路由 | `JourneyIntent` | COLLECT_ERROR／缺 `agent.journey_intent;traveler_principal` | 一致 |
| `backend/tests/test_r64_member_side_quest.py:16` | py | - | 等落线 | 缺模型类、缺后端模块、缺路由 | `JourneyIntent` | COLLECT_ERROR／缺 `execution;execution.live_moment_scout;integrations.mobility;traveler_principal` | 一致 |
| `backend/tests/test_r76_journey_membership_invitation.py:16` | py | - | 等落线 | 缺模型类、缺后端模块、缺路由 | `JourneyMembershipInvitation` | COLLECT_ERROR／缺 `execution.group_presence;execution.group_recovery_followthrough;traveler_principal` | 一致 |
| `backend/tests/test_r79_buddy_rescue_handoff.py:16` | py | - | 等落线 | 缺模型类、缺后端模块、缺路由 | `JourneyRendezvousBuddyHandoff` | COLLECT_ERROR／缺 `execution.rendezvous_buddy_handoff;traveler_principal` | 一致 |
| `backend/tests/test_r80_private_buddy_route.py:12` | py | - | 等落线 | 缺模型类、缺后端模块、缺路由、缺字段 | `JourneyRendezvousBuddyHandoff` | COLLECT_ERROR／缺 `traveler_principal` | 一致 |
| `backend/tests/test_r81_private_location_binding.py:13` | py | - | 等落线 | 缺模型类、缺后端模块、缺路由 | `JourneyRendezvousBuddyHandoff` | COLLECT_ERROR／缺 `traveler_principal` | 一致 |
| `backend/tests/test_r82_buddy_execution.py:10` | py | - | 等落线 | 缺模型类、缺路由 | `JourneyRendezvousBuddyExecution` | COLLECT_ERROR | 一致 |
| `backend/tests/test_r85_zero_catalog_bootstrap.py:10` | py | - | 等落线 | 缺模型类、缺后端模块 | `MemberLiveMomentScoutReceipt` | COLLECT_ERROR／缺 `traveler_principal` | 一致 |
| `backend/tests/test_r87_first_live_city_discovery.py:153` | py | - | 等落线 | 缺路由 | `/api/v1/journeys/{journey_id}/bootstrap-discovery` | RED_ON_TIP | 一致 |
| `backend/tests/test_r88_real_poi_exploration.py:134` | py | - | 等落线 | 缺路由 | `/api/v1/journeys/{journey_id}/bootstrap-discovery` | RED_ON_TIP | 一致 |
| `backend/tests/test_r89_member_shared_osm_identity.py:127` | py | - | 等落线 | 缺路由 | `/api/v1/journeys/{journey_id}/bootstrap-discovery` | RED_ON_TIP | 一致 |
| `backend/tests/test_r90_private_exploration_board.py:13` | py | - | 等落线 | 缺模型类、缺路由 | `MemberDraftResumeIntent` | COLLECT_ERROR | 一致 |
| `backend/tests/test_r93_explicit_city_center_and_private_session.py:110` | py | - | 等落线 | 缺路由 | `/api/v1/journeys/{journey_id}/bootstrap-discovery` | RED_ON_TIP | 一致 |
| `backend/tests/test_r95_city_jump_and_provenance.py:208` | py | - | 等落线 | 缺后端模块、缺路由 | `app.execution.bootstrap_discovery` | RED_ON_TIP | 相左 |
| `backend/tests/test_r96_intent_driven_first_outing.py:169` | py | - | 等落线 | 缺路由 | `/api/v1/journeys/{journey_id}/bootstrap-discovery` | RED_ON_TIP | 一致 |
| `backend/tests/test_r98_two_stop_walkability.py:9` | py | - | 等落线 | 缺模型类、缺后端模块、缺路由 | `MemberDraftShortlistItem` | COLLECT_ERROR | 一致 |
| `backend/tests/test_r99_adaptive_short_walk.py:9` | py | - | 等落线 | 缺模型类、缺后端模块、缺路由 | `MemberDraftShortlistItem` | COLLECT_ERROR | 一致 |
| `backend/tests/test_route_session_operations.py:12` | py | - | 等落线 | 缺模型类、缺后端模块 | `RouteAcquisitionOperation` | COLLECT_ERROR／缺 `route_session_operations` | 一致 |
| `frontend/e2e/r105-provider-readiness-city-discovery.spec.ts:88` | ts | 真后端 | 等落线 | 缺前端件、缺种子 | `bootstrap-city-label-confirm` | 不在分拣里 | - |
| `frontend/e2e/r107-discovery-to-my-pocket-walk.spec.ts:116` | ts | 桩驱动 | 等落线 | 缺前端件 | `bootstrap-city-label-confirm` | 不在分拣里 | - |
| `frontend/e2e/r108-pocket-walk-go-mode.spec.ts:116` | ts | 桩驱动 | 等落线 | 缺前端件 | `bootstrap-city-label-confirm` | 不在分拣里 | - |
| `frontend/e2e/r35-live-guardian-status.spec.ts:65` | ts | 桩驱动 | 等落线 | 缺前端件 | `live-guardian-check` | 不在分拣里 | - |
| `frontend/e2e/r43-journey-operator.spec.ts:62` | ts | 桩驱动 | 等落线 | 缺前端件 | `journey-operator` | 不在分拣里 | - |
| `frontend/e2e/r48-continuous-day.spec.ts:29` | ts | 桩驱动 | 等落线 | 缺前端件 | `journey-continuous-flow` | 不在分拣里 | - |
| `frontend/e2e/r49-journey-ahead.spec.ts:24` | ts | 桩驱动 | 等落线 | 缺前端件 | `journey-ahead` | 不在分拣里 | - |
| `frontend/e2e/r50-overnight-steward.spec.ts:25` | ts | 桩驱动 | 等落线 | 缺前端件 | `journey-ahead` | 不在分拣里 | - |
| `frontend/e2e/r51-live-journey-intent.spec.ts:63` | ts | 桩驱动 | 等落线 | 缺前端件 | `journey-intent-input` | 不在分拣里 | - |
| `frontend/e2e/r52-operator-attention.spec.ts:44` | ts | 桩驱动 | 等落线 | 缺前端件 | `journey-operator` | 不在分拣里 | - |
| `frontend/e2e/r53-journey-inbox.spec.ts:41` | ts | 桩驱动 | 等落线 | 缺前端件 | `journey-inbox-input (词根 inbox-input 在尖上)` | 不在分拣里 | - |
| `frontend/e2e/r54-reality-conflict.spec.ts:37` | ts | 桩驱动 | 等落线 | 缺前端件 | `journey-operator-attention` | 不在分拣里 | - |
| `frontend/e2e/r55-live-progress-drift.spec.ts:39` | ts | 桩驱动 | 等落线 | 缺前端件 | `journey-ahead-risk` | 不在分拣里 | - |
| `frontend/e2e/r56-in-transit-reroute.spec.ts:263` | ts | 桩驱动 | 等落线 | 缺前端件 | `journey-transit-commitment-risk` | 不在分拣里 | - |
| `frontend/e2e/r57-group-presence.spec.ts:77` | ts | 桩驱动 | 等落线 | 缺前端件 | `journey-group-presence` | 不在分拣里 | - |
| `frontend/e2e/r59-collective-group-recovery-room.spec.ts:230` | ts | 未知 | 等落线 | 缺前端件、缺种子 | `journey-group-recovery` | 不在分拣里 | - |
| `frontend/e2e/r60-group-recovery-apply.spec.ts:283` | ts | 未知 | 等落线 | 缺前端件、缺种子 | `journey-group-recovery` | 不在分拣里 | - |
| `frontend/e2e/r62-group-recovery-followthrough.spec.ts:202` | ts | 未知 | 等落线 | 缺前端件、缺种子 | `group-recovery-confirm-rejoin` | 不在分拣里 | - |
| `frontend/e2e/r63-planned-parallel-journey.spec.ts:205` | ts | 未知 | 等落线 | 缺前端件、缺种子 | `journey-group-presence` | 不在分拣里 | - |
| `frontend/e2e/r64-member-side-quest.spec.ts:4` | ts | 未知 | 等落线 | 缺前端件、缺后端模块、缺路由、缺种子 | `journey-group-presence` | 不在分拣里 | - |
| `frontend/e2e/r82-buddy-assist-execution.spec.ts:93` | ts | 未知 | 等落线 | 缺前端件、缺路由、缺种子 | `journey-buddy-accept` | 不在分拣里 | - |

## 四、等落线的阶梯（要先落什么，落完哪一枚能解锁几枚）

| 成因 | 涉及测试枚数 | 缺项去重后 | 占比最高的几项 |
|---|---|---|---|
| 缺后端模块 | 32 枚 | 29 项 | `app.traveler_principal`（12 枚）, `app.execution.bootstrap_discovery`（6 枚）, `app.agent.watch_policy`（2 枚）, `app.execution.readiness`（2 枚）, `app.execution.presence`（2 枚）, `app.route_session_operations`（2 枚） |
| 缺模型类 | 17 枚 | 23 项 | `符号 app.db.models.RouteAcquisitionOperation`（11 枚）, `符号 app.db.models.JourneyRendezvousBuddyHandoff`（3 枚）, `符号 app.db.models.MemberDraftShortlistItem`（3 枚）, `符号 app.db.models.JourneyLaunchContext`（2 枚）, `符号 app.db.models.RecoveryEpoch`（2 枚）, `符号 app.db.models.JourneyIntent`（2 枚） |
| 缺后端符号 | 4 枚 | 8 项 | `符号 app.agent.runtime._server_completion_contract`（2 枚）, `符号 app.execution.traveler_twin.evidence_decay_factor`（1 枚）, `符号 app.replanning.candidate_evidence.canonical_place_tags`（1 枚）, `符号 app.services._strategy_place_score`（1 枚）, `符号 app.main._skip_current_activity`（1 枚）, `符号 app.services.SYNTHETIC_LIVE_SELECTION_BLOCKED`（1 枚） |
| 缺前端件 | 21 枚 | 167 项 | `前端件 journey-group-recovery`（5 枚）, `前端件 journey-continuous-flow`（4 枚）, `前端件 bootstrap-city-label-confirm`（3 枚）, `前端件 bootstrap-city-result-0`（3 枚）, `前端件 bootstrap-city-search-consent`（3 枚）, `前端件 bootstrap-city-search-query`（3 枚） |
| 缺路由 | 21 枚 | 91 项 | `/api/v1/journeys/{journey_id}/operator`（10 枚）, `/api/v1/journeys/{journey_id}/bootstrap-discovery`（7 枚）, `/api/v1/journeys/{journey_id}/group-presence/route`（5 枚）, `/api/v1/journeys/{journey_id}/bootstrap-discovery/preview`（5 枚）, `/api/v1/journeys/{journey_id}/operator/start`（4 枚）, `/api/v1/journeys/{journey_id}/bootstrap-shortlist`（4 枚） |
| 缺种子 | 7 枚 | 0 项 | - |
| 缺字段 | 1 枚 | 0 项 | - |

读法：`缺后端模块` 与 `缺模型类` 这两档归 ORD-0590（接尖可行性）那条梯；`缺前端件` 归计划里 2027 Q4 那一格（docs/REVOLUTION_ABSORPTION_FIVE_YEAR_PLAN.md:60）；`缺路由` 归 `backend/app/main.py` 那一面（尖上路由全部写在这一枚文件里，现读 140 枚去重路由桩）。

## 五、为什么加了第四形

单上给的三态是「现尖可跑 / 需改夹具 / 该作废」，跑因给的是「缺路由、缺字段、还是缺种子」。实测这批的阻塞点第一枚是**这个 import 目标尖上没有、枝上有**——它既不是夹具问题（改 conftest 不会长出 `app.traveler_principal`），也不是该作废（枝上代码是活的）。号令者那把尺自己也分开了这一形，名字是 `COLLECT_ERROR`（94 行里 77 行是它）。所以我把它单列成「等落线」，而没有塞进三态里——塞进「需改夹具」会让读表的人派车道去改测试，塞进「该作废」会让人删掉落线候选。

## 六、可跑那几枚的真相

- `backend/tests/r73_replay_server.py:1`（py，形制 非测试件(夹具/驱动器)）：静态四类缺项全空；号令者分拣读数是 `不在分拣里`。这一枚不是测试，是 e2e 的夹具驱动器（文件名不以 `test_` 起头），三态对它不适用，列出来只为分母完整。
- `backend/tests/test_r24_adaptive_memory.py:1`（py，形制 -）：静态四类缺项全空；号令者分拣读数是 `RED_ON_TIP`。能收集、能跑，但**红在产品面前**——这正是单上「不许改断言换绿」要保的那类红，它是真缺口，不是测试写坏了。
- `backend/tests/test_r86_first_startable_real_city_journey.py:1`（py，形制 -）：静态四类缺项全空；号令者分拣读数是 `RED_ON_TIP`。能收集、能跑，但**红在产品面前**——这正是单上「不许改断言换绿」要保的那类红，它是真缺口，不是测试写坏了。

号令者那 94 行里 `GREEN_ON_TIP` 只有 1 枚（test_r84_empty_catalog_entry.py），它不带 execution 域词，不在本子集里；所以「execution 域测试面今天有没有一枚绿的」这个问题，现有证据答不出，只能答「静态可判的只有上面这几枚」。

## 七、两边相左的行

- `backend/tests/test_r95_city_jump_and_provenance.py:208`：本件判 等落线（缺后端模块、缺路由，首要缺项 `app.execution.bootstrap_discovery`），号令者分拣判 `RED_ON_TIP`，其成因行写 `E   AttributeError: 'Settings' object has no attribute 'traveler_auth_secret'`。
  两种读法都还活着：要么分拣那一代这枚 import 在尖上（后来被移动掉了），要么本件的 import 判据咬错。复核只用一条命令：`git -C D:/moodle/CityNexus cat-file -e 6b4ae6f34cd6:backend/app/execution/bootstrap_discovery.py`。

对拍总账：一致 41 枚、- 22 枚、相左 1 枚。`不在分拣里` 那些行是前端 e2e——号令者那批是 pytest 面，没覆盖 spec。

## 八、本件自报的边界（静态判据不能告诉你什么）

1. 「尖上逐字没有这枚 test id」不等于「尖上没有这个能力」——组件可以动态拼 id。本件对每枚缺的 id 再查一次词根（末两段），词根在尖上的那类标成弱判：实测 239 项缺 id，其中弱判 1 项（`journey-inbox-input (词根 inbox-input 在尖上)`）。这一类请当作待人工确认，不要当结论。
2. 桩驱动的 spec（`page.route(` 把 `/api/v1/` 全打桩）不需要真库，但也**不需要真后端路由**——本件不把 `page.route("**/…")` 的 glob 当路由缺项，只在它缺前端组件时报缺。
3. 运行期才暴露的失败（provider 超时、时区、数据库锁）静态判不出来；那一类只能看分拣列。
4. 本件按 `6b4ae6f34cd6` 那一代判，尖每动一代整表要重跑（跑批里已装「尖动就作废」那道闸）。
5. 零产品字节：只新增本件与 `EXECUTION_TEST_TRISTATE.tsv` 两枚，账本、现有尺、别人名下的文件都没碰。

