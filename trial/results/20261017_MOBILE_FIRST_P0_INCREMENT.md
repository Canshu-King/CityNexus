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
