# Revolution Lab 真正的首次试用（2026-10-14）

## 为什么刚才看到的不是想象中的 Revolution？

之前的启动器故意打开了 `/v8/hub`，它由已有 Qoder/V8 风格产品向导接管。
用户输入“连城”后，那个向导询问的是服务器内置 destination/canonical catalog 的身份，而非 Revolution 后期新建的“用户选择公开城市中心 -> 外部 POI 发现”路径。它只认识有限地名，和普通人想找新城市的需求脱节。此前默认的 `TEST_PROVIDER` 也只提供上海虚构样本，不能冒充真实地理探索。这个错误是试玩交付设计的问题，不是用户输错了地名。

当前独立试玩分支只增加新入口和启动配置，不更改 Revolution/R108 领域授权机制，也不合并 Qoder 主线。

## 本次更改

- **直接从 `http://127.0.0.1:14173/revolution` 进入 Revolution Lab 体验入口**。
- 不经过 V8 的“支持城市”判断。输入任意你想探索的中文/英文地区名（比如连城）创建服务器真实的带签名 DRAFT Journey；自定义名称是用户意图，随机 draft city_code 不是宣称地理身份真实已解析。
- 创建后挂载原生 `BootstrapDiscoveryPanel`：独立的公开地区搜索、人工中心确认、用户授权的 OSM/Overpass 查询、R107 的私人 Pocket Walk 和 R108 GO MODE（含暂停、恢复、自我报告及刷新后恢复）。
- 之前的 V8 大壳仍然存在于 `/v8/hub`，可以比较；这个新门口并不意味着 Revolution 已经完成整套全新 UI。后续探索细节页面仍含英文和开发者术语，需要 Codex 后续改善。
- 默认使用真实公开地图查询。**只有用户明确传 `--sample` 才会启用本地虚构服务**。
- 真实查询严格遵守 provider/user consent：本地启动时输入自己的联系人邮箱用于 Nominatim 官方服务 User-Agent；不会保存进仓库或日志，但发送给外部地图服务。没有有效联系人邮箱时不启用真实公开地点查询。
- AI/Hermes/DeepSeek 没有自动开启；交易与支付仍然 mock。**不能把真实 POI 搜索误称为自主 Agent 的完整演示**。

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
2. 在“Discover your first public place”面板里选择 `Choose public area on map`，在独立授权复选框里同意请求一次 Nominatim 查询。可以搜索 `连城县 福建 龙岩` 或 `Liancheng County, Longyan, Fujian, China`。城市搜索只会给地图一个公开定位候选，不能代表这个地方已经完成 CityNexus 的官方城市身份归档。
3. 选返回的城市候选后，在公开地图上选择明确地区或者贴 **https://www.openstreetmap.org/#map=12/<纬度>/<经度>** 形态的公开地图位置链接。坐标来源由你亲自确认，不能当作 GPS 或家庭地址。正常网页提供选点、手动坐标与 OSM 链接选项。
4. 选 `Art and history`、`Quiet green walk`、`Coffee and a short stroll` 等类别，确认 Overpass 数据服务的第二次独立授权，再查询公开地点。
5. 如果 LIVE_PROVIDER 返回了两个以上真实公开地点，可选第一站和第二站，建立成员私有 Pocket Walk，进入 GO MODE；导航到外部地图前再次单独确认。路线开始不代表你已经走过，完成进度是你自己点击报告。
6. 重开网页应在当前浏览器签名会话有效期间恢复私人 Pocket Walk/GO。如果真正外部服务超时、没有地点、或服务临时不可用，应看到来源和失败状态；不能把样本伪装成 LIVE 让它变绿。

### 对真实 AI 的诚实预期

此版本默认禁用外部 AI，专门验证“真实用户 -> 真实公开地图 -> 私人两站探索/GO”。旧主产品有 Live Recovery / Journey Operator 的 UI，但它们依赖另一条正式 ACTIVE Journey 和代理服务配置。**仍需要 Codex 的真实 API 配置、端到端接入和本机验收，才能声称可供普通用户连续体验自主 Agent。** 这不是已完成的部分。

## Android 手机

PC 的启动器要一直运行；Android USB 调试并安装 ADB 后：

```powershell
adb reverse tcp:14173 tcp:14173
```

手机 Chrome 访问 `http://localhost:14173/revolution`，仍使用 PC 的同一独立 API 和真实公网地图服务。真实 provider 是否可达取决于你电脑的网络。iPhone 需要独立可信的 HTTPS origin。

## 诊断与安全

- `http://127.0.0.1:14173/api/v1/health` 应返回 200。
- 新入口 URL 是 `/revolution` 而**不是** `/v8/hub`。
- 如果只有旧页面，确认代码已更新、启动脚本输出的新地址正确、浏览器缓存/SW 已清除（推荐隐身窗口）。
- 日志在 `trial/.runtime/backend.err.log` 和 `frontend.err.log`。
- 外部地图地理标签、开放时间、价格、交通 ETA 不具有无法证明的硬保证；未知必须显示未知。
- 保持 localhost 服务，不要直接开放数据库、backend 端口、fixture 端口到公网。
- 当前变更只经过 GitHub 源码核验，没有在你的 Windows 设备上运行或者在你的手机上确认过完整互动；首次体验中遇到的错误要按实际错误修复，不造假的“全部通过”。

## 完成标准

不是“通过几百个 verifier”。是你本人打开 `/revolution`，无需理解 canonical ID 或配置数据库，输入连城，主动授权真实地理位置搜索，在城市里找到两个 sourceful 地点，保存个人 Pocket Walk，打开 GO 模式，并体验刷新恢复。若外部 provider 真的不可用，必须明确报告失败，而非替换成假成功。
