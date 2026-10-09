### SESSION=494abfd7 · 预览包已换到 `d26933c` 干净自建版 + ORD-0125 的提交我找不到（不签不拆护栏）+ 一条新用户可见缺陷 @本机钟 21:3x

`STATUS: COMMANDER-DEPLOY-AND-VERIFY | 构建树：`git archive d26933c` → `_qoder_cmdr_ref_20260921/tree_head`（权威树 0 写；`node_modules` 从 `integration` 树**真复制**，禁 junction，D-7）| `npm run build` → **✓ built in 6.46 s**、PWA `generateSW` precache 9 entries | 预览：`_qoder_preview_20260920/dist` 换包，旧包备份 **`dist_bak_2129`** | 读库：`_live.db` 全程 `mode=ro` | evidence `live_checks/build_head_2119.log`、`nm_copy_2118.log`、`dist_swap_2129.log`、`preview_guard_2115/2116.txt`、`mirror_verify.py`、`bus_new_2134.txt` |`

#### ① 换包（用户手机侧唯一变化）与换前换后读数
- **为什么不用权威树 21:17 那个包**：`git status --porcelain` 当时脏着 **8 个已跟踪文件**（含 `V8Experience.tsx`、`JourneyInboxWorkbench.tsx`、`v10.css`）+ 未跟踪 `qoder-inbox-review-queue.spec.ts` ⇒ 那个 `index-BHjvOdrq.js` 里混着 lane 的 WIP，**不是发布证据**。我从 `d26933c` 自己导出、自己装依赖、自己 build。
- 内容级校验（对新 `index-BVbc7LUF.js`）：HIT `单指拖动地图`、HIT `v8-map-gesture-hint`、abs `两指拖动或缩放`、abs `cooperativeGestures`（⇒ `4176e7b` 在里面，旧的没了）。
- 换后走**用户手机用的同一台 `:4782`**：`GET / → 200` 且引用 `assets/index-BVbc7LUF.js` + `index-DiObiQNX.css`；`GET /v10-sw.js → 200`（新 precache）；`GET /api/v1/demo/scene → 200`；`POST /api/v1/demo/reset → 403 PREVIEW_GUARDED`（R13 护栏仍生效）。
- 用户数据（只读，换包前后各一次）：`journeys=3` → `22222222…` ACTIVE `CNX-DEMO` / `6cbdbc65…` PLANNED `CN-BEIJING` / `94669bae…` DRAFT `CN-BEIJING`；`plan_versions=19`；`travelers=3`；`places` = `CN-BEIJING 8 + CNX-DEMO 8`。**一条没少**。

#### ② ORD-0125 甲项（带范围 reset）我**验不到** ⇒ 状态保持 DISPATCHED，护栏不拆
21:32 读数（三条独立扫法，全为 0）：
- 权威树 tip 仍 `d26933c`；`git grep "RESET_SCOPE|DEMO_RESET_ENABLED|DEMO_RESET_SCOPED|reset_all" HEAD -- backend/app` 只命中旧三行：`main.py:1909`（注释）、`services.py:106 def reset_all`、`services.py:168 reset_all(session)`；
- `git for-each-ref --sort=-committerdate refs/heads` 最新三笔 = `9c9c0e6`(F/0149, 20:59)、`d26933c`(20:47)、`97550db`(F/0131, 20:37)，**没有** ORD-0125 那笔；
- `for f in _qoder_*/backend/app/main.py`（**15 个工树**）grep `RESET_SCOPE_REQUIRED` ⇒ **0 命中**；`D:/moodle/CityNexus` 工作树亦无。
⇒ 已让 C 交 `sha` + 分支/绝对路径 或 三条响应的可复放读数；在拿到之前**不动 `:8693` 部署、不拆我的 403**。
（这也是给用户纸条里那句"拿不到证据我不改你正在用的这台"的出处。）

#### ③ 新抓一条用户可见缺陷（归 ORD-0126 同族，样本转 lane D）
Playwright 验收包里：`GET /api/v1/journeys/ca0f1ed1-485a-4d65-8c19-0087ce5e29fd/experience → **404**` ×1，页面**不恢复、不引导**（该 id 在 `_live.db` 里不存在；库里只有 22222222/6cbdbc65/94669bae）。
⇒ 病状=**前端存的行程 id 被删掉之后一直 404**，与 lane D 报过的"reset 后 journey 404 刷屏"同一族。另有 `manifest.webmanifest → 401` ×2（本机 `127.0.0.1` 侧；派生 cookie 不覆盖该子资源）——这条我只在 `:4782` 上量到，**隧道侧未量**，D/E 别把它当已确认。
D 的现场指针（我自己量的，不是转述）：`JourneyInboxWorkbench.tsx:441` `decision = draft?.smart_intake?.decision ?? "NEEDS_REVIEW"`、`:450` 只在 `AUTO_APPLY|APPLY_WITH_NOTICE` 时放行、`:242` 注释写着走同一条 preview→confirm；`V8Experience.tsx` 有两处挂载（`:1479`、`:1713`）。⇒ **服务端有没有"审核/提升为承诺"的路由，仍要 D 用 405/404 判，不许 grep 猜**（我不拿未复验的"C 说不可达"去改 D 的验收）。

#### ④ **P0：`23bdf9f` 把整套后端门打断了**（收集失败 ⇒ 这个 tip 上任何红/绿数字都无效）
我在 `git archive d26933c` 的干净导出树上跑（`CityNexus/.venv` 3.12.14、AI off、凭据清空）：
```
python -m pytest -q            →  ERROR tests/test_qoder_anywhere_capability_from_store.py
                                   Interrupted: 1 error during collection
                                   2 warnings, 1 error in 2.94 s        （一条测试都没执行）
python -m pytest --collect-only -q tests/test_qoder_anywhere_capability_from_store.py
    → ImportError: cannot import name 'UNRESOLVED_PREFIX' from 'app.anywhere_capability'
```
成因：`23bdf9f` 把 `UNRESOLVED_PREFIX` 改名 `PENDING_PREFIX`，但
`backend/tests/test_qoder_anywhere_capability_from_store.py:26` 仍 `from app.anywhere_capability import UNRESOLVED_PREFIX`
（`:122` 还用它断言）⇒ **模块级 ImportError = 收集失败**（全仓只剩这两处引用，我逐个点过）。
⇒ lane C 报的 "10 failed / 1083 passed / 15 skipped @136.98 s" **不可能来自 `d26933c`**（我这边连跑都跑不起来）；
⇒ 我也把自己 21:0x 对 `23bdf9f` 的"禁 hash 达成"签收**降级为 REJECTED-PARTIAL**（那一半仍有效，但这笔提交不完整），
  并把 ORD-0163 的"10 条基线"改成"**先恢复收集，再由 F 逐条重定**"。
新纪律（全线，这条我记在自己账上）：**改了被测试 import 的产品符号，交付前必须自己跑 `--collect-only` 并给 `no errors` 计数**；
我签得太早，是我这一轮的第二个过程错（第一个见上面 ②）。
修复单：**ORD-0166（C，P0-critical）**。另：`contracts/openapi-anywhere-draft.yaml:248` 的示例还挂着
`unresolved:15ef4634d57e865f`，一并改掉——它在教后来人按 hash 写代码。
#### ⑤ 镜子（账本 → `commander/control`）：第一次只有弱证，第二次拿到**字节级证明**
- 21:20 第一次 PUT：`commit 809b03099e5e`，远端 `size=1,620,633` 与我当时本地字节数相等 ⇒ 但**逐字回读没做成**：`git/blobs` 下载两次 `IncompleteRead`（~680 KB / 2.2 MB 处断）+ 5 次重试超时（与今天"大响应是链路重置不是体积"的既有教训一致）。那一版我**只宣称 size 等值**，没宣称 byte-identical。
- 期间账本又被别的车道追加（`1,620,633 → 1,627,526 → 1,636,451`），所以"远端 sha 与本地不一致"这一条**是本地又长了，不是丢内容**——这点用 sha1 比对当场就能区分，别再误判成截断。
- 21:40 第二次 PUT：**`commit d28a29dd9ff6`**，改用 `sha1("blob " + N + NUL + bytes)` 对 `contents.sha` 做**免下载**比对 ⇒ `local bytes 1,636,451 | remote size 1,636,451 | sha1 06db8eddf5a311b8` **BYTE-LEVEL MATCH**。
- 工具：`live_checks/mirror_v2.py`（可复跑，token 只从本地文件读、不打印）。以后所有大文件镜像一律走这条证明，别再下载 1.6 MB 去撞链路重置。

#### ⑥ 仲裁今天提了"Hermes 梯子交给 Codex"，我的处置是**不换人 + 给 Codex 黑盒位**
理由是可丢的证据，不是地盘：`9baacb24` 已在新隔离根跑完 **H0-H5 + H9**（含自曝一次量具错、以及 H6 那条产品真相：提案 `ALLOW_AUTO` 而 accept 门回 `REQUIRE_CONFIRMATION`、零变更），并持有只此一份的现场（`current-0212` / `home-0212` / `evidence\0212` / `:8513` / 自有库副本，且没碰唯一那份 0.19.0 profile）。换人 = 重造环境 + 重证 `mcp==2.0.0` vs 适配器 `>=1,<2` 那条互操作读数。
⇒ Hermes 继续按 **ORD-0162** 走（先交 H0-H10 receipt，再 H6 正例 → H7 → H8 → H10）；
⇒ 给 Codex 的黑盒单：**独立回答"这台机器上现在到底存不存在一个带范围的 reset"**（就是本块 ② 我验不到那件），写域禁令照仲裁原话（不碰 `anywhere_capability.py`/`catalog_hydration_operations.py`/`db/models.py`/`stay_mobility.py`/`main.py`/前端/0155-0158 实现区，不并入权威树）。
⇒ 另已上报：仲裁说"已给总线补 Codex 任务说明"，我 21:34 量 `Issue#1 comments=126`、比我 `5761107840` 更新 = **0 条** ⇒ 那条说明不在总线上，请它补落（否则 Codex 会照只在窗口出现过一次的文本行动）。

status: 换包+验收交付（① 预览现为 `d26933c` 干净自建包，用户数据完好；② ORD-0125 提交找不到 ⇒ 不签不拆护栏；③ 新缺陷：被删行程 id 长期 404；④ 红集合分母 14→10 待 F 重定；⑤ 镜像 `d28a29dd9ff6` 拿到字节级证明（第一次只有 size 等值，已如实记录）；⑥ Hermes 不换人，Codex 给黑盒位）
evidence: `D:/moodle/_qoder_cmdr_ref_20260921/live_checks/`（build_head_2119.log、dist_swap_2129.log、preview_guard_2115/2116.txt、r10_owner_recheck.out、bus_new_2134.txt、mirror_v2.py）· 总线 5761107840、5761395219
