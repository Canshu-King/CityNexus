# CityNexus Revolution | Mobile-First V1 — 立即动工任务书

**日期**：2026-10-16（Asia/Shanghai）  
**状态**：已开工，已有实质 React/CSS 代码提交，不是只创建任务。  
**施工分支**：`design/revolution-mobile-first-v1`  
**继承修复基线**：`fix/revolution-first-human-e2e-20261015` @ `340679d4725393962b6c21e6af362ea502277edb`；PR #20 尚未并入试用主分支，**所以本分支先向 fix 分支发 PR，不向 commander/control 或 Qoder 产品分支合并**。  
**执行主责**：Codex；**配合人**：Qoder（仅审查 UI 接口复用及主线迁移约束，暂不直接改这个设计分支）。  
**触发原因**：真人反复截图证明旧 UI 存在重度开发者术语、超级长表单、满宽大按钮、白屏地图依赖、多层授权和用户卡死。修复分支虽然补过用户闭环，但样式仍像连续堆出的实验工具，而不是现代手机 App。

---

## 目标：一个正常人愿意天天打开的旅行 App

不是增加卡片数量，也不是“AI 科技感渐变”。基准心智模型：

1. **探索**：打开手机，看见 CityNexus 和「想去哪儿逛逛？」；一段可编辑的自然语言 + 清晰的公开地区搜索/发现地点操作。模型/地图请求只在用户主动触发后发生。
2. **行程**：真正从当前签名身份的服务器读取两个地点与 GO MODE 进度；不能存一个前端假行程。可一键回到原版真实 GO controls 继续执行；正式 ACTIVE Journey 显示现有 LiveRecovery / Journey Operator。
3. **我的**：仅显示实际设置和可解释的来源状态；技术细节默认隐藏。不要把“AI 网关已配置”当成“AI 已成功推理”。
4. **地图**：地点卡片、地图、导航自然切换；网络/瓦片不可用时仍可通过真实来源的地点列表完成操作；无 GPS 或到场真相不得伪造。
5. **视觉语法**：浅色自然背景、留白、清晰的中文信息层级、统一动作色、44px+ 触摸目标、底部安全区、可读错误与一个突出主要 CTA。不许出现 WGS84、test provider 内部代码、AgentRun ID、UUID、数据库名在默认首屏。

### 非目标
- 不做 Qoder 和 Revolution 全量融合，不换后端、数据库、Agent 授权。
- 不构建另一个假聊天机器人、假地理 fixture 或内置“永远有地点”的营销卡片。
- 不批量重写 V8Experience（目前 4900 多行）或清理大范围历史 ORD/R 任务。
- 不强制引入 React Native/Ionic，不复制商业产品的资产或受版权保护的视觉素材。

---

## 已开工代码：先保护，再继续

这轮已在设计分支新增：

- `frontend/src/trial/RevolutionMobileNav.tsx`：真正的中文**探索 / 行程 / 我的**底部导航（使用仓库已安装的 `lucide-react`），按钮语义、aria-current、私人路线存在提示。
- `frontend/src/trial/RevolutionMobileV1.css`：**只作用于 /revolution 的移动端样式**，安全区域、浅色卡片、按钮对比度、404/无数据体验、桌面容器及 390px 适配；不修改全仓 `styles.css`。
- `frontend/src/trial/RevolutionFirstLook.tsx`：新 App 外壳与三分区交互；旧 R107/R108 QuickExplore/LiveRecovery 真业务继续挂载。行程页不造假，只显示原服务器 Pocket Walk 回执或“还没有路线”。
- `frontend/src/trial/RevolutionQuickExplore.tsx`：增加 `onPocketWalkChange` 回调，把服务端读取/保存/GO 结果发送给行程 tab；未持久化数据不会冒充已保存。

**重要**：这是起跑线，不要“test only 然后 done”。如果首次 push CI 有任何 TS 或 CSS 报错，Codex 的第一个动作就是按具体错误修复。任何普通用户看着不自然的控件都要实际改掉。

## 外部开源项目选型（先小样证明，不要引入依赖战争）

当前技术栈来源于仓库 `frontend/package.json`：React 19、Vite 7、TypeScript、MapLibre、Lucide、Playwright、Storybook、TanStack Query 已安装。

1. **`ant-design/ant-design-mobile`**：移动端表单、ActionSheet、TabBar、Toast 候选；MIT。官方确认 v5 兼容 React 19 需要 `unstableSetRender` 适配（https://mobile.ant.design/zh/guide/v5-for-19/）。**必须**先在隔离 Storybook/试验屏验证 React 19、StrictMode、Toast/Popover 行为及实际包体积，再改 `package.json` 与锁文件。不要直接全局替换、不要让 `npm ci` 重现 EUSAGE。
2. **`Temzasse/react-modal-sheet`**：地图 bottom sheet 候选；MIT，依赖 Motion。官方说明需安装 `motion`，在 StrictMode 下仍有动画注意点。先试遮罩、键盘、安全区、返回键和地图尺寸；失败就用无额外依赖的 CSS dialog/list fallback，**绝不因地图 sheet 影响地点列表**。https://github.com/Temzasse/react-modal-sheet
3. **`maplibre/maplibre-gl-js`**：已经在项目中，**不得重新引入第二地图引擎**。重点是服务可用性、离线/超时回退、地图高度和手势。
4. **`shadcn-ui/ui`**：桌面或高级工作台的备选，不在同一手机路由混入第二套视觉系统。
5. **`lucide-react`**：已经安装，现阶段足够完成主导航和常规图标。第一阶段零额外 npm 依赖是刻意降低产品风险。

---

## Codex 立即施工顺序（精确到代码，不许转交别人继续写规划）

### M0 — 合并现有修复成果，落实基本手机外壳（已提交初稿，继续实测）

1. 在分支 `design/revolution-mobile-first-v1` 中获取最新提交，跑 `npm run typecheck:all`、`npm run build`、离线 Python smoke。CI workflow `.github/workflows/revolution-trial-ux-smoke.yml` 已扩展至该分支。
2. 用干净的 Playwright/Chromium 访问 `/revolution`，以 390×844、430×932、1440×900 截图。确认新启动页、新 Explore、Trips、Me 的布局真的存在，底部 nav 可点并有安全区；没有无意的横向滚动、遮挡输入框、超宽按钮。
3. 验证换 tab 不触发任何 Nominatim、Overpass、Hermes、支付请求，不重建 DRAFT，不使 GO progress 重置。不串 member bearer。
4. 当服务器没有 pocket walk，Trips 只能显示没有真实行程；真实 GO 刷新后应显示当前签名成员的两个 stop 与正确进度。高级 UI 折叠不可成为主流程依赖。
5. 修这轮初稿的任何真实 TS、a11y、重载/切 tab/StrictMode 生命周期问题。不要以“架构大改”作为拖延的借口。

### M1 — 将一千行 QuickExplore 拆成可维护的用户屏幕

现在 `frontend/src/trial/RevolutionQuickExplore.tsx` 超过 1000 行，集中了网络请求、signed bearer、AI、错误诊断、地图、路线和 GO。

创建 `frontend/src/trial/mobile/` 下受测的可复用小组件：

- `TravelIntentComposer`：自然而短的 AI 输入；**配置成功 ≠ AgentRun**；模型失败可跳过，不阻塞地名搜索。
- `CityPicker`：用户输入连城、公开地名查询，仅一次明确动作；用户点近似中心卡片马上进入下一屏，地图 tiles 不作为必选关卡。
- `InterestPicker`：不超过四个浅显中文类别，一次明确 POI provider 请求。
- `PlaceResultList`：真实地点卡片，清楚区分 TEST/LIVE/UNKNOWN，不显示假门票、假营业、假 ETA。
- `PocketWalkCard`：成员私有两站 GO 状态，操作来自服务端持久化事实。
- `JourneyStateBanner`：明确操作错误、恢复按钮、空数据状态；技术细节折叠。

网络签名、持久化、JSON 契约留在原 `cityNexusApi`，可以提 `useQuickExploreController`，但不能通过拆文件改变请求语义、重复请求或丢失身份 epoch guard。

### M2 — 现代地图与地点卡片（真实可点）

- 沿用 MapLibre；地图可用就展示标记与底部地点 sheet，不可用就显示 list fallback，并保持保存路线功能可用。
- 用户的来源链接始终指向源，打开外站前有清楚可理解的操作。不预先代点击任何授权。
- 不使用需要注册付费 key 的图库/SDK。POI 如果没有授权可展示的照片，就使用类型 icon/简单插图，**不要盗取或错配图片**。
- 手机底栏不得盖住地点选择、确认、输入键盘，尤其 Android Chrome 390x844 和 430x932。
- MapLibre vs React Modal Sheet gesture 冲突要做真实 Playwright touch 试验；不能只在代码里“应该可以”。

### M3 — UX 产品闭环和真实模型

第一次普通人体验应能完成：

`输入连城 → （可选）一句话告诉 AI → 地名搜索 → 点真实地名卡片 → 选兴趣 → 搜真实地点 → 看来源 → 选两站 → 保存 → GO → 刷新恢复。`

逐项保存响应截图和网络/服务器日志。至少运行一个签名用户的 backend E2E，覆盖前端请求到后端响应的完整路径；测试结果记录 PASS/BLOCKED，provider 来源单独标记 TEST_PROVIDER 或真实服务。

如 REAL AI 测试一次，需要本机合法的 `WB2API_KEY`、用户启用 `--agent` 和已有计费权限；最多一次受控请求，不公开 key、完整用户文本或 token。 `MODEL_TOOL_SUGGESTION` 只能报“模型给出工具建议”；真实持久化 AgentRun 需要进一步 ACTIVE Journey Operator。

### M4 — 页面验收和交付

至少完成：
- React/TS/build + 原有 narrow API regression。
- 390×844、430×932、1440×900 的**真实页面截图**，含 Welcome、Explore、Trips、错误恢复四种真实状态。截图里不暴露 key/私人行程。
- 用自动化浏览器逐个点击：底栏切换、快速地名选择、出错返回、公开地点列表、保存路线、GO、刷新恢复、键盘覆盖；至少对触摸目标做 ≥44px 检查。
- 对没有数据/网络失败/Agent 没启动也能前进的清晰失败和恢复状态进行验收。首页从“我想旅行”到主要 CTA 不超过一屏。
- a11y 测试：按钮、当前导航、焦点、屏幕阅读器标签及对比度，减少动效偏好。
- 保持 `/v8/hub` 与旧产品默认分支不变；不要把设计分支当成已经融合到主线。
- 新增 `trial/results/20261016_MOBILE_FIRST_V1_RESULT.md`，第一行报告 `HUMAN_CAN_USE = YES/NO/PARTIAL`，具体哪个闭环通过、哪个 BLOCKED；逐项写出 CI、Playwright、signed backend、真实 provider、真人手机证据级别。
- 提交并 push 到本分支，PR base=`fix/revolution-first-human-e2e-20261015`，head=`design/revolution-mobile-first-v1`。Codex 改动只针对产品和相关 narrow 测试；报告与 commit 必须对应一致。

**阻塞准则**：如果测试说明 API 契约有缺口，先由 Codex 在当前分支提出最小可验证补丁；只有确实涉及 Qoder 跨分支契约时才明确交给 Qoder 一个具名接口。禁止为保持“漂亮的绿”伪造地点、来源、Agent/tool call、到场或订单。

---

## Qoder 收到的任务（跟主线协同，不并行修改这里）

- 检查 Qoder 当前 `mirror/integration-frontend-apple-pass1` 已有 `frontend/src/design-tokens.css`、V8 mobile bottom nav、原有 MapLibre 等能力，提出可复用的**具体模块/API**，只做审查或一个独立迁移建议。
- 不把本设计分支直接并进 `commander/control`（它是协调台账，不是完整 App 代码）。
- 等 Codex 用手机真实跑完 M0/M1 且 UI 具有独立证据后，再讨论如何吸收到 Qoder 产品线，不要启动无边界“全量融合”。
- 若 Codex 的任务指出一个确切共享修复需求，Qoder 可以在自己的分支做该**窄补丁**并给 commit 供审查，禁止双方同时改同一个文件。

---

## 一键执行给本地 Codex

```text
开始 CityNexus Mobile-First Revolution V1 的实质施工。
仓库 Canshu-King/CityNexus；git fetch origin；
切到 design/revolution-mobile-first-v1，
先读仓库根 AGENTS.md 和
trial/tasks/20261016_REVOLUTION_MOBILE_FIRST_V1_EXECUTION.md。
我已经创建了手机底部三 Tab / scoped CSS / 真 Pocket Walk
服务器状态联动的第一批代码。你不是来重新设计任务书的，
而是继续做真正的产品代码、UI 构件拆分、实际浏览器交互
和手机视口验收。任何编译/运行阻塞立即修；每个有效功能增量
commit+push 到本分支，并回写 PR/Issue 的实际进度和截图。
严禁把 API fixture 当 LIVE、模型配置当 AgentRun、
自报到达当 GPS、Qoder 主线或全量合并当本轮交付。
M0-M1 做到用户能看到清楚的新 App，再 M2-M4 做完整体验。
把真正的中间产品交付出来，别在审核和报告里耗尽时间。
```

## 当前实际证据级别

已提交设计分支与第一批 React/CSS 改动；GitHub Actions compile gate 已配置，**全套手机浏览器与真实用户验收仍由 Codex 完成，不能在 GitHub 文档里提前填 PASS**。
