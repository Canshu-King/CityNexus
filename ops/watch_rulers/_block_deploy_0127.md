## commander 亲测 @2026-09-23T01:27+08 —— **前端新代次已按 `DEPLOY_BUNDLE_RETENTION` 上线（A–E 全绿），手机现在能看到 ORD-0216④/0220①②③/0222/0126 那批修复**；另附一次我自己的凭据卫生事故与轮换

### ① 解锁条件由 D 报、我复核后才动手

D（`e345b9d6`）报「`git status --short -- frontend` 空、ORD-0126 补项已提交 `9544628`」。**我自己重核**：live tree tip = `0748a1f`（01:15），`git status --porcelain -- frontend/` **空**；整棵树仍有别人的在制品（`backend/app/anywhere_capability.py`、`backend/app/catalog_hydration_operations.py`、`tools/verification/mutation_campaign.py`、`reports/e2e-provenance/authoritative.json`），但 `vite build` 只读 `frontend/`。
**并用一条读数纠了 D 一句**：D 的 `frontend/dist` 是 **01:05** 产的，而最后一次动 `frontend/` 的提交是 **`9544628`（01:09）** ⇒ 那份产物**落后于源码**，必须重建，不能直接搬。

### ② 构建（绑定到 `0748a1f`）

```text
命令  npm run build   （cwd = _qoder_integration_20260919/frontend）
结果  ✓ built in 6.52s ; PWA mode=generateSW precache 9 entries (2423.21 KiB)
产物  index-DtQ86lsQ.js  1,231,985 B      index-cWMF3pBW.css  183,233 B
      maplibre-gl-CLqlEDxz.js 1,053,381 B  JourneyMap-Ca-Dd9f7.js 4,392 B
```
**一条顺带的相干性读数**：新产物与 01:05 那份**同哈希**（`index-DtQ86lsQ.js`、`index-cWMF3pBW.css` 逐字节同名同大小）——因为 01:05 那次构建是在 `failureAttribution.ts` **未提交**的状态下做的，01:09 才提交。**产物哈希跨越「脏→已提交」不变** ⇒ 既证明我这次重建确实绑在 `0748a1f`，也证明 D 那笔改动确实已经在这份产物里。

### ③ 上线（我新写了工具 `live_checks/deploy_bundle.py`，把保留规则变成可复算的门）

顺序**先 union、再证明、后切 index**，任何一步不合规就非零退出、不切：

```text
union     新增 3 个内容哈希资产（index-DtQ86lsQ.js / JourneyMap-Ca-Dd9f7.js / maplibre-gl-CLqlEDxz.js）
          index-cWMF3pBW.css 已逐字节相同 ⇒ 不重写；serve/assets 现有 11 个文件
gate      切换前逐个 GET 新资产：200 + content-type 正确 + 首字节不是 HTML + body sha256 == 磁盘 sha256
          2/2 OK（点名：E 的判据是「不是 200 就完事」，我这把门连首字节和 body 摘要一起比）
backup    dist_bak_0125 ← index.html / manifest.webmanifest / sw.js / v10-sw.js / workbox-6923124b.js
switch    装上同名 5 个根文件
```

**A–E 收据（全绿，全部用读到的字段算，不带字面量）**：

| | 对象 | 读数 | 判 |
|---|---|---|---|
| A | 上一代 `index-BCF4ptyk.js` | 200 / `text/javascript` / 首字节 `const __vite__mapDep` / 1,230,082 B | GREEN（旧代次**没被删**，手机仍可回退） |
| B | `/` 的 index.html | 200 且引用换成 `/assets/index-DtQ86lsQ.js`（旧名不再出现） | GREEN |
| C | 新入口 | 200 / `text/javascript` / 1,231,985 B / 首字节非 HTML / sha256 `cf3a08108ffba413` | GREEN |
| D | `/sw.js` 7,178 B 与 `/v10-sw.js` 2,096 B | 均 200、`text/javascript`、**与磁盘 sha256 相等**（`matches_disk=true`） | GREEN |
| E | 口径 | 「200 本身从不是充分条件：一个 .js 路径返回 200 却带着 HTML = `DEPLOYMENT_RED / STALE_CLIENT_BREAKAGE_RISK`」；每条都留了首字节与 content-type | 照录 |

收据文件：`live_checks/receipts/deploy_0748a1f_0923_012520.json`。

**端到端（走真隧道，不是我本机端口）**：匿名 `/` **401**；带新凭据 `/` **200 text/html 1,200 B**（sha256 `8c6405e97932642d`，与本地逐字相同）；新入口 200 `text/javascript` 1,231,985 B；**旧代次 `index-BCF4ptyk.js` 仍 200**（A 在隧道上也成立）。
**保留动作的另一半我没做**：`DEPLOY_BUNDLE_RETENTION` 只要求「先并后切」，**清理旧代次是另一次动作**，需要时再具名单删。

⇒ **用户那句话现在成立**：手机上刷新后能看到 ORD-0216④ / ORD-0220 ①②③ / ORD-0222 / ORD-0126 这批修复；在此之前手机跑的一直是 `56d20ec` 那一代。

### ④ 我自己的凭据卫生事故（照实记，不粉饰）

我在读 `run/preview_auth.txt` 时有**一次把预览口令打进了自己的工具输出**——我用了 `sed -E 's/=(.*)/=<hidden>/'` 这个掩码，可那个文件是 **TAB 分隔（`cnx<TAB>secret`）**、不是 `key=value`，于是掩码没命中，值原样进了终端。
处置（当场做完，不推迟）：**轮换该口令**。
```text
旧值 sha256[:10] a80e15ce1e  →  新值 sha256[:10] ac97887747   （两边都不落账本、不进总线）
新值只写在 run/preview_auth.txt（该文件按设计就是凭据落地点，从不进 Issue #1）
代理重启：PID 55564 → 20364（:4782 在听）
验证：本地与隧道各三条 —— 匿名 401 / 错口令 401 / 新口令 200
```
**旧值的退役依据要说清**：代理每次启动只读该文件比对，文件已换 ⇒ 旧值不可再认证；我**没有**再把它发一遍去「证明」它被拒（那等于二次泄露），这条按结构性论证记，不按实测记。
**代价与提醒**：**用户在手机/浏览器里存过的旧口令已失效，需要从 `run/preview_auth.txt` 重新读一次。**

### ⑤ 现场

链三条端口在听（`:4781` 56212 / `:4782` 20364 / `:8693` 55960）；`P7=false`；reference tip `c0d7e3d`；P0 未动（用户库 3/3/19/1/1）；那把 key 仍未轮换。
