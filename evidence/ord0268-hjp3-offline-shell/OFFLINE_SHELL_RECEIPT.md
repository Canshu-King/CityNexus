### 📡 aad2d1f2 (SESSION=aad2d1f2) P3 · **通道恢复** + ORD-0268 killer 第 (3) 件的独立复核读数（真浏览器、我自己的面） @2026-09-24T01:0x+08

**先回应你 23:4x 那行**：通道恢复（我这边一直在跑，只是你那侧发不进来）。你写的"改派不追回"我照认：**0268 现场那一格的读数归 HJ-P1 `1a986a24`，我不追认、不覆盖**；下面这枚按 00:5x 那条口径只算**后到的独立复核**。

**问题（你 23:2x §③ 原样）**：整站下线（**源站断，不是面断**）后 returning client 直访 `/v8/hub`，人拿到的是 SW 答的壳，还是 `chrome-error://`；顺带 CacheStorage 里有没有 `workbox-precache-v2-<origin>`、以及文档引用的资产名。

**被测代（先钉标记，不用 bundle 名）**：landed 尖 `1f44408…`；`v10-sw.js` = **2,055 B / sha256 `e63d7421eda340937df28bd0cae35624ab413607f9819e69b519b7d7ede69dbd`**（我对自己那份快照与**用户链 `_qoder_preview_20260920/dist`** 各跑一次 `sha256sum`，两处**逐位相同**；你给的 16 位前缀是它的头部）；资产名与上一代**相同** ⇒ 我按你的话只用 sw 摘要当代标，不用 bundle 名。我从 `_qoder_cmdr_deploy_1f44408_0923/repo/frontend/dist` 用 `cp -al` 钉成自己的快照再起面（**没动任何人的目录**）。机械先读：`grep -c v10-shell v10-sw.js` = **0**、`grep -o 'url:"/index.html"'` = **0**、precache 清单 8 条里 `index.html` 只有**一条**（`revision:"213aa276…"`，内容派生那枚）。

**两向对照（这是这格的全部）**
| | 条件 | 人拿到什么 |
|---|---|---|
| 正 | SW 已注册 + precache 8 条（含**一条** `/index.html?__WB_REVISION__=213aa276841d50a8a61cf75dd7408a7f`）；我把**我自己**那个 listener（pid 19428，命令行已读回证明是我起的 `vite preview --port 8488`）停掉，`netstat` 上 `:8488` = 0 listener ⇒ 源站真断 | 直访 `http://127.0.0.1:8488/v8/hub` → **产品壳渲染出来**：`title = CityNexus Trip Operations`、正文 168 字（「用你自己的城市试用 CITYNEXUS / 新建行程 / 三步完成。…」）、`script[src] = /assets/index-Cpy_jhEg.js`、`navigator.serviceWorker.controller = true`、**pageerror 0 条**、URL 仍是 `/v8/hub` |
| 反（对照） | 同一台死源站，先在我**自己的 origin** 上注销那 1 枚 SW + 删掉那 1 个 cache（`caches.keys()` 之后 = `[]`） | 同一入口 → `net::ERR_CONNECTION_REFUSED`，URL 变成 **`chrome-error://chromewebdata/`**，屏上是**Chrome 自己的**「无法访问此网站 / 127.0.0.1 拒绝了我们的连接请求。/ 检查网络连接 / 检查代理服务器和防火墙 / ERR_CONNECTION_REFUSED / 重新加载 / 详情」，`controller = false` |

⇒ **结论（可判）**：那一屏壳是 **SW 从 workbox precache 答的**，不是浏览器 HTTP 缓存答的（去掉 SW+缓存就立刻退回 Chrome 的错误页）。**0268 删掉重复 shell 条目这一刀，在真浏览器上是有效的**：precache 真的落地了（8 条），离线导航真的由壳答出来了。

**顺带接上 0263 那一族（只说一句，不并单）**：反面那一屏的文字是 **Chrome 的**，不是产品的——这正是"200+HTML 被读成『网络不可用』"那一族的上游表面：**缓存没落地的用户根本走不到产品那句归因，他看到的是浏览器的错误页**。所以 0268 落地之后，0263 第五态的现场复验才真的有意义。这条我只当背景陈述，不改任何单的射程。

**CacheStorage 与资产名（你点名要的两件，逐字）**：`workbox-precache-v2-http://127.0.0.1:8488/`（存在，1 个 key，8 条 entry）；文档引用 `/assets/index-Cpy_jhEg.js` + `/assets/index-I45CQek8.css` + `/favicon.svg` + `/manifest.webmanifest`。

**纪律与现场**：0 次 `demo/reset`、产品字节 0 改动、两个用户库/隧道/`:4781`/`:4782` 0 接触、凭据 0 打印；**关掉的页 0**（全程只在我自己的 tab 上操作，每次调用先按 URL 从 `context().pages()` 挑出自己的页）；`:8488` 是我为这一格起的、也是我停的 ⇒ 我的 listener 回到 `:8424 :8479 :8483 :8484 :8485 :8486 :8487 :8598 :8599`。

**我不主张的三件**：① 没留离线壳的截图（反面对照把那台 origin 的状态拆掉了，重建要多花一轮，我选择把两向读数逐字贴出来）；② 这是**我这台真浏览器 + 我自己的 origin**，不是用户手机、也不是隧道地址；③ 我没碰换代尺，`DEBT-4` 那格 RED 的判定不归我、我也不改。

**请你回我一行（不催，只是不想默默欠着）**：`ORD-0262-NARROW` 你已记 `ACCEPTED-MECHANICS`，而我 19:1x 那份"四问验收基线"（N1 具名码走 `error()` 信封 / N2 三处 `create_mission(` + 两处 flush 按分布判 / N3 读 `[data-testid="plan-ai-reason"].textContent` 且必须等于服务器 `message`、不许出现 `HTTP 500` / N4 有 mission 行时文案不得说"没记录"）**还没跑过**。要跑我就按这份基线跑；如果 `ACCEPTED-MECHANICS` 已经把这一格收掉了，请就地写明"四问由该判定吸收"，我就不再挂账。
