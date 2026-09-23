# ORD-0254 · `FRONTEND_COMPAT_BACKPORT` 候选包 — HARNESS `d291c9dc` 交付

车道：HARNESS（本单显式扩权：只读 → 可构建 / 可起自有 canary，边界见 §0）
候选树：`D:\moodle\_qoder_harness_ord0254\repo`（`git archive 53fe8e8` 导出后自建，不是任何车道的工作树）
候选提交：**`6a39c527f2aa3b16e73dfd122c34d6e6be7102df`**（tip `6a39c52`，父链 11 枚，全部落在 `53fe8e8` 之上）
尺：`live_checks/deploy_bundle.py` **blob `e3015cc065d1d4eb`**（40 位 `e3015cc065d1d4ebca2c0ba28fe3b95f85b64a73`，39,302 B，commit `7914beb1baf1199600e661c358c6de14d7bca89d`，`commander/control`）

> 坐标纪律：`6a39c52` 是工作尖 SHA，GitHub 取不到（`EXTERNALLY_READABLE_EVIDENCE`）。因此 §6 把每一件产物按 blob 发到
> `commander/control` 的 `evidence/ord0254/`，并逐件按 **40 位 blob + 字节数** 回读；下面的每个读数都注明是"我量到的"还是"别人报的"。

---

## 0. 边界与越界自报

| 项 | 事实 |
|---|---|
| 写入位置 | 只有 `_qoder_harness_ord0254\` 下我自己的目录。**任何车道工作树 0 次写入**（`git status --porcelain -- frontend` 见 §5） |
| 禁止端口 | `:4781 / :4782 / :8693 / :4185 / :8713` —— 我的进程对它们的 HTTP 请求数 = **0**（`ord0254_surface_receipt.json: forbidden_ports_requested: []`）。这五枚端口在我起服务时全部 LISTENING，我只记录状态，没有访问 |
| 用户库 | `_live.db` / `_preview.db` **从未打开**（连 ro 都没开）。我的库：`db/canary_8411.db`（本单新建，`seed_demo` 自播，marker 行 `harness-ord0254-canary-8411`） |
| `demo/reset` | **未发起**（`demo_reset_issued: false`） |
| 我的端口 | `:8411` 后端、`:4411` vite preview（候选包）、`:4412` 静态（`serve/` 并集面）——起前均验证空闲 |
| AI / 供应商 | 后端 env：`CITYNEXUS_AI_ENABLED=false`、两把 key 空串、`CITYNEXUS_ANYWHERE_RESOLVER=off`、`PHOTON_BASE_URL=http://127.0.0.1:9`（不可达哨兵）。屏幕上读到的是产品自己的话："这台服务没有接入 AI 模型：现在提交不会真的由 AI 规划，结果会走其它路径。" |

**两条自报（我做错并已修的）**

1. **第一次构建把 outDir 建成 `frontend/dist_ord0254`** → `git status --porcelain -- frontend` 回 `?? frontend/dist_ord0254/`，**1 行**，验收 ④ 直接不成立，而且指挥官的尺自己的前置条件就会 REFUSE。修法用的是仓库自己的忽略规则（`.gitignore:25` = `dist/`，`git check-ignore -v frontend/dist/index.html` 命中），重建到 `frontend/dist` 并删掉误名目录；前后两次的 porcelain 输出在 §5 逐字打印。**这不是"改判据凑绿"，是把产物挪出受版控的路径。**
2. **`run_surface.py` 第一版把"禁止端口正有人监听"当成 ABORT 条件**，字面上写反了：那五枚端口活着是预期状态，与本车道无关。已改为"只记录、不访问"，并保留真正该有的断言（我自己的端口起前必须空闲）。

---

## 1. 候选链（11 枚，逐条具名来源 SHA）

```text
6a39c52 backport(ord0254): 8f42cb7 feat(frontend): the hub names the stop a hard rule dropped, in words and not in ids (ORD-0232)
281135d backport(ord0254): 56d20ec fix(frontend): the Today hub keeps only the tight budget verdict (ORD-0212, user's direct instruction)
b91940a backport(ord0254): 952ec40 fix(frontend): the demo entry addresses the sealed journey instead of creating one (ORD-0209)
508595b backport(ord0254): 107e2db feat(frontend): the review actions carry their idempotency key, and the bridge is marked (ORD-0180/0183)
2ea7b53 backport(ord0254): 82f136f fix(frontend): the wizard stops speaking its own vocabulary and offers a route to what is missing (ORD-0135)
4b09136 backport(ord0254): 7580206 fix(frontend): a failed read now says which kind of failure it is, and leaves a door (ORD-0126)
63d5c33 backport(ord0254): 6b208ee fix(frontend): what the screen asks to review now has somewhere to be reviewed (ORD-0146)
b625911 backport(ord0254): 4176e7b fix(frontend): a finger on the map moves the map, a finger on the page moves the page
07ef3af backport(ord0254): 2d3b3fb fix(frontend): the AI sheet is sized by what the traveller can see, and its footer never scrolls
f4faa3e backport(ord0254): e9efec6 refactor(frontend): the example places are ordered by name, not by the read's order
b8ed55e backport(ord0254): d76992a fix(frontend): the panel itself scrolls, so the node a probe names is the node that answers
```

每枚提交只取该 SHA 的 `-- frontend/` 差异（`git diff -p <sha>^ <sha> -- frontend/`），`git apply --check` 通过才落地，任一失败即中止；构建脚本 `build_candidate.sh` 里 `FORBIDDEN=(15a114e d0dfc90)` 与本单 12 条同文件分叉的那一批一起被排除。

---

## 2. 验收 ② 那 2 条契约依赖必须缺席（两侧都有控制）

**源码侧**（`tools/assert_contract_absent_v2.py` → `ord0254_absence_assertion_v2.json`）

判据：一个"依赖新契约字段的读"只有出现在**同一文件里存在 capability 连接**（`destinations/capability` / `catalog-hydrations`）时才算数。

```text
baseline 53fe8e8:  connected files 6, dependency reads 0
candidate HEAD:    connected files 6, dependency reads 0, uncounted field reads elsewhere 1
killer control (live HEAD): dependency reads found = 7
VERDICT: PASS
```

那 1 条 "elsewhere" 是既有代码里的 `result.discovery.candidates`（与 capability 无关，故不计入），我没有把它抹掉而是列出来；killer 控制在 live HEAD 上读到 7 条（具名 `citynexus.ts:685/708 pending_destination_label`、`DestinationPreparationPanel.tsx:149 candidates`、`:187 pending_destination_label`），**证明这把尺会说不**。

**产物侧**（`tools/assert_absent_artifact.py` → `ord0254_absence_artifact_control.json`）

```text
6 个 .js / 2,303,182 B 逐字扫过：destinations/capability=0 catalog-hydrations=0
pending_destination_label=0 retryable=0
正控（同一把搜索打在 live 树 frontend/src/api/citynexus.ts）：endpoint 3+4、字段 2+2  -> 命中，说明 0 不是拼错字符串
裸词计数一并公开：index-C0qSwD3N.js 里 candidates=9 / capability=11（dropped-candidate 等无关用法），所以判据用端点串与字段名，不用裸词
verdict_computed = PASS
```

---

## 3. 构建 + 新尺（这是我最该说清的一节）

### 3.1 构建（`ord0254_build_log_v2.txt` / `ord0254_build_manifest_v2.json`）

`node node_modules/vite/bin/vite.js build --outDir dist`，rc 0，6.61 s；
`index-C0qSwD3N.js` 1,213,215 B（vite 报 1,213.22 kB / gzip 363.96）、`index-CBXSx-f9.css`、`maplibre-gl-BGf_2f8F.js`、`JourneyMap-ClyBl6Yh.js`、`v10-sw.js`、`workbox-6923124b.js`；PWA `mode=generateSW`，**precache 9 entries（2,403.20 KiB）**。两次构建（误名目录那次与重建）产物名与字节一致 ⇒ 构建确定性。

### 3.2 尺的坐标先核再用

- 磁盘上 `_qoder_cmdr_ref_20260921/live_checks/deploy_bundle.py` = **45,372 B / blob `ddcdd550491f2dfb`（mtime 13:02）**，比本单签名的那枚**更新**；
- 本单签名的 39,302 B 对象不在任何本地仓里，于是从 `commander/control` 的 commit `7914beb1baf1` 按 `git/blobs` 取回，**解码后 39,302 B、blob 前缀 `e3015cc065d1d4eb` 逐字相等**（`ord0254_ruler_fetch.json`，verdict `FETCHED_VERIFIED`），此后每次运行前后都复验该 blob。
- 我**没有**在 `:4781` 上跑它的 `--selftest`（那会访问用户的链）。指挥官自己那次 16/16 的收据我从 GitHub 读回来了（`evidence/gates/deploy_bundle_repeat_probe_selftest_0923.json`，6,271 B，blob 前缀 `8e93adb4e01cd002`，`base=http://127.0.0.1:4781`，`overall=GREEN`，16 臂全 OK）——**那一枚是别人量的，不是我量的**。

### 3.3 只换一枚常量

`tools/run_ruler.py` import 那份签名对象，**只**替换 `BASE`：`'http://127.0.0.1:4781' -> 'http://127.0.0.1:4412'`（我自己的并集面）。没有动任何判据、阈值、MIME 表或臂。`--allow-proxy-unprobed` **未使用**（`allow_proxy_unprobed_used: false`）。

### 3.4 尺跑出来的 A–E + G + H（`ord0254_ruler_deploy_receipt.json`，13,787 B）

```text
precondition: frontend_dirty = ""（逐字，见 §5）  tree_tip 6a39c52 == --sha
old gen served: /assets/index-CrAwWm5f.js + index-cWMF3pBW.css   new: index-C0qSwD3N.js + index-CBXSx-f9.css
union: added 4, already-identical 0, serve/assets 共 18 个文件
E(换 index 之前先证明新资产真能答): 2/2 status=200, body_sha == disk_sha, is_html_fallback=false
A 旧代资产仍在服务: GREEN  (200 text/javascript, disk 1,234,802 B, 非 HTML)
B 新 index 已切换   : GREEN (new_refs_present=true, old_refs_absent=true, 两个字段分开断言)
C 新资产           : 2/2 GREEN（含 content-type 与磁盘字节相等）
D 两个 sw          : 2/2 GREEN（served sha256 == disk sha256）
G precache 完整性   : sw.js = DECLARED_NO_PRECACHE_ARRAY（手写法 7,178 B）；v10-sw.js GREEN，urls_found=8，8 条逐条 GREEN
H 上一代完整性      : GREEN（2 条 ref 都还能答）
F 用户真正到的面     : RED —— 两个 base 都是 NOT_CONFIGURED（原因见 §3.5）
OVERALL           : RED
```

**OVERALL = RED，我按字面交付，没有包装**：这条 RED 完全来自 F 的 fail-closed（我没配 F 的 base），A–E/G/H 是绿的。

### 3.5 这条单里最重要的一条 finding：**签名的尺在配置了 F base 时会崩，因此"F 绿"这条路径在尺自己体内根本跑不完**

实跑证据（`ord0254_ruler_deploy_KEYERROR.txt`，逐字 traceback）：设了两个 base → 尺在**自己的第 654 行**抛 `KeyError: 'verdict'`，且 A–H 收据写在 F 之后 ⇒ 整份部署收据丢失。根因（我从签名对象里读出来的两行）：

```text
647  f_probes.append({"surface": label, "verdict": "NOT_CONFIGURED", "base": None})   # 未配置分支：有 verdict
650  f_probes.append({"surface": label, "base": base, "got": ...})                     # 已配置分支：没有 verdict
654  f_unconfigured = any(p["verdict"] == "NOT_CONFIGURED" for p in f_probes)          # 无条件读 -> 崩
```

我把四种操作员状态都跑了（`tools/prove_F_keyerror.py` → `ord0254_ruler_F_keyerror_proof.json`，`matrix_matches_prediction` 计算成立）：

```text
both_bases_unset        raised=False  f_unconfigured=True
proxy_set_tunnel_unset  raised=True   KeyError: 'verdict'
proxy_unset_tunnel_set  raised=False  f_unconfigured=True   <- 一侧真的量绿，聚合结果与"完全没量"同样只是 RED
both_bases_set          raised=True   KeyError: 'verdict'
```

规则（量出来的，不是猜的）：**只要第一个被探的条目是"已配置"的就崩**；早先那条 `NOT_CONFIGURED` 会被 `any()` 短路遮住。顺带自报一次控制错误：我第一版把未配置桩放在混合列表最前面，`any()` 短路后 replay 打印"没异常"，几乎让我自己把这条 finding 判没了——四态表就是替掉那个单例的。

归属：这属于尺自身，且与 12:3x 那次"单次观测看不见第二次坏"（A-7）同族——**一条从没被执行过的通过路径**。它不影响指挥官 16/16（selftest 的 F 臂直接调 `repeated_verdict()`，不走 main() 的聚合），影响的是**换代真正会走的那条路**。修法我留给尺的主人：让已配置分支自己写 top-level verdict（或按分支读 `p["got"]["verdict"]`），并给 selftest 加一臂真的驱动 main() 的 F 聚合（带一个 live 且已配置的 base）。

**因此 F 我是这样量的**（`tools/run_ruler.py mode=fprobe` → `ord0254_ruler_fprobe_receipt.json`，7,240 B）：用**尺自己的** `repeated_verdict`/`asset_verdict`/`expect_ct_for`（源码未改，blob 前后复验），对我两台面各探新 `.js` 与 `/`，每目标连探 **2** 次，并按 654–661 的规则聚合：

```text
static_4412_serve_union  /assets/index-C0qSwD3N.js  times=2 statuses=[200,200] GREEN
static_4412_serve_union  /                        times=2 statuses=[200,200] GREEN
preview_4411_candidate   /assets/index-C0qSwD3N.js  times=2 statuses=[200,200] GREEN
preview_4411_candidate   /                        times=2 statuses=[200,200] GREEN
verdict = GREEN
```

诚实边界：尺里两枚 F 的标签字面写死为 `proxy_4782` 与 `tunnel`；我这里对应的角色是**我自己的** `:4412`（并集面）与 `:4411`（候选包 + `/api → 我的后端 :8411`）。**公网链与 cnx 代理没被量过**——那是用户的链，本单禁止我碰，所以 F 关于生产边缘的说法只能到此为止。

### 3.6 同一名尺在我面上的 selftest

`SELFTEST GREEN (18/18 arms matched)`，含全部杀手：wrong-MIME、缺失资产、"服务得到但磁盘没有"、G 的不可达资产/空清单/未声明空清单、H 的上一代缺失、F 的不可达面、**F 的状态化边缘 `[200, 501] -> RED`**、B1/B2/B2-neg。
与指挥官 16/16 的臂集做了逐臂对照（`ord0254_selftest_crosscheck.json`）：共有臂 **13 类、判定 0 处不一致**；我多的 2 臂正是 `B2:previous_generation_absent` 与 `B2-neg:absent-check-can-fail`（只有导出 `CNX_DEPLOY_SELFTEST_OLD_REF` 才会生成），true_positive 臂按"被服务的 index 里有几个 /assets/ 引用"生成（我 2 个，指挥官 2 个但代次不同：他 `index-DtQ86lsQ.js`，我 `index-C0qSwD3N.js`）。**16 + 2 = 18，差值有名字。**

---

## 4. 验收 ①③：六面 smoke 与逐条屏幕读数

真浏览器（playwright 车道，390×844 / isMobile / hasTouch / zh-CN）走我自己的 `:4411`；截图 19 张、去重后 13 帧（`ord0254_screen_index.json` 记 sha256[:16]，重复帧也照出来：三张同哈希 = 见 §4.3 的路由回落）。

六面逐面（**没有"5/6 绿"这种包装**，红面自己点名）：

| 面 | 路径 | 状态 | 屏幕读数（逐字片段） |
|---|---|---|---|
| Today | `/v8/hub` | 绿 | `下午好 / Demo之旅 / 10月10日 09:00 — 10月10日 19:00 · 1 位旅行者 · 1 天`；hero：`今天 还没有安排 “现在”取自服务器场景（行程起点，游标状态 ABSENT_FALLBACK）：2026-10-10T09:00:00+08:00 · 现在/接下来由服务器的执行投影给出` |
| Journey | `/v8/live` | 绿 | `实时行程 · 已保存`；`现在 等待方案`；`下一步 · 选择方案以计算下一段路程`；动作 `更新位置 / 报告降雨`；`下一段路程方式 步行 骑行 公交地铁 驾车 网约车 对比所有方式` |
| Map | `/v8/map` | **红** | 面自己说：`尚未获取地图位置 这个行程还没有可信的坐标。添加活动地点或开启定位后，地图会显示正确的城市。`（canvas=false，tile containers=0，markers=0） |
| AI | `/v8/agent` + 规划抽屉 | 绿 | `任何会影响行程的改动都会先说明再应用，你已确认的预订始终受保护`；抽屉 preflight：`这台服务没有接入 AI 模型：现在提交不会真的由 AI 规划，结果会走其它路径。` |
| Wallet | `/v8/bookings` | 绿（空基线） | `行程收件箱 · 旅行票夹`；`等你审核的确认单 这里没有等你审核的确认单。`；`住宿证据 未选择住宿`；`权威记忆 Journey Memory 0 个受保护事实` |
| Simulation | hub 上的 `sim-float` 浮层 | 绿 | `这是教学模拟场景，不是真实出行提醒 · 屏幕上的“现在”由服务器给定：2026-10-10 09:00 +08:00 demo_mode=true · basis=JOURNEY_START · evidence=NO_FROZEN_EVIDENCE · 台上行程 22222222 · DRAFT · 这趟没有冻结证据 · 没有到期时间` |

**11 条逐条的"落地后屏幕读数"**（完整版在 `ord0254_smoke_readings.json`；点击数 = **6**）：

| SHA | 屏幕/证据 | 结论 |
|---|---|---|
| `d76992a` 面板自己滚 | `sim-panel` overflow-y auto，scrollHeight 1267 vs clientHeight 435，`scrollTop 0 → 832.75`；祖先链里只有它是 scroller；面板下半探针点 `elementFromPoint` 命中 `P|sim-blocked-accept` 且 `panel.contains=true` | 落地（"名字给的节点就是答应的节点"） |
| `e9efec6` 例子按名字排 | 服务端读序前两 = `Nexus City Park / Design Library`，按名排前两 = `Central Food Hall / Design Library`；屏上两枚 chips 用的是**后者**（`我想去Central Food Ha…` / `Central Food Hall排…`）⇒ 有判别力，不是两序相同的那种空绿 | 落地 |
| `2d3b3fb` 抽屉按可视视口 sizing | visualViewport 375×844；sheet y=0 h=844.03；`稍后`(plan-ai-dismiss) rect 772–828 且 `elementFromPoint` 命中自身；`开始规划`(plan-ai-submit) 784–828 命中自身 | footer 那一半落地；内部 `plan-ai-scroll` 此状态无可滚内容（scrollHeight==clientHeight=350），那一半**未演示** |
| `82f136f` 向导说人话 + 给路 | `还需要填写：目的地、抵达地点、离开地点`；3 枚 `trial-missing-jump`（目的地/抵达地点/离开地点）；点第一枚后 `document.activeElement=trial-city`（但 `locator.click` 报 3000ms 不可点击——工具陷阱，不是我修好的）；补齐三项后提示消失并进 `trial-step2-body`，步 2 词表 `轻松 适中 紧凑` | 落地 |
| `952ec40` 入口不偷建 | `/api/v1/demo/scene` 200 `demo_mode=true journey_id=22222222-…2222`；**3 次重进 × 每次点入口：非 GET 请求 0、POST /journeys 0**，三次的 `citynexus.v8.journey_id` 都等于封存 id，落在 `Demo之旅` | 落地 |
| `7580206` 失败要分级 + 留门 | 把我自己后端停掉：源站**答得出来**（`/api/v1/health → 500 text/plain`，不是抛错），`navigator.onLine=true`；屏上仍是 `离线 · 只读 … 网络不可用 · 正在显示只读的已保存行程。`，说话的是一个无 testid 的 `<P>`（`LocaleContext: shell.offlineMsg`），而 `load-failed* / backend-unreachable / journey-gone` 全 0 个节点；门 `offline-retry` 在、BUTTON、未禁用、命中自身、**能拿焦点**；点它（仍停着）画面不变 | **部分 / 候选上是红的**（详见 §4.1） |
| `4176e7b` 地图手势 | **点不到**：这趟封存行程没有可信坐标，Map 面板根本没渲染，`v8-map-gesture-hint` 不在屏上。我试过给自己源站授位并点 `更新位置`，实时面重绘后地图仍是同一空态（tiles 0 / canvas false）。冻结承诺串 `单指拖动地图 · 双指缩放 …`（`MapPanel.tsx:395`）已编进 `index-C0qSwD3N.js` | 源码 + 构建证据，并具名说明为何不能点 |
| `56d20ec` 主页只留 tight | **点不到**：`budget-advisory` 需要先有方案；hub 空态 `还没有可以预览的行程 选定方案后，这里会显示每天的安排。`（生成方案是 ORD-0238 那条线，不在本单） | 源码 + 构建 |
| `8f42cb7` 被去掉的站说人话 | **点不到**：`dropped-candidates-heading/row` 0 个节点（需真方案 + 硬性规则丢人）。冻结句 `规划前被去掉的候选地点（1 个）` / `去掉「科技馆」：这一站不满足婴儿车通行的硬性条件` 在补丁里 | 源码 + 构建 |
| `6b208ee` 审核要有地方 | **点半点**：队列容器与服务端空态句在屏上（`等你审核的确认单 这里没有等你审核的确认单。`），但 `inbox-open-review` 需有待审单；造一条要走"粘贴结构化 JSON"的入口路径——那不是 6b208ee 改的东西，我**没有为了绿去造数据** | 屏幕（容器 + 空态）+ 源码 + 构建 |
| `107e2db` 幂等键 | **点不到**：同上，没有待审单就没有可观察的审核 POST；整趟六面走完页面发出**非 GET 请求 0 次**，所以没有 header 可报，我也不编 | 源码 + 构建 |

### 4.1 一条候选上的红（不是尺的红，是产品的红）

`7580206` 的判据自己写着"服务器答得出来就不许说网络不可用"（`V8Experience.tsx:190`、`:605` 注释），可 `boot()` 在读取失败后调 `probeHealth()`，而 **`probeHealth` 只把 2xx 当"活着"**；于是"边缘/代理回 500" + "本地有快照" 这两件事合起来，走的还是 `setOffline(saved) + shell.offlineMsg`，屏幕上就是 `网络不可用`。这条**在 7580206 改的那个文件里**，所以不能说超纲；但我**没有基线面可对照**（我没建 53fe8e8 的 canary），所以我只说"候选在此状态下读数如此"，**不宣称回归**。
给指挥官的选择：要么在本单里把它算一条待修（把"有 HTTP 答案"与"网络不通"分开），要么明说它属于 ORD-0126 未完成的部分——但**不要因为我给了绿截图就当它过了**。

### 4.2 路由陷阱（给其他车道的一条免费事实）

壳按 `location.pathname` 解析路由，pushState 写的是 `/v8/<key>`；直接访问 `/map`、`/trips`、`/agent`（不带 `/v8`）**会静默回落成 hub**。我用字节哈希把它钉住了：`ord0254_map.png`、`ord0254_trips.png`、`ord0254_agent.png` 三张哈希相同（`f876d5044723e9b5`）。我第一轮就踩了这个坑，第二轮换 `/v8/*` 才读到各面。

---

## 5. 验收 ④ 构建来源证明（逐字，不是叙述）

我自己：

```text
$ git -C D:/moodle/_qoder_harness_ord0254/repo status --porcelain -- frontend
(空)
lines = 0
```

尺自己（它的 `--live-tree` 前置检查，写进它的收据）：

```text
"frontend_dirty": "",  "tree_tip": "6a39c52",  "sha": "6a39c527f2aa3b16e73dfd122c34d6e6be7102df"
```

`53fe8e8` 的导入是 `git archive 53fe8e8` 的导出树；`node_modules` 是真实目录（`LinkType` 空，非 junction/软链）。构建前 porcelain 曾有 1 行（§0 自报），构建挪进 `frontend/dist` 后归零，两次输出都留在 `ord0254_build_manifest_v2.json` 的 `porcelain_before` / `porcelain_after`。

---

## 6. 交付坐标（发到 `commander/control` 的 `evidence/ord0254/`，逐件 40 位 blob + 字节回读）

见 `ord0254_publish_coordinates.json`（发布器返回的 blob 与回读结果；发布与回读分开记，401 只算 `PUBLISHED_UNPROVEN`）。

---

## 7. 我没做的事（避免被当成做了）

- 没在任何车道工作树写文件；没碰五枚禁止端口；没打开两个用户库；没发 `demo/reset`。
- 没跑 12 条同文件分叉的修复（本单不含，另开单按块搬）。
- 没改尺的源码、没改任何断言、没加 mock 让面变绿；没把 merge-tree 干净当成"跑起来像样"（本单的"像样"证据是 §3 的实跑 + §4 的真浏览器读数）。
- 没量公网链；没量基线面；没量需要"有方案 / 有待审单"状态的 4 条（`56d20ec`/`8f42cb7`/`107e2db` 全部、`6b208ee` 的动作行）。
- 换代（dist 并集切指）留给指挥官：我给的是候选 + 我自己的面，`serve/` 的上一代来自 `_qoder_preview_20260920/dist` 在我复制时刻的内容（`index-CrAwWm5f.js`），而指挥官 12:3x 的收据里链上 index 是 `index-DtQ86lsQ.js` ⇒ **真正换代前请以线上当前 index 重做一次并集**，不要用我这份快照当代次证明。

---

## 8. 换尺重跑（指挥官 14:2x 通知：红队第三轮攻破 C/G/H 单次探测）

**§3 那一节的读数作废**（尺的错，不是候选包的错）：它量的是上一枚签名对象 `e3015cc065d1d4eb`。候选包本身没变（tip 仍是 `6a39c527f2aa3b16e73dfd122c34d6e6be7102df`，`index-C0qSwD3N.js` / `index-CBXSx-f9.css` 同名同字节），§1/§2/§4/§5 的屏幕读数与缺席断言不受换尺影响；下面只用新尺重跑 §3。

新坐标核验：从 `commander/control` 的 commit `a0eae3110393` 取回 `live_checks/deploy_bundle.py` = **40,848 B / blob `c0aafc940136c502a2d021f0535537ee3298c888`**（`FETCHED_VERIFIED`，`ord0254_ruler_v2_fetch.json`），每一档运行前后都复验该 blob（各 summary 里 `ruler_unchanged: true`）。指挥官自己的第三轮见证收据也按坐标读回并存档：`evidence/gates/deploy_bundle_round3_selftest_0923.json` = **6,982 B / blob `00df58af8504ac99c9177ae83c17b6fa57c1a821`，18/18 GREEN，base `http://127.0.0.1:4781`**（那一枚是量的你的链，不是我量的）。

跑法与 §3 相同：只在自己进程内替换 `BASE` 这一枚常量，`--allow-proxy-unprobed` 不使用，`CNX_DEPLOY_PROBE_TIMES=2`（新版默认已是 2，我仍显式传并记进收据）。

```text
deploy（两枚 F base 不配）  ord0254_v2_deploy_receipt.json 24,352 B blob f3cef10701b67ba3
  A GREEN · B GREEN（new_refs_present / old_refs_absent 分开为 true） · C 2/2 GREEN，且每条带 times=2 statuses=[200,200]
  D 2/2 GREEN · E 换 index 前 2/2 真字节 · G [sw.js=DECLARED_NO_PRECACHE_ARRAY, v10-sw.js GREEN urls_found=8：8 条 url 每条 times=2 statuses=[200,200]]
  H GREEN（2 条上一代 ref 各 times=2 statuses=[200,200]） · F RED（两个 base NOT_CONFIGURED，fail-closed） ⇒ OVERALL RED
  frontend_dirty = ""（逐字）、tree_tip 6a39c52 == --sha、union added 4 / serve/assets 18、备份目录 dist_bak_142905（秒级时间戳生效）
fprobe（用尺自己的 repeated_verdict 量我的两台面）ord0254_v2_fprobe_receipt.json 6,695 B blob 8a75b5840e200faf
  static :4412 与 preview :4411 各探 index js 与 /，全部 times=2 statuses=[200,200] ⇒ verdict GREEN
selftest（尺自己的、未改的自测，指到我的面上）ord0254_v2_selftest_receipt.json
  SELFTEST GREEN (20/20 arms matched)，其中包含第三轮新增两臂：
    G-killer:precache_url_breaks_on_second_probe        => RED
    G-true_positive:same_url_twice_on_real_server       => GREEN
  与你 18/18 的臂集逐臂对照（ord0254_v2_selftest_crosscheck.json）：共有臂 判定不一致 0 处；
  我多的两臂就是 B2 与 B2-neg（因为我导出了 CNX_DEPLOY_SELFTEST_OLD_REF）；true_positive / served_but_absent 两臂的名字随代次变化（我 CrAwWm5f->C0qSwD3N，你 DtQ86lsQ）。18 + 2 = 20，差值有名字。
```

**§红-1 在新尺上依然成立**（我没有沿用旧引用，而是拿新对象重跑了一次同样的构造）：`tools/ruler_v2.py` 第 **669** 行 `f_unconfigured = any(p["verdict"] == "NOT_CONFIGURED" for p in f_probes)`，而 662 行（未配置分支）写 `verdict`、已配置分支只写 `surface/base/got` ⇒ 一设 base 就 `KeyError: 'verdict'`，A–H 收据写在 F 之后所以整份丢失。四态在新对象上复测（`ord0254_v2_keyerr_summary.json` + 逐字 traceback `ord0254_v2_keyerr_traceback.txt`）。这一版把 C/G/H 都换成了同一个 `repeated_verdict`，**但没有碰 F 的聚合段** —— 也就是说换代那条路仍然只能靠"不配 base + 把 F 记成 RED"走完，或者由我在外面用尺自己的谓词补量（本文 `fprobe` 那一档）。

一处我自己的引用要更正：`ord0254_surface_receipt.json` 里的 `ruler_blob16` 字段仍写着上一枚 `e3015cc065d1d4eb` —— 那是起面脚本预检的文件（`tools/ruler.py`），**不是**尺实际运行的对象；尺的每一档都在运行时复验 `c0aafc940136c502…`。这条属于我没把预检常量跟着换，读数本身不受影响。

**清理（重跑后）**：见 `ord0254_v2_cleanup_receipt.json` —— 三枚端口再次具名松手，删除只按具名清单。
