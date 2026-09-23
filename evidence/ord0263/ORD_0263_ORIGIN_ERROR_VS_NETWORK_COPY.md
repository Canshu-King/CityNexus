# ORD-0263 · `ORIGIN_ERROR_VS_NETWORK_UNREACHABLE_COPY` — 三态矩阵（HARNESS `d291c9dc`，只交 reproducer/verifier）

现场：我自己的 canary —— `:4411` vite preview 跑 ORD-0254 候选包（`/api → :8411`）、`:8411` 我自己的库（marker 行 `harness-ord0254-canary-8411`）。
**零产品码改动、零浏览器 mock**：我只开关自己的进程；`:4411/:4412/:8411` 之外没有请求过任何端口（`:4781/:4782/:8693/:4185/:8713` = 0 次）。
快照位置：IndexedDB `citynexus-offline` / store `journeys` / count 1（三态同一 profile，读的是渲染文字，不看 data 属性）。

## 三态实测

| 态 | 构造 | 源站回答 | 屏上实际文案（逐字片段） | 对照仲裁词表 |
|---|---|---|---|---|
| **S1 2xx** | 全好，点「使用封存的天津演示」进车 | `/api/v1/health → 200 application/json`；`onLine=true` | `下午好 Demo之旅 … 今天 还没有安排 “现在”取自服务器场景（行程起点，游标状态 ABSENT_FALLBACK）` | **LIVE 正确** |
| **S2 HTTP 5xx + 有快照** | 只停我自己的 API 进程 ⇒ 代理**答**了 | `500 text/plain`，`thrown=false`；`onLine=true` | `离线 · 只读 / 你未来 24 小时已保存。 / **网络不可用 · 正在显示只读的已保存行程。** / 重试`（说话的是一个无 testid 的 `<P>`；`load-failed* / backend-unreachable / journey-gone` 全 0 节点；门 `offline-retry` 在、可聚焦） | **文案错**：源站明明答了，却叫"网络不可用"；仲裁要的"服务暂时不可用 + 正在展示本地快照"**一个都没出现** |
| **S3 传输超时 + 有快照** | 把 `:8411` 换成我自己的**静默监听**（接受 TCP、永不回应；直连 6.0 s 后 `000`），壳照常供 | 页内 fetch 8 s 未 resolve；`onLine=true`；快照仍在 | `正在准备城市周末行程… / 锚点 · 住宿 · 出行事实 · 可行性`（`offline-retry / backend-unreachable / load-failed / today-heading` 全 0 ⇒ **没有门、没有解释**） | **状态不可达**：不是"说错"，是**根本没走到分类器**，旅客被无限挂在骨架屏上 |

## 两行代码，两个不同的病（读出来的，不是猜的）

1. **合并 S2/S3 的是** `frontend/src/app/V8Experience.tsx:193-204` 里的 `probeHealth()`，决定性一行是 **:198 `return response.ok;`** —— "答了但非 2xx"和"根本没答"都塌成同一个 `false`；`boot()` 在 **:607 `const up = await probeHealth()`** → **:609 `if (!up)`** → **:613-614 `setOffline(saved); setMessage(t("shell.offlineMsg"))`** 用同一句话覆盖两态（同一 key 的第二个发射点在 **:652**，词条在 `i18n/LocaleContext.tsx:693`）。
2. **S3 之所以连那句错话都读不到**：`boot()` 先 `await load(journeyId)`（**:601**），而数据通道 `frontend/src/api/citynexus.ts:642 async function requestJson<T>(...)` 在整个请求路径里**没有 AbortController、没有超时**（我对该文件 grep `AbortController|setTimeout|signal|timeout` 只命中 642 这一行函数签名本身）。于是静默源站下 promise 永不 settle ⇒ `:602` 的 catch 不执行 ⇒ `busy` 一直 true ⇒ 骨架屏常驻。

⇒ **只改文案修不好第三格。** 三态语义需要两件事同时成立：(a) 每次数据读有截止期限，让"挂着"变成一个可分类的事件；(b) 分类器区分"答了非 2xx"与"没答"。一行改不出来。这也解释了为什么 S2 有门、S3 连门都没有。

## 附带一格（越界之外，但旅客真会撞到）

把**整个源站**下线（`:4411` 也停）再访问 `/v8/hub`：读到的是**浏览器自己的错误页** —— `chrome-error://chromewebdata/`、`net::ERR_CONNECTION_REFUSED`、`无法访问此网站 / 127.0.0.1 拒绝了我们的连接请求`，该文档上 `sw_controller=false`。precache 里有 `/index.html`，但导航目标是 `/v8/hub` ⇒ **深链在离线时没有 SW 兜底**。这不属于 ORD-0263 的三态，具名留在这里：它意味着"离线文案写得再对"也可能根本读不到。

## verifier 配方（给产品写者，可直接跑）

1. 任一前端 + 正常源站，先用界面里的真控件进一趟车，让 `citynexus-offline/journeys ≥ 1`；
2. **S2**：只停 API 进程 → reload → 断言句子指名"服务"而不是"网络"；
3. **S3**：用 `tools/silent_api_port.py` 占住 API 端口（接受不回）→ reload → 断言"源站没回答"+ 展示快照，且**在有限时间内**结束等待；
4. **S1**：恢复源站 → 断言不出现任何离线措辞。

修好之前必须保持为红的三条断言：
- S2 正文含 `/网络不可用/`（今天为真 ⇒ 修后必须为假）；
- S3 正文含 `正在准备` 且 `{offline-retry, backend-unreachable, load-failed}` 计数为 0（今天为真 ⇒ 修后必须出现有界、被分类的回答）；
- S2 与 S3 文案不同源（今天它们**不**相同，因为 S3 到不了 `:198` ⇒ 只改字符串的方案会让 S3 继续错，这一条专门用来拦"改一处交差"）。

## 我没测 / 不能声明的

基线面（没有 53fe8e8 的 canary ⇒ 不宣称回归，与指挥官 15:2x 一致）；鉴权代理与公网链后的生产形态（禁止端口 0 次访问）；DNS 失败与"已加载后连接被拒"两个 S3 变体（我只造了超时那一种，但因为没有 per-read deadline，它们的结局同形）；AI/供应商路径（我这台 `CITYNEXUS_AI_ENABLED=false`）。

## 同一现场顺手做的 ORD-0254 收尾（换尺第五枚）

`live_checks/deploy_bundle.py` 分支尖 = **`e0b4f3c055b9027ae12469b18ad43e920d543bd0` / 86,897 B** 与你的坐标相符；我**不再进程内替换 `BASE`**，全部走 `CNX_DEPLOY_BASE / CNX_DEPLOY_PROXY_BASE / CNX_DEPLOY_TUNNEL_BASE / CNX_DEPLOY_SELFTEST_ROOT`（收据里 `declared_via_env: true`、`pairing` 合法、未设 `BASE_IS_CMDR_LIVE`）。
- **§红-1 `NOT_REPRODUCED_ON_e0b4f3c0`**：两枚 F base 都配上，`main()` 跑完不崩并写出收据 ⇒ 你的判断成立（那句早在 `ddcdd550` 已修，我当时用的是更旧的 `c0aafc94`）。**拒跑现在也会写收据**（`deploy_refused_preflight_0923_164153.json`），我上一轮"拒跑无产物"的口一并撤回。
- **真换代端到端一次过**：union（22 条 name→digest 绑定）→ phase-2b 全绿 → 切换 → `A/B/C/D/E + G[DECLARED, GREEN×8] + I(GREEN) + J(GREEN) + F(GREEN)`，**OVERALL GREEN，rc=0**（`ord0263_deploy_gauge_receipt.json` 63,922 B）。G_pre 已把我报的壳冲突处理成具名 `pending_root_docs=[/sw.js, /index.html, /manifest.webmanifest]` ⇒ **我 §10 那条 phase-2b 阻塞在这枚上不成立，撤回**；当时唯一剩下的红是我把 tunnel 角色挂在 `:4411`（它服务的是构建导出＝未来的壳）而 F_pre 判的磁盘是 `serve/` —— 我的拓扑错，指回部署目标根后即全绿。
- `--selftest` 在我面上 **42/48**（你 46 + 我导出 `SELFTEST_OLD_REF` 的 B2/B2-neg）。6 处不匹配里 4 处是**预设磁盘侧=指挥官 dist** 的臂（`BASE-restore:*`、`SIDES-*` 三条），第二车道结构上不可能满足；其余 2 处（`J-true_positive`、`F-true_positive:two_live_probes_agree`）是同一族：那些臂在 selftest 中途把 base 临时还原到 `:4781` 却仍与我自己的磁盘比字节 ⇒ **混侧**。建议（不代你决定）：这几臂要么绑定同一对 (base, disk)，要么在 `SELFTEST_ROOT` 非本链时打具名 `DECLARED_FOREIGN_DISK_ROOT`，别留 RED。
