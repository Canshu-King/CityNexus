# Revolution Lab 试玩解锁：不要再让用户填写一整套同意表单

**日期：2026-10-15**。仅在 `trial/revolution-first-look-20261014` 施工，原 Qoder、Revolution 主工作线、融合分支未修改。

## 本次真正解决的问题

真实用户操作反馈：打开 Revolution 绿色页面以后，城市搜索、公开坐标、地图瓦片、城市标签、外部查询、兴趣选择、保存两站路线等功能堆在一整张表单上。必须来回勾选许多授权，却看不出进度，最后仍停留在“开始探索”。

旧的 `RevolutionGuide` 只是滚动到原始表单，不是新流程。现在默认由 `RevolutionQuickExplore` 完全替代该表单，原 `BootstrapDiscoveryPanel` 保留在明确的“专业设置（可选）”折叠区域，并且懒加载挂载。

## 新用户流程（真实原生 API）

1. 已经创建的签名 DRAFT Journey 自动进入“城市或地区”。一个主要按钮“查找位置”。只有用户点击时才一次性把所输入地名发送至 Nominatim，`provider_consent:true`。
2. 城市结果只是 **CAMERA_ONLY_TAP_REQUIRED** 的镜头定位，不会变成已证明的坐标。选择结果后用户显式点击“显示地图”，这次操作告知加载 OSM 地图瓦片。然后用户在地图上**亲自点一次**具体区域，立即进入下一步（省掉以前多余的二次确认）。也可以使用经过 `parsePublicMapLink` 严格校验的 OpenStreetMap 公共链接，不加载瓦片。**前景 GPS 永不启用**。
3. “你想逛什么？”只有四张兴趣选择卡。一个主要按钮“搜索附近地点”，旁边明示本次将发送公开坐标和类别给 Overpass；只有主动点击才调用 `bootstrapDiscovery`，保留服务端 `provider_consent:true`、固定半径与受限候选数。
4. 真正的 provider 返回候选后展示简单中文卡片，显示 `LIVE_PROVIDER` / `TEST_PROVIDER` 来源，选择两个**不同的当前候选**，通过原生 `saveBootstrapDiscoveryPocketWalk` 保存成员私有两站路线。没有两个真实返回的地点则不能伪造路线。保存按钮本身就是明确的私人保存确认，不再加毫无意义的重复勾选。
5. 进入原生 `transitionBootstrapPocketWalkGo`：开始/自报第一站完成/前往第二站/自报完成/暂停/恢复。通过 `getBootstrapShortlist` 按签名成员恢复现有私人 Pocket Walk，刷新后可以继续。
6. 出错不留在灰色不可点状态。服务不可用会展示中文原因，并提供“重新检查服务”，不会切到虚构地点，也不会无限重试外部模型。技术信息均折叠，AI 后端只显示“已配置”而非“已自主决策”。

## 真实边界

- 采用真实的签名 Journey API，保留读写鉴权、幂等、版本戳、TEST/LIVE 来源标签。
- 外部 Nominatim、OSM 瓦片和 Overpass 是三个不同的数据接收方，各自需要明确的用户动作；这里没有静默发送 GPS 或自动代点。
- 技术上通过“清楚的按钮文字 + 附近的披露说明 + 仅点击才发送”实现逐次主动同意，不再强迫用户同意复选框再点击同一个操作。
- 系统依然**不会**将地点发现或 Pocket Walk 虚构为真实 AgentRun；要证明 Hermes Agent 还需实际模型工具调用与签名 Journey Operator 记录。
- 没有两个 LIVE_PROVIDER 结果就不能报“真实地点路线已完成”；测试模式只能显示“TEST_PROVIDER”。营业、开放、成本、ETA 没有依据时均为未知。
- 城市查找依照后端定义只用于镜头定位，需用户实际点击地图或明确粘贴地图链接，不能以地理编码中心偷偷变成“用户现场位置”。
- 如果签名成员或 Journey 切换，未结束的 HTTP 响应有本地 epoch/bearer guard，私有路线不会跨用户显示。

## Windows 已有工作目录的**最小**升级操作

旧的 Vite 进程可以继续运行，`git restore` 后通常会自动热更新；不要重新安装 Python/npm、清理本地数据库或重新配置 WB2API。

```powershell
cd D:\moodle\CityNexus-Revolution-Trial
git fetch origin
git restore --source origin/trial/revolution-first-look-20261014 -- frontend/src/trial/RevolutionQuickExplore.tsx frontend/src/trial/RevolutionQuickExplore.css frontend/src/trial/RevolutionFirstLook.tsx
```

浏览器访问 `http://127.0.0.1:14173/revolution`，Ctrl+Shift+R 强制刷新。现在应该首先看到“想去哪儿逛逛？”和四个步骤，只显示**当前一步**。

如本地改过同名文件，先保存自己的改动，因为 `git restore --source` 会覆盖**列出的三个文件**。不会触及用户本地 lockfile、wb2api key、sqlite、原 Qoder 工作树。

## 工程验收状态（诚实）

这轮远程 GitHub 提交与源码静态检查已完成。**我没有运行用户 Windows 的 Vite、实际地理服务，也没有在此轮实际执行 `npm run typecheck:all`、Playwright 或真实手机操作。**

附有专门的 UI 单元式 Playwright 路由/网络 fixture `frontend/e2e/revolution-quick-explore-ui.spec.ts`，模拟 `TEST_PROVIDER` 只验证浏览器在用户按钮之前**不发外部 provider 请求**、页面阶段切换、保存和 GO 刷新恢复。**它是 UI fixture，不等于真实 provider 或 Agent 已通过。**

在已有 Node/npm 项目中执行：

```powershell
cd frontend
npm run typecheck:all
npm run build
```

如果编译报错，优先修当前真实 blocker，而不是开始新的 R110/ORD。最后以用户本人操作是否能进入下一步作为产品验收。
