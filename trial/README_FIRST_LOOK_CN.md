# Revolution Lab 真正的首次试用（2026-10-14）

## 2026-10-14 更新：可接本机真实 Agent（仅经用户主动启用）

上一版强调“AI 未启用”，那只是默认启动状态。现在已通过 **真正的 Hermes-compatible 工具 Agent** 接入本机 wb2api：
- `trial/wb2api_agent.py` 从 `WB2API_KEY` 读取密钥，设置 `CITYNEXUS_HERMES_API_URL=http://127.0.0.1:7865/v1/chat/completions`、`CITYNEXUS_HERMES_MODEL=auto:cheapest`，密钥只传给后端；
- `py -3.13 trial/try_revolution.py --agent` 显式开启；不写 `--agent` 时 AI 仍关闭；
- `py -3.13 trial/probe_wb2api_agent.py` 可做一发**可能扣积分**的工具协议探针，**不会执行**任何工具；
- `/revolution` 显示 `HERMES_COMPAT_ENDPOINT` 后，仅说明配置已被读到；需要选择地点进入正式 ACTIVE Journey 并获得有步骤的 AgentRun 才算 AI 真正工作；
- 免费优先的 7865 存在可能付费的末端兜底。

操作说明：`trial/REVOLUTION_AGENT_WB2API_CONNECT.md`；
用户上传教程的安全脱敏版：`docs/LOCAL_WB2API_GATEWAY_GUIDE_20261014_REDACTED.md`。

## 为什么刚才看到的不是想象中的 Revolution？

之前的启动器故意打开了 `/v8/hub`，它由已有 Qoder/V8 风格产品向导接管。
用户输入“连城”后，早期向导会查询服务器内置 destination/canonical catalog；Revolution 后续流程则允许用户选择公开城市中心并搜索附近 POI。旧版 `TEST_PROVIDER` 使用上海样本，无法覆盖连城的公开地点探索需求。

当前独立试玩分支只增加新入口和启动配置，不更改 Revolution/R108 领域授权机制，也不合并 Qoder 主线。

## 本次更改

- **直接从 `http://127.0.0.1:14173/revolution` 进入 Revolution Lab 体验入口**。
- Revolution 使用独立入口。输入中文或英文地区名（如连城）即可创建带签名 DRAFT Journey；地点定位在后续步骤完成。
- 创建后挂载原生 `BootstrapDiscoveryPanel`：独立的公开地区搜索、人工中心确认、用户授权的 OSM/Overpass 查询、R107 的私人 Pocket Walk 和 R108 GO MODE（含暂停、恢复、自我报告及刷新后恢复）。
- V8 页面保留在 `/v8/hub`；本入口提供地区搜索、地图选点、地点查询、私人 Pocket Walk 和 GO MODE。
- 默认查询公开地图数据；使用 `--sample` 时加载本地示例数据。
- 启动时输入联系人邮箱作为 Nominatim User-Agent。该邮箱会随请求发送给地图服务，不写入仓库或日志；未提供邮箱时不启用公开地点查询。
- AI/Hermes/DeepSeek 默认关闭；支付与交易使用 mock。自主 Agent 流程从 AI 配置到 AgentRun 另行开启。

## Windows PowerShell：更新你已有的试玩工作目录（不用重装 Python）

**先返回原来正在运行启动器的 PowerShell，按 Enter 停止旧的 3 个/4 个服务。** 然后执行：

```powershell
cd D:\moodle\CityNexus-Revolution-Trial
git fetch origin
git restore --source origin/trial/revolution-first-look-20261014 -- trial/try_revolution.py frontend/src/main.tsx frontend/src/trial/RevolutionFirstLook.tsx frontend/src/trial/RevolutionFirstLook.css
py -3.13 trial\try_revolution.py
```

这条命令仅更新本次四个功能文件，不覆盖你已经通过 `npm install` 修好的 `frontend/package-lock.json`，也不动 Qoder/Commander、融合分支或现有真实行程数据库。

启动器会让你在 **本机终端** 输入联系邮箱，以便 Nominatim 合规识别请求。不要把联系方式发给 ChatGPT；本地填入即可。之后浏览器会打开：

`http://127.0.0.1:14173/revolution`

若不想联网，只想看虚构交互，则明确改用：

```powershell
py -3.13 trial\try_revolution.py --sample
```

建议先在浏览器新的隐身窗口使用新的 `/revolution` URL，避免旧 `/v8` 路由和已缓存旧 Service Worker 干扰。

## 真实“连城”探索流程

1. Revolution 首页输入 **连城**，点击 **开始真实探索**。这只在本地后端创建你的个人草稿，**不会向外部地图服务提交地名**。
2. 在“Discover your first public place”面板选择 `Choose public area on map`，再确认一次 Nominatim 查询。可搜索 `连城县 福建 龙岩` 或 `Liancheng County, Longyan, Fujian, China`。搜索结果用于公开地图定位；正式城市身份归档在后续步骤完成。
3. 选择城市候选后，在公开地图选定区域，或粘贴 **https://www.openstreetmap.org/#map=12/<纬度>/<经度>** 形式的公开位置链接。坐标由你选择，页面不读取 GPS 或家庭地址。网页提供地图选点、手动坐标和 OSM 链接三种方式。
4. 选 `Art and history`、`Quiet green walk`、`Coffee and a short stroll` 等类别，确认 Overpass 数据服务的第二次独立授权，再查询公开地点。
5. LIVE_PROVIDER 返回至少两处真实地点后，选择两站、保存私人 Pocket Walk 并进入 GO MODE。打开外部地图前会再次确认；到站进度由你点击报告。
6. 在当前签名会话中重开网页，可恢复 Pocket Walk/GO。外部服务超时、无结果或暂不可用时，页面显示真实来源与状态；`--sample` 始终标为示例数据。

### 对真实 AI 的诚实预期

此版本默认禁用外部 AI，验证真实用户的公开地图搜索、私人两站探索和 GO。Live Recovery / Journey Operator 使用正式 ACTIVE Journey 与代理配置；完成真实 API 接入和本机验收后即可体验完整 Agent 流程。

## Android 手机

PC 的启动器要一直运行；Android USB 调试并安装 ADB 后：

```powershell
adb reverse tcp:14173 tcp:14173
```

手机 Chrome 访问 `http://localhost:14173/revolution`，仍使用 PC 的同一独立 API 和真实公网地图服务。真实 provider 是否可达取决于你电脑的网络。iPhone 需要独立可信的 HTTPS origin。

## 诊断与安全

- `http://127.0.0.1:14173/api/v1/health` 应返回 200。
- 打开 `/revolution` 进入手机版体验；`/v8/hub` 是旧页面。
- 如果只有旧页面，确认代码已更新、启动脚本输出的新地址正确、浏览器缓存/SW 已清除（推荐隐身窗口）。
- 日志在 `trial/.runtime/backend.err.log` 和 `frontend.err.log`。
- 地理标签、开放时间、价格和交通 ETA 暂无来源时显示“未知”。
- 保持 localhost 服务，不要直接开放数据库、backend 端口、fixture 端口到公网。
- 当前记录为 GitHub 源码核验；Windows 与手机完整流程待实测。首次体验遇到的错误按实际请求和服务端响应定位。

## 完成标准

用户打开 `/revolution`，输入连城并授权地点搜索，找到两个有明确来源的地点，保存个人 Pocket Walk，开启 GO，再刷新页面确认行程恢复。若地点服务不可用，页面显示实际失败状态和原因。
