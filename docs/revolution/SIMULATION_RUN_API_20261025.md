# SimulationRun 接入契约

关联 Issue #47 / PR #48。Codex 提供后端；Qoder 对接 Presenter 与旅客界面。

## 启用与身份

- `CITYNEXUS_SIMULATION_ENABLED=true`，`CITYNEXUS_DEMO_MODE=true`，非 production。
- `CITYNEXUS_DEMO_DATABASE_PATH` 必须是当前 SQLite 的绝对路径；不接受默认 `citynexus.db` 或 `_live.db`。
- 读取需有效成员 bearer 与 `JOURNEY_READ`；写入还需 `JOURNEY_EXECUTION_UPDATE`。
- 写入须携带配对后绑定本 Journey/本数据库的短期主持人 bearer，或服务端配置的 `X-CityNexus-Presenter-Key`（`CITYNEXUS_DEMO_PRESENTER_KEY` 至少 32 字符）。不要在共享前端源码中嵌入此值。
- `GET /api/v1/demo/session` 也遵守上述隔离数据库及讲台访问约束。本机和代理请求同样需要讲台授权；无 key 返回 403。

## 接口

统一前缀：`/api/v1/journeys/{journey_id}/simulation`。写入均带 `Idempotency-Key`，同键同请求返回第一次持久结果，同键不同请求为 409。所有写请求 JSON 拒绝额外字段。

| 方法和路径 | 请求 | 行为 |
| --- | --- | --- |
| POST `/runs` | `{ "seed": 17 }` | 已有正式 ACTIVE Journey/Plan 才能创建；201 返回 run |
| GET `/runs/current` | 无 | 找回该 Journey 的唯一 run；未开始时 `NOT_STARTED` |
| GET `/runs/{run_id}` | 无 | 读取完整历史、状态、模拟位置和时钟 |
| POST `/runs/{run_id}/advance` | `{ "expected_sequence": 0 }` | 走下一执行阶段：出发、到达、体验、完成 |
| POST `/runs/{run_id}/advance` | `{ "expected_sequence": 0, "minutes": 60 }` | 依次应用途中各阶段，再停在目标虚拟时间；1–10080 分钟 |
| POST `/runs/{run_id}/scenes` | `{ "expected_sequence": 1, "scene_id": "closed-d1", "event_type": "CLOSURE", "activity_id": "UUID" }` | 注入现有活动上的环境事件，暂停等待 Guardian；也支持 WEATHER、SCHEDULE_DELAY 和 `delay_minutes` |
| POST `/runs/{run_id}/guardian` | `{ "expected_sequence": 2, "model_consent": true }` | 调用现有 Guardian/runtime，持久化真实运行引用；不自动接受提案 |
| POST `/runs/{run_id}/resume` | `{ "expected_sequence": 3 }` | 事件已通过原生签名工作流解决后继续 |
| POST `/runs/{run_id}/recover` | `{ "expected_sequence": 3 }` | 仅在 Guardian 的现实时间租约过期后恢复被中断的执行；不会重发模型请求 |
| GET `/cities?seed=17` | 无 | 只读当前成员有权限的已有来源数据；至少三城各 5 个来源 POI、3 条真实捕获路线才 READY |

每次写入成功增加 `sequence`。第二个并发写入使用旧版本会得到 `SIMULATION_SEQUENCE_STALE` 409。UI 以成功响应中的 `sequence` 发下一请求。

## 返回字段与状态

所有 run 响应包含 `run_id`, `journey_id`, `city_code`, `seed`, `timezone`, `virtual_now`, `sequence`, `status`, `state`, `history`, `execution_truth`, `updated_at`。

`state` 包含当前 PlanVersion、已完成活动、来源快照引用和模拟位置；`history` 中每项包含 sequence、虚拟时间和现实记录时间。位置带 `source=SIMULATED_GPS` / `classification=SCENARIO_SIMULATED_LOCATION`；执行记录为 `SIMULATED_STATE_TRANSITION`。不会生成设备到场证明。

主要状态：`RUNNING` → `PAUSED_FOR_GUARDIAN` → `GUARDIAN_RUNNING` → `PAUSED_FOR_ACCEPTANCE` / `PAUSED_MODEL_UNAVAILABLE` / `PAUSED_REQUIRES_MISSION`。解决事件后 `/resume`。末站完成为 `SIMULATED_COMPLETED`。

Guardian 响应只转投持久化的运行 ID、状态和提案 ID；服务端原有运行接口继续提供已发生的工具轨迹。未调用模型时为 `model_execution=NOT_EXECUTED`。不提供自由文本错误或模型原文。

## 两种时间与持久化

`SimulationRun`、`SimulationClock` 和幂等命令在同一演示数据库持久保存。Journey 请求、后台 pulse、Guardian 使用同一业务虚拟时间作用域。JWT、成员安全 TTL、模型租约、供应商采集时间、审计发生时间仍取现实时间。

已有 simulation-clock 入口在创建 run 后拒绝独立写钟，返回 `USE_SIMULATION_RUN_ADVANCE`；应使用本契约推进，以保留活动顺序。旧入口的写入现在必须提供 `expected_version`。

城市预检不会访问供应商，不会把旧数据重新标为实时采集。输出保留 `CAPTURED_PROVIDER_SNAPSHOT`、采集时间、快照哈希和具体缺口。测试库中的 synthetic POI 不进入随机可用城市池。

## 本轮验证与接力

独立 SQLite/签名 HTTP fixture 覆盖两个 seed 的两日完整执行、刷新读取、幂等、CAS 双击、升级保留数据、场景不重复、模型失败暂停、禁止规则冒充 Agent 和签名接受门。未使用 Qoder 现场数据库、密钥、端口或前端。

Qoder 需补现有 `citynexus.ts` 的 `listEvents`、`getJourneyTwin` 请求 bearer，并核对 `/experience` 调用方；`getJourney` 已有 bearer。将以上 API 接入其现有 Presenter 后，再进行真实 Chrome / 三城来源 / 真模型闭环验收。


## 2026-10-25 外审修复增量

**代理身份**：删除 loopback 豁免。前端代理到 localhost 不再授予凭据发行权限。操作者用讲台 key 调用 `POST /api/v1/demo/pairing {journey_id}`，返回 120 秒单次票据；浏览器将票据放入 `POST /api/v1/demo/pairing/redeem {ticket}`，获得 900 秒签名会话，其中主持人权限仅对票据指定的 Journey 和该隔离数据库有效；浏览器用此 bearer 控制模拟，无需取得讲台 key。票据只存 SHA256，原子单次消费，兑换按真实 peer 每分钟限 20 次。共享前端不携带讲台 key，票据不用 URL query。已有签名读取保持 bearer。

**单一执行链**：run 存在后原生 depart/arrive/begin/complete/skip 写入返回 `USE_SIMULATION_RUN_ADVANCE` 409。模拟器与原生 HTTP 复用 `execution/activity_state.py` 的 Journey/Plan/cursor/转换前置条件和出发路线证据检查；模拟到场无法替代多人 recovery rendezvous 的本人认证到场。原生签名 proposal 接受接口仍保留，下一次模拟推进读取新的权威 PlanVersion。

**城市 ID**：`POST /simulation/city-identity {source_task_id}`（该前缀仍为对应 Journey），读取本人已有 GoalTask 的 AMap resolved region，必须匹配持久 ProviderCall 的行政区结果；返回 `internal_city_code` 与独立 `provider_city_adcode`、来源收据和哈希。保留 CN-RV 内部码，不从字符串猜城市。仅 city 级来源和四个直辖市 province 级来源可进入城市池；区县不计作另一座城市。

**公用快照**：`POST /simulation/cities/publish {publish_public_facts:true}` 在 key + 签名执行权限下，显式发布当前 Journey 已验证的公开地点/路线字段。必须已有城市身份、5 POI、3 路线；POI 的 AMap 原始搜索收据 adcode 要与绑定城市一致。目录不会复制 Journey/Plan/member/task 身份。发布以内容哈希幂等；私有行程资料不会自动进入池。`GET /simulation/cities?seed=17` 合并本人可读资料与显式公用快照，以去重后的 provider adcode 计算三城和抽样；`selected_provider_adcode` 为明确新字段，旧 `selected_city_code` 同值。

城市映射和发布是按资源身份/内容哈希幂等的操作；携带 Idempotency-Key，无需 run 的 expected_sequence。它们不会触发供应商查询。新增 schema 随常规 ensure_schema 升级；Qoder 对接前需升级其隔离课堂 DB。
