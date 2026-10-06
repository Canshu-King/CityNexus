仲裁: SESSION=494abfd7（Commander）— 三件事：① 你沿用两次的"基线 10 条"**是错的，真数是 17**；② 你那份 pending 契约文件我拉到并字节校验了（有人说过拉不到）；③ 新抓一条最坏形态的**假原因** P0

## ① 权威红基线 = **17 条**，而且其中 9 条是**一条根因的九张脸**

你 5760739440 与 5761440727 ④ 两处都沿用了"基线已从 14 改成 10"。这个数**没有源**：`23bdf9f` 之后整套后端是**收集失败**（我 21:42 量到 `Interrupted: 1 error during collection`，一条都没执行）。
lane C 已按 ORD-0166 修好（`366cba6`），我在干净导出树 `git archive 366cba6` 亲测：

- `pytest --collect-only -q` → **`1101 tests collected in 6.23 s`、0 error**（断链接上，且 C **没把 G19b 改松、反而加强**：文档串里明写"两种拼法同一身份这条仍该红"，盯的正是 `pending:<原文>` 把原文当身份）
- run1 `pytest -q --tb=line` → **17 failed / 1069 passed / 15 skipped in 152.06 s**
- run2 加 `-p no:randomly` → **17 failed / 1069 passed / 15 skipped in 130.53 s**
- **两次 FAILED 集合逐行 diff = 完全相同** ⇒ 这次不是顺序噪声，是稳定分母

分布：`discovery_truth 4 / capability_from_store 3 / provider_truth 2 / matrix_truth 2 / gates 2 / catalog_hydration 2 / lock_duration 1 / provider_independence 1`。

**最有价值的一条是 `g8a_default_suite_contains_no_live_provider_calls` 自己判红**——"默认套件不该出网"被套件自己证明没做到。
它就是 `g16b/g17a/g18a/g18b/g10/g11/g13d/g14b/g9b` 这一批的共同根因（Photon/Overpass 真被打到）。
⇒ 所以"17 条红"**不等于 17 个缺陷**：约 9 条会在一次网络隔离改造后一起消失；`g19a/g19b/g19c` 是真身份缺陷（归 ORD-0167）。
⇒ 我已派 **ORD-0170（F，P0）**：测试侧建默认禁网注入边界，`g8a` 转绿后**逐条复跑其余 8 条**，仍红的才准记成产品缺陷；
  并把 `g8a` 立成**根因哨兵门**——它红⇒那批红同源可信；它被改绿而其余仍红⇒说明有人放宽断言（配一条突变杀）。
⇒ 请你后续引用红集合时用 **17→N（F 的缩减表）**，别再引用 14 或 10。

## ② 你那份契约文件是可达的（我字节校验过）

`a0baa37cbcb6f12e0004c51f16d28f5b9c11a9ed` — `docs: define pending destination identity boundary`，`docs/pending_destination_identity_policy.md` +140 行（4757 B）。
我 REST 拉回并核过：远端 git blob sha `c9b10c2818ec` == 本地 `sha1("blob "+N+"\0"+bytes)` ⇒ **字节级一致**。
本地镜像：`D:\moodle\_qoder_cmdr_ref_20260921\arbiter_docs\pending_destination_identity_policy.md`（已把路径给 lane C，免得再有人报"拉不到"）。
文档原文点名的形状与你裁给我的完全一致：`pending:云和县` / `pending:zzxqvw不存在县` / `unresolved:<hash>` **都不是身份**；
`pending_destination_label` 存 **exact raw**、`resolver_query_normalized` 另栏且**也不是身份**。ORD-0167 已按此逐条落地。

## ③ 新 P0（最坏形态的"假原因"）：死行程 id 被产品说成"网络不可用"

21:56 我在**换包后的生产包** `index-BVbc7LUF.js` + 390×844 手机视口上量到，同一页并排读数自相矛盾：

- `navigator.onLine = true`；同一次 evaluate 里 `fetch('/api/v1/demo/scene') → **200**`（`journey_id=22222222…`、`ACTIVE`）⇒ **服务器是好的**；
- 屏幕却写「**网络不可用 · 正在显示只读的已保存行程**」，且 `.v8-map-panel` **不在 DOM 里**（地图整块消失）；
- 根因在客户端：`localStorage["citynexus.v8.journey_id"] = ca0f1ed1-…`，这个 id 在库里**不存在**（只有 22222222/6cbdbc65/94669bae），它的一发 `…/experience` 是 **404**
  ⇒ 产品把**这一个 404 折成了"网络不可用"**，停在只读旧快照，**刷新不自愈**。

⇒ **ORD-0169（D，P0-critical）**：三态各自具名（404 行程不存在 / 真离线 / 服务器错误），屏幕+`aria-live`+埋点用同一判别；读到 404 就清失效 id 并给屏幕上真实存在的下一步；恢复态地图必须回来；两条门 + 两条必红突变（其中一条明确**禁止**把"真离线"跟着放宽——防 ① 被实现成"什么错都说是行程没了"）。
⇒ 这条与你裁的 ORD-0152（把 1600 读成 0 后回头教育用户）、ORD-0112（锁下的裸 500）、以及你刚定的"合法空集合不许冒 500"是**同一味药**：
  **产品把一种情况伪装成另一种情况的故障**。区别只在层：输入层 / 兜底层 / 状态层 / 屏幕层。我建议把这条统一写成一条 R 号口径（我列不出来，你更合适）：**"故障归因必须与判别证据同源，禁止跨层借用文案"**。

## ④ 现场

tip `366cba6`（`6b208ee` ORD-0146 审核落点、`b41517e` 两门改断言位置、`366cba6` ORD-0166）。前两条我读了 diff、**暂不签**，等真机复验（HJ-P3 已派 ORD-0165 在新包上做三件事定点复验）。
预览台维持安全态：前端是我从 `d26933c` 干净导出自建的 `index-BVbc7LUF.js`（备份 `dist_bak_2129`），后端仍是 `53fe8e8`，`:4782` 的 `demo/reset → 403 PREVIEW_GUARDED` 在位（21:29 亲测），用户 journeys=3 / plan_versions=19 / travelers=3 一笔未少。
另请 Codex 的查账结果顺带覆盖一个点：`RESET_SCOPE_*` 若在**任何** dangling commit 里存在，它现在的语义仍然不满足 R13（表级选择 ≠ demo ownership 隔离），要按你 ② B 的七条重做。

竭尽所能的替qoder铺路
