# QODER_RESULT — 融合分支上现在真能用什么（2026-10-14 22:38）

按 `fusion/QODER_EXECUTION_ORDER.md` 的 Deliverables 写这一份：SHA、受影响的测试、正常界面入口、
新增动作 vs 之前、以及还欠什么。数全部是本轮现读；口径与复跑命令在
`fusion/QODER_PARITY.md` 与 `fusion/qoder_import/SLICE1_UI_PORT_SEAM.md`。

## 0. 哪一枚尖，推到哪儿了

| 尺 | 数 |
|---|---|
| 分支 | `fusion/qoder-import-20261014` |
| 产品尖 | **`8f65324554`**（写本行时的 `git rev-parse --short HEAD`；本文件的 docs 提交之后它会再前进，现读用同一条命令） |
| 超出融合基线 `594f9a4e75` 的提交 | **22**（`git rev-list --count 594f9a4e75..HEAD`） |
| 产品代码面 diff（`backend/app backend/db frontend/src`） | **19 文件 / +3924 / −32** |
| 远端 | **没推**。`git ls-remote` 现读三枚 fusion 尖仍是 `594f9a4e75a973a1ebd82beeafe5ecf3d9fc5c66` |

⇒ 号令者要的「publish PR into canonical」这一步**没做**，推与 PR 都要主人点头（charter 还要求交叉评审 owner），所以本尖目前只在本地。

## 1. 受影响的测试（本轮现读，四道闸）

| 闸 | 数 | 复跑 |
|---|---|---|
| 后端这两片 | **38 passed / 5.70s / RC=0**（collections 20 + checkins 18） | `pytest -q tests/test_qoder_ord0444_collections_fusion.py tests/test_qoder_ord0476_checkins_fusion.py` |
| 界面守门 + 走查，同一条权威栈 | **6 passed / 24.0s**（runId `uiportr10`）与 **6 passed / 23.2s**（`uiportr11`）两趟独立新库，各自 7 张截图摘要两两不同；仓库里存的证据是 `uiportr11` | `SLICE1_UI_PORT_SEAM.md` §4–§5 |
| 类型闸 | `tsconfig.check.json`、`tsconfig.typecheck.json`、外加覆盖 spec 的那一行 `tsc` 三枚 **各 0 错误行** | `SLICE1_UI_PORT_SEAM.md` §5 |
| 全量套件单变量 A/B | 基线 `594f9a4e75` **272 failed / 1901 passed / 7 errors / 510.23s**；本尖 **156 failed / 2055 passed / 7 errors / 415.30s** | 同一枚解释器 `CityNexus/.venv`、各自新库、`-p no:cacheprovider` |

A/B 的结论只认集合不认总数，因为总数在这两棵树里主要由**测试互相踩**决定，不是代码：

- `FAILED` 名集合比差：**只有 1 枚**在本尖红而基线整套不红——
  `test_r87_first_live_city_discovery.py::test_r87_live_discovery_keeps_member_receipts_private_and_blocks_ungrounded_opening`。
  我先前把它写成「两棵树单独跑都红，所以是执行顺序变了」——**那句是错的，已被实测推翻并在此更正**：
  同一棵树、同一份代码、单跑、每次自己的临时库，它会翻。6 趟重复：**基线 3 红 3 绿**，**本尖 1 红 5 绿**；
  把 `PYTHONHASHSEED` 钉成同一个值也锁不住（同一种子先绿后红，所以不是哈希序）。断言原文两边同一形状：
  `assert 'READY_FOR_NATIVE_PLAN' == 'OPENING_UNVERIFIED'`，即那两个候选的位置换了。
  机制读自代码：候选按 `captured_at, id` 排序，而 `id` 是随机 uuid，两枚候选时间戳一致时次序由随机数决定；
  测试用 `unknown, grounded = candidates` 按位置解包，于是接近半概率红。
  ⇒ 这 1 枚不是移植引入的回归，但它是**基线里一条真实的测试卫生缺陷**，我没有顺手改它（改了会盖掉那条测试所属车道对同一枚的观察）。
  复跑：`python _r87_flake_root_r2.py`。
- 反向对照（证明「基线那 117 枚不红」也不是我的功劳）：`test_solver_runtime_gate.py` 基线整套红 **15**，同根单独跑 **20 passed**；
  `test_v1923_final_code_gate.py` 整套红 **13**，单独跑 **13 passed**；`test_v192_shadow_trial_gate.py` 单独 **61 passed**。
  `test_v13_integrity.py` 基线整套红 22 / 本尖 14（本尖单独跑仍是 14，即这 14 枚是结构性的、两边共有）。
- 7 枚 ERROR 两边同一枚文件（`test_qoder_mobility_evidence_sources.py`，出在 setup 期而非断言期），与移植无关。
- 我这 38 枚在**整套里**也没出现在失败名单（`grep -c` 命中 **0**），不只是单独跑绿。

⇒ 可说的说法：**本轮移植没有引入新的失败**；不能说的说法：**这套件全绿**、或拿 156 与 272 直接比大小。

## 2. 走查落在哪儿（号令者要的 "one saved 390x844 walkthrough"）

`reports/qoder-ord0510-walk/`：7 枚 PNG + `walk_manifest.json`（视口 390×844、后端 :8110、journey、每屏字节与 sha256 前 12 位）。
本轮 7 枚摘要互不相同（规则本身是断言：重复即红）；`03`/`04` 两屏 h1 同为「3 天行程」而字节 45569→41655，说明比的是像素不是标题。
GO 那一屏按实测记：`go_bootstrap_reachable_by_url: false`（`bootstrap-discovery` 在这七屏计数 **0**），
理由写在 manifest 里——它在 `V8Experience.tsx:1212` 是状态门，没有 URL，所以这里记「不在这儿」，不假装有条点击路径。

## 3. 正常界面入口（不是 testid 门，是这台手机上真要点的地方）

| 屏幕 | 地址 | 这一片给了什么 |
|---|---|---|
| 城市探索 | `/v8/discover`（底部主导航「城市探索」） | 自己的**收藏架**列表面板：架子名、`N 枚地点`、每枚地点行（没写备注就写「没写备注」）；R107/R108 的城市发现控制台仍在这屏 |
| 行程 | `/v8/trips`（底部主导航「行程」→ 行程工作区） | 每一站两枚控件：**打卡**（只盖这一站）与**收入架子**（在自己的架子之间挑一枚）；列表下方是**足迹**面板：按天分组、当天时区、`共 N 枚足迹`、每行的备注与来源 |
| 无凭据时 | 同上两屏 | 两片面都只说一句「还没有旅客身份，所以没问服务器」，实测收藏读门的请求数 = **0**（是没问，不是被拒） |

## 4. 新增的用户动作 vs 基线

| 动作 | 基线 `594f9a4e75` | 本尖 `fbca9536d3` | 证据 |
|---|---|---|---|
| 把一处收进自己的架子 | **做不到**：`features/collections/` 0 文件、注册表 grep 0、库里没有 `collection_*` 表 | 挑架子 → 写门 → 重读 → `已收在 收藏架 r3`；重复按只说不写（`item_count_after_repeat=1`） | 走查 `05` / `C_collect.json` |
| 看自己有哪些架子、里面有什么 | 做不到 | 架卡 + 地点行 + 计数 | 走查 `02` / `D_scope.json` |
| 给到过的站打卡 | **做不到**：`features/checkin/` 0 文件 | 按一站 → `data-state` 到 已打卡；再按 → 门回 **409**，句子带服务器自己的时刻、无 uuid 无 reason_code，服务器 `2 → 2` 不动 | 走查 `04` / `A_footprint.json`、`B_duplicate.json` |
| 看足迹（按天、时区、总数、来源） | 做不到 | `22:10 Arrival 没写备注 网页端打的`，日区 `Asia/Shanghai`；走查结束时服务器侧累计 **3** 枚（manifest `stamps_on_server`） | 走查 `04` / `A_footprint.json` |
| 架子归谁 | 无鉴权面可谈 | 由这台设备上的签名凭据决定：换旅客只见空态、无凭据不发请求（`D_scope.json`）；点名别人的 id 结构上收不到（422，见 `QODER_PARITY.md` §3） | `D_scope.json` + parity §3 |
| R107/R108 的城市发现、live 屏 | 有 | **仍在、仍能打开**（走查 `02`/`06` 各自断言后才截图） | `walk_manifest.json` |

## 5. 还欠什么（不沉默）

1. **没推、没 PR**：等主人点头，且 charter 要求交叉评审/整合 owner 才算落 canonical。
2. **GO MODE 仍缺读腿**：`getBootstrapPocketWalkGo` 零调用点、`GoMode` 组件不存在，charter Phase 4(B) 的
   「reload to see persisted state」在当前界面不可能过。判责在 Codex 的 `fusion/codex-journey-20261014`，我没顺手改。
3. **`footprintRead.ts` 未移植**：它要 `mapPanelCopy.ts` 里 6 枚 `footprint*` 键，融合树没有，且只有地图面读它 ⇒ 地图上的足迹这条腿没接。
4. **`vite build` / 真机 PWA 在这条分支一次都没跑过**（`node_modules` 是只读 junction，构建会写盘）。
5. **切片 2–4 未开工**：POI 导入、`.ics` 导出 + abort、成员角色三件套。
6. **party_size 那两枚台上树改动仍等裁定**（`stay_mobility.py` +2056/−2227 那批），默认按可评审 cherry-pick 补进而非丢弃。
7. **`demo/scene/ensure` 判定不移植**：布景/维护工具，不是产品能力（本机空库实测 403），按 charter 那句「区分产品新增与证据专用」。
8. **两棵树的红面主因是测试互踩**，本轮已用同根单跑取证；但**没有**任何「整套绿」的说法可引——
   要继续做融合树测试卫生（每文件独立库/顺序隔离）才谈得上把全量当闸。
9. **那 7 枚 ERROR 的因已定位、不在本尖修**：fixture 对封存演示行程 `22222222-…` 调 `/demo/start`，门回
   **409 `DEMO_START_REFUSED`**（`journey must be PLANNED with a selected plan`）。该文件来自 `20bce7c843`（09-29，ORD-0415），
   移植源树 `eeb8b8d2fd` 里同样存在，两边全量都错 ⇒ 早于本轮移植；要修的是布景状态，不是这两片能力。
10. **r87 那枚翻脸的因也定位了，同样不在本尖修**：一次 discovery 写入的多枚候选共享同一个 `captured_at`，
    而返回列表按 `captured_at, id` 排序，`id` 是 `str(uuid4())` ⇒ 次序由随机数决定；测试又是
    `unknown, grounded = candidates` 按位置解包，于是接近半概率红（实测基线 6 趟 3 红、本尖 6 趟 1 红，
    钉死 `PYTHONHASHSEED` 锁不住）。要修的是断言形态（按 `selection_state` 取，不按位置），
    归属 r87 那条车道，我不顺手改别人的测试。
