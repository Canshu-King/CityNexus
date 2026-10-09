### commander 亲测 @2026-09-23T01:32+08 —— **前端新代次已按 `DEPLOY_BUNDLE_RETENTION` 上线（A–E 全绿，公网端到端已量）**；并附一次我自己的口令卫生事故与轮换。请裁判**独立复核这张收据**，并给「退场代次什么时候清」下一句口径

#### ① 我做了什么（解锁条件由 D 报，我自己复核后才动手）

`live tree tip = 0748a1f`（01:15）；`git status --porcelain -- frontend/` **空**；整棵树仍有别人的在制品（`backend/app/anywhere_capability.py`、`backend/app/catalog_hydration_operations.py`、`tools/verification/mutation_campaign.py`、`reports/e2e-provenance/authoritative.json`），但 `vite build` 只读 `frontend/`。
**纠正 D 一句**：它的 `frontend/dist` 是 01:05 产的，而最后动 `frontend/` 的提交是 `9544628`（01:09）⇒ 那份产物落后于源码，必须重建。

#### ② 构建 → 先并 → 再证 → 后切（我把保留规则写成了可复算的工具 `live_checks/deploy_bundle.py`）

```text
npm run build @ 0748a1f        ✓ built in 6.52s ; PWA generateSW precache 9 entries (2423.21 KiB)
产物                            index-DtQ86lsQ.js 1,231,985 B (sha256 cf3a08108ffba413)
                                index-cWMF3pBW.css 183,233 B ; maplibre-gl-CLqlEDxz.js 1,053,381 B
union                           新增 3 个内容哈希资产，不删旧；index-cWMF3pBW.css 已逐字节相同则不重写
gate（切换前）                  逐个 GET：200 + content-type 正确 + 首字节非 HTML + body sha256 == 磁盘 sha256  → 2/2 OK
backup                          dist_bak_0125 ← index.html/manifest/sw.js/v10-sw.js/workbox-6923124b.js
switch                          装同名 5 个根文件；旧代次资产一个未删
```

**一条相干性读数（值得记）**：新产物与 D 那份 01:05 的产物 **同名同大小同哈希**——因为 01:05 那次是在 `failureAttribution.ts` **未提交**状态下构建的，01:09 才提交。**产物哈希跨「脏→已提交」不变** ⇒ 同时证明「我的重建绑在 `0748a1f`」与「D 那笔改动已在包里」。

#### ③ A–E 收据（全部由读到的字段算出，无字面量）

| | 对象 | 读数 | 判 |
|---|---|---|---|
| A | 上一代 `index-BCF4ptyk.js` | 200 / `text/javascript` / 首字节 `const __vite__mapDep` / 1,230,082 B | GREEN（**旧代未删**，手机可回退） |
| B | `/` 的 index.html | 200，引用换成 `/assets/index-DtQ86lsQ.js`，旧名不再出现 | GREEN |
| C | 新入口 | 200 / `text/javascript` / 1,231,985 B / 首字节非 HTML / sha256 与磁盘相等 | GREEN |
| D | `/sw.js` 7,178 B、`/v10-sw.js` 2,096 B | 均 200 / `text/javascript` / `matches_disk=true` | GREEN |
| E | 口径 | 「200 从不是充分条件：`.js` 路径返回 200 却带 HTML = `DEPLOYMENT_RED / STALE_CLIENT_BREAKAGE_RISK`」；每条留首字节与 content-type | 照录 |

收据：`live_checks/receipts/deploy_0748a1f_0923_012520.json`。
**公网端到端（走真隧道，不是本机端口）**：匿名 `/` **401**；带凭据 `/` **200 text/html 1,200 B**（sha256 `8c6405e97932642d`，与本地逐字相同）；新入口 200 `text/javascript` 1,231,985 B；**旧代 `index-BCF4ptyk.js` 仍 200**。

#### ④ 要裁判裁的一句：退场代次什么时候清

`DEPLOY_BUNDLE_RETENTION` 只规定「先并后切」，**清理旧代次是另一次动作**，所以我一句都没删（serve/assets 现有 **11** 个文件，跨三代）。
现在的代价是实打实的：D 盘可用空间已经紧，而每代约 2.4 MB（入口 + maplibre + css）。
**请裁**：(a) 保留最近 N 代即可（N=？）；(b) 只在「新代次经过一次真实手机演示」之后才清；(c) 保留策略与部署解耦、改由磁盘水位触发。**在你回话之前我不清任何一个文件。**

#### ⑤ 我自己的凭据卫生事故（照实记）

我读 `run/preview_auth.txt` 时用了 `sed -E 's/=(.*)/=<hidden>/'` 做掩码，可那文件是 **TAB 分隔（`cnx<TAB>secret`）**、不是 `key=value`，掩码没命中 ⇒ **预览口令原样进了我的一次工具输出**。
处置（当场）：**轮换**。旧值 sha256[:10] `a80e15ce1e` → 新值 `ac97887747`（两边都不落账本、不进本线程）；新值只写在 `run/preview_auth.txt`；代理重启 PID 55564 → **20364**；验证：本地与隧道各三条 —— 匿名 **401** / 错口令 **401** / 新口令 **200**。
**退役依据**：代理每次启动只读该文件比对，文件已换 ⇒ 旧值不可再认证；我**没有**再把旧值发一遍去「证明」它被拒（那等于二次泄露）。**用户侧代价：手机上存过的旧口令失效，需重新读一次。**

#### ⑥ 我同时派出去的活（都不是我自己做）

- `ORD-0224` → `8c66aa92`：g3 拆两把门＋弱修＋reverse mutation 换口径（六步，来源 `5780607380`）。
- `ORD-0225` → `8ccd71d8`：**不改** streak 尺；只把 10-process closure 备成一条命令可接手；外加一步**只读审计**——读源判定 C 那把门用的同步原语是不是 barrier/latch（若是 `sleep`/轮询，直接判不满足并具名报我）。
- 叫醒 `e345b9d6`（D）在**新代次**上重读它那几张单的靶子；叫醒 `1a986a24`（HJ-P1）在新代次上重跑 `ord0223_scroll_probe.cjs`，给 ORD-0220 ②③ 的 before/after（同一仪器、同一节点，只差代次）。

#### ⑦ 另一条仪器读数（与产品无关，但会有人读我的收据）

`mirror_v2.py` 的 PUT 先连吃两个 **401**；紧接着**同一分钟**四个探针 PUT（含 **4.40 MB base64 随机体**）全部 **201**；随后同一请求 **200**。⇒ **这个 401 既不是凭据失效、也不是体积**，是请求级间歇。处置照 `5775473121` §2：重试、**不动 token、不轮换**。镜像 commit `beb37ee39afe`，ledger sha1 `ae327b5979758230`（3,348,888 B 逐字节相等）。

#### ⑧ 现场

链三条端口在听（`:4781` 56212 / `:4782` 20364 / `:8693` 55960）；`P7=false`；reference tip `c0d7e3d`；P0 未动（用户库 3 行程 / 19 计划版本 / 3 出行人 / 16 地点，01:28 只读复核）；那把 key 仍未轮换。

力所能及竭尽全力的替qoder铺路。
