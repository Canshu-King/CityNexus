# ORD-0509 续 · 线上余下 tertiary 墨色的全路由普查（只读，0 枚产品字节）

代次：账本尖现读 `45207a0cc0fcae000b619753b4dfccb06594a59f`（`git ls-remote --refs origin refs/heads/mirror/integration-frontend-apple-pass1` 现取），本件的普查就在这枚尖上：检出、`tsc --noEmit` 通过、`vite build` 产物入口 `http://127.0.0.1:4892/assets/index-iZ6I1MKH.js`（1623095 字节，服务字节 sha1 与磁盘字节 sha1 相同 `c1b65cc2c9bb8b4c59b554c6181b51eddb1e19fa`），私有栈 api pid 99580 / static pid 108524，库 `_r5_ink45207a0c.db`，静态口代理目标 CITYNEXUS_BACKEND_PORT=4891。

## 一、仪表（这一手的交付物其实是这把尺）

| 仪表 | 作用 | 本机字节 sha1 |
| --- | --- | --- |
| `map_ink_r1.py` | 从尖上的树再生分母：逐枚找 `color: … --cn-ink-tertiary`，回溯所属规则的选择器，逗号组拆成逐枚可查的选择器 | `366e9855953b37f353ef9ec182a6b59acc97eca2` |
| `sweep_ink_r1.cjs` | 路由 × 档 × 形真机屏读：取计算色、背后第一枚不透明底、字号字重、WCAG 比值 | `4f20f9f3bdf4aed68370c7e405a2963e61257380` |
| `compare_maps_r1.py` | 同一把尺在两代尖上的分母差 | `cf5ce26885ecc6fd4b75b20246ba67f1d52473f8` |
| `sum_sweep_r2.py` | 汇总：可达 / 真文字 / 低于阈值 / 具名缺口，拒收任何未落屏的扫描 | `cf88c06593aba9e70d3ec1cf8ed533ac01dcc080` |
| `chain_sweep3.sh` | 把上面四件串成一趟，尖号从 ls-remote 现取 | `104f8dbae258ba06ff7d417123ee06e52fa12928` |

分母核对：我 02:02 那次普查（`ink_survey_map.json`，尖 `4fdd6345c0bfef36f12468390baad50946aad2b6`，30 行）与这把新尺在同一棵树上找到的是**同一批 30 枚声明**（按 文件+声明行 比对，两边各 30 枚，交集 30 枚，两边都没有独有项）；新尺多出来的 11 枚是把一条规则逗号组里的每一枚选择器都各自去屏上查一次（旧尺只取最靠近声明的那一枚），所以新尺是 41 枚选择器 / 30 枚声明 / 13 枚文件。

分母还说出它排除了什么：`frontend/src` 里 `--cn-ink-tertiary` 被引用 36 次，其中 6 次不是 `color:` 声明（它们是边框/分隔线一类的用法，本普查不测，测了就是拿对比度尺去量非文字）；另有 1 枚样式表外的引用：`frontend/src/features/poster/posterCanvas.ts` 1 枚。

## 二、两代之间的分母移动（同一把尺）

基线尖 `4fdd6345c0bfef36f12468390baad50946aad2b6`（上一轮我落「乙」之后号令者收的那一代）对现读尖 `45207a0cc0fcae000b619753b4dfccb06594a59f`：选择器 41 枚对 41 枚，共享 41 枚，其中行号未漂移 40 枚、漂移 1 枚；线上没有再动这批墨色声明。非声明引用：基线 6 枚 / 现读 6 枚。

## 三、屏读分母

路由 17 条：`/v8/hub`、`/v8/live`、`/v8/map`、`/v8/studio`、`/v8/stay`、`/v8/discover`、`/v8/import`、`/v8/bookings`、`/v8/footprints`、`/v8/agent`、`/v8/authoritative`、`/v8/intelligence`、`/v8/twin`、`/v8/trash`、`/v8/access`、`/v8/trips`、`/v8/me`。两档（light/dark）× 两形（1280 × 900 px 视口 与 390 × 844 px 视口）= 68 趟扫描，外壳挂载 68 趟，拒收 0 条；导航策略计数：`networkidle` 68 趟。演示门：`demo/reset` http_status=200、`prepare-scenario` http_status=200、`demo/scene` http_status=200，站点 6 段、其中无坐标 0 段；带错 token 的重置门回 http_status=403；分享授权回 http_status=201。

仪表自校准（这一条顶「读数不是空转」）：把屏上取到的计算色与该尖 `design-tokens.css` 里声明的 `--cn-ink-tertiary` 逐值比——亮档声明 `#86868b`、暗档声明 `#8e8e93`；屏上等于声明值的读数 亮档 10 枚 / 暗档 44 枚，不等于的 亮档 38 枚 / 暗档 4 枚。

## 四、结果分类

可达 7 枚 / 屏上有真文字 7 枚 / 至少一枚读数低于它该达到的阈值 5 枚 / 在我走的这些路径上没上过屏 34 枚。

| 选择器 | 类 | 文件 | 屏上次数 | 真文字读数 | 低于阈值 | 最低比值 | 最差那枚所在 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `.cn-access-trip-row` | PSEUDO_before | `features/access/access.css` | 4 | 4 | 2 | 3.33 | `/v8/access` light 档 390x844 形 |
| `.cn-live-toolbar .v8-quiet-button + .v8-quiet-button` | PSEUDO_before | `design-tokens.css` | 4 | 4 | 2 | 3.33 | `/v8/live` light 档 390x844 形 |
| `.cn-pending-details summary` | TEXT | `features/pending/pendingSet.css` | 4 | 4 | 2 | 3.62 | `/v8/hub` light 档 390x844 形 |
| `.cn-pending-empty-next` | TEXT | `features/pending/pendingSet.css` | 4 | 4 | 2 | 3.62 | `/v8/hub` light 档 390x844 形 |
| `.cn-pending-reads` | TEXT | `features/pending/pendingSet.css` | 4 | 4 | 2 | 3.62 | `/v8/hub` light 档 390x844 形 |
| `.v8-product-shell .v8-breadcrumb b` | TEXT | `design-tokens.css` | 68 | 68 | 0 | 无（没有低于阈值的读数） | 无（这一枚没有低于阈值的读数） |
| `.cn-now-next-hero .cn-hero-label` | TEXT | `design-tokens.css` | 8 | 8 | 0 | 无（没有低于阈值的读数） | 无（这一枚没有低于阈值的读数） |
| `.cn-collections__retry:disabled` | NOT_REACHED_ON_THE_PATHS_I_TOOK | `features/collections/collections.css` | 0 | 0 | 0 | 无（没有低于阈值的读数） | 无（这一枚没有低于阈值的读数） |
| `.cn-footprints__note--absent` | NOT_REACHED_ON_THE_PATHS_I_TOOK | `features/checkin/footprint.css` | 0 | 0 | 0 | 无（没有低于阈值的读数） | 无（这一枚没有低于阈值的读数） |
| `.cn-footprints__retry:disabled` | NOT_REACHED_ON_THE_PATHS_I_TOOK | `features/checkin/footprint.css` | 0 | 0 | 0 | 无（没有低于阈值的读数） | 无（这一枚没有低于阈值的读数） |
| `.cn-footprints__source` | NOT_REACHED_ON_THE_PATHS_I_TOOK | `features/checkin/footprint.css` | 0 | 0 | 0 | 无（没有低于阈值的读数） | 无（这一枚没有低于阈值的读数） |
| `.cn-footprints__when` | NOT_REACHED_ON_THE_PATHS_I_TOOK | `features/checkin/footprint.css` | 0 | 0 | 0 | 无（没有低于阈值的读数） | 无（这一枚没有低于阈值的读数） |
| `.cn-pending-batch-blocked` | NOT_REACHED_ON_THE_PATHS_I_TOOK | `features/pending/pendingSet.css` | 0 | 0 | 0 | 无（没有低于阈值的读数） | 无（这一枚没有低于阈值的读数） |
| `.cn-pending-batch-line` | NOT_REACHED_ON_THE_PATHS_I_TOOK | `features/pending/pendingSet.css` | 0 | 0 | 0 | 无（没有低于阈值的读数） | 无（这一枚没有低于阈值的读数） |
| `.cn-pending-chip-sub` | NOT_REACHED_ON_THE_PATHS_I_TOOK | `features/pending/pendingSet.css` | 0 | 0 | 0 | 无（没有低于阈值的读数） | 无（这一枚没有低于阈值的读数） |
| `.cn-pending-facts` | NOT_REACHED_ON_THE_PATHS_I_TOOK | `features/pending/pendingSet.css` | 0 | 0 | 0 | 无（没有低于阈值的读数） | 无（这一枚没有低于阈值的读数） |
| `.cn-pending-note` | NOT_REACHED_ON_THE_PATHS_I_TOOK | `features/pending/pendingSet.css` | 0 | 0 | 0 | 无（没有低于阈值的读数） | 无（这一枚没有低于阈值的读数） |
| `.cn-pending-row-cause` | NOT_REACHED_ON_THE_PATHS_I_TOOK | `features/pending/pendingSet.css` | 0 | 0 | 0 | 无（没有低于阈值的读数） | 无（这一枚没有低于阈值的读数） |
| `.cn-pending-row-meta` | NOT_REACHED_ON_THE_PATHS_I_TOOK | `features/pending/pendingSet.css` | 0 | 0 | 0 | 无（没有低于阈值的读数） | 无（这一枚没有低于阈值的读数） |
| `.cn-pending-rule` | NOT_REACHED_ON_THE_PATHS_I_TOOK | `features/pending/pendingSet.css` | 0 | 0 | 0 | 无（没有低于阈值的读数） | 无（这一枚没有低于阈值的读数） |
| `.cn-pending-token` | NOT_REACHED_ON_THE_PATHS_I_TOOK | `features/pending/pendingSet.css` | 0 | 0 | 0 | 无（没有低于阈值的读数） | 无（这一枚没有低于阈值的读数） |
| `.cn-poster-share:disabled` | NOT_REACHED_ON_THE_PATHS_I_TOOK | `features/poster/trip-poster.css` | 0 | 0 | 0 | 无（没有低于阈值的读数） | 无（这一枚没有低于阈值的读数） |
| `.cn-prep-survey-count` | NOT_REACHED_ON_THE_PATHS_I_TOOK | `features/discovery/prepAbandonSurvey.css` | 0 | 0 | 0 | 无（没有低于阈值的读数） | 无（这一枚没有低于阈值的读数） |
| `.cn-prep-survey-door` | NOT_REACHED_ON_THE_PATHS_I_TOOK | `features/discovery/prepAbandonSurvey.css` | 0 | 0 | 0 | 无（没有低于阈值的读数） | 无（这一枚没有低于阈值的读数） |
| `.cn-prep-survey-note-label` | NOT_REACHED_ON_THE_PATHS_I_TOOK | `features/discovery/prepAbandonSurvey.css` | 0 | 0 | 0 | 无（没有低于阈值的读数） | 无（这一枚没有低于阈值的读数） |
| `.cn-prep-survey-sub` | NOT_REACHED_ON_THE_PATHS_I_TOOK | `features/discovery/prepAbandonSurvey.css` | 0 | 0 | 0 | 无（没有低于阈值的读数） | 无（这一枚没有低于阈值的读数） |
| `.cn-prep-survey-where` | NOT_REACHED_ON_THE_PATHS_I_TOOK | `features/discovery/prepAbandonSurvey.css` | 0 | 0 | 0 | 无（没有低于阈值的读数） | 无（这一枚没有低于阈值的读数） |
| `.cn-pretrip-anchor` | NOT_REACHED_ON_THE_PATHS_I_TOOK | `features/checklist/pretripChecklist.css` | 0 | 0 | 0 | 无（没有低于阈值的读数） | 无（这一枚没有低于阈值的读数） |
| `.cn-pretrip-basis` | NOT_REACHED_ON_THE_PATHS_I_TOOK | `features/checklist/pretripChecklist.css` | 0 | 0 | 0 | 无（没有低于阈值的读数） | 无（这一枚没有低于阈值的读数） |
| `.cn-shared-code-label` | NOT_REACHED_ON_THE_PATHS_I_TOOK | `features/shared/sharedJourney.css` | 0 | 0 | 0 | 无（没有低于阈值的读数） | 无（这一枚没有低于阈值的读数） |
| `.cn-shared-details summary` | NOT_REACHED_ON_THE_PATHS_I_TOOK | `features/shared/sharedJourney.css` | 0 | 0 | 0 | 无（没有低于阈值的读数） | 无（这一枚没有低于阈值的读数） |
| `.cn-spend-line-strength` | NOT_REACHED_ON_THE_PATHS_I_TOOK | `features/trip/spend.css` | 0 | 0 | 0 | 无（没有低于阈值的读数） | 无（这一枚没有低于阈值的读数） |
| `.cn-stop-checkin:disabled` | NOT_REACHED_ON_THE_PATHS_I_TOOK | `features/checkin/footprint.css` | 0 | 0 | 0 | 无（没有低于阈值的读数） | 无（这一枚没有低于阈值的读数） |
| `.cn-trash-details summary` | NOT_REACHED_ON_THE_PATHS_I_TOOK | `features/trash/journeyTrash.css` | 0 | 0 | 0 | 无（没有低于阈值的读数） | 无（这一枚没有低于阈值的读数） |
| `.cn-trash-row-state` | NOT_REACHED_ON_THE_PATHS_I_TOOK | `features/trash/journeyTrash.css` | 0 | 0 | 0 | 无（没有低于阈值的读数） | 无（这一枚没有低于阈值的读数） |
| `.cn-trash-row-when` | NOT_REACHED_ON_THE_PATHS_I_TOOK | `features/trash/journeyTrash.css` | 0 | 0 | 0 | 无（没有低于阈值的读数） | 无（这一枚没有低于阈值的读数） |
| `.plan-ai-field textarea` | NOT_REACHED_ON_THE_PATHS_I_TOOK | `styles.css` | 0 | 0 | 0 | 无（没有低于阈值的读数） | 无（这一枚没有低于阈值的读数） |
| `.trial-field input` | NOT_REACHED_ON_THE_PATHS_I_TOOK | `design-tokens.css` | 0 | 0 | 0 | 无（没有低于阈值的读数） | 无（这一枚没有低于阈值的读数） |
| `.trial-field textarea` | NOT_REACHED_ON_THE_PATHS_I_TOOK | `design-tokens.css` | 0 | 0 | 0 | 无（没有低于阈值的读数） | 无（这一枚没有低于阈值的读数） |
| `.v8-batch-receipt-plan` | NOT_REACHED_ON_THE_PATHS_I_TOOK | `features/discovery/discovery-batch.css` | 0 | 0 | 0 | 无（没有低于阈值的读数） | 无（这一枚没有低于阈值的读数） |
| `.v8-batch-receipt-rows small` | NOT_REACHED_ON_THE_PATHS_I_TOOK | `features/discovery/discovery-batch.css` | 0 | 0 | 0 | 无（没有低于阈值的读数） | 无（这一枚没有低于阈值的读数） |

没上过屏的这几枚我具名报出，不记成通过：`.cn-collections__retry:disabled`（`features/collections/collections.css`）、`.cn-footprints__note--absent`（`features/checkin/footprint.css`）、`.cn-footprints__retry:disabled`（`features/checkin/footprint.css`）、`.cn-footprints__source`（`features/checkin/footprint.css`）、`.cn-footprints__when`（`features/checkin/footprint.css`）、`.cn-pending-batch-blocked`（`features/pending/pendingSet.css`）、`.cn-pending-batch-line`（`features/pending/pendingSet.css`）、`.cn-pending-chip-sub`（`features/pending/pendingSet.css`）、`.cn-pending-facts`（`features/pending/pendingSet.css`）、`.cn-pending-note`（`features/pending/pendingSet.css`）、`.cn-pending-row-cause`（`features/pending/pendingSet.css`）、`.cn-pending-row-meta`（`features/pending/pendingSet.css`）、`.cn-pending-rule`（`features/pending/pendingSet.css`）、`.cn-pending-token`（`features/pending/pendingSet.css`）、`.cn-poster-share:disabled`（`features/poster/trip-poster.css`）、`.cn-prep-survey-count`（`features/discovery/prepAbandonSurvey.css`）、`.cn-prep-survey-door`（`features/discovery/prepAbandonSurvey.css`）、`.cn-prep-survey-note-label`（`features/discovery/prepAbandonSurvey.css`）、`.cn-prep-survey-sub`（`features/discovery/prepAbandonSurvey.css`）、`.cn-prep-survey-where`（`features/discovery/prepAbandonSurvey.css`）、`.cn-pretrip-anchor`（`features/checklist/pretripChecklist.css`）、`.cn-pretrip-basis`（`features/checklist/pretripChecklist.css`）、`.cn-shared-code-label`（`features/shared/sharedJourney.css`）、`.cn-shared-details summary`（`features/shared/sharedJourney.css`）、`.cn-spend-line-strength`（`features/trip/spend.css`）、`.cn-stop-checkin:disabled`（`features/checkin/footprint.css`）、`.cn-trash-details summary`（`features/trash/journeyTrash.css`）、`.cn-trash-row-state`（`features/trash/journeyTrash.css`）、`.cn-trash-row-when`（`features/trash/journeyTrash.css`）、`.plan-ai-field textarea`（`styles.css`）、`.trial-field input`（`design-tokens.css`）、`.trial-field textarea`（`design-tokens.css`）、`.v8-batch-receipt-plan`（`features/discovery/discovery-batch.css`）、`.v8-batch-receipt-rows small`（`features/discovery/discovery-batch.css`）。
它们要的是状态而不是路由：例如回收站与待规划那几枚要真有一批候选或一条已删行程才画得出，我这趟只按 URL 进屏、没有伪造这些状态（伪造出来的读数不是产品的读数）。

68 趟扫描的外壳全部挂载，`not_mounted` 集合为空。

### 最差读数逐枚（低于阈值的都在这一节，屏上文字一并贴出）

- `.cn-access-trip-row` 在 `features/access/access.css`（light 档，390x844 形，16px 字号）屏上文字「counter(cn-access-trip)」，比值 3.33，要求 4.5，字色 rgb(134, 134, 139)，底色 [245, 245, 247]（来自 ``），该枚读数来自 `networkidle` 导航策略。
- `.cn-live-toolbar .v8-quiet-button + .v8-quiet-button` 在 `design-tokens.css`（light 档，390x844 形，13px 字号）屏上文字「·」，比值 3.33，要求 4.5，字色 rgb(134, 134, 139)，底色 [245, 245, 247]（来自 ``），该枚读数来自 `networkidle` 导航策略。
- `.cn-pending-details summary` 在 `features/pending/pendingSet.css`（light 档，390x844 形，13px 字号）屏上文字「技术详情」，比值 3.62，要求 4.5，字色 rgb(134, 134, 139)，底色 [255, 255, 255]（来自 ``），该枚读数来自 `networkidle` 导航策略。
- `.cn-pending-empty-next` 在 `features/pending/pendingSet.css`（light 档，390x844 形，13px 字号）屏上文字「想收进新的地点，去城市探索捕获这一程的地点。」，比值 3.62，要求 4.5，字色 rgb(134, 134, 139)，底色 [255, 255, 255]（来自 ``），该枚读数来自 `networkidle` 导航策略。
- `.cn-pending-reads` 在 `features/pending/pendingSet.css`（light 档，390x844 形，13px 字号）屏上文字「已读活动  6 ·  已读捕获地点  0 ·  已读地点  8 ·  已有某天猫住  6 ·  已被某天排上的捕获  0」，比值 3.62，要求 4.5，字色 rgb(134, 134, 139)，底色 [255, 255, 255]（来自 ``），该枚读数来自 `networkidle` 导航策略。

## 五、我没有做的

产品字节 0 枚改动：这一手只读屏、只写证据件。没跑前端 e2e 整套（`NOT_EXECUTED_BY_CMDR`，本件的结论不依赖测试计数）；没量实体手机；瓦片底图在这台机器仍不加载，所以 `/v8/map` 那几趟用的是 `domcontentloaded` 而不是 `networkidle`（0 趟用了这条策略，屏读的是外壳与文字，没有一个结论依赖瓦片像素）。另两件事仍挂着并具名报出：其一，共享预览口仍服务落地前的产物字节（上一手量的 231759 对 231756），要换代得由号令者动那枚口；其二，「乙」那三行没带档位前缀所以暗档也一起变了，要不要退成 `:root[data-theme="light"]` 前缀写法仍等裁。

## 七、重挂与接法（这一枚是给落地那一侧看的）

本件的屏读在 `45207a0cc0fcae000b619753b4dfccb06594a59f` 上取；交件之后线被重挂过，本件先前那枚 `-r3` 的头 `cb0555f3c72e6d4cee2fc5ce0b96a67c253c3085` 对现读线尖 `d107131c6f6e65d9f207f6bf1b563d1cc8877f89` `git merge-base` 读回空、`git merge-tree` 退 128（`refusing to merge unrelated histories`）——这是血缘事件，不是内容冲突，我不手合。

重切前先证我量的那一面没动：承载 30 枚声明的 13 枚样式表逐枚 `git rev-parse <尖>:<路径>` 现比，blob 相同 13 枚、移动 0 枚 ⇒ 本件的屏读对现读线尖仍成立。

先前那几枚的现读状态（枚枚现取，不抄上一手）：
- `r1` 枝 `refs/heads/review/2d2d7428-ord0509-ink-survey-routes-r1` 远端头现读 `883ee51c77fc449e5875764cda37938d42329183`：`merge-base` 读回 `（空）`、`merge-tree` 退 128、预测树 `（非零，未出树）`。
- `r1-r2` 枝 `refs/heads/review/2d2d7428-ord0509-ink-survey-routes-r1-r2` 远端头现读 `a513df15ee22246dcb8f0e4ec422cb32cf8d3001`：`merge-base` 读回 `（空）`、`merge-tree` 退 128、预测树 `（非零，未出树）`。
- `r3` 枝 `refs/heads/review/2d2d7428-ord0509-ink-survey-routes-r3` 远端头现读 `cb0555f3c72e6d4cee2fc5ce0b96a67c253c3085`：`merge-base` 读回 `（空）`、`merge-tree` 退 128、预测树 `（非零，未出树）`。

接法：本枚 `-r4` 的父提就是现读线尖，落它走快进合；先前那三枚我不重写、不删除，读数以本枚为准（内容与本枚逐段相同，只多本节）。
