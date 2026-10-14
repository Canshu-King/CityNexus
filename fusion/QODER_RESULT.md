# QODER_RESULT — 融合分支上现在真能用什么（2026-10-15 00:50）

按 `fusion/QODER_EXECUTION_ORDER.md` 的 Deliverables 写这一份：SHA、受影响的测试、正常界面入口、
新增动作 vs 之前、以及还欠什么。数全部是本轮现读；口径与复跑命令在
`fusion/QODER_PARITY.md`、`fusion/qoder_import/SLICE1_UI_PORT_SEAM.md`（切片 1）与
`fusion/qoder_import/SLICE2_POI_IMPORT_SEAM.md`（切片 2，§6 的数出自这里）。

## 0. 哪一枚尖，推到哪儿了

| 尺 | 数 |
|---|---|
| 分支 | `fusion/qoder-import-20261014` |
| 产品尖 | **`9a3b7ff0fb`**（写本行时的 `git rev-parse --short HEAD`；本文件的 docs 提交之后它会再前进，现读用同一条命令） |
| 超出融合基线 `594f9a4e75` 的提交 | **35**（`git rev-list --count 594f9a4e75..HEAD`；切片 2 占 **11** 枚，其中 **4** 枚只动词典文件——`rev-list --count fbe0d41cbc^..HEAD -- frontend/src/i18n/LocaleContext.tsx`） |
| 产品代码面 diff（pathspec `backend/app backend/tests frontend/src`，**不含 `frontend/e2e`**） | **27 文件 / +8086 / −32** |
| 远端 | **没推**。`git ls-remote` 现读三枚 fusion 尖仍是 `594f9a4e75a973a1ebd82beeafe5ecf3d9fc5c66` |
| 落地面（与「绿不绿」是两回事） | `git merge-base --is-ancestor 594f9a4e75 HEAD` ⇒ **YES**，本尖是基线的后代、不是入账工 12:53 通播里那种「不相交」枝；codex 车道枝 `fusion/codex-journey-20261014` 超基线 **0** 枚 ⇒ 现在合并的冲突面只有我这批纯插入的插入点本身 |

**先认一条我自己报错的数**：上一版这一格写的是 **21 文件 / +6092**。那条 `git diff --stat` 是在切片 2 的文件**还没 `git add`** 的时候取的，`git diff` 不看未跟踪文件，所以少算了 6 枚新文件（`poi_import.py`、它的测试、`PoiCandidateCard.tsx`、`features/poiimport/` 三枚）＝**−6 文件 / −1994 行**。提交之后重跑同一条命令才是 27 / +8086。教训记在 `SLICE2_POI_IMPORT_SEAM.md` §7。

⇒ 号令者要的「publish PR into canonical」这一步**没做**，推与 PR 都要主人点头（charter 还要求交叉评审 owner），所以本尖目前只在本地。

## 1. 受影响的测试（本轮现读，四道闸）

| 闸 | 数 | 复跑 |
|---|---|---|
| 后端这三片 | collections + checkins **38 passed / 7.07s / RC=0**；POI 导入 **9 passed / 2.63s / RC=0** | `pytest -q tests/test_qoder_ord0444_collections_fusion.py tests/test_qoder_ord0476_checkins_fusion.py`、`pytest -q tests/test_qoder_ord0437_poi_import.py` |
| `import app.main`（收集期闸，这棵树咬过我两次） | **COLLECT_OK / RC=0** | 同一枚解释器 `CityNexus/.venv` |
| 界面守门 + 走查 + 导入活口，同一条权威栈 | 当前存档那趟是 **7 passed / 28.1s**（`slice2r5`，`reports/**` 的证据就出自它）。同一支上另有 `slice2r2` **7 passed / 32.1s**、`slice2r3` **7 passed / 28.3s** 两趟独立新库；红面也留在名单里：`slice2r1` **2 failed / 5 passed**（两枚红都红在我的 spec 上，见 `SLICE2_POI_IMPORT_SEAM.md` §7）、`slice2r4` **1 failed / 6 passed**（红在我新加的候选卡断言上：按下之后的按钮文字实为 `✓已选中——点一下取消`，`toHaveText` 精确比不下，改 `toContainText` 后绿） | `_run_e2e_slice2_r1.sh <RUN_ID>` |
| 类型闸 | `tsconfig.check.json`、`tsconfig.typecheck.json`、外加覆盖三枚 spec 的那一行 `tsc` 三枚 **各 0 错误行**。spec 那枚闸做过反向对照：把 `toHaveText` 写成 `toHaveTextx` ⇒ 唯一一条 `error TS2551`，改回 ⇒ 0（`_tsc_specs_r2.txt`） | `SLICE2_POI_IMPORT_SEAM.md` §6 |
| 词典闭包（切片 2 补的漏） | 面板要 **9** 枚 `poiImport.card*`，缺失 **0**，词典共 822 枚键；**上玻璃的是 7 枚**，另 2 枚（`要你选` 与其 reason）要两枚自家地点被同一行对上才出现，本城布景给不出，所以只在门上证明 | `_slice2_dict_closure_r2.py`、`ARM_FILE_CARD_KEYS_PROVEN_ON_GLASS` |
| 行尾漂移闸 | **CRLF_DRIFT_FILES 0**（故意翻坏一枚 `v8Routes.ts` 时它打印 1 并点名，之后修回） | `_slice2_landed_r1.py` |
| 全量套件单变量 A/B（同根**两枚样本**） | 基线 `594f9a4e75` **272 failed / 1901 passed / 7 errors / 510.23s**；上一尖（切片 1 落地时）**156 failed / 2055 passed / 7 errors / 415.30s**；本尖跑了**两趟**：**155 failed / 2065 passed / 7 errors / 367.76s** 与 **155 / 2065 / 7 errors / 392.17s** | 同一枚解释器 `CityNexus/.venv`、各自新库、`-p no:cacheprovider`；样本二存在 `_pytest_import_slice2_full_r2.log` |
| 翻转那枚的地板（切片 2 补的第三条腿） | 两枚文件**各自单跑 20 趟**：r44 `0 / 20`、我的 POI `0 / 20`；**同一进程连跑**累计 **53 趟里 1 趟红**，且那趟没留日志 ⇒ 记为**未结** | `SOLO_REPEAT_*`、`POI_THEN_R44_*` |

A/B 的结论只认集合不认总数，因为总数在这两棵树里主要由**测试互相踩**决定，不是代码。**这一条本轮被我自己的第二枚样本推翻过一次，先认**：上一版写的是「`RED_ONLY_IN_SLICE2 0`」，那是一枚样本的读数；本尖再跑一趟，红名集合就动了 2 枚，所以那个 0 从来不是「零回归」的证据。现在的尺换成「同一尖跑两趟，差集稳不稳定」：

- **本尖两趟之间的红名差**：`SAME_TIP_SAMPLES_FLIPPED 2`。
  `test_r44_resilient_operator_brain.py::test_operator_brain_blocked_lineage_reuses_incident_then_resumes` 样本一**红**、样本二**绿**；
  `test_qoder_g3_xproc_http.py::…` 样本一**绿**、样本二**红**。
  ⇒ 单趟那 1 枚「只有切片 2 红」（`RED_ONLY_IN_SLICE2 1`）**在两枚样本面前不成立**：
  `RED_ONLY_IN_SLICE2_STABLE_IN_BOTH_SAMPLES 0`——没有一枚在本尖两趟都红、而上一尖不红。这才是可说的说法。
- r44 那枚的机制不是猜的，读了代码：它数的是**固定演示行程** `22222222-2222-4222-8222-222222222222` 上的 `AgentRun` 行数（`== 1`），实报错文是 `assert 2 == 1`；
  而这枚 id 被本树 **5** 份测试文件写死共用（现读 `test_wp01_wp03.py`、`test_qoder_ord0219_*` 两枚、`v191/v192_harness.py`），`demo/reset` 还会停掉**进程级** guardian worker。
  同根单变量对照拆成三档：
  ① **各跑各的**：本尖单跑 **3 passed**、基线单跑 **3 passed**（`R44_SOLO_*`），且**各自重复 20 趟红面 0**——我这枚新 POI 文件单跑也是 **0 / 20**（`SOLO_REPEAT_*`），所以「0」是这两枚文件自己的地板，不是我把谁跑绿了。
  ② **同一进程连跑**（我的 POI 文件在前、r44 在后）：当前这趟 **12 passed**，但累计 **53 次同进程尝试里有 1 次红**（汇总行 `1 failed, 11 passed`）——
     **那一次我没留日志，说不出红的是哪一枚**。之后 26 次手写重复全绿，脚本自己还内建 10 趟计数（`POI_THEN_R44_REPEAT_*`，每次复跑刷新）。
     ⇒ 这一条我按**未结**记，不按结论记；①的地板加上「那一次抓不到名字」意味着我不能把它写成「我的文件不会踩到别人」。
  ③ 它在整套里红、单跑绿，配合 ① ⇒ 共用库＋进程级 worker 的时序踩，不是移植引入的。我没改它（它属于别的车道），也没把它算成我的功劳。
- 上一版还错过一次：我把「只有 1 枚比基线红」那枚名字写成了 r87，并断言「两棵树单跑都红，所以是执行顺序变了」——**那句当时就被实测推翻并已更正**：
  同一棵树、同一份代码、单跑、每次自己的临时库，它会翻。6 趟重复：**基线 3 红 3 绿**，**本尖 1 红 5 绿**；钉 `PYTHONHASHSEED` 也锁不住。
  断言原文两边同一形状：`assert 'READY_FOR_NATIVE_PLAN' == 'OPENING_UNVERIFIED'`，即两个候选的位置换了。
  机制读自代码：候选按 `captured_at, id` 排序，而 `id` 是随机 uuid，时间戳一致时次序由随机数决定；测试用 `unknown, grounded = candidates` 按位置解包，于是接近半概率红。
  ⇒ 它是**基线里一条真实的测试卫生缺陷**，我没顺手改（改了会盖掉那条测试所属车道对同一枚的观察）。复跑：`python _r87_flake_root_r2.py`。
- 我这 **47** 枚（collections 20 + checkins 18 + POI 9）在三趟全量里都不在失败名单：`MY_TEST_FILES_RED_IN_FULL_RUN 0`——是在整套里，不是只单独跑绿。
- 反向对照（证明「基线那 117 枚不红」也不是我的功劳）：`test_solver_runtime_gate.py` 基线整套红 **15**，同根单独跑 **20 passed**；
  `test_v1923_final_code_gate.py` 整套红 **13**，单独跑 **13 passed**；`test_v192_shadow_trial_gate.py` 单独 **61 passed**。
  `test_v13_integrity.py` 基线整套红 22 / 本尖 14（本尖单独跑仍是 14，即这 14 枚是结构性的、两边共有）。
- 7 枚 ERROR 两边同一枚文件（`test_qoder_mobility_evidence_sources.py`，出在 setup 期而非断言期），与移植无关。
- ~~我这 38 枚在**整套里**也没出现在失败名单（`grep -c` 命中 **0**）~~ ⇒ 已由上面那条替代：现在是 **47 枚**（collections 20 + checkins 18 + POI 9），`MY_TEST_FILES_RED_IN_FULL_RUN 0`，同样是在整套里而不是只单独跑绿。

⇒ 可说的说法：**同一尖的两趟样本之间没有稳定差集，本轮移植没有引入新的失败**；不能说的说法：**这套件全绿**、拿 156 与 272 直接比大小、或把任何**单趟**红名差当结论。
复跑：`python _slice2_landed_r1.py`（快腿，已经把两趟样本的名字差并进来，不再需要 `--full`；长腿 `--full` 才会再花 6 分钟重跑整套）。名字差本身在 `python _slice2_failed_nameset_r1.py`，它自带 reader 自检：解析出的红名数 ≠ 汇总行自己写的数就退出。

## 2. 走查落在哪儿（号令者要的 "one saved 390x844 walkthrough"）

`reports/qoder-ord0510-walk/`：**8 枚** PNG + `walk_manifest.json`（视口 390×844、后端 :8113、journey、每屏字节与 sha256 前 12 位）。
最新一趟是 `slice2r5`（也是 `reports/**` 里存着的那趟），manifest 记 `8 frames / 8 distinct digests`（规则本身是断言：重复即红）：
`805ba0b41891 45127B hub`、`b618eef82aed 81165B discover`、`dbf0a861e914 32968B trips-fresh`、`9cd925fa40f4 41724B trips-stamped`、
`ba91cf81adca 33453B trips-collected`、`fe3eae4247da 67999B live`、`c51ef6b2e014 43744B me`、`8ae28f864f95 59350B import`。
其中 `03_trips_fresh` 这一屏与上一趟存的那枚**逐字节相同**（32968 B），而它左右的屏都动了——没动的屏就该长这样，这一条也是「摘要比的是像素不是标题」的反证。
第 8 屏是切片 2 的 `/v8/import`，它除了结构（`poi-import`、`poi-import-parse`）还断言两句**面板自己词表里的话**——
「从文本导入地点」与「本地解析，不打开链接」（`poiImportCopy.ts:390`、`:174`；这两句不在 app 词典里，实测 grep 为空），
所以这一屏证明的是导入屏在 390 宽能落地并说得出人话；候选卡的全局词典键由 §6 的活口证明（只有那里会渲染候选卡），**实测到玻璃上的是 9 枚里的 7 枚**，剩下 2 枚只在门上证明——别写成「九枚都上了屏」。
GO 那一屏按实测记：`go_bootstrap_reachable_by_url: false`（`bootstrap-discovery` 在这八屏计数 **0**），
理由写在 manifest 里——它在 `V8Experience.tsx:1212` 是状态门，没有 URL，所以这里记「不在这儿」，不假装有条点击路径。
另有一条同样的诚实记录：`/v8/import` 在 390×844 是**地址直达**，底栏五格（`mobileRoutes`）里没有它，源树也一样只把它放在 `desktopRoutes`。

## 3. 正常界面入口（不是 testid 门，是这台手机上真要点的地方）

| 屏幕 | 地址 | 这一片给了什么 |
|---|---|---|
| 城市探索 | `/v8/discover`（底部主导航「城市探索」） | 自己的**收藏架**列表面板：架子名、`N 枚地点`、每枚地点行（没写备注就写「没写备注」）；R107/R108 的城市发现控制台仍在这屏 |
| 行程 | `/v8/trips`（底部主导航「行程」→ 行程工作区） | 每一站两枚控件：**打卡**（只盖这一站）与**收入架子**（在自己的架子之间挑一枚）；列表下方是**足迹**面板：按天分组、当天时区、`共 N 枚足迹`、每行的备注与来源 |
| 无凭据时 | 同上两屏 | 两片面都只说一句「还没有旅客身份，所以没问服务器」，实测收藏读门的请求数 = **0**（是没问，不是被拒） |
| 导入地点 | `/v8/import`（**抽屉/地址直达**：`import` 只在 `desktopRoutes`，390 宽底栏五格里没有它） | 贴一段文字 → 逐行回「读出了什么、对上了几个、哪几个要你选、哪几个没找到」→ 三条出口（加进计划 / 存进架子 / 只存不排）；截图那一格今天只登记形态不识别 |

## 4. 新增的用户动作 vs 基线

| 动作 | 基线 `594f9a4e75` | 本尖 `9a3b7ff0fb`（`slice2r5` 那趟现读） | 证据 |
|---|---|---|---|
| 把一处收进自己的架子 | **做不到**：`features/collections/` 0 文件、注册表 grep 0、库里没有 `collection_*` 表 | 挑架子 → 写门 → 重读 → `已收在 收藏架 r3`；重复按只说不写（`item_count_after_repeat=1`） | 走查 `05` / `C_collect.json` |
| 看自己有哪些架子、里面有什么 | 做不到 | 架卡 + 地点行 + 计数 | 走查 `02` / `D_scope.json` |
| 给到过的站打卡 | **做不到**：`features/checkin/` 0 文件 | 按一站 → `data-state` 到 已打卡；再按 → 门回 **409**，句子带服务器自己的时刻（`这一站已经打过卡了（服务器记的是 10月15日 00:24）…`）、无 uuid 无 reason_code，服务器 `2 → 2` 不动 | 走查 `04` / `A_footprint.json`、`B_duplicate.json` |
| 看足迹（按天、时区、总数、来源） | 做不到 | `00:24 Arrival 没写备注 网页端打的`，日区 `Asia/Shanghai`；走查结束时服务器侧累计 **3** 枚（manifest `stamps_on_server`） | 走查 `04` / `A_footprint.json` |
| 架子归谁 | 无鉴权面可谈 | 由这台设备上的签名凭据决定：换旅客只见空态、无凭据不发请求（`D_scope.json`）；点名别人的 id 结构上收不到（422，见 `QODER_PARITY.md` §3） | `D_scope.json` + parity §3 |
| R107/R108 的城市发现、live 屏 | 有 | **仍在、仍能打开**（走查 `02`/`06` 各自断言后才截图） | `walk_manifest.json` |
| 把一段笔记/清单贴成计划里的地点 | **做不到**：`features/poiimport/` 0 文件、`backend/app/poi_import.py` 不存在、两扇门都没有 | 贴 → 解析门逐行答（`读出 N 行 · 对上 M 个 · …`）→ 挑 → 加进计划：`9 → 10` 行，新行 `2026-10-09T09:00:00+08:00`，那句故意对不上的行 `junk_rows 0`（没写进去）；对不上的行说「没找到」而不是编一枚 | §6 / `reports/qoder-ord0537/import_arm.json` |
| 同一天再贴一次同一个地点 | 做不到 | 门答 `already_present`，屏上「本来就在那一天」而**成功那句消失**（不是并排出两行），行数 `10 → 10` | 同上 |
| 把贴出来的几枚收进架子 | 做不到（切片 1 只有单枚收架） | 复用切片 1 那两扇门与那套句子，收完以**凭据作用域的重读**为准（`holds_target true`、`item_count 1`） | 同上 |
| 只存不排（不写进行程） | 做不到 | 这一格按** absence** 量：选它之后两枚写控件（`poi-import-add`/`poi-import-collect`）计数都是 **0**，屏上明说这里什么都没写 | 同上 |
| 贴一条纯链接 | 做不到 | 具名形态 `LINK_ONLY` + 具名主机 `xiaohongshu.com`，且**编造出的候选行数 = 0**（不打开链接这条写在徽章上：本地解析，不打开链接） | 同上 |
| 导入会不会顺手造足迹 | 无从谈起 | 活口在导入全程结束后读打卡门：**3 枚**，与同一趟走查 manifest 的 `stamps_on_server` 同一数（两处读的是同一枚 journey）。**这条只是读数，不是前后对照**——它说明导入没把足迹面搅乱，不构成「结构上不能盖章」的证明 | 同上 |

⇒ 一句话口径：**这扇门在融合树上只有「抽屉/URL」这一条来路**（源树挂在 discover 面板与 AI 规划 sheet 上的两条触发腿 `onOpenPreparePlaces`/`onImportPlaces` 都没搬，融合树 `grep` 命中 0），说「导入已接通」必须带上这句。

## 5. 还欠什么（不沉默）

1. **没推、没 PR**：等主人点头，且 charter 要求交叉评审/整合 owner 才算落 canonical。
2. **GO MODE 仍缺读腿**：`getBootstrapPocketWalkGo` 零调用点、`GoMode` 组件不存在，charter Phase 4(B) 的
   「reload to see persisted state」在当前界面不可能过。判责在 Codex 的 `fusion/codex-journey-20261014`，我没顺手改。
3. **`footprintRead.ts` 未移植**：它要 `mapPanelCopy.ts` 里 6 枚 `footprint*` 键，融合树没有，且只有地图面读它 ⇒ 地图上的足迹这条腿没接。
4. **`vite build` / 真机 PWA 在这条分支一次都没跑过**（`node_modules` 是只读 junction，构建会写盘）。
5. **切片 3–4 未开工**：`.ics` 导出 + abort、成员角色三件套。切片 2 已落地（§6），但它带着三条**没接的腿**：
   discover 面板上的 `onOpenPreparePlaces`、AI 规划 sheet 上的 `onImportPlaces`（源树 `v8PanelRegistry.tsx:195`、`V8Experience.tsx:2214`），
   以及 390 宽底栏里的那一格——接它们要动别的屏或 494 行以外的 `V8Experience.tsx`，按切片 1 立的规矩另开一刀。
6. **party_size 那两枚台上树改动仍等裁定**（`stay_mobility.py` +2056/−2227 那批），默认按可评审 cherry-pick 补进而非丢弃。
7. **`demo/scene/ensure` 判定不移植**：布景/维护工具，不是产品能力（本机空库实测 403），按 charter 那句「区分产品新增与证据专用」。
8. **两棵树的红面主因是测试互踩**，本轮已用同根单跑取证；但**没有**任何「整套绿」的说法可引——
   要继续做融合树测试卫生（每文件独立库/顺序隔离）才谈得上把全量当闸。
9. **那 7 枚 ERROR 的因已定位、不在本尖修**：fixture 对封存演示行程 `22222222-…` 调 `/demo/start`，门回
   **409 `DEMO_START_REFUSED`**（`journey must be PLANNED with a selected plan`）。该文件来自 `20bce7c843`（09-29，ORD-0415），
   移植源树 `eeb8b8d2fd` 里同样存在，两边全量都错 ⇒ 早于本轮移植；要修的是布景状态，不是这两片能力。
10. **r87 那枚翻脸的因也定位了，同样不在本尖修**：一次 discovery 写入的多枚候选共享同一个 `captured_at`，
    而返回列表按 `captured_at, id` 排序，`id` 是 `str(uuid4())` ⇒ 次序由随机数决定；测试又是
    `unknown, grounded = candidates` 按位置解包，于是接近半概率红。单跑 6 趟重复，**这一趟的分布**是基线 3 红、
    本尖 1 红（命令本身不确定，重跑数字会变，所以它只用来证明「会翻」，不用来证明比例；
    钉死 `PYTHONHASHSEED` 锁不住，同一种子先绿后红）。要修的是断言形态（按 `selection_state` 取，不按位置），
    归属 r87 那条车道，我不顺手改别人的测试。

## 6. 切片 2（从文本导入地点）的活口数值（2026-10-15 00:28，runId `slice2r5`）

复跑：`bash D:/moodle/_qoder_fusion_import/_run_e2e_slice2_r1.sh <RUN_ID>`（权威栈，setup + 切片 1 四腿 + 走查 + 本条 = **7 passed / 28.1s**），
或 `python D:/moodle/_qoder_613907d0_demo1014/parity/_slice2_landed_r1.py` 把下面每一行连同其它闸一次打全。
**数值取自仓库里的 `reports/qoder-ord0537/import_arm.json`**，不取自控制台——实测 `导入架子` 经 stdout 落到日志里成了 `?????`。

| 尺 | 数 | 这一行钉住的是 |
|---|---|---|
| 计划行数 | `9 → add 10 → replay 10` | 写腿真落库；同一天重贴**不多写** |
| 新行时刻 | `2026-10-09T09:00:00+08:00`，`added_activity_id aba6af54-e783-4176-b3fe-63928a310e22` | 落在计划第一天 09:00（+75 分钟），且是从 `readback_path` 读回来的、不是 201 自说的 |
| 候选卡上玻璃的词典句 | `已对上 / 这里没有 / 这座城市的地点里没有能对上这一行的，所以不能添加。 / 你写的是：Five Great Avenues / 第 1 行 / 选中 / ✓已选中——点一下取消` = **7 枚** | 这 7 枚是 `innerText()` 逐枚取回的（`card_words`），不是我对源码的推断；剩 2 枚要「两枚自家地点被同一行对上」才现身，本城 9 行给不出 ⇒ 只有门证（`test_two_matches_become_the_travelers_choice_not_a_guess`）。按下与抬起是**同一枚控件的两个标签**，都钉了 |
| 对不上的那行 | `junk_rows 0` | 解析器没编造，屏幕没说「已加入」 |
| 候选名来源 | `resolve_probe: Five Great Avenues=RESOLVED` | 名字来自行程投影 + 解析门自证，**没有写死布景**（换种子会喊红而不是空转） |
| 架子 | `导入架子 item_count=1 holds_target=True` | 收架以**凭据作用域的重读**为准 |
| 只存不排 | `poi-import-add`/`poi-import-collect` 计数 **0** | 那格按 absence 量：没有写控件可写 |
| 纯链接 | 形态 `LINK_ONLY` + 主机 `xiaohongshu.com`，编造候选 **0** 行 | 缺口有名字，且没被偷偷识别 |
| 落地日 | `first_day 2026-10-09 / target_day 2026-10-10` | `JOURNEY_FIRST_DAY` 与 `TRAVELLER_CHOSEN` 两条都真走过 |
| 空态那条门 | `nav=/v8/discover` | 「去城市探索」用的是外壳自己的 navigate，没发明第二套跳转 |

**这一片不证明的三件事**（别按「就绪」读）：
1. 不证明窄屏或别的屏能点到导入（§5 第 5 条那三条没接的腿）；
2. 不证明截图识别可用——那一格今天只登记形态（`poi_import.py:23` 的 `SCREENSHOT_OR_IMAGE`，注释写明「本单不含 OCR」），没有识别腿；
   同样只登记不处理的还有 `PASSWORD_CODE`（`:24`）。活口对 `LINK_ONLY` 量的是「有名字 + 零编造候选」；
3. 不证明 `GET /api/v1/places` 与导入的目录口径一致：**实测两者不同**，读门带 provider 过滤（`main.py:16206`），
   解析门故意不带（`main.py:27742` 的注释自认）。种子城 `CN-TIANJIN` 的 9 枚 `Place` 全带 `citynexus-v9-domain`
   ⇒ 那扇读门对这座城返回 **0 行**。这就是本片的布景词汇必须来自行程投影的原因。

## 7. 本轮我自己的量具红过七次（1–3 的细节在 `SLICE2_POI_IMPORT_SEAM.md` §7）

1. **汇总读法会把红跑打印成绿跑**：`_slice2_landed_r1.py` 取「最后一行含 passed」，而 Playwright 的 line reporter 把
   `2 failed` 与 `5 passed (49.1s)` 写在两行、中间夹失败名 ⇒ `slice2r1` 那趟两红在这里显示成 `5 passed`。
   现在取末 60 行内**所有**计数行拼接，并拿 6 枚历史日志反向量过（`slice2r1`/`uiport_r9`/`walk_r8` 三枚红的现在都喊 `failed`）。
2. **`re.M` 我第二次犯**：名字集比对脚本第一版 `^FAILED` 零命中，两个空集合一比得出「零回归」。
   现在脚本自带自检：解析数 ≠ 汇总行自己写的数就退出并喊 reader is broken。
3. **我自己的工具把树弄坏过**：`read_text()/write_text()` 在 Windows 上把 5 枚文件整枚翻成 CRLF，
   `LocaleContext.tsx` 因此显示 3921 行改动（真实 18 行）。修回之后加了 `CRLF_DRIFT_FILES` 闸，
   并**故意翻坏 `v8Routes.ts` 一次**证明它会红（打印 `CRLF_DRIFT_FILES 1` 并点名）再修好；现在是 **0**。
4. **我上一条提交的话比代码多**：那枚 docs/tests 提交写「活口把候选卡的 9 枚词典键读下玻璃」，实测只有 **7 枚**
   ——`要你选` 与其 reason 要两枚自家地点被同一行对上才出现，布景给不出这个形状。**不改写历史**（`--amend` 不在许可里），
   而是两步补：`5980501d41` 的提交说明第一句就是这条更正，并把 7 枚句子写进 `card_words` 让数目变成**读出来的**；
   同时把这条从「我说过」变成闸要盯的口径（`ARM_FILE_CARD_KEYS_PROVEN_ON_GLASS 7` / `…_DOOR_ONLY 2`）。
   顺带一枚真红：新断言在 `slice2r4` 上失败，`Received: "✓已选中——点一下取消"` ——按下态的按钮里还有一个 `aria-hidden` 的 ✓ 字形，
   所以 `toHaveText` 精确比不下，改 `toContainText`；抬起态没有字形，那一枚仍按精确比。这条是断言写错，不是产品写错。
5. **`git diff --stat` 会漏数**：§0 那个 21 文件/+6092 是在切片 2 的文件还没 `git add` 时取的，`git diff` 不看未跟踪文件，
   于是少算 6 枚新文件（≈1994 行）。提交后同一条命令给 **27 / +8086**。口径改成一句话：**凡是「diff 面」的数，必须在提交之后取**，
   未跟踪状态下的 `git diff` 只能证明「这些改动在哪几枚已跟踪文件里」，不能证明总量。
6. **`rc=0` 的空读数长得像「远端没动」**：新加的 `ls-remote` 腿第一版带 `refs/heads/fusion` 这枚模式参数，
   `REMOTE_FUSION_TIPS_LIVE_RC 0` 而 `…_LINES 0`——三枚尖明明在那儿，我的过滤器写法让它们集体消失。
   现在改成拉全表再本地筛 `/fusion/`，并把「零行」当作**错**而不是结果：`REMOTE_TIPS_READER ZERO LINES …` 加退出码 1。
   反向对照做过：故意把筛的子串写成 `/fusion_zzz/` ⇒ 打印 `…_LINES 0` 并 RC=1；改回后脚本 sha1 与改前**逐字节相同**（`3032053f…`）。
7. **一枚样本被我当成了判决**（§1 的那条更正）：`RED_ONLY_IN_SLICE2 0` 与后来的 `1` 都是单趟读数，
   而同一尖跑两趟就有 2 枚名字翻面。口径改成一句话：**回归结论最少两趟样本**，且只认「在两趟里都稳定差集」的名字；
   这条现在写在量具里（`_slice2_failed_nameset_r1.py` 会读 `_pytest_import_slice2_full_r2.log` 并打印 `SAME_TIP_SAMPLES_FLIPPED`），
   不再只写在我脑子里。
