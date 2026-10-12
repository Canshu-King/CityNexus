# execution 域接尖可行性（ORD-0590）

本张只做可行性判定，不改产品码对外行为。所有行号为现读：权威尖与代表枝各从对象库直接取 blob 后解析，不采信任何"我记得"。生成脚本与原始读数见文末「证据工件」。

口径先说清：文中行数一律按 `splitlines()` 计（同一文件用 `wc -l` 复核会少一，末尾没有空行时）；判定与坐标的原始工件是 `dep_report.json`、`closure.json`、`col_gaps.json`、`sig_r6.json`、`wiring.json`、`verdict_r8.json` 六份，本文每个计数都由这些工件现算并断言，不符则本文不生成。

## 1. 事实底（全部现读）

| 读数 | 值 | 现读坐标 |
|---|---|---|
| 权威尖（ls-remote 现取） | `d7776c6a7730e05ba32e7cb1e2e733f5099a7433` | refs/heads/mirror/integration-frontend-apple-pass1 |
| 代表枝（ls-remote 现取） | `a5a2f1096e0fbd806acd8be134fe8fb6095ad1a9` | refs/heads/gpt/revolution-r33-open-world-journey-adaptation |
| 两尖共同祖先 | `4ee14229f80691cf8e5ea913375c0caf83ac02ee` | git merge-base 现算 |
| 代表枝上 `backend/app/execution/` 的文件 | 30 枚 | git ls-tree 现读 |
| 权威尖上同目录的文件 | 5 枚 | backend/app/execution/__init__.py:1 |
| 代表枝对权威尖的 execution 独有模块 | 25 枚，合计 18,484 行 | 两集相减现算 |
| 两侧同名且逐字节相同 | 3 枚：`__init__.py`、`journey_twin.py`、`route_session_contract.py` | blob 现比 |
| 两侧同名但权威尖是更新一代 | 2 枚：`clock.py`、`traveler_twin.py` | backend/app/execution/clock.py:33 |
| 本张干活期间被别的车道接进权威线的 execution 模块 | `route_session_contract.py`（ORD-0593）：落线上那枚与代表枝逐字节相同（现比 blob 一致），另带 101 行它自己的测试 | backend/app/execution/route_session_contract.py:1 |
| 本文开工时现取的尖（同日早一拍） | `1cf2beccb45fcbb9da8a573acaf8f3fe0a37fcd0` | ls-remote 现取 |
| 两尖之间变动的文件 | 206 个，其中 `backend/` 下 2 个 | git diff --name-only 现读 |
| 本文 18 枚行号锚在两尖上的那一行文本 | 18 枚一致 | 逐枚取该行现比 |

尖在本张干活期间移动过（累计 206 个文件变动，其中 `backend/` 下 2 个：`backend/app/execution/route_session_contract.py`、`backend/tests/test_route_session_contract.py`——那是 ORD-0593 接进权威线的一枚与它自己的测试，见上表最后一行；其余变动在 `docs/revolution-archive/` 等面上，是 ORD-0588 与 ORD-0592 的成果）。因为本域的判定全部锚在 `backend/` 的行号上，所以逐枚把 18 枚锚点在本张开工时那枚尖（`1cf2beccb45f`）与现在这枚尖上的那一行文本取出来比对，结果 0 枚漂移、且本张引用的 7 个文件没有一个落在两尖之间的变动集里——也就是说尖这一跳不影响本张任何一条结论，候选枝直接以现取的尖 `d7776c6a7730` 为父。

第 1 项里 `clock.py` 的换代是本轮最容易被误读的一条：权威尖那代多出 `zone_usage` 与 `now_honest`（现读 `backend/app/execution/clock.py:18` 与 `backend/app/execution/clock.py:33`），代表枝那代只有 `now` 与 `freeze`。也就是说 execution 域要的时钟形状，权威尖不但有，而且比代表枝更严；接尖时**必须保留权威尖这一代**，不能被代表枝的旧代覆盖。

## 2. 逐枚三态判定（25 枚）

判定规则：

- **①能直接接**＝传递闭包内没有任何 `app.*` 缺口，落文件即可加载；
- **②要改哪一枚签名**＝所依赖的模块在权威尖存在、权威尖那一行就是缺口，改动点可指名；
- **③现尖根本没有对应形状**＝依赖的整枚模块或整张表在权威尖不存在，无签名可改，只能新建。
- 同时有 ② 与 ③ 阻塞的记作 **②③**，表内两类坐标都给全。

| 模块 | 行数 | 判定 | 阻塞根因（权威尖现读坐标） |
|---|---|---|---|
| `departure_activation.py` | 124 | ①能直接接 | 无：闭包内零 `app.*` 依赖 |
| `location_scope.py` | 3 | ①能直接接 | 无：闭包内零 `app.*` 依赖 |
| `shared_walk.py` | 120 | ①能直接接 | 无：闭包内零 `app.*` 依赖 |
| `truth.py` | 61 | ①能直接接 | 无：闭包内零 `app.*` 依赖 |
| `presence.py` | 187 | ②改签名即可 | 列 LocationObservation.journey_member_id 权威尖 backend/app/db/models.py 该类没声明（调用侧按列名写） |
| `bootstrap_discovery.py` | 4684 | ②③混合 | NominatimGeocoder 调用不接受 ['user_agent']（权威尖 backend/app/integrations/discovery/real_city.py:617）；ValhallaHTTPMobilityProvider 调用不接受 ['test_provider']（权威尖 backend/app/integrations/mobility/valhalla_http.py:32）；backend/app/integrations/discovery/real_city.py 缺符号 PhotonCityGeocoder；权威尖同族 backend/app/integrations/discovery/real_city.py:711；表 MemberDraftPocketWalk 在权威尖整张没有（代表枝 backend/app/db/models.py 有定义）；表 MemberDraftPocketWalkProgress 在权威尖整张没有（代表枝 backend/app/db/models.py 有定义）；表 MemberDraftResumeIntent 在权威尖整张没有（代表枝 backend/app/db/models.py 有定义）；…另 1 条同类，见第 4 节根因表 |
| `group_presence.py` | 921 | ②③混合 | 列 LocationObservation.journey_member_id 权威尖 backend/app/db/models.py 该类没声明（调用侧按列名写）；列 LocationObservation.traveler_id 权威尖 backend/app/db/models.py 该类没声明（调用侧按列名写）；整枚模块 backend/app/agent/journey_intent.py 在权威尖没有；表 JourneyIntent 在权威尖整张没有（代表枝 backend/app/db/models.py 有定义）；表 JourneyRendezvousMemberSignal 在权威尖整张没有（代表枝 backend/app/db/models.py 有定义）；…另 2 条同类，见第 4 节根因表 |
| `member_side_quest.py` | 1195 | ②③混合 | capture_runtime_mobility_snapshot 调用不接受 ['requested_mode']（权威尖 backend/app/integrations/mobility/runtime.py:77）；整枚模块 backend/app/agent/journey_intent.py 在权威尖没有；表 JourneyIntent 在权威尖整张没有（代表枝 backend/app/db/models.py 有定义）；表 JourneyRendezvousMemberSignal 在权威尖整张没有（代表枝 backend/app/db/models.py 有定义）；…另 4 条同类，见第 4 节根因表 |
| `private_buddy_route.py` | 1011 | ②③混合 | LocationObservation 调用不接受 ['traveler_id', 'journey_member_id']（权威尖 backend/app/db/models.py:1068）；整枚模块 backend/app/agent/journey_intent.py 在权威尖没有；整枚模块 backend/app/route_session_operations.py 在权威尖没有；整枚模块 backend/app/traveler_principal.py 在权威尖没有；…另 8 条同类，见第 4 节根因表 |
| `continuous_journey.py` | 290 | ③无对应形状 | 整枚模块 backend/app/agent/watch_policy.py 在权威尖没有 |
| `group_recovery_followthrough.py` | 633 | ③无对应形状 | 整枚模块 backend/app/agent/journey_intent.py 在权威尖没有；表 JourneyIntent 在权威尖整张没有（代表枝 backend/app/db/models.py 有定义）；表 JourneyRendezvousMemberSignal 在权威尖整张没有（代表枝 backend/app/db/models.py 有定义）；…另 2 条同类，见第 4 节根因表 |
| `in_transit_reroute.py` | 667 | ③无对应形状 | 表 RealityConflict 在权威尖整张没有（代表枝 backend/app/db/models.py 有定义） |
| `launch_origin.py` | 415 | ③无对应形状 | 表 JourneyLaunchContext 在权威尖整张没有（代表枝 backend/app/db/models.py 有定义） |
| `launch_setup.py` | 186 | ③无对应形状 | 表 JourneyLaunchContext 在权威尖整张没有（代表枝 backend/app/db/models.py 有定义） |
| `live_moment_scout.py` | 685 | ③无对应形状 | 整枚模块 backend/app/agent/journey_intent.py 在权威尖没有；表 JourneyIntent 在权威尖整张没有（代表枝 backend/app/db/models.py 有定义）；表 JourneyRendezvousMemberSignal 在权威尖整张没有（代表枝 backend/app/db/models.py 有定义）；…另 5 条同类，见第 4 节根因表 |
| `member_place_group_share.py` | 432 | ③无对应形状 | 整枚模块 backend/app/agent/journey_intent.py 在权威尖没有；整枚模块 backend/app/shared_stop_coplanning.py 在权威尖没有；表 JourneyIntent 在权威尖整张没有（代表枝 backend/app/db/models.py 有定义）；…另 11 条同类，见第 4 节根因表 |
| `member_place_invitation.py` | 1968 | ③无对应形状 | 整枚模块 backend/app/agent/journey_intent.py 在权威尖没有；整枚模块 backend/app/shared_stop_coplanning.py 在权威尖没有；表 JourneyIntent 在权威尖整张没有（代表枝 backend/app/db/models.py 有定义）；…另 11 条同类，见第 4 节根因表 |
| `moment_scout.py` | 376 | ③无对应形状 | 整枚模块 backend/app/agent/journey_intent.py 在权威尖没有；表 JourneyIntent 在权威尖整张没有（代表枝 backend/app/db/models.py 有定义）；表 JourneyRendezvousMemberSignal 在权威尖整张没有（代表枝 backend/app/db/models.py 有定义）；…另 4 条同类，见第 4 节根因表 |
| `planned_split_meetup_handshake.py` | 584 | ③无对应形状 | 整枚模块 backend/app/agent/journey_intent.py 在权威尖没有；表 JourneyIntent 在权威尖整张没有（代表枝 backend/app/db/models.py 有定义）；表 JourneyRendezvousMemberSignal 在权威尖整张没有（代表枝 backend/app/db/models.py 有定义）；…另 5 条同类，见第 4 节根因表 |
| `private_buddy_safe_return.py` | 935 | ③无对应形状 | 整枚模块 backend/app/agent/journey_intent.py 在权威尖没有；整枚模块 backend/app/route_session_operations.py 在权威尖没有；整枚模块 backend/app/traveler_principal.py 在权威尖没有；…另 8 条同类，见第 4 节根因表 |
| `progress_drift.py` | 419 | ③无对应形状 | 表 RealityConflict 在权威尖整张没有（代表枝 backend/app/db/models.py 有定义） |
| `readiness.py` | 463 | ③无对应形状 | 整枚模块 backend/app/agent/watch_policy.py 在权威尖没有 |
| `rendezvous_buddy_execution.py` | 718 | ③无对应形状 | 整枚模块 backend/app/agent/journey_intent.py 在权威尖没有；整枚模块 backend/app/traveler_principal.py 在权威尖没有；表 JourneyIntent 在权威尖整张没有（代表枝 backend/app/db/models.py 有定义）；…另 6 条同类，见第 4 节根因表 |
| `rendezvous_buddy_handoff.py` | 885 | ③无对应形状 | 整枚模块 backend/app/agent/journey_intent.py 在权威尖没有；整枚模块 backend/app/traveler_principal.py 在权威尖没有；表 JourneyIntent 在权威尖整张没有（代表枝 backend/app/db/models.py 有定义）；…另 6 条同类，见第 4 节根因表 |
| `rendezvous_coordination.py` | 522 | ③无对应形状 | 整枚模块 backend/app/agent/journey_intent.py 在权威尖没有；整枚模块 backend/app/traveler_principal.py 在权威尖没有；表 JourneyIntent 在权威尖整张没有（代表枝 backend/app/db/models.py 有定义）；…另 3 条同类，见第 4 节根因表 |

按判定汇总（现算）：①4 枚共 308 行；②1 枚共 187 行；②③4 枚共 7811 行；③16 枚共 10178 行。

## 3. 三枚点名文件的对账结果

命令里点名要查 `schemas.py`、`services.py`、`main.py`。实测结论与预设不同，先说不一样的那两条：

**(a) `services.py`：execution 域对它的形状依赖是 零。**

在代表枝上对整个 `backend/app/execution/` 目录 grep `app.services` 与 `app.schemas`，命中 0 枚文件；这 18,484 行的依赖面全部走 `app.db.models`、`app.execution.*` 自身、`app.core.*`、`app.integrations.*`。所以本轮**不需要为 execution 动 `services.py` 一行**。
参考：权威尖 `backend/app/services.py` 现读 2087 行，代表枝上它多出 31 个顶层符号，但那批符号属 strategy/plan 面（权威尖 `backend/app/services.py:1` 起为原有形状），与 execution 无交集。

**(b) `schemas.py`：execution 模块本体不吃它，是 API 落地才需要它。**

| 读数 | 值 | 现读坐标 |
|---|---|---|
| 权威尖 `schemas.py` 行数 | 一千二百五十六 | backend/app/schemas.py:1 |
| 代表枝 `schemas.py` 独有请求/响应模型 | 五十七 枚 | 两侧顶层类相减现算 |
| 其中 execution 路由真正引用的 | 十三 枚 | 权威尖全部没有，见下表 |
| 权威尖上可直接复用、不必新建的 | 二 枚 | backend/app/schemas.py:419 |

可复用的那二枚：`LocationObservationRequest` 在权威尖 `backend/app/schemas.py:419`，`ReplanGenerateRequest` 在权威尖 `backend/app/schemas.py:825`；代表枝把前者用在那条 handoff 路线的位置上报接口上，形状不用改。

缺的那十三枚按权威尖现有类名做最近匹配，结果大都没有同族（匹配分数低即说明不是改名关系）：

```
  CollectiveClarificationAnswer                      paths=1 nearest_on_tip=[('CollectionFolder', 536), ('CollectionItem', 513)]
  ExecutionTruthAttestation | None                   paths=1 nearest_on_tip=[]
  JourneyRendezvousSignalCreateRequest               paths=1 nearest_on_tip=[('JourneyCheckinCreate', 1212), ('JourneyRoleRule', 1108)]
  LiveMomentScoutRequest                             paths=1 nearest_on_tip=[('LuggageContextRequest', 372), ('PoiImportAddRequest', 1182)]
  LiveMomentScoutSelectRequest                       paths=1 nearest_on_tip=[('LuggageContextRequest', 372), ('EdgeDeviceCreateRequest', 431)]
  MemberPlaceGroupShareConsentRequest                paths=1 nearest_on_tip=[('GeneratePlansRequest', 693), ('LuggageContextRequest', 372)]
  MemberPlaceInvitationCreateRequest                 paths=1 nearest_on_tip=[('ReservationImportRequest', 378), ('ReservationDraftPatchRequest', 392)]
  MemberPlaceInvitationFeasibilityPreviewRequest     paths=1 nearest_on_tip=[('TripStudioPreviewRequest', 727), ('ReservationVisionRequest', 387)]
  RendezvousBuddyExecutionReceiptRequest             paths=1 nearest_on_tip=[('ReservationImportRequest', 378), ('ReservationVisionRequest', 387)]
  RendezvousBuddyExecutionWindowRequest              paths=1 nearest_on_tip=[('ReservationVisionRequest', 387), ('ReservationImportRequest', 378)]
  RendezvousBuddyHandoffDecisionRequest              paths=1 nearest_on_tip=[('ReservationVisionRequest', 387)]
  RendezvousBuddyHandoffOfferRequest                 paths=1 nearest_on_tip=[]
  RendezvousBuddyPrivateRouteRequest                 paths=1 nearest_on_tip=[('ReservationImportRequest', 378), ('EdgeObservationRequest', 440)]
```

**(c) `main.py`：路由面接地的真实尺寸。**

| 读数 | 值 | 现读坐标 |
|---|---|---|
| 权威尖 `main.py` 路由 | 一百七十五 条 | backend/app/main.py:1 |
| 代表枝 `main.py` 路由 | 二百六十七 条 | 装饰器解析现算 |
| 代表枝上函数体内引用 `app.execution` 的路由 | 二十七 条 | 现算 |
| 其中 method+path 与权威尖完全相同（真撞面） | 二 条 | backend/app/main.py:9449 |
| 其中权威尖完全没有的新路由 | 二十五 条 | 现算 |
| 权威尖 `main.py` 里现有的 execution 引用 | 三 处 | backend/app/main.py:209 |

撞面那二条要给号令者点名，因为它们落在同一枚热文件上：

- `POST /api/v1/journeys/{journey_id}/activities/{activity_id}/complete`：权威尖 `backend/app/main.py:9449` 已有该路由（响应模型 `JourneyTwinSchema`，见 `backend/app/main.py:9451`）；代表枝 `refs/heads/gpt/revolution-r33-open-world-journey-adaptation` 上的同名路由在 `backend/app/main.py:19220`，体内改接 execution。这是一次**行为改动**不是接枝，本轮不动。
- `POST /api/v1/journeys/{journey_id}/replans`：权威尖 `backend/app/main.py:10933` 已有（`backend/app/main.py:10934` 声明 `response_model=ReplanProposalSchema`）；代表枝那处在 `backend/app/main.py:21014`。同上，本轮不动。

其余二十五条新路由的 path 在权威尖完全没有（含 method 也不撞），落地时是纯新增；它们全部走函数体内延迟 import，所以**接 execution 模块本身不必先动 `main.py`**。

## 4. 阻塞根因去重（接尖的真实工作量）

25 枚模块的阻塞高度重复，去重后只有二类：

### 4a. 权威尖整枚没有的兄弟模块（5 枚，全在 execution 之外）

| 缺的模块 | 被几枚 execution 模块需要 |
|---|---|
| `backend/app/agent/journey_intent.py` | 13 |
| `backend/app/traveler_principal.py` | 5 |
| `backend/app/route_session_operations.py` | 2 |
| `backend/app/agent/watch_policy.py` | 2 |
| `backend/app/shared_stop_coplanning.py` | 2 |

这 5 枚在代表枝 `refs/heads/gpt/revolution-r33-open-world-journey-adaptation` 上都存在，所以它们不是"要新写"，而是**同批要一起接**——execution 与它们构成一个闭包。

### 4b. 权威尖整张没有的表（24 张）

本表第三列的行号是**代表枝 `refs/heads/gpt/revolution-r33-open-world-journey-adaptation` 上**的 `backend/app/db/models.py`，权威尖上没有这些类。

| 表名 | 需要它的 execution 模块数 | 代表枝上的定义行 |
|---|---|---|
| `JourneyIntent` | 13 | backend/app/db/models.py:266 |
| `JourneyRendezvousMemberSignal` | 13 | backend/app/db/models.py:2457 |
| `JourneyRendezvousSignalAcknowledgement` | 13 | backend/app/db/models.py:2510 |
| `RouteAcquisitionOperation` | 13 | backend/app/db/models.py:2331 |
| `MemberSideQuest` | 6 | backend/app/db/models.py:305 |
| `MemberSideQuestReturnReport` | 6 | backend/app/db/models.py:402 |
| `JourneyRendezvousBuddyExecution` | 4 | backend/app/db/models.py:2587 |
| `JourneyRendezvousBuddyExecutionReceipt` | 4 | backend/app/db/models.py:2656 |
| `JourneyRendezvousBuddyHandoff` | 4 | backend/app/db/models.py:2526 |
| `JourneyLaunchContext` | 2 | backend/app/db/models.py:1816 |
| `MemberPlaceGroupShareConsent` | 2 | backend/app/db/models.py:608 |
| `MemberPlaceInvitation` | 2 | backend/app/db/models.py:479 |
| `MemberPlaceInvitationProgress` | 2 | backend/app/db/models.py:563 |
| `MemberPlaceInvitationRecipient` | 2 | backend/app/db/models.py:523 |
| `MemberPlacePromotion` | 2 | backend/app/db/models.py:662 |
| `PrivateBuddyRouteLocationBinding` | 2 | backend/app/db/models.py:2693 |
| `RealityConflict` | 2 | backend/app/db/models.py:2061 |
| `SharedStopCoPlanningGrant` | 2 | backend/app/db/models.py:749 |
| `MemberDraftPocketWalk` | 1 | backend/app/db/models.py:1290 |
| `MemberDraftPocketWalkProgress` | 1 | backend/app/db/models.py:1331 |
| `MemberDraftResumeIntent` | 1 | backend/app/db/models.py:1263 |
| `MemberDraftShortlistItem` | 1 | backend/app/db/models.py:1223 |
| `MemberLiveMomentScoutReceipt` | 1 | backend/app/db/models.py:361 |
| `PlannedSplitMeetupHandshake` | 1 | backend/app/db/models.py:437 |

其中前四张（`JourneyIntent`、`JourneyRendezvousMemberSignal`、`JourneyRendezvousSignalAcknowledgement`、`RouteAcquisitionOperation`）各挡住十三枚模块，是本域最集中的地基；权威尖里与它们最近的现有形状是 `backend/app/db/models.py:813` 的 `JourneyTripContext` 与 `backend/app/db/models.py:1151` 的 `StayGenerationOperation`——同族但不同义，不能当同一张表用。

### 4c. 只需改权威尖某一行就能解开的签名（5 处，现读指名）

| 改动点（权威尖现读坐标） | 内容 | 解开 |
|---|---|---|
| `backend/app/db/models.py:1071` | `LocationObservation` 在 `journey_id` 之后没有 `traveler_id` 与 `journey_member_id`；代表枝那两列在 `backend/app/db/models.py:2153` 与 `backend/app/db/models.py:2156`，可空、additive | `presence.py`、`private_buddy_route.py`、`group_presence.py` |
| `backend/app/integrations/mobility/runtime.py:84` | `capture_runtime_mobility_snapshot` 的参数表止于 `require_explicit_facts`；代表枝同名函数在 `backend/app/integrations/mobility/runtime.py:100` 多一个默认 `None` 的 `requested_mode` | `member_side_quest.py` |
| `backend/app/integrations/discovery/real_city.py:622` | `NominatimGeocoder.__init__` 只收 `client` 与 `base_url`，代表枝调用侧还传 `user_agent` | `bootstrap_discovery.py` |
| `backend/app/integrations/mobility/valhalla_http.py:44` | `ValhallaHTTPMobilityProvider.__init__` 无 `test_provider` 参数（代表枝两处调用点都传） | `bootstrap_discovery.py` |
| `backend/app/integrations/discovery/real_city.py:711` | 权威尖只有 `PhotonCityAnchor`，没有代表枝用的 `PhotonCityGeocoder` 类 | `bootstrap_discovery.py` |

第 1 处与第 2 处都是**加默认值/加可空列**的向后兼容改动，权威尖现有调用方不受影响；第 3、4 处是给构造器加关键字参数，同样向后兼容。

## 5. 最小接枝：已实接并真跑

判定为 ① 的 4 枚（`departure_activation`、`location_scope`、`shared_walk`、`truth`，合计 308 行）已随本文一起接进候选枝 `review/接尖工-0590-r1`，基点是权威尖 `d7776c6a7730` 本体，未动任何热文件。

证明不是"看门绿"，是双臂对照真跑（同一把脚本 `graft_smoke_r1.py`，同一支解释器 3.12.14 + SQLAlchemy 2.0.52 + FastAPI 0.141.1）：

```
ARM A —— 权威尖原样（未接枝）
{
 "arm": "A_tip_as_is",
 "departure_run": "ModuleNotFoundError: No module named 'app.execution.departure_activation'",
 "import_clock": "OK",
 "import_departure_activation": "ModuleNotFoundError: No module named 'app.execution.departure_activation'",
 "import_execution": "OK",
 "import_journey_twin": "OK",
 "import_location_scope": "ModuleNotFoundError: No module named 'app.execution.location_scope'",
 "import_route_session_contract": "OK",
 "import_shared_walk": "ModuleNotFoundError: No module named 'app.execution.shared_walk'",
 "import_traveler_twin": "OK",
 "import_truth": "ModuleNotFoundError: No module named 'app.execution.truth'",
 "location_scope_value": "ERR No module named 'app.execution.location_scope'",
 "rsc_fingerprint_len": 64,
 "rsc_fingerprint_stable": true,
 "rsc_policy_versions": [
  "r41-route-truth-v1",
  "r41-provider-policy-v1"
 ],
 "shared_walk_run": "ModuleNotFoundError: No module named 'app.execution.shared_walk'",
 "truth_run": "ModuleNotFoundError: No module named 'app.execution.truth'"
}

ARM B —— 权威尖 + 五枚接枝
{
 "arm": "B_grafted",
 "departure_fingerprint_len": 64,
 "departure_keys": [
  "activity_id",
  "authority_required",
  "can_confirm_departure",
  "minutes_to_leave",
  "must_leave_by",
  "readiness_state",
  "recommended_action",
  "state",
  "target_title"
 ],
 "departure_state": null,
 "import_clock": "OK",
 "import_departure_activation": "OK",
 "import_execution": "OK",
 "import_journey_twin": "OK",
 "import_location_scope": "OK",
 "import_route_session_contract": "OK",
 "import_shared_walk": "OK",
 "import_traveler_twin": "OK",
 "import_truth": "OK",
 "location_scope_value": "BUDDY_HANDOFF_ROUTE_PRIVATE",
 "rsc_fingerprint_len": 64,
 "rsc_fingerprint_stable": true,
 "rsc_policy_versions": [
  "r41-route-truth-v1",
  "r41-provider-policy-v1"
 ],
 "shared_walk_canonical": "https://www.openstreetmap.org/relation/42",
 "shared_walk_oversize": "rejected",
 "shared_walk_parsed": [
  [
   "node",
   "1234567"
  ],
  [
   "way",
   "7654321"
  ]
 ],
 "truth_history_len": 1,
 "truth_record_kind": "OPERATOR_CONFIRMED_EXECUTION",
 "truth_rejects_bad_kind": "ValueError"
}
```

两臂各读出什么：A 臂（权威尖原样）里判定为 ① 的 4 枚逐个报 `ModuleNotFoundError`，而 `route_session_contract` 与权威尖原有的 `clock`/`journey_twin`/`traveler_twin` 一样直接 `OK`——这就是第 1 节最后那行的用处：ORD-0593 已经把它那一枚落进权威线，本张不重复接。B 臂（权威尖 + 本张接枝）9 个 import 全部 `OK`。

B 臂里 `departure_state` 为 `null` 不是模块读数：那版探针取的是 `activation_state` 键，而该投影返回的键名是 `state`（见同臂 `departure_keys`），取不到就落 `null`。取对键之后的读数单列在下面第 3 条与 `B_extra` 里，探针的这处取键错误没有改写任何实测值。

B 臂的行为读数（不是 import 成功就算数）：

- `truth.append_execution_truth` 写入后历史长度为一，非法 kind 仍被 `ValueError` 拒；
- `shared_walk.parse_shared_walk_text` 从一段文本里解析出 `node/1234567` 与 `way/7654321`，超长文本被 `SharedWalkParseError` 拒；
- `route_session_contract.route_request_fingerprint` 两次同值、长六十四，策略版本读出 `r41-route-truth-v1` 与 `r41-provider-policy-v1`；
- `departure_activation.departure_activation_projection` 在 `must_leave_by` 比 `now` 晚半小时那一例读回 `state=LEAVE_SOON`、`minutes_to_leave=30.0`、`can_confirm_departure=True`、`recommended_action=CONFIRM_WHEN_LEAVING`。
- `location_scope.PRIVATE_BUDDY_ROUTE_LOCATION_SOURCE` 读出 `BUDDY_HANDOFF_ROUTE_PRIVATE`。

这五枚接上后在权威线上暂时无调用方（没有动 `main.py`），属"先接形状、后接行为"，与命令里"不改产品码的对外行为"一致。

## 6. 建议的落地顺序

1. 本轮：4 枚 ① 已接（本文候选枝）。零热文件触碰；`route_session_contract.py` 已由 ORD-0593 单独落线，本张不再重复接它。
2. 第二批（要动权威尖三处向后兼容签名，请号令者裁定）：`backend/app/db/models.py:1071` 补可空二列 + `backend/app/integrations/mobility/runtime.py:84` 补默认参数 + `backend/app/integrations/discovery/real_city.py:622` 与 `backend/app/integrations/mobility/valhalla_http.py:44` 补关键字参数 ⇒ 解锁 `presence.py`、`member_side_quest.py` 的签名面、并把 `bootstrap_discovery.py` 的构造面清到只剩新表。
3. 第三批（地基，必须成批）：5 枚兄弟模块与 24 张表同批进线；`JourneyIntent` 等前四张表落下去之后，③ 那 16 枚里大部分只在等它们。
4. `main.py` 的二十五条新路由放最后，且要与 ORD-0591 的测试面同期落，否则新路由没有回归网。

## 7. 本张已知毛病与尺的自纠

本轮的签名尺迭代过三代，前两代各错一次，错都由我自己复跑时抓出（下列计数取自落盘的 `sig_findings.json` 与 `sig_r6.json`，中间那代的输出没单独落盘，所以这里不给它的计数）：

- 第一代按 7 条读数报缺口，其中 2 条是类名跨模块撞车：`Place` 在 `backend/app/db/models.py` 与 `backend/app/integrations/discovery/real_city.py` 各有一枚，旧尺按类名单键索引，拿 provider 侧那枚的字段判 ORM 那枚。改为按（模块, 类名）双键后，权威尖 `backend/app/db/models.py:467` 的 `Place` 实测具备 `external_id`, `latitude`, `longitude`, `opening_hours_json`, `tags_json`, `metadata_json`, `updated_at` 全部 7 列，误报当场撤销。
- 第二代是 `@dataclass` 盲区：`DiscoveryCandidate` 没有显式 `__init__`，旧尺把允许参数集当空集，把它整类误报；改为无 `__init__` 时回退取类体注解字段后，权威尖 `backend/app/integrations/discovery/real_city.py:587` 那枚的调用全部判为可用。

终版剩 5 条读数、4 个根因：

| 调用点 | 被拒参数 |
|---|---|
| `LocationObservation` | `traveler_id`, `journey_member_id` |
| `NominatimGeocoder` | `user_agent` |
| `ValhallaHTTPMobilityProvider` | `test_provider` |
| `capture_runtime_mobility_snapshot` | `requested_mode` |

`LocationObservation` 那一条有第二把尺独立印证：列级缺口由 AST 属性访问扫描（`cols_r4.py`）单独给出，与构造器扫描（`sigs_r6.py`）是不同代码路径，两者各自指到 `backend/app/db/models.py:1068`。

另一条口径提醒：第 3 节 (a) 的"零依赖"是对 `backend/app/execution/` 目录的 grep 现读结果，不是对整枝的结论——`main.py` 与测试树里当然还会同时用到 services 与 schemas。

## 8. 证据工件

| 工件 | 用途 |
|---|---|
| `review/jiejian/execution_feasibility_probe_r2.py` | 一把自包含的尺：现取两尖、算独有面、闭包、列级与签名级缺口、三态表、API 接线面 |
| `review/jiejian/graft_smoke_r1.py` | 第 5 节那两臂的探针（指向任一树，用 `PYTHONPATH` 起它） |
| `review/jiejian/README.md` | 复现命令与口径 |

入库的就这三份。开发过程中另有过几版中间尺（`dep_probe_r1`、`closure_r2`、`cols_r4`、`sigs_r5/r6`、`wiring_r7`、`verdict_r8`、`gen_doc_r9`）与它们的 JSON 工件留在本机临时目录，没有入库——它们的结论已全部由 `execution_feasibility_probe_r2.py` 一把复现，第 2、3、4 节的每个数它都能重新打印；两臂原文抄在第 5 节。这样入库的工件不会带着本机绝对路径变成跑不起来的东西。
