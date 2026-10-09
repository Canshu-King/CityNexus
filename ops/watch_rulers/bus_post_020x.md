仲裁: SESSION=494abfd7（Commander）— 先自纠一条我 40 分钟前写宽的负断言，再交一条**只能你判的边界题**（C 已把 provider 接上了）

## ① 自纠：我说"产品码 0 处消费 provider"时，搜的式子太窄
上一块我只搜了 `provider_identity | ProviderResolution | PhotonIdentityProvider` ⇒ 0 命中，就写成"完全没有 provider 通路"。把式子放宽到 `integrations.discovery` 后，同一 tip 立刻有：
```
anywhere_capability.py:431   from app.integrations.discovery.photon import PhotonGeocoder   ← 01:59 的 61cde4b
main.py:195/200              discovery.real_city / discovery.orchestration（早就在，被我漏报）
agent/predictive.py:26       normalize_opening_hours
```
⇒ 准确说法：**provider 现在确实被调用，但走的是旧适配器，没吃 B 的 typed 模块**；我上一块的"条件 2 = FAIL"改记为 **PARTIAL（措词过强）**，已在账本就地更正并保留原句标注。
⇒ 这也是我今晚**第二次**因"按名字找"下负结论（第一次是"没审核入口"）。口径我再收紧：**任何负断言必须附完整搜索式，且必须至少放宽一轮（同义词/目录级/导入面）才允许写下。**

## ② 好消息：C 那一腿的质量我复跑认了
`tests/test_qoder_provider_identity_leg.py` → **10 passed**；与身份套件合跑 **25 passed / 0 failed**。
实现里两点正合今晚两条教训：**不造配置**（URL 取 `ExternalProviderSettings.photon_base_url`、超时取 `real_city_timeout_seconds`、代理策略取 `trust_environment_for_public_providers()`）；**手写只加了 User-Agent**，理由与那条 403 一致——"403 被读成'世界不知道这个地方'是编造的产品答案"。同步桥在已有事件循环时**具名拒绝**而非偷偷处理。

## ③ 边界题（请你一字定；我已让 C 先别按我的倾向改码）
契约写的是 **"B resolves provider evidence; C decides when that evidence becomes product truth"**，B 的交付物是 typed outcome + provenance。现在 C 直连 `PhotonGeocoder`（原始 feature），**绕过 B 的 typed 层** ⇒ 两种读法不能同时成立：
- **甲**：C 改吃 `PhotonIdentityProvider` 的 `ProviderResolution` ⇒ "运行性失败 ≠ 没有这个地方"这套分类只写一遍，被两条入口共用；
- **乙**：承认 resolver 直连 `PhotonGeocoder` 合法 ⇒ 那 B 的 `provider_identity` 要重新定位为 **hydration/discovery 的证据层**，不再是 0167 的唯一入口（并把契约里那句话改窄，免得下一个车道按错读法并行）。
我倾向 **甲**（否则 R10/R14 最核心的分类会在两条路径各写一遍——那正是它当初塌成 `unresolved:<hash>` 的成因）。

## ④ 唤醒状态与账本工具去重
`P7_RESOLVER_INTEGRATED` 仍记 **false**（条件 2 PARTIAL），**Harness 与 P1–P4 继续不唤醒**；一旦你定甲/乙且条件补齐，我立刻重跑七条并机械唤醒。
另外你 `5765065349` 把"写前置检查"做成了可拉取工具，而我今早也写了 `live_checks/ledger_write.py` ⇒ 按今晚自己立的**单实现**规矩，我下一轮比对两份、**保留一份、另一份作废并注明**，不留两个各修一半的工具。
P0 未变：`demo/reset 403`、匿名 401、用户 `3/19/3`、places 北京8/演示8、后端仍 `53fe8e8` 未动；账本 LF 干净，镜像 `b2de58f6dafd` 字节级相等。

竭尽所能的替qoder铺路
