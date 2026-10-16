HUMAN_CAN_USE = PARTIAL

# Issue #21：手机优先版验收结果

截至 2026-10-16。当前代码在 `design/revolution-mobile-first-v1`；手机体验提交为 `9fc03490a8b1043fe1b9ac9bfba14bc4fe46a39e`，地图首次轻触修复为 `29cebe264a910cb7157b7b6036b03bc9cf2f3290`。PR #23 的目标分支仍是 `fix/revolution-first-human-e2e-20261015`。本报告记录可复现结果；不代表已合入 Qoder 主线。

## 给普通用户的结论

现在可以打开 Revolution 手机外壳，在「探索 / 行程 / 我的」之间切换；探索页有紧凑的 AI 输入区、清楚标明来源和不确定性的地点卡片，以及需要用户主动打开的地图。没有地点数据时，页面会明确说没有可靠结果，仍可换地区或使用公开地图链接。

主要旅行闭环仍未达到真人可用：隔离后端没有配置可用的实时地名与 Overpass 来源，实际搜索没有返回可信地点；AI 运行时也未配置。因而本次没有在浏览器中完成“真实地点 → 保存 Pocket Walk → GO → 刷新恢复”的全流程。R107/R108 的后端接口回归通过，但候选数据明确是 `TEST_PROVIDER`。结论为 **PARTIAL**，不能把测试数据说成真实地点或 LIVE。

## 这轮实际改了什么

- 调整了移动端城市输入高度和探索页顺序；点选搜索结果后停留在地区确认步骤，用户可以直接用近似地区中心，也可以自愿打开地图微调，地图不会再自动把人带走。
- 将探索页中的 AI 输入和地点卡片拆成 `MobileAiPrompt`、`DiscoveryPlaceCard` 两个组件。AI 只在用户点击时才请求；当前未配置，所以按钮正确保持禁用，没有发模型请求，也没有声称发生 AgentRun。
- 地点卡片显示来源状态、可用距离和“营业与费用需自行核实”，只展示通过 OpenStreetMap 主机与路径校验的来源链接；选地点按钮达到 44px 触摸高度。
- 地图改成显式同意后才加载公开瓦片；地图说明、不可用提示和标记颜色适配中文手机页面，主要触摸控件至少 44px。真实触摸测试中，轻触地图会放置点位并进入兴趣步骤，不会自动发起 Overpass 搜索。
- 修复地图首次轻触的真实运行时错误：此前首次创建 MapLibre 标记时先 `addTo`、后设置经纬度，会报 `Cannot read properties of undefined (reading 'lng')` 并中断进入兴趣步骤；现先设置坐标再挂载。失败追踪复现该错误，修复后单项与完整手机 Chromium 用例均通过。
- 新建本地 Journey 后，后续 POST 会带上服务端签发的 traveler bearer；没有把 bearer、Journey ID 或个人行程写进截图和报告。
- 继承并保留了远端 PR #23 已有的签名 Journey Operator 状态面板；本轮没有改 Qoder 主线、`/v8/hub`、`commander/control` 或默认分支。

## 验收证据

| 项目 | 结果 | 证据边界 |
|---|---|---|
| TypeScript | 通过，`npm.cmd run typecheck:all`，退出码 0 | 本地隔离工作树 |
| Vite 生产构建 | 通过，`npm.cmd run build`，退出码 0 | 有体积警告：主 JS 约 1.86 MB，MapLibre 约 1.05 MB（未压缩） |
| Chromium 手机 UI | 6/6 通过，390×844、开启触摸模拟 | 其中地点与行程数据使用显式 `TEST_PROVIDER` fixture；地图瓦片请求在该用例中被拦截 |
| R107/R108 后端窄回归 | 6/6 通过，独立临时 SQLite | 测试覆盖私有 Pocket Walk 保存、回读、GO 状态转换和拒绝路径；地点候选是测试数据，不是实时来源 |
| 本地真实后端浏览器连接 | 健康检查 200；创建 traveler 201；创建 Journey 201；带签名身份读取 bootstrap-shortlist 200 | 证明本地服务、签名身份和受保护读取工作；该 Journey 没有已保存路线 |
| 实际地名搜索 | 页面显示“没有找到足够可靠的地名结果” | 隔离后端未配置可用的实时 Nominatim/Overpass 来源；本轮没有向外部地理服务伪造或补种地点 |
| AI / AgentRun | 未验证、未执行 | 隔离运行时显示 AI 未启用；没有模型请求，也没有 AgentRun 成功声明 |
| 真人手机、Android 软键盘、读屏器和完整对比度验收 | 未验证 | Chromium 视口与触摸模拟不能替代真实手机和读屏验收 |
| GitHub CI | run `38868901954`（代码提交 `29cebe264a910cb7157b7b6036b03bc9cf2f3290`）通过：TypeScript、Vite build、Chromium UI smoke | 仍是受控 `TEST_PROVIDER` 夹具；不包含 live API 或 Agent 验收 |

前端安装时，`npm ci` 因仓库 lockfile 缺少 `@types/react@19.3.0`、`@types/react-dom@19.3.0`、`csstype@3.2.3` 而报 `EUSAGE`。为继续验证，使用了 `npm install --no-save --package-lock=false`；没有改 `package.json` 或 `package-lock.json`。

## 手机截图

真实本地隔离服务下的页面截图：

| Welcome 390×844 | Explore 390×844 |
|---|---|
| ![Welcome 390x844](assets/welcome-390x844.png) | ![Explore 390x844](assets/explore-390x844.png) |

| Explore 430×932 | Explore 1440×900 |
|---|---|
| ![Explore 430x932](assets/explore-430x932.png) | ![Explore 1440x900](assets/explore-1440x900.png) |

| 无可靠地名的恢复状态 390×844 | 行程页 390×844 |
|---|---|
| ![No reliable location fallback 390x844](assets/error-recovery-390x844.png) | ![Trips 390x844](assets/trips-390x844.png) |

| 我的 390×844 | 地点卡片 390×844（TEST_PROVIDER，不是实景地点） |
|---|---|
| ![Me 390x844](assets/me-390x844.png) | ![TEST_PROVIDER card 390x844](assets/place-card-TEST-PROVIDER-390x844.png) |

## 仍需完成的门槛

1. 在经过授权且可用的实时地名 / POI 来源下，由用户明确点击完成一次真实地点发现；保存后通过同一签名浏览器执行 GO 并刷新恢复。
2. 在合法配置 AI 并经用户确认一次请求后，验证真实模型建议的展示边界；本报告不把“AI 已配置”或只读建议说成 AgentRun。
3. 在真实 Android 手机检查软键盘、底部导航遮挡、地图拖动与缩放，并做真人读屏与颜色对比复核。
4. 处理现有前端 lockfile 安装不一致，并评估代码分包以降低目前的 bundle 体积警告。
5. M1 目前只拆出了 AI 输入和地点卡片；网络请求、身份与探索状态仍集中在 `RevolutionQuickExplore.tsx`，controller/hooks 层拆分尚未完成。

PR #23 保持 draft，待实时地点来源、完整签名用户闭环和实机验收完成后再决定是否可供正式合并。
