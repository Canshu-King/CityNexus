HUMAN_CAN_USE = PARTIAL
LIVE_PROVIDER = PHOTON_HTTP_200 (3 real POIs)
TWO_POI_FLOW = PASSED (2 private stops saved; GO progress restored after reload)
WB2API_TOOL = PASSED (SIGNED_DRAFT_READ_ONLY_SUGGESTION; separate earlier run)
SIGNED_AGENT_RUN = NOT_CREATED (Journey remains DRAFT)
ANDROID_PHONE = NOT_TESTED

# Mobile-First P0 进展｜2026-10-17

## 已交付产品

- ACTIVE 行程的「行程」页加入 WB2API 工作记录卡，并提供签名成员专属的运行创建、最近运行恢复和按请求编号读取接口。
- 创建运行前核验本人身份、行程状态和一次授权；服务端先持久化成员绑定，再请求模型。
- 兼容接口固定单一模型配置、关闭预算重试，只提供行程、状态和已有调整三种读取工具；服务端执行层拒绝其他工具。
- 手机只展示数据库已保存的工具名、状态和时间，不显示模型内部推理、工具参数或返回原文。

## 本轮 P0 实测：真实地点、双站保存、GO、刷新恢复

- 修复了 Photon 地点被全部筛掉的问题。Photon 原始 OSM 类型使用 `N/W/R`，探索流程只接受 `node/way/relation`；适配层现在统一输出后者。跨层回归覆盖三种类型，并核对 bootstrap 实际使用的地点身份解析器。
- 聚焦回归：`uv run --project . python -m pytest -q tests/test_photon_poi_adapter.py tests/test_bootstrap_photon_draft_exploration.py tests/test_bootstrap_photon_provider_selection.py`，结果 `26 passed in 0.72s`；`git diff --check` 通过。
- 在 390×844 签名 DRAFT 手机界面选择宁波公开地图中心后，页面先展示了发送地点与类别的说明，再发起一次新的 Photon 公园/绿地搜索。Photon HTTP 200，页面得到 3 个真实地点：快鹿公园、月湖公园、天封公园。
- 选择快鹿公园和月湖公园，保存到当前签名用户的私有 Pocket Walk，点击“开始散步”。页面显示前往第一站；完整刷新后，两站和当前进度都恢复，进度为 `HEADING_TO_FIRST`。
- 刷新后的手机视口截图：`trial/results/assets/20261017-live-photon-pocketwalk-go-restored-390x844.png`。修复前的零结果截图：`trial/results/assets/20261017-live-photon-adapter-zero-result-390x844.png`。
- 独立试玩库只读汇总：2 条 `SAVED` 私有站点、1 个 Pocket Walk、1 条 `HEADING_TO_FIRST` 进度；没有写入 Places 表。Journey 本身仍为 `DRAFT`，没有创建 `AgentRun`。这次只验证了 Pocket Walk 的 GO 进度恢复，没有把它记成 ACTIVE 行程。
- 本次地点检索使用手动选择的宁波公开地图中心，没有调用地名搜索；当前 AI 关闭。此前真实 WB2API 调用属于单独的签名 DRAFT 建议证据，不是本次 POI/路线流程的一部分。

## 本机真实 AI 实测

- 在隔离试玩环境从 `/revolution` 页面发起三次签名 DRAFT AI 请求，均由 CityNexus 后端转发至本机 wb2api 网关并返回经过校验的建议。
- 请求使用 `auto:cheapest`；网关本轮实际选择 `deepseek-v4.1-flash`。
- 第二次覆盖情侣夜间活动到很晚、次日午后轻松出门的场景。模型返回经过服务端白名单校验的 `propose_public_discovery` 工具建议，类别为 `park/garden`，并提示实际开放时间须查公开地点来源。
- 真实 `tools` 协议探针返回 `inspect_journey` 工具调用帧；实际模型为 `global:deepseek-v4.1-flash`，`usage.credit=0`。这条探针只确认网关返回工具帧，没有执行工具或写入行程。
- 这证明 DRAFT 只读探索建议的真实模型工具调用已通。没有查询 POI provider，也没有创建持久化 AgentRun；响应中的 `provider_calls=0` 和 `agent_run_created=false` 与本次范围一致。
- 2026-10-17 本轮又从浏览器发起一次真实请求：页面显示「AI 建议已生成」，模型为 `deepseek-v4.1-flash`，后端返回 `park/garden` 类别的探索建议。请求没有访问地点服务、没有保存路线，也没有创建 ACTIVE 行程的 AgentRun。
- 390×844 实际页面截图：`trial/results/assets/20261017-live-ai-couple-draft-390x844.png`。
- 本机运行页：`http://127.0.0.1:14173/revolution`；本机 UI 与 API 健康检查均为 HTTP 200。

## 真实地点和行程流程

- 当前已完成一轮真实 Photon 搜索、两站私有保存、Pocket Walk GO 和整页刷新恢复，具体结果见“本轮 P0 实测”。
- 历史来源结果：Nominatim 曾返回厦门地名结果；Overpass 唯一一次 POI 请求返回 HTTP 502，没有重试。
- 历史 Photon 连城查询均未得到可选地点；后来定位到 Photon `N/W/R` 与探索端 `node/way/relation` 的身份格式不一致，并在本轮修复。之前记录的零结果仍作为修复前证据保留。

## 验证

- `uv run --project backend pytest -q backend/tests/test_mobile_compat_agent_run.py`：1 passed，覆盖签名、成员隔离、DRAFT 拒绝、请求去重、输出隐藏和越权工具拒绝。
- `npm.cmd run typecheck`：退出码 0。
- `npm.cmd run typecheck:all`：UI 组件拆分后退出码 0。
- GitHub PR #23 提交 `286e70657a19de7c144ef9fd8699a47b189d583e` 与 `255c6c1e50e0e4b61b7cf4b190c31cfaa28595ce` 的 `trial-build`：PASS。
- GitHub PR #23 当前提交 `9b0690937ea57baf7e74452bbccee2844a7a6771` 的 `trial-build`：PASS（Actions run [38979911296](https://github.com/Canshu-King/CityNexus/actions/runs/38979911296)；TypeScript、Vite build、Chromium mobile fixture 均通过）。
- 此报告中的新 AI 实测来自真实本机页面请求；上述 pytest 与既有手机截图仍分别按其 fixture / 浏览器证据等级理解。

## 2026-10-17 后续移动端检查

- 「换地区」按钮触摸高度从 38px 调整为 44px；浏览器快照在 375px 视口宽度下测得按钮为 112×44px。
- 点击切换「行程」→「我的」→「探索」后，没有新增地点搜索、AI 或支付请求。
- 城市选择和兴趣选择已拆成独立手机组件；首次进入页的按钮说明改为「点击后先创建行程草稿」。
- 390×844 浏览器初屏实测无横向溢出（文档宽度 390px）；只读取运行状态，没有发地点、模型或支付请求。
- PR #23 提交 `79b482891f5e886aadaf339326fa92af2f961c76` 的 `trial-build`：PASS（GitHub Actions run `38965055953`）。

## 尚未验收

- `SIGNED_AGENT_RUN = NOT_CREATED`：Pocket Walk 的 GO 进度已恢复，但服务端 Journey 仍是 DRAFT；当前没有真实 ACTIVE Journey，也没有可展示的持久化 AgentRun。
- `ANDROID_PHONE = NOT_TESTED`：完成的是 390×844 浏览器视口流程，尚未在实体 Android 手机上验收。
- 本次地点流程未经过地名搜索；宁波中心由用户在公开地图位置上选择。

## 下一步

Pocket Walk 双站保存、GO 和刷新恢复已完成。下一阶段是通过正式出行流程形成服务端 `ACTIVE` Journey，再验证 Hermes 工具轨迹是否写入服务端；实体 Android 验收也仍待完成。

## 2026-10-17 本轮继续施工

- 本机 wb2api key 已直接用于隔离试玩页的真实 AI 请求。双人偏好冲突场景返回公园/绿地建议，截图为 `trial/results/assets/20261017-ai-conflicting-preferences-result-390x844.jpg`，SHA-256 `83FAB076E00878F07CE3CCED0AA87FEBBAE496A323EF1DB018A6E89324BED916`。这是 DRAFT 建议，不是已保存的 AgentRun。
- 本轮两次公开地名搜索都收到 Nominatim `ConnectTimeout`，没有地点结果。此前页面把服务连接失败显示成“没有匹配地区”，容易让人以为确实搜不到。
- 已修改 `frontend/src/trial/RevolutionQuickExplore.tsx`：真实无匹配、地名服务不可用、搜索未启用、限流分别显示对应结果；搜索失败后保留地名，用户可换地区或粘贴公开地图链接。
- 新增四种状态的 Chromium UI 回归。命令：`npm.cmd run test:e2e -- --project=chromium --workers=1 --grep 'city search explains'`；隔离运行 `geocoderstatus20261017b`，端口 4191/18241，独立 SQLite，AI 关闭、地名服务由测试响应拦截。结果 `5 passed`，包括 1 项套件初始化和 4 项地名状态断言；无真实地点请求。随后只修正测试响应里的 provider 状态字段以匹配各自结果，没有改产品逻辑。
- 最终工作树执行 `npm.cmd run typecheck:all -- --pretty false`：退出码 0。
- 本轮代码只修正错误反馈，没有伪造地点。`TWO_POI_FLOW` 仍是 `NOT_REACHED`：目前未能拿到两处真实地点，Pocket Walk 保存、GO 和刷新恢复仍待真实来源支持；`SIGNED_AGENT_RUN` 仍是 `NOT_CREATED`。
## 2026-10-17 Photon follow-up

已按页面公开说明和单次授权，对连城当前公开中心各执行一次不同类别的真实 Photon 请求；没有重试同一类别：

| 类别 | Photon HTTP | Photon 原始要素 / adapter 返回 | CityNexus 可选地点 |
|---|---:|---:|---:|
| park/garden（此前同页请求） | 200 | 2 / 2 | 0 |
| museum/gallery | 200 | 0 / 0 | 0 |
| cafe | 200 | 1 / 1 | 0 |
| library | 200 | 1 / 1 | 0 |

cafe 和 library 的服务端回执显示 Photon 返回了原始要素且 adapter 形成候选，但最终 shortlist 为 0。原始 tag 没有进入安全回执，故不声称知道被筛掉的具体标签；没有任何地点写入收藏。四次都是 LIVE_PROVIDER 响应，当前连城查询结果仍为 LIVE_ZERO_RESULTS。页面授权在每次请求后复位。

已核实 Photon 官方 API 文档允许 /reverse 按 OSM 分类过滤；本次 200/零可选地点不能归因于端点错误。Photon 文档也说明其是地名检索服务，公共索引不承诺覆盖所有 POI 分类。来源：[Photon API](https://github.com/komoot/photon/blob/master/docs/api-v1.md)、[Photon 分类过滤](https://github.com/komoot/photon/blob/master/docs/categories.md)。

当前 TWO_POI_FLOW=NOT_REACHED：真实结果仍不足两处，Pocket Walk、GO、刷新恢复尚未运行。没有改成放宽受限地点过滤，也没有用测试地点顶替真实结果。

## 2026-10-17 本机 AI 直连复核

- 按用户授权，本机进程直接读取 `WB2API_KEY` 调用 `http://127.0.0.1:7865/v1/chat/completions`，使用 `auto:cheapest`。本次 HTTP 200，网关选择 `deepseek-v4.1-flash`，返回 `finish_reason=tool_calls` 和 1 个 `save_trip_preferences` 工具提议。凭据未写入代码、仓库或输出；这次直连只验证模型返回工具提议，没有在 CityNexus 执行该工具或写入行程。
- 390×844 签名 DRAFT 页面又完成一次真实 CityNexus AI 请求：`POST /api/v1/journeys/{private-id}/trial-ai-discovery` 返回 HTTP 200，页面显示来自 `deepseek-v4.1-flash` 的晚出发、次日上午不早起场景建议。实测截图：`trial/results/assets/20261017-live-ai-late-date-390x844.png`，SHA-256 `332E8AF6B3B741852CAAAF667816BA34EC10D549CB84FBC61BF90895170AF55E`。
- 隔离后端 `/api/v1/agent/runtime-status` 返回 HTTP 200，身份为 `HERMES_COMPAT_ENDPOINT`，`hermes_compat_configured=true`。当前签名会话的“行程”页显示还没有保存的私人路线；服务端 AgentRun 入口要求路线状态为 `ACTIVE`，所以本轮没有创建 AgentRun，也没有制造 ACTIVE 数据。`SIGNED_AGENT_RUN=NOT_CREATED`；当前差的是真实 ACTIVE 行程。
- 真实地点流程状态不变：Photon 尚无可用的两处 POI，`TWO_POI_FLOW=NOT_REACHED`；Pocket Walk 保存、GO 和刷新恢复还没进入执行。

## 2026-10-17 聚焦后端回归

- 命令：`uv run --project . python -m pytest -q tests/test_bootstrap_photon_provider_selection.py tests/test_bootstrap_photon_draft_exploration.py tests/test_r107_discovery_to_my_pocket_walk.py tests/test_r85_zero_catalog_bootstrap.py tests/test_r86_first_startable_real_city_journey.py tests/test_r87_first_live_city_discovery.py tests/test_r95_city_jump_and_provenance.py`
- 结果：退出码 0，`16 passed, 4 warnings in 4.49s`。
- 覆盖 Photon provider 选择、DRAFT 探索、R107 Pocket Walk 保存/恢复、R85-R87 首次地点发现和 R95 来源信息。
- 本轮只执行隔离 pytest；没有发起真实地点服务请求，也没有完成浏览器端双 POI、GO 或刷新恢复。

## 2026-10-17 Journey 启动身份校验

- `/api/v1/journeys/{journey_id}/start` 现在会先按路径 Journey 校验签名成员，并要求 `JOURNEY_EXECUTION_UPDATE` 能力；检查也覆盖已经是 `ACTIVE` 的幂等返回。未配置旅客签名密钥的旧测试模式保持原有行为。
- 聚焦命令：`uv run --offline --project . pytest -p no:cacheprovider tests/test_signed_journey_start.py -q`；结果 `2 passed`。数据库使用进程内 SQLite。
- 两项用例覆盖匿名请求拒绝、非成员拒绝、具备能力的成员访问 ACTIVE 快照，以及缺少启动能力时拒绝。
- 这些是路由授权回归，测试使用合成数据库记录；它们不代表创建了真实 ACTIVE 行程或 AgentRun。真实签名 ACTIVE Journey 与持久化 Hermes 轨迹仍待真实 Pocket Walk / Journey 启动流程闭环。
## 2026-10-17 手机行程与 Hermes 读取

- 签名旅客读取指定 AgentRun 和最新 Hermes 运行记录时，服务端校验 Journey 成员身份及 `JOURNEY_READ`；成功响应带 `private, no-store` 与身份相关的 `Vary`。前端读取指定 AgentRun 时携带旅客 bearer，并使用 `no-store`。
- 手机启动页只在服务端返回 `ACTIVE` 后切到行程页；返回 `PLANNED` 时保留启动确认页。Hermes 最近记录只在“行程”页读取；页面刷新后回到“行程”会重新读取服务端记录。
- 后端聚焦测试：`tests/test_signed_journey_start.py`、`tests/test_agent_run_signed_member_read.py`、`tests/test_mobile_hermes_run_binding.py`，`6 passed`，使用进程内 SQLite。
- 手机浏览器聚焦测试：`agent-run-restoration-auth-cache.spec.ts`、`revolution-mobile-compat-agent-activity.spec.ts`、`r86-first-startable-real-city-journey.spec.ts`，390×844 Chromium `3 passed`。该组浏览器测试使用 `TEST_FIXTURE` API 响应和隔离 SQLite；没有调用地点服务或 AI provider。前端 `typecheck:all` 通过，当前改动的 `git diff --check` 通过。
- 这些结果验证签名读取门禁、缓存控制和手机界面状态切换；测试中的 ACTIVE Journey 与轨迹是隔离测试数据。当前真实流程仍没有满足本地库中的两处 POI、Pocket Walk 实际保存、GO 后刷新恢复；没有真实签名 ACTIVE Journey 或服务端 Hermes AgentRun，因此持久化 Hermes 轨迹仍未验收。

## 2026-10-17 本轮：零结果引导与晚出发偏好

- 探索页现在能区分“服务返回了地点，但都不适合当前筛选”和“服务没有返回地点”。第一种情况按过滤原因给出一个下一步：更换搜索中心或更换地点类型；按钮只带用户回到对应选择区，不会自动再次搜索。
- 后端回执新增计数汇总：原始条数、可用条数、以及坐标、距离、重复项、访问限制等过滤原因的数量。回执和 ProviderCall 记录都只保存计数，不保存地点名称、坐标、原始标签或服务附加字段。筛选规则与候选地点门槛未变。
- 后端聚焦测试命令：uv run --offline --project . pytest -p no:cacheprovider tests/test_bootstrap_candidate_filter_summary.py tests/test_bootstrap_photon_provider_selection.py tests/test_bootstrap_photon_draft_exploration.py -q；工作目录 backend；结果 12 passed in 0.74s。
- 手机验收环境：Playwright authoritative run mobilep0_20261017_1043，前端端口 4201、后端端口 18301，隔离 SQLite C:\Users\仓鼠王\AppData\Local\Temp\_mobilep0_20261017_1043.db，AI disabled，未复用已有服务。R87 零结果引导和 390×844 夜间晚出发场景的 Chromium 用例均通过；最新截图运行包含 seed setup 1 项和夜间场景 1 项，共 2 passed (15.2s)。
- 夜间场景在 Explore 输入“成年情侣、今晚较晚、次日中午起床、13:00 后出门、留足休息时间”，切到 Trips 再返回后文字仍保留。用例把请求留在 TEST_FIXTURE，确认用户输入到达本地测试路由；没有调用真实 AI、地点服务、保存、GO 或付款。这个截图展示页面排版，不作为 AI 执行凭据。
- 截图：assets/20261017-ui-fixture-late-night-rest-preferences-390x844.png，SHA-256 48839FDC426DA09275C6BA89B0758AC3BFD9C4698E88F0E0A1771C0EE8438350。前端 npm.cmd run typecheck:all -- --pretty false 退出码 0。
- 本轮没有发地点搜索或 AI 请求。当前 P0 仍未完成真实两处 POI → Pocket Walk 保存 → GO → 刷新恢复；真实签名 ACTIVE Journey 和服务端持久化 Hermes AgentRun 仍未创建。

## 2026-10-17 本轮：手机触控与问 AI 快捷入口

- 探索页的“问 AI”入口会滚动并聚焦现有输入框，不会自动发起请求；晚出发偏好页面的浏览器回归验证了该行为。
- 首次空结果页的“更换地点类型”“更换搜索中心”按钮均加入 44px 最小高度；R87 浏览器断言检查了两个按钮的实际宽高。
- Photon OSM 身份映射补了 node / way / relation 的参数化契约测试，检查 external_id 与 OpenStreetMap 来源链接。该测试使用 MockTransport，没有连接 Photon。
- 验证：后端 `uv run --offline --project . pytest -p no:cacheprovider tests/test_bootstrap_candidate_filter_summary.py tests/test_bootstrap_photon_provider_selection.py tests/test_bootstrap_photon_draft_exploration.py -q`，15 passed；`npm.cmd run typecheck:all -- --pretty false` 退出码 0；Chromium `r87-first-live-city-discovery.spec.ts` 与 `revolution-night-out-rest-preferences.spec.ts`，3 passed。
- 浏览器验收使用隔离运行 `mobilep0_20261017_1151`（前端 4202、后端 18302、临时 SQLite）；API 由 TEST_FIXTURE 响应，AI 关闭，没有请求地点服务、模型或支付。现有 390×844 页面截图为 `assets/20261017-ui-fixture-late-night-rest-preferences-390x844.png`（SHA-256 `48839FDC426DA09275C6BA89B0758AC3BFD9C4698E88F0E0A1771C0EE8438350`）；本轮未单独截图快捷入口。
- 本轮没有真实地点搜索、Pocket Walk 保存或 GO；当前仍缺两处可用真实地点，所以刷新恢复闭环尚未到达。已有模型响应仍是 DRAFT 建议，当前试用库没有真实签名 ACTIVE Journey 或持久化 AgentRun。
## 2026-10-17 本轮：新地图中心地点搜索

- 在签名 DRAFT 页面通过公开 OSM 链接选择杭州西湖附近地图中心，并选择“博物馆和艺术”；页面在查询前说明地点区域与类别会发送给 Photon。浏览器视口为 1058×676，本次不是手机验收。
- 城市搜索内部接口返回 HTTP 200，但状态为 `GEOCODER_UNAVAILABLE`；Nominatim 回执为 `ConnectTimeout`、0 个地区结果。没有重试。
- Photon 接口返回 HTTP 200，服务端 attempt 记录 3 个原始要素、adapter 返回 3 个候选；CityNexus 响应为 `LIVE_ZERO_RESULTS`，0 个可选候选，未进入 Pocket Walk 保存或 GO。没有重试。
- 页面标题仍显示原行程城市“连城”，而新查询使用刚确认的杭州地图中心。这个标题需要改为当前探索中心，避免与实际搜索区域不一致。
- 实际 HTTP JSON 未包含 `filter_summary`。当前工作树的发现函数会生成该字段，并由无 `response_model` 的路由直接返回；活动服务代码版本或实际请求路径尚未绑定到当前 checkout，缺字段原因未定。

P0 仍未闭环：两处真实 POI、Pocket Walk 保存、GO 后刷新恢复；真实签名 ACTIVE Journey 与持久化 Hermes AgentRun 也未创建。

## 2026-10-17 本轮：上海咖啡馆查询界面与手机回归

- 在 390×844 手机视口的签名 DRAFT 页面，先展示 Photon 公共地点服务与查询区域说明，再从公开 OSM 地图链接选择上海人民广场附近中心（31.2304, 121.4737），外层标题显示地图中心坐标；Journey 私有 cityName 仍为“连城”。
- 用户点选“咖啡馆”后只发起一次查询。本机 CityNexus 的 bootstrap-discovery 返回 HTTP 200，页面响应标记 LIVE_PROVIDER / LIVE_ZERO_RESULTS、0 个候选；响应没有 filter_summary。页面没有可保存地点。
- 同一页面的健康检查 e2e_run_id 与 e2e_database_id 均为空，且未取得 Photon 出站请求轨迹；LIVE_PROVIDER 标签未绑定到当前隔离 checkout，不能作为 Photon 实际调用证据。没有保存、GO、刷新恢复或新截图。
- 后端聚焦命令：uv run --offline --project . pytest -p no:cacheprovider tests/test_photon_poi_adapter.py tests/test_bootstrap_photon_draft_exploration.py tests/test_bootstrap_filter_summary_route.py tests/test_bootstrap_shortlist_private_cache_headers.py tests/test_r108_pocket_walk_go_mode.py -q；backend 工作目录；结果 33 passed、4 warnings。测试数据库为本机临时 SQLite，完成后已删除本次数据库文件与 WAL sidecars。
- 手机 UI 回归使用 authoritative 隔离运行 mobile_p0_20261017_135806_71515f0e，前端/后端端口 43617/19617、独立临时 SQLite、AI disabled。首跑有 3 项测试断言沿用旧坐标/旧空结果文案而失败；只改测试期望后重跑，地图中心标签、过滤计数、单候选提示和 TEST_FIXTURE 刷新恢复共 6 passed。该运行没有访问 Photon、AI 或真实保存接口；临时数据库与 sidecars 已清理，端口已关闭。
- 另一组独立 authoritative TEST_FIXTURE 运行 mobile_p0_20261017_140020_cca4be1d（端口 43618/19618，AI disabled）验证 Springfield 城市歧义需要用户选择、晚出发偏好跨页保留且只在点击后发送；2 passed，没有调用地名、POI、AI 或付款服务。该临时数据库与 sidecars 已清理。
- 前端 npm.cmd run typecheck:all -- --pretty false 退出码 0。

P0 仍未闭环：当前页面没有两处可用真实 POI，Pocket Walk 保存、GO 与刷新恢复尚未完成；真实签名 ACTIVE Journey 和持久化 Hermes AgentRun 仍不存在。

## 2026-10-17 14:35 本机 P0 进展

- 本机试玩页尝试搜索公开区域“杭州市 西湖区”。当前 Journey 成员校验返回 HTTP 403（REQUEST_ERROR），请求在进入 Nominatim 前被拒；本次地点服务调用数为 0。继续前需要在试玩页进入一个有效签名旅客的 Journey。
- 探索地点卡片已加大触控面积，并清楚标出第 1 站、第 2 站和当前选择状态。
- 后端 LIVE_RESULTS 过滤汇总路由测试：1 passed；使用 Photon 测试响应，3 条候选中 2 条通过，响应只带计数汇总。
- 手机 Playwright：Hermes 成员切换清空旧轨迹 1 passed；探索→地点选择→Pocket Walk→GO→刷新恢复用例 1 passed。用例中的接口响应为 TEST_FIXTURE。
- npm.cmd run typecheck:all -- --pretty false：退出码 0。
- 当前真实闭环停在地点搜索授权；真实双 POI、Pocket Walk、GO 与刷新恢复待有效 Journey 会话。当前试用库没有签名 ACTIVE Journey 或 Hermes AgentRun。

## 2026-10-17 本轮：厦门真实地点 → 私人散步 → GO 刷新恢复

在独立试玩库和隔离页面中，从普通的签名旅客入口实际走完：输入厦门 → 使用公开 OSM 链接选地图中心（24.4798, 118.0894）→ Photon 搜索 → 选两站 → 保存私人散步 → GO → 刷新恢复。没有调用 Nominatim，也没有使用测试地点。

- 搜索前的签名 readiness 返回 HTTP 200：`provider=photon`、`expected_recipient=Photon by Komoot public geocoding service`、`external_request_allowed=true`、`test_only=false`；页面在搜索按钮前说明所选区域和类别会发给 Photon。用户授权的联系邮箱仅用作 Photon User-Agent 联系方式，本报告不记录邮箱。
- 第一次实际 Photon 查询选“咖啡馆”：CityNexus 接口 HTTP 200，页面显示 1 个真实结果：Basao cafe（约 60 米，OSM node 来源链接）。
- 第二次查询换成“公园和绿地”：接口 HTTP 200，页面显示 3 个真实结果：嘉禾园（约 730 米）、白鹭洲公园（约 740 米）、南湖公园（约 1.2 公里）。页面状态为 `LIVE_RESULTS / LIVE_PROVIDER`，来源卡片链接指向对应 OSM 对象。
- 选嘉禾园和白鹭洲公园后，`POST /api/v1/journeys/{id}/bootstrap-discovery/pocket-walk` 返回 HTTP 200；页面显示路线已保存到私人行程。
- 点击“开始散步”后，`POST /api/v1/journeys/{id}/bootstrap-shortlist/pocket-walk/go` 返回 HTTP 200。页面显示“正前往第一站”。
- 强制刷新后，`GET /bootstrap-shortlist` 返回 HTTP 200，页面恢复同两站路线和“正前往第一站”；`GET /journeys/{id}` 返回 HTTP 200，Journey 自身状态仍为 `DRAFT`。因此已验证的是 Pocket Walk GO 状态可保存、可刷新恢复；它不等于正式 Journey 的 `ACTIVE` 状态。

本次隔离运行端口为 14273/18301，独立数据库 `_revolution_hands_on_20261017_151206.db`。没有运行导航、付款或预订。

AI 网关在新试用环境中配置为 `auto:cheapest`，本轮没有另发模型请求。Journey 仍为 DRAFT，尚无可用于服务端 ACTIVE Operator 的行程；本轮没有创建 Hermes AgentRun，也没有宣称工具轨迹已落库。

`TWO_POI_FLOW`：REAL_PROVIDER_PASS；`PRIVATE_POCKET_WALK_SAVE`：PASS；`POCKET_WALK_GO_REFRESH_RESTORE`：PASS；`SIGNED_ACTIVE_JOURNEY`：NOT_CREATED；`PERSISTED_HERMES_AGENT_RUN`：NOT_CREATED。

真实手机视口截图：`trial/results/assets/20261017-photon-xiamen-pocket-walk-go-reload-390x844.jpg`，SHA-256 `4EF83E3DA840E6FCBBDA03FA9674F455C223E13E2ABC0B5A4A3D633A01361C22`。截图记录刷新后两站和 GO 进度状态。

## 2026-10-17：Chrome-use 旧会话恢复实测

- 在独立 Chrome-use 会话和内存数据库中，实际点击“开始探索”创建测试旅客与厦门 DRAFT 行程；接口分别返回 201。
- 保留签名 bearer 和本地行程指针，仅移除本地旅客编号，再由浏览器重新打开页面。服务端 `/api/v1/travelers/session` 返回 200，私有 `bootstrap-shortlist` 成员读取返回 200，页面恢复厦门探索状态。
- 此次只验证浏览器中的旧会话身份恢复；没有真实 POI、Pocket Walk、GO、AI 请求或 AgentRun。临时服务已停止，数据库为内存库。
- Chrome-use 截图调用超时，没有生成截图文件；页面状态和两项 HTTP 200 由浏览器快照及请求记录确认。

## 2026-10-17 Chrome-use 交互复测

- 环境：隔离试玩页 `http://127.0.0.1:14175/revolution`，390×844 手机视口；测试对应 PR #23 当前代码 SHA `35ec0ed503628324da1df9b63db1b8f802cb195f`。通过 Chrome-use 的真实鼠标点击与键盘刷新操作页面，没有调用自动化夹具代替这轮交互。
- 操作：在“探索 / 行程”之间切换，进入手动选地点；输入“福州”后按页面说明发起一次地点搜索。后端的 `POST /api/v1/journeys/{journey_id}/bootstrap-city-search` 返回 HTTP 200，但页面结果为 `GEOCODER_UNAVAILABLE`，没有拿到 POI。当前脱敏记录只有本地路由的 HTTP 状态，不能确定上游具体失败原因。
- 刷新：强制刷新后，城市输入、偏好文字和失败状态仍显示；没有自动重发搜索。浏览器只观察到这一笔地点搜索请求。
- 结果：这轮没有进入双 POI 选择、Pocket Walk 保存或 GO。没有重试地点服务，也没有重复 AI 请求。旧的厦门成功闭环证据仍以本报告前文记录为准；本轮福州查询失败不改写那次结果。
- 本轮没有修改产品代码或保存新截图；本节记录的是 Chrome-use 浏览器快照与网络请求观察。

## 2026-10-17 21:03 Chrome-use：武汉真实咖啡地点 → Pocket Walk GO → 刷新恢复

- 运行版本：PR #23 `design/revolution-mobile-first-v1`，代码 SHA `bf00dc739ef6e9b5ea6690a3416534fc8b2a995f`；隔离 worktree `citynexus-pr23-user-openable-20261017`，前端 `http://127.0.0.1:14176/revolution`，后端 `http://127.0.0.1:18205`，数据库 `backend/_revolution_hands_on_20261017_204330.db`。没有复用旧 14173 页面或数据库。
- 前端与后端健康检查均返回 HTTP 200，`status=ok`、`database=ok`。此试玩环境显示 `ai=disabled`、`ai_state=CONFIGURED_UNVERIFIED`。
- Chrome-use 在 390×844 视口操作：开始探索后，`POST /travelers` 与 `POST /journeys` 均返回 201；隔离库中是一条 DRAFT Journey。
- 对“武汉市”的 Nominatim 请求仅发出一次，CityNexus 收到地名服务 `ConnectTimeout`，没有结果；没有重试。之后在页面明确选用公开 OSM 地图链接定位到武汉 `30.5928, 114.3055`，页面说明搜索会将区域与类别发送给 Photon。
- 选择“咖啡馆”并只发起一次 Photon 地点搜索。页面显示 3 个公开候选：A Giraffe Coffee&Cacao（约 1.5 公里）、Puzzle Coffee（约 1.3 公里）、Lilly Cafe（约 1.5 公里）；均显示 OSM 来源。隔离库回执为 `photon / bootstrap_city_discovery / SUCCESS` 1 条。
- 选择 A Giraffe Coffee&Cacao 为第一站、Puzzle Coffee 为第二站。`POST /bootstrap-discovery/pocket-walk` 返回 200；数据库有 2 个 `photon / SAVED` 站点。
- 点击“开始散步”，`POST /bootstrap-shortlist/pocket-walk/go` 返回 200。页面进入“正前往第一站”。
- 强制刷新后，服务端恢复两站路线和“我完成了第一站”进度控件；readiness 与 shortlist 均返回 200。没有重发地点查询，也没有把 Journey 状态改成 ACTIVE。
- 本轮验证结论：`REAL_PHOTON_RESULTS=3`、`PRIVATE_POCKET_WALK_SAVE=PASS`、`POCKET_WALK_GO=PASS`、`GO_REFRESH_RESTORE=PASS`。这是隔离 Chrome-use 会话的实测，用户本人尚未打开验证（`USER_VERIFIED=NOT_YET`）。没有调用导航、预订或付款。
- AI / Hermes 仍是下一阶段：本试玩健康状态为 `ai=disabled`；隔离库没有签名 ACTIVE Journey 或 Hermes AgentRun。此前一次 DRAFT AI 请求得到 HTTP 502，本轮没有重试，也没有宣称 AI 工具轨迹已落库。

可直接打开当前页面：`http://127.0.0.1:14176/revolution`。启动器终端仍运行 `trial/try_revolution.py`；本机服务保持开启。
