### SESSION=494abfd7 · 先更正我自己：我上一块写的"产品码 0 处消费 provider"**搜窄了**；实测是 **provider 现在被调用了，但走的是旧适配器而不是 B 的 typed 模块** @02:0x

`STATUS: MY-NEGATIVE-CLAIM-CORRECTED-SAME-NIGHT | 树 `git archive 61cde4b` → `v_61cde4b`（只读+跑测试，未改权威树）| 我把两次搜索的**式子本身**贴出来，便于任何人复放 |`

#### ① 我错在哪（这次隔了 40 分钟就自己撞见）
我上一块用的式子只有三个符号：`provider_identity | ProviderResolution | PhotonIdentityProvider` ⇒ 0 命中，我就写成"产品码 0 处消费 provider"。
把式子放宽成 `integrations.discovery` 之后，同一个 tip 上立刻出现：
```
backend/app/anywhere_capability.py:431   from app.integrations.discovery.photon import PhotonGeocoder
backend/app/main.py:195/200              discovery.real_city / discovery.orchestration（早已存在，被我漏报）
backend/app/agent/predictive.py:26       normalize_opening_hours
```
⇒ **准确说法**：`61cde4b`（01:59，"a real provider may name a destination, when the deployment asks"）之后，
   **解析器确实会打真 provider**；但**它没走 B 的 `provider_identity` typed 模块**。
⇒ 而 `61cde4b` 之前我那句"完全没有 provider 通路"也只对 `provider_identity` 这一支成立 ⇒ 上一块的 `P7 条件2 = FAIL` 应改记为 **PARTIAL/措词过强**，我已在此就地更正（不改历史结论的样子，而是把错的那句标出来）。

#### ② 新代码我复跑了，质量是真的好（不是格式过关）
```
tests/test_qoder_provider_identity_leg.py            → **10 passed**（--tb=no）
+ tests/test_qoder_pending_destination_identity.py    → **25 passed / 0 failed**
```
读实现的两点值得记：
- **不造配置**：base URL 取 `ExternalProviderSettings.photon_base_url`、超时用 `real_city_timeout_seconds`、代理策略用 `trust_environment_for_public_providers()`；
- **手写只加了 User-Agent**，理由与我 01:3x 提的那条完全一致：**"一个 403 会被读成'世界不知道这个地方'，那是编造的产品答案"**；
- 同步桥 `_run_provider_coroutine` 在已有事件循环时**具名拒绝而不是偷偷处理**（不吞别人调度）。

#### ③ 由此产生一条**必须你（仲裁）或 B/C 认的边界问题**，我不擅自判
契约写的是 **"B resolves provider evidence; C decides when it becomes product truth"**，B 的交付物是 typed outcome（MATCH/AMBIGUOUS/NO_MATCH/RUNTIME_FAILURE + provenance）。
现在 C 直接消费 `PhotonGeocoder`（返回原始 feature），**绕过了 B 的 typed 层** ⇒ 两条路都有道理，但**不能同时成立**：
- **(甲)** C 必须改吃 `PhotonIdentityProvider` 的 `ProviderResolution` ⇒ B 的"运行性失败 ≠ 没有这个地方"分类才被真正复用；
- **(乙)** 承认"resolver 直连 PhotonGeocoder"是合法路径 ⇒ 那 B 的 `provider_identity` 就该重新定位为**给 hydration/discovery 用的证据层**，别再当 0167 的唯一入口。
⇒ 我倾向 **甲**（否则今晚 R10/R14 最核心的那条分类会在两条路径上各写一遍，正是一切塌缩成 `unresolved:hash` 的成因）。
⇒ **C 先不要按我的倾向改码**，等仲裁一字；我把 `P7_RESOLVER_INTEGRATED` 继续记为 **false（条件 2 PARTIAL）**，**真人组与 Harness 仍不唤醒**。

#### ④ 账本纪律：仲裁已把"写前置检查"做成可拉取工具（`5765065349`）
我这边今早也写了 `live_checks/ledger_write.py`（EOL 检查 + 邻域锚点 + 逆操作证明 + 他人已写则 ABORT）。
⇒ 按今晚自己立的**单实现**规矩：**两份工具必须合一**，我下一轮先比对它那份，保留一份、另一份作废并在账本注明，不留两个各修一半的实现。

status: 更正我"0 处消费 provider"的过强措词（provider 已接入但走旧适配器）；61cde4b 复跑 10/10 与合跑 25/25；提出 P7 条件2 的甲/乙边界问题待仲裁定；P7 仍 false，真人组/Harness 继续不唤醒；账本工具去重待办
