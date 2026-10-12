# execution 域接尖可行性三态表（ORD-0590）

车道「地图工」产出。判的是第一年 Q1 那一域：代表枝 `backend/app/execution/` 的 **29 枚**模块，逐枚问「它要接的形状，现尖上有没有」。允许零产品字节交回，本枚就是零产品字节。

- 现取权威尖：`refs/heads/mirror/integration-frontend-apple-pass1` = `b68f381712abd9207b5ecd7625d18d0883838459`（命令原样 `git -C D:/moodle/CityNexus ls-remote origin refs/heads/mirror/integration-frontend-apple-pass1`）。
- 代表枝：`refs/heads/gpt/revolution-r33-open-world-journey-adaptation` = `a5a2f1096e0fbd806acd8be134fe8fb6095ad1a9`（对账行 `docs/REVOLUTION_ABSORPTION_MANIFEST.tsv:29`）。
- 判据：模块自己字节里每一条 `from app.X import a, b` / `import app.X` / `schemas.Y` / `services.z` 都算「它要接的形状」；到现尖那一代逐枚查该文件在不在、该 class/def 在不在，行号现读。
- 三态之外还有一格：`prod imports` = 现尖那一代里 import 这枚模块的非测试文件数。CMDR-RULING-0607 要的正是这一格，所以它按 `app.execution.<模块名>` 逐枚 grep，不按词面。

## 一、判语汇总

- 能直接接（形状齐）：3 枚
- 要改哪一枚签名（现尖那枚文件里缺符号）：0 枚
- 现尖根本没有对应形状（整枚 app 模块不在线上）：18 枚
- 这枚路径已在现尖（另一代或同代，见blob列）：5 枚
- 零 app 形状依赖（可独立 import，但仍没有入口）：3 枚

## 二、逐枚三态表

| 模块（代表枝内） | 行数 | 要接的形状 | 缺什么（逐枚点名） | 三态判语 | 枝内锚 | 现尖锚 | prod imports |
|---|---|---|---|---|---|---|---|
| `bootstrap_discovery` | 4685 | 1 项，命中 1 | — | 能直接接（形状齐） | `backend/app/execution/bootstrap_discovery.py:26` | `backend/app/core/config.py:105` | 0 |
| `clock` | 36 | 0 项，命中 0 | blob 两代不同 | 这枚路径已在现尖（另一代或同代，见blob列） | `backend/app/execution/clock.py:1` | `backend/app/execution/clock.py:1` | 6 |
| `continuous_journey` | 291 | 6 项，命中 4 | 现尖没有模块 `app.execution.presence`（要 `presence_projection`）；现尖没有模块 `app.execution.readiness`（要 `departure_readiness_projection`） | 现尖根本没有对应形状（整枚 app 模块不在线上） | `backend/app/execution/continuous_journey.py:13` | `docs/REVOLUTION_ABSORPTION_MANIFEST.tsv:29` | 0 |
| `departure_activation` | 125 | 0 项，命中 0 | blob 同值 | 这枚路径已在现尖（另一代或同代，见blob列） | `backend/app/execution/departure_activation.py:1` | `backend/app/execution/departure_activation.py:1` | 0 |
| `group_presence` | 922 | 3 项，命中 1 | 现尖没有模块 `app.execution.location_scope`（要 `PRIVATE_BUDDY_ROUTE_LOCATION_SOURCE`）；现尖没有模块 `app.agent.journey_intent`（要 `intent_is_active`） | 现尖根本没有对应形状（整枚 app 模块不在线上） | `backend/app/execution/group_presence.py:26` | `docs/REVOLUTION_ABSORPTION_MANIFEST.tsv:29` | 0 |
| `group_recovery_followthrough` | 634 | 2 项，命中 1 | 现尖没有模块 `app.execution.group_presence`（要 `rendezvous_target`） | 现尖根本没有对应形状（整枚 app 模块不在线上） | `backend/app/execution/group_recovery_followthrough.py:17` | `docs/REVOLUTION_ABSORPTION_MANIFEST.tsv:29` | 0 |
| `in_transit_reroute` | 668 | 2 项，命中 1 | 现尖没有模块 `app.execution.location_scope`（要 `PRIVATE_BUDDY_ROUTE_LOCATION_SOURCE`） | 现尖根本没有对应形状（整枚 app 模块不在线上） | `backend/app/execution/in_transit_reroute.py:16` | `docs/REVOLUTION_ABSORPTION_MANIFEST.tsv:29` | 0 |
| `journey_twin` | 40 | 0 项，命中 0 | blob 同值 | 这枚路径已在现尖（另一代或同代，见blob列） | `backend/app/execution/journey_twin.py:1` | `backend/app/execution/journey_twin.py:1` | 0 |
| `launch_origin` | 416 | 2 项，命中 1 | 现尖没有模块 `app.execution.location_scope`（要 `PRIVATE_BUDDY_ROUTE_LOCATION_SOURCE`） | 现尖根本没有对应形状（整枚 app 模块不在线上） | `backend/app/execution/launch_origin.py:23` | `docs/REVOLUTION_ABSORPTION_MANIFEST.tsv:29` | 0 |
| `launch_setup` | 187 | 3 项，命中 1 | 现尖没有模块 `app.execution.launch_origin`（要 `grounded_launch_origin`）；现尖没有模块 `app.execution.location_scope`（要 `PRIVATE_BUDDY_ROUTE_LOCATION_SOURCE`） | 现尖根本没有对应形状（整枚 app 模块不在线上） | `backend/app/execution/launch_setup.py:19` | `docs/REVOLUTION_ABSORPTION_MANIFEST.tsv:29` | 0 |
| `live_moment_scout` | 686 | 10 项，命中 4 | 现尖没有模块 `app.execution.group_presence`（要 `_member_in_force`）；现尖没有模块 `app.execution.group_presence`（要 `planned_separation_for_member`）；现尖没有模块 `app.execution.member_side_quest`（要 `_fresh_member_observation`）… | 现尖根本没有对应形状（整枚 app 模块不在线上） | `backend/app/execution/live_moment_scout.py:16` | `docs/REVOLUTION_ABSORPTION_MANIFEST.tsv:29` | 0 |
| `location_scope` | 4 | 0 项，命中 0 | — | 零 app 形状依赖（可独立 import，但仍没有入口） | `backend/app/execution/location_scope.py:1` | — | 0 |
| `member_place_group_share` | 433 | 2 项，命中 0 | 现尖没有模块 `app.shared_stop_coplanning`（要 `member_is_in_force`）；现尖没有模块 `app.execution.member_place_invitation`（要 `_invitation_context_is_current`） | 现尖根本没有对应形状（整枚 app 模块不在线上） | `backend/app/execution/member_place_group_share.py:21` | `docs/REVOLUTION_ABSORPTION_MANIFEST.tsv:29` | 0 |
| `member_place_invitation` | 1969 | 8 项，命中 2 | 现尖没有模块 `app.execution.member_side_quest`（要 `_fresh_member_observation`）；现尖没有模块 `app.execution.member_side_quest`（要 `_member_side_quest_for_action`）；现尖没有模块 `app.shared_stop_coplanning`（要 `grant_status_for_projection`）… | 现尖根本没有对应形状（整枚 app 模块不在线上） | `backend/app/execution/member_place_invitation.py:17` | `docs/REVOLUTION_ABSORPTION_MANIFEST.tsv:29` | 0 |
| `member_side_quest` | 1196 | 5 项，命中 5 | — | 能直接接（形状齐） | `backend/app/execution/member_side_quest.py:13` | `backend/app/core/audit.py:12` | 0 |
| `moment_scout` | 377 | 9 项，命中 6 | 现尖 `backend/app/db/models.py` 里没有 `MemberSideQuest`；现尖没有模块 `app.execution.member_side_quest`（要 `_active_split`）；现尖没有模块 `app.execution.member_side_quest`（要 `_fresh_member_observation`） | 现尖根本没有对应形状（整枚 app 模块不在线上） | `backend/app/execution/moment_scout.py:14` | `docs/REVOLUTION_ABSORPTION_MANIFEST.tsv:29` | 0 |
| `planned_split_meetup_handshake` | 585 | 5 项，命中 2 | 现尖没有模块 `app.execution.group_presence`（要 `_member_in_force`）；现尖没有模块 `app.execution.group_presence`（要 `planned_separation_for_member`）；现尖没有模块 `app.execution.member_side_quest`（要 `invalidate_member_side_quests_for_intents`） | 现尖根本没有对应形状（整枚 app 模块不在线上） | `backend/app/execution/planned_split_meetup_handshake.py:11` | `docs/REVOLUTION_ABSORPTION_MANIFEST.tsv:29` | 0 |
| `presence` | 188 | 6 项，命中 5 | 现尖没有模块 `app.execution.location_scope`（要 `PRIVATE_BUDDY_ROUTE_LOCATION_SOURCE`） | 现尖根本没有对应形状（整枚 app 模块不在线上） | `backend/app/execution/presence.py:11` | `docs/REVOLUTION_ABSORPTION_MANIFEST.tsv:29` | 0 |
| `private_buddy_route` | 1012 | 8 项，命中 4 | 现尖没有模块 `app.execution.location_scope`（要 `PRIVATE_BUDDY_ROUTE_LOCATION_SOURCE`）；现尖没有模块 `app.execution.rendezvous_buddy_handoff`（要 `_current_projection`）；现尖没有模块 `app.traveler_principal`（要 `TravelerPrincipal`）… | 现尖根本没有对应形状（整枚 app 模块不在线上） | `backend/app/execution/private_buddy_route.py:14` | `docs/REVOLUTION_ABSORPTION_MANIFEST.tsv:29` | 0 |
| `private_buddy_safe_return` | 936 | 7 项，命中 4 | 现尖没有模块 `app.route_session_operations`（要 `submit_operation`）；现尖没有模块 `app.traveler_principal`（要 `TravelerPrincipal`）；现尖没有模块 `app.execution.private_buddy_route`（要 `_route_request`） | 现尖根本没有对应形状（整枚 app 模块不在线上） | `backend/app/execution/private_buddy_safe_return.py:20` | `docs/REVOLUTION_ABSORPTION_MANIFEST.tsv:29` | 0 |
| `progress_drift` | 420 | 1 项，命中 1 | — | 能直接接（形状齐） | `backend/app/execution/progress_drift.py:25` | `backend/app/execution/clock.py:61` | 0 |
| `readiness` | 464 | 8 项，命中 7 | 现尖没有模块 `app.agent.watch_policy`（要 `next_move_projection`） | 现尖根本没有对应形状（整枚 app 模块不在线上） | `backend/app/execution/readiness.py:13` | `docs/REVOLUTION_ABSORPTION_MANIFEST.tsv:29` | 0 |
| `rendezvous_buddy_execution` | 719 | 10 项，命中 2 | 现尖没有模块 `app.traveler_principal`（要 `TravelerPrincipal`）；现尖没有模块 `app.execution.rendezvous_buddy_handoff`（要 `_candidate`）；现尖没有模块 `app.execution.rendezvous_buddy_handoff`（要 `_distance_m`）… | 现尖根本没有对应形状（整枚 app 模块不在线上） | `backend/app/execution/rendezvous_buddy_execution.py:14` | `docs/REVOLUTION_ABSORPTION_MANIFEST.tsv:29` | 0 |
| `rendezvous_buddy_handoff` | 886 | 6 项，命中 2 | 现尖没有模块 `app.execution.group_presence`（要 `public_destination_coordinates`）；现尖没有模块 `app.traveler_principal`（要 `TravelerPrincipal`）；现尖没有模块 `app.execution.rendezvous_buddy_execution`（要 `create_execution_window_offer_record`）… | 现尖根本没有对应形状（整枚 app 模块不在线上） | `backend/app/execution/rendezvous_buddy_handoff.py:15` | `docs/REVOLUTION_ABSORPTION_MANIFEST.tsv:29` | 0 |
| `rendezvous_coordination` | 523 | 6 项，命中 2 | 现尖没有模块 `app.execution.group_presence`（要 `planned_separation_for_member`）；现尖没有模块 `app.execution.group_presence`（要 `rendezvous_target`）；现尖没有模块 `app.execution.group_recovery_followthrough`（要 `active_group_recovery_spend`）… | 现尖根本没有对应形状（整枚 app 模块不在线上） | `backend/app/execution/rendezvous_coordination.py:19` | `docs/REVOLUTION_ABSORPTION_MANIFEST.tsv:29` | 0 |
| `route_session_contract` | 121 | 0 项，命中 0 | blob 同值 | 这枚路径已在现尖（另一代或同代，见blob列） | `backend/app/execution/route_session_contract.py:1` | `backend/app/execution/route_session_contract.py:1` | 0 |
| `shared_walk` | 121 | 0 项，命中 0 | — | 零 app 形状依赖（可独立 import，但仍没有入口） | `backend/app/execution/shared_walk.py:1` | — | 0 |
| `traveler_twin` | 595 | 5 项，命中 4 | blob 两代不同 | 这枚路径已在现尖（另一代或同代，见blob列） | `backend/app/execution/traveler_twin.py:14` | `backend/app/execution/traveler_twin.py:1` | 10 |
| `truth` | 62 | 0 项，命中 0 | — | 零 app 形状依赖（可独立 import，但仍没有入口） | `backend/app/execution/truth.py:1` | — | 0 |

## 三、给下一刀（ORD-0602）的结论，全部由上面的表算出来

- **形状齐、可直接接的有 3 枚**：`bootstrap_discovery`（要 1 项形状，现尖生产码 import 它的文件 0 枚）、`member_side_quest`（要 5 项形状，现尖生产码 import 它的文件 0 枚）、`progress_drift`（要 1 项形状，现尖生产码 import 它的文件 0 枚）。这三枚要的每一个 app 形状都能在现尖那一代查到定义行，所以「挑一枚带真接线落」可以从这三枚里选，不必先补形状。
- 落在「要改哪一枚签名」那一格的有 0 枚。
- **零 app 形状依赖、可独立 import 的有 3 枚**：`location_scope`、`shared_walk`、`truth`。但按 CMDR-RULING-0607 那一格，它们落线后现尖生产码 import 它们的文件数仍全是 0，除非同一刀里给入口。

- **先补哪一枚缺模块能一次解锁最多**：下面按「需要它的现尖缺形状模块数」排名，逐枚给枝名。这是 18 枚 NO_SHAPE 的共同底。

| 现尖没有的 app 模块 | 需要它的 execution 模块数 | 被要到的符号（逐枚） | 需要它的模块（逐枚，前六） |
|---|---|---|---|
| `app.execution.group_presence` | 6 | `_member_in_force`、`planned_separation_for_member`、`public_destination_coordinates`、`rendezvous_target` | group_recovery_followthrough、live_moment_scout、planned_split_meetup_handshake、rendezvous_buddy_execution、rendezvous_buddy_handoff、rendezvous_coordination |
| `app.execution.location_scope` | 6 | `PRIVATE_BUDDY_ROUTE_LOCATION_SOURCE` | group_presence、in_transit_reroute、launch_origin、launch_setup、presence、private_buddy_route |
| `app.traveler_principal` | 5 | `TravelerPrincipal` | private_buddy_route、private_buddy_safe_return、rendezvous_buddy_execution、rendezvous_buddy_handoff、rendezvous_coordination |
| `app.execution.member_side_quest` | 4 | `_active_split`、`_fresh_member_observation`、`_member_side_quest_for_action`、`invalidate_member_side_quests_for_intents` | live_moment_scout、member_place_invitation、moment_scout、planned_split_meetup_handshake |
| `app.execution.rendezvous_buddy_execution` | 2 | `activate_execution_on_handoff_accept`、`create_execution_window_offer_record`、`execution_for_current_viewer` | private_buddy_route、rendezvous_buddy_handoff |
| `app.execution.rendezvous_buddy_handoff` | 2 | `_candidate`、`_current_projection`、`_distance_m`、`_is_public_place` | private_buddy_route、rendezvous_buddy_execution |
| `app.shared_stop_coplanning` | 2 | `find_accepted_grant`、`grant_status_for_projection`、`member_is_in_force` | member_place_group_share、member_place_invitation |
| `app.agent.journey_intent` | 1 | `intent_is_active` | group_presence |
| `app.agent.watch_policy` | 1 | `next_move_projection` | readiness |
| `app.execution.group_recovery_followthrough` | 1 | `active_group_recovery_spend` | rendezvous_coordination |
| `app.execution.launch_origin` | 1 | `grounded_launch_origin` | launch_setup |
| `app.execution.member_place_group_share` | 1 | `current_group_share` | member_place_invitation |

  这一格是纯计数：同一枚缺模块被多枚 execution 模块要到时只算一次符号集合并。排名并列时按模块名字典序，判据可复算。

## 四、本枚边界（自报）

- **一处自报，尺错过两次**：第一遍只把 `class`/`def` 当形状，把模块级单例漏了，于是把 `backend/app/core/config.py:105` 的 `settings = Settings()` 与 `backend/app/execution/clock.py:61` 的 `execution_clock = ExecutionClock()` 判成「现尖没有」，当场得到「0 枚可直接接、18 枚缺形状」的错表。补上模块级绑定这一臂后，同一代尖、同一批枝重跑才出现在这份表；脚本里另加一条自检：取不到那两枚单例、或取到一个假名字，就拒绝出表。
- **第二处自报**：枝内锚第一次算出来落在空行上——我的 `from` 正则用了 `\s*` 开头，把上一行的换行也吃进匹配，行号整体回退一行。是发布前的坐标审计（每枚 `file:行` 必须取到非空行）当场拦下 15 枚没拦回去，改成只允许空格与制表符后再加了一条对齐自检：每个记录的行必须真的含它声称的那条 import 与那个符号。
- 判的是**符号存在性**，不是行为兼容：现尖有同名 class/def 不等于语义对得上，接线前仍要逐枚读签名。命中项都给到 `文件:行号`，可逐枚 `git cat-file blob` 对读。
- 「缺什么」表里每行只截三枚加省略号；完整逐枚清单共 55 项，在同目录 `EXECUTION_MISSING_SHAPES.tsv` 那一枚文件里，项项给枝内行号、它要的 app 模块、符号名，以及现尖那枚文件在不在。
- 本枚零产品字节、没跑后端与测试、没起端口、工作树没碰；权威枝一笔没推。
