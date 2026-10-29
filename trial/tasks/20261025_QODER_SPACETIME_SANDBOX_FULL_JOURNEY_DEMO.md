# P0｜CityNexus Revolution V3「时空沙盒」：几分钟演示完整随机城市旅行

日期：2026-10-25。负责人：**Qoder（唯一实施人）**。开发位置：`rescue/v3-final-departure-20261022`、PR #43、Issue #42。

## 用户需求与验收定义

用户原话：课堂上无法真实跨城、无法测试几天的旅行，必须在几分钟内展示随机城市的**完整 Journey**，包含虚拟定位、虚拟时间、迟到、天气/景点关闭/路线中断等意外，由**真正的 Agent** 自主查询工具、决定如何应对、必要时征求本人/同行同意，然后继续第二天、完成整个旅程。**不能继续在纸上谈兵、只能画图或循环跑后端全绿。**

本任务优先于新一轮脚注、更多 AMap 资料字段、历史测试量具。不要只做一张模拟动画；不要为了演示绕过现有的 signed Journey、PlanVersion、Guardian、Event、工具调用和执行记录。**Demo is simulated travel, but Agent and product code execute for real.**

**完成标准**：老师在真实浏览器（最好平板）选「随机城市」→开始可用的两天计划→演示控制台点击/加速时间/虚拟旅客沿地图位置移动→观察 Guardian 真实收到至少两次模拟外部事件→Agent 的真实工具/推理摘要与提案→同一 PlanVersion 的合法变更/用户确认→从 Day1 到 Day2 再到 SIMULATED_COMPLETED→有可回放、能说明“哪些是模拟、哪些是系统真的执行”的证据。**必须一趟相同 journey_id/run_id，不能把各自不同测试的截图拼接冒充一条完整执行。**

## 先复用仓库现有的真模块，不要重写平行假系统

已从本分支源代码核实：

- `backend/app/execution/clock.py` 已有 `execution_clock.now(timezone)` 与 `freeze(value)` 的 **ContextVar 请求作用域时钟**。但它不是跨 HTTP 请求持久模拟时钟；`guardian.py`、`signal_pipeline.py`、`autorun.py` 和其他领域函数大量直接使用 `datetime.now(timezone.utc)`，所以**只改浏览器 Date 或改 ContextVar 不足以保证后端真的过了一天**。
- `backend/app/execution/truth.py` 已有 `SIMULATED_STATE_TRANSITION`，明确把模拟执行与 `DEVICE_LOCATION_VERIFIED_EXECUTION`、`OPERATOR_CONFIRMED_EXECUTION` 区分。**继续使用这个真相分层，不得把教师按钮扮成物理到场**。
- `backend/app/execution/presence.py`、`group_presence.py` 只把 `DEVICE_ATTESTED/LOCATION_ATTESTED` 认作可信设备位置，`FOREGROUND_WEB` 为建议位置。**不要把 SIMULATED_GPS 加入可信设备位置白名单**。
- `backend/app/agent/signal_pipeline.py` 已有 `CitySignalFixture`，`NORMAL / DISRUPTED / OUTAGE / RISK_FORECAST`，支持 `target_place_id` 的定点模拟闭馆，`refresh_demo_signals` 通过服务器写 `ProviderObservation` / `Event`，具幂等缓存。`backend/app/agent/autorun.py:pulse_journey` 已经按 `refresh_signals → Guardian → Agent/trace` 执行。把这些接成一条可见演示管线，不要前端直接 INSERT Event / GuardianRun / AgentRun。
- `backend/app/execution/continuous_journey.py` 已有只读当前站/下一站/到达/完成投影，配合 `journey_twin.py`、`execution/launch_setup`、`agent/guardian_stream.py`、`goal_route_freeze.py`、`goal_travel_gaps.py`、多人同意与版本写入；按已有计划权限调用。
- `trial/play_launcher/citynexus-play*.bat` 可启动本地栈；**但每次 boot 的 `CITYNEXUS_TRAVELER_AUTH_SECRET` 随机轮换、 bearer 在 sessionStorage，重启续玩仍有身份缺口；不要把「KEEP_DB=1」说成身份能恢复。** 演示必须是独立演示数据库和可复位 session。

## 1. 两个相互隔离的世界，避免把模拟当真实

### 演示后端入口与保护

- 新增 `CITYNEXUS_SIMULATION_ENABLED` 默认 false；只有本机/受控课堂 LAN + 明确 `CITYNEXUS_DEMO_MODE=true` + **隔离的 DEMO_DB** + presenter 身份授权才允许创建演示 run。默认生产全部 404/403。禁用公网、禁写真实用户数据库、禁真实预订/付款/发邀请、禁主动调用真实设备到场权威。
- 把 `SimulationRun`（run_id, seed, city, journey_id, clock, scene_cursor, status, provider_snapshot_refs, event_log, actor / version / idempotency）和 `SimulationStepReceipt` 存入 demo DB；多 session 也必须仅影响对应 run。重复按「+1 小时」带 Idempotency-Key 时不得重复 Event/Guardian pulse/变更。
- 前端一直可见水印 **「课堂时空模拟｜不是实际定位或真实灾情」**，信息面板分开标：`LIVE_AMAP_POI` / `CAPTURED_PROVIDER_SNAPSHOT` / `SCENARIO_SYNTHETIC_WEATHER` / `SCENARIO_SIMULATED_LOCATION` / `MODEL_RUN` / `RECORDED_MODEL_REPLAY` / `UNKNOWN`。如果某条 Event 内部 provenance 是 `PROVIDER_VERIFIED` 而 provider_key 为 `city-signal-fixture`，UI 仍必须显示**模拟供应商信号**，不能说「景区官方已关闭」。
- “全程 2 天模拟结束”是 `SIMULATED_COMPLETED`（或在模拟库的终态投影），**不证明真人实际到场，也不向现实数据库写完成**。保持 execution_truth.kind = SIMULATED_STATE_TRANSITION 及 run_id。

### 真实 Agent 与模拟场景的明确分工

- 事件发动者：时空沙盒（教师或随机事件引擎）；不预先替 Agent 选备选方案。
- 信息：真实高德 POI/路线可以提前录制合法来源快照（保留 ID/采集时间/有效期），但未来日的“暴雨/临时闭馆”由模拟事件提供，不是假装实时高德天气；预录事实标 `CAPTURED_PROVIDER_SNAPSHOT`。
- 决策：使用现有 Hermes/兼容真实 Agent runtime，通过**正常工具、Guardian、proposal、授权与 PlanVersion** 得出判断；UI 真实显示工具步骤、来源、为什么改、不确定性、老新计划差异。若模型 503，只显示失败和可恢复/回放入口；**规则兜底和预录 Agent 响应必须明确标签**，不许宣称模型现场自主完成。

## 2. 虚拟时间：必须后端和前端同时认同

设计 `SimulationClock`：run_id → persisted virtual_now + timezone + scene_cursor + pause/status。UI 要同时显示：
- 「模拟旅行时间：2026-11-02 09:00（Asia/Shanghai）」；
- 「现实演示时间：2026-10-25 XX:XX」；
- `+30 分钟`、`下一站`、`下一天`、`播放/暂停`、`回到起点（新 run/明确重置隔离库）`。

用 `execution_clock.freeze(simulated_now)` 包住**每个相关执行请求和 Guardian pulse/background step**，但先审计并改造所有涉及演示真相的直接 `datetime.now`：阶段判定、营业日期、Guardian 冷却/候选事件/事件时间戳、行程到达和完成、计划时间、旅客意图过期、模拟观察的新鲜度；以显式依赖注入取得 virtual time。真实系统审计时间、JWT token TTL、供应商响应采集时间**继续使用现实安全时钟**，避免时间旅行伪造有效证书/签名。
- `+1 天` 要分步骤依次触发应到的事件与阶段变更（事件索引、领域命令与结果），不能只将 Chrome 的 `Date.now()` 改到明天；快进可跳动画但不可吞掉中途的关键事件。
- 前端 Playwright Clock 或 Chrome 时钟覆盖**只作 UI 验证辅助**，权威是服务器 SimulationClock；不能改 Windows 系统时间。
- 断电/重启、刷新、重复点击、点击「上一站」时不得回退已应用的权威事件。可重播只读证据；想走另一条分叉须从同样 seed 创建**新** demo run，不改写原审计。

## 3. 虚拟 GPS：沿真实地点连成的旅行路径移动

- 复用当前同一 Journey 的 canonical Place 坐标和已冻结的路线 geometry。对国内 AMap 的 GCJ-02 与地图/设备可能使用的 WGS84 显式标注并在正确边界转换，**不要把不同坐标系直接相加**。
- ScenarioLocation 在演示库按 run_id/旅客身份/route hop 记录位置 + accuracy + captured_virtual_at，允许 `前进到下一站` / `到达` / `绕路` / `手动拖动蓝点`。地图显示旅客蓝点、路径线、下一站图钉和预计到达时间；不要求教室真的移动。
- 浏览器人工验证可以调用官方 Playwright `context.setGeolocation` / Chrome DevTools Sensors override；但这**只影响浏览器，不会自动变成后端认证的位置**。正式的模拟位置要通过 presenter-auth 的测试 API、demo DB 与投影消费，源为 `SCENARIO_SIMULATED_LOCATION`，绝不可标 `DEVICE_ATTESTED`。定位没有权限时仍可用地图模拟器。
- 如用户模拟按「到达」，复用现有执行 transition endpoint 的**显式模拟身份/过渡种类**或新增窄 simulation-only adapter，使用 `append_execution_truth(kind=SIMULATED_STATE_TRANSITION)`。不能把模拟经纬度写进常规 `LocationObservation` 并谎称设备已在景点，更不能伪造正式多人 arrival receipt。

## 4. 随机城市：真正可复现，不赌陌生城市必有数据

- UI 两种按钮：**「随机城市（可用城市池）」**和**「指定城市（现场挑战）」**。
- 第一版随机池限定预检通过的至少 3 座真实城市（先核验高德 adcode/真实 POI ID ≥ 5、坐标、至少 3 条合理转场、有效来源快照/或实时能力、照片可选）；池成员按**检测结果**选，不能写死“任何城市都能跑”。以 seed 选择并在 UI 展示随机种子、池名单、真实 provider 数据采集时间，不准现场暗改 seed 保证老师想看哪座都成功。
- 课堂稳定模式允许缓存**课前合法采集**的真实景点/路线（明确标签）；现场任一随机池城市初始化**一趟新的 demo Journey**。Agent 规划或采用预热的基线计划时，要说明 `PREPARED_BASELINE` 与 `LIVE_AGENT_GENERATED` 之间的区别。
- 「指定城市」尝试实时研究，供应商没权限/无覆盖则如实 `BLOCKED / PARTIAL`、保留目前结果并给替代城市，不能用北京名单换个城市名。
- 随机的是**城市 + 途中事件顺序/时段**，不是把 Agent 解决问题的答案一起预先写死。至少 2 个不同 seed 的整趟 run 能独立完成，不许只有演示指定城市被硬编码。

## 5. 场景卡与 Agent 自主应变（演示 UI 必须可点）

可手工由老师点事件牌，也可用 reproducible seed 选有意义的组合。当前已有 `signal_pipeline` 内 `NORMAL, DISRUPTED, OUTAGE, RISK_FORECAST`；**先接最窄四种**，必要时扩展有语义的新事件模型，不给 fixture 私自改不属于它的真值：

1. **目标景点临时关闭**：scenario 指向当日**真实计划中使用的 canonical Place** → `CitySignalFixture.set_fixture_state(DISRUPTED, target_place_id)` → server `refresh_demo_signals` → `pulse_journey`/Guardian → Agent 搜附近可去、对比时间和来源、提出修改；用户接受才产生正式 plan 变更。
2. **大雨/交通延误**：注入 `RISK_FORECAST` 或交通退化 → Guardian 是否主动预警、建议调整室内场所/出发时刻；不能把 simulated rain 写成 LIVE_WEATHER。
3. **旅客迟到或临时偏好**：模拟时钟超时/调整 GPS、用户说「今天只想少走路」→ Agent 识别已冻结路线、步行接驳、活动顺序，提出新版本（现有 `goal_travel_gaps`、短步行规则优先）；若真无法满足约束必须诚实 BLOCKED。
4. **三人有分歧**：三名**独立真实签名的测试身份**分别作答，先展示 2/3 状态但计划不变，再 3/3 触发真正服务器 authority 判据；若 ACL/成员资格还有阻断就如实显示，不可把同一 owner token 拿来扮演三个人。

至少 2 次情境突变必须触发一次真实 Guardian→Agent 工具执行，另一次允许 NO_ACTION（如果当前证据确实不影响计划）。展示「未做调整」与做了调整同样有价值。

## 6. UI：双视角而不是一块工程师控制台

**旅客端（大屏左 70% 或平板主屏）**：地图（路线/移动蓝点/站点/POI 图片）、时间线（日 1/日 2/当前站）、统一 Agent 对话、Guardian 工作轨迹与事件消息、提案 A/B、同意、执行进度；不出现生硬的 WB2API/JOURNEY OPERATOR 默认面板。

**演示者控制台（右侧 30% 或老师操作区）**：城市随机按钮、seed、模拟时钟/位置、事件卡「关闭景点 / 交通延误 / 大雨 / 迟到 / 断网」「播放下一幕」「暂停」「重置新 run」「查看回执」。只在 SIMULATION_ENABLED 的受认证课堂环境显示。每一步可以手动停下给老师提问，而不是视频自动播完。

**信任标识始终常驻**：「模拟第 2 天 09:20」「模拟定位 · 不是物理 GPS」「本次事件：人工注入」「Agent 本轮：真实模型/回放/降级」「外部地点：高德真实来源（采集于…）」。不要在监控 trace 中合成看似真实的模型思维链；只展示已实际发生的工具调用、可见行动摘要和真实记录。

## 7. 讲台 5 分钟操作脚本（实物而非 PPT 讲故事）

**课前预检**：跑真实浏览器 390px 和现场投屏宽度各一次，隔离 DB、Agent 连通、供应商快照、完整预备 Journey 与截图/视频备用，不能第一次在讲台启动/授权/调试 Key。讲台选随机城市是从已预检池中随机，不是暗中固定北京。

- **0:00–0:40**：老师点击「随机城市」，看到 seed、真实景点地图；如果是课前准备的基线计划，明确说明这是缓存 POI 与已准备方案，绝不宣称现场模型 30 秒规划完一切。
- **0:40–1:20**：点「开始模拟旅行」，时钟 Day1 08:00→11:00，旅客蓝点沿路线前进、状态「前往/到达」通过模拟执行记录变化。
- **1:20–2:30**：让老师点「下一站临时关闭」，显示单独标注的模拟 Event → Guardian 真实检测 → Agent 正常查可替换地点并给理由；真实等候可见，失败直接演示「重试/已有成果」。
- **2:30–3:20**：旅客/教师审阅 PlanVersion 变更前后 A/B，点允许则按合法签名流程接受；地图和下一站即时变化。
- **3:20–4:20**：一键 Day2，中途注入「迟到/少走路」；Agent 主动修路线和时间，展示计算结果与仍未知的事实。必要时展示多人 2/3 未生效→3/3 继续（多人作为可切独立场景，不依赖做完一趟才开始）。
- **4:20–5:00**：到 Day2 终点、标记 SIMULATED_COMPLETED，展开「全程回放」：初始/最终行程、地点来源、2 次触发的 Event、2 次 Guardian/Agent run、工具调用、签名确认、PlanVersion 差异。用一句话说明：模拟的是外界时间与 GPS，真实的是产品引擎的动作与结果。

实时 Agent 若超 40–60 秒或模型 503，可**主动切换到明确“先前同样场景录制的运行回放”**，然后继续现场演示时间跳跃；该屏清楚写 `RECORDED_REPLAY`，**不要把预录冒充现场自主生成**。这不是失败，真实故障恢复是系统能力。

## 8. 分阶段实施，不允许两周都只有 MD/绿测

**第一刀（最重要、最少代码）**：隔离 demo session + persistent `SimulationClock` + 当前 Journey 有效地点的地图蓝点 + `+1小时/下一站` + `SIMULATED_STATE_TRANSITION`，用真实浏览器点 Day1 起点→下一站（刷新仍在）；新 UI 与产品代码 commit + before/after 视频/图。这一刀尚不需要生成全世界。

**第二刀**：用 `CitySignalFixture + refresh_demo_signals + pulse_journey + Guardian` 接一张「下一站临时关闭」场景卡；**真实模型**得出带证据的提案、用户点同意、同 Journey 新 PlanVersion，不借用 mock 数据库内预设答案。

**第三刀**：随机城市池≥3、加速运行到 Day2 模拟结束、雨/迟到第二事件、两套不同随机 seed 的全流程录屏、遇 503 的显式 replay 降级、课堂 Presenter 控制台。

**第四刀（可选）**：3 人签名多人决策，在真实浏览器三身份、2/3 vs 3/3 拍屏。这个不允许阻塞单人端“整趟旅行完成”的交付。

每刀必须：`PRODUCT_SHA`、Chrome-use 或隔离 Chrome 从**可见按钮**实际点击、`run_id/journey_id/plan_version_before/after`、模拟时间线和位置、真实工具调用、provider snapshots 标注、截图/可选短录屏、明确 PASS/PARTIAL/BLOCKED；最小相关测试作为护栏。**不要只发测试结果而不动产品。**

## 必须通过的六条红线

1. SIMULATION_ENABLED=false 时模拟 API 全禁用；模拟 DB 与真实 DB 分开，用户真实数据/身份绝不被重置或复写。
2. 修改虚拟时间不会修改 OS 时间、认证/密钥有效期或真实供应商本次采集时间；时钟跨 HTTP、后台 worker、一整趟 Journey 一致。
3. 虚拟 GPS 不能被宣称为已物理到场，不得伪造 `DEVICE_ATTESTED`、真实成员位置或执行权威。
4. 模拟突发事件来源为 `SCENARIO_REPLAY`，不能包装成景区官方闭馆或真实暴雨。
5. 演示者只能注入“环境条件”，不能直接命令 Agent 选哪一个替代地点；方案变化仍经过实际权限/PlanVersion 机制。
6. 同随机 seed 的重播可复现环境；换 seed 至少两种城市/情境有效，第一版用真实来源预检池，不宣称所有城市都支持。

### 参考
- 官方 Playwright geolocation： https://playwright.dev/docs/emulation
- 官方 Playwright Clock： https://playwright.dev/docs/clock
- 官方 Chrome DevTools Sensors： https://developer.chrome.com/docs/devtools/sensors

**用户要求的最终交付是一个可以在课堂上几分钟亲手操控的「完整旅行 Agent 模拟系统」，不是模拟 API 白皮书，不是手工拼接后端结果。现在就先做第一刀。**
