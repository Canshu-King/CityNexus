# Revolution Lab 试玩解锁：不要再让用户填写一整套同意表单

**日期：2026-10-15**。仅在 `trial/revolution-first-look-20261014` 施工，原 Qoder、Revolution 主工作线、融合分支未修改。

## 本次真正解决的问题

真实用户操作反馈：打开 Revolution 绿色页面以后，城市搜索、公开坐标、地图瓦片、城市标签、外部查询、兴趣选择、保存两站路线等功能堆在一整张表单上。必须来回勾选许多授权，却看不出进度，最后仍停留在“开始探索”。

旧的 `RevolutionGuide` 只是滚动到原始表单，不是新流程。现在默认由 `RevolutionQuickExplore` 完全替代该表单，原 `BootstrapDiscoveryPanel` 保留在明确的“专业设置（可选）”折叠区域，并且懒加载挂载。

## 新用户流程（真实原生 API）

1. 已经创建的签名 DRAFT Journey 自动进入“城市或地区”。一个主要按钮“查找位置”。只有用户点击时才一次性把所输入地名发送至 Nominatim，`provider_consent:true`。
2. 城市候选用于地图定位。选中候选后点击“显示地图”加载 OSM 瓦片，再在地图上选择具体区域进入下一步；也可粘贴经 `parsePublicMapLink` 校验的 OpenStreetMap 公共链接。页面使用你选择的公开地图位置，不读取 GPS。
3. “你想逛什么？”只有四张兴趣选择卡。一个主要按钮“搜索附近地点”，旁边明示本次将发送公开坐标和类别给 Overpass；只有主动点击才调用 `bootstrapDiscovery`，保留服务端 `provider_consent:true`、固定半径与受限候选数。
4. Provider 返回候选后显示中文卡片和 `LIVE_PROVIDER` / `TEST_PROVIDER` 来源。选择两个不同候选，通过 `saveBootstrapDiscoveryPocketWalk` 保存成员私有两站路线；真实结果少于两处时，页面显示当前结果数。点击保存即确认私人保存。
5. 进入原生 `transitionBootstrapPocketWalkGo`：开始/自报第一站完成/前往第二站/自报完成/暂停/恢复。通过 `getBootstrapShortlist` 按签名成员恢复现有私人 Pocket Walk，刷新后可以继续。
6. 服务不可用时显示中文原因和“重新检查服务”。地点查询失败会保留当前步骤；技术信息折叠显示。AI 状态显示“已配置”。

## 真实边界

- 采用真实的签名 Journey API，保留读写鉴权、幂等、版本戳、TEST/LIVE 来源标签。
- Nominatim 接收地名，OSM 接收瓦片请求，Overpass 接收已确认的公开坐标和类别；每项都由对应按钮触发。
- 每个服务的用途和发送内容显示在操作按钮旁，用户点击后才发送请求。
- 地点发现与 Pocket Walk 显示为地点探索；真实 AgentRun 以模型工具调用和签名 Journey Operator 记录展示。
- 卡片标明 `LIVE_PROVIDER` 或 `TEST_PROVIDER`。营业、开放、价格、ETA 暂无依据时显示“未知”。
- 城市候选用于地图定位；最终区域由用户在地图点选或粘贴公开地图链接确定。
- 签名成员或 Journey 切换时，本地 epoch/bearer guard 会拦截旧请求对当前页面的更新。

## Windows 已有工作目录的**最小**升级操作

旧的 Vite 进程可以继续运行，`git restore` 后通常会自动热更新；不要重新安装 Python/npm、清理本地数据库或重新配置 WB2API。

```powershell
cd D:\moodle\CityNexus-Revolution-Trial
git fetch origin
git restore --source origin/trial/revolution-first-look-20261014 -- frontend/src/trial/RevolutionQuickExplore.tsx frontend/src/trial/RevolutionQuickExplore.css frontend/src/trial/RevolutionFirstLook.tsx
```

浏览器访问 `http://127.0.0.1:14173/revolution`，Ctrl+Shift+R 强制刷新。现在应该首先看到“想去哪儿逛逛？”和四个步骤，只显示**当前一步**。

如本地改过同名文件，先另存自己的版本；命令只恢复上面列出的三个文件。

## 当前验收

本轮已完成远程 GitHub 提交和源码静态检查。尚未在用户 Windows 上运行 Vite、真实地理服务、`npm run typecheck:all`、Playwright 或手机操作。

Playwright UI fixture `frontend/e2e/revolution-quick-explore-ui.spec.ts` 使用 `TEST_PROVIDER`，覆盖点击前的请求状态、页面阶段切换、保存和 GO 刷新恢复。真实 Provider 与 AgentRun 需分别完成现场验收。

在已有 Node/npm 项目中执行：

```powershell
cd frontend
npm run typecheck:all
npm run build
```

如果编译报错，优先修当前真实 blocker，而不是开始新的 R110/ORD。最后以用户本人操作是否能进入下一步作为产品验收。
