# Revolution Lab 第一次真正给人用：2026-10-15 AI + 空白地图堵点修复

**真问题**：用户已通过真实 Nominatim 查到了“连城县，龙岩市，福建省”，但后续地图因瓦片不显示而只剩一块灰底；程序强制用户在图上点选或复制 OpenStreetMap URL，造成无法向下一屏移动。此前 GPT 提供的“三步引导”还只是滚动到旧表单，另一版虽然分屏，却仍让用户必经地图，并把 Hermes AI 关在正式行程后面。

## 这轮代码实际做了什么

- 在独立的 `trial/revolution-first-look-20261014` 分支直接改前后端，不触碰 Qoder、Commander、Revolution Lab 主工作分支。
- `frontend/src/trial/RevolutionQuickExplore.tsx`：
  - 用户点击 Nominatim 某条**公开近似中心**结果时，**立即进入兴趣选择**；不需要灰色地图、不需要再确认一次、不需要经纬度或 OSM 链接。
  - 页面明确标注：地名中心是 `CITY_CENTROID_UNCERTAIN` 的**约 2.5 km 范围的近似公开搜索区**，不是精确到场、更不是实时 GPS。前端记录 `EXPLICIT_GEOCODER_APPROX`，没有冒充 `MAP_TAP`。真实公开 POI API 要等用户点“搜索附近地点”时才调用。
  - 仍可自愿展开手动地图，决定精确搜索区。若地图瓦片为空白，不再堵住前进。
  - 顶部加一句自然语言（可修改），例如“我在连城，今天下午三小时，想轻松逛逛”，一键请求真实 Hermes 兼容模型给出**只读的兴趣类别工具建议**；模型不给出有效 `tool_calls` 时如实报告。
  - 搜索公开地点仍需要点击明确说明接收方的按钮；真正返回两条以上 sourceful POI 后可保存私人 Pocket Walk，使用原有带版本戳的 GO MODE，刷新恢复。没有结果不会创造假景点。
  - 若某候选的 `selection_state=READY_FOR_NATIVE_PLAN`，用户可选“让 AI 继续照看正式行程”，经真实 `selectBootstrapCandidate` 和原 `BootstrapJourneyStartPanel` 再转到正式 Journey Operator；未验证营业等必备事实时不放行。
- `trial/agent_preview_app.py`：仅在**本地试玩启动器**下，把新 `POST /api/v1/journeys/{id}/trial-ai-discovery` 添加到原 FastAPI app；HMAC bearer + 当前 in-force Journey membership + DRAFT + 主人权限验证；每用户 15 秒间隔、每半小时最多 5 次模型请求；拒绝非 loopback 7863/7865 网关 URL，不存密钥、不打印模型原始输出、不接收前端传入 API Key，不自动调用公开地点 API、不写入真实 Journey 状态。
  - 依靠 `CITYNEXUS_HERMES_API_URL`、`CITYNEXUS_HERMES_API_KEY`、`CITYNEXUS_HERMES_MODEL`（来自 `trial/wb2api_agent.py`）发送**真实 OpenAI-compatible tools 请求**。只有提供 `propose_public_discovery` 结构化 tool_calls 且满足严格类别白名单，才返回 `MODEL_TOOL_SUGGESTION`。
  - 这是**模型在引导期的真实只读工具建议**，**不是完整 HermesJourneyAgent 的 AgentToolGateway / 已持久化 AgentRun**。完整自主 Agent 仍在真实 ACTIVE Journey Operator 流程，绝不把前者包装成后者。
- `trial/try_revolution.py`：后台 Uvicorn 加载 `trial/agent_preview_app.py` wrapper；原 `app.main` 其他所有路由和权限机制保持不变。使用 `--agent` 就是明确选择启用 AI 配置，不再多问一遍 “y”；但**真正产生外部模型请求**仍只有网页里点“让 AI 帮我想想”时发生。支持已有本地环境变量 `CITYNEXUS_NOMINATIM_CONTACT_EMAIL`，减少重复输入。
- `frontend/src/api/citynexus.ts`：增加 `suggestTrialDiscovery()`，使用正常本机代理及浏览器现有签名 token，密钥只在后端。
- `frontend/src/trial/RevolutionFirstLook.tsx`：把 AI 配置状态交给真正的引导页；若用户明确从可信结果启动正式计划，自动滚到原计划确认组件。
- `frontend/src/trial/RevolutionQuickExplore.css`：自然语言引导卡和无需地图的简洁流程，手机布局受限。
- `frontend/e2e/revolution-quick-explore-ui.spec.ts`：源标为 **TEST_PROVIDER 的模拟网络 UI 回归**，断言不点按钮不调用模型/地名服务/公开地点服务；点城市结果直接进入分类，不加载 OSM 瓦片；验证保存 Pocket Walk 和刷新恢复。这不是实机 LIVE_PROOF。
- `.github/workflows/revolution-trial-ux-smoke.yml`：只运行 Python 语法、模型连接配置离线单测、前端 typecheck:all 和 Vite build，不发真实 AI 请求，不传真实 key。

## 你电脑上的一次更新命令

先在旧启动器终端**按 Enter**停止旧的本地后端与 Vite（换了后端模块，需要完整重启）。不清空任何 SQLite DB、不动锁文件、不动密钥。

打开 PowerShell：

```powershell
cd D:\moodle\CityNexus-Revolution-Trial
git fetch origin
git restore --source origin/trial/revolution-first-look-20261014 -- trial/try_revolution.py trial/agent_preview_app.py frontend/src/api/citynexus.ts frontend/src/trial/RevolutionQuickExplore.tsx frontend/src/trial/RevolutionQuickExplore.css frontend/src/trial/RevolutionFirstLook.tsx
py -3.13 trial\try_revolution.py --agent
```

网页：`http://127.0.0.1:14173/revolution`。不要复制 Markdown 的末尾星号。

### 现在真正需要的交互

1. 同一个绿色页面，先看到可编辑的自然语言：“我在连城，今天想轻松逛逛……”。点“让 AI 帮我想想”。**这次操作才会将这些字交给外部模型，可能计费**。若 AI 不可用，仍可直接输入城市。
2. 城市输入“连城”，点击“查找位置”：一次 Nominatim 请求，返回连城县等候选。
3. **直接点对应的整行“连城县，龙岩市”**，马上进入下一屏“你想逛什么？”！**不需要等任何地图加载，不用粘贴坐标，也没有地图复选框。**
4. 已选或自动采用 AI 建议的类别，点“搜索附近地点”：一次公开 Overpass 请求，显示真实 POI 或真实服务失败。
5. 选两个实际返回的 POI，保存私人散步并使用原生 GO MODE。若想进入完整 Operator，需要在有来源且具备计划启动资格的地点上主动选择，之后经过正式行程确认。
6. 如果连城县中心 2.5 km 内没有相关类型 POI，不允许“绿到成功”；回到地区或类别重新选择，不能假造地点。

## 模型/地点隐私与费用

- `--agent` = 明确配置模型，并不等于自动提交用户内容。用户在页面点击 AI 按钮时才向模型发送已展示的文字和行程地名。浏览器没有 wb2api Key。
- `7865 auto:cheapest` 免费优先但**最后候选可能收费**。有 15 秒请求间隔和 5 次/半小时的简单本地试用限流，**不是保证零收费**。
- “点击查找位置”只发送公开地名给 Nominatim；“点击搜索附近地点”只发送用户确认的公开大致坐标、类别和范围给 Overpass；地图瓦片按需单独加载。**没有隐藏发 GPS、私址或群成员身份**。
- MODEL_TOOL_SUGGESTION = 模型真的给出了一个 `propose_public_discovery` 工具建议，**尚未执行地点查询**；MODEL_NO_TOOL_CALL = 模型没按协议给建议；AgentRun 和正式权限执行仍需真实 ACTIVE Journey 的用户确认和工具步骤。
- AI 超时或地图不可达应显示中文错误和可继续路径，而不是不停要求用户多签一次。

## 给 Codex 的下一棒：只关一个真正的首次用户闭环

**不要**开新的 R110 验证工程。切到 trial 分支，保留用户的本机测试 DB、lockfile 和密钥，按这一条真体验做工程验收：

1. 在 Python 3.13 Windows 下 `py -3.13 trial/try_revolution.py --agent`，真实 7865 网关可达但绝不在自动 E2E 中调用付费模型。先 `npm run typecheck:all` 和 `npm run build`，修真正 compile blocker。
2. 用桌面 1440px 和手机 390x844 访问 `/revolution`。重复用户 screenshot：Nominatim 给出“连城县”后，地图瓦片全阻断仍然可以**点结果直达兴趣选择**，不输入任何 WGS84、不粘 OSM URL。
3. 一次明确模型点击检验 `/trial-ai-discovery` 使用真实签名 Journey 和 wb2api，不把“已配置”冒充返回 `tool_calls`，控制调用费用并记录模型实际反馈为隐私安全的摘要。不让 Agent 自动调用公开服务。
4. Overpass 成功才显示真实 sourced POI，失败则友好停在下一步可返回；两站保存要落服务器、GO 要刷新恢复，成员 token 切换不能串。
5. 有合格 native-plan sourced candidate 时可选择进入正式 Journey，必须经过原 `BootstrapJourneyStartPanel` 的授权/计划创建，Operator 必须显示真正工具/审批结果；若 Provider 无可行事实则明确 UNAVAILABLE，不掺假。
6. 把**用户能走通的连续点击**作为结案标准，不再让用户读代码、帮忙输入坐标和反复点同意。

**本 GitHub 施工的证据等级**：代码提交和静态核对，GitHub Actions typecheck/build 的实际结果应以 workflow 为准，**还没完成用户 Windows 上的真实 wb2api 工具响应和浏览器 UI 实机验收**。
