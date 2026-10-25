# QODER_RESULT — 融合分支上现在真能用什么（2026-10-15 02:50）

按 `fusion/QODER_EXECUTION_ORDER.md` 的 Deliverables 写这一份：SHA、受影响的测试、正常界面入口、
新增动作 vs 之前、以及还欠什么。数全部是本轮现读；口径与复跑命令在
`fusion/QODER_PARITY.md`、`fusion/qoder_import/SLICE1_UI_PORT_SEAM.md`（切片 1）、
`fusion/qoder_import/SLICE2_POI_IMPORT_SEAM.md`（切片 2）与
`fusion/qoder_import/SLICE3_CALENDAR_EXPORT_SEAM.md`（切片 3，§6/§7 的数出自它）。
**切片 3 的每一枚数现在有一条同根的复跑命令**：`python review/ord0496/slice3_gates_r1.py`（本仓库内），
它把 §0、§1 的 git 面、词典闭包、一杖三枚键的分枝审计、玻璃回执、四趟全量的名字差一次打全；反过来能红的证明在
`review/ord0496/glass_can_go_red_r1.py`（三枚反向对照）与同脚本的 `--run-control crlf`。

## 0. 哪一枚尖，推到哪儿了

| 尺 | 数 |
|---|---|
| 分支 | `fusion/qoder-import-20261014` |
| 产品尖 / 现读尖 | 最后一枚带产品改动的尖 **`41fbb9c731`**；其后全是 docs 与量具提交（**取值这一行时 5 枚**，`git rev-list --count 41fbb9c731..HEAD` 现读）。**改这张表的那枚提交本身会让枚数多一枚、把表里的「现读」作废**——那正是 §7 第 5 次的形状，所以你重跑看到尖号与枚数不同是预期内的，只有产品面那几个数不受影响（同数与否也由命令现读，见下两行） |
| 超出融合基线 `594f9a4e75` 的提交 | 取这行时 **48**（`git rev-list --count 594f9a4e75..HEAD`），分两段现读：`594f9a4e75..f9abba3fde` **37** 枚（切片 1 与切片 2，其中词典枝 4 枚）、`f9abba3fde..HEAD` **11** 枚（切片 3 的产品与词典 6 枚 + 其后的 docs 与量具 5 枚，逐枚点名用 `git log --oneline f9abba3fde..HEAD`） |
| 产品代码面 diff（pathspec `backend/app backend/tests frontend/src`，**不含 `frontend/e2e`**） | **30 文件 / +10074 / −33**（docs 与量具那几枚提交不碰产品面，所以它与上一版同数——同数本身是现读出来的，不是假设） |
| 含证据面（再加 `frontend/e2e reports review fusion`） | **66 文件 / +13785 / −41**（上一版是 `65 / +13694 / −41`；多的那一枚文件、那 91 行就是 `bb_letter_precheck_r1.py` 自身。这一枚每次加提交都会动，所以它只作为「现读」报，不作为基线报） |
| 远端 | **没推**。`git ls-remote` 现读三枚 fusion 尖仍是 `594f9a4e75a973a1ebd82beeafe5ecf3d9fc5c66` |
| 落地面（与「绿不绿」是两回事） | `git merge-base --is-ancestor 594f9a4e75 HEAD` ⇒ **YES**，本尖是基线的后代、不是入账工 12:53 通播里那种「不相交」枝；codex 车道枝 `fusion/codex-journey-20261014` 超基线 **0** 枚 ⇒ 现在合并的冲突面只有我这批纯插入的插入点本身 |
| 号令者的字典规矩（「字典单独一枝、一杖最多三枚键」） | 动 `LocaleContext.tsx` 的提交 **8** 枚，逐枚新增**不同键**数是 **3,3,3,3,3,3,1,1** ⇒ 全部 ≤3，且每枚只进一个命名空间（`calendar.` 三枚 / `poiImport.` 三枚 / `nav.import` 与 `checkin.title` 各一枚）。逐枚审计在 `slice3_gates_r1.py::dictionary_branch_audit`（打印 `DICTIONARY_BRANCH_COMMITS 8 / KEYS_ADDED_TOTAL 20 / OVER_3_KEYS 0 / DICT_BRANCH_READER_SELF_CHECK PASS`），它按提交 diff 现算而不是按我数过；反向对照 `--run-control dictclass` 见 §1 表那一行 |


**先认一条我自己报错的数**：上一版这一格写的是 **21 文件 / +6092**。那条 `git diff --stat` 是在切片 2 的文件**还没 `git add`** 的时候取的，`git diff` 不看未跟踪文件，所以少算了 6 枚新文件（`poi_import.py`、它的测试、`PoiCandidateCard.tsx`、`features/poiimport/` 三枚）＝**−6 文件 / −1994 行**。提交之后重跑同一条命令才是 27 / +8086。教训记在 `SLICE2_POI_IMPORT_SEAM.md` §7。

⇒ 号令者要的「publish PR into canonical」这一步**没做**，推与 PR 都要主人点头（charter 还要求交叉评审 owner），所以本尖目前只在本地。

## 1. 受影响的测试（本轮现读，八道闸）

| 闸 | 数 | 复跑 |
|---|---|---|
| 后端这四片 | collections + checkins + POI 导入 **47 passed / 6.02s / RC=0**（20 + 18 + 9），日历导出 **17 passed / 2.52s / RC=0** ⇒ 我这轮移植自带的测试共 **64** 枚 | `pytest -q tests/test_qoder_ord0444_collections_fusion.py tests/test_qoder_ord0476_checkins_fusion.py tests/test_qoder_ord0437_poi_import.py`、`pytest -q tests/test_qoder_ord0496_calendar_export.py` |
| `import app.main`（收集期闸，这棵树咬过我两次） | **COLLECT_OK / RC=0**，`app/main.py` 现读 **28163** 行 | 同一枚解释器 `CityNexus/.venv` |
| 界面守门（切片 3 的 `.ics` 那一屏） | BASELINE 趟 **rc=0 / 2 passed**（runId `slice3base022320`，`reports/qoder-ord0496-calendar/**` 的证据就出自它）。三枚反向对照各自 **rc=1 / failed=1 / passed=1** ⇒ `CONTROLS_RAN=3 CONTROLS_THAT_BIT=3`，被改的源文件事后**逐字节修回** | `python review/ord0496/glass_can_go_red_r1.py` |
| 界面守门（切片 1+2 那五屏 + 走查 + 导入活口） | 存档那趟 **7 passed / 28.1s**（`slice2r5`）；同支另有 `slice2r2` **7 passed / 32.1s**、`slice2r3` **7 passed / 28.3s** 两趟独立新库；红面留在名单里：`slice2r1` **2 failed / 5 passed**、`slice2r4` **1 failed / 6 passed**（都在我的 spec 的断言上，见 `SLICE2_POI_IMPORT_SEAM.md` §7） | `bash D:/moodle/_qoder_fusion_import/_run_e2e_slice2_r1.sh <RUN_ID>` |
| 类型闸 | `tsconfig.check.json`、`tsconfig.typecheck.json`、外加覆盖 e2e 那三族 spec 的手工 `tsc` 一行，三枚 **各 RC=0 / 0 错误行**。手工闸的反向对照：把 `census.bare_line_feeds` 写成 `census.bare_line_feeds_typo` ⇒ 唯一一条 `error TS2551`，改回 ⇒ 0（日志 `D:/moodle/_qoder_fusion_import/_tsc_specs_slice3_tamper_r1.txt`）。**注意这枚闸不在任何工程配置里**：`tsconfig.check.json` 只点名 5 枚文件、`tsconfig.typecheck.json` 只管 `src/**`，`e2e/**` 谁都不覆盖——这条是本轮现读的，别再当成配置替你把关 | `SLICE3_CALENDAR_EXPORT_SEAM.md` §6 |
| 词典闭包（切片 3 的 9 枚） | 面板与导出客户端要 **9** 枚 `calendar.*`，词典里 **9** 枚，缺失 **0**，「同一枚键被定义不止一次」也 **0**，词典里总出现次数 **18**（每枚一次定义、两处语言包）。九枚的**出处逐枚打印**（`TripItinerary:139/143/301` 的 `t()` 调用、`calendarExport:63-67` 的拒绝映射），逐枚带行号、可点验 | `python review/ord0496/slice3_gates_r1.py` 的 `CALENDAR_KEYS_*` 段 |
| 「字典单独一枝、一杖最多三枚键」（号令者的规矩，现由脚本核） | **8 枚词典枝提交、逐枝 3,3,3,3,3,3,1,1 枚键、超 3 枚的枝 0 枝、累计新增 20 枚键**（切片 3 的 9 + 切片 2 的 10 + 切片 1 的 1；逐枚键名由脚本自己打印，不是我数给你看）。这枚 leg 自带**合成自检**：reader 若读不出 `calendar.refused.not_found` 这种带下划线的键，就打印 `DICT_BRANCH_READER_SELF_CHECK BROKEN` 并以退出码 1 结束。反向对照 `--run-control dictclass` **在进程内把字符类换成我这轮真写错的那枚**（`[A-Za-z.]`，不含 `_`）⇒ 总数 **20 → 18**、两枝被读成 2 枚键、`OVER_3_KEYS` 仍是 0（**少报看着像更守规矩**，所以没有自检它永远不会被发现）、自检 BROKEN、`BITE rc= 1`；改回 ⇒ `PASS`，全程**不改磁盘上任何文件** | `python review/ord0496/slice3_gates_r1.py` 的 `DICTIONARY_BRANCH_*` 段；对照：`... --run-control dictclass` |
| 行尾漂移闸 | **CRLF_DRIFT_FILES 0**；故意翻坏一枚 `v8Routes.ts` 时它打印 **1** 并点名，之后按原字节修回 | `python review/ord0496/slice3_gates_r1.py --run-control crlf` |
| 全量套件单变量 A/B（同根**每尖两趟**，共四趟） | 见下表的四行；本尖 **156 failed / 2081 passed / 7 errors / 388.73s** 与 **155 / 2082 / 7 / 427.20s** | `python review/ord0496/slice3_gates_r1.py` 的 `SAMPLE` / `MEMBERSHIP_TABLE` 段（日志 `_pytest_import_slice{2,3}_full*.log` 在仓库外同盘 `_qoder_fusion_import/`） |
| 那枚 xproc 闸的地板 | 见 §1b | `python review/ord0496/xproc_floor_r1.py --repeat 8` |


A/B 的结论只认集合不认总数，因为总数在这两棵树里主要由**测试互相踩**决定，不是代码。

**先认一条本轮又错给自己的地方**：上一版给这枚差集起的名字是 `RED_ONLY_IN_SLICE3_STABLE_IN_BOTH_SAMPLES 1`，
它算的是「本尖两趟都红」**减去**「上一尖两趟的交集」——而 `g3_xproc` 那枚在上一尖的**第二趟**里也红过，
所以「1 枚新红」这句话是量具的标签骗人，不是差集本身骗人。现在四行标签各自描述自己的算法，并把逐趟归属打成表：

| 趟 | 汇总行 | 红名数 | reader 自检 |
|---|---|---|---|
| 上一尖（切片 2 落地时）样本一 | 155 failed / 2065 passed / 7 errors / 367.76s | 162 | 与汇总行一致（162 = 155+7） |
| 上一尖样本二 | 155 / 2065 / 7 / 392.17s | 162 | 一致 |
| 本尖（切片 3 落地）样本一 | **156 / 2081 / 7 / 388.73s** | 163 | 一致 |
| 本尖样本二 | **155 / 2082 / 7 / 427.20s** | 162 | 一致 |

`MEMBERSHIP_TABLE 3 varying names`（列序＝上一尖#1、上一尖#2、本尖#1、本尖#2）：

```
- Y Y Y   slice2 1/2  slice3 2/2   tests/test_qoder_g3_xproc_http.py::test_g3_xproc_two_uvicorn_workers_over_http_share_one_operation
Y - - -   slice2 1/2  slice3 0/2   tests/test_r44_resilient_operator_brain.py::test_operator_brain_blocked_lineage_reuses_incident_then_resumes
- - Y -   slice2 0/2  slice3 1/2   tests/test_r87_first_live_city_discovery.py::test_r87_live_discovery_keeps_member_receipts_private_and_blocks_ungrounded_opening
```

四行差集按新标签现读：`RED_IN_BOTH_SLICE3_AND_IN_NEITHER_SLICE2_SAMPLE **0**`、
`RED_IN_BOTH_SLICE3_BUT_ALREADY_FLAKY_ON_SLICE2 **1**`（就是 `g3_xproc`，见 §1b）、
`RED_IN_BOTH_SLICE2_AND_IN_NEITHER_SLICE3_SAMPLE **0**`、`RED_IN_BOTH_SLICE2_BUT_NOW_FLAKY_ON_SLICE3 **0**`，
`SAME_TIP_SAMPLES_FLIPPED **1**`（本尖两趟之间翻面的只有 r87），`SLICE3_OWN_TESTS_RED **0**`。
⇒ 四趟里**没有一枚**是「本尖两趟都红、而上一尖两趟都不红」。

- 我这 **64** 枚自带的测试（collections 20 + checkins 18 + POI 9 + calendar 17）在**四趟全量里都不在失败名单**：
  `SLICE3_OWN_TESTS_RED 0` 是本尖两趟的交集，上面那张逐趟表里也没有任何 `ord0496` 名字——是在整套里，不是只单独跑绿。
- **156 与 272 不能直接比大小**：272/1901 那趟是基线树在自己的根里跑的，跨根的红面主因（测试互踩的形态）不同根就不同；
  只有同一根内的单变量 A/B 可比。这条在 `tip16` 那轮已经实测过一次（拷贝树 19/22 vs 活树 14/14，同一份代码）。
- 反向对照（证明「基线那批不红」也不是我的功劳，切片 2 那轮现读，本轮未重跑）：
  `test_solver_runtime_gate.py` 基线整套红 **15**、同根单独跑 **20 passed**；`test_v1923_final_code_gate.py` 整套红 **13**、
  单独跑 **13 passed**；`test_v192_shadow_trial_gate.py` 单独 **61 passed**；`test_v13_integrity.py` 基线整套红 22 / 本尖 14
  （本尖单独跑仍是 14 ⇒ 这 14 枚是结构性的、两边共有）。
- 7 枚 ERROR 两边同一枚文件（`test_qoder_mobility_evidence_sources.py`，出在 setup 期而非断言期），与移植无关；
  因由定位在 §5 第 9 条。
- 上面表里那两枚历史翻面者的机制，都是**读了代码**而不是猜的：
  r44 数的是固定演示行程 `22222222-2222-4222-8222-222222222222` 上的 `AgentRun` 行数（`== 1`，实报 `assert 2 == 1`），
  而这枚 id 被本树 **5** 份测试文件写死共用，`demo/reset` 还会停掉**进程级** guardian worker；
  它的地板实测是**各跑各的 0/20 红**（本尖与基线各自单跑 20 趟），同一进程连跑累计 53 趟里 1 趟红**且那次没留日志**，
  所以那一档我至今按**未结**记，不按结论记。
  r87 是候选按 `captured_at, id` 排序而 `id` 是随机 uuid，测试又按位置解包 `unknown, grounded = candidates` ⇒ 近半概率红；
  钉 `PYTHONHASHSEED` 锁不住。两枚都不属于我的车道，我都没顺手改（改了会盖掉那条车道对同一枚的观察）。
  ⇒ 它是**基线里一条真实的测试卫生缺陷**，我没顺手改（改了会盖掉那条测试所属车道对同一枚的观察）。
  复跑：`python D:/moodle/_qoder_613907d0_demo1014/parity/_r87_flake_root_r2.py`（2150 字节，本轮现读它在那儿）。

⇒ 可说的说法：**同一尖的两趟样本之间没有稳定差集，本轮移植没有引入新的失败**；不能说的说法：**这套件全绿**、
拿 156 与 272 直接比大小、把任何**单趟**红名差当结论，或者把「两趟都红」当成「新红」——那还得看上一尖的两趟里有没有它。

### 1b. `g3_xproc` 那枚为什么本尖两趟都红（现读，不是我猜的）

`test_qoder_g3_xproc_http.py` 是 ORD-0224 车道的闸（两枚真 uvicorn worker 共用一个库）。它在我这轮的回归表里
是唯一一枚「本尖两趟都红」的名字，所以必须单独量，不能靠"它以前也翻过"搪塞。`python review/ord0496/xproc_floor_r1.py --repeat 8`：

| 尺 | 读数 |
|---|---|
| 这轮移植有没有碰过这枚闸的代码 | `XPROC_ARM_DIFF_VS_BASELINE (empty)`；同一枚文件在两棵树里 `sha256` 前 16 位都是 **`07fdf6c97187a6dd`** ⇒ **一字没动** |
| 洞在哪 | 直接调它自己的 `_http` 打一枚没人听的端口：两棵树都打印 `PROBE ESCAPED as urllib.error.URLError … -> the poll loop cannot survive this`。`_http` 只捕 `HTTPError`（该文件注释自陈「4xx/5xx 是读数不是异常」），于是**首枚就绪轮询**的连接失败直接逃出 `_wait_for_serving`（`:401 → :195 → :84`），`READY_DEADLINE_S = 120.0` 的重试窗与「子进程先退了」那条分支都轮不到说话 |
| 安静机器上的地板（同一条命令跑了两批） | 每批每棵树各 8 趟单跑：**第一批 tip 0/8、baseline 0/8**；**第二批 tip 1/8、baseline 2/8** ——红的那三趟失败帧全是同一形状 `frame[401 195 84]`、各自 `refusal_frames=2`、`1 failed in 3.49s / 3.61s / 3.82s`，绿的那些中位 **6.8–6.9s**。**基线尖（没有我一行代码的那棵树）点火次数比本尖还多一次**，两批合计 tip 1/16、baseline 2/16 |
| 点火过的证据 | 仓库外同盘存着 **7 枚**历史单跑红日志（`_xproc_solo_red_1..7.log`，每枚 `1 failed in ~4s`），本轮另存 16+16 趟带自述表头的日志（每枚日志第一行写 `# tree=<tip|baseline> sha=<那棵树的尖> target=… db=…`，因为 `pytest -q` 不打印 rootdir——上一版我就用「文件名里有树名」当身份，结果两棵树同名互相覆盖）；四趟全量里它 上一尖 1/2、本尖 2/2 |


⇒ 结论口径：**不是切片 3 引入的失败**——同一枚文件在两棵树里逐字节相同、失败帧同一形状（`:401 → :195 → :84`），
且**没有我代码的那棵树点火更多**（1/16 vs 2/16）；洞在「首枚就绪轮询让 `URLError` 逃出重试窗」这三行里，读得出来。
但也不能反过来说「与我无关」：子进程 `import app.main`，我的移植把它推到 **28163** 行，绑定端口更晚，
理论上会抬高点火概率——**这一批样本没能让这个方向成立，也没能把它打掉**，两批合计 32 趟里只有 3 趟红。
要它变成结论，得同一台机器上几百趟、或把它放到负载可控的 CI 里跑；那是 ORD-0224 车道的账。
**修法是一行**（在轮询里 `except urllib.error.URLError: time.sleep(0.1); continue`），
**我没改它**——那是别人车道正在读的闸，改了会替他们抹掉他们那侧的观察。这条已经写进 §8 给号令者的待决清单，等他裁定要我改还是让原车道改。



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

第二枚存档的**玻璃回执**不是那八屏，是切片 3 那一枚单独的证据：`reports/qoder-ord0496-calendar/`
（runId `slice3base022320`）＝ `manifest.json` + `exported.ics`（**2879 字节、9 枚 VEVENT**）+ 两枚 PNG。
它满足的是号令者那句「界面守门在 390×844 真点一次导出并留字节数/事件数回执」——下载只有文件能证明，
所以这里数的是 **Chromium 自己接受下来的那枚文件**，没有第二条腿去重访那扇门冒充导出。
manifest 现在自带 `run`（runId / 权威栈标记 / 那趟后端的库路径）与 `grammar`（CRLF 对数、裸 LF、超 75 octet 的行数、
最长行、`DTSTART/DTEND/UID/DTSTAMP` 各 9 枚）两块，回执因此能自己作证，不靠我复述；逐枚数值由
`python review/ord0496/slice3_gates_r1.py` 从存档件重新读出来（它同时校验 manifest 里写的字节数/sha 与文件真身一致）。


## 3. 正常界面入口（不是 testid 门，是这台手机上真要点的地方）

| 屏幕 | 地址 | 这一片给了什么 |
|---|---|---|
| 城市探索 | `/v8/discover`（底部主导航「城市探索」） | 自己的**收藏架**列表面板：架子名、`N 枚地点`、每枚地点行（没写备注就写「没写备注」）；R107/R108 的城市发现控制台仍在这屏 |
| 行程 | `/v8/trips`（底部主导航「行程」→ 行程工作区，默认子页就是「行程」那枚 tab，`V8Experience.tsx:2312`） | 每一站两枚控件：**打卡**（只盖这一站）与**收入架子**（在自己的架子之间挑一枚）；列表下方是**足迹**面板：按天分组、当天时区、`共 N 枚足迹`、每行的备注与来源。**切片 3 新增**：面板顶部一句人话旁边一枚**导出日历**按钮，按一次落一个 `.ics` 文件，屏上回「已下载 N 个日程…」 |
| 无凭据时 | 同上两屏 + 导出那一格 | 两片面都只说一句「还没有旅客身份，所以没问服务器」，实测收藏读门的请求数 = **0**（是没问，不是被拒）；导出这一格实测**下载数 0**、门回 **401**，屏上说「日历没能导出，所以没有下载任何东西。」——这句话本身也在词典里，不是裸键 |
| 导入地点 | `/v8/import`（**抽屉/地址直达**：`import` 只在 `desktopRoutes`，390 宽底栏五格里没有它） | 贴一段文字 → 逐行回「读出了什么、对上了几个、哪几个要你选、哪几个没找到」→ 三条出口（加进计划 / 存进架子 / 只存不排）；截图那一格今天只登记形态不识别 |

## 4. 新增的用户动作 vs 基线

| 动作 | 基线 `594f9a4e75` | 本尖 `41fbb9c731`（切片 1/2 那两趟走查 + 切片 3 的 `slice3base022320` 现读） | 证据 |
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

| 把整趟行程导成日历文件（`.ics`） | **做不到**，基线树四枚位置现读全空：`backend/app/calendar_export.py` 不存在、`app/main.py` 里 `calendar.ics` 命中 **0**、`TripItinerary.tsx` 里 `calendar-export` 命中 **0**、`LocaleContext.tsx` 里 `"calendar.` 键 **0** 枚 | 390×844 按一次 ⇒ 真下载一枚 **2879 字节**、文件名 `Tianjin · stay-aware weekend--d746ac1b-….ics`（带行程自己的标题），体内 **9 枚 VEVENT**、`DTSTART/DTEND/UID/DTSTAMP` 各 9 枚、**88 对 CRLF**、裸 LF **0**、超 75 octet 的行 **0**、最长行正好 **75**；屏上那句「已下载 9 个日程…」数的就是字节里那个 9 | `reports/qoder-ord0496-calendar/`、`slice3_gates_r1.py` 的 `GLASS_*` 段 |
| 没有旅客身份时按导出 | 无从谈起 | **下载数 0**，门回 **401**，屏上「日历没能导出，所以没有下载任何东西。」——这句话是词典值不是裸键（反向对照 `notice_prints_a_raw_key` 实测能红） | `glass_can_go_red_r1.py` |

⇒ 一句话口径：**这扇门在融合树上只有「抽屉/URL」这一条来路**（源树挂在 discover 面板与 AI 规划 sheet 上的两条触发腿 `onOpenPreparePlaces`/`onImportPlaces` 都没搬，融合树 `grep` 命中 0），说「导入已接通」必须带上这句。
⇒ 切片 3 的一句话口径：**导出这条腿在台上真点得动、文件真落得下，但它还没进契约**——`contracts/openapi.yaml` 与
`frontend/src/generated/api.ts` 都没有 `calendar.ics`（本轮现读：两枚文件里 grep 命中 **0**），所以「移植完成」不包含契约面；
把它接进契约要让生成客户端一起重跑，那是一刀独立的改动（§5 第 11 条）。

## 5. 还欠什么（不沉默）

1. **没推、没 PR**：等主人点头，且 charter 要求交叉评审/整合 owner 才算落 canonical。
2. **GO MODE 仍缺读腿**：`getBootstrapPocketWalkGo` 零调用点、`GoMode` 组件不存在，charter Phase 4(B) 的
   「reload to see persisted state」在当前界面不可能过。判责在 Codex 的 `fusion/codex-journey-20261014`，我没顺手改。
3. **`footprintRead.ts` 未移植**：它要 `mapPanelCopy.ts` 里 6 枚 `footprint*` 键，融合树没有，且只有地图面读它 ⇒ 地图上的足迹这条腿没接。
4. **`vite build` / 真机 PWA 在这条分支一次都没跑过**（`node_modules` 是只读 junction，构建会写盘）。
5. **切片 3 已落地（§8），切片 3b 与切片 4 未开工**。切片 2 落地时带着三条**没接的腿**（discover 面板上的
   `onOpenPreparePlaces`、AI 规划 sheet 上的 `onImportPlaces`，源树 `v8PanelRegistry.tsx:195`、`V8Experience.tsx:2214`，
   以及 390 宽底栏里的那一格）；切片 3 复用同一枚规矩：它接进行程面板的默认子页，所以**没有**新的「点不到」缺口，
   但见下面第 11、12 条两笔欠账。
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
11. **契约面（openapi / 生成客户端）里日历这条路是 0 命中**——不是「文件不存在」，是我这次**先按新规矩核过存在性**再数的：
    `contracts/openapi.yaml` 167236 B、`frontend/src/generated/api.ts` 265557 B 两枚都在，
    而 `calendar|\.ics|vevent` 大小写不敏感命中各为 **0**（`grep -c` 回 0、退出码 1＝零命中，两回事）。
    ⇒ 切片 3 的产品能力是**后端路由 + 手写契约测试 + 活口**三层落地的，生成物那一层按 §7 移植顺序表第 6 条
    「放最后靠合并后重生成，不手抄」处理。**耦合点记下**：重生成时这棵树的客户端会一起带上别的车道已经埋进
    契约面的键（如 `x-citynexus-max-administrators-per-journey`），所以生成腿必须在合并后跑，不能在本尖跑。
12. **切片 3b（abort）的闭包比我先前说的窄，也比它宽**。
    **先认一条我这轮读错过的数**：我先前写「融合树没有 `backend/app/services.py` 这枚文件」——那是我把 `grep -c` 的
    退出码 1（零命中）当成了「文件不存在」；现读三棵树这枚文件**都在**：融合尖 132459 B、融合基线尖 125832 B、源树 96762 B。
    真正为 0 的是里面的内容（同命令现读，非记忆）：

    | 尺 | 融合尖 | 融合基线 | 移植源树 `eeb8b8d2fd` |
    |---|---|---|---|
    | `backend/app/services.py` 里 `live_view` | **0** | **0** | **2**（定义在 `services.py:461 def journey_live_view(item: Journey) -> JourneyLiveView`） |
    | `class JourneyLiveView` | **0** | **0** | **1** |
    | `backend/app/main.py` 里 `live_view` | **0** | **0** | **5** |
    | `backend/db/schema.sql` 里 `aborted_at` / `abort_reason` | **0 / 0** | **0 / 0** | **1 / 1** |
    | `backend/app/main.py` 里 `abort` 命中 | — | — | 45（`_abort_refusal` 在 `:3499`、`abort_journey` 在 `:3529`） |

    ⇒ 切片 3b 的最小闭包是「**两列 DDL + 一枚融合树没有的 schema 类 + `services.py` 里那枚投影函数 + `main.py` 五处接线**」，
    而不是我上一版写的「搬一枚不存在的文件」。`services.py` 是**已跟踪、两尖都有、体量差 6657 B** 的共用文件
    ⇒ 这一片的合并冲突面从「未知」变成「一枚具体的、双方都改过的文件」，这是可评的差，不是盲搬。

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

## 7. 本轮我自己的量具红过十七次

第 1–7 条的细节在 `SLICE2_POI_IMPORT_SEAM.md` §7；第 8–16 条那一轮的机器细节在 `SLICE3_CALENDAR_EXPORT_SEAM.md` §4。
**两份列表颗粒度不同、编号不对应**：那份按仪器逐条写（含本份没单列的「反向对照瞄错门」与「贪婪 `.` 把 156 读成 6」），
本份按我这侧的读数写（含那份没单列的「引用被自己覆盖掉的工件」「字段点数全 0」「缺失工件点查」），
本份第 13、15、16 条在两份里都有。

第 1–7 条引到的那批脚本**在仓库外**：`D:/moodle/_qoder_613907d0_demo1014/parity/`（本轮逐字节点过：
`_slice2_landed_r1.py` 19083 B、`_slice2_failed_nameset_r1.py` 4316 B、`_r87_flake_root_r2.py` 2150 B、
`_tsc_specs_r2.txt`、`_auth_accept_r1.json` 1033 B、`_boot_tables_r6.txt` 5783 B 全在）。
文档里以前只写了裸文件名没写目录，这不算假、但不可复跑——切片 3 起，引用的量具一律**放进仓库**
（`review/ord0496/`），这一条本身就是下面第 15 条的教训。

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

切片 3 那一轮又加了九次，**九次全在我这侧**（产品的字节没动过）：

8. **CRLF 的「对数」和「分段数」我混过一次**：文档里写「89 对 CRLF」，那是
   `len(bytes.split(b"\r\n"))` ——文件以 CRLF 收尾时分段数必然比对数 **多 1**，真数是 **88 对**。
   现在 `grammarCensus()` 直接数成对字节，并把 `bare_line_feeds === 0` 写成断言（裸 LF 有枚就该红），
   `slice3_gates_r1.py` 从存档 `.ics` 重读时也对这两个数各打一行。
9. **我引用了自己刚覆盖掉的证据**：那一版 §5 引的 sha `3eb676d3…`、journeyId `d27f4079…`、runId `slice3r1`
   都在我下一次跑玻璃时被同名覆盖——存档件被覆写之后再引旧读数，等于引用一枚不存在的东西。
   口径改成：**回执落进 `reports/**` 才算数**，且 manifest 现在自带 `run`（runId / 权威栈 / 那趟的库路径），
   读数与它自己那趟同源；这一版的数出自 `slice3base022320`。
10. **我自己的 `.ics` 字段点数全是 0**：写了 `b.count(b + k + b":")`，`b` 是整份文件，于是每枚字段都数成 0。
    改成按字段名逐行数（`DTSTART/DTEND/UID/DTSTAMP` 各 **9**），并且加了「`DTSTAMP` 去重后仍是 9 枚不同值」这种
    形状检查——否则「全 0」和「全 9」在只看总数时都可能被读成合理。
11. **词典闭包把文件名兜底当成了键**：`calendarExport.ts:143` 有一句 `... : "calendar.ics"`（下载失败时的
    兜底文件名），我的第一版闭包把任意引号里的 `calendar.` 都算成请求，于是打 `ASKED 10 / MISSING 1`。
    虚报的破口与漏报的破口一样贵：现在只认两种形状——`t("calendar.x")` 的实参，和拒绝映射的值，
    并**逐枚打印出处行号**（§1 那九行 `ASKED … <- …` 就是它）。
12. **「这句话是不是词典值」用整句包含去比，假红过一次**：屏上的句子是插值后的
    「已下载 9 个日程…」，词典值是「已下载 {events} 个日程…」，直接 `in` 永远不成立。
    现在先把数字与 `{placeholder}` 折成同一形状再比，两枚回执句各自打印 `…_IS_A_DICTIONARY_VALUE True`。
13. **差集那枚标签骗了我自己**（§1 开头的更正）：`…_STABLE_IN_BOTH_SAMPLES` 减的是上一尖两趟的**交集**，
    于是「上一尖只红过一趟」的名字被报成「新且稳定」；同一次改动里我还把 `set().intersection(*sets.values())`
    当交集用——那是**空集**去 intersection，恒为空，「逐趟归属表」当场把整片红面（一百多枚）当差集打了出来。
    两条一起修：四行标签各自描述自己的算法（`…_AND_IN_NEITHER_…` / `…_BUT_ALREADY_FLAKY_ON_…`），
    交集改用 `set.intersection(*sets)`，并补了那张 3 行 `MEMBERSHIP_TABLE`。
    **这一条是本轮最值钱的一次**：如果没有那张表，`1` 这个数字会顺理成章地读成「切片 3 带来一枚新红」，
    而它是上一尖也红过的那枚 xproc；§1b 才是要写进信里的东西。
14. **我的「缺失工件点查」本身是错的**：正则 `_slice2_[a-z_]*\.py` 不吃数字，而且只在仓库里找——
    于是把 7 枚在仓库外、确确实实存在的脚本判成「当时只是 heredoc，没落盘」。我差点把「引用没写目录」
    升级成「我编过复跑命令」，并已经把那句假认定写进了两份文档才撤掉。
    口径改成：**判「不存在」之前必须先在文件系统里找一遍**，且引用外部脚本要带绝对路径（本节开头那条就是补这个）。

15. **我把 `grep -c` 的退出码 1 读成了「文件不存在」**：第 14 条刚立完「判不存在之前先在文件系统里找一遍」的规矩，
    我就在同一轮里用 `grep -c live_view backend/app/services.py || echo "NO FILE"` 写出「融合树没有 `services.py` 这枚文件」，
    并把它写进了 §5 当作切片 3b 的未知项。零命中和没这枚文件是两件事：**`grep -c` 找不到匹配时回 0 并退出码 1**，
    文件在不在要用 `test -f` / `stat` 说。现读三棵树这枚文件都在（融合尖 132459 B / 融合基线 125832 B / 源树 96762 B），
    为 0 的是里面的 `live_view`——§5 第 12 条那张表就是改完的版本。
    这条与第 6 条同形状（`rc=0` 的空读数像「远端没动」），差别只在于这次是我把**非零码**读成了不存在：
    退出码是**关于命中**的，不是**关于文件**的，凡靠退出码分支的判断都要自带一枚存在性腿。

16. **我用来核「一杖最多三枚键」的那条 bash 正则，把带下划线的键整枚吃掉**：`grep -oP '^\+\s+"[a-zA-Z.]+"(?=:)'`
    的字符类里没有 `_`，于是 `calendar.refused.not_found` 与 `calendar.refused.not_calendar` 两枚键**凭空消失**，
    中间那枝被读成「2 枚键」（真数 3 枚）。这次的错方向是**少报**，看着像更守规矩，所以不会有人去查它；
    真正贵的是同一个字符类若长在 ASKED 那一侧，闭包会因为「不问了」而绿。
    ⇒ 已经把这条审计从我的记忆搬进仓库（`slice3_gates_r1.py::dictionary_branch_audit`），字符类写成
    `[A-Za-z0-9_.]+`，并**自带一枚合成自检**：拿 `+  "calendar.refused.not_found": "x",` 喂给 reader，
    读不出完整键名就打印 `DICT_BRANCH_READER_SELF_CHECK BROKEN` 并退出码 1。
    反向对照也进了仓库（`--run-control dictclass`，**进程内换类、一个字节都不落盘**）：换成我这轮真写错的
    那枚 `[A-Za-z.]` ⇒ 总数 **20 → 18**、两枝被读成 2 枚键、`OVER_3_KEYS` 仍是 **0**（少报会伪装成守规矩，
    这正是没有自检它永远不会被发现的原因）、自检 BROKEN、`CONTROL dictclass BITE rc= 1`；
    改回 ⇒ `DICTIONARY_BRANCH_COMMITS 8 / KEYS_ADDED_TOTAL 20 / OVER_3_KEYS 0 / SELF_CHECK PASS`，
    逐枝键名由脚本打印（3,3,3,3,3,3,1,1），不再靠我数给你看。

17. **我给号令者发的第一封 BB 机信被中枢拒收，孤儿是 6 枚数**：拒因由 `bus_hub.validate` 现读——正文里每一枚「待证的数」都必须真出现在某条 `--evidence` 命令的输出里。
    我这封只在信尾挂了一枚 `git rev-parse && git diff --stat | tail -1` 的腿，所以跨树字节数、含证据面的那行、以及两处**根本不是数**的东西都成了孤儿：
    `3,3,3,3,3,3,1,1` 被 `NUM_RE` 当成一枚带千分位的 `1,1`，而 `§12` 留下 `12`。⇒ 两处口径要记住：
    它比的是**整段输出**（`excerpt` 只截头部 400 字节，但每条命中的上下文片段也算出处，所以别按头部猜能不能过），
    而 `155/2065/7` 这种带斜杠的形状会被 `PATHISH` 当路径剥掉、`m_3b60c531cefb` 里紧跟字母的数字不被当作待证。
    第二封我先在本地重放了中枢的判据（用 `bus_hub.numeric_claims` 与 `bus.collect_evidence` 本身，不是另写一份近似版），
    ⇒ 量具进库：`review/ord0496/bb_letter_precheck_r1.py <正文> <出处腿JSON>` 打 `PRECHECK PASS/FAIL` 与逐枚孤儿数；
    第二次投递 `ORPHAN_COUNT 0 / PRECHECK PASS` 后一次通过，落账 `m_3b60c531cefb`（4 枚腿全 `rc=0`）。
    顺带一条现场发现：发信时 `:4799` **没有监听**（`hub.log` 末条活动是当夜 06:46 那批注册），信是先落 `drop/` 的；
    hub 的单实例锁按端口探活，所以我起了一支把它压着的信吸收进账（`delivered_at` 仍为空＝还没被读，不是已送达）。

⇒ 这十七次的形状是同一枚：**读数没毛病，读数的读法或标签有毛病**。所以本轮起的规矩是
「每一枚被文档引用的数，都要有一枚在仓库里的脚本能重新打出来；每一枚绿闸，都要有一枚反向对照证明它咬得住」。
§1 表里那八行「复跑」现在全部指向 `review/` 里在库的脚本，不再指向我的记忆。

## 8. 切片 3（`.ics` 日历导出）的数值与给号令者的待决清单（2026-10-15 03:00，runId `slice3base022320`）

| 尺 | 数 | 这一行钉住的是 |
|---|---|---|
| 玻璃上真点一次 | **1 次按下 ⇒ 1 枚下载**，`2879 B`，文件名 `Tianjin · stay-aware weekend--d746ac1b-….ics`（标题来自行程自己，不是写死） | 下载只有文件能证明；没有第二条腿重访那扇门冒充导出 |
| 文件自己数自己 | **9 枚 VEVENT** / `DTSTART` 9 / `DTEND` 9 / `UID` 9 / `DTSTAMP` 9（去重仍 9）/ **88 对 CRLF** / 裸 LF **0** / 超 75 octet 的行 **0** / 最长行 **75** | RFC 5545 §3.1 的两条硬限是断言不是注释；反向对照 `screen_stops_sending_the_credential`、`notice_prints_a_raw_key`、`button_loses_its_testid` 三枚各能红 |
| 门上的算术与字节对得上 | `activities=9 events=9 no_clock=0 no_stamp=0 sums=True` | 屏上那句「已下载 9 个日程」数的就是字节里那个 9，两处不是各说各话 |
| 回执跨趟稳不稳 | 三趟独立新库里**字节数 2879 与事件数 9 相同**（控制台读），但 **sha256 逐趟不同**（`7fb59c4d…` → `2d3eb7ce…`）：`UID` 是布景那枚行自己的 id、`DTSTAMP` 是行自己的 `updated_at`，所以哈希跨趟动是**设计如此**，不是内容漂 | 别把 sha 当回归闸；这一格把「哪两枚字段是 run-dependent」写进 manifest 的 `run_dependent_fields` |
| 无凭据那一腿 | 下载 **0** 枚、门 **401**、屏上「日历没能导出，所以没有下载任何东西。」 | 「它拒了」不能靠一句 grep：这一腿单独断言**没有出现裸键** |
| 后端这三片 | 日历 **17 passed / 2.52s**；collections+checkins+POI **47 passed / 6.02s** ⇒ 自带 **64** 枚，四趟全量里 `SLICE3_OWN_TESTS_RED 0` | 是在整套里不红，不是只单跑绿 |
| 契约面 | **0 处**（`contracts/openapi.yaml`、`frontend/src/generated/api.ts` 各 grep `calendar` 命中 0） | 明确没接的腿，见 §5 第 11 条 |

给号令者的待决清单（每一条都是我能动但**不该我单独定**的）：

1. **推不推**：三枚远端 fusion 尖现在仍是基线 `594f9a4e75a…`，本尖 43 枚提交只在本地。要推/开 PR 需要点头，
   charter 还要交叉评审 owner 才算落 canonical。
2. **`g3_xproc` 那一行谁改**（§1b）：`_wait_for_serving` 的首枚轮询让 `URLError` 逃出重试窗；基线尖 2/16、本尖 1/16 同帧红。
   我不改别人车道的闸；要我改请明说。
3. **契约 + 生成客户端这一刀什么时候开**：`.ics` 与切片 4 的成员三件套都要它（后者自带一枚契约键
   `x-citynexus-max-administrators-per-journey`，源树那枚测试还**去读生成客户端的文本**）。我按 80% 功能优先把它排在后面。
4. **第 10 枚 `calendar.` 键要不要**：`401` 现在落到 `calendar.refused.unknown` 这句「日历没能导出」，
   语义正确但不说「你没身份」。源树同样是 unknown 兜底；加一枚专门的键要多占一枝（号令者的「一杖最多三枚键」），所以我没加。
5. **`GET /api/v1/places` 与解析门口径不同**（§6 第 3 条，实测两座城都这样）：读门带 provider 过滤、解析门故意不带。
   这不是移植引入的，但它是「界面上能选到的地点」与「贴文本能对上」不一致的根因，等裁要不要合流。
6. **codex 车道**：`fusion/codex-journey-20261014` 超基线 **0** 枚提交（现读），GO MODE 的读腿还在那边欠着（§5 第 2 条）。
7. **切片 4（成员角色三件套）要不要开工**：我已把它的依赖闭包量完——**schema 差集为 0**（三件套写的列在融合库全在，
   `journey_role_capabilities` 还是超集），但两枚写门要做与日历门同一类的**鉴权接缝改写**（源树把 actor 当请求体里的自称，
   融合树只认签名令牌），而且融合树的 `access` 前端比源树小得多（`AccessPanel.tsx` 357 行 vs 1087 行、
   `accessDoors.ts` 119 行且**没有任何写函数**、roster 相关 grep 命中 **0**）——前端那半是新建子系统，不是一枚 diff。
   按「80% 投功能」我打算先开工两枚写门 + 门上测试，前端另立一刀；等他定优先级。

## 9. Amap 两条腿（B 地点发现 / C 路线）接上后的现读数（2026-10-26）

这两腿是同一枚产品提交 `0214d16706`（14 文件 / +2418 / −80，`git show --stat 0214d16706` 现读）。
B 此前只有「收集线索」的库、没有门，所以界面永远看不见真实世界的店；现在有门、能落库、能被既有目录读回。
C 此前只有 adapter、运行时从不选它；现在融合运行时只在「中国城市 + 有 key + 没配 Valhalla」三件事同时成立时选它，
任何一条不成立都一个字不改旧行为。两条腿拒绝时都走 fail-closed：B 的未知域进 `unknown_fields`、不编坐标；
C 的 hard 捕获不落 mock 兜底。

| 尺 | 数（本趟现读） | 这一行钉住的是 |
|---|---|---|
| 自带测试 | **53 passed / 4.69s / RC=0**；逐文件 21 + 7 + 14 + 6 + 5 | 五枚文件一起跑绿，不是单跑绿 |
| B 发现 | `amap-web-service:ANSWERED:rows=5`；Photon `SKIPPED`；5 条线索 5 条有坐标 | 高德先答且答满 5 条；全球地理编码器根本没被问 |
| B 落库 | 持久化 **5** 行；`provider_key=amap-web-service`、存 `WGS84`、源 `GCJ02` | 坐标换到系统帧，来源帧没丢 |
| B 幂等 | 同一查询再发现一次：**5** 条，库仍 **5** 行 | provider item 就是身份，重复发现不添行 |
| B 读回 | `GET /api/v1/places?city_code=CN-TIANJIN&q=天津博物馆` ⇒ **3** 行（另 2 座馆名不含该子串） | 既有目录门不改一行就能看见新行 |
| C 活跑（hard） | `provider_key=amap-web-service`、`minutes=6`、`fact_quality=LIVE_PROVIDER_CAPTURE`、`time_basis=AMAP_ROUTE_CAPTURED_AT`、`mode=WALK`、几何 **19** 点、`degraded=False`、fallback **0** | 这几枚字段就是硬可行性闸读的那些；分钟数是服务当次回答（同一对点上趟读 5，不是常量） |
| C 供给面 | `/api/v1/providers/v9` ⇒ `status=READY`、`provenance=LIVE`、`coordinate_crs=GCJ02` | 前端状态角标读的就是这里 |
| 区域守卫 | `is_amap_region("CN-12-01")=False`、`("天津市")=True`、`("120000")=True`；门上 `422 AMAP_REGION_UNUSABLE`，测试断言 provider 构造次数 **0** | 2026-10-25 实测：`region=CN-12-01&citylimit=true` 仍 `status=1` 并答了山东 POI（adcode 370321）——它会静默答错省，不会拒 |
| 密钥面 | 新增行里真 key 出现 **0** 次；唯一 32 位十六进制是测试里的伪造 `0123…`；`backend/.env` 在 `.gitignore:14`，未暂存 | 「不把 key 写进树」是扫出来的，不是承诺 |
| 一键复跑 | `python review/ord0701/amap_legs_proof_r1.py` ⇒ `ORD0701_PROOF=PASS` / RC=0 | 本表 B/C 两段数就是这条命令的 stdout（要进程环境里有 key，脚本只打印前三字符） |

**别当成已完成（这段是给明天手机演示看的）**：

1. **B 门还没有前端调用者**：`places/discover` 在 `frontend/src` 命中 **0**；建行程仍走
   `GET /api/v1/places?city_code=`（`frontend/src/app/V8Experience.tsx:1202-1206`），真实城目录空时停在那条 early return。
   要让老师/学生在手机上看见「高德把真实博物馆拉进来」，还需要一次 UI 接缝；本轮没接。
2. **C 的证明是脚本直调产品函数**，不是 HTTP 门。旅行者可见的 plan/replan 路径本轮没在 390×844 上点过；
   这枚证明的是「引擎真供给、闸门真读它」，不是「屏上已经显示高德分钟数」。
3. **契约面 0 命中**：`contracts/openapi.yaml` 与 `frontend/src/generated/api.ts` 都没有这扇门，
   生成客户端不认识 `POST /api/v1/places/discover`；要进契约得另开一刀（与切片 4 的契约刀同一处）。
4. **融合树仍有两枚文件预存红**：`tests/test_qoder_live_replans_endpoint.py` + `tests/test_qoder_mobility_evidence_sources.py`
   ⇒ **5 failed / 7 errors**（本轮复跑 7.64s，同数），来源是 demo-stage 的 `409 DEMO_START_REFUSED`；
   此前用单变量 A/B（把 `runtime.py` 暂存起来再跑同两枚文件）证明与这两腿无关。
5. **演示树是另一棵树**：`D:/moodle/CityNexus`（CNX-DEMO 布景）不在本枝上。明天下午若跑的是那棵，
   这两腿不会出现；要出现只有两条路：把本枝合过去，或在融合树上演示。演示前必须先拍板，否则台上会演成「进步看不见」。
6. **§0 那一格「远端：没推」在本节推送之后作废**：本节与 `review/ord0701/amap_legs_proof_r1.py` 一起推上
   `origin/fusion/qoder-import-20261014`（不 force、未开 PR；开 PR 需号令者另点头）。远端尖与本地是否同 sha
   用 `git ls-remote --heads origin fusion/qoder-import-20261014` 与 `git rev-parse HEAD` 现读，下一枚 docs 提交会把 sha 钉回 §0。

