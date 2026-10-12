# continuous_journey 的选料与接线设计（ORD-0613 的设计半）

车道「地图工」产出。这张单写明：**等 ORD-0610 与 ORD-0611 落线再动码；在此之前只许交选料与接线设计，
点名每一处调用点**。所以本枚零产品字节、没动任何 `.py`、没跑 pytest，只交设计。

- 现取权威尖：命令原样 `git -C D:/moodle/CityNexus ls-remote origin refs/heads/mirror/integration-frontend-apple-pass1`
  现读 `f85194013ac10202e40b52d7ba2b6b95a7231059`。本件起草在 `82229876934fa7fd4124b726a2f1be2b7821c28d` 那一代；交付这一刻全部坐标又在下述新代上重跑一遍。本文件里每一枚「现尖坐标」都在这一代上现读；
  代次不符时本件整代作废，按同一把尺重跑，不在旧数上补话。
- 依赖来源枝：`refs/heads/gpt/revolution-r33-open-world-journey-adaptation` =
  `a5a2f1096e0fbd806acd8be134fe8fb6095ad1a9`（对账行 `docs/REVOLUTION_ABSORPTION_MANIFEST.tsv:29`）。
- 判据：逐枚读 `from app.X import a, b` 那一行的**完整包路径**（不只看第一段包名），再到尖那一代的
  `git ls-tree` 里查 `backend/app/<X>.py` 在不在；模块级 import 与函数内 import 分开记，因为前者是
  硬 ImportError，后者只在走到那一臂时才要。

## 一、真顺序（这条是本件最要紧的一条，和派单顺序不一样）

| 步 | 要落的模块 | 它的硬 import（模块级）里尖上没有的 | 判据 |
|---|---|---|---|
| 1 | `backend/app/execution/presence.py` | 无（3 条 import 全部命中尖） | `backend/app/execution/presence.py:13` |
| 2 | `backend/app/agent/watch_policy.py` | 无，但它第 14 行硬 import `app.execution.presence`，所以必须排在 presence 之后 | `backend/app/agent/watch_policy.py:14` |
| 3 | `backend/app/execution/readiness.py` | `app.agent.watch_policy`（第 12 行是模块级硬 import，第 152 行真调用） | `backend/app/execution/readiness.py:12` |
| 4 | `backend/app/execution/continuous_journey.py` | `app.execution.presence` 与 `app.execution.readiness` 两枚 | `backend/app/execution/continuous_journey.py:14` |

**结论：单文那张「readiness 零缺兄弟」的表没有错，但「零缺兄弟」不等于「可直接落」。** readiness 的缺口不在
execution 同族里，而在 `backend/app/agent/watch_policy.py` 那一枚——尖上 `backend/app/agent/` 那一包存在，
包里现读十九枚模块没有它。屏工在 0610 的复核里已给出同一判断的成因（选料尺只比 import 的第一段包名），
本件不重复那条成因，只补两件事：**watch_policy 自己也硬依赖 presence（所以顺序不是任选）**，以及
**watch_policy 目前不在 0610、0611、0612、0613 任何一张单上**。要落 readiness 就得先给 watch_policy 一刀，
或者把 readiness 的那枚模块级 import 改成延迟 import——后者会改对外行为，不属于「纯搬运」，本车道不越权做。

## 二、逐枚 import 台账（枝内行号现读，尖上有没有逐枚标出）

| 模块 | 枝内行 | 它要的 app 形状 | 尖上 | 尖上对应文件 |
|---|---|---|---|---|
| presence.py | 11 | `app.db.models`（Activity、Journey、LocationObservation、Place） | 有 | `backend/app/db/models.py:1068` |
| presence.py | 12 | `app.execution.clock`（execution_clock） | 有 | `backend/app/execution/clock.py:61` |
| presence.py | 13 | `app.execution.location_scope`（PRIVATE_BUDDY_ROUTE_LOCATION_SOURCE） | 有（0602 刚落线） | `backend/app/execution/location_scope.py:3` |
| readiness.py | 12 | `app.agent.watch_policy`（next_move_projection） | **没有** | `backend/app/agent/watch_policy.py:223`（枝上定义） |
| readiness.py | 13-15 | `app.db.models`、`app.execution.clock`、`app.execution.departure_activation` | 有 | `backend/app/execution/departure_activation.py:1` |
| readiness.py | 348 | 函数内：`app.operations.v9`（notify） | 有 | `backend/app/operations/v9.py:1242` |
| readiness.py | 460 | 函数内：`app.operations.v9`（refresh_offline_snapshot） | 有 | `backend/app/operations/v9.py:1301` |
| continuous_journey.py | 13 | `app.db.models`（Activity、Journey、JourneyLeg、PlanVersion） | 有 | `backend/app/db/models.py:937` |
| continuous_journey.py | 14 | `app.execution.presence`（presence_projection） | 没有（0610 的目标） | `backend/app/execution/presence.py:78` |
| continuous_journey.py | 15 | `app.execution.readiness`（departure_readiness_projection） | 没有（0611 的目标） | `backend/app/execution/readiness.py:132` |

## 三、0610 与 0611 必须原样导出的签名（cj 按这两个形状调）

- `def presence_projection(session, journey, *, viewer_member_id=None, target_activity_id=None, now=None) -> dict`
  定义在 `backend/app/execution/presence.py:78`（枝内）。cj 在 `backend/app/execution/continuous_journey.py:14`
  按这个名字调，改名即断。
- `def departure_readiness_projection(session, journey, *, now=None) -> dict`
  定义在 `backend/app/execution/readiness.py:132`（枝内）。它在函数内真调
  `next_move_projection(session, journey, now=stamp)`（`backend/app/execution/readiness.py:152`），
  那一枚就是第一节里 watch_policy 的缺口来源。
- cj 自己的对外面只有两枚可读投影，都不写状态：
  `continuous_journey_state(*, journey_status, activity_status, presence_state, readiness_state, must_leave_by, activity_end_at, next_activity_id, operator_needs_attention=False, now)`
  在 `backend/app/execution/continuous_journey.py:30`，
  `continuous_flow_projection(session, journey, *, viewer_member_id=None, operator_needs_attention=False, now=None)`
  在 `backend/app/execution/continuous_journey.py:156`，其文档行自己写明不写执行态、不取路线。

## 四、候选调用点逐枚点名（尖上现读，含「为什么它/为什么不它」）

现尖上已经在读 `app.execution.clock` 的生产文件有六枚，命令原样 `git grep -n "app.execution.clock" <尖> -- backend`：

| 候选宿主 | 坐标 | 能不能承接 cj | 理由 |
|---|---|---|---|
| `backend/app/operations/v9.py` | `backend/app/operations/v9.py:123` | **首选** | `_execution_truth(activities, legs, current_activity_id)` 的文档行自称「the shared NOW/NEXT projection consumed by mobile and Edge」，与 `continuous_flow_projection` 同形状：两者都按 `Activity.plan_version_id == journey.active_plan_version_id` 取活动并按 `sequence_no` 排、都优先用冻结的 JourneyLeg 边（对照 `backend/app/operations/v9.py:1301` 与 `backend/app/execution/continuous_journey.py:156`）。接在这里等于把旅客看得见的那条 NOW/NEXT 换成带 presence/readiness 的版本。 |
| `backend/app/operations/v9.py` | `backend/app/operations/v9.py:1301` | 次选 | `refresh_offline_snapshot(session: Session, journey: Journey)` 的参数形状就是 cj 要的 (session, journey)，且 readiness 已经在函数内调它（`backend/app/execution/readiness.py:460`）。缺点是它写离线快照，加投影要过「读了什么就写什么」那条老规矩。 |
| `backend/app/stay_mobility.py` | `backend/app/stay_mobility.py:281` | 可用 | `journey_projection_window(context, journey)` 是「读路径必须报出的那种行程窗」，与 cj 的 milestone 语义同层；本文件也是 0602 已验收的宿主先例（import 在 `backend/app/stay_mobility.py:54`，谓词在 `backend/app/stay_mobility.py:1751`）。缺点是它拿的是 `JourneyTripContext` 不是 session，cj 需要 session 取 Activity。 |
| `backend/app/integrations/discovery/orchestration.py` | `backend/app/integrations/discovery/orchestration.py:21` | 不建议 | 它 import clock 只为取时间，属发现编排链路，接日流程投影会把 execution 的读语义漏进编排层。 |
| `backend/app/intelligence/impact_resolver.py` | `backend/app/intelligence/impact_resolver.py:12` | 不建议 | 影响解析的输入是事件，不是「谁在这趟行程里」，接上去会把 presence 的权限判定绕开。 |
| `backend/app/main.py` | `backend/app/main.py:209` | **禁** | 本批共同纪律点名不许动（88 枚真并行撞面里最挤的那枚）。 |
| `backend/app/agent/runtime.py` | `backend/app/agent/runtime.py:26` | **禁** | 同上，热文件排队中。 |

## 五、给这一刀落线时的前后对照形状（本车道没跑，交给落线那扇车道）

- 反控必须是「去掉接线就变红」：同一代尖导出整树 → 跑 cj 自己的测试拿基线 → 只在宿主文件加那一处调用 →
  再跑同一条测试，断言里要有一条读**宿主输出**的（例如 `v9.py` 那份 NOW/NEXT 投影里出现 cj 给的里程碑字段），
  否则「接线」只是 import。
- 顺序上先给 presence 的测试补一条「被 readiness 的调用者看见」的断言，再落 readiness，避免 0611 落线后
  出现一枚 import 得到、但没人调的模块——CMDR-RULING-0607 已经为此更正过一次口径。

## 六、本枚边界（自报）

- 零产品字节：没动 `.py`、没建测试、没跑 pytest、没起端口、工作树没碰；本件与台账只新增文档。
- 我这把尺今晚错过三处，第三处在本件里：一版 `^def|class` 的正则被竖线劈成两支，`def` 那一支没有捕获组，
  于是把 `backend/app/execution/presence.py:78` 的 `presence_projection` 报成「分支里找不到」。
  改成 `^(?:def|class)` 后重跑才出第二、三节那两张表；自检已加进尺里（同一行必须含它声称的符号名）。
- 「有 import 且尖上有那枚文件」不等于「能落」：第一节讲的就是这一件——第一段包名命中、包里没有那一枚。
- 判语只到「顺序与调用点」，不替车道决定改不改延迟 import；那一条要号令者点头。
