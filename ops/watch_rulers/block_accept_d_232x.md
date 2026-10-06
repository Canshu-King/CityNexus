### SESSION=494abfd7 · ORD-0126/0164 **签收（我在部署后的生产包上亲手复现正反两向）**；预览已换到 `index-BwIS1pck.js`；另开 ORD-0178 补"已保存"没有存储背书这个真相缺口 @本机钟 23:2x

`STATUS: ACCEPTED-BY-USING-IT | 构建：`git archive 82f136f` → `tree_next`（`npm run build` 成功，`✓ built`，precache 9 entries/2400.47 KiB）| 部署：`_qoder_preview_20260920/dist`，旧包备份 **`dist_bak_2314`** | 只读复核用户数据未变 |`

#### ① 我把 21:56 那个缺陷在**新包**上重放了一遍（同一个死 id、同一台 `:4782`、390×844）
| 读数 | 21:56（旧包 `index-BVbc7LUF.js`） | 23:15（新包 `index-BwIS1pck.js`） |
|---|---|---|
| 屏幕 | 「**网络不可用** · 正在显示只读的已保存行程」 | 「**连接正常** / 这台服务器上没有这一趟行程了」 |
| 具名原因 | 无 | `journey-gone-reason` = 「这台设备还记得行程 **ca0f1ed1…**，但服务器说它不存在。**你的账号和别的行程没有受影响。**」 |
| 失效 id | 留着，**刷新继续撞** | **已被清除**（`localStorage` 该键 = `null`） |
| 出口 | 无 | 屏幕上真有 **「选一趟行程」** 按钮 |
| 另一个测试 id | — | `load-failed-reason` **不存在** ⇒ 两种状态确实分开 |
⇒ **R14-S/P 在我手里第一次有正反两向的实测**：404 不再冒充离线，且 `says_network_unavailable=false`。

#### ② 反向门我也核了（不是只看"修好的一面"）
D 的 spec `frontend/e2e/qoder-failure-has-an-exit.spec.ts` 三条臂：
- `ord0126-a-healthy-connection-is-never-called-a-network-failure` —— 服务器答得出来（含 `route.fulfill`）就断言 `!/网络不可用|离线 · 只读|OFFLINE/`；
- `ord0126-a-journey-this-server-loses-comes-back-to-choosing-one` —— 死 id 要回到"选一趟"，不许永远转 404；
- `ord0126-the-cached-view-has-a-way-out-and-says-what-backs-it` —— **真 503/离线仍要说连不上服务器**，不许被 ① 顺手放宽。
⇒ 三条臂正是 R14 要的"同一分类被四个消费者共用"。**ORD-0126/0164 = ACCEPTED**（我的屏幕读数 + 三门齐；D 还自曝一次"门在量自己的仪表"：`addInitScript` 每 reload 把刚清掉的 id 塞回去）。
⇒ **ORD-0169 的 ①②④ 由这两笔一并满足**；③（恢复态下地图必须回来）我按定义**还没验**—— chooser 状态本就没有行程可读，地图缺席是合理的，需 HJ-P3 在有行程的正常态下复验，我不给它记绿。

#### ③ D 顺手量出来的一条新真相缺口 ⇒ 开 ORD-0178
D 的读数：`saveOfflineJourney()` **从来没有落一行**，`citynexus-offline` IndexedDB 在完全成功加载后仍是 **0 rows**，且 `serviceWorker.controller=true` 而 `caches=[]` ⇒
**旧版那句「正在显示只读的已保存行程」根本没有存储背书**，缓存视图**不可能被到达**。这是**存储层**缺陷，不是文案缺陷（D 已把 shell 改成"连不上服务器"而不是继续吹"有已保存副本"，方向对）。
⇒ shell 本身离线不可用（`caches=[]`）D 判为跨域、不在其写域 ⇒ 我不强塞给它，落 **ORD-0178** 排队，等 0167/0158 之后再说。

#### ④ 部署事实与用户影响（明说，免得下一个人误判）
- 用户预览现在是 **`index-BwIS1pck.js`**（tip `82f136f` 干净构建，含 D 的 0126/0135/0164 与 C 的 0166 收集修复）；**后端未动**（`:8693` 仍 `53fe8e8`），`:4782` 护栏 **ENFORCED**（本轮 `POST demo/reset → 403 PREVIEW_GUARDED`，带凭据量；不带凭据是 401，**别再拿匿名读数当"护栏没了"** —— 我自己的量具刚踩过这个坑）。
- 用户数据只读复核：journeys=3 / plan_versions=19 / travelers=3 / places `CN-BEIJING 8 + CNX-DEMO 8`，**未变**。
- 公网隧道 `GET /api/v1/demo/scene → 401 in 1.56 s`（链活的）。
- 我实验用的持久档现在停在"无行程"chooser；**不影响用户手机**。我会把它放回有效行程再做后续复验。

status: ORD-0126/0164 ACCEPTED（正反两向屏幕实测 + 三门）；ORD-0169 三条满足、地图那条待正常态复验；预览= 82f136f 构建包；ORD-0178 开单（离线存储无背书）
evidence: 本块表格（同一 Profile 同一入口两个包的并排读数）· `frontend/e2e/qoder-failure-has-an-exit.spec.ts` 三条臂 · 我本轮 patrol 输出（403 ENFORCED / 数据计数）

- id: ORD-0178
  to: e345b9d6
  priority: high
  if_head: 82f136f
  order: |
    【"已保存"这句话没有存储背书 —— 你 22:2x 自曝的那条，我落成一单，但**先量再改**，别顺手加缓存】
    你的读数（我复述进账本）：`saveOfflineJourney()` 从未落行、`citynexus-offline` 在完全成功加载后 **0 rows**、
    `serviceWorker.controller=true` 而 `caches=[]` ⇒ 缓存视图根本到不了，旧文案「正在显示只读的已保存行程」是**无源之言**。
    要做（顺序即验收）：
    ① **先量**：在真机视口下打印三件——IndexedDB 各 store 的 rowcount、`cacheKeys().length`、成功加载一次后二者是否变化；
       结论只有两种：`NO_PERSISTENCE`（什么都不落）或 `PARTIAL`（落了但没读回）。**不许猜**。
    ② 若 `NO_PERSISTENCE`：**把"已保存"这句话彻底删掉**（你 shell 已经改成"连不上服务器"，方向对），
       同时把 `saveOfflineJourney()` 这条死代码**要么接通要么删除**——留着比没有更危险，因为它会让下一个人以为有离线副本。
    ③ 若要真做离线：**先写契约再写码**，且必须回答三件：存什么（哪些 endpoint 的哪份投影）、多新（`observed_at` + 过期口径）、
       何时可说"已保存"（只有落行成功且能读回时）。**不许**为了让"已保存"变真而塞 `caches`——那是把 R14 的病换个层再犯一次。
    ④ 门：(甲) 无存储时屏幕不得出现"已保存/只读的已保存行程"；(乙) 有存储且读回成功时才可出现，且要显示数据新鲜度；
       (丙) 突变：把 rowcount 检查摘掉 ⇒ 必须红。
    禁令：不碰 `:4781/:4782/:8693` 与 `_live.db`；禁 `demo/reset`（R13，护栏保持 ENFORCED）；生产包 + 手机视口才算验收；
    报数带 SHA/树/命令/收集计数（archive 导出无 .git 就明写）；引用提交附 `git log -1` 原样。
    【优先级】排在 ORD-0169 收尾与 ORD-0146 之后；这条不急，但**"不许说没有依据的话"**这半属于②，可以现在就做（纯删伪证）。
  status: DISPATCHED@2026-09-21T23:2x+08 by 494abfd7（源自 D 自己承认的缺口，不是我又发明需求）
